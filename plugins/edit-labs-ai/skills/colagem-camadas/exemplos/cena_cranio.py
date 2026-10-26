"""Exemplo do crânio: "Seu cérebro está boiando agora" (crânio Z-Anatomy CC BY-SA 4.0 + cérebro BodyParts3D CC BY-SA 2.1 JP).

O crânio gira a 7 qps, a tampa sai voando, o líquor (azul) enche em volta do cérebro, o cérebro sai, gira no papel
limpo e volta; o crânio leva um tranco (o soco no queixo) e o cérebro chega atrasado; a tampa volta e encaixa.

Regras aplicadas (TECNICA.md):
- contraste: crânio marfim sobre papel escuro;
- profundidade: a parede de trás e a borda da frente do crânio saem da MESMA camada (base), separadas onde o cérebro
  ou o líquor aparecem na frente dela nas prévias "encaixe"; o cérebro mexe entre as duas sem atravessar o osso;
- borda branca só por fora da figura inteira; a peça que descola (a tampa, o cérebro) ganha a borda dela no mesmo
  degrau em que descola, e perde quando assenta;
- lascas finas da malha saem do alfa antes do papel (apara_lascas);
- o giro e a vista parada têm o mesmo traço: as vistas do giro são papelizadas na densidade da vista A (px/m) e o
  centro do giro foi MEDIDO na vista A por casamento de alfa (IoU 0,998), não suposto;
- o que gira sai antes para o papel limpo e a câmera vai junto, com o mesmo tempo da peça;
- a legenda entra depois da imagem; tudo volta ao lugar no fim.

Antes: preparar.py cranio (monta cranio.blend e renderiza camadas, giros e a luva do soco).

    python3 cena_cranio.py              quadros de conferência em previa/cranio/
    python3 cena_cranio.py --conferir   só a figura sobre magenta + conferir_figura (buraco, borda branca, lascas)
    python3 cena_cranio.py --video      previa/cranio.mp4 (sem som)
    python3 cena_cranio.py --som        mix e entrega em previa/cranio_som.mp4"""
import os
import sys
import json
import math
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
import conferir_figura as CF

CR = AQUI / "cranio"
VA, VB, VC, PAP = CR / "vistas_camadas", CR / "vistas_giro_cranio", CR / "vistas_giro_cerebro", CR / "papel"
IA = json.load(open(VA / "vistas.json"))
PXM_A = IA["px_por_m"]
PXM_B = json.load(open(VB / "vistas.json"))["px_por_m"]
PXM_C = json.load(open(VC / "vistas.json"))["px_por_m"]
AW, AH = IA["res"]
# onde o centro de cada giro cai na vista A (px): medido casando o alfa da vista 0 (ampliada para o px/m da A) com a
# camada da A; IoU 0,998 nos dois. (O marco "centro_cranio" não é o eixo do giro: ficaria 40 px fora.)
CENTRO_B = (791.89, 958.89)
CENTRO_C = (760.70, 725.70)
BORDA = 10
PAD = BORDA + 4
X0, Y0, E = 700, 1400, 0.6
FIM = 600
T_ABRE = 98                       # o giro termina na vista 0 e segura; aqui entram as camadas e a tampa descola
PIV_PX = (800.0, 1450.0)          # o tranco gira em volta do pescoço (atrás da mandíbula)
SOBE = (280, 304)                 # o cérebro sai do crânio
GIRA = (306, 378)                 # gira no papel limpo
VOLTA = (378, 404)                # volta e assenta


