"""Reel narrado: "O que acontece quando você estala os dedos?" (exemplo com voz).

Voz grave de narrador (35 s). A narração do exemplo (voz sintética gerada por IA, sem metadados) e as palavras com tempo
(faster-whisper) vêm em dados/estalar/voz.mp3 e dados/estalar/palavras_bruto.json, então o --som roda sem nada seu.
Para usar a sua narração: <trabalho>/estalar/voz.mp3 (ou $COLAGEM_VOZ) e as suas palavras em
<trabalho>/estalar/palavras_bruto.json (as duas juntas: os tempos da cena saem das palavras).
Os quadros estão no relógio de autoria de 24 qps; a voz entra no quadro 10: q(t) = 10 + 24·t, com t em segundos da voz.
Fontes científicas do roteiro: Kawchuk et al., PLoS ONE 10(4): e0119470 (2015); D. L. Unger, Arthritis & Rheumatism
(1998).

Antes: preparar.py luva (a mão) e preparar.py estalar (mão em 2×, junta, mão com esqueleto).

Imagem: a mão do atlas (Z-Anatomy, CC BY-SA 4.0) em 2×, a pele rasga numa janela redonda sobre o nó do indicador e, por
baixo, a junta feita no Blender com os ossos reais da mão (junta_blender.py): os ossos se afastam, nasce a bolha de gás.
A junta é registrada com a mão pelo ponto da articulação (medido no Blender) e a rotação de 14° (medida na sobreposição).

    clpy cena_estalar.py              quadros de conferência em previa/estalar/
    clpy cena_estalar.py --video      previa/estalar.mp4 (sem som)
    clpy cena_estalar.py --som        mix (voz + trilha + efeitos + estalo) e entrega em previa/estalar_som.mp4"""
import os
import sys
import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C, camadas as K
from motor import W, H

EST = AQUI / "estalar"
MAO = EST / "mao" / "vistas"
JD = EST / "junta" / "vistas"
CACHE = EST / "papel"
PAL = json.load(open(EST / "palavras_bruto.json" if (EST / "palavras_bruto.json").exists()
                    else CM.EXEMPLOS / "dados" / "estalar" / "palavras_bruto.json"))

# ---- escalas e registro (medidos)
PXM_M = json.load(open(MAO / "vistas.json"))["px_por_m"]            # 9615,4 px/m: a mão em 2×
J_M = json.load(open(MAO / "vistas.json"))["marcos"]["junta"]        # a junta na mão (px): (1049,0; 1132,7)
dj = json.load(open(JD / "vistas.json"))
PXM_J = dj["px_por_m"]                                               # 16483,5 px/m: a junta
MJ = dj["marcos"]["junta"]                                           # a junta no render da junta (px)
KJ = PXM_M / PXM_J                                                   # px da mão por px da junta (0,583)
ROT_J = 14.0                                                         # graus (anti-horário) para a junta cair sobre os ossos
CROP = (560, 400, 2230, 3900)                                        # o pedaço da mão que usamos (px do render 2×); o antebraço vai longe,
                                                                     # senão a câmera mostra o corte reto dele
J_C = (J_M[0] - CROP[0], J_M[1] - CROP[1])                           # a junta no recorte
BORDA = 12
PAD = BORDA + 4
E = 0.32                                                             # px do mundo por px da mão
JW = (1000.0, 1400.0)                                                # onde a junta fica no mundo
R_JANELA = 270                                                       # raio da janela (px da mão)
S_I = 720                                                            # lado do quadro do interior (px da mão)
FIM = 880
Z3 = 3.2                                                             # o zoom da janela
RIG = EST / "rig" / "vistas"                                         # a mão com esqueleto (mao_rig_blender.py), 2×
CLIPES = json.load(open(EST / "rig" / "clipes.json"))                # A gancho · B esquerda · C as duas · D estalo final · E parada · G gira · F puxado
P7 = K.PASSO_7
DIR = (-math.sin(math.radians(14)), -math.cos(math.radians(14)))     # a direção do dedo (para cima, inclinado)


