#!/usr/bin/env python3
"""
Legibilidade — o texto vai ser LIDO onde foi posto?

    python3 lib/legibilidade.py com_texto.png sem_texto.png
    python3 lib/legibilidade.py frame.png --sem fundo.png --json

Existe porque a rubrica D2 pergunta "legivel a 300px?" e "a cor de destaque tem funcao?"
em sim/nao, e a olho ninguem acerta contraste — tinta escura sobre foto escura parece
legivel na tela grande do editor e some no feed. O principio: tudo que se quer que seja
lido precisa ser pensado em como vai ser mostrado — texto que se difunde no meio da
imagem pode nao ser percebido.

## Como mede

Recebe o MESMO frame renderizado duas vezes — com o texto e sem ele. A diferenca isola
a mascara do texto sem precisar saber onde ele foi desenhado. Para cada bloco:

  contraste   razao WCAG entre a tinta do texto e o fundo IMEDIATO (anel de 14px em
              volta do bloco, que e o que o olho compara). 1,0 = invisivel.
  piso        o pior pedaco do bloco — um bloco pode ter media boa e um trecho que some
              sobre uma area clara da foto. E o piso que reprova, nao a media.
  altura      altura da tinta em px, e o equivalente a 300px de largura de preview.

## Faixas

  >= 4,5   confortavel (WCAG AA para texto normal)
  3,0-4,5  aceitavel so para texto GRANDE (>= 96px de tinta)
  < 3,0    REPROVA — sobre foto, resolve-se com sombra, tarja, ou mudando de lugar
  altura de tinta < 36px  ->  ilegivel a 300px de preview
"""
import sys, json
import numpy as np, cv2
from PIL import Image

AA, GRANDE, MIN_TINTA = 4.5, 3.0, 36


def _lum(rgb):
    """Luminancia relativa WCAG (canal linearizado)."""
    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _razao(l1, l2):
    a, b = max(l1, l2), min(l1, l2)
    return (a + 0.05) / (b + 0.05)


