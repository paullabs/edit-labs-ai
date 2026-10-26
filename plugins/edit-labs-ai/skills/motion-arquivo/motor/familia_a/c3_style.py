"""
Camada 3 — style.

Mundo: documentario de arquivo. Regra de cor: num quadro sem cor, so o elemento que
importa ganha cor — aqui, a tecnologia moderna (azul de interface).

Caixa de interface, medida pixel a pixel na borda:
  preenchimento azul (21,126,190) · filete claro nos quatro lados (~3 px) ·
  sombra solida azul-escura deslocada ~12 px para baixo e para a direita ·
  rotulo em grotesca bold branca centrado.
Radar: aneis finos que nascem no centro, se afastam 82 px a cada 0,8 s e apagam com o
raio (luz 61 -> 20 sobre fundo 7, medida em 720).
"""
import numpy as np
import cv2
from PIL import Image
from . import W, H
from .c2_letras import rotulo

AZUL_UI = (21.0, 126.0, 190.0)
FILETE = (228.0, 242.0, 250.0)
SOMBRA = (16.0, 74.0, 146.0)
CAIXA = (426, 110)          # externo, com o filete (284x73 em 720)
FILETE_PX = 3
SOMBRA_DESLOC = (12, 12)

RADAR_PASSO = 82.5          # distancia entre aneis (55 px em 720)
RADAR_PERIODO = 0.8         # s para um anel ocupar o lugar do seguinte
RADAR_RMAX = 480.0          # raio em que o anel some (320 em 720)
RADAR_PLANO = 189.0         # ate aqui o anel tem luz cheia (130 em 720), depois apaga
RADAR_LUZ = 92.0            # brilho do traco, antes do borrao de 720
RADAR_TRACO = 2.4


def caixa_ui(texto):
    """RGBA float da caixa com sombra; devolve (camada, (dx, dy) do canto da caixa)."""
    w, h = CAIXA; sx, sy = SOMBRA_DESLOC
    lay = np.zeros((h + sy, w + sx, 4), np.float32)
    lay[sy:, sx:, :3] = SOMBRA; lay[sy:, sx:, 3] = 1.0
    lay[:h, :w, :3] = FILETE; lay[:h, :w, 3] = 1.0
    f = FILETE_PX
    lay[f:h - f, f:w - f, :3] = AZUL_UI
    m, cor = rotulo(texto)
    a = np.asarray(m, np.float32) / 255.0
    mh, mw = a.shape
    x0 = (w - mw) // 2; y0 = (h - mh) // 2
    reg = lay[y0:y0 + mh, x0:x0 + mw, :3]
    reg[:] = reg * (1 - a[..., None]) + np.array(cor, np.float32) * a[..., None]
    return lay


def radar(fase, centro=(W / 2, H / 2)):
    """Camada RGBA dos aneis. `fase` em [0,1): quanto o anel mais interno ja andou."""
    lay = np.zeros((H, W, 4), np.float32)
    yy, xx = np.ogrid[:H, :W]
    r = np.sqrt((xx - centro[0]) ** 2 + (yy - centro[1]) ** 2).astype(np.float32)
    alfa = np.zeros((H, W), np.float32)
    k = 0
    while True:
        raio = (k + fase) * RADAR_PASSO
        if raio > RADAR_RMAX:
            break
        if raio > 2:
            luz = 1.0 if raio <= RADAR_PLANO else max(0.0, 1 - (raio - RADAR_PLANO) / (RADAR_RMAX - RADAR_PLANO))
            d = np.abs(r - raio)
            alfa = np.maximum(alfa, np.clip(1 - (d - RADAR_TRACO / 2), 0, 1) * luz)
        k += 1
    lay[..., :3] = RADAR_LUZ / 0.9
    lay[..., 3] = alfa * 0.9
    return lay


# --- colagem do Hedy completo --------------------------------------------------------
from pathlib import Path as _P
_RAIZ = _P(__file__).resolve().parent.parent / "assets"


def usar_assets(pasta):
    """Aponta o carregador para a pasta assets/ do PROJETO (reais/, prontos/, baixados/,
    gerados/). Cada projeto tem a sua; o motor nao guarda asset de projeto."""
    global _RAIZ
    _RAIZ = _P(pasta).resolve()
    _cache_img.clear()
