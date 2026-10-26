"""
Camada 1 — background.

Papel cinza NEUTRO (193,193,193), sem vinheta, com manchas de baixissima frequencia
(desvio 3). Preto chapado (7,7,7). Os dois foram medidos no trecho 18,9–23,3 s.
"""
import math
import numpy as np
import cv2
from . import W, H

PAPEL = (194.5, 194.5, 194.5)
PRETO = (7.2, 7.2, 7.2)
MANCHAS = 0.0          # medido 0,29: o papel e chapado


def papel(seed=11):
    rng = np.random.default_rng(seed)
    base = np.empty((H, W, 3), np.float32)
    base[:] = PAPEL
    m = rng.normal(0, 1, (H // 48 + 2, W // 48 + 2)).astype(np.float32)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_CUBIC)
    m = cv2.GaussianBlur(m, (0, 0), 18)
    m *= MANCHAS / (m.std() + 1e-6)
    return base + m[..., None]


def preto():
    base = np.empty((H, W, 3), np.float32)
    base[:] = PRETO
    return base


# --- fundos do Hedy completo (cores amostradas nos quadros do original) -------------
ESCURO = (9.0, 9.0, 9.0)            # "EVERYONE"
TEAL = (4.0, 14.0, 15.0)            # atras do roteador: verde-azulado quase preto
SITE = (26.0, 26.0, 25.0)
CEU = [(0.016, (33, 85, 124)), (0.234, (36, 91, 132)), (0.50, (52, 110, 156)),
       (0.78, (64, 130, 179)), (0.98, (75, 145, 193))]
PAREDE = [(0.0, (194, 187, 181)), (1.0, (172, 159, 147))]


def chapado(cor):
    base = np.empty((H, W, 3), np.float32); base[:] = cor
    return base


def degrade_vertical(paradas):
    y = np.linspace(0, 1, H)
    cols = [np.interp(y, [p for p, _ in paradas], [c[k] for _, c in paradas]) for k in range(3)]
    return np.broadcast_to(np.stack(cols, -1)[:, None, :], (H, W, 3)).astype(np.float32).copy()


def escuro():
    return chapado(ESCURO)


def teal():
    img = chapado(TEAL)
    yy, xx = np.ogrid[:H, :W]
    d = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H * .86) / (H * .42)) ** 2)
    return img + (np.clip(1 - d, 0, 1) ** 1.5 * 2.5)[..., None]


def ceu():
    return degrade_vertical(CEU)


def parede():
    img = degrade_vertical(PAREDE)
    xx = np.linspace(1.0, 0.94, W)[None, :, None]          # luz entrando pela esquerda
    return img * xx


def ondas(semente=4):
    """Fundo preto com curvas claras fluindo (o fundo do icone no fim)."""
    img = chapado((13.0, 13.0, 14.0))
    rng = np.random.default_rng(semente)
    lay = np.zeros((H, W), np.float32)
    xs = np.arange(-200, W + 200, 2, dtype=np.float32)
    for fam in range(4):
      y0 = rng.uniform(0, H); a1 = rng.uniform(220, 420); f1 = rng.uniform(0.0022, 0.0040)
      ph = rng.uniform(0, 6.28); incl = rng.uniform(-0.5, 0.5)
      for k in range(7):
        ys = y0 + k * 34 + a1 * np.sin(f1 * xs + ph + k * 0.05) + xs * incl
        pts = np.stack([xs + 200, ys], 1).astype(np.int32).reshape(-1, 1, 2) - np.array([200, 0])
        cv2.polylines(lay, [pts.astype(np.int32)], False, float(rng.uniform(45, 115)), 2, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 1.2)
    return img + lay[..., None]


