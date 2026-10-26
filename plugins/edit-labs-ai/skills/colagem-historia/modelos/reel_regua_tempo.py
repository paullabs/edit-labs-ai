"""Modelo de reel de curiosidade histórica: "a régua do tempo" (exemplo: Cleópatra viveu mais perto da chegada à Lua
do que da construção das pirâmides).

≈ 19,5 s, 9:16 (1080×1920), sem voz, colagem de papel antigo, uma mecânica só. Uma linha do tempo vertical EM ESCALA
(PX_ANO px do mundo por ano): a caneta vermelha mede a distância entre dois marcos, um contador de anos corre junto
com a ponta, e o carimbo com a resposta cai NA BATIDA da trilha (sem voz, a batida é o relógio do vídeo).
Copie para PROJETO/ferramentas/reel.py e troque só o bloco "1. O QUE TROCAR". As fotos vêm de PROJETO/pecas/; sem
pecas/, o modelo usa as fotos de exemplo da release (pacote colagem-historia-fotos, em
$EDITLABS_DATA/colagem/assets/historia/cleopatra), se estiverem baixadas.

    clpy ferramentas/reel.py --folha            -> previa/folha_pecas.jpg (todas as peças sobre azul)
    clpy ferramentas/reel.py --batidas          -> os golpes da trilha (s e quadro) e o período sugerido para BATIDA
    clpy ferramentas/reel.py --quadros 10,200   -> previa/quadros/qNNNN.png
    clpy ferramentas/reel.py --margens          -> objetos cortados ou fora da margem segura
    clpy ferramentas/reel.py --video            -> previa/sem_som.mp4
    clpy ferramentas/reel.py --som              -> som/mix.wav + entrega/<NOME>.mp4 (depois do --video)
    --sem-texto                                 -> sem legendas, etiquetas, contadores e carimbos (o texto entra por último)

Rode sempre com clpy, o Python do motor de colagem do plugin (se ele disser que falta: editlabs-setup --colagem).

Mundo de papel com a régua do tempo na coluna X_REGUA e os marcos na coluna X_OBJ, à direita dela.
Batidas: gancho no personagem → chicote até o marco antigo → a caneta mede antigo → personagem (contador; carimbo na
batida) → recuo → volta ao personagem → a caneta mede personagem → marco recente (contador; carimbo na batida) → recuo →
plano geral → a caneta circula o marco antigo. Tempos em quadros de 24 por segundo (sempre pares).
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
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


def _achar_pecas(exemplo):
    """PROJETO/pecas > as fotos de exemplo da release ($EDITLABS_ASSETS/historia/<exemplo>), se o projeto não tiver pecas/"""
    proprio = PROJ / "pecas"
    if proprio.is_dir():
        return proprio
    dados = Path(os.environ.get("EDITLABS_DATA", "~/.local/share/edit-labs-ai")).expanduser()
    ex = Path(os.environ.get("EDITLABS_ASSETS", str(dados / "colagem" / "assets"))).expanduser() / "historia" / exemplo
    if ex.is_dir():
        print(f"Sem pecas/ no projeto: usando as fotos de exemplo em {ex} (créditos no LEIA.md do pacote)")
        return ex
    return proprio


sys.path.insert(0, str(_achar_motor()))
import motor as M          # noqa: E402  camadas, câmera, boil, transições, render
import pecas as PC         # noqa: E402  cartão com fita, recorte com borda de tesoura, etiqueta, carimbo, legenda
import cena as C           # noqa: E402  cai, traço de caneta, contador, carimbo, câmera por planos
# som e som_auto só entram no --som e no --batidas

PROJ = _achar_projeto()
EXEMPLO = "cleopatra"                       # pasta das fotos de exemplo (pacote colagem-historia-fotos)
P = _achar_pecas(EXEMPLO)

# =====================================================================================================================
# 1. O QUE TROCAR
# =====================================================================================================================
NOME = "regua_tempo"                        # nome do arquivo final em entrega/
FIM = 468                                   # duração em quadros de 24 (468 = 19,5 s)

# a régua do tempo, em ESCALA: o comprimento na tela é a distância no tempo (a história é essa proporção)
PX_ANO = 0.8                                # px do mundo por ano
REGUA_ANOS = (-2700, 2100)                  # do topo ao pé da régua (anos negativos = a.C.)
MARCA_PEQ, MARCA_GRANDE = 100, 500          # traço curto a cada 100 anos; traço longo e número a cada 500

# trilha calma (você baixa e licencia; não vai junto com o projeto se a licença proibir redistribuir)
TRILHA = "trilha.mp3"                       # em pecas/ ou em $EDITLABS_DATA/colagem/trilhas/
TRILHA_INI = 0.0                            # segundo da trilha onde começa o trecho usado
TRILHA_LICENCA = "trilha: veja CREDITOS.md do projeto"
# a batida da trilha (meça com --batidas): os carimbos e os pousos dos marcos caem nela. None = não encaixa.
BATIDA = 0.510                              # segundos entre uma batida e a próxima
BATIDA_INI = 0.015                          # segundo da 1ª batida, contado de TRILHA_INI

# arquivos em PROJETO/pecas/ (PNG = recorte com alfa; JPG = foto que vira cartão)
ARQ = {
    "antigo": "antigo.jpg",                 # o marco mais antigo (a pirâmide, foto de 1865)
    "pessoa": "pessoa.png",                 # recorte do personagem do gancho (o busto de Cleópatra)
    "recente": "recente.jpg",               # o marco mais recente (o astronauta na Lua, 1969)
    "selo": "selo.png",                     # OPCIONAL: recorte que cai junto do marco recente (o emblema da missão)
}
OPCIONAIS = {"selo"}

# os anos de cada ponto (negativo = a.C.). A caneta mede MEDE[0] e depois MEDE[1].
ANOS = {"antigo": -2560, "pessoa_ini": -69, "pessoa_fim": -30, "recente": 1969}
MEDE = [("antigo", "pessoa_ini"), ("pessoa_fim", "recente")]

# como cada foto vira cartão: (largura, altura, sépia) e o foco do corte em fração (0–1) da foto
CARTAO = {"antigo": (600, 430, True), "recente": (470, 560, False)}
FOCO = {"antigo": (0.62, 0.5), "recente": (0.5, 0.42)}
PESSOA_ALT, PESSOA_CORTE = 760, 0.94        # altura do recorte no mundo e onde cortar embaixo (fração; None = não corta)

# texto: pouco (a resposta é o carimbo); *palavra* sai em vermelho
LEGENDAS = [
    "Cleópatra viveu mais perto\nda *chegada à Lua* do que\nda construção das *pirâmides*.",
    "Quando ela nasceu, a\n*Grande Pirâmide* já tinha…",
    "E de Cleópatra até a\n*chegada à Lua*, em 1969:",
    "Para Cleópatra, as pirâmides\njá eram *antiguidade*.",
]
ETIQUETAS = {
    "antigo": ["GRANDE PIRÂMIDE", "c. 2560 a.C."],
    "pessoa": ["CLEÓPATRA", "69 – 30 a.C."],
    "recente": ["HOMEM NA LUA", "1969"],
}
CARIMBOS = ["≈ 2.500 ANOS", "≈ 2.000 ANOS"]  # a resposta de cada medida (arredonde: o contador mostra o número exato)
CONTA = "+{} anos"                          # o texto do contador


def anos_entre(a, b):
    """anos de a até b; não existe ano zero (de 30 a.C. a 1969 são 1.998 anos)"""
    return abs(b - a) - (1 if min(a, b) < 0 < max(a, b) else 0)


# tempos (quadros de 24, sempre pares). Os carimbos e os pousos dos marcos são puxados para a batida mais perto.
T = dict(whip=(92, 112), cai_antigo=104, et_antigo=116, caneta1=(136, 176), carimbo1=196,
         leg2=240, vai_pessoa=(240, 258), caneta2=(262, 304), cai_recente=288, cai_selo=300, et_recente=308,
         carimbo2=330, final=(366, 390), leg4=376, circulo=(392, 410))

# região segura da tela (REGRAS.md): x 80–960, y 260–1420; o assunto fica acima da legenda (y 1320)
REGIAO = (80, 260, 960, 1190)
Y_CONTADOR = 1100                           # o contador na tela, logo acima da legenda (dentro da margem segura)
# =====================================================================================================================

X_REGUA, X_OBJ = 1150, 1640                 # coluna da régua (onde corre a caneta) e coluna dos marcos
Y_TOPO = 420                                # y do mundo do 1º ano da régua
MUNDO = (3000, int(Y_TOPO + PX_ANO * (REGUA_ANOS[1] - REGUA_ANOS[0]) + 700))
CX = 1408                                   # x da câmera nos planos da régua (régua à esquerda, marcos à direita)
Z_SEGUE = 0.84                              # zoom enquanto a câmera segue a ponta da caneta
TELA_PONTA = 600                            # y da tela onde a ponta da caneta fica parada

TEXTO_FINAL = ("LEG", "c_", "RAJ_", "CONT", "ET_")   # camadas de texto que entram por último (--sem-texto)


def y_ano(ano):
    return Y_TOPO + PX_ANO * (ano - REGUA_ANOS[0])


def na_batida(q):
    """o quadro (24 qps, par) da batida da trilha mais perto de q"""
    if not BATIDA:
        return q
    n = round((q / M.FPS - BATIDA_INI) / BATIDA)
    return int(round((BATIDA_INI + n * BATIDA) * M.FPS / 2) * 2)


def tempos():
    """T com os carimbos e os pousos na batida, e os recuos de câmera terminando antes do carimbo"""
    t = dict(T)
    t["carimbo1"], t["carimbo2"] = na_batida(T["carimbo1"]), na_batida(T["carimbo2"])
    t["cai_antigo"] = na_batida(T["cai_antigo"] + 6) - 6                # o objeto encosta no papel na batida
    t["cai_recente"] = na_batida(T["cai_recente"] + 6) - 6
    t["recua1"] = (t["caneta1"][1], t["carimbo1"] - 2)
    t["recua2"] = (t["caneta2"][1] + 0, t["carimbo2"] - 4)
    return t


def tem(chave):
    return (P / ARQ[chave]).exists()


def conferir_pecas():
    falta = [f"pecas/{v}" for k, v in ARQ.items() if not (P / v).exists() and k not in OPCIONAIS]
    for k in sorted(OPCIONAIS):
        if not tem(k):
            print(f"aviso: sem pecas/{ARQ[k]} ({k}): a cena sai sem essa peça")
    if falta:
        sys.exit("Faltam peças em " + str(P) + ":\n  " + "\n  ".join(falta) + "\nVeja modelos/LEIA.md.")


def regua():
    """tira de papel com a escala do tempo: traço a cada MARCA_PEQ anos, número a cada MARCA_GRANDE, presa por fitas.
    Devolve (imagem, canto do mundo onde ela fica)"""
    a0, a1 = REGUA_ANOS
    alto = round(PX_ANO * (a1 - a0))
    larg_tira, W = 86, 520
    ox = W - 140 - larg_tira
    im = Image.new("RGBA", (W, alto + 120), (0, 0, 0, 0))
    tira = PC.rasgar(PC.textura_papel(larg_tira, alto, (236, 226, 200), 11), amp=3, passo=30, semente=11)
    im.alpha_composite(tira, (ox, 60))
    d = ImageDraw.Draw(im)
    fo = PC.fonte("IBMPlexMono-Medium.ttf", 44)
    tinta = PC.TINTA + (255,)
    for ano in range(a0 - a0 % MARCA_PEQ, a1 + 1, MARCA_PEQ):
        if ano < a0:
            continue
        y = 60 + round(PX_ANO * (ano - a0))
        grande = ano % MARCA_GRANDE == 0
        d.line([(ox, y), (ox + (46 if grande else 22), y)], fill=tinta, width=4 if grande else 2)
        if not grande:
            continue
        if ano == 0 and a0 < 0:
            for txt, dy in (("a.C.", -54), ("d.C.", 6)):
                d.text((ox - 18 - fo.getlength(txt), y + dy), txt, font=fo, fill=tinta)
            continue
        txt = f"{-ano} a.C." if ano < 0 else f"{ano}"
        d.text((ox - 18 - fo.getlength(txt), y - 28), txt, font=fo, fill=tinta)
    for k, ano in enumerate(np.linspace(a0 + 0.04 * (a1 - a0), a1 - 0.04 * (a1 - a0), 4)):
        f = PC.fita(120, 40, 4 if k % 2 else -5, k)
        im.alpha_composite(f, (ox + larg_tira // 2 - f.width // 2, 60 + round(PX_ANO * (ano - a0)) - f.height // 2))
    return im, (X_REGUA - ox - larg_tira // 2, round(y_ano(a0)) - 60)


def pecas():
    conferir_pecas()
    p = {}
    p["regua"], p["regua_canto"] = regua()
    for k in ("antigo", "recente"):
        w, h, sep = CARTAO[k]
        p[k] = PC.cartao(Image.open(P / ARQ[k]), w, h, foco=FOCO[k], sepia=sep, semente=21 if k == "antigo" else 31,
                         fitas=((0.18, -14), (0.84, 11)) if k == "antigo" else ((0.5, 6),))
    p["pessoa"] = PC.recorte(P / ARQ["pessoa"], alt=PESSOA_ALT, corte_base=PESSOA_CORTE, semente=9)
    p["selo"] = PC.recorte(P / ARQ["selo"], larg=330, borda=9, semente=13) if tem("selo") else None
    for i, k in enumerate(("antigo", "pessoa", "recente")):
        p["et_" + k] = PC.etiqueta(ETIQUETAS[k], semente=41 + i)
    for i, t in enumerate(CARIMBOS):
        p[f"c_{i + 1}"] = PC.carimbo(t, corpo=128, semente=51 + i)
    for i, t in enumerate(LEGENDAS):
        p[f"leg{i}"] = PC.legenda(t, semente=60 + i)
    return p


def fmt_anos(total):
    def f(v):
        n = total if v >= total else int(round(v / 10.0) * 10)         # corre de 10 em 10 e para no número exato
        return CONTA.format(f"{n:,}".replace(",", "."))
    return f


def montar(p):
    t = tempos()
    c = []
    et = dict(sombra=(4, 8, 0.2), boil="paper")
    YP = y_ano(ANOS["antigo"])
    YN, YM = y_ano(ANOS["pessoa_ini"]), y_ano(ANOS["pessoa_fim"])
    YL = y_ano(ANOS["recente"])
    XO = X_OBJ
    XB, YB = X_OBJ + 50, (YN + YM) / 2 + 8
    # ---- a régua do tempo, presa no papel
    c.append(C.fixo("REGUA", p["regua"], *p["regua_canto"], ancora=(0, 0), sombra=(4, 10, 0.18), boil="paper"))
    # ---- a caneta mede as duas distâncias (por baixo dos objetos)
    medidas = []
    for i, (a, b) in enumerate(MEDE):
        q0, q1 = t[f"caneta{i + 1}"]
        tr = C.Traco(f"MARCA{i + 1}", [(X_REGUA, y_ano(ANOS[a])), (X_REGUA, y_ano(ANOS[b]))], q0, q1, espessura=30,
                     op=0.8, tremor=3.0, semente=5 + i)
        medidas.append(tr)
        c.append(tr.camada)
    # ---- os marcos da linha do tempo. As etiquetas só vivem nos planos de perto: no recuo e no plano geral ficariam
    # pequenas demais para ler (e o ajustar_texto as incharia); ali quem fala é o carimbo.
    c.append(C.cai("ANTIGO", p["antigo"], t["cai_antigo"], XO, YP, rot=2.0, de_y=-200, sombra=(10, 22, 0.28)))
    c.append(C.cai("ET_ANTIGO", p["et_antigo"], t["et_antigo"], XO - 10, YP + p["antigo"].height / 2 + 55, rot=-2.0,
                   fim=t["recua1"][0], **et))
    c.append(C.cai("PESSOA", p["pessoa"], -2, XB, YB, de_y=-220, sombra=(14, 26, 0.32)))
    c.append(C.cai("ET_PESSOA", p["et_pessoa"], 14, XB - 180, YB - 340, rot=-3.0, fim=t["whip"][0], **et))
    c.append(C.cai("ET_PESSOA2", p["et_pessoa"], t["vai_pessoa"][1] - 4, XB - 180, YB - 340, rot=2.0,
                   fim=t["caneta2"][0] + 6, **et))
    c.append(C.cai("RECENTE", p["recente"], t["cai_recente"], XO, YL, rot=-3.0, de_y=-260, sombra=(10, 22, 0.28)))
    if p["selo"] is not None:
        c.append(C.cai("SELO", p["selo"], t["cai_selo"], XO + 230, YL - p["recente"].height / 2 + 55, rot=8.0,
                       de_y=-160, sombra=(8, 16, 0.3)))
    c.append(C.cai("ET_RECENTE", p["et_recente"], t["et_recente"], XO, YL + p["recente"].height / 2 + 45, rot=2.0,
                   fim=t["recua2"][0] + 8, **et))
    aw, ah = p["antigo"].size
    c.append(C.circulo("CIRC_ANTIGO", XO, YP - 10, aw * 0.65, ah * 0.68, *t["circulo"]))
    # ---- carimbos: a resposta de cada medida, na batida, com a explosão de traços
    for i, (a, b) in enumerate(MEDE):
        ya, yb = y_ano(ANOS[a]), y_ano(ANOS[b])
        y = ya + (0.4 if i == 0 else 0.32) * (yb - ya)
        q = t[f"carimbo{i + 1}"]
        c.append(C.carimbo(f"c_{i + 1}", p[f"c_{i + 1}"], q, 1730, y, -5.0 if i == 0 else 4.0))
        c.append(C.rajada(f"RAJ_{i + 1}", 1730, y, q, raio=560))
    # ---- legendas (tiras de papel em y 1320) e o contador de anos logo acima, enquanto a caneta corre
    sai1, sai2 = t["recua1"][0] + 10, t["recua2"][0] + 10          # saem no meio do recuo (não cobrem os objetos)
    c.append(C.legenda("LEG0", p["leg0"], -2, t["whip"][0], rot=1.0))
    c.append(C.legenda("LEG1", p["leg1"], 98, sai1, rot=-1.2))
    c.append(C.legenda("LEG2", p["leg2"], t["leg2"], sai2, rot=1.0))
    c.append(C.legenda("LEG3", p["leg3"], t["leg4"], FIM, rot=-1.2))
    for i, (a, b) in enumerate(MEDE):
        q0, q1 = t[f"caneta{i + 1}"]
        total = anos_entre(ANOS[a], ANOS[b])
        c.append(C.contador(f"CONT{i + 1}", q0, q1, (sai1, sai2)[i], total, fmt_anos(total), y=Y_CONTADOR,
                            largura_ref=CONTA.format("0.000")))
    c.append(C.vinheta(FIM))
    # ---- câmera: um plano por batida; nas medidas, a ponta da caneta fica parada em y TELA_PONTA
    segue = (M.H / 2 - TELA_PONTA) / Z_SEGUE

    def em(ano_y):
        return (Z_SEGUE, CX, ano_y + segue)

    def recuo(ya, yb):
        return (min(0.5, 1500 / (yb - ya + 900)), CX, (ya + yb) / 2 + 50)
    gancho = C.quadro((XB - 420, YB - 400, XB + 420, YB + 400), regiao=REGIAO)
    gancho_fim = (gancho[0] * 1.04,) + gancho[1:]
    final = (min(0.5, M.H / (YL - YP + 1400)), CX + 52, (YP + YL) / 2 + 200)
    (c1a, c1b), (c2a, c2b) = t["caneta1"], t["caneta2"]
    w1a, w1b = t["whip"]
    cam = (C.Camera()
           .plano(0, gancho, "lin").plano(w1a, gancho_fim, "io").plano(w1b, em(YP), "segura")
           .plano(c1a, em(YP), "io").plano(c1b, em(YN), "io")                    # segue a ponta da caneta
           .plano(t["recua1"][0], em(YN), "io").plano(t["recua1"][1], recuo(YP, YN), "segura")
           .plano(t["vai_pessoa"][0], recuo(YP, YN), "io").plano(t["vai_pessoa"][1], em(YM), "segura")
           .plano(c2a, em(YM), "io").plano(c2b, em(YL), "io")
           .plano(t["recua2"][0], em(YL), "io").plano(t["recua2"][1], recuo(YM, YL), "segura")
           .plano(t["final"][0], recuo(YM, YL), "io").plano(t["final"][1], final, "segura")
           .montar())
    return c, cam, {"trans": [], "medidas": medidas, "tempos": t}


def achar_trilha():
    trilha = P / TRILHA
    if not trilha.exists():                       # a pasta de trilhas do motor ($EDITLABS_DATA/colagem/trilhas)
        import recursos
        trilha = Path(getattr(recursos, "TRILHAS", P)) / TRILHA
    if not trilha.exists():
        sys.exit(f"Falta a trilha: {trilha}")
    return trilha


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--folha", action="store_true", help="folha com todas as peças sobre azul")
    ap.add_argument("--batidas", action="store_true", help="golpes da trilha e o período sugerido para BATIDA")
    ap.add_argument("--quadros", help="quadros (relógio de 24) separados por vírgula, ex.: 10,200,330")
    ap.add_argument("--margens", action="store_true", help="lista objetos cortados ou fora da margem segura")
    ap.add_argument("--video", action="store_true", help="previa/sem_som.mp4")
    ap.add_argument("--som", action="store_true", help="som/mix.wav e entrega/<NOME>.mp4 (depois do --video)")
    ap.add_argument("--sem-texto", action="store_true",
                    help="sem legendas, etiquetas, contadores e carimbos (o texto entra por último)")
    a = ap.parse_args()
    if a.batidas:
        import som as S
        golpes = S.acentos(achar_trilha(), dur=FIM / M.FPS + 1, inicio=TRILHA_INI)
        for s, salto in golpes:
            print(f"golpe {s:6.2f} s  quadro {round(s * M.FPS):4d}  (+{salto} dB)")
        if len(golpes) > 2:
            dif = np.diff([s for s, _ in golpes])
            per = float(np.median(dif[dif > 0.2])) if (dif > 0.2).any() else float(np.median(dif))
            print(f"período sugerido: BATIDA = {per:.3f}, BATIDA_INI = {golpes[0][0]:.3f} (confira de ouvido)")
        return
    p = pecas()
    previa = PROJ / "previa"
    previa.mkdir(exist_ok=True)
    if a.folha:
        PC.folha(sorted((k, v) for k, v in p.items() if isinstance(v, Image.Image)), previa / "folha_pecas.jpg")
    camadas, cam, extra = montar(p)
    print("carimbos na batida, quadros:", extra["tempos"]["carimbo1"], extra["tempos"]["carimbo2"])
    if a.sem_texto:
        camadas = [L for L in camadas if not L.nome.startswith(TEXTO_FINAL)]
    for aj in M.ajustar_texto(camadas, cam, FIM, extra.get("trans", ())):
        print("texto aumentado:", aj)
    if a.margens:
        for achado in M.checar_margens(camadas, cam, range(0, FIM, 12), regiao=(80, 260, 960, 1420)):
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
        r = SA.mixar_auto(camadas, cam, extra.get("trans", ()), achar_trilha(), FIM, PROJ / "som", inicio=TRILHA_INI,
                          licenca=TRILHA_LICENCA)
        (PROJ / "entrega").mkdir(exist_ok=True)
        print("mix", r["master"], "final", S.juntar(previa / "sem_som.mp4", PROJ / "som" / "mix.wav",
                                                    PROJ / "entrega" / f"{NOME}.mp4"))
    print("ok")


if __name__ == "__main__":
    main()
