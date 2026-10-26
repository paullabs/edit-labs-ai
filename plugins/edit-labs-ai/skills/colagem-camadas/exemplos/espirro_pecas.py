"""Peças do exemplo "E se você segurasse um espirro?" (cena_espirro.py).

Tudo aqui é papel e caneta, desenhado em código (nada baixado):
- o AR é um personagem: bolinhas de papel azul-claro com contorno de tinta (camada_bolhas, Trilha);
- a PRESSÃO é um manômetro de papel cuja agulha vem da chave "trim" (relogio_pressao);
- a mangueira dobra e a água (bolinhas) se acumula atrás da dobra (Mangueira, torneira);
- o lenço, o relógio das horas e as folhas de papel colorido de fundo de cada cena (folha_papel).
O cache fica em <trabalho>/espirro/papel/."""
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
import motor as M, pecas as PC, cena as C, camadas as K

ROOT = CM.TRABALHO / "espirro"                                    # pasta de trabalho do exemplo (fora do plugin)
PAP = ROOT / "papel"
AZUL = (198, 226, 242)
VERDE_MANG = (96, 150, 98)


def cache_png(nome, faz):
    PAP.mkdir(parents=True, exist_ok=True)
    out = PAP / f"{nome}.png"
    if not out.exists():
        im = faz()
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def cola(dest, sprite, x, y):
    """alpha_composite com recorte nas bordas (x, y = canto de cima à esquerda do sprite)"""
    x, y = int(round(x)), int(round(y))
    sx0, sy0 = max(0, -x), max(0, -y)
    sx1, sy1 = min(sprite.width, dest.width - x), min(sprite.height, dest.height - y)
    if sx1 <= sx0 or sy1 <= sy0:
        return
    dest.alpha_composite(sprite.crop((sx0, sy0, sx1, sy1)), (x + sx0, y + sy0))