# --- papel quadriculado escuro (o fundo de "EVERYONE") -------------------------------
# Medido no original (quadro 15, 720 px; valores abaixo ja em 1080): grade de 69,2 px com
# linhas passando pelo centro do quadro, +2,5 niveis sobre o papel; entre as linhas,
# manchas claras alongadas na vertical, poeira e um risco azul em diagonal. Calibrado
# DEPOIS da entrega 720 (x264 1265k): media 10,8/11,0, desvio 3,09/3,03, p5 7/7, p50 10/10,
# p95 16,3/16, linha da grade +2,4/+2,5 (nosso/original). A folha e 1,18x o quadro: no primeiro
# degrau a camera a mostra a 0,764 e sobra borda preta (a folha cobre 90% do quadro).
GRADE_FOLHA = 1.18
GRADE_PASSO = 69.2
GRADE_BASE = 9.8
GRADE_LINHA = (10.0, 2.2)           # amplitude, sigma (px)
GRADE_LINHA_ZOOM = [(0.764, 0.46), (0.881, 0.68), (0.943, 1.0)]   # forca da linha x zoom
GRADE_MANCHA = 4.0
GRADE_MANCHA_SIGMA = (9.1, 15.0)    # px; alongadas na vertical (meia altura 8 x 11 em 720)
GRADE_CROMA = 0.3                   # o papel e quase neutro: R-G 0,44, B-G 0,74
GRADE_POEIRA = (4.0, 10.0)
GRADE_VALE = 1.8                    # vales mais escuros que a base: o p5 do original e 7
RISCO_AZUL = ((406.8, 599.8), (213.1, 802.6))   # pontas no quadro, camera a 1
PRETO_EVERY = (8.0, 8.0, 8.0)       # quadros 0-1, antes da folha entrar (medido 7,3)


def _grade_escura_partes(semente=7):
    """(papel sem linhas (Ht,Wt,3), linhas de amplitude 1 (Ht,Wt)) — a folha maior que o quadro."""
    Wt, Ht = int(round(W * GRADE_FOLHA)), int(round(H * GRADE_FOLHA))
    cx, cy = Wt / 2, Ht / 2
    rng = np.random.default_rng(semente)
    # manchas alongadas na vertical
    n = cv2.GaussianBlur(rng.normal(0, 1, (Ht, Wt)).astype(np.float32), (0, 0),
                         sigmaX=GRADE_MANCHA_SIGMA[0], sigmaY=GRADE_MANCHA_SIGMA[1])
    n /= n.std() + 1e-6
    l = GRADE_BASE + GRADE_MANCHA * np.clip(n - 0.25, 0, None) ** 1.35 - GRADE_VALE * np.clip(-n - 0.3, 0, None)
    # grade: linhas levemente onduladas e de forca irregular
    ond = cv2.GaussianBlur(rng.normal(0, 1, (Ht, Wt)).astype(np.float32), (0, 0), 60)
    ond *= 1.6 / (ond.std() + 1e-6)
    xx = np.arange(Wt, dtype=np.float32)[None, :] + ond
    yy = np.arange(Ht, dtype=np.float32)[:, None] + ond[::-1, ::-1]
    p = GRADE_PASSO
    dx = np.abs((xx - cx + p / 2) % p - p / 2); dy = np.abs((yy - cy + p / 2) % p - p / 2)
    sig = GRADE_LINHA[1]
    linhas = np.maximum(np.exp(-0.5 * (dx / sig) ** 2), np.exp(-0.5 * (dy / sig) ** 2))
    forca = cv2.GaussianBlur(rng.normal(0, 1, (Ht, Wt)).astype(np.float32), (0, 0), 50)
    forca = 0.7 + 0.3 * np.tanh(forca / (forca.std() + 1e-6))
    linhas = (linhas * forca).astype(np.float32)
    img = np.repeat(l[..., None], 3, axis=2)
    # croma muito fraco em manchas (verde, magenta, azul) como no papel fotografado
    cr = cv2.GaussianBlur(rng.normal(0, 1, (Ht, Wt, 3)).astype(np.float32), (0, 0), 12)
    cr -= cr.mean(axis=2, keepdims=True)
    img += cr * (GRADE_CROMA / (cr.std() + 1e-6))
    # poeira
    po = np.zeros((Ht, Wt), np.float32)
    for _ in range(140):
        x, y = rng.uniform(0, Wt), rng.uniform(0, Ht)
        cv2.circle(po, (int(x * 4), int(y * 4)), int(rng.uniform(2, 6)), float(rng.uniform(*GRADE_POEIRA)), -1,
                   cv2.LINE_AA, shift=2)
    img += cv2.GaussianBlur(po, (0, 0), 0.8)[..., None]
    # risco azul: traco macio em diagonal, interrompido
    (x0, y0), (x1, y1) = RISCO_AZUL
    ox, oy = (Wt - W) / 2, (Ht - H) / 2
    ri = np.zeros((Ht, Wt), np.float32)
    for t in np.linspace(0, 1, 90):
        if 0.42 < t < 0.47 or 0.80 < t < 0.84:
            continue
        x = ox + x0 + (x1 - x0) * t + 10 * math.sin(t * 3.1)
        y = oy + y0 + (y1 - y0) * t
        cv2.circle(ri, (int(x * 4), int(y * 4)), int(4 * (11 + 4 * math.sin(t * 7))), 1.0, -1, cv2.LINE_AA, shift=2)
    ri = cv2.GaussianBlur(ri, (0, 0), 6)
    img += ri[..., None] * np.array([3.0, 5.0, 17.0], np.float32)
    return img.astype(np.float32), linhas


