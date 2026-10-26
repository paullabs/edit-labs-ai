"""
Camada 5 — movimentos. A camera move a CENA MONTADA; os filtros vem depois.

No Hedy quase todo plano respira (pull-out lento em 48% dos planos). No trecho de
teste: o papel fica parado; o radar fica parado ate 21,53 s e entao a camera acelera
para a esquerda com curva de potencia 3,6 — o corte acontece com ela em alta.
"""
import numpy as np
import cv2
from . import W, H


def borrao_direcional(img, comprimento):
    """Borrao horizontal da saida em chicote. Medido: ~37 px no ultimo passo antes do corte."""
    L = int(round(abs(comprimento)))
    if L < 2:
        return img
    k = np.ones((1, L), np.float32) / L
    return cv2.filter2D(img, -1, k, borderType=cv2.BORDER_REPLICATE)


def camera(img, dx=0.0, dy=0.0, zoom=1.0, fundo=None):
    M = np.float32([[zoom, 0, (1 - zoom) * W / 2 + dx], [0, zoom, (1 - zoom) * H / 2 + dy]])
    val = tuple(float(v) for v in (fundo if fundo is not None else img[0, 0, :3]))
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=val)


# --- curvas de camera por plano ----------------------------------------------------
# Medido: cada plano do Hedy tem seu easing. Lixeira, moldura, icone e site DESACELERAM
# (o grosso do zoom no primeiro quarto); o close colorido ACELERA para dentro do
# desfoque; a multidao faz um S.

def suavizar_curva(u, tipo="linear", p=2.0):
    u = min(1.0, max(0.0, u))
    if tipo == "saida":
        return 1 - (1 - u) ** p
    if tipo == "entrada":
        return u ** p
    if tipo == "s":
        return u ** p / (u ** p + (1 - u) ** p)
    return u


def entre(a, b, u, tipo="linear", p=2.0):
    return a + (b - a) * suavizar_curva(u, tipo, p)
