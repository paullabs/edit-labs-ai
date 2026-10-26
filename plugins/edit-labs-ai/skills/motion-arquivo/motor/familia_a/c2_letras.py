"""
Camada 2 — letras.

Serifa italica estreita de alto contraste: Instrument Serif Italic, corpo 86 em
1080x1920 — o corpo que reproduz as larguras medidas ("Foundation" 369 px,
"Technologies" 380 px, "Became" 242 px). Uma palavra por vez, centrada pela CAIXA DA
TINTA no centro exato do quadro (centro medido: 360,640 em 720x1280).

Rotulo de interface: grotesca bold branca (Inter 800, corpo 73), altura de maiuscula ~50 px.
"""
import math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
from . import W, H

RAIZ = Path(__file__).resolve().parent.parent
SERIFA = str(RAIZ / "fontes" / "InstrumentSerif-Italic.ttf")
INTER = str(RAIZ / "fontes" / "Inter[opsz,wght].ttf")
CORPO = 86
TINTA = (24.0, 18.0, 28.0)       # o tom magenta do nucleo vem do RGB split, nao da tinta
CONTORNO = 1.0                   # contorno na cor da letra (px @1080): o original e mais
                                 # encorpado — traco 16,6 vs 14,0 e altura-x 23 vs 19 em 720
SS = 4                           # supersample: tamanho com precisao de 1/4 px

_cache = {}


def _fonte(path, size, peso=None):
    k = (path, size, peso)
    if k not in _cache:
        f = ImageFont.truetype(path, size)
        if peso is not None:
            try:
                eixos = f.get_variation_axes()
                f.set_variation_by_axes([peso if (a["name"] in (b"Weight", "Weight")) else a["default"]
                                         for a in eixos])
            except Exception:
                pass
        _cache[k] = f
    return _cache[k]


def _tinta_ss(texto, path, size_ss, peso=None, contorno=0.0):
    """Mascara da tinta em supersample, recortada na caixa da tinta."""
    f = _fonte(path, size_ss, peso)
    sw = int(round(contorno * SS))
    l, t, r, b = f.getbbox(texto, stroke_width=sw)
    im = Image.new("L", (r - l + 8 * SS, b - t + 8 * SS), 0)
    ImageDraw.Draw(im).text((4 * SS - l, 4 * SS - t), texto, font=f, fill=255,
                            stroke_width=sw, stroke_fill=255)
    return im.crop(im.getbbox())


def palavra(texto, escala=1.0, centro=(W / 2, H / 2), cor=TINTA, corpo=CORPO):
    """
    Camada RGBA float (H,W,4) com a palavra. A escala e de TRANSFORMACAO (como o
    Scale do After Effects): a fonte e redesenhada no tamanho, entao a letra continua
    nitida em qualquer degrau. Centro pela caixa da tinta, nao pela linha de base.
    """
    m = _tinta_ss(texto, SERIFA, max(1, int(round(corpo * escala * SS))), contorno=CONTORNO * escala)
    w, h = m.size[0] / SS, m.size[1] / SS
    m = m.resize((max(1, int(round(w))), max(1, int(round(h)))), Image.LANCZOS)
    return _colar(m, centro, cor)


def rotulo(texto, tamanho=73, cor=(232.0, 230.0, 238.0)):
    """Mascara do rotulo (L) — quem posiciona e a caixa. Peso 800: o original e mais pesado
    que a Inter Bold ("Bluetooth" com 344 px de largura em 1080)."""
    m = _tinta_ss(texto, INTER, tamanho * SS, peso=800)
    return m.resize((max(1, round(m.size[0] / SS)), max(1, round(m.size[1] / SS))), Image.LANCZOS), cor


def _colar(mask, centro, cor):
    lay = np.zeros((H, W, 4), np.float32)
    mw, mh = mask.size
    x0 = int(round(centro[0] - mw / 2)); y0 = int(round(centro[1] - mh / 2))
    a = np.asarray(mask, np.float32) / 255.0
    xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + mw), min(H, y0 + mh)
    if xa >= xb or ya >= yb:
        return lay
    sub = a[ya - y0:yb - y0, xa - x0:xb - x0]
    lay[ya:yb, xa:xb, :3] = cor
    lay[ya:yb, xa:xb, 3] = sub
    return lay


