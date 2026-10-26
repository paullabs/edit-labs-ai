#!/usr/bin/env python3
"""
Triptico de estado por plano: INICIO / MEIO / FIM, ja com o acabamento — o material da
revisao do Diretor (D2/D3). Um PNG por plano e uma prancha geral.

    python3 triptico.py <projeto> [plano1,plano2,...]

Sem triptico o plano nao vai para o render inteiro: e nele que se ve se a entrada, a
permanencia e a saida contam a ideia da batida.
"""
import _caminho  # noqa: F401
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from familia_a.tempo import grade
from familia_a.c4_filtro import acabamento
import projeto

proj = Path(sys.argv[1]); cena = projeto.carregar(proj)
so = {int(x) for x in sys.argv[2].split(",")} if len(sys.argv) > 2 else None
out = proj / "saida" / "tripticos"; out.mkdir(parents=True, exist_ok=True)
linhas = []
for i, p in enumerate(cena.planos, 1):
    if so and i not in so:
        continue
    a, b = p["inicio"], p["fim"]
    qs = sorted({max(cena.INICIO, grade(min(b - 1, max(a, x)))) for x in (a + 2, (a + b) // 2, b - 1)})
    ims = []
    for q in qs:
        img, _, _ = cena.estado(q)
        ims.append(Image.fromarray(np.clip(acabamento(img, semente=q), 0, 255).astype(np.uint8)).resize((360, 640)))
    f = Image.new("RGB", (len(ims) * 366 - 6, 680), (24, 24, 24)); d = ImageDraw.Draw(f)
    for j, (im, q) in enumerate(zip(ims, qs)):
        f.paste(im, (j * 366, 40)); d.text((j * 366 + 4, 22), f"q{q}", fill=(255, 210, 80))
    d.text((4, 4), f"plano {i}  {p['tipo']}  [{a}-{b})", fill=(255, 255, 255))
    f.save(out / f"plano_{i:02d}.png"); linhas.append(f)
    print(f"plano {i:2d} {p['tipo']:20s} -> {out / f'plano_{i:02d}.png'}")
if linhas:
    wmax = max(l.width for l in linhas)
    g = Image.new("RGB", (wmax, sum(l.height for l in linhas)), (0, 0, 0)); y = 0
    for l in linhas:
        g.paste(l, (0, y)); y += l.height
    g.save(out / "prancha.jpg", quality=85); print(out / "prancha.jpg")
