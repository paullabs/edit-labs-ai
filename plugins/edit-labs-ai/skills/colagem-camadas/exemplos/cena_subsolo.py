"""Exemplo "as camadas do subsolo de um poço" (9 s, sem voz): a DESCIDA EM CAMADAS da Terra.

Um bloco geológico 3D próprio em corte (modelos/presal_blender.py: mar, pós-sal em 3 faixas, sal, rocha do reservatório
com o óleo na crista, embasamento), renderizado pela mesma câmera e papelizado em camadas registradas
(subsolo_pecas.py). A superfície do mar é feita de tiras de papel que balançam; a sonda desce na vertical e a câmera
desce junto (a ponta da sonda fica parada na tela); o nome de cada camada entra preso à TELA quando a ponta passa por
ela, um por vez (o seguinte troca o anterior: MAR → PÓS-SAL → SAL → PRÉ-SAL); na crista, o óleo aparece enchendo a
rocha, as gotas sobem pelo tubo e a câmera abre devagar para o bloco inteiro, com um número só em carimbo.

Mecânicas que servem para qualquer descida (poço, mina, oceano, camadas da pele):
  onda(...)         tira de papel com crista ondulada (mar, rio, nuvem baixa) que balança em degraus
  sonda + quando()  um traço que desce e o quadro em que a ponta passa de cada camada (o rótulo entra nessa hora)
  revela(...)       uma camada que aparece "enchendo" a partir de um ponto (borda irregular, degraus de 7 qps)
  gotas(...)        bolinhas que sobem por um caminho (óleo, bolhas, sangue)
  câmera            plano a plano seguindo a ponta (zoom leve, sem pressa) e a vista aberta no fim

Espessuras esquemáticas (as do modelo): lâmina d'água ~2 km, pós-sal ~1 km, sal ~2 km, reservatório a ~5 km.
Antes: preparar.py subsolo.

    clpy cena_subsolo.py              quadros de conferência em previa/subsolo/
    clpy cena_subsolo.py 40,150       só esses quadros
    clpy cena_subsolo.py --video      previa/subsolo.mp4 (sem som)
    clpy cena_subsolo.py --som        mix (trilha + efeitos) e entrega em previa/subsolo_som.mp4"""
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import motor as M, pecas as PC, cena as C, camadas as K
import subsolo_pecas as SP

ORIGEM = (300, 1300)                     # onde o canto (0, 0) do bloco registrado cai no mundo
MUNDO = (4300, 6200)
ACO, ACO_CLARO = (52, 54, 58), (168, 170, 174)
OLEO, OLEO_BRILHO = (34, 22, 14), (190, 150, 96)
FIM = 216                                # 9 s a 24 qps


def T(s):
    return int(round(24 * s))


def W(pt):
    """px do bloco registrado -> mundo"""
    return (ORIGEM[0] + pt[0], ORIGEM[1] + pt[1])


