"""Blocos de cena das colagens (sobre o motor): objeto que cai e pousa, legenda na tela, traço vermelho que se
desenha (com a ponta que a câmera pode seguir), contador, carimbo, círculo, vinheta e câmera por planos.

Tudo em quadros de 24 qps; os eventos do desenho caem em quadros PARES (12 qps). Coordenadas do mundo em px."""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor as M
import pecas as PC

W, H = M.W, M.H
POP = [(0, 1.10, "out"), (3, 1.03, "io"), (5, 0.995, "io"), (7, 1.0, "segura")]   # pouso (v3: mais suave)

# região segura da tela para o assunto (v3): margem lateral de 70 px, nada importante acima de 210 (interface do topo)
# nem abaixo de 1190 (a legenda fica em 1220–1390; abaixo de ~1440 entra a interface do Reels/TikTok)
REGIAO = (70, 210, 1010, 1190)
REGIAO_SEM_LEGENDA = (70, 210, 1010, 1450)


def quadro(caixa, regiao=REGIAO, rot=0.0):
    """(z, cx, cy, rot) que encaixa a caixa do mundo (x0, y0, x1, y1) DENTRO da região da tela, o maior possível"""
    x0, y0, x1, y1 = caixa
    rx0, ry0, rx1, ry1 = regiao
    z = min((rx1 - rx0) / (x1 - x0), (ry1 - ry0) / (y1 - y0))
    cx = (x0 + x1) / 2 - ((rx0 + rx1) / 2 - W / 2) / z
    cy = (y0 + y1) / 2 - ((ry0 + ry1) / 2 - H / 2) / z
    return (z, cx, cy, rot)


def k(*pares):
    return [tuple(x) for x in pares]


def cai(nome, imagem, q0, x, y, rot=0.0, de_y=-140, sombra=(10, 22, 0.28), boil="obj", fim=10 ** 6, esc=1.0):
    """objeto que cai do alto e pousa no papel: desce em 6 quadros, escala com pop, gira até o ângulo final"""
    L = M.Camada(nome, imagem, q0, fim, boil=boil, sombra=sombra, chaves={
        "x": k((q0, x, "segura")),
        "y": k((q0, y + de_y, "out"), (q0 + 6, y, "segura")),
        "s": [(q0 + a, v * esc, c) for a, v, c in POP],
        "rot": k((q0, rot - 7, "out"), (q0 + 8, rot, "segura")),
        "op": k((q0, 0.0, "lin"), (q0 + 2, 1.0, "segura"))})
    L.som = ("pouso", q0 + 5)                                  # o objeto encosta no papel
    return L


