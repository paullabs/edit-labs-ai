"""
Telestração (v12.7) — o desenho que EXPLICA, por cima de qualquer plano: filmagem real, foto ou papel.

Regra: quando a fala explica algo, a explicação vira um desenho animado por cima da imagem, não uma frase.
A filmagem mostra o que aconteceu; o desenho mostra por quê (o ar que o ventilador puxa, a força que gruda, os jatos
contados, o caminho do salto). Cada plano pode ter

    "desenhos": [{"tipo": ..., "quadro": q, "ate": q?, "camada": "cena" | "tela", ...}, ...]

No video_clip a camada padrão é "cena": o desenho entra ANTES do empurrão da câmera e anda junto com a filmagem. Nos
outros planos (e com "camada": "tela") entra por cima de tudo, antes das palavras grandes.

Tipos (coordenadas na tela 1080x1920; `dur` em quadros; `cor` com nome ou [r, g, b]):
  escurece    fator 0,45, dur 6           baixa a imagem: o modo explicação (o desenho acende por cima)
  traco       pts, dur, tracejado [28,18], ponta, esp 7, fecha   linha que se desenha do primeiro ao último ponto
  seta        de, para, dur 6, curva 0,12, esp 8, ponta 38        seta à mão que cresce até a ponta
  fluxo       pts, vel 14, traco 34, vao 26, esp 6, ponta, dur    tracejado que corre pelo caminho (o ar indo)
  circulo     centro, rx, ry, dur 8, esp 7                        círculo à mão que fecha passando do início
  ventilador  centro, tam 150, gira 47 (graus por quadro), entra 5  hélice que gira (a 10 qps "pisca" de propósito)
  rotulo      texto, pos, corpo 40, linha [[x,y],[x,y]], fundo, alinha, fonte (inter|grotesca|serifa)   etiqueta com fio
  balao       centro, larg, alt, ponta, texto, quadro_texto, corpo 96, entra 5   balão de fala que estoura
  recorte     imagem (RGBA), largura, pos [cx, y_base], entra baixo|esquerda|direita|pop, dur 7, borda 12, rot
              foto recortada com borda de adesivo e sombra, que entra e assenta
  proibido    centro, r, dur 9, esp 30                            placa de proibido desenhada (círculo e a barra)
  cronometro  centro, r 110, para (quadro), volta_s 1,0, entra 5  cronômetro que corre e para
  numero      de, ate, passo 3, pos, corpo 220, sufixo           contador em serifa (1, 2, 3 ... 10)
  carrinho    centro, comprimento 320, rot (graus), gira {"de": q, "ate": q, "graus": 180}, espelha, pista, dur
              carro de perfil a giz (corpo, vidro, rodas) que se desenha e pode girar — o pictograma do "de cabeça
              para baixo" e do esquema do ventilador
Qualquer desenho aceita `segue`: [[quadro, dx, dy], ...] — desloca o desenho junto com um objeto que anda na filmagem
(posição medida por quadro, interpolada). `traco` aceita `linhas` (várias polilinhas que se desenham juntas).
`escurece` aceita `desfoca` (sigma do desfoque no fim da rampa).
Cores com nome: giz (branco quente), ar (azul claro), forca (vermelho vivo), amarelo, tinta, azul, vermelho, branco.

Todo traço tem tremor e "ferve" (boil) a cada 2 degraus, com semente por elemento — parece feito à mão, não vetor
(memória "boil": intensidade por classe, semente por elemento). Sobre filmagem clara, `sombra` põe um halo escuro
embaixo do traço para ele ler em qualquer fundo.
"""
import math

import cv2
import numpy as np

from familia_a import W, H
from familia_a import c2_letras as le, c3_style as st, c5_movimentos as mv
from familia_a.compor import sobre

FPS = 30
CORES = {"giz": (244.0, 242.0, 234.0), "ar": (128.0, 202.0, 255.0), "forca": (246.0, 74.0, 58.0),
         "amarelo": (248.0, 210.0, 72.0), "tinta": (26.0, 22.0, 24.0), "azul": (21.0, 126.0, 190.0),
         "vermelho": (176.0, 30.0, 36.0), "branco": (250.0, 250.0, 250.0), "preto": (12.0, 12.0, 14.0)}
SS = 3                     # supersample das máscaras de traço


