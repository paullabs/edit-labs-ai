#!/usr/bin/env python3
"""
voxlab — motor de composicao da identidade MOTION-VOX para motion sobre footage.

Principio: tudo que precisa ser ANIMADO e procedural e aceita `progress` (0..1).
Assim o estado MID de uma cena e renderizavel sem regerar imagem.

Camadas de um frame, de baixo para cima:
    BG_PAPER -> CTX_PAPERS -> HERO -> LABEL -> ANNOTATION -> PROP_FOREGROUND -> FINISH
"""
import math
import os
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageEnhance

# Quadro. Vertical e o padrao da identidade; MV_CANVAS=H escolhe o horizontal (1920x1080) no
# PROCESSO inteiro (kit, legenda e aferidor leem daqui). Cada render roda num processo so.
ORIENT = "H" if os.environ.get("MV_CANVAS", "V").strip().upper() == "H" else "V"
W, H = (1920, 1080) if ORIENT == "H" else (1080, 1920)

# ---------------------------------------------------------------- paleta
PAPER      = (217, 216, 209)
PAPER_LIGHT= (244, 240, 232)
INK        = ( 55,  54,  57)
CHARCOAL   = ( 41,  41,  43)
YELLOW     = (219, 214,  83)
BLUE       = ( 46, 130, 247)
RED        = (201,  72,  80)
TAPE       = (191, 187, 174)

# ---------------------------------------------------------------- fontes
# ---------------------------------------------------------------- fontes
# A identidade MOTION-VOX viaja com as fontes. As do macOS (DIN Condensed, Bradley Hand,
# Helvetica Neue) NAO podem ser redistribuidas, entao a identidade estaria presa a uma
# maquina. Estas cinco sao de licenca livre e sao as alternativas que a propria Style
# Bible §5 nomeia para cada funcao. Ficam em `fontes/`, ao lado da lib.
def _fontes_dir():
    here = Path(__file__).resolve().parent
    for c in (here / "fontes", here.parent / "fontes", here.parent / "lib" / "fontes"):
        if c.is_dir():
            return c
    raise FileNotFoundError(
        "Pasta `fontes/` nao encontrada. Copie-a da skill para junto de voxlab.py — "
        "a identidade MOTION-VOX depende dela.")


_FD = _fontes_dir()
F_COND   = str(_FD / "ArchivoNarrow[wght].ttf")              # manchete condensada
F_MARKER = str(_FD / "PermanentMarker-Regular.ttf")          # etiqueta manual
F_MONO   = str(_FD / "IBMPlexMono-Medium.ttf")               # legenda tecnica
F_SERIF  = str(_FD / "Fraunces[SOFT,WONK,opsz,wght].ttf")    # numero editorial
F_SANS   = str(_FD / "Inter[opsz,wght].ttf")                 # legenda falada
F_ITAL   = str(_FD / "Fraunces-Italic[SOFT,WONK,opsz,wght].ttf")  # serifa italica
# Tipografia da frase de impacto, tirada das referencias: um grotesco BLACK carrega a
# palavra-chave (mais encorpado que Inter 700) e uma serifa italica de alto contraste
# faz o contraponto. Inter fica para a linha de apoio.
F_BLACK  = str(_FD / "ArchivoBlack-Regular.ttf")
F_PLAY   = str(_FD / "PlayfairDisplay-Italic[wght].ttf")

# Fontes variaveis precisam do eixo travado, senao o PIL usa a instancia padrao —
# Archivo Narrow abriria em Regular onde a identidade pede peso 700.
_AXES = {F_COND: {"Weight": 700}, F_SERIF: {"Weight": 800}, F_SANS: {"Weight": 700},
         F_ITAL: {"Weight": 600, "Wonky": 1}, F_PLAY: {"Weight": 700}}


_font_cache = {}


def font(path, size):
    key = (str(path), size)
    if key in _font_cache:
        return _font_cache[key]
    try:
        f = ImageFont.truetype(str(path), size)
    except OSError:
        f = ImageFont.truetype(str(path), size, index=0)
    want = _AXES.get(str(path))
    if want:
        try:
            axes = f.get_variation_axes()
            vals = []
            for ax in axes:
                nm = ax["name"]
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                vals.append(float(want.get(nm, ax["default"])))
            f.set_variation_by_axes(vals)
        except Exception:
            pass
    _font_cache[key] = f
    return f