def papel(pasta, nome, semente, sil=None, chave=""):
    PAP.mkdir(exist_ok=True)
    out = PAP / f"{pasta.name}_{nome}{chave}.png"
    if not out.exists():
        cor = K.apara_lascas(Image.open(pasta / nome / "cor_v_000.png"))
        if nome != "liquido":
            cor = K.fecha_vazados(cor)
        im = K.papelizar(cor, luz=pasta / nome / "luz_v_000.png", registrado=True, semente=semente, cor=1.0,
                         borda=BORDA, contraste=1.6, silhueta=sil)
        tmp = out.with_suffix(".tmp.png")                         # atômico: dois renders dividem o cache
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def papel_giro(pasta, nome, i, semente, px_m):
    """vista do giro papelizada na densidade da vista A: amplia até o px/m da A, papeliza (traço, pontilhado e borda do
    mesmo tamanho que nas camadas) e volta ao tamanho do giro. Sem isso o traço engrossava 1,5x na troca."""
    PAP.mkdir(exist_ok=True)
    out = PAP / f"{pasta.name}_{nome}_v_{i:03d}.png"
    if not out.exists():
        s = PXM_A / px_m
        cor = Image.open(pasta / nome / f"cor_v_{i:03d}.png").convert("RGBA")
        luz = Image.open(pasta / nome / f"luz_v_{i:03d}.png").convert("RGB")
        tam = (round(cor.width * s), round(cor.height * s))
        cor = K.fecha_vazados(K.apara_lascas(cor.resize(tam, Image.LANCZOS)))
        im = K.papelizar(cor, luz=luz.resize(tam, Image.LANCZOS), registrado=True, semente=semente, cor=1.0,
                         borda=BORDA, contraste=1.6, escala=1 / s)
        tmp = out.with_suffix(".tmp.png")                         # atômico: dois renders dividem o cache
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def papel_rgba(rgba, semente, nome):
    """papel de uma imagem montada aqui (o anel do líquor), com cache atômico"""
    PAP.mkdir(exist_ok=True)
    out = PAP / f"{nome}.png"
    if not out.exists():
        im = K.papelizar(Image.fromarray(rgba), registrado=True, semente=semente, cor=1.0, borda=BORDA, contraste=1.6)
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def luva_soco():
    """a luva de boxe de J-Toastie (CC BY 3.0) de perfil, polegar em cima, o punho apontando para a esquerda"""
    PAP.mkdir(exist_ok=True)
    out = PAP / "luva_soco.png"
    if not out.exists():
        pasta = CR / "luva" / "vistas_soco" / "luva"
        im = K.papelizar(K.apara_lascas(Image.open(pasta / "cor_v_000.png")), luz=pasta / "luz_v_000.png", semente=81,
                         cor=1.0, borda=BORDA, contraste=1.6)
        im = im.rotate(90, expand=True, resample=Image.BICUBIC)
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def mundo_a(px, py):
    """px da vista A (render, sem a margem do papel) -> mundo"""
    return X0 + (px - AW / 2) * E, Y0 + (py - AH / 2) * E


def alfa(nome):
    return np.asarray(Image.open(VA / nome / "cor_v_000.png").getchannel("A"))


def rgb(nome):
    return np.asarray(Image.open(VA / nome / "cor_v_000.png").convert("RGB")).astype(np.int32)


def caixa(a, lim=128):
    ys, xs = np.nonzero(a > lim)
    return xs.min(), ys.min(), xs.max(), ys.max()


def com_alfa(im, m):
    a = np.asarray(im).copy()
    a[..., 3] = (a[..., 3].astype(np.float32) * m).astype(np.uint8)
    return Image.fromarray(a)


def gira(p, centro, graus):
    """o ponto p girado em volta de centro (horário na tela, como o motor)"""
    a = math.radians(graus)
    dx, dy = p[0] - centro[0], p[1] - centro[1]
    return centro[0] + dx * math.cos(a) - dy * math.sin(a), centro[1] + dx * math.sin(a) + dy * math.cos(a)


def camada(nome, img, x, y, ancora, ini=0, fim=10 ** 6, esc=E, sombra=None, boil="obj"):
    L = C.fixo(nome, img, x, y, ini=ini, fim=fim, esc=esc, sombra=sombra, boil=boil, ancora=ancora)
    L.tam = img.size if isinstance(img, Image.Image) else img.tam
    return L


