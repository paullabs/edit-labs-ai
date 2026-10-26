"""
Família A' — a galeria documental (moldura dourada na parede, luz de janela, jornais na mesa), medida quadro a
quadro na abertura (0 a 11,8 s) de uma referência de terceiros. Referência estudada, sem nenhuma mídia no plugin:
o vídeo "Netflix In 2022", do canal "Viral Instagram Growth Tips" (crédito de referência apenas).

Quatro tipos de plano, cada um com a sua medida:

  moldura_entra     parede com luz de janela e moldura dourada; a câmera entra na moldura (largura do ouro
                    297 -> 716 px em 720 até 1,7 s, lenta até 1,2 s e rápida depois) e a abertura se estica
                    até virar a tela (2,3 s). A foto passa de P&B a cor no empurrão rápido. Frases trocam
                    sobre o peito, com desfoque de entrada.
  foto_recorte      foto P&B com o sujeito em cor (máscara do Vision, ferramentas/recorte.swift); empurra
                    1,0 -> 1,19 em 25 quadros e para. O bloco de texto monta palavra a palavra ATRÁS do
                    sujeito. Na virada: o quadro desfoca, escurece a 45% em 0,45 s, a frase nova entra à
                    direita e o sublinhado amarelo cresce do MEIO para as pontas em 15 quadros.
  etiqueta_rasgada  foto P&B que afasta 5% (ease-out); etiqueta amarela rasgada que nasce dobrada em Z e
                    abre da esquerda para a direita em 3 degraus de 2 quadros (60, 69, 87, 100% da largura).
  jornais_mesa      mesa de madeira vista de cima (procedural) e jornais desenhados pelo motor (nomes
                    inventados, sem logo). Os jornais chegam a 1,7x com borrão e pousam em 8 quadros; depois
                    a câmera afasta até 0,91. Laço branco feito à mão na manchete e foco que respira.

Peças comuns: frase com desfoque de entrada (90% de nitidez em 6-8 quadros), sublinhado à mão, etiqueta
rasgada. Pouso desfocado depois do corte, cadência de 15 qps e linhas verticais de CRT ficam em projeto.py,
familia_a/tempo.py e familia_a/c4_filtro.py ("cadencia": 15, "acabamento": "galeria", "pouso": {...}).
"""
import math

import numpy as np
import cv2
from PIL import Image

from familia_a import W, H
from familia_a import c2_letras as le, c3_style as st, c4_filtro as fi, c5_movimentos as mv
from familia_a.compor import sobre
from planos import u, zoom_em, _parede, _moldura

BRANCO_NF = (234.0, 232.0, 228.0)
TINTA_LEGENDA = (34.0, 30.0, 30.0)
AMARELO_SUB = (234.0, 222.0, 54.0)       # medido 187,180,34 com borda misturada no fundo escurecido
AMARELO_TAG = (214.0, 166.0, 26.0)       # medido 212,164,28
SERIFA_RETA = str(le.RAIZ / "fontes" / "InstrumentSerif-Regular.ttf")


# ------------------------------------------------------------------------------------------- utilidades
def _tingir_arr(img, a, x, y, cor):
    h, w = a.shape
    x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y)
    xb, yb = min(img.shape[1], x + w), min(img.shape[0], y + h)
    if xa >= xb or ya >= yb:
        return
    s = a[ya - y:yb - y, xa - x:xb - x, None]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - s) + np.array(cor, np.float32) * s


def frase(img, texto, ponto, corpo, q, dur=7, sigma0=6.0, alfa0=0.45, cor=BRANCO_NF, fonte=None,
          alinha="centro", alfa=1.0, sombra=0.0):
    """Frase em serifa itálica que entra desfocada e transparente e assenta em `dur` quadros.
    Medido: "one million" chega a 90% da nitidez em 6 quadros; com a câmera rápida, até 22.
    `ponto` é o centro da tinta (alinha="centro") ou a ponta esquerda na altura do centro ("esquerda")."""
    if q < 0 or alfa <= 0:
        return None
    m, _ = le.mascara(texto, fonte or le.SERIFA, corpo)
    a = np.asarray(m, np.float32) / 255.0
    v = min(1.0, q / max(1.0, dur))
    sig = sigma0 * (1 - v) ** 1.5
    pad = int(3 * sig + 3)
    a = np.pad(a, pad)
    if sig > 0.3:
        a = cv2.GaussianBlur(a, (0, 0), sig)
    k = (alfa0 + (1 - alfa0) * v ** 0.8) * alfa
    h, w = a.shape
    x = ponto[0] - w / 2 if alinha == "centro" else ponto[0] - pad
    y = ponto[1] - h / 2
    if sombra:
        s = cv2.GaussianBlur(a, (0, 0), 9.0)
        _tingir_arr(img, np.clip(s * 1.6, 0, 1) * sombra * k, x, y, (0.0, 0.0, 0.0))
    _tingir_arr(img, a * k, x, y, cor)
    return (x + pad, y + pad, x + w - pad, y + h - pad)


