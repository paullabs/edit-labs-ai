"""
Família A + objeto real em ação (v12.5) — o recorte de uma foto real (máscara do ferramentas/recorte.swift) faz o
que a fala diz, sobre o canvas claro com piso (look Priming). Cada tipo é um gancho visual diferente.

  salto       o objeto pula por cima de outro (também recorte real), gira no ar e pousa: rola até a decolagem,
              arco com o ápice na palavra do obstáculo, giro de 360° na palavra "girou", sombra que encolhe com a
              altura, linhas de velocidade, poeira e tranco no pouso.
  de_cabeca   o objeto anda de cabeça para baixo sob uma pista desenhada a tinta (hachura acima), setas de ar.
  ventilador  o objeto sobre a pista, um ventilador que gira embaixo dele, setas do ar puxado e setas que
              apertam o carro na pista; na palavra-chave a cena inteira vira de cabeça para baixo e ele não cai.
  jatos       vista de cima: carro desenhado a tinta e N jatos que disparam um a um em volta dele; no fim
              todos juntos e o carro sobe (cresce, a sombra encolhe).

Imagens: nomes de arquivo do projeto (assets/prontos, baixados...), RGBA com alfa (o recorte).
"""
import math

import cv2
import numpy as np

from familia_a import W, H
from familia_a import c5_movimentos as mv
from familia_a import c3_style as st
from familia_a.compor import sobre
from planos import u, _canvas
from planos_noticia import _camera, TINTA_D, AZUL, VERMELHO, _seta, _traco, _camada_traco

FPS = 30


# ------------------------------------------------------------------ peças
def _img(ctx, nome, largura, flip=None):
    def f():
        a = st.escalar(st.carregar(nome), largura=largura)
        if flip == "v":
            a = a[::-1].copy()
        elif flip == "h":
            a = a[:, ::-1].copy()
        return a
    return ctx.cache(("obj", nome, int(largura), flip), f)


def _rot(a, graus):
    if abs(graus) < 0.05:
        return a
    h, w = a.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), graus, 1.0)
    c, s = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * s + w * c) + 2, int(h * c + w * s) + 2
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    return cv2.warpAffine(a, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def _escala_xy(a, sx, sy):
    h, w = a.shape[:2]
    return cv2.resize(a, (max(1, int(w * sx)), max(1, int(h * sy))), interpolation=cv2.INTER_LINEAR)


def _sombra(img, cx, y, larg, forca):
    """Sombra mole no chão: elipse escurece por multiplicação."""
    if forca <= 0.01 or larg < 4:
        return
    rx, ry = larg / 2, max(4.0, larg * 0.07)
    x0, x1 = int(max(0, cx - rx * 1.6)), int(min(W, cx + rx * 1.6))
    y0, y1 = int(max(0, y - ry * 4)), int(min(H, y + ry * 4))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    d = ((xx - cx) / rx) ** 2 + ((yy - y) / ry) ** 2
    m = np.exp(-d * 1.6) * forca
    img[y0:y1, x0:x1] *= (1 - m)[..., None]


def _poeira(img, x, y, t, larg, semente=4):
    """Nuvem de poeira no pouso: bolhas cinzentas que crescem e somem em ~14 quadros."""
    if t < 0 or t > 14:
        return
    rng = np.random.default_rng(semente)
    g = t / 14.0
    for k in range(9):
        dx = (rng.random() - 0.5) * larg * 1.1
        r = (18 + rng.random() * 30) * (0.6 + 1.6 * g)
        cx, cy = x + dx * (0.6 + 0.8 * g), y - 8 - rng.random() * 26 * g
        x0, x1 = int(max(0, cx - r)), int(min(W, cx + r)); y0, y1 = int(max(0, cy - r)), int(min(H, cy + r))
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        m = np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1) ** 1.5 * 0.42 * (1 - g)
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - m[..., None]) + np.array((176.0, 170.0, 162.0)) * m[..., None]


