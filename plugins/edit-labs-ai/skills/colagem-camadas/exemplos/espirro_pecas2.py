"""Mais peças do exemplo do espirro (cena_espirro.py), em cima do modelo 3D da garganta: a rolha do nariz, a tampa da
boca, o ar em fila, a cruz do hospital e o braço de perfil (o cotovelo na frente do rosto).

Tudo em papel e caneta, no estilo da colagem: cor chapada + textura de papel + borda branca de tesoura + contorno de tinta."""
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
import pecas as PC


def papel_forma(mascara, tom, semente=3, borda=7, tinta=3, mancha=None):
    """a forma (máscara L) vira recorte de papel: tom + grão, contorno de tinta, borda branca de tesoura"""
    w, h = mascara.size
    pad = borda + 6
    m = np.asarray(mascara)
    tex = PC.textura_papel(w, h, tom, semente).convert("RGBA")
    a = np.asarray(tex).copy()
    if mancha is not None:                                            # manchas de cor (ex.: as pintas da cortiça)
        a = mancha(a)
    out = Image.fromarray(a)
    out.putalpha(Image.fromarray(m))
    # contorno de tinta por dentro
    er = cv2.erode(m, np.ones((tinta * 2 + 1, tinta * 2 + 1), np.uint8))
    linha = (m.astype(np.int16) - er.astype(np.int16)).clip(0, 255).astype(np.uint8)
    arr = np.asarray(out).copy()
    t = (linha.astype(np.float32) / 255)[..., None]
    arr[..., :3] = (arr[..., :3] * (1 - t) + np.array(PC.TINTA, np.float32) * t).astype(np.uint8)
    out = Image.fromarray(arr)
    # borda branca
    big = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(out, (pad, pad))
    al = np.asarray(big.getchannel("A"))
    dil = cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * borda + 1, 2 * borda + 1)))
    base = PC.textura_papel(big.width, big.height, (246, 240, 224), semente + 1)
    base.putalpha(Image.fromarray(cv2.GaussianBlur(dil, (0, 0), 0.8)))
    base.alpha_composite(big)
    return base


def rolha(larg=120, alt=84, semente=5):
    """rolha de cortiça vista de lado, afinando para a esquerda (a ponta entra na narina): 'larg' x 'alt' px"""
    S = 3
    m = Image.new("L", (larg * S, alt * S), 0)
    d = ImageDraw.Draw(m)
    pts = [(0.0, 0.30), (0.78, 0.0), (1.0, 0.0), (1.0, 1.0), (0.78, 1.0), (0.0, 0.70)]
    d.polygon([(x * larg * S, y * alt * S) for x, y in pts], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S * 0.6)).resize((larg, alt), Image.LANCZOS)
    rng = np.random.default_rng(semente)

    def pintas(a):
        h, w = a.shape[:2]
        for _ in range(int(w * h / 150)):
            x, y = rng.integers(0, w), rng.integers(0, h)
            a[max(0, y - 1):y + 2, max(0, x - 2):x + 3, :3] = (150, 104, 62)
        return a
    im = papel_forma(m, (214, 170, 118), semente, borda=6, tinta=3, mancha=pintas)
    return im


def tampa(larg=96, alt=170, semente=6):
    """tampa vermelha de papel com a borda serrilhada, vista de lado, para a boca: estreita e alta"""
    S = 3
    m = Image.new("L", (larg * S, alt * S), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, larg * S - 1, alt * S - 1], radius=int(larg * S * 0.28), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S * 0.6)).resize((larg, alt), Image.LANCZOS)

    def estrias(a):
        h, w = a.shape[:2]
        for y in range(8, h - 6, 14):
            a[y:y + 3, 6:w - 6, :3] = (150, 40, 36)
        return a
    return papel_forma(m, (190, 60, 52), semente, borda=6, tinta=3, mancha=estrias)


def fila_specs(trilha, n, r, t0, passo, dur, parar_em=None, gap=2.15, amp=3.0, fim=None, fase0=0.0, cresce=1.0, encolhe=None):
    """o ar chega em fila e para: a i-ésima bolinha sai em t0 + i*passo, anda por 'dur' quadros e fica parada a (i*gap*r)
    px antes do fim (parar_em: comprimento onde a fila termina; padrão = o fim da trilha)"""
    L = trilha.L if parar_em is None else parar_em
    out = []
    for i in range(n):
        alvo = max(L - i * gap * r, 2 * r)
        tr = trilha.corta(alvo)
        out.append(dict(t0=t0 + int(round(i * passo)), t1=t0 + int(round(i * passo)) + dur, trilha=tr, r=r, amp=amp,
                        ciclos=1.5, fase=fase0 + 1.7 * i, fim=fim, cresce=cresce, **({'encolhe': encolhe} if encolhe else {})))
    return out


