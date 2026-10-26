"""Motor das colagens de papel: camadas com chaves, desenho em degraus de 2 quadros (14 desenhos por segundo), boil por
camada com semente própria, sombra por material, traço que se desenha, câmera sobre o mundo, grão e RGB mínimos no fim.

Convenções (as de um editor de vídeo comum, para traduzir uma cena para outro editor sem conversão):
- tela 1080×1920, quadros de 24 qps; x, y em px da tela com origem no canto de cima à esquerda;
- cada camada tem uma âncora (px dentro da própria imagem); x, y dizem onde a âncora cai no MUNDO;
- rotação em graus, positiva no sentido horário; escala 1 = pixel nativo da imagem;
- chaves: [(quadro, valor, curva)] — a curva vale do quadro dela até a próxima chave."""
import math
import subprocess
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import recursos as R

W, H, FPS = 1080, 1920, 24          # FPS = relógio de AUTORIA (as chaves das cenas estão em quadros de 24)
FPS_SAIDA, DESENHOS = 28, 14         # o vídeo sai a 28 qps com 14 desenhos por segundo (cada desenho dura 2 quadros);
                                     # 14 qps: mais fluido que 12 e ainda com cara de desenho
FONTES = R.FONTES
KIT = R.KIT

# boil por classe: amplitude em px DA TELA (não cresce com o zoom da câmera) e célula do ruído em px da imagem.
# Regra: amplitude medida na TELA (~1 px), nunca na imagem (com zoom 1,3 ela inflava até 6–7 px e ficava agressiva), e
# um CICLO de 3 deformações fixas por camada, como o boil feito à mão.
# Regra: cada deformação segura BOIL_SEGURA desenhos (3,5 trocas por segundo). Trocar a cada desenho (14/s) parece
# tremor de FPS alto.
BOIL = {"obj": (0.7, 170), "paper": (0.7, 150), "type": (0.3, 190), "ink": (0.9, 110), "print": (0.45, 50)}
BOIL_CICLO = 3
BOIL_SEGURA = 4

# sombras por material (medidas): deslocamento y, desfoque, opacidade
SOMBRA = {"papel": (6, 14, 0.15), "recorte": (12, 22, 0.30), "cartao": (11, 24, 0.17), "nenhuma": None}


# ------------------------------------------------------------------ curvas
def curva(nome, t):
    t = min(max(t, 0.0), 1.0)
    if nome == "lin":
        return t
    if nome == "out":                       # sai rápido, assenta devagar (entrada de objeto)
        return 1 - (1 - t) ** 3
    if nome == "in":                        # começa devagar, sai rápido (saída de objeto)
        return t ** 3
    if nome == "io":
        return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
    if nome == "back":                      # passa um pouco e volta (pop de encaixe)
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
    if nome == "segura":
        return 0.0
    raise KeyError(nome)


def valor(chaves, f, padrao):
    """valor da propriedade no quadro f; antes da 1ª chave segura a 1ª, depois da última segura a última"""
    if not chaves:
        return padrao
    if f <= chaves[0][0]:
        return chaves[0][1]
    for (f0, v0, c0), (f1, v1, _) in zip(chaves, chaves[1:]):
        if f0 <= f < f1:
            k = curva(c0, (f - f0) / (f1 - f0))
            return v0 + (v1 - v0) * k
    return chaves[-1][1]


def q(t):
    """primeiro quadro PAR em/depois de t segundos (os eventos do desenho caem em degrau, um relógio só)"""
    f = int(math.ceil(t * FPS - 0.25))
    return f + (f % 2)


