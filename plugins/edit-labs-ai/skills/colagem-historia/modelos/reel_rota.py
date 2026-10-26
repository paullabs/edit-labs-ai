"""Modelo enxuto de reel de curiosidade histórica: "a viagem que mudou a história" (rota num mapa antigo).

≈ 22 s, 9:16 (1080×1920), sem voz, colagem de papel antigo. É o esqueleto dos reels de rota (Santos-Dumont e o
relógio, Dom Pedro e o telefone, a Mona Lisa até Florença). Copie para PROJETO/ferramentas/reel.py e troque só o bloco
"1. O QUE TROCAR". As fotos vêm de PROJETO/pecas/ (veja modelos/LEIA.md da skill).

    clpy ferramentas/reel.py --folha | --quadros 10,120 | --margens | --video | --som  [--sem-texto]

Mundo de papel 9000×3200, quatro áreas lado a lado (separadas na horizontal: o zoom aberto não mostra a vizinha):
  A  abertura: a foto de época, a pessoa entra deslizando, o carimbo da data; a foto VIRA o documento.
  B  o mapa: a caneta traça a rota, o veículo viaja na ponta e a câmera segue a ponta.
  C  o momento dramático no papel carvão: a foto do lugar, o carimbo, os objetos que se MULTIPLICAM.
  D  o fecho: a foto final e a resposta em letras que se montam; o carimbo no lugar da legenda.
Transições: íris (A→B), mergulho (B→C), rasgo (C→D). Tempos em quadros de 24.
"""
import argparse
import os
import sys
from pathlib import Path

from PIL import Image

AQUI = Path(__file__).resolve().parent


def _achar_motor():
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
    if os.environ.get("REEL_PROJETO"):
        return Path(os.environ["REEL_PROJETO"]).resolve()
    return AQUI.parent if AQUI.name == "ferramentas" else Path.cwd().resolve()


sys.path.insert(0, str(_achar_motor()))
import motor as M          # noqa: E402
import pecas as PC         # noqa: E402
import cena as C           # noqa: E402

PROJ = _achar_projeto()
P = PROJ / "pecas"

# =====================================================================================================================
# 1. O QUE TROCAR
# =====================================================================================================================
NOME = "reel_rota"
FIM = 528                                   # 22 s
MUNDO = (9000, 3200)
TRILHA, TRILHA_INI = "trilha.mp3", 0.0      # em pecas/; meça o trecho calmo antes
TRILHA_LICENCA = "trilha: veja CREDITOS.md do projeto"

ARQ = {
    "pessoa": "pessoa.png",                 # recorte (PNG com alfa) da pessoa, meio corpo ou corpo inteiro
    "retrato": "retrato.jpg",               # foto de época que abre o vídeo
    "documento": "documento.jpg",           # o documento em que a foto vira (jornal, carta, patente)
    "mapa": "mapa.jpg",                     # mapa ANTIGO da região da viagem
    "veiculo": "veiculo.png",               # recorte do veículo que viaja na ponta da caneta (navio, trem, dirigível)
    "lugar": "lugar.jpg",                   # foto do momento dramático
    "objeto": "objeto.png",                 # recorte do objeto que se multiplica ("todo mundo quis um")
    "fecho": "fecho.jpg",                   # foto do fecho
}
ROSTO = (0.5, 0.12)                         # onde fica o rosto no recorte da pessoa (fração): a íris sai dali
ROTA = [(0.78, 0.80), (0.70, 0.62), (0.52, 0.50), (0.34, 0.40), (0.22, 0.24)]   # pontos no mapa (fração da foto)
RESPOSTA = "1877"                           # letras que se montam no fecho

LEGENDAS = [                                # ≈ 40 palavras no total; *palavra* sai em vermelho
    "Quase ninguém *ligava*\npro telefone.",
    "Até chegar um\n*imperador brasileiro*.",
    "Ele *atravessou* o oceano\npara ver.",
    "Domingo. Os jurados\niam *embora*.",
    "Depois, *todo mundo*\nquis um.",
]
TEMPOS_LEG = [(-2, 66), (70, 112), (150, 290), (322, 360), (372, 420)]
ETIQUETAS = {"pessoa": ["DOM PEDRO II", "imperador do Brasil"], "inicio": ["RIO"], "fim": ["FILADÉLFIA"]}
CARIMBOS = {"data": "1876", "drama": "25 JUN 1876 · DOMINGO", "fecho": "NO PALÁCIO"}