def primeiro_degrau(q0, q1, fracao):
    """o 1º degrau de 7 qps em que a peça já se mexe (a borda própria entra aí, nem antes nem depois)"""
    return K.tempos_7qps(q0, q0 + (q1 - q0) * fracao)[1]


# o tranco: o crânio gira e volta; o cérebro chega atrasado, bate de um lado, depois do outro (2° de diferença:
# ele encosta na parede dentro do líquor). Regra: tranco pequeno demais esconde o atraso, que é o que explica
TRANCO_CRANIO = [(0, 0.0, "segura"), (480, 8.0, "segura"), (484, -2.5, "segura"), (488, 1.0, "segura"),
                 (492, -0.3, "segura"), (496, 0.0, "segura")]
TRANCO_CEREBRO = [(0, 0.0, "segura"), (480, 6.0, "segura"), (484, -0.5, "segura"), (488, 0.0, "segura"),
                  (492, 0.3, "segura"), (496, 0.0, "segura")]
# o nível do líquor (0 vazio, 1 cheio): enche em volta do cérebro, esvazia quando ele sai, enche quando ele volta
NIVEL = [(0, 0.0, "segura")] + K.curva_7qps(150, 174, 0.0, 1.0, "out") + \
    K.curva_7qps(SOBE[0], SOBE[0] + 12, 1.0, 0.0, "in") + K.curva_7qps(VOLTA[1] - 6, VOLTA[1] + 10, 0.0, 1.0, "out")


def boia(f):
    """o cérebro boiando: sobe e desce devagar (zero nas trocas de camada, para não pular)"""
    if 120 <= f < 276:
        return 6.0 * math.sin(2 * math.pi * (f - 120) / 52)
    if 414 <= f < 474:
        return 7.0 * math.sin(2 * math.pi * (f - 414) / 60)
    return 0.0


def liquor_fonte(img, ini):
    """o líquor enche como água: só aparece abaixo do nível, com a superfície ondulando (troca a 7 qps)"""
    la = np.asarray(img)
    h, w = la.shape[:2]
    _, y_top, _, y_bot = caixa(la[..., 3], 20)
    vazio = Image.new("RGBA", img.size, (0, 0, 0, 0))
    memo = {}
    Y = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)

    def fonte(fd, p):
        passo = int(math.floor((fd - ini) / K.PASSO_7))
        n = round(M.valor(NIVEL, ini + passo * K.PASSO_7, 0.0), 3)
        if n >= 0.999:
            return img
        if n <= 0.001:
            return vazio
        chave = (n, passo % 3)
        if chave not in memo:
            if len(memo) > 12:
                memo.clear()
            fase = (passo % 3) * 2.1
            linha = y_bot - n * (y_bot - y_top) + 6 * np.sin(xs / 70 + fase) + 3 * np.sin(xs / 23 + 2 * fase)
            abaixo = Y >= linha[None, :]
            a = la.copy()
            a[..., 3] = np.where(abaixo, a[..., 3], 0)
            sup = abaixo & (Y < linha[None, :] + 6) & (la[..., 3] > 20)
            a[sup, :3] = (a[sup, :3] * 0.62).astype(np.uint8)                 # a linha d'água, um azul mais fundo
            memo[chave] = Image.fromarray(a)
        return memo[chave]
    fonte.tam = img.size
    return fonte


