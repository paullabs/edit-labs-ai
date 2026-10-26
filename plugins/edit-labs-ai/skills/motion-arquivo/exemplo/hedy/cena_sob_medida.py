"""
Hedy completo — os 32 s do original (quadros 0–959), 23 planos, cortes nos mesmos
quadros da grade de 10 qps. Cada plano so COMBINA pecas das seis camadas; tempos,
posicoes e tamanhos foram medidos no original (coordenadas em 1080x1920).

Fotos da Hedy: dominio publico (Wikimedia Commons; nao acompanham o plugin, baixe pelo
buscar_assets.py e registre em assets/FONTES.md) — nunca rosto gerado. Objetos e cenas sem
pessoa real: gerados. O fecho e generico (sem a marca do anuncio original). Os poucos
textos curtos na tela seguem o original porque as medidas (largura, tempo por letra)
foram tiradas deles; num projeto novo, o texto e o da sua narracao.
"""
import math
import numpy as np, cv2
from familia_a import W, H
from familia_a import c1_background as bg, c2_letras as le, c3_style as st
from familia_a import c4_filtro as fi, c5_movimentos as mv, c6_motion as mo
from familia_a.compor import sobre
import teste_hedy as teste  # mesmo diretorio (rode com o motor e esta pasta no sys.path)

INICIO, FIM = 0, 960
CORTES = [0, 20, 32, 47, 92, 140, 146, 170, 209, 248, 359, 407, 449, 503, 536, 566, 617,
          698, 728, 758, 824, 845, 905, 960]
FPS = 30
BRANCO = (238.0, 236.0, 232.0)
PRETO_TINTA = (24.0, 20.0, 22.0)
_c = {}


def plano(n):
    for k in range(len(CORTES) - 1):
        if CORTES[k] <= n < CORTES[k + 1]:
            return k + 1
    return len(CORTES) - 1


def u(n, a, b):
    return min(1.0, max(0.0, (n - a) / float(b - a)))


def cache(nome, fn):
    if nome not in _c:
        _c[nome] = fn()
    return _c[nome]


def cam(img, z=1.0, dx=0.0, dy=0.0, fundo=None):
    return mv.camera(img, dx=dx, dy=dy, zoom=z, fundo=fundo)


def palavra_entra(img, texto, aparece, n, centro, corpo, cor=None, fonte=None):
    """Palavra que entra a 70% e cresce em ease-out (a entrada medida no papel)."""
    if n < aparece:
        return img
    e = mo.escala_palavra((n - aparece) / FPS)
    le.escrever(img, texto, centro=centro, fonte=fonte or le.SERIFA, corpo=corpo, cor=cor or le.TINTA,
                contorno=le.CONTORNO, escala=e)
    return img


def letras(img, texto, k, esquerda_tinta, yc, corpo, fonte, peso=None, cor=BRANCO, novos=0, queda=0.0):
    """Linha que cresce letra a letra a partir de uma borda esquerda fixa."""
    if k <= 0:
        return img
    cheio, (ox, oy) = le.mascara(texto, fonte, corpo, peso)
    topo = yc - cheio.size[1] / 2 + oy
    f = le._fonte(fonte, int(round(corpo * le.SS)), peso)
    x = esquerda_tinta + ox
    for i, ch in enumerate(texto[:k]):
        if ch != " ":
            m, (mx, my) = le.mascara(ch, fonte, corpo, peso)
            d = queda if i >= k - novos else 0.0
            le.tingir(img, m, x - mx, topo - my + d, cor)
        x += f.getlength(ch) / le.SS
    return img


def foto(nome, n, cx, cy, s, dx=0.0, dy=0.0, pb=False, grao=True):
    a = st.carregar(nome)
    if pb:
        a = cache("pb_" + nome, lambda: st.pb(st.carregar(nome)))
    img = st.foto_no_quadro(a, cx, cy, s, dx, dy)
    return fi.grao_foto(img, n) if grao else img


# ---------------------------------------------------------------- 1. EVERYONE
# Medido degrau a degrau no original (720 -> 1080, em coordenadas da composicao com a
# camera a 1). A camera inteira (folha quadriculada + texto) cresce em ease-out em torno do
# centro: periodo da grade 35,3 / 40,7 / 43,6 / 44,9 / 45,8 / 46,05 px. Grotesca bold
# (Arial Bold), maiuscula 67,4 px, tracking -7,8 px, tinta a partir de x 300,8, centro da
# maiuscula em y 958,5. So a letra nova de cada degrau se mexe: chega caida e apagada (a
# primeira tambem menor e inclinada). No ultimo degrau so o texto escorrega para a
# esquerda, borrado; a folha fica.
EVERY_ZOOM = {0: None, 2: 0.764, 5: 0.881, 8: 0.943, 11: 0.972, 14: 0.991, 17: 0.997}
EVERY_K = {2: 1, 5: 5, 8: 7, 11: 8}
EVERY_NOVA = {2: dict(queda=50.7, alfa=0.73, escala=0.85, cisalha=12.0),
              5: dict(queda=35.8, alfa=0.79),
              8: dict(queda=22.3, alfa=0.91),
              11: dict(queda=40.1, alfa=0.79)}
