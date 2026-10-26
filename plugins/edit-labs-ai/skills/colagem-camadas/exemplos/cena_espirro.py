"""Exemplo narrado: "E se você segurasse um espirro?" (medicina, 55 s).

O exemplo roda SEM voz: a narração não vem no plugin. Os quadros continuam no relógio da narração original (relógio de
autoria de 24 qps; a voz entra no quadro 10: q(t) = 10 + 24·t, com t em segundos da voz), então cada cena dura o que a
frase dela durava. Com a sua narração (mesmo roteiro, mesmos tempos ou os tempos ajustados nos q(...)), ponha
COLAGEM_VOZ=<arquivo> e o --som mistura a voz por cima com sidechain. Fontes do caso: BMJ Case Reports (2018 e 2023).

Imagem: o homem de foto de arquivo (NMAAHC, CC0, pacote colagem-homem3) abre o vídeo e fecha com o tchau; o corpo é o
modelo 3D da garganta (Z-Anatomy, CC BY-SA 4.0, pacote colagem-zanatomy-garganta) em camadas registradas: pele →
músculos → músculos da faringe → corte sagital (osso, pulmão, brônquios, vias aéreas). O resto é papel e caneta: o AR é
um personagem de bolinhas azuis, a PRESSÃO é um manômetro, a mangueira dobra. Nada de rosto gerado. O ouvido (cena da
audição) é opcional e tem licença não comercial: ver ouvido_blender.py; sem ele, a câmera fica na traqueia.

Antes: os pacotes colagem-homem3 e colagem-zanatomy-garganta, e preparar.py espirro (monta o .blend e renderiza os
patamares).

    clpy cena_espirro.py              quadros de conferência em previa/espirro/
    clpy cena_espirro.py 120,300      só esses quadros
    clpy cena_espirro.py t=8.9,22.6   os quadros desses instantes da narração (s)
    clpy cena_espirro.py --video      previa/espirro.mp4 (sem som)
    clpy cena_espirro.py --som        mix (trilha + efeitos [+ COLAGEM_VOZ]) e entrega em previa/espirro_som.mp4"""
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C, camadas as K
import cena_homem3 as HM
import espirro_pecas as P
import espirro_pecas2 as P2
import garganta_pecas as G
from motor import W, H

ROOT = P.ROOT                                                     # <trabalho>/espirro
P7 = K.PASSO_7
VOZ = os.environ.get("COLAGEM_VOZ")                               # a sua narração (opcional)
OUVIDO = G.tem_ouvido()


def q(t):
    """quadro de autoria no instante t (s) da voz"""
    return int(round(10 + 24 * t))


Q_CRED = q(52.95)                               # a tela de créditos (2,3 s) entra depois do "médico"
FIM = Q_CRED + 56
TAM = HM.TAM                                    # o homem em px de trabalho (1625 × 2700); o mundo dele = esses px

# ---- onde as coisas estão no corpo do homem (px de trabalho, medidos na foto)
PESCOCO = (1062.0, 625.0)                       # a laringe, no nó da gravata

# ---- onde ficam as outras cenas no mundo (cada uma em seu canto do papel)
MANG_O = (-2150.0, 560.0)                       # a mangueira (serpentina), origem local


def fixo(nome, img, ini=0, fim=10 ** 6, sombra=None, boil="obj", x=None, y=None, esc=1.0):
    return HM.fixo(nome, img, ini=ini, fim=fim, sombra=sombra, boil=boil, x=x, y=y)


def creditos_card(q0):
    """a tela de créditos (1 parágrafo curto), nos últimos 2,3 s"""
    txt = ("Foto: NMAAHC, Smithsonian (CC0); pose do braço editada com IA. Anatomia em 3D: Z-Anatomy (CC BY-SA 4.0), "
           "baseado em BodyParts3D (CC BY-SA 2.1 JP); o seio piriforme é modelo próprio. Caso: BMJ Case Reports, 2018 e 2023.")
    if OUVIDO:
        txt += " Orelha interna e ossículos: University of Dundee (CC BY-NC-SA 4.0)."
    if VOZ:
        txt += " " + os.environ.get("COLAGEM_VOZ_CREDITO", "")
    larg = 900
    fo = PC.fonte("Inter-800.ttf", 30)
    ls, atual = [], ""
    for w in txt.split(" "):
        if fo.getlength((atual + " " + w).strip()) <= larg - 90 or not atual:
            atual = (atual + " " + w).strip()
        else:
            ls.append(atual)
            atual = w
    ls.append(atual)
    alt = int(len(ls) * 30 * 1.3) + 60
    im = PC.textura_papel(larg, alt, (246, 240, 224), 77)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(ls):
        d.text((45, 30 + int(i * 30 * 1.3)), l, font=fo, fill=PC.TINTA + (255,))
    im = PC.rasgar(im, amp=6, passo=18, semente=5)
    out = Image.new("RGBA", (im.width + 60, im.height + 60), (0, 0, 0, 0))
    out.alpha_composite(im, (30, 30))
    L = C.cai("CREDITOS", out, q0, 540, 1180, rot=-1.0, sombra=(6, 12, 0.3), boil="paper", fim=FIM)
    L.mundo = False
    L.tam = out.size
    return L


# ====================================================================== as camadas de verdade
# O corpo (a "figura F") é o modelo 3D da garganta (Z-Anatomy CC BY-SA 4.0) em camadas registradas:
# pele → músculos → (músculos da faringe) → o corte sagital (osso, pulmão, brônquios, vias aéreas). O ar sobe pelo canal
# aberto, as camadas se descascam, a pressão sobe, o bolsinho da garganta rompe e o ar desce pelo pescoço.
F0 = (2800.0, 0.0)                                  # onde F mora no mundo (o homem de foto fica em 0..1625)
FOLHA = (4800, 7200)
PEN = (250, 214, 64)                                # marca-texto amarelo: aparece sobre o rosa, o osso e o escuro


def Wp(y, z):
    """(y, z) do atlas, em metros → mundo"""
    u, v = G.MUNDO(y, z)
    return (u + F0[0], v + F0[1])


def caixa_atlas(ya, yb, za, zb):
    (x1, y1), (x2, y2) = Wp(ya, za), Wp(yb, zb)
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


QA = lambda caixa: C.quadro(caixa, (30, 110, 1050, 1810))        # a imagem usa a tela toda (nada de texto)

# o caminho do ar, medido sobre o corte (atlas: y para trás, z para cima; metros)
CAM_ATLAS = {
    "traq": [(0.026, 1.30), (0.0095, 1.352), (0.0081, 1.361), (0.0, 1.40), (-0.0088, 1.436), (-0.0147, 1.462),
             (-0.017, 1.485), (-0.018, 1.505), (-0.0155, 1.526)],
    "nariz": [(-0.0155, 1.526), (-0.0192, 1.553), (-0.032, 1.568), (-0.060, 1.572), (-0.090, 1.568), (-0.112, 1.560)],
    "boca": [(-0.0155, 1.526), (-0.030, 1.535), (-0.050, 1.537), (-0.075, 1.536), (-0.098, 1.534)],
    "fora_nariz": [(-0.112, 1.560), (-0.135, 1.553), (-0.19, 1.545), (-0.26, 1.54)],
    "fora_boca": [(-0.098, 1.534), (-0.125, 1.530), (-0.19, 1.50), (-0.26, 1.47)],
    # o ar que vaza do bolsinho: para trás, desce pelo vão atrás do esôfago e abre no peito, em volta da traqueia
    "vaza": [(-0.0125, 1.4815), (-0.003, 1.474), (0.0045, 1.455), (0.0066, 1.436), (0.0154, 1.40), (0.0215, 1.375),
             (0.0235, 1.36), (0.024, 1.335)],
}
NARINA, BOCA_P = (-0.1125, 1.560), (-0.098, 1.533)          # a saída do nariz e a da boca
BOLSO_P = (-0.0125, 1.4815)                                  # o seio piriforme (modelo próprio)


def rota(*nomes, a_partir_de=None):
    """caminho em pontos do mundo; a_partir_de: tira da traqueia o que está abaixo desse z (a câmera nem vê)"""
    pts = []
    for n in nomes:
        p = list(CAM_ATLAS[n])
        if n == "traq" and a_partir_de is not None:
            p = [q_ for q_ in p if q_[1] >= a_partir_de]
        if pts and p and pts[-1] == p[0]:
            p = p[1:]
        pts += p
    return P.Trilha([Wp(*p_) for p_ in pts])


