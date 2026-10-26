"""Exemplo do corpo humano: "O homem comum por dentro", com a FOTO real de arquivo e a anatomia 3D encaixada nele.

Foto: "Photographic postcard of an unidentified man in a suit", 1926–1940s, NMAAHC 2013.46.29.86, Smithsonian Open
Access (CC0). Anatomia: Z-Anatomy (CC BY-SA 4.0) e BodyParts3D (CC BY-SA 2.1 JP), girada 22° no Blender para casar
com o corpo dele (homem3_quadros.py tem o encaixe).

Regras que saíram da revisão de espectador:
- personagem 3D com cara de manequim → foto real de arquivo, em preto e branco antigo;
- braço de foto girando ficava estranho (palito em V) → ele cumprimenta com a CABEÇA (gira por trás da gola) e a
  caneta escreve "oi!";
- portas que viravam asas → janela de papel rasgado com a forma do tronco (janela_forma), nunca um círculo;
- tronco sem cabeça → o rosto fica sempre na tela;
- a janela nunca passa da borda do corpo do atlas (senão abria um buraco preto).

Antes: o pacote colagem-homem3 (recorte e poses) e preparar.py homem (texturas, .blend do atlas, renders).

    clpy cena_homem3.py              quadros de conferência em previa/homem3/
    clpy cena_homem3.py --video      previa/homem3.mp4
    clpy cena_homem3.py --som        previa/homem3_som.mp4"""
import os
import sys
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor as M, pecas as PC, cena as C, camadas as K
import homem3_quadros as HQ

H3 = AQUI / "homem3"
CACHE = H3 / "papel_cena"
VCOR = H3 / "coracao" / "vistas_coracao"
FIM = 866
F = 0.45                                    # resolução de trabalho: 45% da foto (a tela nunca pede mais)
CAIXA = (-1300, -300, 2312, 5700)           # recorte da foto usado (px do recorte), com margem para o braço levantado
# as poses (repouso, meio, alto): CM.homem3("poses/...") = <trabalho>/homem3/poses ou o pacote colagem-homem3
MARGEM_POSES = (1300, 300)
TAM = (round((CAIXA[2] - CAIXA[0]) * F), round((CAIXA[3] - CAIXA[1]) * F))
A0, A1 = 150, 760                           # o interior existe enquanto a janela está aberta


def w(px, py):
    """px do recorte da foto → mundo (= px de trabalho)"""
    return (px - CAIXA[0]) * F, (py - CAIXA[1]) * F


def cache_png(nome, faz):
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / f"{nome}.png"
    if not out.exists():
        im = faz()
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def para_trabalho(im_recorte):
    """imagem no px do recorte (do tamanho do recorte) → px de trabalho (com a margem da CAIXA)"""
    A = np.array([[F, 0, -CAIXA[0] * F], [0, F, -CAIXA[1] * F]], np.float32)
    return Image.fromarray(cv2.warpAffine(np.asarray(im_recorte), A, TAM, flags=cv2.INTER_AREA,
                                          borderValue=(0, 0, 0, 0)))


def mascara_janela_trab(limite_recorte):
    jan = HQ.mascara_janela((2232, 7014))
    lim = cv2.GaussianBlur(cv2.erode(limite_recorte, np.ones((61, 61), np.uint8)), (0, 0), 6) / 255
    jan = jan * lim
    A = np.array([[F, 0, -CAIXA[0] * F], [0, F, -CAIXA[1] * F]], np.float32)
    return cv2.warpAffine(jan.astype(np.float32), A, TAM, flags=cv2.INTER_AREA)


def anat_trab(nome, semente):
    def faz():
        return para_trabalho(HQ.anat(nome, semente, (2232, 7014)))
    return cache_png(f"anat_{nome}", faz)


def recorta(im, m):
    a = np.asarray(im).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * m).astype(np.uint8)
    return Image.fromarray(a)


def fixo(nome, img, ini=0, fim=10 ** 6, sombra=None, boil="obj", ancora=None, x=None, y=None):
    tam = img.size if isinstance(img, Image.Image) else img.tam
    L = C.fixo(nome, img, TAM[0] / 2 if x is None else x, TAM[1] / 2 if y is None else y, ini=ini, fim=fim, esc=1.0,
               sombra=sombra, boil=boil, ancora=ancora or (tam[0] / 2, tam[1] / 2))
    L.tam = tam
    return L


