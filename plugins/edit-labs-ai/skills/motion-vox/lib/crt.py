#!/usr/bin/env python3
"""
Tela de CRT com terminal rodando, projetada em perspectiva dentro do monitor.

Por que BLOCOS e nao texto de verdade: a nota do editor costuma proibir interface falsa
de aplicativo (referencias/registros.md), e escrever codigo na tela seria inventar
conteudo. Alem disso, no tamanho em que o monitor aparece (~330px de largura no quadro)
nenhum caractere seria legivel. Blocos de comprimento variavel leem como "tem coisa
rodando" sem afirmar nada — e a mesma regra do "indistinct pale field" dos prompts de foto.

O quadrilatero da tela foi MEDIDO no recorte (`A14_CRT_screen.npy`), nao estimado: o
monitor esta em tres-quartos, entao a tela e um trapezio e um paste reto denunciaria.
"""
import math
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
CUT = ROOT / "07_assets" / "cutout"

# fosforo ambar: registro documentario retro (Style Bible Familia C), e amarra no
# amarelo que ja e o acento do projeto
PHOSPHOR = (232, 214, 122)
GLASS = (18, 16, 14)

# comprimento de cada "linha" de terminal, em fracao da largura util
LINES = [0.30, 0.62, 0.44, 0.78, 0.36, 0.70, 0.52, 0.84, 0.41, 0.66, 0.29]
INDENT = [0.00, 0.06, 0.06, 0.00, 0.06, 0.06, 0.12, 0.00, 0.06, 0.06, 0.00]


def screen_content(w, h, progress, blink=0.0):
    """Terminal chapado, ainda sem perspectiva. `progress` revela linha a linha."""
    im = Image.new("RGB", (w, h), GLASS)
    d = ImageDraw.Draw(im)
    pad = w * 0.075
    uw = w - 2 * pad
    n = len(LINES)
    lh = (h - 2 * pad) / (n + 0.6)
    bh = max(2, int(lh * 0.34))

    shown = progress * n
    for i, (ln, ind) in enumerate(zip(LINES, INDENT)):
        if i >= shown:
            break
        frac = min(1.0, shown - i)
        y = pad + i * lh
        x0 = pad + ind * uw
        x1 = x0 + ln * uw * frac
        # a primeira linha e o prompt: um bloco curto separado
        if i == 0:
            d.rectangle([x0, y, x0 + bh * 1.1, y + bh], fill=PHOSPHOR)
            x0 += bh * 2.0
            x1 = max(x1, x0)
        d.rectangle([x0, y, x1, y + bh], fill=PHOSPHOR)

    # cursor piscando na linha corrente
    i = int(min(shown, n - 1e-6))
    if progress > 0:
        y = pad + i * lh
        frac = min(1.0, shown - i)
        x = pad + INDENT[i] * uw + LINES[i] * uw * frac + bh * 0.5
        if i == 0:
            x += bh * 2.0
        if blink < 0.55:
            d.rectangle([x, y, x + bh * 0.8, y + bh], fill=PHOSPHOR)

    a = np.asarray(im).astype(np.float32)
    # brilho de fosforo: o proprio traco espalha um pouco no vidro. Nao e "glow" de
    # filtro — e como fosforo se comporta, e some fora da tela.
    a = np.maximum(a, np.asarray(im.filter(ImageFilter.GaussianBlur(w * 0.012)))
                   .astype(np.float32) * 0.55)
    # scanlines
    yy = np.arange(h).reshape(-1, 1, 1)
    a *= (0.80 + 0.20 * (np.sin(yy * math.pi) * 0 + (yy % 3 != 0)))
    # vinheta do tubo
    Y, X = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((X - w / 2) / (w / 2)) ** 2 + ((Y - h / 2) / (h / 2)) ** 2)
    a *= np.clip(1.15 - 0.42 * np.clip(r - 0.35, 0, None) / 0.8, 0, 1)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def crt(width, progress=1.0, blink=0.0, rotation=0.0):
    """
    Monitor com a tela ligada. Devolve (imagem, ancora_do_centro_da_tela), com a
    ancora ja corrigida pela rotacao.
    """
    base = Image.open(CUT / "A14_CRT.png").convert("RGBA")
    quad = np.load(CUT / "A14_CRT_screen.npy")          # fracoes (TL,TR,BR,BL)
    s = width / base.width
    base = base.resize((int(base.width * s), int(base.height * s)), Image.LANCZOS)
    W_, H_ = base.size
    dst = (quad * np.array([W_, H_])).astype(np.float32)

    sw = int(max(np.linalg.norm(dst[1] - dst[0]), np.linalg.norm(dst[2] - dst[3])))
    sh = int(max(np.linalg.norm(dst[3] - dst[0]), np.linalg.norm(dst[2] - dst[1])))
    flat = screen_content(max(8, sw), max(8, sh), progress, blink)

    src = np.array([[0, 0], [sw, 0], [sw, sh], [0, sh]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(np.asarray(flat), M, (W_, H_),
                                 flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((sh, sw), 255, np.uint8), M, (W_, H_))
    mask = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=1)
    lay = Image.fromarray(warped).convert("RGBA")
    lay.putalpha(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(1.0)))

    out = base.copy()
    out.alpha_composite(lay)
    anchor = tuple((dst.mean(axis=0)).tolist())
    if rotation:
        old = out.size
        out = out.rotate(rotation, resample=Image.BICUBIC, expand=True)
        import voxlab as V
        anchor = V.rotate_anchor(old, out.size, rotation, anchor)
    return out, anchor


if __name__ == "__main__":
    from PIL import ImageDraw as D
    W = 300
    s = Image.new("RGB", (W * 5, 340), (232, 230, 222))
    d = D.Draw(s)
    for i, pr in enumerate([0.0, 0.25, 0.5, 0.75, 1.0]):
        im, _ = crt(W - 20, progress=pr, blink=(i % 2) * 0.9)
        s.paste(im, (i * W + 10, 30), im)
        d.text((i * W + 12, 8), f"progress {pr}", fill=(20, 20, 20))
    s.save(str(Path.cwd() / "crt_test.jpg"), quality=94)
    print("ok")
