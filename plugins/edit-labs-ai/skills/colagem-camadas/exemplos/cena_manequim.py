"""Exemplo do manequim (a referência do estilo): o boneco de papel de 1890 que se desmonta (American Manikin Co., Wellcome Collection, domínio público).

Só material real: as 12 fotos do mesmo boneco, tirando uma peça por vez. Cada peça é a diferença entre duas fotos
(manequim_pecas.py), recortada da foto de cima; ela levanta e a foto de baixo aparece no lugar. No fim todas as peças
voltam, em ordem inversa, e o boneco se monta de novo.

Antes: manequim_pecas.py (precisa do pacote de pranchas da release).

    python3 cena_manequim.py              quadros de conferência em previa/manequim/
    python3 cena_manequim.py --video      previa/manequim.mp4 (sem som)
    python3 cena_manequim.py --som        mix e entrega em previa/manequim_som.mp4"""
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

D = AQUI / "manequim"
X0, Y0, E = 540, 760, 0.34
FIM = 540
# (de, para, início, duração, para onde vai, giro, volta: início, duração, paira)
# as peças grandes saem da tela; as pequenas se afastam um pouco e ficam paradas no ar em volta do boneco (vista
# explodida, legível no corpo inteiro), até voltarem para o lugar
PASSOS = [(0, 2, 96, 36, (760, -1000), 16, 482, 22, False),
          (2, 4, 176, 36, (1150, -250), -12, 472, 22, False),
          (4, 5, 236, 26, (900, 260), 14, 464, 18, False),
          (5, 6, 268, 26, (-900, 300), -14, 456, 18, False),
          (6, 7, 330, 22, (250, -70), 8, 448, 16, True),
          (7, 8, 340, 22, (-250, 60), -6, 442, 16, True),
          (8, 9, 350, 22, (-230, -150), -8, 436, 16, True),
          (9, 10, 360, 22, (-260, 40), 6, 430, 16, True),
          (10, 11, 370, 22, (-220, -230), -5, 424, 16, True)]


def mundo(ix, iy, w=1672, h=3000):
    return X0 + (ix - w / 2) * E, Y0 + (iy - h / 2) * E


def caixa(ix0, iy0, ix1, iy1):
    return mundo(ix0, iy0) + mundo(ix1, iy1)


