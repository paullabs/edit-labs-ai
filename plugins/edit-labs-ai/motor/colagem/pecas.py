"""Peças da colagem de papel antigo, comuns a todos os vídeos de colagem.

Cada função devolve uma PIL RGBA pronta para virar Camada no motor:
    cartao(foto)          foto real impressa num cartão de borda clara, com fita
    fita(...)             tira de fita crepe (procedural; ou a sua imagem em $EDITLABS_DATA/colagem/kit/fita.png)
    recorte(png_alfa)     pessoa/objeto recortado (recorte.swift), com a borda branca da tesoura
    etiqueta([linhas])    tira de papel com nome e data
    carimbo("TEXTO")      carimbo vermelho com falhas de tinta
    legenda("a *b*")      frase numa tira de papel (quebra com \\n, *trecho* em vermelho)
    papel_mundo(w, h)     o papel creme do mundo (fundo)
Cores: TINTA (texto), CREME (papel de etiqueta), VERMELHO (o único acento)."""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

import recursos as R

AQUI = Path(__file__).resolve().parent
KIT = R.KIT
FONTES = R.FONTES
FITA_USUARIO = R.DADOS / "kit" / "fita.png"          # opcional: uma imagem sua de fita (4 tiras empilhadas)
TINTA = (43, 35, 28)
CREME = (241, 232, 210)
VERMELHO = (172, 46, 38)
PAPEL = (233, 221, 192)              # creme do mundo


def fonte(nome, corpo):
    return R.fonte(nome, corpo)


def rasgar(im, amp=6, passo=14, semente=1):
    """borda de papel rasgado: alfa recortado por um contorno irregular"""
    w, h = im.size
    rng = np.random.default_rng(semente)
    pts = [(min(x, w), rng.uniform(0, amp)) for x in range(0, w + passo, passo)]
    pts += [(w - rng.uniform(0, amp), min(y, h)) for y in range(0, h + passo, passo)]
    pts += [(max(x, 0), h - rng.uniform(0, amp)) for x in range(w, -passo, -passo)]
    pts += [(rng.uniform(0, amp), max(y, 0)) for y in range(h, -passo, -passo)]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(0.8))
    out = im.copy()
    out.putalpha(Image.fromarray(np.minimum(np.asarray(im.getchannel("A")), np.asarray(m))))
    return out


def textura_papel(w, h, tom=CREME, semente=3, forca=0.9):
    """papel de etiqueta/cartão: o tom pedido com o grão da página antiga (blocos espelhados, sem emenda)"""
    pg = Image.open(KIT / "papel_antigo.jpg").convert("L")
    rng = np.random.default_rng(semente)
    cw, ch = min(w, pg.width - 800), min(h, pg.height - 800)
    x0 = int(rng.integers(400, pg.width - 400 - cw + 1))
    y0 = int(rng.integers(400, pg.height - 400 - ch + 1))
    bloco = np.asarray(pg.crop((x0, y0, x0 + cw, y0 + ch)), dtype=np.float32)
    reps_y, reps_x = -(-h // ch), -(-w // cw)
    linhas = [np.concatenate([bloco if (i + j) % 2 == 0 else bloco[:, ::-1] for j in range(reps_x)], axis=1)
              for i in range(reps_y)]
    g = np.concatenate([l if i % 2 == 0 else l[::-1] for i, l in enumerate(linhas)], axis=0)[:h, :w]
    g = (g - g.mean(dtype=np.float64)) / 255.0
    a = np.clip(np.array(tom, dtype=np.float32)[None, None, :] / 255.0 + g[..., None] * forca, 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8)).convert("RGBA")