def desliza(nome, imagem, q0, de, para, rot=0.0, dur=8, sombra=(10, 22, 0.28), boil="obj", fim=10 ** 6, esc=1.0):
    """objeto que entra deslizando (de → para, no mundo) e assenta com um leve passo além"""
    (x0, y0), (x1, y1) = de, para
    L = M.Camada(nome, imagem, q0, fim, boil=boil, sombra=sombra, chaves={
        "x": k((q0, x0, "out"), (q0 + dur, x1, "segura")),
        "y": k((q0, y0, "out"), (q0 + dur, y1, "segura")),
        "s": k((q0, esc, "segura")),
        "rot": k((q0, rot + 4, "out"), (q0 + dur, rot, "segura"))})
    L.som = ("desliza", q0 + dur // 2, 1 if x0 > x1 else -1)   # direção: entra pela direita (1) ou pela esquerda (-1)
    return L


def fixo(nome, imagem, x, y, rot=0.0, ini=0, fim=10 ** 6, sombra=(10, 22, 0.28), boil="obj", esc=1.0, ancora=None):
    return M.Camada(nome, imagem, ini, fim, ancora=ancora, boil=boil, sombra=sombra, chaves={
        "x": k((ini, x, "segura")), "y": k((ini, y, "segura")), "rot": k((ini, rot, "segura")),
        "s": k((ini, esc, "segura"))})


def legenda(nome, imagem, q0, q1, y=1320, rot=1.0):
    """tira de papel na faixa segura da tela (não anda com a câmera)"""
    return M.Camada(nome, imagem, q0, q1, mundo=False, boil="type", sombra=(5, 12, 0.22), chaves={
        "x": k((q0, W / 2, "segura")), "y": k((q0, y + 18, "out"), (q0 + 4, y, "segura")),
        "rot": k((q0, rot, "segura")), "op": k((q0, 0.0, "lin"), (q0 + 2, 1.0, "segura"))})


class Traco:
    """traço de caneta vermelha por pontos do MUNDO, que se desenha de q0 a q1 (curva 'io' por padrão).
    .camada → a Camada; .ponta(f) → onde está a ponta no quadro f (para a câmera seguir e o contador andar junto)"""

    def __init__(self, nome, pontos, q0, q1, espessura=26, cor=PC.VERMELHO, curva="io", seta=False, tam_seta=46,
                 tracejado=None, op=0.85, tremor=2.0, fim=10 ** 6, semente=3, suave=False):
        pts = np.array(pontos, dtype=np.float32)
        if suave and len(pts) > 2:                        # curva que passa pelos pontos (Catmull-Rom), sem bicos
            pts = _catmull(pts)
        if tremor:                                        # mão: um tremor baixo e lento ao longo do traço
            pts = _densificar(pts, 40.0)
            rng = np.random.default_rng(semente)
            n = np.cumsum(rng.normal(0, 1, (len(pts), 2)), axis=0)
            n = n - np.linspace(n[0], n[-1], len(pts))
            pts[1:-1] += (n[1:-1] / max(1.0, np.abs(n).max())) * tremor
        m = espessura + tam_seta + 20
        self.x0, self.y0 = pts[:, 0].min() - m, pts[:, 1].min() - m
        loc = pts - [self.x0, self.y0]
        larg = int(pts[:, 0].max() - self.x0 + m)
        alt = int(pts[:, 1].max() - self.y0 + m)
        self.pts, self.q0, self.q1, self.curva = pts, q0, q1, curva
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        self.acum = np.concatenate([[0], np.cumsum(seg)])
        fonte = M.traco_fonte([tuple(p) for p in loc], larg, alt, cor=cor, espessura=espessura, seta=seta,
                              tam_seta=tam_seta, tracejado=tracejado)
        self.camada = M.Camada(nome, fonte, q0, fim, ancora=(0, 0), boil="ink", chaves={
            "x": k((q0, self.x0, "segura")), "y": k((q0, self.y0, "segura")),
            "trim": k((q0, 0.0, curva), (q1, 1.0, "segura")), "op": k((q0, op, "segura"))})

    def fracao(self, f):
        f = f - f % 2
        return M.curva(self.curva, (f - self.q0) / (self.q1 - self.q0)) if f < self.q1 else 1.0

    def ponta(self, f):
        alvo = self.fracao(f) * self.acum[-1]
        i = min(int(np.searchsorted(self.acum, alvo, side="right") - 1), len(self.pts) - 2)
        u = (alvo - self.acum[i]) / max(self.acum[i + 1] - self.acum[i], 1e-6)
        return tuple(self.pts[i] + (self.pts[i + 1] - self.pts[i]) * min(max(u, 0), 1))


def _catmull(p, n=16):
    p = np.vstack([p[0], p, p[-1]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-2])
    return np.array(out, dtype=np.float32)


def _densificar(pts, passo):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        n = max(1, int(np.linalg.norm(b - a) / passo))
        out += [a + (b - a) * (j / n) for j in range(1, n + 1)]
    return np.array(out, dtype=np.float32)


def contador(nome, q0, q1, fim, total, fmt, x=W / 2, y=1478, curva="io", corpo=62, mundo=False, largura_ref=None):
    """número que corre de 0 a total entre q0 e q1 (fmt(v) → texto), numa tira de papel. Na tela por padrão."""
    fo = PC.fonte("IBMPlexMono-Medium.ttf", corpo)
    w = int(fo.getlength(largura_ref or fmt(total))) + 56
    hh = int(corpo * 1.68)
    cache = {}

    def fonte(fd, p):
        t = max(0.0, min(1.0, p["trim"]))
        v = total * t
        txt = fmt(total if t >= 1 else v)
        if txt not in cache:
            im = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle((0, 4, w - 1, hh - 4), radius=10, fill=(246, 238, 220, 245))
            d.text((w / 2, hh / 2), txt, font=fo, fill=PC.VERMELHO + (255,), anchor="mm")
            cache[txt] = im
        return cache[txt]

    return M.Camada(nome, fonte, q0, fim, ancora=(w / 2, hh / 2), mundo=mundo, boil="type", sombra=(4, 10, 0.2),
                    chaves={"x": k((q0, x, "segura")), "y": k((q0, y, "segura")), "rot": k((q0, -1.5, "segura")),
                            "s": k((q0, 1.15, "lin"), (q0 + 2, 0.97, "lin"), (q0 + 4, 1.0, "segura")),
                            "trim": k((q0, 0.0, curva), (q1, 1.0, "segura"))})


def carimbo(nome, imagem, q0, x, y, rot, fim=10 ** 6, mundo=True, esc=1.0):
    return M.Camada(nome, imagem, q0, fim, boil="print", sombra=None, mundo=mundo, chaves={
        "x": k((q0, x, "segura")), "y": k((q0, y, "segura")),
        "s": k((q0, 1.7 * esc, "lin"), (q0 + 2, 0.94 * esc, "lin"), (q0 + 4, 1.02 * esc, "lin"), (q0 + 6, esc, "segura")),
        "rot": k((q0, rot, "segura")),
        "op": k((q0, 0.0, "lin"), (q0 + 2, 1.0, "segura"))})


def circulo(nome, cx, cy, rx, ry, q0, q1, espessura=26, rot=-4, fim=10 ** 6, volta=395):
    """volta de caneta em torno de algo (passa um pouco do começo, como à mão)"""
    pts = []
    for t in np.linspace(0, 1, 90):
        a = math.radians(-120 + volta * t)
        r = 1.0 + 0.035 * math.sin(3 * a + 0.6) + 0.05 * t
        pts.append((rx * 1.1 + 30 + rx * r * math.cos(a), ry * 1.1 + 30 + ry * r * math.sin(a)))
    larg, alt = int(2 * rx * 1.1 + 60), int(2 * ry * 1.1 + 60)
    fonte = M.traco_fonte(pts, larg, alt, cor=PC.VERMELHO, espessura=espessura)
    return M.Camada(nome, fonte, q0, fim, ancora=(larg / 2, alt / 2), boil="ink", chaves={
        "x": k((q0, cx, "segura")), "y": k((q0, cy, "segura")), "rot": k((q0, rot, "segura")),
        "trim": k((q0, 0.0, "out"), (q1, 1.0, "segura")), "op": k((q0, 0.85, "segura"))})


def vinheta(fim):
    gx, gy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    r = np.sqrt(gx ** 2 + (gy * 0.8) ** 2)
    a = (np.clip((r - 0.6) / 0.7, 0, 1) ** 1.8 * 0.2 * 255).astype(np.uint8)   # v7: bem leve; o resto é a vinheta da câmera
    v = np.zeros((H, W, 4), np.uint8); v[..., :3] = (58, 40, 22); v[..., 3] = a
    return M.Camada("VINHETA", Image.fromarray(v), 0, fim, mundo=False, degrau=False)


class Camera:
    """câmera por planos. plano(q, (z, cx, cy[, rot]), curva até o próximo); seguir(traço, q0, q1, z, tela=(x, y)) põe
    chaves a cada 2 quadros para a ponta do traço ficar parada no ponto (x, y) da tela"""

    def __init__(self):
        self.ch = {"z": [], "cx": [], "cy": [], "rot": []}

    def plano(self, q, zxy, curva="segura", rot=None):
        z, cx, cy = zxy[:3]
        r = rot if rot is not None else (zxy[3] if len(zxy) > 3 else 0.0)
        for nome, v in (("z", z), ("cx", cx), ("cy", cy), ("rot", r)):
            self.ch[nome].append((q, v, curva))
        return self

    def seguir(self, traco, q0, q1, z, tela=(540, 760), so_y=False, cx=None):
        for f in range(q0, q1 + 1, 2):
            px, py = traco.ponta(f)
            ccx = cx if so_y else px - (tela[0] - W / 2) / z
            self.plano(f, (z, ccx, py - (tela[1] - H / 2) / z), "lin")
        return self

    def montar(self):
        for nome in self.ch:
            self.ch[nome].sort(key=lambda c: c[0])
        return M.Camera(self.ch, degrau=True)


def enquadra(caixa, margem=0.08, tela_y=(0.0, 1.0)):
    """(z, cx, cy) que cabe a caixa (x0, y0, x1, y1) do mundo na tela, com margem; tela_y limita a faixa vertical
    usada (ex.: (0.05, 0.62) deixa o terço de baixo livre para a legenda)"""
    x0, y0, x1, y1 = caixa
    hy = (tela_y[1] - tela_y[0]) * H
    z = min(W * (1 - 2 * margem) / (x1 - x0), hy * (1 - 2 * margem) / (y1 - y0))
    cx = (x0 + x1) / 2
    cy_tela = (tela_y[0] + tela_y[1]) / 2 * H
    cy = (y0 + y1) / 2 - (cy_tela - H / 2) / z
    return (z, cx, cy)


# ------------------------------------------------------------------ vocabulário de movimento (estudo dos trechos Vox)
def fundo_escuro(fim, chaves, cor=(32, 35, 33)):
    """papel carvão na tela inteira, POR BAIXO dos objetos (pôr como 1ª camada da lista); chaves = [(q, op, curva)]"""
    pg = PC.papel_mundo(W, H, tom=cor, textura=0.6, manchas=0.2).convert("RGBA")
    L = M.Camada("FUNDO_ESCURO", pg, 0, fim, mundo=False, degrau=True, chaves={
        "x": k((0, W / 2, "segura")), "y": k((0, H / 2, "segura")), "op": [tuple(c) for c in chaves]})
    L.fundo = True
    return L


def rajada(nome, x, y, q0, raio=420, n=14, cor=(246, 238, 220), mundo=True, dur=8, espessura=18, semente=5, fim=None):
    """explosão gráfica de papel no instante do evento: raios que saem do centro e somem (8 quadros)"""
    rng = np.random.default_rng(semente)
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False) + rng.uniform(-0.12, 0.12, n)
    comps = rng.uniform(0.55, 1.0, n)
    tam = int(raio * 2 + 60)

    def fonte(fd, p):
        t = max(0.0, min(1.0, p["trim"]))
        im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = tam / 2
        for a, L in zip(angs, comps):
            r0 = raio * (0.18 + 0.55 * t) * L
            r1 = raio * (0.35 + 0.65 * M.curva("out", t)) * L
            w = max(2, int(espessura * (1 - t) + 2))
            d.line([(c + r0 * math.cos(a), c + r0 * math.sin(a)), (c + r1 * math.cos(a), c + r1 * math.sin(a))],
                   fill=cor + (255,), width=w)
        return im
    return M.Camada(nome, fonte, q0, fim or q0 + dur, ancora=(tam / 2, tam / 2), mundo=mundo, boil="ink",
                    sombra=(3, 6, 0.25), chaves={"x": k((q0, x, "segura")), "y": k((q0, y, "segura")),
                                                  "trim": k((q0, 0.0, "lin"), (q0 + dur, 1.0, "segura")),
                                                  "op": k((q0, 1.0, "lin"), (q0 + dur, 0.0, "segura"))})


