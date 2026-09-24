#!/usr/bin/env python3
"""
kit — mecanica da identidade MOTION-VOX.

Tudo que NAO e conteudo de cena mora aqui: fundo de mesa, carregamento de asset,
separacao de pecas, relogio com ponteiros desenhados, foto montada em cartao, medida
de texto manual, sombra, camera e as curvas de progresso.

O `compose.py` de cada projeto importa daqui e escreve so as cenas. Sem isso cada
projeto reimplementaria a identidade e ela divergiria.

    from kit import *
"""
import sys, math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

import voxlab as V
try:
    import crt as CRT
except Exception:
    CRT = None
from voxlab import (W, H, INK, YELLOW, BLUE, RED, CHARCOAL, PAPER_LIGHT, boil_ctx, boil, boil_full, hand_pie, F_COND, F_MARKER, F_MONO,
                    ink_center, contact_shadow,
                    place, centered, text_layer, hand_circle, hand_arrow,
                    hand_underline, blue_line, clock_hands, rotate_anchor,
                    finish, ease, persona)

ROOT = Path(__file__).resolve().parent
CUT = ROOT / "07_assets" / "cutout"
PLATES = ROOT / "09_plates"
OUTF = ROOT / "08_images" / "frames"
OUTF.mkdir(parents=True, exist_ok=True)

# sombras por classe de material
SH_PAPER = dict(dy=6,  blur=14, opacity=0.15)
SH_CARD  = dict(dy=11, blur=24, opacity=0.17)
SH_TALL  = dict(dy=20, blur=32, opacity=0.20)
SH_TAPE  = dict(dy=3,  blur=9,  opacity=0.11)
SH_ONVID = dict(dy=14, blur=26, opacity=0.42)   # sobre video: precisa cravar mais

# acabamento por tipo de cena
FX_DESK  = dict(grain=0.050, vignette=0.06, chroma=1, sat=0.92)   # mesa de papel
FX_PLATE = dict(grain=0.028, vignette=0.02, chroma=0, sat=1.00)   # sobre o video

# CORPOS CALIBRADOS para as fontes empacotadas: Archivo Narrow e 1,35x mais larga
# que a DIN Condensed do macOS, entao um corpo pensado para a DIN estoura a composicao.
# Permanent Marker fica a 1,04x da Bradley Hand.

# medidas tiradas dos cutouts, em fracao do bitmap
DIAL_CX, DIAL_CY, DIAL_R = 0.4978, 0.6536, 0.4117      # A02_CLOCK
# Caixa da TELA medida em A11_NIGHT (nao centroide de brilho: o centroide puxa
# para o lado errado e o circulo sai grande demais e alto demais).
SCREEN   = (0.681, 0.588)                               # centro, em fracao da foto
SCREEN_WH = (0.202, 0.257)                              # tamanho, em fracao da foto
# A13_EMPTY: o notebook APAGADO ocupa o mesmo papel narrativo da tela acesa.
LAPTOP   = (0.272, 0.505)
LAPTOP_WH = (0.175, 0.200)


def p(frame, a, b):
    """Progresso de um evento entre os frames a e b. Curva de POUSO (ease-out)."""
    if frame <= a:
        return 0.0
    if frame >= b:
        return 1.0
    return ease((frame - a) / (b - a))


def d(frame, a, b):
    """Progresso de um TRACO sendo desenhado. Velocidade quase constante."""
    if frame <= a:
        return 0.0
    if frame >= b:
        return 1.0
    return V.ease_draw((frame - a) / (b - a))


def apply_camera(img, scale, focus=None, pan=(0, 0)):
    """Push de leitura. Operacao de CAMERA: o quadro inteiro aproxima, nenhum objeto
    cresce sozinho. Sem isso o triptico nao representa o
    que vai ao ar.

    `pan` desloca o recorte em px (Style Bible §9.5: pan de 3–8% da largura em 1,5–3s).
    Tem teto (armadilha 2): `pan_max = (scale - 1) * W / 2`. Acima disso o recorte
    encostaria na borda e puxaria preto pra dentro — aqui e travado, nunca vaza."""
    if scale <= 1.0001 and pan == (0, 0):
        return img
    scale = max(scale, 1.0001)
    big = img.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    focus = focus or (W / 2, H / 2)
    fx, fy = focus[0] / W, focus[1] / H
    ox = (big.width - W) * fx - pan[0]
    oy = (big.height - H) * fy - pan[1]
    ox = min(max(ox, 0), big.width - W)
    oy = min(max(oy, 0), big.height - H)
    return big.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))