# ------------------------------------------------------------------ imagem
def rgba(img):
    """RGBA float 0-1 com a cor PRÉ-MULTIPLICADA pelo alfa (interpolar e misturar sem halo claro)"""
    a = np.asarray(img.convert("RGBA"), dtype=np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


def fonte(nome, corpo):
    return R.fonte(nome, corpo)


def texto_img(txt, nome="ArchivoBlack-Regular.ttf", corpo=120, cor=(32, 35, 33), tracking=0, margem=24):
    """texto em RGBA com margem (para boil e sombra não cortarem); tracking em px entre letras"""
    f = fonte(nome, corpo)
    larg = sum(f.getlength(c) for c in txt) + tracking * (len(txt) - 1)
    asc, desc = f.getmetrics()
    im = Image.new("RGBA", (int(larg + 2 * margem), int(asc + desc + 2 * margem)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = margem
    for c in txt:
        d.text((x, margem), c, font=f, fill=cor + (255,))
        x += f.getlength(c) + tracking
    return im


def borda_papel(img, px=10, cor=(244, 240, 232)):
    """contorno de papel em volta do recorte (o branco da tesoura da colagem)"""
    a = np.asarray(img.getchannel("A"))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    pad = px + 2
    a2 = np.pad(a, pad)
    dil = cv2.dilate(a2, k)
    base = Image.new("RGBA", (a2.shape[1], a2.shape[0]), cor + (0,))
    base.putalpha(Image.fromarray(dil))
    base.alpha_composite(img, (pad, pad))
    return base


def cartao_foto(img, larg, alt, foco=(0.5, 0.42), bw=24, bb=66, sepia=False, papel=(241, 236, 224)):
    """foto impressa com margem (fotos-reais.md): recorta na proporção, dessatura leve ou duotone de época"""
    im = img.convert("RGB")
    r = larg / alt
    w0, h0 = im.size
    if w0 / h0 > r:
        nw = int(h0 * r)
        x0 = int(min(max(foco[0] * w0 - nw / 2, 0), w0 - nw))
        im = im.crop((x0, 0, x0 + nw, h0))
    else:
        nh = int(w0 / r)
        y0 = int(min(max(foco[1] * h0 - nh / 2, 0), h0 - nh))
        im = im.crop((0, y0, w0, y0 + nh))
    im = im.resize((larg, alt), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    if sepia:
        escuro, claro = np.array([0.16, 0.13, 0.11]), np.array([0.93, 0.89, 0.80])
        a = escuro + lum[..., None] * (claro - escuro)
    else:
        a = lum[..., None] + 0.86 * (a - lum[..., None])
    a = np.clip((a - 0.5) * 1.03 + 0.5, 0, 1)
    foto = Image.fromarray((a * 255).astype(np.uint8))
    out = Image.new("RGBA", (larg + 2 * bw, alt + bw + bb), papel + (255,))
    out.paste(foto, (bw, bw))
    return out


# ------------------------------------------------------------------ boil
@lru_cache(maxsize=4096)
def _campo(h, w, celula, semente):
    rng = np.random.default_rng(semente)
    gh, gw = max(2, int(h / celula) + 2), max(2, int(w / celula) + 2)
    dx = cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    dy = cv2.resize(rng.standard_normal((gh, gw)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    return dx, dy


def boil(arr, classe, semente, passo, escala=1.0):
    """passo: degrau de 12 qps; escala: quanto 1 px da imagem vale na tela (câmera × escala da camada)"""
    amp, cel = BOIL[classe]
    amp = float(amp / max(float(escala), 0.05))        # float puro: com np.float64 o remap recebia mapas float64
    h, w = arr.shape[:2]
    dx, dy = _campo(h, w, cel, (semente * 7919 + ((passo // BOIL_SEGURA) % BOIL_CICLO) * 104729) % (2 ** 31))
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    return cv2.remap(arr, gx + dx * amp, gy + dy * amp, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                     borderValue=0)


# ------------------------------------------------------------------ camadas
class Camada:
    """uma coisa na tela. fonte: PIL RGBA fixo, ou função(quadro_degrau, props) -> PIL RGBA (traço que se desenha)"""

    def __init__(self, nome, fonte, ini, fim, ancora=None, chaves=None, boil=None, sombra="nenhuma", degrau=True,
                 mundo=True, semente=None, trilha=None, cena=None, nota="", prof=1.0):
        self.nome, self.fonte, self.ini, self.fim = nome, fonte, ini, fim
        self.prof = prof                         # paralaxe: >1 = plano mais perto da câmera (anda e cresce mais)
        self.chaves = chaves or {}
        self.boil, self.sombra, self.degrau, self.mundo = boil, sombra, degrau, mundo
        self.semente = semente if semente is not None else (abs(hash(nome)) % 100000)
        self.trilha, self.cena, self.nota = trilha, cena, nota
        img = fonte if isinstance(fonte, Image.Image) else None
        self.tam = img.size if img is not None else None
        self.ancora = ancora if ancora is not None else ((img.size[0] / 2, img.size[1] / 2) if img else (0, 0))
        self._arr = rgba(img) if img is not None else None
        self.texto_px = img.info.get("texto_px") if img is not None else None     # corpo do texto na imagem (px)
        self.texto_min = img.info.get("texto_min", 46) if img is not None else 46  # mínimo na tela (px)

    def props(self, f):
        return {"x": valor(self.chaves.get("x"), f, W / 2), "y": valor(self.chaves.get("y"), f, H / 2),
                "s": valor(self.chaves.get("s"), f, 1.0) * valor(self.chaves.get("sm"), f, 1.0),   # sm: pulso (vida)
                "rot": valor(self.chaves.get("rot"), f, 0.0),
                "op": valor(self.chaves.get("op"), f, 1.0), "trim": valor(self.chaves.get("trim"), f, 1.0),
                "sx": valor(self.chaves.get("sx"), f, 1.0),
                # laboratório de camadas: perspectiva de porta (kx > 0 aumenta a borda direita, < 0 a esquerda) e a sombra
                # animada de quem levanta do papel (multiplicam o deslocamento, o desfoque e a força da sombra)
                "kx": valor(self.chaves.get("kx"), f, 0.0), "ang": valor(self.chaves.get("ang"), f, 0.0),
                "sdy": valor(self.chaves.get("sdy"), f, 1.0), "sbl": valor(self.chaves.get("sbl"), f, 1.0),
                "sop": valor(self.chaves.get("sop"), f, 1.0)}

    def arr(self, fd, p):
        if self._arr is not None:
            return self._arr
        return rgba(self.fonte(fd, p))


class Camera:
    """câmera sobre o mundo: zoom em volta de (cx, cy) do mundo, que cai no centro da tela"""

    def __init__(self, chaves=None, degrau=False):
        self.chaves = chaves or {}
        self.degrau = degrau

    def matriz(self, f):
        z = valor(self.chaves.get("z"), f, 1.0)
        cx = valor(self.chaves.get("cx"), f, W / 2)
        cy = valor(self.chaves.get("cy"), f, H / 2)
        r = valor(self.chaves.get("rot"), f, 0.0)
        return afim(z, r, (cx, cy), (W / 2, H / 2))


def afim(s, rot_graus, de, para, sx=1.0):
    """leva o ponto 'de' para 'para', escalando s (sx a mais na horizontal) e girando rot (horário) em volta dele"""
    a = math.radians(rot_graus)
    c, si = math.cos(a), math.sin(a)
    A = np.array([[c * s * sx, -si * s], [si * s * sx, c * s]])
    t = np.array(para) - A @ np.array(de)
    return np.vstack([np.hstack([A, t[:, None]]), [0, 0, 1]])


def na_tela(C, ponto):
    """onde um ponto do mundo cai na tela com a matriz de câmera C"""
    v = C @ np.array([ponto[0], ponto[1], 1.0])
    return (float(v[0]), float(v[1]))


def escala_de(M):
    return math.sqrt(abs(np.linalg.det(M[:2, :2])))


def perto(C, prof):
    """a câmera vista de um plano mais perto (prof>1) ou mais longe (<1): escala a matriz em volta do centro da tela"""
    return C if prof == 1.0 else afim(prof, 0, (W / 2, H / 2), (W / 2, H / 2)) @ C


def _desce(a, d):
    """desloca a máscara d px para baixo (d < 0: para cima) SEM dar a volta: com np.roll, a sombra de uma peça que
    passa da borda de baixo da tela reaparecia como uma faixa cinza no alto do quadro"""
    if d == 0:
        return a
    out = np.zeros_like(a)
    if d > 0:
        out[d:] = a[:-d]
    else:
        out[:d] = a[-d:]
    return out


def compor(base, cam, f, camadas, so=None, C=None, passo=None):
    """base: float32 HxWx3 (sRGB 0-1). Desenha as camadas ativas no quadro f, na ordem da lista (de baixo para cima).
    so="mundo" ou "tela" filtra as camadas; C força a matriz da câmera (as transições compõem o mundo duas vezes)"""
    if C is None:
        C = cam.matriz(f if not cam.degrau else f - f % 2)
    for L in camadas:
        if not (L.ini <= f < L.fim):
            continue
        fundo = getattr(L, "fundo", False)          # camada de tela desenhada POR BAIXO dos objetos (papel escuro)
        if (so == "mundo" and not (L.mundo or fundo)) or (so == "tela" and (L.mundo or fundo)):
            continue
        Cl = perto(C, L.prof) if L.mundo else None
        fd = f if passo is not None else (f - f % 2 if L.degrau else f)     # com passo, f já vem no degrau
        p = L.props(fd)
        if p["op"] <= 0.001 or p["s"] <= 0.001:
            continue
        if L.tam is not None:                       # fora da tela (com folga para sombra e perspectiva): nem desenha
            w_, h_ = L.tam
            M0 = afim(p["s"], p["rot"], L.ancora, (p["x"], p["y"]), p["sx"])
            if L.mundo:
                M0 = Cl @ M0
            cs = M0 @ np.array([[0, w_, 0, w_], [0, 0, h_, h_], [1, 1, 1, 1]], dtype=np.float64)
            if cs[0].max() < -300 or cs[0].min() > W + 300 or cs[1].max() < -300 or cs[1].min() > H + 300:
                continue
        a = L.arr(fd, p)
        if L.boil:
            pad = 8
            a = np.pad(a, ((pad, pad), (pad, pad), (0, 0)))
            esc = p["s"] * (escala_de(Cl) if L.mundo else 1.0)
            a = boil(a, L.boil, L.semente, int(passo if passo is not None else fd // 2), esc)
            anc = (L.ancora[0] + pad, L.ancora[1] + pad)
        else:
            anc = L.ancora
        M = afim(p["s"], p["rot"], anc, (p["x"], p["y"]), p["sx"])
        if L.mundo:
            M = Cl @ M
        if abs(p["kx"]) > 1e-4:                     # perspectiva de porta: a borda que vem para perto fica mais alta
            h_, w_ = a.shape[:2]
            src = np.float32([[0, 0], [w_, 0], [w_, h_], [0, h_]])
            cy_ = h_ / 2
            fd_, fe_ = (1 + p["kx"], 1.0) if p["kx"] > 0 else (1.0, 1 - p["kx"])
            loc = np.float32([[0, cy_ + (0 - cy_) * fe_], [w_, cy_ + (0 - cy_) * fd_], [w_, cy_ + (h_ - cy_) * fd_],
                              [0, cy_ + (h_ - cy_) * fe_]])
            dst = (M @ np.vstack([loc.T, np.ones(4)]))[:2].T.astype(np.float32)
            Hp = cv2.getPerspectiveTransform(src, dst)
            warp = cv2.warpPerspective(a, Hp, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                       borderValue=0)
        else:
            warp = cv2.warpAffine(a, M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=0)
        alfa = warp[..., 3:4] * p["op"]
        cor = warp[..., :3] * p["op"]
        som = SOMBRA.get(L.sombra) if isinstance(L.sombra, str) else L.sombra
        if som:
            dy, blur, op = som
            dy, blur, op = dy * p["sdy"], blur * p["sbl"], op * p["sop"]
            esc = escala_de(Cl) if L.mundo else 1.0
            sa = cv2.GaussianBlur(warp[..., 3], (0, 0), max(0.5, blur * esc / 2))
            sa = _desce(sa, int(round(dy * esc))) * op * p["op"]
            base *= (1 - sa[..., None] * 0.85)
        base[:] = base * (1 - alfa) + cor
    return base


# ------------------------------------------------------------------ acabamento
# ---- câmera de filme: grão, um RGB quase imperceptível e uma vinheta bem leve. Tudo no acabamento, depois da
# composição, com quatro números:
FUJI_GRAO = 4.6            # amplitude do grão em níveis de 255 (nos meios-tons); ~2,6 antes e invisível depois do H.264
FUJI_GRAO_TROCA = 2        # o grão troca a cada 2 desenhos (7/s); o tremor das bordas (boil) continua em 3,5/s
FUJI_RGB = 0.0016          # aberração cromática radial: o vermelho se afasta e o azul se aproxima do centro (±1,8 px nos cantos)
FUJI_VINHETA = 0.05        # escurecimento do canto (5%), somado à vinheta de papel da cena (agora leve): cantos ~14% mais escuros que o centro
_FUJI_CACHE = {}


def _vinheta_camera():
    if "v" not in _FUJI_CACHE:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - (W - 1) / 2) / (W / 2)) ** 2 + ((yy - (H - 1) / 2) / (H / 2)) ** 2) / math.sqrt(2)   # 0 centro … 1 canto
        t = np.clip((r - 0.38) / 0.62, 0, 1)
        t = t * t * (3 - 2 * t)
        _FUJI_CACHE["v"] = (1 - FUJI_VINHETA * t ** 1.25)[..., None].astype(np.float32)
    return _FUJI_CACHE["v"]


def _aberracao(img, e):
    """RGB radial: R cresce (afasta do centro), B encolhe, G fica; zero no centro e ~1,8 px nos cantos"""
    c = (W / 2, H / 2)
    r = cv2.warpAffine(np.ascontiguousarray(img[..., 0]), afim(1 + e, 0, c, c)[:2], (W, H), flags=cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    b = cv2.warpAffine(np.ascontiguousarray(img[..., 2]), afim(1 - e, 0, c, c)[:2], (W, H), flags=cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REPLICATE)
    return np.dstack([r, img[..., 1], b])


def fuji(img, k, forca=1.0):
    """leve emulação de filme Fuji: pretos um pouco lavados, curva em S suave, sombras
    verde-azuladas e altas luzes quentes, saturação um pouco menor, halo avermelhado nos brilhos, difusão leve e grão de
    filme (mais nos meios-tons) que muda a cada desenho (k)"""
    x = np.clip(img, 0, 1)
    lum = 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    s = x * x * (3 - 2 * x)
    x = x * (1 - 0.22 * forca) + s * 0.22 * forca                       # contraste suave nos meios-tons
    x = 0.028 * forca + x * (1 - 0.045 * forca)                           # preto lavado, ombro nas altas
    ws = np.clip(1 - lum * 1.7, 0, 1) ** 1.5
    wh = np.clip((lum - 0.55) / 0.45, 0, 1)
    x = x + forca * (ws[..., None] * np.array([-0.014, 0.008, 0.016], np.float32)
                     + wh[..., None] * np.array([0.016, 0.006, -0.018], np.float32))
    lum = 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
    x = lum[..., None] + (x - lum[..., None]) * (1 - 0.08 * forca)
    hl = np.clip((lum - 0.80) / 0.2, 0, 1)
    if hl.max() > 0:
        g = cv2.GaussianBlur(hl, (0, 0), 14)
        x = x + forca * g[..., None] * np.array([0.05, 0.016, 0.0], np.float32)
    dif = cv2.GaussianBlur(x, (0, 0), 5)
    x = x * (1 - 0.07 * forca) + dif * 0.07 * forca
    rng = np.random.default_rng(5000 + k // FUJI_GRAO_TROCA)
    n = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 1.0)
    n = n / (n.std() + 1e-6)
    cor = cv2.GaussianBlur(rng.standard_normal((H, W, 3)).astype(np.float32), (0, 0), 1.3)
    cor = cor / (cor.std() + 1e-6)
    meio = 0.55 + 1.8 * lum * (1 - lum)                              # mais grão nos meios-tons, menos no preto e no branco
    x = x + forca * (n[..., None] * 0.85 + cor * 0.28) * meio[..., None] * (FUJI_GRAO / 255.0)
    return np.clip(x, 0, 1)


def acabamento(base, f, grao=1.6, separacao=1.0, passo=None, filme=True):
    """RGB mínimo (radial, zero no centro), grão e o filme Fuji; tudo muda só a cada desenho"""
    k = passo if passo is not None else f // 2
    out = _aberracao(base, FUJI_RGB) if separacao > 0 else base
    if filme:
        return np.clip(fuji(out, int(k)) * _vinheta_camera(), 0, 1)
    if grao > 0:
        rng = np.random.default_rng(1000 + int(k))
        n = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7) * (grao / 255.0) * 1.6
        out = out + n[..., None]
    return np.clip(out, 0, 1)


def papel_fundo(larg=W, alt=H, tom=(232, 229, 211)):
    """papel creme do mundo: a textura do papel antigo do kit tingida para o creme, repetida até o tamanho pedido"""
    bg = Image.open(KIT / "papel_antigo.jpg").convert("RGB")
    bg = bg.crop((330, 330, bg.width - 330, bg.height - 330))
    bg = bg.resize((min(larg, bg.width), round(bg.height * min(larg, bg.width) / bg.width)), Image.LANCZOS)
    a = np.asarray(bg, dtype=np.float32) / 255.0
    lum = a.mean(axis=2, keepdims=True)
    alvo = np.array(tom, dtype=np.float32) / 255.0
    a = np.clip(alvo + (lum - lum.mean()) * 0.9, 0, 1)
    t = Image.fromarray((a * 255).astype(np.uint8))
    out = Image.new("RGB", (larg, alt))
    for y in range(0, alt, t.size[1]):
        for x in range(0, larg, t.size[0]):
            out.paste(t if (x // t.size[0] + y // t.size[1]) % 2 == 0 else t.transpose(Image.FLIP_LEFT_RIGHT), (x, y))
    return out


# ------------------------------------------------------------------ traço que se desenha
def traco_fonte(pontos, larg, alt, cor=(32, 35, 33), espessura=10, seta=False, tam_seta=34, tracejado=None):
    """devolve fonte(fd, props) que desenha a polilinha até a fração props['trim'] (0–1), com ponta de seta no fim"""
    pts = np.array(pontos, dtype=np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acum = np.concatenate([[0], np.cumsum(seg)])
    total = acum[-1]

    def fonte(fd, p):
        t = max(0.0, min(1.0, p["trim"]))
        im = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
        if t <= 0.001:
            return im
        alvo = t * total
        i = int(np.searchsorted(acum, alvo, side="right") - 1)
        i = min(i, len(seg) - 1)
        k = (alvo - acum[i]) / max(seg[i], 1e-6)
        fim = pts[i] + (pts[i + 1] - pts[i]) * k
        viz = [tuple(v) for v in pts[: i + 1]] + [tuple(fim)]
        d = ImageDraw.Draw(im)
        c = cor + (255,)
        if tracejado:
            on, off = tracejado
            pos = 0.0
            for a, b in zip(viz, viz[1:]):
                a, b = np.array(a), np.array(b)
                L = np.linalg.norm(b - a)
                u = (b - a) / max(L, 1e-6)
                s = 0.0
                while s < L:
                    fase = pos % (on + off)
                    if fase < on:
                        e = min(L, s + on - fase)
                        d.line([tuple(a + u * s), tuple(a + u * e)], fill=c, width=espessura)
                        pos += e - s
                        s = e
                    else:
                        e = min(L, s + (on + off) - fase)
                        pos += e - s
                        s = e
        else:
            d.line(viz, fill=c, width=espessura, joint="curve")
            r = espessura / 2
            for v in (viz[0], viz[-1]):
                d.ellipse([v[0] - r, v[1] - r, v[0] + r, v[1] + r], fill=c)
        if seta and t > 0.02:
            a = np.array(viz[-2]) if len(viz) > 1 else pts[0]
            b = np.array(viz[-1])
            u = (b - a) / max(np.linalg.norm(b - a), 1e-6)
            n = np.array([-u[1], u[0]])
            ts = tam_seta * min(1.0, t * 4)
            p1, p2 = b - u * ts + n * ts * 0.6, b - u * ts - n * ts * 0.6
            d.polygon([tuple(b + u * espessura * 0.4), tuple(p1), tuple(p2)], fill=c)
        return im

    return fonte


def arco(cx, cy, r, a0, a1, n=48):
    """pontos de um arco (graus, 0 = direita, positivo no sentido horário na tela)"""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]


# ------------------------------------------------------------------ render
def _linha_kernel(comp, ang):
    n = int(comp) | 1
    k = np.zeros((n, n), np.float32)
    c = n // 2
    dx, dy = math.cos(ang) * c, math.sin(ang) * c
    cv2.line(k, (int(round(c - dx)), int(round(c - dy))), (int(round(c + dx)), int(round(c + dy))), 1.0, 1, cv2.LINE_AA)
    return k / max(k.sum(), 1e-6)


def borrao_radial(img, centro, forca, n=5):
    """rastro de zoom: média de cópias escaladas em volta de um ponto (forca = 0.1 → 10% de alongamento)"""
    acc = img.copy()
    for i in range(1, n):
        s = 1 + forca * i / (n - 1)
        M = afim(s, 0, centro, centro)
        acc += cv2.warpAffine(img, M[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def borrao_camera(base, cam, fd, dt=FPS / DESENHOS):
    """rastro na direção do movimento quando a câmera anda rápido (de um desenho para o seguinte), como nos chicotes"""
    if fd < dt:
        return base
    Ma, Mm, Mb = cam.matriz(fd - dt), cam.matriz(fd - dt / 2), cam.matriz(fd)
    centro = np.array([W / 2, H / 2, 1.0])
    pw = np.linalg.inv(Mb) @ centro
    v = (Mb @ pw - Ma @ pw)[:2]
    vel = float(np.hypot(*v))
    v1 = float(np.hypot(*(Mm @ pw - Ma @ pw)[:2]))
    v2 = float(np.hypot(*(Mb @ pw - Mm @ pw)[:2]))
    if vel > 30 and max(v1, v2) > 0.85 * (v1 + v2):
        return base                                       # salto (corte seco): não é movimento, não leva rastro
    if vel > 900:
        return base                                       # deslocamento maior que meia tela num desenho: corte
    s = escala_de(Mb) / max(escala_de(Ma), 1e-6)
    out = base
    vel *= (FPS / DESENHOS) / 2.0                         # normaliza para o passo de 2 quadros de 24 (limiares medidos)
    if vel > 170:                                         # só nos chicotes MUITO rápidos, e leve (v4.1: legível)
        out = cv2.filter2D(out, -1, _linha_kernel(min(0.14 * (vel - 150), 16), math.atan2(v[1], v[0])),
                           borderType=cv2.BORDER_REFLECT)
    if abs(math.log(s)) > 0.16:
        out = borrao_radial(out, (W / 2, H / 2), min((abs(s - 1) - 0.12) * 0.4, 0.05))
    return out


class Transicao:
    """corte entre dois enquadramentos da câmera principal: A = cam em q0 (saindo), B = cam em q1 (entrando).
    tipo: "iris" (círculo abre a partir de centro), "rasgo" (borda de papel rasgado varre a tela), "empurra" (A sai, B
    entra empurrando, direcao=(dx, dy)), "mergulho" (A afunda num ponto, B vem de dentro), "flash" (passa pelo papel)."""

    def __init__(self, q0, q1, tipo, centro=(W / 2, H / 2), direcao=(-1, 0), semente=3, centro_b=None):
        self.q0, self.q1, self.tipo, self.centro, self.direcao = q0, q1, tipo, centro, direcao
        self.centro_b = centro_b or (W / 2, H / 2)
        rng = np.random.default_rng(semente)
        r = np.cumsum(rng.normal(0, 1, H + 8))
        self.borda = cv2.GaussianBlur((r - r.mean()).astype(np.float32).reshape(-1, 1), (0, 0), 6).ravel()[:H]
        self.borda = self.borda / max(np.abs(self.borda).max(), 1e-6) * 34 + rng.normal(0, 3.5, H)

    def compor(self, f, fd, cam, mundo):
        t = min(max((fd - self.q0) / max(self.q1 - self.q0, 1), 0.0), 1.0)
        CA, CB = cam.matriz(self.q0), cam.matriz(self.q1)
        cx, cy = self.centro
        if self.tipo == "iris":
            A = mundo(afim(1 + 0.12 * curva("in", t), 0, self.centro, self.centro) @ CA, f)
            B = mundo(afim(1.10 - 0.10 * curva("out", t), 0, self.centro, self.centro) @ CB, f)
            R = curva("io", t) * math.hypot(max(cx, W - cx), max(cy, H - cy)) * 1.02
            m = np.zeros((H, W), np.float32)
            cv2.circle(m, (int(cx), int(cy)), int(R), 1.0, -1, cv2.LINE_AA)
            out = A * (1 - m[..., None]) + B * m[..., None]
            if 4 < R:                                    # aro de papel claro com sombra (o furo na folha)
                aro = np.zeros((H, W), np.float32)
                cv2.circle(aro, (int(cx), int(cy)), int(R), 1.0, 12, cv2.LINE_AA)
                sombra = cv2.GaussianBlur(aro, (0, 0), 9) * 0.35
                out = out * (1 - sombra[..., None])
                aro = cv2.GaussianBlur(aro, (0, 0), 1.0)
                out = out * (1 - aro[..., None]) + aro[..., None] * np.array([0.95, 0.93, 0.86], np.float32)
            return out
        if self.tipo == "rasgo":
            A = mundo(CA, f)
            B = mundo(afim(1.06 - 0.06 * curva("out", t), 0, (W / 2, H / 2), (W / 2, H / 2)) @ CB, f)
            x = (W + 80) - curva("io", t) * (W + 160)
            xs = (x + self.borda)[:, None]
            col = np.arange(W)[None, :]
            m = (col > xs).astype(np.float32)
            m = cv2.GaussianBlur(m, (0, 0), 0.8)
            out = A * (1 - m[..., None]) + B * m[..., None]
            fibra = ((col > xs - 16) & (col <= xs)).astype(np.float32)      # a borda branca do papel rasgado
            fibra = cv2.GaussianBlur(fibra, (0, 0), 1.2)
            sombra = cv2.GaussianBlur(((col > xs) & (col < xs + 40)).astype(np.float32), (0, 0), 12) * 0.38
            out = out * (1 - sombra[..., None])
            return out * (1 - fibra[..., None]) + fibra[..., None] * np.array([0.96, 0.94, 0.88], np.float32)
        if self.tipo == "empurra":
            dx, dy = self.direcao
            k = curva("io", t)
            MA = afim(1, -3 * k * dx, (W / 2, H / 2), (W / 2 + dx * W * k, H / 2 + dy * H * k)) @ CA
            MB = afim(1, 3 * (1 - k) * dx, (W / 2, H / 2), (W / 2 - dx * W * (1 - k), H / 2 - dy * H * (1 - k))) @ CB
            A, B = mundo(MA, f), mundo(MB, f)
            m = np.zeros((H, W), np.float32)
            if dx:
                borda = W / 2 + dx * W * k + (-dx) * W / 2
                col = np.arange(W)[None, :]
                m = ((col - borda) * (-dx) > 0).astype(np.float32) * np.ones((H, 1), np.float32)
            else:
                borda = H / 2 + dy * H * k + (-dy) * H / 2
                lin = np.arange(H)[:, None]
                m = ((lin - borda) * (-dy) > 0).astype(np.float32) * np.ones((1, W), np.float32)
            out = A * (1 - m[..., None]) + B * m[..., None]
            v = math.hypot(dx * W, dy * H) * (curva("io", min(t + 0.08, 1)) - curva("io", t))
            if v > 20:
                out = cv2.filter2D(out, -1, _linha_kernel(min(0.5 * v, 90), math.atan2(dy, dx)), borderType=cv2.BORDER_REFLECT)
            return out
        if self.tipo == "mergulho":
            sa = 1 + 4.5 * curva("in", min(t / 0.62, 1))
            sb = 3.2 - 2.2 * curva("out", max((t - 0.38) / 0.62, 0))
            A = mundo(afim(sa, 0, self.centro, self.centro) @ CA, f)
            B = mundo(afim(sb, 0, self.centro_b, self.centro_b) @ CB, f)
            a = curva("io", min(max((t - 0.36) / 0.28, 0), 1))           # cruzamento mais longo e suave
            out = A * (1 - a) + B * a
            forca = 0.05 * math.sin(math.pi * t)
            if forca > 0.04:
                out = borrao_radial(out, self.centro if t < 0.5 else self.centro_b, forca)
            return out
        if self.tipo == "recua":                   # a câmera recua: A encolhe até um ponto e B (outra escala) assenta
            sa = 1 - 0.55 * curva("io", min(t / 0.62, 1))
            sb = 1.55 - 0.55 * curva("out", max((t - 0.38) / 0.62, 0))
            A = mundo(afim(sa, 0, self.centro, self.centro) @ CA, f)
            B = mundo(afim(sb, 0, self.centro_b, self.centro_b) @ CB, f)
            papel = np.array([0.95, 0.92, 0.84], np.float32)             # sem fantasma: A some no papel e B nasce dele
            if t < 0.5:
                k = curva("in", t / 0.5)
                return A * (1 - k) + papel * k
            k = curva("out", (t - 0.5) / 0.5)
            return papel * (1 - k) + B * k
        # flash: A → papel claro → B
        A, B = mundo(CA, f), mundo(CB, f)
        papel = np.array([0.95, 0.92, 0.84], np.float32)
        if t < 0.5:
            k = curva("in", t / 0.5)
            return A * (1 - k) + papel * k
        k = curva("out", (t - 0.5) / 0.5)
        return papel * (1 - k) + B * k


def render(camadas, cam, fundo, n_quadros, saida, audio=None, quadros=None, acab=True, crf=18, transicoes=(),
           borrao=True, filme=True):
    """fundo: PIL RGB do tamanho do mundo. n_quadros e quadros estão no relógio de autoria (24); o vídeo sai a
    FPS_SAIDA com DESENHOS por segundo (cada desenho repetido). transicoes: lista de Transicao; borrao: rastro nos
    chicotes; filme: acabamento Fuji"""
    fundo_arr = np.asarray(fundo.convert("RGB"), dtype=np.float32) / 255.0
    dt = FPS / DESENHOS                                    # quanto do relógio de autoria cada desenho avança

    def mundo(C, f, k):
        base = cv2.warpAffine(fundo_arr, C[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return compor(base, cam, f, camadas, so="mundo", C=C, passo=k)

    def desenho(k):
        f = k * dt
        tr = next((t for t in transicoes if t.q0 <= f < t.q1), None)
        if tr:
            base = tr.compor(f, f, cam, lambda C, ff: mundo(C, ff, k))
        else:
            base = mundo(cam.matriz(f), f, k)
            saiu = any(t.q0 <= f - dt < t.q1 or (f - dt < t.q1 <= f) for t in transicoes)
            if borrao and not saiu:                        # o 1º desenho depois da transição é sempre nítido
                base = borrao_camera(base, cam, f, dt)
        base = compor(base, cam, f, camadas, so="tela", passo=k)
        return acabamento(base, f, passo=k, filme=filme) if acab else base

    if quadros is not None:
        Path(saida).mkdir(parents=True, exist_ok=True)
        for f in quadros:
            k = int(round(f / dt))
            im = Image.fromarray((desenho(k) * 255 + 0.5).astype(np.uint8))
            im.save(Path(saida) / f"q{f:04d}.png")
        return
    n_saida = int(round(n_quadros / FPS * FPS_SAIDA))
    rep = FPS_SAIDA // DESENHOS
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS_SAIDA),
           "-i", "-"]
    if audio:
        cmd += ["-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "256k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-movflags", "+faststart",
            str(saida)]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    k = 0
    g = 0
    while g < n_saida:
        quadro = (desenho(k) * 255 + 0.5).astype(np.uint8).tobytes()
        for _ in range(rep):
            if g < n_saida:
                pr.stdin.write(quadro)
                g += 1
        k += 1
    pr.stdin.close()
    pr.wait()


REGIAO_REELS = (80, 260, 960, 1420)      # margem segura do Reels/TikTok/Shorts (x0, y0, x1, y1) num quadro 1080×1920


def checar_margens(camadas, cam, quadros, regiao=REGIAO_REELS, ignorar=("PAPEL", "MAPA", "VINHETA", "FUNDO", "REGUA",
                                                                          "GRADE")):
    """revisor de enquadramento: para cada quadro, os objetos do mundo que aparecem na tela mas ficam CORTADOS na borda
    ou saem da região segura (margem lateral, topo e rodapé da interface). Devolve [(quadro, camada, problema)]"""
    achados = []
    for f in quadros:
        C = cam.matriz(f)
        for L in camadas:
            if not L.mundo or not (L.ini <= f < L.fim) or any(L.nome.startswith(x) for x in ignorar):
                continue
            p = L.props(f)
            if p["op"] < 0.5 or p["s"] < 0.2 or L.tam is None:
                continue
            w, h = L.tam
            Mm = perto(C, L.prof) @ afim(p["s"], p["rot"], L.ancora, (p["x"], p["y"]), p["sx"])
            cs = np.array([[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]], dtype=np.float64).T
            xy = (Mm @ cs)[:2]
            x0, y0, x1, y1 = xy[0].min(), xy[1].min(), xy[0].max(), xy[1].max()
            if x1 < 0 or x0 > W or y1 < 0 or y0 > H:
                continue                                   # fora da tela: não aparece
            vis = (min(x1, W) - max(x0, 0)) * (min(y1, H) - max(y0, 0)) / max((x1 - x0) * (y1 - y0), 1)
            if vis < 0.15:
                continue                                   # só uma pontinha: é passagem, não enquadramento
            if (x1 - x0) * (y1 - y0) > W * H * 1.3:
                continue                                   # peça maior que a tela (fundo)
            prob = []
            if x0 < -10 or x1 > W + 10 or y0 < -10 or y1 > H + 10:
                prob.append(f"cortada ({vis:.0%} visível)")
            elif x0 < regiao[0] - 25 or x1 > regiao[2] + 25 or y0 < regiao[1] - 40 or y1 > regiao[3] + 40:
                prob.append("fora da margem segura")
            if prob:
                achados.append((f, L.nome, ", ".join(prob), (int(x0), int(y0), int(x1), int(y1))))
    return achados



def ajustar_texto(camadas, cam, fim, transicoes=(), passo=6, fator_max=3.4):
    """garante que todo texto do mundo (etiquetas, carimbos) apareça na tela com corpo >= texto_min (regra: muita gente
    enxerga mal no celular; nada pequeno). Mede o corpo na tela nos quadros parados em que a
    camada aparece e, se faltar, aumenta as chaves de escala dela. Devolve [(camada, corpo_antes, fator)]"""
    feitos = []
    for L in camadas:
        if not L.mundo or not L.texto_px or L.tam is None:
            continue
        medidas = []
        for f in range(max(L.ini, 0), min(L.fim, fim), passo):
            if any(t.q0 <= f < t.q1 for t in transicoes):
                continue
            p = L.props(f)
            if p["op"] < 0.5:
                continue
            C = perto(cam.matriz(f), L.prof)
            x, y = na_tela(C, (p["x"], p["y"]))
            if not (-100 < x < W + 100 and -100 < y < H + 100):
                continue
            medidas.append(L.texto_px * p["s"] * escala_de(C))
        if not medidas:
            continue
        corpo = float(np.percentile(medidas, 12))      # o pior momento (câmera aberta) manda, não a média
        if corpo >= L.texto_min:
            continue
        fator = min(L.texto_min / corpo, fator_max)
        if L.chaves.get("s"):
            L.chaves["s"] = [(q, v * fator, c) for q, v, c in L.chaves["s"]]
        else:
            L.chaves["s"] = [(L.ini, fator, "segura")]
        feitos.append((L.nome, round(corpo), round(fator, 2)))
    return feitos