def ondas(nome, x, y, q0, q1, raio=380, n=3, cor=PC.VERMELHO, mundo=True, espessura=10, periodo=12):
    """ondas de som: anéis que saem de um ponto, um a cada 'periodo' quadros, crescendo e sumindo"""
    tam = int(raio * 2 + 40)

    def fonte(fd, p):
        im = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        c = tam / 2
        for j in range(n):
            t = ((fd - q0) / periodo - j / n) % 1.0 if fd >= q0 + j * periodo / n else None
            if t is None:
                continue
            r = raio * (0.15 + 0.85 * M.curva("out", t))
            a = int(255 * (1 - t) * 0.9)
            d.arc([c - r, c - r, c + r, c + r], -70, 70, fill=cor + (a,), width=max(2, int(espessura * (1 - 0.6 * t))))
        return im
    return M.Camada(nome, fonte, q0, q1, ancora=(tam / 2, tam / 2), mundo=mundo, boil="ink", chaves={
        "x": k((q0, x, "segura")), "y": k((q0, y, "segura"))})


def letras(nome, texto, q0, x, y, corpo=150, cor=PC.TINTA, mundo=False, passo=2, espalha=600, semente=7,
           fim=10 ** 6, fonte_nome="ArchivoBlack-Regular.ttf", tracking=None):
    """palavra que se monta: cada letra vem de um ponto espalhado, girando, e encaixa (uma a cada 'passo' quadros).
    tracking=(q, px): a partir de q as letras se afastam px a mais (a abertura do título da Vox)"""
    fo = PC.fonte(fonte_nome, corpo)
    rng = np.random.default_rng(semente)
    larg = fo.getlength(texto)
    xc = x - larg / 2
    out = []
    j = 0
    for i, ch in enumerate(texto):
        w = fo.getlength(ch)
        if ch.strip():
            l, t, r, b = fo.getbbox(ch)
            im = Image.new("RGBA", (int(r - l + 24), int(b - t + 24)), (0, 0, 0, 0))
            ImageDraw.Draw(im).text((12 - l, 12 - t), ch, font=fo, fill=cor + (255,))
            fx = xc + l - 12 + im.width / 2
            fy = y + t - 12 + im.height / 2 - corpo * 0.6
            qa = q0 + j * passo
            ang = rng.uniform(0, 2 * math.pi)
            dx, dy = math.cos(ang) * espalha * rng.uniform(0.6, 1.0), math.sin(ang) * espalha * rng.uniform(0.6, 1.0)
            n = len(texto)
            off = (i - (n - 1) / 2) * tracking[1] / max(n - 1, 1) if tracking else 0
            xs = [(qa, fx + dx, "out"), (qa + 6, fx, "segura")]
            if tracking:
                xs += [(tracking[0], fx, "io"), (tracking[0] + 10, fx + off, "segura")]
            out.append(M.Camada(f"{nome}_{i}", im, qa, fim, mundo=mundo, boil="type", sombra=(4, 8, 0.25), chaves={
                "x": xs, "y": k((qa, fy + dy, "out"), (qa + 6, fy, "segura")),
                "rot": k((qa, rng.uniform(-120, 120), "out"), (qa + 6, rng.uniform(-3, 3), "segura")),
                "s": k((qa, 0.3, "out"), (qa + 6, 1.0, "segura")),
                "op": k((qa, 0.0, "lin"), (qa + 2, 1.0, "segura"))}))
            j += 1
        xc += w
    return out


