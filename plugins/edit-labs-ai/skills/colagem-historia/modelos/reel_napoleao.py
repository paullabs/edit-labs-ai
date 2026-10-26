"""Modelo de reel de curiosidade histórica: "a medida desmente o mito" (exemplo: Napoleão não era baixinho).

31 s, 9:16 (1080×1920), sem voz, colagem de papel antigo. Copie este arquivo para PROJETO/ferramentas/reel.py e troque
só o bloco "1. O QUE TROCAR". As fotos vêm de PROJETO/pecas/ (veja modelos/LEIA.md da skill: o que baixar e com
que licença).

    clpy ferramentas/reel.py --folha            -> previa/folha_pecas.jpg (todas as peças sobre azul)
    clpy ferramentas/reel.py --quadros 10,120   -> previa/quadros/qNNNN.png (quadros de conferência)
    clpy ferramentas/reel.py --margens          -> lista objetos cortados ou fora da margem segura
    clpy ferramentas/reel.py --video            -> previa/sem_som.mp4
    clpy ferramentas/reel.py --som              -> som/mix.wav + entrega/<NOME>.mp4 (depois do --video)
    --sem-texto                                 -> sem legendas e carimbos (o texto entra por último)

clpy é o Python do motor de colagem do plugin (editlabs-setup --colagem). Sem ele: python3 com numpy, Pillow e
OpenCV, e EDITLABS_MOTOR=<raiz do plugin>/motor/colagem.

Mundo de papel 7000×5000, em ESCALA REAL na régua: 10 px do mundo = 1 cm, chão em y=3000.
  K (alto à direita): o objeto real que abre o vídeo.
  H (centro): régua de altura, a pessoa e quem a fazia parecer menor; as imagens do mito viram no lugar dela.
  S (embaixo à direita, papel carvão): o lugar do momento dramático, o objeto que chega, o objeto do drama e o
    documento com a medida.
Os tempos estão em quadros no relógio de autoria (24 por segundo); o motor sai a 28 qps com 14 desenhos por segundo.
"""
import argparse
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

AQUI = Path(__file__).resolve().parent


def _achar_motor():
    """EDITLABS_MOTOR > CLAUDE_PLUGIN_ROOT/motor/colagem > a pasta motor/colagem de algum pai deste arquivo"""
    cands = []
    if os.environ.get("EDITLABS_MOTOR"):
        cands.append(Path(os.environ["EDITLABS_MOTOR"]))
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        cands.append(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "motor" / "colagem")
    cands += [p / "motor" / "colagem" for p in AQUI.parents]
    for c in cands:
        if (c / "motor.py").exists():
            return c
    sys.exit("Não achei o motor de colagem. Rode com EDITLABS_MOTOR=<raiz do plugin>/motor/colagem")


def _achar_projeto():
    """REEL_PROJETO > a pasta acima de ferramentas/ > a pasta onde o comando foi rodado"""
    if os.environ.get("REEL_PROJETO"):
        return Path(os.environ["REEL_PROJETO"]).resolve()
    return AQUI.parent if AQUI.name == "ferramentas" else Path.cwd().resolve()


sys.path.insert(0, str(_achar_motor()))
import motor as M          # noqa: E402  camadas, câmera, boil, transições, render
import pecas as PC         # noqa: E402  cartão com fita, recorte com borda de tesoura, etiqueta, carimbo, legenda
import cena as C           # noqa: E402  cai, desliza, vira, traço de caneta, carimbo, câmera por planos
# som e som_auto só entram no --som (precisam da biblioteca de efeitos configurada no motor)

PROJ = _achar_projeto()
P = PROJ / "pecas"

# =====================================================================================================================
# 1. O QUE TROCAR
# =====================================================================================================================
NOME = "napoleao_altura"                    # nome do arquivo final em entrega/
FIM = 744                                   # duração em quadros de 24 (744 = 31 s)
MUNDO = (7000, 5000)                        # tamanho do mundo de papel (px)
CHAO, PXCM = 3000, 10.0                     # régua: chão em y=3000 do mundo, 10 px por cm (escala real)
RX = 1080                                   # x da tira da régua

