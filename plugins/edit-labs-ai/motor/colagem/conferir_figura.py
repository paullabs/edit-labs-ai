"""Conferência da figura: acha automaticamente, antes de renderizar o vídeo, os defeitos que já quebraram figuras em
camadas (o boneco de terno que acena é o caso de estudo).

1. buracos(pasta, ref)      renders com alfa (quadros do Blender): buraco DENTRO da figura que não existe no repouso
                            (a axila que abria no tchau)
2. cortados(pasta)          peça encostando na borda do render (a mão do boneco 2D cortada pela caixa)
3. composto(pasta_quadros)  quadros da cena com só o exterior sobre magenta: buraco dentro da figura (o fundo
                            aparecendo) e borda branca de papel DENTRO da figura (corte interno com a borda de tesoura)
4. lascas(pasta)            renders com alfa: ponta fina saindo da figura (faces dobradas na barra, no punho, embaixo
                            do braço)
5. faltando(pecas, ref)     as peças do boneco 2D juntas cobrem a silhueta do 3D no repouso? (dente aberto no cotovelo)

Cada função devolve [(quadro, problema, área em px)] e grava uma imagem com o defeito marcado em magenta.

    python3 -I conferir_figura.py buracos <pasta com cor_q_*.png> <ref.png>
    python3 -I conferir_figura.py composto <pasta com q*.png>
    python3 -I conferir_figura.py lascas <pasta com cor_*.png>"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

MAGENTA = np.array([255, 0, 255])


def _fora(mascara_fundo):
    """pixels do fundo que se ligam à borda da imagem (o resto do fundo está preso dentro da figura = buraco)"""
    h, w = mascara_fundo.shape
    m = (mascara_fundo > 0).astype(np.uint8)
    ff = np.zeros((h + 2, w + 2), np.uint8)
    for x in range(0, w, 7):
        for y in (0, h - 1):
            if m[y, x] and not ff[y + 1, x + 1]:
                cv2.floodFill(m, ff, (x, y), 2)
    for y in range(0, h, 7):
        for x in (0, w - 1):
            if m[y, x] and not ff[y + 1, x + 1]:
                cv2.floodFill(m, ff, (x, y), 2)
    return m == 2


def _novos(buracos_, ref):
    """só os buracos que NÃO tocam um vão que já existe no repouso (o vão entre o braço e o corpo cresce quando o
    braço abre: é o mesmo vão, não é defeito)"""
    n, lab = cv2.connectedComponents(buracos_.astype(np.uint8), connectivity=8)
    out = np.zeros_like(buracos_, dtype=bool)
    for i in range(1, n):
        comp = lab == i
        if not (comp & ref).any():
            out |= comp
    return out


def _marca(rgb, mascara, saida):
    out = rgb.copy()
    out[mascara] = MAGENTA
    Image.fromarray(out.astype(np.uint8)).save(saida)


def buracos(pasta, ref, minimo=40, prefixo="cor_q_"):
    """buracos no alfa dos renders que não existem no quadro de referência (repouso)"""
    pasta = Path(pasta)
    a_ref = np.asarray(Image.open(ref).getchannel("A")) > 128
    buraco_ref = (~a_ref) & ~_fora(~a_ref)
    buraco_ref = cv2.dilate(buraco_ref.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    achados = []
    for f in sorted(pasta.glob(f"{prefixo}*.png")):
        im = Image.open(f)
        a = np.asarray(im.getchannel("A")) > 128
        b = (~a) & ~_fora(~a)
        b = cv2.morphologyEx(b.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        b = _novos(b, buraco_ref)
        area = int(b.sum())
        if area >= minimo:
            achados.append((f.name, "buraco dentro da figura", area))
            _marca(np.asarray(im.convert("RGB")), cv2.dilate(b.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0,
                   pasta.parent / f"_buraco_{f.stem}.png")
    return achados


def cortados(pasta, permitido=("baixo",), prefixo="cor_"):
    """peça encostando na borda do render (fora do quadro)"""
    achados = []
    for f in sorted(Path(pasta).rglob(f"{prefixo}*.png")):
        a = np.asarray(Image.open(f).getchannel("A")) > 20
        bordas = {"cima": a[0].sum(), "baixo": a[-1].sum(), "esquerda": a[:, 0].sum(), "direita": a[:, -1].sum()}
        for lado, n in bordas.items():
            if n > 3 and lado not in permitido:
                achados.append((str(f.relative_to(pasta)), f"encosta na borda de {lado}", int(n)))
    return achados


def composto(pasta, minimo_buraco=60, minimo_borda=120, ref=None):
    """quadros da cena com só o exterior sobre magenta puro: buraco (magenta preso dentro da figura) e borda branca
    de papel dentro da figura (clara e lisa, longe do contorno de fora)"""
    pasta = Path(pasta)
    fs = sorted(pasta.glob("q*.png"))
    achados = []
    ref_b = None
    if ref:
        r = np.asarray(Image.open(ref).convert("RGB")).astype(np.int32)
        fundo_r = np.abs(r - MAGENTA).sum(axis=2) < 90
        ref_b = cv2.dilate(((fundo_r) & ~_fora(fundo_r)).astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    for f in fs:
        rgb = np.asarray(Image.open(f).convert("RGB")).astype(np.int32)
        fundo = np.abs(rgb - MAGENTA).sum(axis=2) < 90
        preso = fundo & ~_fora(fundo)
        preso = cv2.morphologyEx(preso.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        if ref_b is not None:
            preso = _novos(preso, ref_b)
        figura = ~fundo
        dentro = cv2.erode(figura.astype(np.uint8), np.ones((29, 29), np.uint8)) > 0
        cinza = rgb.mean(axis=2).astype(np.float32)
        media = cv2.blur(cinza, (5, 5))
        desvio = np.sqrt(np.maximum(cv2.blur(cinza ** 2, (5, 5)) - media ** 2, 0))
        papel = (cinza > 222) & (desvio < 5) & (np.abs(rgb[..., 0] - rgb[..., 2]) < 40) & dentro
        papel = cv2.morphologyEx(papel.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        nb, nr = int(preso.sum()), int(papel.sum())
        if nb >= minimo_buraco:
            achados.append((f.name, "fundo aparecendo dentro da figura", nb))
        if nr >= minimo_borda:
            achados.append((f.name, "borda branca de papel dentro da figura", nr))
        if nb >= minimo_buraco or nr >= minimo_borda:
            _marca(rgb, cv2.dilate((preso | papel).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0,
                   pasta / f"_defeito_{f.stem}.png")
    return achados


def lascas(pasta, k=15, minimo=40, prefixo="cor_"):
    """pontas mais finas que k px saindo da figura (o que a abertura morfológica tira do alfa)"""
    achados = []
    for f in sorted(Path(pasta).rglob(f"{prefixo}*.png")):
        im = Image.open(f)
        a = np.asarray(im.getchannel("A"))
        ab = cv2.morphologyEx(a, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
        sobra = ((a > 128) & (ab < 128)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(sobra, connectivity=8)
        ruins = [i for i in range(1, n) if st[i, 4] >= minimo]
        if ruins:
            m = np.isin(lab, ruins)
            achados.append((str(f.relative_to(pasta)), f"{len(ruins)} lasca(s)", int(m.sum())))
            _marca(np.asarray(im.convert("RGB")), cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)) > 0,
                   Path(pasta) / f"_lasca_{f.stem}.png")
    return achados


def faltando(pecas, ref, minimo=60, folga=5):
    """pecas: alfas (mesmo tamanho) das peças do boneco no repouso; ref: alfa da figura inteira (o render 3D). Devolve a
    área da silhueta que nenhuma peça cobre (dente no cotovelo, fresta entre peças)"""
    uniao = np.zeros(ref.shape, bool)
    for a in pecas:
        uniao |= np.asarray(a) > 128
    dentro = cv2.erode((np.asarray(ref) > 128).astype(np.uint8), np.ones((2 * folga + 1, 2 * folga + 1), np.uint8)) > 0
    falta = (dentro & ~uniao).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(falta, connectivity=8)
    return [(int(cen[i, 0]), int(cen[i, 1]), int(st[i, 4])) for i in range(1, n) if st[i, 4] >= minimo]


if __name__ == "__main__":
    modo = sys.argv[1]
    if modo == "buracos":
        r = buracos(sys.argv[2], sys.argv[3])
    elif modo == "cortados":
        r = cortados(sys.argv[2])
    elif modo == "lascas":
        r = lascas(sys.argv[2])
    else:
        r = composto(sys.argv[2], ref=sys.argv[3] if len(sys.argv) > 3 else None)
    for x in r:
        print(x)
    print(f"{len(r)} problema(s)")
