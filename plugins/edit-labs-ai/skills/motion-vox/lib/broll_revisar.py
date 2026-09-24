#!/usr/bin/env python3
"""
Revisão de vídeo gerado (B-roll) antes de montar: N quadros espaçados do vídeo INTEIRO numa tira por vídeo, com o tempo
de cada quadro, mais duração, resolução, cadência e se há áudio. Quatro quadros não aprovam movimento: use 8 ou mais.
Procure mão deformada, objeto flutuando, troca de cor ou forma no fim, texto acidental e rosto que não devia aparecer,
e anote o trecho útil de cada vídeo.

    mvpy broll_revisar.py SAIDA.jpg VIDEO.mp4 [VIDEO.mp4 ...] [--n 8]
"""
import json
import subprocess
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _fonte(tam):
    p = Path(__file__).resolve().parent / "fontes" / "Inter[opsz,wght].ttf"
    return ImageFont.truetype(str(p), tam) if p.exists() else ImageFont.load_default()


def tira(arq, n=8, w=150):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(arq)],
                                   capture_output=True, text=True).stdout)
    dur = float(pr["format"]["duration"])
    v = next(s for s in pr["streams"] if s["codec_type"] == "video")
    aud = any(s["codec_type"] == "audio" for s in pr["streams"])
    info = f"{Path(arq).stem} · {dur:.2f} s · {v['width']}x{v['height']} · {v['r_frame_rate']} · áudio={'sim' if aud else 'não'}"
    F = _fonte(15)
    qs = []
    for i in range(n):
        t = min(dur - 0.05, (i + 0.5) * dur / n)
        png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(arq), "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True).stdout
        im = Image.open(BytesIO(png)).convert("RGB")
        im = im.resize((w, int(im.height * w / im.width)))
        ImageDraw.Draw(im).text((4, 4), f"{t:.1f}s", fill=(255, 255, 0), font=F)
        qs.append(im)
    h = qs[0].height
    lin = Image.new("RGB", (n * (w + 4), h + 22), (255, 255, 255))
    ImageDraw.Draw(lin).text((4, 2), info, fill=(0, 0, 0), font=F)
    for i, im in enumerate(qs):
        lin.paste(im, (i * (w + 4), 22))
    return lin, info


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    if "--n" in sys.argv:
        args.remove(str(n))
    if len(args) < 2:
        sys.exit(__doc__)
    saida, videos = args[0], args[1:]
    linhas = []
    for v in videos:
        lin, info = tira(v, n)
        print(info)
        linhas.append(lin)
    W = max(l.width for l in linhas)
    out = Image.new("RGB", (W, sum(l.height + 6 for l in linhas)), (255, 255, 255))
    y = 0
    for l in linhas:
        out.paste(l, (0, y))
        y += l.height + 6
    out.save(saida, quality=85)
    print(saida)


if __name__ == "__main__":
    main()