def multiplica(nome, imagem, q0, centro, n=9, raio=(700, 900), passo=2, esc=(0.45, 0.7), semente=11, fim=10 ** 6,
               sombra=(8, 16, 0.28), boil="paper"):
    """cópias que se multiplicam em volta de um centro (quantidade, 'todo mundo'): pousam uma a cada 'passo'"""
    rng = np.random.default_rng(semente)
    out = []
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.25, 1.0)
        x, y = centro[0] + math.cos(a) * raio[0] * r, centro[1] + math.sin(a) * raio[1] * r
        out.append(cai(f"{nome}_{i}", imagem, q0 + i * passo, x, y, rot=rng.uniform(-14, 14), de_y=-120,
                       esc=rng.uniform(*esc), sombra=sombra, boil=boil, fim=fim))
    return out


def vira(nome, frente, verso, q0, x, y, rot=0.0, ini=0, fim=10 ** 6, esc_f=1.0, esc_v=1.0, sombra=(10, 22, 0.28)):
    """cartão que vira: a frente estreita até sumir (4 quadros) e o verso abre no mesmo lugar (4 quadros)"""
    a = M.Camada(nome + "_F", frente, ini, q0 + 4, boil="obj", sombra=sombra, chaves={
        "x": k((ini, x, "segura")), "y": k((ini, y, "segura")), "rot": k((ini, rot, "segura")),
        "s": k((ini, esc_f, "segura"), (q0, esc_f, "lin"), (q0 + 4, esc_f * 1.08, "segura")),
        "sx": k((ini, 1.0, "segura"), (q0, 1.0, "in"), (q0 + 4, 0.02, "segura"))})
    b = M.Camada(nome + "_V", verso, q0 + 4, fim, boil="obj", sombra=sombra, chaves={
        "x": k((q0 + 4, x, "segura")), "y": k((q0 + 4, y, "segura")), "rot": k((q0 + 4, rot, "segura")),
        "s": k((q0 + 4, esc_v * 1.08, "out"), (q0 + 10, esc_v, "segura")),
        "sx": k((q0 + 4, 0.02, "out"), (q0 + 8, 1.0, "segura"))})
    b.som = ("vira", q0 + 4)
    return [a, b]


