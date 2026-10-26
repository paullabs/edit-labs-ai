#!/usr/bin/env python3
"""
Video lado a lado (referencia | nosso) com o audio do projeto, e duas pranchas de quadros
do meio de cada plano. So quando ha referencia; sem ela, a entrega e o render + tripticos.

    mvpy montar_entrega.py <quadros_ref_720> <quadros_nosso_720> <projeto>
"""
import _caminho  # noqa: F401
import json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import projeto

A, B, proj = sys.argv[1], sys.argv[2], Path(sys.argv[3])
cena = projeto.carregar(proj)
CORTES = cena.cortes(); N = CORTES[-1]
from familia_a import c2_letras as _le
try:                                               # a grotesca do sistema (Arial/Liberation) ou a Inter do pacote
    F = ImageFont.truetype(_le.GROTESCA, 22)
    F2 = ImageFont.truetype(_le.GROTESCA, 13)
except OSError:
    F = F2 = ImageFont.load_default()
out = proj / "saida"; out.mkdir(parents=True, exist_ok=True)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1440x1320", "-r", "30",
                      "-i", "-", "-i", str(cena.audio), "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "18",
                      "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out / "lado_a_lado.mp4")],
                     stdin=subprocess.PIPE)
for n in range(N):
    k = max(i for i, c in enumerate(CORTES[:-1]) if c <= n) + 1
    s = Image.new("RGB", (1440, 1320), (18, 18, 18)); d = ImageDraw.Draw(s)
    s.paste(Image.open(f"{A}/{n:04d}.png").convert("RGB"), (0, 40)); s.paste(Image.open(f"{B}/{n:04d}.png").convert("RGB"), (720, 40))
    d.text((12, 8), "REFERENCIA", fill=(255, 210, 80), font=F); d.text((732, 8), "NOSSO", fill=(120, 220, 255), font=F)
    d.text((1180, 8), f"plano {k:2d}  q{n:03d}", fill=(200, 200, 200), font=F)
    p.stdin.write(s.tobytes())
p.stdin.close(); p.wait()
chave = [(a + b) // 2 for a, b in zip(CORTES, CORTES[1:])]
w, h = 150, 267
for parte, lista in (("1", chave[:len(chave) // 2 + 1]), ("2", chave[len(chave) // 2 + 1:])):
    if not lista:
        continue
    s = Image.new("RGB", (len(lista) * (w + 2), 2 * (h + 16)), (20, 20, 20)); d = ImageDraw.Draw(s)
    for j, q in enumerate(lista):
        s.paste(Image.open(f"{A}/{q:04d}.png").convert("RGB").resize((w, h)), (j * (w + 2), 16))
        s.paste(Image.open(f"{B}/{q:04d}.png").convert("RGB").resize((w, h)), (j * (w + 2), h + 32))
        d.text((j * (w + 2) + 2, 1), f"q{q}", fill=(255, 210, 80), font=F2)
    s.save(out / f"quadros_chave_{parte}.jpg", quality=90)
print(f"ok: {out / 'lado_a_lado.mp4'} e pranchas")