_cache_img = {}


_KIT = _P(__file__).resolve().parent.parent / "kit"      # pecas que viajam com a skill


def localizar(nome):
    """Caminho do asset: primeiro no projeto (prontos/, reais/, baixados/, gerados/), depois
    no kit da skill (moldura, papel amassado...)."""
    for pasta in [_RAIZ / s for s in ("prontos", "reais", "baixados", "gerados")] + [_KIT]:
        if (pasta / nome).exists():
            return pasta / nome
    raise FileNotFoundError(f"{nome} (procurado em {_RAIZ} e no kit)")


def carregar(nome):
    """Asset como float RGBA (alfa 0-255)."""
    if nome not in _cache_img:
        _cache_img[nome] = np.asarray(Image.open(localizar(nome)).convert("RGBA")).astype(np.float32)
    return _cache_img[nome]


def escalar(a, largura=None, altura=None):
    h, w = a.shape[:2]
    s = (largura / w) if largura else (altura / h)
    return cv2.resize(a, (max(1, int(round(w * s))), max(1, int(round(h * s)))),
                      interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)


def foto_no_quadro(a, cx, cy, s, dx=0.0, dy=0.0, fundo=(0, 0, 0)):
    """Foto preenchendo o quadro: o ponto (cx,cy) da foto vai para o centro + (dx,dy),
    com escala s. Reamostra da fonte (nao de um quadro ja reduzido)."""
    M = np.float32([[s, 0, W / 2 + dx - s * cx], [0, s, H / 2 + dy - s * cy]])
    rgb = a[..., :3] if a.shape[2] == 4 else a
    return cv2.warpAffine(rgb, M, (W, H), flags=cv2.INTER_CUBIC if s > 1 else cv2.INTER_AREA,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=tuple(float(v) for v in fundo))


def pb(a):
    """Preto e branco (mantem o alfa)."""
    out = a.copy(); l = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    out[..., 0] = out[..., 1] = out[..., 2] = l
    return out


def recolorir(a, cor):
    """Pinta um recorte com uma cor, preservando a luz (o torpedo que fica vermelho)."""
    out = a.copy(); l = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0
    l = np.clip(l * 1.8, 0, 1.4)
    for k in range(3):
        out[..., k] = np.clip(cor[k] * l, 0, 255)
    return out


def cartao_foto(a, largura, borda=20, rot=-2.0, sombra=True):
    """Copia fotografica: foto P&B com borda branca, levemente torta, com sombra."""
    f = escalar(a, largura=largura)
    h, w = f.shape[:2]
    c = np.zeros((h + 2 * borda, w + 2 * borda, 4), np.float32)
    c[..., :3] = (236, 234, 228); c[..., 3] = 255
    c[borda:borda + h, borda:borda + w, :3] = f[..., :3]
    pad = 60
    out = np.zeros((c.shape[0] + 2 * pad, c.shape[1] + 2 * pad, 4), np.float32)
    if sombra:
        s = np.zeros(out.shape[:2], np.float32)
        s[pad + 10:pad + 10 + c.shape[0], pad + 6:pad + 6 + c.shape[1]] = 0.45
        s = cv2.GaussianBlur(s, (0, 0), 12)
        out[..., 3] = s * 255
    reg = out[pad:pad + c.shape[0], pad:pad + c.shape[1]]
    reg[..., :3] = c[..., :3]; reg[..., 3] = 255
    M = cv2.getRotationMatrix2D((out.shape[1] / 2, out.shape[0] / 2), rot, 1.0)
    return cv2.warpAffine(out, M, (out.shape[1], out.shape[0]), flags=cv2.INTER_CUBIC)