EVERY_DX = {2: 8.0, 5: 12.6, 8: 13.2, 11: 7.6, 14: 0.0}
EVERY_SAIDA = (17, -40.0, 14.0)          # degrau, deslocamento (px), borrao horizontal (px)
EVERY_COR = (194.0, 194.0, 194.0)        # nucleo p90 200 no original depois do acabamento


def _degrau(tabela, n):
    return tabela[max(k for k in tabela if k <= n)]


def p01(n):
    z = _degrau(EVERY_ZOOM, n)
    if z is None:
        return bg.chapado(bg.PRETO_EVERY)
    img = bg.grade_escura_no_quadro(z)
    corpo = cache("c_every", lambda: le.corpo_para_maiuscula(67.4))
    k = _degrau(EVERY_K, n)
    nova = EVERY_NOVA.get(n)
    lay = le.linha_digitada("EVERYONE", k, 300.8 + _degrau(EVERY_DX, n), 958.5, corpo=corpo, tracking=-7.8,
                            cor=EVERY_COR, nova=nova)
    q, desloc, borrao = EVERY_SAIDA
    lay = cam(lay, z=z, dx=desloc * z if n >= q else 0.0, fundo=EVERY_COR + (0.0,))
    if n >= q:
        lay[..., 3] = mv.borrao_direcional(lay[..., 3], borrao)
    return sobre(img, lay)


# ------------------------------------------------------------- 2-3. her beauty
def cena_beauty(lado):
    img = bg.papel()
    card = cache("cartao_hedy", lambda: st.cartao_foto(st.carregar("hedy_1940_clarence_bull.jpg"), 640, borda=22, rot=-2.0))
    sobre(img, card, 540 - card.shape[1] / 2, 300)
    corda = cache("corda", lambda: st.escalar(st.carregar("corda_veludo.png"), largura=1180))
    sobre(img, corda, 540 - corda.shape[1] / 2, 930)
    if lado == "dir":
        le.escrever(img, "her beauty", centro=(860, 330), corpo=50, contorno=le.CONTORNO)
        sobre(img, cache("seta_d", lambda: st.seta_mao((790, 366), (690, 470), curva=0.45, esp=3.0)))
    else:
        le.escrever(img, "her beauty", centro=(330, 560), corpo=50, contorno=le.CONTORNO)
        sobre(img, cache("seta_e", lambda: st.seta_mao((395, 600), (420, 650), curva=-0.55, esp=3.0)))
    return img


def p02(n):
    img = cache("beauty_dir", lambda: cena_beauty("dir")).copy()
    v = u(n, 20, 32)
    return cam(img, z=mv.entre(1.0, 0.976, v), dx=mv.entre(0, -73, v))


def p03(n):
    img = cache("beauty_esq", lambda: cena_beauty("esq")).copy()
    return cam(img, z=1.42, dx=40, dy=300)


# ------------------------------------------------------------------- 4. multidao
def p04(n):
    img = bg.papel()
    crowd = cache("crowd", lambda: st.escalar(st.carregar("multidao.png"), altura=760))
    dx = mv.entre(0, -167, u(n, 47, 92), "s", 2.0)
    sobre(img, crowd, 540 - crowd.shape[1] / 2 + 60 + dx, 760)
    for txt, ap, cx in [("almost", 50, 285), ("no one", 62, 502), ("realize", 74, 735)]:
        palavra_entra(img, txt, ap, n, (cx, 690), 38)
    return cam(img, z=mv.entre(1.0, 0.982, u(n, 47, 92)))


# ------------------------------------------------------------------- 5. patente
FRASE = "SHE HELPED CREATE THE TECHNOLOGY"
INI_TEC = len("SHE HELPED CREATE THE ")


def patente_desbotada():
    """Patente em bege fraco: tracos a ~35% de contraste sobre (189,179,163), como no original."""
    a = st.foto_no_quadro(st.carregar("patente_pag6.jpg"), 1150, 2300, 1.25)
    l = a.mean(-1, keepdims=True) / 255.0
    traco = np.clip((0.80 - l) / 0.55, 0, 1)
    papel = np.array((189.0, 179.0, 163.0)); tinta = np.array((128.0, 118.0, 106.0))
    return papel * (1 - traco * 0.55) + tinta * (traco * 0.55)


def base_patente(n):
    img = cache("pat6", lambda: patente_desbotada()).copy()
    corpo = cache("c_she", lambda: le.corpo_para_largura("SHE HELPED", 215, le.INTER, peso=700))
    k = 0 if n < 96 else min(len(FRASE), 3 + (n - 96))
    x0, yc = 330.0, 958.0
    letras(img, FRASE, k, x0, yc, corpo, le.INTER, 700, PRETO_TINTA)
    f = le._fonte(le.INTER, int(round(corpo * le.SS)), 700)
    adv = lambda s: f.getlength(s) / le.SS
    cheio, (ox, oy) = le.mascara(FRASE, le.INTER, corpo, 700)
    xc = x0 + ox + adv(FRASE[:k]) + 4
    alt = cheio.size[1]
    if n >= 116 and k > INI_TEC:
        xs = x0 + ox + adv(FRASE[:INI_TEC]) - 3
        sobre(img, st.selecao_azul(xs, yc - alt / 2 - 6, xc + 2, yc + alt / 2 + 6, esp=2.0, r=6))
    img[int(yc - alt * .62):int(yc + alt * .62), int(xc):int(xc) + 3] = PRETO_TINTA
    return img, xc, yc


