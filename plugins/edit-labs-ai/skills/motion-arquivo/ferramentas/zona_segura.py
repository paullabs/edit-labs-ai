#!/usr/bin/env python3
"""
Zona segura do Reels: acha todo texto que cai embaixo da interface do Instagram.

    python3 zona_segura.py <projeto> [--passo 6] [--folha saida.png] [--json saida.json]

Como mede: cada degrau é montado duas vezes, com e sem texto (o ImageDraw.text do PIL vira nada na segunda
montagem). A diferença entre as duas é a tinta de TODO texto do quadro, de qualquer tipo de plano, já depois da
câmera — não depende de cada plano declarar onde escreve.

Zona (1080x1920, Reels orgânico; Meta e os guias de 2026 dão 14% em cima e 6% dos lados; a coluna de botões e a
legenda ocupam a direita de baixo e a faixa de baixo):
  topo     y < 270        cabeçalho "Reels" e câmera
  base     y > 1520       nome do perfil, legenda, áudio
  trilho   x > 930 e y > 880   coluna de curtir, comentar, enviar
  bordas   x < 90 ou x > 990
"Fora do meio" é aviso, não erro: o centro do texto fora de y 560-1360 (regra do estilo: texto no meio).
"""
import _caminho  # noqa: F401
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from familia_a import W, H, ZONA, MEIO
import projeto

_texto_original = ImageDraw.ImageDraw.text
_SEM_TEXTO = {"ligado": False}


def _texto(self, *a, **k):
    if _SEM_TEXTO["ligado"]:
        return None
    return _texto_original(self, *a, **k)


ImageDraw.ImageDraw.text = _texto


def tinta(cena_com, cena_sem, g):
    _SEM_TEXTO["ligado"] = False
    a, _, _ = cena_com.estado(g)
    _SEM_TEXTO["ligado"] = True
    b, _, _ = cena_sem.estado(g)
    _SEM_TEXTO["ligado"] = False
    return np.abs(np.asarray(a, np.float32) - np.asarray(b, np.float32)).sum(2) > 60


def regioes(m):
    z = ZONA
    yy = np.arange(H)[:, None]; xx = np.arange(W)[None, :]
    return {"topo": m & (yy < z["topo"]), "base": m & (yy > z["base"]),
            "trilho": m & (xx > z["trilho_x"]) & (yy > z["trilho_y"]) & (yy <= z["base"]),
            "bordas": m & ((xx < z["esquerda"]) | (xx > z["direita"])) & (yy >= z["topo"]) & (yy <= z["base"])}


def guia(im):
    """Desenha a zona por cima de um quadro (PIL RGB)."""
    z = ZONA
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rectangle([0, 0, W, z["topo"]], fill=(255, 0, 80, 70))
    d.rectangle([0, z["base"], W, H], fill=(255, 0, 80, 70))
    d.rectangle([z["trilho_x"], z["trilho_y"], W, z["base"]], fill=(255, 140, 0, 70))
    d.rectangle([z["esquerda"], z["topo"], z["direita"], z["base"]], outline=(0, 255, 120, 200), width=4)
    d.line([0, MEIO[0], W, MEIO[0]], fill=(0, 200, 255, 120), width=3)
    d.line([0, MEIO[1], W, MEIO[1]], fill=(0, 200, 255, 120), width=3)
    return Image.alpha_composite(im.convert("RGBA"), lay).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--passo", type=int, default=6)
    ap.add_argument("--folha")
    ap.add_argument("--json")
    a = ap.parse_args()
    com, sem = projeto.carregar(a.projeto), projeto.carregar(a.projeto)
    achados, fora_meio, piores = [], [], []
    for g in range(com.INICIO + 2, com.FIM, a.passo):
        m = tinta(com, sem, g)
        if not m.any():
            continue
        p = com.plano_de(g)
        idx = com.planos.index(p)
        ys = np.nonzero(m.any(1))[0]; xs = np.nonzero(m.any(0))[0]
        caixa = [int(xs[0]), int(ys[0]), int(xs[-1]), int(ys[-1])]
        r = {k: int(v.sum()) for k, v in regioes(m).items() if v.sum() > 40}
        corpo_ = m.copy(); corpo_[:ZONA["topo"] + 70] = False          # o crédito do alto não conta para o "meio"
        cy = float(np.nonzero(corpo_)[0].mean()) if corpo_.any() else (MEIO[0] + MEIO[1]) / 2
        if r:
            achados.append({"quadro": g, "plano": idx, "tipo": p["tipo"], "caixa": caixa, "pixels": r})
            piores.append((sum(r.values()), g))
        if not (MEIO[0] <= cy <= MEIO[1]):
            fora_meio.append({"quadro": g, "plano": idx, "tipo": p["tipo"], "centro_y": round(cy)})
    por_plano = {}
    for f in achados:
        d = por_plano.setdefault(f["plano"], {"tipo": f["tipo"], "quadros": [], "regioes": set()})
        d["quadros"].append(f["quadro"]); d["regioes"].update(f["pixels"])
    rel = {"projeto": str(a.projeto), "zona": ZONA, "meio": MEIO, "passo": a.passo,
           "planos_com_texto_fora": {k: {"tipo": v["tipo"], "quadros": [v["quadros"][0], v["quadros"][-1]],
                                         "regioes": sorted(v["regioes"])} for k, v in sorted(por_plano.items())},
           "fora_do_meio": fora_meio, "achados": achados}
    print(f"{Path(a.projeto).name}: {len(achados)} degraus com texto fora da zona, em {len(por_plano)} planos; "
          f"{len(fora_meio)} degraus com o texto fora do meio")
    for k, v in sorted(por_plano.items()):
        print(f"  plano {k:2d} {v['tipo']:16s} q{v['quadros'][0]}-{v['quadros'][-1]}  {', '.join(sorted(v['regioes']))}")
    if a.json:
        Path(a.json).write_text(json.dumps(rel, ensure_ascii=False, indent=1))
    if a.folha and piores:
        sel = sorted({g for _, g in sorted(piores, reverse=True)[:12]})
        esc = 0.25; tw, th = int(W * esc), int(H * esc)
        cols = min(6, len(sel)); lin = (len(sel) + cols - 1) // cols
        folha = Image.new("RGB", (cols * tw, lin * (th + 18)), (20, 20, 20))
        dd = ImageDraw.Draw(folha)
        for i, g in enumerate(sel):
            img, _, _ = com.estado(g)
            im = guia(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))).resize((tw, th))
            x0, y0 = (i % cols) * tw, (i // cols) * (th + 18)
            folha.paste(im, (x0, y0 + 18))
            dd.text((x0 + 4, y0 + 3), f"q{g}", fill=(230, 230, 230))
        folha.save(a.folha)


if __name__ == "__main__":
    main()
