#!/usr/bin/env python3
"""
Confere cada B-roll DENTRO do master: quadros 0,3 s antes da entrada, logo depois dela, no meio, perto do fim e 0,3 s
depois da cena (a volta para o rosto), numa folha em 11_qa/BROLL_NO_MASTER_<versão>.jpg. Rode da pasta do projeto,
com um compose feito no motor por dados (cenas_plano.py), depois do render:

    MV_VERSAO=v02 mvpy broll_no_master.py
"""
import json
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def _fonte(tam, nome="Inter[opsz,wght].ttf"):
    p = ROOT / "fontes" / nome
    return ImageFont.truetype(str(p), tam) if p.exists() else ImageFont.load_default()


def quadro(arq, t, w=150):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", str(arq), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    im = Image.open(BytesIO(png)).convert("RGB")
    return im.resize((w, int(im.height * w / im.width)))


def main():
    import compose as C
    import render as R
    versao = os.environ.get("MV_VERSAO", "v01").strip() or "v01"
    mst = ROOT / "12_master" / f"MASTER_{R.SAIDA}_{versao}.mp4"
    F, FB = _fonte(15), _fonte(16, "ArchivoBlack-Regular.ttf")
    linhas = []
    for nome, v in sorted(((n, v) for n, v in C.INFO.items() if v.get("video")), key=lambda kv: kv[1]["j"][0]):
        j0, j1 = v["j"]
        for a, z in v["video"]:
            ts = [j0 + a - 0.3, j0 + a + 0.1, j0 + (a + z) / 2, j0 + z - 0.2, j1 + 0.3]
            qs = [quadro(mst, t) for t in ts]
            lin = Image.new("RGB", (len(qs) * 154 + 4, qs[0].height + 26), "white")
            d = ImageDraw.Draw(lin)
            d.text((4, 4), f"{nome}  {j0 + a:.2f}–{j0 + z:.2f} s", fill=(0, 0, 0), font=FB)
            for i, (im, t) in enumerate(zip(qs, ts)):
                ImageDraw.Draw(im).text((4, 4), f"{t:.2f}", fill=(255, 255, 0), font=F)
                lin.paste(im, (4 + i * 154, 24))
            linhas.append(lin)
    if not linhas:
        sys.exit("nenhum beat de vídeo no compose (INFO[...]['video'] vazio)")
    out = Image.new("RGB", (max(l.width for l in linhas), sum(l.height + 6 for l in linhas)), "white")
    y = 0
    for l in linhas:
        out.paste(l, (0, y))
        y += l.height + 6
    dst = ROOT / "11_qa" / f"BROLL_NO_MASTER_{versao}.jpg"
    dst.parent.mkdir(exist_ok=True)
    out.save(dst, quality=85)
    print(f"{len(linhas)} B-rolls conferidos -> {dst.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
