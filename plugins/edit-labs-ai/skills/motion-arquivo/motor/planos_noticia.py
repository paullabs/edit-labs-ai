"""
Planos v11 — a noticia explicada (IA contra IA, dados, "viralizou, e verdade?").

Mesma gramatica da Familia A: a camera anda o plano inteiro, cada palavra dita vira um
evento no 1o degrau da grade (10 qps) e o corte se esconde no movimento. Estes tipos
desenham o que a noticia NOMEIA — sem logotipo de marca: nome de empresa so em tipografia.

    ranking     lista de posicoes (radar / canvas): a linha entra pela direita, ultrapassa a outra
    terminal    janela escura com texto monoespacado digitado (ranking de teste de programacao)
    podio       tres blocos no piso do canvas; a etiqueta cai no bloco quando a fala diz a posicao
    barras      2-3 barras que crescem com o numero contando; uma pode mudar de valor depois
    centena     10 x 10 (pessoas ou quadrados); grupos mudam de cor na batida; anel no que importa
    pizzas      uma ou mais pizzas; cada uma com valor unico ou fatias (candidatos), e o "fora"
    celular     telefone desenhado: barra de status (modo aviao), conversa, download, canal, carimbo
    icones      1-3 icones a tinta (nota, wifi, nuvem, cadeado, jornal, terminal, pessoa...) com
                rotulo, certo, xis e risco; setas entre eles; divisor de dois paineis
    semana      tira de calendario na parede: o dia da fala ganha o circulo, os anteriores o X
    linha_no_papel  uma linha que se monta palavra a palavra (PROMESSA ≠ ENTREGA)
    botao_cta   o botao "Seguir" com o cursor REAL do sistema clicando: vira "Seguindo"
"""
import math
import re
from pathlib import Path

import numpy as np
import cv2
from familia_a import W, H
from familia_a import c1_background as bg, c2_letras as le, c3_style as st
from familia_a import c4_filtro as fi, c5_movimentos as mv, c6_motion as mo
from familia_a.compor import sobre
from planos import (FPS, TINTA_D, VERMELHO, FOLHA, u, cam, zoom_em, assenta, _fundo, _parede, _canvas,
                    _sombra_alfa, _com_sombra, _colar_mascara, _icone_pessoa, _caixa_larga, _tinta_carimbo,
                    _cursor_sistema, _rot_rgba)

