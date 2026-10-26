"""Exemplo "três pontos num mapa" (12,5 s, sem voz): MAPA DE PAPEL com ALFINETES e um PAINEL que brota de cada alfinete.

O Brasil recortado dos contornos do Natural Earth (domínio público) em papel, sobre a folha do oceano. Três alfinetes
caem um por um (Manaus, Brasília, Porto Alegre); a caneta vermelha liga os três com uma rota tracejada. Depois, para
cada trecho, um painel de papel brota do alfinete no oceano (o canto vazio), mostra UMA etiqueta e UM número (a
distância em linha reta, CALCULADA das coordenadas em mapa_papel.distancia_km) e encolhe de volta para o alfinete
quando a câmera segue: o mapa nunca acumula etiquetas. No fim, a vista aberta com a rota inteira.

Troque os lugares em LUGARES (nome, lon, lat) e o país em Pais(...) (o nome do campo ADMIN do geojson) para fazer o seu.
Antes: nada (o mapa vem no plugin, em dados/mapa/).

    clpy cena_mapa.py              quadros de conferência em previa/mapa/
    clpy cena_mapa.py 40,150       só esses quadros
    clpy cena_mapa.py --video      previa/mapa.mp4 (sem som)
    clpy cena_mapa.py --som        mix (trilha + efeitos) e entrega em previa/mapa_som.mp4"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C
import mapa_papel as MP

MUNDO = (5600, 4600)
OCEANO = (2300, 0, MUNDO[0], MUNDO[1])          # a folha do oceano no mundo (o país fica por cima)
LUGARES = [("MANAUS", -60.02, -3.10), ("BRASÍLIA", -47.88, -15.79), ("PORTO ALEGRE", -51.22, -30.03)]
PAINEIS = [(4200, 1450), (4200, 3050)]          # onde o painel de cada trecho fica (no oceano, fora do caminho)
FIM = 300                                       # 12,5 s a 24 qps


def T(s):
    return int(round(24 * s))


def Q(x0, y0, x1, y1):
    return C.quadro((x0, y0, x1, y1), regiao=M.REGIAO_REELS)


def push(z, f=1.03):
    return (z[0] * f,) + tuple(z[1:])


def montar():
    c = []
    cam = C.Camera()
    br = MP.Pais("Brazil", 62.0, (1900, 2300), -15.0, (150, 186, 128), semente=3)
    c.append(br.camada())
    pts = [br.mundo_xy(lon, lat) for _, lon, lat in LUGARES]

    # ---- o país e o nome dele; os alfinetes caem um por um; a caneta liga os três
    c.append(C.cai("R_PAIS", MP.rotulo(["BRASIL"], semente=11, corpo=(150,)), T(0.4), br.centro[0] - 150,
                   br.centro[1] + 250, rot=-3, de_y=-90, sombra=(4, 9, 0.22), boil="paper", fim=T(3.2)))
    pins = []
    for i, ((x, y), q) in enumerate(zip(pts, (T(1.2), T(1.5), T(1.8))), start=1):
        im = MP.alfinete(str(i), tam=150)
        L = C.cai(f"PIN{i}", im, q, x, y - im.height / 2 + 10, rot=0, de_y=-260, sombra=(6, 14, 0.3), boil="paper")
        pins.append(L)
        c.append(L)
    rota = MP.rota("ROTA", [pts[0], ((pts[0][0] + pts[1][0]) / 2 + 120, (pts[0][1] + pts[1][1]) / 2 - 60), pts[1],
                            ((pts[1][0] + pts[2][0]) / 2 + 140, (pts[1][1] + pts[2][1]) / 2), pts[2]],
                   T(2.2), T(3.4), cor=PC.VERMELHO, esp=16)
    c.append(rota.camada)
    LARGO = Q(br.centro[0] - 1100, br.centro[1] - 1250, br.centro[0] + 1250, br.centro[1] + 1250)
    cam.plano(0, LARGO, "lin").plano(T(3.4), push(LARGO, 1.03), "io")

    # ---- um painel por trecho: brota do alfinete de saída, mostra o trecho e a distância, encolhe de volta
    janelas = [(T(3.6), T(7.0)), (T(7.4), T(10.8))]
    for i, ((px, py), (q0, q1)) in enumerate(zip(PAINEIS, janelas)):
        a, b = LUGARES[i], LUGARES[i + 1]
        km = MP.distancia_km(a[1:], b[1:])
        g = [MP.painel(f"P{i}_PAINEL", px, py, 1300, 1150, q0, semente=51 + i)]
        g.append(C.fixo(f"P{i}_PIN", MP.alfinete(str(i + 1), tam=190), px - 420, py - 330, ini=q0, sombra=(6, 14, 0.3)))
        g.append(C.fixo(f"P{i}_PIN2", MP.alfinete(str(i + 2), tam=190), px + 420, py - 330, ini=q0, sombra=(6, 14, 0.3)))
        g.append(C.Traco(f"P{i}_SETA", [(px - 270, py - 300), (px + 270, py - 300)], q0 + 16, q0 + 24, espessura=18,
                         cor=PC.VERMELHO, seta=True, tam_seta=50, tremor=0.6).camada)
        rot_ = C.cai(f"P{i}_ROTULO", MP.rotulo([a[0], "ATÉ " + b[0]], semente=14 + i, corpo=(110, 64)), q0 + 18, px, py + 40,
                     rot=(-2, 2)[i], de_y=-90, sombra=(4, 9, 0.22), boil="paper")
        rot_.texto_px = None
        g.append(rot_)
        num = MP.valor(MP.km_texto(km), semente=8 + i, corpo=120)
        g.append(C.cai(f"P{i}_KM", num, q0 + 28, px, py + 330, rot=(-4, 3)[i], de_y=-60, sombra=(4, 9, 0.2)))
        MP.brota(g[:3], q0, q0 + 14, pts[i], (px, py))
        c.append(MP.lider(f"P{i}_LIDER", pts[i], (px - 650, py), q0, fim=q1))
        c += g
        MP.encolhe(g, q1 - 14, q1, pts[i], (px, py))
        ZP = Q(px - 760, py - 700, px + 760, py + 640)
        cam.plano(q0 + 4, ZP, "io").plano(q1 - 16, push(ZP, 1.03), "io")
        cam.plano(q1, LARGO, "io")
    cam.plano(FIM, push(LARGO, 1.04), "io")
    c.append(C.vinheta(FIM))
    return c, cam.montar()


def fundo_mundo():
    return MP.pinta_oceano(PC.papel_mundo(*MUNDO), OCEANO)


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = fundo_mundo()
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "mapa.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, AQUI / "mapa" / "som", inicio=0.0, licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "mapa.mp4", AQUI / "mapa" / "som" / "mix.wav", prev / "mapa_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        q = [int(x) for x in args[0].split(",")] if args else [10, 50, 82, 130, 160, 215, 250, 290]
        M.render(camadas, cam, fundo, FIM, prev / "mapa", quadros=q)
    print("ok")