def q(t):
    """quadro de autoria no instante t (s) da voz"""
    return int(round(10 + 24 * t))


def mundo(dx, dy):
    """(dx, dy) em px da mão em relação à junta → mundo"""
    return JW[0] + dx * E, JW[1] + dy * E


def cam_em(z, wx, wy):
    """(z, cx, cy) que deixa o ponto do mundo (wx, wy) no centro da região segura (540, 700)"""
    return (z, wx, wy + 260 / z)


def cache_png(nome, faz):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{nome}.png"
    if not out.exists():
        im = faz()
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


# ------------------------------------------------------------------ a pele da mão (e a espelhada: a mão esquerda)
def pele_img():
    def faz():
        cor = Image.open(MAO / "pele" / "cor_v_000.png").convert("RGBA").crop(CROP)
        luz = Image.open(MAO / "pele" / "luz_v_000.png").convert("RGB").crop(CROP)
        return K.papelizar(K.apara_lascas(cor), luz=luz, registrado=True, semente=1, cor=1.0, borda=BORDA, contraste=1.6)
    return cache_png("pele", faz)


def rig_pele(frame, espelho=False):
    """um quadro da mão com esqueleto, em papel (mesmo recorte e mesma escala da mão parada)"""
    nome = f"rig_{frame:03d}"

    def faz():
        cor = Image.open(RIG / "pele" / f"cor_q_{frame:03d}.png").convert("RGBA").crop(CROP)
        luz = Image.open(RIG / "pele" / f"luz_q_{frame:03d}.png").convert("RGB").crop(CROP)
        return K.papelizar(K.apara_lascas(cor), luz=luz, registrado=True, semente=1, cor=1.0, borda=BORDA, contraste=1.6)
    im = cache_png(nome, faz)
    return ImageOps.mirror(im) if espelho else im


def alfa_rig(frame):
    return np.asarray(Image.open(RIG / "pele" / f"cor_q_{frame:03d}.png").getchannel("A").crop(CROP))


def passo(frames, q0, fd, ciclo=False):
    """o quadro do clipe no instante fd (degraus de 7 qps a partir de q0)"""
    n = int(max(0.0, fd - q0) // P7)
    return frames[n % len(frames)] if ciclo else frames[min(n, len(frames) - 1)]


def alfa_pele():
    return np.asarray(Image.open(MAO / "pele" / "cor_v_000.png").getchannel("A").crop(CROP))


# ------------------------------------------------------------------ o interior da janela (a junta em cada quadro)
def interior(f):
    """a junta no quadro f do Blender, já na escala e no ângulo da mão: quadro S_I×S_I (px da mão) centrado na junta,
    cortado pelo disco da janela e pela silhueta da pele (nada vaza para fora do dedo)"""
    def faz():
        nomes = ["capsula", "liquido", "meta", "falange", "bolha"]
        cors = {n: K.apara_lascas(Image.open(JD / n / f"cor_q_{1 if n == 'meta' else f:03d}.png")) for n in nomes}
        uni = np.maximum.reduce([np.asarray(c.getchannel("A")) for c in cors.values()])
        comp = Image.new("RGBA", cors["capsula"].size, (0, 0, 0, 0))
        for i, n in enumerate(nomes):
            luz = JD / n / f"luz_q_{1 if n == 'meta' else f:03d}.png"
            im = K.papelizar(cors[n], luz=luz, registrado=True, semente=40 + i, cor=1.0, borda=0, contraste=1.6,
                             silhueta=uni)
            comp.alpha_composite(im.crop((4, 4, im.width - 4, im.height - 4)))     # borda 0 → margem de 4 px
        # junta (px) → mão (px): gira 14° em volta do marco, escala KJ e leva o marco ao centro do quadro
        Rm = cv2.getRotationMatrix2D((MJ[0], MJ[1]), ROT_J, KJ)             # o marco fica no lugar...
        Rm[:, 2] += np.array([S_I / 2, S_I / 2]) - np.array(MJ)             # ...e vai para o centro do quadro
        arr = cv2.warpAffine(np.asarray(comp), Rm, (S_I, S_I), flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0))
        # a cavidade escura por baixo, o disco da janela e a silhueta da pele
        yy, xx = np.mgrid[0:S_I, 0:S_I].astype(np.float32)
        disco = (np.hypot(xx - S_I / 2, yy - S_I / 2) <= R_JANELA * 1.10).astype(np.float32)
        ap = alfa_pele()
        x0, y0 = int(J_C[0] - S_I / 2), int(J_C[1] - S_I / 2)
        pele = np.zeros((S_I, S_I), np.float32)
        sub = ap[max(y0, 0):y0 + S_I, max(x0, 0):x0 + S_I].astype(np.float32) / 255
        pele[max(-y0, 0):max(-y0, 0) + sub.shape[0], max(-x0, 0):max(-x0, 0) + sub.shape[1]] = sub
        mascara = cv2.GaussianBlur(disco * pele, (0, 0), 1.0)
        cav = np.asarray(PC.textura_papel(S_I, S_I, (26, 17, 16), 61).convert("RGBA")).copy()
        base = Image.fromarray(cav)
        base.alpha_composite(Image.fromarray(arr))
        out = np.asarray(base).copy()
        out[..., 3] = (out[..., 3].astype(np.float32) * mascara).astype(np.uint8)
        return Image.fromarray(out)
    return cache_png(f"interior_{f:02d}", faz)