def fl(nome, tier, a, b, fi=0, fo=0, img=None, sombra=None, boil="obj"):
    """uma camada de F no patamar (tier), visível de a a b (fade de entrada/saída em quadros), no lugar e na escala certos"""
    im = img if img is not None else (G.cama(tier) if nome == "cama" else G.camada(tier, nome))
    if img is None and tier in ("alto", "peito"):
        im = G.suaviza_bordas(im, 350 if tier == "alto" else 250)
    cx, cy = G.centro(tier)
    tam = im.size if isinstance(im, Image.Image) else im.tam
    L = C.fixo(f"F_{tier}_{nome}", im, cx + F0[0], cy + F0[1], ini=a - 1, fim=b + 1, esc=G.esc(tier), sombra=sombra, boil=boil,
               ancora=(tam[0] / 2, tam[1] / 2))
    L.tam = tam
    if fi or fo:
        ks = [(a, 0.0 if fi else 1.0, "lin")]
        if fi:
            ks.append((a + fi, 1.0, "segura"))
        if fo:
            ks += [(b - fo, 1.0, "lin"), (b, 0.0, "segura")]
        L.chaves["op"] = C.k(*ks)
    return L


def interior(tier, a, b, fi=0, fo=0, nomes=("cama", "osso", "pulm", "bronq", "via")):
    out = []
    for n in nomes:
        sb = (10, 22, 0.30) if n == "cama" else None
        out.append(fl(n, tier, a, b, fi, fo, sombra=sb, boil="paper" if n == "cama" else "obj"))
    return out


