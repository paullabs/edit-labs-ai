"""Folha de conferência dos quadros: python3 -I folha_quadros.py <pasta com qNNNN.png> <saida.jpg> [colunas]"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

pasta, saida = Path(sys.argv[1]), sys.argv[2]
col = int(sys.argv[3]) if len(sys.argv) > 3 else 5
qs = sorted(pasta.glob("q*.png"))
w, h = 288, 512
lin = -(-len(qs) // col)
f = Image.new("RGB", (col * (w + 6) + 6, lin * (h + 24) + 6), (30, 30, 30))
d = ImageDraw.Draw(f)
for i, q in enumerate(qs):
    x, y = 6 + (i % col) * (w + 6), 6 + (i // col) * (h + 24)
    f.paste(Image.open(q).convert("RGB").resize((w, h), Image.LANCZOS), (x, y + 18))
    d.text((x, y + 2), q.stem, fill=(255, 255, 0))
f.save(saida, quality=86)
