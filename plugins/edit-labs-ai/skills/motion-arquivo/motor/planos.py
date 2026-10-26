"""
Planos da Familia A — a biblioteca generica.

Cada tipo e uma funcao  TIPO(n, p, ctx) -> imagem (H, W, 3) float, ANTES do acabamento.

  n    quadro absoluto da grade de 10 qps (o render so chama n % 3 == 2)
  p    o dicionario do plano no plano.json: inicio, fim, textos, assets, tempos
  ctx  Contexto do plano (cache)

Tempos dentro de p sao QUADROS ABSOLUTOS a 30 qps, ja ancorados na fala
(ferramentas/batidas.py). Tempo de palavra com fracao ("t": 145.6) e o instante exato em
que ela comeca a ser dita — usado nos fades continuos. Os padroes numericos sao os do
Hedy medido; cada tipo diz de qual plano saiu. O porque de cada numero esta em
referencias/gramatica.md e o catalogo com exemplos em referencias/planos.md.
"""
import math
import numpy as np
import cv2
from familia_a import W, H
from familia_a import c1_background as bg, c2_letras as le, c3_style as st
from familia_a import c4_filtro as fi, c5_movimentos as mv, c6_motion as mo
from familia_a.compor import sobre

FPS = 30
BRANCO = (238.0, 236.0, 232.0)
PRETO_TINTA = (24.0, 20.0, 22.0)
CINZA_TEXTO = (194.0, 194.0, 194.0)       # grotesca sobre escuro: nucleo p90 200 no original


class Ctx:
    def __init__(self):
        self.c = {}

    def cache(self, k, fn):
        if k not in self.c:
            self.c[k] = fn()
        return self.c[k]


# --------------------------------------------------------------------- auxiliares
def u(n, a, b):
    return 1.0 if b == a else min(1.0, max(0.0, (n - a) / float(b - a)))


def cam(img, z=1.0, dx=0.0, dy=0.0, fundo=None):
    return mv.camera(img, dx=dx, dy=dy, zoom=z, fundo=fundo)


def zoom_em(img, z, ancora, dx=0.0, dy=0.0, fundo=None):
    """Zoom em torno de um ponto da TELA (o sujeito fica parado e o mundo escala em volta)."""
    return mv.camera(img, dx=(1 - z) * (ancora[0] - W / 2) + dx, dy=(1 - z) * (ancora[1] - H / 2) + dy,
                     zoom=z, fundo=fundo)


def degrau(tab, q):
    """Valor de uma tabela {quadro_relativo: valor} no ultimo degrau <= q."""
    ks = [k for k in tab if k <= q]
    return tab[max(ks)] if ks else None


def interp(tab, q):
    ks = sorted(tab)
    return float(np.interp(q, ks, [tab[k] for k in ks]))


def assenta(q, excesso, tau):
    """Revelacao: 1 + excesso * e^(-q/tau). Abre de 1+excesso para 1 em ease-out exponencial."""
    return 1.0 + excesso * math.exp(-max(0.0, q) / tau)


def fade_palavra(n, t, dur=6.0):
    """Fade linear de 0,2 s a partir do instante EXATO em que a palavra comeca a ser dita,
    amostrado na grade: e o que faz cada palavra chegar numa opacidade diferente
    (roteador do Hedy: 41/86/99%, 8/79/96%, 6/56/92%)."""
    return min(1.0, max(0.0, (n - t) / dur))


def _sobre_pre(lay, src, x, y, alfa=1.0):
    """Cola RGBA (alfa 0-255 ou 0-1) numa camada PREMULTIPLICADA."""
    h, w = src.shape[:2]; x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y); xb, yb = min(W, x + w), min(H, y + h)
    if xa >= xb or ya >= yb:
        return lay
    s = src[ya - y:yb - y, xa - x:xb - x]
    a = s[..., 3:4] / (255.0 if src[..., 3].max() > 1.5 else 1.0) * alfa
    lay[ya:yb, xa:xb, :3] = s[..., :3] * a + lay[ya:yb, xa:xb, :3] * (1 - a)
    lay[ya:yb, xa:xb, 3:4] = a + lay[ya:yb, xa:xb, 3:4] * (1 - a)
    return lay


def _compor_pre(img, lay):
    return lay[..., :3] + img * (1 - lay[..., 3:4])


def _escala_ink(a, largura_tinta):
    """Redimensiona um RGBA pela largura da TINTA; devolve (img, centro_x, centro_y) da tinta."""
    al = a[..., 3]
    ys, xs = np.nonzero(al > (10 if al.max() > 1.5 else 0.04))
    k = largura_tinta / float(xs.max() - xs.min() + 1)
    r = cv2.resize(a, (max(1, int(round(a.shape[1] * k))), max(1, int(round(a.shape[0] * k)))),
                   interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
    return r, (xs.min() + xs.max()) / 2 * k, (ys.min() + ys.max()) / 2 * k


def casar_cor(a, mapa):
    """Mapa linear por canal ((ganho, soma) x3), tirado de DUAS cores-ancora medidas."""
    a = a.copy()
    for c, (g, o) in enumerate(mapa):
        a[..., c] = a[..., c] * g + o
    return a


def foto_quadro(ctx, nome, n, cx, cy, s, dx=0.0, dy=0.0, pb=False, grao=True):
    a = ctx.cache(("pb_" if pb else "") + nome, lambda: st.pb(st.carregar(nome)) if pb else st.carregar(nome))
    img = st.foto_no_quadro(a, cx, cy, s, dx, dy)
    return fi.grao_foto(img, n) if grao else img


def escala_cobrir(a):
    return max(W / a.shape[1], H / a.shape[0])


def aplicar_exposicao(img, p):
    """ganho: numero (luz) ou [r, g, b] (cor media do plano casada por canal); saturacao."""
    g = p.get("ganho")
    sat = p.get("saturacao")
    if isinstance(g, (list, tuple)):
        img = img * np.array(g, np.float32)
        g = None
    if g is not None or sat is not None:
        img = fi.corrigir(img, g if g is not None else 1.0, sat if sat is not None else 1.0)
    return img


def linha_letras(img, texto, k, esquerda, yc, corpo, fonte=le.SERIFA, peso=None, cor=BRANCO, contorno=0.0):
    """Linha que cresce letra a letra a partir de uma borda esquerda de TINTA fixa."""
    if k <= 0:
        return img
    cheio, (ox, oy) = le.mascara(texto, fonte, corpo, peso, contorno)
    topo = yc - cheio.size[1] / 2 + oy
    f = le._fonte(fonte, int(round(corpo * le.SS)), peso)
    x = esquerda + ox
    for ch in texto[:k]:
        if ch != " ":
            m, (mx, my) = le.mascara(ch, fonte, corpo, peso, contorno)
            le.tingir(img, m, x - mx, topo - my, cor)
        x += f.getlength(ch) / le.SS
    return img


def linha_palavras(img, palavras, n, xc, yc, corpo, fonte=le.SERIFA, cor=le.TINTA, contorno=0.8, modo="degrau"):
    """Linha centrada que se monta palavra a palavra. palavras = [{"texto", "quadro" | "t"}].
    modo "degrau": 45% no 1o degrau e firme no seguinte (moldura do Hedy);
    modo "fade": fade continuo a partir de "t" (roteador do Hedy)."""
    texto = " ".join(w["texto"] for w in palavras)
    cheio, (ox, oy) = le.mascara(texto, fonte, corpo, None, contorno)
    xx = xc - cheio.size[0] / 2
    f = le._fonte(fonte, int(round(corpo * le.SS)))
    topo = yc - cheio.size[1] / 2 + oy
    pos = 0
    for w in palavras:
        i = texto.index(w["texto"], pos); pos = i + len(w["texto"])
        if modo == "fade":
            a = fade_palavra(n, w.get("t", w.get("quadro", 0)))
        else:
            ap = w["quadro"]
            a = 0.0 if n < ap else (0.45 if n < ap + 3 else 1.0)
        if a > 0:
            m, (mx, my) = le.mascara(w["texto"], fonte, corpo, None, contorno)
            le.tingir(img, m, xx + ox + f.getlength(texto[:i]) / le.SS - mx, topo - my, cor, a)
    return img


# ============================================================ 1. gancho_digitado
# Hedy plano 1 (EVERYONE). Papel quadriculado escuro entra no 1o degrau junto com a 1a
# letra; a camera inteira fecha de 0,764 para 1 (1 - 0,236 e^(-q/4,3)); so a letra nova de
# cada degrau se mexe (cai e acende; a primeira tambem menor e inclinada); no ultimo
# degrau antes do corte so o texto escorrega 40 px para a esquerda com borrao de 14 px.
GANCHO_FRACOES = (0.125, 0.625, 0.875, 1.0)
GANCHO_NOVA = [dict(queda=50.7, alfa=0.73, escala=0.85, cisalha=12.0), dict(queda=35.8, alfa=0.79),
               dict(queda=22.3, alfa=0.91), dict(queda=40.1, alfa=0.79)]
GANCHO_MAIUSCULA = 67.4
GANCHO_TRACKING = -0.1157               # x altura da maiuscula
GANCHO_LARGURA_MAX = 0.80 * W


def gancho_digitado(n, p, ctx):
    t0 = p.get("primeira_letra", p["inicio"] + 2)
    if n < t0:
        return bg.chapado(bg.PRETO_EVERY)
    q = n - t0; j = q // 3
    z = 1 - 0.236 * math.exp(-q / 4.3)
    img = bg.grade_escura_no_quadro(z) if p.get("fundo", "grade") == "grade" else bg.chapado(bg.PRETO_EVERY)
    texto = p["texto"]; L = len(texto)

    def _medidas():
        cap = GANCHO_MAIUSCULA
        corpo = le.corpo_para_maiuscula(cap)
        larg = le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO, 0.0, GANCHO_TRACKING * cap)[0].size[0]
        if larg > GANCHO_LARGURA_MAX:
            cap *= GANCHO_LARGURA_MAX / larg
            corpo = le.corpo_para_maiuscula(cap)
            larg = le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO, 0.0, GANCHO_TRACKING * cap)[0].size[0]
        return corpo, GANCHO_TRACKING * cap, larg
    corpo, trk, larg = ctx.cache("medidas", _medidas)
    passos = GANCHO_FRACOES if L <= 10 else tuple(np.linspace(1.0 / L, 1.0, max(4, round(L / 2.5))))
    k = L if j >= len(passos) else max(1, int(round(L * passos[j])))
    nova = GANCHO_NOVA[min(j, len(GANCHO_NOVA) - 1)] if j < len(passos) else None
    xc, yc = p.get("centro", (529.3, 958.5))
    lay = le.linha_digitada(texto, k, xc - larg / 2, yc, corpo=corpo, tracking=trk, cor=CINZA_TEXTO, nova=nova)
    saindo = p.get("saida", True) and n >= p["fim"] - 3
    lay = cam(lay, z=z, dx=-40.0 * z if saindo else 0.0, fundo=CINZA_TEXTO + (0.0,))
    if saindo:
        lay[..., 3] = mv.borrao_direcional(lay[..., 3], 14.0)
    return sobre(img, lay)


# ============================================================ 2. palavra_no_papel
# Hedy planos 10 e 16. Uma palavra por vez, serifa italica corpo 86, centrada pela tinta,
# entra a 70% e cresce em ease-out (70 -> 91 -> 97 -> 99%); sai seca quando a proxima entra.
_CORPO_CABE = {}


def _corpo_cabe(texto, maximo=900.0, base=None):
    """Corpo da serifa em que `texto` cabe em `maximo` px (frase de 3-4 palavras num gancho)."""
    base = base or le.CORPO
    k = (texto, maximo, base)
    if k not in _CORPO_CABE:
        l = le.mascara(texto, le.SERIFA, base, None, le.CONTORNO)[0].size[0]
        _CORPO_CABE[k] = base if l <= maximo else base * maximo / l
    return _CORPO_CABE[k]


def _caixa_larga(texto, corpo=58):
    """Caixa azul de interface (mesmo estilo de st.caixa_ui) com largura que acompanha o texto."""
    m = le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO)[0]
    a = np.asarray(m, np.float32) / 255.0
    w, h = m.size[0] + 96, m.size[1] + 60
    sx, sy = st.SOMBRA_DESLOC
    lay = np.zeros((h + sy, w + sx, 4), np.float32)
    lay[sy:, sx:, :3] = st.SOMBRA; lay[sy:, sx:, 3] = 1.0
    lay[:h, :w, :3] = st.FILETE; lay[:h, :w, 3] = 1.0
    f = st.FILETE_PX
    lay[f:h - f, f:w - f, :3] = st.AZUL_UI
    x0, y0 = (w - m.size[0]) // 2, (h - m.size[1]) // 2
    reg = lay[y0:y0 + a.shape[0], x0:x0 + a.shape[1], :3]
    reg[:] = reg * (1 - a[..., None]) + np.array((232.0, 230.0, 238.0), np.float32) * a[..., None]
    return lay