REGIAO = (80, 260, 960, 1190)               # região segura (REGRAS.md); a legenda fica em y 1320
REGIAO_SEM_LEG = (80, 260, 960, 1420)
# =====================================================================================================================

AX, BX, CX, DX = 1100, 3500, 5900, 8000     # centros das áreas
Y0 = 1500


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


def pecas():
    conferir_pecas()
    p = {}
    abrir = lambda k: Image.open(P / ARQ[k])                                      # noqa: E731
    p["pessoa"] = PC.recorte(P / ARQ["pessoa"], alt=1300, semente=11)
    p["retrato"] = PC.cartao(abrir("retrato"), 900, semente=21, fitas=((0.2, -10), (0.8, 8)))
    p["documento"] = PC.cartao(abrir("documento"), 900, semente=22, envelhece=False)
    p["mapa_px"] = abrir("mapa").size
    p["mapa"] = PC.cartao(abrir("mapa"), 1800, semente=23, envelhece=False, fitas=((0.1, -12), (0.9, 10)))
    p["veiculo"] = PC.recorte(P / ARQ["veiculo"], larg=380, semente=24, borda=6, sepia=True)
    p["lugar"] = PC.cartao(abrir("lugar"), 1000, semente=25, sepia=True)
    p["objeto"] = PC.recorte(P / ARQ["objeto"], alt=300, semente=26, borda=6)
    p["fecho"] = PC.cartao(abrir("fecho"), 1000, semente=27, fitas=((0.3, -8), (0.7, 9)))
    p["et_pessoa"] = PC.etiqueta(ETIQUETAS["pessoa"], semente=31)
    p["et_inicio"] = PC.etiqueta(ETIQUETAS["inicio"], corpo=(40,), fontes=("ArchivoBlack-Regular.ttf",), semente=32)
    p["et_fim"] = PC.etiqueta(ETIQUETAS["fim"], corpo=(40,), fontes=("ArchivoBlack-Regular.ttf",), semente=33)
    for k, t in CARIMBOS.items():
        p["c_" + k] = PC.carimbo(t, semente=40 + len(t))
    for i, t in enumerate(LEGENDAS):
        p[f"leg{i}"] = PC.legenda(t, semente=60 + i)
    return p


def Q(caixa, regiao=REGIAO):
    return C.quadro(caixa, regiao=regiao)


