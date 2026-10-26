"""Exemplo da luva de boxe: "A luva protege a mão de quem bate" (luva que sai, pele que abre, ossos que giram e tudo volta).

Camadas registradas pela mesma câmera do Blender (mao_blender.py + blender_giro.py): luva por cima, pele, ossos da mão
(peça que sai), ossos do antebraço e o fundo escuro da mão. A luva descola e sai; a pele abre numa janela rasgada; o
5º metacarpo acende e a caneta circula; os ossos saem, giram a 7 qps e voltam; a pele fecha e a luva volta.

Antes: preparar.py luva (monta mao.blend e renderiza as camadas e o giro).

    clpy cena_luva.py              quadros de conferência em previa/luva/
    clpy cena_luva.py --video      previa/luva.mp4 (sem som)
    clpy cena_luva.py --som        mix e entrega em previa/luva_som.mp4"""
import os
import sys
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C, camadas as K

L_ = AQUI / "luva"
VM, VG, PAP = L_ / "vistas_mao", L_ / "vistas_giro", L_ / "papel"
PXM_R = json.load(open(VM / "vistas.json"))["px_por_m"]
PXM_G = json.load(open(VG / "vistas.json"))["px_por_m"]
XC, ZC = -0.28, -0.975                                           # centro do quadro do render (caixa_mundo)
X0, Y0, E = 540, 1500, 0.5
PXM = PXM_R * E
FIM = 570


def mundo(xm, zm):
    """ponto do modelo (metros; x para a direita da tela, z para cima, braço levantado) -> px do mundo"""
    return X0 + (xm - XC) * PXM, Y0 - (zm - ZC) * PXM


def caixa(x0, z0, x1, z1):
    a, b = mundo(x0, z1)
    c, d = mundo(x1, z0)
    return (a, b, c, d)


def img_px(xm, zm, borda=10):
    """ponto do modelo -> px da camada papelizada (registrada, com a margem da borda)"""
    pad = borda + 4
    w, h = json.load(open(VM / "vistas.json"))["res"]
    return pad + w / 2 + (xm - XC) * PXM_R, pad + h / 2 - (zm - ZC) * PXM_R


def papel(nome, semente, vistas=VM, arquivo="v_000", cor=0.85, tinge=None):
    PAP.mkdir(parents=True, exist_ok=True)
    out = PAP / f"{vistas.name}_{nome}_{arquivo}{'_t' if tinge else ''}_c16.png"     # a pasta entra no nome: o giro e a cena têm camadas com o mesmo nome
    if out.exists():
        return Image.open(out).convert("RGBA")
    cor_png = Image.open(vistas / nome / f"cor_{arquivo}.png").convert("RGBA")
    if tinge:                                                    # a mesma peça em outra cor (o osso que acende)
        a = np.asarray(cor_png).copy()
        a[..., :3] = tinge
        cor_png = Image.fromarray(a)
    im = K.papelizar(cor_png, luz=vistas / nome / f"luz_{arquivo}.png", registrado=True, semente=semente, cor=1.0,
                     contraste=1.6)                                 # contraste alto entre as partes
    im.save(out)
    return im


def cavidade(base):
    al = cv2.erode(np.asarray(base.getchannel("A")), np.ones((9, 9), np.uint8))
    im = PC.textura_papel(base.width, base.height, (64, 33, 30), 43)
    im.putalpha(Image.fromarray(al))
    return im


def fixo(nome, img, x, y, ini=0, fim=10 ** 6, esc=E, sombra=None, boil="obj"):
    tam = img.size if isinstance(img, Image.Image) else img.tam
    L = C.fixo(nome, img, x, y, ini=ini, fim=fim, esc=esc, sombra=sombra, boil=boil, ancora=(tam[0] / 2, tam[1] / 2))
    L.tam = tam
    if getattr(img, "som", None):
        L.som = img.som
    return L


