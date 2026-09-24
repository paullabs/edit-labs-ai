#!/usr/bin/env python3
"""
Recorte local dos assets gerados.

Regra do Diretor (D1, item 2): sombra e CAMADA, nunca pixel embutido no asset.

Tres passes:

  P1  Flood-fill FIXED_RANGE semeado nas bordas, tolerancia lida no PLATO da varredura.
      Remove o fundo chapado. Sobra a sombra de contato colada no objeto.
      (Tolerancia RELATIVA AO VIZINHO nao serve: escorre por gradiente liso e come o
      interior de objetos chapados — cartao e caixa somem inteiros.)

  P2  Dilatacao do fundo restrita a mascara de sombra. Medido nos assets do kit:
      TODO objeto e mais CLARO que o fundo (nucleo 172-242 contra fundo 150-177) e
      a sombra e mais ESCURA e LISA. Entao o fundo so pode crescer onde o pixel e
      simultaneamente (a) nao mais claro que o fundo, (b) neutro como o fundo,
      (c) de gradiente baixo. Aco escovado e tinta de gravura tem gradiente alto e
      ficam protegidos.

  P3  Fundo encapsulado: o miolo dos clipes de papel e cinza-fundo cercado pelo arame.
      O flood da P1 nao chega la. Como esse miolo tem exatamente a cor do fundo e e
      liso, basta furar por cor+gradiente. So ligado onde faz sentido (`punch_bg`).

Uso:  python3 cutout.py                    # processa todos os do CFG
      python3 cutout.py A02_CLOCK ...      # processa alguns
      python3 cutout.py --sweep A12_KEY    # varredura de tolerancia: escolha o PLATO

ESCOLHA DO FUNDO NA GERACAO: pelo maior afastamento de LUMINANCIA do objeto.
  objeto claro (papel, cartao)  -> fundo #8A8A8A
  objeto escuro (teclado)       -> fundo #D8D8D8  + dark_floor no CFG
Fundo chroma torna o matte trivial mas contamina ~65% dos pixels de borda com spill.
Pedir "fundo transparente" ao modelo NAO funciona: devolve RGB sem alfa.
"""
import sys
from pathlib import Path
import numpy as np
import cv2
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "07_assets" / "raw"
OUT = ROOT / "07_assets" / "cutout"
OUT.mkdir(parents=True, exist_ok=True)

def luma(a):
    """BLAS da Accelerate estoura com matmul (h,w,3)@(3,) — faz na mao, em float32."""
    f = a.astype(np.float32)
    return 0.299 * f[..., 0] + 0.587 * f[..., 1] + 0.114 * f[..., 2]

# shadow_reach=200: a dilatacao e barata e so avanca onde `permit` deixa, entao dar
# alcance de sobra nao custa nada e garante que a cunha de sombra profunda seja
# alcancada. Quem controla a seguranca e `grad`, nao o alcance.
# Preencha por asset. `tol` sai da varredura (--sweep), lida no PLATO.
CFG = {
    "A02_CLOCK":  dict(tol=22, shadow_reach=200, grad=18.0),
    "A03_TAPE":   dict(tol=26, shadow_reach=200, grad=14.0),
    "A04_CLIPS":  dict(tol=20, shadow_reach=200, grad=7.0, trim=1, punch_bg=True),
    "A05_CARD":   dict(tol=20, shadow_reach=200, grad=14.0),
    "A06_CAVE":   dict(tol=20, shadow_reach=200, grad=14.0),
    "A07_IDEA":   dict(tol=20, shadow_reach=200, grad=14.0),
    "A08_BOX":    dict(tol=26, shadow_reach=200, grad=22.0),
    "A09_STACK":  dict(tol=20, shadow_reach=200, grad=14.0, min_area=0.004),
    "A10_SCRAPS": dict(tol=20, shadow_reach=200, grad=12.0),
    "A12_KEYBOARD": dict(tol=22, shadow_reach=200, grad=6.0, dark_floor=52, trim=1),
    "A14_CRT":      dict(tol=20, shadow_reach=200, grad=22.0, min_area=0.02),
    "A15_MONEY_STACK": dict(tol=20, shadow_reach=200, grad=16.0),
    "A17_MONEY_FEW":   dict(tol=32, shadow_reach=200, grad=16.0),
}