def desfoque_pulso(img, q, q0, dur=10, sigma=7.0):
    """Foco que respira: sobe a `sigma` e volta a 0 (a virada do "of the end.", o foco dos jornais)."""
    if q0 is None or not (q0 <= q < q0 + dur):
        return img
    v = (q - q0) / dur
    return fi.desfocar(img, sigma * math.sin(math.pi * min(1.0, v * 1.25)) ** 1.2 if v < 0.8 else sigma * (1 - v) * 1.5)


def zoom_borrao(img, z, ancora, forca, amostras=8):
    """Borrão de zoom (o empurrão rápido para dentro da moldura): média de cópias de 1 a 1+forca."""
    if forca < 0.004:
        return img
    acc = img.copy()
    for k in range(1, amostras):
        acc += zoom_em(img, 1 + forca * k / (amostras - 1), ancora)
    return acc / amostras


def _cobrir(a, larg, alt, ponto, zoom=1.0):
    """Recorta da foto a janela com o aspecto (larg x alt) em torno de `ponto` e redimensiona (cobre)."""
    h0, w0 = a.shape[:2]
    s = max(larg / w0, alt / h0) * zoom
    cw, ch = larg / s, alt / s
    cx = min(max(ponto[0], cw / 2), w0 - cw / 2)
    cy = min(max(ponto[1], ch / 2), h0 - ch / 2)
    M = np.float32([[s, 0, larg / 2 - s * cx], [0, s, alt / 2 - s * cy]])
    return cv2.warpAffine(a[..., :3], M, (int(round(larg)), int(round(alt))), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT)


def _pb(rgb):
    l = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return np.repeat(l[..., None], 3, axis=2)