def tingida(im, mult):
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    a[..., :3] = np.clip(a[..., :3] * np.array(mult, np.float32), 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def via_quente(tier):
    """as vias aéreas num tom mais quente e escuro: a pressão cobrando"""
    return tingida(G.camada(tier, "via"), (1.0, 0.60, 0.52))


def circulo_cor(nome, cx, cy, rx, ry, q0, q1, espessura, fim, cor=PEN, rot=-4, volta=395):
    """o círculo de caneta (como C.circulo) na cor do marcador"""
    pts = []
    for t in np.linspace(0, 1, 90):
        a = math.radians(-120 + volta * t)
        r = 1.0 + 0.035 * math.sin(3 * a + 0.6) + 0.05 * t
        pts.append((rx * 1.1 + 30 + rx * r * math.cos(a), ry * 1.1 + 30 + ry * r * math.sin(a)))
    larg, alt = int(2 * rx * 1.1 + 60), int(2 * ry * 1.1 + 60)
    fonte = M.traco_fonte(pts, larg, alt, cor=cor, espessura=espessura)
    return M.Camada(nome, fonte, q0, fim, ancora=(larg / 2, alt / 2), boil="ink", chaves={
        "x": C.k((q0, cx, "segura")), "y": C.k((q0, cy, "segura")), "rot": C.k((q0, rot, "segura")),
        "trim": C.k((q0, 0.0, "out"), (q1, 1.0, "segura")), "op": C.k((q0, 0.95, "segura"))})


def caixa_trilhas(trs, m=60):
    xs = np.concatenate([t.p[:, 0] for t in trs])
    ys = np.concatenate([t.p[:, 1] for t in trs])
    return (xs.min() - m, ys.min() - m, xs.max() + m, ys.max() + m)



def traco_hi(nome, pts, q0, q1, espessura, cor=PEN, K=3, fim=10 ** 6, semente=3, tremor=0.8, suave=False):
    """traço de caneta desenhado K vezes maior e escalado de volta: nítido nos close-ups"""
    t = C.Traco(nome, [(x * K, y * K) for x, y in pts], q0, q1, espessura=espessura * K, cor=cor, fim=fim, semente=semente, tremor=tremor * K, suave=suave)
    L = t.camada
    L.chaves["x"] = C.k((q0, t.x0 / K, "segura"))
    L.chaves["y"] = C.k((q0, t.y0 / K, "segura"))
    L.chaves["s"] = C.k((q0, 1.0 / K, "segura"))
    return L


def circulo_hi(nome, cx, cy, rx, ry, q0, q1, espessura, fim, cor=PEN, rot=-4, K=3):
    L = circulo_cor(nome, cx, cy, rx * K, ry * K, q0, q1, espessura * K, fim, cor=cor, rot=rot)
    L.chaves["s"] = C.k((q0, 1.0 / K, "segura"))
    return L


def ondas_hi(nome, x, y, q0, q1, raio, cor, espessura, periodo=12, n=3, K=6):
    L = C.ondas(nome, x, y, q0, q1, raio=raio * K, n=n, cor=cor, espessura=espessura * K, periodo=periodo)
    L.chaves["s"] = C.k((q0, 1.0 / K, "segura"))
    return L


def bolhas_hi(nome, specs, caixa, q0, q1, K=3):
    """camada de bolinhas desenhada K vezes maior (close-up nítido). A memória cresce com K²: só nas cenas de perto"""
    sp = []
    for s_ in specs:
        d = dict(s_)
        d["trilha"] = P.Trilha((s_["trilha"].p * K).tolist(), suave=False)
        d["r"] = s_["r"] * K
        if d.get("amp"):
            d["amp"] = d["amp"] * K
        sp.append(d)
    x0, y0, x1, y1 = caixa
    L = P.camada_bolhas(nome, sp, (x0 * K, y0 * K, x1 * K, y1 * K), q0, q1)
    L.chaves["x"] = C.k((q0, int(x0 * K) / K, "segura"))
    L.chaves["y"] = C.k((q0, int(y0 * K) / K, "segura"))
    L.chaves["s"] = C.k((q0, 1.0 / K, "segura"))
    return L


def cena_ouvido(fig, ar, folha):
    """o ouvido de lado (só com ouvido_blender.py montado); devolve os dois planos de câmera"""
    EAR_C = (-2600.0, 3000.0)
    folha("FOLHA_OUVIDO", EAR_C, (190, 208, 226), q(37.4), q(39.1), 14)
    ce = G.esc_ouvido()

    def fo_(nome, a, b, img=None, sombra=None, boil="obj"):
        im = img if img is not None else G.ouvido(nome)
        tam = im.size if isinstance(im, Image.Image) else im.tam
        L = C.fixo(f"OUV_{nome}", im, EAR_C[0], EAR_C[1], ini=a - 1, fim=b + 1, esc=ce, sombra=sombra, boil=boil, ancora=(tam[0] / 2, tam[1] / 2))
        L.tam = tam
        return L
    ea, eb = q(37.4), q(39.1)
    for n in ("cama", "coclea", "ossic", "membr"):
        fig.append(fo_(n, ea, eb, sombra=(10, 22, 0.3) if n == "cama" else None, boil="paper" if n == "cama" else "obj"))
    pin = fo_("pele", ea, eb, sombra=(8, 16, 0.3))
    K.levanta(pin, q(37.95), q(38.35), para=(190, -250), giro=14.0)
    fig.append(pin)
    # (tier-px do centro do ouvido: u = largura/2 + (y - 0,0055)*28000; v = altura/2 - (z - 1,585)*28000)
    def e_pt(y, z):
        return (EAR_C[0] + (0.0055 - y) * 0 + (y - 0.0055) * 28000 * ce, EAR_C[1] - (z - 1.585) * 28000 * ce)
    x_dr, y_dr = e_pt(0.0075, 1.5775)                                 # o tímpano
    x_co, y_co = e_pt(0.0000, 1.5800)                                 # a cóclea
    onda = ondas_hi("ONDAS_SOM", x_dr - 110, y_dr + 4, q(38.05), q(38.62), 150, PEN, 5, K=6)
    ar.append(onda)
    ar.append(traco_hi("SOM_RETO", [(x_dr - 90, y_dr + 4), (x_dr - 8, y_dr + 4)], q(38.5), q(38.7), 5, fim=q(39.0), semente=3, tremor=0.0, K=6))
    S_ouv1 = C.quadro((EAR_C[0] - 105, EAR_C[1] - 135, EAR_C[0] + 105, EAR_C[1] + 135), (30, 110, 1050, 1810))
    S_ouv2 = C.quadro((x_dr - 62, y_dr - 40, x_dr + 38, y_dr + 50), (30, 110, 1050, 1810))
    return S_ouv1, S_ouv2


def montar():
    c, sheets, fig, ar, ui, transicoes = [], [], [], [], [], []
    poses = {n: HM.pose_trab(n) for n in ("repouso", "meio", "alto")}
    rng = np.random.default_rng(12)
    VERM = (236, 86, 66)
    FC = Wp(0.002, 1.43)                                   # o centro de F no mundo

    def folha(nome, centro, cor, a, b, sem=5):
        sheets.append(P.folha_papel(nome, centro, FOLHA, cor, a, b, semente=sem, esc=2.0))

    # ------------------------------------------------------------------ planos de câmera
    S1 = C.quadro((640, 100, 1500, 1200), C.REGIAO_SEM_LEGENDA)
    S_inteiro = QA(caixa_atlas(-0.165, 0.165, 1.12, 1.745))
    S_cab = QA(caixa_atlas(-0.27, 0.075, 1.36, 1.74))                  # cabeça e pescoço, com espaço na frente para o ar sair
    S_rosto = QA(caixa_atlas(-0.155, 0.020, 1.440, 1.640))
    S_cab2 = QA(caixa_atlas(-0.20, 0.125, 1.38, 1.735))                 # cabeça e pescoço (cena 5)
    S_pesc = QA(caixa_atlas(-0.115, 0.045, 1.425, 1.60))
    S_lar = QA(caixa_atlas(-0.058, 0.033, 1.436, 1.527))               # a garganta de perto: a faringe, a laringe e o bolsinho
    S_pesc2 = QA(caixa_atlas(-0.100, 0.055, 1.37, 1.54))
    S_d1 = QA(caixa_atlas(-0.090, 0.060, 1.40, 1.54))                  # a descida (cena 8): pescoço
    S_d2 = QA(caixa_atlas(-0.100, 0.070, 1.32, 1.47))
    S_d3 = QA(caixa_atlas(-0.115, 0.095, 1.22, 1.42))                  # peito
    CR = (7700.0, 1000.0)                                  # a "reunião" (cópias do corte de pele em volta de uma mesa)
    S_reuniao = C.quadro((CR[0] - 520, CR[1] - 650, CR[0] + 520, CR[1] + 900), (30, 110, 1050, 1810))
    xn, yn = Wp(*NARINA)
    xb, yb = Wp(*BOCA_P)
    xp, yp = Wp(*BOLSO_P)                                  # o bolsinho no mundo

    # ================================================================== B1 (0–3,14): o homem de foto, a garganta circulada
    homem = fixo("HOMEM", poses["repouso"], ini=0, fim=q(3.45), sombra=(10, 22, 0.28), boil="paper")
    homem.chaves["y"] = C.k((0, TAM[1] / 2 - 110, "out"), (8, TAM[1] / 2, "segura"))
    homem.chaves["s"] = C.k(*[(a_, v, cv) for a_, v, cv in C.POP])
    homem.som = ("pouso", 7)
    ar.append(homem)
    ar.append(C.circulo("CIRCULO_GARGANTA", PESCOCO[0] + 6, PESCOCO[1] - 8, 128, 92, q(2.54), q(3.05), espessura=11, fim=q(3.45)))

    # ================================================================== B2 (3,42–5,68): a "reunião": o mesmo corte de pele, à mesa
    folha("FOLHA_REUNIAO", (CR[0], CR[1] + 100), (190, 204, 214), q(3.0), q(5.95), 3)
    pele_b = G.camada("base", "pele")
    iw, ih = pele_b.size
    busto = pele_b.crop((0, 0, iw, 1381))                  # cabeça, pescoço e ombros (a mesa esconde o resto)
    esc_h = 0.36
    tons = [(1.0, 1.0, 1.0), (0.72, 0.60, 0.50), (1.10, 1.02, 0.94), (0.62, 0.48, 0.38)]
    X2 = (-215, 215)
    topo_y = CR[1] - 620 + busto.height * esc_h / 2                  # trás da mesa (olham para a direita)
    base_y = CR[1] + 30 + pele_b.height * esc_h / 2                  # na frente da mesa (espelhados: olham para a esquerda)
    mesa = PC.textura_papel(1500, 270, (168, 124, 86), 41).convert("RGBA")
    mesa = PC.rasgar(mesa, amp=5, passo=18, semente=4)
    pes = [("A", busto, topo_y, X2[0], tons[0], False), ("B", busto, topo_y, X2[1], tons[1], False),
           ("C", pele_b, base_y, X2[0], tons[2], True), ("D", pele_b, base_y, X2[1], tons[3], True)]
    ordem = {"A": 0, "B": 2, "C": 1, "D": 3}
    for nome, base_im, yy, dx, tom, esp in pes:
        im_i = tingida(base_im, tom)
        if esp:
            im_i = ImageOps.mirror(im_i)
        L = C.cai(f"PESSOA_{nome}", im_i, q(3.46) + 4 * ordem[nome], CR[0] + dx, yy, rot=0.0, de_y=-320, esc=esc_h, sombra=(8, 16, 0.28),
                  boil="paper", fim=q(5.95))
        L.tam = im_i.size
        ar.append(L)
        if nome == "B":                                    # a mesa entra depois dos de trás e antes dos da frente
            mc = C.cai("MESA", mesa, q(3.46) + 9, CR[0], CR[1] - 90, rot=0.0, de_y=300, sombra=(10, 20, 0.3), boil="paper", fim=q(5.95))
            mc.tam = mesa.size
            ar.append(mc)
    # "você" é quem está na frente, à esquerda: circulado, e o espirro fica preso (umas bolinhas que sobem e param no nariz)
    cxv, cyv = CR[0] + X2[0], base_y
    nx, ny = cxv + (iw - 1022 - iw / 2) * esc_h, cyv + (730 - ih / 2) * esc_h
    ar.append(C.circulo("CIRCULO_VOCE", cxv - 5, cyv - 560 * esc_h - 70, 215, 250, q(4.85), q(5.35), espessura=14, fim=q(5.95)))
    specs2 = [dict(t0=q(4.95) + 3 * j, t1=q(4.95) + 3 * j + 20, trilha=P.Trilha([(nx - 8, ny + 2), (nx - 90 - 16 * (j % 4), ny - 40 - 22 * (j % 4) + 14 * (j // 4))], suave=False),
                   r=16, amp=0, curva="out", cresce=1.3, fim=q(5.95), fase=j) for j in range(8)]
    ar.append(P.camada_bolhas("AR_VOCE", specs2, (nx - 420, ny - 260, nx + 60, ny + 120), q(4.9), q(5.95)))

    # ================================================================== B3 (5,88–9,52): a pele sai, os músculos saem e o ar explode
    folha("FOLHA_3", FC, (178, 196, 206), q(5.4), q(10.15), 4)
    fig += interior("base", q(6.1), q(10.3))
    musc_img = K.descasca(G.camada("base", "musc"), q(6.95), q(7.65), "direita", 22)
    fig.append(fl("musc", "base", q(6.1), q(7.78), img=musc_img, sombra=(8, 16, 0.28)))
    pele_img = K.descasca(G.camada("base", "pele"), q(6.15), q(6.85), "esquerda", 21)
    fig.append(fl("pele", "base", q(5.70), q(6.98), img=pele_img, sombra=(10, 22, 0.28), boil="paper"))
    R_N = rota("traq", "nariz", "fora_nariz")
    R_B = rota("traq", "boca", "fora_boca")
    specs3 = []
    for i in range(20):
        tr, t0 = (R_N if i % 3 else R_B), q(7.55) + int(round(1.9 * i))
        specs3.append(dict(t0=t0, t1=t0 + 34, trilha=tr, r=rng.uniform(11, 15), amp=rng.uniform(2, 4), ciclos=1.5, fase=rng.uniform(0, 6.28),
                           some=4, curva="in", cresce=1.7))
    qb = q(8.85)                                            # a explosão: o ar sai pelo nariz e pela boca
    for (px, py), a0, a1, n in ((Wp(*NARINA), -38, 22, 18), (Wp(*BOCA_P), -14, 52, 15)):
        for i in range(n):
            ang = math.radians(rng.uniform(a0, a1))
            dist = rng.uniform(170, 520)
            alvo = (px + dist * math.cos(ang), py + dist * math.sin(ang) * 0.9)
            t0 = qb + int(rng.integers(0, 6))
            specs3.append(dict(t0=t0, t1=t0 + int(rng.integers(14, 24)), trilha=P.Trilha([(px, py), alvo], suave=False), r=rng.uniform(15, 27),
                               cresce=rng.uniform(1.5, 2.4), curva="out", some=8, fase=i))
    # depois da explosão o ar continua saindo, mais fraco, pelo nariz e pela boca (até o nariz ser tapado)
    for i in range(4):
        tr, t0 = (R_N if i % 2 == 0 else R_B), q(9.45) + 6 * i
        specs3.append(dict(t0=t0, t1=t0 + 34, trilha=rota("traq", "nariz" if i % 2 == 0 else "boca", "fora_nariz" if i % 2 == 0 else "fora_boca",
                                                          a_partir_de=1.436),
                           r=rng.uniform(9, 12), amp=2.5, ciclos=1.5, fase=i, some=4, cresce=1.7))
    ar.append(P.camada_bolhas("AR_ESPIRRO", specs3, caixa_trilhas([R_N, R_B], 80), q(7.4), q(10.55)))
    ar.append(C.rajada("RAJ_NARIZ", xn, yn, qb, raio=330, n=16, dur=10, espessura=12, fim=qb + 14))
    ar.append(C.rajada("RAJ_BOCA", xb, yb, qb + 1, raio=270, n=12, dur=10, espessura=11, fim=qb + 15, semente=9))

    # ================================================================== B4a (10,14–11,50): tapar o nariz e a boca (rolha e tampa)
    folha("FOLHA_4A", FC, (200, 218, 190), q(9.5), q(11.62), 5)
    fig += interior("meio", q(9.5), q(17.8))
    rol = P2.rolha(120, 84)
    rol_c = C.desliza("ROLHA", rol, q(10.40), (xn + 340, yn + 6), (xn + 22, yn + 8), rot=0.0, dur=7, sombra=(6, 10, 0.3), boil="paper", fim=q(22.8), esc=0.62)
    rol_c.tam = rol.size
    tam_ = P2.tampa(96, 170)
    tam_c = C.desliza("TAMPA", tam_, q(10.95), (xb + 330, yb + 4), (xb - 4, yb + 4), rot=0.0, dur=7, sombra=(6, 10, 0.3), boil="paper", fim=q(22.8), esc=0.55)
    tam_c.tam = tam_.size
    # o ar chega em fila e para atrás da rolha e da tampa
    Rn_in, Rb_in = rota("nariz"), rota("boca")
    fila_n = P2.fila_specs(Rn_in, 26, 8.5, q(10.15), 2.0, 18, gap=1.9, amp=5.0, fim=q(22.7), encolhe=7)
    fila_b = P2.fila_specs(Rb_in, 14, 8.5, q(10.75), 2.0, 14, gap=1.9, amp=4.0, fim=q(22.7), fase0=2.0, encolhe=7)
    ar.append(P.camada_bolhas("FILA_AR", fila_n + fila_b, caixa_trilhas([Rn_in, Rb_in], 50), q(10.1), q(22.8)))
    ar.append(rol_c)
    ar.append(tam_c)
    # o ar que sai antes de fechar
    # (o resto do ar da cena anterior, que ainda passa pelo nariz e pela boca)

    # ================================================================== B4b (11,52–13,64): a mangueira dobra
    mg = P.Mangueira("MANGUEIRA", MANG_O, q(11.3), q(11.82), q(13.92))
    folha("FOLHA_MANGUEIRA", (MANG_O[0] + 520, MANG_O[1] + 560), (236, 222, 166), q(11.2), q(13.95), 8)
    ar.append(mg.camada)
    tq = P.torneira().resize((286, 231), Image.LANCZOS)
    ar.append(fixo("TORNEIRA", tq, ini=q(11.3), fim=q(13.92), x=MANG_O[0] + 13 + 143, y=MANG_O[1] - 41 + 115, sombra=(6, 12, 0.26), boil="paper"))
    S_mang = C.quadro((MANG_O[0] - 30, MANG_O[1] - 130, MANG_O[0] + 1090, MANG_O[1] + 1160), (30, 110, 1050, 1810))

    # o manômetro (a pressão) vive na tela, no canto, da mangueira até o POP
    gf = P.relogio_pressao(250, rotulo=False)
    g = M.Camada("MANOMETRO", gf, q(12.7), q(41.9), ancora=(gf.tam[0] / 2, gf.tam[1] / 2), mundo=False, boil="paper", sombra=(6, 12, 0.3), chaves={
        "x": C.k((q(12.7), 165, "segura")), "y": C.k((q(12.7), 330, "segura")),
        "s": [(q(12.7) + a_, v, cv) for a_, v, cv in C.POP],
        "op": C.k((q(12.7), 0.0, "lin"), (q(12.7) + 2, 1.0, "segura"), (q(22.6), 1.0, "lin"), (q(22.9), 0.0, "segura"),
                  (q(38.95), 0.0, "lin"), (q(39.05), 1.0, "segura"), (q(41.45), 1.0, "lin"), (q(41.65), 0.0, "segura")),
        "trim": C.k((q(12.7), 0.0, "io"), (q(13.6), 0.42, "segura"), (q(13.9), 0.42, "io"), (q(16.5), 0.97, "segura"),
                    (q(22.55), 0.97, "io"), (q(22.9), 0.0, "segura"),
                    (q(38.95), 0.97, "io"), (q(40.4), 0.0, "segura"))})
    g.tam = gf.tam
    g.som = ("pouso", q(12.7) + 5)
    ui.append(g)

    # ================================================================== B5 (13,82–17,22): a pressão procura o ponto mais fraco
    folha("FOLHA_5", FC, (240, 214, 170), q(13.4), q(17.8), 6)
    fig += interior("base", q(13.4), q(17.8))
    vq = fl("via_quente", "base", q(13.4), q(17.8), img=via_quente("base"))
    vq.chaves["op"] = C.k((q(13.4), 0.0, "lin"), (q(13.86), 0.0, "lin"), (q(16.7), 0.92, "segura"), (q(17.8), 0.92, "segura"))
    fig.append(vq)
    # a rolha e a tampa continuam no lugar (as camadas da cena 4a seguem até q(17.4))
    # o ar vem dos pulmões e entope o caminho: a fila cresce de cima para baixo na traqueia
    Rt = rota("traq")
    fila_t = P2.fila_specs(Rt, 26, 8.0, q(13.9), 4.0, 22, gap=1.9, amp=3.0, fim=q(22.7), fase0=4.0, encolhe=7)
    ar.append(bolhas_hi("FILA_TRAQ", fila_t, caixa_trilhas([Rt], 50), q(13.8), q(22.8), K=3))
    # a caneta procura: roda pelas paredes e para no bolsinho
    busca = [Wp(-0.100, 1.567), Wp(-0.062, 1.574), Wp(-0.036, 1.568), Wp(-0.0205, 1.548), Wp(-0.0215, 1.526), Wp(-0.0225, 1.510),
             Wp(-0.0200, 1.496), Wp(-0.0150, 1.4830)]
    ar.append(traco_hi("BUSCA", busca, q(15.52), q(16.55), 7, fim=q(17.28), semente=7, tremor=0.8, K=2, suave=True))
    ar.append(circulo_cor("CIRCULO_FRACO", xp, yp, 46, 62, q(16.6), q(17.15), 8, q(17.28)))

    # ================================================================== B6 (17,74–21,48): o cantinho da garganta, sem músculo de reforço
    folha("FOLHA_6", FC, (190, 206, 222), q(17.2), q(23.6), 9)
    fig += interior("alto", q(17.2), q(23.6), nomes=("cama", "osso", "via"), fo=6)
    mus_al = fl("faringe", "alto", q(17.2), q(23.6), fo=6, sombra=(8, 16, 0.3))
    x0m, y0m = mus_al.chaves["x"][0][1], mus_al.chaves["y"][0][1]
    mus_al.chaves["x"] = C.k((q(17.2), x0m + 1500, "segura"))
    mus_al.chaves["y"] = C.k((q(17.2), y0m - 900, "segura"))
    mus_al.chaves["rot"] = C.k((q(17.2), 16.0, "segura"))
    mus_al.chaves["op"] = C.k((q(17.2), 0.0, "lin"), (q(19.9), 0.0, "lin"), (q(19.95), 1.0, "segura"), (q(23.2), 1.0, "lin"), (q(23.6), 0.0, "segura"))
    K.pousa(mus_al, q(19.95), q(20.55), para=(x0m, y0m), rot=0.0)
    mus_al.som = ("pouso", q(20.5))
    fig.append(mus_al)
    ar.append(circulo_hi("CIRCULO_BOLSO", xp, yp, 36, 50, q(18.85), q(19.5), 6, q(20.6)))
    ar.append(circulo_hi("CIRCULO_BOLSO2", xp, yp, 40, 54, q(20.75), q(21.3), 6, q(22.7), rot=3))

    # ================================================================== B7 (21,70–26,06): o estalo no pescoço; horas depois, dói engolir
    q_pop = q(22.62)
    ar.append(C.rajada("RAJ_POP", xp, yp, q_pop, raio=250, n=14, dur=9, espessura=12, fim=q_pop + 12))
    crack = [Wp(-0.0170, 1.4950), Wp(-0.0135, 1.4880), Wp(-0.0160, 1.4820), Wp(-0.0120, 1.4750), Wp(-0.0145, 1.4690)]
    ar.append(traco_hi("FENDA_BOLSO", crack, q_pop + 4, q_pop + 10, 7, fim=q(26.2), semente=3, tremor=0.6))
    # o ar vaza: para trás, desce pelo vão atrás do esôfago e se espalha no peito
    Rv = rota("vaza")
    leak = []
    fins = np.linspace(q(31.4), q(33.9), 40)
    for i in range(40):
        t0 = q_pop + 8 + 2 * i
        yf, zf = rng.uniform(-0.040, 0.030), rng.uniform(1.296, 1.340)
        trv = P.Trilha([Wp(*p_) for p_ in CAM_ATLAS["vaza"]] + [Wp(yf, zf)])
        dur = int(trv.L / 4.6)
        leak.append(dict(t0=t0, t1=t0 + dur, trilha=trv, r=5.2, amp=1.2, ciclos=2, fase=i * 1.9, cresce=2.9, curva="io", fim=int(fins[i]), encolhe=10))
    ar.append(bolhas_hi("AR_VAZA", leak, caixa_trilhas([P.Trilha([Wp(*p_) for p_ in CAM_ATLAS["vaza"]] + [Wp(-0.04, 1.296), Wp(0.03, 1.296)])], 60),
                         q_pop, q(34.3), K=2))
    # as horas passam: o relógio entra no canto da tela, no lugar do manômetro
    rh = P.relogio_horas(250)
    rel = M.Camada("RELOGIO_H", rh, q(24.2), q(26.1), ancora=(rh.tam[0] / 2, rh.tam[1] / 2), mundo=False, boil="paper", sombra=(6, 12, 0.3), chaves={
        "x": C.k((q(24.2), 165, "segura")), "y": C.k((q(24.2), 330, "segura")),
        "s": [(q(24.2) + a_, v, cv) for a_, v, cv in C.POP], "rot": C.k((q(24.2), -4.0, "segura")),
        "op": C.k((q(24.2), 0.0, "lin"), (q(24.2) + 2, 1.0, "segura"), (q(26.0), 1.0, "lin"), (q(26.1), 0.0, "segura")),
        "trim": C.k((q(24.2), 0.0, "io"), (q(24.95), 1.0, "segura"))})
    rel.tam = rh.tam
    ui.append(rel)
    # engolir dói: o risco na garganta
    zig = [Wp(-0.0090, 1.4950), Wp(-0.0045, 1.4890), Wp(-0.0100, 1.4830), Wp(-0.0050, 1.4770), Wp(-0.0105, 1.4710), Wp(-0.0055, 1.4650)]
    ar.append(traco_hi("RISCO_ENGOLIR", zig, q(25.3), q(25.95), 6, fim=q(26.3), semente=9, tremor=1.0))

    # ================================================================== B8 (26,42–29,80): o ar desce do pescoço ao peito
    fig += interior("meio", q(23.0), q(27.0), fi=6, fo=6)
    fig += interior("peito", q(26.6), q(30.2), fi=6)
    folha("FOLHA_7", FC, (212, 224, 196), q(23.4), q(30.2), 10)

    # ================================================================== B9 (30,00–34,34): internado, sonda, recuperou
    folha("FOLHA_9", FC, (238, 208, 190), q(29.9), q(34.7), 12)
    fig += interior("base", q(29.8), q(34.8), fi=4)
    S_amplo = QA(caixa_atlas(-0.245, 0.12, 1.19, 1.74))
    cruz = P2.cruz_hospital(360)
    cx_, cy_ = Wp(-0.205, 1.64)
    crz = C.cai("CRUZ_HOSPITAL", cruz, q(30.1), cx_, cy_, rot=-4, de_y=-260, esc=0.9, sombra=(8, 16, 0.28), boil="paper", fim=q(34.8))
    crz.tam = cruz.size
    ar.append(crz)
    sonda = [Wp(-0.1125, 1.560), Wp(-0.080, 1.572), Wp(-0.045, 1.570), Wp(-0.0215, 1.545), Wp(-0.017, 1.520), Wp(-0.011, 1.495),
             Wp(-0.006, 1.468), Wp(-0.0024, 1.436), Wp(0.0064, 1.40), Wp(0.0145, 1.361), Wp(0.021, 1.32), Wp(0.0275, 1.26), Wp(0.032, 1.20)]
    ar.append(C.Traco("SONDA", sonda, q(31.7), q(33.0), espessura=9, cor=(96, 150, 214), suave=True, fim=q(34.8), semente=5, tremor=0.8).camada)
    certo = [Wp(-0.215, 1.325), Wp(-0.198, 1.300), Wp(-0.160, 1.355)]
    ar.append(C.Traco("CERTO", certo, q(33.75), q(34.2), espessura=17, cor=(64, 148, 92), fim=q(34.8), semente=8, tremor=0.5).camada)

    # ================================================================== B10 (34,62–38,66): a traqueia racha; o som não chega
    fim10 = q(37.8) if OUVIDO else q(39.1)                           # sem o ouvido, a traqueia fica até o rasgo da cena 11
    folha("FOLHA_10", FC, (206, 224, 200), q(34.2), fim10 + 6, 13)
    fig += interior("alto", q(34.2), fim10, nomes=("cama", "osso", "via"))
    S_trq = QA(caixa_atlas(-0.034, 0.034, 1.410, 1.470))
    Rtr = rota("traq", a_partir_de=1.375)
    sp_t = []
    for j in range(9):
        t0 = q(34.75) + 5 * j
        sp_t.append(dict(t0=t0, t1=t0 + 30, trilha=Rtr, r=6.5, amp=2.5, fase=j * 1.7, some=4))
    ar.append(bolhas_hi("AR_TRAQUEIA", sp_t, caixa_trilhas([Rtr], 50), q(34.7), q(37.7), K=3))
    fenda = [Wp(-0.0170, 1.4275), Wp(-0.0120, 1.4315), Wp(-0.0075, 1.4255), Wp(-0.0030, 1.4300), Wp(0.0010, 1.4240), Wp(0.0045, 1.4275)]
    ar.append(traco_hi("FENDA_TRAQ", fenda, q(36.72), q(37.05), 6, fim=q(37.8), semente=3, tremor=0.5))
    fuga = P.Trilha([Wp(0.0045, 1.4275), Wp(0.0085, 1.4220), Wp(0.0120, 1.4140)], suave=False)
    sp_f = [dict(t0=q(37.0) + 3 * j, t1=q(37.0) + 3 * j + 18, trilha=fuga, r=4.5, cresce=1.6, some=5, fase=j) for j in range(4)]
    ar.append(bolhas_hi("AR_FENDA", sp_f, caixa_trilhas([fuga], 40), q(36.95), q(37.8), K=3))

    # --- o ouvido (cena 10b, OPCIONAL: licença não comercial, ver ouvido_blender.py): o pavilhão sai, aparecem o tímpano,
    #     os ossinhos e a cóclea; o som chega e cai
    if OUVIDO:
        S_ouv1, S_ouv2 = cena_ouvido(fig, ar, folha)

    # ================================================================== B11 (39,02–41,38): deixar o espirro sair
    folha("FOLHA_11", FC, (178, 196, 206), q(38.6), q(41.75), 15)
    fig += interior("base", q(38.55), q(41.8), fi=3)
    sp11 = []
    q11 = q(39.58)
    for (px, py), a0, a1, n in ((Wp(*NARINA), -38, 22, 16), (Wp(*BOCA_P), -14, 52, 13)):
        for i in range(n):
            ang = math.radians(rng.uniform(a0, a1))
            dist = rng.uniform(170, 520)
            alvo = (px + dist * math.cos(ang), py + dist * math.sin(ang) * 0.9)
            t0 = q11 + int(rng.integers(0, 6))
            sp11.append(dict(t0=t0, t1=t0 + int(rng.integers(14, 24)), trilha=P.Trilha([(px, py), alvo], suave=False), r=rng.uniform(14, 25),
                             cresce=rng.uniform(1.5, 2.3), curva="out", some=8, fase=i))
    for i in range(9):
        t0 = q(39.9) + 7 * i
        sp11.append(dict(t0=t0, t1=t0 + 34, trilha=rota("traq", "nariz" if i % 2 == 0 else "boca", "fora_nariz" if i % 2 == 0 else "fora_boca",
                                                         a_partir_de=1.436), r=rng.uniform(9, 12), amp=2.5, ciclos=1.5, fase=i, some=4, cresce=1.7))
    ar.append(P.camada_bolhas("AR_SAI", sp11, caixa_trilhas([R_N, R_B], 80), q(39.5), q(41.8)))
    ar.append(C.rajada("RAJ_SAI_N", xn, yn, q11, raio=330, n=16, dur=10, espessura=12, fim=q11 + 14, semente=5))
    ar.append(C.rajada("RAJ_SAI_B", xb, yb, q11 + 1, raio=270, n=12, dur=10, espessura=11, fim=q11 + 15, semente=9))

    # ================================================================== B12 (41,64–45,86): lenço, cotovelo e o que NÃO fazer
    folha("FOLHA_12", FC, (238, 214, 200), q(41.3), q(46.35), 16)
    pele12 = K.descasca(G.camada("base", "pele"), 0, 1, "esquerda", 31, volta=(q(41.45), q(41.95)))
    fig.append(fl("pele", "base", q(41.3), q(52.3), img=pele12, sombra=(10, 22, 0.28), boil="paper"))
    S_f12 = QA(caixa_atlas(-0.225, 0.125, 1.30, 1.74))
    len_ = P.lenco(470)
    xl, yl = Wp(-0.142, 1.538)
    lnc = C.desliza("LENCO", len_, q(41.95), (xl + 360, yl + 30), (xl, yl), rot=-6, dur=7, sombra=(8, 16, 0.28), boil="paper", fim=q(42.5), esc=0.62)
    lnc.tam = len_.size
    ar.append(lnc)
    sp12 = []
    for j in range(8):
        t0 = q(42.0) + 4 * j
        sgn = -1 if j % 2 == 0 else 1
        sp12.append(dict(t0=t0, t1=t0 + 22, trilha=P.Trilha([Wp(-0.118, 1.545), (xl - 30 + 10 * j, yl + sgn * 110), (xl + 40 + 24 * j, yl + sgn * 210)]),
                         r=rng.uniform(10, 14), amp=2, cresce=1.6, fase=j, some=5))
    ar.append(P.camada_bolhas("AR_LENCO", sp12, (xl - 300, yl - 400, xl + 420, yl + 400), q(41.95), q(42.6)))
    brc, bd = P2.braco_perfil(700, 250)
    X0 = Wp(-0.126, 1.5)[0]
    xa = X0 + (brc.width / 2 - bd["barra_esq"])
    ya = Wp(0, 1.395)[1] - (bd["base_y"] - brc.height / 2)
    arm = C.desliza("BRACO", brc, q(42.4), (xa + 420, ya + 120), (xa, ya), rot=0.0, dur=7, sombra=(8, 16, 0.28), boil="paper", fim=q(43.6), esc=1.0)
    arm.tam = brc.size
    ar.append(arm)
    sp12b = []
    for j in range(10):
        t0 = q(42.8) + 4 * j
        sgn = -1 if j % 2 == 0 else 1
        sp12b.append(dict(t0=t0, t1=t0 + 24, trilha=P.Trilha([Wp(-0.118, 1.545), (X0 - 20 + 8 * j, ya - 100 * 0 + sgn * 120 - 150), (X0 + 120 + 20 * j, ya + sgn * 240 - 150)]),
                          r=rng.uniform(10, 14), amp=2, cresce=1.6, fase=j, some=5))
    ar.append(P.camada_bolhas("AR_BRACO", sp12b, (X0 - 300, ya - 700, X0 + 520, ya + 700), q(42.75), q(43.6)))
    # o que NÃO fazer: a rolha e a tampa de novo, e o X
    xn2, yn2 = Wp(-0.0985, 1.5515)
    rol2 = C.desliza("ROLHA2", rol, q(44.40), (xn2 + 340, yn2 + 160), (xn2 + 30, yn2 + 21), rot=35.0, dur=7, sombra=(6, 10, 0.3), boil="paper", fim=q(46.3), esc=0.62)
    rol2.tam = rol.size
    tam2 = C.desliza("TAMPA2", tam_, q(45.05), (xb + 330, yb + 4), (xb - 4, yb + 4), rot=0.0, dur=7, sombra=(6, 10, 0.3), boil="paper", fim=q(46.3), esc=0.55)
    tam2.tam = tam_.size
    ar += [rol2, tam2]
    xx, yy_ = (xn + xb) / 2 + 40, (yn + yb) / 2 + 10
    for k_, (d1, d2) in enumerate((((-125, -170), (125, 170)), ((125, -170), (-125, 170)))):
        ar.append(C.Traco(f"X_NAO_{k_}", [(xx + d1[0], yy_ + d1[1]), (xx + d2[0], yy_ + d2[1])], q(45.7) + 5 * k_, q(45.7) + 5 * k_ + 6, espessura=18, cor=VERM,
                          fim=q(46.35), semente=3 + k_, tremor=0.0).camada)

    # ================================================================== B13 (46,32–51,20): os três sinais, marcados no corpo
    folha("FOLHA_13", FC, (240, 230, 176), q(45.9), q(51.4), 17)
    gx, gy = Wp(-0.0150, 1.4700)
    ar.append(circulo_cor("CIRCULO_DOR", gx, gy, 90, 112, q(46.55), q(47.1), 8, q(51.2), cor=VERM))
    for nome, sg, (ya_, za_) in (("INCHA_F", 1, (-0.040, 1.470)), ("INCHA_T", -1, (0.040, 1.465))):
        ex, ey = Wp(ya_, za_)
        ar.append(C.Traco(nome, [(ex + sg * 40, ey - 80), (ex + sg * 90, ey), (ex + sg * 40, ey + 80)], q(47.6), q(48.1), espessura=9, cor=VERM, suave=True, fim=q(51.2),
                          semente=4).camada)
    ar.append(C.rajada("RAJ_ESTALA", gx - 10, gy - 20, q(48.76), raio=190, n=12, dur=8, espessura=9, fim=q(48.76) + 12, cor=(250, 240, 220)))
    ex_, ey_ = Wp(0.0055, 1.585)                                       # a orelha
    ond = C.ondas("ONDAS_OUVIDO", ex_ + 200, ey_ + 10, q(49.55), q(50.4), raio=210, n=3, cor=VERM, espessura=9, periodo=12)
    f_o = ond.fonte
    ond.fonte = lambda fd, p: ImageOps.mirror(f_o(fd, p))
    ar.append(ond)
    ar.append(C.Traco("OUVIDO_RETO", [(ex_ + 70, ey_ + 14), (ex_ + 160, ey_ + 14)], q(50.42), q(50.7), espessura=9, cor=VERM, fim=q(51.2), semente=3, tremor=0.0).camada)

    # ================================================================== o fecho (51,26–52,56): o tchau do homem e a cruz do hospital
    q_tchau = q(51.2)

    def homem_fim(fd, p):
        n = "repouso"
        for i, nome in enumerate(["meio", "alto", "meio", "alto", "meio"]):
            if fd >= q_tchau + P7 * i:
                n = nome
        if fd >= q_tchau + P7 * 5:
            n = "repouso"
        return poses[n]
    homem_fim.tam = TAM
    ar.append(fixo("HOMEM_FIM", homem_fim, ini=q(50.95), sombra=(10, 22, 0.28), boil="paper"))
    cx_h, cy_h = 1430, 420
    ar.append(C.circulo("CIRCULO_HOSPITAL", cx_h, cy_h, 100, 100, q(51.5), q(51.95), espessura=12, fim=Q_CRED))
    for k_, (p0, p1) in enumerate((((cx_h - 52, cy_h), (cx_h + 52, cy_h)), ((cx_h, cy_h - 52), (cx_h, cy_h + 52)))):
        ar.append(C.Traco(f"CRUZ_{k_}", [p0, p1], q(51.95) + 4 * k_, q(51.95) + 4 * k_ + 4, espessura=18, cor=PC.VERMELHO, fim=Q_CRED, semente=6 + k_,
                          tremor=0.0).camada)
    ui.append(creditos_card(Q_CRED))

    # ------------------------------------------------------------------ a câmera
    cam = C.Camera()
    cam.plano(0, S1, "segura")
    cam.plano(q(3.40), S_reuniao, "segura")
    cam.plano(q(5.90), S_inteiro, "segura")
    cam.plano(q(7.8), S_inteiro, "io").plano(q(8.6), S_cab, "segura")
    cam.plano(q(10.10), S_rosto, "segura")
    cam.plano(q(11.52), S_mang, "segura")
    cam.plano(q(13.86), S_cab2, "segura")
    cam.plano(q(16.0), S_cab2, "io").plano(q(17.25), S_pesc, "segura")
    cam.plano(q(17.70), S_lar, "segura")
    for dq, dz, dx, dy in ((0, 1.10, 8, -6), (2, 1.03, -6, 4), (4, 1.07, 4, -3), (6, 1.04, -2, 2)):          # o POP: tranco de câmera
        cam.plano(q_pop + dq, (S_lar[0] * dz, S_lar[1] + dx, S_lar[2] + dy), "segura")
    cam.plano(q_pop + 9, S_lar, "segura")
    cam.plano(q(23.3), S_lar, "io").plano(q(24.6), S_pesc2, "segura")
    cam.plano(q(25.6), S_pesc2, "io").plano(q(26.42), S_d1, "segura")
    cam.plano(q(27.1), S_d1, "io").plano(q(28.2), S_d2, "segura")
    cam.plano(q(28.7), S_d2, "io").plano(q(29.4), S_d3, "segura")
    cam.plano(q(30.05), S_amplo, "segura")
    cam.plano(q(34.62), S_trq, "segura")
    if OUVIDO:
        cam.plano(q(37.72), S_ouv1, "segura")
        cam.plano(q(38.2), S_ouv1, "io").plano(q(38.6), S_ouv2, "segura")
    cam.plano(q(39.0), S_cab, "segura")
    cam.plano(q(41.66), S_f12, "segura")
    cam.plano(q(46.2), S_cab2, "segura")
    cam.plano(q(51.3), S1, "segura")
    transicoes += [
        M.Transicao(q(3.14), q(3.40), "empurra", direcao=(-1, 0)),
        M.Transicao(q(5.68), q(5.90), "iris", centro=(540, 800)),
        M.Transicao(q(9.60), q(10.10), "rasgo", semente=5),
        M.Transicao(q(11.30), q(11.52), "empurra", direcao=(-1, 0)),
        M.Transicao(q(13.64), q(13.86), "iris", centro=(540, 700)),
        M.Transicao(q(17.30), q(17.70), "rasgo", semente=9),
        M.Transicao(q(29.85), q(30.05), "iris", centro=(540, 760)),
        M.Transicao(q(34.34), q(34.62), "empurra", direcao=(0, -1)),
        M.Transicao(q(38.66), q(39.0), "rasgo", semente=15),
        M.Transicao(q(41.40), q(41.66), "iris", centro=(540, 700)),
        M.Transicao(q(45.9), q(46.2), "iris", centro=(540, 760)),
        M.Transicao(q(51.0), q(51.3), "empurra", direcao=(1, 0)),
    ]
    if OUVIDO:
        transicoes.append(M.Transicao(q(37.45), q(37.72), "iris", centro=(540, 900)))
    c = sheets + fig + ar + ui
    c.append(C.vinheta(FIM))
    return c, cam, transicoes


# ------------------------------------------------------------------ som
SR_E = 44100


def _bp(x, lo, hi):
    """passa-banda por FFT (janela suave)"""
    f = np.fft.rfftfreq(len(x), 1 / SR_E)
    X = np.fft.rfft(x)
    m = np.clip((f - lo) / (lo * 0.4 + 1), 0, 1) * np.clip((hi - f) / (hi * 0.4 + 1), 0, 1)
    return np.fft.irfft(X * m, len(x))


def pop_bolha(f0, f1, dur, seed):
    """uma bolinha: seno que sobe de f0 a f1 e some em poucos ms, com um toque de ruído no começo"""
    rng = np.random.default_rng(seed)
    n = int(SR_E * dur)
    tt = np.arange(n) / SR_E
    f = f0 + (f1 - f0) * (tt / dur)
    fase = 2 * np.pi * np.cumsum(f) / SR_E
    x = np.sin(fase) * np.exp(-tt / (dur / 3.2))
    x += rng.normal(0, 1, n) * np.exp(-tt / 0.002) * 0.25
    return x / np.abs(x).max()


def sopro(dur, lo, hi, seed, subida=0.6, curva=1.6):
    """ar passando: ruído passa-banda com um swell (sobe até 'subida' da duração e desce)"""
    rng = np.random.default_rng(seed)
    n = int(SR_E * dur)
    x = _bp(rng.normal(0, 1, n), lo, hi)
    u = np.linspace(0, 1, n)
    env = np.where(u < subida, (u / subida) ** curva, ((1 - u) / (1 - subida)) ** 1.2)
    x = x * env
    return x / np.abs(x).max()


def rangido(dur, seed):
    """a mangueira dobrando: um guincho que cai de 1100 a 520 Hz, com tremor, mais um 'tump' grave"""
    rng = np.random.default_rng(seed)
    n = int(SR_E * dur)
    tt = np.arange(n) / SR_E
    f = 1100 - 580 * (tt / dur) ** 0.7 + 25 * np.sin(2 * np.pi * 31 * tt)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR_E) * np.exp(-tt / (dur * 0.7))
    x += _bp(rng.normal(0, 1, n), 700, 3000) * 0.35 * np.exp(-tt / (dur * 0.5))
    return x / np.abs(x).max()


def estalo_seco(freq, seed):
    """o POP do pescoço: clique seco + tom agudo + baque grave (como o estalo do reel dos dedos, mais fechado)"""
    rng = np.random.default_rng(seed)
    n = int(SR_E * 0.18)
    tt = np.arange(n) / SR_E
    ruido = np.convolve(rng.normal(0, 1, n) * np.exp(-tt / 0.0022), [1, -0.95], mode="same")
    x = ruido * 0.9 + np.sin(2 * np.pi * freq * tt) * np.exp(-tt / 0.009) * 0.7 + \
        np.sin(2 * np.pi * (freq / 14.0) * tt) * np.exp(-tt / 0.03) * 0.8
    return x / np.abs(x).max()


def tique_seco(seed, f=3200):
    n = int(SR_E * 0.02)
    tt = np.arange(n) / SR_E
    x = np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.004) + np.random.default_rng(seed).normal(0, 1, n) * np.exp(-tt / 0.0015) * 0.3
    return x / np.abs(x).max()


def faixa_extras(saida, dur):
    """os sons que as imagens pedem e a biblioteca não tem: bolinhas, sopro do ar, o guincho da mangueira, o POP, o tique do
    relógio. t = instante da VOZ (s); na faixa, + 10/24 s (a voz entra no quadro 10)"""
    import wave
    x = np.zeros(int(SR_E * dur))
    rng = np.random.default_rng(31)
    off = 10 / 24

    def poe(s, tv, g=1.0):
        a = int(round((tv + off) * SR_E))
        if a < 0 or a >= len(x):
            return
        b = min(len(x), a + len(s))
        x[a:b] += s[: b - a] * g
    # cena 3: o ar sobe e o POOF no nariz
    poe(sopro(1.3, 500, 2600, 1, subida=0.9, curva=2.2), 7.55, 0.55)
    poe(sopro(0.34, 400, 4200, 2, subida=0.15, curva=1.0), 8.83, 0.9)
    for i in range(6):
        poe(pop_bolha(500 + 60 * i, 1100 + 80 * i, 0.07, 10 + i), 8.87 + 0.045 * i, 0.5)
    poe(sopro(1.2, 350, 3200, 3, subida=0.3), 9.45, 0.16)
    # B4a: a rolha entra no nariz e a tampa fecha a boca (um 'tum' seco), e o ar se amontoa
    poe(pop_bolha(170, 80, 0.12, 21), 10.64, 0.85)
    poe(pop_bolha(150, 70, 0.12, 22), 11.16, 0.85)
    for i, tv in enumerate((10.9, 11.05, 11.2, 11.3, 11.4)):
        poe(pop_bolha(420 + 40 * i, 640 + 50 * i, 0.05, 25 + i), tv, 0.22)
    # cena 4b: a mangueira dobra e a água se amontoa
    poe(rangido(0.30, 3), 11.82, 0.75)
    poe(pop_bolha(120, 70, 0.14, 4), 11.86, 0.9)
    for i, tv in enumerate((12.15, 12.42, 12.66, 12.9, 13.12, 13.34)):
        poe(pop_bolha(420 + 40 * i, 640 + 50 * i, 0.06, 30 + i), tv, 0.3)
    # cena 5: a pressão sobe (um chiado fino que cresce) e fica
    poe(sopro(3.4, 2400, 7000, 5, subida=0.92, curva=2.4), 13.95, 0.20)
    # cena 7: o POP, o tique do relógio, o risco na garganta
    poe(estalo_seco(1900, 6), 22.60, 1.0)
    poe(pop_bolha(160, 90, 0.16, 7), 22.62, 0.7)
    for i in range(9):
        poe(tique_seco(40 + i), 24.30 + 0.075 * i, 0.30)
    # cena 8: o ar escorre pelo pescoço e vai para o peito (bolhinhas esparsas)
    tt = np.sort(rng.uniform(23.4, 30.0, 22))
    for i, tv in enumerate(tt):
        poe(pop_bolha(rng.uniform(420, 700), rng.uniform(700, 1100), 0.055, 50 + i), float(tv), 0.26)
    poe(sopro(2.4, 300, 1500, 8, subida=0.4), 26.5, 0.18)
    # cena 10: a fenda rachando, as ondas do som e o silêncio
    poe(tique_seco(70, 2400), 36.76, 0.5)
    poe(estalo_seco(2300, 8), 36.90, 0.30)
    for i, tv in enumerate((38.10, 38.26, 38.42, 38.56)):
        poe(pop_bolha(900, 760 - 60 * i, 0.12, 80 + i), tv, 0.22 - 0.04 * i)
    # B10: o monitor do hospital e, depois, o ar diminuindo
    for i, tv in enumerate((30.35, 30.95, 31.55)):
        n_ = int(SR_E * 0.075)
        tt_ = np.arange(n_) / SR_E
        poe(np.sin(2 * np.pi * 880 * tt_) * np.exp(-tt_ / 0.05), tv, 0.30)
    # B12: o espirro sai livre (a explosão de bolinhas) e o sopro
    poe(sopro(0.34, 400, 4200, 22, subida=0.15, curva=1.0), 39.58, 0.9)
    for i in range(6):
        poe(pop_bolha(500 + 60 * i, 1100 + 80 * i, 0.07, 110 + i), 39.64 + 0.045 * i, 0.5)
    poe(sopro(1.7, 350, 3200, 9, subida=0.35), 39.95, 0.22)
    for i, tv in enumerate(np.sort(rng.uniform(40.0, 41.3, 5))):
        poe(pop_bolha(rng.uniform(450, 650), rng.uniform(700, 1000), 0.06, 90 + i), float(tv), 0.2)
    # B13: o ar passa pelos lados do lenço e do cotovelo; depois a rolha e a tampa de novo, com o X
    poe(pop_bolha(170, 80, 0.12, 121), 44.46, 0.75)
    poe(pop_bolha(150, 70, 0.12, 122), 45.11, 0.75)
    for i, tv in enumerate((45.78, 45.88)):
        poe(tique_seco(130 + i, 2200), tv, 0.45)
    for i, tv in enumerate(np.sort(rng.uniform(42.0, 43.5, 6))):
        poe(pop_bolha(rng.uniform(450, 650), rng.uniform(700, 1000), 0.06, 120 + i), float(tv), 0.16)
    # B14: o estalo, as ondas que chegam ao ouvido e o som que cai
    poe(estalo_seco(2100, 15), 48.76, 0.35)
    for i, tv in enumerate((49.60, 49.76, 49.92, 50.08)):
        poe(pop_bolha(900, 740 - 60 * i, 0.12, 130 + i), tv, 0.22 - 0.04 * i)
    # nível: o pico (RMS de 30 ms) fica em −37 dBFS, ~17 dB abaixo da voz normalizada
    h, w = int(0.01 * SR_E), int(0.03 * SR_E)
    rms = max(np.sqrt(np.mean(x[i:i + w] ** 2)) for i in range(0, len(x) - w, h) if True)
    x = x / max(rms, 1e-9) * 10 ** (-37 / 20)
    x = np.clip(x, -0.5, 0.5)
    st = np.stack([x, x], axis=1)
    with wave.open(str(saida), "wb") as w_:
        w_.setnchannels(2); w_.setsampwidth(2); w_.setframerate(SR_E)
        w_.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())


def mixar(camadas, cam, trans, refazer=False):
    """trilha + efeitos da cena (som_auto) + os extras. Com COLAGEM_VOZ: voz a −16 LUFS por cima, trilha −9 dB com
    sidechain. Sem voz: trilha −3 dB e os extras 8 dB mais altos. Master a −14 LUFS"""
    import som as S, som_auto as SA
    pasta = ROOT / "som"
    pasta.mkdir(parents=True, exist_ok=True)
    if not refazer:
        SA.mixar_auto(camadas, cam, trans, CM.trilha(), FIM, pasta, inicio=0.0, licenca=CM.TRILHA_LICENCA)
    dur = FIM / 24
    faixa_extras(pasta / "extras.wav", dur)
    final = pasta / "master.wav"
    if VOZ:
        CM.exige(VOZ, como="COLAGEM_VOZ=<o arquivo da sua narração>")
        delay = int(round(q(0.0) / 24 * 1000))
        fc = (f"[1:a]adelay={delay}|{delay},loudnorm=I=-16:TP=-1.5:LRA=7,apad=whole_dur={dur:.3f},asplit=2[v][vs];"
              f"[0:a]volume=-9dB[b];[b][vs]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=300[bd];"
              f"[bd][v][2:a]amix=inputs=3:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.2:LRA=9[m]")
        ent = ["-i", str(pasta / "mix.wav"), "-i", str(VOZ), "-i", str(pasta / "extras.wav")]
    else:
        fc = ("[0:a]volume=-3dB[b];[1:a]volume=8dB[x];"
              "[b][x]amix=inputs=2:normalize=0:duration=longest,loudnorm=I=-14:TP=-1.2:LRA=9[m]")
        ent = ["-i", str(pasta / "mix.wav"), "-i", str(pasta / "extras.wav")]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ent, "-filter_complex", fc, "-map", "[m]", "-ar", "48000", str(final)],
                   check=True)
    return final


if __name__ == "__main__":
    camadas, cam, trans = montar()
    cam = cam.montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(2200, 2800)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "espirro.mp4", transicoes=trans)
    elif "--som" in sys.argv:
        import som as S
        master = mixar(camadas, cam, trans, refazer="--refazer" in sys.argv)
        print("master", master, "final", S.juntar(prev / "espirro.mp4", master, prev / "espirro_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        tt = [a[2:] for a in sys.argv[1:] if a.startswith("t=")]
        if tt:                                                          # t=1.0,2.8: instantes da voz (s)
            qs = [q(float(x)) for x in tt[0].split(",")]
        else:
            qs = [int(x) for x in args[0].split(",")] if args else \
                [q(t) for t in (1.5, 4.6, 6.6, 8.9, 10.8, 12.6, 15.6, 19.2, 22.7, 27.0, 31.0, 35.6, 38.3, 40.0, 43.0, 48.0, 51.6,
                                54.0)]
        M.render(camadas, cam, fundo, FIM, prev / "espirro", quadros=qs, transicoes=trans)
    print("ok")