def cut(name, tol=20, shadow_reach=70, grad=12.0, feather=1.1, trim=2,
        min_area=0.0008, punch_bg=False, dark_floor=None, break_bridge=0,
        min_col=0.0):
    a = np.asarray(Image.open(RAW / f"{name}.png").convert("RGB"))
    h, w = a.shape[:2]

    bg_lum = float(luma(a[:40, :40]).mean())
    bg_chroma = float(a[:40, :40].max(axis=2).mean() - a[:40, :40].min(axis=2).mean())

    # ---- P1: flood do fundo chapado
    work = a.copy()
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
    for s in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3),
              (w // 2, 2), (w // 2, h - 3), (2, h // 2), (w - 3, h // 2)]:
        cv2.floodFill(work, mask, s, 0, (tol,) * 3, (tol,) * 3, flags)
    bg = (mask[1:-1, 1:-1] > 0).astype(np.uint8)

    # ---- P2: cresce o fundo apenas dentro da sombra
    lum = luma(a)
    chroma = a.max(axis=2).astype(np.float32) - a.min(axis=2).astype(np.float32)
    g = cv2.GaussianBlur(lum, (0, 0), 2.0).astype(np.float32)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    gmag = cv2.GaussianBlur(np.sqrt(gx * gx + gy * gy), (0, 0), 2.0)

    # A regra padrao ("objeto e mais CLARO que o fundo") vale para papel e metal, mas
    # NAO para objeto escuro — o teclado tem nucleo em 73 contra fundo 144, e a regra
    # comeria a peca inteira. `dark_floor` troca o teto por uma FAIXA: o fundo so cresce
    # dentro do intervalo onde mora a sombra. Quem protege as teclas e o gradiente:
    # sombra e lisa, tecla e cercada de borda.
    lo_ok = (lum >= bg_lum - dark_floor) if dark_floor else True
    permit = ((lum <= bg_lum + 3.0) & lo_ok &
              (chroma <= bg_chroma + 12.0) &
              (gmag <= grad)).astype(np.uint8)

    k = np.ones((3, 3), np.uint8)
    if shadow_reach:
        grown = cv2.dilate(bg, k, iterations=int(shadow_reach))
        # so a parte da dilatacao que e permitida, e ainda conectada ao fundo
        cand = ((grown | bg) & (permit | bg)).astype(np.uint8)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(cand, 8)
        touch = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
        touch.discard(0)
        bg = np.isin(lab, list(touch)).astype(np.uint8)

    bg = cv2.morphologyEx(bg, cv2.MORPH_CLOSE, k, iterations=1)
    alpha = (1 - bg).astype(np.uint8) * 255

    # ---- descarta faixa fina lateral encostada no objeto
    # Resto de sombra as vezes forma uma barra baixa colada na lateral: e um so
    # componente com o corpo e a ponte e grossa demais para abertura morfologica.
    # A geometria separa: a barra tem poucas dezenas de linhas por coluna, o corpo tem
    # centenas. Zera as colunas cuja altura de objeto nao chega a `min_col` do pico.
    if min_col:
        colh = (alpha > 128).sum(axis=0)
        thr = colh.max() * min_col
        keepc = colh >= thr
        if keepc.any():
            lo, hi = np.argmax(keepc), len(keepc) - np.argmax(keepc[::-1])
            alpha[:, :lo] = 0
            alpha[:, hi:] = 0

    # ---- quebra pontes finas antes de contar componentes
    # Resto de sombra as vezes liga um respingo distante ao corpo por uma tira de poucos
    # pixels: o filtro de area nao pega, porque tudo vira UM componente. Abrir com um
    # kernel maior que a ponte separa, ai fica so a massa principal, e a dilatacao
    # devolve a silhueta original (limitada pelo alfa de antes, entao nao incha).
    if break_bridge:
        k2 = np.ones((break_bridge, break_bridge), np.uint8)
        core = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, k2, iterations=1)
        nn, ll, ss, _ = cv2.connectedComponentsWithStats(core, 8)
        if nn > 1:
            keep = 1 + int(np.argmax(ss[1:, cv2.CC_STAT_AREA]))
            core = (ll == keep).astype(np.uint8) * 255
            alpha = np.minimum(alpha, cv2.dilate(core, k2, iterations=2))

    # ---- descarta ilhas de ruido
    n, lab, stats, _ = cv2.connectedComponentsWithStats(alpha, 8)
    if n > 1:
        keep = [i for i in range(1, n) if stats[i, cv2.CC_STAT_AREA] > h * w * min_area]
        alpha = np.isin(lab, keep).astype(np.uint8) * 255

    # ---- P3: fundo encapsulado (miolo dos clipes)
    if punch_bg:
        near_bg = (np.abs(lum - bg_lum) < 9) & (chroma <= bg_chroma + 8) & (gmag <= grad)
        alpha[near_bg] = 0
        alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, k, iterations=1)

    if trim:
        alpha = cv2.erode(alpha, k, iterations=trim)
    ai = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(feather))

    out = Image.fromarray(a).convert("RGBA")
    out.putalpha(ai)
    bbox = out.getbbox()
    if bbox:
        out = out.crop(bbox)
    out.save(OUT / f"{name}.png")
    print(f"{name:12s} {out.width}x{out.height}  cobertura={(np.asarray(ai)>128).mean()*100:5.1f}%")
    return out


def sweep(name):
    """Varredura de tolerancia. Escolha o PLATO: o ponto a partir do qual aumentar a
    tolerancia nao remove mais nada — fundo e penumbra ja foram consumidos."""
    a = np.asarray(Image.open(RAW / f"{name}.png").convert("RGB"))
    h, w = a.shape[:2]
    print(f"{name}: percentual que sobra como OBJETO, por tolerancia")
    for tol in (4, 8, 12, 16, 20, 26, 32, 40):
        work = a.copy()
        mask = np.zeros((h + 2, w + 2), np.uint8)
        flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
        for sd in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3),
                   (w // 2, 2), (w // 2, h - 3), (2, h // 2), (w - 3, h // 2)]:
            cv2.floodFill(work, mask, sd, 0, (tol,) * 3, (tol,) * 3, flags)
        print(f"   tol={tol:3d}  {(mask[1:-1,1:-1]==0).mean()*100:5.1f}%")


if __name__ == "__main__":
    # --cfg '{"punch_bg": true, "tol": 22}' vale para os nomes desta chamada (asset novo sem linha no CFG:
    # ex. etiqueta com barbante em laço pede punch_bg para furar o fundo preso dentro do laço)
    import json as _json
    args = sys.argv[1:]
    extra = {}
    if "--cfg" in args:
        k = args.index("--cfg")
        extra = _json.loads(args[k + 1])
        del args[k:k + 2]
    if args and args[0] == "--sweep":
        for t in args[1:]:
            sweep(t)
    else:
        for t in (args or list(CFG)):
            cut(t, **{**CFG.get(t, {}), **extra})
