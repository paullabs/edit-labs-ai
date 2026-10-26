"""Homem de foto real: quadros-chave parados para aprovar o visual ANTES de animar (regra: revisão de espectador antes
de qualquer vídeo).

    clpy homem3_quadros.py     grava previa/homem3_quadros/*.png e uma folha"""
import os
import sys
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
import camadas as K, pecas as PC

H3 = AQUI / "homem3"
PECAS = H3 / "pecas"
VAN = H3 / "anat" / "vistas_anat"
PAP = H3 / "papel"
W, H = 1080, 1920
# o atlas na foto: a fúrcula do atlas cai no nó da gravata, a linha do meio inclina +3° como a do paletó e a escala vem
# da altura cabeça → fúrcula (31 cm no atlas, 1215 px na foto)
JUG_FOTO = (990.0, 1250.0)
ROT = 3.0
PXM_FOTO = 1215 / 0.31
# a janela rasgada no peito (px do recorte): segue o tronco, mais larga do lado que está virado para a câmera
JANELA = [(700, 1430), (930, 1390), (1180, 1420), (1420, 1470), (1600, 1600), (1660, 1900), (1650, 2350),
          (1600, 2750), (1450, 2990), (1150, 3070), (870, 3040), (650, 2930), (560, 2650), (540, 2200), (560, 1800),
          (610, 1560)]


def ajusta_foto(im):
    """a cópia do postal é desbotada: os níveis vão só na LUMINÂNCIA e o tom sépia volta suave por cima. Esticar os três
    canais deixava a foto amarelo-laranja, com cara de colorização falsa"""
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3] / 255
    m = a[..., 3] > 128
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    lo, hi = np.percentile(lum[m], 1.0), np.percentile(lum[m], 99.5)
    l2 = np.clip((lum - lo) / (hi - lo), 0, 1)
    l2 = np.clip(0.5 + (l2 - 0.5) * 1.08, 0, 1)
    tom = np.array([1.0, 0.93, 0.80], np.float32)                     # sépia leve (papel fotográfico antigo)
    out = (l2[..., None] * (0.82 + 0.18 * tom)) * 0.97 + 0.015
    a[..., :3] = np.clip(out, 0, 1) * 255
    return Image.fromarray(a.astype(np.uint8))


def matriz_atlas():
    d = json.load(open(VAN / "vistas.json"))
    s = PXM_FOTO / d["px_por_m"]
    r = math.radians(ROT)
    R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]]) * s
    t = np.array(JUG_FOTO) - R @ np.array(d["marcos"]["jugular"])
    return np.hstack([R, t[:, None]])