def p05(n):
    img, xc, yc = base_patente(n)
    if n < 116:
        return cam(img, z=mv.entre(1.0, 0.985, u(n, 92, 116)))
    z = 1.85 if n < 137 else mv.entre(1.85, 1.35, u(n, 137, 140), "entrada", 2.0)
    alvo = (810.0, 910.0)
    dx = alvo[0] - (W / 2 + z * (xc - W / 2)); dy = alvo[1] - (H / 2 + z * (yc - H / 2))
    return cam(img, z=z, dx=dx, dy=dy)


# ------------------------------------------------------------------ 6-7. roteador
LINHA = "BEHIND YOUR WI-FI."


# Medido degrau a degrau (720 -> 1080). A camera inteira (roteador + texto) ABRE de 1,7x
# para 1x em torno de (540, 990) — o corpo do roteador vai de 446 a 303 px em 720 — e o
# roteador ainda sobe na composicao. Fundo preto (7,7,7) onde um DOMO teal (raio 2046)
# sobe da base e cobre o quadro em 0,8 s: a onda do Wi-Fi. Texto em grotesca bold
# (maiuscula 55, tracking -4,4, 682 px, centro 543,741), cinza 193; cada palavra entra a
# fade proprio (P7_ALFA): BEHIND a partir de 143, YOUR de 146, WI-FI. de 149.
P7_ZOOM = {140: 1.70, 143: 1.487, 146: 1.327, 149: 1.223, 152: 1.15, 155: 1.11, 158: 1.07,
           161: 1.045, 164: 1.028, 167: 1.012}
P7_SUBIDA = {140: 420.0, 143: 252.0, 146: 159.0, 149: 103.0, 152: 65.0, 155: 38.0, 158: 22.0,
             161: 10.0, 164: 3.6, 167: 2.2}
P7_DOMO = {140: None, 143: 1821.0, 146: 1119.0, 149: 627.0, 152: 309.0, 155: 162.0, 158: 81.0,
           161: 36.0, 164: 0.0, 167: -15.0}
P7_ANCORA = (540.0, 990.0)
P7_DOMO_R = 2046.0
P7_DOMO_PERFIL = [(0, 12.9), (60, 12.9), (300, 14.5), (540, 17.9), (780, 16.6), (1020, 18.6),
                  (1260, 13.0), (1500, 9.7), (1740, 3.6), (1920, 2.0)]
P7_PALAVRAS = [("BEHIND", 143), ("YOUR", 146), ("WI-FI.", 152)]
# opacidade de cada palavra por degrau (p99 da palavra no original): o fade e continuo e
# cada palavra comeca numa fase diferente da grade de 10 qps
P7_ALFA = {"BEHIND": {143: 0.41, 146: 0.86, 149: 1.0},
           "YOUR": {146: 0.08, 149: 0.79, 152: 0.96, 155: 1.0},
           "WI-FI.": {149: 0.06, 152: 0.56, 155: 0.92, 158: 1.0}}
P7_COR = (193.0, 193.0, 193.0)
P7_ROTEADOR = (572.0, 541.5, 1230.0)     # largura do asset (corpo 455), centro do corpo


def _sobre_pre(lay, src, x, y):
    """Cola RGBA (alfa 0-255 ou 0-1) numa camada PREMULTIPLICADA."""
    h, w = src.shape[:2]; x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y); xb, yb = min(W, x + w), min(H, y + h)
    if xa >= xb or ya >= yb:
        return lay
    s = src[ya - y:yb - y, xa - x:xb - x]
    a = s[..., 3:4] / (255.0 if src[..., 3].max() > 1.5 else 1.0)
    lay[ya:yb, xa:xb, :3] = s[..., :3] * a + lay[ya:yb, xa:xb, :3] * (1 - a)
    lay[ya:yb, xa:xb, 3:4] = a + lay[ya:yb, xa:xb, 3:4] * (1 - a)
    return lay


def _fundo_domo(n):
    img = bg.chapado((7.0, 7.0, 7.0))
    topo = _degrau(P7_DOMO, n)
    if topo is None:
        return img
    yy, xx = cache("grade_xy", lambda: np.mgrid[:H, :W].astype(np.float32))
    dentro = np.clip((P7_DOMO_R - np.hypot(xx - W / 2, yy - (topo + P7_DOMO_R))) / 4.0 + 0.5, 0, 1)
    # o perfil anda COM o domo: a frente ja chega teal e a base escurece depois que ele passa
    perfil = np.interp(np.arange(H) - topo, *zip(*P7_DOMO_PERFIL)).astype(np.float32)[:, None]
    sinal = dentro * perfil
    img[..., 0] -= 0.06 * sinal; img[..., 1] += 0.90 * sinal; img[..., 2] += 0.97 * sinal
    return img


