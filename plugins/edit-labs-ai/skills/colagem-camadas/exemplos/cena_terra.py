"""Exemplo da Terra em camadas, 3D próprio sem licença de terceiros (giro a 7 qps, a fatia levanta, as cascas se
separam).

Antes: preparar.py terra (terra_blender.py + blender_giro.py).

    python3 cena_terra.py              quadros de conferência em previa/terra/
    python3 cena_terra.py --video      previa/terra.mp4
    python3 cena_terra.py --som        previa/terra_som.mp4"""
import os
import sys
from pathlib import Path
from PIL import Image
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C, camadas as K

V = AQUI / "terra" / "vistas"
ESC = 1.0
FIM = 300


def vista(camada, i, semente=1, borda=10):
    return K.papelizar(V / camada / f"cor_v_{i:03d}.png", luz=V / camada / f"luz_v_{i:03d}.png", registrado=True,
                       escala=ESC, semente=semente, cor=0.85, borda=borda)


def montar():
    c = []
    X, Y = 540, 760
    PARA = 34                                                   # a vista com o corte virado para a câmera
    vistas = [vista("fechada", i, i) for i in range(36)]
    giro = K.giro("TERRA", vistas, X, Y, C.k((0, 0.0, "lin"), (84, 340.0, "segura")), ini=0, fim=96)
    giro.som = None
    c.append(giro)
    aberta = vista("aberta", PARA, 3)
    fatia = vista("fatia", PARA, 4)
    cascas = [vista(n, PARA, 10 + i, borda=3) for i, n in enumerate(("s_crosta", "s_manto", "s_nucleo_externo", "s_nucleo_interno"))]
    pil = K.pilha("CASCA", cascas, X, Y, ini=176, fim=FIM, sombra=(8, 16, 0.25))
    for L in pil:
        L.sombra = (8, 16, 0.25)
    c += K.explode(pil, 186, 222, passo=(0, 360))
    base = K.pilha("ABERTA", [aberta], X, Y, ini=96, fim=188)[0]          # cobre as cascas empilhadas até separar
    c.append(base)
    f = K.pilha("FATIA", [fatia], X, Y, ini=96, fim=FIM, sombra=(8, 16, 0.3))[0]
    c.append(K.levanta(f, 110, 150, para=(900, -1100), giro=25))
    nomes = [("CROSTA", "fina como casca"), ("MANTO", "rocha quente"), ("NÚCLEO", "metal líquido"), ("NÚCLEO", "metal sólido")]
    for i, (a, b) in enumerate(nomes):
        et = PC.etiqueta([a, b], semente=40 + i)
        c.append(C.cai(f"ET_{i}", et, 226 + 6 * i, X + 560 - (140 if i >= 2 else 0), Y + 360 * i - 40 + (40 if i == 3 else 0),
                       rot=-2 if i % 2 else 2, sombra=(4, 8, 0.2), boil="paper"))
    for i, (txt, a, b) in enumerate([("A Terra tem *camadas*.", -2, 96), ("Tire uma *fatia*...", 100, 176),
                                     ("...e ela se *separa*.", 180, FIM)]):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=60 + i), a, b))
    c.append(C.vinheta(FIM))
    Q = C.quadro
    r = 520
    G = Q((X - r, Y - r, X + r, Y + r))
    cam = (C.Camera().plano(0, G).plano(176, G, "io")
           .plano(214, Q((X - 540, Y - 540, X + 900, Y + 3 * 360 + 120)), "segura").montar())
    return c, cam


if __name__ == "__main__":
    camadas, cam = montar()
    print(M.ajustar_texto(camadas, cam, FIM))
    fundo = PC.papel_mundo(2400, 3600)
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, AQUI / "previa" / "terra.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, AQUI / "terra" / "som",
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(AQUI / "previa" / "terra.mp4", AQUI / "terra" / "som" / "mix.wav",
                                                    AQUI / "previa" / "terra_som.mp4"))
    else:
        M.render(camadas, cam, fundo, FIM, AQUI / "previa" / "terra", quadros=[0, 30, 60, 90, 104, 120, 132, 150, 190, 210, 240, 290])
    print("ok")
