"""Preparo do exemplo do manequim: o manequim de papel de 1890 (American Manikin Co., Wellcome Collection, domínio público).

Os 12 estados foram fotografados na mesma posição, tirando uma peça por vez. A peça que saiu entre o estado i e o
i+1 é a DIFERENÇA entre as duas fotos: recortamos essa região da foto i e ela vira uma peça de verdade, que pode
levantar e mostrar a foto i+1 por baixo (que é exatamente o que havia embaixo dela no boneco).

    clpy manequim_pecas.py     ->  manequim/estado_XX.png (figura recortada) e manequim/peca_XX.png (+ folha)"""
import os
import sys
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
SRC = CM.ASSETS / "pranchas" / "american-manikin-1890"
OUT = AQUI / "manequim"
ALT = 3000                                                    # altura de trabalho (o original baixado tem 6000)
# os passos do vídeo: (estado de cima, estado de baixo); pular estados junta peças (cérebro + rosto, as duas paredes)
PARES = [(0, 2), (2, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11)]


def carrega(nome):
    im = cv2.imread(str(SRC / nome), cv2.IMREAD_COLOR)
    h, w = im.shape[:2]
    return cv2.resize(im, (round(w * ALT / h), ALT), interpolation=cv2.INTER_AREA)


def preenche(m):
    """fecha os buracos de uma máscara (tudo que não é alcançado da borda vira dentro)"""
    h, w = m.shape
    ff = m.copy()
    msk = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, msk, (0, 0), 255)
    return m | cv2.bitwise_not(ff)


def maior(m, n=1, minimo=0):
    k, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    ordem = sorted(range(1, k), key=lambda i: -st[i, cv2.CC_STAT_AREA])
    out = np.zeros_like(m)
    for i in ordem[:n]:
        if st[i, cv2.CC_STAT_AREA] >= minimo:
            out[lab == i] = 255
    return out


def silhueta(bgr):
    """a figura de papel sobre o fundo cinza liso (a sombra do recorte no fundo fica de fora: tem pouca cor)"""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    borda = np.concatenate([bgr[:20].reshape(-1, 3), bgr[-20:].reshape(-1, 3), bgr[:, :20].reshape(-1, 3),
                            bgr[:, -20:].reshape(-1, 3)])
    fundo = np.median(borda, axis=0)
    dist = np.linalg.norm(bgr.astype(np.float32) - fundo, axis=2)
    m = ((hsv[..., 1] > 48) | (dist > 70)).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    m = preenche(maior(m))
    return cv2.GaussianBlur(m, (0, 0), 0.8)


def rgba(bgr, al):
    return Image.fromarray(np.dstack([cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), al]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    nomes = [f"c{i}.jpg" for i in range(10, 22)]
    ims = [carrega(n) for n in nomes]
    sil = silhueta(ims[0])                                     # todas as fotos têm a mesma silhueta (IoU > 0,99)
    info = []
    for i, im in enumerate(ims):
        rgba(im, sil).save(OUT / f"estado_{i:02d}.png")
    for i, j in PARES:
        lab_a = cv2.cvtColor(ims[i], cv2.COLOR_BGR2LAB).astype(np.float32)
        lab_b = cv2.cvtColor(ims[j], cv2.COLOR_BGR2LAB).astype(np.float32)
        d = np.linalg.norm(cv2.GaussianBlur(lab_a, (0, 0), 3) - cv2.GaussianBlur(lab_b, (0, 0), 3), axis=2)
        m = ((d > 14) & (sil > 128)).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
        m = maior(m, n=3, minimo=4000)
        m = preenche(m) & (sil > 128).astype(np.uint8) * 255
        area = int((m > 0).sum())
        al = cv2.GaussianBlur(m, (0, 0), 1.0)
        peca = rgba(ims[i], al)
        peca.save(OUT / f"peca_{i:02d}_{j:02d}.png")
        ys, xs = np.nonzero(m)
        caixa = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if area else None
        info.append({"de": i, "para": j, "fotos": [nomes[i], nomes[j]], "area_px": area, "caixa": caixa})
        print(i, j, nomes[i], "->", nomes[j], area, caixa)
    json.dump({"altura": ALT, "pecas": info}, open(OUT / "pecas.json", "w"), indent=1)
    # folha: cada peça sobre o estado seguinte esmaecido
    tw, th = 300, 540
    fol = Image.new("RGB", (tw * 6, (th + 24) * 2), "white")
    dr = ImageDraw.Draw(fol)
    for n, (i, j) in enumerate(PARES):
        base = Image.open(OUT / f"estado_{j:02d}.png").convert("RGBA")
        fundo = Image.new("RGBA", base.size, (60, 60, 60, 255))
        b2 = base.copy(); b2.putalpha(base.getchannel("A").point(lambda v: v * 0.35)); fundo.alpha_composite(b2)
        fundo.alpha_composite(Image.open(OUT / f"peca_{i:02d}_{j:02d}.png"))
        x, y = (n % 6) * tw, (n // 6) * (th + 24)
        fol.paste(fundo.convert("RGB").resize((tw, th)), (x, y + 24))
        dr.text((x + 4, y + 4), f"peça {i}->{j}: {nomes[i]} -> {nomes[j]}", fill="black")
    fol.save(AQUI / "previa" / "manequim_pecas.jpg", quality=85)


if __name__ == "__main__":
    main()