def cor(c, padrao="giz"):
    c = padrao if c is None else c
    if isinstance(c, str):
        return CORES[c]
    return tuple(float(v) for v in c)


def _u(n, q, dur):
    return 1.0 if dur <= 0 else min(1.0, max(0.0, (n - q + 3) / float(dur)))


def _saida(t, p=2.2):
    return 1 - (1 - min(1.0, max(0.0, t))) ** p


# ------------------------------------------------------------------ traço à mão
def _ferve(pts, semente, n, amp=1.3):
    """Tremor suave ao longo da linha; muda a cada 2 degraus (6 quadros)."""
    pts = np.asarray(pts, np.float32)
    if amp <= 0 or len(pts) < 2:
        return pts
    rng = np.random.default_rng(semente * 7919 + (n // 6) * 104729)
    r = rng.normal(0, 1, pts.shape).astype(np.float32)
    k = min(7, len(pts))
    if k > 2:
        ker = np.ones(k, np.float32) / k
        r = np.stack([np.convolve(r[:, i], ker, mode="same") for i in range(2)], 1)
    return pts + r * amp


def _densa(pts, passo=6.0):
    """Reamostra a polilinha a cada `passo` px (o tremor precisa de pontos)."""
    pts = np.asarray(pts, np.float32)
    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        L = float(np.hypot(*(b - a)))
        k = max(1, int(L / passo))
        for j in range(1, k + 1):
            out.append(a + (b - a) * j / k)
    return np.array(out, np.float32)


def _comprimentos(pts):
    d = np.hypot(*(np.diff(pts, axis=0).T))
    return np.concatenate([[0.0], np.cumsum(d)])


def _parcial(pts, frac):
    """O trecho da polilinha até `frac` do comprimento."""
    if frac >= 0.999:
        return pts
    s = _comprimentos(pts)
    alvo = s[-1] * max(0.0, frac)
    i = int(np.searchsorted(s, alvo))
    if i <= 0:
        return pts[:1]
    a, b = pts[i - 1], pts[i]
    t = (alvo - s[i - 1]) / max(1e-6, s[i] - s[i - 1])
    return np.vstack([pts[:i], a + (b - a) * t])


def _tracos(pts, traco, vao, fase=0.0):
    """Pedaços do tracejado (lista de polilinhas); `fase` desloca o tracejado ao longo da linha (anda)."""
    s = _comprimentos(pts)
    L, per = s[-1], traco + vao
    out = []
    ini = -(fase % per)
    while ini < L:
        a, b = max(0.0, ini), min(L, ini + traco)
        if b > a + 1:
            ia, ib = np.searchsorted(s, a), np.searchsorted(s, b)
            seg = [np.interp(a, s, pts[:, 0]), np.interp(a, s, pts[:, 1])]
            meio = pts[ia:ib].tolist()
            fim = [np.interp(b, s, pts[:, 0]), np.interp(b, s, pts[:, 1])]
            out.append(np.array([seg] + meio + [fim], np.float32))
        ini += per
    return out


def _ponta(pts, tam):
    """As duas pernas da ponta de seta no fim da polilinha."""
    if len(pts) < 2:
        return []
    k = min(len(pts) - 1, 6)
    d = pts[-1] - pts[-1 - k]
    nrm = float(np.hypot(*d))
    if nrm < 1e-3:
        return []
    d = d / nrm
    pernas = []
    for ang in (2.55, -2.55):
        r = np.array([[math.cos(ang), -math.sin(ang)], [math.sin(ang), math.cos(ang)]], np.float32)
        pernas.append(np.array([pts[-1], pts[-1] + (r @ d) * tam], np.float32))
    return pernas


def _caixa(listas, pad):
    allp = np.vstack([np.asarray(p, np.float32).reshape(-1, 2) for p in listas if len(p)])
    return (allp[:, 0].min() - pad, allp[:, 1].min() - pad, allp[:, 0].max() + pad, allp[:, 1].max() + pad)


def _mascara(listas, esp, fechadas=False, preenche=None):
    """Máscara (alfa 0-1) das polilinhas, alocada só na caixa delas. Devolve (a, x0, y0)."""
    if not listas and not preenche:
        return None, 0, 0
    pad = esp + 20
    x0, y0, x1, y1 = _caixa(listas + (preenche or []), pad)
    x0, y0 = int(max(0, math.floor(x0))), int(max(0, math.floor(y0)))
    x1, y1 = int(min(W, math.ceil(x1))), int(min(H, math.ceil(y1)))
    if x1 <= x0 + 1 or y1 <= y0 + 1:
        return None, 0, 0
    m = np.zeros(((y1 - y0) * SS, (x1 - x0) * SS), np.uint8)
    conv = lambda p: np.int32(np.round((np.asarray(p, np.float32) - (x0, y0)) * SS * 4))
    for poli in preenche or []:
        cv2.fillPoly(m, [conv(poli)], 255, cv2.LINE_AA, shift=2)
    for poli in listas:
        if len(poli) >= 2:
            cv2.polylines(m, [conv(poli)], fechadas, 255, max(1, int(round(esp * SS))), cv2.LINE_AA, shift=2)
    a = cv2.resize(m, (x1 - x0, y1 - y0), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return a, x0, y0


def _pintar(img, a, x0, y0, c, alfa=1.0, sombra=0.0):
    """Pinta a máscara `a` (alfa 0-1) com o canto em (x0, y0), recortando nas bordas da tela. `sombra` escurece um
    halo embaixo (o traço claro lê sobre filmagem clara)."""
    if a is None or alfa <= 0:
        return img
    if sombra > 0:
        pad = 16
        a = np.pad(a, pad); x0 -= pad; y0 -= pad
    h, w = a.shape
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(img.shape[1], x0 + w), min(img.shape[0], y0 + h)
    if xa >= xb or ya >= yb:
        return img
    a = a[ya - y0:yb - y0, xa - x0:xb - x0]
    reg = img[ya:yb, xa:xb]
    if sombra > 0:
        s = np.clip(cv2.GaussianBlur(a, (0, 0), 5.0) * 1.6, 0, 1) * sombra
        reg *= (1 - s)[..., None]
    aa = (a * alfa)[..., None]
    reg[:] = reg * (1 - aa) + np.array(c, np.float32) * aa
    return img


def _riscar(img, listas, esp, c, alfa=1.0, sombra=0.0, fechadas=False):
    a, x0, y0 = _mascara(listas, esp, fechadas)
    return _pintar(img, a, x0, y0, c, alfa, sombra)


# ------------------------------------------------------------------ tipos
def _escurece(img, n, d):
    g = mv.suavizar_curva(_u(n, d["quadro"], d.get("dur", 6)), "s", 1.6)
    sig = float(d.get("desfoca", 0.0)) * g
    if sig > 0.3:
        img[:] = cv2.GaussianBlur(img, (0, 0), sig)
    img *= 1 - float(d.get("fator", 0.45)) * g
    return img


def _traco(img, n, d, sem):
    if d.get("linhas"):
        frac = _saida(_u(n, d["quadro"], d.get("dur", 9)), 1.8)
        if frac <= 0.01:
            return img
        listas = [_parcial(_ferve(_densa(l), sem + k, n, d.get("tremor", 1.0)), frac) for k, l in enumerate(d["linhas"])]
        return _riscar(img, listas, float(d.get("esp", 5)), cor(d.get("cor")), d.get("alfa", 1.0), d.get("sombra", 0.5))
    pts = _densa(d["pts"])
    frac = _saida(_u(n, d["quadro"], d.get("dur", 9)), 1.8)
    if frac <= 0.01:
        return img
    pts = _ferve(pts, sem, n, d.get("tremor", 1.3))
    parte = _parcial(pts, frac)
    if d.get("fecha") and frac >= 0.999:
        parte = np.vstack([parte, parte[:1]])
    esp = float(d.get("esp", 7))
    listas = _tracos(parte, *d["tracejado"]) if d.get("tracejado") else [parte]
    if d.get("ponta"):
        listas += _ponta(parte, d.get("ponta_tam", esp * 4.5))
    return _riscar(img, listas, esp, cor(d.get("cor")), d.get("alfa", 1.0), d.get("sombra", 0.5))


def _seta(img, n, d, sem):
    g = _saida(_u(n, d["quadro"], d.get("dur", 6)), 2.0)
    if g <= 0.04:
        return img
    p0, p1 = np.array(d["de"], np.float32), np.array(d["para"], np.float32)
    meio = (p0 + p1) / 2
    nv = np.array([-(p1 - p0)[1], (p1 - p0)[0]], np.float32)
    ctrl = meio + nv * float(d.get("curva", 0.12))
    t = np.linspace(0, 1, 40)[:, None]
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * p1
    pts = _ferve(pts, sem, n, d.get("tremor", 1.0))
    parte = _parcial(pts, g)
    esp = float(d.get("esp", 8))
    listas = [parte] + _ponta(parte, d.get("ponta", esp * 4.6))
    return _riscar(img, listas, esp, cor(d.get("cor")), d.get("alfa", 1.0), d.get("sombra", 0.5))


def _fluxo(img, n, d, sem):
    """Setas tracejadas que correm pelo caminho (o ar sendo puxado)."""
    q, dur = d["quadro"], d.get("dur", 6)
    g = _saida(_u(n, q, dur), 1.6)
    if g <= 0.02:
        return img
    pts = _ferve(_densa(d["pts"]), sem, n, d.get("tremor", 0.8))
    parte = _parcial(pts, g)
    fase = (n - q) * float(d.get("vel", 14))
    esp = float(d.get("esp", 6))
    listas = _tracos(parte, d.get("traco", 34), d.get("vao", 26), -fase)
    if d.get("ponta", True):
        listas += _ponta(parte, d.get("ponta_tam", esp * 4.2))
    return _riscar(img, listas, esp, cor(d.get("cor"), "ar"), d.get("alfa", 1.0), d.get("sombra", 0.45))


def _circulo(img, n, d, sem):
    frac = _saida(_u(n, d["quadro"], d.get("dur", 8)), 1.8)
    if frac <= 0.02:
        return img
    rng = np.random.default_rng(sem)
    cx, cy = d["centro"]
    rx = float(d["rx"]); ry = float(d.get("ry", rx))
    a0 = float(d.get("inicio_ang", -2.3))
    k = 120
    ang = a0 + np.linspace(0, frac * 2 * math.pi * 1.08, k)
    ruido = np.cumsum(rng.normal(0, 0.010, k)); ruido -= np.linspace(0, ruido[-1], k) * 0.4
    pts = np.stack([cx + rx * (1 + ruido) * np.cos(ang), cy + ry * (1 + ruido) * np.sin(ang)], 1)
    pts = _ferve(pts, sem, n, d.get("tremor", 0.9))
    return _riscar(img, [pts], float(d.get("esp", 7)), cor(d.get("cor")), d.get("alfa", 1.0), d.get("sombra", 0.5))


def _ventilador_rgba(tam, ang, c):
    s = 4
    w = int(tam)
    m = np.zeros((w * s, w * s), np.float32)
    ce = w * s / 2
    cv2.circle(m, (int(ce), int(ce)), int(w * s * 0.47), 1.0, max(2, int(w * s * 0.05)), cv2.LINE_AA)
    for k in range(3):
        a = math.radians(ang + k * 120)
        pts = []
        for f, r in ((-0.30, 0.09), (-0.22, 0.40), (0.00, 0.43), (0.25, 0.30), (0.10, 0.09)):
            pts.append((ce + math.cos(a + f) * r * w * s, ce + math.sin(a + f) * r * w * s))
        cv2.fillPoly(m, [np.int32(pts)], 1.0, cv2.LINE_AA)
    cv2.circle(m, (int(ce), int(ce)), int(w * s * 0.085), 1.0, -1, cv2.LINE_AA)
    return cv2.resize(m, (w, w), interpolation=cv2.INTER_AREA)


def _ventilador(img, n, d, sem):
    q = d["quadro"]
    e = _saida(_u(n, q, d.get("entra", 5)), 2.4)
    tam = int(d.get("tam", 150) * max(0.05, e))
    if tam < 6:
        return img
    a = _ventilador_rgba(tam, (n - q) * float(d.get("gira", 47.0)), None)
    cx, cy = d["centro"]
    return _pintar(img, a, int(round(cx - tam / 2)), int(round(cy - tam / 2)), cor(d.get("cor")), d.get("alfa", 1.0),
                   d.get("sombra", 0.55))


def _rotulo(img, n, d, sem):
    q = d["quadro"]
    if d.get("linha"):
        _riscar(img, [_parcial(_ferve(_densa(d["linha"], 4.0), sem, n, 0.6), _saida(_u(n, q, 4)))],
                float(d.get("esp_linha", 4)), cor(d.get("cor")), 1.0, 0.5)
    if n < q + d.get("atraso_texto", 2):
        return img
    corpo = float(d.get("corpo", 40))
    fonte = {"inter": le.INTER, "serifa": le.SERIFA, "grotesca": le.GROTESCA}[d.get("fonte", "inter")]
    peso = d.get("peso", 700) if fonte == le.INTER else (le.GROTESCA_PESO if fonte == le.GROTESCA else None)
    m, _ = le.mascara(d["texto"], fonte, corpo, peso, 0.0, d.get("tracking", 1.0))
    mw, mh = m.size
    x, y = d["pos"]
    al = d.get("alinha", "centro")
    x0 = x - mw / 2 if al == "centro" else (x if al == "esq" else x - mw)
    y0 = y - mh / 2
    if d.get("fundo", True):
        px, py = corpo * 0.42, corpo * 0.30
        caixa = _ret_arredondado(x0 - px, y0 - py, x0 + mw + px, y0 + mh + py, (mh + 2 * py) * 0.5)
        a, ax, ay = _mascara([], 1, preenche=[caixa])
        _pintar(img, a, ax, ay, cor(d.get("cor_fundo"), "preto"), d.get("alfa_fundo", 0.62), 0.0)
    a = np.asarray(m, np.float32) / 255.0
    return _pintar(img, a, int(round(x0)), int(round(y0)), cor(d.get("cor")), 1.0, 0.0 if d.get("fundo", True) else 0.5)


def _ret_arredondado(x0, y0, x1, y1, r):
    r = max(1.0, min(r, (x1 - x0) / 2, (y1 - y0) / 2))
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for a in np.linspace(a0, a0 + 90, 10):
            pts.append((cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))))
    return np.array(pts, np.float32)


def _balao(img, n, d, sem, ctx):
    q = d["quadro"]
    t = min(1.0, (n - q + 3) / float(d.get("entra", 5)))
    if t <= 0:
        return img
    c1 = 1.70158                                                 # ease-out com recuo: passa de 1 e volta (estoura)
    esc = 0.55 + 0.45 * (1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2)
    cx, cy = d["centro"]
    lw, lh = float(d["larg"]) * esc, float(d["alt"]) * esc
    r = min(lw, lh) * 0.5
    px, py = d["ponta"]
    # corpo arredondado (elipse achatada) + rabicho até a ponta
    ang = np.linspace(0, 2 * math.pi, 90, endpoint=False)
    sup = 3.4                                                    # superelipse: entre retângulo e elipse
    ex = np.sign(np.cos(ang)) * np.abs(np.cos(ang)) ** (2 / sup) * lw / 2
    ey = np.sign(np.sin(ang)) * np.abs(np.sin(ang)) ** (2 / sup) * lh / 2
    corpo_pts = np.stack([cx + ex, cy + ey], 1).astype(np.float32)
    v = np.array([px - cx, py - cy], np.float32)
    vn = v / (np.hypot(*v) + 1e-6)
    base_c = np.array([cx, cy], np.float32) + vn * min(lw, lh) * 0.30
    perp = np.array([-vn[1], vn[0]], np.float32) * r * 0.30
    pta = np.array([cx, cy], np.float32) + (np.array([px, py], np.float32) - np.array([cx, cy], np.float32)) * min(1.0, esc)
    rab = np.array([base_c + perp, pta, base_c - perp], np.float32)
    a, x0, y0 = _mascara([], 1, preenche=[corpo_pts, rab])
    if a is None:
        return img
    contorno = cv2.dilate((a > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
    contorno = cv2.GaussianBlur(contorno, (0, 0), 0.8)
    _pintar(img, contorno, x0, y0, cor(d.get("cor_borda"), "tinta"), 1.0, d.get("sombra", 0.55))
    _pintar(img, a, x0, y0, cor(d.get("cor_fundo"), "branco"), 1.0, 0.0)
    qt = d.get("quadro_texto", q + 3)
    if n >= qt and d.get("texto"):
        from familia_a import c6_motion as mo
        e2 = mo.escala_palavra((n - qt) / FPS)
        corpo = float(d.get("corpo", 96))
        le.escrever(img, d["texto"], centro=(cx, cy + float(d.get("dy_texto", 0))), fonte=le.SERIFA, corpo=corpo * esc,
                    cor=cor(d.get("cor_texto"), "tinta"), contorno=1.0, escala=e2)
    return img


def _adesivo(ctx, nome, largura, borda):
    def f():
        a = st.escalar(st.carregar(nome), largura=largura)
        alfa = a[..., 3] / 255.0 if a[..., 3].max() > 1.5 else a[..., 3]
        pad = borda + 40
        h, w = alfa.shape
        A = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
        A[pad:pad + h, pad:pad + w] = alfa
        rgb = np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32)
        rgb[pad:pad + h, pad:pad + w] = a[..., :3]
        k = 2 * borda + 1
        dil = cv2.dilate((A > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))).astype(np.float32)
        dil = cv2.GaussianBlur(dil, (0, 0), 1.2)
        som = cv2.GaussianBlur(dil, (0, 0), 14.0)
        lay = np.zeros(A.shape + (4,), np.float32)
        lay[..., :3] = np.array(CORES["branco"], np.float32) * (1 - A[..., None]) + rgb * A[..., None]
        lay[..., 3] = np.maximum(dil, A)
        return lay, som
    return ctx.cache(("adesivo", nome, int(largura), int(borda)), f)


def _recorte(img, n, d, sem, ctx):
    q = d["quadro"]
    if n < q:
        return img
    lay, som = _adesivo(ctx, d["imagem"], d.get("largura", 600), d.get("borda", 12))
    t = _u(n, q, d.get("dur", 7))
    g = mv.suavizar_curva(t, "saida", 3.0)
    cx, yb = d["pos"]
    h, w = lay.shape[:2]
    x, y = cx - w / 2, yb - h
    rot = float(d.get("rot", 0.0))
    modo = d.get("entra", "baixo")
    if modo == "baixo":
        y += (1 - g) * (H - y + 40)
        rot += (1 - g) * 6.0
    elif modo in ("esquerda", "direita"):
        sinal = -1 if modo == "esquerda" else 1
        x += sinal * (1 - g) * (W * 0.9)
        rot += sinal * (1 - g) * 8.0
    esc = 1.0
    if modo == "pop":
        esc = 0.5 + 0.5 * g + 0.06 * math.sin(math.pi * t) * (1 - t)
    dr = float(d.get("deriva", 0.0)) * (n - q) / FPS                      # assentado, continua respirando
    if abs(rot) > 0.05 or esc != 1.0:
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, esc)
        lay = cv2.warpAffine(lay, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        som = cv2.warpAffine(som, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if d.get("sombra", True):
        dx, dy = d.get("sombra_desloc", (12, 22))
        xs, ys = int(round(x + dx)), int(round(y + dy - dr))
        xa, ya, xb, yb = max(0, xs), max(0, ys), min(W, xs + w), min(H, ys + h)
        if xa < xb and ya < yb:
            img[ya:yb, xa:xb] *= (1 - 0.55 * som[ya - ys:yb - ys, xa - xs:xb - xs])[..., None]
    return sobre(img, lay, x, y - dr)


def _proibido(img, n, d, sem):
    dur = d.get("dur", 9)
    frac = _saida(_u(n, d["quadro"], dur), 1.6)
    if frac <= 0.02:
        return img
    cx, cy = d["centro"]
    r = float(d["r"])
    fc = min(1.0, frac / 0.68)
    fb = max(0.0, (frac - 0.68) / 0.32)
    rng = np.random.default_rng(sem)
    ang = -2.2 + np.linspace(0, fc * 2 * math.pi * 1.04, 120)
    ru = np.cumsum(rng.normal(0, 0.006, 120)); ru -= np.linspace(0, ru[-1], 120) * 0.5
    circ = np.stack([cx + r * (1 + ru) * np.cos(ang), cy + r * (1 + ru) * np.sin(ang)], 1)
    listas = [_ferve(circ, sem, n, 1.0)]
    if fb > 0:
        a0 = np.array([cx - r * 0.70, cy - r * 0.70], np.float32)
        a1 = np.array([cx + r * 0.70, cy + r * 0.70], np.float32)
        barra = _densa(np.array([a0, a0 + (a1 - a0) * _saida(fb, 1.6)]))
        listas.append(_ferve(barra, sem + 1, n, 1.0))
    return _riscar(img, listas, float(d.get("esp", 30)), cor(d.get("cor"), "forca"), 1.0, d.get("sombra", 0.6))


def _cronometro(img, n, d, sem):
    q = d["quadro"]
    e = _saida(_u(n, q, d.get("entra", 5)), 2.4)
    if e <= 0.02:
        return img
    cx, cy = d["centro"]
    r = float(d.get("r", 110)) * e
    c = cor(d.get("cor"))
    esp = float(d.get("esp", 9))
    rng_ang = np.linspace(0, 2 * math.pi, 100)
    aro = np.stack([cx + r * np.cos(rng_ang), cy + r * np.sin(rng_ang)], 1)
    listas = [_ferve(aro, sem, n, 0.8)]
    listas.append(np.array([[cx, cy - r], [cx, cy - r - r * 0.16]], np.float32))            # haste
    listas.append(np.array([[cx - r * 0.14, cy - r * 1.20], [cx + r * 0.14, cy - r * 1.20]], np.float32))  # botão
    for k in range(12):                                                                      # marcas
        a = k * math.pi / 6
        r0 = r * (0.80 if k % 3 == 0 else 0.87)
        listas.append(np.array([[cx + r0 * math.sin(a), cy - r0 * math.cos(a)],
                                [cx + r * 0.94 * math.sin(a), cy - r * 0.94 * math.cos(a)]], np.float32))
    fim = d.get("para")
    t = ((min(n, fim) if fim is not None else n) - q) / FPS
    a = 2 * math.pi * t / float(d.get("volta_s", 1.0))
    listas.append(np.array([[cx, cy], [cx + r * 0.74 * math.sin(a), cy - r * 0.74 * math.cos(a)]], np.float32))
    _riscar(img, listas, esp, c, 1.0, d.get("sombra", 0.55))
    a2, x0, y0 = _mascara([], 1, preenche=[np.stack([cx + r * 0.09 * np.cos(rng_ang), cy + r * 0.09 * np.sin(rng_ang)], 1)])
    return _pintar(img, a2, x0, y0, c, 1.0, 0.0)


def _numero(img, n, d, sem):
    from familia_a import c6_motion as mo
    q, passo = d["quadro"], int(d.get("passo", 3))
    if n < q:
        return img
    k = (n - q) // passo
    v = min(int(d["ate"]), int(d.get("de", 1)) + k)
    q_v = q + (v - int(d.get("de", 1))) * passo
    texto = f"{v}{d.get('sufixo', '')}"
    x, y = d["pos"]
    if d.get("sombra", True):
        m, _ = le.mascara(texto, le.SERIFA, float(d.get("corpo", 220)), None, 1.0)
        a = cv2.GaussianBlur(np.asarray(m, np.float32) / 255.0, (0, 0), 10.0)
        mw, mh = m.size
        xi, yi = int(round(x - mw / 2)), int(round(y - mh / 2))
        xa, ya, xb, yb = max(0, xi), max(0, yi), min(W, xi + mw), min(H, yi + mh)
        if xa < xb and ya < yb:
            img[ya:yb, xa:xb] *= (1 - 0.6 * np.clip(a[ya - yi:yb - yi, xa - xi:xb - xi] * 2, 0, 1))[..., None]
    le.escrever(img, texto, centro=(x, y), fonte=le.SERIFA, corpo=float(d.get("corpo", 220)), cor=cor(d.get("cor")),
                contorno=1.0, escala=mo.escala_palavra((n - q_v) / FPS))
    return img


# carro de perfil (de frente para a esquerda), comprimento 1, chão em y=0, y para cima negativo
_PERFIL = [(0.000, -0.062), (0.006, -0.088), (0.045, -0.112), (0.300, -0.150), (0.400, -0.176), (0.525, -0.256),
           (0.645, -0.258), (0.800, -0.196), (0.950, -0.176), (1.000, -0.150), (1.000, -0.082), (0.962, -0.056)]
_VIDRO = [(0.418, -0.176), (0.530, -0.240), (0.636, -0.242), (0.770, -0.192), (0.418, -0.176)]


def _carro_linhas(L):
    def arco(cx, cy, r, de, ate, k=14):
        a = np.linspace(math.radians(de), math.radians(ate), k)
        return [(cx + r * math.cos(t), cy - r * math.sin(t)) for t in a]
    corpo = list(_PERFIL)
    corpo += [(0.882, -0.056)] + arco(0.80, -0.056, 0.082, 0, 180) + [(0.718, -0.056), (0.282, -0.056)]
    corpo += arco(0.20, -0.056, 0.082, 0, 180) + [(0.118, -0.056), (0.020, -0.056), corpo[0]]
    rodas = [arco(cx, -0.068, 0.066, 0, 360, 28) for cx in (0.20, 0.80)]
    linhas = [corpo, list(_VIDRO)] + rodas
    return [np.array(l, np.float32) * L for l in linhas]


def _carrinho(img, n, d, sem):
    q = d["quadro"]
    frac = _saida(_u(n, q, d.get("dur", 8)), 1.6)
    if frac <= 0.01:
        return img
    L = float(d.get("comprimento", 320))
    linhas = _carro_linhas(L)
    if d.get("pista"):
        linhas.append(np.array([[-0.12 * L, 0.0], [1.12 * L, 0.0]], np.float32))
    ctr = np.array([L / 2, -0.13 * L], np.float32)                     # centro do carro (meio da altura)
    ang = float(d.get("rot", 0.0))
    gi = d.get("gira")
    if gi:
        ang += float(gi.get("graus", 180.0)) * mv.suavizar_curva(_u(n, gi["de"], max(1, gi["ate"] - gi["de"])), "s", 2.0)
    a = math.radians(ang)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]], np.float32)
    cx, cy = d["centro"]
    sy = -1.0 if d.get("espelha") else 1.0
    out = []
    for l in linhas:
        v = (l - ctr) * np.array([1.0, sy], np.float32)
        v = v @ R.T + np.array([cx, cy], np.float32)
        out.append(_parcial(_ferve(_densa(v, 5.0), sem + len(out), n, d.get("tremor", 0.9)), frac))
    return _riscar(img, out, float(d.get("esp", 6)), cor(d.get("cor")), d.get("alfa", 1.0), d.get("sombra", 0.5))