def montar():
    c = []
    luva, pele = papel("luva", 1), papel("pele", 2)
    braco, mao = papel("osso_braco", 3), papel("ossos_mao", 4)
    quinto = papel("quinto", 5, tinge=(214, 52, 40))

    c.append(fixo("CAVIDADE", cavidade(pele), X0, Y0, sombra=(10, 22, 0.28), boil="paper"))
    c.append(fixo("BRACO", braco, X0, Y0))
    peca, (dx, dy) = K.cortar_alfa(mao)
    ossos = fixo("OSSOS_MAO", peca, X0 + dx * E, Y0 + dy * E, sombra=(5, 10, 0.25))
    P = mundo(-0.07, -0.78)                                       # ao lado da mão, no papel limpo: gira sozinho
    K.destaca(ossos, 336, 360, para=P, esc=1.3)
    ossos.chaves["op"] = C.k((0, 1.0, "segura"), (362, 0.0, "segura"), (446, 1.0, "segura"))
    K.pousa(ossos, 444, 470, para=(X0 + dx * E, Y0 + dy * E), esc=1 / 1.3)   # os ossos chegam antes da câmera
    c.append(ossos)
    vistas = [papel("ossos_mao", 20 + i, vistas=VG, arquivo=f"v_{i:03d}") for i in range(36)]
    c.append(K.giro("OSSOS_GIRO", vistas, P[0], P[1], C.k((362, 0.0, "lin"), (434, 360.0, "segura")), ini=362,
                    fim=446, esc=PXM * 1.3 / PXM_G, sombra=(10, 20, 0.3)))
    acende = fixo("QUINTO", quinto, X0, Y0, ini=246, fim=332)
    acende.chaves["op"] = C.k((246, 0.0, "lin"), (250, 1.0, "segura"), (326, 1.0, "lin"), (332, 0.0, "segura"))
    c.append(acende)
    centro = img_px(-0.28, -0.775)
    c.append(fixo("PELE", K.janela(pele, centro, 156, 192, 0.098 * PXM_R, semente=8, fecha=(472, 496)), X0, Y0,
                  boil="paper"))
    c.append(K.levanta(fixo("LUVA", luva, X0, Y0, sombra=(10, 22, 0.3)), 74, 112, para=(1100, -1500), giro=22))
    volta = fixo("LUVA_VOLTA", luva, X0 + 700, Y0 - 1300, ini=496, sombra=(10, 22, 0.3))
    volta.chaves.update({"rot": C.k((496, 18.0, "segura")), "sdy": C.k((0, 3.4, "segura")),
                         "sbl": C.k((0, 2.6, "segura")), "sop": C.k((0, 0.65, "segura"))})
    K.pousa(volta, 498, 522, para=(X0, Y0), esc=1.0, rot=0.0)
    volta.som = ("pouso", 518)
    c.append(volta)

    # ---- caneta: a volta no colo do 5º metacarpo (onde quebra)
    cx_q, cy_q = mundo(-0.243, -0.792)
    c.append(C.circulo("VOLTA_QUINTO", cx_q, cy_q, 0.024 * PXM, 0.030 * PXM, 256, 276, espessura=8, fim=332))

    # a legenda entra depois que o olho já viu a coisa
    for i, (txt, q0, q1) in enumerate([("A luva não protege só *quem apanha*.", 0, 96),
                                       ("Ela protege *a mão* de quem bate.", 100, 182),
                                       ("Aqui dentro: *27 ossos*.", 186, 252),
                                       ("Quebrar este tem nome: *fratura do boxeador*.", 256, 340),
                                       ("Um soco mal dado e ele *quebra*.", 344, 496),
                                       ("Por isso: *luva*.", 500, FIM)]):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=70 + i), q0, q1))
    c.append(C.vinheta(FIM))

    Q = C.quadro
    pl_luva = Q(caixa(-0.385, -0.975, -0.175, -0.66))
    abre = (pl_luva[0] * 0.9,) + pl_luva[1:]
    pl_mao = Q(caixa(-0.37, -0.90, -0.19, -0.675))
    pl_quinto = Q(caixa(-0.33, -0.87, -0.19, -0.70))
    pl_giro = Q(caixa(-0.19, -0.90, 0.05, -0.66))                       # a câmera segue os ossos: um foco só
    cam = (C.Camera()
           .plano(0, abre, "io").plano(64, pl_luva, "segura")
           .plano(100, pl_luva, "io").plano(128, pl_mao, "segura")
           .plano(238, pl_mao, "io").plano(254, pl_quinto, "segura")
           .plano(343, pl_quinto, "io").plano(360, pl_giro, "segura")      # junto com a viagem dos ossos
           .plano(448, pl_giro, "io").plano(465, pl_mao, "segura")
           .plano(474, pl_mao, "io").plano(500, pl_luva, "segura")
           .montar())
    return c, cam


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(1400, 2800)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "luva.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, L_ / "som", inicio=42.0,
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "luva.mp4", L_ / "som" / "mix.wav", prev / "luva_som.mp4"))
    else:
        q = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else \
            [0, 60, 84, 96, 120, 166, 180, 210, 262, 290, 344, 360, 380, 410, 440, 458, 476, 490, 506, 514, 540]
        M.render(camadas, cam, fundo, FIM, prev / "luva", quadros=q)
    print("ok")