def montar():
    c = []
    c.append(C.fundo_escuro(FIM, [(0, 1.0, "segura")], cor=(30, 33, 40)))   # contraste: o marfim no papel escuro

    # ---- silhuetas e a profundidade
    a_cranio, a_cer, a_liq, a_bas = alfa("cranio"), alfa("cerebro"), alfa("liquido"), alfa("base")
    # o líquor é uma faixa azul EM VOLTA do cérebro, POR BAIXO dele: o cérebro continua rosa e boia dentro dela. Por
    # cima, ele pintaria o cérebro de lilás (parece morto) e a água ficaria em pé acima do crânio
    anel = np.maximum(cv2.dilate(a_cer, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (55, 55))), a_liq)
    uniao = np.maximum.reduce([a_cranio, a_cer, anel])
    bas, cer, liq = rgb("base"), rgb("cerebro"), rgb("liquido")

    def na_frente(prev, obj, a_obj):
        """onde, na prévia base+objeto, o pixel é do objeto (ele está na frente da base)"""
        d_obj = np.abs(prev - obj).sum(axis=2)
        d_bas = np.abs(prev - bas).sum(axis=2)
        return (a_bas > 128) & (a_obj > 128) & (d_obj < d_bas)
    tras = na_frente(rgb("encaixe"), cer, a_cer) | na_frente(rgb("encaixe_liquido"), liq, a_liq)
    m_tras = np.pad(tras.astype(np.float32), PAD)

    base = papel(VA, "base", 1, sil=uniao, chave="_u")
    base_tras, base_frente = com_alfa(base, m_tras), com_alfa(base, 1 - m_tras)
    tampa_colada = papel(VA, "tampa", 2, sil=a_cranio, chave="_c")
    tampa_solta = papel(VA, "tampa", 2)
    cer_colado = papel(VA, "cerebro", 3, sil=uniao, chave="_u")
    cer_solto = papel(VA, "cerebro", 3)
    liquido = papel_rgba(np.dstack([np.full(anel.shape + (3,), (70, 130, 200), np.uint8), anel]), 4, "liquor_anel")

    piv = mundo_a(*PIV_PX)
    anc_piv = (PIV_PX[0] + PAD, PIV_PX[1] + PAD)
    cb = mundo_a(*CENTRO_C)                                           # o centro do cérebro no mundo
    anc_cer = (CENTRO_C[0] + PAD, CENTRO_C[1] + PAD)
    centro_img = ((AW + 2 * PAD) / 2, (AH + 2 * PAD) / 2)

    # ---- o giro do crânio (0–80), segura na vista 0 = a vista A até a tampa descolar
    vistas_b = [papel_giro(VB, "cranio", i, 60 + i, PXM_B) for i in range(36)]
    giro_b = K.giro("CRANIO_GIRO", vistas_b, *mundo_a(*CENTRO_B), C.k((0, 0.0, "lin"), (80, 360.0, "segura")),
                    ini=0, fim=T_ABRE, esc=E * PXM_A / PXM_B, sombra=(10, 22, 0.4))
    c.append(giro_b)

    # ---- a parede de trás (atrás do cérebro)
    tr = camada("BASE_TRAS", base_tras, *piv, anc_piv, ini=T_ABRE)
    tr.chaves["rot"] = TRANCO_CRANIO
    c.append(tr)

    # ---- o líquor: por baixo do cérebro (a faixa azul em volta dele) e da borda da frente
    lq = camada("LIQUOR", liquor_fonte(liquido, T_ABRE), *piv, anc_piv, ini=T_ABRE, fim=550)   # some sob a tampa
    lq.chaves["rot"] = TRANCO_CRANIO
    c.append(lq)

    # ---- o cérebro colado (no crânio, sem borda própria): boia e chega atrasado no tranco
    desc_cer = primeiro_degrau(SOBE[0], SOBE[1], 0.3)

    def pos_cer(f):
        th_c = M.valor(TRANCO_CEREBRO, f, 0.0)
        x, y = gira(cb, piv, th_c)
        return x, y + boia(f), th_c + 0.08 * boia(f)
    ts = sorted(set([T_ABRE] + K.tempos_7qps(T_ABRE, FIM) + [r[0] for r in TRANCO_CEREBRO if r[0] >= T_ABRE]))
    cc = camada("CEREBRO", cer_colado, *cb, anc_cer, ini=T_ABRE, sombra=(6, 12, 0.35))
    cc.chaves["x"] = [(t, pos_cer(t)[0], "segura") for t in ts]
    cc.chaves["y"] = [(t, pos_cer(t)[1], "segura") for t in ts]
    cc.chaves["rot"] = [(t, pos_cer(t)[2], "segura") for t in ts]
    cc.chaves["op"] = C.k((0, 1.0, "segura"), (desc_cer, 0.0, "segura"), (VOLTA[1], 1.0, "segura"))
    cc.sons = [("pouso", 484)]
    c.append(cc)

    # ---- o cérebro solto: descola (ganha a borda dele), sobe com a câmera, gira, volta e assenta
    _, yb0, _, _ = caixa(a_bas)
    bx0, by0, bx1, by1 = caixa(a_cer)
    borda_cranio = mundo_a(0, yb0)[1]
    P = (cb[0], borda_cranio - (by1 - CENTRO_C[1]) * E * 1.2 - 60)  # papel limpo acima do crânio aberto
    cs = camada("CEREBRO_SOLTO", cer_solto, *cb, anc_cer, ini=SOBE[0] - 4, fim=VOLTA[1] + 2, sombra=(6, 12, 0.35))
    K.destaca(cs, SOBE[0], SOBE[1], para=P, esc=1.2)
    K.pousa(cs, VOLTA[0], VOLTA[1], para=cb, esc=1 / 1.2)
    cs.sons = [("pouso", VOLTA[1] - 2)]
    cs.chaves["op"] = C.k((0, 0.0, "segura"), (desc_cer, 1.0, "segura"), (GIRA[0], 0.0, "segura"),
                          (GIRA[1], 1.0, "segura"), (VOLTA[1], 0.0, "segura"))
    c.append(cs)
    vistas_c = [papel_giro(VC, "cerebro", i, 30 + i, PXM_C) for i in range(36)]
    giro_c = K.giro("CEREBRO_GIRO", vistas_c, P[0], P[1], C.k((GIRA[0], 0.0, "lin"), (GIRA[1] - 8, 360.0, "segura")),
                    ini=GIRA[0], fim=GIRA[1], esc=E * PXM_A / PXM_C * 1.2, sombra=(20, 29, 0.25))
    c.append(giro_c)

    # ---- a borda da frente (o rosto e o aro do corte), na frente do cérebro
    fr = camada("BASE_FRENTE", base_frente, *piv, anc_piv, ini=T_ABRE, sombra=(10, 22, 0.4))
    fr.chaves["rot"] = TRANCO_CRANIO
    fr.sons = [("pouso", 480)]
    c.append(fr)

    # ---- a tampa: colada até o 1º degrau do levanta; aí ganha a borda dela, descola e sai voando. Volta no fim,
    #      assenta e cola de novo (sem a borda no corte, que virava costura branca)
    desc_tampa = primeiro_degrau(T_ABRE, 132, 0.35)
    c.append(camada("TAMPA_COLADA0", tampa_colada, X0, Y0, centro_img, ini=T_ABRE, fim=desc_tampa))
    tp = camada("TAMPA", tampa_solta, X0, Y0, centro_img, ini=desc_tampa, sombra=(10, 22, 0.4))
    K.levanta(tp, T_ABRE, 132, para=(760, -1350), giro=16.0)
    c.append(tp)
    tv = camada("TAMPA_VOLTA", tampa_solta, X0 + 760, Y0 - 1350, centro_img, ini=514, fim=550, sombra=(10, 22, 0.4))
    tv.chaves["rot"] = C.k((514, 16.0, "segura"))
    for ch, v in (("sdy", 4.0), ("sbl", 2.6), ("sop", 0.65)):
        tv.chaves[ch] = C.k((0, v, "segura"))
    K.pousa(tv, 514, 550, para=(X0, Y0))
    tv.sons = [("pouso", 548)]
    c.append(tv)
    c.append(camada("TAMPA_COLADA", tampa_colada, X0, Y0, centro_img, ini=550))

    # ---- o nome do líquor: etiqueta no papel limpo à direita (onde estava a tampa), seta de caneta clara até a água
    #      em volta do cérebro. A etiqueta já nasce no tamanho de leitura (o ajuste automático a aumentava 1,9x
    #      depois de posicionada e ela encostava no cérebro)
    x0c, y0c, x1c, y1c = caixa(a_cranio)
    et = PC.etiqueta(["LÍQUOR"], corpo=(76, 30), semente=71)
    ex, ey = mundo_a(x1c, by0 + 60)
    ex += 90 + et.width / 2
    c.append(C.cai("ET_LIQUOR", et, 186, ex, ey, rot=-3, sombra=(4, 8, 0.25), boil="paper", fim=278))
    so_agua = (anel > 128) & (a_cer < 30) & (a_bas < 30)                  # a faixa de água fora do cérebro
    if not so_agua.any():
        so_agua = (a_liq > 128) & (a_bas < 30)
    ys, xs = np.nonzero(so_agua)
    alvo_px = (ex - et.width / 2 - X0) / E + AW / 2, (ey - Y0) / E + AH / 2
    i = int(np.argmin((xs - alvo_px[0]) ** 2 + (ys - alvo_px[1]) ** 2))
    tx, ty = mundo_a(xs[i], ys[i])
    x_et = ex - et.width / 2 - 14
    seta = C.Traco("SETA_LIQUOR", [(x_et, ey + 10), ((x_et + tx) / 2, (ey + ty) / 2 + 30), (tx + 12, ty + 4)],
                   192, 206, espessura=8, cor=(240, 232, 214), seta=True, tam_seta=26, fim=278, suave=True, semente=4)
    c.append(seta.camada)

    # ---- o soco: a luva de boxe entra pela direita, bate na frente do queixo, acompanha o tranco e volta. Regra: só
    #      riscos no queixo não mostram o soco; a ação tem que se ver sem som
    ys, xs = np.nonzero(a_cranio > 128)
    queixo = ys >= ys.max() - 120
    qx, qy = mundo_a(xs[queixo].max(), ys.max() - 70)                 # a frente do queixo
    luva = luva_soco()
    esc_l = 820 / luva.width                                          # ~0,75 do tamanho real ao lado do crânio
    lv = camada("LUVA", luva, qx + 1150, qy - 20, (10, luva.height * 0.5), ini=464, fim=502, esc=esc_l,
                sombra=(14, 26, 0.35))
    lv.chaves["x"] = C.k((464, qx + 1150, "in"), (479, qx + 6, "segura"), (480, qx - 46, "out"),
                         (487, qx + 240, "in"), (500, qx + 1300, "segura"))
    lv.chaves["rot"] = C.k((464, -7.0, "out"), (479, 0.0, "segura"))
    lv.som = ("desliza", 468, 1)
    c.append(lv)
    c.append(C.rajada("RAJ_SOCO", qx + 10, qy - 20, 479, raio=260, n=12, dur=9, espessura=14))

    for i, (txt, q0, q1) in enumerate([("Dentro da sua cabeça, agora,", 8, 94),
                                       ("seu cérebro está *boiando*.", 136, 200),
                                       ("Num líquido chamado *líquor*.", 210, 276),
                                       ("Ele pesa *1,4 kg*...", 310, 376),
                                       ("...mas no líquor, parece pesar só *25 g*.", 414, 476),
                                       ("Por isso um soco no queixo *chacoalha* o cérebro.", 484, 548),
                                       ("E o líquor *amortece* o tranco.", 556, FIM)]):
        if CM.LEGENDAS:                                    # legenda de fala: desligada por padrão
            c.append(C.legenda(f"LEG{i}", PC.legenda(txt, semente=120 + i), q0, q1))
    c.append(C.vinheta(FIM))

    # ---- câmera: o crânio inteiro; abre espaço para a etiqueta; sobe com o cérebro e desce com ele
    Q = C.quadro
    w0, h0 = mundo_a(x0c, y0c)
    w1, h1 = mundo_a(x1c, y1c)
    inteiro = Q((w0 - 40, h0 - 40, w1 + 40, h1 + 40))
    rotulo = Q((w0 - 40, h0 - 40, ex + et.width / 2 + 40, h1 + 40))
    k = E * 1.2                                                       # o cérebro no ar, enquadrado pela caixa dele
    alto = Q((P[0] + (bx0 - CENTRO_C[0]) * k - 70, P[1] + (by0 - CENTRO_C[1]) * k - 70,
              P[0] + (bx1 - CENTRO_C[0]) * k + 70, P[1] + (by1 - CENTRO_C[1]) * k + 70))
    m_sobe = SOBE[0] + (SOBE[1] - SOBE[0]) * 0.3                      # a câmera anda junto com o "vai" do destaca
    m_desce = VOLTA[0] + (VOLTA[1] - VOLTA[0]) * 0.75                 # e com o "vai" do pousa
    soco = Q((w0 - 40, h0 - 40, w1 + 520, h1 + 40))                     # espaço à direita para a luva inteira
    cam = C.Camera()
    for q, dx, dy, r in ((480, -16, 7, 0.7), (483, 9, -4, -0.4), (486, -3, 2, 0.1), (489, 0, 0, 0.0)):
        cam.plano(q, (soco[0], soco[1] + dx, soco[2] + dy, r), "segura")   # a câmera treme no impacto
    cam = (cam
           .plano(0, inteiro, "segura")
           .plano(452, inteiro, "io").plano(470, soco, "segura")
           .plano(500, soco, "io").plano(516, inteiro, "segura")
           .plano(158, inteiro, "io").plano(182, rotulo, "segura")
           .plano(m_sobe, rotulo, "io").plano(SOBE[1], alto, "segura")
           .plano(VOLTA[0], alto, "io").plano(m_desce, inteiro, "segura")
           .montar())
    return c, cam