def seta_mao(p0, p1, curva=0.35, esp=3.2, cor=(30, 24, 28), semente=2, ponta=26):
    """Seta desenhada a mao: curva de Bezier com tremor leve e ponta aberta."""
    lay = np.zeros((H, W, 4), np.float32)
    rng = np.random.default_rng(semente)
    p0, p1 = np.array(p0, np.float32), np.array(p1, np.float32)
    meio = (p0 + p1) / 2; n = np.array([-(p1 - p0)[1], (p1 - p0)[0]], np.float32)
    ctrl = meio + n * curva
    t = np.linspace(0, 1, 80)[:, None]
    pts = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * p1
    pts += rng.normal(0, 0.6, pts.shape)
    m = np.zeros((H, W), np.uint8)
    cv2.polylines(m, [np.int32(pts * 4)], False, 255, int(esp * 4), cv2.LINE_AA, shift=2)
    d = pts[-1] - pts[-8]; d /= np.linalg.norm(d) + 1e-6
    for ang in (2.55, -2.55):
        r = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
        q = pts[-1] + (r @ d) * ponta
        cv2.line(m, tuple(np.int32(pts[-1] * 4)), tuple(np.int32(q * 4)), 255, int(esp * 4), cv2.LINE_AA, shift=2)
    lay[..., :3] = cor; lay[..., 3] = m.astype(np.float32) / 255
    return lay


def torre(topo, base_y, larg_base, larg_topo, esp=2.6):
    """Torre de radio em trelica, desenho a traco preto, com isoladores no topo."""
    lay = np.zeros((H, W, 4), np.float32); m = np.zeros((H, W), np.uint8)
    cx, ty = topo
    def lado(y, sinal):
        f = (y - ty) / (base_y - ty)
        return cx + sinal * (larg_topo / 2 + f * (larg_base - larg_topo) / 2)
    seg = 11
    ys = [ty + (base_y - ty) * (k / seg) ** 0.92 for k in range(seg + 1)]
    L = lambda a, b: cv2.line(m, (int(a[0] * 4), int(a[1] * 4)), (int(b[0] * 4), int(b[1] * 4)), 255, int(esp * 4), cv2.LINE_AA, shift=2)
    for s in (-1, 1):
        L((lado(ty, s), ty), (lado(base_y, s), base_y))
    for a, b in zip(ys[:-1], ys[1:]):
        L((lado(a, -1), a), (lado(a, 1), a))
        L((lado(a, -1), a), (lado(b, 1), b)); L((lado(a, 1), a), (lado(b, -1), b))
    L((lado(base_y, -1), base_y), (lado(base_y, 1), base_y))
    L((cx, ty - 70), (cx, ty))
    for (dx, dy, r) in [(-14, -34, 17), (22, -4, 17), (-26, 50, 18), (18, 56, 18)]:
        cv2.circle(m, (int((cx + dx) * 4), int((ty + dy) * 4)), r * 4, 255, -1, cv2.LINE_AA, shift=2)
    lay[..., :3] = (20, 18, 20); lay[..., 3] = m.astype(np.float32) / 255
    return lay


