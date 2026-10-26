"""Poses do tchau geradas por IA de imagem (ex.: GPT Image no Higgsfield, com a própria foto como referência e o prompt
"mude SÓ o braço"), coladas sobre a FOTO original.

Por quê: girar o recorte do braço vira um palito em V, completar com a textura da foto deixa o braço fino e usar a mão
de outra fonte (o atlas) não combina com a pessoa. Gerar a parte que mexe a partir da própria foto resolve.

Regra de pessoa real: da imagem gerada só entram o braço, a manga e o ombro que mudaram. O rosto e o resto do corpo
continuam sendo os pixels da foto original (o rosto nunca é gerado).

1. registro: a imagem gerada é alinhada à entrada (SIFT + RANSAC, semelhança) só pelo rosto e pelo tronco;
2. tom: os quantis de luminância da gerada são casados com os da foto, na área do corpo que não mudou;
3. corte: entra da gerada a figura dela FORA do corpo original sem o braço (a manga levantada, o ombro, a lateral
   do paletó que o braço cobria); o corpo original sem o braço fica por cima, com a costura suavizada.

As poses prontas e as imagens geradas vêm no pacote colagem-homem3 da release (assets/homem3/poses e assets/homem3/ia);
este script só é preciso para refazer as poses ou fazer poses de OUTRA foto. O prompt e o passo a passo estão no
LEIA.md do pacote ("Poses novas para outra foto"). Entrada: <trabalho>/homem3/ia/ se existir, senão a do pacote.

    clpy homem3_poses_ia.py     grava <trabalho>/homem3/poses/{repouso,meio,alto}.png (px do recorte + margem) e uma
                                folha; as cenas passam a usar estas poses no lugar das do pacote"""
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import homem3_quadros as HQ

IA = CM.homem3("ia")                                                  # a sua (trabalho) ou a do pacote
SAIDA = AQUI / "homem3" / "poses"
# a entrada da IA: o recorte (0..2232, 0..4700) colado em (ML, MT) numa tela cinza e reduzido por K
ML, MT, K = 1300, 300, 2048 / 5000
# a tela das poses (px do recorte): margem à esquerda e em cima para o braço levantado
MARGEM = (1300, 300)
COSTURA = [(470, 1500), (475, 1700), (480, 2000), (490, 2600), (492, 3350), (400, 3420), (360, 3560), (350, 3660),
           (440, 3700), (470, 4300)]


def entrada_para_tela():
    """matriz 2x3: px da entrada da IA → px da tela das poses"""
    s = 1 / K
    return np.array([[s, 0, -ML + MARGEM[0]], [0, s, -MT + MARGEM[1]]], np.float64)