def onda(larg, alt, cor, semente, amp=14.0, comp=170.0):
    """tira de mar em papel: crista ondulada com espuma clara, o resto na cor, grão de papel; a base fica reta (some
    embaixo da tira da frente)"""
    S = 2
    rng = np.random.default_rng(semente)
    xs = np.arange(larg * S) / S
    fase = rng.uniform(0, 6.28)
    topo = amp + amp * 0.75 * np.sin(2 * np.pi * xs / comp + fase) + amp * 0.35 * np.sin(2 * np.pi * xs / (comp * 0.43) + 2 * fase)
    topo += np.convolve(rng.normal(0, 1.2, len(xs)), np.ones(9) / 9, mode="same")
    yy = np.arange(alt * S)[:, None] / S
    dentro = (yy >= topo[None, :]).astype(np.float32)
    espuma = ((yy >= topo[None, :]) & (yy < topo[None, :] + 7)).astype(np.float32)
    tinta = ((yy >= topo[None, :] + 7) & (yy < topo[None, :] + 10)).astype(np.float32)
    tex = np.asarray(PC.textura_papel(larg * S, alt * S, cor, semente).convert("RGB")).astype(np.float32)
    claro = np.array([236, 244, 240], np.float32)
    escuro = np.array(cor, np.float32) * 0.55
    rgb = tex * (1 - espuma[..., None]) + claro * espuma[..., None]
    rgb = rgb * (1 - tinta[..., None] * 0.7) + escuro * tinta[..., None] * 0.7
    a = np.dstack([rgb, dentro * 255]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(a).resize((larg, alt), Image.LANCZOS)


def gotas(nome, pts, q0, q1, n, raio, dur, semente=5, fim=None):
    """gotas que sobem por um caminho (pts, do fundo para cima): a gota i sai em q0 + i·passo e leva 'dur' quadros"""
    pts = np.array(pts, np.float32)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    acum = np.concatenate([[0], np.cumsum(seg)])
    m = raio * 3
    x0, y0 = pts[:, 0].min() - m, pts[:, 1].min() - m
    larg, alt = int(pts[:, 0].max() - x0 + m), int(pts[:, 1].max() - y0 + m)
    rng = np.random.default_rng(semente)
    passo = (q1 - q0 - dur) / max(n - 1, 1)
    infos = [(q0 + i * passo, rng.uniform(0.75, 1.25), rng.uniform(-0.35, 0.35)) for i in range(n)]

    def ponto(u):
        alvo = u * acum[-1]
        i = min(int(np.searchsorted(acum, alvo, side="right") - 1), len(pts) - 2)
        f = (alvo - acum[i]) / max(acum[i + 1] - acum[i], 1e-6)
        return pts[i] + (pts[i + 1] - pts[i]) * min(max(f, 0), 1)

    def fonte(fd, p):
        im = Image.new("RGBA", (larg, alt), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for t0, esc, lado in infos:
            u = (fd - t0) / dur
            if not 0 <= u <= 1:
                continue
            x, y = ponto(M.curva("in", u) * 0.15 + u * 0.85)
            x += lado * raio
            r = raio * esc
            x, y = x - x0, y - y0
            d.ellipse([x - r, y - r * 1.1, x + r, y + r * 1.1], fill=OLEO + (255,), outline=(14, 10, 8, 255), width=3)
            d.ellipse([x - r * 0.45, y - r * 0.7, x - r * 0.05, y - r * 0.3], fill=OLEO_BRILHO + (230,))
        return im
    return M.Camada(nome, fonte, q0, fim or q1 + 4, ancora=(0, 0), boil="ink", chaves={
        "x": C.k((q0, x0, "segura")), "y": C.k((q0, y0, "segura"))})


def revela(img, q0, q1, centro, semente=4):
    """a camada aparece enchendo a partir de 'centro' (px da peça): uma elipse de borda irregular cresce para os lados,
    em degraus de 7 qps. Antes de q0 a camada não aparece; depois de q1 fica inteira"""
    a0 = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    h, w = a0.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = (xx - centro[0]) / (w * 0.55), (yy - centro[1]) / (h * 0.9)
    dist = np.sqrt(dx ** 2 + dy ** 2)
    ang = (np.arctan2(dy, dx) + math.pi) / (2 * math.pi)
    var = K._ruido_borda(720, semente, 0.10)[(ang * 719).astype(int)]
    cache = {}

    def fonte(fd, p):
        t = min(max((fd - q0) / max(q1 - q0, 1), 0), 1)
        t = math.floor(t * 7) / 7 if t < 1 else 1.0                      # degraus de 7 qps
        t = M.curva("out", t)
        if t not in cache:
            m = cv2.GaussianBlur((dist < t * 1.15 * (1 + var)).astype(np.float32), (0, 0), 1.2)
            o = a0.copy()
            o[..., 3] *= m
            cache[t] = Image.fromarray((o * 255).astype(np.uint8))
        return cache[t]
    fonte.tam = (w, h)
    fonte.som = ("janela", q0, q1)
    return fonte


def rotulo_tela(nome, texto, q0, x, y, r=-2.0, fim=10 ** 6, corpo=64, semente=60):
    """rótulo preso à TELA (não ao mundo): fica parado enquanto o mundo desce, e o seguinte o troca"""
    L = M.Camada(nome, PC.etiqueta([texto], corpo=(corpo,), semente=semente), q0, fim, mundo=False, boil="type",
                 sombra=(4, 9, 0.22), chaves={
                     "x": C.k((q0, x, "segura")), "y": C.k((q0, y + 24, "out"), (q0 + 5, y, "segura")),
                     "rot": C.k((q0, r, "segura")), "op": C.k((q0, 0.0, "lin"), (q0 + 2, 1.0, "segura"))})
    L.texto_px = None
    return L


def montar():
    c = []
    cam = C.Camera()
    blo = SP.pecas_bloco()
    mk, pxkm = SP.marcos()
    pt = {k: W(v) for k, v in mk.items()}
    oleo_w = W(mk["oleo"])

    # ---- o céu: uma folha azul-clara atrás do topo do bloco, com nuvens de papel que andam devagar
    c.append(C.papel_area("PAPEL_CEU", (pt["c_tl"][0] - 380, pt["c_btl"][1] - 1100, pt["c_btr"][0] + 380, pt["c_tr"][1] + 120),
                          cor=(188, 214, 222), semente=43))
    for i, (dx, dy, lg) in enumerate(((260, -760, 620), (1500, -900, 480), (2300, -560, 400))):
        nv = PC.rasgar(PC.textura_papel(lg, int(lg * 0.32), (246, 244, 236), 70 + i), amp=10, passo=18, semente=70 + i)
        xn, yn = pt["c_tl"][0] + dx, pt["c_btl"][1] + dy + 300
        L = C.fixo(f"NUVEM_{i}", nv, xn, yn, sombra=(4, 10, 0.12), boil="paper")
        L.chaves["x"] = C.k((0, xn, "lin"), (FIM, xn + 160 + 40 * i, "segura"))
        c.append(L)

    # ---- a sonda: desce do alto da tela (a plataforma fica fora do quadro), fura as camadas e chega na crista
    topo = pt["poco_topo"]
    fundo_poco = (topo[0], oleo_w[1] - 70)
    entrada = (topo[0], topo[1] - 1900)                              # acima do alto do primeiro quadro: a sonda entra pela borda
    tubo = [entrada, topo, fundo_poco]
    Q0, Q1 = T(0.6), T(5.6)

    # ---- o bloco (de baixo para cima); o óleo aparece enchendo a crista quando a sonda chega
    for n in SP.ORDEM:
        img, (cx, cy) = blo[n]
        x, y = W((cx, cy))
        if n == "oleo":
            oc = (mk["oleo"][0] - (cx - img.width / 2), mk["oleo"][1] - (cy - img.height / 2) - 60)
            L = M.Camada("BLOCO_oleo", revela(img, Q1, Q1 + 16, oc), 0, FIM, ancora=(img.width / 2, img.height / 2),
                         boil="obj", chaves={"x": C.k((0, x, "segura")), "y": C.k((0, y, "segura"))})
            L.tam = img.size
            c.append(L)
        else:
            c.append(C.fixo(f"BLOCO_{n}", img, x, y, sombra=(18, 34, 0.32) if n == "emb" else None, boil="paper"))

    # ---- o mar por cima: 4 tiras de papel paralelas à borda da frente, do fundo para a frente, balançando
    ang = math.degrees(math.atan2(pt["c_tr"][1] - pt["c_tl"][1], pt["c_tr"][0] - pt["c_tl"][0]))
    fr = ((pt["c_tl"][0] + pt["c_tr"][0]) / 2, (pt["c_tl"][1] + pt["c_tr"][1]) / 2)
    fu = ((pt["c_btl"][0] + pt["c_btr"][0]) / 2, (pt["c_btl"][1] + pt["c_btr"][1]) / 2)
    larg = int(math.hypot(pt["c_tr"][0] - pt["c_tl"][0], pt["c_tr"][1] - pt["c_tl"][1]) * 0.98)
    cores = [(58, 118, 138), (64, 132, 152), (52, 112, 136), (70, 140, 160)]
    for i, t in enumerate((0.12, 0.38, 0.64, 0.93)):
        x = fu[0] + (fr[0] - fu[0]) * t
        y = fu[1] + (fr[1] - fu[1]) * t
        L = C.fixo(f"MAR_{i}", onda(larg, 150, cores[i], 60 + i, amp=13 + 2 * i, comp=150 + 25 * i), x, y - 40, rot=ang,
                   sombra=(4, 10, 0.18), boil="paper")
        ch_x, ch_y = [], []
        for f in range(0, FIM + 4, 4):                                   # balanço lento, em degraus
            a = 2 * math.pi * f / (56 + 10 * i) + i * 1.3
            ch_x.append((f, x + 26 * math.sin(a), "io"))
            ch_y.append((f, y - 40 + 7 * math.sin(a * 1.6 + 0.5), "io"))
        L.chaves["x"], L.chaves["y"] = ch_x, ch_y
        c.append(L)

    sonda = C.Traco("SONDA", tubo, Q0, Q1, espessura=30, cor=ACO, curva="io", seta=True, tam_seta=36, tremor=0.4)
    brilho = C.Traco("SONDA_B", tubo, Q0, Q1, espessura=8, cor=ACO_CLARO, curva="io", tremor=0.4)
    c += [sonda.camada, brilho.camada]

    def quando(y_alvo):
        """quadro em que a ponta da sonda passa da altura y_alvo"""
        for f in range(Q0, Q1 + 2, 2):
            if sonda.ponta(f)[1] >= y_alvo:
                return f
        return Q1

    # ---- um nome por vez, preso à tela, na hora em que a ponta entra na camada
    nomes = [("MAR", T(0.9)), ("PÓS-SAL", quando(pt["fundo"][1] - 60)), ("SAL", quando(pt["sal_topo"][1] - 60)),
             ("PRÉ-SAL", quando(pt["sal_base"][1] - 60))]
    for i, (txt, q) in enumerate(nomes):
        q_fim = nomes[i + 1][1] if i + 1 < len(nomes) else T(6.6)
        c.append(rotulo_tela(f"R_DESCE{i}", txt, q, 310, 640, r=(-2, 2, -1, 2)[i], fim=q_fim, semente=60 + i))

    # ---- chega no óleo: a rajada, o óleo enche a crista e sobe em gotas pelo tubo
    c.append(C.rajada("RAJ_FURA", fundo_poco[0], fundo_poco[1] + 30, Q1, raio=360, cor=(246, 238, 220), espessura=16))
    c.append(gotas("GOTAS", [fundo_poco, topo, entrada], T(6.0), T(8.4), 22, 34, 30, fim=FIM))

    # ---- a vista aberta: o bloco inteiro e um número só, em carimbo, preso ao mundo ao lado do óleo
    prof = PC.carimbo("5 KM", corpo=190, semente=7, cor=PC.VERMELHO)
    c.append(C.cai("V_PROF", prof, T(7.6), oleo_w[0] + 780, oleo_w[1] + 380, rot=-4, de_y=-120, sombra=(4, 9, 0.2)))
    regua = [(pt["c_tl"][0] - 140, pt["c_tl"][1]), (pt["c_tl"][0] - 140, oleo_w[1])]
    c.append(C.Traco("REGUA", regua, T(7.3), T(7.7), espessura=16, cor=PC.VERMELHO, seta=True, tam_seta=46, tremor=0.6).camada)

    # ---- câmera: a superfície; a descida contínua (a ponta da sonda fica parada na tela); a vista aberta, devagar
    z0, z1 = 1.0, 1.12
    sm = lambda u: u * u * (3 - 2 * u)
    ty0, ty1 = 1260, 760
    cam.plano(0, (z0, topo[0], topo[1] - 380 - (ty0 - 960) / z0), "lin")
    cam.plano(Q0, (z0 * 1.01, topo[0], topo[1] - 380 - (ty0 - 960) / (z0 * 1.01)), "lin")
    f0 = None
    for f in range(Q0 + 2, Q1 + 1, 2):
        px, py = sonda.ponta(f)
        if py < topo[1] - 380:                                         # a câmera só desce quando a ponta passa da superfície
            continue
        f0 = f0 or f
        u = min(max((f - f0) / (T(2.4) - Q0), 0), 1)
        z = z0 + (z1 - z0) * sm(min((f - f0) / (Q1 - f0), 1))
        ty = ty0 + (ty1 - ty0) * sm(u)
        cam.plano(f, (z, px, py - (ty - 960) / z), "lin")
    cam.plano(T(6.2), (z1 * 1.03, fundo_poco[0], fundo_poco[1] - (ty1 - 960) / (z1 * 1.03)), "io")
    LARGO = C.quadro((pt["c_tl"][0] - 220, pt["c_btl"][1] - 200, pt["c_btr"][0] + 60, pt["c_br"][1] + 40),
                     regiao=M.REGIAO_REELS)
    cam.plano(T(7.2), LARGO, "lin").plano(FIM, (LARGO[0] * 1.03,) + LARGO[1:], "io")
    c.append(C.vinheta(FIM))
    return c, cam.montar()


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(*MUNDO)
    prev = AQUI / "previa"
    if "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "subsolo.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, AQUI / "subsolo" / "som", inicio=0.0,
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "subsolo.mp4", AQUI / "subsolo" / "som" / "mix.wav",
                                                    prev / "subsolo_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        q = [int(x) for x in args[0].split(",")] if args else [0, 30, 60, 90, 120, 140, 160, 185, 210]
        M.render(camadas, cam, fundo, FIM, prev / "subsolo", quadros=q)
    print("ok")