# ------------------------------------------------------------------ o ar: bolinhas de papel
def sprite_bolha(r):
    """bolinha de papel azul-claro com contorno de tinta e um reflexo; r em px"""
    S = 3
    pad = 5
    d = int(2 * r + 2 * pad)
    im = Image.new("RGBA", (d * S, d * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    c = d * S / 2
    rr = r * S
    dr.ellipse([c - rr, c - rr, c + rr, c + rr], fill=AZUL + (238,), outline=PC.TINTA + (255,),
               width=max(2, int(rr * 0.12)))
    hr = rr * 0.62
    dr.arc([c - hr, c - hr, c + hr, c + hr], 200, 268, fill=(255, 255, 255, 255), width=max(2, int(rr * 0.10)))
    dr.arc([c - rr * 0.84, c - rr * 0.84, c + rr * 0.84, c + rr * 0.84], 20, 70, fill=(150, 190, 215, 200),
           width=max(2, int(rr * 0.07)))
    return im.resize((d, d), Image.LANCZOS)


class Trilha:
    """caminho por pontos do mundo; em(s) = o ponto a s px do começo"""

    def __init__(self, pts, suave=True):
        p = np.array(pts, np.float32)
        if suave and len(p) > 2:
            p = C._catmull(p, 14)
        self.p = p
        seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
        self.acum = np.concatenate([[0], np.cumsum(seg)])
        self.L = float(self.acum[-1])

    def _i(self, s):
        s = min(max(s, 0.0), self.L)
        i = min(int(np.searchsorted(self.acum, s, side="right") - 1), len(self.p) - 2)
        u = (s - self.acum[i]) / max(self.acum[i + 1] - self.acum[i], 1e-6)
        return i, u

    def em(self, s):
        i, u = self._i(s)
        return tuple(self.p[i] + (self.p[i + 1] - self.p[i]) * u)

    def corta(self, s_fim):
        """a mesma trilha, só até s_fim px do começo"""
        s_fim = min(max(s_fim, 1.0), self.L)
        i, u = self._i(s_fim)
        pts = [tuple(p) for p in self.p[: i + 1]] + [self.em(s_fim)]
        return Trilha(pts, suave=False)

    def normal(self, s):
        i, _ = self._i(s)
        t = self.p[i + 1] - self.p[i]
        t = t / max(np.linalg.norm(t), 1e-6)
        return (-t[1], t[0])


def camada_bolhas(nome, specs, caixa, q0, q1, boil="paper", sombra=None):
    """camada com várias bolinhas; cada spec: dict(t0, t1, trilha, r, curva='lin', amp=0, ciclos=2, fase=0, fim=None,
    some=4). A bolinha anda pela trilha de t0 a t1; fica visível até 'fim' (padrão: some ao chegar, em 'some' quadros)"""
    x0, y0, x1, y1 = [int(v) for v in caixa]
    w, h = x1 - x0, y1 - y0
    sprites, cache = {}, {}

    def spr(r):
        k = int(round(r))
        if k not in sprites:
            sprites[k] = sprite_bolha(max(k, 3))
        return sprites[k]

    def fonte(fd, p):
        k = int(fd) // 2
        if k in cache:
            return cache[k]
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for sp in specs:
            t0, t1 = sp["t0"], sp["t1"]
            fim = sp.get("fim")
            fim = t1 + sp.get("some", 4) if fim is None else fim
            if fd < t0 or fd >= fim:
                continue
            u = min(max((fd - t0) / max(t1 - t0, 1), 0.0), 1.0)
            u = M.curva(sp.get("curva", "lin"), u)
            s = u * sp["trilha"].L
            x, y = sp["trilha"].em(s)
            amp = sp.get("amp", 0)
            if amp:
                nx, ny = sp["trilha"].normal(s)
                off = amp * math.sin(2 * math.pi * u * sp.get("ciclos", 2) + sp.get("fase", 0))
                x, y = x + nx * off, y + ny * off
            r = sp["r"] * min(1.0, (fd - t0 + 2) / 5.0) * (1.0 + (sp.get("cresce", 1.0) - 1.0) * u)
            if sp.get("encolhe") and sp.get("fim") is not None and fd > fim - sp["encolhe"]:
                r *= max(0.0, (fim - fd) / sp["encolhe"])
            if fd > t1:
                r *= max(0.0, 1.0 - (fd - t1) / max(sp.get("some", 4), 1)) if sp.get("fim") is None else 1.0
            if r < 3:
                continue
            s_ = spr(r)
            cola(im, s_, x - x0 - s_.width / 2, y - y0 - s_.height / 2)
        cache[k] = im
        return im
    fonte.tam = (w, h)
    L = M.Camada(nome, fonte, q0, q1, ancora=(0, 0), boil=boil, sombra=sombra,
                 chaves={"x": C.k((q0, x0, "segura")), "y": C.k((q0, y0, "segura"))})
    L.tam = (w, h)
    return L


# ------------------------------------------------------------------ a pressão: um manômetro de papel
def relogio_pressao(tam=330, rotulo=True):
    """manômetro: a agulha vai de 0 (embaixo à esquerda) a 1 (embaixo à direita) pela chave 'trim' da camada; verde,
    amarelo e vermelho no mostrador. Fonte: fonte(fd, p) → PIL, com .tam"""
    pad = 18
    T = tam + 2 * pad
    S = 2
    cache = {}
    ang = lambda v: 135 + 270 * v

    def fonte(fd, p):
        v = round(min(max(p["trim"], 0.0), 1.0), 2)
        if v in cache:
            return cache[v]
        R = tam / 2 * S
        c = T * S / 2
        im = Image.new("RGBA", (T * S, T * S), (0, 0, 0, 0))
        face = PC.textura_papel(T * S, T * S, (247, 241, 226), 17)
        m = Image.new("L", (T * S, T * S), 0)
        ImageDraw.Draw(m).ellipse([c - R, c - R, c + R, c + R], fill=255)
        face.putalpha(m)
        im.alpha_composite(face)
        d = ImageDraw.Draw(im)
        d.ellipse([c - R, c - R, c + R, c + R], outline=PC.TINTA + (255,), width=int(R * 0.06))
        ra = R * 0.80
        for a0, a1, cor in ((0.0, 0.55, (116, 166, 92)), (0.55, 0.80, (232, 190, 62)), (0.80, 1.0, PC.VERMELHO)):
            d.arc([c - ra, c - ra, c + ra, c + ra], ang(a0), ang(a1), fill=cor + (255,), width=int(R * 0.13))
        for i in range(11):
            a = math.radians(ang(i / 10))
            r1, r2 = R * 0.64, R * 0.56
            d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
                   fill=PC.TINTA + (255,), width=max(3, int(R * 0.025)))
        if rotulo:
            fo = PC.fonte("ArchivoBlack-Regular.ttf", int(R * 0.17))
            d.text((c, c + R * 0.40), "PRESSÃO", font=fo, fill=PC.TINTA + (255,), anchor="mm")
        a = math.radians(ang(v))
        tip = (c + R * 0.70 * math.cos(a), c + R * 0.70 * math.sin(a))
        tail = (c - R * 0.14 * math.cos(a), c - R * 0.14 * math.sin(a))
        nx, ny = -math.sin(a), math.cos(a)
        wd = R * 0.035
        d.polygon([(tip[0], tip[1]), (c + nx * wd, c + ny * wd), (tail[0], tail[1]), (c - nx * wd, c - ny * wd)],
                  fill=PC.VERMELHO + (255,), outline=PC.TINTA + (255,))
        d.ellipse([c - R * 0.07, c - R * 0.07, c + R * 0.07, c + R * 0.07], fill=PC.TINTA + (255,))
        out = im.resize((T, T), Image.LANCZOS)
        cache[v] = out
        return out
    fonte.tam = (T, T)
    return fonte


# ------------------------------------------------------------------ a mangueira que dobra
class Mangueira:
    """mangueira de papel em serpentina (retrato 9:16), com a água (bolinhas) correndo; no quadro q_dobra ela dobra num
    'V' (em 2 degraus) e a água se acumula atrás da dobra, enquanto o que já passou termina de sair.
    .camada → a Camada; .ponto_dobra → o ápice da dobra no mundo; .boca → a ponta aberta; .inicio → onde a água entra.
    A água já corre quando a cena começa (a simulação parte 80 quadros antes de q0)."""

    PRE0 = [(0, 120), (300, 70), (640, 130), (880, 300), (800, 460), (660, 520)]      # até o começo da dobra (E)
    POS0 = [(420, 520), (210, 570), (110, 760), (260, 910), (560, 960), (830, 1070), (940, 1250)]   # depois dela (X)

    def __init__(self, nome, origem, q0, q_dobra, q1, v=21.0, passo_spawn=3, r=29, esc=0.85, dx=255):
        self.ox, self.oy = origem
        self.esc = esc
        self.LARG = 90
        self.PRE = [(x * esc + dx, y * esc) for x, y in self.PRE0]
        self.POS = [(x * esc + dx, y * esc) for x, y in self.POS0]
        self.qd, self.v, self.r = q_dobra, v, r
        todos = self.PRE + self.POS
        xs, ys = [p[0] for p in todos], [p[1] for p in todos]
        self.regiao = (int(self.ox + min(xs) - 120), int(self.oy + min(ys) - 260), int(self.ox + max(xs) + 120),
                       int(self.oy + max(ys) + 120))
        w, h = self.regiao[2] - self.regiao[0], self.regiao[3] - self.regiao[1]
        self.q_sim = q0 - 90
        self.spawn = list(range(self.q_sim, q1, passo_spawn))
        self.trilhas, self.cache = {}, {}
        ta, tb = self._trilha(0.0), self._trilha(1.0)
        self.La, self.Lb = ta.L, tb.L
        self.s_ent = float(ta.acum[len(C._catmull(np.array(self.PRE, np.float32), 14)) - 1])
        self.s_sai = float(ta.acum[len(C._catmull(np.array(self.PRE, np.float32), 14)) + 1])
        self.npre = len(C._catmull(np.array(self.PRE, np.float32), 14))
        j = self.npre + 1                                      # o ápice é o 2º ponto do trecho dobrado
        self.s_apice = float(tb.acum[j])
        self.ponto_dobra = (self.ox + float(tb.p[j][0]), self.oy + float(tb.p[j][1]))
        self.boca = (self.ox + self.POS[-1][0], self.oy + self.POS[-1][1])
        self.inicio = (self.ox + self.PRE[0][0], self.oy + self.PRE[0][1])

        def fonte(fd, p):
            return self._quadro(fd)
        fonte.tam = (w, h)
        self.camada = M.Camada(nome, fonte, q0, q1, ancora=(0, 0), boil="paper", sombra=(8, 16, 0.26),
                               chaves={"x": C.k((q0, self.regiao[0], "segura")), "y": C.k((q0, self.regiao[1], "segura"))})
        self.camada.tam = (w, h)

    def _trilha(self, a):
        """trilha local; a = quanto a dobra já subiu (0 = reta, 1 = V completo). Antes e depois da dobra é curva suave"""
        a = round(a, 2)
        if a in self.trilhas:
            return self.trilhas[a]
        pre = C._catmull(np.array(self.PRE, np.float32), 14)
        pos = C._catmull(np.array(self.POS, np.float32), 14)
        E, X = np.array(self.PRE[-1], np.float32), np.array(self.POS[0], np.float32)
        Mm = (E + X) / 2
        d = (X - E) / np.linalg.norm(X - E)
        n = np.array([d[1], -d[0]], np.float32)
        if n[1] > 0:
            n = -n
        if a > 0:
            e = self.esc
            meio = np.array([E + 0.30 * (X - E) + n * 70 * a * e, Mm + n * 150 * a * e, E + 0.70 * (X - E) + n * 70 * a * e],
                            np.float32)
        else:
            meio = np.array([Mm], np.float32)
        t = Trilha(np.vstack([pre, meio, pos]), suave=False)
        self.trilhas[a] = t
        return t

    def _largura(self, a, s, apice):
        if a <= 0:
            return self.LARG
        d = s - apice
        w = self.LARG
        if abs(d) < 80:
            w = self.LARG * (0.20 + 0.80 * (abs(d) / 80) ** 1.4)
        if -400 < d < -80:                                    # a pressão incha a mangueira antes da dobra
            x = (d + 240) / 160.0
            w = self.LARG * (1.0 + 0.24 * a * max(0.0, 1 - x * x))
        return w

    def _tubo(self, im, tr, a, dx, dy):
        dr = ImageDraw.Draw(im, "RGBA")
        n = int(tr.L // 6)
        apice = float(tr.acum[self.npre + 1]) if a > 0 else 0.0
        pts = [tr.em(i * 6.0) for i in range(n + 1)]
        ws = [self._largura(a, i * 6.0, apice) for i in range(n + 1)]
        nors = [tr.normal(i * 6.0) for i in range(n + 1)]

        def faixa(esc, cor, off=(0, 0)):
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[i + 1]
                n0, n1 = nors[i], nors[i + 1]
                w0, w1 = ws[i] * esc / 2, ws[i + 1] * esc / 2
                quad = [(x0 + n0[0] * w0 + off[0] + dx, y0 + n0[1] * w0 + off[1] + dy),
                        (x1 + n1[0] * w1 + off[0] + dx, y1 + n1[1] * w1 + off[1] + dy),
                        (x1 - n1[0] * w1 + off[0] + dx, y1 - n1[1] * w1 + off[1] + dy),
                        (x0 - n0[0] * w0 + off[0] + dx, y0 - n0[1] * w0 + off[1] + dy)]
                dr.polygon(quad, fill=cor)
        faixa(1.20, PC.TINTA + (255,))
        faixa(1.0, VERDE_MANG + (255,))
        faixa(0.26, (150, 200, 150, 255), off=(-9, -12))
        for i in range(0, n, 6):                              # os anéis da mangueira
            (x, y), (nx, ny) = pts[i], nors[i]
            w = ws[i] / 2 * 0.95
            dr.line([(x + nx * w + dx, y + ny * w + dy), (x - nx * w + dx, y - ny * w + dy)], fill=(60, 100, 64, 150),
                    width=3)

    def _bolinhas(self, k):
        """s (px ao longo da mangueira reta) de cada bolinha no degrau k, simulado desde q_sim"""
        bs, n_sp = [], 0
        s_stop = self.s_ent + 0.40 * (self.s_sai - self.s_ent)
        for kk in range(self.q_sim // 2, k + 1):
            f = kk * 2
            while n_sp < len(self.spawn) and self.spawn[n_sp] <= f:
                bs.append({"s": 0.0, "parou": False})
                n_sp += 1
            dobrada = f >= self.qd + 2
            fila = 0
            for b in sorted(bs, key=lambda b: -b["s"]):
                if b["parou"]:
                    fila += 1
                    continue
                novo = b["s"] + self.v * 2
                if dobrada and b["s"] <= s_stop:
                    lim = s_stop - 1.2 * self.r - fila * 1.95 * self.r
                    if novo >= lim:
                        novo, b["parou"] = max(b["s"], lim), True
                        fila += 1
                b["s"] = novo
            bs = [b for b in bs if b["s"] < self.La - 4]
        return [b["s"] for b in bs]

    def _quadro(self, fd):
        k = int(fd) // 2
        if k in self.cache:
            return self.cache[k]
        w, h = self.regiao[2] - self.regiao[0], self.regiao[3] - self.regiao[1]
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dx, dy = self.ox - self.regiao[0], self.oy - self.regiao[1]
        a = 0.0 if fd < self.qd else (0.5 if fd < self.qd + 2 else 1.0)
        tr = self._trilha(a)
        self._tubo(im, tr, a, dx, dy)
        spr = sprite_bolha(self.r)
        spr_pressao = sprite_bolha(self.r * 1.12)
        s_stop = self.s_ent + 0.40 * (self.s_sai - self.s_ent)
        for s in self._bolinhas(k):
            sp_ = spr_pressao if (a > 0 and s > s_stop - 12 * self.r and s <= s_stop) else spr
            sb = s
            if a > 0:                                         # a mesma bolinha, medida agora ao longo da trilha dobrada
                t = min(max((s - self.s_ent) / (self.s_sai - self.s_ent), 0.0), 1.0)
                sb = s + (tr.L - self.La) * t
            x, y = tr.em(min(sb, tr.L))
            cola(im, sp_, x + dx - sp_.width / 2, y + dy - sp_.height / 2)
        self.cache[k] = im
        return im


# ------------------------------------------------------------------ a torneira
def torneira():
    """torneira de papel (o cano, a base e o volante vermelho) – a boca fica no lado direito"""
    im = Image.new("RGBA", (520, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cinza, escuro = (176, 178, 176, 255), PC.TINTA + (255,)
    d.rounded_rectangle([90, 220, 470, 300], radius=26, fill=cinza, outline=escuro, width=8)      # o cano
    d.rounded_rectangle([60, 200, 110, 320], radius=14, fill=(150, 152, 150, 255), outline=escuro, width=8)
    d.rounded_rectangle([390, 206, 440, 314], radius=14, fill=(150, 152, 150, 255), outline=escuro, width=8)   # a boca
    d.rounded_rectangle([240, 130, 300, 226], radius=12, fill=cinza, outline=escuro, width=8)       # o pescoço
    d.rounded_rectangle([200, 110, 340, 150], radius=16, fill=(150, 152, 150, 255), outline=escuro, width=8)
    d.rounded_rectangle([140, 60, 400, 104], radius=20, fill=PC.VERMELHO + (255,), outline=escuro, width=8)   # o volante
    d.ellipse([255, 96, 285, 126], fill=cinza, outline=escuro, width=6)
    d.arc([300, 322, 420, 380], 0, 180, fill=(120, 170, 200, 255), width=8)
    return im


# ------------------------------------------------------------------ lenço e cotovelo
def lenco(larg=470, semente=4):
    def faz():
        S = 2
        w, h = larg * S, int(larg * 0.78) * S
        pad = 30 * S
        rng = np.random.default_rng(semente)
        pts = []
        N = 24
        for i in range(N + 1):
            x = pad + (w - 2 * pad) * i / N
            pts.append((x, pad + 10 * math.sin(i * 0.9 + 0.4) + rng.normal(0, 2.5)))
        for i in range(N + 1):
            y = pad + (h - 2 * pad) * i / N
            pts.append((w - pad + 9 * math.sin(i * 0.8) + rng.normal(0, 2.5), y))
        for i in range(N + 1):
            x = w - pad - (w - 2 * pad) * i / N
            pts.append((x, h - pad + 10 * math.sin(i * 0.7 + 1.1) + rng.normal(0, 2.5)))
        for i in range(N + 1):
            y = h - pad - (h - 2 * pad) * i / N
            pts.append((pad + 9 * math.sin(i * 0.95 + 2.0) + rng.normal(0, 2.5), y))
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tex = PC.textura_papel(w, h, (250, 247, 238), semente, forca=0.45)
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        tex.putalpha(m)
        im.alpha_composite(tex)
        d = ImageDraw.Draw(im)
        # as dobras (vincos) e a listra azul perto da borda, como num lenço de tecido
        for fx in (0.5,):
            d.line([(pad + (w - 2 * pad) * fx, pad + 16), (pad + (w - 2 * pad) * fx, h - pad - 16)], fill=(205, 200, 188, 255),
                   width=5)
        d.line([(pad + 16, h / 2), (w - pad - 16, h / 2)], fill=(205, 200, 188, 255), width=5)
        for off in (46, 62):
            d.rectangle([pad + off, pad + off, w - pad - off, h - pad - off], outline=(120, 150, 200, 255), width=4)
        d.line(pts + [pts[0]], fill=PC.TINTA + (255,), width=7, joint="curve")
        return im.resize((w // S, h // S), Image.LANCZOS)
    return cache_png(f"lenco_{larg}", faz)


# ------------------------------------------------------------------ etiquetas
def relogio_horas(tam=300):
    """relógio de papel: 'trim' 0..1 → o ponteiro dos minutos dá 4 voltas e o das horas, 1/3 de volta (as horas passam)"""
    pad = 14
    T = tam + 2 * pad
    S = 2
    cache = {}

    def fonte(fd, p):
        v = round(min(max(p["trim"], 0.0), 1.0), 2)
        if v in cache:
            return cache[v]
        R = tam / 2 * S
        c = T * S / 2
        im = Image.new("RGBA", (T * S, T * S), (0, 0, 0, 0))
        face = PC.textura_papel(T * S, T * S, (247, 241, 226), 23)
        m = Image.new("L", (T * S, T * S), 0)
        ImageDraw.Draw(m).ellipse([c - R, c - R, c + R, c + R], fill=255)
        face.putalpha(m)
        im.alpha_composite(face)
        d = ImageDraw.Draw(im)
        d.ellipse([c - R, c - R, c + R, c + R], outline=PC.TINTA + (255,), width=int(R * 0.07))
        for i in range(12):
            a = math.radians(i * 30 - 90)
            r1, r2 = R * 0.86, R * (0.70 if i % 3 == 0 else 0.78)
            d.line([(c + r1 * math.cos(a), c + r1 * math.sin(a)), (c + r2 * math.cos(a), c + r2 * math.sin(a))],
                   fill=PC.TINTA + (255,), width=max(3, int(R * (0.045 if i % 3 == 0 else 0.025))))
        for frac, comp, esp, cor in ((v * 4, 0.78, 0.035, PC.TINTA), (v / 3, 0.52, 0.055, PC.VERMELHO)):
            a = math.radians(frac * 360 - 90)
            tip = (c + R * comp * math.cos(a), c + R * comp * math.sin(a))
            tail = (c - R * 0.12 * math.cos(a), c - R * 0.12 * math.sin(a))
            nx, ny = -math.sin(a), math.cos(a)
            wd = R * esp
            d.polygon([tip, (c + nx * wd, c + ny * wd), tail, (c - nx * wd, c - ny * wd)], fill=cor + (255,))
        d.ellipse([c - R * 0.07, c - R * 0.07, c + R * 0.07, c + R * 0.07], fill=PC.TINTA + (255,))
        out = im.resize((T, T), Image.LANCZOS)
        cache[v] = out
        return out
    fonte.tam = (T, T)
    return fonte


# ------------------------------------------------------------------ v2: assuntos novos (a "reunião", a cama, os pictogramas)
def folha_papel(nome, centro, tam, cor, ini, fim, semente=5, esc=1.5):
    """uma folha grande de papel de OUTRA COR presa no mundo, por baixo de uma cena (cada assunto tem o seu papel).
    Feita em resolução menor e escalada (esc) para não pesar na memória."""
    w0, h0 = int(tam[0] / esc), int(tam[1] / esc)
    pg = PC.papel_mundo(w0, h0, tom=cor, textura=0.7, manchas=0.25).convert("RGBA")
    pg = PC.rasgar(pg, amp=18, passo=40, semente=semente)
    return M.Camada(nome, pg, ini, fim, boil=None, sombra=(10, 30, 0.35), chaves={
        "x": C.k((ini, centro[0], "segura")), "y": C.k((ini, centro[1], "segura")), "s": C.k((ini, esc, "segura")),
        "rot": C.k((ini, 0.5, "segura"))})


PELES = [(236, 208, 178), (198, 150, 112), (152, 106, 74), (242, 216, 192), (216, 172, 132), (180, 130, 94)]
TERNOS = [(88, 112, 152), (202, 162, 72), (130, 56, 64), (72, 112, 90), (72, 72, 80), (62, 132, 142)]
FUNDOS = [(214, 226, 236), (240, 226, 196), (232, 208, 206), (206, 228, 214), (226, 216, 236), (238, 232, 206)]