def _linhas_velocidade(img, x, y, w, h, dirx, n, semente=2):
    """Riscos de tinta atrás do objeto que voa (o 'ar' do movimento)."""
    rng = np.random.default_rng(semente + n // 3)
    for k in range(4):
        yy = y - h * 0.3 + k * h * 0.2 + rng.normal(0, 6)
        x0 = x - dirx * (w * 0.55 + 20 + rng.random() * 30)
        L = 90 + rng.random() * 90
        pts = np.stack([np.linspace(x0, x0 - dirx * L, 10), np.full(10, yy)], 1)

        def d(m, ss, pts=pts):
            _traco(m, pts, 5.0, 7 + k, 1.0, ss)
        sobre(img, _camada_traco(d, (90.0, 90.0, 96.0), 0.75))


def _texto_tinta(img, texto, centro, corpo, q, cor=TINTA_D):
    from familia_a import c2_letras as le
    from familia_a import c6_motion as mo
    le.escrever(img, texto, centro=centro, fonte=le.SERIFA, corpo=corpo, cor=cor, contorno=1.0,
                escala=mo.escala_palavra(q / FPS))


# ------------------------------------------------------------------ salto
def salto(n, p, ctx):
    img = _canvas(ctx, p.get("piso", True)).copy()
    chao = p.get("chao", 1330)
    ob, sa = p["obstaculo"], p["saltador"]
    A = _img(ctx, ob["imagem"], ob["largura"])
    if n >= ob.get("entra", p["inicio"]):
        _sombra(img, ob["x"], chao, ob["largura"] * 0.95, 0.38)
        sobre(img, A, ob["x"] - A.shape[1] / 2, chao - A.shape[0] + ob.get("afunda", 10))
    B = _img(ctx, sa["imagem"], sa["largura"], sa.get("flip"))
    bh, bw = B.shape[:2]
    qd, qa, qp = sa["decola"], sa.get("apice", (sa["decola"] + sa["pousa"]) // 2), sa["pousa"]
    xi, xd, xp, xf = sa["x_inicio"], sa["x_decola"], sa["x_pousa"], sa["x_fim"]
    hap = sa.get("altura", 640)
    dirx = -1 if xp < xd else 1
    ang, sx, sy = 0.0, 1.0, 1.0
    if n < qd:                                                   # rola até a decolagem
        t = u(n, p["inicio"], qd)
        x = xi + (xd - xi) * (t ** 1.4)
        yb = chao
        if qd - n <= 4:
            ang = sa.get("empina", 7.0) * dirx * (1 - (qd - n) / 4.0)   # a frente sobe antes do pulo
    elif n < qp:                                                 # no ar: arco com o ápice em qa
        s = float(np.interp(n, [qd, qa, qp], [0.0, 0.5, 1.0]))
        x = xd + (xp - xd) * s
        yb = chao - hap * 4 * s * (1 - s)
        g0, g1 = sa.get("giro_de", qa), sa.get("giro_ate", qp - 3)
        giro = sa.get("giro", 360.0) * mv.suavizar_curva(u(n, g0, g1), "s", 1.6) if n >= g0 else 0.0
        ang = giro * (-dirx) + (8.0 * dirx * (1 - 2 * s) if n < g0 else 0.0)
    else:                                                        # pouso: tranco e desliza até parar
        t = u(n, qp, qp + 18)
        x = xp + (xf - xp) * (1 - (1 - t) ** 2.2)
        yb = chao
        k = n - qp
        if k < 3:
            sx, sy = 1.06, 0.90
        elif k < 6:
            sx, sy = 0.98, 1.03
    alt = chao - yb
    _sombra(img, x, chao, bw * (0.95 - 0.55 * min(1.0, alt / 700.0)), 0.36 * (1 - 0.65 * min(1.0, alt / 700.0)))
    if qd <= n < qp:
        _linhas_velocidade(img, x, yb - bh / 2, bw, bh, dirx, n)
    Bi = _escala_xy(B, sx, sy) if (sx, sy) != (1.0, 1.0) else B
    Bi = _rot(Bi, ang)
    cy = yb - bh * sy / 2 + sa.get("afunda", 10)
    sobre(img, Bi, x - Bi.shape[1] / 2, cy - Bi.shape[0] / 2)
    if n >= qp:
        _poeira(img, x - bw * 0.3, chao, n - qp, bw * 0.45, 4)
        _poeira(img, x + bw * 0.3, chao, n - qp, bw * 0.45, 9)
    img = _camera(img, n, p, (1.0, 1.03), centro=(W / 2, chao - 300))
    if n >= qp and n - qp < 4:                                   # tranco do pouso
        img = mv.camera(img, dx=0.0, dy=(0, 10, -6, 3)[n - qp], zoom=1.0, fundo=(240.0, 240.0, 240.0))
    return img


# ------------------------------------------------------------------ de cabeça para baixo
def _pista(img, y, x0=40, x1=1040, hachura=True, embaixo=False):
    pts = np.stack([np.linspace(x0, x1, 40), np.full(40, float(y))], 1)

    def d(m, ss):
        _traco(m, pts, 9.0, 3, 0.8, ss)
        if hachura:
            for k, x in enumerate(np.arange(x0 + 10, x1, 38)):
                sgn = 1 if embaixo else -1
                q = np.array([[x, y + sgn * 4], [x + 22, y + sgn * 30]])
                _traco(m, q, 4.0, 20 + k, 0.6, ss)
    sobre(img, _camada_traco(d, TINTA_D))


def de_cabeca(n, p, ctx):
    img = _canvas(ctx, False).copy()
    teto = p.get("teto", 700)
    _pista(img, teto, hachura=True, embaixo=False)
    sa = p["movel"]
    B = _img(ctx, sa["imagem"], sa["largura"], "v")              # de cabeça para baixo, ainda de frente para a esquerda
    t = u(n, p["inicio"], p["fim"])
    x = sa["x_de"] + (sa["x_ate"] - sa["x_de"]) * mv.suavizar_curva(t, "s", 1.2)
    y = teto + B.shape[0] / 2 - sa.get("afunda", 14)
    sobre(img, B, x - B.shape[1] / 2, y - B.shape[0] / 2)
    q_ar = p.get("quadro_ar")
    if q_ar is not None and n >= q_ar:                           # o ar puxado: setas entre a pista e o carro
        g = min(1.0, (n - q_ar) / 6.0)
        for k, dx in enumerate((-0.3, 0.0, 0.3)):
            xs = x + dx * B.shape[1]
            _seta(img, (xs, teto + B.shape[0] * 0.95), (xs, teto + B.shape[0] * 0.95 + 140 * g), 1.0, AZUL, 0.0, 6.0, 30 + k, 30)
    return _camera(img, n, p, (1.0, 1.05), centro=(W / 2, teto + 200))


# ------------------------------------------------------------------ ventilador
def _ventilador(tam, t, cor=TINTA_D):
    """Ventilador visto de frente: aro, cubo e três pás que giram (t em quadros). RGBA alfa 0-1."""
    s = 4
    w = int(tam)
    m = np.zeros((w * s, w * s), np.float32)
    c = w * s / 2
    cv2.circle(m, (int(c), int(c)), int(w * s * 0.47), 1.0, int(w * s * 0.045), cv2.LINE_AA)
    a0 = t * 47.0                                                # graus por quadro (a 10 qps vira "piscando" de propósito)
    for k in range(3):
        ang = math.radians(a0 + k * 120)
        pts = []
        for f, r in ((-0.30, 0.08), (-0.22, 0.40), (0.00, 0.43), (0.25, 0.30), (0.10, 0.08)):
            aa = ang + f
            pts.append((c + math.cos(aa) * r * w * s, c + math.sin(aa) * r * w * s))
        cv2.fillPoly(m, [np.int32(pts)], 1.0, cv2.LINE_AA)
    cv2.circle(m, (int(c), int(c)), int(w * s * 0.08), 1.0, -1, cv2.LINE_AA)
    m = cv2.resize(m, (w, w), interpolation=cv2.INTER_AREA)
    lay = np.zeros((w, w, 4), np.float32)
    lay[..., :3] = cor
    lay[..., 3] = m
    return lay


def ventilador(n, p, ctx):
    img = _canvas(ctx, False).copy()
    pista = p.get("pista", 1150)
    _pista(img, pista, hachura=True, embaixo=True)
    sa = p["movel"]
    B = _img(ctx, sa["imagem"], sa["largura"])
    x = sa.get("x", W / 2)
    sobre(img, B, x - B.shape[1] / 2, pista - B.shape[0] + sa.get("afunda", 14))
    qv = p.get("quadro_ventilador", p["inicio"])
    if n >= qv:                                                  # o ventilador fica embaixo do carro, rente à pista
        tam = p.get("tam_ventilador", 170)
        lay = _ventilador(tam, n - qv)
        sobre(img, lay, x - tam / 2, pista - tam * 0.62)
    qa = p.get("quadro_ar")
    if qa is not None and n >= qa:                               # o ar puxado para dentro do ventilador
        g = min(1.0, (n - qa) / 6.0)
        for k, dx in enumerate((-300, -170, 170, 300)):            # o ar entra pelos lados, rente à pista, até o ventilador
            x0 = x + dx
            _seta(img, (x0, pista - 40), (x0 - dx * 0.55 * g, pista - 60), 1.0, AZUL, 0.18 * (1 if dx > 0 else -1), 6.0, 40 + k, 30)
    qg = p.get("quadro_gruda")
    if qg is not None and n >= qg:                               # a força que aperta o carro na pista
        g = min(1.0, (n - qg) / 5.0)
        for k, dx in enumerate((-0.28, 0.0, 0.28)):
            xs = x + dx * B.shape[1]
            y0 = pista - B.shape[0] - 230
            _seta(img, (xs, y0), (xs, y0 + 170 * g), 1.0, VERMELHO, 0.0, 9.0, 50 + k, 44)
    img = _camera(img, n, p, (1.0, 1.05), centro=(W / 2, pista - 200))
    vira = p.get("vira")                                         # a cena inteira vira: de cabeça para baixo e não cai
    if vira is not None and n >= vira:
        g = mv.suavizar_curva(min(1.0, (n - vira) / 9.0), "s", 1.6)
        M = cv2.getRotationMatrix2D((W / 2, H / 2), 180.0 * g, 1.0 - 0.12 * math.sin(math.pi * g))
        img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(240.0, 240.0, 240.0))
    return img


# ------------------------------------------------------------------ jatos (vista de cima)
def _carro_topo(w, h):
    s = 4
    m = np.zeros((h * s, w * s), np.float32)
    r = int(w * s * 0.32)
    cv2.rectangle(m, (r, 0), (w * s - r, h * s), 1.0, -1)
    cv2.rectangle(m, (0, r), (w * s, h * s - r), 1.0, -1)
    for cx, cy in ((r, r), (w * s - r, r), (r, h * s - r), (w * s - r, h * s - r)):
        cv2.circle(m, (cx, cy), r, 1.0, -1, cv2.LINE_AA)
    vid = np.zeros_like(m)                                      # para-brisa e vidro de trás, vazados
    cv2.rectangle(vid, (int(w * s * 0.18), int(h * s * 0.24)), (int(w * s * 0.82), int(h * s * 0.36)), 1.0, -1)
    cv2.rectangle(vid, (int(w * s * 0.22), int(h * s * 0.72)), (int(w * s * 0.78), int(h * s * 0.80)), 1.0, -1)
    m = np.clip(m - vid * 0.75, 0, 1)
    rodas = np.zeros_like(m)                                     # quatro rodas para ler como carro
    for fx, fy in ((-0.04, 0.17), (0.92, 0.17), (-0.04, 0.70), (0.92, 0.70)):
        cv2.rectangle(rodas, (int(w * s * fx), int(h * s * fy)), (int(w * s * (fx + 0.12)), int(h * s * (fy + 0.15))), 1.0, -1)
    m = np.clip(m + rodas, 0, 1)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA)