# --- texto generico do Hedy completo -----------------------------------------------
CAPS_PESO = 700


def mascara(texto, fonte=SERIFA, corpo=60, peso=None, contorno=0.0, tracking=0.0):
    """Mascara (PIL L) da tinta, recortada na caixa da tinta, mais o deslocamento do
    inicio da linha de base em relacao a caixa (para alinhar texto que cresce)."""
    size = max(1, int(round(corpo * SS)))
    f = _fonte(fonte, size, peso)
    sw = int(round(contorno * SS))
    asc, desc = f.getmetrics()
    largura = int(sum(f.getlength(c) for c in texto) + tracking * SS * max(0, len(texto) - 1)) + 8 * SS + 2 * sw
    im = Image.new("L", (max(8, largura), asc + desc + 8 * SS + 2 * sw), 0)
    d = ImageDraw.Draw(im); x = 4 * SS + sw
    for c in texto:
        d.text((x, 4 * SS + sw), c, font=f, fill=255, stroke_width=sw, stroke_fill=255)
        x += f.getlength(c) + tracking * SS
    bb = im.getbbox()
    if bb is None:
        return Image.new("L", (1, 1), 0), (0, 0)
    m = im.crop(bb)
    m = m.resize((max(1, round(m.size[0] / SS)), max(1, round(m.size[1] / SS))), Image.LANCZOS)
    # origem da linha (x do inicio do texto, y do topo da caixa da fonte) relativa a caixa
    return m, ((4 * SS + sw - bb[0]) / SS, (4 * SS + sw - bb[1]) / SS)


def tingir(img, m, x, y, cor, alfa=1.0):
    """Pinta a mascara `m` em `img` com o canto superior esquerdo em (x, y)."""
    a = np.asarray(m, np.float32) / 255.0 * alfa
    h, w = a.shape; x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y); xb, yb = min(img.shape[1], x + w), min(img.shape[0], y + h)
    if xa >= xb or ya >= yb:
        return img
    s = a[ya - y:yb - y, xa - x:xb - x, None]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - s) + np.array(cor, np.float32) * s
    return img


def escrever(img, texto, centro=None, esquerda=None, fonte=SERIFA, corpo=60, cor=TINTA,
             alfa=1.0, peso=None, contorno=0.0, tracking=0.0, escala=1.0):
    """Escreve centrando pela caixa da tinta (centro=(x,y)) ou ancorando a esquerda
    (esquerda=(x, y_centro)). Devolve a caixa (x0, y0, x1, y1) usada."""
    m, _ = mascara(texto, fonte, corpo * escala, peso, contorno * escala, tracking * escala)
    w, h = m.size
    if centro is not None:
        x, y = centro[0] - w / 2, centro[1] - h / 2
    else:
        x, y = esquerda[0], esquerda[1] - h / 2
    tingir(img, m, x, y, cor, alfa)
    return (x, y, x + w, y + h)


def corpo_para_largura(texto, largura, fonte=SERIFA, peso=None, contorno=0.0, tracking=0.0):
    """Corpo que faz `texto` ocupar `largura` px de tinta (busca binaria)."""
    lo, hi = 8.0, 400.0
    for _ in range(22):
        mid = (lo + hi) / 2
        w = mascara(texto, fonte, mid, peso, contorno, tracking)[0].size[0]
        lo, hi = (mid, hi) if w < largura else (lo, mid)
    return (lo + hi) / 2


# --- grotesca do gancho ("EVERYONE") ------------------------------------------------
# Medido contra o original (perfil de colunas, mesma altura e largura): Helvetica Bold
# 0,92, Helvetica Neue Bold 0,91, Arial Bold 0,90 ... Inter 700 0,70. Fica a Arial Bold:
# a perna reta do R e a do original, vem no macOS e no Windows, e no Linux a Liberation
# Sans Bold tem a MESMA metrica. Fonte de sistema: nao viaja dentro do pacote.
def _primeira(*caminhos):
    for c in caminhos:
        if c and Path(c).exists():
            return str(c)
    return None


GROTESCA = _primeira("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                     "C:/Windows/Fonts/arialbd.ttf",
                     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
                     "/usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf",
                     str(RAIZ / "fontes" / "Arimo-Bold.ttf")) or INTER
GROTESCA_PESO = 800 if GROTESCA == INTER else None