def medir(com, sem, limiar=14, anel=14):
    """Devolve um dicionario por bloco de texto encontrado."""
    A = np.asarray(Image.open(com).convert("RGB"))
    B = np.asarray(Image.open(sem).convert("RGB"))
    if A.shape != B.shape:
        raise SystemExit("os dois frames precisam ter o mesmo tamanho")
    dif = np.abs(A.astype(np.int16) - B.astype(np.int16)).max(axis=2)
    m = (dif > limiar).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8), iterations=2)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    LA, LB = _lum(A), _lum(B)
    out = []
    for i in range(1, n):
        x, y, w, h, area = st[i]
        if area < 900:                      # ruido de grao / boil
            continue
        sel = (lab == i)
        # anel de fundo: o que o olho compara e o que esta em volta, no frame SEM texto
        dil = cv2.dilate(sel.astype(np.uint8), np.ones((anel * 2 + 1,) * 2, np.uint8))
        ring = (dil > 0) & (~sel)
        l_bg = float(np.median(LB[ring])) if ring.any() else 0.0
        # A TINTA, nao o halo. A mascara de diferenca pega tambem a sombra projetada e o
        # antialiasing; num texto claro com sombra escura, a mediana do bloco cai em cima
        # da sombra e reporta contraste 1,2 num texto que se le perfeitamente. Pega-se o
        # extremo mais AFASTADO do fundo — que e o nucleo do glifo.
        p15, p85 = np.percentile(LA[sel], [15, 85])
        l_txt = float(p85 if abs(p85 - l_bg) > abs(p15 - l_bg) else p15)
        # piso: divide o bloco em colunas e acha o pior contraste local
        piso, pior_x = 99.0, None
        passo = max(24, w // 8)
        for xx in range(x, x + w, passo):
            col = sel.copy(); col[:, :xx] = False; col[:, xx + passo:] = False
            if col.sum() < 120: continue
            dcol = cv2.dilate(col.astype(np.uint8), np.ones((anel * 2 + 1,) * 2, np.uint8))
            rcol = (dcol > 0) & (~sel)
            if not rcol.any(): continue
            bgc = float(np.median(LB[rcol]))
            q15, q85 = np.percentile(LA[col], [15, 85])
            r = _razao(float(q85 if abs(q85 - bgc) > abs(q15 - bgc) else q15), bgc)
            if r < piso: piso, pior_x = r, xx
        # contraste INTERNO: tinta contra o que ela tem por tras DENTRO do bloco (a
        # faixa amarela, a tarja). Separa as duas causas de "nao se le":
        #   interno baixo -> a tinta some no proprio fundo dela
        #   externo baixo -> o bloco inteiro some na imagem (o caso da faixa amarela
        #                    sobre carroceria vermelha)
        vals = LA[sel]
        interno = _razao(float(np.percentile(vals, 12)), float(np.percentile(vals, 88)))
        # DIFERENCA DE MATIZ. O WCAG so mede luminancia — e por isso subestima um bloco
        # de cor saturada contra um fundo de outra cor. Uma etiqueta amarela sobre
        # carroceria vermelha da razao 2,7 (que "reprovaria") e o olho separa as duas
        # sem esforco, porque a diferenca esta no croma, nao no brilho. Entao: para o
        # BLOCO ser notado basta luminancia OU croma; para o TEXTO ser lido, so
        # luminancia serve (o interno).
        lab_a = cv2.cvtColor(A, cv2.COLOR_RGB2LAB).astype(np.float32)
        lab_b = cv2.cvtColor(B, cv2.COLOR_RGB2LAB).astype(np.float32)
        ab_t = lab_a[..., 1:][sel].mean(axis=0)
        ab_f = lab_b[..., 1:][ring].mean(axis=0) if ring.any() else ab_t
        croma = float(np.hypot(*(ab_t - ab_f)))
        out.append(dict(caixa=[int(x), int(y), int(w), int(h)],
                        externo=round(_razao(l_txt, l_bg), 2),
                        interno=round(interno, 2), croma=round(croma, 1),
                        piso=round(piso, 2), pior_x=pior_x,
                        altura_tinta=int(h), area=int(area),
                        quadro=(int(A.shape[1]), int(A.shape[0]))))
    return sorted(out, key=lambda o: o["caixa"][1])


def veredito(o, W=None, H=None):
    p = []
    r, i = o["piso"], o["interno"]
    grande = o["altura_tinta"] >= 96
    if i < GRANDE:
        p.append(f"INTERNO {i} — a tinta some no proprio fundo dela")
    croma_ok = o.get("croma", 0) >= 28      # separacao por matiz, medida em Lab
    if r < GRANDE and not croma_ok:
        p.append(f"EXTERNO {r} — o bloco some na imagem" if i >= GRANDE
                 else f"EXTERNO {r}")
    elif r < GRANDE and croma_ok:
        p.append(f"externo {r} baixo, mas croma {o['croma']:.0f} separa — ok")
    elif r < AA and not grande and not croma_ok:
        p.append(f"externo {r} — so passa se for texto grande")
    if o["altura_tinta"] < MIN_TINTA:
        p.append(f"tinta de {o['altura_tinta']}px — ilegivel a 300px de preview")
    if W is None or H is None:  # o quadro da imagem medida (vertical ou horizontal)
        W, H = o.get("quadro", (1080, 1920))
    x, y, w, h = o["caixa"]
    if H > W:   # vertical: faixas de interface do celular (Reels/TikTok/Shorts)
        if x + w > W - 120: p.append(f"invade a exclusao de interface da direita (x>{W - 120})")
        if y + h > H - 260: p.append(f"invade a exclusao inferior (y>{H - 260})")
        if x < 96 or x + w > W - 96: p.append("fora das margens laterais de 96px")
    else:       # horizontal: margem de titulo de 5% em volta
        mx, my = int(W * 0.05), int(H * 0.05)
        if x < mx or x + w > W - mx or y < my or y + h > H - my:
            p.append(f"fora da margem de titulo de 5% ({mx}px x {my}px)")
    return p or ["ok"]


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    com, sem = argv[0], argv[1] if not argv[1].startswith("--") else argv[argv.index("--sem") + 1]
    regs = medir(com, sem)
    if "--json" in argv:
        print(json.dumps(regs, indent=1)); return 0
    print(f"{len(regs)} bloco(s) de texto em {com}\n")
    print(f"{'caixa (x,y,w,h)':>24s}{'tinta':>7s}{'interno':>9s}{'externo':>9s}{'piso':>7s}{'croma':>7s}  veredito")
    ruim = 0
    for o in regs:
        v = veredito(o); ruim += (v != ["ok"])
        x, y, w, h = o["caixa"]
        print(f"{f'{x},{y},{w},{h}':>24s}{o['altura_tinta']:>6d}p{o['interno']:>9.2f}"
              f"{o['externo']:>9.2f}{o['piso']:>7.2f}{o['croma']:>7.0f}  {' · '.join(v)}")
    print("\ninterno = tinta contra o fundo DELA — so luminancia serve")
    print("externo = o bloco contra a imagem — luminancia OU croma >= 28 basta")
    print("piso    = o pior pedaco do bloco, que e o que reprova")
    print(f"faixas: >=4,5 confortavel · 3,0-4,5 so para tinta >=96px · <3,0 reprova")
    return 1 if ruim else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
