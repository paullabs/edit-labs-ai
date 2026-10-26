"""
Família A + desenho que explica (v12.7) — planos inteiros feitos de traço, para quando a explicação é o assunto.

  linha_do_tempo  a promessa contra a realidade: o eixo dos anos se desenha no papel, um cursor anda de "hoje" até o
                  ano que a fala diz com o ano rolando em cima (o odômetro da série, agora com lugar no tempo), o ano
                  grande pousa no meio da tela e desce para o eixo; a foto do que foi prometido entra alfinetada
                  como polaroide no ano da promessa, uma seta tracejada liga a foto ao prazo prometido, o prazo leva
                  círculo e X em vermelho e uma chave vermelha mede o atraso até o ano real.

Parâmetros (quadros absolutos; anos podem ser fracionários, 2026.8 = outubro de 2026):
  anos [a0, a1], x [x0, x1] (px do eixo), y (altura do eixo), quadro_linha, dur_linha (12), fundo ("papel")
  rotulos   [{"ano", "quadro", "texto"?}]                      o ano escrito embaixo da marca
  marcas    [{"ano", "quadro", "texto", "cor", "abaixo"}]      bolinha no eixo e etiqueta curta em cima ou embaixo
  cursor    {"de", "ate", "quadro", "chega"}                   a bolinha vermelha anda e o ano rola em cima dela
  destaque  {"ano", "texto", "quadro", "desce", "corpo", "y", "pousa_dy"}  o ano grande no meio que desce para o eixo
  foto      {"imagem", "ponto" [x,y], "larg", "alt", "zoom", "ano", "quadro", "largura", "y", "rot", "legenda"}
  promessa  {"de", "ate", "quadro", "texto"}                   seta tracejada em arco de um ano a outro
  risco     {"ano", "quadro", "quadro_x"}                      círculo e depois X em vermelho no ano
  atraso    {"de", "ate", "quadro", "texto"?}                  chave vermelha embaixo do eixo entre os dois anos
Tudo dentro da zona segura do Reels (x 90-990, y 270-1520; ver ferramentas/zona_segura.py).
"""
import math

import cv2
import numpy as np

from familia_a import W, H
from familia_a import c2_letras as le, c3_style as st, c5_movimentos as mv, c6_motion as mo
from familia_a.compor import sobre
from planos import u, _fundo
from planos_noticia import _camera, TINTA_D, VERMELHO
import desenho as ds

FPS = 30
CINZA_ANO = (98.0, 96.0, 104.0)


def _polaroide(ctx, f):
    """A foto recortada num retângulo com moldura branca de polaroide (legenda escrita na faixa de baixo)."""
    def g():
        a = st.carregar(f["imagem"])[..., :3]
        lw, lh = int(f.get("largura", 360)), int(f.get("largura", 360) * f.get("proporcao", 0.72))
        z = float(f.get("zoom", 1.0))
        hh, ww = a.shape[:2]
        cw = min(ww, hh * lw / lh) / z
        ch = cw * lh / lw
        cx, cy = f.get("ponto", (ww / 2, hh / 2))
        x0 = int(min(max(0, cx - cw / 2), ww - cw)); y0 = int(min(max(0, cy - ch / 2), hh - ch))
        rec = cv2.resize(a[y0:y0 + int(ch), x0:x0 + int(cw)], (lw, lh), interpolation=cv2.INTER_AREA)
        rec = rec * float(f.get("ganho", 0.95))
        m = int(lw * 0.055)
        base = int(lw * 0.20) if f.get("legenda") else m
        lay = np.zeros((lh + m + base, lw + 2 * m, 4), np.float32)
        lay[..., :3] = (246.0, 244.0, 238.0)
        lay[..., 3] = 1.0
        lay[m:m + lh, m:m + lw, :3] = rec
        if f.get("legenda"):
            le.escrever(lay[..., :3], f["legenda"], centro=(lay.shape[1] / 2, m + lh + base / 2), fonte=le.SERIFA,
                        corpo=f.get("corpo_legenda", base * 0.62), cor=TINTA_D, contorno=0.6)
        return lay
    return ctx.cache(("polaroide", f["imagem"]), g)