def quadro_junta(fd):
    """qual quadro da junta (1–30) o instante fd mostra, em degraus de 7 qps"""
    p7 = K.PASSO_7
    q_puxa, q_pop, q_some = q(9.08), q(14.14), q(22.0)
    if fd < q_puxa:
        return 1
    if fd < q_pop:
        return min(8, 2 + int((fd - q_puxa) / p7))                   # 2..8: os ossos se afastam (1 s)
    if fd < q_pop + 4 * p7:
        return 9 + int((fd - q_pop) / p7)                            # 9, 10, 11, 12: a bolha nasce e assenta
    if fd < q_some:
        return 12
    n = int((fd - q_some) / p7)                                      # 14 degraus: a bolha some
    return 30 if n >= 14 else 13 + int(round(n * 17 / 13))


def fonte_interior(fd, p):
    return interior(quadro_junta(fd))


fonte_interior.tam = (S_I, S_I)


def fonte_gas():
    """os pontinhos do gás dissolvido: andam para o vão e se juntam (quadro 12,0–14,14 s)"""
    t0, t1 = q(12.0), q(14.14)
    rng = np.random.default_rng(11)
    n = 13
    # o gás está DENTRO do líquido, no vão entre os ossos (a 18–109 px acima da junta): espalhado, depois junta no centro
    ini = np.stack([rng.uniform(-92, 92, n), rng.uniform(-100, -26, n)], axis=1)
    alvo = np.array([0.0, -63.0])
    raios = rng.uniform(7, 11, n)
    cache = {}

    def fonte(fd, p):
        passo = int(max(0, fd - t0) // K.PASSO_7)
        if passo not in cache:
            u = min(1.0, passo * K.PASSO_7 / (t1 - t0))
            u = u * u * (3 - 2 * u)
            im = Image.new("RGBA", (S_I, S_I), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            for i in range(n):
                pos = ini[i] * (1 - u) + alvo * u + rng.normal(0, 0.0, 2)
                r = raios[i] * (1 - 0.25 * u)
                c = (S_I / 2 + pos[0], S_I / 2 + pos[1])
                d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(226, 240, 252, 235), outline=(40, 30, 28, 255),
                          width=3)
            cache[passo] = im
        return cache[passo]
    fonte.tam = (S_I, S_I)
    return fonte


def tique(texto, corpo=84, semente=2):
    return PC.etiqueta([texto], corpo=(corpo, 30), semente=semente)


# ------------------------------------------------------------------ a cena
def camada(nome, img, x, y, ancora, ini=0, fim=10 ** 6, esc=E, sombra=None, boil="obj", mundo_=True):
    L = C.fixo(nome, img, x, y, ini=ini, fim=fim, esc=esc, sombra=sombra, boil=boil, ancora=ancora)
    L.tam = img.size if isinstance(img, Image.Image) else img.tam
    L.mundo = mundo_
    return L


def centro_mudanca(f0, f1):
    """onde, na imagem (px da mão em relação à junta), um dedo mudou entre dois quadros: o centro de massa da diferença"""
    a = np.asarray(Image.open(RIG / "pele" / f"cor_q_{f0:03d}.png").convert("RGBA").crop(CROP)).astype(np.int16)
    b = np.asarray(Image.open(RIG / "pele" / f"cor_q_{f1:03d}.png").convert("RGBA").crop(CROP)).astype(np.int16)
    d = (np.abs(a - b).sum(axis=2) > 60)
    ys, xs = np.nonzero(d)
    alto = ys <= np.quantile(ys, 0.25)                               # o quarto de cima da mudança: a ponta do dedo
    return float(xs[alto].mean() - J_C[0]), float(ys[alto].mean() - J_C[1])


def montar():
    c = []
    c.append(C.fundo_escuro(FIM, [(0, 1.0, "segura")], cor=(30, 33, 40)))
    pele = pele_img()
    ap = alfa_pele()
    anc_pele = (J_C[0] + PAD, J_C[1] + PAD)
    jx, jy = JW

    # ---- a linha do tempo da mão direita (a original) e da esquerda (espelhada), em quadros de autoria
    QA0 = q(0.25)                                                    # o gancho: os 4 dedos estalam
    QA1 = QA0 + int(round(len(CLIPES["A"]) * P7))
    q_jan0, q_jan1 = q(3.0), q(5.1)                                  # a janela abre
    q_fecha0, q_fecha1 = q(23.9), q(24.9)                            # e fecha
    QG0 = q_fecha1                                                   # a mão gira de costas para 30°
    QE0 = QG0 + int(round(len(CLIPES["G"]) * P7))                    # e fica parada (o "controle")
    QC0 = q(28.7)                                                    # as duas abrem e fecham juntas
    QD0 = QC0 + int(round(len(CLIPES["C"]) * P7))                    # gira para as costas e estala de novo
    QL0 = q(24.1)                                                    # a esquerda (do médico) entra
    gap_mundo = mundo(DIR[0] * 63, DIR[1] * 63)                      # o centro do vão entre os ossos (a 63 px da junta)

    # os limites da mão parada (30°) no mundo, para as duas mãos lado a lado
    ae = alfa_rig(CLIPES["E"][0])
    ys, xs = np.nonzero(ae > 128)
    xe_min, xe_max = (xs.min() - J_C[0]) * E, (xs.max() - J_C[0]) * E
    ye_min = (ys.min() - J_C[1]) * E
    y_punho = (1512 - 733) * E
    ys0, xs0 = np.nonzero(ap > 128)
    x_min, x_max = (xs0.min() - J_C[0]) * E, (xs0.max() - J_C[0]) * E
    y_min = (ys0.min() - J_C[1]) * E
    DX = 2 * xe_max + 100                                            # a junta da mão esquerda, em relação à da direita

    # ---- a janela sobre o nó (a pele do dedo acompanha o osso puxado: um quadro de pele por quadro da junta)
    janelas = {}

    def janela_de(i):
        if i not in janelas:
            if len(janelas) > 2:
                janelas.pop(next(iter(janelas)))
            im = rig_pele(CLIPES["F"][i - 1]) if i > 1 else pele
            f_ = K.janela(im, anc_pele, q_jan0, q_jan1, R_JANELA, semente=12, fecha=(q_fecha0, q_fecha1))
            janelas[i] = f_
        return janelas[i]

    def fonte_dir(fd, p):
        if fd < QA0:
            return rig_pele(CLIPES["A"][0])
        if fd < QA1:
            return rig_pele(passo(CLIPES["A"], QA0, fd))
        if fd < QG0:
            return janela_de(quadro_junta(fd))(fd, p)
        if fd < QE0:
            return rig_pele(passo(CLIPES["G"], QG0, fd))
        if fd < QC0:
            return rig_pele(CLIPES["E"][0])
        if fd < QD0:
            return rig_pele(passo(CLIPES["C"], QC0, fd))
        return rig_pele(passo(CLIPES["D"], QD0, fd))
    fonte_dir.tam = pele.size
    pele_l = camada("MAO", fonte_dir, jx, jy, anc_pele, sombra=(8, 16, 0.32), boil="paper")
    pele_l.chaves["y"] = C.k((0, jy - 160 * E, "out"), (6, jy, "segura"))
    pele_l.chaves["s"] = [(a, v * E, cv) for a, v, cv in C.POP]
    pele_l.chaves["op"] = C.k((0, 0.0, "lin"), (2, 1.0, "segura"))
    pele_l.som = ("pouso", 5)
    ant = (S_I / 2, S_I / 2)
    interior_l = camada("INTERIOR", fonte_interior, jx, jy, ant, ini=q_jan0 - 2, fim=q_fecha1 + 2, boil="paper")
    gas = camada("GAS", fonte_gas(), jx, jy, ant, ini=q(12.0), fim=q(14.2), boil="obj")
    c += [interior_l, gas, pele_l]

    # ---- a mão esquerda (espelhada): estala sem parar enquanto o médico é citado; depois abre e fecha com a direita
    def fonte_esq(fd, p):
        if fd < QC0:
            return rig_pele(passo(CLIPES["B"], QL0, fd, ciclo=True), espelho=True)
        return rig_pele(passo(CLIPES["C"], QC0, fd), espelho=True)
    fonte_esq.tam = pele.size
    anc_esp = (pele.width - anc_pele[0], anc_pele[1])
    esq = camada("MAO_ESQUERDA", fonte_esq, jx + DX, jy, anc_esp, ini=QL0, sombra=(8, 16, 0.32), boil="paper")
    q_sai = QD0 - 2
    esq.chaves["x"] = C.k((QL0, jx + DX + 700, "out"), (QL0 + 10, jx + DX, "segura"), (q_sai, jx + DX, "in"),
                          (q_sai + 12, jx + DX + 700, "segura"))
    esq.chaves["op"] = C.k((QL0, 0.0, "lin"), (QL0 + 2, 1.0, "segura"))
    esq.fim = q_sai + 14
    esq.som = ("desliza", QL0 + 5, 1)
    c.append(esq)

    # ---- etiqueta "LÍQUIDO SINOVIAL" (na tela) com a seta até o líquido, enquanto o zoom está no nó
    et = tique("LÍQUIDO SINOVIAL", corpo=58, semente=71)
    ex, ey = 700, 330
    L_et = C.cai("ET_LIQUIDO", et, q(4.95), ex, ey, rot=-3, sombra=(4, 8, 0.25), boil="paper", fim=q(7.0))
    L_et.mundo = False
    c.append(L_et)
    alvo = (540 + 92, 690)                                           # o líquido âmbar, ao lado do osso
    seta = C.Traco("SETA_LIQUIDO", [(ex - et.width / 2 - 8, ey + 30), (alvo[0] + 90, alvo[1] - 130), alvo], q(5.15),
                   q(5.8), espessura=9, cor=(240, 232, 214), seta=True, tam_seta=26, fim=q(7.0), suave=True, semente=4)
    seta.camada.mundo = False
    c.append(seta.camada)

    # ---- caneta: a seta de puxar (sobre o dedo, para cima), antes dos ossos se afastarem
    p0 = (540 + DIR[0] * (R_JANELA * E * Z3 + 40), 700 + DIR[1] * (R_JANELA * E * Z3 + 40))
    p1 = (540 + DIR[0] * (R_JANELA * E * Z3 + 190), 700 + DIR[1] * (R_JANELA * E * Z3 + 190))
    puxa = C.Traco("SETA_PUXA", [p0, p1], q(7.35), q(8.25), espessura=16, seta=True, tam_seta=46, fim=q(10.6), semente=9)
    puxa.camada.mundo = False
    c.append(puxa.camada)
    et_p = tique("PRESSÃO CAI", corpo=50, semente=33)
    L_p = C.cai("ET_PRESSAO", et_p, q(10.55), 770, 350, rot=2, sombra=(4, 8, 0.25), boil="paper", fim=q(12.3))
    L_p.mundo = False
    c.append(L_p)

    # ---- o estalo: a bolha nasce em q(14,14): rajada de papel no vão, e a câmera treme (abaixo)
    q_pop = q(14.14)
    c.append(C.rajada("RAJ_ESTALO", gap_mundo[0], gap_mundo[1], q_pop, raio=70, n=12, dur=9, espessura=5, fim=q_pop + 12))
    c.append(C.circulo("CIRCULO_BOLHA", gap_mundo[0], gap_mundo[1], 30, 30, q(15.3), q(16.3), espessura=5, fim=q(19.0)))
    et_b = tique("BOLHA", corpo=84, semente=51)
    L_b = C.cai("ET_BOLHA", et_b, q(16.5), 760, 470, rot=-4, sombra=(4, 8, 0.25), boil="paper", fim=q(19.0))
    L_b.mundo = False
    c.append(L_b)

    # ---- o relógio dos 20 minutos (na tela, em cima): corre de 00:00 a 20:00 (19,58 → 21,94 s)
    rel = C.contador("RELOGIO", q(19.5), q(21.9), q(24.0), 1200, lambda v: f"{int(v) // 60:02d}:{int(v) % 60:02d}",
                     x=W / 2, y=300, curva="io", corpo=82)
    c.append(rel)

    # ---- o gancho: uma rajadinha em cada dedo que estala (onde o dedo mudou, medido nos quadros)
    snap_a = {"2": 4, "3": 7, "4": 10, "5": 13}                      # o quadro do clipe A em que cada dedo solta
    for k_, f_ in snap_a.items():
        fa = CLIPES["A"]
        dx, dy = centro_mudanca(fa[f_ - 2], fa[f_ - 1])
        wx, wy = mundo(dx, dy)
        qs = QA0 + int(round((f_ - 1) * P7))
        c.append(C.rajada(f"RAJ_DEDO{k_}", wx, wy, qs, raio=55, n=9, dur=7, espessura=5, fim=qs + 10, semente=int(k_)))

    # ---- o médico: as etiquetas (CONTROLE e 2× POR DIA) sobre as mãos e o contador de estalos (na tela)
    Q = C.quadro
    mao = Q((jx + x_min - 25, jy + y_min - 20, jx + x_max + 25, jy + y_punho + 40))
    duas = Q((jx + xe_min - 20, jy + ye_min - 150, jx + DX - xe_min + 20, jy + y_punho + 60))
    z2, cx2, cy2 = duas[:3]

    def na_tela(wx, wy):
        return 540 + (wx - cx2) * z2, 960 + (wy - cy2) * z2
    sx_dir, _ = na_tela(jx + (xe_min + xe_max) / 2, 0)
    sx_esq, _ = na_tela(jx + DX - (xe_min + xe_max) / 2, 0)
    y_et = 420
    et_c = tique("CONTROLE", corpo=46, semente=61)
    L_c = C.cai("ET_CONTROLE", et_c, q(25.4), sx_dir, y_et, rot=-3, sombra=(4, 8, 0.25), boil="paper", fim=q(28.7))
    L_c.mundo = False
    c.append(L_c)
    et_x = tique("2× POR DIA", corpo=46, semente=62)
    L_x = C.cai("ET_2XDIA", et_x, q(25.6), sx_esq, y_et, rot=3, sombra=(4, 8, 0.25), boil="paper", fim=q(28.7))
    L_x.mundo = False
    c.append(L_x)
    anos = C.contador("ESTALOS", q(26.0), q(28.0), q(29.0), 36500, lambda v: f"{int(v):,}".replace(",", ".") + " ESTALOS",
                      x=W / 2, y=310, curva="io", corpo=66, largura_ref="36.500 ESTALOS")
    c.append(anos)

    # ---- as duas mãos iguais: o "=" entre elas e o carimbo
    xm = jx + (xe_max + (DX - xe_max)) / 2 + 0                      # o meio entre as duas mãos
    ig = C.Traco("IGUAL_1", [(xm - 45, jy + 70), (xm + 45, jy + 70)], q(30.0), q(30.35), espessura=14, fim=q(32.7),
                 semente=5)
    ig2 = C.Traco("IGUAL_2", [(xm - 45, jy + 115), (xm + 45, jy + 115)], q(30.4), q(30.75), espessura=14, fim=q(32.7),
                  semente=6)
    c += [ig.camada, ig2.camada]
    st = PC.carimbo("SEM ARTRITE", corpo=104, semente=8, cor=(236, 86, 66))
    c.append(C.carimbo("c_ARTRITE", st, q(31.55), 540, 400, -6, fim=q(32.1), mundo=False))   # antes da câmera entrar na mão

    # ---- o fecho: o último estalo (a rajada pequena no nó, no quadro em que o dedo solta no clipe D)
    q_fim_est = QD0 + int(round(6 * P7))
    c.append(C.rajada("RAJ_FINAL", jx, jy, q_fim_est, raio=60, n=10, dur=8, espessura=5, fim=q_fim_est + 12))

    # ---- legendas (entram DEPOIS da imagem)
    leg = [("Esse estalo não é *osso* batendo.", 0.55, 2.85),
           ("Dentro da junta tem um *líquido*.", 3.2, 6.95),
           ("Você puxa, a pressão cai e o gás vira *bolha*.", 7.45, 14.0),
           ("O estalo é a bolha *nascendo*, não estourando.", 14.45, 18.7),
           ("Só estala de novo em *20 minutos*.", 19.0, 24.1),
           ("Um médico estalou só a *mão esquerda* por *50 anos*.", 24.4, 28.55),
           ("As duas mãos ficaram *iguais*. Sem artrite.", 28.9, 32.6),
           ("Pode estalar. É só uma *bolha*.", 32.9, FIM / 24 - 10 / 24 - 0.001)]
    for i, (txt, a, b) in enumerate(leg):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=120 + i), q(a), min(q(b), FIM - 2)))
    c.append(C.vinheta(FIM))

    # ---- a câmera
    mao_zoom = cam_em(Z3, jx, jy)
    final = cam_em(2.1, jx + 60, jy - 40)
    cam = C.Camera().plano(0, mao, "segura")
    cam.plano(q(2.75), mao, "io").plano(q(5.0), mao_zoom, "segura")
    cam.plano(q(9.0), mao_zoom, "io").plano(q(10.3), (Z3 * 1.06, mao_zoom[1], mao_zoom[2]), "io")
    cam.plano(q_pop - 1, (Z3 * 1.06, mao_zoom[1], mao_zoom[2]), "segura")
    for dq, dz, dx, dy in ((0, 1.10, 6, -4), (2, 1.03, -5, 3), (4, 1.07, 3, -2), (6, 1.05, -1, 1)):
        cam.plano(q_pop + dq, (Z3 * dz, mao_zoom[1] + dx, mao_zoom[2] + dy), "segura")
    cam.plano(q_pop + 9, mao_zoom, "io").plano(q(23.85), mao_zoom, "io")
    cam.plano(q(25.4), duas, "segura").plano(q(32.2), duas, "io").plano(QD0 + 6, final, "segura")
    return c, cam.montar(), dict(QA0=QA0, QA1=QA1, QL0=QL0, QC0=QC0, QD0=QD0, snap_a=snap_a)


