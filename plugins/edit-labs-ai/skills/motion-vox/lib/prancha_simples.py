#!/usr/bin/env python3
"""Prancha simples numa folha só, com as cenas que você escolher — inclusive a cartela de abertura (O1),
que o prancha.py da skill não pega. Uma linha por cena: START · MID · END · EXIT.

    python3 prancha_simples.py 08_images/frames 08_images/PRANCHA_a.jpg O1 M1 M2 M3
"""
import sys, glob, os
from PIL import Image, ImageDraw
d = sys.argv[1]; saida = sys.argv[2]; cenas = sys.argv[3:]
W, H = 216, 384
lin = []
for c in cenas:
    row = Image.new("RGB", (W * 4 + 90, H), (20, 20, 22))
    dr = ImageDraw.Draw(row); dr.text((10, H // 2 - 8), c, fill=(250, 240, 120))
    for k, st in enumerate(("START", "MID", "END", "EXIT")):
        f = os.path.join(d, f"{c}_{st}.png")
        if os.path.exists(f):
            im = Image.open(f).convert("RGB").resize((W, H))
            ImageDraw.Draw(im).text((4, 4), st, fill=(255, 255, 0))
            row.paste(im, (90 + k * W, 0))
    lin.append(row)
out = Image.new("RGB", (W * 4 + 90, H * len(lin)), (0, 0, 0))
for i, r in enumerate(lin):
    out.paste(r, (0, i * H))
out.save(saida, quality=86)
print(saida, out.size)
