"""Homem de foto real: a FOTO de arquivo recortada em peças de papel.

Foto: "Photographic postcard of an unidentified man in a suit", 1926–1940s, NMAAHC 2013.46.29.86 (Smithsonian Open
Access, CC0): https://nmaahc.si.edu/object/nmaahc_2013.46.29.86 (arquivo NMAAHC-2013_46_29_86_001.jpg; confira a
licença CC0 na página e baixe você mesmo).
O recorte pronto vem no pacote colagem-homem3 da release (assets/homem3/recorte/foto3_recorte.png). Para outra foto:
recorte com motor/colagem/recorte.swift (macOS) ou removendo o fundo no Higgsfield e salve o PNG com alfa em
<trabalho>/homem3/recorte/foto3_recorte.png (o seu vale mais que o do pacote).

Peças (no px do recorte, que é o da foto deslocado pela caixa do recorte):
- corpo: tudo menos o braço direito dele (à esquerda de quem olha); fica com o "boné" do ombro (disco em volta do
  pivô), que cobre o alto do braço quando ele gira;
- braco: a manga do ombro até o cotovelo, por TRÁS do corpo;
- antebraco: do cotovelo até a mão, por CIMA do braço, com o disco do cotovelo (gira sobre ele sem abrir fresta).

A costura entre a manga e o paletó (a faixa escura em x ≈ 470–490) é a linha que separa o braço do corpo.

    clpy homem3_pecas.py      grava homem3/pecas/{corpo,braco,antebraco}.png e pecas.json"""
import os
import sys
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
H3 = CM.TRABALHO / "homem3"

# a costura manga × paletó (de cima para baixo) e o contorno de baixo do braço, em px do recorte
COSTURA = [(470, 1500), (475, 1700), (480, 2000), (490, 2600), (492, 3350), (400, 3420), (360, 3560), (350, 3660),
           (440, 3700), (470, 4300)]
OMBRO = (420, 1690)            # pivô do ombro
R_OMBRO = 230                  # o "boné" do ombro (fica no corpo, por cima do braço)
COTOVELO = (330, 2700)         # pivô do cotovelo
R_COTOVELO = 165               # o disco do cotovelo (vai com o antebraço, por cima do braço)
EIXO = (np.array([300.0, 3600.0]) - np.array(OMBRO))   # direção do braço (ombro → punho)


def lado_braco(w, h):
    """máscara do lado do braço: à esquerda da costura e abaixo do alto do ombro"""
    poli = [(0, 1450)] + [(x, y) for x, y in COSTURA] + [(0, 4300)]
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).polygon(poli, fill=255)
    return np.asarray(m) > 0


def disco(w, h, c, r):
    yy, xx = np.mgrid[0:h, 0:w]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


def main():
    rec = np.asarray(Image.open(CM.homem3("recorte/foto3_recorte.png")).convert("RGBA"))
    h, w = rec.shape[:2]
    a = rec[..., 3] > 0
    braco_todo = a & lado_braco(w, h)
    bone = disco(w, h, OMBRO, R_OMBRO)
    # o corte do cotovelo: perpendicular ao eixo do braço no pivô
    yy, xx = np.mgrid[0:h, 0:w]
    u = EIXO / np.linalg.norm(EIXO)
    abaixo = ((xx - COTOVELO[0]) * u[0] + (yy - COTOVELO[1]) * u[1]) > 0
    disco_cot = disco(w, h, COTOVELO, R_COTOVELO)
    antebraco = braco_todo & (abaixo | disco_cot)
    braco = braco_todo & ~antebraco
    corpo = a & ~(braco_todo & ~bone)          # o boné do ombro fica no corpo

    out = H3 / "pecas"
    out.mkdir(parents=True, exist_ok=True)
    for nome, m in (("corpo", corpo), ("braco", braco_todo & ~antebraco), ("antebraco", antebraco)):
        img = rec.copy()
        img[..., 3] = np.where(m, rec[..., 3], 0)
        Image.fromarray(img).save(out / f"{nome}.png")
        print(nome, int(m.sum()))
    json.dump({"ombro": OMBRO, "cotovelo": COTOVELO, "r_ombro": R_OMBRO, "r_cotovelo": R_COTOVELO,
               "tam": [w, h]}, open(out / "pecas.json", "w"), indent=1)


if __name__ == "__main__":
    main()
