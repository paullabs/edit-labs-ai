#!/usr/bin/env python3
"""
Prepara a fotografia noturna do kit (pessoa imersa no notebook) para uma cena.

A imagem gerada tem 82,5% de massa escura — o que falta nas cenas de mesa clara
(podem medir menos de 5%, contra os 10-18% da identidade). Mas o azul da area
iluminada tem croma 6,5: praticamente neutro. O azul da tela precisa ser CONSTRUIDO,
nao "realcado".

Como: mapa de gradiente sobre a luminancia (duotone estendido).
  - sombras profundas ficam em carvao QUENTE e quase neutro, para ancorar o quadro
    e nao virar "imagem azul";
  - a faixa media, que e a luz derramada no rosto e na mesa, recebe o azul da paleta;
  - o nucleo da tela permanece quase branco, senao para de ler como FONTE de luz.

Isso e a Familia B da Style Bible — foto monocromatica com uma unica cor intensa
codificando a informacao. Nao e filtro azul, nao e glow, nao e bloom: a luz continua
sendo a que foi fotografada, so a curva de cor mudou.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "07_assets" / "raw"
CUT = ROOT / "07_assets" / "cutout"

# Proporcao de FOTO IMPRESSA (~1.43), nao da geracao. O cartao de montagem e 1.40:
# com um corte de 1.26 a foto fica quase da altura do cartao e a margem branca some —
# e a margem grossa e o que separa a foto do fundo azul-escuro do estudio.
CROP = (0.030, 0.160, 0.975, 0.820)          # left, top, right, bottom (fracao)
CROP_EMPTY = (0.045, 0.180, 0.960, 0.845)

# paradas do mapa de gradiente: (posicao na luminancia, cor)
STOPS = [
    (0.00, (20, 20, 24)),        # preto fosco, nao esmagado
    (0.17, (30, 39, 60)),        # parede: precisa continuar VISIVEL, senao o corpo
    (0.40, (34, 74, 142)),       # some no fundo e a silhueta se perde
    (0.66, (46, 130, 247)),      # #2E82F7 — acento da paleta
    (0.86, (150, 200, 252)),     # borda da tela
    (1.00, (244, 250, 255)),     # nucleo da tela: quase branco = fonte
]


# A mesa VAZIA e o par de contraste da mesa iluminada. Mesmo sistema, cor ausente:
# a foto morta vai para cinza frio neutro. Assim o azul da cena noturna nao e enfeite —
# e a diferenca entre quem esta fazendo e quem nao esta. "A cor tem funcao."
STOPS_EMPTY = [
    (0.00, (19, 19, 22)),
    (0.20, (38, 39, 43)),
    (0.48, (78, 80, 86)),
    (0.74, (126, 128, 134)),
    (0.90, (172, 174, 179)),
    (1.00, (214, 216, 220)),
]


def gradient_map(lum01, STOPS=None):
    STOPS = STOPS or globals()["STOPS"]
    xs = np.array([s[0] for s in STOPS], dtype=np.float32)
    out = np.empty(lum01.shape + (3,), dtype=np.float32)
    for c in range(3):
        ys = np.array([s[1][c] for s in STOPS], dtype=np.float32)
        out[..., c] = np.interp(lum01, xs, ys)
    return out


def build(src="A11_NIGHT_v1", dst="A11_NIGHT", crop=None, stops=None, core_blur=7.0):
    crop = crop or CROP
    im = Image.open(RAW / f"{src}.png").convert("RGB")
    w, h = im.size
    im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    a = np.asarray(im).astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]

    # normaliza pelo alcance real da foto, senao o mapa desperdica metade da curva
    # 82% da foto e escura: um percentil baixo joga quase tudo no fundo da curva e
    # esmaga a silhueta. Corta em 2% e levanta os meios-tons com gama < 1.
    lo, hi = np.percentile(lum, 2.0), np.percentile(lum, 99.6)
    n = np.clip((lum - lo) / max(1.0, hi - lo), 0, 1)
    n = n ** 0.80

    out = gradient_map(n, stops)

    # a interface fraca na tela nao pode virar "app falso" (interface falsa e proibida):
    # borra SO o nucleo mais claro, onde ela esta, preservando a borda do notebook
    core = np.clip((n - 0.74) / 0.26, 0, 1)[..., None]
    soft = np.asarray(Image.fromarray(out.astype(np.uint8))
                      .filter(ImageFilter.GaussianBlur(core_blur))).astype(np.float32)
    out = out * (1 - core) + soft * core

    # grao de filme, coerente com o resto do projeto
    rng = np.random.default_rng(7)
    out = np.clip(out + rng.normal(0, 5.0, out.shape), 0, 255)

    img = Image.fromarray(out.astype(np.uint8))
    DST = CUT / f"{dst}.png"
    img.save(DST)

    fl = 0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2]
    lit = fl > 110
    mx, mn = out.max(axis=2), out.min(axis=2)
    print(f"{DST.name}  {img.width}x{img.height}")
    print(f"  massa escura(lum<105) {(fl < 105).mean() * 100:5.1f}%")
    print(f"  area iluminada        {lit.mean() * 100:5.1f}%   croma medio {(mx - mn)[lit].mean():5.1f}"
          f"   (antes: 6.5)")
    ys, xs = np.where(fl > 190)
    if len(xs):
        print(f"  centroide da tela     x={xs.mean() / img.width:.3f} y={ys.mean() / img.height:.3f}")
    return img


if __name__ == "__main__":
    build()
    build(src="A13_EMPTY_v1", dst="A13_EMPTY", crop=CROP_EMPTY, stops=STOPS_EMPTY,
          core_blur=2.0)