def cruz_hospital(tam=360, semente=4):
    """placa de papel branca com a cruz vermelha (sem texto), a marca do hospital"""
    m = Image.new("L", (tam, tam), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, tam - 1, tam - 1], radius=int(tam * 0.12), fill=255)

    def cruz(a):
        h, w = a.shape[:2]
        c, b, l = w // 2, int(w * 0.13), int(w * 0.34)
        a[c - b:c + b, c - l:c + l, :3] = PC.VERMELHO
        a[c - l:c + l, c - b:c + b, :3] = PC.VERMELHO
        return a
    return papel_forma(m, (248, 244, 232), semente, borda=8, tinta=4, mancha=cruz)


def braco_perfil(h_antebraco=640, larg=250, semente=7):
    """o antebraço levantado na frente do rosto, de perfil: a manga (azul-acinzentado) sobe na vertical, com o punho branco e a mão
    no alto, e o braço volta para trás, saindo do ombro (para a esquerda, na horizontal). O cotovelo (a dobra) fica embaixo, de
    frente para o rosto. Devolve (PIL, (x, y) do ponto da dobra, em px da imagem)."""
    S = 2
    esp = int(larg * 0.78) * S
    comp_tras = int(h_antebraco * 0.95) * S
    H = (h_antebraco + 260) * S
    W = comp_tras + esp * 2
    cot = (comp_tras, H - esp)                            # a dobra, embaixo, no canto
    topo = (comp_tras, int(esp * 1.9))
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    d.line([(0, cot[1]), cot, topo], fill=255, width=esp, joint="curve")
    d.ellipse([cot[0] - esp / 2, cot[1] - esp / 2, cot[0] + esp / 2, cot[1] + esp / 2], fill=255)
    cinza = PC.textura_papel(W, H, (96, 118, 154), semente, forca=0.9).convert("RGBA")
    cinza.putalpha(m)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.alpha_composite(cinza)
    borda = cv2.morphologyEx(np.asarray(m), cv2.MORPH_GRADIENT, np.ones((9, 9), np.uint8))
    ink = Image.new("RGBA", (W, H), PC.TINTA + (0,))
    ink.putalpha(Image.fromarray(borda))
    im.alpha_composite(ink)
    dr = ImageDraw.Draw(im)
    # o vinco da dobra do cotovelo
    dr.arc([cot[0] - esp * 0.55, cot[1] - esp * 0.75, cot[0] + esp * 0.35, cot[1] + esp * 0.25], 200, 300, fill=(60, 74, 104, 255), width=8)
    # o punho branco e a mão
    pun = [(topo[0] - esp / 2, topo[1] + esp * 0.55), (topo[0] + esp / 2, topo[1] + esp * 0.55), (topo[0] + esp / 2, topo[1] + esp * 0.18),
           (topo[0] - esp / 2, topo[1] + esp * 0.18)]
    dr.polygon(pun, fill=(246, 242, 232, 255), outline=PC.TINTA + (255,))
    dr.rounded_rectangle([topo[0] - esp * 0.46, topo[1] - esp * 0.62, topo[0] + esp * 0.46, topo[1] + esp * 0.2], radius=int(esp * 0.3),
                         fill=(226, 190, 150, 255), outline=PC.TINTA + (255,), width=8)
    out = im.resize((W // S, H // S), Image.LANCZOS)
    pad = 20
    big = Image.new("RGBA", (out.width + 2 * pad, out.height + 2 * pad), (0, 0, 0, 0))
    big.alpha_composite(out, (pad, pad))
    al = np.asarray(big.getchannel("A"))
    dil = cv2.dilate(al, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    base = PC.textura_papel(big.width, big.height, (246, 240, 224), semente + 1)
    base.putalpha(Image.fromarray(cv2.GaussianBlur(dil, (0, 0), 0.8)))
    base.alpha_composite(big)
    return base, {"cot": (cot[0] / S + pad, cot[1] / S + pad), "esp": esp / S, "barra_esq": cot[0] / S + pad - esp / S / 2,
                  "base_y": cot[1] / S + pad + esp / S / 2, "mao_topo": topo[1] / S + pad - 0.62 * esp / S}