# trilha calma (você baixa e licencia; não vai junto com o projeto se a licença proibir redistribuir)
TRILHA = "trilha.mp3"                       # em pecas/
TRILHA_INI = 42.0                           # segundo da trilha onde começa o trecho calmo (meça: poucos ataques)
TRILHA_LICENCA = "trilha: veja CREDITOS.md do projeto"

# arquivos em PROJETO/pecas/ (PNG = recorte com alfa; JPG = foto que vira cartão)
ARQ = {
    "pessoa": "pessoa_em_pe.png",           # a pessoa em pé, corpo inteiro (o retrato de David, 1812)
    "contraste": "contraste_em_pe.png",     # quem a fazia parecer menor (o granadeiro da Guarda Imperial)
    "mito": "mito.jpg",                     # a imagem do mito, que vira no lugar da pessoa (caricatura, 1803)
    "mito2": "mito2.jpg",                   # a 2ª imagem do mito, que entra embaixo (o rei e o Napoleão minúsculo)
    "lugar": "lugar.jpg",                   # o lugar do momento dramático (mapa de Santa Helena)
    "documento": "documento.jpg",           # a página com a medida (memórias do médico, 1825)
    "obj_abre": "obj_abertura.png",         # o objeto real que abre o vídeo (o chapéu dele)
    "obj_chega": "obj_chegada.png",         # o objeto que chega ao lugar (o navio)
    "obj_drama": "obj_drama.png",           # o objeto do momento dramático (a máscara mortuária)
    "regua_errada": "regua_errada.png",     # a unidade que gera o mito (régua em polegada inglesa)
    "regua_certa": "regua_certa.png",       # a unidade certa (a régua do rei, em polegada francesa)
}

# altura real (cm) e onde ficam o topo da cabeça e a sola no recorte de ENTRADA (px); None = caixa do alfa
ALTURA_CM = {"pessoa": 169, "contraste": 178}
# (os valores abaixo são dos recortes do exemplo; com outro recorte, meça de novo ou use None)
TOPO_SOLA = {"pessoa": (40, 4404), "contraste": (250, 1660)}   # o granadeiro: topo da cabeça sob o gorro

# pontos dentro das imagens, em fração (0–1) da foto
MITO2_ALVO = (0.215, 0.46)                  # onde está o Napoleão minúsculo na 2ª caricatura (círculo de caneta)
DOC_CAIXA = (0.028, 0.250, 0.984, 0.569)    # o pedaço da página que entra no cartão (x0, y0, x1, y1)
DOC_SUBLINHA = [((0.515, 0.504), (0.980, 0.502)),       # a caneta sublinha a medida (em fração do pedaço)
                ((0.005, 0.580), (0.284, 0.579))]
DOC_FOCO = (0.510, 0.509)                   # onde a câmera mergulha na página
REGUA_CERTA_CIRCULO = (0.44, 0.14)          # onde a caneta circula a palavra da unidade (fração da peça)

# as três marcas da régua: (cm, etiqueta). A 1ª é riscada (o mito), a última é a resposta.
MEDIDAS = [(157, ["1,57 m"]), (165, ["1,65 m", "francês médio"]), (169, ["1,69 m", "Napoleão"])]
RESPOSTA = "1,69 m"                         # letras que se montam no alto, no fecho