def segue(nome, imagem, traco, q0, q1, desloc=(0, -60), vira_lado=True, fim=10 ** 6, rot=0.0, sombra=(14, 12, 0.28),
          esc=None, boil="obj"):
    """peça que viaja na ponta de um traço (vira de lado quando o traço vai para a esquerda); esc=(q, s) opcional"""
    xs, ys, sxs = [], [], []
    ant = traco.ponta(q0)
    for f in range(q0, q1 + 2, 2):
        px, py = traco.ponta(f)
        xs.append((f, px + desloc[0], "lin")); ys.append((f, py + desloc[1], "lin"))
        if vira_lado:
            sxs.append((f, -1.0 if px - ant[0] < -0.5 else 1.0, "segura"))
        ant = (px, py)
    ch = {"x": xs, "y": ys, "rot": k((q0, rot, "segura")), "op": k((q0, 0.0, "lin"), (q0 + 2, 1.0, "segura"))}
    if sxs:
        ch["sx"] = sxs
    if esc:
        ch["s"] = [tuple(e) for e in esc]
    return M.Camada(nome, imagem, q0, fim, boil=boil, sombra=sombra, chaves=ch)


def estilhaca(nome, imagem, centro, nx, ny, destinos, q0, passo=1, dur=10, fim=10 ** 6, semente=9, some=True,
              arco=(150, 320)):
    """a imagem se parte em nx×ny pedaços que voam em arco até os destinos (ciclando) e somem lá dentro"""
    rng = np.random.default_rng(semente)
    w, h = imagem.size
    out = []
    pw, ph = w / nx, h / ny
    i = 0
    for yy in range(ny):
        for xx in range(nx):
            pc = imagem.crop((int(xx * pw), int(yy * ph), int((xx + 1) * pw), int((yy + 1) * ph)))
            pc = PC.rasgar(pc, amp=4, passo=10, semente=semente + i)
            x0 = centro[0] - w / 2 + (xx + 0.5) * pw
            y0 = centro[1] - h / 2 + (yy + 0.5) * ph
            dx, dy = destinos[i % len(destinos)]
            qa = q0 + i * passo
            meio_y = min(y0, dy) - rng.uniform(*arco)
            ys = [(qa, y0, "out"), (qa + dur // 2, meio_y, "in"), (qa + dur, dy, "segura")]
            ch = {"x": k((qa, x0, "lin"), (qa + dur, dx, "segura")), "y": ys,
                  "rot": k((qa, 0.0, "lin"), (qa + dur, rng.uniform(-200, 200), "segura")),
                  "s": k((qa, 1.0, "lin"), (qa + dur, 0.35, "segura"))}
            if some:
                ch["op"] = k((qa, 1.0, "segura"), (qa + dur - 1, 1.0, "lin"), (qa + dur + 1, 0.0, "segura"))
            out.append(M.Camada(f"{nome}_{i}", pc, q0 - 1, fim if not some else qa + dur + 2, boil="paper",
                                sombra=(8, 12, 0.25), chaves=ch))
            i += 1
    return out


def flutua(camada, q0, q1, amp=(10, 8), rot=2.0, periodo=24, fase=0.0):
    """vida para um objeto parado: deriva lenta (no degrau de 12 qps) em vez de ficar congelado"""
    base_x = camada.chaves["x"][-1][1]
    base_y = camada.chaves["y"][-1][1]
    base_r = camada.chaves["rot"][-1][1] if camada.chaves.get("rot") else 0.0
    xs, ys, rs = [], [], []
    for f in range(q0, q1, 4):
        a = 2 * math.pi * (f - q0) / periodo + fase
        xs.append((f, base_x + amp[0] * math.sin(a), "io"))
        ys.append((f, base_y + amp[1] * math.sin(a * 0.7 + 1.1), "io"))
        rs.append((f, base_r + rot * math.sin(a * 0.5 + 0.4), "io"))
    camada.chaves["x"] = [c for c in camada.chaves["x"] if c[0] < q0] + xs
    camada.chaves["y"] = [c for c in camada.chaves["y"] if c[0] < q0] + ys
    camada.chaves["rot"] = [c for c in camada.chaves.get("rot", []) if c[0] < q0] + rs
    return camada



def papel_area(nome, caixa, cor=(32, 35, 33), semente=21, ini=0, fim=10 ** 6):
    """uma folha grande de papel (carvão por padrão) presa no mundo, por baixo de uma área: cada área tem a sua cor,
    e as transições (rasgo, íris) mostram cada lado com o seu fundo"""
    x0, y0, x1, y1 = caixa
    w, h = int(x1 - x0), int(y1 - y0)
    pg = PC.papel_mundo(w, h, tom=cor, textura=0.6, manchas=0.2).convert("RGBA")
    pg = PC.rasgar(pg, amp=26, passo=40, semente=semente)
    return M.Camada(nome, pg, ini, fim, boil=None, sombra=(10, 30, 0.35), chaves={
        "x": k((ini, (x0 + x1) / 2, "segura")), "y": k((ini, (y0 + y1) / 2, "segura")), "rot": k((ini, 0.6, "segura"))})