def anat(nome, semente, tam):
    """camada do atlas em gravura de papel, já no px do recorte da foto"""
    PAP.mkdir(parents=True, exist_ok=True)
    out = PAP / f"anat_{nome}_{tam[0]}x{tam[1]}_{JUG_FOTO[0]:.0f}.png"     # o registro depende do tamanho e da margem
    if not out.exists():
        im = K.papelizar(VAN / nome / "cor_q_001.png", luz=VAN / nome / "luz_q_001.png", registrado=True,
                         semente=semente, cor=1.0, borda=10, contraste=1.6)
        A = matriz_atlas().copy()
        A[:, 2] -= A[:, :2] @ np.array([14.0, 14.0])          # a margem do papel (borda + 4) desloca o registro
        w = cv2.warpAffine(np.asarray(im), A, tam, flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        Image.fromarray(w).save(out)
    return Image.open(out).convert("RGBA")


def mascara_janela(tam, semente=7):
    """polígono com borda rasgada (ruído de baixa frequência na direção normal)"""
    pts = np.array(JANELA, np.float32)
    dens = []
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n = max(2, int(np.linalg.norm(b - a) / 6))
        for k in range(n):
            dens.append(a + (b - a) * k / n)
    dens = np.array(dens)
    rng = np.random.default_rng(semente)
    c = dens.mean(axis=0)
    ruido = np.convolve(rng.normal(0, 1, len(dens)), np.ones(9) / 9, mode="same") * 22 + rng.normal(0, 4, len(dens))
    dirs = dens - c
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    dens = dens + dirs * ruido[:, None]
    m = Image.new("L", tam, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in dens], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255


def janela_aberta(corpo, camadas_dentro, tam, limite=None):
    """o corpo com a janela rasgada: dentro, o fundo escuro + as camadas; na borda, a fibra branca do papel rasgado e a
    sombra da espessura do papel caindo sobre a anatomia. 'limite' (alfa do tronco do atlas): a janela nunca passa dele,
    senão abria um buraco preto entre o corpo do atlas e a borda (o paletó é mais largo que o corpo)"""
    jan = mascara_janela(tam)
    if limite is not None:
        jan = jan * (cv2.GaussianBlur(cv2.erode(limite, np.ones((61, 61), np.uint8)), (0, 0), 6) / 255)
    fibra = np.clip(cv2.dilate(jan, np.ones((13, 13), np.uint8)) - jan, 0, 1)        # a fibra fica do lado da foto
    dentro = Image.new("RGBA", tam, (0, 0, 0, 0))
    cav = PC.textura_papel(tam[0], tam[1], (26, 17, 16), 61).convert("RGBA")
    cav.putalpha(Image.fromarray((jan * 255).astype(np.uint8)))
    dentro.alpha_composite(cav)
    for L in camadas_dentro:
        a = np.asarray(L).copy()
        a[..., 3] = (a[..., 3].astype(np.float32) * jan).astype(np.uint8)
        dentro.alpha_composite(Image.fromarray(a))
    sombra = cv2.GaussianBlur(np.roll(1 - jan, (14, 10), axis=(0, 1)), (0, 0), 9) * jan
    d = np.asarray(dentro).astype(np.float32)
    d[..., :3] *= (1 - 0.55 * sombra[..., None])
    c = np.asarray(corpo).astype(np.float32)
    c[..., 3] *= (1 - jan)
    branco = np.array([244, 238, 222], np.float32)
    f = (fibra * (c[..., 3] / 255 > 0.5))[..., None] * 0.95
    c[..., :3] = c[..., :3] * (1 - f) + branco * f
    out = Image.fromarray(np.clip(d, 0, 255).astype(np.uint8))
    out.alpha_composite(Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)))
    return out


def gira_peca(img, piv, graus):
    """gira a peça em volta do pivô (horário na tela, como o motor)"""
    return img.rotate(-graus, center=piv, resample=Image.BICUBIC)


def figura(corpo, braco, antebraco, p, th_ombro=0.0, th_cotovelo=0.0):
    """braço por trás do corpo; antebraço por cima do braço; o cotovelo acompanha o giro do ombro"""
    tam = corpo.size
    ox, oy = p["ombro"]
    cx, cy = p["cotovelo"]
    r = math.radians(th_ombro)
    cot = (ox + (cx - ox) * math.cos(r) - (cy - oy) * math.sin(r), oy + (cx - ox) * math.sin(r) + (cy - oy) * math.cos(r))
    b = gira_peca(braco, p["ombro"], th_ombro)
    ab = gira_peca(antebraco, p["ombro"], th_ombro)
    ab = gira_peca(ab, cot, th_cotovelo)
    out = Image.new("RGBA", tam, (0, 0, 0, 0))
    out.alpha_composite(b)
    out.alpha_composite(corpo)
    out.alpha_composite(ab)
    return out


def com_borda(fig, borda=26, semente=3):
    """a borda branca de tesoura em volta da figura inteira (só por fora)"""
    a = np.asarray(fig.getchannel("A"))
    dil = cv2.dilate(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * borda + 1, 2 * borda + 1)))
    base = PC.textura_papel(fig.width, fig.height, (244, 238, 222), semente)
    base.putalpha(Image.fromarray(cv2.GaussianBlur(dil, (0, 0), 1.5)))
    base.alpha_composite(fig)
    return base


