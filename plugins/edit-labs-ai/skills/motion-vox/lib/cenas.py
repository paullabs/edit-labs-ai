#!/usr/bin/env python3
"""
Peças de cena do kit: âncora por palavra (`tp`), disco amarelo, pouso com sombra, etiqueta, marcador,
troca de insert com flash, cartela de nome, santinho e pessoa recortada. A mecânica da identidade continua
vindo de `kit`/`voxlab`; aqui só se junta.

Regras aplicadas (referências da motion-vox):
- herói já em voo no frame 0 (armadilha 62): toda entrada começa NEGATIVA;
- um dominante por cena; sombra por camada, nunca a mesma (hierarquia §1–2);
- disco amarelo ATRÁS do herói, etiqueta amarela para o nome (Porsche bf10, bf22, bf31);
- troca de insert dentro da mesma cutaway por flash (transicoes.md, `_swap_flash`).
"""
import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kit import *            # noqa: F401,F403
import kit as K
import voxlab as V

ROOT = Path(__file__).resolve().parent
_PAL = json.loads((ROOT / "00_brief" / "transcript_palavras.json").read_text(encoding="utf-8"))


def _n(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def tp(palavra, depois=0.0, fim=False):
    """Tempo (s do clipe) em que `palavra` começa (ou termina, `fim=True`): primeira ocorrência
    depois de `depois`. Âncora por palavra, nunca por segundo digitado à mão."""
    alvo = _n(palavra)
    for w in _PAL:
        if w["t"] >= depois - 0.01 and _n(w["w"]).startswith(alvo):
            return w["e"] if fim else w["t"]
    raise KeyError(f"'{palavra}' depois de {depois}s")


def fr(t, t0):
    """Frame da timeline de 24 fps de uma cena que começa em t0."""
    return (t - t0) * 24.0


# ------------------------------------------------------------------ fundos
_bg = {}


def fundo_escuro(seed=3):
    """Carvão com textura baixa de papel — o chão das fotos (Porsche bf10, bf28)."""
    if seed not in _bg:
        rng = np.random.default_rng(seed)
        n = rng.normal(0, 1, (H // 10, W // 10)).astype(np.float32)
        n = np.asarray(Image.fromarray(np.clip(n * 22 + 128, 0, 255).astype(np.uint8))
                       .resize((W, H), Image.BICUBIC), np.float32) - 128.0
        a = np.zeros((H, W, 4), np.float32)
        a[..., :3] = np.clip(np.array(CHARCOAL, np.float32) + n[..., None] * 0.45, 0, 255)
        a[..., 3] = 255
        _bg[seed] = Image.fromarray(a.astype(np.uint8), "RGBA")
    return _bg[seed].copy()


# ------------------------------------------------------------------ peças
_disc = {}


def disco(c, cx, cy, r, prog, seed=7, cor=None):
    """Círculo amarelo CHEIO atrás do herói, crescendo do centro (Porsche bf22)."""
    if prog <= 0:
        return
    rr = max(3, int(r * V.ease(min(1.0, prog))))
    key = (rr, seed)
    if key not in _disc:
        pad = 14
        s = 2 * rr + 2 * pad
        yy, xx = np.mgrid[0:s, 0:s]
        m = (((xx - rr - pad) ** 2 + (yy - rr - pad) ** 2) <= rr * rr).astype(np.float32)
        m = K.torn(m, 3, 0.16, seed)
        lay = np.zeros((s, s, 4), np.uint8)
        lay[..., :3] = cor or YELLOW
        lay[..., 3] = (m * 232).astype(np.uint8)
        _disc[key] = Image.fromarray(lay, "RGBA")
    d = _disc[key]
    c.alpha_composite(d, (int(cx - d.width / 2), int(cy - d.height / 2)))


def pousa(c, layer, cx, cy, prog, sombra=None, queda=240, kind="obj", boil_seed=None):
    """Herói pousando de cima, com overshoot pequeno; a sombra cresce junto do pouso."""
    if prog <= 0 or layer is None:
        return None
    sombra = sombra or K.SH_CARD
    pg = min(1.0, prog)
    y = cy - (1 - pg) * queda + math.sin(pg * math.pi) * 10
    lay = layer if pg >= 1 else K.fade(layer, min(1.0, pg * 1.7))
    pos = V.centered(lay, cx, y)
    sh = dict(dy=int(sombra["dy"] * (0.4 + 0.6 * pg)), blur=sombra["blur"],
              opacity=sombra["opacity"] * pg)
    V.place(c, lay, pos, shadow=sh, kind=kind, boil_seed=boil_seed)
    return pos


def etiqueta(c, texto, cx, cy, prog, tam=66, fonte=None, rot=-1.5, seed=13, sombra=False):
    """Etiqueta de marca-texto amarelo (kit.yellow_label). Estado final pede progress=1 (arm. 54)."""
    if prog <= 0:
        return
    c.alpha_composite(K.yellow_label(c.size, texto, fontpath=fonte or F_COND, fontsize=tam,
                                     xy=(cx, cy), progress=min(1.0, prog), rotation=rot,
                                     seed=seed, sombra=sombra))


def marcador(c, texto, cx, cy, prog, tam=96, seed=21, cor=None):
    """Escrita a marcador, revelada como traço (write), nunca caractere a caractere."""
    if prog <= 0:
        return
    c.alpha_composite(V.text_layer(c.size, texto, F_MARKER, tam, (cx, cy), color=cor or INK,
                                   anchor="mm", stroke_w=2, tracking=3, hand=True, seed=seed,
                                   mode="write", optical=True, progress=min(1.0, prog)))


def cartao_logo(nome, largura, margem=0.10, rot=0.0):
    """Logo impresso num cartão branco — a marca vira OBJETO do mundo da mesa (não selo)."""
    lg = K.asset(nome, largura)
    pad = int(largura * margem)
    card = Image.new("RGBA", (lg.width + 2 * pad, lg.height + 2 * pad), PAPER_LIGHT + (255,))
    card.alpha_composite(lg, (pad, pad))
    return card.rotate(rot, resample=Image.BICUBIC, expand=True) if rot else card


# ------------------------------------------------------------------ troca de insert
def flash(img, sl):
    """_swap_flash: desfoca + estoura em branco; o corte fica escondido no pico."""
    if sl <= 0:
        return img
    im = img.convert("RGB").filter(ImageFilter.GaussianBlur(26 * sl))
    branco = Image.new("RGB", im.size, (250, 249, 246))
    return Image.blend(im, branco, min(0.92, sl * 0.92)).convert("RGBA")


def sequencia(frame, itens, janela=4.0):
    """Insert-burst dentro de UMA cutaway: itens = [(f_inicio, fn(frame_local))]. O flash sobe
    `janela` frames antes da troca e desce `janela` frames depois."""
    itens = sorted(itens, key=lambda x: x[0])
    k = 0
    for i, (f0, _) in enumerate(itens):
        if frame >= f0:
            k = i
    f0, fn = itens[k]
    img = fn(frame - f0)
    sl = 0.0
    if k > 0 and frame - f0 < janela:
        sl = max(sl, 1 - (frame - f0) / janela)
    if k + 1 < len(itens) and itens[k + 1][0] - frame < janela:
        sl = max(sl, 1 - (itens[k + 1][0] - frame) / janela)
    return flash(img, sl)


# ------------------------------------------------------------------ cartela de identificação
def ident(frame, nome, sub, total24):
    """Overlay SEM fundo sobre o rosto (a abertura nunca é cutaway): etiqueta amarela com o nome e
    rodapé em serifa itálica, na faixa livre abaixo da legenda (y 1540–1660). Sai em fade."""
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    etiqueta(c, nome, W // 2, 1565, K.p(frame, -3, 11), tam=60, sombra=True, seed=17)
    ps = K.p(frame, 6, 16)
    if ps > 0:
        c.alpha_composite(K.footer_caption(c.size, sub, progress=ps, y=1640, fontsize=40))
    sai = K.p(frame, total24 - 8, total24)
    return K.fade(c, 1 - sai) if sai > 0 else c


# ------------------------------------------------------------------ gente de verdade
# Personagem da história é PESSOA, não palavra nem boneco. Pessoa anônima = pessoa fictícia gerada;
# pessoa real nomeada = só foto real licenciada (rosto real nunca é gerado — regra da skill).
_sant = {}


def santinho(nome_raw, cargo, largura, rot=0.0, cor=None, foco_y=0.30, seed=5):
    """Santinho de campanha: a foto (07_assets/raw/<nome_raw>.png, retrato gerado de pessoa FICTÍCIA)
    impressa num cartão com a faixa do cargo embaixo. Texto em PIL (nunca do gerador)."""
    key = (nome_raw, cargo, int(largura), round(rot, 2), cor, seed)
    if key in _sant:
        return _sant[key]
    w = int(largura)
    m = int(w * 0.055)
    pw = w - 2 * m
    ph = int(pw * 1.18)
    faixa = int(w * 0.30)
    h = m + ph + faixa
    foto = Image.open(ROOT / "07_assets" / "raw" / f"{nome_raw}.png").convert("RGB")
    fw, fh = foto.size
    cw = int(min(fw, fh * pw / ph))
    ch = int(cw * ph / pw)
    x0 = (fw - cw) // 2
    y0 = int(max(0, min(fh - ch, fh * foco_y - ch * 0.30)))
    foto = foto.crop((x0, y0, x0 + cw, y0 + ch)).resize((pw, ph), Image.LANCZOS)
    # foto contemporânea impressa: dessatura leve (0,86, fotos-reais.md) + grão; a retícula do kit é
    # monocromática e apaga a cor da faixa, que é o que faz ler o cargo
    foto = Image.fromarray(_dessatura(np.asarray(foto, np.float32), 0.86, seed)).convert("RGBA")
    card = Image.new("RGBA", (w, h), PAPER_LIGHT + (255,))
    card.alpha_composite(foto, (m, m))
    d = ImageDraw.Draw(card)
    d.rectangle([0, m + ph + int(w * 0.03), w, h], fill=(cor or INK) + (255,))
    f = V.font(F_COND, int(w * 0.135))
    tw = d.textlength(cargo, font=f)
    while tw > w * 0.88:
        f = V.font(F_COND, int(f.size * 0.92)); tw = d.textlength(cargo, font=f)
    ty = m + ph + int(w * 0.03) + (faixa - int(w * 0.03)) / 2
    d.text((w / 2, ty), cargo, font=f, fill=(250, 248, 242, 255), anchor="mm")
    if rot:
        card = card.rotate(rot, resample=Image.BICUBIC, expand=True)
    _sant[key] = card
    return card


def _dessatura(rgb, fator=0.86, seed=5):
    lum = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    out = lum + (rgb - lum) * fator
    rng = np.random.default_rng(seed)
    out += cv2_blur(rng.normal(0, 3.0, rgb.shape[:2]).astype(np.float32))[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def cv2_blur(a, s=1.2):
    import cv2
    return cv2.GaussianBlur(a, (0, 0), s)


_rec = {}


def recorte_pessoa(nome, largura, seed=3, margin=15, jornal=False):
    """Pessoa recortada com margem de papel rasgada (o mesmo mundo de papel da mesa). Em COR, com a
    dessaturação de foto contemporânea; `jornal=True` usa a trama monocromática do kit (recorte de jornal)."""
    if jornal:
        return K.clip_asset(nome, largura, seed=seed, margin=margin, mix=0.45)
    key = (nome, int(largura), seed, margin)
    if key not in _rec:
        im = K.asset(nome, largura)
        pad = int(margin * 1.9) + 10
        src = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
        src.alpha_composite(im, (pad, pad))
        a = np.asarray(src.getchannel("A"), np.float32) / 255.0
        cor = _dessatura(np.asarray(src.convert("RGB"), np.float32), 0.86, seed).astype(np.float32)
        papel = K.torn(a, margin, 0.34, seed)
        rng = np.random.default_rng(seed + 77)
        grao = cv2_blur(rng.normal(0, 3.4, a.shape).astype(np.float32), 1.6)
        out = np.zeros((src.height, src.width, 4), np.float32)
        for c in range(3):
            out[..., c] = (PAPER_LIGHT[c] + grao) * (1 - a) + cor[..., c] * a
        out[..., 3] = np.maximum(papel, a) * 255.0
        o = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
        _rec[key] = o.crop(o.getbbox())
    return _rec[key]
