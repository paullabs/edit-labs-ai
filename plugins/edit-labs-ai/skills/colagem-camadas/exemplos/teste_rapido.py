"""Teste rápido das mecânicas, sem nenhum asset da release: três camadas de papel registradas (feitas em código) que se
revelam com janela, descasca e levanta, e voltam ao lugar. Serve para conferir a instalação do motor, não é referência
de estilo (a referência é o manequim de 1890: objeto real em camadas).

    python3 teste_rapido.py              3 quadros de conferência em <trabalho>/previa/teste_rapido/
    python3 teste_rapido.py --video      <trabalho>/previa/teste_rapido.mp4 (6 s)
    python3 teste_rapido.py --som        + som sintetizado: <trabalho>/previa/teste_rapido_som.mp4"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
import motor as M, pecas as PC, cena as C, camadas as K

AQUI = CM.TRABALHO
FIM = 144                                     # 6 s no relógio de 24
LADO = 820
X, Y = 540, 840


def disco(raio, tom, semente):
    """um disco de papel do tamanho da pilha (camadas registradas: mesmo tamanho, mesmo centro)"""
    im = PC.textura_papel(LADO, LADO, tom, semente)
    m = Image.new("L", (LADO, LADO), 0)
    ImageDraw.Draw(m).ellipse([LADO / 2 - raio, LADO / 2 - raio, LADO / 2 + raio, LADO / 2 + raio], fill=255)
    im.putalpha(m)
    return PC.rasgar(im, amp=5, passo=18, semente=semente)


def montar():
    c = [C.fundo_escuro(FIM, [(0, 1.0, "segura")], cor=(36, 34, 40))]
    nucleo = disco(170, (196, 64, 44), 3)
    manto = disco(290, (222, 140, 62), 4)
    crosta = disco(380, (92, 128, 112), 5)
    base, meio = K.pilha("CAMADA", [nucleo, manto], X, Y, esc=1.0)
    topo = K.janela(crosta, (LADO / 2, LADO / 2), 12, 40, 400, fecha=(108, 126))
    cima, = K.pilha("CROSTA", [topo], X, Y)
    c += [base, meio, cima]
    K.levanta(meio, 52, 80, para=(700, -500), giro=14)
    volta = C.fixo("MANTO_VOLTA", manto, X + 700, Y - 500, ini=92, esc=1.08, sombra=(6, 12, 0.3), boil="obj")
    volta.chaves.update({"rot": C.k((92, 14.0, "segura")), "sdy": C.k((0, 3.0, "segura")),
                         "sbl": C.k((0, 2.4, "segura")), "sop": C.k((0, 0.7, "segura"))})
    K.pousa(volta, 92, 106, para=(X, Y), esc=1 / 1.08, rot=0.0)
    volta.som = ("pouso", 104)
    c.append(volta)
    K.pulsa(base, 80, 92, [1.06, 1.02, 1.0, 1.0], 4)
    c.append(C.carimbo("c_NUCLEO", PC.carimbo("NÚCLEO", corpo=96), 82, X, Y + 260, -4, fim=92))
    c.append(C.vinheta(FIM))
    G = C.quadro((X - 430, Y - 430, X + 430, Y + 430), regiao=M.REGIAO_REELS)
    cam = C.Camera().plano(0, (G[0] * 0.94,) + G[1:], "io").plano(30, G, "segura").plano(FIM, G).montar()
    return c, cam


if __name__ == "__main__":
    camadas, cam = montar()
    M.ajustar_texto(camadas, cam, FIM)
    print("margens:", M.checar_margens(camadas, cam, range(0, FIM, 12))[:5])
    fundo = PC.papel_mundo(1400, 2200)
    prev = AQUI / "previa"
    if "--video" in sys.argv or "--som" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "teste_rapido.mp4")
        if "--som" in sys.argv:
            import som as S, som_auto as SA
            r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, AQUI / "teste_rapido" / "som",
                              licenca=CM.TRILHA_LICENCA)
            print("mix", r["master"], "final", S.juntar(prev / "teste_rapido.mp4", AQUI / "teste_rapido" / "som" / "mix.wav",
                                                        prev / "teste_rapido_som.mp4"))
    else:
        M.render(camadas, cam, fundo, FIM, prev / "teste_rapido", quadros=[20, 66, 84])
    print("ok", prev)