def p07(n):
    lay = np.zeros((H, W, 4), np.float32)
    larg_r, cx_r, cy_r = P7_ROTEADOR
    r = cache("roteador_p7", lambda: st.escalar(st.carregar("roteador.png"), largura=larg_r))
    k = r.shape[1] / 841.0                       # corpo do asset: x 55-723, y 428-639 em 841 px
    _sobre_pre(lay, r, cx_r - 389.0 * k, cy_r - 533.5 * k + _degrau(P7_SUBIDA, n))
    corpo = cache("c_behind", lambda: le.corpo_para_maiuscula(55.0))
    larg = cache("l_behind", lambda: le.mascara(LINHA, le.GROTESCA, corpo, None, 0.0, -4.4)[0].size[0])
    linha = lambda kk: cache(f"behind_k{kk}", lambda: le.linha_digitada(
        LINHA, kk, 543.0 - larg / 2, 741.0, corpo=corpo, tracking=-4.4)[..., 3])
    a = np.zeros((H, W), np.float32); pos = 0
    for w, _ in P7_PALAVRAS:
        i = LINHA.index(w, pos); pos = i + len(w)
        tab = P7_ALFA[w]
        if n >= min(tab):
            a += _degrau(tab, n) * (linha(pos) - (linha(i) if i else 0.0))
    if a.max() > 0:
        a = a[..., None]
        lay[..., :3] = np.array(P7_COR, np.float32) * a + lay[..., :3] * (1 - a)
        lay[..., 3:4] = a + lay[..., 3:4] * (1 - a)
    z = _degrau(P7_ZOOM, n) if n < 170 else 1.0
    lay = cam(lay, z=z, dx=(1 - z) * (P7_ANCORA[0] - W / 2), dy=(1 - z) * (P7_ANCORA[1] - H / 2),
              fundo=(0.0, 0.0, 0.0, 0.0))
    img = _fundo_domo(n)
    return lay[..., :3] + img * (1 - lay[..., 3:4])


# --------------------------------------------------------------- 8. During WW2
P8_GANHO = (0.875, 0.857, 0.925)