# texto: pouco (≈ 40 palavras de legenda no vídeo todo); *palavra* sai em vermelho
LEGENDAS = [
    "Napoleão *não* era baixinho.",
    "Os ingleses o desenhavam\n*minúsculo*.",
    "Ao lado da Guarda,\nele *parecia* baixo.",
    "A medida: *5 pés e 2 polegadas*.",
    "Em polegada inglesa: *1,57 m*.",
    "Mas a polegada francesa\nera *maior*.",
    "O francês médio: *1,65 m*.",
]
TEMPOS_LEG = [(-2, 48), (124, 210), (222, 300), (330, 418), (436, 494), (500, 566), (574, 640)]
ETIQUETAS = {
    "pessoa": ["NAPOLEÃO", "1769–1821"],
    "contraste": ["GUARDA IMPERIAL", "1,75 m ou mais"],
    "obj_abre": ["O CHAPÉU DE NAPOLEÃO", "Musée de l'Armée, Paris"],
    "obj_drama": ["MÁSCARA MORTUÁRIA", "Santa Helena, 1821"],
    "regua_errada": ["POLEGADA INGLESA", "2,54 cm"],
    "regua_certa": ["POLEGADA FRANCESA", "2,71 cm"],
}
CARIMBOS = {"pergunta": "?", "mito": "GILLRAY · 1803", "lugar": "SANTA HELENA · 1821", "fecho": "ACIMA DA MÉDIA"}

# região segura da tela (REGRAS.md): x 80–960, y 260–1420; o assunto fica acima da legenda (y 1320)
REGIAO = (80, 260, 960, 1190)
REGIAO_SEM_LEG = (80, 260, 960, 1420)
# =====================================================================================================================


def y_cm(cm):
    return CHAO - cm * PXCM


def _arq(chave):
    return P / ARQ[chave]


TEXTO_FINAL = ("LEG", "c_", "RAJ_", "RESP")      # camadas de texto que entram por último (--sem-texto)


def conferir_pecas():
    falta = [f"pecas/{v}" for v in ARQ.values() if not (P / v).exists()]
    if falta:
        sys.exit("Faltam peças em " + str(P) + ":\n  " + "\n  ".join(falta) + "\nVeja modelos/LEIA.md.")


def em_cartao(centro, peca, larg, foto_px, rel):
    """ponto relativo (0–1) da foto impressa num cartão (pad 40 + borda 22) → mundo"""
    w, h = peca.size
    fw, fh = foto_px
    return (centro[0] - w / 2 + 62 + rel[0] * larg, centro[1] - h / 2 + 62 + rel[1] * larg * fh / fw)


def recorte_em_escala(chave, semente, **kw):
    """recorte de pessoa em escala real: topo da cabeça → sola = ALTURA_CM × PXCM. Devolve (peça, mapa, topo, sola, xc)"""
    im = Image.open(_arq(chave)).convert("RGBA")
    bx0, by0, bx1, by1 = im.getchannel("A").getbbox()
    topo, sola = TOPO_SOLA.get(chave) or (by0, by1)
    escala = ALTURA_CM[chave] * PXCM / (sola - topo)
    borda = kw.get("borda", 12)
    alt = round((by1 - by0 + 2 * (borda + 4)) * escala)
    peca, mapa = PC.recorte(im, alt=alt, semente=semente, mapa=True, **kw)
    return peca, mapa, topo, sola, (bx0 + bx1) / 2