def asas(centro, n_visiveis, raios=(95, 155, 215, 275, 335), banda=34, abertura=34.0,
         cor=(214, 62, 74), cor2=(236, 128, 140)):
    """Ondas vermelhas dos dois lados do topo da torre; crescem de dentro para fora."""
    lay = np.zeros((H, W, 4), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dx, dy = xx - centro[0], yy - centro[1]
    r = np.sqrt(dx ** 2 + dy ** 2); ang = np.degrees(np.arctan2(dy, dx))
    setor = (np.abs(ang) < abertura) | (np.abs(np.abs(ang) - 180) < abertura)
    for k, raio in enumerate(raios):
        vis = np.clip(n_visiveis - k, 0, 1)
        if vis <= 0:
            break
        dentro = np.clip((banda / 2 - np.abs(r - raio)) / 2.5, 0, 1) * setor
        c = np.array(cor if k % 2 == 0 else cor2, np.float32)
        a = dentro * 0.72 * vis
        lay[..., :3] = lay[..., :3] * (1 - a[..., None]) + c * a[..., None]
        lay[..., 3] = np.maximum(lay[..., 3], a)
    return lay


def etiqueta_rasgada(largura, altura, semente=7, progresso=1.0):
    """Tira de papel branco com bordas rasgadas; `progresso` desenrola da esquerda."""
    rng = np.random.default_rng(semente)
    pad = 24; h, w = altura + 2 * pad, largura + 2 * pad
    m = np.zeros((h, w), np.uint8)
    xs = np.linspace(pad, pad + largura * progresso, 60)
    topo = pad + rng.normal(0, 3.5, xs.shape).cumsum() * 0.25 + rng.normal(0, 2.2, xs.shape)
    base = pad + altura + rng.normal(0, 3.5, xs.shape).cumsum() * 0.25 + rng.normal(0, 2.2, xs.shape)
    poly = np.concatenate([np.stack([xs, topo], 1), np.stack([xs[::-1], base[::-1]], 1)])
    cv2.fillPoly(m, [np.int32(poly)], 255, cv2.LINE_AA)
    lay = np.zeros((h, w, 4), np.float32)
    somb = cv2.GaussianBlur(np.roll(m, (5, 3), (0, 1)).astype(np.float32) / 255, (0, 0), 5) * 0.35
    lay[..., 3] = somb
    a = m.astype(np.float32) / 255
    fibra = cv2.GaussianBlur(rng.normal(0, 1, (h, w)).astype(np.float32), (0, 0), 1.0) * 4
    papel = np.stack([238 + fibra, 236 + fibra, 230 + fibra], -1)
    lay[..., :3] = papel * a[..., None]
    lay[..., 3] = np.maximum(lay[..., 3], a)
    lay[..., :3] = np.where(a[..., None] > 0, papel, 0)
    return lay


def arcos_brancos(centro, fase, passo=135.0, n=8, r0=160.0, esp=3.0, luz=225.0):
    """Arcos de radar brancos e finos (plano do torpedo), pulsando para fora."""
    lay = np.zeros((H, W, 4), np.float32)
    yy, xx = np.ogrid[:H, :W]
    r = np.sqrt((xx - centro[0]) ** 2 + (yy - centro[1]) ** 2).astype(np.float32)
    a = np.zeros((H, W), np.float32)
    for k in range(n):
        raio = r0 + (k + fase) * passo
        a = np.maximum(a, np.clip(1 - (np.abs(r - raio) - esp / 2), 0, 1) * max(0.0, 1 - k / n) * 0.9)
    lay[..., :3] = luz; lay[..., 3] = a
    return lay


def listras_luz(semente, forca=1.0):
    """Riscos verticais finos de luz (rosa/branco) sobre o ceu — vazamento de pelicula."""
    rng = np.random.default_rng(semente)
    lay = np.zeros((H, W, 4), np.float32)
    for _ in range(6):
        x = rng.uniform(40, W - 40); w = rng.uniform(1.5, 5); c = rng.choice([0, 1])
        cor = (250, 170, 190) if c else (245, 240, 250)
        xx = np.arange(W, dtype=np.float32)
        a = np.clip(1 - np.abs(xx - x) / w, 0, 1) * rng.uniform(0.15, 0.45) * forca
        lay[..., :3] = np.where(a[None, :, None] > lay[..., 3:4], np.array(cor, np.float32), lay[..., :3])
        lay[..., 3] = np.maximum(lay[..., 3], a[None, :])
    return lay


def selecao_azul(x0, y0, x1, y1, esp=3.0, r=11.0):
    """Caixa de selecao de texto de software: preenchimento azul claro, borda e alcas."""
    lay = np.zeros((H, W, 4), np.float32)
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    lay[y0:y1, x0:x1, :3] = (150, 196, 232); lay[y0:y1, x0:x1, 3] = 0.55
    m = np.zeros((H, W), np.uint8)
    cv2.rectangle(m, (x0, y0), (x1, y1), 255, int(esp))
    cv2.line(m, (x0, y0 - 18), (x0, y1), 255, int(esp)); cv2.line(m, (x1, y0), (x1, y1 + 18), 255, int(esp))
    cv2.circle(m, (x0, y0 - 18 - int(r)), int(r), 255, -1, cv2.LINE_AA)
    cv2.circle(m, (x1, y1 + 18 + int(r)), int(r), 255, -1, cv2.LINE_AA)
    a = m.astype(np.float32) / 255
    lay[..., :3] = lay[..., :3] * (1 - a[..., None]) + np.array((40, 125, 176), np.float32) * a[..., None]
    lay[..., 3] = np.maximum(lay[..., 3], a)
    return lay


def icone_projeto(lado=230):
    """Icone generico de arquivo de projeto (no lugar do icone de marca do original)."""
    lay = np.zeros((lado, lado, 4), np.float32); m = np.zeros((lado, lado), np.uint8)
    cv2.rectangle(m, (8, 8), (lado - 8, lado - 8), 255, -1)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)); m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
    a = m.astype(np.float32) / 255
    lay[..., :3] = (26, 27, 75); lay[..., 3] = a
    borda = cv2.morphologyEx(m, cv2.MORPH_GRADIENT, np.ones((7, 7), np.uint8)).astype(np.float32) / 255
    lay[..., :3] = lay[..., :3] * (1 - borda[..., None]) + np.array((150, 150, 245), np.float32) * borda[..., None]
    from .c2_letras import mascara, INTER
    t, _ = mascara("PRJ", INTER, lado * 0.30, peso=700)
    ta = np.asarray(t, np.float32) / 255; th, tw = ta.shape
    oy, ox = int(lado * 0.30), (lado - tw) // 2
    lay[oy:oy + th, ox:ox + tw, :3] = lay[oy:oy + th, ox:ox + tw, :3] * (1 - ta[..., None]) + np.array((160, 160, 255), np.float32) * ta[..., None]
    return lay