_CHAVES_PONTO = ("centro", "pos", "de", "para", "ponta")
_CHAVES_LISTA = ("pts", "linha")


def _desloca(d, n):
    """Cópia do desenho deslocada pela posição medida do objeto (`segue` = [[quadro, dx, dy], ...])."""
    ks = sorted(d["segue"])
    qs = [k[0] for k in ks]
    dx = float(np.interp(n, qs, [k[1] for k in ks])); dy = float(np.interp(n, qs, [k[2] for k in ks]))
    e = dict(d)
    for k in _CHAVES_PONTO:
        if k in e:
            e[k] = [e[k][0] + dx, e[k][1] + dy]
    for k in _CHAVES_LISTA:
        if k in e:
            e[k] = [[x + dx, y + dy] for x, y in e[k]]
    if "linhas" in e:
        e["linhas"] = [[[x + dx, y + dy] for x, y in l] for l in e["linhas"]]
    return e


TIPOS = {"escurece": None, "traco": _traco, "seta": _seta, "fluxo": _fluxo, "circulo": _circulo,
         "ventilador": _ventilador, "rotulo": _rotulo, "balao": None, "recorte": None, "proibido": _proibido,
         "cronometro": _cronometro, "numero": _numero, "carrinho": _carrinho}


def aplicar(img, n, p, ctx, camada):
    """Desenha os `desenhos` do plano desta camada ("cena" ou "tela") que estão valendo no quadro n."""
    padrao = "cena" if p.get("tipo") in ("video_clip", "tela_dividida") else "tela"
    for i, d in enumerate(p.get("desenhos", [])):
        if d.get("camada", padrao) != camada:
            continue
        if n < d["quadro"] or n >= d.get("ate", 10 ** 9):
            continue
        sem = int(d.get("semente", 11 + 17 * i))
        if d.get("segue"):
            d = _desloca(d, n)
        t = d["tipo"]
        if t == "escurece":
            img = _escurece(img, n, d)
        elif t == "balao":
            img = _balao(img, n, d, sem, ctx)
        elif t == "recorte":
            img = _recorte(img, n, d, sem, ctx)
        elif t in TIPOS:
            img = TIPOS[t](img, n, d, sem)
        else:
            raise ValueError(f"desenho desconhecido: {t} (ver motor/desenho.py)")
    return img