# ------------------------------------------------------------------ som
def clique(freq, seed, sr=44100):
    """um estalo curto, sintetizado: clique seco de ruído + tom agudo + baque grave (freq varia de um para outro)"""
    rng = np.random.default_rng(seed)
    n = int(sr * 0.16)
    t = np.arange(n) / sr
    ruido = np.convolve(rng.normal(0, 1, n) * np.exp(-t / 0.0016), [1, -0.95], mode="same")
    x = ruido * 0.9 + np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.007) * 0.7 + \
        np.sin(2 * np.pi * (freq / 15.3) * t) * np.exp(-t / 0.022) * 0.5
    return x / np.abs(x).max()


def faixa_estalos(saida, grandes, pequenos, dur, sr=44100):
    """a faixa dos estalos: os dois grandes (a bolha nasce; o último) e os pequenos de cada dedo que solta"""
    import wave
    x = np.zeros(int(sr * dur))
    for i, t in enumerate(grandes):
        c = clique(2600, 3 + i) * 0.9
        a = int(t * sr)
        x[a:a + len(c)] += c[:len(x) - a]
    for i, t in enumerate(pequenos):
        c = clique(1900 + 170 * (i % 5), 40 + i) * 0.24
        a = int(t * sr)
        if a + len(c) < len(x):
            x[a:a + len(c)] += c
    st = np.stack([x, x], axis=1)
    with wave.open(str(saida), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())


