"""Mecânicas de camadas: a mesma folha com CAMADAS REGISTRADAS que se revelam uma por cima da outra, peças que se
desmontam e objetos 3D girando a 7 qps como stop-motion de recortes.

Revelar a camada de baixo:
    aba(...)        a camada (ou um pedaço dela) abre como a aba de um livro de anatomia antigo: gira na dobradiça,
                    com perspectiva de porta, sombra e o verso de papel liso
    janela(...)     abre um buraco de papel rasgado que cresce a partir de um ponto (com a borda branca e a sombra dentro)
    descasca(...)   uma borda rasgada atravessa a camada e leva o papel embora
    levanta(...)    a peça descola do papel (sombra cresce), sobe e sai: a luva sai da mão, a tampa sai do crânio
    destaca(...)    a peça descola e viaja até um ponto, crescendo (o coração sai do peito e vem para o meio)
    pousa(...)      o contrário: a peça volta ao lugar e assenta no papel (tudo encaixa de novo)
    explode(...)    as camadas se separam (vista explodida, ou para uma grade com desloc=) e depois voltam

Cortar: cortar_alfa(...) tira uma peça do quadro registrado sem perder o lugar; metades(...) abre a camada ao meio.

Girar: giro(...) troca as vistas de um objeto 3D (render do Blender, ver blender_giro.py) a 7 qps, com a borda de
tesoura em cada vista; o ângulo vem de chaves, então dá para girar, parar, voltar.

Encaixe: pilha(...) põe camadas do mesmo tamanho exatamente uma sobre a outra (mesma âncora, mesmas chaves).
registrar(ref, mov) alinha duas pranchas 2D (ECC) para que encaixem."""
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor as M
import pecas as PC
import cena as C

k = C.k
PASSO_7 = 24.0 / 7.0                     # um desenho de 7 qps no relógio de autoria (24)


def tempos_7qps(q0, q1):
    """instantes de troca a 7 qps entre q0 e q1 (inclui o último)"""
    n = max(1, int(math.ceil((q1 - q0) / PASSO_7)))
    return [q0 + i * (q1 - q0) / n for i in range(n + 1)]


def curva_7qps(q0, q1, v0, v1, curva="io"):
    """chaves em degraus de 7 qps (cada valor segura até o próximo): o movimento anda como stop-motion"""
    ts = tempos_7qps(q0, q1)
    n = len(ts) - 1
    return [(t, v0 + (v1 - v0) * M.curva(curva, i / n), "segura") for i, t in enumerate(ts)]


# ------------------------------------------------------------------ encaixe
def pilha(nome, imagens, x, y, ini=0, fim=10 ** 6, esc=1.0, rot=0.0, sombra=(10, 22, 0.28), boil="obj"):
    """camadas do MESMO tamanho, empilhadas (a 1ª embaixo), com chaves iguais: andam e escalam juntas.
    imagens: lista de PIL RGBA ou de fontes (função fd, p -> PIL) — as fontes servem para revelar (janela, descasca)."""
    out = []
    for i, im in enumerate(imagens):
        tam = im.size if isinstance(im, Image.Image) else getattr(im, "tam", None)
        anc = (tam[0] / 2, tam[1] / 2) if tam else None
        L = M.Camada(f"{nome}_{i}", im, ini, fim, ancora=anc, boil=boil, sombra=sombra if i == 0 else None, chaves={
            "x": k((ini, x, "segura")), "y": k((ini, y, "segura")), "s": k((ini, esc, "segura")),
            "rot": k((ini, rot, "segura"))})
        if getattr(im, "som", None):
            L.som = im.som                       # janela/descasca levam o próprio som
        if tam:
            L.tam = tam
        out.append(L)
    return out