def registro(gerada, entrada, m_ger, m_ent, zona):
    """semelhança gerada → entrada, só com pontos do rosto e do tronco (zona = máscara na entrada)"""
    sift = cv2.SIFT_create(4000)
    g1 = cv2.cvtColor(np.asarray(gerada), cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(np.asarray(entrada), cv2.COLOR_RGB2GRAY)
    k1, d1 = sift.detectAndCompute(g1, (m_ger > 128).astype(np.uint8) * 255)
    k2, d2 = sift.detectAndCompute(g2, ((m_ent > 128) & zona).astype(np.uint8) * 255)
    pares = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    bons = [m for m, n in pares if m.distance < 0.7 * n.distance]
    p1 = np.float32([k1[m.queryIdx].pt for m in bons])
    p2 = np.float32([k2[m.trainIdx].pt for m in bons])
    A, inl = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    print(f"  registro: {int(inl.sum())}/{len(bons)} pontos; escala {np.hypot(A[0, 0], A[1, 0]):.4f}")
    return A


def compoe(A_ger_ent, gerada, m_ger, base, m_base, braco):
    """a pose: figura gerada (alinhada e no tom da foto) por baixo, o corpo original sem o braço por cima"""
    T = entrada_para_tela()
    A = (np.vstack([T, [0, 0, 1]]) @ np.vstack([A_ger_ent, [0, 0, 1]]))[:2]
    tam = base.size
    g = cv2.warpAffine(np.asarray(gerada), A, tam, flags=cv2.INTER_CUBIC, borderValue=(0, 0, 0))
    mg = cv2.warpAffine(m_ger, A, tam, flags=cv2.INTER_LINEAR, borderValue=0).astype(np.float32) / 255
    # da gerada só entra o lado do braço (à esquerda de x ≈ 700 do recorte, acima do quadril): o resto do corpo é
    # sempre a foto (um erro de registro de poucos px deixaria um contorno fantasma do corpo gerado)
    xx = np.arange(tam[0])[None, :].astype(np.float32)
    yy = np.arange(tam[1])[:, None].astype(np.float32)
    zona = np.clip((700 + MARGEM[0] - xx) / 60, 0, 1) * np.clip((4400 + MARGEM[1] - yy) / 60, 0, 1)
    mg_toda = mg
    mg = mg * zona
    b = np.asarray(base).astype(np.float32)
    ab = m_base.astype(np.float32) / 255
    corpo = ab * (1 - braco)                                             # o corpo original, sem o braço
    # tom: quantis de luminância da gerada → os da foto, no corpo INTEIRO que os dois mostram (rosto, camisa e mãos
    # incluídos: medido só no paletó, a pele clara da mão gerada era travada num cinza médio)
    comum = (ab > 0.9) & (mg_toda > 0.9)
    lg = g.astype(np.float32).mean(axis=2)
    lb = b[..., :3].mean(axis=2)
    qs = np.linspace(0.01, 0.99, 50)
    mapa_g, mapa_b = np.quantile(lg[comum], qs), np.quantile(lb[comum], qs)
    lg2 = np.interp(lg, mapa_g, mapa_b)
    g2 = g.astype(np.float32) * (lg2 / np.maximum(lg, 1))[..., None]
    tom = b[..., :3][comum].mean(axis=0) / np.maximum(b[..., :3][comum].mean(axis=0).mean(), 1)
    g2 = g2.mean(axis=2, keepdims=True) * tom                            # o mesmo tom sépia leve da foto
    out = np.zeros(b.shape, np.float32)
    out[..., :3] = g2
    out[..., 3] = mg * 255
    # o corpo original por cima, com a costura do braço suavizada (o braço gerado continua por baixo dela)
    corpo_s = cv2.GaussianBlur(corpo, (0, 0), 3) * (ab > 0.5)
    out[..., :3] = out[..., :3] * (1 - corpo_s[..., None]) + b[..., :3] * corpo_s[..., None]
    out[..., 3] = np.maximum(out[..., 3], corpo * 255)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    (AQUI / "previa" / "homem3_quadros").mkdir(parents=True, exist_ok=True)
    rec = HQ.ajusta_foto(Image.open(CM.homem3("recorte/foto3_recorte.png")).convert("RGBA"))
    tam = (rec.width + MARGEM[0], rec.height + MARGEM[1])
    base = Image.new("RGBA", tam, (0, 0, 0, 0))
    base.alpha_composite(rec, MARGEM)
    m_base = np.asarray(base.getchannel("A"))
    # o braço original (da costura para fora, abaixo do ombro), com a costura suave
    m = Image.new("L", tam, 0)
    ImageDraw.Draw(m).polygon([(x + MARGEM[0], y + MARGEM[1]) for x, y in [(-1300, 1350)] + COSTURA + [(-1300, 4400)]],
                              fill=255)
    braco = cv2.GaussianBlur(np.asarray(m).astype(np.float32) / 255, (0, 0), 4)
    base.save(SAIDA / "repouso.png")
    entrada = Image.open(IA / "entrada_braco.png").convert("RGB")
    m_ent = np.asarray(Image.open(IA / "entrada_mascara.png").convert("L"))
    # zona de registro na entrada: rosto e tronco (à direita da costura), sem o braço
    zona = np.zeros(m_ent.shape, bool)
    zx0 = int((ML + 560) * K)
    zona[:, zx0:] = True
    for nome, pasta in (("meio", "gerado_meio_1/meio_1"), ("alto", "gerado_aceno_1/aceno_1")):
        print(nome)
        g = Image.open(IA / f"{pasta}.png").convert("RGB")
        mg = np.asarray(Image.open(IA / f"{pasta}_mascara.png").convert("L"))
        A = registro(g, entrada, mg, m_ent, zona)
        compoe(A, g, mg, base, m_base, braco).save(SAIDA / f"{nome}.png")
    # folha para a revisão de espectador
    ims = []
    for nome in ("repouso", "meio", "alto"):
        fig = HQ.com_borda(Image.open(SAIDA / f"{nome}.png").convert("RGBA"), borda=26)
        ims.append(HQ.na_tela(fig, (0, 100, tam[0], 3700 + MARGEM[1])).resize((432, 768)))
    folha = Image.new("RGB", (432 * 3, 768), "white")
    for i, im in enumerate(ims):
        folha.paste(im, (i * 432, 0))
    folha.save(AQUI / "previa" / "homem3_quadros" / "poses_ia.jpg", quality=90)
    print("ok")


if __name__ == "__main__":
    main()