def mixar(camadas, cam, info, refazer=False):
    """trilha + efeitos (som_auto) → mix com a voz, os estalos e a normalização. refazer=True reaproveita o mix.wav"""
    import som as S, som_auto as SA
    pasta = EST / "som"
    if not refazer:
        SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, pasta, inicio=0.0,
                      licenca=CM.TRILHA_LICENCA)
    # os estalos grandes caem na PAUSA antes de "De repente" e antes do último "estalar" (a 30 ms da palavra)
    q_fim_est = info["QD0"] + int(round(6 * P7))
    grandes = [q(14.14) / 24 - 0.03, q_fim_est / 24 - 0.02]
    pequenos = [(info["QA0"] + (f - 1) * P7) / 24 for f in info["snap_a"].values()]
    for off in (0, 3, 6, 9):                                         # a mão esquerda: um estalinho por dedo
        for m in range(3):
            tq = info["QL0"] + (off + 3 + 12 * m) * P7
            if tq < info["QC0"]:
                pequenos.append(tq / 24)
    faixa_estalos(pasta / "estalos.wav", grandes, sorted(pequenos), FIM / 24)
    voz = Path(os.environ.get("COLAGEM_VOZ", str(EST / "voz.mp3")))
    if not voz.exists() and not (EST / "palavras_bruto.json").exists():
        voz = CM.EXEMPLOS / "dados" / "estalar" / "voz.mp3"            # a narração do exemplo, casada com as palavras
    CM.exige(voz, como="grave a narração (ou gere com 'pode' do usuário) e salve como estalar/voz.mp3")
    delay = int(round(q(0.0) / 24 * 1000))
    dur = FIM / 24
    fc = (f"[1:a]adelay={delay}|{delay},loudnorm=I=-16:TP=-1.5:LRA=7,apad=whole_dur={dur:.3f},asplit=2[v][vs];"
          f"[0:a]volume=-9dB[b];[b][vs]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=300[bd];"
          f"[bd][v][2:a]amix=inputs=3:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.2:LRA=9[m]")
    final = pasta / "master.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pasta / "mix.wav"), "-i", str(voz),
                    "-i", str(pasta / "estalos.wav"), "-filter_complex", fc, "-map", "[m]", "-ar", "48000", str(final)],
                   check=True)
    return final


if __name__ == "__main__":
    camadas, cam, info = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(2400, 2800)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "estalar.mp4")
    elif "--som" in sys.argv:
        import som as S
        master = mixar(camadas, cam, info, refazer="--refazer" in sys.argv)
        print("master", master, "final", S.juntar(prev / "estalar.mp4", master, prev / "estalar_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        qs = [int(x) for x in args[0].split(",")] if args else \
            [0, 8, 20, 40, 60, 90, 120, 160, 205, 232, 260, 300, 345, 352, 360, 400, 440, 520, 580, 620, 700, 760, 800, 860]
        M.render(camadas, cam, fundo, FIM, prev / "estalar", quadros=qs)
    print("ok")