def fita_procedural(larg, alt, semente=0):
    """tira de fita crepe feita em código: bege translúcido, pontas serrilhadas de rasgo, fibras no sentido do
    comprimento e um leve brilho. Não depende de nenhuma imagem."""
    rng = np.random.default_rng(1000 + semente)
    esc = 3                                              # desenha 3× maior e reduz (borda sem serrilhado)
    w, h = larg * esc, alt * esc
    base = np.array([226, 212, 176], np.float32) + rng.uniform(-6, 6, 3)
    fibra = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), sigmaX=w * 0.04, sigmaY=1.2)
    fibra = fibra / (np.abs(fibra).max() + 1e-6)
    grao = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 1.4)
    grao = grao / (np.abs(grao).max() + 1e-6)
    yy = np.linspace(-1, 1, h)[:, None]
    brilho = np.exp(-((yy + 0.35) / 0.25) ** 2) * 10           # faixa de luz perto do topo
    rgb = base[None, None, :] + (fibra * 9 + grao * 6 + brilho)[..., None]
    m = Image.new("L", (w, h), 0)
    pts = []
    for y in range(0, h + 1, max(2, h // 9)):            # ponta esquerda: rasgo em zigue-zague
        pts.append((rng.uniform(0, 0.09) * w, min(y, h)))
    for y in range(h, -1, -max(2, h // 9)):              # ponta direita
        pts.append((w - rng.uniform(0, 0.09) * w, max(y, 0)))
    ImageDraw.Draw(m).polygon(pts, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(esc * 0.6)), np.float32) / 255
    alfa = m * (0.78 + 0.08 * grao)
    out = np.dstack([np.clip(rgb, 0, 255), np.clip(alfa * 255, 0, 255)]).astype(np.uint8)
    return Image.fromarray(out, "RGBA").resize((larg, alt), Image.LANCZOS)


def fita(larg=150, alt=46, ang=0, semente=0):
    if FITA_USUARIO.exists():                           # imagem do usuário: 4 tiras empilhadas na vertical
        t = Image.open(FITA_USUARIO).convert("RGBA")
        k = semente % 4
        tira = t.crop((0, k * t.height // 4, t.width, (k + 1) * t.height // 4))
        tira = tira.crop(tira.getbbox()).resize((larg, alt), Image.LANCZOS)
    else:
        tira = fita_procedural(larg, alt, semente)
    a = np.asarray(tira).astype(np.float32)
    a[..., 3] *= 0.82
    return Image.fromarray(a.astype(np.uint8)).rotate(ang, expand=True, resample=Image.BICUBIC)


def envelhecer(rgb, sepia=False, forca=0.25):
    """foto real 'impressa': menos saturação e um pouco de sépia (sepia=True: sépia total, para foto P&B)"""
    a = np.asarray(rgb.convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    if sepia:
        esc, cla = np.array([0.17, 0.13, 0.10]), np.array([0.92, 0.86, 0.72])
        a = esc + lum[..., None] ** 1.05 * (cla - esc)
    else:
        sep = np.array([0.18, 0.14, 0.11]) + lum[..., None] * np.array([0.74, 0.70, 0.60])
        a = (1 - forca) * (lum[..., None] + 0.7 * (a - lum[..., None])) + forca * sep
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def cartao(foto, larg, alt=None, foco=(0.5, 0.5), borda=22, base=58, sepia=False, semente=1,
           fitas=((0.5, -12),), envelhece=True):
    """foto impressa em cartão de borda clara com fita; alt=None mantém a proporção da foto"""
    im = foto.convert("RGB")
    w0, h0 = im.size
    alt = alt or round(larg * h0 / w0)
    r = larg / alt
    if w0 / h0 > r:
        nw = int(h0 * r); x0 = int(min(max(foco[0] * w0 - nw / 2, 0), w0 - nw)); im = im.crop((x0, 0, x0 + nw, h0))
    else:
        nh = int(w0 / r); y0 = int(min(max(foco[1] * h0 - nh / 2, 0), h0 - nh)); im = im.crop((0, y0, w0, y0 + nh))
    im = im.resize((larg, alt), Image.LANCZOS)
    if envelhece:
        im = envelhecer(im, sepia)
    c = textura_papel(larg + 2 * borda, alt + borda + base, (238, 231, 214), semente)
    c.paste(im, (borda, borda))
    c = rasgar(c, amp=3, passo=22, semente=semente)
    pad = 40
    out = Image.new("RGBA", (c.width + 2 * pad, c.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(c, (pad, pad))
    for k, (fx, ang) in enumerate(fitas):
        t = fita(170, 52, ang, semente + k)
        out.alpha_composite(t, (int(pad + fx * c.width - t.width / 2), int(pad - t.height / 2 + 6)))
    return out


def recorte(png, alt=None, larg=None, borda=12, envelhece=True, sepia=False, semente=9, corte_base=None, mapa=False):
    """pessoa/objeto já recortado (PNG com alfa) com a borda branca da tesoura.
    corte_base: fração da altura onde cortar embaixo (rasgo ondulado), para tirar pedestal ou moldura.
    mapa=True devolve (imagem, f) com f(x, y) = onde um ponto da imagem de entrada cai na peça final"""
    im = Image.open(png).convert("RGBA") if not isinstance(png, Image.Image) else png.convert("RGBA")
    a = np.asarray(im).copy()
    al = a[..., 3].copy()
    if corte_base:
        h, w = al.shape
        rng = np.random.default_rng(semente)
        linha = (h * corte_base + 6 * np.sin(np.arange(w) / 37.0) + np.cumsum(rng.normal(0, 0.9, w))).astype(int)
        al[np.arange(h)[:, None] >= linha[None, :]] = 0
    m = (al > 127).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(m)
    if n > 2:                                           # só a maior peça (sem ilhas soltas)
        al = np.where(lb == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]), al, 0).astype(np.uint8)
    a[..., 3] = al
    im = Image.fromarray(a)
    caixa = im.getbbox()
    im = im.crop(caixa)
    if envelhece:
        rgb = envelhecer(im.convert("RGB"), sepia)
        rgb.putalpha(im.getchannel("A"))
        im = rgb
    al = np.asarray(im.getchannel("A"))
    pad = borda + 4
    al2 = np.pad(al, pad)
    dil = cv2.dilate(al2, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * borda + 1, 2 * borda + 1)))
    base = textura_papel(al2.shape[1], al2.shape[0], (244, 238, 222), semente)
    base.putalpha(Image.fromarray(cv2.GaussianBlur(dil, (0, 0), 0.8)))
    base.alpha_composite(im, (pad, pad))
    f = 1.0
    if alt or larg:
        f = (alt / base.height) if alt else (larg / base.width)
        base = base.resize((round(base.width * f), round(base.height * f)), Image.LANCZOS)
    if mapa:
        return base, (lambda x, y: ((x - caixa[0] + pad) * f, (y - caixa[1] + pad) * f))
    return base


def etiqueta(linhas, corpo=(44, 30), fontes=("ArchivoBlack-Regular.ttf", "IBMPlexMono-Medium.ttf"), cor=TINTA,
             pad=(26, 16), semente=4, fundo=CREME):
    fs = [fonte(fn, c) for fn, c in zip(fontes, corpo)]
    larg = max(int(fs[i].getlength(t)) for i, t in enumerate(linhas)) + 2 * pad[0]
    alts = [fs[i].getbbox(t)[3] + 8 for i, t in enumerate(linhas)]
    im = textura_papel(larg, sum(alts) + 2 * pad[1], fundo, semente)
    d = ImageDraw.Draw(im)
    y = pad[1]
    for i, t in enumerate(linhas):
        d.text((pad[0], y), t, font=fs[i], fill=cor + (255,))
        y += alts[i]
    out = rasgar(im, amp=4, passo=12, semente=semente)
    out.info["texto_px"] = corpo[0]
    out.info["texto_min"] = 50 if len(linhas) == 1 else 54      # com 2ª linha (corpo menor), a 1ª fica maior
    return out


def carimbo(texto, corpo=128, semente=7, cor=VERMELHO):
    fo = fonte("ArchivoBlack-Regular.ttf", corpo)
    l, t, r, b = fo.getbbox(texto)
    w, h = r - l + 70, b - t + 60
    im = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius=14, outline=cor + (255,), width=9)
    d.text((20 + 35 - l, 20 + 30 - t), texto, font=fo, fill=cor + (255,))
    a = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(semente)
    ruido = cv2.GaussianBlur(rng.random((im.height, im.width)).astype(np.float32), (0, 0), 2.2)
    ruido = (ruido - ruido.min()) / (ruido.max() - ruido.min())
    a[..., 3] *= np.clip((ruido - 0.18) * 2.4, 0, 1) * 0.92
    out = Image.fromarray(a.astype(np.uint8))
    out.info["texto_px"] = corpo
    out.info["texto_min"] = 58
    return out


def _quebrar(texto, fo, largura):
    """quebra gulosa por palavras, mantendo os *trechos vermelhos* (os asteriscos não contam na largura)"""
    palavras = [w for w in texto.replace("\n", " ").split(" ") if w]    # " " e não split(): o espaço fixo (\xa0) segura "1,57 m"
    linhas, atual = [], ""
    for w in palavras:
        prova = (atual + " " + w).strip()
        if fo.getlength(prova.replace("*", "")) <= largura or not atual:
            atual = prova
        else:
            linhas.append(atual)
            atual = w
    linhas.append(atual)
    out, aberto = [], False                                  # fecha/reabre o vermelho em cada quebra
    for l in linhas:
        l2 = ("*" if aberto else "") + l
        if l2.count("*") % 2:
            l2 += "*"
            aberto = True
        else:
            aberto = False
        out.append(l2.replace("**", ""))
    return out


def legenda(texto, semente=60, corpo=64, largura=880):
    """tira de papel com a frase (v4: corpo 64, legível para todo mundo); quebra com \\n e *trecho* em vermelho;
    se uma linha passar da largura, a frase é requebrada sozinha"""
    fo = fonte("Inter-800.ttf", corpo)
    linhas = texto.split("\n")
    if max(fo.getlength(l.replace("*", "")) for l in linhas) > largura:
        linhas = _quebrar(texto, fo, largura)
    passo = round(corpo * 1.22)
    larg = max(fo.getlength(l.replace("*", "")) for l in linhas) + 76
    im = textura_papel(int(larg), int(passo * len(linhas) + 44), (246, 240, 224), semente)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(linhas):
        x = (im.width - fo.getlength(l.replace("*", ""))) / 2
        for k, trecho in enumerate(l.split("*")):
            d.text((x, 22 + i * passo), trecho, font=fo, fill=(VERMELHO if k % 2 else (30, 25, 20)) + (255,))
            x += fo.getlength(trecho)
    im = rasgar(im, amp=5, passo=16, semente=semente)
    pad = 30
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(im, (pad, pad))
    out.alpha_composite(fita(130, 42, -8, semente), (pad - 30, pad - 18))
    return out


def papel_mundo(w, h, tom=PAPEL, textura=0.85, manchas=0.45):
    """o papel creme do mundo: a página antiga repetida em espelho, com o tom puxado para o creme"""
    pg = Image.open(KIT / "papel_antigo.jpg").convert("RGB")
    c = pg.crop((330, 330, pg.width - 330, pg.height - 330))
    c = c.resize((w, round(c.height * w / c.width)), Image.LANCZOS)
    out = Image.new("RGB", (w, h))
    y, k = 0, 0
    while y < h:
        out.paste(c if k % 2 == 0 else c.transpose(Image.FLIP_TOP_BOTTOM), (0, y))
        y += c.height; k += 1
    a = np.asarray(out, dtype=np.float32) / 255
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    media, lm = a.reshape(-1, 3).mean(0, dtype=np.float64), lum.mean(dtype=np.float64)   # float64: em float32 a soma deriva
    alvo = np.array(tom, dtype=np.float32) / 255
    a = alvo + (lum - lm)[..., None] * textura + ((a - lum[..., None]) - (media - lm)) * manchas
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def folha(pecas, saida, larg=1400, fundo=(60, 90, 140)):
    """folha de conferência: as peças lado a lado sobre azul (para ver recorte e borda)"""
    x = y = 20
    linha = 0
    ims = []
    for nome, im in pecas:
        im = im.copy()
        im.thumbnail((420, 420))
        if x + im.width > larg - 20:
            x, y, linha = 20, y + linha + 40, 0
        ims.append((nome, im, x, y))
        x += im.width + 20
        linha = max(linha, im.height)
    f = Image.new("RGB", (larg, y + linha + 40), fundo)
    d = ImageDraw.Draw(f)
    for nome, im, x, y in ims:
        f.paste(im, (x, y + 18), im)
        d.text((x, y), nome, fill=(255, 255, 0))
    f.save(saida, quality=88)



def grade(w, h, passo=70, cor=TINTA, op=0.26, losango=True, semente=3):
    """grade fina (em losango, como nos esquemas da Vox) que some nas bordas: apoio de escala atrás de um objeto"""
    lado = int(math.hypot(w, h)) + 4 * passo
    im = Image.new("L", (lado, lado), 0)
    d = ImageDraw.Draw(im)
    for v in range(0, lado + 1, passo):
        d.line([(v, 0), (v, lado)], fill=255, width=2)
        d.line([(0, v), (lado, v)], fill=255, width=2)
    if losango:
        im = im.rotate(45, resample=Image.BICUBIC)
    im = im.crop(((lado - w) // 2, (lado - h) // 2, (lado - w) // 2 + w, (lado - h) // 2 + h))
    gx, gy = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    fade = np.clip(1.25 - np.maximum(np.abs(gx), np.abs(gy)) ** 3 * 1.25, 0, 1) if not losango else \
        np.clip(1.15 - (np.abs(gx) + np.abs(gy)) ** 2 * 1.0, 0, 1)
    a = (np.asarray(im, dtype=np.float32) / 255 * fade * op * 255).astype(np.uint8)
    out = Image.new("RGBA", (w, h), cor + (0,))
    out.putalpha(Image.fromarray(a))
    return out