def palavra_no_papel(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    ws = sorted(p["palavras"], key=lambda w: w["quadro"])
    for i, w in enumerate(ws):
        ate = w.get("ate", ws[i + 1]["quadro"] if i + 1 < len(ws) else p["fim"])
        if w["quadro"] <= n < ate:
            esc = mo.escala_palavra((n - w["quadro"]) / FPS)
            lay_w = le.palavra(w["texto"], esc, centro=tuple(w.get("centro", (W / 2, H / 2))),
                               corpo=w.get("corpo") or _corpo_cabe(w["texto"]), cor=tuple(w.get("cor", le.TINTA)))
            if w.get("queda") and n >= w["queda"]:      # a palavra cai girando (como o torpedo do Hedy)
                rot, ddx, ddy = mo.queda((n - w["queda"]) / FPS, 0.5)
                M = _afim_em_torno(tuple(w.get("centro", (W / 2, H / 2))), -rot, ddx, ddy)
                img = _tela_com_camada(img, lay_w, M)
            else:
                img = sobre(img, lay_w)
    sa = p.get("seta")                      # {"lado": "dir"|"esq", "quadro": q, "y": 1230}: seta a mao sob a palavra
    if sa and n >= sa["quadro"]:
        f = min(1.0, (n - sa["quadro"]) / 6.0)
        y = sa.get("y", 1230)
        lado = sa.get("lado", "dir")
        if lado == "baixo":
            p0, p1 = (W / 2.0, y), (W / 2.0 + 8, y + 330.0 * f)
        elif lado == "cima":
            p0, p1 = (W / 2.0, y), (W / 2.0 + 8, y - 330.0 * f)
        elif lado == "dir":
            p0, p1 = (300.0, y), (300.0 + 480.0 * f, y + 6)
        else:
            p0, p1 = (780.0, y), (780.0 - 480.0 * f, y + 6)
        if f > 0.05:
            img = sobre(img, st.seta_mao(p0, p1, curva=0.10, esp=7.0, cor=(26, 22, 24), ponta=44, semente=5))
    return img


# ============================================================ 3. foto_pullout
# Hedy planos 8, 9, 11, 18, 19, 21. Foto cheia (P&B ou cor escurecida) com deriva lenta:
# zoom 1,08 -> 1,0 (ou o que o plano pedir) em ease-out, deslocamento diagonal de +-60-120 px.
# Texto opcional digitado letra a letra (serifa branca, borda esquerda fixa) e desfoque de
# saida opcional (casar foco com o proximo plano).
def foto_pullout(n, p, ctx):
    a = ctx.cache("foto", lambda: st.carregar(p["foto"]))
    s0 = escala_cobrir(a)
    v = mv.suavizar_curva(u(n, p["inicio"], p["fim"]), p.get("curva", "saida"), p.get("potencia", 1.5))
    z0, z1 = p.get("zoom", (1.08, 1.0))
    (dx0, dx1), (dy0, dy1) = p.get("deriva", ((0, 0), (0, 0)))
    cx, cy = p.get("ponto", (a.shape[1] / 2, a.shape[0] / 2))
    s_ = s0 * mv.entre(z0, z1, v)
    dxv, dyv = mv.entre(dx0, dx1, v), mv.entre(dy0, dy1, v)
    hw, hh = W / 2.0 / s_, H / 2.0 / s_                  # a janela nunca passa da borda da foto
    ex = min(max(cx - dxv / s_, hw), a.shape[1] - hw)
    ey = min(max(cy - dyv / s_, hh), a.shape[0] - hh)
    img = foto_quadro(ctx, p["foto"], n, ex + dxv / s_, ey + dyv / s_, s_, dxv, dyv, pb=p.get("pb", False))
    img = aplicar_exposicao(img, p)
    t = p.get("texto")
    if t:
        lpd = t.get("letras_por_degrau", 1)
        k = 0 if n < t["quadro"] else min(len(t["texto"]), t.get("letras_inicio", lpd) + lpd * ((n - t["quadro"]) // 3))
        corpo = ctx.cache("c_texto", lambda: le.corpo_para_largura(t["texto"], t.get("largura", 440), le.SERIFA))
        linha_letras(img, t["texto"], k, t.get("esquerda", 320), t.get("yc", 950), corpo,
                     cor=tuple(t.get("cor", BRANCO)))
    for c in p.get("caixas", []):                # caixas azuis que entram pela direita
        if n >= c["quadro"]:
            x = c.get("x", 110) + mo.entrada_caixa((n - c["quadro"]) / FPS)
            caixa = ctx.cache(("caixa", c["texto"]), lambda c=c: _caixa_larga(c["texto"]))
            sobre(img, caixa, x, c.get("y", 1240))
    if p.get("hud_dezena"):                       # dez pessoas sobre a foto (HUD): X em cada dez
        _hud_dezena(img, n, p["hud_dezena"])
    ds = p.get("desfoque_saida")                 # {"de": quadro, "sigma": 14}
    if ds and n >= ds["de"]:
        img = fi.desfocar(img, ds.get("sigma", 14) * u(n, ds["de"] - 3, p["fim"] - 1))
    return img


def _hud_dezena(img, n, h):
    """Faixa escura translucida com dez pessoas que acendem uma a uma (a ultima com a fracao)."""
    y = h.get("y", 1380)
    w_, h_, P = 70, 92, 92
    X0 = (W - (9 * P + w_)) / 2.0
    img[int(y - 100):int(y + 100)] *= 0.40
    ico = _icone_pessoa(w_, h_)
    q0 = h["quadro"]; passo = h.get("passo", 3)
    s_ = 0 if n < q0 else (n - q0) // passo + 1
    v = min(float(h["valor"]), float(s_))
    for k in range(10):
        f = max(0.0, min(1.0, v - k))
        x, yy = int(X0 + k * P), int(y - h_ / 2)
        lit = np.arange(w_)[None, :] < f * w_
        reg = img[yy:yy + h_, x:x + w_]
        reg[:] = (reg * (1 - ico[..., None]) + np.array((72.0, 72.0, 76.0)) * (ico * ~lit)[..., None]
                  + np.array((238.0, 236.0, 232.0)) * (ico * lit)[..., None])
    return img


# ============================================================ 4. cartao_rotulo
# Hedy planos 2-3. Foto em cartao no papel, objeto de base opcional (corda de veludo),
# rotulo serifado pequeno com seta desenhada a mao apontando o sujeito; camera deriva.
def cartao_rotulo(n, p, ctx):
    def _cena():
        img = bg.papel()
        card = st.cartao_foto(st.carregar(p["foto"]), p.get("largura", 640), borda=22, rot=p.get("rot", -2.0))
        sobre(img, card, W / 2 - card.shape[1] / 2, p.get("y_cartao", 300))
        if p.get("base"):
            b = st.escalar(st.carregar(p["base"]), largura=p.get("largura_base", 1180))
            sobre(img, b, W / 2 - b.shape[1] / 2, p.get("y_base", 930))
        r = p["rotulo"]
        if p.get("lado", "dir") == "dir":
            le.escrever(img, r, centro=(860, 330), corpo=50, contorno=le.CONTORNO)
            sobre(img, st.seta_mao((790, 366), (690, 470), curva=0.45, esp=3.0))
        else:
            le.escrever(img, r, centro=(330, 560), corpo=50, contorno=le.CONTORNO)
            sobre(img, st.seta_mao((395, 600), (420, 650), curva=-0.55, esp=3.0))
        return img
    img = ctx.cache("cena", _cena).copy()
    c = p.get("camera", {"zoom": (1.0, 0.976), "dx": (0, -73), "dy": (0, 0)})
    v = u(n, p["inicio"], p["fim"])
    return cam(img, z=mv.entre(*c["zoom"], v), dx=mv.entre(*c.get("dx", (0, 0)), v), dy=mv.entre(*c.get("dy", (0, 0)), v))


# ============================================================ 5. figura_e_palavras
# Hedy plano 4 (multidao). Recorte P&B com UMA cor (cor seletiva) no papel, pan em S de
# ~170 px no plano; palavras serifadas pequenas entrando uma a uma acima da figura.
def figura_e_palavras(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    fig = ctx.cache("fig", lambda: st.escalar(st.carregar(p["figura"]), altura=p.get("altura", 760)))
    dx = mv.entre(0, p.get("pan", -167), u(n, p["inicio"], p["fim"]), "s", 2.0)
    sobre(img, fig, W / 2 - fig.shape[1] / 2 + p.get("x", 60) + dx, p.get("y", 760))
    for w in p.get("palavras", []):
        if n >= w["quadro"]:
            e = mo.escala_palavra((n - w["quadro"]) / FPS)
            le.escrever(img, w["texto"], centro=(w["x"], p.get("y_palavras", 690)), corpo=p.get("corpo", 38),
                        cor=le.TINTA, contorno=le.CONTORNO, escala=e)
    return cam(img, z=mv.entre(1.0, 0.982, u(n, p["inicio"], p["fim"])))


# ============================================================ 6. documento_digitado
# Hedy plano 5 (patente). Documento desbotado em bege; frase digitada com cursor; o termo
# chave ganha selecao azul; a camera mergulha no cursor (1,85x, cursor em 810,910) e no fim
# abre rapido (1,85 -> 1,35 em 3 quadros) para o corte.
def _documento_desbotado(nome, ponto=(0.48, 0.48), escala=1.25):
    d = st.carregar(nome)
    a = st.foto_no_quadro(d, d.shape[1] * ponto[0], d.shape[0] * ponto[1], escala)
    l = a.mean(-1, keepdims=True) / 255.0
    traco = np.clip((0.80 - l) / 0.55, 0, 1)
    papel = np.array((189.0, 179.0, 163.0)); tinta = np.array((128.0, 118.0, 106.0))
    return papel * (1 - traco * 0.55) + tinta * (traco * 0.55)


def documento_digitado(n, p, ctx):
    frase, destaque = p["frase"], p.get("destaque", "")
    img = ctx.cache("doc", lambda: _documento_desbotado(p["documento"], tuple(p.get("ponto_doc", (0.48, 0.48))),
                                                          p.get("escala_doc", 1.25))).copy()
    corpo = ctx.cache("c_frase", lambda: le.corpo_para_largura(" ".join(frase.split()[:2]), p.get("largura_inicio", 215),
                                                               le.INTER, peso=700))
    t0 = p["quadro_digitar"]
    k = 0 if n < t0 else min(len(frase), 3 + (n - t0) * p.get("letras_por_quadro", 1))
    x0, yc = p.get("esquerda", 330.0), p.get("yc", 958.0)
    linha_letras(img, frase, k, x0, yc, corpo, le.INTER, 700, PRETO_TINTA)
    f = le._fonte(le.INTER, int(round(corpo * le.SS)), 700)
    adv = lambda s: f.getlength(s) / le.SS
    cheio, (ox, oy) = le.mascara(frase, le.INTER, corpo, 700)
    xc = x0 + ox + adv(frase[:k]) + 4
    alt = cheio.size[1]
    ini = frase.find(destaque) if destaque else -1
    if ini >= 0 and n >= p.get("quadro_selecao", 10 ** 9) and k > ini:
        xs = x0 + ox + adv(frase[:ini]) - 3
        sobre(img, st.selecao_azul(xs, yc - alt / 2 - 6, xc + 2, yc + alt / 2 + 6, esp=2.0, r=6))
    img[int(yc - alt * .62):int(yc + alt * .62), int(xc):int(xc) + 3] = PRETO_TINTA
    zq = p.get("quadro_zoom")
    if zq is None or n < zq:
        return cam(img, z=mv.entre(1.0, 0.985, u(n, p["inicio"], zq or p["fim"])))
    z = 1.85 if n < p["fim"] - 3 else mv.entre(1.85, 1.35, u(n, p["fim"] - 3, p["fim"]), "entrada", 2.0)
    alvo = p.get("alvo_cursor", (810.0, 910.0))
    return cam(img, z=z, dx=alvo[0] - (W / 2 + z * (xc - W / 2)), dy=alvo[1] - (H / 2 + z * (yc - H / 2)))


# ============================================================ 7. objeto_revela
# Hedy planos 6-7 (roteador). Preto; a camera inteira ABRE de 1,7x para 1x (tau 8,5 q) em
# torno de (540, 990) enquanto o objeto ainda sobe (420 px, tau 6,1 q); um domo teal (a onda)
# sobe da base e cobre o quadro em 0,8 s; legenda em grotesca, cada palavra com fade
# continuo de 0,2 s a partir do instante em que e dita.
ONDA_TOPO = {3: 1821.0, 6: 1119.0, 9: 627.0, 12: 309.0, 15: 162.0, 18: 81.0, 21: 36.0, 24: 0.0, 27: -15.0}
ONDA_PERFIL = [(0, 12.9), (60, 12.9), (300, 14.5), (540, 17.9), (780, 16.6), (1020, 18.6), (1260, 13.0),
               (1500, 9.7), (1740, 3.6), (1920, 2.0)]
ONDA_COR = (-0.06, 0.90, 0.97)          # quanto cada canal ganha por unidade de sinal (teal)
REVELA_ZOOM = {0: 1.70, 3: 1.487, 6: 1.327, 9: 1.223, 12: 1.15, 15: 1.11, 18: 1.07, 21: 1.045, 24: 1.028,
               27: 1.012, 30: 1.0}             # medido pelo corpo do roteador (446 -> 303 px em 720)


def _fundo_onda(q, ctx, cor=ONDA_COR):
    img = bg.chapado((7.0, 7.0, 7.0))
    topo = degrau(ONDA_TOPO, q)
    if topo is None:
        return img
    yy, xx = ctx.cache("xy", lambda: np.mgrid[:H, :W].astype(np.float32))
    R = 2046.0
    dentro = np.clip((R - np.hypot(xx - W / 2, yy - (topo + R))) / 4.0 + 0.5, 0, 1)
    # o perfil anda COM o domo: a frente ja chega teal e a base escurece depois que ele passa
    perfil = np.interp(np.arange(H) - topo, *zip(*ONDA_PERFIL)).astype(np.float32)[:, None]
    s = dentro * perfil
    for c in range(3):
        img[..., c] += cor[c] * s
    return img


def objeto_revela(n, p, ctx):
    q = n - p["inicio"]
    lay = np.zeros((H, W, 4), np.float32)
    larg, cx, cy = p.get("largura_objeto", 572.0), *p.get("centro_objeto", (541.5, 1230.0))
    def _obj():
        o, ocx, ocy = _escala_ink(st.carregar(p["objeto"]), larg)
        if p.get("ponto_objeto"):                 # ponto do asset (px do original) que cai em centro_objeto
            k = o.shape[1] / st.carregar(p["objeto"]).shape[1]
            ocx, ocy = p["ponto_objeto"][0] * k, p["ponto_objeto"][1] * k
        return o, ocx, ocy
    o, ocx, ocy = ctx.cache("obj", _obj)
    sub = 420.0 * math.exp(-max(0, q) / 6.1)
    _sobre_pre(lay, o, cx - ocx, cy - ocy + sub)
    leg = p.get("legenda")
    if leg:
        cap = leg.get("maiuscula", 55.0)
        corpo = ctx.cache("c_leg", lambda: le.corpo_para_maiuscula(cap))
        texto = " ".join(w["texto"] for w in leg["palavras"])
        trk = leg.get("tracking", -0.08 * cap)
        largura = ctx.cache("l_leg", lambda: le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO, 0.0, trk)[0].size[0])
        linha = lambda kk: ctx.cache(f"leg_{kk}", lambda: le.linha_digitada(
            texto, kk, leg.get("x", 543.0) - largura / 2, leg.get("y", 741.0), corpo=corpo, tracking=trk)[..., 3])
        a = np.zeros((H, W), np.float32); pos = 0
        for w in leg["palavras"]:
            i = texto.index(w["texto"], pos); pos = i + len(w["texto"])
            al = fade_palavra(n, w["t"])
            if al > 0:
                a += al * (linha(pos) - (linha(i) if i else 0.0))
        a = a[..., None]
        cor = np.array(leg.get("cor", (193.0, 193.0, 193.0)), np.float32)
        lay[..., :3] = cor * a + lay[..., :3] * (1 - a)
        lay[..., 3:4] = a + lay[..., 3:4] * (1 - a)
    z = interp(REVELA_ZOOM, q)
    anc = p.get("ancora", (540.0, 990.0))
    lay = zoom_em(lay, z, anc, fundo=(0.0, 0.0, 0.0, 0.0))
    img = _fundo_onda(q, ctx, tuple(p.get("cor_onda", ONDA_COR))) if p.get("onda", True) else bg.chapado((7.0, 7.0, 7.0))
    return _compor_pre(img, lay)


# ============================================================ 8. lista_ui
# Hedy plano 17 (Wi-Fi / Bluetooth / GPS). Radar pulsando no preto (um anel a cada 0,8 s);
# caixas azuis entram pela direita (ease-out tau 0,392 s, 408 px) ANTECIPANDO a fala em
# 2-7 quadros; saida em chicote exponencial com borrao acima de 45 px por passo.
def lista_ui(n, p, ctx):
    img = bg.preto()
    fase = mo.fase_radar((n - p["inicio"]) / FPS, p.get("fase_radar", 0.673))
    img = sobre(img, st.radar(fase))
    itens = p["itens"]
    nn = len(itens)
    for i, it in enumerate(itens):
        if n >= it["quadro"]:
            alvo_x = it.get("x", 327.0 + 13.5 * i)
            topo = it.get("y", 906.0 + (i - (nn - 1) / 2) * 161.0 - 55)
            x = alvo_x + mo.entrada_caixa((n - it["quadro"]) / FPS)
            cx_ = ctx.cache(("cx", it["texto"]), lambda it=it: (st.caixa_ui(it["texto"]) if len(it["texto"]) <= 7
                                                                 else _caixa_larga(it["texto"], 64)))
            img = sobre(img, cx_, x, topo)
    sd = p.get("saida_desde")
    if sd is not None and n >= sd:
        dx = mo.saida_camera((n - sd) / 3.0)
        passo = dx - mo.saida_camera((n - 3 - sd) / 3.0)
        img = cam(img, dx=dx, fundo=bg.PRETO)
        img = mv.borrao_direcional(img, mo.borrao_saida(passo))
    return img


# ============================================================ 9. odometro
# Hedy plano 14 (1940 -> 1990). Numeros rolando de 5 em 5 no papel, corpo 90, aceleram no
# meio e assentam: fracao do caminho medida em 1 s.
ODO_CURVA = [(0, 0.0), (3, 0.0), (6, 0.02), (9, 0.10), (12, 0.25), (15, 0.55), (18, 0.75), (21, 0.85),
             (24, 0.90), (27, 0.95), (30, 1.0)]


def odometro(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    de, ate, passo = p["de"], p["ate"], p.get("passo", 5)
    q = (n - p["inicio"]) * 30.0 / p.get("duracao", 30)
    v = de + (ate - de) * float(np.interp(q, *zip(*ODO_CURVA)))
    base = math.floor((v - de) / passo) * passo + de; frac = (v - base) / passo
    alt = 66.0
    for num, dy, al in [(int(base), -frac * alt, 1 - frac), (int(base) + passo, (1 - frac) * alt, frac)]:
        if al > 0.04 and (num <= ate if ate > de else num >= ate):
            le.escrever(img, str(num), centro=(540, 958 + dy), corpo=p.get("corpo", 90), alfa=al, contorno=1.0)
    return img


# ============================================================ 10. moldura_legenda
# Hedy plano 20. Foto dentro de moldura no papel; a camera ABRE de 1,75x para 1x (tau 10 q)
# em torno de (548, 983) saindo de um foco puxado (sigma 12 -> 0 ate o 5o degrau); legenda
# serifada em 1-2 linhas, palavra a palavra (45% no 1o degrau, firme no seguinte).
MOLDURA_DESFOQUE = {0: 12.0, 3: 10.0, 6: 8.5, 9: 6.0, 12: 2.0, 15: 1.0, 18: 0.0}


def _moldura(p):
    a = st.carregar(p.get("moldura", "moldura.png"))
    hsv = cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    ouro = (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 1] > 90) & (hsv[..., 2] > 90) & (a[..., 3] > 128)
    ys, xs = np.nonzero(ouro)
    x0, x1 = np.percentile(xs, [0.5, 99.5]); y0, y1 = np.percentile(ys, [0.5, 99.5])
    ow, oh = p.get("tamanho_ouro", (615.0, 732.0))
    sx, sy = ow / (x1 - x0), oh / (y1 - y0)
    m = cv2.resize(a, (int(round(a.shape[1] * sx)), int(round(a.shape[0] * sy))), interpolation=cv2.INTER_AREA)
    nome = p.get("moldura", "moldura.png")
    furo = np.load(st.localizar(nome.rsplit(".", 1)[0] + "_furo.npy")) * np.array([sx, sy, sx, sy])
    cx, cy = p.get("centro_moldura", (547.5, 867.0))
    return m, cx - (x0 + x1) / 2 * sx, cy - (y0 + y1) / 2 * sy, furo


def moldura_legenda(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    mold, x0, y0, (fx0, fy0, fx1, fy1) = ctx.cache("mold", lambda: _moldura(p))
    fw, fh = int(fx1 - fx0) + 6, int(fy1 - fy0) + 6

    def _retrato():
        a = st.carregar(p["foto"])
        cx, cy = p.get("ponto", (a.shape[1] / 2, a.shape[0] * 0.42))
        s = max(fw / a.shape[1], fh / a.shape[0]) * p.get("zoom_foto", 1.0)
        M = np.float32([[s, 0, fw / 2 - s * cx], [0, s, fh / 2 - s * cy]])
        r = cv2.warpAffine(a, M, (fw, fh), flags=cv2.INTER_AREA)
        r[..., :3] = aplicar_exposicao(r[..., :3], p)
        r[..., 3] = 255.0
        return r
    sobre(img, ctx.cache("retrato", _retrato), x0 + fx0 - 3, y0 + fy0 - 3)
    sobre(img, mold, x0, y0)
    leg = p.get("legenda", [])
    if leg:
        primeira = " ".join(w["texto"] for w in leg[0])
        corpo = ctx.cache("c_leg", lambda: le.corpo_para_largura(primeira, p.get("largura_legenda", 484.5), le.SERIFA,
                                                                  contorno=0.8))
        ys = p.get("y_linhas", (1290.8, 1348.7))
        for linha, yc in zip(leg, ys):
            linha_palavras(img, linha, n, p.get("x_legenda", 541.5), yc, corpo)
    q = n - p["inicio"]
    z = assenta(q, 0.75, 10.0)
    img = zoom_em(img, z, p.get("ancora", (548.0, 983.0)))
    return fi.desfocar(img, degrau(MOLDURA_DESFOQUE, q) or 0.0)


# ============================================================ 11. icone_cursor
# Hedy plano 22, com assets REAIS (icone do aplicativo instalado, cursor de mao do macOS).
# Camera abre de 2,43x para 1x em torno do icone; icone e cursor escalam com ela; o dedo
# sobe da esquerda-baixo ate o icone, agarra e, nos 4 ultimos degraus, arrasta para a
# esquerda acelerando (-7, -19, -49, -142 px) ate o corte.
ICONE_ZOOM = {0: 2.43, 3: 1.85, 6: 1.67, 9: 1.53, 12: 1.44, 15: 1.37, 18: 1.31, 21: 1.26, 24: 1.21, 27: 1.17,
              30: 1.14, 33: 1.11, 36: 1.08, 39: 1.05, 42: 1.02, 45: 1.0}
ICONE_DEDO = {0: (-256, 448), 3: (-197, 470), 6: (-138, 492), 9: (-34, 340), 12: (0, 229), 15: (27, 172),
              18: (29, 132), 21: (27, 94), 24: (21, 69), 27: (24, 61), 30: (20, 49), 33: (17, 38), 36: (15, 33),
              39: (13, 28), 42: (12, 23), 45: (11, 20)}
ICONE_ARRASTO = [(-7.5, 3.0), (-19.5, -1.5), (-49.5, -13.5), (-142.5, -45.0)]   # 4 ultimos degraus


def _cursor_sistema(nome, largura_tinta):
    """Cursor do sistema (PNG renderizado do vetor por ferramentas/assets_locais.py, com
    hotspot no JSON ao lado), com a sombra do macOS (45% preto, desfoque 2 pt, 1 pt abaixo)."""
    import json
    a = st.carregar(nome)
    meta = st._RAIZ / "reais" / (nome.rsplit(".", 1)[0] + ".json")
    info = json.loads(meta.read_text()) if meta.exists() else {"hotspot_px": [156, 96], "px_por_pt": 12}
    ys, xs = np.nonzero(a[..., 3] > 10)
    k = largura_tinta / float(xs.max() - xs.min() + 1)
    r = cv2.resize(a, (max(1, int(round(a.shape[1] * k))), max(1, int(round(a.shape[0] * k)))), interpolation=cv2.INTER_AREA)
    pt = info["px_por_pt"] * k
    al = r[..., 3] / 255.0
    sombra = cv2.GaussianBlur(np.roll(al, max(1, int(round(pt))), axis=0), (0, 0), max(0.5, 2 * pt)) * 0.45
    out = np.zeros_like(r); tot = al + sombra * (1 - al)
    out[..., :3] = (r[..., :3] * al[..., None]) / np.maximum(tot, 1e-6)[..., None]
    out[..., 3] = tot * 255
    return out, info["hotspot_px"][0] * k, info["hotspot_px"][1] * k


def icone_cursor(n, p, ctx):
    q = n - p["inicio"]
    z = interp(ICONE_ZOOM, q)
    cx, cy = p.get("centro", (546.0, 967.5))
    img = bg.dobras_escuras(zoom=z, ancora=(cx, cy)) if p.get("fundo", "dobras") == "dobras" else bg.chapado((12, 12, 13))
    passos_fim = (p["fim"] - 1 - n) // 3                     # 0 no ultimo degrau
    dx, dy = ICONE_ARRASTO[3 - passos_fim] if p.get("arrasto", True) and passos_fim < 4 else (0.0, 0.0)
    base = ctx.cache("icone", lambda: casar_cor(st.carregar(p["icone"]), p["cor_icone"]) if p.get("cor_icone")
                     else st.carregar(p["icone"]))
    ic, icx, icy = _escala_ink(base, p.get("largura_icone", 120.0) * z)
    sobre(img, ic, cx + dx - icx, cy + dy - icy)
    cur, hx, hy = _cursor_sistema(p.get("cursor", "cursor_pointinghand.png"), p.get("largura_cursor", 57.0) * z)
    ox, oy = interp({k: v[0] for k, v in ICONE_DEDO.items()}, q), interp({k: v[1] for k, v in ICONE_DEDO.items()}, q)
    if passos_fim < 4 and p.get("arrasto", True):
        ox, oy = 8 * 1.5 + dx, 9 * 1.5 + dy                  # preso ao icone durante o arrasto
    sobre(img, cur, cx + ox - hx, cy + oy - hy)
    return img


# ============================================================ 12. site_url
# Hedy plano 23. Tela do site (print REAL do navegador) com a URL digitada na barra; a
# camera assenta de 1,2x deslocada para o enquadramento (ease-out forte).
def site_url(n, p, ctx):
    if p.get("tela"):
        a = ctx.cache("tela", lambda: st.carregar(p["tela"]))
        img = st.foto_no_quadro(a, a.shape[1] / 2, a.shape[0] / 2, escala_cobrir(a))
        url = p.get("url", "")
        k = 0 if n < p.get("quadro_digitar", p["inicio"] + 7) else min(len(url), (n - p.get("quadro_digitar", p["inicio"] + 7)) // 3 + 1)
        if url and p.get("barra"):
            bx, by, bc = p["barra"]
            le.escrever(img, url[:k] or " ", esquerda=(bx, by), fonte=le.INTER, corpo=bc, cor=(30, 30, 34), peso=500)
    else:
        url = p.get("url", "seusite.com")
        t0 = p.get("quadro_digitar", p["inicio"] + 7)
        k = 0 if n < t0 else min(len(url), (n - t0) // 3 + 1)
        img = st.site_generico(url[:k])
    if p.get("desfoque"):
        img = fi.desfocar(img, p["desfoque"])
    img = aplicar_exposicao(img, p)
    v = mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 4.0)
    return cam(img, z=mv.entre(1.2, 1.0, v), dx=mv.entre(180, 0, v), dy=mv.entre(140, 0, v), fundo=bg.SITE)


# ============================================================ 13. queda_objeto
# Hedy plano 12 (torpedo). Ceu; listras de luz no comeco; o objeto sobe (tau 0,10 s), uma
# etiqueta rasgada abre e o texto aparece em letras sorteadas; o objeto vira VERMELHO e cai
# girando (0,5 s: 75 graus, -260 px x, +640 px y); arcos brancos pulsam do alto.
def queda_objeto(n, p, ctx):
    q = n - p["inicio"]
    img = bg.ceu()
    if q < 15:
        sobre(img, st.listras_luz(n // 3, forca=1.0 - u(q, 0, 15)), 0, 0)
    if q >= 19:
        sobre(img, st.arcos_brancos((540, -150), ((q - 19) / 24.0) % 1.0), 0, 0)
    t = ctx.cache("obj", lambda: st.escalar(st.carregar(p["objeto"]), altura=p.get("altura", 660)))
    vira = p.get("vira_cor", 24)
    if q >= vira:
        t = ctx.cache("obj_v", lambda: st.recolorir(ctx.cache("obj", lambda: None), tuple(p.get("cor_alerta", (178, 30, 36)))))
    f = mo.subida((q - 3) / FPS, dur=0.45, tau=0.10)
    cy = 975 + (1 - f) * 1300
    cai = p.get("cai", 27)
    rot, ddx, ddy = mo.queda((q - cai) / FPS, dur=0.50) if q >= cai else (0, 0, 0)
    if rot:
        pad = 400; big = np.zeros((t.shape[0] + 2 * pad, t.shape[1] + 2 * pad, 4), np.float32)
        big[pad:pad + t.shape[0], pad:pad + t.shape[1]] = t
        M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), -rot, 1.0)
        t = cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR)
    sobre(img, t, 502 + ddx - t.shape[1] / 2, cy + ddy - t.shape[0] / 2)
    rot_txt = p.get("rotulo")
    if rot_txt and q >= 12:
        prog = min(1.0, 0.25 + (q - 12) / 3 * 0.75)
        lab = ctx.cache(f"etq_{prog:.2f}", lambda: st.etiqueta_rasgada(660, 82, progresso=prog))
        sobre(img, lab, 156, 659)
        if q >= 15:
            ordem = np.random.default_rng(11).permutation(len(rot_txt))
            k = min(len(rot_txt), int((q - 15) / 9 * len(rot_txt)) + 4)
            vis = "".join(c if (i in ordem[:k] or c == " ") else " " for i, c in enumerate(rot_txt))
            corpo = ctx.cache("c_rot", lambda: le.corpo_para_largura(rot_txt, 520, le.SERIFA, contorno=0.8))
            cheio, _ = le.mascara(rot_txt, le.SERIFA, corpo, None, 0.8)
            linha_letras(img, vis, len(vis), 510 - cheio.size[0] / 2, 724, corpo, cor=PRETO_TINTA)
    return cam(img, z=mv.entre(1.0, 0.964, u(n, p["inicio"], p["fim"])), fundo=bg.CEU[0][1])


# ============================================================ 14. palavras_e_figura
# Hedy plano 10. Primeiro palavras soltas no papel (como palavra_no_papel); depois uma figura
# entra deslizando da direita (760 px, ease-out p 2,2, 18 q) com rotulo pequeno + titulo
# serifado ancorados a esquerda; a camera empurra 3% ate o fim.
def palavras_e_figura(n, p, ctx):
    tf = p["quadro_figura"]
    if n < tf:
        return palavra_no_papel(n, dict(p, fim=tf), ctx)
    img = ctx.cache("papel", bg.papel).copy()
    desloc = mv.entre(760, 0, u(n, tf, tf + 18), "saida", 2.2)
    fig = ctx.cache("fig", lambda: st.escalar(st.carregar(p["figura"]), altura=p.get("altura_figura", 1100)))
    fx, fy = p.get("pos_figura", (W / 2 - fig.shape[1] / 2, 560))
    sobre(img, fig, fx + desloc, fy)
    pq = p.get("rotulo_pequeno")
    if pq and n >= pq["quadro"]:
        le.escrever(img, pq["texto"], esquerda=(pq.get("x", 225) + desloc, pq.get("y", 472)), corpo=40, contorno=0.6)
    tt = p.get("titulo")
    if tt:
        corpo = ctx.cache("c_tit", lambda: le.corpo_para_largura(tt["texto"], tt.get("largura", 675), le.SERIFA, contorno=1.0))
        todas = tt["partes"] if "partes" in tt else [{"texto": tt["texto"], "quadro": tt["quadro"]}]
        partes = [w for w in todas if n >= w["quadro"]]
        if partes:
            le.escrever(img, partes[-1]["texto"], esquerda=(tt.get("x", 165) + desloc, tt.get("y", 518)), corpo=corpo, contorno=1.0)
    return cam(img, z=mv.entre(1.0, 1.03, u(n, tf + 18, p["fim"])))


# ============================================================ 15. objeto_na_parede
# Hedy plano 15 (lousa). Objeto na parede clara (luz entrando pela esquerda), borda macia,
# a camera chega mais perto: largura 1000 -> 1390 px em ease-out (p 1,8).
def objeto_na_parede(n, p, ctx):
    img = ctx.cache("parede", bg.parede).copy()
    obj = ctx.cache("obj", lambda: st.carregar(p["objeto"]))
    v = mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 1.8)
    l = st.escalar(obj, largura=mv.entre(*p.get("largura", (1000, 1390)), v)).copy()
    m = np.ones(l.shape[:2], np.float32); b = 40
    for k in range(b):
        f = (k + 1) / b
        m[k, :] = np.minimum(m[k, :], f); m[-1 - k, :] = np.minimum(m[-1 - k, :], f)
        m[:, k] = np.minimum(m[:, k], f); m[:, -1 - k] = np.minimum(m[:, -1 - k], f)
    l[..., 3] = m * (l[..., 3] if l[..., 3].max() <= 1.5 else l[..., 3] / 255.0) * 255
    sobre(img, l, W / 2 - l.shape[1] / 2 + mv.entre(-40, 0, v), p.get("y", 900) - l.shape[0] / 2)
    return img


# ============================================================ 16. amassar_lixeira
# Hedy plano 13. A folha do plano anterior fica 1 degrau; amassa por 4 degraus (continua
# LARGA, contorno em poligono que fecha de cima e de baixo, desenho quase limpo); no 5o ja
# esta dentro da lixeira, que afasta numa curva so (1,2 (1 + 0,4 e^(-q/10,5))) com a boca
# parada na tela.
AMASSA = {3: (0.25, 0.97, (620, 665, 540, 991)), 6: (0.45, 0.93, (640, 644, 540, 1094)),
          9: (0.65, 0.88, (650, 445, 540, 985)), 12: (0.85, 0.84, (590, 402, 540, 957))}
AMASSA_ZOOM_ANTES = {3: 1.95, 6: 1.65, 9: 1.48, 12: 1.42}


def _lixeira_boca(nome):
    a = st.carregar(nome)
    hsv = cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    m = (hsv[..., 0] > 35) & (hsv[..., 0] < 85) & (hsv[..., 1] > 60)
    ys, xs = np.where(m)
    return float(np.median(xs)), float(ys.min()), float(xs.max() - xs.min())


def amassar_lixeira(n, p, ctx):
    q = n - p["inicio"]
    bx, by, bw = ctx.cache("boca", lambda: _lixeira_boca(p["lixeira"]))
    boca = p.get("boca_tela", (576.0, 585.0))
    if q >= 3:
        s = 1.2 * (AMASSA_ZOOM_ANTES[q] if q in AMASSA_ZOOM_ANTES else 1 + 0.40 * math.exp(-(q - 15) / 10.5))
        img = foto_quadro(ctx, p["lixeira"], n, bx, by, s, boca[0] - W / 2, boca[1] - H / 2)
        img = aplicar_exposicao(img, p)
        if q >= 15:
            bola = ctx.cache("bola", lambda: st.escalar(st.carregar(p.get("bola", "papel_amassado.png")), largura=420))
            bb = st.escalar(bola, largura=bw * s * 0.62)
            sobre(img, bb, boca[0] - bb.shape[1] / 2, boca[1] - bb.shape[0] * 0.55)
    else:
        img = bg.chapado(bg.PAPEL)
    if q < 15:
        def _folha():
            if p.get("folha"):
                f = st.carregar(p["folha"]); f = cv2.resize(f, (W, H), interpolation=cv2.INTER_AREA)
                if f[..., 3].max() > 1.5:
                    f[..., 3] = f[..., 3] / 255.0
                return f
            lay = np.zeros((H, W, 4), np.float32); lay[..., :3] = bg.PAPEL; lay[..., 3] = 1.0
            return lay
        folha = ctx.cache("folha", _folha)
        if q >= 3:
            prog, esc, borda = AMASSA[max(k for k in AMASSA if k <= q)]
            lay = mo.amassar(folha, prog, (borda[2], borda[3]), escala=esc, borda=borda, rugas=0.22)
        else:
            lay = folha
        sobre(img, lay, 0, 0)
    return img


# ============================================================ retratos redondos / meios retratos
def _crop_quadrado(a, ponto, lado):
    h, w = a.shape[:2]
    x0 = int(min(max(ponto[0] - lado / 2, 0), w - lado)); y0 = int(min(max(ponto[1] - lado / 2, 0), h - lado))
    return a[y0:y0 + int(lado), x0:x0 + int(lado)]


def _retrato_redondo(nome, ponto, lado, d, ganho=0.9):
    """Foto recortada em circulo (P&B) com aro claro: no lugar do nome escrito."""
    a = st.pb(st.carregar(nome))[..., :3].astype(np.float32) * ganho
    c = cv2.resize(_crop_quadrado(a, ponto, lado), (d, d), interpolation=cv2.INTER_AREA)
    yy, xx = np.mgrid[:d, :d].astype(np.float32)
    r = np.hypot(xx - d / 2 + 0.5, yy - d / 2 + 0.5)
    alfa = np.clip(d / 2 - r, 0, 1)
    aro = np.clip(1 - np.abs(r - (d / 2 - 3)) / 2.5, 0, 1)
    rgb = c * (1 - aro[..., None]) + np.array((232.0, 229.0, 222.0), np.float32) * aro[..., None]
    return np.dstack([rgb, np.clip(alfa, 0, 1)]).astype(np.float32)


# ============================================================ barras_placar
# Resultado em barras, sem nome escrito: o retrato de cada um sob a barra e um selo "25/10"
# carimbado. Barras cor de papel crescem do chao (ease-out) com o numero contando.
def _selo(titulo, sub=None):
    cor_t = (14.0, 14.0, 14.0)
    m1 = le.mascara(titulo, le.GROTESCA, 112, le.GROTESCA_PESO)[0]
    w = m1.size[0] + 96; h = m1.size[1] + 64
    lay = np.zeros((h, w, 4), np.float32); lay[..., :3] = (232, 229, 222); lay[..., 3] = 1.0
    a = np.asarray(m1, np.float32) / 255.0
    reg = lay[32:32 + a.shape[0], 48:48 + a.shape[1], :3]
    reg[:] = reg * (1 - a[..., None]) + np.array(cor_t) * a[..., None]
    pad = 40
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32); big[pad:pad + h, pad:pad + w] = lay
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), 6.0, 1.0)
    return cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR)