def cursor_mao(alt=110):
    """Cursor de mao (dedo apontando), branco com contorno preto."""
    s = alt / 110.0
    pts = np.array([[38, 0], [52, 0], [55, 8], [55, 46], [64, 42], [74, 46], [76, 52], [86, 50], [96, 56], [97, 62],
                    [104, 62], [112, 70], [112, 94], [100, 110], [52, 110], [22, 72], [16, 56], [26, 52], [36, 62], [36, 8]],
                   np.float32) * s
    w, h = int(120 * s), int(116 * s)
    lay = np.zeros((h, w, 4), np.float32)
    mf = np.zeros((h, w), np.uint8); cv2.fillPoly(mf, [np.int32(pts)], 255, cv2.LINE_AA)
    mb = np.zeros((h, w), np.uint8); cv2.polylines(mb, [np.int32(pts)], True, 255, max(2, int(4 * s)), cv2.LINE_AA)
    a = mf.astype(np.float32) / 255; b = mb.astype(np.float32) / 255
    lay[..., :3] = 250; lay[..., :3] = lay[..., :3] * (1 - b[..., None]) + 10 * b[..., None]
    lay[..., 3] = np.maximum(a, b)
    return lay


def site_generico(digitado):
    """Pagina de loja escura e generica, com uma busca sendo digitada (fecho)."""
    from .c2_letras import escrever, INTER
    img = np.empty((H, W, 3), np.float32); img[:] = (26, 26, 25)
    escrever(img, "Arquivos de projeto", esquerda=(70, 150), fonte=INTER, corpo=64, cor=(238, 238, 236), peso=800)
    escrever(img, "para editores de video", esquerda=(70, 232), fonte=INTER, corpo=64, cor=(238, 238, 236), peso=800)
    for k, w in enumerate([880, 820, 860, 700]):
        img[318 + k * 34:330 + k * 34, 70:70 + w] = (88, 88, 86)
    for x0, x1, cor in [(70, 340, (46, 150, 90)), (370, 640, (196, 106, 44))]:
        m = np.zeros((H, W), np.uint8); cv2.rectangle(m, (x0, 480), (x1, 548), 255, -1)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (61, 61)))
        img[m > 0] = cor
    painel = np.zeros((H, W), np.uint8); cv2.rectangle(painel, (90, 640), (760, 1820), 255, -1)
    painel = cv2.morphologyEx(painel, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (91, 91)))
    img[painel > 0] = (214, 216, 214)
    m = np.zeros((H, W), np.uint8); cv2.rectangle(m, (200, 760), (980, 840), 255, 4)
    img[m > 0] = (40, 40, 42)
    escrever(img, digitado + "|", esquerda=(232, 800), fonte=INTER, corpo=42, cor=(30, 30, 32), peso=500)
    for k, (x, y, c) in enumerate([(180, 1000, (66, 133, 244)), (330, 1130, (52, 168, 83)), (230, 1300, (234, 67, 53))]):
        cv2.circle(img, (x, y), 52, c, -1, cv2.LINE_AA)
    for k in range(4):
        img[930 + k * 70:950 + k * 70, 820:1020] = (70, 70, 68)
    cv2.circle(img, (900, 1500), 48, (46, 160, 90), -1, cv2.LINE_AA)
    return img