def jatos(n, p, ctx):
    img = _canvas(ctx, False).copy()
    cx, cy = p.get("centro", (W / 2, 900))
    cw, ch = p.get("tamanho", (300, 560))
    N = p.get("n", 10)
    q0, passo = p["quadro"], p.get("passo", 3)
    sobe = p.get("sobe")
    esc = 1.0
    if sobe is not None and n >= sobe:
        esc = 1.0 + 0.22 * mv.suavizar_curva(min(1.0, (n - sobe) / 12.0), "saida", 2.0)
    # sombra que encolhe quando ele sobe
    _sombra(img, cx + 30 * (esc - 1) * 4, cy + ch * 0.52, cw * 1.3 / esc, 0.30 / esc)
    m = ctx.cache(("topo", cw, ch), lambda: _carro_topo(cw, ch))
    if esc != 1.0:
        m = cv2.resize(m, (int(cw * esc), int(ch * esc)), interpolation=cv2.INTER_LINEAR)
    lay = np.zeros(m.shape + (4,), np.float32)
    lay[..., :3] = p.get("cor", (190.0, 34.0, 40.0))
    lay[..., 3] = m
    sobre(img, lay, cx - m.shape[1] / 2, cy - m.shape[0] / 2)
    # N bocais em volta (perímetro) e o jato de cada um: cone cinza que cresce e some
    for k in range(N):
        a = -math.pi / 2 + k * 2 * math.pi / N
        bx, by = cx + math.cos(a) * cw * 0.52 * esc, cy + math.sin(a) * ch * 0.52 * esc
        qk = q0 + passo * k
        if n < qk:
            continue
        cv2.circle(img, (int(bx), int(by)), 11, TINTA_D, -1, cv2.LINE_AA)
        todos = sobe is not None and n >= sobe
        t = (n - qk) if not todos else (n - sobe) % 9
        if t <= 8 or todos:
            g = min(1.0, t / 8.0)
            L = 80 + 120 * g
            ex, ey = bx + math.cos(a) * L, by + math.sin(a) * L
            r = 14 + 44 * g
            x0, x1 = int(max(0, min(bx, ex) - r)), int(min(W, max(bx, ex) + r))
            y0, y1 = int(max(0, min(by, ey) - r)), int(min(H, max(by, ey) + r))
            yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
            vx, vy = ex - bx, ey - by
            tt = np.clip(((xx - bx) * vx + (yy - by) * vy) / (vx * vx + vy * vy), 0, 1)
            dist = np.hypot(xx - (bx + tt * vx), yy - (by + tt * vy))
            rad = 6 + tt * r
            mm = np.clip(1 - dist / rad, 0, 1) ** 0.9 * (0.85 * (1 - 0.45 * g)) * (1 - tt * 0.4)
            img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - mm[..., None]) + np.array((92.0, 128.0, 170.0)) * mm[..., None]
    for tx in p.get("textos", []):
        if n >= tx["quadro"]:
            _texto_tinta(img, tx["texto"], tuple(tx["pos"]), tx.get("corpo", 130), n - tx["quadro"], tuple(tx.get("cor", TINTA_D)))
    return _camera(img, n, p, (1.0, 1.05), centro=(cx, cy))


TIPOS_OBJETO = {"salto": salto, "de_cabeca": de_cabeca, "ventilador": ventilador, "jatos": jatos}