def barras_placar(n, p, ctx):
    img = bg.preto()
    q = n - p["inicio"]
    barras = p["barras"]
    escala = p.get("escala", 16.0)                 # px por ponto percentual
    base_y = p.get("base_y", 1250)
    larg, gap = 270, 150
    total = len(barras) * larg + (len(barras) - 1) * gap
    x0 = (W - total) / 2
    cor = (232.0, 229.0, 222.0)
    prog = min(1.0, max(0.0, (q - 2) / 15.0)); e = 1 - (1 - prog) ** 3
    img[base_y:base_y + 3, int(x0 - 40):int(x0 + total + 40)] = (90.0, 90.0, 90.0)
    for i, b in enumerate(barras):
        x = x0 + i * (larg + gap)
        h = b["valor"] * escala * e
        if h >= 1:
            img[int(base_y - h):base_y, int(x):int(x + larg)] = cor
            le.escrever(img, f'{b["valor"] * e:.2f}%'.replace(".", ","), centro=(x + larg / 2, base_y - h - 62),
                        corpo=88, cor=cor, contorno=1.0)
        if b.get("foto"):
            r = ctx.cache(("ret", b["foto"]), lambda b=b: _retrato_redondo(b["foto"], b["ponto"], b["lado"], 290))
            sobre(img, r, x + larg / 2 - r.shape[1] / 2, base_y + 46)
    qs = p.get("quadro_selo")
    if qs is not None and n >= qs:
        sel = ctx.cache("selo", lambda: _selo(p["selo"]))
        k = mo.escala_palavra((n - qs) / FPS)
        r = cv2.resize(sel, (max(1, int(sel.shape[1] * k)), max(1, int(sel.shape[0] * k))), interpolation=cv2.INTER_AREA)
        sobre(img, r, W / 2 - r.shape[1] / 2, p.get("y_selo", 330) - r.shape[0] / 2)
    return zoom_em(img, 1.0 + 0.04 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


# ============================================================ dupla_retratos
# Os dois lado a lado, tela dividida, P&B escurecido, sem texto, na ordem em que a fala
# os chama. Camera empurra devagar.
def dupla_retratos(n, p, ctx):
    def _montar():
        out = np.zeros((H, W, 3), np.float32)
        for i, (nome, pt) in enumerate(zip(p["fotos"], p["pontos"])):
            a = st.pb(st.carregar(nome))[..., :3].astype(np.float32)
            k = H / a.shape[0]
            r = cv2.resize(a, (int(a.shape[1] * k), H), interpolation=cv2.INTER_AREA if k < 1 else cv2.INTER_CUBIC)
            cx = pt[0] * k
            x0 = int(min(max(cx - W / 4, 0), r.shape[1] - W // 2))
            out[:, i * (W // 2):(i + 1) * (W // 2)] = r[:, x0:x0 + W // 2] * p.get("ganho", 0.7)
        out[:, W // 2 - 2:W // 2 + 2] = (232.0, 229.0, 222.0)
        return out
    base = ctx.cache("dupla", _montar)
    img = fi.grao_foto(base.copy(), n)
    return zoom_em(img, 1.0 + 0.05 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


# ============================================================ dezena
# Proporcao que se enxerga: fileiras de 10 pessoas que acendem uma a uma (a ultima com a
# fracao), cada uma com o desenho do predio no lugar do nome: a cuia (Camara) e a cupula
# (Senado). Linhas de marca com numeral grande e anel no que falta. Nenhuma palavra.
_ICONE = {}
ACENTO = (96.0, 168.0, 224.0)


def _icone_pessoa(w=70, h=92):
    k = (w, h)
    if k not in _ICONE:
        SS = 4
        big = np.zeros((h * SS, w * SS), np.uint8)
        cv2.circle(big, (int(w / 2 * SS), int(0.27 * h * SS)), int(0.19 * w * SS), 255, -1, cv2.LINE_AA)
        cv2.ellipse(big, (int(w / 2 * SS), int(0.99 * h * SS)), (int(0.47 * w * SS), int(0.50 * h * SS)),
                    0, 180, 360, 255, -1, cv2.LINE_AA)
        _ICONE[k] = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return _ICONE[k]


def _predio(tipo, w=150, h=86, cor=(190.0, 190.0, 190.0)):
    """Cuia da Camara (aberta para cima) ou cupula do Senado (fechada para cima), sobre a laje."""
    SS = 4
    big = np.zeros((h * SS, w * SS), np.uint8)
    laje = int(h * SS * 0.14)
    if tipo == "camara":
        cv2.ellipse(big, (w * SS // 2, int(h * SS * 0.10)), (w * SS // 2 - 4, int(h * SS * 0.74)), 0, 0, 180, 255, -1, cv2.LINE_AA)
    else:
        cv2.ellipse(big, (w * SS // 2, int(h * SS * 0.84)), (w * SS // 2 - 4, int(h * SS * 0.74)), 0, 180, 360, 255, -1, cv2.LINE_AA)
    big[h * SS - laje:, 4:w * SS - 4] = 255
    m = cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return np.dstack([np.broadcast_to(np.array(cor, np.float32), (h, w, 3)), m]).astype(np.float32)


def dezena(n, p, ctx):
    papel_t = p.get("tema") == "papel" or p.get("fundo") in ("canvas", "papel")
    img = np.ascontiguousarray(_fundo(ctx, p) if papel_t else bg.preto())
    q = n - p["inicio"]
    cols = int(p.get("colunas", 10))              # 10 = uma fileira; 5 = grade 2x5 (cabe melhor no vertical)
    if cols == 5:
        w, h, P, pitch = 150, 198, 182, 250
    else:
        w, h, P, pitch = (78, 104, 92, 0) if papel_t else (88, 116, 104, 0)
    X0 = (W - ((cols - 1) * P + w)) / 2.0
    ico = _icone_pessoa(w, h)
    if papel_t:
        DIM, LIT, ACENTO = (np.array((196.0, 196.0, 202.0)) if p.get("fundo") == "canvas" else np.array((170.0, 168.0, 164.0))), np.array((26.0, 22.0, 24.0)), tuple(float(c) for c in st.AZUL_UI)
    else:
        DIM, LIT, ACENTO = np.array((46.0, 46.0, 50.0)), np.array((232.0, 229.0, 222.0)), globals()["ACENTO"]
    linhas = p["linhas"]
    ys = [L.get("y", 700 + i * 420) for i, L in enumerate(linhas)]

    def pos(yc, k):
        r_, c_ = divmod(k, cols)
        return int(X0 + c_ * P), int(yc - h / 2 + r_ * pitch)
    for L, yc in zip(linhas, ys):
        if L.get("predio") and cols == 10:
            pr = ctx.cache(("predio", L["predio"]), lambda L=L: _predio(
                L["predio"], cor=(26.0, 22.0, 24.0) if papel_t else (190.0, 190.0, 190.0)))
            sobre(img, pr, X0 + 2, yc - 74 - pr.shape[0])
        ini = L.get("inicio", 0)
        passo = L.get("passo", 3)
        s_ = 0 if q < ini else (q - ini) // passo + 1
        v = min(float(L["valor"]), float(s_))
        novo = int(math.ceil(v)) - 1 if (0 < s_ <= L["valor"] + 1 and q >= ini and (q - ini) % passo < 3) else -1
        for k in range(10):
            f = max(0.0, min(1.0, v - k))
            x, y = pos(yc, k)
            m = ico
            if k == novo and f > 0:
                g = 1.16                            # a que acabou de acender "salta"
                m2 = cv2.resize(ico, (int(w * g), int(h * g)), interpolation=cv2.INTER_LINEAR)
                dx, dy = (m2.shape[1] - w) // 2, m2.shape[0] - h
                x, y, m = x - dx, y - dy, m2
            hh, ww = m.shape
            lit = np.arange(ww)[None, :] < f * ww
            reg = img[y:y + hh, x:x + ww]
            reg[:] = (reg * (1 - m[..., None]) + DIM * (m * ~lit)[..., None] + LIT * (m * lit)[..., None])
    for mk in p.get("marcas", []):
        if mk["quadro"] <= n < mk.get("ate", 10 ** 9):
            if cols == 10:
                xb = int(X0 + mk["valor"] * P - (P - w) / 2.0)
                y_top, y_bot = int(ys[0] - 170), int(ys[-1] + 84)
                for yy in range(y_top, y_bot, 20):
                    img[yy:yy + 11, xb - 2:xb + 3] = ACENTO
                le.escrever(img, mk["texto"], centro=(min(max(xb, 160), W - 160), y_top - 56), fonte=le.SERIFA, corpo=118,
                            cor=ACENTO, contorno=1.0, escala=mo.escala_palavra((n - mk["quadro"]) / FPS))
            else:
                le.escrever(img, mk["texto"], centro=tuple(mk.get("pos", (W / 2, ys[0] + 2 * pitch + 60))), fonte=le.SERIFA,
                            corpo=mk.get("corpo", 220), cor=ACENTO, contorno=1.0,
                            escala=mo.escala_palavra((n - mk["quadro"]) / FPS))
    for fl in p.get("falta", []):
        if n >= fl["quadro"]:
            yc = ys[fl["linha"]]
            x0_, y0_ = pos(yc, fl["icone"])
            x, yy = x0_ + w // 2, y0_ + h // 2
            pulso = 6 if ((n - fl["quadro"]) // 3) % 2 == 0 else 0            # o anel pulsa a cada degrau
            cv2.circle(img, (x, yy), int(0.62 * max(w, h)) + pulso, tuple(float(c) for c in ACENTO), 5, cv2.LINE_AA)
            if fl.get("texto"):
                le.escrever(img, fl["texto"], centro=(min(max(x, 200), W - 200), yy + int(0.62 * max(w, h)) + 100),
                            fonte=le.SERIFA, corpo=fl.get("corpo", 118), cor=ACENTO, contorno=1.0,
                            escala=mo.escala_palavra((n - fl["quadro"]) / FPS))
    return zoom_em(img, 1.0 + 0.04 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


# ====================================================================== v9 — papel e tinta
# Explicativo sobre o papel da Familia A (nao sobre preto): figura desenhada a tinta, foto
# colorida de arquivo, carimbo, folha de calendario, caixa de selecao digitada. Cada tipo
# abaixo e uma figura que uma frase nomeia — nunca um rotulo.
VERMELHO = (176.0, 30.0, 36.0)
TINTA_D = (26.0, 22.0, 24.0)
FOLHA = (240.0, 238.0, 232.0)


def _com_sombra(rgb, rot=0.0, pad=70, desloc=(8, 20), blur=18.0, forca=0.40):
    """RGB (h,w,3) -> RGBA com sombra mole embaixo, opcionalmente torta."""
    h, w = rgb.shape[:2]
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    s = np.zeros(out.shape[:2], np.float32)
    s[pad + desloc[1]:pad + desloc[1] + h, pad + desloc[0]:pad + desloc[0] + w] = forca
    out[..., 3] = cv2.GaussianBlur(s, (0, 0), blur)
    reg = out[pad:pad + h, pad:pad + w]
    reg[..., :3] = rgb; reg[..., 3] = 1.0
    if rot:
        M = cv2.getRotationMatrix2D((out.shape[1] / 2, out.shape[0] / 2), rot, 1.0)
        out = cv2.warpAffine(out, M, (out.shape[1], out.shape[0]), flags=cv2.INTER_CUBIC)
    return out


def _tela_com_camada(img, lay, M, alfa=1.0):
    """Cola uma camada RGBA (0-1) na imagem aplicando a afim M (2x3) — folha que gira."""
    w = cv2.warpAffine(lay, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    a = w[..., 3:4] * alfa
    return img * (1 - a) + w[..., :3] * a


def _afim_em_torno(ponto, graus, tx=0.0, ty=0.0, origem=(0.0, 0.0), escala=1.0):
    """Translada a camada para `origem` (canto no quadro), gira/escala em torno de `ponto` (tela), soma (tx, ty)."""
    R = cv2.getRotationMatrix2D((float(ponto[0]), float(ponto[1])), graus, escala)
    R3 = np.vstack([R, [0, 0, 1]])
    T = np.float64([[1, 0, origem[0]], [0, 1, origem[1]], [0, 0, 1]])
    S = np.float64([[1, 0, tx], [0, 1, ty], [0, 0, 1]])
    return (S @ R3 @ T)[:2].astype(np.float32)


# ============================================================ 20. calendario
# A data como folha de calendario de parede: faixa vermelha com o mes, o dia em serifa
# italica enorme. Na fala do dia a folha anterior se levanta, gira na dobradica e some em 3
# degraus, revelando a nova. Camera abre de 1,5x para 1x.
def _pagina_calendario(mes, dia, larg=660, alt=800):
    f = np.empty((alt, larg, 3), np.float32); f[:] = FOLHA
    faixa = int(alt * 0.215)
    f[:faixa] = VERMELHO
    cv2.circle(f, (larg // 2, 30), 15, (70.0, 18.0, 22.0), -1, cv2.LINE_AA)
    cv2.circle(f, (larg // 2, 30), 15, (196.0, 70.0, 74.0), 2, cv2.LINE_AA)
    le.escrever(f, mes.upper(), centro=(larg / 2, faixa * 0.64), fonte=le.INTER, corpo=62, cor=(244.0, 240.0, 232.0),
                peso=800, tracking=7.0)
    le.escrever(f, str(dia), centro=(larg / 2, faixa + (alt - faixa) / 2 + 6), fonte=le.SERIFA, corpo=470,
                cor=TINTA_D, contorno=2.0)
    f[faixa:faixa + 3] = (120.0, 20.0, 24.0)
    return f


def calendario(n, p, ctx):
    img = _fundo(ctx, p)
    q = n - p["inicio"]
    rot = p.get("rot", -2.0)
    nova = ctx.cache("pg_dia", lambda: _com_sombra(_pagina_calendario(p["mes"], p["dia"]), rot))
    ant = ctx.cache("pg_ant", lambda: _com_sombra(_pagina_calendario(p["mes"], p["dia_antes"]), rot))
    cx, cy = p.get("centro", (W / 2, 930.0))
    tt = p["quadro_troca"]
    pos = lambda lay: (cx - lay.shape[1] / 2, cy - lay.shape[0] / 2)
    if n < tt:
        sobre(img, ant, *pos(ant))
    else:
        sobre(img, nova, *pos(nova))
        k = (n - tt) // 3
        if k < 3:
            x, y = pos(ant)
            ang = (6.0, 17.0, 33.0)[k]; sobe = (-26.0, -210.0, -560.0)[k]; al = (1.0, 0.85, 0.5)[k]
            M = _afim_em_torno((cx, y + 84), ang, 0.0, sobe, origem=(x, y))
            img = _tela_com_camada(img, ant, M, al)
    z = assenta(q, 0.45, 9.0)
    return zoom_em(img, z, (cx, cy))


# ============================================================ 21. hemiciclo
# O plenario como figura: cada assento e um ponto; a bancada acende da DIREITA para o centro
# (o lado em que ela senta), e cruzar a linha do meio e "mais da metade" sem uma palavra.
# `figuras`: uma ou mais camaras no mesmo quadro (a camera viaja entre elas, como no
# Priming); `limiares`: linha radial tracejada na fracao dos assentos (1/2, 3/5);
# `falta`: os assentos seguintes ganham destaque azul pulsando — o voto que falta.
def _assentos(N, R_in, R_out, linhas):
    rs = np.linspace(R_in, R_out, linhas)
    pesos = rs / rs.sum()
    ni = np.floor(pesos * N).astype(int)
    for k in np.argsort(-(pesos * N - ni))[:N - ni.sum()]:
        ni[k] += 1
    s = []
    for r, k in zip(rs, ni):
        for j in range(int(k)):
            s.append((math.pi * (1 - (j + 0.5) / k), float(r)))
    s.sort(key=lambda a: (round(a[0], 4), a[1]))          # 0 = o assento mais a direita
    return s


def _fig_hemiciclo(img, n, f, ctx, idx):
    entra = f.get("entra")
    if entra is not None and n < entra:
        return img
    ap = f.get("apaga")                          # {"de": quadro, "alfa": 0.25}: fica de fundo quando a camera sai
    base = img.copy() if (entra is not None and n - entra < 6) or ap else None
    alfa_fig = 1.0
    if entra is not None and n - entra < 6:
        alfa_fig = (n - entra + 1) / 6.0
    if ap and n >= ap["de"]:
        alfa_fig = 1.0 + (ap.get("alfa", 0.25) - 1.0) * min(1.0, (n - ap["de"] + 3) / 9.0)
    N = int(f["total"])
    cx, cy = f.get("centro", (W / 2.0, 1060.0))
    R_out = f.get("raio", 430.0); R_in = f.get("raio_interno", 0.37 * R_out)
    A = 2.0 * N * (R_out - R_in) / (math.pi * (R_in + R_out))
    linhas = f.get("linhas") or max(3, int(round((1 + math.sqrt(1 + 4 * A)) / 2)))
    seats = ctx.cache(("seats", idx), lambda: _assentos(N, R_in, R_out, linhas))
    d = (R_out - R_in) / (linhas - 1)
    s_arco = math.pi * (R_in + R_out) / 2 * linhas / N
    rs = 0.43 * min(d, s_arco)
    ac = f["acende"]
    ease = lambda m: mv.suavizar_curva(u(m, ac["de"], ac["ate"]), "saida", 1.8)
    k_on = int(round(ac["k"] * ease(n)))
    k_antes = int(round(ac["k"] * ease(n - 3)))
    novos = max(0, k_on - k_antes) if n < ac["ate"] + 3 else 0
    fl = f.get("falta")
    falta_on = bool(fl) and n >= fl["quadro"]
    pulsa = ((n - (fl["quadro"] if fl else 0)) // 3) % 2 == 0
    CLARO, BORDA = ((216.0, 216.0, 221.0), (150.0, 150.0, 158.0)) if f.get("_fundo") == "canvas" \
        else ((214.0, 212.0, 207.0), (150.0, 148.0, 146.0))
    azul = tuple(float(c) for c in st.AZUL_UI)
    for i, (th, r) in enumerate(seats):
        x = cx + r * math.cos(th); y = cy - r * math.sin(th)
        c = (int(round(x)), int(round(y)))
        if i < k_on:
            rr = rs * (1.28 if i >= k_on - novos else 1.0)
            cv2.circle(img, c, int(round(rr)), TINTA_D, -1, cv2.LINE_AA)
        else:
            cv2.circle(img, c, int(round(rs)), CLARO, -1, cv2.LINE_AA)
            cv2.circle(img, c, int(round(rs)), BORDA, 1, cv2.LINE_AA)
            ct = f.get("contra")                     # {"quadro", "n"}: os votos contra, em vermelho, logo depois dos acesos
            if ct and n >= ct["quadro"] and ac["k"] <= i < ac["k"] + ct.get("n", 1):
                g_ = 1.35 if n - ct["quadro"] < 6 else 1.15
                cv2.circle(img, c, int(round(rs * g_)), VERMELHO, -1, cv2.LINE_AA)
                continue
            if falta_on and i < ac["k"] + fl.get("n", 1):
                if fl.get("n", 1) == 1:
                    cv2.circle(img, c, int(round(rs * (1.55 if pulsa else 1.3))), azul, -1, cv2.LINE_AA)
                    cv2.circle(img, c, int(round(rs * (2.4 if pulsa else 2.0))), azul, 4, cv2.LINE_AA)
                else:
                    cv2.circle(img, c, int(round(rs + (5 if pulsa else 3))), azul, 3 if pulsa else 2, cv2.LINE_AA)
    lims = list(f.get("limiares", []))
    if f.get("metade"):
        lims.append(dict(f["metade"], fracao=0.5))
    for lm in lims:
        if n >= lm["quadro"]:
            th = math.pi * lm.get("fracao", 0.5)
            r0, r1 = R_in * 0.55, R_out + 46
            n_tr = int((r1 - r0) / 24)
            for j in range(n_tr):
                a = r0 + j * 24; b = a + 13
                p0 = (int(round(cx + a * math.cos(th))), int(round(cy - a * math.sin(th))))
                p1 = (int(round(cx + b * math.cos(th))), int(round(cy - b * math.sin(th))))
                cv2.line(img, p0, p1, azul, 5, cv2.LINE_AA)
    for sa in f.get("setas", []):
        if n >= sa["quadro"]:
            g = min(1.0, (n - sa["quadro"]) / 6.0)
            (x0, y0), (x1, y1) = sa["de"], sa["para"]
            if g > 0.05:
                sobre(img, st.seta_mao((x0, y0), (x0 + (x1 - x0) * g, y0 + (y1 - y0) * g), curva=sa.get("curva", 0.12),
                                       esp=6.0, cor=tuple(sa.get("cor", (26, 22, 24))), ponta=40, semente=5))
    for nm in f.get("numerais", []):
        if nm["quadro"] <= n < nm.get("ate", 10 ** 9):
            le.escrever(img, nm["texto"], centro=tuple(nm.get("pos", (cx, cy + 190))), fonte=le.SERIFA,
                        corpo=nm.get("corpo", 190), cor=tuple(nm.get("cor", azul)), contorno=1.0,
                        escala=mo.escala_palavra((n - nm["quadro"]) / FPS))
    if base is not None:
        img = base * (1 - alfa_fig) + img * alfa_fig
    return img


def hemiciclo(n, p, ctx):
    img = _fundo(ctx, p)
    figs = p.get("figuras") or [p]
    for i, f in enumerate(figs):
        img = _fig_hemiciclo(img, n, dict(f, _fundo=p.get("fundo")), ctx, i)
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
        return cam(img, z=z, dx=z * (W / 2 - anc[0]), dy=z * (H / 2 - anc[1]), fundo=tuple(float(v) for v in img[27, 27, :3]))
    c = p.get("centro", (W / 2.0, 1060.0))
    return zoom_em(img, 1.0 + 0.045 * u(n, p["inicio"], p["fim"]), tuple(c))


# ============================================================ 21b. pizza
# "Mais da metade": circulo que se enche no sentido horario; a metade (tinta) e a parte que
# passa (azul). Linha tracejada no meio; sem palavra.
def pizza(n, p, ctx):
    img = _fundo(ctx, p)
    cx, cy = p.get("centro", (W / 2.0, 880.0)); R = int(p.get("raio", 340))
    ac = p["acende"]
    v = p["valor"] * mv.suavizar_curva(u(n, ac["de"], ac["ate"]), "saida", 1.6)
    azul = tuple(float(c) for c in st.AZUL_UI)
    cx, cy = int(cx), int(cy)
    c = (cx, cy)
    cv2.circle(img, c, R, (222.0, 222.0, 226.0) if p.get("fundo") == "canvas" else (214.0, 212.0, 207.0), -1, cv2.LINE_AA)
    a_ink = min(v, 0.5) * 360.0
    if a_ink > 0.5:
        cv2.ellipse(img, c, (R, R), 0, -90, -90 + a_ink, TINTA_D, -1, cv2.LINE_AA)
    if v > 0.5:
        cv2.ellipse(img, c, (R, R), 0, 90, 90 + (v - 0.5) * 360.0, azul, -1, cv2.LINE_AA)
    cv2.circle(img, c, R, TINTA_D, 6, cv2.LINE_AA)
    m = p.get("metade")
    if m and n >= m["quadro"]:
        for yy in range(cy - R - 50, cy + R + 60, 26):
            cv2.line(img, (cx, yy), (cx, yy + 14), azul if v > 0.5 else TINTA_D, 5, cv2.LINE_AA)
    for nm in p.get("numerais", []):
        if nm["quadro"] <= n < nm.get("ate", 10 ** 9):
            le.escrever(img, nm["texto"], centro=tuple(nm.get("pos", (cx, cy + R + 190))), fonte=le.SERIFA,
                        corpo=nm.get("corpo", 190), cor=tuple(nm.get("cor", azul)), contorno=1.0,
                        escala=mo.escala_palavra((n - nm["quadro"]) / FPS))
    return zoom_em(img, 1.0 + 0.05 * u(n, p["inicio"], p["fim"]), (cx, cy))


# ============================================================ 22. carimbo
# Uma folha (a lei) e a palavra carimbada em vermelho: chega grande, bate (1,9x -> 1x em
# 2 degraus), a folha afunda e a camera treme 2 degraus. Tinta que "morde" o papel
# (multiplicativa) e com falhas.
def _folha_lei(larg=700, alt=920, semente=3):
    f = np.empty((alt, larg, 3), np.float32); f[:] = FOLHA
    f[70:104, 70:larg - 210] = (46.0, 42.0, 44.0)             # titulo
    rng = np.random.default_rng(semente)                       # a semente muda o desenho das linhas do texto
    y = 170
    while y < alt - 120:
        fim = larg - 70 - int(rng.integers(0, 150))
        f[y:y + 16, 70:fim] = (168.0, 166.0, 162.0)
        y += 46
        if rng.random() < 0.18:
            y += 38
    return f


def _tinta_carimbo(texto, cor, corpo=150, rot=-8.0, semente=4):
    m = le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO, 0.0, 3.0)[0]
    a = np.asarray(m, np.float32) / 255.0
    pad = 46
    h, w = a.shape[0] + 2 * pad, a.shape[1] + 2 * pad
    full = np.zeros((h, w), np.float32)
    full[pad:pad + a.shape[0], pad:pad + a.shape[1]] = a
    cv2.rectangle(full, (6, 6), (w - 7, h - 7), 1.0, 11, cv2.LINE_AA)
    cv2.rectangle(full, (24, 24), (w - 25, h - 25), 1.0, 4, cv2.LINE_AA)
    rng = np.random.default_rng(semente)
    ruido = cv2.GaussianBlur(rng.random((h, w)).astype(np.float32), (0, 0), 1.3)
    ruido = (ruido - ruido.min()) / (ruido.max() - ruido.min())
    falha = np.clip((ruido - 0.22) / 0.10, 0, 1)
    full = cv2.GaussianBlur(full, (0, 0), 0.9) * (0.58 + 0.42 * falha)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, 1.0)
    big = np.zeros((h + 80, w + 80), np.float32); big[40:40 + h, 40:40 + w] = full
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), rot, 1.0)
    return cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_CUBIC)


def carimbo(n, p, ctx):
    """Variacoes (para a folha nao virar a mesma cena em todo video): "fundo" (papel, canvas, parede), "tamanho_folha" [larg, alt],
    "semente" (o desenho das linhas), "rot" da folha, "centro", "rot_carimbo", "dx"/"dy" do carimbo, "cor",
    "zoom" [z0, z1] e "foco" [x, y] (o ponto da tela que fica parado no zoom)."""
    img = _fundo(ctx, p)
    q = n - p["inicio"]; qs = p["quadro_carimbo"]
    k = (n - qs) // 3 if n >= qs else -1
    def _folha():
        larg, alt = p.get("tamanho_folha", (700, 920))
        f = _folha_lei(larg, alt, p.get("semente", 3))
        if p.get("titulo"):                           # o titulo do documento (pedido, decisao) no lugar da barra
            f[60:100 + 64 * len(p["titulo"]) + 56, 60:larg - 60] = FOLHA
            for i, L in enumerate(p["titulo"]):
                le.escrever(f, L, esquerda=(70, 88 + i * 64), fonte=le.INTER, corpo=46, cor=(36.0, 32.0, 34.0), peso=800)
            f[100 + 64 * (len(p["titulo"]) - 1) + 40:100 + 64 * (len(p["titulo"]) - 1) + 44, 70:larg - 70] = (60.0, 56.0, 58.0)
        return _com_sombra(f, p.get("rot", 2.0), blur=22, desloc=(10, 26))
    folha = ctx.cache("folha", _folha)
    cx, cy = p.get("centro", (W / 2, 900.0))
    afunda = 0.992 if 0 <= k < 2 else 1.0
    lay = folha
    if afunda != 1.0:
        lay = cv2.resize(folha, (int(folha.shape[1] * afunda), int(folha.shape[0] * afunda)), interpolation=cv2.INTER_AREA)
    sobre(img, lay, cx - lay.shape[1] / 2, cy - lay.shape[0] / 2)
    if k >= 0:
        cor = np.array(p.get("cor", VERMELHO), np.float32)
        tinta = ctx.cache("tinta", lambda: _tinta_carimbo(p["texto"], cor, p.get("corpo", 124), p.get("rot_carimbo", -8.0)))
        esc = (1.9, 1.25, 1.0)[min(k, 2)]
        a = tinta if esc == 1.0 else cv2.resize(tinta, (int(tinta.shape[1] * esc), int(tinta.shape[0] * esc)),
                                                interpolation=cv2.INTER_CUBIC)
        al = (0.55, 0.9, 0.96)[min(k, 2)]
        x0 = int(round(cx + p.get("dx", 0) - a.shape[1] / 2)); y0 = int(round(cy + p.get("dy", 90) - a.shape[0] / 2))
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(W, x0 + a.shape[1]), min(H, y0 + a.shape[0])
        if xa < xb and ya < yb:
            s = a[ya - y0:yb - y0, xa - x0:xb - x0, None] * al
            reg = img[ya:yb, xa:xb]
            img[ya:yb, xa:xb] = reg * (1 - s) + (reg * (cor / 255.0)) * s
    tremor = (0.0, 9.0, -6.0, 3.0)[k] if 0 <= k < 4 else 0.0
    z0, z1 = p.get("zoom", (1.0, 1.05))
    z = z0 + (z1 - z0) * mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 1.5) if "zoom" in p else 1.0 + 0.05 * u(n, p["inicio"], p["fim"])
    return zoom_em(img, z, tuple(p.get("foco", (cx, cy))), dy=tremor)


# ============================================================ 23. selecao_digitada
# Hedy plano 5 ("THE |TECHNOLOGY|"): a sigla aparece letra a letra, cada uma NO instante em
# que e dita, o cursor pisca no fim e a caixa de selecao azul fecha em volta; a camera mergulha.
def selecao_digitada(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    texto = p["texto"]; tempos = p["letras"]
    k = sum(1 for t in tempos if n >= t)
    corpo = p.get("corpo", 330.0)
    if p.get("balao"):
        corpo = min(corpo, 235.0)
    bl = p.get("balao")                       # {"quadro": q}: a sigla vai DENTRO de um balao de fala
    if bl and n >= bl["quadro"]:
        e = mo.escala_palavra((n - bl["quadro"]) / FPS)
        bw_, bh_ = 900, 470
        big = np.zeros((bh_ + 150, bw_ + 60, 4), np.float32)
        m = np.zeros(big.shape[:2], np.uint8)
        x0b, y0b = 30, 20
        cv2.rectangle(m, (x0b + 70, y0b), (x0b + bw_ - 70, y0b + bh_), 255, -1, cv2.LINE_AA)
        cv2.rectangle(m, (x0b, y0b + 70), (x0b + bw_, y0b + bh_ - 70), 255, -1, cv2.LINE_AA)
        for cx_, cy_ in ((x0b + 70, y0b + 70), (x0b + bw_ - 70, y0b + 70), (x0b + 70, y0b + bh_ - 70), (x0b + bw_ - 70, y0b + bh_ - 70)):
            cv2.circle(m, (cx_, cy_), 70, 255, -1, cv2.LINE_AA)
        cauda = np.array([[x0b + 160, y0b + bh_ - 10], [x0b + 290, y0b + bh_ - 10], [x0b + 120, y0b + bh_ + 120]], np.int32)
        cv2.fillConvexPoly(m, cauda, 255, cv2.LINE_AA)
        a = cv2.GaussianBlur(m.astype(np.float32) / 255.0, (0, 0), 1.0)
        borda = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))).astype(np.float32) / 255.0, (0, 0), 1.0)
        big[..., :3] = TINTA_D; big[..., 3] = borda
        big[..., :3] = big[..., :3] * (1 - a[..., None]) + np.array(FOLHA, np.float32) * a[..., None]
        sh, pad_ = _sombra_alfa(big, (14, 24), 16.0, 0.35)
        bb = big if e >= 0.999 else cv2.resize(big, (max(1, int(big.shape[1] * e)), max(1, int(big.shape[0] * e))), interpolation=cv2.INTER_AREA)
        sb = sh if e >= 0.999 else cv2.resize(sh, (max(1, int(sh.shape[1] * e)), max(1, int(sh.shape[0] * e))), interpolation=cv2.INTER_AREA)
        cxb, cyb = p.get("centro", (W / 2.0, 900.0))
        cyb -= 40
        sobre(img, sb, cxb - sb.shape[1] / 2, cyb - sb.shape[0] / 2)
        sobre(img, bb, cxb - bb.shape[1] / 2, cyb - bb.shape[0] / 2)
        if k == 0 and e > 0.9:                            # reticencias enquanto ninguem disse
            for j in range(3):
                cv2.circle(img, (int(cxb - 120 + j * 120), int(cyb - 40)), 18, TINTA_D, -1, cv2.LINE_AA)
    cheio, (ox, oy) = ctx.cache("m", lambda: le.mascara(texto, le.INTER, corpo, 700))
    xc, yc = p.get("centro", (W / 2.0, 900.0))
    x0 = xc - cheio.size[0] / 2
    linha_letras(img, texto, k, x0, yc, corpo, le.INTER, 700, TINTA_D)
    f = le._fonte(le.INTER, int(round(corpo * le.SS)), 700)
    xe = x0 + ox + f.getlength(texto[:k]) / le.SS + 8
    alt = cheio.size[1]
    sel = p.get("quadro_selecao")
    if sel is None or n < sel:
        if k < len(texto) or ((n - tempos[-1]) // 3) % 2 == 0:
            img[int(yc - alt * 0.62):int(yc + alt * 0.62), int(xe):int(xe) + 6] = TINTA_D
    else:
        pad = 26
        sobre(img, st.selecao_azul(x0 + ox - pad, yc - alt / 2 - pad * 0.8, x0 + ox + cheio.size[0] + pad,
                                   yc + alt / 2 + pad * 0.8, esp=4.0, r=13.0))
    v = mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "entrada", 1.6)
    return zoom_em(img, 1.0 + (0.07 if p.get("balao") else 0.22) * v, (xc, yc))


# ============================================================ 24. duas_molduras
# O "contra": dois retratos em moldura dourada lado a lado, cada um entra (pop) na palavra
# do nome, que fica em serifa italica sob a moldura. Abertura da referencia da galeria.
def _retrato_na_moldura(ctx, chave, foto, ponto, zoom_foto, ow, oh, ganho, sat):
    def _montar():
        mold, x0, y0, (fx0, fy0, fx1, fy1) = _moldura({"tamanho_ouro": (ow, oh), "centro_moldura": (0, 0)})
        a = st.carregar(foto)
        fw, fh = int(fx1 - fx0) + 6, int(fy1 - fy0) + 6
        s = max(fw / a.shape[1], fh / a.shape[0]) * zoom_foto
        cx = min(max(ponto[0], fw / 2 / s), a.shape[1] - fw / 2 / s)      # janela dentro da foto
        cy = min(max(ponto[1], fh / 2 / s), a.shape[0] - fh / 2 / s)
        M = np.float32([[s, 0, fw / 2 - s * cx], [0, s, fh / 2 - s * cy]])
        r = cv2.warpAffine(a, M, (fw, fh), flags=cv2.INTER_AREA)
        r[..., :3] = fi.corrigir(r[..., :3], ganho, sat)
        r[..., 3] = 255.0
        W2, H2 = mold.shape[1], mold.shape[0]
        out = np.zeros((H2, W2, 4), np.float32)
        out[...] = 0
        out = sobre_rgba(out, r, int(fx0 - 3), int(fy0 - 3))
        out = sobre_rgba(out, mold, 0, 0)
        return out
    return ctx.cache(chave, _montar)


def sobre_rgba(base, lay, x, y):
    """RGBA sobre RGBA (alfa 0-255 ou 0-1 na camada; a base fica em 0-1)."""
    h, w = lay.shape[:2]
    xa, ya = max(0, x), max(0, y); xb, yb = min(base.shape[1], x + w), min(base.shape[0], y + h)
    if xa >= xb or ya >= yb:
        return base
    s = lay[ya - y:yb - y, xa - x:xb - x]
    a = s[..., 3:4] / (255.0 if lay[..., 3].max() > 1.5 else 1.0)
    b = base[ya:yb, xa:xb]
    ao = a + b[..., 3:4] * (1 - a)
    b[..., :3] = (s[..., :3] * a + b[..., :3] * b[..., 3:4] * (1 - a)) / np.maximum(ao, 1e-6)
    b[..., 3:4] = ao
    return base


def duas_molduras(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    ow, oh = p.get("tamanho_ouro", (400.0, 478.0))
    cx_l, cx_r = p.get("x", (290.0, 790.0)); cy = p.get("y", 880.0)
    ys = p.get("ys", (cy, cy))
    for i, it in enumerate(p["itens"]):
        if n < it["quadro"]:
            continue
        lay = _retrato_na_moldura(ctx, f"mold{i}", it["foto"], it["ponto"], it.get("zoom_foto", 1.0), ow, oh,
                                  it.get("ganho", 0.78), it.get("saturacao", 0.7))
        e = mo.escala_palavra((n - it["quadro"]) / FPS)
        if e < 0.999:
            lay = cv2.resize(lay, (max(1, int(lay.shape[1] * e)), max(1, int(lay.shape[0] * e))), interpolation=cv2.INTER_AREA)
        cx = cx_l if i == 0 else cx_r
        cyi = ys[i]
        sobre(img, lay, cx - lay.shape[1] / 2, cyi - lay.shape[0] / 2)
        if it.get("legenda"):
            corpo = _corpo_cabe(it["legenda"], ow * 1.05, 120)
            lp = it.get("legenda_pos")                  # [dx, dy] a partir do centro da moldura
            lc = (cx + lp[0], cyi + lp[1]) if lp else (cx, cyi + oh / 2 + 120)
            le.escrever(img, it["legenda"], centro=lc, fonte=le.SERIFA, corpo=corpo,
                        cor=le.TINTA, contorno=1.0, escala=e)
    z = assenta(n - p["inicio"], 0.22, 14.0)
    return zoom_em(img, z, (W / 2, cy))


# ============================================================ 25. encontro
# Duas fotos em cartao entram de lados opostos e se encontram no meio (negociar). Ease-out,
# cartoes tortos em sentidos contrarios, sombra mole; ao encontrar, um empurrao de camera.
def encontro(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    q = n - p["inicio"]
    larg = p.get("largura", 430.0)
    fim_q = p.get("chegada", 9)
    v = 1 - (1 - min(1.0, q / float(fim_q))) ** 2.4
    y = p.get("y", 880.0)
    for i, (foto, pt) in enumerate(zip(p["fotos"], p["pontos"])):
        card = ctx.cache(f"card{i}", lambda foto=foto, pt=pt, i=i: _com_sombra(
            _crop_rgb(st.carregar(foto), pt, larg, p.get("altura", 640.0)), (-3.0 if i == 0 else 3.0), pad=40))
        x_fim = (W / 2 - larg / 2 - 18) if i == 0 else (W / 2 + larg / 2 + 18)
        x_ini = -larg if i == 0 else W + larg
        x = x_ini + (x_fim - x_ini) * v
        sobre(img, card, x - card.shape[1] / 2, y - card.shape[0] / 2)
    z = 1.0 + 0.03 * u(q, fim_q, fim_q + 9)
    return zoom_em(img, z, (W / 2, y))


def _crop_rgb(a, ponto, larg, alt, ganho=0.92):
    s = max(larg / a.shape[1], alt / a.shape[0])
    cx = min(max(ponto[0], larg / 2 / s), a.shape[1] - larg / 2 / s)
    cy = min(max(ponto[1], alt / 2 / s), a.shape[0] - alt / 2 / s)
    M = np.float32([[s, 0, larg / 2 - s * cx], [0, s, alt / 2 - s * cy]])
    r = cv2.warpAffine(a[..., :3], M, (int(larg), int(alt)), flags=cv2.INTER_AREA)
    return fi.corrigir(r, ganho, 0.85)


# ============================================================ 26. objeto_no_papel
# Recorte de objeto REAL (foto de produto) no papel, com sombra mole, subindo e assentando
# com um leve giro — o "objeto 3D" do Priming feito com foto de verdade.
def objeto_no_papel(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    q = n - p["inicio"]
    larg = p.get("largura", 820.0)
    a = ctx.cache("obj", lambda: st.carregar(p["objeto"]))
    ob = ctx.cache("ob", lambda: _escala_ink(a, larg)[0])
    sombra = ctx.cache("sombra", lambda: _sombra_objeto(ob))
    f = mo.subida((q - 1) / FPS, dur=0.45, tau=0.11)
    cx, cy = p.get("centro", (W / 2, 900.0))
    dy = (1 - f) * 900.0
    rot = p.get("rot", 0.0) * (1 - 0.6 * f)
    for lay in (sombra, ob):
        l = lay
        if rot:
            M = cv2.getRotationMatrix2D((l.shape[1] / 2, l.shape[0] / 2), rot, 1.0)
            l = cv2.warpAffine(l, M, (l.shape[1], l.shape[0]), flags=cv2.INTER_LINEAR)
        sobre(img, l, cx - l.shape[1] / 2, cy - l.shape[0] / 2 + dy)
    return zoom_em(img, 1.0 + 0.05 * u(n, p["inicio"], p["fim"]), (cx, cy))


def _sombra_objeto(ob):
    h, w = ob.shape[:2]
    al = ob[..., 3] / (255.0 if ob[..., 3].max() > 1.5 else 1.0)
    pad = 60
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    s = np.zeros(out.shape[:2], np.float32)
    s[pad + 26:pad + 26 + h, pad + 12:pad + 12 + w] = al * 0.5
    out[..., 3] = cv2.GaussianBlur(s, (0, 0), 20)
    return out


# ============================================================ 27. baloes
# "Todo mundo falando": balões de fala a tinta estouram em pontos diferentes do papel, um a
# cada degrau da fala, cada um com seu giro e suas reticências.
def baloes(n, p, ctx):
    img = ctx.cache("papel", bg.papel).copy()
    q = n - p["inicio"]
    rng = np.random.default_rng(p.get("semente", 8))
    pos = [(250, 520), (760, 440), (520, 700), (190, 930), (830, 880), (470, 1130), (260, 1330), (780, 1260),
           (560, 1480), (150, 640), (900, 650), (640, 1010)]
    cada = p.get("cada", 3)
    for i, (x, y) in enumerate(pos):
        t0 = p["inicio"] + 2 + i * cada
        if n < t0:
            continue
        e = mo.escala_palavra((n - t0) / FPS)
        w = 250 + int(rng.integers(-40, 70)); h = 150 + int(rng.integers(-20, 40))
        lado = 1 if i % 2 else -1
        big = np.zeros((h + 80, w + 40, 4), np.float32)
        m = np.zeros((h + 80, w + 40), np.uint8)
        cv2.rectangle(m, (20 + 24, 12 + 24), (20 + w - 24, 12 + h - 24), 255, -1, cv2.LINE_AA)
        cv2.circle(m, (20 + 24 + 24, 12 + h - 24), 24, 255, -1, cv2.LINE_AA)
        cv2.circle(m, (20 + w - 24 - 24, 12 + 24 + 24), 24, 255, -1, cv2.LINE_AA)
        cv2.rectangle(m, (20 + 24, 12), (20 + w - 24, 12 + h), 255, -1, cv2.LINE_AA)
        cv2.rectangle(m, (20, 12 + 24), (20 + w, 12 + h - 24), 255, -1, cv2.LINE_AA)
        cauda = np.array([[20 + w // 2 - 20 * lado, 12 + h - 6], [20 + w // 2 + 30 * lado, 12 + h - 6],
                          [20 + w // 2 + 46 * lado, 12 + h + 46]], np.int32)
        cv2.fillConvexPoly(m, cauda, 255, cv2.LINE_AA)
        a = cv2.GaussianBlur(m.astype(np.float32) / 255.0, (0, 0), 0.9)
        borda = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(np.float32) / 255.0,
                                 (0, 0), 0.9)
        big[..., :3] = TINTA_D; big[..., 3] = borda
        big[..., :3] = big[..., :3] * (1 - a[..., None]) + np.array(FOLHA, np.float32) * a[..., None]
        for j in range(3):
            cv2.circle(big, (20 + w // 2 + (j - 1) * 46, 12 + h // 2), 10, TINTA_D + (1.0,), -1, cv2.LINE_AA)
        r = cv2.resize(big, (max(1, int(big.shape[1] * e)), max(1, int(big.shape[0] * e))), interpolation=cv2.INTER_AREA)
        r = _rot_rgba(r, float(rng.integers(-9, 10)))
        sobre(img, r, x - r.shape[1] / 2, y - r.shape[0] / 2)
    return zoom_em(img, 1.0 + 0.04 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


def _rot_rgba(a, graus):
    pad = int(0.25 * max(a.shape[:2]))
    big = np.zeros((a.shape[0] + 2 * pad, a.shape[1] + 2 * pad, 4), np.float32)
    big[pad:pad + a.shape[0], pad:pad + a.shape[1]] = a
    M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), graus, 1.0)
    return cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR)


# ============================================================ 28. termometro
# "Seis em cada dez": coluna de dez blocos que acendem de baixo para cima, um por degrau, com
# a linha do limite e o numeral ao lado. Outra forma de ver a mesma proporcao (sem pessoas).
def termometro(n, p, ctx):
    img = _fundo(ctx, p)
    q = n - p["inicio"]
    bw, bh, gap = p.get("largura", 500), 100, 14
    cx = p.get("x", W / 2.0 - 130)
    base = p.get("base", 1420)
    passo = p.get("passo", 3); ini = p.get("de", 0)
    s_ = 0 if q < ini else (q - ini) // passo + 1
    v = min(float(p["valor"]), float(s_))
    azul = tuple(float(c) for c in st.AZUL_UI)
    for k in range(10):
        y1 = base - k * (bh + gap); y0 = y1 - bh
        x0 = int(cx - bw / 2); x1 = int(cx + bw / 2)
        if k < v:
            cv2.rectangle(img, (x0, int(y0)), (x1, int(y1)), TINTA_D, -1, cv2.LINE_AA)
        else:
            cv2.rectangle(img, (x0, int(y0)), (x1, int(y1)), (220.0, 220.0, 224.0) if p.get("fundo") == "canvas" else (214.0, 212.0, 207.0), -1, cv2.LINE_AA)
            cv2.rectangle(img, (x0, int(y0)), (x1, int(y1)), (150.0, 150.0, 158.0) if p.get("fundo") == "canvas" else (150.0, 148.0, 146.0), 2, cv2.LINE_AA)
    m = p.get("limite")
    if m and n >= m["quadro"]:
        yl = int(base - m["valor"] * (bh + gap) + gap / 2)
        xa = int(cx - bw / 2 - 60)
        for xx in range(xa, int(cx + bw / 2 + 330), 26):
            cv2.line(img, (xx, yl), (xx + 14, yl), azul, 5, cv2.LINE_AA)
        le.escrever(img, m["texto"], centro=(cx + bw / 2 + 170, yl - 105), fonte=le.SERIFA, corpo=m.get("corpo", 210),
                    cor=azul, contorno=1.0, escala=mo.escala_palavra((n - m["quadro"]) / FPS))
    return zoom_em(img, 1.0 + 0.04 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


# ============================================================ 29. dois_lados
# "Negociar": o presidente (pessoa) e o Congresso (a silhueta das duas cupulas e das torres)
# frente a frente, com setas a mao de ida e de volta que se desenham uma depois da outra.
def _congresso_icone(w=520):
    h = int(w * 0.52)
    SS = 4
    big = np.zeros((h * SS, w * SS), np.uint8)
    laje = int(h * SS * 0.09)
    y_laje = h * SS - laje
    big[y_laje:, :] = 255
    cv2.ellipse(big, (int(w * SS * 0.20), y_laje), (int(w * SS * 0.17), int(h * SS * 0.30)), 0, 180, 360, 255, -1, cv2.LINE_AA)
    r2y = int(h * SS * 0.20)
    cv2.ellipse(big, (int(w * SS * 0.77), y_laje - r2y), (int(w * SS * 0.20), r2y), 0, 0, 180, 255, -1, cv2.LINE_AA)
    tx, tw = int(w * SS * 0.44), int(w * SS * 0.040)
    big[y_laje - int(h * SS * 0.88):y_laje, tx:tx + tw] = 255
    big[y_laje - int(h * SS * 0.80):y_laje, tx + tw + int(w * SS * 0.035):tx + 2 * tw + int(w * SS * 0.035)] = 255
    return cv2.resize(big, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0


def dois_lados(n, p, ctx):
    img = _fundo(ctx, p)
    azul = tuple(float(c) for c in st.AZUL_UI)
    ink = np.array(TINTA_D, np.float32)

    def pecas(m, centro, quadro):
        if n < quadro:
            return
        e = mo.escala_palavra((n - quadro) / FPS)
        mm = m if e >= 0.999 else cv2.resize(m, (max(1, int(m.shape[1] * e)), max(1, int(m.shape[0] * e))),
                                              interpolation=cv2.INTER_AREA)
        reg_y = int(centro[1] - mm.shape[0] / 2); reg_x = int(centro[0] - mm.shape[1] / 2)
        h_, w_ = mm.shape
        ya, xa = max(0, reg_y), max(0, reg_x)
        yb, xb = min(H, reg_y + h_), min(W, reg_x + w_)
        if ya < yb and xa < xb:
            s = mm[ya - reg_y:yb - reg_y, xa - reg_x:xb - reg_x, None]
            img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - s) + ink * s
    pessoa = ctx.cache("pessoa", lambda: _icone_pessoa(250, 330))
    cong = ctx.cache("cong", lambda: _congresso_icone(600))
    pecas(pessoa, p.get("pos_pessoa", (540, 620)), p["quadro_pessoa"])
    pecas(cong, p.get("pos_congresso", (540, 1270)), p["quadro_congresso"])
    for chave, (x, y0, y1) in (("quadro_ida", (410, 790, 1090)), ("quadro_volta", (670, 1090, 790))):
        q0 = p.get(chave)
        if q0 is not None and n >= q0:
            g = min(1.0, (n - q0) / 6.0)
            if g > 0.05:
                sobre(img, st.seta_mao((x, y0), (x + 6, y0 + (y1 - y0) * g), curva=0.10, esp=8.0, cor=azul, ponta=46,
                                       semente=7 if chave == "quadro_ida" else 9))
    return zoom_em(img, 1.0 + 0.045 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


# ====================================================================== v10 — looks
# Cada tipo de CONTEUDO ganha o look da referencia que o faz bem:
#   papel   (Hedy)    palavra, carimbo
#   parede  (galeria) moldura dourada pendurada com luz de janela; calendario
#   canvas  (Priming) diagrama e objeto: claro, quadriculado fino, piso em perspectiva
#   preto   (Outreach) texto que acende com desfoque, regua, curva fina
#   radar   (Hedy)    caixas de interface
def _parede(ctx):
    def _f():
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        base = 178.0 + 16.0 * (1 - yy / H) - 8.0 * xx / W
        img = np.repeat(base[..., None], 3, axis=2)
        ang = math.radians(-24.0)
        u_ = xx * math.cos(ang) + yy * math.sin(ang)
        luz = np.zeros((H, W), np.float32)
        for c, w, a in ((120, 80, 0.24), (470, 140, 0.18), (860, 70, 0.14), (1250, 120, 0.10)):
            luz += a * np.exp(-(((u_ - c) / w) ** 2))
        img += (luz * 70.0)[..., None]
        r = np.hypot((xx - W / 2) / (W * 0.8), (yy - H * 0.45) / (H * 0.7))
        img *= (1 - 0.30 * np.clip(r, 0, 1.3) ** 2)[..., None]
        rng = np.random.default_rng(5)
        m = cv2.resize(rng.normal(0, 1, (H // 40 + 2, W // 40 + 2)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
        img += (cv2.GaussianBlur(m, (0, 0), 12) * 2.2)[..., None]
        img[..., 2] += 3.0                               # parede levemente fria
        return img
    return ctx.cache("parede", _f).copy()


def _canvas(ctx, piso=False):
    def _f():
        img = np.empty((H, W, 3), np.float32); img[:] = 240.0
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W * 0.8), (yy - H / 2) / (H * 0.75))
        img *= (1 - 0.045 * np.clip(r, 0, 1.4) ** 2)[..., None]
        pas = 54
        for x in range(0, W, pas):
            img[:, x:x + 1] -= 17.0
        for y in range(0, H, pas):
            img[y:y + 1, :] -= 17.0
        if piso:
            y0 = int(H * 0.60)
            vp = (W / 2.0, H * 0.46)
            m = np.zeros((H, W), np.float32)
            for k in range(-14, 15):
                xb = W / 2 + k * 150.0
                cv2.line(m, (int(vp[0]), int(vp[1])), (int(xb), H), 1.0, 2, cv2.LINE_AA)
            yk = y0
            d = 26.0
            while yk < H:
                cv2.line(m, (0, int(yk)), (W, int(yk)), 1.0, 2, cv2.LINE_AA)
                yk += d; d *= 1.22
            fade = np.clip((np.arange(H) - y0) / 260.0, 0, 1)[:, None]
            img -= (m * fade * 30.0)[..., None]
            img[:y0] += 0
        return img
    return ctx.cache(("canvas", piso), _f).copy()


def _sombra_alfa(lay, desloc=(16, 26), blur=20.0, forca=0.5):
    """Sombra mole de uma camada RGBA (alfa 0-1 ou 0-255): devolve RGBA preto com a sombra."""
    a = lay[..., 3] / (255.0 if lay[..., 3].max() > 1.5 else 1.0)
    h, w = a.shape
    pad = int(blur * 3 + max(abs(desloc[0]), abs(desloc[1])))
    s = np.zeros((h + 2 * pad, w + 2 * pad), np.float32)
    s[pad + desloc[1]:pad + desloc[1] + h, pad + desloc[0]:pad + desloc[0] + w] = a * forca
    s = cv2.GaussianBlur(s, (0, 0), blur)
    out = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    out[..., 3] = s
    return out, pad


# ---------------------------------------------------------------- multidao (o povo, de costas)
def _pessoa_costas(img, cx, cy, r, cor, luz=None):
    """Silhueta de uma pessoa de costas: cabeca em (cx, cy), raio r; o tronco desce ate a borda."""
    c = tuple(float(v) for v in cor)
    ombro_y = cy + 1.9 * r
    if luz is not None:
        l = tuple(float(v) for v in luz)
        cv2.circle(img, (int(cx), int(cy - 1)), int(r + 1), l, -1, cv2.LINE_AA)
        cv2.ellipse(img, (int(cx), int(ombro_y + 1.2 * r)), (int(2.45 * r), int(1.7 * r)), 0, 180, 360, l, -1, cv2.LINE_AA)
    cv2.circle(img, (int(cx), int(cy)), int(r), c, -1, cv2.LINE_AA)
    cv2.rectangle(img, (int(cx - 0.45 * r), int(cy + 0.6 * r)), (int(cx + 0.45 * r), int(ombro_y + 0.2 * r)), c, -1)
    cv2.ellipse(img, (int(cx), int(ombro_y + 1.4 * r)), (int(2.45 * r), int(1.8 * r)), 0, 180, 360, c, -1, cv2.LINE_AA)
    cv2.rectangle(img, (int(cx - 2.45 * r), int(ombro_y + 1.4 * r)), (int(cx + 2.45 * r), H + 4), c, -1)


def _multidao_posicoes(n, x0, x1, semente):
    """n pessoas em 5 fileiras com perspectiva, entre x0 e x1. Devolve [(x, y_cabeca, r, fila, atraso)]."""
    rng = np.random.default_rng(semente)
    filas = [(1175, 11, 0.20), (1245, 13, 0.18), (1330, 16, 0.18), (1435, 20, 0.22), (1565, 25, 0.22)]
    tot = sum(f[2] for f in filas)
    out = []; k = 0
    for fi_, (y, r, frac) in enumerate(filas):
        m = int(round(n * frac / tot)) if fi_ < len(filas) - 1 else n - k
        k += m
        for j in range(m):
            x = x0 + (x1 - x0) * (j + 0.5 + rng.uniform(-0.28, 0.28)) / m
            out.append((x, y + rng.uniform(-9, 9), r * rng.uniform(0.92, 1.08), fi_, int(rng.integers(0, 10))))
    return out


MULTIDAO_COR = [(150, 148, 150), (112, 110, 114), (78, 76, 80), (48, 46, 50), (24, 22, 26)]


MULTIDAO_AZUL = [(120, 170, 210), (70, 130, 190), (34, 100, 168), (21, 80, 140), (14, 56, 104)]


def _desenhar_multidao(img, n, pessoas, q0, acento=None, voce=None, paleta=None):
    """Cada pessoa sobe de baixo (ease-out) a partir de q0 + atraso*? ; fila de tras primeiro."""
    for (x, y, r, fi_, atraso) in sorted(pessoas, key=lambda p: p[3]):
        t = n - (q0 + fi_ * 3 + atraso)
        if t < 0:
            continue
        sobe = 330.0 * math.exp(-t / 5.0)
        cor = (paleta or MULTIDAO_COR)[fi_]
        luz = tuple(min(255, c + 46) for c in cor)
        _pessoa_costas(img, x, y + sobe, r, cor, luz)
    if voce is not None and n >= voce["quadro"]:
        t = n - voce["quadro"]
        sobe = 330.0 * math.exp(-t / 5.0)
        _pessoa_costas(img, voce.get("x", W / 2), voce.get("y", 1500) + sobe, voce.get("r", 30), st.AZUL_UI,
                       tuple(min(255, c + 50) for c in st.AZUL_UI))


def _fundo(ctx, p):
    """Fundo do plano: "papel" (padrao), "canvas" (Priming), "parede" (galeria)."""
    f = p.get("fundo", "papel")
    if f == "canvas":
        return _canvas(ctx, p.get("piso", False))
    if f == "parede":
        return _parede(ctx)
    return ctx.cache("papel", bg.papel).copy()


# ============================================================ 30. galeria
# Galeria documental: as molduras douradas penduradas na parede, luz de janela
# riscando; legenda em serifa italica; e o POVO de costas embaixo, cada grupo sob a sua
# moldura (a proporcao de cada lado como gente, sem numero).
def galeria(n, p, ctx):
    img = _parede(ctx)
    ow, oh = p.get("tamanho_ouro", (420.0, 502.0))
    cxs = p.get("x", (300.0, 780.0)); cy = p.get("y", 610.0)
    for i, it in enumerate(p["itens"]):
        if n < it["quadro"]:
            continue
        lay = _retrato_na_moldura(ctx, f"gal{i}", it["foto"], it["ponto"], it.get("zoom_foto", 1.0), ow, oh,
                                  it.get("ganho", 0.86), it.get("saturacao", 0.78))
        e = mo.escala_palavra((n - it["quadro"]) / FPS)
        lay2 = lay if e >= 0.999 else cv2.resize(lay, (max(1, int(lay.shape[1] * e)), max(1, int(lay.shape[0] * e))),
                                                  interpolation=cv2.INTER_AREA)
        sh, pad = _sombra_alfa(lay2, (18, 28), 18.0, 0.55)
        x = cxs[i] - lay2.shape[1] / 2; y = cy - lay2.shape[0] / 2
        sobre(img, sh, x - pad, y - pad)
        sobre(img, lay2, x, y)
        if it.get("legenda"):
            corpo = _corpo_cabe(it["legenda"], ow * 0.9, 96)
            le.escrever(img, it["legenda"], centro=(cxs[i], cy + oh / 2 + 84), fonte=le.SERIFA, corpo=corpo,
                        cor=(34.0, 30.0, 34.0), contorno=1.0, escala=e)
    for k, sa in enumerate(p.get("setas", [])):      # "um do outro": setas a mao entre as molduras
        if n >= sa["quadro"]:
            g = min(1.0, (n - sa["quadro"]) / 6.0)
            (x0, y0), (x1, y1) = sa["de"], sa["para"]
            if g > 0.05:
                sobre(img, st.seta_mao((x0, y0), (x0 + (x1 - x0) * g, y0 + (y1 - y0) * g), curva=sa.get("curva", 0.3),
                                       esp=sa.get("esp", 6.0), cor=tuple(sa.get("cor", VERMELHO)), ponta=44, semente=5 + k))
    me = p.get("meio")                               # um objeto que "entra no meio" (cai entre as molduras)
    if me and n >= me["quadro"]:
        from planos_noticia import _icone
        ic = ctx.cache("meio", lambda: _icone(me.get("icone", "celular"), me.get("tam", 150)))
        f_ = mo.subida((n - me["quadro"]) / FPS, 0.45, 0.09)
        x, y = me.get("pos", (W / 2, 980))
        y = y - (1 - f_) * 700
        sh, pad = _sombra_alfa(ic, (10, 22), 14.0, 0.4)
        sobre(img, sh, x - ic.shape[1] / 2 - pad, y - ic.shape[0] / 2 - pad)
        sobre(img, ic, x - ic.shape[1] / 2, y - ic.shape[0] / 2)
        if me.get("rotulo") and n >= me.get("quadro_rotulo", me["quadro"]):
            e = mo.escala_palavra((n - me.get("quadro_rotulo", me["quadro"])) / FPS)
            le.escrever(img, me["rotulo"], centro=(x, y + ic.shape[0] / 2 + 80), fonte=le.SERIFA, corpo=me.get("corpo", 110),
                        cor=(30.0, 26.0, 30.0), contorno=1.0, escala=e)
    # o povo
    pov = p.get("povo")
    if pov:
        gr = ctx.cache("povo", lambda: [
            _multidao_posicoes(pov.get("n", (47, 45))[0], 70, 500, 3),
            _multidao_posicoes(pov.get("n", (47, 45))[1], 580, 1010, 8)])
        for k, pes in enumerate(gr):
            q0 = pov["quadro"][k] if isinstance(pov["quadro"], (list, tuple)) else pov["quadro"]
            dest = any(d["grupo"] == k and d["quadro"] <= n < d.get("ate", 10 ** 9) for d in pov.get("destaque", []))
            _desenhar_multidao(img, n, pes, q0, paleta=MULTIDAO_AZUL if dest else None)
        if pov.get("voce"):                                  # UMA pessoa em azul: voce (por cima dos dois grupos)
            _desenhar_multidao(img, n, [], 0, voce=pov["voce"])
    for b in p.get("baloes", []):                    # "todo mundo falando": baloes sobre o povo
        _baloes_desenhar(img, n, b["inicio"], b.get("cada", 3), b.get("pos"), b.get("semente", 8))
    for w in p.get("palavras", []):                  # palavra sobre a parede (serifa grande; pode cair)
        if n < w["quadro"] or n >= w.get("ate", 10 ** 9):
            continue
        if w.get("queda") and n >= w["queda"] + 16:       # ja saiu de quadro
            continue
        esc = mo.escala_palavra((n - w["quadro"]) / FPS)
        cor = tuple(w.get("cor", (30.0, 26.0, 30.0)))
        lay_w = le.palavra(w["texto"], esc, centro=(w.get("x", W / 2), w.get("y", 1070)), corpo=w.get("corpo", 150), cor=cor)
        if w.get("queda") and n >= w["queda"]:
            t_ = (n - w["queda"]) / FPS
            rot, ddx, ddy = mo.queda(t_, 0.5)
            ddy += 1500.0 * max(0.0, t_ - 0.5)              # continua caindo ate sair do quadro
            img = _tela_com_camada(img, lay_w, _afim_em_torno((w.get("x", W / 2), w.get("y", 1070)), -rot, ddx, ddy))
        else:
            img = sobre(img, lay_w)
    c = p.get("camera", {"z": (1.16, 1.0)})
    z = mv.entre(c["z"][0], c["z"][1], mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "saida", 1.8))
    return zoom_em(img, z, tuple(c.get("foco", (W / 2, 800))))


# ============================================================ 31. hud_texto
# Outreach: preto, regua nas bordas, curva fina que se desenha, texto creme que entra
# desfocado e assenta; a palavra-chave ganha a caixa de selecao azul.
def hud_texto(n, p, ctx):
    def _bg():
        yy, xx = np.mgrid[:H, :W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W * 0.7), (yy - H / 2) / (H * 0.6))
        img = (7.0 + 9.0 * np.clip(1 - r, 0, 1) ** 1.5)
        img = np.repeat(img[..., None], 3, axis=2).astype(np.float32)
        img[..., 2] += 3.0 * np.clip(1 - r, 0, 1)
        for x in (46, W - 46):
            img[250:1700, x:x + 2] = (62, 62, 68)
            for y in range(250, 1700, 28):
                ln = 26 if ((y - 250) // 28) % 5 == 0 else 12
                xa = x if x < W / 2 else x - ln + 2
                img[y:y + 2, xa:xa + ln] = (84, 84, 92)
        rng = np.random.default_rng(2)
        for _ in range(14):
            x, y = int(rng.integers(80, W - 80)), int(rng.integers(260, 1660))
            img[y:y + 3, x:x + 3] = (170, 170, 176)
        return img
    img = ctx.cache("bg", _bg).copy()
    q = n - p["inicio"]
    z = 1.0 + 0.07 * u(n, p["inicio"], p["fim"])
    # curva fina
    cv_ = p.get("curva")
    if cv_ is not False:
        pts = ctx.cache("curva", lambda: _bezier_pts([(-40, 1640), (60, 700), (420, 380), (1140, 520)], 120))
        g = min(1.0, q / 14.0)
        m = np.zeros((H, W), np.uint8)
        k = max(2, int(len(pts) * g))
        cv2.polylines(m, [np.int32(pts[:k])], False, 255, 3, cv2.LINE_AA)
        a = (m.astype(np.float32) / 255.0 * 0.85)[..., None]
        img = img * (1 - a) + np.array((222.0, 148.0, 72.0), np.float32) * a
    lin = p["linhas"]
    ys = p.get("ys") or [900 + (i - (len(lin) - 1) / 2) * 190 for i in range(len(lin))]
    cor = np.array(p.get("cor", (238.0, 228.0, 192.0)), np.float32)
    for L, yc in zip(lin, ys):
        if n < L["quadro"]:
            continue
        t = n - L["quadro"]
        borr = 10.0 * max(0.0, 1.0 - t / 6.0)
        alfa = min(1.0, (t + 2) / 6.0)
        corpo = L.get("corpo", 120)
        corpo = _corpo_cabe(L["texto"], 880.0, corpo) if False else corpo
        lay = np.zeros((H, W, 3), np.float32); lay_a = np.zeros((H, W), np.float32)
        m_, _ = le.mascara(L["texto"], le.INTER, corpo, 800, 0.0, -2.0)
        w_, h_ = m_.size
        lim_ = 820.0 if L.get("caixa") else 900.0               # a caixa de selecao (alcas) tambem cabe na margem
        if w_ > lim_:
            corpo = corpo * lim_ / w_
            m_, _ = le.mascara(L["texto"], le.INTER, corpo, 800, 0.0, -2.0); w_, h_ = m_.size
        x0, y0 = int(W / 2 - w_ / 2), int(yc - h_ / 2)
        a_ = np.asarray(m_, np.float32) / 255.0
        ya, xa = max(0, y0), max(0, x0); yb, xb = min(H, y0 + h_), min(W, x0 + w_)
        lay_a[ya:yb, xa:xb] = a_[ya - y0:yb - y0, xa - x0:xb - x0]
        halo = cv2.GaussianBlur(lay_a, (0, 0), 14.0) * 0.30
        if borr > 0.5:
            lay_a = cv2.GaussianBlur(lay_a, (0, 0), borr)
        s = np.clip(lay_a * alfa + halo * alfa, 0, 1)[..., None]
        img = img * (1 - s) + cor * s
        if L.get("caixa") and t >= 4:
            pad = 22
            sobre(img, st.selecao_azul(x0 - pad, y0 - pad * 0.6, x0 + w_ + pad, y0 + h_ + pad * 0.6, esp=4.0, r=12.0))
    return zoom_em(img, z, (W / 2, H / 2))


def _bezier_pts(c, k=100):
    c = np.array(c, np.float32)
    t = np.linspace(0, 1, k)[:, None]
    return ((1 - t) ** 3 * c[0] + 3 * (1 - t) ** 2 * t * c[1] + 3 * (1 - t) * t ** 2 * c[2] + t ** 3 * c[3])


# ============================================================ 32. canvas_objeto
# Priming: canvas claro quadriculado (piso em perspectiva), UM objeto em cinza com sombra
# mole, 1-3 palavras ao redor (a pequena clara, a grande escura) que entram desfocadas e
# assentam; circulo fino e caixa tracejada; a camera viaja ~1 s e para.
def canvas_objeto(n, p, ctx):
    img = _canvas(ctx, p.get("piso", True))
    q = n - p["inicio"]
    o = ctx.cache("obj", lambda: st.carregar(p["objeto"]))
    larg = p.get("largura", 700.0)
    ob = ctx.cache("ob", lambda: _escala_ink(o, larg)[0])
    if p.get("cinza", True):
        ob = ctx.cache("ob_cz", lambda: _cinza_contraste(ob))
    sh, pad = ctx.cache("sh", lambda: _sombra_alfa(ob, (22, 40), 26.0, 0.42))
    cx, cy = p.get("centro", (W / 2.0, 940.0))
    viagem = p.get("viagem", 14)
    v = mv.suavizar_curva(min(1.0, q / float(viagem)), "saida", 2.4)
    pos = p.get("origem", (130.0, 240.0))
    dx = (1 - v) * pos[0]; dy = (1 - v) * pos[1]
    zz = 1.0 + (1 - v) * p.get("zoom_inicio", 0.30)
    lay_obj = np.zeros((H, W, 3), np.float32)
    sobre(img, sh, cx - ob.shape[1] / 2 - pad, cy - ob.shape[0] / 2 - pad)
    sobre(img, ob, cx - ob.shape[1] / 2, cy - ob.shape[0] / 2)
    ci = p.get("circulo")
    if ci and n >= ci["quadro"]:
        g = min(1.0, (n - ci["quadro"]) / 8.0)
        cv2.ellipse(img, (int(cx), int(cy)), (int(ci["raio"]), int(ci["raio"])), 0, -90, -90 + 360 * g, (120.0, 120.0, 124.0), 3, cv2.LINE_AA)
    for w in p.get("palavras", []):
        if n < w["quadro"]:
            continue
        t = n - w["quadro"]
        borr = 9.0 * max(0.0, 1.0 - t / 8.0)
        alfa = min(1.0, (t + 2) / 8.0)
        peso = w.get("peso", 600); corpo = w.get("corpo", 96)
        cor = np.array(w.get("cor", (42.0, 42.0, 44.0)), np.float32)
        m_, _ = le.mascara(w["texto"], le.INTER, corpo, peso, 0.0, -1.5)
        w_, h_ = m_.size
        x0 = int(w["x"] - w_ / 2); y0 = int(w["y"] - h_ / 2)
        a_ = np.zeros((H, W), np.float32)
        am = np.asarray(m_, np.float32) / 255.0
        ya, xa = max(0, y0), max(0, x0); yb, xb = min(H, y0 + h_), min(W, x0 + w_)
        if ya < yb and xa < xb:
            a_[ya:yb, xa:xb] = am[ya - y0:yb - y0, xa - x0:xb - x0]
        if borr > 0.5:
            a_ = cv2.GaussianBlur(a_, (0, 0), borr)
        s = (a_ * alfa)[..., None]
        img = img * (1 - s) + cor * s
        if w.get("caixa"):
            pad_ = 20
            xa_, ya_, xb_, yb_ = x0 - pad_, y0 - pad_ * 0.7, x0 + w_ + pad_, y0 + h_ + pad_ * 0.7
            for xx in range(int(xa_), int(xb_), 24):
                cv2.line(img, (xx, int(ya_)), (min(xx + 12, int(xb_)), int(ya_)), (150.0, 150.0, 154.0), 3, cv2.LINE_AA)
                cv2.line(img, (xx, int(yb_)), (min(xx + 12, int(xb_)), int(yb_)), (150.0, 150.0, 154.0), 3, cv2.LINE_AA)
            for yy in range(int(ya_), int(yb_), 24):
                cv2.line(img, (int(xa_), yy), (int(xa_), min(yy + 12, int(yb_))), (150.0, 150.0, 154.0), 3, cv2.LINE_AA)
                cv2.line(img, (int(xb_), yy), (int(xb_), min(yy + 12, int(yb_))), (150.0, 150.0, 154.0), 3, cv2.LINE_AA)
    return cam(img, z=zz, dx=dx, dy=dy, fundo=(240.0, 240.0, 240.0))


def _cinza_contraste(a):
    """Objeto em escala de cinza com curva de contraste (pretos fundos, brancos limpos)."""
    out = a.copy()
    l = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0
    l = np.clip((l - 0.5) * 1.18 + 0.52, 0, 1) * 255.0
    out[..., 0] = out[..., 1] = out[..., 2] = l
    return out


# ============================================================ 33. pictograma
# "Sozinha": UMA pessoa grande, em tinta, sozinha no canvas; os votos que faltam chegam como
# contornos tracejados ao redor dela.
def pictograma(n, p, ctx):
    img = _canvas(ctx, False)
    q = n - p["inicio"]
    ink = np.array(TINTA_D, np.float32)
    alt = p.get("altura", 640)
    w_ = int(alt * 0.76)
    ico = ctx.cache("ico", lambda: _icone_pessoa(w_, alt))
    qp = p.get("quadro_pessoa", p["inicio"])
    cx, cy = p.get("centro", (W / 2.0, 900.0))
    if n >= qp:
        e = mo.escala_palavra((n - qp) / FPS)
        m = ico if e >= 0.999 else cv2.resize(ico, (max(1, int(ico.shape[1] * e)), max(1, int(ico.shape[0] * e))), interpolation=cv2.INTER_AREA)
        sh = cv2.GaussianBlur(np.pad(m, 40), (0, 0), 16) * 0.35
        y0 = int(cy - m.shape[0] / 2); x0 = int(cx - m.shape[1] / 2)
        img = _colar_mascara(img, sh, x0 - 40 + 16, y0 - 40 + 26, np.array((0.0, 0.0, 0.0), np.float32))
        img = _colar_mascara(img, m, x0, y0, ink)
    qf = p.get("quadro_fantasmas")
    if qf is not None:
        pos = p.get("fantasmas", [(250, 640), (830, 640), (160, 1000), (920, 1000), (300, 1330), (780, 1330)])
        for k, (fx, fy) in enumerate(pos):
            if n < qf + 3 * k:
                continue
            e = mo.escala_palavra((n - qf - 3 * k) / FPS)
            hh = int(alt * 0.42 * e); ww = int(hh * 0.76)
            if hh < 8:
                continue
            m = _icone_pessoa(ww, hh)
            cont, _ = cv2.findContours((m > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            oy, ox = int(fy - hh / 2), int(fx - ww / 2)
            for c in cont:
                c = c[:, 0, :]
                for i in range(0, len(c) - 1, 22):
                    seg = c[i:i + 12]
                    if len(seg) > 1:
                        cv2.polylines(img, [np.int32(seg + [ox, oy])], False, tuple(float(v) for v in st.AZUL_UI), 4, cv2.LINE_AA)
    return zoom_em(img, 1.0 + 0.05 * u(n, p["inicio"], p["fim"]), (W / 2, H / 2))


def _colar_mascara(img, m, x0, y0, cor):
    h, w = m.shape
    ya, xa = max(0, y0), max(0, x0); yb, xb = min(H, y0 + h), min(W, x0 + w)
    if ya >= yb or xa >= xb:
        return img
    s = m[ya - y0:yb - y0, xa - x0:xb - x0, None]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - s) + cor * s
    return img


def _baloes_desenhar(img, n, inicio, cada, pos=None, semente=8):
    """Os baloes de fala (mesmo desenho do tipo `baloes`) sobre uma imagem pronta."""
    rng = np.random.default_rng(semente)
    pos = pos or [(250, 1105), (790, 1100), (520, 1140), (150, 1150), (900, 1135), (400, 1095), (690, 1150), (80, 1115)]
    for i, (x, y) in enumerate(pos):
        t0 = inicio + 2 + i * cada
        if n < t0:
            continue
        e = mo.escala_palavra((n - t0) / FPS)
        w = 168 + int(rng.integers(-20, 36)); h = 100 + int(rng.integers(-10, 20))
        lado = 1 if i % 2 else -1
        big = np.zeros((h + 70, w + 40, 4), np.float32)
        m = np.zeros((h + 70, w + 40), np.uint8)
        cv2.rectangle(m, (20 + 22, 12), (20 + w - 22, 12 + h), 255, -1, cv2.LINE_AA)
        cv2.rectangle(m, (20, 12 + 22), (20 + w, 12 + h - 22), 255, -1, cv2.LINE_AA)
        for cxx, cyy in ((20 + 22, 12 + 22), (20 + w - 22, 12 + 22), (20 + 22, 12 + h - 22), (20 + w - 22, 12 + h - 22)):
            cv2.circle(m, (cxx, cyy), 22, 255, -1, cv2.LINE_AA)
        cauda = np.array([[20 + w // 2 - 18 * lado, 12 + h - 6], [20 + w // 2 + 26 * lado, 12 + h - 6],
                          [20 + w // 2 + 40 * lado, 12 + h + 40]], np.int32)
        cv2.fillConvexPoly(m, cauda, 255, cv2.LINE_AA)
        a = cv2.GaussianBlur(m.astype(np.float32) / 255.0, (0, 0), 0.9)
        borda = cv2.GaussianBlur(cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(np.float32) / 255.0, (0, 0), 0.9)
        big[..., :3] = TINTA_D; big[..., 3] = borda
        big[..., :3] = big[..., :3] * (1 - a[..., None]) + np.array(FOLHA, np.float32) * a[..., None]
        for j in range(3):
            cv2.circle(big, (20 + w // 2 + (j - 1) * 40, 12 + h // 2), 9, TINTA_D + (1.0,), -1, cv2.LINE_AA)
        r = cv2.resize(big, (max(1, int(big.shape[1] * e)), max(1, int(big.shape[0] * e))), interpolation=cv2.INTER_AREA)
        r = _rot_rgba(r, float(rng.integers(-9, 10)))
        sobre(img, r, x - r.shape[1] / 2, y - r.shape[0] / 2)
    return img

TIPOS = {
    "gancho_digitado": gancho_digitado, "palavra_no_papel": palavra_no_papel, "foto_pullout": foto_pullout,
    "cartao_rotulo": cartao_rotulo, "figura_e_palavras": figura_e_palavras, "documento_digitado": documento_digitado,
    "objeto_revela": objeto_revela, "lista_ui": lista_ui, "odometro": odometro, "moldura_legenda": moldura_legenda,
    "icone_cursor": icone_cursor, "site_url": site_url, "queda_objeto": queda_objeto,
    "palavras_e_figura": palavras_e_figura, "objeto_na_parede": objeto_na_parede, "amassar_lixeira": amassar_lixeira,
    "barras_placar": barras_placar, "dezena": dezena, "dupla_retratos": dupla_retratos,
    "calendario": calendario, "hemiciclo": hemiciclo, "carimbo": carimbo, "selecao_digitada": selecao_digitada,
    "duas_molduras": duas_molduras, "pizza": pizza, "termometro": termometro, "dois_lados": dois_lados, "galeria": galeria, "hud_texto": hud_texto,
    "canvas_objeto": canvas_objeto, "pictograma": pictograma, "encontro": encontro, "objeto_no_papel": objeto_no_papel, "baloes": baloes,
}

# v11 — a noticia explicada (ranking, terminal, podio, barras, centena, pizzas, celular, icones, semana,
# linha_no_papel, botao_cta): ver planos_noticia.py e referencias/planos.md
from planos_noticia import TIPOS_NOTICIA  # noqa: E402
TIPOS.update(TIPOS_NOTICIA)

# v12 — a galeria documental (moldura_entra, foto_recorte, etiqueta_rasgada, jornais_mesa): ver planos_galeria.py
from planos_galeria import TIPOS_GALERIA  # noqa: E402
TIPOS.update(TIPOS_GALERIA)

# v12.3 — o b-roll em vídeo (clipe gerado ou filmado) na grade da série: ver planos_video.py
from planos_video import TIPOS_VIDEO  # noqa: E402
TIPOS.update(TIPOS_VIDEO)

# v12.5 — objeto real (recorte de foto) em ação: salto, de_cabeca, ventilador, jatos — ver planos_objeto.py
from planos_objeto import TIPOS_OBJETO  # noqa: E402
TIPOS.update(TIPOS_OBJETO)

# v12.7 — o desenho que explica: linha_do_tempo (e a telestração de qualquer plano em desenho.py)
from planos_desenho import TIPOS_DESENHO  # noqa: E402
TIPOS.update(TIPOS_DESENHO)