def bg_paper():
    im = Image.open(CUT.parent / "raw" / "BG_PAPER.png").convert("RGBA")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    return im.crop(((im.width - W) // 2, (im.height - H) // 2,
                    (im.width - W) // 2 + W, (im.height - H) // 2 + H))


def asset(name, width, rotation=0.0):
    return V.load_cutout(CUT / f"{name}.png", target_w=width, rotation=rotation)


_pieces = {}


def piece(name, index, width, rotation=0.0):
    """Uma peca isolada de um asset multi-objeto (fita, clipes, retalhos).
    Sem isso os quatro retalhos entram sempre em fileira e viram padrao, nao mesa."""
    if name not in _pieces:
        im = Image.open(CUT / f"{name}.png").convert("RGBA")
        alpha = (np.asarray(im.getchannel("A")) > 110).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(alpha, 8)
        order = sorted(range(1, n), key=lambda i: -st[i, cv2.CC_STAT_AREA])
        out = []
        for i in order:
            x, y, w, h, _ = st[i]
            sub = im.crop((x, y, x + w, y + h)).copy()
            m = Image.fromarray(((lab[y:y + h, x:x + w] == i) * 255).astype(np.uint8))
            a2 = Image.fromarray(np.minimum(np.asarray(sub.getchannel("A")),
                                            np.asarray(m)))
            sub.putalpha(a2)
            out.append(sub)
        _pieces[name] = out
    im = _pieces[name][index % len(_pieces[name])]
    s = width / im.width
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    return im.rotate(rotation, resample=Image.BICUBIC, expand=True) if rotation else im


def asset_anchor(name, width, rotation, frac):
    """Onde um ponto marcado em fracao do cutout cai depois de escalar E rotacionar.
    Fracao medida no bitmap original nao vale no bitmap rotacionado (expand muda o
    referencial) — mesmo erro de classe que o do mostrador do relogio."""
    base = V.load_cutout(CUT / f"{name}.png", target_w=width)
    pt = (frac[0] * base.width, frac[1] * base.height)
    if not rotation:
        return base, pt
    rot = base.rotate(rotation, resample=Image.BICUBIC, expand=True)
    return rot, rotate_anchor(base.size, rot.size, rotation, pt)


_night = {}


def photo_card(width, rotation=0.0, photo="A11_NIGHT", focus=None, focus_wh=None):
    """
    Fotografia noturna montada em cartao de papel rasgado, como copia impressa com
    margem branca grossa (Style Bible §4.3). A margem nao e enfeite: e ela que separa
    a foto azul-escura do fundo azul-escuro do estudio. Sem cartao, o overlay some.

    Devolve (imagem, ancora_da_tela, rx, ry) — ancora e raios do circulo de anotacao,
    derivados da CAIXA medida da tela, ja corrigidos pela rotacao.
    """
    focus = focus or SCREEN
    focus_wh = focus_wh or SCREEN_WH
    key = (photo, round(width), round(rotation, 2))
    if key in _night:
        return _night[key]
    card = Image.open(CUT / "A05_CARD.png").convert("RGBA").rotate(90, expand=True)
    ph_im = Image.open(CUT / f"{photo}.png").convert("RGBA")

    s = width / card.width
    card = card.resize((int(card.width * s), int(card.height * s)), Image.LANCZOS)
    pw = int(card.width * 0.865)
    ph = int(pw * ph_im.height / ph_im.width)
    ph_im = ph_im.resize((pw, ph), Image.LANCZOS)

    px = (card.width - pw) // 2
    py = int((card.height - ph) * 0.42)          # margem inferior maior, como copia real
    # sombra fina da foto sobre o cartao: sao dois papeis, nao um so
    card.alpha_composite(contact_shadow(card.size, ph_im, (px, py), dy=4, blur=9,
                                        opacity=0.30))
    card.alpha_composite(ph_im, (px, py))

    anchor = (px + focus[0] * pw, py + focus[1] * ph)
    rx, ry = focus_wh[0] * pw * 0.82, focus_wh[1] * ph * 0.88
    if rotation:
        old = card.size
        card = card.rotate(rotation, resample=Image.BICUBIC, expand=True)
        anchor = rotate_anchor(old, card.size, rotation, anchor)
    _night[key] = (card, anchor, rx, ry)
    return card, anchor, rx, ry


_hw_cache = {}


def hand_width(text, fontpath, size, tracking, seed, stroke_w=2):
    """
    Largura REAL do texto manual, medida no desenho.
    `V.text_width` soma avancos de fonte e ignora que o modo `hand` rotaciona e desloca
    cada caractere — subestima em ate 20%. Uma fita dimensionada por essa largura fica
    menor que o texto que vai por cima dela, e palavras longas em caixa alta vazam para
    fora da fita.
    """
    key = (text, fontpath, size, tracking, seed, stroke_w)
    if key not in _hw_cache:
        lay = text_layer((W, H), text, fontpath, size, (W // 2, H // 2), anchor="mm",
                         stroke_w=stroke_w, tracking=tracking, hand=True, seed=seed)
        bb = lay.getbbox()
        _hw_cache[key] = (bb[2] - bb[0]) if bb else V.text_width(text, fontpath, size,
                                                                tracking)
    return _hw_cache[key]


def fade(im, k):
    if k >= 1.0:
        return im
    o = im.copy()
    o.putalpha(o.getchannel("A").point(lambda v: int(v * max(0.0, min(1.0, k)))))
    return o


_dial_cache = {}


def clean_dial():
    """Mostrador com os ponteiros originais apagados. Calculado uma vez."""
    if "im" in _dial_cache:
        return _dial_cache["im"]
    im = Image.open(CUT / "A02_CLOCK.png").convert("RGBA")
    a = np.asarray(im).copy()
    h, w = a.shape[:2]
    cx, cy, r = DIAL_CX * w, DIAL_CY * h, DIAL_R * w
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    hands = ((d < r * 0.80) & (lum < 175)).astype(np.uint8)
    hands = cv2.dilate(hands, np.ones((3, 3), np.uint8), iterations=3)
    ring = (d > r * 0.30) & (d < r * 0.60) & (lum > 205)
    dial_rgb = a[..., :3][ring].mean(axis=0)
    patch = a[..., :3].astype(np.float32).copy()
    for c in range(3):
        patch[..., c] = np.where(hands > 0, dial_rgb[c], patch[..., c])
    patch = cv2.GaussianBlur(patch, (0, 0), 1.6)
    a[..., :3] = np.where(hands[..., None] > 0, patch, a[..., :3]).astype(np.uint8)
    _dial_cache["im"] = Image.fromarray(a)
    return _dial_cache["im"]


def clock_at(minutes, width, rotation=0.0):
    """
    Relogio com os ponteiros DESENHADOS POR NOS, a partir de um total em minutos
    (aceita fracao, entao o ponteiro pode varrer). A hora vira dado controlado e
    animavel — com a hora estatica do bitmap o objeto fica morto em cena.

    Devolve (imagem, centro_do_mostrador, raio) ja corrigidos pela rotacao.
    """
    im = clean_dial().copy()
    w, h = im.size
    cx, cy, r = DIAL_CX * w, DIAL_CY * h, DIAL_R * w
    hh, mm = int(minutes // 60), minutes % 60.0
    im.alpha_composite(clock_hands(im.size, cx, cy, r, hh, mm,
                                   width=max(5, int(r * 0.070))))
    s = width / im.width
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    c2, r2 = (cx * s, cy * s), r * s
    if rotation:
        old = im.size
        im = im.rotate(rotation, resample=Image.BICUBIC, expand=True)
        c2 = rotate_anchor(old, im.size, rotation, c2)
    return im, c2, r2




# =====================================================================================
# Registros reutilizaveis: trama de jornal, borda rasgada, balao de fala, carimbo,
# contagem manual, foto em tela cheia, cartao de foto sem asset e a etiqueta amarela.
# Ficam no kit para o compose.py de cada projeto nao reimplementar.
# =====================================================================================
from PIL import ImageDraw, ImageChops, ImageFilter
from voxlab import RED, F_BLACK, F_SERIF


def halftone(rgb, cell=6.4, angle=17.0, mix=0.60):
    """
    Trama de meio-tom: a imagem vira pontos de tinta sobre papel, como jornal impresso.
    O ponto cresce com a densidade (raio ~ sqrt da tinta) e a grade e rotacionada —
    reticula alinhada ao pixel produz moire. `mix` deixa uma fracao em duotone continuo
    por baixo dos pontos: com 100% de trama o rosto vira mancha; com 60% ainda le.
    E o que permite uma foto de estudio gerada e um frame de podcast comprimido conviverem
    no mesmo quadro — os dois passam pelo mesmo processo de impressao.
    """
    h, w = rgb.shape[:2]
    g = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0
    g = np.clip((g - 0.05) / 0.86, 0.0, 1.0) ** 1.05     # jornal nao tem preto nem branco puro
    t = math.radians(angle)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xr = xx * math.cos(t) - yy * math.sin(t)
    yr = xx * math.sin(t) + yy * math.cos(t)
    fx = (xr % cell) / cell - 0.5
    fy = (yr % cell) / cell - 0.5
    d = np.sqrt(fx * fx + fy * fy) / 0.7071
    r = np.sqrt(np.clip(1.0 - g, 0, 1)) * 0.98
    dot = np.clip((r - d) * cell * 0.80 + 0.5, 0, 1)
    out = np.zeros_like(rgb)
    for c in range(3):
        ht = PAPER_LIGHT[c] + (INK[c] - PAPER_LIGHT[c]) * dot
        duo = PAPER_LIGHT[c] + (INK[c] - PAPER_LIGHT[c]) * (1.0 - g)
        out[..., c] = ht * mix + duo * (1.0 - mix)
    return out


def torn(alpha, margin, tear, seed):
    """Margem de papel rasgada em volta do alfa. Ruido de BAIXA frequencia: rasgo de
    papel tem fibra grossa; ruido fino daria borda serrilhada de recorte digital."""
    k = np.ones((3, 3), np.uint8)
    big = cv2.dilate((alpha > 0.5).astype(np.uint8), k, iterations=int(margin))
    big = cv2.GaussianBlur(big.astype(np.float32), (0, 0), max(1.0, margin * 0.5))
    rng = np.random.default_rng(seed)
    n = cv2.GaussianBlur(rng.normal(0, 1, alpha.shape).astype(np.float32), (0, 0), 6.0)
    n /= (np.abs(n).max() + 1e-6)
    return np.clip(((big + n * tear) - 0.40) * 6.0, 0, 1)


_clip_cache = {}


def clipping(im, margin=17, tear=0.34, seed=3, cell=6.4, mix=0.60):
    """Trama + margem rasgada numa camada JA ESCALADA para o tamanho final. A ordem
    importa: tramar antes de escalar faria os pontos sumirem na reducao."""
    pad = int(margin * 1.9) + 10
    src = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    src.alpha_composite(im, (pad, pad))
    a = np.asarray(src.getchannel("A"), np.float32) / 255.0
    printed = halftone(np.asarray(src.convert("RGB"), np.float32), cell, 17.0, mix)
    paper_m = torn(a, margin, tear, seed)
    rng = np.random.default_rng(seed + 77)
    grain = cv2.GaussianBlur(rng.normal(0, 3.4, a.shape).astype(np.float32), (0, 0), 1.6)
    out = np.zeros((src.height, src.width, 4), np.float32)
    for c in range(3):
        out[..., c] = (PAPER_LIGHT[c] + grain) * (1 - a) + printed[..., c] * a
    out[..., 3] = np.maximum(paper_m, a) * 255.0
    o = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    bb = o.getbbox()
    return o.crop(bb) if bb else o


def clip_asset(name, width, rotation=0.0, seed=3, margin=17, mix=0.60):
    """Asset recortado de jornal (trama + borda rasgada), com cache — a trama e cara e
    nao muda entre frames."""
    key = (name, int(width), round(rotation, 2), seed, margin, round(mix, 2))
    if key not in _clip_cache:
        base = clipping(asset(name, width), margin=margin, seed=seed, mix=mix)
        if rotation:
            base = base.rotate(rotation, resample=Image.BICUBIC, expand=True)
        _clip_cache[key] = base
    return _clip_cache[key]


def speech_bubble(size, cx, cy, rx, ry, tail, progress=1.0, width=8, color=INK,
                  seed=11, amp=4.5):
    """
    Balao de fala a mao, bicuda apontando para quem fala. Preenchimento entra nos
    primeiros 45% e o contorno e DESENHADO por cima — a ordem da mao. A base da bicuda
    tem largura FIXA em px (abrir por angulo da base enorme em balao largo).
    """
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    if progress <= 0:
        return lay
    fp = min(1.0, progress / 0.45)
    ang = math.atan2(tail[1] - cy, tail[0] - cx)
    ex, ey = cx + (rx - 4) * math.cos(ang), cy + (ry - 4) * math.sin(ang)
    nx, ny = -math.sin(ang), math.cos(ang)
    b0, b1 = (ex + nx * 23, ey + ny * 23), (ex - nx * 23, ey - ny * 23)
    m = Image.new("L", size, 0)
    md = ImageDraw.Draw(m)
    md.ellipse([cx - rx + 5, cy - ry + 5, cx + rx - 5, cy + ry - 5], fill=255)
    md.polygon([b0, b1, tail], fill=255)
    fillc = Image.new("RGBA", size, PAPER_LIGHT + (255,))
    fillc.putalpha(m.point(lambda v: int(v * fp)))
    lay.alpha_composite(fillc)
    lay.alpha_composite(hand_circle(size, cx, cy, rx, ry, progress=progress, passes=1,
                                    width=width, color=color, seed=seed, amp=amp))
    tp = max(0.0, (progress - 0.55) / 0.45)
    if tp > 0:
        d_ = ImageDraw.Draw(lay)
        for i, pt in enumerate((b0, b1)):
            pts = V.jitter(V.smooth_path([pt, ((pt[0] + tail[0]) / 2, (pt[1] + tail[1]) / 2),
                                          tail]), 2.4, seed + 30 + i)
            V.stroke(d_, V.cut(pts, min(1.0, tp)), width, color + (255,), seed=seed + i)
    return lay


def _d_from(pg):
    """A mao escreve DEPOIS de fechar o balao, nao junto."""
    return max(0.0, min(1.0, (pg - 0.40) / 0.60))


def bubble_com_texto(c, txt, cx, cy, tail, size_pt, progress, seed=11, pad=1.34):
    """Balao dimensionado PELA palavra — como a fita. Medido no desenho (`hand_width`),
    nao na metrica da fonte."""
    tw = hand_width(txt, F_MARKER, size_pt, 6, seed, 3)
    rx = max(96.0, tw * pad / 2 + 26)
    ry = max(64.0, size_pt * 0.86)
    c.alpha_composite(speech_bubble(c.size, cx, cy, rx, ry, tail, progress=progress, seed=seed))
    c.alpha_composite(text_layer(c.size, txt, F_MARKER, size_pt, (cx, cy), color=INK,
                                 anchor="mm", stroke_w=3, tracking=6, hand=True, seed=seed,
                                 mode="write", optical=True, progress=_d_from(progress)))
    return rx, ry


_fc_cache = {}


def foto_cheia(nome, vinheta=0.55, escurece=0.05):
    """
    Fotografia cobrindo o quadro inteiro, com vinheta — registro "foto em tela cheia"
    (`hierarquia-e-profundidade.md` §3). Le de `07_assets/raw/<nome>.png`. A foto tem
    que ser GERADA em 9:16: recortar 4:3 joga fora ~58% da largura (armadilha 52).
    """
    key = (nome, round(vinheta, 2), round(escurece, 2))
    if key in _fc_cache:
        return _fc_cache[key]
    im = Image.open(CUT.parent / "raw" / f"{nome}.png").convert("RGB")
    s = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * s + 1), int(im.height * s + 1)), Image.LANCZOS)
    ox, oy = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((ox, oy, ox + W, oy + H))
    a = np.asarray(im, np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2)
    r = np.sqrt(nx * nx + ny * ny)
    v = np.clip(1.0 - vinheta * np.clip((r - 0.42) / 0.95, 0, 1) ** 1.6, 0, 1)[..., None]
    _fc_cache[key] = Image.fromarray(np.clip(a * v * (1.0 - escurece), 0, 255)
                                     .astype(np.uint8)).convert("RGBA")
    return _fc_cache[key]


def carimbo(canvas, txt, cx, cy, corpo, rot, p_txt, p_anel, cor=RED, seed=51):
    """Carimbo SOBRE o documento, girado, 60-75% da largura dele (armadilha 48). Texto e
    anel numa camada propria, girados JUNTOS."""
    tw = V.text_width(txt, F_BLACK, corpo, 3)
    m = int(corpo * 1.7)
    Wl, Hl = int(tw + m * 2), int(corpo * 3.2)
    sub = Image.new("RGBA", (Wl, Hl), (0, 0, 0, 0))
    sub.alpha_composite(text_layer((Wl, Hl), txt, F_BLACK, corpo, (Wl // 2, Hl // 2),
                                   color=cor, anchor="mm", tracking=3, mode="block",
                                   rise=5, progress=p_txt))
    sub.alpha_composite(hand_circle((Wl, Hl), Wl // 2, Hl // 2, tw * 0.60, corpo * 0.88,
                                    progress=p_anel, passes=2, width=8, color=cor,
                                    seed=seed, amp=7))
    if rot:
        sub = sub.rotate(rot, resample=Image.BICUBIC, expand=True)
    canvas.alpha_composite(sub, (int(cx - sub.width / 2), int(cy - sub.height / 2)))


def tally_marks(size, x0, y, n, gap, progress, frame, height=64, width=9, color=INK,
                seed=71):
    """n tracos verticais revelados um a um — contagem manual (registro "dado a mao")."""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    if progress <= 0 or n <= 0:
        return lay
    per = 1.0 / n
    d_ = ImageDraw.Draw(lay)
    for i in range(n):
        local = (progress - i * per) / per
        if local <= 0:
            break
        x = x0 + i * gap
        pts = V.jitter([(x, y - height / 2), (x, y + height / 2)], 2.2, seed + i)
        V.stroke(d_, V.cut(pts, min(1.0, local)), width, color + (255,), seed=seed + i)
    if frame is not None:
        lay = V.boil_full(lay, frame, **V.BOIL_PRESETS["ink"])
    return lay


_card_cache = {}


def photo_card_custom(photo, width, margin=0.055, bottom=0.16, tear=0.0, seed=5,
                      rotation=0.0):
    """
    Cartao de foto revelada com margem branca desenhada em PIL (nao depende do A05_CARD).
    Le `07_assets/raw/<photo>.png`. Devolve (cartao, (px, py, pw, ph)) — onde a foto cai
    DENTRO do cartao, para ancorar anotacao. `tear` > 0 rasga a borda: recorte colado na
    mesa; `tear=0` e a copia guardada (armadilha: e essa distincao que separa os dois).
    """
    key = (photo, int(width), round(margin, 3), round(bottom, 3), round(tear, 2), seed,
           round(rotation, 2))
    if key in _card_cache:
        return _card_cache[key]
    ph_im = Image.open(CUT.parent / "raw" / f"{photo}.png").convert("RGBA")
    pw = int(width * (1 - 2 * margin))
    ph = int(pw * ph_im.height / ph_im.width)
    ph_im = ph_im.resize((pw, ph), Image.LANCZOS)
    card_h = int(ph + width * margin * 2 + width * bottom)
    card = Image.new("RGBA", (width, card_h), PAPER_LIGHT + (255,))
    px = py = int(width * margin)
    card.alpha_composite(contact_shadow(card.size, ph_im, (px, py), dy=4, blur=9, opacity=0.30))
    card.alpha_composite(ph_im, (px, py))
    if tear > 0:
        pad = 16
        big = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
        big.alpha_composite(card, (pad, pad))
        a = np.asarray(big.getchannel("A"), np.float32) / 255.0
        m = torn(a, 4, tear, seed)
        big.putalpha(Image.fromarray((np.minimum(a, m) * 255).astype(np.uint8)))
        card, px, py = big, px + pad, py + pad
    if rotation:
        old = card.size
        card = card.rotate(rotation, resample=Image.BICUBIC, expand=True)
        px += (card.width - old[0]) // 2
        py += (card.height - old[1]) // 2
    _card_cache[key] = (card, (px, py, pw, ph))
    return _card_cache[key]


# ===================================================================== etiqueta amarela
_yl_cache = {}


def yellow_label(size, text, fontpath=None, fontsize=72, xy=None, progress=1.0,
                 rotation=-1.5, pad=0.55, outline=False, color=YELLOW, ink=INK,
                 tracking=2, seed=13, boil=True, largura_px=None, sombra=False):
    """
    Etiqueta de marca-texto amarelo com texto por cima — o dispositivo mais repetido da
    Vox (Style Bible §4.3; estudo Porsche bf11/bf15/bf17). Complementa a fita crepe
    bege e leva o amarelo da paleta alem do sublinhado.

    A faixa e uma PINCELADA, nao um retangulo: borda de baixa frequencia (`torn`), grao,
    leve rotacao. Entra como traco — esquerda->direita nos primeiros 55% do progresso —
    e o texto entra em bloco depois. `outline=True` fecha o retangulo fino de tinta por
    cima (bf01, bf15). Faixa e texto compartilham a semente de boil: sao um objeto so
    (armadilha 34). `xy` e o CENTRO da etiqueta.
    """
    fontpath = fontpath or F_COND
    xy = xy or (W // 2, H // 2)
    tw = V.text_width(text, fontpath, fontsize, tracking)
    # `largura_px` forca a largura da FAIXA sem mexer no texto — a cartela de ano precisa
    # de uma faixa do tamanho do numero, e medir espacos em branco nao da a mesma largura.
    w = int(largura_px if largura_px else tw + fontsize * pad * 2)
    h = int(fontsize * 1.42)
    key = (w, h, seed, round(rotation, 2))
    if key not in _yl_cache:
        pp = 14
        m = np.zeros((h + 2 * pp, w + 2 * pp), np.float32)
        m[pp:pp + h, pp:pp + w] = 1.0
        m = torn(m, 3, 0.22, seed)
        rng = np.random.default_rng(seed + 5)
        grain = cv2.GaussianBlur(rng.normal(0, 4.0, m.shape).astype(np.float32), (0, 0), 2.0)
        strip = np.zeros((m.shape[0], m.shape[1], 4), np.float32)
        for c in range(3):
            strip[..., c] = np.clip(color[c] + grain, 0, 255)
        strip[..., 3] = m * 255 * 0.94
        _yl_cache[key] = Image.fromarray(strip.astype(np.uint8), "RGBA")
    s = _yl_cache[key].copy()
    sp = min(1.0, progress / 0.55)
    tp = max(0.0, (progress - 0.55) / 0.45)
    if sp < 1.0:
        mk = Image.new("L", s.size, 0)
        ImageDraw.Draw(mk).rectangle([0, 0, int(s.width * sp), s.height], fill=255)
        s.putalpha(ImageChops.multiply(s.getchannel("A"), mk))
    if boil:
        s = V._auto_boil(s, "paper", seed=seed)
    if outline and sp >= 1.0:
        ImageDraw.Draw(s).rectangle([16, 16, s.width - 17, s.height - 17],
                                    outline=ink + (230,), width=2)
    sub = Image.new("RGBA", s.size, (0, 0, 0, 0))
    sub.alpha_composite(s)
    sub.alpha_composite(text_layer(s.size, text, fontpath, fontsize,
                                   (s.width // 2, s.height // 2), color=ink, anchor="mm",
                                   tracking=tracking, mode="block", rise=8, progress=tp,
                                   boil_seed=seed))
    if rotation:
        sub = sub.rotate(rotation, resample=Image.BICUBIC, expand=True)
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    pos = centered(sub, xy[0], xy[1])
    if sombra:
        # Sobre FOTO a faixa some: medido, uma etiqueta amarela sobre carroceria vermelha
        # da contraste externo de 1,14 — o bloco inteiro se dissolve. A sombra de contato
        # e o que descola. Sobre papel ela e desnecessaria (SH_TAPE ja resolve), entao
        # `sombra` e opcional e default False.
        lay.alpha_composite(contact_shadow(size, sub, pos, **(
            sombra if isinstance(sombra, dict) else dict(dy=9, blur=22, opacity=0.55))))
    lay.alpha_composite(sub, pos)
    return lay


# ===================================================================== camera: pan e drift
def drift(frame, per_sec=0.005, fps=24.0):
    """Escala de drift constante e discreto (Style Bible §9.5: 0,3–0,8% por segundo).
    Use como `apply_camera(c, drift(frame))` numa cena que nao tem push proprio — o
    quadro nunca fica bit a bit parado, mas nada 'anda'."""
    return 1.0 + per_sec * (frame / fps)


# =====================================================================================
# Registros medidos no estudo Porsche.
# Ver referencias/registros.md para quando usar — e para os limites que evitam virarem
# tique.
# =====================================================================================

def year_card(size, ano, fundo=None, escura=False, progress=1.0, fontsize=210,
              cy=None, marca=True, color_ink=None, seed=61):
    """
    Cartela de ano — o ano em tela cheia, sozinho, como separador de capitulo.

    A referencia ALTERNA clara e escura: bf05 mede 0,1% de massa escura e bf09 mede
    98,5%. A escura e o que quebra uma sequencia palida no miolo da peca; duas claras
    seguidas desperdicam o recurso.

    `fundo`: imagem RGBA ja no tamanho do quadro (foto de arquivo, mapa, papel). Se
    None, usa o papel da mesa. `escura=True` rebaixa e dessatura o fundo e escreve o
    ano em claro. `marca` poe o marca-texto amarelo por baixo do numero (claro) ou um
    sublinhado (escura).

    Ordem de entrada: fundo (ja la) -> numero pousa -> amarelo passa por baixo.
    """
    c = fundo.copy().convert("RGBA") if fundo is not None else bg_paper()
    if c.size != tuple(size):
        s = max(size[0] / c.width, size[1] / c.height)
        c = c.resize((int(c.width * s + 1), int(c.height * s + 1)), Image.LANCZOS)
        c = c.crop(((c.width - size[0]) // 2, (c.height - size[1]) // 2,
                    (c.width - size[0]) // 2 + size[0], (c.height - size[1]) // 2 + size[1]))
    cy = cy if cy is not None else int(size[1] * 0.47)
    ink = color_ink or (PAPER_LIGHT if escura else INK)
    if escura:
        # rebaixa o fundo: e o ano que tem que ler, nao a foto
        a = np.asarray(c.convert("RGB"), np.float32)
        lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
        a = lum * 0.20 + a * 0.06          # dessatura e escurece junto
        # comprime o topo da faixa: ceu e parede claros sobrevivem ao escurecimento
        # proporcional e o ano creme some em cima deles (medido: contraste interno 2,0).
        a = np.clip(a, 0, 96)
        c = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")

    tp = p(progress * 100, 0, 55)          # numero pousa nos primeiros 55%
    mp = d(progress * 100, 50, 100)        # amarelo passa depois, como traco
    txt = str(ano)
    if marca and mp > 0:
        w = V.text_width(txt, F_SERIF, fontsize, 6)
        if escura:
            c.alpha_composite(V.hand_underline(size, int(size[0] / 2 - w * 0.46),
                                               int(size[0] / 2 + w * 0.46),
                                               cy + int(fontsize * 0.52), progress=mp,
                                               width=9, color=YELLOW, seed=seed))
        else:
            w = V.text_width(txt, F_SERIF, fontsize, 6)
            c.alpha_composite(yellow_label(size, "", F_SERIF, fontsize,
                                           (size[0] // 2, cy), progress=mp, rotation=-0.8,
                                           seed=seed, boil=False,
                                           largura_px=int(w * 1.14)))
    num = text_layer(size, txt, F_SERIF, fontsize, (size[0] // 2, cy),
                     color=ink, anchor="mm", tracking=6, mode="block",
                     rise=12, progress=tp, boil_seed=seed)
    if escura and tp > 0:
        sh = Image.new("RGBA", size, (0, 0, 0, 0))
        tint = Image.new("RGBA", size, (8, 7, 9, 255)); tint.putalpha(num.getchannel("A"))
        sh.alpha_composite(tint, (0, 7))
        sh = sh.filter(ImageFilter.GaussianBlur(12))
        sh.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.72)))
        c.alpha_composite(sh)
    c.alpha_composite(num)
    return c


def footer_caption(size, texto, progress=1.0, y=None, fontsize=44, color=None,
                   tri=None, seed=67, sombra=True):
    """
    Legenda de rodape com o triangulo amarelo — o dado numerico SECUNDARIO sobre
    footage (Porsche bf07, bf08, bf30). Serif italica, base do quadro.

    Se o dado e o assunto da fala, ele e CENA, nao rodape. Maximo uma por cena, e
    nunca sobre cena que ja tem tipografia propria.

    `y` fica dentro da exclusao inferior de interface (nada critico abaixo de 1660).
    """
    y = int(H * 0.8125) if y is None else y   # 1560 no vertical; mesma fracao no horizontal
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    if progress <= 0:
        return lay
    color = color or PAPER_LIGHT
    tri = tri or YELLOW
    tw = V.text_width(texto, V.F_ITAL, fontsize, 1)
    gap = int(fontsize * 0.62)
    th = int(fontsize * 0.52)                       # meia altura do triangulo
    x0 = int((size[0] - (tw + gap + th * 1.7)) / 2)  # bloco inteiro centrado
    tp = min(1.0, progress / 0.35)                   # o triangulo entra primeiro
    xp = max(0.0, (progress - 0.30) / 0.70)          # depois o texto, como impressao
    if tp > 0:
        t = Image.new("RGBA", size, (0, 0, 0, 0))
        ImageDraw.Draw(t).polygon([(x0, y - th), (x0, y + th),
                                   (x0 + int(th * 1.55), y)], fill=tri + (255,))
        if tp < 1:
            t.putalpha(t.getchannel("A").point(lambda v: int(v * tp)))
        lay.alpha_composite(t)
    if xp > 0:
        lay.alpha_composite(text_layer(size, texto, V.F_ITAL, fontsize,
                                       (x0 + int(th * 1.7) + gap, y), color=color,
                                       anchor="lm", tracking=1, mode="wipe",
                                       progress=xp, boil_seed=seed))
    if sombra:
        # sobre foto a legenda precisa de sombra propria, senao some no claro
        sh = Image.new("RGBA", size, (0, 0, 0, 0))
        tint = Image.new("RGBA", size, (12, 10, 14, 255)); tint.putalpha(lay.getchannel("A"))
        sh.alpha_composite(tint, (0, 5))
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        sh.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.62)))
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        out.alpha_composite(sh); out.alpha_composite(lay)
        return out
    return lay


def yellow_lens(img, cx, cy, r, progress=1.0, color=YELLOW, forca=0.80, borda=True):
    """
    Lente amarela — circulo translucido em MULTIPLY sobre a regiao citada de uma
    FOTOGRAFIA (Porsche bf19, bf22). Colore a coisa citada em vez de so apontar pra
    ela, que e por que le melhor que a seta.

    Substitui a seta em fotografia; em objeto recortado sobre papel o circulo a mao
    continua sendo o certo. Conta como o acento da cena — nao somar outro amarelo.

    Recebe e devolve o QUADRO (nao uma camada): multiply precisa dos dois lados.
    """
    if progress <= 0:
        return img
    rr = r * ease(min(1.0, progress / 0.7))          # o circulo abre, nao aparece
    base = img.convert("RGB")
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2.5))
    tint = Image.new("RGB", base.size, tuple(int(255 - (255 - v) * forca) for v in color))
    mult = ImageChops.multiply(base, tint)
    out = Image.composite(mult, base, mask).convert("RGBA")
    if borda and progress > 0.55:
        ring = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                                     outline=color + (170,), width=3)
        out.alpha_composite(ring)
    return out