def peca(img, nome, **kw):
    p_, (dx, dy) = K.cortar_alfa(img, margem=6)
    return fixo(nome, p_, x=TAM[0] / 2 + dx, y=TAM[1] / 2 + dy, **kw), (TAM[0] / 2 + dx, TAM[1] / 2 + dy)


def pose_trab(nome):
    """a pose (px do recorte + MARGEM_POSES) no px de trabalho, com a borda branca de tesoura em volta da figura"""
    def faz():
        im = Image.open(CM.homem3(f"poses/{nome}.png")).convert("RGBA")
        dx, dy = CAIXA[0] + MARGEM_POSES[0], CAIXA[1] + MARGEM_POSES[1]
        A = np.array([[F, 0, -dx * F], [0, F, -dy * F]], np.float32)
        t = Image.fromarray(cv2.warpAffine(np.asarray(im), A, TAM, flags=cv2.INTER_AREA, borderValue=(0, 0, 0, 0)))
        return HQ.com_borda(t, borda=12)
    return cache_png(f"pose_{nome}", faz)


def tchau(q0):
    """o tchau em degraus: repouso → meio → alto → meio → alto → meio → repouso (as poses alto e meio alternadas
    são o aceno: a mão vai de um lado para o outro)"""
    seq = ["meio", "alto", "meio", "alto", "meio"]
    return [(q0 + 7 * i, n) for i, n in enumerate(seq)] + [(q0 + 7 * len(seq), "repouso")]


def oi(q0, x0, y0, esc=1.0):
    """'oi!' escrito à mão com a caneta vermelha, traço a traço (o, i, pingo, !, ponto)"""
    def P(lista):
        return [(x0 + x * esc, y0 + y * esc) for x, y in lista]
    o = [(60 + 52 * math.sin(2 * math.pi * t * 1.08 + 0.3), 100 - 66 * math.cos(2 * math.pi * t * 1.08 + 0.3))
         for t in np.linspace(0, 1, 28)]
    tracos = [("O", o, 0, 8), ("I", [(152, 62), (150, 168)], 8, 12), ("IP", [(155, 12), (157, 20)], 12, 13),
              ("EX", [(228, -6), (224, 118)], 13, 17), ("EXP", [(223, 152), (225, 160)], 17, 18)]
    out = []
    for nome, pts, a, b in tracos:
        t = C.Traco(f"OI_{nome}_{q0}", P(pts), q0 + a, q0 + b, espessura=int(round(15 * esc)), cor=PC.VERMELHO, curva="out",
                    suave=len(pts) > 2, fim=q0 + 110, semente=3 + a)
        out.append(t.camada)
    return out