if __name__ == "__main__":
    camadas, cam = montar()
    for aj in M.ajustar_texto(camadas, cam, FIM):
        print("texto aumentado:", aj)
    fundo = PC.papel_mundo(2400, 2800)
    prev = AQUI / "previa"
    if "--conferir" in sys.argv:
        for nome, pasta in (("A", VA), ("giro crânio", VB), ("giro cérebro", VC)):
            for x in CF.lascas(pasta):
                print("LASCA", nome, x)
        fora = ("LEG", "VINHETA", "FUNDO", "ET_", "SETA", "RAJ_")
        so_figura = [L for L in camadas if not L.nome.startswith(fora)]
        magenta = Image.new("RGB", (2400, 2800), (255, 0, 255))
        q = [160, 0, 40, 97, 98, 102, 116, 132, 176, 240, 284, 300, 340, 384, 404, 440, 480, 484, 488, 530, 550, 590]
        pasta = prev / "cranio_conferir"
        M.render(so_figura, cam, magenta, FIM, pasta, quadros=q, acab=False, borrao=False)
        for x in CF.composto(pasta, ref=pasta / "q0160.png"):
            print("PROBLEMA", x)
    elif "--video" in sys.argv:
        M.render(camadas, cam, fundo, FIM, prev / "cranio.mp4")
    elif "--som" in sys.argv:
        import som as S, som_auto as SA
        r = SA.mixar_auto(camadas, cam, (), CM.trilha(), FIM, CR / "som", inicio=0.0,
                          licenca=CM.TRILHA_LICENCA)
        print("mix", r["master"], "final", S.juntar(prev / "cranio.mp4", CR / "som" / "mix.wav", prev / "cranio_som.mp4"))
    else:
        args = [a for a in sys.argv[1:] if a.replace(",", "").isdigit()]
        q = [int(x) for x in args[0].split(",")] if args else \
            [0, 40, 97, 98, 104, 132, 166, 196, 240, 286, 300, 340, 384, 404, 440, 480, 484, 520, 550, 590]
        M.render(camadas, cam, fundo, FIM, prev / "cranio", quadros=q)
    print("ok")