def pecas():
    conferir_pecas()
    p = {}
    p["pessoa"], p["m_pessoa"], p["topo_p"], p["sola_p"], p["xc_p"] = recorte_em_escala("pessoa", 11, envelhece=True)
    p["contraste"], p["m_contraste"], p["topo_c"], p["sola_c"], p["xc_c"] = recorte_em_escala("contraste", 12)
    p["regua"], p["regua_anc"] = regua_altura()
    p["regua_certa"] = PC.recorte(_arq("regua_certa"), larg=500, semente=13, envelhece=True)
    p["mito2_px"] = Image.open(_arq("mito2")).size
    p["mito2"] = PC.cartao(Image.open(_arq("mito2")), 700, semente=21, fitas=((0.2, -12), (0.8, 10)))
    p["mito"] = PC.cartao(Image.open(_arq("mito")), 820, semente=22, fitas=((0.5, 5),))
    p["lugar"] = PC.cartao(Image.open(_arq("lugar")), 640, semente=23, sepia=True)
    pag = Image.open(_arq("documento")).convert("RGB")
    w, h = pag.size
    x0, y0, x1, y1 = DOC_CAIXA
    p["pag_px"] = (round((x1 - x0) * w), round((y1 - y0) * h))
    p["pag"] = PC.cartao(pag.crop((round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h))), 1100, semente=24,
                         envelhece=False, fitas=((0.1, -10), (0.9, 8)))
    p["obj_abre"] = PC.recorte(_arq("obj_abre"), larg=900, envelhece=True, semente=81, borda=10)
    p["obj_chega"] = PC.recorte(_arq("obj_chega"), larg=700, envelhece=True, semente=82, borda=8, sepia=True)
    p["obj_drama"] = PC.recorte(_arq("obj_drama"), alt=560, envelhece=True, semente=83, borda=10)
    p["regua_errada"] = PC.recorte(_arq("regua_errada"), alt=900, envelhece=True, semente=84, borda=8)
    p["et_pessoa"] = PC.etiqueta(ETIQUETAS["pessoa"], semente=31)
    p["et_contraste"] = PC.etiqueta(ETIQUETAS["contraste"], semente=32)
    p["et_obj_abre"] = PC.etiqueta(ETIQUETAS["obj_abre"], corpo=(36, 26), semente=88)
    p["et_obj_drama"] = PC.etiqueta(ETIQUETAS["obj_drama"], semente=85)
    p["et_regua_errada"] = PC.etiqueta(ETIQUETAS["regua_errada"], corpo=(36, 28), semente=86)
    p["et_regua_certa"] = PC.etiqueta(ETIQUETAS["regua_certa"], corpo=(36, 28), cor=PC.VERMELHO, semente=87)
    (cm0, t0), (cm1, t1), (cm2, t2) = MEDIDAS
    p["m0"] = PC.etiqueta(t0, corpo=(46,), fontes=("ArchivoBlack-Regular.ttf",), semente=41)
    p["m1"] = PC.etiqueta(t1, corpo=(44, 26), semente=42)
    p["m2"] = PC.etiqueta(t2, corpo=(44, 26), cor=PC.VERMELHO, semente=43)
    for k, t in CARIMBOS.items():
        p["c_" + k] = PC.carimbo(t, semente=50 + len(t))
    for i, t in enumerate(LEGENDAS):
        p[f"leg{i}"] = PC.legenda(t, semente=60 + i)
    return p