def _ruido(h, w, escala, semente):
    rng = np.random.default_rng(semente)
    m = rng.normal(0, 1, (max(2, h // escala + 3), max(2, w // escala + 3))).astype(np.float32)
    return cv2.resize(m, (w + 2 * escala, h + 2 * escala), interpolation=cv2.INTER_CUBIC)[escala:escala + h, escala:escala + w]


# ------------------------------------------------------------------------------------------- 1. moldura_entra
# Largura do ouro (relativa ao quadro 0), medida a cada 3 quadros até a moldura tocar as bordas (1,7 s).
MOLDURA_Z = {0: 1.0, 3: 1.077, 6: 1.104, 9: 1.175, 12: 1.205, 15: 1.256, 18: 1.273, 21: 1.313, 24: 1.327, 27: 1.354,
             30: 1.367, 33: 1.414, 36: 1.444, 39: 1.562, 42: 1.663, 45: 2.007, 48: 2.226, 51: 2.41}


def _interp(tab, q):
    ks = sorted(tab)
    return float(np.interp(q, ks, [tab[k] for k in ks]))


def _moldura_fina(p):
    """Moldura dourada fina (a da galeria: borda ~7% da largura), feita em código: canto em meia-esquadria,
    perfil de friso (escuro, brilho, meio-tom, filete claro, lábio escuro) e luz de cima à esquerda.
    Devolve o mesmo que planos._moldura: (rgba, x0, y0, furo)."""
    ow, oh = (int(round(v)) for v in p.get("tamanho_ouro", (445.0, 549.0)))
    b = max(8, int(round(ow * p.get("borda", 0.075))))
    yy, xx = np.mgrid[:oh, :ow].astype(np.float32)
    dist = np.minimum.reduce([xx, yy, ow - 1 - xx, oh - 1 - yy])
    d = np.clip(dist / b, 0, 1.2)
    perfil = np.interp(d, [0.0, 0.06, 0.18, 0.34, 0.50, 0.66, 0.80, 0.90, 0.96, 1.0],
                          [0.30, 0.55, 1.15, 0.80, 0.95, 0.62, 0.85, 1.10, 0.40, 0.30])
    lado = np.argmin(np.stack([xx, yy, ow - 1 - xx, oh - 1 - yy]), 0)        # 0 esq, 1 topo, 2 dir, 3 base
    luz = np.choose(lado, [1.08, 1.15, 0.88, 0.80])
    orn = 1 + 0.10 * np.sin(xx * 0.9 + yy * 0.9) * np.sin(xx * 0.45 - yy * 0.45) * ((d > 0.36) & (d < 0.64))
    gasto = 1 + 0.07 * _ruido(oh, ow, 5, 21) + 0.04 * _ruido(oh, ow, 1, 22)
    ouro = np.array([178.0, 134.0, 58.0])
    rgb = ouro[None, None, :] * (perfil * luz * orn * gasto)[..., None]
    rgb[..., 2] *= 0.92
    a = (dist < b).astype(np.float32) * 255.0
    m = np.dstack([np.clip(rgb, 0, 255), a])
    cx, cy = p.get("centro_moldura", (537.0, 954.0))
    return m, cx - ow / 2, cy - oh / 2, np.array([b, b, ow - b, oh - b], np.float32)


def _parede_galeria(ctx, p):
    """Parede cinza com faixas de luz de janela em diagonal (mais fortes que a parede da galeria)."""
    def _f():
        img = _parede(ctx)
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        ang = math.radians(p.get("angulo_luz", -22.0))
        u_ = xx * math.cos(ang) + yy * math.sin(ang)
        luz = np.zeros((H, W), np.float32)
        for c, w, a in ((-80, 120, 0.9), (330, 90, 0.7), (640, 150, 0.8), (1010, 110, 0.6), (1380, 140, 0.5)):
            luz += a * np.exp(-(((u_ - c) / w) ** 2))
        img = img * (0.86 + 0.20 * luz[..., None] * p.get("forca_luz", 1.0))
        return img * (1 - 0.10 * (1 - yy / H))[..., None]
    return ctx.cache("parede_nf", _f).copy()


def moldura_entra(n, p, ctx):
    q = n - p["inicio"]
    mold, mx0, my0, furo = ctx.cache("mold", lambda: _moldura_fina(p) if p.get("moldura", "fina") == "fina" else _moldura(p))
    mh, mw = mold.shape[:2]
    fx0, fy0, fx1, fy1 = furo
    anc = (mx0 + mw / 2, my0 + mh / 2)

    def _parede_legenda():
        img = _parede_galeria(ctx, p)
        for lin in p.get("legenda", []):            # a etiqueta de museu sob a moldura
            le.escrever(img, lin["texto"], centro=(anc[0], my0 + mh + lin["dy"]), fonte=le.SERIFA, corpo=lin["corpo"],
                        cor=TINTA_LEGENDA, contorno=0.4)
        return img
    base = ctx.cache("parede_legenda", _parede_legenda)
    Q2, Q3 = p.get("q_borda", 51), p.get("q_tela", 69)
    z = _interp(MOLDURA_Z, min(q, Q2)) * (1.0 + 0.10 * u(q, Q2, Q3) ** 2)
    img = zoom_em(base, z, anc)
    # furo na tela: zoom uniforme até a borda; depois a abertura estica até virar a tela (ease in-out)
    def furo_z(zz):
        return [anc[0] + (mx0 + fx0 - anc[0]) * zz, anc[1] + (my0 + fy0 - anc[1]) * zz,
                anc[0] + (mx0 + fx1 - anc[0]) * zz, anc[1] + (my0 + fy1 - anc[1]) * zz]
    f2 = furo_z(_interp(MOLDURA_Z, Q2))
    if q <= Q2:
        fr = furo_z(z)
    else:                                            # medido: a largura enche em ~7 quadros, a altura até ~q69
        vx = mv.suavizar_curva(u(q, Q2, Q2 + p.get("q_largura", 7)), "s", 1.5)
        vy = mv.suavizar_curva(u(q, Q2, Q3), "s", 1.5)
        alvo = [-0.035 * W, -0.025 * H, 1.035 * W, 1.025 * H]
        fr = [f2[0] + (alvo[0] - f2[0]) * vx, f2[1] + (alvo[1] - f2[1]) * vy,
              f2[2] + (alvo[2] - f2[2]) * vx, f2[3] + (alvo[3] - f2[3]) * vy]
    fw, fh = fr[2] - fr[0], fr[3] - fr[1]
    # borda da moldura: proporcional ao tamanho do furo em cada eixo
    bx, by = fw / (fx1 - fx0), fh / (fy1 - fy0)
    ox0, oy0 = fr[0] - fx0 * bx, fr[1] - fy0 * by
    ow, oh = mw * bx, mh * by
    # a foto dentro do furo: P&B -> cor no empurrão rápido; depois de encher, continua entrando devagar
    a = ctx.cache("foto", lambda: st.carregar(p["foto"]))
    ponto = p.get("ponto", (a.shape[1] / 2, a.shape[0] * 0.42))
    zf = 1.0 + p.get("entra_depois", 0.06) * u(q, Q3, p["fim"] - p["inicio"])
    if fw > 4 and fh > 4:
        foto = _cobrir(a, fw, fh, ponto, zf * p.get("zoom_foto", 1.0))
        c0, c1 = p.get("cor", (41, 49))
        c = u(q, c0, c1)
        if c < 1:
            foto = _pb(foto) * (1 - c) + foto * c
        foto = foto * p.get("ganho", 1.0)
        lay = np.dstack([foto, np.full(foto.shape[:2], 255.0, np.float32)])
        sobre(img, lay, fr[0], fr[1])
    if q < Q3 + 4 and ow > 2 and oh > 2:
        mm = cv2.resize(mold, (max(2, int(round(ow))), max(2, int(round(oh)))), interpolation=cv2.INTER_LINEAR)
        sobre(img, mm, ox0, oy0)
    # borrão de zoom no empurrão rápido (só parede e moldura; a frase entra depois)
    veloc = (_interp(MOLDURA_Z, min(q + 2, Q2)) - _interp(MOLDURA_Z, min(q, Q2))) / max(z, 1e-3)
    img = zoom_borrao(img, z, anc, min(0.06, veloc * 0.9) if q < Q2 + 6 else 0.0)
    # frases: presas à foto (crescem com o furo) até ela encher a tela
    for k, fz in enumerate(p.get("frases", [])):
        prox = p["frases"][k + 1]["quadro"] if k + 1 < len(p["frases"]) else 10 ** 9
        if fz["quadro"] <= n < prox:
            rx, ry = fz.get("rel", (0.5, 0.656))
            corpo = fz.get("corpo_rel", 0.118) * fw
            frase(img, fz["texto"], (fr[0] + rx * fw, fr[1] + ry * fh), corpo, n - fz["quadro"], fz.get("dur", 7),
                  sombra=0.25)
    return img


# ------------------------------------------------------------------------------------------- 2. foto_recorte
def _mascara_tela(ctx, nome, ponto, s, dx=0.0, dy=0.0):
    m = ctx.cache(("m", nome), lambda: np.asarray(Image.open(st.localizar(nome)).convert("L"), np.float32) / 255.0)
    M = np.float32([[s, 0, W / 2 + dx - s * ponto[0]], [0, s, H / 2 + dy - s * ponto[1]]])
    return cv2.warpAffine(m, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def foto_recorte(n, p, ctx):
    q = n - p["inicio"]
    a = ctx.cache("foto", lambda: st.carregar(p["foto"]))
    ponto = p.get("ponto", (a.shape[1] / 2, a.shape[0] / 2))
    s0 = max(W / a.shape[1], H / a.shape[0]) * p.get("zoom", 1.0)
    e = p.get("empurra", {"de": 6, "ate": 31, "z": 1.19})
    z = 1 + (e["z"] - 1) * mv.suavizar_curva(u(q, e["de"], e["ate"]), "s", 1.3)
    s = s0 * z
    dx, dy = p.get("desloc", (0.0, 0.0))
    cor = st.foto_no_quadro(a, ponto[0], ponto[1], s, dx, dy)
    fundo = _pb(cor) * p.get("luz_fundo", 0.92)
    mask = _mascara_tela(ctx, p["mascara"], ponto, s, dx, dy)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.2)[..., None]
    vr = p.get("virada")
    qv = (vr["quadro"] - p["inicio"]) if vr else 10 ** 9
    # bloco montando palavra a palavra, ATRÁS do sujeito; some com desfoque na virada
    b = p.get("bloco")
    if b:
        saida = 1 - u(q, qv, qv + 8)
        for i, linha in enumerate(b["linhas"]):
            y = b["y0"] + i * b["passo"]
            for w in linha:
                if n >= w["quadro"]:
                    frase(fundo, w["texto"], (b["x"], y), b["corpo"], n - w["quadro"] + (qv - q if q > qv else 0) * 0,
                          w.get("dur", 7), cor=tuple(b.get("cor", (206.0, 206.0, 206.0))),
                          alfa=b.get("alfa", 0.9) * saida, sigma0=6.0 + 8.0 * (1 - saida))
    img = fundo * (1 - mask) + cor * p.get("luz_sujeito", 1.0) * mask
    if vr and q >= qv:
        img = img * (1 - (1 - vr.get("escurece", 0.45)) * mv.suavizar_curva(u(q, qv, qv + vr.get("dur_escuro", 14)), "saida", 2.0))
        img = desfoque_pulso(img, q, qv, vr.get("dur_desfoque", 10), vr.get("desfoque", 7.0))
        fz = vr["frase"]
        frase(img, fz["texto"], fz["centro"], fz["corpo"], q - qv, fz.get("dur", 8), sigma0=8.0)
        sb = vr.get("sublinhado")
        if sb:
            # medido: 62 -> 123 -> 173 -> 220 -> 259 -> 289 px (de 289) a cada 2-3 quadros, do meio para as pontas
            frac = _interp({0: 0.0, 1: 0.21, 3: 0.43, 5: 0.60, 8: 0.76, 10: 0.90, 15: 1.0}, q - qv - sb.get("atraso", 1))
            sublinhado(img, sb["x0"], sb["x1"], sb["y"], frac, sb.get("esp", 9.0))
    return img


def sublinhado(img, x0, x1, y, frac, esp=9.0, cor=AMARELO_SUB, arco=7.0, incl=7.0, semente=3):
    """Traço amarelo à mão, do meio para as pontas: sorriso leve, desce um pouco à direita,
    mais grosso no meio."""
    if frac <= 0.005:
        return
    c, h = (x0 + x1) / 2, (x1 - x0) / 2
    a_, b_ = c - frac * h, c + frac * h
    SS = 4
    pad = int(esp * 3 + arco + incl + 6)
    X0, Y0 = int(a_ - pad), int(y - pad)
    lw, lh = int(b_ - a_ + 2 * pad), int(2 * pad)
    m = np.zeros((lh * SS, lw * SS), np.float32)
    rng = np.random.default_rng(semente)
    xs = np.linspace(a_, b_, 48)
    t = (xs - c) / h
    ys = y + arco * t ** 2 + incl * t + rng.normal(0, 0.35, len(xs)).cumsum() * 0.15
    for i in range(len(xs) - 1):
        tt = abs((xs[i] - c) / h)
        e = esp * (1.08 - 0.30 * tt ** 2)
        p0 = (int((xs[i] - X0) * SS), int((ys[i] - Y0) * SS))
        p1 = (int((xs[i + 1] - X0) * SS), int((ys[i + 1] - Y0) * SS))
        cv2.line(m, p0, p1, 1.0, max(1, int(e * SS)), cv2.LINE_AA)
    m = cv2.resize(m, (lw, lh), interpolation=cv2.INTER_AREA)
    _tingir_arr(img, np.clip(m, 0, 1), X0, Y0, cor)


# ------------------------------------------------------------------------------------------- 3. etiqueta_rasgada
# Forma final (0-1 na caixa da etiqueta) e os três degraus dobrados (medidos nas larguras 60/69/87/100%).
TAG_FINAL = [(0.10, 0.03), (0.93, 0.0), (0.94, 0.40), (1.0, 0.43), (0.91, 1.0), (0.0, 0.97), (0.07, 0.55)]
TAG_DOBRAS = [
    [(0.10, 0.03), (0.60, 0.01), (0.46, 0.36), (0.63, 0.62), (0.50, 0.99), (0.0, 0.97), (0.07, 0.55)],
    [(0.10, 0.03), (0.70, 0.01), (0.58, 0.42), (0.72, 0.99), (0.0, 0.97), (0.07, 0.55)],
    [(0.10, 0.03), (0.88, 0.0), (0.81, 0.50), (0.88, 0.99), (0.0, 0.97), (0.07, 0.55)],
]


def _rasgar(pts, larg, alt, semente, amp=2.6, passo=7.0):
    """Densifica o contorno com serrilhado de papel rasgado."""
    rng = np.random.default_rng(semente)
    out = []
    P = [(x * larg, y * alt) for x, y in pts]
    for (x0, y0), (x1, y1) in zip(P, P[1:] + P[:1]):
        L = math.hypot(x1 - x0, y1 - y0)
        k = max(2, int(L / passo))
        nx, ny = -(y1 - y0) / (L + 1e-6), (x1 - x0) / (L + 1e-6)
        for i in range(k):
            t = i / k
            d = rng.normal(0, amp)
            out.append((x0 + (x1 - x0) * t + nx * d, y0 + (y1 - y0) * t + ny * d))
    return np.array(out, np.float32)


def _tag(etapa, larg, alt, semente=11):
    pts = TAG_FINAL if etapa >= 3 else TAG_DOBRAS[etapa]
    pad = 24
    SS = 3
    m = np.zeros(((alt + 2 * pad) * SS, (larg + 2 * pad) * SS), np.float32)
    P = (_rasgar(pts, larg, alt, semente + etapa) + pad) * SS
    cv2.fillPoly(m, [P.astype(np.int32)], 1.0, cv2.LINE_AA)
    m = cv2.resize(m, (larg + 2 * pad, alt + 2 * pad), interpolation=cv2.INTER_AREA)
    tex = 1 + 0.018 * _ruido(alt + 2 * pad, larg + 2 * pad, 14, semente) + 0.006 * _ruido(alt + 2 * pad, larg + 2 * pad, 2, semente + 1)
    rgb = np.array(AMARELO_TAG, np.float32)[None, None, :] * tex[..., None]
    if etapa < 3:                                  # a dobra: a parte de trás aparece mais escura
        yy, xx = np.mgrid[:alt + 2 * pad, :larg + 2 * pad]
        dob = np.clip((xx - pad - larg * (0.40 + 0.12 * etapa)) / (larg * 0.25), 0, 1)
        rgb *= (1 - 0.22 * dob)[..., None]
    lay = np.dstack([rgb, m * 255.0])
    return lay, pad


def etiqueta_rasgada(n, p, ctx):
    q = n - p["inicio"]
    a = ctx.cache("foto", lambda: st.carregar(p["foto"]))
    ponto = p.get("ponto", (a.shape[1] / 2, a.shape[0] / 2))
    af = p.get("afasta", {"z1": 0.952, "tau": 8.0, "deriva": (-114.0, 54.0)})
    v = 1 - math.exp(-q / af.get("tau", 8.0))
    z = 1 + (af["z1"] - 1) * v
    s = max(W / a.shape[1], H / a.shape[0]) * p.get("zoom", 1.08) * z
    ddx, ddy = af.get("deriva", (0.0, 0.0))
    img = st.foto_no_quadro(a, ponto[0], ponto[1], s, ddx * v, ddy * v)
    if p.get("pb", True):
        img = _pb(img)
    img = img * p.get("luz", 0.86)
    e = p["etiqueta"]
    qt = e["quadro"]
    if n >= qt:
        etapa = min(3, (n - qt) // 2)
        lay, pad = ctx.cache(("tag", etapa), lambda: _tag(etapa, e["larg"], e["alt"]))
        sh = lay.copy(); sh[..., :3] = 0; sh[..., 3] = cv2.GaussianBlur(lay[..., 3], (0, 0), 7) * 0.35
        sobre(img, sh, e["x"] - pad + 6, e["y"] - pad + 10)
        sobre(img, lay, e["x"] - pad, e["y"] - pad)
    for t in p.get("textos", []):
        txt = " ".join(w["texto"] for w in t["palavras"] if n >= w["quadro"])
        if not txt:
            continue
        q0 = max(w["quadro"] for w in t["palavras"] if n >= w["quadro"])
        x = e["x"] + t["rel"][0] * e["larg"]
        y = e["y"] + t["rel"][1] * e["alt"]
        frase(img, txt, (x, y), t["corpo"], n - q0 if len(txt.split()) == 1 else 99, t.get("dur", 6),
              alinha=t.get("alinha", "esquerda"))
    return img


# ------------------------------------------------------------------------------------------- 4. jornais_mesa
def _madeira():
    """Tampo de madeira visto de cima: veios ondulados na horizontal, marrom escuro (medido ~95,55,32)."""
    yy, xx = np.mgrid[:H, :W].astype(np.float32)
    n1 = _ruido(H, W, 320, 1) * 0.9
    n2 = _ruido(H, W, 80, 2) * 0.25
    cy = H * 2.6
    d = np.hypot((xx - W * 0.4) * 0.12, (yy - cy)) + 70 * n1 + 18 * n2       # veio quase reto na horizontal
    anel = 0.5 + 0.5 * np.sin(2 * np.pi * d / 58.0)
    anel = anel ** 2.2
    fibra = cv2.resize(np.random.default_rng(3).normal(0, 1, (H, W // 40 + 1)).astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
    fibra = cv2.GaussianBlur(fibra, (0, 0), sigmaX=0.6, sigmaY=1.2)
    escuro = np.array([78.0, 42.0, 24.0]); claro = np.array([146.0, 88.0, 50.0])   # medido ~95,55,32 na média
    v = np.clip(0.52 - 0.22 * anel + 0.07 * fibra + 0.10 * n1, 0, 1)
    img = escuro + (claro - escuro) * v[..., None]
    r = np.hypot((xx - W / 2) / (W * 0.75), (yy - H / 2) / (H * 0.7))
    return (img * (1 - 0.32 * np.clip(r, 0, 1.4) ** 2)[..., None]).astype(np.float32)


def _jornal(spec, semente):
    """Página de jornal envelhecida: cabeçalho, manchete vermelha, colunas de texto cinza, foto e gráfico."""
    larg, alt = spec.get("tam", (520, 660))
    rng = np.random.default_rng(semente)
    yy, xx = np.mgrid[:alt, :larg].astype(np.float32)
    papel = np.array([232.0, 218.0, 186.0])
    r = np.hypot((xx - larg / 2) / (larg * 0.58), (yy - alt / 2) / (alt * 0.58))
    velho = np.clip(r, 0, 1.3) ** 2.0
    img = papel[None, None, :] * (1 - 0.30 * velho)[..., None]
    img[..., 2] *= (1 - 0.18 * velho)                     # a borda amarela mais que o miolo
    img *= (1 + 0.04 * _ruido(alt, larg, 9, semente) + 0.03 * _ruido(alt, larg, 1, semente + 1))[..., None]
    tinta = (40.0, 36.0, 34.0); verm = (186.0, 32.0, 38.0); cinza = (118.0, 112.0, 104.0)
    m = 28
    le.escrever(img, spec.get("nome", "The Daily Ledger"), centro=(larg / 2, m + 26), fonte=SERIFA_RETA,
                corpo=spec.get("corpo_nome", 44), cor=tinta)
    cv2.line(img, (m, m + 58), (larg - m, m + 58), tinta, 2, cv2.LINE_AA)
    cv2.line(img, (m, m + 64), (larg - m, m + 64), tinta, 1, cv2.LINE_AA)
    y = m + 92
    for linha in spec.get("sobre", []):
        le.escrever(img, linha, esquerda=(m, y), fonte=le.INTER, corpo=26, cor=verm, peso=700); y += 32
    for linha in spec.get("manchete", ["25 MILLION"]):
        bb = le.escrever(img, linha, esquerda=(m, y + 26), fonte=le.INTER, corpo=spec.get("corpo_manchete", 64),
                         cor=verm, peso=900)
        y = bb[3] + 12
    for linha in spec.get("sub", []):
        le.escrever(img, linha, esquerda=(m, y + 10), fonte=le.INTER, corpo=22, cor=tinta, peso=600); y += 28
    y = int(y + 10)
    fx0, fy0, fx1 = m, y, larg - m
    fy1 = int(min(y + alt * 0.28, alt - m - 30))
    if fy1 - fy0 > 20:
        g = np.linspace(0, 1, fy1 - fy0)[:, None, None]
        img[fy0:fy1, fx0:fx1] = (np.array([40.0, 46.0, 54.0]) * (1 - g) + np.array([86.0, 98.0, 110.0]) * g)
        if spec.get("palavra_foto"):
            le.escrever(img, spec["palavra_foto"], centro=((fx0 + fx1) / 2, (fy0 + fy1) / 2), fonte=le.INTER, corpo=44,
                        cor=verm, peso=900)
        y = fy1 + 18
    cols = 3
    cw = (larg - 2 * m - (cols - 1) * 14) / cols
    for c in range(cols):
        x = m + c * (cw + 14)
        yy_ = y
        while yy_ < alt - m - (60 if c == cols - 1 and spec.get("grafico") else 0):
            w_ = cw * rng.uniform(0.55, 1.0) if rng.random() < 0.2 else cw
            cv2.rectangle(img, (int(x), int(yy_)), (int(x + w_), int(yy_ + 4)), cinza, -1)
            yy_ += 11
    if spec.get("grafico"):
        x0 = m + 2 * (cw + 14); base = alt - m
        for k in range(6):
            hh = 10 + k * 9 + rng.uniform(-3, 3)
            cv2.rectangle(img, (int(x0 + k * cw / 6.5), int(base - hh)), (int(x0 + k * cw / 6.5 + cw / 9), int(base)), verm, -1)
    # sombra de dobra no meio
    img *= (1 - 0.06 * np.exp(-((xx - larg * 0.5) / 6.0) ** 2))[..., None]
    return np.dstack([np.clip(img, 0, 255), np.full((alt, larg), 255.0, np.float32)])


def _rgba_girado(lay, graus, escala=1.0):
    h, w = lay.shape[:2]
    c = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(c, graus, escala)
    cs, sn = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sn + w * cs) + 4, int(h * cs + w * sn) + 4
    M[0, 2] += nw / 2 - c[0]; M[1, 2] += nh / 2 - c[1]
    return cv2.warpAffine(lay, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def _mesa_com_jornais(p):
    """A mesa montada uma vez, em 1,35x o quadro, para a câmera poder afastar sem mostrar borda."""
    S = p.get("folga", 1.35)
    Wb, Hb = int(W * S), int(H * S)
    mesa = cv2.resize(_madeira(), (Wb, Hb), interpolation=cv2.INTER_LINEAR)
    for k, j in enumerate(p["jornais"]):                  # centro e tamanho dados na tela, no pouso
        pg = _rgba_girado(_jornal(j, 40 + k), j.get("giro", 0.0), j.get("escala", 1.0) * S)
        cx, cy = j["centro"]
        x, y = Wb / 2 + (cx - W / 2) * S - pg.shape[1] / 2, Hb / 2 + (cy - H / 2) * S - pg.shape[0] / 2
        sh = pg.copy(); sh[..., :3] = 0; sh[..., 3] = cv2.GaussianBlur(pg[..., 3], (0, 0), 14) * 0.55
        sobre(mesa, sh, x + 10, y + 18)
        sobre(mesa, pg, x, y)
    return mesa


def jornais_mesa(n, p, ctx):
    q = n - p["inicio"]
    mesa = ctx.cache("mesa", lambda: _mesa_com_jornais(p))
    S = mesa.shape[1] / W
    po = p.get("chegada", {"de": 1.7, "quadros": 8, "giro": 5.0})
    v = min(1.0, q / po["quadros"])
    chega = 1 + (po["de"] - 1) * (1 - mv.suavizar_curva(v, "saida", 2.2))
    giro = po["giro"] * (1 - mv.suavizar_curva(v, "saida", 2.2))
    af = p.get("afasta", {"z1": 0.91})
    z_af = 1 + (af["z1"] - 1) * mv.suavizar_curva(u(q, po["quadros"], p["fim"] - p["inicio"]), "saida", 1.6)
    z = chega * z_af / S
    alvo = p.get("alvo", (W / 2, H / 2))                   # o ponto da mesa que fica no centro
    ax, ay = mesa.shape[1] / 2 + (alvo[0] - W / 2) * S, mesa.shape[0] / 2 + (alvo[1] - H / 2) * S
    M = cv2.getRotationMatrix2D((ax, ay), giro, z)
    M[0, 2] += alvo[0] - ax; M[1, 2] += alvo[1] - ay
    img = cv2.warpAffine(mesa, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    if v < 1:                                              # borrão do pouso
        img = zoom_borrao(img, 1.0, (W / 2, H / 2), 0.08 * (1 - v) ** 1.5)
    # laço branco feito à mão na manchete (presa à mesa: acompanha a câmera)
    lc = p.get("laco")
    if lc and n >= lc["quadro"]:
        frac = min(1.0, (n - lc["quadro"] + 1) / lc.get("dur", 8))
        _laco(img, lc, frac, M, S, mesa.shape)
    t = p.get("titulo")
    if t:
        txt = " ".join(w["texto"] for w in t["palavras"] if n >= w["quadro"])
        if txt:
            q0 = max(w["quadro"] for w in t["palavras"] if n >= w["quadro"])
            frase(img, txt, (W / 2, t["y"] - t.get("sobe", 30) * u(q, 0, p["fim"] - p["inicio"])), t["corpo"],
                  n - q0 if q0 == t["palavras"][0]["quadro"] else 99, 7, sombra=0.3)
    ln = p.get("linha")
    if ln:
        txt = " ".join(w["texto"] for w in ln["palavras"] if n >= w["quadro"])
        if txt:
            frase(img, txt, (W / 2, ln["y"]), ln["corpo"], 99, sombra=0.3, cor=(226.0, 222.0, 214.0))
    fo = p.get("foco")
    if fo:
        img = desfoque_pulso(img, q, fo["quadro"] - p["inicio"], fo.get("dur", 12), fo.get("sigma", 6.0))
    return img


def _laco(img, lc, frac, M, S, forma):
    """Volta e meia em torno da manchete, com rabicho (lupa desenhada), traço branco fino.
    Centro e raio dados na tela, no pouso; o laço é desenhado na mesa e anda com a câmera."""
    cx = forma[1] / 2 + (lc["centro"][0] - W / 2) * S
    cy = forma[0] / 2 + (lc["centro"][1] - H / 2) * S
    rx, ry = (r * S for r in lc.get("raio", (250.0, 200.0)))
    k = 90
    th = np.linspace(-0.35 * math.pi, 1.75 * math.pi, k)
    jit = np.random.default_rng(7).normal(0, 0.012, k).cumsum() * 0.3
    xs = cx + rx * (1 + jit) * np.cos(th)
    ys = cy + ry * (1 + jit) * np.sin(th)
    rab = np.linspace(0, 1, 18)
    xs = np.r_[xs, xs[-1] + rab * rx * 0.55]
    ys = np.r_[ys, ys[-1] + rab * ry * 0.75]
    m = int(len(xs) * frac)
    if m < 2:
        return
    pts = np.stack([xs[:m], ys[:m], np.ones(m)], 1) @ M.T
    SS = 3
    camada = np.zeros((H * SS // 4, W * SS // 4), np.float32)   # meia resolução x 3/4 bastam para um traço fino
    esc = SS / 4
    cv2.polylines(camada, [(pts * esc).astype(np.int32)], False, 1.0, max(1, int(round(lc.get("esp", 5.0) * esc))), cv2.LINE_AA)
    a = cv2.resize(camada, (W, H), interpolation=cv2.INTER_LINEAR)
    a = cv2.GaussianBlur(a, (0, 0), 0.8)
    img[:] = img * (1 - a[..., None] * 0.92) + np.array([242.0, 240.0, 236.0]) * a[..., None] * 0.92


TIPOS_GALERIA = {"moldura_entra": moldura_entra, "foto_recorte": foto_recorte, "etiqueta_rasgada": etiqueta_rasgada,
                 "jornais_mesa": jornais_mesa}