AZUL = tuple(float(c) for c in st.AZUL_UI)
CINZA_PECA = (196.0, 196.0, 202.0)
BRANCO_UI = (248.0, 248.0, 250.0)
MONO = next((f for f in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf") if Path(f).exists()), le.INTER)
CORES = {"tinta": TINTA_D, "azul": AZUL, "vermelho": VERMELHO, "cinza": (150.0, 150.0, 156.0),
         "claro": CINZA_PECA, "branco": BRANCO_UI, "verde": (64.0, 140.0, 92.0)}


def _cor(c, padrao=TINTA_D):
    if c is None:
        return padrao
    if isinstance(c, str):
        return CORES.get(c, padrao)
    return tuple(float(v) for v in c)


# --------------------------------------------------------------------- auxiliares
def _camera(img, n, p, empurra=(1.0, 1.04), centro=(W / 2, H / 2), revela=0.10):
    """Camera do plano. Com chaves p["camera"] = [{"quadro", "ancora": [x, y], "z"}] a camera
    viaja em S entre elas (a ancora vai para o centro da tela); sem chaves, revelacao de
    entrada (1 + revela -> 1) e empurrao lento em torno do centro."""
    fundo = tuple(float(v) for v in img[27, 27, :3])
    ks = p.get("camera")
    if ks:
        ks = sorted(ks, key=lambda k: k["quadro"])
        if n <= ks[0]["quadro"]:
            anc, z = ks[0]["ancora"], ks[0]["z"]
        elif n >= ks[-1]["quadro"]:
            anc, z = ks[-1]["ancora"], ks[-1]["z"]
        else:
            for a, b in zip(ks, ks[1:]):
                if a["quadro"] <= n <= b["quadro"]:
                    t = mv.suavizar_curva(u(n, a["quadro"], b["quadro"]), "s", 2.2)
                    anc = [a["ancora"][0] + (b["ancora"][0] - a["ancora"][0]) * t,
                           a["ancora"][1] + (b["ancora"][1] - a["ancora"][1]) * t]
                    z = a["z"] + (b["z"] - a["z"]) * t
                    break
        return cam(img, z=z, dx=z * (W / 2 - anc[0]), dy=z * (H / 2 - anc[1]), fundo=fundo)
    q = n - p["inicio"]
    z = assenta(q, p.get("revela", revela), 8.0) * mv.entre(empurra[0], empurra[1], u(n, p["inicio"], p["fim"]))
    return zoom_em(img, z, tuple(p.get("centro_camera", centro)), fundo=fundo)


def _ret_arred(w, h, r, ss=4):
    """Mascara (h, w) 0-1 de um retangulo de cantos redondos, com antisserrilhado."""
    w, h = max(2, int(round(w))), max(2, int(round(h)))
    W2, H2 = w * ss, h * ss
    R2 = int(max(1, min(r * ss, W2 / 2 - 1, H2 / 2 - 1)))
    m = np.zeros((H2, W2), np.uint8)
    cv2.rectangle(m, (R2, 0), (W2 - R2 - 1, H2 - 1), 255, -1)
    cv2.rectangle(m, (0, R2), (W2 - 1, H2 - R2 - 1), 255, -1)
    for cx, cy in ((R2, R2), (W2 - R2 - 1, R2), (R2, H2 - R2 - 1), (W2 - R2 - 1, H2 - R2 - 1)):
        cv2.circle(m, (cx, cy), R2, 255, -1, cv2.LINE_AA)
    return cv2.resize(m, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def _rgba(m, cor):
    lay = np.zeros(m.shape + (4,), np.float32)
    lay[..., :3] = cor
    lay[..., 3] = m
    return lay


def _escalar_rgba(lay, e):
    if e >= 0.999:
        return lay
    return cv2.resize(lay, (max(1, int(lay.shape[1] * e)), max(1, int(lay.shape[0] * e))), interpolation=cv2.INTER_AREA)


def _colar_centro(img, lay, cx, cy, e=1.0, sombra=None):
    """Cola uma camada RGBA (alfa 0-1) centrada em (cx, cy), com escala e sombra mole opcional."""
    l = _escalar_rgba(lay, e)
    if sombra:
        sh, pad = _sombra_alfa(l, sombra.get("desloc", (14, 24)), sombra.get("blur", 16.0), sombra.get("forca", 0.35))
        sobre(img, sh, cx - l.shape[1] / 2 - pad, cy - l.shape[0] / 2 - pad)
    sobre(img, l, cx - l.shape[1] / 2, cy - l.shape[0] / 2)
    return img


def _largura(texto, fonte, corpo, peso=None, tracking=0.0):
    f = le._fonte(fonte, int(round(corpo * le.SS)), peso)
    return (sum(f.getlength(c) for c in texto) + tracking * le.SS * max(0, len(texto) - 1)) / le.SS


def _escreve(img, texto, x, y, fonte=le.INTER, corpo=40, peso=None, cor=TINTA_D, alfa=1.0, alinha="esq", tracking=0.0):
    """Texto com o TOPO DA CAIXA DA FONTE em y (linhas de interface alinham pela linha de base)."""
    if not texto:
        return img
    m, (ox, oy) = le.mascara(texto, fonte, corpo, peso, 0.0, tracking)
    if alinha != "esq":
        lw = _largura(texto, fonte, corpo, peso, tracking)
        x = x - (lw if alinha == "dir" else lw / 2)
    le.tingir(img, m, x - ox, y - oy, cor, alfa)
    return img


def _quebrar(texto, fonte, corpo, peso, larg):
    linhas, atual = [], ""
    for w in texto.split():
        t = (atual + " " + w).strip()
        if atual and _largura(t, fonte, corpo, peso) > larg:
            linhas.append(atual)
            atual = w
        else:
            atual = t
    if atual:
        linhas.append(atual)
    return linhas


def _formata(texto, v):
    """Troca o 1o numero do texto pelo valor v (mesmas casas decimais, virgula e milhar com ponto)."""
    m = re.search(r"\d[\d.]*(?:,\d+)?", texto)
    if not m:
        return texto
    s = m.group(0)
    dec = len(s.split(",")[1]) if "," in s else 0
    milhar = "." in s.split(",")[0]
    num = f"{v:,.{dec}f}" if milhar else f"{v:.{dec}f}"
    num = num.replace(",", "§").replace(".", ",").replace("§", ".")
    return texto[:m.start()] + num + texto[m.end():]


def _cresce(n, q, dur=12, p=3.0):
    if n < q:
        return 0.0
    return 1 - (1 - min(1.0, (n - q + 3) / float(dur))) ** p


def _traco(m, pts, esp, semente=3, tremor=1.2, ss=4):
    """Linha a mao (mascara uint8 em supersample ss): polilinha com tremor leve."""
    rng = np.random.default_rng(semente)
    pts = np.asarray(pts, np.float32)
    if len(pts) < 2:
        return m
    pts = pts + rng.normal(0, tremor, pts.shape).astype(np.float32)
    cv2.polylines(m, [np.int32(pts * ss)], False, 255, max(1, int(esp * ss)), cv2.LINE_AA)
    return m


def _camada_traco(desenho, cor, alfa=1.0):
    """Roda `desenho(m)` numa mascara do quadro em supersample 4 e devolve a camada RGBA (H, W)."""
    ss = 4
    m = np.zeros((H * ss // 2, W * ss // 2), np.uint8)       # 2x na mascara (memoria), 4x nas coordenadas
    desenho(m, 2)
    a = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0 * alfa
    return _rgba(a, cor)


def _circulo_mao(img, centro, rx, ry, frac, cor, esp=7.0, semente=4):
    """Circulo desenhado a mao (fecha passando um pouco do inicio), ate a fracao `frac`."""
    if frac <= 0.02:
        return img
    rng = np.random.default_rng(semente)
    a0 = -2.3
    k = 90
    ang = a0 + np.linspace(0, frac * 2 * math.pi * 1.08, k)
    ruido = np.cumsum(rng.normal(0, 0.012, k)); ruido -= np.linspace(0, ruido[-1], k) * 0.4
    r = 1 + ruido
    pts = np.stack([centro[0] + rx * r * np.cos(ang), centro[1] + ry * r * np.sin(ang)], 1)

    def d(m, ss):
        cv2.polylines(m, [np.int32(pts * ss)], False, 255, max(1, int(esp * ss)), cv2.LINE_AA)
    return sobre(img, _camada_traco(d, cor))


def _xis_mao(img, centro, r, frac, cor, esp=9.0, semente=6):
    """X a mao (duas pernadas): a primeira na metade inicial de frac, a segunda na outra."""
    if frac <= 0.02:
        return img
    x, y = centro
    a = [(x - r, y - r), (x + r, y + r)]
    b = [(x + r, y - r), (x - r, y + r)]
    f1 = min(1.0, frac * 2); f2 = max(0.0, frac * 2 - 1)

    def d(m, ss):
        for (p0, p1), f, s in ((a, f1, semente), (b, f2, semente + 1)):
            if f > 0.02:
                p1x = p0[0] + (p1[0] - p0[0]) * f; p1y = p0[1] + (p1[1] - p0[1]) * f
                pts = np.stack([np.linspace(p0[0], p1x, 12), np.linspace(p0[1], p1y, 12)], 1)
                _traco(m, pts, esp, s, 0.9, ss)
    return sobre(img, _camada_traco(d, cor))


def _seta(img, de, para, g, cor=TINTA_D, curva=0.12, esp=6.0, semente=5, ponta=40):
    if g <= 0.05:
        return img
    (x0, y0), (x1, y1) = de, para
    return sobre(img, st.seta_mao((x0, y0), (x0 + (x1 - x0) * g, y0 + (y1 - y0) * g), curva=curva, esp=esp,
                                  cor=tuple(cor), ponta=ponta, semente=semente))


def _selo(tipo, r):
    """Selo redondo: 'certo' (azul com o tique) ou 'xis' (vermelho com o X)."""
    d = int(2 * r + 4)
    ss = 4
    big = np.zeros((d * ss, d * ss), np.uint8)
    cv2.circle(big, (d * ss // 2, d * ss // 2), int(r * ss), 255, -1, cv2.LINE_AA)
    m = cv2.resize(big, (d, d), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    lay = _rgba(m, AZUL if tipo == "certo" else VERMELHO)
    g = np.zeros((d * ss, d * ss), np.uint8)
    c = d * ss / 2
    if tipo == "certo":
        pts = np.array([[c - 0.48 * r * ss, c + 0.02 * r * ss], [c - 0.12 * r * ss, c + 0.38 * r * ss],
                        [c + 0.52 * r * ss, c - 0.36 * r * ss]], np.int32)
        cv2.polylines(g, [pts], False, 255, int(0.20 * r * ss), cv2.LINE_AA)
    else:
        k = 0.40 * r * ss
        cv2.line(g, (int(c - k), int(c - k)), (int(c + k), int(c + k)), 255, int(0.20 * r * ss), cv2.LINE_AA)
        cv2.line(g, (int(c + k), int(c - k)), (int(c - k), int(c + k)), 255, int(0.20 * r * ss), cv2.LINE_AA)
    ga = cv2.resize(g, (d, d), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    lay[..., :3] = lay[..., :3] * (1 - ga[..., None]) + np.array((250.0, 250.0, 252.0)) * ga[..., None]
    return lay


def _titulo(img, n, p, y, escuro=False):
    tit = p.get("titulo")
    if tit and n >= tit.get("quadro", p["inicio"]):
        e = mo.escala_palavra((n - tit.get("quadro", p["inicio"])) / FPS)
        le.escrever(img, tit["texto"], centro=(W / 2, tit.get("y", y)), fonte=le.INTER, corpo=tit.get("corpo", 40) * e,
                    cor=(150.0, 150.0, 158.0) if escuro else (104.0, 104.0, 112.0), peso=800, tracking=4.0)
    return img


# ====================================================================== icones desenhados
def _mascara_ss(w, h, desenho, ss=4):
    big = np.zeros((int(h) * ss, int(w) * ss), np.uint8)
    desenho(big, ss)
    return cv2.resize(big, (int(w), int(h)), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def _icone(nome, tam, cor=TINTA_D, t=0):
    """Icone desenhado (RGBA 0-1). `tam` = largura; `t` = quadros desde a entrada (relogio gira)."""
    tam = int(tam)
    cor = tuple(float(c) for c in cor)
    if nome == "pessoa":
        return _rgba(_icone_pessoa(int(tam * 0.76), tam), cor)
    if nome == "wifi":
        w, h = tam, int(tam * 0.78)

        def d(m, s):
            cx, cy = w / 2 * s, h * 0.92 * s
            for r in (0.18, 0.34, 0.50):
                cv2.ellipse(m, (int(cx), int(cy)), (int(r * w * s), int(r * w * s)), 0, 222, 318, 255,
                            int(0.085 * w * s), cv2.LINE_AA)
            cv2.circle(m, (int(cx), int(cy - 0.02 * w * s)), int(0.065 * w * s), 255, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "sinal":
        w, h = tam, int(tam * 0.8)

        def d(m, s):
            for k in range(4):
                x0 = (0.06 + k * 0.24) * w; hh = (0.25 + k * 0.25) * h
                cv2.rectangle(m, (int(x0 * s), int((h - hh) * s)), (int((x0 + 0.16 * w) * s), int(h * s)), 255, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "nuvem":
        w, h = tam, int(tam * 0.66)

        def cheia(m, s):
            for (x, y, r) in ((0.30, 0.64, 0.19), (0.52, 0.45, 0.26), (0.74, 0.64, 0.18)):
                cv2.circle(m, (int(x * w * s), int(y * h * s)), int(r * w * s), 255, -1, cv2.LINE_AA)
            cv2.rectangle(m, (int(0.30 * w * s), int(0.60 * h * s)), (int(0.75 * w * s), int(0.93 * h * s)), 255, -1)
            cv2.circle(m, (int(0.30 * w * s), int(0.74 * h * s)), int(0.19 * h * s), 255, -1, cv2.LINE_AA)
            cv2.circle(m, (int(0.75 * w * s), int(0.74 * h * s)), int(0.19 * h * s), 255, -1, cv2.LINE_AA)
        m = _mascara_ss(w, h, cheia)
        k = max(3, int(tam * 0.065)) | 1
        dentro = cv2.erode(m, np.ones((k, k), np.uint8))
        return _rgba(np.clip(m - dentro, 0, 1), cor)
    if nome == "cadeado":
        w, h = tam, int(tam * 1.15)

        def d(m, s):
            cv2.ellipse(m, (int(0.5 * w * s), int(0.46 * h * s)), (int(0.24 * w * s), int(0.27 * h * s)), 0, 180, 360,
                        255, int(0.09 * w * s), cv2.LINE_AA)
            x0, y0, x1, y1 = 0.14 * w, 0.44 * h, 0.86 * w, 0.97 * h
            r = 0.08 * w
            mm = _ret_arred((x1 - x0) * s, (y1 - y0) * s, r * s, 1)
            m[int(y0 * s):int(y0 * s) + mm.shape[0], int(x0 * s):int(x0 * s) + mm.shape[1]] = np.maximum(
                m[int(y0 * s):int(y0 * s) + mm.shape[0], int(x0 * s):int(x0 * s) + mm.shape[1]], (mm * 255).astype(np.uint8))
            cv2.circle(m, (int(0.5 * w * s), int(0.66 * h * s)), int(0.075 * w * s), 0, -1, cv2.LINE_AA)
            cv2.rectangle(m, (int(0.465 * w * s), int(0.66 * h * s)), (int(0.535 * w * s), int(0.82 * h * s)), 0, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "relogio":
        w = h = tam

        def d(m, s):
            c = (int(w / 2 * s), int(h / 2 * s))
            cv2.circle(m, c, int(0.44 * w * s), 255, int(0.07 * w * s), cv2.LINE_AA)
            for k in range(12):
                a = k * math.pi / 6
                r0, r1 = 0.30 * w, 0.36 * w
                cv2.line(m, (int(c[0] + r0 * s * math.cos(a)), int(c[1] + r0 * s * math.sin(a))),
                         (int(c[0] + r1 * s * math.cos(a)), int(c[1] + r1 * s * math.sin(a))), 255, int(0.03 * w * s), cv2.LINE_AA)
            am = -math.pi / 2 + (t // 3) * math.pi / 4
            ah = -math.pi / 2 + 1.1 + (t // 3) * math.pi / 48
            cv2.line(m, c, (int(c[0] + 0.30 * w * s * math.cos(am)), int(c[1] + 0.30 * w * s * math.sin(am))), 255,
                     int(0.05 * w * s), cv2.LINE_AA)
            cv2.line(m, c, (int(c[0] + 0.19 * w * s * math.cos(ah)), int(c[1] + 0.19 * w * s * math.sin(ah))), 255,
                     int(0.06 * w * s), cv2.LINE_AA)
            cv2.circle(m, c, int(0.05 * w * s), 255, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "engrenagem":
        w = h = tam

        def d(m, s):
            c = (int(w / 2 * s), int(h / 2 * s))
            cv2.circle(m, c, int(0.33 * w * s), 255, -1, cv2.LINE_AA)
            for k in range(8):
                a = k * math.pi / 4
                pts = []
                for da, rr in ((-0.20, 0.30), (-0.13, 0.46), (0.13, 0.46), (0.20, 0.30)):
                    pts.append([c[0] + rr * w * s * math.cos(a + da), c[1] + rr * w * s * math.sin(a + da)])
                cv2.fillConvexPoly(m, np.int32(pts), 255, cv2.LINE_AA)
            cv2.circle(m, c, int(0.13 * w * s), 0, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "aviao":
        w = h = tam

        def d(m, s):
            P = lambda x, y: [int(x * w * s), int(y * h * s)]
            corpo = [P(0.47, 0.05), P(0.53, 0.05), P(0.56, 0.12), P(0.56, 0.86), P(0.53, 0.95), P(0.47, 0.95),
                     P(0.44, 0.86), P(0.44, 0.12)]
            asa = [P(0.44, 0.38), P(0.56, 0.38), P(0.96, 0.58), P(0.96, 0.66), P(0.56, 0.56), P(0.44, 0.56),
                   P(0.04, 0.66), P(0.04, 0.58)]
            cauda = [P(0.45, 0.80), P(0.55, 0.80), P(0.72, 0.92), P(0.72, 0.97), P(0.55, 0.92), P(0.45, 0.92),
                     P(0.28, 0.97), P(0.28, 0.92)]
            for poly in (corpo, asa, cauda):
                cv2.fillPoly(m, [np.int32(poly)], 255, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "jornal":
        w, h = tam, int(tam * 1.25)
        f = np.empty((h, w, 3), np.float32); f[:] = (242.0, 240.0, 234.0)
        k = w / 400.0
        cv2.rectangle(f, (int(24 * k), int(30 * k)), (w - int(24 * k), int(92 * k)), TINTA_D, -1)
        le.escrever(f, "NOTÍCIAS", centro=(w / 2, 61 * k), fonte=le.SERIFA, corpo=58 * k, cor=(242.0, 240.0, 234.0))
        cv2.rectangle(f, (int(24 * k), int(112 * k)), (w - int(24 * k), int(132 * k)), (60.0, 56.0, 58.0), -1)
        cv2.rectangle(f, (int(24 * k), int(144 * k)), (w - int(100 * k), int(164 * k)), (60.0, 56.0, 58.0), -1)
        cv2.rectangle(f, (int(24 * k), int(186 * k)), (int(196 * k), int(300 * k)), (176.0, 174.0, 170.0), -1)
        y = 186 * k
        while y < h - 30 * k:
            x0 = 212 * k if y < 306 * k else 24 * k
            cv2.rectangle(f, (int(x0), int(y)), (w - int(24 * k), int(y + 8 * k)), (168.0, 166.0, 162.0), -1)
            y += 22 * k
        cv2.rectangle(f, (0, 0), (w - 1, h - 1), (120.0, 118.0, 116.0), max(1, int(2 * k)))
        lay = np.zeros((h, w, 4), np.float32); lay[..., :3] = f; lay[..., 3] = 1.0
        return _rot_rgba(lay, -4.0)
    if nome == "terminal":
        w, h = tam, int(tam * 0.74)
        m = _ret_arred(w, h, 0.06 * w)
        lay = _rgba(m, (34.0, 34.0, 40.0))
        bar = int(0.13 * h)
        lay[:bar, :, :3] = (62.0, 62.0, 70.0)
        for k in range(3):
            cv2.circle(lay, (int(0.07 * w + k * 0.055 * w), bar // 2), int(0.018 * w), (130.0, 130.0, 140.0, 1.0), -1, cv2.LINE_AA)
        img = lay[..., :3]
        corpo = 0.20 * h
        _escreve(img, ">_", 0.10 * w, 0.40 * h, MONO, corpo, None, (226.0, 226.0, 232.0))
        lay[..., :3] = img
        return lay
    if nome == "imagem":
        w, h = tam, int(tam * 0.8)
        m = _ret_arred(w, h, 0.07 * w)
        lay = _rgba(m, (214.0, 214.0, 220.0))
        tri = lambda pts: cv2.fillPoly(lay, [np.int32(pts)], (150.0, 150.0, 160.0, 1.0), cv2.LINE_AA)
        tri([[0.10 * w, 0.84 * h], [0.40 * w, 0.40 * h], [0.66 * w, 0.84 * h]])
        tri([[0.44 * w, 0.84 * h], [0.66 * w, 0.54 * h], [0.90 * w, 0.84 * h]])
        cv2.circle(lay, (int(0.74 * w), int(0.28 * h)), int(0.08 * w), (170.0, 170.0, 180.0, 1.0), -1, cv2.LINE_AA)
        lay[..., 3] = np.minimum(lay[..., 3], m)
        return lay
    if nome == "celular":
        w, h = tam, int(tam * 1.9)
        m = _ret_arred(w, h, 0.17 * w)
        lay = _rgba(m, (30.0, 30.0, 34.0))
        b = int(0.06 * w)
        mt = _ret_arred(w - 2 * b, h - 2 * b, 0.13 * w)
        reg = lay[b:b + mt.shape[0], b:b + mt.shape[1], :3]
        reg[:] = reg * (1 - mt[..., None]) + np.array((236.0, 236.0, 240.0)) * mt[..., None]
        pil = _ret_arred(0.30 * w, 0.06 * w, 0.03 * w)
        y0 = int(b + 0.03 * h); x0 = int(w / 2 - pil.shape[1] / 2)
        reg2 = lay[y0:y0 + pil.shape[0], x0:x0 + pil.shape[1], :3]
        reg2[:] = reg2 * (1 - pil[..., None]) + np.array((30.0, 30.0, 34.0)) * pil[..., None]
        return lay
    if nome == "nota":
        return _nota(tam)
    if nome in ("camara", "senado"):                     # a cuia e a cupula do Congresso (o predio no lugar do nome)
        from planos import _predio
        return _predio(nome, tam, int(tam * 0.57), cor)
    if nome == "urna_tecla":
        w, h = tam, int(tam * 0.5)
        m = _ret_arred(w, h, 0.08 * w)
        lay = _rgba(m, (250.0, 250.0, 250.0))
        aro = np.clip(m - cv2.erode(m, np.ones((5, 5), np.uint8)), 0, 1)
        lay[..., :3] = lay[..., :3] * (1 - aro[..., None]) + np.array((120.0, 120.0, 126.0)) * aro[..., None]
        img = np.ascontiguousarray(lay[..., :3])
        le.escrever(img, "BRANCO", centro=(w / 2, h / 2), fonte=le.INTER, corpo=0.16 * w, cor=(40.0, 40.0, 44.0), peso=800)
        lay[..., :3] = img
        return lay
    if nome == "robo":                                   # robô de atendimento: cabeça, antena, olhos e boca vazados
        w, h = tam, int(tam * 0.92)

        def d(m, s):
            cv2.line(m, (int(0.50 * w * s), int(0.04 * h * s)), (int(0.50 * w * s), int(0.20 * h * s)), 255,
                     max(1, int(0.05 * w * s)), cv2.LINE_AA)
            cv2.circle(m, (int(0.50 * w * s), int(0.06 * h * s)), int(0.065 * w * s), 255, -1, cv2.LINE_AA)
            cab = (_ret_arred(0.86 * w * s, 0.66 * h * s, 0.16 * w * s) * 255).astype(np.uint8)
            y0, x0 = int(0.22 * h * s), int(0.07 * w * s)
            m[y0:y0 + cab.shape[0], x0:x0 + cab.shape[1]] = np.maximum(m[y0:y0 + cab.shape[0], x0:x0 + cab.shape[1]], cab)
            for xx in (0.33, 0.67):
                cv2.circle(m, (int(xx * w * s), int(0.50 * h * s)), int(0.085 * w * s), 0, -1, cv2.LINE_AA)
            cv2.rectangle(m, (int(0.33 * w * s), int(0.68 * h * s)), (int(0.67 * w * s), int(0.74 * h * s)), 0, -1)
            for xx in (0.02, 0.92):
                cv2.rectangle(m, (int(xx * w * s), int(0.42 * h * s)), (int((xx + 0.06) * w * s), int(0.62 * h * s)), 255, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "loja":                                   # fachada de loja: toldo de ondinhas, vitrine e porta
        w, h = tam, int(tam * 0.92)

        def d(m, s):
            lw = max(2, int(0.045 * w * s))
            cv2.rectangle(m, (int(0.06 * w * s), int(0.08 * h * s)), (int(0.94 * w * s), int(0.30 * h * s)), 255, -1)
            for k in range(5):                           # a borda do toldo em meias-luas
                cx = (0.06 + 0.088 + k * 0.176) * w
                cv2.circle(m, (int(cx * s), int(0.30 * h * s)), int(0.088 * w * s), 255, -1, cv2.LINE_AA)
            for k in range(1, 5):                        # as listras do toldo
                x = (0.06 + k * 0.176) * w
                cv2.line(m, (int(x * s), int(0.10 * h * s)), (int(x * s), int(0.28 * h * s)), 0, max(1, lw // 2), cv2.LINE_AA)
            cv2.rectangle(m, (int(0.12 * w * s), int(0.42 * h * s)), (int(0.88 * w * s), int(0.97 * h * s)), 255, lw)
            cv2.rectangle(m, (int(0.20 * w * s), int(0.52 * h * s)), (int(0.52 * w * s), int(0.74 * h * s)), 255, -1)
            cv2.rectangle(m, (int(0.60 * w * s), int(0.54 * h * s)), (int(0.78 * w * s), int(0.97 * h * s)), 255, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "envelope":                               # convite: envelope com a aba e o lacre
        w, h = tam, int(tam * 0.68)

        def d(m, s):
            e = int(0.05 * w * s)
            cv2.rectangle(m, (e, e), (int(w * s) - e, int(h * s) - e), 255, int(0.06 * w * s), cv2.LINE_AA)
            cv2.line(m, (e, e), (int(w * s / 2), int(h * s * 0.58)), 255, int(0.05 * w * s), cv2.LINE_AA)
            cv2.line(m, (int(w * s) - e, e), (int(w * s / 2), int(h * s * 0.58)), 255, int(0.05 * w * s), cv2.LINE_AA)
            cv2.circle(m, (int(w * s / 2), int(h * s * 0.58)), int(0.12 * w * s), 255, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "balao":                                  # balão de chat (atendimento por mensagem)
        w, h = tam, int(tam * 0.80)

        def d(m, s):
            b = (_ret_arred(0.96 * w * s, 0.66 * h * s, 0.16 * w * s) * 255).astype(np.uint8)
            m[:b.shape[0], int(0.02 * w * s):int(0.02 * w * s) + b.shape[1]] = b
            cv2.fillPoly(m, [np.int32([[0.22 * w * s, 0.60 * h * s], [0.46 * w * s, 0.60 * h * s],
                                       [0.16 * w * s, 0.98 * h * s]])], 255, cv2.LINE_AA)
            for xx in (0.30, 0.50, 0.70):
                cv2.circle(m, (int(xx * w * s), int(0.33 * h * s)), int(0.055 * w * s), 0, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "sol":                                    # sol: disco e oito raios (GPT-6 Sol, dia, verão)
        w = h = tam

        def d(m, s):
            c = 0.5 * w * s
            cv2.circle(m, (int(c), int(c)), int(0.24 * w * s), 255, -1, cv2.LINE_AA)
            for k in range(8):
                a = k * math.pi / 4
                p0 = (c + math.cos(a) * 0.33 * w * s, c + math.sin(a) * 0.33 * w * s)
                p1 = (c + math.cos(a) * 0.47 * w * s, c + math.sin(a) * 0.47 * w * s)
                cv2.line(m, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 255, max(1, int(0.065 * w * s)), cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "lua":                                    # lua crescente (GPT-6 Luna, noite)
        w = h = tam

        def d(m, s):
            cv2.circle(m, (int(0.48 * w * s), int(0.5 * h * s)), int(0.40 * w * s), 255, -1, cv2.LINE_AA)
            cv2.circle(m, (int(0.66 * w * s), int(0.38 * h * s)), int(0.34 * w * s), 0, -1, cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "lampada":
        w, h = int(tam * 0.70), tam

        def d(m, s):
            cv2.circle(m, (int(0.50 * w * s), int(0.36 * h * s)), int(0.46 * w * s), 255, -1, cv2.LINE_AA)
            pts = np.int32([[0.20 * w * s, 0.52 * h * s], [0.80 * w * s, 0.52 * h * s], [0.68 * w * s, 0.74 * h * s],
                            [0.32 * w * s, 0.74 * h * s]])
            cv2.fillPoly(m, [pts], 255, cv2.LINE_AA)
            for k in range(3):
                y = (0.78 + k * 0.07) * h * s
                cv2.rectangle(m, (int(0.33 * w * s), int(y)), (int(0.67 * w * s), int(y + 0.045 * h * s)), 255, -1)
            cv2.ellipse(m, (int(0.50 * w * s), int(0.36 * h * s)), (int(0.24 * w * s), int(0.24 * w * s)), 0, 200, 290, 0,
                        max(1, int(0.05 * w * s)), cv2.LINE_AA)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "saude":                                  # cruz de saúde (plano de saúde, hospital)
        w = h = tam

        def d(m, s):
            a, b = 0.34, 0.66
            cv2.rectangle(m, (int(a * w * s), int(0.06 * h * s)), (int(b * w * s), int(0.94 * h * s)), 255, -1)
            cv2.rectangle(m, (int(0.06 * w * s), int(a * h * s)), (int(0.94 * w * s), int(b * h * s)), 255, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    if nome == "banco":                                  # prédio de banco: frontão, colunas e base
        w, h = tam, int(tam * 0.86)

        def d(m, s):
            cv2.fillPoly(m, [np.int32([[0.50 * w * s, 0.02 * h * s], [0.98 * w * s, 0.28 * h * s],
                                       [0.02 * w * s, 0.28 * h * s]])], 255, cv2.LINE_AA)
            cv2.rectangle(m, (int(0.06 * w * s), int(0.30 * h * s)), (int(0.94 * w * s), int(0.36 * h * s)), 255, -1)
            for k in range(4):
                x = (0.13 + k * 0.215) * w
                cv2.rectangle(m, (int(x * s), int(0.40 * h * s)), (int((x + 0.10 * w) * s), int(0.82 * h * s)), 255, -1)
            cv2.rectangle(m, (int(0.04 * w * s), int(0.86 * h * s)), (int(0.96 * w * s), int(0.98 * h * s)), 255, -1)
        return _rgba(_mascara_ss(w, h, d), cor)
    raise ValueError(f"icone desconhecido: {nome}")


def _nota(tam):
    """Tres cedulas genericas em leque (verde-acinzentado, R$ no centro): dinheiro sem marca."""
    w, h = int(tam * 0.92), int(tam * 0.46)
    f = np.empty((h, w, 3), np.float32); f[:] = (204.0, 216.0, 194.0)
    k = w / 400.0
    cv2.rectangle(f, (int(10 * k), int(10 * k)), (w - int(10 * k), h - int(10 * k)), (92.0, 112.0, 90.0), max(1, int(4 * k)))
    cv2.rectangle(f, (int(26 * k), int(26 * k)), (w - int(26 * k), h - int(26 * k)), (140.0, 158.0, 136.0), max(1, int(2 * k)))
    cv2.circle(f, (w // 2, h // 2), int(h * 0.30), (120.0, 140.0, 116.0), max(1, int(3 * k)), cv2.LINE_AA)
    le.escrever(f, "R$", centro=(w / 2, h / 2), fonte=le.INTER, corpo=h * 0.26, cor=(64.0, 84.0, 62.0), peso=800)
    for (x, y) in ((54 * k, 50 * k), (w - 54 * k, h - 50 * k)):
        le.escrever(f, "100", centro=(x, y), fonte=le.INTER, corpo=h * 0.12, cor=(84.0, 104.0, 82.0), peso=800)
    m = _ret_arred(w, h, 0.03 * w)
    one = np.zeros((h, w, 4), np.float32); one[..., :3] = f; one[..., 3] = m
    S = int(tam * 1.3)
    out = np.zeros((S, S, 4), np.float32)
    for ang, dx, dy in ((-16.0, -0.06, 0.08), (-6.0, 0.0, 0.0), (7.0, 0.06, -0.07)):
        r = _rot_rgba(one, ang)
        sh, pad = _sombra_alfa(r, (6, 12), 10.0, 0.30)
        x = int(S / 2 - r.shape[1] / 2 + dx * S); y = int(S / 2 - r.shape[0] / 2 + dy * S)
        from planos import sobre_rgba
        out = sobre_rgba(out, sh, x - pad, y - pad)
        out = sobre_rgba(out, r, x, y)
    ys, xs = np.nonzero(out[..., 3] > 0.02)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


# ====================================================================== 34. ranking
def _linha_ranking(texto, w, h, estilo, valor=None):
    """Uma linha do ranking: caixa de interface (azul do Hedy, cinza escura ou branca) com o nome."""
    sx, sy = 12, 12
    lay = np.zeros((h + sy, w + sx, 4), np.float32)
    if estilo == "azul":
        fundo, filete, sombra, tinta = st.AZUL_UI, st.FILETE, st.SOMBRA, (242.0, 242.0, 248.0)
    elif estilo == "branco":
        fundo, filete, sombra, tinta = BRANCO_UI, (206.0, 206.0, 212.0), (198.0, 198.0, 204.0), TINTA_D
    else:
        fundo, filete, sombra, tinta = (46.0, 46.0, 52.0), (96.0, 96.0, 104.0), (18.0, 18.0, 22.0), (206.0, 206.0, 212.0)
    lay[sy:, sx:, :3] = sombra; lay[sy:, sx:, 3] = 1.0
    lay[:h, :w, :3] = filete; lay[:h, :w, 3] = 1.0
    f = 3
    lay[f:h - f, f:w - f, :3] = fundo
    img = lay[..., :3]
    corpo = min(58.0, 58.0 * (w - 120 - (200 if valor else 0)) / max(1.0, _largura(texto, le.INTER, 58, 800)))
    le.escrever(img, texto, esquerda=(44, h / 2), fonte=le.INTER, corpo=corpo, cor=tinta, peso=800)
    if valor:
        vw = _largura(valor, le.INTER, 50, 700)
        le.escrever(img, valor, esquerda=(w - 40 - vw, h / 2), fonte=le.INTER, corpo=50, cor=tinta, peso=700)
    lay[..., :3] = img
    return lay


def ranking(n, p, ctx):
    estilo = p.get("fundo", "radar")
    if estilo == "radar":
        img = bg.preto()
        img = sobre(img, st.radar(mo.fase_radar((n - p["inicio"]) / FPS, 0.673), (W / 2, p.get("y0", 800) + 186)))
        cor_num, cor_tit = (150.0, 150.0, 158.0), (150.0, 150.0, 158.0)
    else:
        img = _fundo(ctx, p)
        cor_num, cor_tit = (110.0, 110.0, 118.0), (110.0, 110.0, 118.0)
    itens = p["itens"]
    w, h = p.get("largura", 720), p.get("altura", 130)
    y0, passo = p.get("y0", 800), p.get("passo", 186)
    xbox = p.get("x_caixa", 250)
    tit = p.get("titulo")
    if tit and n >= tit.get("quadro", p["inicio"]):
        e = mo.escala_palavra((n - tit.get("quadro", p["inicio"])) / FPS)
        le.escrever(img, tit["texto"], centro=(W / 2, y0 - 150), fonte=le.INTER, corpo=40 * e, cor=cor_tit, peso=800,
                    tracking=4.0)
    ordem0 = [it["texto"] for it in sorted(itens, key=lambda it: it["pos"])]
    estados = [(-10 ** 9, ordem0)] + [(t["quadro"], t["ordem"]) for t in sorted(p.get("trocas", []), key=lambda t: t["quadro"])]
    vigentes = [e for e in estados if e[0] <= n]
    q1, o1 = vigentes[-1]
    o0 = vigentes[-2][1] if len(vigentes) > 1 else o1
    v = mv.suavizar_curva(u(n, q1, q1 + 9), "saida", 2.2) if len(vigentes) > 1 else 1.0
    nslots = max(len(ordem0), p.get("vagas", 0))
    for k in range(nslots):                            # o numero da posicao e da VAGA, nao da linha
        if n >= p.get("quadro_numeros", p["inicio"]):
            le.escrever(img, f"{k + 1}", centro=(xbox - 70, y0 + k * passo), fonte=le.SERIFA, corpo=118, cor=cor_num,
                        contorno=1.0)
    desenhos = []
    for it in itens:
        if n < it["quadro"]:
            continue
        s0 = o0.index(it["texto"]) if it["texto"] in o0 else o1.index(it["texto"])
        s1 = o1.index(it["texto"])
        k = s0 + (s1 - s0) * v
        x = xbox + mo.entrada_caixa((n - it["quadro"]) / FPS)
        sobe = s1 < s0 and v < 1.0
        estilo_it = it.get("cor", "cinza" if estilo == "radar" else "branco")
        for tr in it.get("muda_cor", []):
            if n >= tr["quadro"]:
                estilo_it = tr["cor"]
        caixa = ctx.cache(("lin", it["texto"], estilo_it, w, h), lambda it=it, e_=estilo_it: _linha_ranking(it["texto"], w, h, e_, it.get("valor")))
        alfa = 1.0
        for ap in p.get("apaga", []):
            if ap["texto"] == it["texto"] and n >= ap["quadro"]:
                alfa = 0.35
        desenhos.append((1 if sobe else 0, x, y0 + k * passo - h / 2, caixa, alfa, it))
    for _, x, y, caixa, alfa, it in sorted(desenhos, key=lambda d: d[0]):
        c = caixa if alfa >= 0.999 else np.dstack([caixa[..., :3], caixa[..., 3] * alfa])
        sobre(img, c, x, y)
        for mk in it.get("marcas", []):
            if n < mk["quadro"]:
                continue
            yc = y + h / 2
            if mk["tipo"] in ("cai", "sobe"):
                cor = VERMELHO if mk["tipo"] == "cai" else (64.0, 168.0, 96.0)
                e = mo.escala_palavra((n - mk["quadro"]) / FPS)
                xr, s_ = x + w - 58, 26 * e
                pts = ([[xr - s_, yc - s_ * 0.6], [xr + s_, yc - s_ * 0.6], [xr, yc + s_ * 0.8]] if mk["tipo"] == "cai"
                       else [[xr - s_, yc + s_ * 0.6], [xr + s_, yc + s_ * 0.6], [xr, yc - s_ * 0.8]])
                cv2.fillPoly(img, [np.int32(pts)], cor, cv2.LINE_AA)
            elif mk["tipo"] == "circulo":
                f = min(1.0, (n - mk["quadro"] + 3) / 9.0)
                _circulo_mao(img, (x + w / 2, yc), w / 2 + 50, h / 2 + 40, f, _cor(mk.get("cor"), AZUL), 6.0)
    return _camera(img, n, p, (1.0, 1.05), centro=(W / 2, y0 + passo * (nslots - 1) / 2))


# ====================================================================== 35. terminal
def terminal(n, p, ctx):
    """Janela de terminal (escura) no canvas; linhas monoespacadas digitadas a partir do quadro
    de cada uma; o cursor em bloco pisca no fim da ultima; linha em destaque ganha a selecao azul."""
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    corpo = p.get("corpo", 56)
    lh = corpo * 1.62
    jw = p.get("largura", 900)
    jh = int(p.get("altura", 150 + len(p["linhas"]) * lh + 90))
    cx, cy = p.get("centro", (W / 2, 930))
    x0, y0 = cx - jw / 2, cy - jh / 2
    jan = ctx.cache("jan", lambda: _janela_terminal(jw, jh, p.get("titulo", "terminal")))
    _colar_centro(img, jan, cx, cy, 1.0, {"desloc": (18, 30), "blur": 24.0, "forca": 0.45})
    ultima = None
    for i, L in enumerate(p["linhas"]):
        if n < L["quadro"]:
            continue
        cps = L.get("letras_por_degrau", 6)
        k = min(len(L["texto"]), cps * ((n - L["quadro"]) // 3 + 1))
        yy = y0 + 150 + i * lh
        cor = _cor(L.get("cor"), (222.0, 222.0, 228.0))
        if L.get("destaque") and n >= L["destaque"]:
            lw = _largura(L["texto"], MONO, corpo)
            sobre(img, st.selecao_azul(x0 + 50, yy - 14, x0 + 70 + lw, yy + corpo * 1.25, esp=3.0, r=9.0))
            cor = (250.0, 250.0, 252.0)
        _escreve(img, L["texto"][:k], x0 + 60, yy, MONO, corpo, None, cor)
        ultima = (x0 + 60 + _largura(L["texto"][:k], MONO, corpo), yy, k == len(L["texto"]))
    if ultima and ((n // 3) % 2 == 0 or not ultima[2]):
        cv2.rectangle(img, (int(ultima[0] + 6), int(ultima[1] + 4)), (int(ultima[0] + 6 + corpo * 0.58), int(ultima[1] + corpo * 1.12)),
                      (222.0, 222.0, 228.0), -1)
    return _camera(img, n, p, (1.0, 1.05), centro=(cx, cy))


def _janela_terminal(jw, jh, titulo):
    m = _ret_arred(jw, jh, 30)
    lay = _rgba(m, (28.0, 28.0, 33.0))
    lay[:76, :, :3] = (54.0, 54.0, 62.0)
    for k in range(3):
        cv2.circle(lay, (40 + k * 40, 38), 12, (120.0, 120.0, 130.0, 1.0), -1, cv2.LINE_AA)
    img = lay[..., :3]
    _escreve(img, titulo, jw / 2, 20, le.INTER, 30, 600, (170.0, 170.0, 178.0), alinha="centro")
    lay[..., :3] = img
    lay[..., 3] = m
    return lay


# ====================================================================== 36. podio
def podio(n, p, ctx):
    img = _canvas(ctx, True)
    base = p.get("base_y", 1340)
    lw = p.get("largura_bloco", 240)
    blocos = {1: (540, 500), 2: (250, 360), 3: (830, 270)}
    sh = np.zeros((H, W), np.float32)
    cv2.ellipse(sh, (540, base + 10), (440, 34), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    sh = cv2.GaussianBlur(sh, (0, 0), 18) * 0.30
    img *= (1 - sh[..., None])
    for pos, (cx, hb) in blocos.items():
        x0, x1 = int(cx - lw / 2), int(cx + lw / 2)
        yt = base - hb
        pts = np.array([[x0 + 22, yt - 40], [x1 - 22, yt - 40], [x1, yt], [x0, yt]], np.int32)
        cv2.fillConvexPoly(img, pts, (238.0, 238.0, 240.0), cv2.LINE_AA)
        cv2.polylines(img, [pts], True, (150.0, 150.0, 156.0), 2, cv2.LINE_AA)
        cv2.rectangle(img, (x0, yt), (x1, base), (218.0, 218.0, 222.0), -1)
        cv2.rectangle(img, (x0, yt), (x1, base), (150.0, 150.0, 156.0), 2)
        le.escrever(img, str(pos), centro=(cx, yt + hb * 0.48), fonte=le.SERIFA, corpo=(210 if pos == 1 else 170),
                    cor=(132.0, 132.0, 140.0), contorno=1.0)
    for ci in p.get("circulos", []):
        if n >= ci["quadro"]:
            cx, hb = blocos[ci["pos"]]
            yt = base - hb
            _circulo_mao(img, (cx, yt + hb * 0.48), 92, 112, min(1.0, (n - ci["quadro"] + 3) / 9.0), AZUL, 7.0, 3 + ci["pos"])
    for et in p.get("etiquetas", []):
        if n < et["quadro"]:
            continue
        cx, hb = blocos[et["pos"]]
        yt = base - hb - 40
        t = (n - et["quadro"]) / FPS
        cai = (1 - mo.subida(t, 0.45, 0.09)) * 520.0
        caixa = ctx.cache(("et", et["texto"], et.get("cor", "azul")), lambda et=et: _etiqueta(et["texto"], et.get("cor", "azul"),
                                                                                          et.get("corpo", 44)))
        sobre(img, caixa, cx - caixa.shape[1] / 2, yt - caixa.shape[0] - 18 - cai)
    return _camera(img, n, p, (1.0, 1.04), centro=(W / 2, base - 300))


def _etiqueta(texto, cor="azul", corpo=50):
    """Etiqueta de interface: azul do Hedy (destaque) ou branca com sombra cinza (os outros)."""
    if cor == "azul":
        return _caixa_larga(texto, corpo)
    w = int(_largura(texto, le.INTER, corpo, 800) + 96); h = int(corpo + 60)
    sx, sy = 12, 12
    lay = np.zeros((h + sy, w + sx, 4), np.float32)
    lay[sy:, sx:, :3] = (186.0, 186.0, 194.0); lay[sy:, sx:, 3] = 1.0
    lay[:h, :w, :3] = (206.0, 206.0, 212.0); lay[:h, :w, 3] = 1.0
    lay[3:h - 3, 3:w - 3, :3] = BRANCO_UI
    img = lay[..., :3]
    le.escrever(img, texto, centro=(w / 2, h / 2), fonte=le.INTER, corpo=corpo, cor=TINTA_D, peso=800)
    lay[..., :3] = img
    return lay


# ====================================================================== 37. barras
def barras(n, p, ctx):
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    itens = p["itens"]
    k = len(itens)
    lw, gap = p.get("largura", 250), p.get("gap", 150)
    total = k * lw + (k - 1) * gap
    x0 = W / 2 - total / 2
    base = p.get("base_y", 1330)
    hmax = p.get("altura_max", 720)
    vmax = p.get("maximo") or max(max(it["valor"], it.get("muda", {}).get("valor", 0)) for it in itens)
    tit = p.get("titulo")
    if tit and n >= tit.get("quadro", p["inicio"]):
        le.escrever(img, tit["texto"], centro=(W / 2, base - hmax - 250), fonte=le.INTER, corpo=tit.get("corpo", 36),
                    cor=(110.0, 110.0, 118.0), peso=800, tracking=3.0)
    cv2.line(img, (int(x0 - 60), base), (int(x0 + total + 60), base), TINTA_D, 4, cv2.LINE_AA)
    for i, it in enumerate(itens):
        xb = x0 + i * (lw + gap)
        cor = _cor(it.get("cor", "tinta"))
        g = _cresce(n, it["quadro"])
        v = it["valor"] * g
        txt = it.get("texto", str(it["valor"]))
        mu = it.get("muda")
        if mu and n >= mu["quadro"]:
            g2 = _cresce(n, mu["quadro"])
            v = it["valor"] + (mu["valor"] - it["valor"]) * g2
            txt = mu.get("texto", txt)
            cor = _cor(mu.get("cor"), cor)
        hpx = hmax * v / vmax
        if hpx > 1:
            cv2.rectangle(img, (int(xb), int(base - hpx)), (int(xb + lw), base), cor, -1)
            cv2.rectangle(img, (int(xb), int(base - hpx)), (int(xb + lw), int(base - hpx + 8)),
                          tuple(min(255.0, c + 40) for c in cor), -1)
        mg = it.get("margem", p.get("margem"))
        if mg and n >= p.get("quadro_margem", it["quadro"]) and hpx > 1:      # margem de erro: faixa de v-m a v+m
            ya, yb = int(base - hmax * (v + mg) / vmax), int(base - hmax * (v - mg) / vmax)
            faixa = img[ya:yb, int(xb - 22):int(xb + lw + 22)]
            faixa[:] = faixa * 0.55 + np.array(cor) * 0.45 * 0.5 + 255.0 * 0.45 * 0.5
            for yy in (ya, yb):
                for xx in range(int(xb - 22), int(xb + lw + 22), 22):
                    cv2.line(img, (xx, yy), (min(int(xb + lw + 22), xx + 12), yy), cor, 4, cv2.LINE_AA)
        if n >= it["quadro"] and txt:
            s = _formata(txt, v)
            le.escrever(img, s, centro=(xb + lw / 2, base - hpx - 74), fonte=le.INTER, corpo=p.get("corpo_valor", 92),
                        cor=cor if cor != CINZA_PECA else (120.0, 120.0, 126.0), peso=800)
        qr = it.get("quadro_rotulo", it["quadro"])
        if n >= qr and it.get("rotulo"):
            e = mo.escala_palavra((n - qr) / FPS)
            corpo = min(p.get("corpo_rotulo", 92), 92 * (lw + gap * 0.8) / max(1.0, _largura(it["rotulo"], le.SERIFA, 92)))
            le.escrever(img, it["rotulo"], centro=(xb + lw / 2, base + 86), fonte=le.SERIFA, corpo=corpo, cor=TINTA_D,
                        contorno=1.0, escala=e)
    so = p.get("sobreposicao")                   # onde as faixas de margem se cruzam: a zona do empate técnico
    if so and n >= so["quadro"]:
        lo, hi = so["de"], so["ate"]
        ya, yb = int(base - hmax * hi / vmax), int(base - hmax * lo / vmax)
        fr = min(1.0, (n - so["quadro"] + 3) / 9.0)
        xa, xb2 = int(x0 - 70), int(x0 - 70 + (total + 140) * fr)
        zona = img[ya:yb, xa:xb2]
        zona[:] = zona * 0.62 + np.array(AMARELO_EMPATE) * 0.38
        if so.get("texto") and fr >= 1:
            le.escrever(img, so["texto"], centro=(W / 2, ya - 70), fonte=le.INTER, corpo=so.get("corpo", 64),
                        cor=TINTA_D, peso=900, tracking=2.0)
    li = p.get("linha")
    if li and n >= li["quadro"]:
        yl = int(base - hmax * li["valor"] / vmax)
        for xx in range(int(x0 - 60), int(x0 + total + 60), 28):
            cv2.line(img, (xx, yl), (xx + 15, yl), AZUL, 5, cv2.LINE_AA)
        if li.get("texto"):
            le.escrever(img, li["texto"], centro=(W / 2, yl + li.get("dy", -70)), fonte=le.SERIFA, corpo=li.get("corpo", 150), cor=AZUL,
                        contorno=1.0, escala=mo.escala_palavra((n - li["quadro"]) / FPS))
    return _camera(img, n, p, (1.0, 1.04), centro=(W / 2, base - hmax / 2))


AMARELO_EMPATE = (236.0, 200.0, 40.0)


# ====================================================================== 38. centena
def centena(n, p, ctx):
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    forma = p.get("forma", "pessoa")
    px = p.get("passo", 84)
    if forma == "pessoa":
        w, h, py = 56, 74, 100
        ico = _icone_pessoa(w, h)
    else:
        w = h = 62
        py = px
        ico = _ret_arred(w, h, 14)
    X0 = W / 2 - (9 * px + w) / 2
    Y0 = p.get("y0", 420)
    base = np.array(p.get("cor_base", (200.0, 200.0, 206.0) if p.get("fundo", "canvas") == "canvas" else (170.0, 168.0, 164.0)),
                    np.float32)
    cores = [base] * 100
    novos = set()
    xs_marca = set()
    for g in p.get("grupos", []):
        if n < g["quadro"]:
            continue
        de, ate = g["de"], g["ate"]
        dur = max(1, g.get("duracao", 6))
        idx = list(range(de, ate))
        if g.get("ordem") == "aleatoria":
            idx = list(np.random.default_rng(g.get("semente", 3)).permutation(idx))
        on = int(round(len(idx) * min(1.0, (n - g["quadro"] + 3) / float(dur))))
        on_ant = int(round(len(idx) * min(1.0, max(0.0, (n - g["quadro"]) / float(dur))))) if n - g["quadro"] >= 3 else 0
        cor = np.array(_cor(g["cor"]), np.float32)
        for j, ii in enumerate(idx[:on]):
            cores[ii] = cor
            if j >= on_ant:
                novos.add(ii)
            if g.get("marca") == "x":
                xs_marca.add(ii)
    ent = p.get("entrada")
    for i in range(100):
        r, c = divmod(i, 10)
        if ent is not None and n < ent + r:
            continue
        x, y = int(X0 + c * px), int(Y0 + r * py)
        m = ico
        if i in novos:
            m = cv2.resize(ico, (int(w * 1.18), int(h * 1.18)), interpolation=cv2.INTER_LINEAR)
            x -= (m.shape[1] - w) // 2; y -= (m.shape[0] - h)
        _colar_mascara(img, m, x, y, cores[i])
        if i in xs_marca:
            cx_, cy_ = x + m.shape[1] / 2, y + m.shape[0] * (0.30 if forma == "pessoa" else 0.5)
            k_ = 12
            cv2.line(img, (int(cx_ - k_), int(cy_ - k_)), (int(cx_ + k_), int(cy_ + k_)), (240.0, 240.0, 242.0), 4, cv2.LINE_AA)
            cv2.line(img, (int(cx_ + k_), int(cy_ - k_)), (int(cx_ - k_), int(cy_ + k_)), (240.0, 240.0, 242.0), 4, cv2.LINE_AA)
    _titulo(img, n, p, Y0 - 110)
    um = p.get("um")
    if um and n >= um["quadro"]:
        r, c = divmod(um["indice"], 10)
        x, y = X0 + c * px + w / 2, Y0 + r * py + h / 2
        pulso = 6 if ((n - um["quadro"]) // 3) % 2 == 0 else 0
        cv2.circle(img, (int(x), int(y)), int(0.95 * max(w, h)) + pulso, _cor(um.get("cor"), AZUL), 5, cv2.LINE_AA)
    for nm in p.get("numerais", []):
        if nm["quadro"] <= n < nm.get("ate", 10 ** 9):
            le.escrever(img, nm["texto"], centro=tuple(nm.get("pos", (W / 2, Y0 + 10 * py + 120))), fonte=le.SERIFA,
                        corpo=nm.get("corpo", 190), cor=_cor(nm.get("cor"), AZUL), contorno=1.0,
                        escala=mo.escala_palavra((n - nm["quadro"]) / FPS))
    return _camera(img, n, p, (1.0, 1.04), centro=(W / 2, Y0 + 5 * py))


# ====================================================================== 39. pizzas
def pizzas(n, p, ctx):
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    for pz in p["pizzas"]:
        _pizza(img, n, pz, p.get("fundo", "canvas"))
    return _camera(img, n, p, (1.0, 1.04))


def _pizza(img, n, pz, fundo):
    cx, cy = (int(v) for v in pz["centro"]); R = int(pz.get("raio", 260))
    if n < pz.get("quadro", -10 ** 9):
        return img
    e = mo.escala_palavra((n - pz.get("quadro", -10 ** 9)) / FPS) if pz.get("quadro") is not None else 1.0
    R = int(R * e)
    cv2.circle(img, (cx, cy), R, (222.0, 222.0, 226.0) if fundo == "canvas" else (214.0, 212.0, 207.0), -1, cv2.LINE_AA)
    fatias = pz.get("fatias") or [{"valor": pz["valor"], "cor": pz.get("cor", "tinta"), "quadro": pz["acende"]["de"],
                                   "dur": pz["acende"]["ate"] - pz["acende"]["de"]}]
    a0 = -90.0
    aceso = -90.0
    for k, f in enumerate(fatias):
        g = mv.suavizar_curva(u(n, f["quadro"], f["quadro"] + f.get("dur", 9)), "saida", 1.6)
        ang = 360.0 * f["valor"] * g
        dx = dy = 0.0
        de = f.get("destaque")
        if de is not None and n >= de:
            meio = math.radians(a0 + 180.0 * f["valor"])
            off = 34.0 * min(1.0, (n - de + 3) / 6.0)
            dx, dy = off * math.cos(meio), off * math.sin(meio)
        if ang > 0.5:
            c_ = (int(cx + dx), int(cy + dy))
            cv2.ellipse(img, c_, (R, R), 0, a0, a0 + ang, _cor(f.get("cor")), -1, cv2.LINE_AA)
            for a_ in (a0, a0 + ang):                      # raios brancos separando as fatias
                cv2.line(img, c_, (int(c_[0] + R * math.cos(math.radians(a_))), int(c_[1] + R * math.sin(math.radians(a_)))),
                         (250.0, 250.0, 250.0), 5, cv2.LINE_AA)
            cv2.ellipse(img, c_, (R, R), 0, a0, a0 + ang, TINTA_D, 5, cv2.LINE_AA)
        if f.get("rotulo") and g > 0.6:
            meio = math.radians(a0 + 180.0 * f["valor"])
            le.escrever(img, f["rotulo"], centro=(cx + dx + 0.58 * R * math.cos(meio), cy + dy + 0.58 * R * math.sin(meio)),
                        fonte=le.INTER, corpo=pz.get("corpo_fatia", 64), cor=(246.0, 246.0, 248.0), peso=800)
        if ang > 0.5:
            aceso = a0 + ang
        a0 += 360.0 * f["valor"]
    if aceso < 269.5:                                      # o que falta encher ainda tem o contorno
        cv2.ellipse(img, (cx, cy), (R, R), 0, aceso, 270.0, TINTA_D, 5, cv2.LINE_AA)
    m = pz.get("metade")
    if m and n >= m["quadro"]:
        for yy in range(cy - R - 50, cy + R + 60, 26):
            cv2.line(img, (cx, yy), (cx, yy + 14), AZUL, 5, cv2.LINE_AA)
    fo = pz.get("fora")
    if fo and n >= fo["quadro"]:
        ef = mo.escala_palavra((n - fo["quadro"]) / FPS)
        fx, fy = fo.get("pos", (cx + R + 120, cy + R - 40))
        rr = int(fo.get("raio", 90) * ef)
        cv2.circle(img, (int(fx), int(fy)), rr, (176.0, 176.0, 182.0), -1, cv2.LINE_AA)
        cv2.circle(img, (int(fx), int(fy)), rr, (120.0, 120.0, 126.0), 3, cv2.LINE_AA)
        if fo.get("texto"):
            le.escrever(img, fo["texto"], centro=(fx, fy + rr + 56), fonte=le.SERIFA, corpo=fo.get("corpo", 70),
                        cor=(96.0, 96.0, 102.0), contorno=1.0, escala=ef)
    for nm in pz.get("numerais", []):
        if nm["quadro"] <= n < nm.get("ate", 10 ** 9):
            le.escrever(img, nm["texto"], centro=tuple(nm.get("pos", (cx, cy - R - 110))), fonte=le.SERIFA,
                        corpo=nm.get("corpo", 170), cor=_cor(nm.get("cor"), AZUL), contorno=1.0,
                        escala=mo.escala_palavra((n - nm["quadro"]) / FPS))
    rt = pz.get("rotulo")
    if rt and n >= rt["quadro"]:
        le.escrever(img, rt["texto"], centro=(cx, cy + R + 96), fonte=le.SERIFA, corpo=rt.get("corpo", 96), cor=TINTA_D,
                    contorno=1.0, escala=mo.escala_palavra((n - rt["quadro"]) / FPS))
    return img


# ====================================================================== 40. celular
FONE = (30.0, 30.0, 34.0)
TELA = (247.0, 247.0, 249.0)


def _fone_corpo(lw, lh):
    m = _ret_arred(lw, lh, 0.15 * lw)
    lay = _rgba(m, FONE)
    k = max(3, int(lw * 0.008)) | 1
    aro = np.clip(m - cv2.erode(m, np.ones((k, k), np.uint8)), 0, 1)
    lay[..., :3] = lay[..., :3] * (1 - aro[..., None]) + np.array((92.0, 92.0, 100.0)) * aro[..., None]
    return lay


def _bolha(texto, lado, larg_max, corpo=34):
    linhas = _quebrar(texto, le.INTER, corpo, 500, larg_max - 52)
    lh = corpo * 1.32
    bw = int(max(_largura(L, le.INTER, corpo, 500) for L in linhas) + 52)
    bh = int(len(linhas) * lh + 36)
    m = _ret_arred(bw, bh, 30)
    cor = AZUL if lado == "eu" else (233.0, 233.0, 238.0)
    tinta = (250.0, 250.0, 252.0) if lado == "eu" else (30.0, 30.0, 34.0)
    lay = _rgba(m, cor)
    img = lay[..., :3]
    for i, L in enumerate(linhas):
        _escreve(img, L, 26, 16 + i * lh, le.INTER, corpo, 500, tinta)
    lay[..., :3] = img
    lay[..., 3] = m
    return lay


# ---------------------------------------------------------------- a resposta que vira interface (v12.8)
# Um item da conversa com "tipo": "interface" é a resposta da IA montada como app: cada componente entra na palavra
# que a fala diz (botão, gráfico, calculadora, campos e o resultado que conta). Coordenadas da tela do celular.
_ALT = {"titulo": 46, "texto": 36, "botoes": 64, "grafico": 230, "calculadora": 336, "campos": 66, "resultado": 96,
        "barra": 88}


def _comp_altura(c):
    if c.get("altura"):                                   # gráfico e calculadora compactos cabem na zona segura
        return int(c["altura"])
    if c["tipo"] == "texto":
        return 36 * max(1, len(c.get("linhas", [c.get("texto", "")])))
    if c["tipo"] == "campos":
        return 66 * len(c.get("itens", []))
    if c["tipo"] == "opcoes":
        return 70 * len(c.get("itens", []))
    return _ALT[c["tipo"]]


def _desenha_comp(lay, c, n, x0, y0, larg):
    """Desenha o componente c em lay (RGB float) com o canto em (x0, y0) e largura larg."""
    t = c["tipo"]
    q = c.get("quadro", 0)
    if t == "titulo":
        _escreve(lay, c["texto"], x0, y0 + 4, le.INTER, c.get("corpo", 30), 800, (24.0, 24.0, 28.0))
    elif t == "texto":
        for i, L in enumerate(c.get("linhas", [c.get("texto", "")])):
            _escreve(lay, L, x0, y0 + i * 36, le.INTER, c.get("corpo", 25), 500, (70.0, 70.0, 78.0))
    elif t == "botoes":
        itens = c["itens"]
        gap = 14
        bw = (larg - gap * (len(itens) - 1)) / len(itens)
        ativo = c.get("ativo", 0)
        clicado = c.get("clique") is not None and n >= c["clique"]
        for i, txt in enumerate(itens):
            bx = x0 + i * (bw + gap)
            m = _ret_arred(int(bw), 56, 28)
            on = clicado and i == ativo
            fundo = AZUL if on else (236.0, 238.0, 244.0)
            sobre(lay, _rgba(m, fundo), bx, y0)
            _escreve(lay, txt, bx + bw / 2, y0 + 14, le.INTER, c.get("corpo", 24), 700,
                     (250.0, 250.0, 252.0) if on else (40.0, 40.0, 48.0), alinha="centro")
            if on and n - c["clique"] < 9:                                   # o toque: anel que abre
                k = (n - c["clique"]) / 9.0
                cv2.circle(lay, (int(bx + bw / 2), int(y0 + 28)), int(20 + 50 * k), (120.0, 170.0, 230.0), 3, cv2.LINE_AA)
    elif t == "grafico":
        vals = c["valores"]
        vmax = max(vals) or 1
        alt = _comp_altura(c)
        base = y0 + alt - 44
        gap = 18
        bw = (larg - gap * (len(vals) - 1)) / len(vals)
        cv2.line(lay, (int(x0), int(base)), (int(x0 + larg), int(base)), (200.0, 200.0, 208.0), 2, cv2.LINE_AA)
        for i, v in enumerate(vals):
            g = _cresce(n, q + 2 * i, 10)
            h = (alt - 60) * v / vmax * g
            bx = x0 + i * (bw + gap)
            cor = AZUL if i == len(vals) - 1 else (150.0, 186.0, 224.0)
            if h > 1:
                cv2.rectangle(lay, (int(bx), int(base - h)), (int(bx + bw), int(base)), cor, -1, cv2.LINE_AA)
            rot = c.get("rotulos", [None] * len(vals))[i]
            if rot:
                _escreve(lay, rot, bx + bw / 2, base + 10, le.INTER, 20, 600, (110.0, 110.0, 118.0), alinha="centro")
    elif t == "calculadora":
        visor = c.get("visor", "0")
        if c.get("conta") and n >= c.get("quadro_conta", q):
            a, b = c["conta"]
            g = _cresce(n, c.get("quadro_conta", q), c.get("dur", 12))
            visor = _formata(visor, a + (b - a) * g)                     # o modelo do visor dá o formato ("R$ 1.000")
        m = _ret_arred(int(larg), 70, 18)
        sobre(lay, _rgba(m, (30.0, 32.0, 40.0)), x0, y0)
        _escreve(lay, visor, x0 + larg - 22, y0 + 14, le.INTER, 38, 700, (246.0, 246.0, 250.0), alinha="dir")
        teclas = c.get("teclas", ["7", "8", "9", "÷", "4", "5", "6", "×", "1", "2", "3", "−", "0", ",", "=", "+"])
        gap = 10
        kw = (larg - 3 * gap) / 4
        kh = (_comp_altura(c) - 84 - 3 * gap) / 4
        for i, tx in enumerate(teclas):
            if n < q + (i // 4) * 1:
                continue
            col, lin = i % 4, i // 4
            kx, ky = x0 + col * (kw + gap), y0 + 84 + lin * (kh + gap)
            op = tx in "÷×−+="
            m = _ret_arred(int(kw), int(kh), 16)
            sobre(lay, _rgba(m, AZUL if op else (232.0, 234.0, 240.0)), kx, ky)
            _escreve(lay, tx, kx + kw / 2, ky + kh / 2 - 16, le.INTER, 28, 700,
                     (250.0, 250.0, 252.0) if op else (36.0, 36.0, 44.0), alinha="centro")
    elif t == "campos":
        for i, (rot, val) in enumerate(c["itens"]):
            yy = y0 + i * 66
            _escreve(lay, rot, x0, yy + 14, le.INTER, 24, 600, (110.0, 110.0, 118.0))
            m = _ret_arred(int(larg * 0.46), 52, 14)
            sobre(lay, _rgba(m, (236.0, 238.0, 244.0)), x0 + larg * 0.54, yy)
            _escreve(lay, val, x0 + larg - 18, yy + 12, le.INTER, 26, 700, (30.0, 30.0, 36.0), alinha="dir")
    elif t == "opcoes":                                  # lista de escolha (rádio); as bloqueadas apagam e ganham cadeado
        bloq = c.get("bloqueados", [])
        qb = c.get("quadro_bloqueio")
        for i, txt in enumerate(c["itens"]):
            yy = y0 + i * 70
            off = qb is not None and n >= qb and i in bloq
            ativo = i == c.get("ativo", 0)
            m = _ret_arred(int(larg), 60, 16)
            sobre(lay, _rgba(m, (232.0, 240.0, 252.0) if ativo else (243.0, 244.0, 247.0)), x0, yy)
            cr = (int(x0 + 30), int(yy + 30))
            cv2.circle(lay, cr, 13, AZUL if ativo else (170.0, 170.0, 178.0), 3, cv2.LINE_AA)
            if ativo:
                cv2.circle(lay, cr, 7, AZUL, -1, cv2.LINE_AA)
            cor_t = (178.0, 178.0, 186.0) if off else ((20.0, 60.0, 110.0) if ativo else (36.0, 36.0, 44.0))
            _escreve(lay, txt, x0 + 58, yy + 14, le.INTER, 26, 700 if ativo else 600, cor_t)
            if off:
                k = min(1.0, (n - qb + 3) / 6.0)
                cad = _icone("cadeado", int(30 + 8 * (1 - k)), (150.0, 150.0, 158.0))
                sobre(lay, cad, x0 + larg - 50, yy + 30 - cad.shape[0] / 2)
    elif t == "barra":                                   # barra que esvazia (o limite de uso)
        g = _cresce(n, q, c.get("dur", 12))
        de, ate = c.get("de", 1.0), c.get("ate", 0.4)
        v = de + (ate - de) * g
        _escreve(lay, c.get("rotulo", ""), x0, y0, le.INTER, 24, 600, (110.0, 110.0, 118.0))
        m = _ret_arred(int(larg), 30, 15)
        sobre(lay, _rgba(m, (232.0, 234.0, 240.0)), x0, y0 + 44)
        if v > 0.02:
            m2 = _ret_arred(max(31, int(larg * v)), 30, 15)
            sobre(lay, _rgba(m2, VERMELHO if v < 0.5 else AZUL), x0, y0 + 44)
    elif t == "resultado":
        a, b = c.get("conta", [0, 0])
        g = _cresce(n, q, c.get("dur", 12))
        v = a + (b - a) * g
        txt = f"{c.get('prefixo', '')}{v:,.0f}{c.get('sufixo', '')}".replace(",", ".")
        _escreve(lay, txt, x0 + larg / 2, y0 + 8, le.INTER, c.get("corpo", 54), 800, AZUL, alinha="centro")


def _cartao_interface(bm, n, larg):
    """A resposta-app: cartão branco com os componentes que já entraram (o espaço dos outros fica reservado)."""
    pad, gap = 22, 16
    comps = bm["componentes"]
    alt = pad * 2 + sum(_comp_altura(c) for c in comps) + gap * (len(comps) - 1)
    m = _ret_arred(int(larg), int(alt), 30)
    lay = _rgba(m, (252.0, 252.0, 253.0))
    rgb = np.ascontiguousarray(lay[..., :3])                # o cv2 só desenha em memória contínua
    borda = cv2.morphologyEx((m > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)).astype(np.float32)
    rgb[:] = rgb * (1 - borda[..., None]) + np.array((214.0, 216.0, 224.0)) * borda[..., None]
    y = pad
    for c in comps:
        if n >= c.get("quadro", bm["quadro"]):
            _desenha_comp(rgb, c, n, pad, y, larg - 2 * pad)
        y += _comp_altura(c) + gap
    lay[..., :3] = rgb
    return lay


def _tela_status(img, sw, n, p):
    """Barra de status: hora a esquerda, ilha no meio, sinal/wifi/bateria a direita (ou o aviao)."""
    _escreve(img, "9:41", 54, 30, le.INTER, 32, 700, (24.0, 24.0, 28.0))
    ilha = _ret_arred(170, 46, 23)
    x0 = int(sw / 2 - 85)
    reg = img[22:68, x0:x0 + 170]
    reg[:] = reg * (1 - ilha[..., None]) + np.array(FONE) * ilha[..., None]
    av = p.get("aviao")
    on = av is not None and n >= av
    bat = _ret_arred(50, 25, 7)
    xb = sw - 82
    reg = img[37:62, xb:xb + 50]
    reg[:] = reg * (1 - bat[..., None]) + np.array((24.0, 24.0, 28.0)) * bat[..., None]
    if not on:
        sobre(img, _icone("sinal", 38, (24.0, 24.0, 28.0)), sw - 186, 32)
        sobre(img, _icone("wifi", 42, (24.0, 24.0, 28.0)), sw - 138, 30)
    else:
        e = mo.escala_palavra((n - av) / FPS)
        a = _rot_rgba(_icone("aviao", max(4, int(52 * e)), AZUL), -45.0)
        sobre(img, a, sw - 140 - a.shape[1] / 2, 50 - a.shape[0] / 2)
    return img


def celular(n, p, ctx):
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    esc = p.get("escala", 1.0)
    lw, lh = int(600 * esc), int(1220 * esc)
    cx, cy = p.get("centro", (W / 2, 960))
    corpo_fone = ctx.cache("corpo", lambda: _fone_corpo(lw, lh))
    b = int(20 * esc)
    sw, sh_ = lw - 2 * b, lh - 2 * b
    mt = ctx.cache("mt", lambda: _ret_arred(sw, sh_, 0.12 * lw))
    # ---- a tela, desenhada em escala 1 (600 x 1220) e reduzida
    S = 1.0 / esc
    tw, th = int(sw * S), int(sh_ * S)
    tela = np.empty((th, tw, 3), np.float32); tela[:] = TELA
    q = n - p["inicio"]
    _tela_status(tela, tw, n, p)
    cab = p.get("cabecalho")
    y_chat = 120
    if cab:
        cv2.circle(tela, (70, 150), 36, (206.0, 206.0, 214.0), -1, cv2.LINE_AA)
        _escreve(tela, cab.get("inicial", cab["titulo"][:1]), 70, 132, le.INTER, 34, 800, (96.0, 96.0, 104.0), alinha="centro")
        _escreve(tela, cab["titulo"], 124, 118, le.INTER, 36, 800, (24.0, 24.0, 28.0))
        if cab.get("sub"):
            sub = cab["sub"]
            for tr in cab.get("sub_muda", []):
                if n >= tr["quadro"]:
                    sub = tr["texto"]
            _escreve(tela, sub, 124, 160, le.INTER, 26, 500, (120.0, 120.0, 128.0))
        tela[206:208, 20:tw - 20] = (220.0, 220.0, 226.0)
        y_chat = 236
    # conversa
    y = y_chat
    for bm in p.get("conversa", []):
        if bm.get("pensa") is not None and bm["pensa"] <= n < bm["quadro"]:
            m = _ret_arred(130, 70, 30)
            lay = _rgba(m, (233.0, 233.0, 238.0))
            for j in range(3):
                on = (n // 3) % 3 == j
                cv2.circle(lay, (34 + j * 31, 35), 10, ((110.0, 110.0, 118.0, 1.0) if on else (170.0, 170.0, 176.0, 1.0)), -1, cv2.LINE_AA)
            sobre(tela, lay, 28, y)
            y += 70 + 20
            continue
        if n < bm["quadro"]:
            continue
        e = mo.escala_palavra((n - bm["quadro"]) / FPS)
        if bm.get("tipo") == "imagem":
            lay = ctx.cache(("img", id(bm)), lambda: _icone("imagem", 360))
        elif bm.get("tipo") == "interface":
            lay = _cartao_interface(bm, n, int(bm.get("largura", 0.88) * tw))
        else:
            lay = ctx.cache(("bolha", bm["texto"], bm["lado"]), lambda bm=bm: _bolha(bm["texto"], bm["lado"], 0.76 * tw,
                                                                                bm.get("corpo", 34)))
        l = _escalar_rgba(lay, e)
        x = (tw - 28 - l.shape[1]) if bm["lado"] == "eu" else 28
        sobre(tela, l, x, y + (lay.shape[0] - l.shape[0]))
        for mk in bm.get("marcas", []):
            if n >= mk["quadro"]:
                s = _selo(mk["tipo"], 30)
                sobre(tela, s, x + l.shape[1] - 34, y + l.shape[0] - 40)
        y += lay.shape[0] + 20
    dl = p.get("download")
    if dl and n >= dl.get("quadro", p["inicio"]):
        _tela_download(tela, tw, th, n, dl)
    cn = p.get("canal")
    if cn:
        _tela_canal(tela, tw, th, n, cn)
    ent = p.get("entrada")
    if ent and ent.get("texto"):
        k = 0 if n < ent["quadro"] else min(len(ent["texto"]), ent.get("letras_por_degrau", 4) * ((n - ent["quadro"]) // 3 + 1))
        m = _ret_arred(tw - 56, 76, 38)
        lay = _rgba(m, (233.0, 233.0, 238.0))
        sobre(tela, lay, 28, th - 120)
        _escreve(tela, ent["texto"][:k] if k else "Mensagem", 56, th - 102, le.INTER, 32, 500,
                 (30.0, 30.0, 34.0) if k else (150.0, 150.0, 158.0))
    if esc != 1.0:
        tela = cv2.resize(tela, (sw, sh_), interpolation=cv2.INTER_AREA)
    fone = corpo_fone.copy()
    reg = fone[b:b + sh_, b:b + sw, :3]
    reg[:] = reg * (1 - mt[..., None]) + tela * mt[..., None]
    # ---- entrada do telefone (sobe) e colagem
    dy = 0.0
    if p.get("sobe", True):
        dy = (1 - mo.subida((q - 1) / FPS, 0.45, 0.11)) * 1100.0
    sh, pad = ctx.cache("sombra", lambda: _sombra_alfa(corpo_fone, (22, 40), 26.0, 0.45))
    sobre(img, sh, cx - lw / 2 - pad, cy - lh / 2 - pad + dy)
    sobre(img, fone, cx - lw / 2, cy - lh / 2 + dy)
    # ---- por fora do telefone: etiqueta, nuvem, carimbo
    et = p.get("etiqueta")
    if et and n >= et["quadro"]:
        cx_ = ctx.cache(("et", et["texto"]), lambda: _caixa_larga(et["texto"], et.get("corpo", 58)))
        ex, ey = et.get("pos", (790, 1380))
        if et.get("entra") == "pop":        # cresce no lugar: sob câmera fechada, a entrada pela direita cruza os botões do Reels
            _colar_centro(img, cx_, ex, ey, mo.escala_palavra((n - et["quadro"]) / FPS))
        else:
            x = ex + mo.entrada_caixa((n - et["quadro"]) / FPS)
            sobre(img, cx_, x - cx_.shape[1] / 2, ey - cx_.shape[0] / 2)
    nv = p.get("nuvem")
    if nv and n >= nv["quadro"]:
        e = mo.escala_palavra((n - nv["quadro"]) / FPS)
        nu = ctx.cache("nuvem", lambda: _icone("nuvem", nv.get("tam", 230), (60.0, 60.0, 66.0)))
        nx, ny = nv["pos"]
        _colar_centro(img, nu, nx, ny, e)
        if nv.get("seta") is not None and n >= nv["seta"]:
            g = min(1.0, (n - nv["seta"]) / 6.0)
            _seta(img, nv["de"], (nx - 60, ny + 70), g, (70.0, 70.0, 76.0), curva=-0.25, esp=4.0, semente=8, ponta=34)
        if nv.get("xis") is not None and n >= nv["xis"]:
            mx = ((nv["de"][0] + nx - 60) / 2 + 10, (nv["de"][1] + ny + 70) / 2 - 20)
            _xis_mao(img, mx, 44, min(1.0, (n - nv["xis"] + 3) / 6.0), VERMELHO, 10.0)
    ca = p.get("carimbo")
    tremor = 0.0
    if ca and n >= ca["quadro"]:
        k = (n - ca["quadro"]) // 3
        cor = np.array(_cor(ca.get("cor"), VERMELHO), np.float32)
        tinta = ctx.cache("tinta", lambda: _tinta_carimbo(ca["texto"], cor, ca.get("corpo", 150), ca.get("rot", -10.0)))
        es = (1.9, 1.25, 1.0)[min(k, 2)]
        a = tinta if es == 1.0 else cv2.resize(tinta, (int(tinta.shape[1] * es), int(tinta.shape[0] * es)), interpolation=cv2.INTER_CUBIC)
        al = (0.55, 0.9, 0.96)[min(k, 2)]
        px, py = ca.get("pos", (cx, cy))
        x0 = int(round(px - a.shape[1] / 2)); y0 = int(round(py - a.shape[0] / 2))
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + a.shape[1]), min(H, y0 + a.shape[0])
        if xa < xb and ya < yb:
            s = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * al
            reg = img[ya:yb, xa:xb]
            img[ya:yb, xa:xb] = reg * (1 - s) + (np.array((250.0, 246.0, 244.0)) * (cor / 255.0) * 0.92) * s
        tremor = (0.0, 9.0, -6.0, 3.0)[k] if 0 <= k < 4 else 0.0
    out = _camera(img, n, p, (1.0, 1.04), centro=(cx, cy))
    if tremor:
        out = cam(out, dy=tremor, fundo=tuple(float(v) for v in out[27, 27]))
    return out


def _tela_download(tela, tw, th, n, dl):
    cy = dl.get("y", 560)
    m = _ret_arred(tw - 80, 330, 36)
    lay = _rgba(m, (255.0, 255.0, 255.0))
    sh, pad = _sombra_alfa(lay, (0, 10), 14.0, 0.18)
    sobre(tela, sh, 40 - pad, cy - pad)
    sobre(tela, lay, 40, cy)
    _escreve(tela, dl["titulo"], 80, cy + 40, le.INTER, 44, 800, (24.0, 24.0, 28.0))
    if dl.get("sub"):
        _escreve(tela, dl["sub"], 80, cy + 100, le.INTER, 28, 500, (120.0, 120.0, 128.0))
    g = mv.suavizar_curva(u(n, dl["de"], dl["ate"]), "s", 1.6)
    x0, x1, yb = 80, tw - 80, cy + 190
    trilho = _ret_arred(x1 - x0, 22, 11)
    sobre(tela, _rgba(trilho, (226.0, 226.0, 232.0)), x0, yb)
    if g > 0.01:
        fw = max(22, int((x1 - x0) * g))
        sobre(tela, _rgba(_ret_arred(fw, 22, 11), AZUL), x0, yb)
    pr = dl.get("pronto")
    if pr is not None and n >= pr:
        e = mo.escala_palavra((n - pr) / FPS)
        s = _escalar_rgba(_selo("certo", 34), e)
        sobre(tela, s, x0, yb + 50)
        _escreve(tela, dl.get("texto_pronto", "Instalado no aparelho"), x0 + 86, yb + 58, le.INTER, 32, 700, (24.0, 24.0, 28.0))
    else:
        _escreve(tela, f"{int(round(100 * g))}%", x0, yb + 54, le.INTER, 32, 700, (120.0, 120.0, 128.0))


def _tela_canal(tela, tw, th, n, cn):
    y0 = 236
    cv2.circle(tela, (int(tw / 2), y0 + 120), 92, (206.0, 206.0, 214.0), -1, cv2.LINE_AA)
    le.escrever(tela, cn.get("inicial", "C"), centro=(tw / 2, y0 + 120), fonte=le.INTER, corpo=80, cor=(110.0, 110.0, 118.0), peso=800)
    if cn.get("nome"):
        _escreve(tela, cn["nome"], tw / 2, y0 + 250, le.INTER, 42, 800, (24.0, 24.0, 28.0), alinha="centro")
    else:                                                  # nome de verdade nao aparece: so a barra do nome
        sobre(tela, _rgba(_ret_arred(300, 34, 17), (206.0, 206.0, 214.0)), tw / 2 - 150, y0 + 254)
    _escreve(tela, cn.get("tipo", "Canal"), tw / 2, y0 + 308, le.INTER, 30, 600, (110.0, 110.0, 118.0), alinha="centro")
    co = cn.get("conta")
    if co and n >= co["de"]:
        g = _cresce(n, co["de"], max(3, co["ate"] - co["de"]), 2.4)
        num = _formata(co.get("formato", "3.000.000"), co["valor"] * g)
        corpo = 92
        _escreve(tela, num, tw / 2, y0 + 400, le.INTER, corpo, 800, (24.0, 24.0, 28.0), alinha="centro")
        _escreve(tela, co.get("rotulo", "seguidores"), tw / 2, y0 + 520, le.INTER, 34, 500, (120.0, 120.0, 128.0), alinha="centro")
    for k in range(4):
        yy = y0 + 640 + k * 96
        m = _ret_arred(tw - 120, 70, 24)
        sobre(tela, _rgba(m, (236.0, 236.0, 240.0)), 60, yy)
    fora = cn.get("derrubado")
    volta = cn.get("volta")
    if fora is not None and n >= fora and (volta is None or n < volta):
        tela *= 0.55
        tela += 0.45 * 120.0
        m = _ret_arred(tw - 100, 200, 30)
        lay = _rgba(m, (36.0, 36.0, 40.0))
        sobre(tela, lay, 50, th / 2 - 100)
        _escreve(tela, cn.get("texto_fora", "Canal indisponível"), tw / 2, th / 2 - 46, le.INTER, 42, 800,
                 (246.0, 246.0, 248.0), alinha="centro")
    if volta is not None and n >= volta:
        e = mo.escala_palavra((n - volta) / FPS)
        s = _escalar_rgba(_selo("certo", 40), e)
        sobre(tela, s, tw / 2 + 120, y0 + 160)


# ====================================================================== 41. icones
def icones(n, p, ctx):
    f = p.get("fundo", "canvas")
    img = _parede(ctx) if f == "parede" else _fundo(ctx, dict(p, fundo=f))
    dv = p.get("divisor")
    if dv and n >= dv.get("quadro", p["inicio"]):
        g = min(1.0, (n - dv.get("quadro", p["inicio"]) + 3) / 6.0)
        yd = dv.get("y", 960)
        x0, x1 = 110, 970
        pts = np.stack([np.linspace(x0, x0 + (x1 - x0) * g, 20), np.full(20, yd)], 1)

        def d(m, ss):
            _traco(m, pts, 4.0, 11, 1.0, ss)
        sobre(img, _camada_traco(d, (120.0, 120.0, 126.0)))
    _titulo(img, n, p, 330)
    for lg in p.get("ligacoes", []):
        a_, b_ = p["itens"][lg["de"]], p["itens"][lg["para"]]
        if n >= lg["quadro"] and n >= a_["quadro"] and n >= b_["quadro"]:
            g = min(1.0, (n - lg["quadro"] + 3) / 6.0)
            (x0, y0), (x1, y1) = a_["pos"], b_["pos"]
            cv2.line(img, (int(x0), int(y0)), (int(x0 + (x1 - x0) * g), int(y0 + (y1 - y0) * g)),
                     _cor(lg.get("cor"), (150.0, 150.0, 156.0)), 4, cv2.LINE_AA)
    for i, it in enumerate(p["itens"]):
        if n < it["quadro"]:
            continue
        t = n - it["quadro"]
        e = mo.escala_palavra(t / FPS)
        cor = _cor(it.get("cor"))
        nome = it["icone"]
        lay = (_icone(nome, it.get("tam", 360), cor, t) if nome == "relogio"
               else ctx.cache(("ic", i), lambda it=it, cor=cor: _icone(it["icone"], it.get("tam", 360), cor)))
        x, y = it["pos"]
        _colar_centro(img, lay, x, y, e, {"desloc": (10, 18), "blur": 12.0, "forca": 0.28} if it.get("sombra", True) else None)
        hh, ww = lay.shape[0] * e, lay.shape[1] * e
        rt = it.get("rotulo")
        if rt and n >= rt.get("quadro", it["quadro"]):
            er = mo.escala_palavra((n - rt.get("quadro", it["quadro"])) / FPS)
            fonte = le.SERIFA if rt.get("fonte", "serifa") == "serifa" else le.INTER
            pos = rt.get("pos", (x, y + lay.shape[0] / 2 + rt.get("dy", 90)))
            le.escrever(img, rt["texto"], centro=tuple(pos), fonte=fonte, corpo=rt.get("corpo", 110),
                        cor=_cor(rt.get("cor")), contorno=1.0 if fonte == le.SERIFA else 0.0,
                        peso=None if fonte == le.SERIFA else 800, escala=er)
        for chave, tipo in (("certo", "certo"), ("xis", "xis")):
            q0 = it.get(chave)
            if q0 is not None and n >= q0:
                es = mo.escala_palavra((n - q0) / FPS)
                s = _escalar_rgba(_selo(tipo, it.get("raio_selo", 52)), es)
                sobre(img, s, x + ww / 2 - s.shape[1] * 0.7, y + hh / 2 - s.shape[0] * 0.7)
        rq = it.get("risco")
        if rq is not None and n >= rq:
            g = min(1.0, (n - rq + 3) / 6.0)
            p0 = (x - ww * 0.62, y + hh * 0.55); p1 = (x + ww * 0.62, y - hh * 0.55)
            pts = np.stack([np.linspace(p0[0], p0[0] + (p1[0] - p0[0]) * g, 16), np.linspace(p0[1], p0[1] + (p1[1] - p0[1]) * g, 16)], 1)

            def d(m, ss, pts=pts):
                _traco(m, pts, 14.0, 9, 1.2, ss)
            sobre(img, _camada_traco(d, VERMELHO))
    for tx in p.get("textos", []):                   # palavras soltas (serifa) em qualquer ponto do quadro
        if tx["quadro"] <= n < tx.get("ate", 10 ** 9):
            le.escrever(img, tx["texto"], centro=tuple(tx["pos"]), fonte=le.SERIFA, corpo=tx.get("corpo", 120),
                        cor=_cor(tx.get("cor")), contorno=1.0, escala=mo.escala_palavra((n - tx["quadro"]) / FPS))
    for k, sa in enumerate(p.get("setas", [])):
        if n >= sa["quadro"]:
            g = min(1.0, (n - sa["quadro"]) / 6.0)
            _seta(img, sa["de"], sa["para"], g, _cor(sa.get("cor")), sa.get("curva", 0.15), sa.get("esp", 6.0), 5 + k, 42)
            if sa.get("xis") is not None and n >= sa["xis"]:
                mx = ((sa["de"][0] + sa["para"][0]) / 2, (sa["de"][1] + sa["para"][1]) / 2)
                _xis_mao(img, mx, 46, min(1.0, (n - sa["xis"] + 3) / 6.0), VERMELHO, 11.0)
    return _camera(img, n, p, (1.0, 1.04))


# ====================================================================== 42. semana
def semana(n, p, ctx):
    img = _parede(ctx) if p.get("fundo", "parede") == "parede" else _fundo(ctx, p)
    dias = p["dias"]
    cw = p.get("largura_dia", 128)
    larg = len(dias) * cw + 40
    alt = 120 + 270 + 30

    def _card():
        f = np.empty((alt, larg, 3), np.float32); f[:] = FOLHA
        f[:112] = VERMELHO
        le.escrever(f, p.get("mes", "OUTUBRO"), centro=(larg / 2, 60), fonte=le.INTER, corpo=56, cor=(244.0, 240.0, 232.0),
                    peso=800, tracking=8.0)
        f[112:115] = (120.0, 20.0, 24.0)
        for i, (sem, dia) in enumerate(dias):
            x = 20 + i * cw
            if i:
                f[132:alt - 24, x:x + 2] = (206.0, 204.0, 200.0)
            if p.get("sem_numero"):                     # "em uma semana": só o dia da semana, sem data (a marca vai em cima)
                le.escrever(f, sem, centro=(x + cw / 2, 352), fonte=le.INTER, corpo=40, cor=TINTA_D, peso=800, tracking=2.0)
                continue
            le.escrever(f, sem, centro=(x + cw / 2, 168), fonte=le.INTER, corpo=30, cor=(120.0, 116.0, 112.0), peso=800,
                        tracking=2.0)
            le.escrever(f, str(dia), centro=(x + cw / 2, 290), fonte=le.SERIFA, corpo=150, cor=TINTA_D, contorno=1.5)
        return f
    base = ctx.cache("card", _card)
    f = base.copy()
    idx = {d[1]: i for i, d in enumerate(dias)}
    for dia in p.get("riscados", []):
        i = idx[dia]
        _xis_card(f, (20 + i * cw + cw / 2, 285), 44, 1.0, semente=dia)
    sq = p.get("sequencia")                             # a semana passando: uma marca por dia, uma a cada `passo` quadros
    if sq:
        for i in range(len(dias)):
            q0 = sq["de"] + i * sq.get("passo", 3)
            if n >= q0:
                c = (20 + i * cw + cw / 2, 285 if not p.get("sem_numero") else 222)
                if sq.get("marca") == "certo":
                    _certo_card(f, c, 36 if p.get("sem_numero") else 40)
                else:
                    _xis_card(f, c, 38 if p.get("sem_numero") else 44, min(1.0, (n - q0 + 2) / 4.0), semente=i + 1)
    at = p.get("ativo")
    if at is not None and n >= p["quadro"]:
        i = idx[at]
        fr = min(1.0, (n - p["quadro"] + 3) / 9.0)
        _circulo_card(f, (20 + i * cw + cw / 2, 290), cw * 0.52, 100, fr)
    card = _com_sombra(f, p.get("rot", -1.2), pad=60, desloc=(10, 24), blur=20.0, forca=0.42)
    cx, cy = W / 2, p.get("y", 900)
    sobre(img, card, cx - card.shape[1] / 2, cy - card.shape[0] / 2)
    if at is not None and not p.get("camera"):
        i = idx[at]
        ax = cx - larg / 2 + 20 + i * cw + cw / 2
        z = mv.entre(1.0, p.get("zoom", 1.22), mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 1.6))
        anc_x = mv.entre(W / 2, ax, mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 1.6))
        return cam(img, z=z, dx=z * (W / 2 - anc_x), dy=z * (H / 2 - (cy + 40)), fundo=tuple(float(v) for v in img[27, 27]))
    return _camera(img, n, p, (1.0, 1.05), centro=(cx, cy))


def _circulo_card(f, centro, rx, ry, frac):
    if frac <= 0.02:
        return
    rng = np.random.default_rng(12)
    k = 80
    ang = -2.4 + np.linspace(0, frac * 2 * math.pi * 1.08, k)
    r = 1 + np.cumsum(rng.normal(0, 0.01, k))
    pts = np.stack([centro[0] + rx * r * np.cos(ang), centro[1] + ry * r * np.sin(ang)], 1)
    m = np.zeros(f.shape[:2], np.uint8)
    cv2.polylines(m, [np.int32(pts * 4)], False, 255, 28, cv2.LINE_AA, shift=2)
    a = (m.astype(np.float32) / 255.0)[..., None] * 0.92
    f[:] = f * (1 - a) + np.array(VERMELHO) * a


def _certo_card(f, centro, r):
    x, y = centro
    m = np.zeros(f.shape[:2], np.uint8)
    pts = np.array([[x - r, y], [x - r * 0.25, y + r * 0.75], [x + r * 1.1, y - r * 0.9]])
    cv2.polylines(m, [np.int32(pts * 4)], False, 255, 34, cv2.LINE_AA, shift=2)
    al = (m.astype(np.float32) / 255.0)[..., None] * 0.92
    f[:] = f * (1 - al) + np.array(AZUL) * al


def _xis_card(f, centro, r, frac, semente=1):
    x, y = centro
    m = np.zeros(f.shape[:2], np.uint8)
    rng = np.random.default_rng(semente)
    for (a, b) in (((x - r, y - r), (x + r, y + r)), ((x + r, y - r), (x - r, y + r))):
        pts = np.stack([np.linspace(a[0], b[0], 10), np.linspace(a[1], b[1], 10)], 1) + rng.normal(0, 1.0, (10, 2))
        cv2.polylines(m, [np.int32(pts * 4)], False, 255, 36, cv2.LINE_AA, shift=2)
    al = (m.astype(np.float32) / 255.0)[..., None] * 0.85
    f[:] = f * (1 - al) + np.array(VERMELHO) * al


# ====================================================================== 43. linha_no_papel
def linha_no_papel(n, p, ctx):
    """Uma linha centrada que se monta palavra a palavra no papel (cada palavra com sua cor):
    "PROMESSA ≠ ENTREGA". Cada palavra entra a 70% e cresce como a palavra do Hedy. Sinal que a
    serifa nao tem (≠ → ✓ ×) sai na Inter, na mesma altura."""
    img = _fundo(ctx, p)
    ws = p["palavras"]
    corpo = p.get("corpo", 150)
    fonte_de = lambda t: le.INTER if any(c in t for c in "≠→←↓↑✓×") else le.SERIFA
    esp = _largura(" ", le.SERIFA, corpo)
    larguras = [_largura(w["texto"], fonte_de(w["texto"]), corpo) for w in ws]
    total = sum(larguras) + esp * (len(ws) - 1)
    if total > 900:
        k = 900 / total
        corpo *= k; esp *= k; larguras = [l * k for l in larguras]; total = 900
    yc = p.get("y", 900)
    x = W / 2 - total / 2
    for w, lw in zip(ws, larguras):
        x_meio = x + lw / 2
        x += lw + esp
        if n < w["quadro"]:
            continue
        e = mo.escala_palavra((n - w["quadro"]) / FPS)
        fonte = fonte_de(w["texto"])
        le.escrever(img, w["texto"], centro=(x_meio, yc), fonte=fonte, corpo=corpo * (0.8 if fonte == le.INTER else 1.0),
                    cor=_cor(w.get("cor")), contorno=1.0 if fonte == le.SERIFA else 0.0,
                    peso=None if fonte == le.SERIFA else 500, escala=e)
        if w.get("risco") is not None and n >= w["risco"]:
            g = min(1.0, (n - w["risco"] + 3) / 6.0)
            hw = lw / 2 + 16
            pts = np.stack([np.linspace(x_meio - hw, x_meio - hw + 2 * hw * g, 14), np.linspace(yc + 10, yc - 6, 14)], 1)

            def d(m, ss, pts=pts):
                _traco(m, pts, 11.0, 4, 1.0, ss)
            img = sobre(img, _camada_traco(d, VERMELHO))
    sa = p.get("seta")
    if sa and n >= sa["quadro"]:
        _seta(img, sa["de"], sa["para"], min(1.0, (n - sa["quadro"]) / 6.0), _cor(sa.get("cor")), sa.get("curva", 0.1), 7.0, 5, 44)
    return _camera(img, n, p, (1.0, 1.05), centro=(W / 2, yc))


# ====================================================================== 44. botao_cta
def botao_cta(n, p, ctx):
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    q = n - p["inicio"]
    cx, cy = p.get("centro", (W / 2, 1010))
    bw, bh = p.get("tamanho", (560, 156))
    qc = p["quadro_clique"]
    seguindo = n >= qc + 3
    for w in p.get("palavras", []):
        if n >= w["quadro"]:
            e = mo.escala_palavra((n - w["quadro"]) / FPS)
            le.escrever(img, w["texto"], centro=(W / 2, w.get("y", 690)), fonte=le.SERIFA, corpo=w.get("corpo", 120),
                        cor=_cor(w.get("cor")), contorno=1.0, escala=e)
    ent = mo.escala_palavra((q - 1) / FPS) if q >= 1 else 0.0
    aperta = qc <= n < qc + 3
    e = ent * (0.93 if aperta else 1.0)
    if e > 0.05:
        m = _ret_arred(bw * e, bh * e, bh * e / 2)
        cor = (226.0, 226.0, 230.0) if seguindo else AZUL
        lay = _rgba(m, cor)
        if seguindo:
            k = 5
            aro = np.clip(m - cv2.erode(m, np.ones((k, k), np.uint8)), 0, 1)
            lay[..., :3] = lay[..., :3] * (1 - aro[..., None]) + np.array((190.0, 190.0, 198.0)) * aro[..., None]
        _colar_centro(img, lay, cx, cy, 1.0, {"desloc": (0, 18), "blur": 18.0, "forca": 0.30 if not seguindo else 0.18})
        texto = p.get("texto_depois", "Seguindo") if seguindo else p.get("texto", "Seguir")
        corpo = 62 * e
        tcor = TINTA_D if seguindo else (250.0, 250.0, 252.0)
        if seguindo:
            tw_ = _largura(texto, le.INTER, corpo, 800)
            s = _selo("certo", 30 * e)
            x_txt = cx - tw_ / 2 + 30
            sobre(img, s, x_txt - 30 - s.shape[1], cy - s.shape[0] / 2)
            le.escrever(img, texto, centro=(x_txt + tw_ / 2, cy), fonte=le.INTER, corpo=corpo, cor=tcor, peso=800)
        else:
            le.escrever(img, texto, centro=(cx, cy), fonte=le.INTER, corpo=corpo, cor=tcor, peso=800)
    try:
        cur, hx, hy = ctx.cache("cursor", lambda: _cursor_sistema(p.get("cursor", "cursor_pointinghand.png"), 66.0))
    except FileNotFoundError:
        cur = None
    if cur is not None and q >= 2:
        alvo = (cx + 60, cy + 22)
        ini = (cx + 380, cy + 640)
        g = mv.suavizar_curva(u(n, p["inicio"] + 2, qc - 1), "saida", 2.6)
        x = ini[0] + (alvo[0] - ini[0]) * g; y = ini[1] + (alvo[1] - ini[1]) * g
        if n >= qc + 6:
            g2 = mv.suavizar_curva(u(n, qc + 6, qc + 18), "saida", 2.0)
            x += 130 * g2; y += 160 * g2
        sobre(img, cur, x - hx, y - hy)
    return _camera(img, n, p, (1.0, 1.05), centro=(cx, cy - 120))


# ====================================================================== 46. escala_semana
DIAS_SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


def escala_semana(n, p, ctx):
    """A escala de trabalho em blocos: cada dia é um bloco escuro (trabalho) ou azul (folga). `semanas` são as linhas
    ("TTTTTTF" = 6x1); `muda` vira, um por degrau a partir do quadro, os blocos que mudam (com um pulo); `nome_escala`
    grande embaixo ("6x1" -> "5x2", com muda.rotulo); `destaque` circula um dia (o domingo); `legenda` explica as cores."""
    img = _fundo(ctx, dict(p, fundo=p.get("fundo", "canvas")))
    sem = p["semanas"]
    mu = p.get("muda")
    bw, gap = p.get("largura_bloco", 116), p.get("gap", 14)
    bh = p.get("altura_bloco", 150 if len(sem) == 1 else 104)
    tw = 7 * bw + 6 * gap
    x0 = W / 2 - tw / 2
    y0 = p.get("y", 860 - (len(sem) - 1) * (bh + gap) / 2 - bh / 2)
    for j, d in enumerate(p.get("dias", DIAS_SEMANA)):
        le.escrever(img, d, centro=(x0 + j * (bw + gap) + bw / 2, y0 - 44), fonte=le.INTER, corpo=30,
                    cor=(110.0, 110.0, 118.0), peso=800, tracking=2.0)
    if p.get("titulo") and n >= p["titulo"].get("quadro", p["inicio"]):
        le.escrever(img, p["titulo"]["texto"], centro=(W / 2, y0 - 130), fonte=le.INTER, corpo=p["titulo"].get("corpo", 36),
                    cor=(110.0, 110.0, 118.0), peso=800, tracking=3.0)
    k = 0
    for r, est in enumerate(sem):
        alvo = mu["semanas"][r] if mu else est
        for j in range(7):
            e, esc = est[j], 1.0
            if mu and alvo[j] != est[j]:
                qf = mu["quadro"] + 3 * k
                k += 1
                if n >= qf:
                    e = alvo[j]
                    esc = 1.0 + 0.22 * math.exp(-(n - qf) / 4.0)
            cor = AZUL if e == "F" else TINTA_D
            ww, hh = bw * esc, bh * esc
            xc, yc = x0 + j * (bw + gap) + bw / 2, y0 + r * (bh + gap) + bh / 2
            m = _ret_arred(ww, hh, 0.12 * bw)
            sobre(img, _rgba(m, cor), xc - m.shape[1] / 2, yc - m.shape[0] / 2)
            if p.get("letras", True):
                le.escrever(img, "F" if e == "F" else "T", centro=(xc, yc), fonte=le.INTER, corpo=0.30 * bh * esc,
                            cor=(244.0, 244.0, 246.0), peso=800)
    de = p.get("destaque")
    if de and n >= de["quadro"]:
        j = de["dia"]; r = de.get("semana", 0)
        xc, yc = x0 + j * (bw + gap) + bw / 2, y0 + r * (bh + gap) + bh / 2
        _circulo_mao(img, (xc, yc), bw * 0.78, bh * 0.72, min(1.0, (n - de["quadro"] + 3) / 9.0), VERMELHO, 7.0)
        if de.get("texto"):
            le.escrever(img, de["texto"], centro=(xc - 40, yc + bh * 0.72 + 80), fonte=le.SERIFA, corpo=de.get("corpo", 96),
                        cor=VERMELHO, contorno=1.0, escala=mo.escala_palavra((n - de["quadro"]) / FPS))
    ro = p.get("nome_escala")
    if ro and n >= ro.get("quadro", p["inicio"]):
        txt = ro["texto"]
        if mu and mu.get("rotulo") and n >= mu["quadro"] + 3 * max(0, k - 1):
            txt = mu["rotulo"]
        ybase = y0 + len(sem) * (bh + gap) + ro.get("dy", 170)
        le.escrever(img, txt, centro=(W / 2, ybase), fonte=le.SERIFA, corpo=ro.get("corpo", 230), cor=TINTA_D, contorno=1.5,
                    escala=mo.escala_palavra((n - ro.get("quadro", p["inicio"])) / FPS))
    lg = p.get("legenda")
    if lg and n >= lg.get("quadro", p["inicio"]):
        yl = lg.get("y", 1560)
        for i, (cor, txt) in enumerate(((TINTA_D, "trabalho"), (AZUL, "folga"))):
            xl = W / 2 - 230 + i * 300
            mq = _ret_arred(44, 44, 8)
            sobre(img, _rgba(mq, cor), xl - 22, yl - 22)
            le.escrever(img, txt, esquerda=(xl + 40, yl), fonte=le.SERIFA, corpo=64, cor=TINTA_D, contorno=1.0)
    for t in p.get("textos", []):
        if n >= t["quadro"]:
            le.escrever(img, t["texto"], centro=tuple(t["pos"]), fonte=le.SERIFA, corpo=t.get("corpo", 110),
                        cor=_cor(t.get("cor"), TINTA_D), contorno=1.0, escala=mo.escala_palavra((n - t["quadro"]) / FPS))
    return _camera(img, n, p, (1.0, 1.05), centro=(W / 2, y0 + len(sem) * (bh + gap) / 2))


TIPOS_NOTICIA = {
    "ranking": ranking, "terminal": terminal, "podio": podio, "barras": barras, "centena": centena,
    "pizzas": pizzas, "celular": celular, "icones": icones, "semana": semana, "linha_no_papel": linha_no_papel,
    "botao_cta": botao_cta, "escala_semana": escala_semana,
}
