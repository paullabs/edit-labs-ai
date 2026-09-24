#!/usr/bin/env python3
"""
Verificação do master (etapa 8 da motion-vox), da pasta do projeto:
    python3 verificar_master.py
  - quadro, cadência, início e duração do vídeo iguais aos da fonte
  - SINCRONIA: em todo trecho de rosto, o master mostra no instante t o mesmo quadro que a fonte mostra em t
    (comparado na metade de cima, sem legenda). Contagem de quadros NÃO é trava: a fonte da corte-viral tem
    salto de timestamp em algumas emendas, e a cutaway em CFR por cima de uma delas soma 1 quadro sem deriva.
  - áudio: MD5 dos pacotes igual ao da fonte (o render copia o áudio; sem SFX não há reencode)
  - uma folha de contato com o meio de cada cutaway, o pico do flash de saída, a cartela e legenda
Grava 11_qa/VERIFICACAO.json e 11_qa/CONTATO_MASTER.jpg. Sai com 1 se alguma trava falhar.
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import render as R  # noqa: E402

SRC = ROOT / "00_brief" / "fonte.mp4"
import os  # noqa: E402
VERSAO = os.environ.get("MV_VERSAO", "v01").strip() or "v01"
SUF = "" if VERSAO == "v01" else f"_{VERSAO}"
MASTER = ROOT / "12_master" / f"MASTER_{R.SAIDA}_{VERSAO}.mp4"


def probe(f, sel, campos):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries",
                          f"stream={campos}", "-of", "json", str(f)], capture_output=True, text=True).stdout
    return json.loads(out)["streams"][0]


def md5_audio(f):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-map", "0:a:0", "-c", "copy", "-f", "md5", "-"],
                         capture_output=True, text=True).stdout.strip()
    return out.replace("MD5=", "")


def quadro(f, t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(f), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(raw)).convert("RGB")


def _decod(f):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-fps_mode", "passthrough", "-vf",
                          "scale=54:96,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    q = np.frombuffer(raw, np.uint8).reshape(-1, 96, 54).astype(np.float32)
    pts = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                          "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout.split()
    return q, sorted(float(x) for x in pts if x not in ("", "N/A"))


def sincronia():
    """Pior erro (0–255, metade de cima) entre master e fonte no mesmo instante, em pontos de rosto."""
    import bisect
    import numpy as np
    S, ps = _decod(SRC)
    M, pm = _decod(MASTER)
    cuts = [(s_[2], s_[3]) for s_ in R.SHOTS]
    livres, prev = [], 0.0
    for a, b in cuts:
        livres.append((prev, a)); prev = b
    livres.append((prev, R.DUR))
    pontos = []
    for a, b in livres:
        if b - a > 0.6:
            pontos += [a + 0.25, (a + b) / 2, b - 0.25]
    pior, ruins = 0.0, []
    for t in pontos:
        i = min(max(bisect.bisect_left(pm, t) - 1, 0), len(pm) - 1)
        j = min(max(bisect.bisect_left(ps, pm[i] - 1e-4), 0), len(ps) - 1)
        erro = {d: float(np.abs(M[i, :55] - S[j + d, :55]).mean()) for d in (-1, 0, 1) if 0 <= j + d < len(S)}
        melhor = min(erro, key=erro.get)
        pior = max(pior, erro[0])
        if melhor != 0 and erro[melhor] < erro[0] * 0.7:
            ruins.append((round(t, 2), melhor))
    return pior, ruins, len(pontos)


def main():
    v_src = probe(SRC, "v:0", "width,height,r_frame_rate,nb_frames,start_time,duration")
    v_mst = probe(MASTER, "v:0", "width,height,r_frame_rate,nb_frames,start_time,duration")
    a_src, a_mst = md5_audio(SRC), md5_audio(MASTER)
    pior, ruins, npts = sincronia()
    travas = {
        "quadro": (v_src["width"], v_src["height"]) == (v_mst["width"], v_mst["height"]),
        "cadencia": v_src["r_frame_rate"] == v_mst["r_frame_rate"],
        # o master é CFR na grade de 1/59,94; o início da fonte (21–38 ms) não cai na grade: meio quadro
        "inicio_video": abs(float(v_src["start_time"]) - float(v_mst["start_time"])) <= 0.5 / R.FPS,
        "duracao_video": abs(float(v_src["duration"]) - float(v_mst["duration"])) < 1.5 / R.FPS,
        "sincronia": not ruins,
        "audio_md5": a_src == a_mst,
    }
    print(f"  sincronia: {npts} pontos de rosto, pior erro {pior:.2f}, fora de fase: {ruins or 'nenhum'}")
    print(f"  quadros: fonte {v_src['nb_frames']} · master {v_mst['nb_frames']} (informativo)")
    # folha de contato
    pontos = [("cartela", 1.6)]
    for name, fn, t0, t1, tot, cut in R.SHOTS:
        pontos += [(f"{name} meio", (t0 + t1) / 2), (f"{name} saída", t1 - 0.5 * R.EXIT_SLIDE / R.FPS)]
    jan = R._janelas_do_json()
    if jan:
        a, b = max(jan, key=lambda j: j[1] - j[0])
        pontos.append(("legenda", (a + b) / 2))
    th = []
    for nome, t in pontos:
        im = quadro(MASTER, t).resize((216, 384))
        ImageDraw.Draw(im).text((6, 6), f"{nome} {t:.2f}s", fill=(255, 230, 0))
        th.append(im)
    cols = 6
    folha = Image.new("RGB", (216 * cols, 384 * ((len(th) + cols - 1) // cols)), (18, 18, 20))
    for i, im in enumerate(th):
        folha.paste(im, ((i % cols) * 216, (i // cols) * 384))
    (ROOT / "11_qa").mkdir(exist_ok=True)
    folha.save(ROOT / "11_qa" / f"CONTATO_MASTER{SUF}.jpg", quality=88)
    rel = {"master": str(MASTER.relative_to(ROOT)), "fonte": dict(v_src), "master_v": dict(v_mst),
           "audio_md5": {"fonte": a_src, "master": a_mst}, "travas": travas,
           "sincronia": {"pontos": npts, "pior_erro": round(pior, 2), "fora_de_fase": ruins},
           "tamanho_mb": round(MASTER.stat().st_size / 1e6, 1)}
    (ROOT / "11_qa" / f"VERIFICACAO{SUF}.json").write_text(json.dumps(rel, ensure_ascii=False, indent=1))
    for k, ok in travas.items():
        print(f"  {'OK' if ok else '✗ '} {k}")
    print(f"  {rel['tamanho_mb']} MB · {v_mst['nb_frames']} quadros · folha: 11_qa/CONTATO_MASTER{SUF}.jpg")
    return 0 if all(travas.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