def p08(n):
    v = mv.suavizar_curva(u(n, 170, 209), "saida", 1.3)
    s = 0.714 * mv.entre(1.78, 1.30, v)
    img = foto("g02_ww2_caminhoes.png", n, 760, 1344, s, dx=mv.entre(-72, 72, v), dy=mv.entre(59, -59, v))
    img = img * np.array(P8_GANHO, np.float32)                 # media do plano: 102/97/96 no original
    corpo = cache("c_ww2", lambda: le.corpo_para_largura("During WW2", 440, le.SERIFA))
    k = 0 if n < 173 else min(10, 1 + (n - 173) // 3)
    letras(img, "During WW2", k, 320, 950, corpo, le.SERIFA, None, BRANCO)
    return img


# --------------------------------------------------------- 9. retrato Ziegfeld
def p09(n):
    v = mv.suavizar_curva(u(n, 209, 248), "saida", 1.5)
    s = (1920 / 2904) * mv.entre(1.08, 1.045, v)
    return fi.corrigir(foto("hedy_ziegfeld_1941.jpg", n, 1014, 1250, s, dx=mv.entre(-120, 120, v), pb=True), 0.69)


# -------------------------------------------------- 10. palavras + torre
def camada_torre(n, desloc):
    lay = np.zeros((H, W, 4), np.float32)
    p = cache("pat7_tracos", lambda: tracos_patente())
    sobre_lay(lay, p, -210 + desloc, 150)
    vis = 0 if n < 302 else min(5.0, (n - 302) / 3.0 + 1)
    pecas = [cache(f"asas_{vis:.2f}", lambda: st.asas((495, 735), vis)),
             cache("torre", lambda: st.torre((495, 645), 1395, 315, 90))]
    for lay2 in pecas:
        sobre_lay(lay, lay2 if abs(desloc) < 0.5 else desloca(lay2, desloc), 0, 0)
    return lay


def tracos_patente():
    """So os tracos da patente (pag. 7), cinza e apagados — sem o retangulo da pagina."""
    pat = st.escalar(st.carregar("patente_pag7.jpg"), largura=1500)
    l = pat[..., :3].mean(-1) / 255.0
    a = np.clip((0.72 - l) / 0.40, 0, 1) * 0.24
    out = np.zeros_like(pat); out[..., :3] = (120.0, 118.0, 116.0); out[..., 3] = a
    return out


def desloca(lay, dx):
    M = np.float32([[1, 0, dx], [0, 1, 0]])
    return cv2.warpAffine(lay, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def sobre_lay(base, lay, x, y):
    """Compoe RGBA sobre RGBA (para montar uma camada antes de colar no papel)."""
    h, w = lay.shape[:2]; x, y = int(round(x)), int(round(y))
    xa, ya = max(0, x), max(0, y); xb, yb = min(base.shape[1], x + w), min(base.shape[0], y + h)
    if xa >= xb or ya >= yb:
        return base
    l = lay[ya - y:yb - y, xa - x:xb - x]; a = l[..., 3:4]
    if a.max() > 1.5:
        a = a / 255.0
    b = base[ya:yb, xa:xb]
    b[..., :3] = b[..., :3] * (1 - a) + l[..., :3] * a
    b[..., 3:4] = np.maximum(b[..., 3:4], a)
    return base


def p10(n):
    img = bg.papel()
    if n < 296:
        for txt, ap, fim in [("wasn't", 251, 260), ("just", 260, 266), ("Making", 266, 278), ("Films", 278, 296)]:
            if ap <= n < fim:
                palavra_entra(img, txt, ap, n, (540, 960), le.CORPO)
        return img
    desloc = mv.entre(760, 0, u(n, 296, 314), "saida", 2.2)
    lay = camada_torre(n, desloc)
    sobre(img, lay, 0, 0)
    if n >= 302:
        le.escrever(img, "designed a", esquerda=(225 + desloc, 472), corpo=40, contorno=0.6)
    corpo_c = cache("c_comm", lambda: le.corpo_para_largura("Communication System", 675, le.SERIFA, contorno=1.0))
    if n >= 320:
        txt = "Communication System" if n >= 335 else "Communication"
        le.escrever(img, txt, esquerda=(165 + desloc, 518), corpo=corpo_c, contorno=1.0)
    return cam(img, z=mv.entre(1.0, 1.03, u(n, 320, 359)))


# ------------------------------------------------------------ 11. soldados
def p11(n):
    v = u(n, 359, 407)
    img = foto("g03_ww2_soldados.png", n, 760, 1344, 0.714 * mv.entre(1.08, 1.075, v), dy=mv.entre(21, -21, v))
    return img * np.array((0.914, 0.869, 0.955), np.float32)  # media do plano: 91/81/84 no original


# --------------------------------------------------------------- 12. torpedo
def p12(n):
    img = bg.ceu()
    if n < 422:
        sobre(img, st.listras_luz(n // 3, forca=1.0 - u(n, 407, 422)), 0, 0)
    if n >= 426:
        sobre(img, st.arcos_brancos((540, -150), ((n - 426) / 24.0) % 1.0), 0, 0)
    t = cache("torpedo", lambda: st.escalar(st.carregar("torpedo.png"), altura=660))
    if n >= 431:
        t = cache("torpedo_v", lambda: st.recolorir(cache("torpedo", lambda: None), (178, 30, 36)))
    f = mo.subida((n - 410) / FPS, dur=0.45, tau=0.10)
    cy = 975 + (1 - f) * 1300
    rot, ddx, ddy = mo.queda((n - 434) / FPS, dur=0.50) if n >= 434 else (0, 0, 0)
    if rot:
        pad = 400; big = np.zeros((t.shape[0] + 2 * pad, t.shape[1] + 2 * pad, 4), np.float32)
        big[pad:pad + t.shape[0], pad:pad + t.shape[1]] = t
        M = cv2.getRotationMatrix2D((big.shape[1] / 2, big.shape[0] / 2), -rot, 1.0)
        t = cv2.warpAffine(big, M, (big.shape[1], big.shape[0]), flags=cv2.INTER_LINEAR)
    sobre(img, t, 502 + ddx - t.shape[1] / 2, cy + ddy - t.shape[0] / 2)
    if n >= 419:
        prog = min(1.0, 0.25 + (n - 419) / 3 * 0.75)
        lab = cache(f"etq_{prog:.2f}", lambda: st.etiqueta_rasgada(660, 82, progresso=prog))
        sobre(img, lab, 180 - 24, 683 - 24)
        if n >= 422:
            texto = "jamming torpedoes"
            ordem = np.random.default_rng(11).permutation(len(texto))
            k = min(len(texto), int((n - 422) / 9 * len(texto)) + 4)
            vis = "".join(c if (i in ordem[:k] or c == " ") else " " for i, c in enumerate(texto))
            corpo = cache("c_jam", lambda: le.corpo_para_largura(texto, 520, le.SERIFA, contorno=0.8))
            cheio, (ox, oy) = le.mascara(texto, le.SERIFA, corpo, None, 0.8)
            x0 = 510 - cheio.size[0] / 2
            letras(img, vis, len(vis), x0, 724, corpo, le.SERIFA, None, PRETO_TINTA)
    return cam(img, z=mv.entre(1.0, 0.964, u(n, 407, 449)), fundo=bg.CEU[0][1])


# --------------------------------------------------------- 13. amassa e lixeira
def lixeira_topo():
    a = st.carregar("lixeira_salao.png")
    hsv = cv2.cvtColor(a[..., :3].astype(np.uint8), cv2.COLOR_RGB2HSV)
    m = (hsv[..., 0] > 35) & (hsv[..., 0] < 85) & (hsv[..., 1] > 60)
    ys, xs = np.where(m)
    return float(np.median(xs)), float(ys.min()), float(xs.max() - xs.min())


# Medido (720 -> 1080): a lixeira afasta numa curva so de 452 a 503 —
# s = 1,2 (1 + 0,40 e^-(n-464)/10,5), largura 349 -> 249 px em 720 entre 464 e 500 — com a
# BOCA parada na tela (y 585) e o corpo 36 px a direita do centro. A folha nao vira bola
# na frente da camera: fica larga e o contorno fecha de cima e de baixo (meia-altura
# 710 / 610 / 454 / 414 px) e so no 464 ja esta dentro da lixeira.
P13_BOCA = (576.0, 585.0)
P13_ZOOM = (1.2, 0.40, 10.5)
P13_FOLHA = {452: (0.25, 0.97, (620, 665, 540, 991)), 455: (0.45, 0.93, (640, 644, 540, 1094)),
             458: (0.65, 0.88, (650, 445, 540, 985)), 461: (0.85, 0.84, (590, 402, 540, 957))}
P13_ZOOM_ANTES = {452: 1.95, 455: 1.65, 458: 1.48, 461: 1.42}   # lixeira atras da folha (fator sobre 1,2)


def p13(n):
    bx, by, bw = cache("lix_topo", lixeira_topo)
    if n >= 452:
        s0, amp, tau = P13_ZOOM
        s = s0 * (P13_ZOOM_ANTES[n] if n in P13_ZOOM_ANTES else 1 + amp * math.exp(-(n - 464) / tau))
        img = fi.corrigir(foto("lixeira_salao.png", n, bx, by, s, dx=P13_BOCA[0] - W / 2, dy=P13_BOCA[1] - H / 2,
                               grao=True), 0.78)
        img = img * np.array((0.866, 0.983, 0.911), np.float32)  # media da lixeira: 49/59/53 no original
        tx, ty = P13_BOCA                                          # boca da lixeira na tela
        bola = cache("bola", lambda: st.escalar(st.carregar("papel_amassado.png"), largura=420))
        if n >= 464:
            bb = st.escalar(bola, largura=bw * s * 0.62)
            sobre(img, bb, tx - bb.shape[1] / 2, ty - bb.shape[0] * 0.55)
    else:
        img = bg.chapado(bg.PAPEL)               # o mesmo papel cinza do video (p50 187 medido)
    if n < 464:
        folha = cache("folha_torre", lambda: folha_torre())
        if n >= 452:
            prog, esc, borda = P13_FOLHA[n]
            lay = mo.amassar(folha, prog, (borda[2], borda[3]), escala=esc, borda=borda, rugas=0.22)
        else:
            lay = folha
        sobre(img, lay, 0, 0)
    return img


def folha_torre():
    lay = np.zeros((H, W, 4), np.float32); lay[..., :3] = bg.PAPEL; lay[..., 3] = 1.0
    t = st.torre((540, 330), 2300, 640, 170, esp=3.2)
    a = st.asas((540, 470), 5, raios=(190, 300, 410, 520, 630), banda=60)
    sobre_lay(lay, a, 0, 0); sobre_lay(lay, t, 0, 0)
    return lay


# ---------------------------------------------------------------- 14. anos
def p14(n):
    img = bg.papel()
    v = mo.odometro(n)
    base = math.floor(v / 5) * 5; frac = (v - base) / 5.0
    passo = 66.0                     # "1985" sozinho mede 142 px de largura -> corpo 90
    for ano, dy, al in [(int(base), -frac * passo, 1 - frac), (int(base) + 5, (1 - frac) * passo, frac)]:
        if al > 0.04:
            le.escrever(img, str(ano), centro=(540, 958 + dy), corpo=90, alfa=al, contorno=1.0)
    return img


# ---------------------------------------------------------------- 15. lousa
def p15(n):
    img = bg.parede()
    lousa = cache("lousa", lambda: st.carregar("lousa_giz.png"))
    v = mv.suavizar_curva(u(n, 536, 566), "saida", 1.8)
    larg = mv.entre(1000, 1390, v)
    l = st.escalar(lousa, largura=larg)
    m = np.ones(l.shape[:2], np.float32)
    borda = 40
    for k in range(borda):
        f = (k + 1) / borda
        m[k, :] = np.minimum(m[k, :], f); m[-1 - k, :] = np.minimum(m[-1 - k, :], f)
        m[:, k] = np.minimum(m[:, k], f); m[:, -1 - k] = np.minimum(m[:, -1 - k], f)
    l = l.copy(); l[..., 3] = m * 255
    sobre(img, l, 540 - l.shape[1] / 2 + mv.entre(-40, 0, v), 900 - l.shape[0] / 2)
    return img


# ------------------------------------------------------- 18-19. stills coloridos
def p18(n):
    a = st.carregar("hedy_samson_delilah_1949.png")
    s = (1920 / a.shape[0]) * mv.entre(1.0, 1.049, u(n, 698, 728))
    return fi.corrigir(foto("hedy_samson_delilah_1949.png", n, 1180, 760, s), 0.70, 0.80)


def p19(n):
    v = u(n, 728, 758)
    s = (1920 / 892) * mv.entre(1.15, 1.0, v, "entrada", 3.0)
    img = fi.corrigir(foto("hedy_1944_cor.jpg", n, 334, 400, s * 1.12), 0.62, 0.55)
    if n >= 749:
        img = fi.desfocar(img, 14 * u(n, 746, 757))
    return img


# ---------------------------------------------------------------- 20. moldura
# Medido (720 -> 1080): a camera ABRE de 1,75x para 1x em ease-out exponencial (tau 10
# quadros) em torno de (548, 983), saindo do desfoque do corte. Em repouso o ouro da moldura
# ocupa 615 x 732 px centrado em (547,5, 867) e a legenda vem centrada embaixo: linha 1 com
# 484 px de tinta, miolo das minusculas em y 1291 e 1356. Cada palavra entra a 45% e firma
# no degrau seguinte: history 770, remembers 773, her 776, for 779, her 785, brain. 788.
MOLD_OURO = (615.0, 732.0)
MOLD_CENTRO = (547.5, 867.0)
P20_ZOOM = (0.75, 10.0)                  # excesso inicial de zoom, tau (quadros)
P20_ANCORA = (548.0, 983.0)
# desfoque que sai em foco puxado: largura 10-90% da borda do ouro no original, descontada
# a borda natural ampliada pelo zoom -> sigma em px de 1080 por degrau
P20_DESFOQUE = {758: 12.0, 761: 10.0, 764: 8.5, 767: 6.0, 770: 2.0, 773: 1.0}   # o foco firma entre 764 e 770


def _moldura_medida():
    """Moldura redimensionada para o ouro medir MOLD_OURO, com o canto que poe o centro do
    ouro em MOLD_CENTRO e o furo do retrato na mesma escala."""
    a = st.carregar("moldura.png")
    hsv = cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV)
    ouro = (hsv[..., 0] >= 12) & (hsv[..., 0] <= 32) & (hsv[..., 1] > 90) & (hsv[..., 2] > 90) & (a[..., 3] > 128)
    ys, xs = np.nonzero(ouro)
    x0, x1 = np.percentile(xs, [0.5, 99.5]); y0, y1 = np.percentile(ys, [0.5, 99.5])
    sx, sy = MOLD_OURO[0] / (x1 - x0), MOLD_OURO[1] / (y1 - y0)
    m = cv2.resize(a, (int(round(a.shape[1] * sx)), int(round(a.shape[0] * sy))), interpolation=cv2.INTER_AREA)
    furo = np.load(st._RAIZ / "prontos" / "moldura_furo.npy") * np.array([sx, sy, sx, sy])
    return m, MOLD_CENTRO[0] - (x0 + x1) / 2 * sx, MOLD_CENTRO[1] - (y0 + y1) / 2 * sy, furo


def p20(n):
    img = bg.papel()
    mold, x0, y0, (fx0, fy0, fx1, fy1) = cache("moldura_medida", _moldura_medida)
    fw, fh = int(fx1 - fx0) + 6, int(fy1 - fy0) + 6
    def _retrato():
        r = cv2.resize(st.carregar("hedy_1944_cor.jpg")[40:640, 60:620], (fw, fh), interpolation=cv2.INTER_AREA)
        r[..., :3] = fi.corrigir(r[..., :3], 0.62, 0.55)      # so RGB: o alfa fica intacto
        return r
    retr = cache("retrato_moldura", _retrato)
    sobre(img, retr, x0 + fx0 - 3, y0 + fy0 - 3)
    sobre(img, mold, x0, y0)
    corpo = cache("c_hist", lambda: le.corpo_para_largura("history remembers", 484.5, le.SERIFA, contorno=0.8))
    linha1 = [("history", 770), ("remembers", 773)]
    linha2 = [("her", 776), ("for", 779), ("her", 785), ("brain.", 788)]
    for linha, xc, yc in [(linha1, 541.5, 1290.8), (linha2, 536.3, 1348.7)]:
        texto = " ".join(w for w, _ in linha)
        cheio, (ox, oy) = le.mascara(texto, le.SERIFA, corpo, None, 0.8)
        xx = xc - cheio.size[0] / 2
        fnt = le._fonte(le.SERIFA, int(round(corpo * le.SS)))
        topo = yc - cheio.size[1] / 2 + oy; pos = 0
        for w, ap in linha:
            i = texto.index(w, pos); pos = i + len(w)
            if n >= ap:
                m, (mx, my) = le.mascara(w, le.SERIFA, corpo, None, 0.8)
                le.tingir(img, m, xx + ox + fnt.getlength(texto[:i]) / le.SS - mx, topo - my, le.TINTA, 0.45 if n < ap + 3 else 1.0)
    z = 1.0 + P20_ZOOM[0] * math.exp(-(n - 758) / P20_ZOOM[1])
    img = cam(img, z=z, dx=(1 - z) * (P20_ANCORA[0] - W / 2), dy=(1 - z) * (P20_ANCORA[1] - H / 2))
    return fi.desfocar(img, P20_DESFOQUE.get(n, 0.0))


# ---------------------------------------------------------------- 21. Editors
def p21(n):
    v = mv.suavizar_curva(u(n, 824, 845), "saida", 1.6)
    img = fi.corrigir(foto("g08_editor.png", n, 760, 1300, 0.714 * mv.entre(1.15, 1.045, v)), 1.30)
    corpo = cache("c_ed", lambda: le.corpo_para_largura("Editors", 250, le.SERIFA))
    cont = [(827, 1), (830, 3), (833, 5), (836, 7)]
    k = max([c for f, c in cont if f <= n], default=0)
    letras(img, "Editors", k, 415, 945, corpo, le.SERIFA, None, BRANCO)
    return img


# ------------------------------------------------------------ 22. icone e cursor
# Medido (720 -> 1080) com os assets REAIS: o icone .aep do After Effects (do proprio
# aplicativo instalado) e o cursor de mao do macOS (vetor do sistema, ponta do dedo no hotspot).
# A camera abre de 2,43x para 1x em torno do icone; cursor e icone fazem parte da cena (os
# dois escalam com a camera). O dedo sobe da esquerda-baixo ate o "AEP" e, do 893 em diante,
# arrasta o arquivo para a esquerda acelerando ate o corte.
P22_ZOOM = {845: 2.43, 848: 1.85, 851: 1.67, 854: 1.53, 857: 1.44, 860: 1.37, 863: 1.31, 866: 1.26,
            869: 1.21, 872: 1.17, 875: 1.14, 878: 1.11, 881: 1.08, 884: 1.05, 887: 1.02, 890: 1.0}
P22_ICONE = (546.0, 967.5, 120.0)        # centro na tela e largura da tinta com a camera a 1
P22_ARRASTO = {893: (-7.5, 3.0), 896: (-19.5, -1.5), 899: (-49.5, -13.5), 902: (-142.5, -45.0)}
P22_DEDO = {845: (290, 1416), 848: (349, 1438), 851: (408, 1460), 854: (512, 1308), 857: (546, 1197),
            860: (573, 1140), 863: (575, 1100), 866: (573, 1062), 869: (567, 1037), 872: (570, 1029),
            875: (566, 1017), 878: (563, 1006), 881: (561, 1001), 884: (559, 996), 887: (558, 991),
            890: (557, 988), 893: (550, 991), 896: (538, 979), 899: (508, 967), 902: (420, 934)}
P22_CURSOR = 57.0                        # largura da tinta do cursor com a camera a 1


# cor do icone no original: casamento linear por canal a partir de duas ancoras medidas
# (navy 4,4,90 -> 13,15,79 e lilas 139,148,235 -> 111,136,198)
P22_COR_ICONE = ((0.726, 10.1), (0.840, 11.6), (0.820, 5.1))


def _icone_real(nome, largura_tinta, cor=None):
    a = st.carregar(nome).copy()
    if cor:
        for c, (g, o) in enumerate(cor):
            a[..., c] = a[..., c] * g + o
    ys, xs = np.nonzero(a[..., 3] > 10)
    k = largura_tinta / float(xs.max() - xs.min() + 1)
    r = cv2.resize(a, (max(1, int(round(a.shape[1] * k))), max(1, int(round(a.shape[0] * k)))), interpolation=cv2.INTER_AREA)
    cx, cy = (xs.min() + xs.max()) / 2 * k, (ys.min() + ys.max()) / 2 * k
    return r, cx, cy


def _cursor_real(largura_tinta):
    """Cursor de mao do macOS com a sombra do sistema (45% preto, desfoque 2 pt, 1 pt abaixo)."""
    a = st.carregar("cursor_mao_macos.png")                       # 32 pt x 12; hotspot (13, 8) pt
    ys, xs = np.nonzero(a[..., 3] > 10)
    k = largura_tinta / float(xs.max() - xs.min() + 1)
    r = cv2.resize(a, (max(1, int(round(a.shape[1] * k))), max(1, int(round(a.shape[0] * k)))), interpolation=cv2.INTER_AREA)
    pt = 12 * k                                                    # px por ponto do cursor
    al = r[..., 3] / 255.0
    sombra = cv2.GaussianBlur(np.roll(al, max(1, int(round(pt))), axis=0), (0, 0), max(0.5, 2 * pt)) * 0.45
    out = np.zeros_like(r); a_tot = al + sombra * (1 - al)
    out[..., :3] = (r[..., :3] * al[..., None]) / np.maximum(a_tot, 1e-6)[..., None]
    out[..., 3] = a_tot * 255
    return out, 13 * pt, 8 * pt


def p22(n):
    z = _degrau(P22_ZOOM, n)
    cx0, cy0, larg = P22_ICONE
    img = bg.dobras_escuras(zoom=z, ancora=(cx0, cy0))
    dx, dy = P22_ARRASTO.get(n, (0.0, 0.0))
    ic, icx, icy = _icone_real("ae_aep_icone.png", larg * z, P22_COR_ICONE)
    sobre(img, ic, cx0 + dx - icx, cy0 + dy - icy)
    cur, hx, hy = _cursor_real(P22_CURSOR * z)
    px, py = P22_DEDO[n]
    sobre(img, cur, px - hx, py - hy)
    return img


# ----------------------------------------------------------------- 23. site
def p23(n):
    k = 0 if n < 912 else min(11, (n - 912) // 3 + 1)
    img = st.site_generico("seusite.com"[:k])
    img = fi.corrigir(fi.desfocar(img, 3.2), 0.58)
    v = mv.suavizar_curva(u(n, 905, 960), "saida", 4.0)
    return cam(img, z=mv.entre(1.2, 1.0, v), dx=mv.entre(180, 0, v), dy=mv.entre(140, 0, v), fundo=bg.SITE)


PLANOS = {1: p01, 2: p02, 3: p03, 4: p04, 5: p05, 6: p07, 7: p07, 8: p08, 9: p09, 10: p10, 11: p11,
          12: p12, 13: p13, 14: p14, 15: p15, 18: p18, 19: p19, 20: p20, 21: p21, 22: p22, 23: p23}


def estado(n):
    k = plano(n)
    if k in (16, 17):
        return teste.estado(n)
    return PLANOS[k](n), 0.0, None


def borrao(n):
    return teste.borrao(n) if plano(n) == 17 else 0.0