def regua_altura():
    """tira de papel do chão a 2,10 m: marca a cada 5 cm, número a cada 10 cm (de 1,00 m para cima)"""
    larg_tira, alto = 96, int(212 * PXCM)
    W = 420
    im = Image.new("RGBA", (W, alto + 120), (0, 0, 0, 0))
    tira = PC.rasgar(PC.textura_papel(larg_tira, alto + 40, (236, 226, 200), 11), amp=3, passo=30, semente=11)
    ox = W - 40 - larg_tira
    im.alpha_composite(tira, (ox, 40))
    d = ImageDraw.Draw(im)
    fo = PC.fonte("IBMPlexMono-Medium.ttf", 30)
    base = 40 + alto                                        # y do chão dentro da imagem
    for cm in range(0, 211, 5):
        y = base - cm * PXCM
        grande = cm % 10 == 0
        d.line([(ox, y), (ox + (40 if grande else 20), y)], fill=PC.TINTA + (255,), width=3 if grande else 2)
        if grande and cm >= 100:
            t = f"{cm // 100},{cm % 100:02d}"
            d.text((ox - 14 - fo.getlength(t), y - 18), t, font=fo, fill=PC.TINTA + (255,))
    for k, cm in enumerate((30, 120, 190)):
        f = PC.fita(110, 38, 5 if k % 2 else -4, k)
        im.alpha_composite(f, (ox + larg_tira // 2 - f.width // 2, int(base - cm * PXCM - f.height / 2)))
    return im, (ox + larg_tira / 2, base)                  # âncora: (x da tira, y do chão)


def pos(peca, mapa, centro, ponto):
    """onde o ponto (px da imagem de entrada) cai no mundo, com a peça centrada em 'centro'"""
    w, h = peca.size
    x, y = mapa(*ponto)
    return centro[0] - w / 2 + x, centro[1] - h / 2 + y


def Q(caixa, regiao=REGIAO):
    return C.quadro(caixa, regiao=regiao)


def montar(p):
    c = []
    et = dict(sombra=(4, 8, 0.2), boil="paper")
    # ---- K: o objeto real abre o vídeo (o olho chega num objeto, não num texto)
    KX, KY = 4400, 650
    c.append(C.fixo("GRADE_K", PC.grade(1400, 1400, passo=70), KX, KY, boil=None, sombra=None))
    c.append(C.cai("OBJ_ABRE", p["obj_abre"], -2, KX, KY, rot=-3, de_y=-180, sombra=(16, 28, 0.35)))
    c.append(C.cai("ET_OBJ_ABRE", p["et_obj_abre"], 14, KX - 120, KY + 300, rot=2, **et))
    # ---- H: a régua em escala real, a pessoa com a sola no chão, quem a fazia parecer menor
    c.append(C.fixo("REGUA", p["regua"], RX, CHAO, ancora=p["regua_anc"], sombra=(4, 10, 0.18), boil="paper"))
    pes = p["pessoa"]
    _, ysola = p["m_pessoa"](p["xc_p"], p["sola_p"])
    NX = 1560
    NY = CHAO - ysola + pes.height / 2
    CAB = pos(pes, p["m_pessoa"], (NX, NY), (p["xc_p"], p["topo_p"]))
    c.append(C.fixo("PESSOA", pes, NX, NY, ini=0, fim=120, sombra=(16, 26, 0.3)))
    c.append(C.cai("ET_PESSOA", p["et_pessoa"], 70, NX + 330, y_cm(118), rot=3, fim=120, **et))
    # o mito: o retrato vira a caricatura e volta (cartão que vira)
    c += C.vira("V1", pes, p["mito"], 120, NX, NY, ini=120, fim=210, esc_v=0.95)
    c += C.vira("V2", p["mito"], pes, 210, NX, NY, ini=210, esc_f=0.95)
    c.append(C.cai("ET_PESSOA2", p["et_pessoa"], 222, NX + 290, y_cm(118), rot=3, **et))
    # a caneta sobe pela régua até a cabeça (a medida é a assinatura do reel)
    medir = C.Traco("MEDE", [(RX, CHAO - 10), (RX, y_cm(ALTURA_CM["pessoa"]))], 66, 100, espessura=20, tremor=1.0)
    c.append(medir.camada)
    c.append(C.carimbo("c_pergunta", p["c_pergunta"], 104, RX - 40, y_cm(184), -8, esc=0.9, fim=120))
    c.append(C.rajada("RAJ_Q", RX - 40, y_cm(184), 104, raio=300, cor=PC.VERMELHO))
    ct = p["contraste"]
    _, ysg = p["m_contraste"](p["xc_c"], p["sola_c"])
    GX = 2520
    GY = CHAO - ysg + ct.height / 2
    TOPO_C = pos(ct, p["m_contraste"], (GX, GY), (p["xc_c"], p["topo_c"]))
    c.append(C.desliza("CONTRASTE", ct, 218, (GX + 1600, GY), (GX, GY), dur=12, sombra=(16, 26, 0.3), fim=300))
    c.append(C.cai("ET_CONTRASTE", p["et_contraste"], 232, GX - 160, y_cm(52), rot=-3, fim=300, **et))
    c.append(C.Traco("LINHA_ALTURA", [(TOPO_C[0] + 60, TOPO_C[1]), (CAB[0] - 120, TOPO_C[1])], 244, 260, espessura=14,
                     tracejado=(34, 22), curva="out", fim=420).camada)
    # a 2ª imagem do mito entra embaixo (empilhadas, as duas cabem grandes)
    BX, BY = NX, NY + 760
    c.append(M.Camada("MITO2", p["mito2"], 128, 220, boil="obj", sombra=(10, 22, 0.28), chaves={
        "x": C.k((128, BX + 1500, "out"), (138, BX, "segura"), (204, BX, "in"), (214, BX + 1800, "segura")),
        "y": C.k((128, BY, "segura")),
        "rot": C.k((128, 3, "out"), (138, -3, "segura"), (204, -3, "in"), (214, 8, "segura"))}))
    alvo = em_cartao((BX, BY), p["mito2"], 700, p["mito2_px"], MITO2_ALVO)
    c.append(C.circulo("CIRC_MITO2", alvo[0], alvo[1], 80, 120, 150, 166, fim=204))
    c.append(C.carimbo("c_mito", p["c_mito"], 142, NX + 60, NY + 300, -6, esc=0.55, fim=210))
    # ---- S: o momento dramático no papel carvão (fica preso à área, longe das vizinhas)
    SX, SY = 5900, 3900
    c.append(C.papel_area("PAPEL_S", (SX - 1600, SY - 1750, SX + 1600, SY + 2900)))
    c.append(C.fixo("LUGAR", p["lugar"], SX + 300, SY - 780, rot=5))
    c.append(C.desliza("OBJ_CHEGA", p["obj_chega"], 316, (SX - 1500, SY - 880), (SX - 300, SY - 900), dur=18,
                       sombra=(12, 20, 0.3)))
    c.append(C.carimbo("c_lugar", p["c_lugar"], 340, SX + 260, SY - 430, -7, esc=0.55))
    c.append(C.rajada("RAJ_LUGAR", SX + 260, SY - 430, 340, raio=380))
    MKX, MKY = SX - 420, SY + 120
    c.append(C.cai("OBJ_DRAMA", p["obj_drama"], 348, MKX, MKY, rot=-6, de_y=-200, sombra=(16, 26, 0.35)))
    c.append(C.cai("ET_OBJ_DRAMA", p["et_obj_drama"], 356, MKX + 260, MKY + 330, rot=2, fim=380, **et))
    PGX, PGY = SX + 260, SY + 980
    c.append(C.fixo("PAG", p["pag"], PGX, PGY, rot=-2))

    def na_pag(rel):
        return em_cartao((PGX, PGY), p["pag"], 1100, p["pag_px"], rel)
    for i, (a, b) in enumerate(DOC_SUBLINHA):
        q0 = 384 + i * 16
        c.append(C.Traco(f"SUB{i}", [na_pag(a), na_pag(b)], q0, q0 + 14 - 6 * i, espessura=14, curva="out").camada)
    FOCO_PAG = na_pag(DOC_FOCO)
    # ---- de volta à régua: a medida errada (riscada), as duas unidades, a média, a resposta
    (cm0, _), (cm1, _), (cm2, _) = MEDIDAS

    def marca(nome, cm, q0, q1, **kw):
        return C.Traco(nome, [(RX - 60, y_cm(cm)), (NX + 250, y_cm(cm))], q0, q1, espessura=14, curva="out", **kw)
    c.append(marca("M0", cm0, 436, 450, tracejado=(30, 18)).camada)
    c.append(C.cai("ET_M0", p["m0"], 450, RX - 230, y_cm(cm0), rot=-3, **et))
    c.append(C.Traco("X0a", [(RX - 320, y_cm(cm0) - 50), (RX - 140, y_cm(cm0) + 50)], 466, 472, espessura=20,
                     curva="out").camada)
    c.append(C.Traco("X0b", [(RX - 140, y_cm(cm0) - 50), (RX - 320, y_cm(cm0) + 50)], 472, 478, espessura=20,
                     curva="out").camada)
    PX_, PY_ = RX - 230, y_cm(112)
    IX, IY = RX - 640, y_cm(98)
    c.append(C.desliza("REGUA_ERRADA", p["regua_errada"], 496, (IX - 1200, IY), (IX, IY), rot=-4, dur=10,
                       sombra=(10, 18, 0.3), fim=572))
    c.append(C.cai("ET_REGUA_ERRADA", p["et_regua_errada"], 506, IX + 10, IY + 520, rot=-3, fim=572, **et))
    c.append(C.cai("REGUA_CERTA", p["regua_certa"], 512, PX_, PY_, rot=-6, de_y=-200, sombra=(10, 18, 0.3), fim=572))
    c.append(C.cai("ET_REGUA_CERTA", p["et_regua_certa"], 520, PX_ + 40, PY_ + 220, rot=3, fim=572, **et))
    pdw, pdh = p["regua_certa"].size
    fx, fy = REGUA_CERTA_CIRCULO
    c.append(C.circulo("CIRC_UNIDADE", PX_ + pdw * (fx - 0.5), PY_ + pdh * (fy - 0.5), 105, 52, 530, 544, rot=-8,
                       espessura=18, fim=572))
    c.append(marca("M1", cm1, 572, 586).camada)
    c.append(C.cai("ET_M1", p["m1"], 586, NX + 390, y_cm(cm1) + 62, rot=2, **et))
    c.append(marca("M2", cm2, 646, 660).camada)
    c.append(C.cai("ET_M2", p["m2"], 660, NX + 390, y_cm(cm2) - 74, rot=-2, **et))
    c.append(C.Traco("VISTO", [(CAB[0] + 150, y_cm(cm2 + 7)), (CAB[0] + 190, y_cm(cm2 + 2)),
                               (CAB[0] + 270, y_cm(cm2 + 14))], 670, 680, espessura=20, curva="out").camada)
    c.append(C.rajada("RAJ_RESP", CAB[0], y_cm(cm2 + 2), 662, raio=380, cor=PC.VERMELHO))
    c.append(C.carimbo("c_fecho", p["c_fecho"], 694, 540, 1320, -4, esc=0.72, mundo=False))   # no lugar da legenda
    c += C.letras("RESP", RESPOSTA, 652, 540, 400, corpo=170, cor=PC.VERMELHO, passo=2)        # a resposta, no alto
    # ---- legendas (sempre no mesmo lugar: y 1320)
    for i, (a, b) in enumerate(TEMPOS_LEG[:len(LEGENDAS)]):
        c.append(C.legenda(f"LEG{i}", p[f"leg{i}"], a, b, rot=1.0 if i % 2 else -1.2))
    c.append(C.vinheta(FIM))
    # ---- câmera: um plano por batida, deriva lenta (×1,02–1,04) e chegada antes do texto
    K1 = Q((KX - 500, KY - 380, KX + 500, KY + 420))
    H_PES = Q((RX - 330, y_cm(198), NX + 440, CHAO + 40), REGIAO_SEM_LEG)
    H_MITO = Q((NX - 470, NY - 420, NX + 470, BY + 360))
    H_ALL = Q((RX - 260, y_cm(212), GX + 420, CHAO + 40))
    S1a = Q((SX - 880, SY - 1360, SX + 760, SY - 380))
    S1b = Q((SX - 760, SY - 260, SX + 940, SY + 1100))
    S2 = (1.0, FOCO_PAG[0] - 40, FOCO_PAG[1] + 350, 0.0)            # mergulho na linha da medida
    H_CAB = Q((RX - 360, y_cm(205), NX + 540, y_cm(95)))
    RG = Q((IX - 330, y_cm(160), PX_ + 380, y_cm(40)))
    H_FIM = Q((RX - 360, y_cm(196), NX + 540, y_cm(80)), (80, 470, 960, 1420))   # o alto fica para a resposta

    def deriva(z, f=1.03):
        return (z[0] * f,) + z[1:]
    cam = (C.Camera()
           .plano(0, K1, "lin").plano(48, deriva(K1, 1.04), "segura")
           .plano(64, H_PES, "lin").plano(118, deriva(H_PES), "io")
           .plano(134, H_MITO, "lin").plano(206, deriva(H_MITO), "io")
           .plano(226, H_ALL, "lin").plano(300, deriva(H_ALL), "segura")
           .plano(318, S1a, "lin").plano(346, deriva(S1a), "io")
           .plano(360, S1b, "lin").plano(370, S1b, "io")
           .plano(382, S2, "lin").plano(418, deriva(S2, 1.04), "segura")
           .plano(434, H_CAB, "lin").plano(494, deriva(H_CAB, 1.02), "io")
           .plano(508, RG, "lin").plano(560, deriva(RG), "io")
           .plano(574, H_CAB, "lin").plano(646, deriva(H_CAB), "io")
           .plano(664, H_FIM, "lin").plano(FIM, deriva(H_FIM), "segura")
           .montar())
    # transições variadas, saindo de onde o olho está
    trans = [M.Transicao(48, 64, "iris", centro=M.na_tela(cam.matriz(48), (KX, KY))),
             M.Transicao(300, 318, "iris", centro=M.na_tela(cam.matriz(300), CAB)),
             M.Transicao(418, 434, "rasgo", semente=7)]
    return c, cam, {"medir": medir, "trans": trans}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--folha", action="store_true", help="folha com todas as peças sobre azul")
    ap.add_argument("--quadros", help="quadros (relógio de 24) separados por vírgula, ex.: 10,120,300")
    ap.add_argument("--margens", action="store_true", help="lista objetos cortados ou fora da margem segura")
    ap.add_argument("--video", action="store_true", help="previa/sem_som.mp4")
    ap.add_argument("--som", action="store_true", help="som/mix.wav e entrega/<NOME>.mp4 (depois do --video)")
    ap.add_argument("--sem-texto", action="store_true",
                    help="sem legendas, carimbos e resposta (o texto entra por último)")
    a = ap.parse_args()
    p = pecas()
    previa = PROJ / "previa"
    previa.mkdir(exist_ok=True)
    if a.folha:
        PC.folha(sorted((k, v) for k, v in p.items() if isinstance(v, Image.Image)), previa / "folha_pecas.jpg")
    camadas, cam, extra = montar(p)
    if a.sem_texto:
        camadas = [L for L in camadas if not L.nome.startswith(TEXTO_FINAL)]
    for aj in M.ajustar_texto(camadas, cam, FIM, extra.get("trans", ())):
        print("texto aumentado:", aj)
    if a.margens:
        for achado in M.checar_margens(camadas, cam, range(0, FIM, 12), regiao=REGIAO_SEM_LEG):
            print("margem:", achado)
    fundo = PC.papel_mundo(*MUNDO)
    if a.quadros:
        M.render(camadas, cam, fundo, FIM, previa / "quadros", quadros=[int(x) for x in a.quadros.split(",")],
                 transicoes=extra["trans"])
    if a.video:
        M.render(camadas, cam, fundo, FIM, previa / "sem_som.mp4", transicoes=extra["trans"])
    if a.som:
        import som as S            # juntar vídeo e som
        import som_auto as SA      # efeitos lidos da cena + trilha calma, master -20 LUFS
        trilha = P / TRILHA
        if not trilha.exists():                       # a pasta de trilhas do motor ($EDITLABS_DATA/colagem/trilhas)
            import recursos
            trilha = Path(getattr(recursos, "TRILHAS", P)) / TRILHA
        if not trilha.exists():
            sys.exit(f"Falta a trilha: {trilha}")
        r = SA.mixar_auto(camadas, cam, extra.get("trans", ()), trilha, FIM, PROJ / "som", inicio=TRILHA_INI,
                          licenca=TRILHA_LICENCA)
        (PROJ / "entrega").mkdir(exist_ok=True)
        print("mix", r["master"], "final", S.juntar(previa / "sem_som.mp4", PROJ / "som" / "mix.wav",
                                                    PROJ / "entrega" / f"{NOME}.mp4"))
    print("ok")


if __name__ == "__main__":
    main()