# ---------------------------------------------------------------- utilitarios de traco
def _walk(n, amp, seed, corr=26):
    """
    Ruido suave de media zero, ancorado nas duas pontas.
    `corr` = comprimento de correlacao em pontos. O ruido e sorteado numa grade grossa
    e interpolado: da ondulacao de caneta, nao chiado. Sem isso o traco vira corrente
    de contas, o que salta aos olhos numa linha longa como a azul de continuidade.
    """
    n = max(int(n), 2)
    k = max(3, n // max(1, int(corr)))
    rng = np.random.default_rng(seed)
    v = np.cumsum(rng.normal(0, 1, k))
    v -= np.linspace(v[0], v[-1], k)
    m = np.abs(v).max()
    v = (v / m * amp) if m > 0 else v
    return np.interp(np.linspace(0, k - 1, n), np.arange(k), v)


def rotate_anchor(old_size, new_size, angle, pt):
    """
    Onde um ponto do bitmap original vai parar depois de Image.rotate(angle, expand=True).
    Verificado empiricamente contra o PIL (erro < 1px).
    Sem isso, qualquer anotacao ancorada num objeto rotacionado cai no lugar errado —
    o circulo anotado num relogio vai parar no centro do mostrador.
    """
    t = math.radians(angle)
    cx, cy = old_size[0] / 2, old_size[1] / 2
    nx, ny = new_size[0] / 2, new_size[1] / 2
    dx, dy = pt[0] - cx, pt[1] - cy
    return (math.cos(t) * dx + math.sin(t) * dy + nx,
            -math.sin(t) * dx + math.cos(t) * dy + ny)


def smooth_path(pts, samples=18):
    """
    Catmull-Rom: transforma uma polilinha de controle em curva.
    Seta desenhada a mao nao tem quina; sem isso o traco sai em ziguezague.
    """
    if len(pts) < 3:
        return list(pts)
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(len(p) - 3):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        for j in range(samples):
            t = j / samples
            t2, t3 = t * t, t * t * t
            out.append((
                0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
                0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)))
    out.append(pts[-1])
    return out


def jitter(pts, amp=3.0, seed=0):
    n = len(pts)
    jx, jy = _walk(n, amp, seed), _walk(n, amp, seed + 991)
    return [(p[0] + jx[i], p[1] + jy[i]) for i, p in enumerate(pts)]


def stroke(draw, pts, width=5, color=INK + (255,), pressure=0.30, seed=0):
    """Traco com variacao de pressao e juntas redondas. Nao e vetor perfeito."""
    if len(pts) < 2:
        return
    rng = np.random.default_rng(seed)
    phase = rng.uniform(0, 6.28)
    for i in range(len(pts) - 1):
        w = width * (1.0 + pressure * math.sin(i * 0.22 + phase))
        w = max(1.0, w)
        draw.line([pts[i], pts[i + 1]], fill=color, width=int(round(w)))
        r = w / 2.0
        x, y = pts[i]
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color)
    x, y = pts[-1]
    r = width / 2.0
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