def registrar(ref, mov, iteracoes=200):
    """alinha a imagem 'mov' sobre 'ref' (PIL) por ECC afim no contorno; devolve (mov alinhada, matriz, correlação)"""
    def contorno(im):
        a = np.asarray(im.convert("RGBA"))
        al = a[..., 3].astype(np.float32) / 255 if a[..., 3].min() < 250 else \
            1 - cv2.cvtColor(a[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
        return cv2.GaussianBlur(al, (0, 0), 3)
    r, m = contorno(ref), contorno(mov.resize(ref.size, Image.LANCZOS))
    Wm = np.eye(2, 3, dtype=np.float32)
    cc, Wm = cv2.findTransformECC(r, m, Wm, cv2.MOTION_AFFINE,
                                  (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iteracoes, 1e-6), None, 5)
    a = np.asarray(mov.resize(ref.size, Image.LANCZOS).convert("RGBA"))
    al = cv2.warpAffine(a, Wm, ref.size, flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderValue=(0, 0, 0, 0))
    return Image.fromarray(al), Wm, float(cc)


# ------------------------------------------------------------------ revelações por máscara (fontes dinâmicas)
def _ruido_borda(n, semente, amp):
    rng = np.random.default_rng(semente)
    r = np.cumsum(rng.normal(0, 1, n + 16))
    r = cv2.GaussianBlur((r - r.mean()).astype(np.float32).reshape(-1, 1), (0, 0), 5).ravel()[:n]
    return r / max(np.abs(r).max(), 1e-6) * amp + rng.normal(0, amp * 0.12, n)


def janela(img, centro, q0, q1, raio_final, semente=5, curva="out", sete=True, fecha=None):
    """fonte que abre um buraco de papel rasgado a partir de 'centro' (px da imagem), de raio 0 a raio_final.
    A borda do buraco é branca (fibra do papel) e o fundo do buraco recebe uma sombra (a camada de baixo fica funda).
    fecha=(q2, q3): o buraco se fecha de novo (a pele volta por cima: tudo encaixa)."""
    a0 = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    h, w = a0.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - centro[0], yy - centro[1]
    dist = np.sqrt(dx ** 2 + dy ** 2)
    ang = (np.arctan2(dy, dx) + math.pi) / (2 * math.pi)
    borda = _ruido_borda(720, semente, 0.07)
    var = borda[(ang * 719).astype(int)]
    cache = {}

    def progresso(fd, a, b, cv):
        t = min(max((fd - a) / max(b - a, 1), 0), 1)
        if sete:
            t = math.floor(t * (b - a) / PASSO_7) / max((b - a) / PASSO_7, 1) if t < 1 else 1.0
        return M.curva(cv, t)

    def fonte(fd, p):
        t = progresso(fd, q0, q1, curva)
        if fecha and fd >= fecha[0]:                                   # fecha acelerando: sem "furinho" no fim
            t = 1 - progresso(fd, fecha[0], fecha[1], "in")
        chave = round(t, 3)
        if chave in cache:
            return cache[chave]
        if t <= 0.001:
            im = Image.fromarray((a0 * 255).astype(np.uint8))
        else:
            r = raio_final * t * (1 + var)
            buraco = (dist < r).astype(np.float32)
            buraco = cv2.GaussianBlur(buraco, (0, 0), 0.8)
            fibra = ((dist >= r) & (dist < r + 9)).astype(np.float32)
            fibra = cv2.GaussianBlur(fibra, (0, 0), 1.0) * (a0[..., 3] > 0.05)
            sombra = np.clip(1 - (r - dist) / 40.0, 0, 1) * buraco * 0.38 * (a0[..., 3] > 0.05)   # só dentro do papel
            out = a0.copy()
            out[..., 3] = a0[..., 3] * (1 - buraco)
            papel = np.array([0.96, 0.94, 0.88], np.float32)
            out[..., :3] = out[..., :3] * (1 - fibra[..., None]) + papel * fibra[..., None]
            out[..., 3] = np.maximum(out[..., 3], fibra)
            sub = sombra > out[..., 3]                                    # dentro do buraco: só a sombra, preta
            out[..., :3] = np.where(sub[..., None], 0.0, out[..., :3])
            out[..., 3] = np.maximum(out[..., 3], sombra)
            im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        cache[chave] = im
        return im
    fonte.tam = (w, h)
    fonte.som = ("janela", q0, q1)
    return fonte


def janela_forma(img, mascara, q0, q1, semente=5, curva="out", sete=True, fecha=None):
    """como janela, mas o buraco tem a FORMA da máscara (0–1, do tamanho da imagem): ele nasce no miolo da forma e
    cresce até a borda dela. Regra: a janela redonda faz o músculo ler como uma bola vermelha; com a forma do tronco,
    ele lê como tronco."""
    a0 = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    h, w = a0.shape[:2]
    m = (mascara > 0.5).astype(np.uint8)
    dist = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    prof = dist / max(dist.max(), 1)                                    # 1 no miolo, 0 na borda da forma
    ys, xs = np.nonzero(m)
    cy, cx = ys.mean(), xs.mean()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = (np.arctan2(yy - cy, xx - cx) + math.pi) / (2 * math.pi)
    var = _ruido_borda(720, semente, 0.10)[(ang * 719).astype(int)]
    cache = {}

    def progresso(fd, a, b, cv):
        t = min(max((fd - a) / max(b - a, 1), 0), 1)
        if sete:
            t = math.floor(t * (b - a) / PASSO_7) / max((b - a) / PASSO_7, 1) if t < 1 else 1.0
        return M.curva(cv, t)

    def fonte(fd, p):
        t = progresso(fd, q0, q1, curva)
        if fecha and fd >= fecha[0]:
            t = 1 - progresso(fd, fecha[0], fecha[1], "in")
        chave = round(t, 3)
        if chave in cache:
            return cache[chave]
        if t <= 0.001:
            im = Image.fromarray((a0 * 255).astype(np.uint8))
        else:
            limiar = 1 - t * (1 + var)                                     # o buraco: o que é mais fundo que o limiar
            buraco = ((prof > limiar) & (m > 0)).astype(np.float32) if t < 1 else m.astype(np.float32)
            buraco = cv2.GaussianBlur(buraco, (0, 0), 0.8)
            borda = cv2.dilate((buraco > 0.5).astype(np.uint8), np.ones((19, 19), np.uint8)).astype(np.float32)
            fibra = cv2.GaussianBlur(np.clip(borda - buraco, 0, 1), (0, 0), 1.0) * (a0[..., 3] > 0.05)
            dentro = cv2.distanceTransform((buraco > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
            sombra = np.clip(1 - dentro / 40.0, 0, 1) * buraco * 0.38 * (a0[..., 3] > 0.05)
            out = a0.copy()
            out[..., 3] = a0[..., 3] * (1 - buraco)
            papel = np.array([0.96, 0.94, 0.88], np.float32)
            out[..., :3] = out[..., :3] * (1 - fibra[..., None]) + papel * fibra[..., None]
            out[..., 3] = np.maximum(out[..., 3], fibra)
            sub = sombra > out[..., 3]
            out[..., :3] = np.where(sub[..., None], 0.0, out[..., :3])
            out[..., 3] = np.maximum(out[..., 3], sombra)
            im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        cache[chave] = im
        return im
    fonte.tam = (w, h)
    fonte.som = ("janela", q0, q1)
    return fonte


def descasca(img, q0, q1, direcao="esquerda", semente=7, sete=True, volta=None):
    """fonte: uma borda de papel rasgado atravessa a camada (da direita para a esquerda, por padrão) e leva o papel.
    volta=(q2, q3): o papel volta pelo mesmo caminho (a camada se monta de novo)"""
    a0 = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    h, w = a0.shape[:2]
    borda = _ruido_borda(h, semente, 26)
    col = np.arange(w)[None, :].astype(np.float32)
    cache = {}

    def progresso(fd, a, b):
        t = min(max((fd - a) / max(b - a, 1), 0), 1)
        if sete and t < 1:
            n = max((b - a) / PASSO_7, 1)
            t = math.floor(t * n) / n
        return M.curva("io", t)

    def fonte(fd, p):
        t = progresso(fd, q0, q1)
        if volta and fd >= volta[0]:
            t = 1 - progresso(fd, volta[0], volta[1])
        chave = round(t, 3)
        if chave in cache:
            return cache[chave]
        x = (w + 60) - t * (w + 120) if direcao == "esquerda" else -60 + t * (w + 120)
        xs = (x + borda)[:, None]
        resta = (col < xs) if direcao == "esquerda" else (col > xs)
        resta = cv2.GaussianBlur(resta.astype(np.float32), (0, 0), 0.8)
        fibra = (np.abs(col - xs) < 9).astype(np.float32) * (a0[..., 3] > 0.05)
        out = a0.copy()
        out[..., 3] = a0[..., 3] * resta
        papel = np.array([0.96, 0.94, 0.88], np.float32)
        out[..., :3] = out[..., :3] * (1 - fibra[..., None]) + papel * fibra[..., None]
        out[..., 3] = np.maximum(out[..., 3], fibra * resta.clip(0.5, 1))
        im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
        cache[chave] = im
        return im
    fonte.tam = (w, h)
    fonte.som = ("descasca", q0, q1)
    fonte.sons = [("descasca", volta[0], volta[1])] if volta else []
    return fonte


# ------------------------------------------------------------------ revelações por movimento
def aba(nome, frente, x, y, q0, q1, dobradica="esquerda", verso=None, ini=0, fim=10 ** 6, esc=1.0, rot=0.0,
        abre=170.0, sombra=(10, 22, 0.28), boil="paper", fecha=None):
    """a camada abre como a aba de um livro de anatomia: gira 'abre' graus na dobradiça (esquerda ou direita), em degraus
    de 7 qps, com perspectiva (a borda livre cresce ao vir para perto), escurece ao virar e mostra o verso de papel.
    x, y: onde fica o CENTRO da aba fechada (como nas outras camadas)."""
    w, h = frente.size
    if verso is None:
        verso = PC.textura_papel(w, h, (236, 228, 208), 31)
        verso.putalpha(frente.getchannel("A"))
        verso = verso.transpose(Image.FLIP_LEFT_RIGHT)
    fa = np.asarray(frente.convert("RGBA")).astype(np.float32)
    va = np.asarray(verso.convert("RGBA")).astype(np.float32)
    cache = {}

    def fonte(fd, p):
        sx = p["sx"]
        luz = round(0.62 + 0.38 * abs(sx), 2)                          # de lado ela escurece
        chave = (sx >= 0, luz)
        if chave not in cache:
            base = fa if sx >= 0 else va
            o = base.copy()
            o[..., :3] *= luz
            cache[chave] = Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))
        return cache[chave]
    sinal = 1 if dobradica == "esquerda" else -1
    anc = (0, h / 2) if dobradica == "esquerda" else (w, h / 2)
    xd = x - sinal * w / 2 * esc                                       # a dobradiça fica parada
    ts = tempos_7qps(q0, q1)
    n = len(ts) - 1
    sx, kx, sdy = [(ini, 1.0, "segura")], [(ini, 0.0, "segura")], [(ini, 1.0, "segura")]
    def passo(t, g):
        th = math.radians(g)
        sx.append((t, math.cos(th), "segura"))
        kx.append((t, sinal * 0.16 * math.sin(th), "segura"))
        sdy.append((t, 1.0 + 2.5 * math.sin(th), "segura"))
    for i, t in enumerate(ts):
        passo(t, abre * M.curva("io", i / n))
    if fecha:                                                          # a aba volta e fecha (tudo encaixa)
        ts2 = tempos_7qps(*fecha)
        for i, t in enumerate(ts2):
            passo(t, abre * (1 - M.curva("io", i / (len(ts2) - 1))))
    L = M.Camada(nome, fonte, ini, fim, ancora=anc, boil=boil, sombra=sombra, chaves={
        "x": k((ini, xd, "segura")), "y": k((ini, y, "segura")), "s": k((ini, esc, "segura")),
        "rot": k((ini, rot, "segura")), "sx": sx, "kx": kx, "sdy": sdy})
    L.tam = (w, h)
    L.som = ("vira", q0)
    L.sons = [("vira", fecha[0])] if fecha else []
    return L


def pulsa(camada, q0, q1, padrao, periodo):
    """vida: multiplica a escala por um padrão que se repete (em degraus de 7 qps), sem mexer nas chaves de movimento.
    O coração: padrao=[1.07, 1.03, 1.0, 1.0, 1.0, 1.0] com periodo de 6 desenhos (70 batidas por minuto);
    o pulmão: uma senoide lenta (periodo de 28 desenhos, 4 s)."""
    ch = [(0, 1.0, "segura")]
    t, i = float(q0), 0
    while t < q1:
        ch.append((t, padrao[i % len(padrao)], "segura"))
        t += PASSO_7 * periodo / len(padrao)
        i += 1
    ch.append((q1, 1.0, "segura"))
    camada.chaves["sm"] = ch
    return camada


def levanta(camada, q0, q1, para=(0, -900), giro=12.0, sobe=0.08, sete=True):
    """a peça descola do papel (cresce um pouco e a sombra se afasta), depois sai na direção 'para' girando;
    a camada de baixo (a mão, o cérebro) aparece no mesmo lugar"""
    x0 = M.valor(camada.chaves.get("x"), q0, 0)
    y0 = M.valor(camada.chaves.get("y"), q0, 0)
    s0 = M.valor(camada.chaves.get("s"), q0, 1.0)
    r0 = M.valor(camada.chaves.get("rot"), q0, 0.0)
    meio = q0 + (q1 - q0) * 0.35
    corta = lambda lst: [c for c in lst if c[0] < q0]
    if sete:
        desc = curva_7qps(q0, meio, 0, 1, "out")
        sai = curva_7qps(meio, q1, 0, 1, "in")
    else:
        desc = [(q0, 0, "out"), (meio, 1, "segura")]
        sai = [(meio, 0, "in"), (q1, 1, "segura")]
    camada.chaves["s"] = corta(camada.chaves.get("s", [(0, s0, "segura")])) + \
        [(t, s0 * (1 + sobe * v), c) for t, v, c in desc]
    camada.chaves["sdy"] = [(0, 1.0, "segura")] + [(t, 1 + 3.0 * v, c) for t, v, c in desc]
    camada.chaves["sbl"] = [(0, 1.0, "segura")] + [(t, 1 + 1.6 * v, c) for t, v, c in desc]
    camada.chaves["sop"] = [(0, 1.0, "segura")] + [(t, 1 - 0.35 * v, c) for t, v, c in desc]
    camada.chaves["x"] = corta(camada.chaves.get("x", [])) + [(q0, x0, "segura")] + \
        [(t, x0 + para[0] * v, c) for t, v, c in sai]
    camada.chaves["y"] = corta(camada.chaves.get("y", [])) + [(q0, y0, "segura")] + \
        [(t, y0 + para[1] * v, c) for t, v, c in sai]
    camada.chaves["rot"] = corta(camada.chaves.get("rot", [(0, r0, "segura")])) + [(q0, r0, "segura")] + \
        [(t, r0 + giro * v, c) for t, v, c in sai]
    camada.fim = min(camada.fim, int(q1) + 2)
    camada.som = ("levanta", q0)
    return camada


def explode(camadas, q0, q1, passo=(0, 260), volta=None, giro=0.0, sete=True, desloc=None):
    """vista explodida: a camada i se desloca i·passo (as de cima mais longe); 'volta' = quadro em que elas se juntam.
    desloc = [(dx, dy), ...] dá o deslocamento de cada camada (ex.: uma grade 2×2) em vez de i·passo"""
    for i, L in enumerate(camadas):
        x0 = M.valor(L.chaves.get("x"), q0, 0)
        y0 = M.valor(L.chaves.get("y"), q0, 0)
        dx, dy = desloc[i] if desloc else (passo[0] * i, passo[1] * i)
        ida = curva_7qps(q0, q1, 0, 1, "io") if sete else [(q0, 0, "io"), (q1, 1, "segura")]
        L.chaves["x"] = [c for c in L.chaves["x"] if c[0] < q0] + [(t, x0 + dx * v, c) for t, v, c in ida]
        L.chaves["y"] = [c for c in L.chaves["y"] if c[0] < q0] + [(t, y0 + dy * v, c) for t, v, c in ida]
        if volta:
            vt = curva_7qps(volta, volta + (q1 - q0), 1, 0, "io") if sete else [(volta, 1, "io"), (volta + q1 - q0, 0, "segura")]
            L.chaves["x"] += [(t, x0 + dx * v, c) for t, v, c in vt]
            L.chaves["y"] += [(t, y0 + dy * v, c) for t, v, c in vt]
    return camadas


def destaca(camada, q0, q1, para, esc=1.0, rot=0.0, sobe=0.08, sete=True):
    """a peça descola do papel (cresce e a sombra se afasta) e viaja até 'para' (x, y do mundo), mudando de escala
    ('esc' multiplica a atual) e de ângulo: o coração sai do peito e vem para o meio da tela. Fica lá (não some)."""
    x0 = M.valor(camada.chaves.get("x"), q0, 0)
    y0 = M.valor(camada.chaves.get("y"), q0, 0)
    s0 = M.valor(camada.chaves.get("s"), q0, 1.0)
    r0 = M.valor(camada.chaves.get("rot"), q0, 0.0)
    meio = q0 + (q1 - q0) * 0.3
    corta = lambda lst: [c for c in lst if c[0] < q0]
    desc = curva_7qps(q0, meio, 0, 1, "out") if sete else [(q0, 0, "out"), (meio, 1, "segura")]
    vai = curva_7qps(meio, q1, 0, 1, "io") if sete else [(meio, 0, "io"), (q1, 1, "segura")]
    s1 = s0 * (1 + sobe)
    camada.chaves["s"] = corta(camada.chaves.get("s", [])) + [(t, s0 + (s1 - s0) * v, c) for t, v, c in desc] + \
        [(t, s1 + (s0 * esc - s1) * v, c) for t, v, c in vai]
    camada.chaves["sdy"] = [(0, 1.0, "segura")] + [(t, 1 + 2.4 * v, c) for t, v, c in desc]
    camada.chaves["sbl"] = [(0, 1.0, "segura")] + [(t, 1 + 1.4 * v, c) for t, v, c in desc]
    camada.chaves["sop"] = [(0, 1.0, "segura")] + [(t, 1 - 0.3 * v, c) for t, v, c in desc]
    for chave, a, b in (("x", x0, para[0]), ("y", y0, para[1]), ("rot", r0, rot)):
        camada.chaves[chave] = corta(camada.chaves.get(chave, [])) + [(q0, a, "segura")] + \
            [(t, a + (b - a) * v, c) for t, v, c in vai]
    camada.som = ("levanta", q0)
    return camada


def pousa(camada, q0, q1, para, esc=1.0, rot=0.0, sete=True):
    """o contrário de destaca: a peça (já descolada) viaja até 'para' com a escala 'esc' (multiplica a atual) e assenta
    no papel (a sombra volta para perto): o coração volta para o peito, os ossos voltam para a mão"""
    x0 = M.valor(camada.chaves.get("x"), q0, 0)
    y0 = M.valor(camada.chaves.get("y"), q0, 0)
    s0 = M.valor(camada.chaves.get("s"), q0, 1.0)
    r0 = M.valor(camada.chaves.get("rot"), q0, 0.0)
    sdy0 = M.valor(camada.chaves.get("sdy"), q0, 1.0)
    sbl0 = M.valor(camada.chaves.get("sbl"), q0, 1.0)
    sop0 = M.valor(camada.chaves.get("sop"), q0, 1.0)
    corta = lambda lst: [c for c in lst if c[0] < q0]
    pouso = q0 + (q1 - q0) * 0.75
    vai = curva_7qps(q0, pouso, 0, 1, "io") if sete else [(q0, 0, "io"), (pouso, 1, "segura")]
    assenta = curva_7qps(pouso, q1, 0, 1, "in") if sete else [(pouso, 0, "in"), (q1, 1, "segura")]
    s1 = s0 * esc
    camada.chaves["s"] = corta(camada.chaves.get("s", [])) + [(q0, s0, "segura")] + \
        [(t, s0 + (s1 * 1.06 - s0) * v, c) for t, v, c in vai] + [(t, s1 * 1.06 + (s1 - s1 * 1.06) * v, c) for t, v, c in assenta]
    for chave, a in (("sdy", sdy0), ("sbl", sbl0), ("sop", sop0)):
        camada.chaves[chave] = corta(camada.chaves.get(chave, [(0, 1.0, "segura")])) + [(q0, a, "segura")] + \
            [(t, a + (1.0 - a) * v, c) for t, v, c in assenta]
    for chave, a, b in (("x", x0, para[0]), ("y", y0, para[1]), ("rot", r0, rot)):
        camada.chaves[chave] = corta(camada.chaves.get(chave, [])) + [(q0, a, "segura")] + \
            [(t, a + (b - a) * v, c) for t, v, c in vai]
    return camada


def cortar_alfa(img, margem=24):
    """recorta uma camada registrada (quadro inteiro) no contorno do que tem nela; devolve (peça, (dx, dy)): dx, dy é
    onde fica o centro da peça em relação ao centro do quadro, em px da imagem (para pôr a peça no mesmo lugar)"""
    x0, y0, x1, y1 = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    x0, y0 = max(0, x0 - margem), max(0, y0 - margem)
    x1, y1 = min(img.width, x1 + margem), min(img.height, y1 + margem)
    return img.crop((x0, y0, x1, y1)), ((x0 + x1) / 2 - img.width / 2, (y0 + y1) / 2 - img.height / 2)


def metades(img, corte=None, fibra=5):
    """corta a camada ao meio na vertical (em 'corte', px; padrão o meio), como a pele aberta pela linha do meio
    nos livros de anatomia; a borda do corte ganha a fibra branca do papel. Devolve (esquerda, direita)."""
    w, h = img.size
    cx = int(corte if corte is not None else w // 2)
    a = np.asarray(img.convert("RGBA")).copy()
    papel = np.array([244, 238, 222], np.uint8)
    for x0, x1 in ((cx - fibra, cx), (cx, cx + fibra)):
        faixa = a[:, x0:x1]
        dentro = faixa[..., 3] > 40
        faixa[dentro, :3] = papel
    esq = Image.fromarray(a[:, :cx].copy())
    dir_ = Image.fromarray(a[:, cx:].copy())
    return esq, dir_


# ------------------------------------------------------------------ objeto 3D girando a 7 qps
def giro(nome, vistas, x, y, chaves_ang, ini=0, fim=10 ** 6, esc=1.0, fps=7.0, sombra=(12, 24, 0.3), boil="obj",
         mundo=True):
    """vistas: lista de PIL RGBA (todas do mesmo tamanho), a vista i = ângulo 360·i/N. chaves_ang: [(q, graus, curva)].
    A vista troca a 'fps' por segundo (7 = stop-motion de recortes), mesmo com a câmera a 14."""
    n = len(vistas)
    w, h = vistas[0].size
    passo = 24.0 / fps

    def fonte(fd, p):
        fq = ini + math.floor((fd - ini) / passo) * passo
        ang = M.valor(chaves_ang, fq, 0.0)
        return vistas[int(round(ang / 360.0 * n)) % n]
    L = M.Camada(nome, fonte, ini, fim, ancora=(w / 2, h / 2), boil=boil, sombra=sombra, mundo=mundo, chaves={
        "x": k((ini, x, "segura")), "y": k((ini, y, "segura")), "s": k((ini, esc, "segura"))})
    L.tam = (w, h)
    L.som = ("giro", ini)
    return L


# ------------------------------------------------------------------ render 3D -> recorte de papel
def _recorte_quadro(peca, borda=10, semente=3, escala=1.0, silhueta=None):
    """como pecas.recorte, mas SEM cortar no contorno: o quadro inteiro fica, então camadas renderizadas pela mesma
    câmera continuam encaixadas pixel a pixel depois da borda de tesoura e da escala.
    silhueta (alfa do objeto inteiro, mesmo tamanho): a borda branca só sai por FORA dela. Corte interno de uma peça
    (o braço separado do tronco, a porta do paletó) não ganha borda: ela apareceria como franja branca dentro do corpo"""
    al = np.asarray(peca.getchannel("A"))
    pad = borda + 4
    al2 = np.pad(al, pad)
    dil = cv2.dilate(al2, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * borda + 1, 2 * borda + 1)))
    if silhueta is not None:
        sil = silhueta if isinstance(silhueta, np.ndarray) else np.asarray(
            (Image.open(silhueta) if not isinstance(silhueta, Image.Image) else silhueta).getchannel("A"))
        sil = np.pad((sil > 20).astype(np.uint8) * 255, pad)
        sil = cv2.dilate(sil, np.ones((5, 5), np.uint8))
        dil = np.maximum(al2, np.minimum(dil, 255 - sil))
    base = PC.textura_papel(al2.shape[1], al2.shape[0], (244, 238, 222), semente)
    base.putalpha(Image.fromarray(cv2.GaussianBlur(dil, (0, 0), 0.8)))
    base.alpha_composite(peca, (pad, pad))
    if escala != 1.0:
        base = base.resize((round(base.width * escala), round(base.height * escala)), Image.LANCZOS)
    return base


def apara_lascas(im, k=15):
    """tira do alfa as lascas mais finas que k px que a malha deixa na borda (faces dobradas na barra, no punho e embaixo
    do braço viravam pontas de papel). Vai ANTES do papelizar, senão a borda branca contorna a lasca."""
    a = np.asarray(im.convert("RGBA")).copy()
    aberto = cv2.morphologyEx(a[..., 3], cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    a[..., 3] = np.minimum(a[..., 3], aberto)
    return Image.fromarray(a)


def fecha_vazados(im, area_max=20000, cor=(46, 38, 32)):
    """furo pequeno e fechado no alfa (o vão da mandíbula, a fresta do arco zigomático) vira sombra escura: com o fundo
    aparecendo, o papel ganhava uma borda branca DENTRO da figura)"""
    a = np.asarray(im.convert("RGBA")).copy()
    vazio = (a[..., 3] < 128).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(vazio, connectivity=4)
    h, w = vazio.shape
    for i in range(1, n):
        x, y, bw, bh, area = st[i]
        if area <= area_max and x > 0 and y > 0 and x + bw < w and y + bh < h:     # não encosta na borda: é furo
            m = lab == i
            a[m, :3] = cor
            a[m, 3] = 255
    return Image.fromarray(a)


def papelizar(png, estilo="gravura", borda=10, semente=3, cor=0.55, alt=None, luz=None, registrado=False, escala=1.0,
              contraste=1.0, silhueta=None):
    """transforma um render 3D (PNG com alfa) numa peça da colagem.
    estilo 'gravura': pontilhado de tinta sépia sobre papel, colorido à mão (como as pranchas de anatomia antigas);
    com 'luz' (o passe de sombra do blender_giro), o pontilhado vem da luz e a cor vem do passe chapado (png).
    estilo 'impresso': foto impressa envelhecida. Sempre com a borda branca de tesoura.
    registrado=True mantém o quadro inteiro (camadas da mesma câmera continuam encaixadas); senão corta no contorno."""
    im = Image.open(png).convert("RGBA") if not isinstance(png, Image.Image) else png.convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3]
    if estilo == "gravura":
        if luz is not None:
            lz = np.asarray(Image.open(luz).convert("RGB") if not isinstance(luz, Image.Image) else luz.convert("RGB"))
            lum = (lz.astype(np.float32) / 255).mean(axis=2)
            albedo = rgb
        else:
            lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
            albedo = None
        lum = np.clip((lum - 0.06) / 0.86, 0, 1)
        escuro = (1 - lum) ** 1.35                                      # quanto de tinta cada ponto pede
        rng = np.random.default_rng(semente)
        lim = rng.random(lum.shape).astype(np.float32)                  # pontilhado fino (ponto de 1 px), como buril
        pontos = (escuro * 1.05 > lim + 0.08).astype(np.float32)
        pontos = cv2.GaussianBlur(pontos, (0, 0), 0.45)
        papel = np.array(PC.CREME, np.float32) / 255
        sepia = np.array([0.20, 0.15, 0.11], np.float32)
        tom = 0.35 * escuro / contraste ** 0.5                          # um tom contínuo leve por baixo (aguada)
        tinta = np.clip(tom + pontos * 0.75, 0, 0.92)
        contorno = cv2.morphologyEx((al > 0.5).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        fonte_linhas = albedo.mean(axis=2) if albedo is not None else lum
        linhas = cv2.Canny((np.clip(fonte_linhas, 0, 1) * 255).astype(np.uint8), 40, 110) / 255.0
        if contraste > 1.0:                                             # contorno mais firme entre as partes
            linhas = cv2.dilate(linhas.astype(np.float32), np.ones((2, 2), np.uint8))
        traco = np.clip(cv2.GaussianBlur((contorno + linhas * 0.7 * contraste).astype(np.float32), (0, 0), 0.6) * 1.4,
                        0, 1)
        tinta = np.maximum(tinta, traco * 0.85)
        out = papel * (1 - tinta[..., None]) + sepia * tinta[..., None]
        if albedo is not None:                                          # aquarela: a cor chapada multiplicada
            aq = 1 - (1 - albedo) * cor
            out = out * np.clip(aq * 1.08, 0, 1.1)
        else:
            lum3 = lum[..., None]
            tinta_cor = np.clip(rgb / np.maximum(lum3, 0.12), 0, 1.6)
            tinta_cor = 1 + (tinta_cor - 1) * cor
            out = out * np.clip(tinta_cor, 0.45, 1.15)
        tex = PC.textura_papel(im.width, im.height, (255, 255, 255), semente)
        t = np.asarray(tex.convert("L")).astype(np.float32) / 255
        out = out * (0.92 + 0.08 * t[..., None])
        rgb = np.clip(out, 0, 1)
    else:
        rgb = np.asarray(PC.envelhecer(Image.fromarray((rgb * 255).astype(np.uint8)))).astype(np.float32) / 255
    peca = Image.fromarray(np.dstack([(rgb * 255).astype(np.uint8), (al * 255).astype(np.uint8)]))
    if registrado:
        return _recorte_quadro(peca, borda=borda, semente=semente, escala=escala, silhueta=silhueta)
    return PC.recorte(peca, alt=alt, borda=borda, envelhece=False, semente=semente)
