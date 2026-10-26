#!/usr/bin/env python3
"""
Melhora um asset para a cena. Entrada em qualquer pasta do projeto; saida em assets/prontos/.

    mvpy melhorar.py recorte     <entrada> <saida.png> [--tol 22] [--tudo]
    mvpy melhorar.py recorte-ceu <entrada> <saida.png>            (fundo em degrade + chao)
    mvpy melhorar.py pb-cor      <entrada> <saida.png> --faixa 170,8 [--faixa 35,85] [--sat 70]
    mvpy melhorar.py casar-cor   <entrada> <saida.png> --de R,G,B:R,G,B --para R,G,B:R,G,B
    mvpy melhorar.py ampliar     <entrada> <saida.png> --fator 2
    mvpy melhorar.py grao        <entrada> <saida.png> [--forca 5.0]

Receitas e porques em referencias/assets.md.
"""
import sys
import numpy as np, cv2
from PIL import Image


def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)


def salvar(a, p):
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(p); print(p, a.shape[1], "x", a.shape[0])


def cortar_caixa(a):
    ys, xs = np.where(a[..., 3] > 8)
    return a[max(0, ys.min() - 4):ys.max() + 5, max(0, xs.min() - 4):xs.max() + 5]


def recorte_chapado(a, tol=22, macio=10, so_borda=True):
    rgb = a[..., :3]
    h, w = rgb.shape[:2]
    canto = np.median(np.concatenate([rgb[:8, :8].reshape(-1, 3), rgb[:8, -8:].reshape(-1, 3),
                                      rgb[-8:, :8].reshape(-1, 3), rgb[-8:, -8:].reshape(-1, 3)]), axis=0)
    dist = np.sqrt(((rgb - canto) ** 2).sum(-1))
    fundo = dist < tol
    if so_borda:
        m = np.zeros((h + 2, w + 2), np.uint8); f8 = fundo.astype(np.uint8) * 255
        for (x, y) in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
            if f8[y, x]:
                cv2.floodFill(f8, m, (x, y), 128)
        fundo = f8 == 128
    alfa = np.clip((dist - tol) / max(1, macio), 0, 1)
    alfa[fundo] = 0
    a = a.copy(); a[..., 3] = cv2.GaussianBlur(alfa, (0, 0), 0.8) * 255
    return a


def recorte_ceu(a):
    rgb = a[..., :3].astype(np.uint8)
    liso = cv2.bilateralFilter(cv2.GaussianBlur(rgb, (0, 0), 1.5), 9, 25, 9)
    h, w = rgb.shape[:2]; fundo = np.zeros((h + 2, w + 2), np.uint8)
    for x in range(3, w - 3, max(1, w // 12)):
        cv2.floodFill(liso.copy(), fundo, (x, 3), (0, 0, 0), (3, 3, 3), (3, 3, 3), 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    ceu = fundo[1:-1, 1:-1] > 0
    escuro = (rgb.mean(-1) < 90).mean(1)
    linha_pes = int(np.max(np.where(escuro > 0.05)[0])) if (escuro > 0.05).any() else h - 1
    grad = np.clip(1 - (np.arange(h) - linha_pes) / 18.0, 0, 1)[:, None]
    a = a.copy(); a[..., 3] = cv2.GaussianBlur((1 - ceu.astype(np.float32)) * grad, (0, 0), 0.8) * 255
    return a


def pb_cor(a, faixas, sat_min=70):
    hsv = cv2.cvtColor(np.clip(a[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
    hh, s = hsv[..., 0], hsv[..., 1]
    m = np.zeros(hh.shape, bool)
    for lo, hi in faixas:
        m |= ((hh >= lo) | (hh <= hi)) if lo > hi else ((hh >= lo) & (hh <= hi))
    m &= s > sat_min
    mm = cv2.GaussianBlur(cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(np.float32), (0, 0), 1.5)
    cinza = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2])[..., None]
    out = a.copy(); out[..., :3] = a[..., :3] * mm[..., None] + cinza * (1 - mm[..., None])
    return out


def casar_cor(a, de, para):
    """Duas cores-ancora (medidas no asset e na referencia) -> mapa linear por canal."""
    out = a.copy(); mapa = []
    for c in range(3):
        g = (para[1][c] - para[0][c]) / max(1e-6, de[1][c] - de[0][c]); o = para[0][c] - g * de[0][c]
        out[..., c] = a[..., c] * g + o; mapa.append((round(g, 3), round(o, 1)))
    print("mapa por canal (ganho, soma):", mapa)
    return out


def ampliar(a, fator):
    r = cv2.resize(a, (int(a.shape[1] * fator), int(a.shape[0] * fator)), interpolation=cv2.INTER_LANCZOS4)
    borr = cv2.GaussianBlur(r, (0, 0), 1.0)
    r[..., :3] = np.clip(r[..., :3] * 1.5 - borr[..., :3] * 0.5, 0, 255)
    return r


def grao(a, forca=5.0, semente=1):
    g = cv2.GaussianBlur(np.random.default_rng(semente).normal(0, 1, a.shape[:2]).astype(np.float32), (0, 0), 1.0)
    g *= forca / (g.std() + 1e-6)
    out = a.copy(); out[..., :3] += g[..., None]
    return out


if __name__ == "__main__":
    c, ent, sai = sys.argv[1], sys.argv[2], sys.argv[3]
    arg = sys.argv[4:]
    op = lambda k, d=None: arg[arg.index(k) + 1] if k in arg else d
    a = rgba(ent)
    if c == "recorte":
        salvar(cortar_caixa(recorte_chapado(a, tol=float(op("--tol", 22)), so_borda="--tudo" not in arg)), sai)
    elif c == "recorte-ceu":
        salvar(cortar_caixa(recorte_ceu(a)), sai)
    elif c == "pb-cor":
        fx = [tuple(int(v) for v in arg[i + 1].split(",")) for i, x in enumerate(arg) if x == "--faixa"]
        salvar(pb_cor(a, fx, float(op("--sat", 70))), sai)
    elif c == "casar-cor":
        par = lambda s: [tuple(float(v) for v in t.split(",")) for t in s.split(":")]
        salvar(casar_cor(a, par(op("--de")), par(op("--para"))), sai)
    elif c == "ampliar":
        salvar(ampliar(a, float(op("--fator", 2))), sai)
    elif c == "grao":
        salvar(grao(a, float(op("--forca", 5.0))), sai)