def linha_do_tempo(n, p, ctx):
    img = _fundo(ctx, p)
    a0, a1 = p["anos"]
    x0, x1 = p.get("x", (130, 900))
    y = float(p.get("y", 1060))
    X = lambda ano: x0 + (float(ano) - a0) / (a1 - a0) * (x1 - x0)
    q0 = p.get("quadro_linha", p["inicio"])
    dl = p.get("dur_linha", 12)
    prog = ds._saida(ds._u(n, q0, dl), 1.8)
    ink = TINTA_D
    # eixo (o tempo anda para a direita: ponta no fim)
    ds._traco(img, n, {"pts": [[x0 - 40, y], [x1 + 30, y]], "quadro": q0, "dur": dl, "esp": 7, "ponta": True,
                       "cor": ink, "sombra": 0.0, "tremor": 0.8}, 5)
    xlim = x0 - 40 + prog * (x1 + 70 - x0)
    principais = {int(r["ano"]) for r in p.get("rotulos", [])}
    for ano in range(math.ceil(a0), math.floor(a1) + 1):
        xa = X(ano)
        if xa <= xlim:
            alto = 26 if ano in principais else 13
            ds._riscar(img, [np.array([[xa, y - alto], [xa, y + alto]], np.float32)], 5 if ano in principais else 3.5,
                       ink, 1.0, 0.0)
    for r in p.get("rotulos", []):
        if n >= r["quadro"]:
            e = mo.escala_palavra((n - r["quadro"]) / FPS)
            le.escrever(img, r.get("texto", str(r["ano"])), centro=(X(r["ano"]), y + 74), fonte=le.INTER,
                        corpo=r.get("corpo", 44), peso=800, cor=r.get("cor", CINZA_ANO), escala=e)
    for mk in p.get("marcas", []):
        if n >= mk["quadro"]:
            e = ds._saida(ds._u(n, mk["quadro"], 4), 2.4)
            c = ds.cor(mk.get("cor"), "tinta")
            cv2.circle(img, (int(X(mk["ano"])), int(y)), max(1, int(15 * e)), c, -1, cv2.LINE_AA)
            if mk.get("texto"):
                le.escrever(img, mk["texto"], centro=(X(mk["ano"]), y + 74 if mk.get("abaixo") else y - 70), fonte=le.INTER,
                            corpo=40, peso=800, cor=c, escala=mo.escala_palavra((n - mk["quadro"]) / FPS))
    cu = p.get("cursor")
    if cu and n >= cu["quadro"]:
        t = mv.suavizar_curva(u(n, cu["quadro"], cu["chega"]), "s", 1.7)
        ano = cu["de"] + (cu["ate"] - cu["de"]) * t
        xc = X(ano)
        ds._riscar(img, [np.array([[X(cu["de"]), y], [xc, y]], np.float32)], 9, VERMELHO, 1.0, 0.0)
        cv2.circle(img, (int(xc), int(y)), 18, VERMELHO, -1, cv2.LINE_AA)
        if n < cu.get("some", 10 ** 9):                             # o ano rola em cima do cursor (odômetro)
            v = math.floor(ano)
            fr = ano - v if n < cu["chega"] else 0.0
            for num, dy, al in ((v, -fr * 56, 1 - fr), (v + 1, (1 - fr) * 56, fr)):
                if al > 0.05 and num <= cu["ate"]:
                    le.escrever(img, str(num), centro=(xc, y - 78 + dy), fonte=le.INTER, corpo=46, peso=800,
                                cor=VERMELHO, alfa=al)
    de = p.get("destaque")
    if de and n >= de["quadro"]:
        desce = de.get("desce")
        g = mv.suavizar_curva(u(n, desce, desce + 9), "s", 2.0) if desce is not None and n >= desce else 0.0
        cx = 540 + (X(de["ano"]) - 540) * g
        cy = de.get("y", 700) + (y + de.get("pousa_dy", -150) - de.get("y", 700)) * g
        corpo = de.get("corpo", 230) * (1 - 0.55 * g)
        if g < 0.02:                                                # fio do número até o eixo
            ds._traco(img, n, {"pts": [[540, de.get("y", 700) + 120], [X(de["ano"]), y - 30]], "quadro": de["quadro"] + 2,
                               "dur": 6, "esp": 4, "tracejado": [16, 12], "cor": ink, "sombra": 0.0}, 9)
        le.escrever(img, de.get("texto", str(de["ano"])), centro=(cx, cy), fonte=le.SERIFA, corpo=corpo,
                    cor=de.get("cor", ink), contorno=1.0, escala=mo.escala_palavra((n - de["quadro"]) / FPS))
        if de.get("rotulo") and n >= de.get("quadro_rotulo", de["quadro"]):
            le.escrever(img, de["rotulo"], centro=(X(de["ano"]), y + 74 + 52), fonte=le.INTER, corpo=38, peso=800,
                        cor=VERMELHO, escala=mo.escala_palavra((n - de.get("quadro_rotulo", de["quadro"])) / FPS))
    pr = p.get("promessa")
    if pr and n >= pr["quadro"]:
        xa, xb = X(pr["de"]), X(pr["ate"])
        t = np.linspace(0, 1, 40)
        alt = pr.get("altura", 150)
        pts = np.stack([xa + (xb - xa) * t, y - 40 - alt * np.sin(np.pi * t)], 1)
        ds._traco(img, n, {"pts": pts.tolist(), "quadro": pr["quadro"], "dur": 9, "esp": 6, "tracejado": [22, 14],
                           "ponta": True, "cor": VERMELHO, "sombra": 0.0}, 21)
        if pr.get("texto") and n >= pr["quadro"] + 4:
            le.escrever(img, pr["texto"], centro=((xa + xb) / 2, y - 40 - alt - 46), fonte=le.SERIFA, corpo=pr.get("corpo", 76),
                        cor=VERMELHO, contorno=1.0, escala=mo.escala_palavra((n - pr["quadro"] - 4) / FPS))
    f = p.get("foto")
    if f and n >= f["quadro"]:
        lay = _polaroide(ctx, f)
        tq = u(n, f["quadro"], f["quadro"] + 7)
        g = mv.suavizar_curva(tq, "saida", 3.0)
        esc = 0.55 + 0.45 * g + 0.05 * math.sin(math.pi * tq) * (1 - tq)
        rot = float(f.get("rot", -4.0)) + (1 - g) * 10.0
        h_, w_ = lay.shape[:2]
        M = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), rot, esc)
        c, s = abs(M[0, 0]), abs(M[0, 1])
        nw, nh = int(h_ * s + w_ * c) + 4, int(h_ * c + w_ * s) + 4
        M[0, 2] += nw / 2 - w_ / 2; M[1, 2] += nh / 2 - h_ / 2
        lr = cv2.warpAffine(lay, M, (nw, nh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        cx, cy = f.get("x", X(f["ano"])), f.get("y", 700)
        som = cv2.GaussianBlur(lr[..., 3], (0, 0), 12.0)
        xs, ys = int(cx - nw / 2 + 10), int(cy - nh / 2 + 18)
        xa_, ya_, xb_, yb_ = max(0, xs), max(0, ys), min(W, xs + nw), min(H, ys + nh)
        if xa_ < xb_ and ya_ < yb_:
            img[ya_:yb_, xa_:xb_] *= (1 - 0.35 * som[ya_ - ys:yb_ - ys, xa_ - xs:xb_ - xs])[..., None]
        sobre(img, lr, cx - nw / 2, cy - nh / 2)
        if n >= f["quadro"] + 5:                                    # o alfinete
            px, py = int(cx + f.get("alfinete_dx", 0)), int(cy - nh / 2 + 22)
            cv2.circle(img, (px + 3, py + 5), 15, (150.0, 146.0, 140.0), -1, cv2.LINE_AA)
            cv2.circle(img, (px, py), 15, VERMELHO, -1, cv2.LINE_AA)
            cv2.circle(img, (px - 4, py - 5), 5, (236.0, 150.0, 150.0), -1, cv2.LINE_AA)
        if f.get("fio", True) and n >= f["quadro"] + 6:              # fio da foto até o ano
            ds._traco(img, n, {"pts": [[cx, cy + nh / 2 - 6], [X(f["ano"]), y - 34]], "quadro": f["quadro"] + 6, "dur": 5,
                               "esp": 4, "tracejado": [14, 10], "cor": ink, "sombra": 0.0}, 31)
    rs = p.get("risco")
    if rs and n >= rs["quadro"]:
        xr = X(rs["ano"])
        ds._circulo(img, n, {"centro": [xr, y + 40], "rx": 92, "ry": 92, "quadro": rs["quadro"], "dur": 7, "esp": 9,
                             "cor": VERMELHO, "sombra": 0.0}, 41)
        qx = rs.get("quadro_x")
        if qx is not None and n >= qx:
            r = 52
            for k, (pa, pb) in enumerate(((( xr - r, y + 40 - r), (xr + r, y + 40 + r)), ((xr + r, y + 40 - r), (xr - r, y + 40 + r)))):
                ds._traco(img, n, {"pts": [pa, pb], "quadro": qx + 2 * k, "dur": 3, "esp": 12, "cor": VERMELHO, "sombra": 0.0},
                          51 + k)
    at = p.get("atraso")
    if at and n >= at["quadro"]:
        xa, xb = X(at["de"]), X(at["ate"])
        yb = y + 170
        t = ds._saida(ds._u(n, at["quadro"], 8), 1.8)
        meio = (xa + xb) / 2
        ch = [[xa, yb - 34], [xa, yb], [meio - 18, yb], [meio, yb + 26], [meio + 18, yb], [xb, yb], [xb, yb - 34]]
        ds._traco(img, n, {"pts": ch, "quadro": at["quadro"], "dur": 8, "esp": 7, "cor": VERMELHO, "sombra": 0.0}, 61)
        if at.get("texto") and t > 0.9:
            le.escrever(img, at["texto"], centro=(meio, yb + 92), fonte=le.SERIFA, corpo=at.get("corpo", 84), cor=VERMELHO,
                        contorno=1.0, escala=mo.escala_palavra((n - at["quadro"] - 6) / FPS))
    return _camera(img, n, p, tuple(p.get("empurra", (1.0, 1.04))), centro=tuple(p.get("centro_camera", (W / 2, y - 160))))


TIPOS_DESENHO = {"linha_do_tempo": linha_do_tempo}
