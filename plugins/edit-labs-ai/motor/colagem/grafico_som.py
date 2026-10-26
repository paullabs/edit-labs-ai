"""Gráfico do som de um reel: nível da música (RMS de 1 s), picos dos efeitos e o master.
    clpy grafico_som.py <pasta do reel>/som saida.png"""
import sys
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import som as S

pasta, saida = Path(sys.argv[1]), sys.argv[2]
mus = S.ler(pasta / "trilha_no_nivel.wav").mean(axis=1)
sfx = S.ler(pasta / "efeitos_so.wav").mean(axis=1)
mix = S.ler(pasta / "mix.wav").mean(axis=1)
info = json.load(open(pasta / "som.json"))
SR = S.SR
W, H = 1500, 560
im = Image.new("RGB", (W, H), (250, 247, 240))
d = ImageDraw.Draw(im)
dur = len(mix) / SR
X = lambda t: 60 + t / dur * (W - 90)
Y = lambda db: 30 + (0 - db) / 60 * (H - 90)          # 0 dB em cima, −60 embaixo
for db in range(0, -61, -10):
    d.line([(60, Y(db)), (W - 30, Y(db))], fill=(220, 214, 200))
    d.text((8, Y(db) - 6), f"{db} dB", fill=(90, 80, 60))
for t in range(0, int(dur) + 1, 2):
    d.text((X(t) - 6, H - 40), f"{t}s", fill=(90, 80, 60))
def curva(sig, cor, janela=0.5, passo=0.1, esp=2):
    w, h = int(janela * SR), int(passo * SR)
    pts = []
    for i in range(0, len(sig) - w, h):
        v = 10 * np.log10(np.mean(sig[i:i + w] ** 2) + 1e-12)
        pts.append((X(i / SR), Y(max(v, -60))))
    d.line(pts, fill=cor, width=esp)
curva(mix, (40, 40, 40), 0.5, 0.1, 3)                    # o que se ouve (master)
curva(mus, (60, 110, 170), 0.5, 0.1, 2)                   # só a música (antes do master)
cores = {"carimbo": (180, 40, 40), "pouso": (200, 120, 30), "caneta": (120, 150, 60), "tique": (120, 150, 60)}
for e in info["efeitos"]:
    a = int(e["t"] * SR)
    seg = sfx[a: a + int(0.25 * SR)]
    if len(seg):
        pico = 20 * np.log10(np.abs(seg).max() + 1e-9)
        c = cores.get(e["classe"], (140, 60, 150))
        d.line([(X(e["t"]), Y(pico)), (X(e["t"]), H - 60)], fill=c, width=2)
        d.ellipse([X(e["t"]) - 4, Y(pico) - 4, X(e["t"]) + 4, Y(pico) + 4], fill=c)
d.text((70, 8), f"preto = master ({info['master']['I']} LUFS)   azul = música sozinha   barras = picos dos efeitos "
                 f"(vermelho carimbo, laranja pouso, verde caneta/relógio, roxo transições)", fill=(40, 30, 20))
im.save(saida)