def _tinta_glifo(f, ch):
    """Caixa da tinta REAL de um glifo relativa a origem do desenho. O getbbox do Pillow
    (layout basico) ignora o recuo esquerdo positivo: na Arial Bold o E comeca 7 px depois."""
    k = ("tinta", id(f), ch)
    if k not in _cache:
        pad = f.size
        im = Image.new("L", (int(f.getlength(ch)) + 2 * pad, 3 * pad), 0)
        ImageDraw.Draw(im).text((pad, pad), ch, font=f, fill=255)
        l, t, r, b = im.getbbox()
        _cache[k] = (l - pad, t - pad, r - pad, b - pad)
    return _cache[k]


def corpo_para_maiuscula(altura, fonte=GROTESCA, peso=GROTESCA_PESO):
    """Corpo cuja maiuscula (H) tem `altura` px de tinta."""
    _, t, _, b = _tinta_glifo(_fonte(fonte, 400, peso), "H")
    return altura * 400.0 / (b - t)


def linha_digitada(texto, k, esquerda, yc, fonte=GROTESCA, corpo=90.0, tracking=0.0,
                   peso=GROTESCA_PESO, cor=(228.0, 228.0, 228.0), nova=None):
    """
    Camada RGBA (H,W,4) com as k primeiras letras de `texto` numa linha ancorada pela
    TINTA da primeira letra (x = esquerda) e pelo centro da maiuscula (y = yc).

    `nova` e o estado da letra mais recente no degrau — a entrada da Familia A, medida no
    gancho do Hedy: so a ultima letra esta em movimento; ela chega CAIDA e APAGADA (e a
    primeira de todas tambem menor e inclinada). As outras ja estao assentadas.
        nova = {"queda": px, "alfa": 0-1, "escala": fator, "cisalha": graus (topo p/ direita)}
    """
    lay = np.zeros((H, W, 4), np.float32)
    lay[..., :3] = cor
    if k <= 0:
        return lay
    f = _fonte(fonte, max(1, int(round(corpo * SS))), peso)
    hb = _tinta_glifo(f, "H")
    meio = (hb[1] + hb[3]) / 2.0
    larg = sum(f.getlength(c) for c in texto) / SS + tracking * (len(texto) - 1)
    queda = (nova or {}).get("queda", 0.0)
    m = 60
    ox, oy = int(math.floor(esquerda)) - m, int(math.floor(yc - corpo)) - m
    wc, hc = int(larg + corpo) + 2 * m, int(2 * corpo + queda) + 2 * m
    caneta = (esquerda - ox) * SS - _tinta_glifo(f, texto[0])[0]
    topo = (yc - oy) * SS - meio
    assentadas = Image.new("L", (wc * SS, hc * SS), 0)
    d = ImageDraw.Draw(assentadas)
    ultima = None
    for i, ch in enumerate(texto[:k]):
        if nova is not None and i == k - 1:
            ultima = (ch, caneta)
        elif ch != " ":
            d.text((caneta, topo), ch, font=f, fill=255)
        caneta += f.getlength(ch) + tracking * SS
    a = np.asarray(assentadas, np.float32) / 255.0
    if ultima is not None and ultima[0] != " ":
        ch, x = ultima
        im = Image.new("L", (wc * SS, hc * SS), 0)
        ImageDraw.Draw(im).text((x, topo), ch, font=f, fill=255)
        l, t, r, b = im.getbbox()
        cx, cy = (l + r) / 2.0, (t + b) / 2.0
        e = nova.get("escala", 1.0); sh = math.tan(math.radians(nova.get("cisalha", 0.0)))
        M = np.float32([[e, -e * sh, cx - e * cx + e * sh * cy],
                        [0, e, cy - e * cy + queda * SS]])
        n = cv2.warpAffine(np.asarray(im, np.float32) / 255.0, M, (wc * SS, hc * SS), flags=cv2.INTER_LINEAR)
        a = 1 - (1 - a) * (1 - n * nova.get("alfa", 1.0))
    a = cv2.resize(a, (wc, hc), interpolation=cv2.INTER_AREA)
    xa, ya = max(0, ox), max(0, oy); xb, yb = min(W, ox + wc), min(H, oy + hc)
    if xa < xb and ya < yb:
        lay[ya:yb, xa:xb, 3] = a[ya - oy:yb - oy, xa - ox:xb - ox]
    return lay