def cut(pts, progress):
    """Trunca um caminho em `progress` do comprimento total (traco sendo desenhado)."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0:
        return []
    if progress >= 1:
        return pts
    d = [0.0]
    for i in range(1, len(pts)):
        d.append(d[-1] + math.dist(pts[i - 1], pts[i]))
    target = d[-1] * progress
    out = [pts[0]]
    for i in range(1, len(pts)):
        if d[i] <= target:
            out.append(pts[i])
        else:
            seg = d[i] - d[i - 1]
            t = (target - d[i - 1]) / seg if seg else 0
            out.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * t,
                        pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * t))
            break
    return out


# ---------------------------------------------------------------- anotacoes
def hand_circle(size, cx, cy, rx, ry, progress=1.0, passes=2, width=6,
                color=INK, seed=1, amp=6.0):
    """Circulo manual de 2-3 passadas, cada uma com centro e raio ligeiramente diferentes."""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    per = 1.0 / passes
    for p in range(passes):
        lo, hi = p * per, (p + 1) * per
        local = (progress - lo) / per
        if local <= 0:
            break
        local = min(1.0, local)
        ox, oy = rng.uniform(-5, 5), rng.uniform(-5, 5)
        sx, sy = rng.uniform(0.97, 1.04), rng.uniform(0.97, 1.04)
        start = rng.uniform(-0.6, 0.6) + p * 0.7
        n = 220
        pts = [(cx + ox + rx * sx * math.cos(start + 2 * math.pi * i / n),
                cy + oy + ry * sy * math.sin(start + 2 * math.pi * i / n))
               for i in range(n + 1)]
        pts = jitter(pts, amp, seed + p * 17)
        stroke(d, cut(pts, local), width, color + (255,), seed=seed + p)
    return _auto_boil(lay, "ink")


def _limb(anchor, deg1, len1, deg2, len2, facing):
    """Dois segmentos a partir de `anchor` (ombro/quadril). Convencao de angulo: 0 =
    para baixo, 90 = para a frente (na direcao de `facing`), negativo = para tras.
    `deg2` e o angulo do SEGUNDO segmento RELATIVO ao primeiro (cotovelo/joelho)."""
    a1 = math.radians(deg1)
    p1 = (anchor[0] + facing * math.sin(a1) * len1, anchor[1] + math.cos(a1) * len1)
    a2 = math.radians(deg1 + deg2)
    p2 = (p1[0] + facing * math.sin(a2) * len2, p1[1] + math.cos(a2) * len2)
    return [anchor, p1, p2]


_POSES = {
    # cada pose: (hip_L, knee_L, hip_R, knee_R, sh_L, elbow_L, sh_R, elbow_R)
    # graus na convencao de _limb: 0=para baixo, 90=na direcao de `facing` (frente),
    # negativo=para tras — a MESMA direcao pros dois lados (perfil, nao espelhado).
    # R e o lado "ativo" (o que aponta/segura/empurra).
    "stand":  (7, -4, -5, 3, 8, -4, -10, 6),
    "sit":    (76, -82, 80, -86, 14, -8, -10, 8),
    "walk":   (34, -12, -32, -16, -28, 12, 32, -14),
    "point":  (7, -4, -5, 3, 8, -4, None, 10),   # sh_R sobrescrito por arm_deg
    "reject": (7, -4, -5, 3, 62, 18, 68, 16),
}


def persona(size, cx, cy, height=320, pose="stand", progress=1.0, color=INK, seed=50,
           facing=1, arm_deg=None, width=8, amp=4.0):
    """
    Personagem de papel: pictograma de tinta (cabeca, tronco, dois bracos, duas
    pernas), na MESMA familia de `hand_circle`/`hand_arrow` — traco de marcador,
    jitter, boil "ink". Nunca IA desenhando gente: e a mesma mao que desenha o
    circulo e a seta, agora desenhando uma pessoa. Resolve de saida a regra de nunca
    gerar rosto sintetico de gente real — a figura e deliberadamente abstrata.

    `pose`: stand | sit | walk | point | reject. `arm_deg` sobrescreve o angulo do
    ombro do braco ATIVO (o direito, lado de `facing`) — 0=para baixo, 90=para a
    frente (horizontal), 180=para cima, -90=para tras — para apontar ou segurar um
    objeto herdado com precisao (aponte para a posicao real do objeto/anotacao na
    cena: `math.degrees(math.atan2(facing*(alvo_x-ombro_x), alvo_y-ombro_y))`).
    `facing`: 1 olha/aponta para a direita, -1 para a esquerda.

    Progresso revela em ordem — cabeca, tronco, pernas, bracos — a ordem em que uma
    mao desenharia. Devolve (camada, juntas): `juntas["hand_r"]`/`["hand_l"]` sao as
    posicoes das maos, para prender um objeto herdado exatamente ali.
    """
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    h = height
    hr = h * 0.115
    head_c = (cx, cy - h * 0.5 + hr)
    neck_y = head_c[1] + hr
    sh_y = neck_y + h * 0.03
    hip_y = neck_y + h * 0.34
    sh_dx = h * 0.10
    # quadril mais aberto sentado — senao as duas coxas quase se sobrepoe e a pose
    # nao le como pose nenhuma, so um borrao de tinta. Andando e o oposto: e perfil,
    # os dois quadris sao quase o MESMO ponto (so a fase da passada os diferencia) —
    # com hip_dx normal, uma perna nasce a esquerda girando pra frente e a outra
    # nasce a direita girando pra tras, e elas se CRUZAM em X debaixo do tronco.
    hip_dx = h * (0.14 if pose == "sit" else 0.018 if pose == "walk" else 0.075)
    leg_len, arm_len = (h * 0.5 - hip_y + cy) * 0.5, h * 0.19

    hipL, kneeL, hipR, kneeR, shL, elbL, shR, elbR = _POSES[pose]
    if shR is None:
        shR = 40.0
    if arm_deg is not None:
        shR = arm_deg

    # os dois lados usam o MESMO multiplicador de `facing` — perfil, nao espelho: o
    # sinal de cada angulo na pose (nao o lado L/R) e que decide frente/tras.
    legL = _limb((cx - hip_dx, hip_y), hipL, leg_len, kneeL, leg_len, facing)
    legR = _limb((cx + hip_dx, hip_y), hipR, leg_len, kneeR, leg_len, facing)
    armL = _limb((cx - sh_dx, sh_y), shL, arm_len, elbL, arm_len, facing)
    armR = _limb((cx + sh_dx, sh_y), shR, arm_len, elbR, arm_len, facing)

    def seg(pts, lo, hi, sd):
        local = (progress - lo) / (hi - lo)
        if local <= 0:
            return
        j = jitter(smooth_path(pts, samples=10), amp * 0.6, seed + sd)
        stroke(d, cut(j, min(1.0, local)), width, color + (255,), seed=seed + sd)

    # cabeca (0.00-0.22) -> tronco (0.22-0.45) -> pernas (0.45-0.72) -> bracos (0.72-1.00)
    hp = min(1.0, progress / 0.22)
    if hp > 0:
        d.ellipse([head_c[0] - hr, head_c[1] - hr, head_c[0] + hr, head_c[1] + hr],
                 outline=color + (255,), width=width)
    seg([(cx, neck_y), (cx - hip_dx * 0.9, hip_y * 0.5 + neck_y * 0.5), (cx - hip_dx, hip_y)],
        0.22, 0.34, 900)
    seg([(cx, neck_y), (cx + hip_dx * 0.9, hip_y * 0.5 + neck_y * 0.5), (cx + hip_dx, hip_y)],
        0.22, 0.34, 901)
    seg(legL, 0.45, 0.585, 1)
    seg(legR, 0.585, 0.72, 2)
    seg(armL, 0.72, 0.86, 3)
    seg(armR, 0.86, 1.00, 4)

    juntas = dict(head=head_c, hand_l=armL[-1], hand_r=armR[-1],
                 foot_l=legL[-1], foot_r=legR[-1])
    return _auto_boil(lay, "ink"), juntas


def hand_pie(size, cx, cy, r, frac=0.5, progress=1.0, width=7, color=INK,
             fill=None, seed=9, amp=6.0, start_deg=-90.0, hatch_gap=26):
    """
    Grafico de pizza DESENHADO A MAO: circulo de duas passadas, dois raios, e o setor
    preenchido por hachura de marcador.

    Nao e vetor por escolha. O numero que ele diz e uma estimativa que ele mesmo
    corrige no audio — em tipografia de dado limpo ganharia uma autoridade que a fala
    nao tem. Hachura de marcador e o registro honesto para isso, e ainda e um registro
    visual novo dentro do video.

    A ordem de desenho reproduz a mao: contorno -> raios -> hachura.
    """
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    fill = fill or color

    # 0.00-0.42 contorno | 0.42-0.60 raios | 0.60-1.00 hachura
    ring = min(1.0, progress / 0.42)
    if ring > 0:
        lay.alpha_composite(hand_circle(size, cx, cy, r, r, progress=ring, passes=2,
                                        width=width, color=color, seed=seed, amp=amp))
    if progress > 0.42:
        sp = min(1.0, (progress - 0.42) / 0.18)
        a0 = math.radians(start_deg)
        a1 = math.radians(start_deg + 360.0 * frac)
        for k, ang in enumerate((a0, a1)):
            spoke = [(cx, cy), (cx + r * math.cos(ang), cy + r * math.sin(ang))]
            pts = jitter(smooth_path(spoke + [spoke[-1]]), amp * 0.5, seed + 40 + k)
            stroke(d, cut(pts, sp), width, color + (255,), seed=seed + k)

    if progress > 0.60:
        hp = min(1.0, (progress - 0.60) / 0.40)
        sect = Image.new("L", size, 0)
        ImageDraw.Draw(sect).pieslice([cx - r, cy - r, cx + r, cy + r],
                                      start_deg, start_deg + 360.0 * frac, fill=255)
        hat = Image.new("RGBA", size, (0, 0, 0, 0))
        hd = ImageDraw.Draw(hat)
        n = int(4 * r / hatch_gap)
        shown = int(round(n * hp))
        for i in range(shown):
            off = -2 * r + i * hatch_gap
            p0 = (cx + off - r, cy - r)
            p1 = (cx + off + r, cy + r)
            hd.line([p0, p1], fill=fill + (255,), width=max(3, width - 2))
        hat.putalpha(ImageChops.multiply(hat.getchannel("A"), sect))
        lay.alpha_composite(hat)
    return _auto_boil(lay, "ink")


def hand_arrow(size, path, progress=1.0, width=6, color=INK, seed=2,
               amp=4.0, head=34, head_angle=0.42, smooth=True, halo=None):
    """
    Seta manual. A ponta so aparece quando o corpo esta praticamente pronto.
    `halo`: cor de contorno desenhada por baixo, mais grossa. Serve para a seta
    continuar legivel quando cruza do papel claro para o video escuro.
    """
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    path = smooth_path(path) if smooth else list(path)
    dense = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        steps = max(2, int(math.dist(a, b) / 6))
        for s in range(steps):
            t = s / steps
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    dense.append(path[-1])
    dense = jitter(dense, amp, seed)

    body_p = min(1.0, progress / 0.82)
    body = cut(dense, body_p)
    if halo:
        stroke(d, body, width + 7, halo + (255,), pressure=0.10, seed=seed)
    stroke(d, body, width, color + (255,), seed=seed)

    if progress > 0.82 and len(body) >= 2:
        hp = (progress - 0.82) / 0.18
        tip = body[-1]
        prev = body[max(0, len(body) - 8)]
        ang = math.atan2(tip[1] - prev[1], tip[0] - prev[0])
        for sgn in (+1, -1):
            a = ang + math.pi + sgn * head_angle
            end = (tip[0] + head * math.cos(a), tip[1] + head * math.sin(a))
            barb = jitter([tip, end], 2.0, seed + (7 if sgn > 0 else 13))
            if halo:
                stroke(d, cut(barb, hp), width + 7, halo + (255,), pressure=0.10,
                       seed=seed + sgn)
            stroke(d, cut(barb, hp), width, color + (255,), seed=seed + sgn)
    return _auto_boil(lay, "ink")


def hand_underline(size, x1, x2, y, progress=1.0, passes=2, width=7,
                   color=YELLOW, seed=3, amp=5.0, pressure=0.12):
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rng = np.random.default_rng(seed)
    per = 1.0 / passes
    for p in range(passes):
        local = (progress - p * per) / per
        if local <= 0:
            break
        local = min(1.0, local)
        yy = y + rng.uniform(-6, 6)
        n = 80
        pts = [(x1 + (x2 - x1) * i / n, yy) for i in range(n + 1)]
        pts = jitter(pts, amp, seed + p * 23)
        stroke(d, cut(pts, local), width, color + (255,), pressure=pressure, seed=seed + p)
    return _auto_boil(lay, "ink")


def blue_line(size, path, progress=1.0, width=7, color=BLUE, seed=4, amp=3.0,
              smooth=True):
    """Linha de continuidade. Atravessa cenas: sai de uma pela direita e reaparece numa seguinte."""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    path = smooth_path(path) if smooth else list(path)
    dense = []
    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        steps = max(2, int(math.dist(a, b) / 6))
        for s in range(steps):
            t = s / steps
            dense.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    dense.append(path[-1])
    dense = jitter(dense, amp, seed)
    stroke(d, cut(dense, progress), width, color + (255,), pressure=0.12, seed=seed)
    return _auto_boil(lay, "ink")


# ---------------------------------------------------------------- texto
def text_layer(size, text, fontpath, fontsize, xy, color=INK, anchor="lt",
              stroke_w=0, tracking=0, hand=False, seed=5, progress=1.0,
              line_gap=1.0, mode="block", rise=14, optical=False, boil_seed=None):
    """
    Texto como camada. `hand=True` aplica variacao de baseline/rotacao por caractere
    (escrita feita de uma vez, nao fonte perfeita).

    `mode` decide COMO o texto entra:
      block — bloco inteiro, opacidade 0->1 com subida curta. Padrao para tipografia
              editorial. Revelar caractere a caractere e efeito de maquina de escrever:
              e transicao de template, proibida pela Style Bible §9.6.
      wipe  — mascara da esquerda para a direita, borda suave. Sensacao de impressao.
      write — mascara da esquerda para a direita com borda dura (ponta de caneta).
              Unico modo valido para marcador: a mao escreve, nao datilografa.
    """
    if optical:
        # Centro pelo DESENHO da letra, nao pela caixa da fonte. A caixa inclui
        # ascendente e descendente, entao uma sigla em caixa alta centrada nela
        # escorrega para baixo e sai da faixa da fita. Mede no estado cheio e aplica o
        # mesmo desvio sempre, para o texto nao andar durante a animacao.
        full = text_layer(size, text, fontpath, fontsize, xy, color, anchor, stroke_w,
                          tracking, hand, seed, 1.0, line_gap, mode, rise, optical=False,
                          boil_seed=boil_seed)
        bb = full.getbbox()
        if bb:
            cx, cy = (bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0
            xy = (xy[0] + (xy[0] - cx), xy[1] + (xy[1] - cy))
        return text_layer(size, text, fontpath, fontsize, xy, color, anchor, stroke_w,
                          tracking, hand, seed, progress, line_gap, mode, rise,
                          optical=False, boil_seed=boil_seed)

    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    f = font(fontpath, fontsize)
    progress = max(0.0, min(1.0, progress))
    if progress <= 0:
        return lay
    lines = text.split("\n")
    rng = np.random.default_rng(seed)

    # medir bloco
    widths, heights = [], []
    for l in lines:
        w = sum(f.getlength(ch) + tracking for ch in l)
        widths.append(w)
        bb = f.getbbox(l or "X")
        heights.append(bb[3] - bb[1])
    lh = (max(heights) if heights else fontsize) * line_gap
    block_h = lh * len(lines)
    block_w = max(widths) if widths else 0

    ax, ay = xy
    if anchor[0] == "m":
        ax -= block_w / 2
    elif anchor[0] == "r":
        ax -= block_w
    if anchor[1] == "m":
        ay -= block_h / 2
    elif anchor[1] == "b":
        ay -= block_h

    if mode == "block":
        ay += (1.0 - progress) * rise      # sobe os ultimos pixels ao aparecer

    for li, line in enumerate(lines):
        x = ax
        if anchor[0] == "m":
            x = ax + (block_w - widths[li]) / 2
        y = ay + li * lh
        for ch in line:
            adv = f.getlength(ch) + tracking
            if ch == " ":
                x += adv
                continue
            if hand:
                # Style Bible §5: "escrito de uma vez, com PEQUENAS variacoes".
                # Variacao maior (baseline 3.5%, rotacao 3.2 graus) faz uma sigla de
                # tres letras parecer tres letras soltas, nao uma palavra.
                dy = rng.uniform(-fontsize * 0.016, fontsize * 0.016)
                rot = rng.uniform(-1.4, 1.4)
                sc = rng.uniform(0.985, 1.02)
                pad = int(fontsize * 0.9)
                g = Image.new("RGBA", (int(adv) + pad * 2, int(fontsize * 2.2) + pad * 2),
                              (0, 0, 0, 0))
                ImageDraw.Draw(g).text((pad, pad), ch, font=f, fill=color + (255,),
                                       stroke_width=stroke_w, stroke_fill=color + (255,))
                if abs(sc - 1) > 1e-3:
                    g = g.resize((max(1, int(g.width * sc)), max(1, int(g.height * sc))),
                                 Image.LANCZOS)
                g = g.rotate(rot, resample=Image.BICUBIC, expand=True)
                lay.alpha_composite(g, (int(x - pad), int(y + dy - pad)))
            else:
                ImageDraw.Draw(lay).text((x, y), ch, font=f, fill=color + (255,),
                                         stroke_width=stroke_w, stroke_fill=color + (255,))
            x += adv

    kind = "ink" if hand else "type"
    if progress >= 1.0:
        return _auto_boil(lay, kind, seed=boil_seed)
    if mode == "block":
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * progress)))
        return _auto_boil(lay, kind, seed=boil_seed)

    # wipe / write: frente de revelacao horizontal sobre o bloco inteiro
    soft = 46 if mode == "wipe" else 14
    x0, x1 = ax - soft, ax + block_w + soft
    front = x0 + (x1 - x0) * progress
    ramp = np.clip((front - np.arange(size[0], dtype=np.float32)) / soft, 0, 1)
    m = np.tile((ramp * 255).astype(np.uint8), (size[1], 1))
    a = np.minimum(np.asarray(lay.getchannel("A")), m)
    lay.putalpha(Image.fromarray(a))
    return _auto_boil(lay, kind, seed=boil_seed)


def text_width(text, fontpath, fontsize, tracking=0):
    f = font(fontpath, fontsize)
    return max(sum(f.getlength(c) + tracking for c in l) for l in text.split("\n"))


# ---------------------------------------------------------------- objetos
# ---------------------------------------------------------------- boil
_noise = {}


def _field(w, h, size, seed, complexity):
    """Campo de ruido fractal suave, em duas componentes. Cacheado por parametro."""
    key = (w, h, size, seed, complexity)
    if key in _noise:
        return _noise[key]
    rng = np.random.default_rng(seed)
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)
    amp = 1.0
    for o in range(max(1, int(complexity))):
        sc = max(2, int(size / (2 ** o)))
        nh, nw = max(2, h // sc), max(2, w // sc)
        a = rng.normal(0, 1, (nh, nw)).astype(np.float32)
        b = rng.normal(0, 1, (nh, nw)).astype(np.float32)
        dx += cv2.resize(a, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        dy += cv2.resize(b, (w, h), interpolation=cv2.INTER_CUBIC) * amp
        amp *= 0.5
    m = max(np.abs(dx).max(), np.abs(dy).max(), 1e-6)
    dx, dy = dx / m, dy / m
    _noise[key] = (dx, dy)
    if len(_noise) > 240:
        _noise.pop(next(iter(_noise)))
    return dx, dy


# Relogio do boil. 9 e o padrao desta lib sozinha (dois relogios: desenho 16 + boil 9). O estudo
# Porsche mediu UM relogio so, a 12 (ESTUDO.md §3 e §8 #1), e a regua do kit e 12: o render do
# projeto iguala BOIL_FPS ao MOTION_FPS, e tudo segura e salta junto.
BOIL_FPS = 9.0


def boil(im, frame, amount=9.0, size=90, seed=0, complexity=1, fps=None, timeline_fps=24.0):
    """
    Deslocamento turbulento, o "boil" que faz o objeto parecer redesenhado a cada quadro.

    Equivale ao Turbulent Displace do After Effects com Posterize Time: o campo de ruido
    NAO evolui suavemente — ele TROCA de semente a cada passo de `fps`. E o salto que da
    a sensacao de desenho refeito; evolucao continua daria ondulacao de gelatina.

    `fps=9` sobre uma timeline de 24 significa um campo novo a cada ~2,7 frames.

    A camada e preenchida com margem de `amount` antes do remap, senao o deslocamento
    empurraria pixel para fora e cortaria a borda. Devolve (imagem, deslocamento) — quem
    posiciona precisa somar o offset.
    """
    if amount <= 0:
        return im, (0, 0)
    fps = BOIL_FPS if fps is None else fps
    pad = int(math.ceil(amount)) + 2
    src = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    src.alpha_composite(im, (pad, pad))
    w, h = src.size
    step = int(math.floor(frame * fps / timeline_fps))
    dx, dy = _field(w, h, size, seed * 7919 + step, complexity)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    mx = (xx + dx * amount).astype(np.float32)
    my = (yy + dy * amount).astype(np.float32)
    out = cv2.remap(np.asarray(src), mx, my, cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return Image.fromarray(out), (-pad, -pad)


def boil_full(im, frame, **kw):
    """Boil numa camada que ja e do tamanho do quadro (texto, anotacao). Sem offset."""
    out, off = boil(im, frame, **kw)
    return out.crop((-off[0], -off[1], -off[0] + im.width, -off[1] + im.height))


# Quanto cada classe aguenta, medido: acima disso o objeto DERRETE, que a Style Bible
# §13 proibe. Tinta desenhada aguenta o dobro do que um objeto fotografado.
# Multiplicador global. Calibrar o boil inteiro mexendo num numero so.
BOIL_SCALE = 1.0

BOIL_PRESETS = {
    "obj":    dict(amount=3.0, size=110, complexity=1),   # objeto fotografado
    "paper":  dict(amount=4.0, size=95,  complexity=1),   # papel, cartao, fita
    "type":   dict(amount=2.0, size=130, complexity=1),   # tipografia editorial
    "ink":    dict(amount=6.0, size=75,  complexity=2),   # marcador e anotacao
    # Tipografia de impacto: ruido FINO. O preset "ink" tem ruido grosso e deforma a
    # FORMA da letra; aqui a ideia e erodir a BORDA, como tinta em papel aspero — e o
    # que da o aspecto impresso do "DOCUMENTARIES" da referencia.
    "print":  dict(amount=3.0, size=22,  complexity=2),
}

# O frame corrente. E estado implicito de proposito: sem ele, cada uma das ~50 chamadas
# de desenho precisaria carregar o frame, e uma cena nova nasceria sem boil por
# esquecimento. `boil_ctx(frame)` no topo de cada build_M# liga tudo.
_BOIL = {"frame": None}


def boil_ctx(frame):
    _BOIL["frame"] = frame


def _auto_boil(im, kind, depth=2, seed=None):
    """
    Aplica o boil da classe. Sem `seed`, a semente vem da LINHA que chamou: cada
    elemento ganha um campo proprio, estavel entre frames e diferente dos vizinhos.
    Semear por ordem de desenho quebraria quando um objeto condicional aparece ou some.

    `seed` explicito serve para AMARRAR elementos que sao fisicamente um so — fita e a
    palavra escrita sobre ela precisam do MESMO campo, senao balancam em separado e a
    etiqueta parece descolar do papel.
    """
    f = _BOIL["frame"]
    if f is None:
        return im
    if seed is None:
        try:
            seed = sys._getframe(depth).f_lineno * 131 + len(kind)
        except Exception:
            seed = len(kind)
    a = dict(BOIL_PRESETS[kind])
    # "print" nao escala com BOIL_SCALE: ele e TEXTURA de impressao, nao intensidade de
    # tremor. Baixar o boil dos objetos nao deve apagar a erosao da tipografia.
    if kind != "print":
        a["amount"] *= BOIL_SCALE
    return boil_full(im, f, seed=seed, **a)


def load_cutout(path, target_w=None, rotation=0.0):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox() or (0, 0, im.width, im.height))
    if target_w:
        s = target_w / im.width
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    if rotation:
        im = im.rotate(rotation, resample=Image.BICUBIC, expand=True)
    return im


def rough_edge(im, amp=5, seed=7):
    """Come a borda do alfa de forma irregular. Mata o recorte vetorial perfeito."""
    a = im.getchannel("A")
    noise = Image.fromarray(
        (np.random.default_rng(seed).random((im.height, im.width)) * 255).astype(np.uint8)
    ).filter(ImageFilter.GaussianBlur(2.2))
    n = np.asarray(noise, dtype=np.int16)
    arr = np.asarray(a, dtype=np.int16)
    edge = np.asarray(a.filter(ImageFilter.FIND_EDGES), dtype=np.int16)
    mask = edge > 8
    arr[mask] = np.clip(arr[mask] + (n[mask] - 128) * (amp / 8.0), 0, 255)
    im = im.copy()
    im.putalpha(Image.fromarray(arr.astype(np.uint8)))
    return im


def contact_shadow(size, layer, pos, dy=11, blur=24, opacity=0.17, dx=0, spread=1.0):
    """Sombra de contato como CAMADA PROPRIA. Papel fino: dy baixo. Objeto alto: dy alto."""
    sh = Image.new("RGBA", size, (0, 0, 0, 0))
    a = layer.getchannel("A")
    if spread != 1.0:
        a = a.point(lambda v: min(255, int(v * spread)))
    tint = Image.new("RGBA", layer.size, (26, 22, 18, 255))
    tint.putalpha(a)
    sh.alpha_composite(tint, (int(pos[0] + dx), int(pos[1] + dy)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    al = sh.getchannel("A").point(lambda v: int(v * opacity))
    sh.putalpha(al)
    return sh


def place(canvas, layer, pos, shadow=None, kind="obj", boil_seed=None):
    """
    shadow = dict(dy, blur, opacity) ou None.
    `kind` escolhe a intensidade do boil: "obj" fotografado, "paper" papel, None desliga.
    A sombra e calculada DEPOIS do boil — ela tem que acompanhar a forma deformada.
    """
    if kind and _BOIL["frame"] is not None:
        pre = layer
        layer = _auto_boil(layer, kind, depth=2, seed=boil_seed)
        pos = (pos[0] - (layer.width - pre.width) // 2,
               pos[1] - (layer.height - pre.height) // 2)
    if shadow:
        canvas.alpha_composite(contact_shadow(canvas.size, layer, pos, **shadow))
    canvas.alpha_composite(layer, (int(pos[0]), int(pos[1])))
    return canvas


def ink_center(layer):
    """
    Centro OPTICO de uma camada: media ponderada pelo alfa, nao centro da bounding box.
    Fita crepe e curva — a caixa inclui o arco, entao o centro da caixa fica abaixo da
    faixa util e o texto centrado nela escorrega para fora do papel.
    """
    a = np.asarray(layer.getchannel("A"), dtype=np.float32)
    tot = a.sum()
    if tot <= 0:
        return layer.width / 2.0, layer.height / 2.0
    yy, xx = np.mgrid[0:layer.height, 0:layer.width]
    return float((xx * a).sum() / tot), float((yy * a).sum() / tot)


def centered(layer, cx, cy):
    return (int(cx - layer.width / 2), int(cy - layer.height / 2))


# ---------------------------------------------------------------- relogio
def clock_hands(size, cx, cy, r, hour, minute, width=None, color=(24, 23, 25)):
    """Ponteiros desenhados por nos. Garante hora exata e legivel."""
    lay = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    w = width or max(4, int(r * 0.075))
    ah = math.radians((hour % 12) * 30 + minute * 0.5 - 90)
    am = math.radians(minute * 6 - 90)
    d.line([(cx, cy), (cx + r * 0.52 * math.cos(ah), cy + r * 0.52 * math.sin(ah))],
           fill=color + (255,), width=w)
    d.line([(cx, cy), (cx + r * 0.78 * math.cos(am), cy + r * 0.78 * math.sin(am))],
           fill=color + (255,), width=max(3, int(w * 0.78)))
    rr = w * 0.85
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color + (255,))
    return lay


# ---------------------------------------------------------------- acabamento
def finish(img, grain=0.055, vignette=0.05, chroma=1.0, sat=0.92, seed=11):
    """Grao + vinheta + aberracao cromatica. Aplicado ao CONJUNTO, nunca por objeto."""
    im = img.convert("RGB")
    if sat != 1.0:
        im = ImageEnhance.Color(im).enhance(sat)
    if chroma > 0:
        # Deslocamento RADIAL, nulo no centro e maximo nas bordas — e assim que lente
        # real se comporta. Deslocamento horizontal uniforme franja TODA letra de
        # vermelho e ciano, inclusive a manchete, e le como erro de render.
        arr = np.asarray(im, dtype=np.float32)
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = w / 2.0, h / 2.0
        nx, ny = (xx - cx) / cx, (yy - cy) / cy
        rad = np.sqrt(nx * nx + ny * ny)
        k = chroma * np.clip((rad - 0.35) / 0.85, 0, 1) ** 2
        out = arr.copy()
        for ch, sgn in ((0, 1.0), (2, -1.0)):
            sx = np.clip(xx + sgn * k * nx * 2.0, 0, w - 1)
            sy = np.clip(yy + sgn * k * ny * 2.0, 0, h - 1)
            out[..., ch] = cv2.remap(arr[..., ch], sx, sy,
                                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if grain > 0:
        # Semente POR FRAME: grao identico em todos os frames le como sujeira de lente
        # colada na tela. Grao de filme cintila.
        #
        # MAS ruido branco por pixel e INCOMPRESSIVEL: sem correlacao entre frames o
        # x264 nao consegue prever nada e os planos de motion vao a ~120 Mbps, contra
        # ~4 Mbps do resto do clipe. Grao real tem TAMANHO — borrar o campo de ruido
        # devolve a compressibilidade e ainda fica mais parecido com filme.
        rng = np.random.default_rng(int(seed))
        n = rng.normal(0, 255 * grain * 1.7, (im.height, im.width)).astype(np.float32)
        n = cv2.GaussianBlur(n, (0, 0), 0.9)
        arr = np.clip(np.asarray(im, dtype=np.float32) + n[..., None], 0, 255)
        im = Image.fromarray(arr.astype(np.uint8))
    if vignette > 0:
        yy, xx = np.mgrid[0:im.height, 0:im.width]
        cx, cy = im.width / 2, im.height / 2
        dist = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
        v = np.clip(1 - vignette * np.clip(dist - 0.55, 0, None) / 0.75, 0, 1)[..., None]
        im = Image.fromarray((np.asarray(im, dtype=float) * v).astype(np.uint8))
    return im.convert("RGBA")


def canvas(size=(W, H), color=PAPER):
    return Image.new("RGBA", size, color + (255,))


def ease(t):
    """cubic-bezier(0.20, 0.80, 0.20, 1.00) aproximada. Para objeto que POUSA."""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def ease_in(t, power=2.4):
    """Aceleracao. Para objeto SAINDO de cena: comeca devagar e vai embora rapido."""
    t = max(0.0, min(1.0, t))
    return t ** power


def ease_draw(t):
    """
    Para TRACO sendo desenhado. Uma caneta anda a velocidade quase constante: com
    ease-out cubico os ultimos 20% do traco ficam imperceptiveis e o desenho parece
    terminar antes da hora. Aqui so as pontas sao suavizadas.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t) * 0.22 + t * 0.78