def grade_escura(semente=7):
    """Folha inteira (Ht, Wt, 3) com as linhas na forca plena."""
    papel, linhas = _grade_escura_partes(semente)
    return papel + GRADE_LINHA[0] * linhas[..., None]


_folhas = {}


def grade_escura_no_quadro(zoom, semente=7):
    """A folha enquadrada com zoom. A linha da grade some quando a camera esta longe e
    aparece quando chega (medido: +1,39 / +2,08 / +3,08 / +3,03 nos zooms 0,764 / 0,881 /
    0,943 / 0,991) — a foto do papel perde a linha fina ao ser reduzida."""
    if semente not in _folhas:
        _folhas[semente] = _grade_escura_partes(semente)
    papel, linhas = _folhas[semente]
    forca = GRADE_LINHA[0] * float(np.interp(zoom, *zip(*GRADE_LINHA_ZOOM)))
    return no_quadro(papel, zoom) + forca * no_quadro(linhas, zoom, fundo=(0.0,))[..., None]


def no_quadro(folha, zoom=1.0, fundo=PRETO_EVERY):
    """Enquadra uma folha maior que o quadro com zoom em torno do centro."""
    ht, wt = folha.shape[:2]
    M = np.float32([[zoom, 0, W / 2 - zoom * wt / 2], [0, zoom, H / 2 - zoom * ht / 2]])
    return cv2.warpAffine(folha, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                          borderValue=tuple(float(v) for v in fundo))


# --- dobras escuras (fundo do icone no fecho) ----------------------------------------
# Faixas sobrepostas com borda iluminada, como fitas 3D escuras: isolinhas de um campo
# suave. Desenhado DIRETO na tela para qualquer zoom de camera (sem folha gigante): a
# linha de borda fica fina na tela e o sombreado acompanha a escala.
DOBRAS_PASSO = 30.0          # distancia entre camadas vizinhas (unidades do campo)
DOBRAS_GRUPO = 300.0         # as camadas vem em feixes; entre os feixes, vao escuro
DOBRAS_FUNDO = 10.0         # media 19 no original (provisorio: o certo e foto de estoque/gerada)


def dobras_escuras(zoom=1.0, ancora=(W / 2, H / 2), semente=9):
    rng = np.random.default_rng(semente)
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    x = ancora[0] + (xs - ancora[0]) / zoom; y = ancora[1] + (ys - ancora[1]) / zoom
    p1, p2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3)
    # campo com curvas grandes em S: as isolinhas descem da esquerda-alto e dobram
    F = (0.85 * y + 430 * np.sin(0.0019 * x + 0.0005 * y + p1) + 160 * np.sin(0.0031 * y - 0.0012 * x + p2)
         + 0.30 * x)
    gy, gx = np.gradient(F)
    grad = np.sqrt(gx ** 2 + gy ** 2) * zoom + 1e-6
    frac = F / DOBRAS_PASSO - np.floor(F / DOBRAS_PASSO)
    dist = frac * DOBRAS_PASSO / grad                                   # px de tela ate a borda
    g = 0.5 + 0.5 * np.sin(2 * np.pi * F / DOBRAS_GRUPO)                 # forca do feixe
    feixe = np.clip((g - 0.35) / 0.4, 0, 1) ** 1.5
    luz = 22.0 * (1 - frac) ** 4 * feixe                                 # face de cada lamina
    aro = 125.0 * np.exp(-0.5 * (dist / 0.8) ** 2) * (0.25 + 0.75 * feixe)
    profund = 7.0 * feixe
    v = DOBRAS_FUNDO + profund + luz + aro
    return np.repeat(v[..., None], 3, axis=2).astype(np.float32)