def montar():
    c = []
    estados = {i: Image.open(D / f"estado_{i:02d}.png").convert("RGBA") for i in (0, 2, 4, 5, 6, 7, 8, 9, 10, 11)}
    # quando cada estado está à vista: entra quando a peça de cima sai; volta quando a peça de cima pousa de novo
    janelas = {i: [] for i in estados}
    janelas[0].append([0, PASSOS[0][2]])
    for k, (a, b, q0, dur, para, giro, v0, vd, _p) in enumerate(PASSOS):
        prox = PASSOS[k + 1][2] if k + 1 < len(PASSOS) else None
        janelas[b].append([q0, prox if prox else PASSOS[-1][6] + PASSOS[-1][7]])
    for k in range(len(PASSOS) - 1, -1, -1):                     # a volta: cada estado reaparece quando a peça pousa
        a, b, *_r, v0, vd, _p = PASSOS[k]
        anterior = PASSOS[k - 1][6] + PASSOS[k - 1][7] if k > 0 else FIM
        janelas[a].append([v0 + vd, anterior])
    for i, img in estados.items():
        jan = sorted(janelas[i])
        op = [] if jan[0][0] == 0 else [(0, 0.0, "segura")]          # duas chaves no quadro 0: vale a 1ª (some)
        for q0, q1 in jan:
            op += [(q0, 1.0, "segura"), (q1, 0.0, "segura")]
        L = C.fixo(f"ESTADO_{i:02d}", img, X0, Y0, ini=jan[0][0], fim=jan[-1][1], esc=E, sombra=(10, 22, 0.28),
                   boil="obj")
        L.chaves["op"] = op
        c.append(L)
    for k, (a, b, q0, dur, para, giro, v0, vd, paira) in enumerate(PASSOS):
        peca, (dx, dy) = K.cortar_alfa(Image.open(D / f"peca_{a:02d}_{b:02d}.png").convert("RGBA"), margem=16)
        x, y = X0 + dx * E, Y0 + dy * E
        sai = C.fixo(f"PECA_{a}_{b}", peca, x, y, ini=0, fim=10 ** 6, esc=E, sombra=(6, 12, 0.3), boil="obj")
        sai.ini = max(0, q0 - 2)
        if paira:                                                 # sai um pouco, fica no ar e depois volta
            K.destaca(sai, q0, q0 + dur, para=(x + para[0], y + para[1]), esc=1.12, rot=giro)
            K.pousa(sai, v0, v0 + vd, para=(x, y), esc=1 / 1.12, rot=0.0)
            sai.sons = [("pouso", v0 + vd - 2)]
            anterior = PASSOS[k - 1][6] + PASSOS[k - 1][7] if k > 0 else FIM
            sai.fim = anterior + 1
            c.append(sai)
            continue
        c.append(K.levanta(sai, q0, q0 + dur, para=para, giro=giro))
        volta = C.fixo(f"VOLTA_{a}_{b}", peca, x + para[0], y + para[1], ini=v0, esc=E * 1.08, sombra=(6, 12, 0.3),
                       boil="obj")
        volta.chaves.update({"rot": C.k((v0, float(giro), "segura")), "sdy": C.k((0, 3.0, "segura")),
                             "sbl": C.k((0, 2.4, "segura")), "sop": C.k((0, 0.7, "segura"))})
        K.pousa(volta, v0, v0 + vd, para=(x, y), esc=1 / 1.08, rot=0.0)
        volta.som = ("pouso", v0 + vd - 2)
        if k > 0:                                                # depois de pousar, o estado de cima já tem a peça
            volta.fim = PASSOS[k - 1][6] + PASSOS[k - 1][7] + 1
        c.append(volta)

    for i, (txt, q0, q1) in enumerate([("Em 1890, anatomia se estudava *num boneco de papel*.", 0, 84),
                                       ("Cada peça *sai do lugar*...", 88, 172),
                                       ("...e mostra a camada de *baixo*.", 176, 252),
                                       ("O estômago, *por fora e por dentro*.", 256, 326),
                                       ("São *12 camadas* num boneco só.", 330, 420),
                                       ("E tudo *volta para o lugar*.", 424, FIM)]):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=80 + i), q0, q1))
    c.append(C.vinheta(FIM))

    Q = C.quadro
    corpo = Q(caixa(160, 40, 1520, 2960))
    cabeca = Q(caixa(400, 60, 1240, 900))
    tronco = Q(caixa(330, 420, 1330, 1700))
    barriga = Q(caixa(470, 760, 1250, 1560))
    joelho = Q(caixa(160, 40, 1520, 2320))                            # da cabeça ao joelho: as peças pequenas aparecem
    cam = (C.Camera()
           .plano(0, (joelho[0] * 0.94,) + joelho[1:], "io").plano(56, joelho, "segura")   # já grande desde o início
           .plano(60, joelho, "io").plano(96, cabeca, "segura")            # aproximação lenta (sem borrão)
           .plano(148, cabeca, "io").plano(170, tronco, "segura")
           .plano(222, tronco, "io").plano(236, barriga, "segura")
           .plano(300, barriga, "io").plano(326, joelho, "segura")
           .plano(492, joelho, "io").plano(FIM, corpo, "segura")
           .montar())
    return c, cam


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(1600, 1700)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "manequim.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, D / "som", inicio=30.0,
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "manequim.mp4", D / "som" / "mix.wav",
                                                    prev / "manequim_som.mp4"))
    else:
        q = [int(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else \
            [0, 70, 100, 112, 124, 150, 186, 200, 230, 250, 280, 300, 336, 352, 372, 400, 430, 446, 470, 490, 520]
        M.render(camadas, cam, fundo, FIM, prev / "manequim", quadros=q)
    print("ok")