def montar(p):
    c = []
    et = dict(sombra=(4, 8, 0.2), boil="paper")
    # ---- A: abertura (objeto real primeiro, o texto confirma depois)
    RX_, RY_ = AX - 180, Y0 - 420
    c.append(C.fixo("GRADE_A", PC.grade(1500, 1700, passo=70), AX, Y0, boil=None, sombra=None))
    c += C.vira("RET", p["retrato"], p["documento"], 70, RX_, RY_, rot=-2, ini=-6)        # a foto vira o documento
    PX_, PY_ = AX + 260, Y0 + 260
    c.append(C.desliza("PESSOA", p["pessoa"], 8, (PX_ + 1400, PY_), (PX_, PY_), dur=12, sombra=(16, 28, 0.32)))
    c.append(C.cai("ET_PESSOA", p["et_pessoa"], 26, PX_ - 80, PY_ + 520, rot=-3, **et))
    c.append(C.carimbo("c_data", p["c_data"], 44, RX_ + 120, RY_ + 330, -6, esc=0.7))
    c.append(C.rajada("RAJ_DATA", RX_ + 120, RY_ + 330, 44, raio=320, cor=PC.VERMELHO))
    pw, ph = p["pessoa"].size
    rosto = (PX_ - pw / 2 + ROSTO[0] * pw, PY_ - ph / 2 + ROSTO[1] * ph)
    # ---- B: o mapa, a rota e o veículo na ponta da caneta
    c.append(C.fixo("MAPA", p["mapa"], BX, Y0, rot=0.8, sombra=(8, 20, 0.22), boil="paper"))
    rota = [em_cartao((BX, Y0), p["mapa"], 1800, p["mapa_px"], r) for r in ROTA]
    viagem = C.Traco("ROTA", rota, 146, 226, espessura=18, suave=True, seta=True, tam_seta=34)
    c.append(viagem.camada)
    c.append(C.segue("VEICULO", p["veiculo"], viagem, 146, 226, desloc=(0, -70), vira_lado=True, fim=300))
    ini, fim_ = rota[0], rota[-1]
    c.append(C.circulo("PT_INICIO", ini[0], ini[1], 28, 28, 130, 138, espessura=16))
    c.append(C.cai("ET_INICIO", p["et_inicio"], 132, ini[0] - 170, ini[1] + 80, rot=-3, **et))
    c.append(C.cai("ET_FIM", p["et_fim"], 228, fim_[0] + 40, fim_[1] - 110, rot=3, **et))
    c.append(C.circulo("PT_FIM", fim_[0], fim_[1], 40, 40, 226, 236, espessura=16))
    # ---- C: o momento dramático no papel carvão
    c.append(C.papel_area("PAPEL_C", (CX - 900, Y0 - 1000, CX + 900, Y0 + 1100)))
    c.append(C.fixo("LUGAR", p["lugar"], CX, Y0 - 250, rot=-2))
    c.append(C.carimbo("c_drama", p["c_drama"], 332, CX, Y0 + 180, -5, esc=0.5))
    c.append(C.rajada("RAJ_DRAMA", CX, Y0 + 180, 332, raio=420))
    c += C.multiplica("OBJS", p["objeto"], 372, (CX, Y0 + 520), n=7, raio=(560, 260), passo=3, esc=(0.8, 1.05),
                      semente=17, sombra=(8, 14, 0.3), boil="obj")
    # ---- D: o fecho
    c.append(C.cai("FECHO", p["fecho"], 440, DX, Y0 - 100, rot=2, de_y=-200))
    c += C.letras("RESP", RESPOSTA, 456, 540, 420, corpo=170, cor=PC.VERMELHO, passo=2)
    c.append(C.carimbo("c_fecho", p["c_fecho"], 484, 540, 1320, -4, esc=0.72, mundo=False))
    # ---- legendas (sempre em y 1320)
    for i, (a, b) in enumerate(TEMPOS_LEG[:len(LEGENDAS)]):
        c.append(C.legenda(f"LEG{i}", p[f"leg{i}"], a, b, rot=1.0 if i % 2 else -1.2))
    c.append(C.vinheta(FIM))
    # ---- câmera
    A1 = Q((AX - 760, Y0 - 1000, AX + 760, Y0 + 900))
    A2 = Q((RX_ - 480, RY_ - 380, PX_ + 520, PY_ + 640))           # aproxima sem cortar o documento
    mw, mh = p["mapa"].size
    B1 = Q((BX - mw / 2, Y0 - mh / 2, BX + mw / 2, Y0 + mh / 2))
    C1 = Q((CX - 620, Y0 - 760, CX + 620, Y0 + 800))
    D1 = Q((DX - 620, Y0 - 520, DX + 620, Y0 + 420), (80, 520, 960, 1190))     # o alto fica para a resposta

    def deriva(z, f=1.03):
        return (z[0] * f,) + z[1:]
    cam = (C.Camera()
           .plano(0, A1, "lin").plano(60, deriva(A1, 1.04), "io")
           .plano(76, A2, "lin").plano(104, deriva(A2), "segura")
           .plano(120, B1, "lin").plano(128, B1, "io")             # 18 quadros para chegar na ponta
           .seguir(viagem, 146, 226, B1[0] * 1.9, tela=(540, 700))        # a câmera segue a ponta da caneta
           .plano(244, B1, "io").plano(296, deriva(B1, 1.05), "segura")
           .plano(314, C1, "lin").plano(420, deriva(C1, 1.04), "segura")
           .plano(436, D1, "lin").plano(FIM, deriva(D1, 1.04), "segura")
           .montar())
    trans = [M.Transicao(104, 120, "iris", centro=M.na_tela(cam.matriz(104), rosto)),
             M.Transicao(296, 314, "mergulho", centro=M.na_tela(cam.matriz(296), fim_),
                         centro_b=M.na_tela(cam.matriz(314), (CX, Y0 - 250))),
             M.Transicao(420, 436, "rasgo", semente=11)]
    return c, cam, {"trans": trans, "rota": viagem}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--folha", action="store_true")
    ap.add_argument("--quadros")
    ap.add_argument("--margens", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--som", action="store_true")
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
        import som as S
        import som_auto as SA
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
