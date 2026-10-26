"""Texturas do homem comum de terno (projeção de frente, a mesma da câmera ortográfica do Blender).

paleto.png: azul-marinho com risca de giz, lapela com entalhe, dois botões, bolso do peito com lenço, lapelas dos
bolsos e o punho branco da camisa na ponta da manga.
camisa.png: branca com listra azul fina, gravata vinho listrada com nó, pontas da gola, botões da carcela, cinto com
fivela e a calça (aparecem quando o paletó abre).

    python3 homem2_textura.py  ->  homem2/paleto.png e homem2/camisa.png"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
X0, X1, Z0, Z1 = -0.40, 0.40, 0.64, 1.76
W = 2048
H = round(W * (Z1 - Z0) / (X1 - X0))
MARINHO, MARINHO_LAPELA, TINTA = (34, 44, 68), (44, 56, 86), (14, 17, 26)
CAMISA, LISTRA = (242, 241, 236), (196, 210, 228)
GRAVATA, GRAVATA_RISCA, CINTO, CALCA = (118, 26, 36), (158, 54, 62), (38, 26, 20), (30, 34, 46)


def P(x, z):
    return ((x - X0) / (X1 - X0) * W, (1 - (z - Z0) / (Z1 - Z0)) * H)


def poli(d, pts, fill=None, outline=None, width=1):
    q = [P(*p) for p in pts]
    d.polygon(q, fill=fill)
    if outline:
        d.line(q + [q[0]], fill=outline, width=width, joint="curve")


def la(rng, cor, ruido=3.0):
    base = np.zeros((H, W, 3), np.float32) + cor
    base += rng.normal(0, ruido, (H, W, 1))
    return base


def paleto():
    rng = np.random.default_rng(4)
    base = la(rng, MARINHO)
    for x in np.arange(X0, X1, 0.016):                                   # risca de giz
        px = int(P(x, 0)[0])
        base[:, px:px + 2] += 13
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    d = ImageDraw.Draw(im)
    # o V e o que aparece por dentro do paletó: escuro como o avesso (nunca o branco da camisa, que virava franja
    # branca na borda da lapela)
    poli(d, [(-0.058, 1.47), (0.058, 1.47), (0.0, 1.175)], fill=(20, 24, 36))
    for s in (-1, 1):                                                     # lapelas com o entalhe
        lap = [(s * 0.058, 1.470), (s * 0.002, 1.175), (s * 0.034, 1.215), (s * 0.090, 1.368), (s * 0.072, 1.384),
               (s * 0.100, 1.402), (s * 0.112, 1.458)]
        poli(d, lap, fill=MARINHO_LAPELA, outline=TINTA, width=5)
    for s in (-1, 1):                                                     # a frente abre em curva abaixo do botão
        pts = [(0.004, 1.175), (0.004, 1.06), (0.004, 0.99)] + [(0.004 + s * 0.06 * t ** 2, 0.99 - 0.13 * t)
                                                                for t in np.linspace(0.1, 1, 8)]
        d.line([P(*p) for p in pts], fill=TINTA, width=5, joint="curve")
    poli(d, [(-0.02, 0.99), (0.02, 0.99), (0.08, 0.84), (-0.08, 0.84)], fill=CALCA)
    for z in (1.125, 1.035):                                              # botões
        cx, cy = P(0.006, z)
        r = 0.0085 / (X1 - X0) * W
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(22, 25, 34), outline=(74, 80, 96), width=3)
        for a in (-1, 1):
            for b in (-1, 1):
                d.ellipse([cx + a * r * 0.32 - 3, cy + b * r * 0.32 - 3, cx + a * r * 0.32 + 3, cy + b * r * 0.32 + 3],
                          fill=(74, 80, 96))
    poli(d, [(0.078, 1.305), (0.090, 1.336), (0.098, 1.312), (0.106, 1.331), (0.116, 1.302)], fill=CAMISA,
         outline=(150, 148, 140), width=3)                                # lenço no bolso
    d.line([P(0.070, 1.302), P(0.126, 1.298)], fill=TINTA, width=6)
    for s in (-1, 1):                                                     # lapelas dos bolsos
        poli(d, [(s * 0.062, 1.005), (s * 0.152, 1.003), (s * 0.152, 0.981), (s * 0.062, 0.983)], fill=MARINHO_LAPELA,
             outline=TINTA, width=4)
    return im


def manga(tronco):
    """a manga usa a textura do paletó com o punho da camisa na ponta. O punho NÃO pode estar na textura do tronco:
    projetado de frente, ele caía também na lateral do quadril e aparecia como franja branca quando o braço subia"""
    im = tronco.copy()
    d = ImageDraw.Draw(im)
    for s in (-1, 1):
        poli(d, [(s * 0.190, 0.888), (s * 0.340, 0.888), (s * 0.340, 0.840), (s * 0.190, 0.840)], fill=CAMISA)
        d.line([P(s * 0.190, 0.888), P(s * 0.340, 0.888)], fill=TINTA, width=5)
    return im


def camisa():
    rng = np.random.default_rng(7)
    base = la(rng, CAMISA, 2.0)
    for x in np.arange(X0, X1, 0.009):                                   # listra fina
        px = int(P(x, 0)[0])
        base[:, px:px + 3] = base[:, px:px + 3] * 0.55 + np.array(LISTRA, np.float32) * 0.45
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5))
    d = ImageDraw.Draw(im)
    d.rectangle([0, P(0, 0.925)[1], W, H], fill=CALCA)                   # a calça
    d.rectangle([0, P(0, 0.955)[1], W, P(0, 0.925)[1]], fill=CINTO)      # o cinto
    bx, by = P(0.0, 0.94)
    d.rectangle([bx - 26, by - 30, bx + 26, by + 30], outline=(190, 160, 90), width=7)   # a fivela
    for z in (0.975, 1.03, 1.09):                                         # botões da carcela abaixo da gravata
        cx, cy = P(0.0, z)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(225, 224, 218), outline=(150, 150, 146), width=2)
    d.line([P(0.0, 0.955), P(0.0, 1.06)], fill=(205, 206, 204), width=3)
    tie = [(-0.013, 1.425), (0.013, 1.425), (0.026, 1.10), (0.0, 1.065), (-0.026, 1.10)]
    gr = Image.new("RGB", im.size, GRAVATA)
    g = ImageDraw.Draw(gr)
    for k in range(-60, 40):
        z = 1.065 + k * 0.012
        g.line([P(-0.04, z), P(0.04, z + 0.022)], fill=GRAVATA_RISCA, width=7)
    m = Image.new("L", im.size, 0)
    poli(ImageDraw.Draw(m), tie, fill=255)
    im.paste(gr, (0, 0), m)
    poli(d, tie, outline=TINTA, width=4)
    poli(d, [(-0.017, 1.455), (0.017, 1.455), (0.012, 1.424), (-0.012, 1.424)], fill=(96, 20, 30), outline=TINTA, width=4)
    for s in (-1, 1):                                                     # pontas da gola
        poli(d, [(s * 0.010, 1.452), (s * 0.050, 1.456), (s * 0.030, 1.412)], fill=CAMISA, outline=(140, 140, 136),
             width=4)
    return im


if __name__ == "__main__":
    (AQUI / "homem2").mkdir(exist_ok=True)
    t = paleto()
    t.save(AQUI / "homem2" / "paleto.png")
    manga(t).save(AQUI / "homem2" / "manga.png")
    camisa().save(AQUI / "homem2" / "camisa.png")
    print("ok")
