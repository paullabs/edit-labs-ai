"""
Camada 4 — filtro. Tudo em espaco de tela, aplicado DEPOIS da camera.

scanline   horizontal, multiplicativa (no preto nao aparece), senoide de 8,07 px
           (5,38 px em 720). Amplitude por canal medida no papel: R 4,9% · G 6,7% ·
           B 5,9%, com cada canal 0,1 periodo atrasado em relacao ao anterior — e isso
           que da a franja de cor nas listras.
rgb_split  vermelho para a esquerda, azul para a direita (medido na borda da letra).
grao       QUASE NENHUM no papel (1,0 medido sem as listras). O grao forte do Hedy
           mora dentro das fotos de arquivo (3,7–4,8), nao num filtro global.
suavizar   o original e macio: a tinta tem borda mole e nucleo claro.
"""
import numpy as np
import cv2
from . import W, H

SCAN_PERIODO = 8.07
SCAN_AMP = (0.016, 0.086, 0.070)
SCAN_FASE = (0.5, 0.6, 0.7)          # fracao do periodo onde cai a linha escura
SPLIT_PX = 1.6        # por canal; borda medida R-B = -1,35 px em 720 depois da compressao
GRAO = 1.9
GRAO_BORRAO = 1.0
SUAVE = 1.05

_scan = None


def scanline(img):
    global _scan
    if _scan is None:
        y = np.arange(H, dtype=np.float32)[:, None]
        _scan = np.stack([1 + a * np.cos(2 * np.pi * (y / SCAN_PERIODO - f))
                          for a, f in zip(SCAN_AMP, SCAN_FASE)], -1).astype(np.float32)
        _scan = np.broadcast_to(_scan, (H, 1, 3)).copy()
    return img * _scan


def rgb_split(img, px=None):
    px = SPLIT_PX if px is None else px      # lido na hora: default de funcao congela no import
    out = img.copy()
    for c, dx in ((0, -px), (2, +px)):
        M = np.float32([[1, 0, dx], [0, 1, 0]])
        out[..., c] = cv2.warpAffine(img[..., c], M, (W, H), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_REPLICATE)
    return out


def grao(img, semente, forca=None):
    forca = GRAO if forca is None else forca
    rng = np.random.default_rng(semente)
    g = rng.normal(0, 1, (H, W)).astype(np.float32)
    g = cv2.GaussianBlur(g, (0, 0), GRAO_BORRAO)
    g *= forca / (g.std() + 1e-6)
    return img + g[..., None]


def suavizar(img, sigma=None):
    sigma = SUAVE if sigma is None else sigma
    return cv2.GaussianBlur(img, (0, 0), sigma) if sigma > 0 else img


ESTILO = "hedy"


def configurar(estilo="hedy"):
    global ESTILO
    ESTILO = estilo


def acabamento(img, semente):
    """A ordem do After Effects: suaviza -> split -> scanline -> grao."""
    if ESTILO == "galeria":
        return acabamento_galeria(img, semente)
    return grao(scanline(rgb_split(suavizar(img))), semente)


# --- galeria documental -------------------------------------------------------------
# Medido na abertura da referencia da galeria: as linhas sao VERTICAIS,
# periodo 5,31 px em 720 (7,97 em 1080) e 5,1% de contraste; na horizontal so 0,8%. Sem vinheta
# medivel na parede. O resto do acabamento e o do Hedy, mais leve.
CRT_PERIODO = 7.97
_crt = None


def linhas_verticais(img):
    global _crt
    if _crt is None:
        x = np.arange(W, dtype=np.float32)[None, :]
        _crt = np.stack([1 + a * np.cos(2 * np.pi * (x / CRT_PERIODO - f))
                         for a, f in zip(SCAN_AMP, SCAN_FASE)], -1).astype(np.float32)
        _crt = np.broadcast_to(_crt, (1, W, 3)).copy()
    return img * _crt


def acabamento_galeria(img, semente):
    return grao(linhas_verticais(rgb_split(suavizar(img, 0.8), 1.0)), semente, 1.5)


# --- so nas fotos ------------------------------------------------------------------
GRAO_FOTO = 5.0          # o grao forte do Hedy mora DENTRO das fotos (3,7-4,8 medido em 720)


def grao_foto(img, semente, forca=None):
    """Grao de filme aplicado so na camada da foto, antes de compor."""
    return grao(img, semente + 7919, GRAO_FOTO if forca is None else forca)


def desfocar(img, sigma):
    return cv2.GaussianBlur(img, (0, 0), sigma) if sigma > 0.3 else img


def corrigir(img, ganho=1.0, saturacao=1.0):
    """Correcao de cor por plano. O original escurece e dessatura as fotos (documentario):
    medido plano a plano, o Ziegfeld tem luz 89 contra 129 do nosso sem correcao."""
    l = (0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2])[..., None]
    return (l + (img - l) * saturacao) * ganho