def montar():
    c = []
    poses = {n: pose_trab(n) for n in ("repouso", "meio", "alto")}
    corpo = poses["repouso"]
    musc_rec = np.asarray(HQ.anat("musc", 7, (2232, 7014)).getchannel("A"))
    jan = mascara_janela_trab(musc_rec)

    # ---- o interior, recortado na janela (o atlas tem braços e cabeça que não podem aparecer fora dela)
    cav = PC.textura_papel(TAM[0], TAM[1], (26, 17, 16), 61).convert("RGBA")
    cav.putalpha(Image.fromarray((jan * 255).astype(np.uint8)))
    c.append(fixo("CAVIDADE", cav, ini=A0, fim=A1, boil="paper"))
    dentro = lambda n, s: recorta(anat_trab(n, s), jan)
    c.append(fixo("OSSO_RESTO", dentro("osso_resto", 8), ini=A0, fim=A1))
    c.append(fixo("ORG", dentro("org", 4), ini=A0, fim=A1, sombra=(5, 10, 0.3)))
    pul, _ = peca(dentro("pul", 5), "PULMOES", ini=A0, fim=A1, sombra=(5, 10, 0.3))
    K.pulsa(pul, 410, 634, [1 + 0.03 * math.sin(2 * math.pi * i / 28) for i in range(28)], 28)
    c.append(pul)
    cor, (hx, hy) = peca(dentro("cor", 6), "CORACAO", ini=A0, fim=A1, sombra=(5, 10, 0.32))
    cor.chaves["op"] = C.k((0, 1.0, "segura"), (512, 0.0, "segura"), (630, 1.0, "segura"))
    K.pulsa(cor, 480, 512, [1.07, 1.03, 1.0, 1.0, 1.0, 1.0], 6)
    c.append(cor)
    rib, (rx, ry) = peca(dentro("costelas", 9), "COSTELAS", ini=A0, fim=A1, sombra=(6, 12, 0.32))
    rib.chaves["op"] = C.k((0, 1.0, "segura"), (372, 0.0, "segura"), (656, 1.0, "segura"))
    c.append(rib)
    c.append(fixo("MUSC", K.descasca(dentro("musc", 7), 264, 300, direcao="esquerda", semente=9, volta=(660, 688)),
                  ini=A0, fim=A1, boil="paper"))

    # ---- o homem: dá tchau (poses da foto + braço gerado), abre a janela no peito e fecha no fim; dá tchau de novo
    marcas = tchau(22) + tchau(782)

    def homem(fd, p):
        n = "repouso"
        for q, nome in marcas:
            if fd >= q:
                n = nome
        return poses[n]
    homem.tam = TAM
    c.append(fixo("HOMEM", homem, fim=A0 + 6, sombra=(10, 22, 0.28), boil="paper"))
    c.append(fixo("CORPO", K.janela_forma(corpo, jan, A0 + 6, A0 + 38, semente=12, fecha=(692, 712)), ini=A0 + 6,
                  fim=760, sombra=(10, 22, 0.28), boil="paper"))
    c.append(fixo("HOMEM_FIM", homem, ini=760, sombra=(10, 22, 0.28), boil="paper"))

    # ---- o que viaja passa por cima de tudo (cópias): o coração sai, gira no papel limpo e volta; as costelas saem
    #      pelo alto e voltam
    viagem = []
    cor_v, _ = peca(anat_trab("cor", 6), "CORACAO_VIAGEM", ini=512, fim=631, sombra=(5, 10, 0.32))
    P = (w(2232, 0)[0] + 330, hy - 60)
    AUM = 2.4
    K.destaca(cor_v, 512, 538, para=P, esc=AUM)
    cor_v.chaves["op"] = C.k((0, 1.0, "segura"), (540, 0.0, "segura"), (600, 1.0, "segura"))
    K.pousa(cor_v, 604, 630, para=(hx, hy), esc=1 / AUM)
    cor_v.sons = [("pouso", 628)]
    viagem.append(cor_v)
    giro = giro_coracao(anat_trab("cor", 6), P, AUM)
    viagem.append(giro)
    PARA_RIB = (900, -1300)
    rib_sai, _ = peca(anat_trab("costelas", 9), "COSTELAS_SAI", ini=372, sombra=(6, 12, 0.32))
    viagem.append(K.levanta(rib_sai, 372, 408, para=PARA_RIB, giro=22))
    rib_volta, _ = peca(anat_trab("costelas", 9), "COSTELAS_VOLTA", ini=634, fim=657, sombra=(6, 12, 0.32))
    rib_volta.chaves.update({"x": C.k((634, rx + PARA_RIB[0], "segura")), "y": C.k((634, ry + PARA_RIB[1], "segura")),
                             "rot": C.k((634, 22.0, "segura")), "sdy": C.k((0, 3.0, "segura")),
                             "sbl": C.k((0, 2.4, "segura")), "sop": C.k((0, 0.7, "segura"))})
    K.pousa(rib_volta, 634, 656, para=(rx, ry))
    rib_volta.som = ("pouso", 654)
    viagem.append(rib_volta)
    c += viagem
    c.append(C.circulo("VOLTA_CORACAO", hx, hy, 95, 88, 486, 504, espessura=7, fim=512))

    # ---- o "oi!" de caneta ao lado do rosto (para onde ele olha)
    ox, oy = w(1560, 260)                                             # do outro lado do rosto (a mão acena à esquerda)
    c += oi(30, ox, oy, esc=1.4)

    for i, (txt, q0, q1) in enumerate([("Um homem comum, *saindo para o trabalho*.", 6, 146),
                                       ("Por baixo do paletó: mais de *600 músculos*.", 192, 268),
                                       ("Segurando tudo de pé: *206 ossos*.", 304, 372),
                                       ("Os pulmões respiram *20 mil vezes por dia*.", 412, 480),
                                       ("E o coração bate *100 mil vezes por dia*.", 484, 604),
                                       ("Tudo volta *para o lugar*...", 608, 748),
                                       ("...e ele *nem percebe*.", 752, FIM)]):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=60 + i), q0, q1))
    c.append(C.vinheta(FIM))

    Q = C.quadro
    inteiro = Q((*w(-1150, -200), *w(2392, 3700)))                     # da mão levantada ao quadril
    tronco = Q((*w(-200, -80), *w(2400, 3250)))
    lado = Q((P[0] - 520, P[1] - 560, P[0] + 520, P[1] + 560))
    cam = (C.Camera()
           .plano(0, inteiro, "segura")
           .plano(118, inteiro, "io").plano(150, tronco, "segura")
           .plano(520, tronco, "io").plano(538, lado, "segura")
           .plano(604, lado, "io").plano(624, tronco, "segura")
           .plano(744, tronco, "io").plano(770, inteiro, "segura")
           .montar())
    return c, cam