def callout(size, de, para, progress=1.0, width=3, color=None, seed=73):
    """Linha de chamada fina, reta, ligando a lente/regiao a etiqueta. Nao e a seta a
    mao: e a linha tecnica do registro editorial (Porsche bf19/bf22), sem ponta."""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    if progress <= 0:
        return lay
    color = color or INK
    x0, y0 = de; x1, y1 = para
    k = ease(min(1.0, progress))
    xm, ym = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
    dr = ImageDraw.Draw(lay)
    dr.line([(x0, y0), (xm, ym)], fill=color + (235,), width=width)
    if k > 0.02:
        dr.ellipse([x0 - width * 1.4, y0 - width * 1.4, x0 + width * 1.4, y0 + width * 1.4],
                   fill=color + (235,))
    return lay


def scrim_inferior(img, altura=560, forca=0.62, curva=1.7):
    """
    Aprofunda a vinheta na BASE do quadro para o texto de rodape ter onde pousar.

    Nao e gradiente decorativo (proibido pela Style Bible §13): e a mesma vinheta que o
    `finish` ja aplica, so que assimetrica. A diferenca importa — gradiente decorativo e
    uma faixa colorida sobreposta; isto e a propria foto perdendo luz na borda, que e o
    que uma lente faz.

    Existe porque foi MEDIDO: `lib/legibilidade.py` sobre uma legenda ▶ em cima da foto de
    um carro vermelho da contraste externo de 1,02 — o texto creme sobre a carroceria
    vermelha some por completo. Com scrim de 560px/0,62 o mesmo bloco passa dos 4,5.
    """
    im = img.convert("RGB")
    a = np.asarray(im, np.float32)
    h, w = a.shape[:2]
    y = np.arange(h, dtype=np.float32)
    k = np.clip((y - (h - altura)) / max(1.0, altura), 0, 1) ** curva
    a *= (1.0 - forca * k)[:, None, None]
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
    out.putalpha(img.getchannel("A") if img.mode == "RGBA" else 255)
    return out


# ---------------------------------------------------------------- quadro V e H
# O mesmo build_M# serve aos dois quadros quando escreve posicao em FRACAO do quadro.
#   X(0.5), Y(0.44)   -> pixel no quadro atual
#   U                 -> escala de tamanho: 1.0 no vertical (1080 de lado curto), igual no H
#   ORIENT            -> "V" ou "H", para a cena escolher o LAYOUT (nao so escalar):
#                        split vertical = rosto em cima, prova embaixo; no H = rosto de um lado,
#                        prova do outro. Um layout vertical esticado no H nao e composicao.
ORIENT = V.ORIENT
U = min(W, H) / 1080.0


def X(fx):
    return int(round(W * fx))


def Y(fy):
    return int(round(H * fy))


def regioes_split():
    """Retangulos (x0, y0, x1, y1) do rosto e da prova no split, por orientacao."""
    if ORIENT == "H":
        return {"rosto": (0, 0, X(0.46), H), "prova": (X(0.50), Y(0.08), X(0.96), Y(0.92))}
    return {"rosto": (0, 0, W, Y(0.46)), "prova": (X(0.06), Y(0.50), X(0.94), Y(0.86))}

