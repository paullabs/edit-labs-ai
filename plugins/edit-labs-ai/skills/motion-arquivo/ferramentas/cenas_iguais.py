#!/usr/bin/env python3
"""
Acha cenas iguais (ou quase) entre vídeos e dentro do mesmo vídeo, para não entregar repetição.

    python3 cenas_iguais.py <saida_dir> <nome>=<video.mp4>:<plano.json> [...] [--limite 0.15]
    python3 cenas_iguais.py <saida_dir> <nome>=<pasta_do_projeto> [...]      (sem render: quadros direto do motor)

Para cada plano: dois quadros (50% e 85% do plano) → o conteúdo sem o fundo (cinza menos o fundo borrado) e a cor
grossa. Distância de duas cenas = 1 − correlação, a menor entre os pares de quadros (0 = idênticas).
Compara todas as cenas de vídeos diferentes e as cenas não vizinhas do mesmo vídeo. Grava:
  <saida>/cenas_iguais.json   pares com distância <= limite (e as "parecidas", até limite + 0,08)
  <saida>/cenas_iguais.jpg    os pares lado a lado, para conferir de olho
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

FPS = 30


def quadro(mp4, t, w=270, h=480):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    if len(pcm) < w * h * 3:
        return None
    return np.frombuffer(pcm[: w * h * 3], np.uint8).reshape(h, w, 3)


def assinatura(img):
    """Conteúdo sem o fundo: cinza 108x192 menos o fundo borrado (papel, canvas, céu); a tinta, a foto e o texto ficam.
    Mais a cor grossa (12x21) para as fotos."""
    import cv2
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_RGB2GRAY), (108, 192), interpolation=cv2.INTER_AREA).astype(np.float32)
    fundo = cv2.GaussianBlur(g, (0, 0), 12)
    c = np.abs(g - fundo)
    c = (c - c.mean()) / (c.std() + 1e-6)
    cor = cv2.resize(img, (12, 21), interpolation=cv2.INTER_AREA).astype(np.float32).flatten()
    cor = (cor - cor.mean()) / (cor.std() + 1e-6)
    return c.flatten(), cor


def dist(s1, s2):
    """1 - correlação do conteúdo (0 = a mesma cena). A cor só conta quando o conteúdo já bate."""
    r = float(np.mean(s1[0] * s2[0]))
    rc = float(np.mean(s1[1] * s2[1]))
    return 1.0 - (0.8 * r + 0.2 * rc)


def quadros_do_projeto(proj):
    """Sem render: os quadros saem direto do motor (mesmo acabamento do render), para iterar rápido nos montadores.
    A conferência final é sempre nos mp4 (a régua depois da compressão)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _caminho  # noqa: F401
    import cv2
    import projeto
    from familia_a.tempo import grade
    from familia_a.c4_filtro import acabamento
    cena = projeto.carregar(proj)

    def q2im(q):
        q = max(cena.INICIO, min(cena.FIM - 1, grade(int(round(q)))))
        img, _, _ = cena.estado(q)
        im = np.clip(acabamento(img, semente=q), 0, 255).astype(np.uint8)
        return cv2.resize(im, (270, 480), interpolation=cv2.INTER_AREA)
    return cena.planos, q2im


def main():
    a = sys.argv[1:]
    lim = float(a[a.index("--limite") + 1]) if "--limite" in a else 0.15
    pos = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--limite")]
    saida = Path(pos[0]); saida.mkdir(parents=True, exist_ok=True)
    cenas = []
    for item in pos[1:]:
        nome, resto = item.split("=", 1)
        if ":" in resto:                                   # nome=<video.mp4>:<plano.json>
            mp4, pj = resto.rsplit(":", 1)
            planos = json.loads(Path(pj).read_text())["planos"]
            pega = lambda q, mp4=mp4: quadro(mp4, q / FPS)
        else:                                              # nome=<pasta do projeto>: quadros do motor
            planos, pega = quadros_do_projeto(resto)
        for k, p in enumerate(planos):
            sig, ims = [], []
            for fr in (0.5, 0.85):
                q = p["inicio"] + (p["fim"] - p["inicio"]) * fr
                im = pega(q)
                if im is not None:
                    sig.append(assinatura(im)); ims.append(im)
            if sig:
                cenas.append({"video": nome, "plano": k + 1, "tipo": p["tipo"], "t": round(p["inicio"] / FPS, 1),
                              "sig": sig, "img": ims[0]})
        print(nome, len(planos), "planos")
    pares = []
    for i in range(len(cenas)):
        for j in range(i + 1, len(cenas)):
            a_, b_ = cenas[i], cenas[j]
            if a_["video"] == b_["video"] and abs(a_["plano"] - b_["plano"]) <= 1:
                continue                                         # vizinhas: o reenquadramento da mesma cena é de propósito
            d = min(dist(x, y) for x in a_["sig"] for y in b_["sig"])
            if d <= lim + 0.08:
                pares.append((d, i, j))
    pares.sort()
    out = [{"dist": round(d, 3), "nivel": "igual" if d <= lim else "parecida",
            "a": {k: cenas[i][k] for k in ("video", "plano", "tipo", "t")},
            "b": {k: cenas[j][k] for k in ("video", "plano", "tipo", "t")}} for d, i, j in pares]
    (saida / "cenas_iguais.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    mostra = pares[:40]
    if mostra:
        W, H = 270, 480
        fol = Image.new("RGB", (4 * (2 * W + 30), ((len(mostra) + 3) // 4) * (H + 40)), (18, 18, 18))
        d_ = ImageDraw.Draw(fol)
        for k, (d, i, j) in enumerate(mostra):
            x = (k % 4) * (2 * W + 30); y = (k // 4) * (H + 40)
            fol.paste(Image.fromarray(cenas[i]["img"]), (x, y + 36)); fol.paste(Image.fromarray(cenas[j]["img"]), (x + W + 6, y + 36))
            d_.text((x + 2, y + 4), f"{d:.3f} {cenas[i]['video']} #{cenas[i]['plano']} {cenas[i]['tipo'][:12]}", fill=(255, 210, 80))
            d_.text((x + 2, y + 18), f"      {cenas[j]['video']} #{cenas[j]['plano']} {cenas[j]['tipo'][:12]}", fill=(255, 210, 80))
        fol.save(saida / "cenas_iguais.jpg", quality=82)
    iguais = sum(1 for o in out if o["nivel"] == "igual")
    print(f"{len(cenas)} cenas; {iguais} pares iguais (<= {lim}), {len(out) - iguais} parecidos")


if __name__ == "__main__":
    main()