def giro_coracao(cor_img, P, AUM):
    """o giro do coração começa no MESMO ângulo do atlas na janela (−22°) e na mesma densidade de traço; o encaixe é
    pelo centro de massa do alfa: o do coração que viajou (já em P, aumentado) = o da vista 0 do giro"""
    d = json.load(open(VCOR / "vistas.json"))
    pxm_trab = HQ.PXM_FOTO * F
    s_den = 3750.0 / d["px_por_m"]                                     # o papel do giro na densidade do atlas

    def vista(i):
        def faz():
            im = Image.open(VCOR / "coracao" / f"cor_v_{i:03d}.png").convert("RGBA")
            luz = Image.open(VCOR / "coracao" / f"luz_v_{i:03d}.png").convert("RGB")
            tam = (round(im.width * s_den), round(im.height * s_den))
            return K.papelizar(K.apara_lascas(im.resize(tam, Image.LANCZOS)), luz=luz.resize(tam, Image.LANCZOS),
                               registrado=True, semente=20 + i, cor=1.0, borda=10, contraste=1.6)
        return cache_png(f"giro_cor_{i:03d}", faz)
    vistas = [vista(i) for i in range(36)]
    esc = pxm_trab / 3750.0 * AUM

    def centro_massa(im):
        a = np.asarray(im.getchannel("A")).astype(np.float32)
        ys, xs = np.nonzero(a > 128)
        return np.array([xs.mean() - im.width / 2, ys.mean() - im.height / 2])
    pec, _ = K.cortar_alfa(cor_img, margem=6)
    d_p = centro_massa(pec) * AUM                                      # o coração que viajou, no mundo, a partir de P
    r = math.radians(HQ.ROT)
    Rm = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    d_g = Rm @ (centro_massa(vistas[0]) * esc)
    G = np.array(P) + d_p - d_g
    g = K.giro("CORACAO_GIRO", vistas, G[0], G[1], C.k((540, 0.0, "lin"), (598, 360.0, "segura")), ini=540, fim=600,
               esc=esc, sombra=(10, 20, 0.3))
    g.chaves["rot"] = C.k((540, HQ.ROT, "segura"))
    K.pulsa(g, 540, 600, [1.06, 1.025, 1.0, 1.0, 1.0, 1.0], 6)
    return g


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(2200, 2800)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "homem3.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, H3 / "som", inicio=0.0,
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "homem3.mp4", H3 / "som" / "mix.wav", prev / "homem3_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        q = [int(x) for x in args[0].split(",")] if args else \
            [0, 20, 30, 40, 52, 120, 160, 175, 200, 280, 330, 390, 440, 500, 530, 570, 620, 680, 705, 720, 790, 860]
        M.render(camadas, cam, fundo, FIM, prev / "homem3", quadros=q)
    print("ok")