def na_tela(fig, caixa, legenda=None):
    """encaixa a caixa (px do recorte) na região segura da tela sobre papel creme, com sombra"""
    x0, y0, x1, y1 = caixa
    rx0, ry0, rx1, ry1 = 70, 210, 1010, 1190
    z = min((rx1 - rx0) / (x1 - x0), (ry1 - ry0) / (y1 - y0))
    peca = fig.crop((int(x0), int(y0), int(x1), int(y1)))
    peca = peca.resize((int(peca.width * z), int(peca.height * z)), Image.LANCZOS)
    tela = PC.papel_mundo(W, H).convert("RGBA")
    ox = int((rx0 + rx1) / 2 - peca.width / 2)
    oy = int((ry0 + ry1) / 2 - peca.height / 2)
    sombra = Image.new("RGBA", peca.size, (40, 30, 20, 0))
    sombra.putalpha(peca.getchannel("A").point(lambda v: int(v * 0.3)).filter(ImageFilter.GaussianBlur(10)))
    tela.alpha_composite(sombra, (ox + 8, oy + 16))
    tela.alpha_composite(peca, (ox, oy))
    if legenda:
        leg = PC.legenda(legenda, semente=60)
        tela.alpha_composite(leg, (int(W / 2 - leg.width / 2), int(1320 - leg.height / 2)))
    return tela.convert("RGB")


def main():
    p = json.load(open(PECAS / "pecas.json"))
    corpo = ajusta_foto(Image.open(PECAS / "corpo.png").convert("RGBA"))
    braco = ajusta_foto(Image.open(PECAS / "braco.png").convert("RGBA"))
    antebraco = ajusta_foto(Image.open(PECAS / "antebraco.png").convert("RGBA"))
    # margem em volta do recorte: o braço que levanta sai da caixa do recorte (o antebraço era cortado)
    M_ = 1400
    def margem(im):
        out = Image.new("RGBA", (im.width + 2 * M_, im.height + M_), (0, 0, 0, 0))
        out.alpha_composite(im, (2 * M_ - M_, M_))
        return out
    corpo, braco, antebraco = margem(corpo), margem(braco), margem(antebraco)
    p = dict(p, ombro=(p["ombro"][0] + M_, p["ombro"][1] + M_), cotovelo=(p["cotovelo"][0] + M_, p["cotovelo"][1] + M_))
    global JUG_FOTO, JANELA
    JUG_FOTO = (JUG_FOTO[0] + M_, JUG_FOTO[1] + M_)
    JANELA = [(x + M_, y + M_) for x, y in JANELA]
    tam = corpo.size
    saida = AQUI / "previa" / "homem3_quadros"
    saida.mkdir(parents=True, exist_ok=True)
    inteiro = (M_ - 80, M_ - 60, M_ + 2232 + 80, M_ + 5300)
    tronco = (M_ - 150, M_ - 60, M_ + 2350, M_ + 3250)          # com a cabeça: nunca um tronco sem cabeça
    q = {}
    q["1_parado"] = na_tela(com_borda(figura(corpo, braco, antebraco, p)), inteiro,
                            "Um homem comum, *saindo para o trabalho*.")
    q["2_tchau"] = na_tela(com_borda(figura(corpo, braco, antebraco, p, 35.0, 125.0)),
                           (M_ - 1100, M_ - 60, M_ + 2232 + 80, M_ + 5300),
                           "Um homem comum, *saindo para o trabalho*.")
    musc, cost, resto = anat("musc", 7, tam), anat("costelas", 9, tam), anat("osso_resto", 8, tam)
    org, pul, cor = anat("org", 4, tam), anat("pul", 5, tam), anat("cor", 6, tam)
    fig = figura(corpo, braco, antebraco, p)
    lim = np.asarray(musc.getchannel("A"))
    q["3_musculos"] = na_tela(com_borda(janela_aberta(fig, [resto, musc], tam, lim)), tronco,
                              "Por baixo do paletó: mais de *600 músculos*.")
    q["4_ossos"] = na_tela(com_borda(janela_aberta(fig, [resto, org, pul, cor, cost], tam, lim)), tronco,
                           "Segurando tudo de pé: *206 ossos*.")
    q["5_orgaos"] = na_tela(com_borda(janela_aberta(fig, [resto, org, pul, cor], tam, lim)), tronco,
                            "Os pulmões respiram *20 mil vezes por dia*.")
    for k, im in q.items():
        im.save(saida / f"{k}.png")
    folha = Image.new("RGB", (5 * 432, 768), "white")
    for i, k in enumerate(sorted(q)):
        folha.paste(q[k].resize((432, 768)), (i * 432, 0))
    folha.save(saida / "folha.jpg", quality=90)
    print("ok", saida)


if __name__ == "__main__":
    main()
