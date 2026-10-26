"""Peças do explicador Vox no tamanho planejado do plano.json, em resolução R x (R = 2: o mundo aguenta o
mergulho de 2x da câmera sem borrar). Toda peça que gira tem o pivô no centro do arquivo.

    clpy pecas.py base <pasta_pecas>
        -> fundo_papel, fundo_carvao, grade_papel, grade_escuro, vinheta (servem para qualquer vídeo do estilo)

    clpy pecas.py exemplo --reais <pasta> --gerados <pasta> --lizars <pasta> --saida <pasta_pecas>
        -> as receitas do exemplo "soco no queixo" (pessoa de cima, luva, pino, fita, chave, crânio e cérebro,
           foto em cartão, cartão do artigo). Use como modelo: as coordenadas foram medidas nas imagens daquele
           vídeo (ver os comentários) e mudam com as suas.

As peças prontas do exemplo já estão em exemplo/pecas/; este script é para refazer ou para copiar as receitas.
Funções gerais que valem para qualquer vídeo: canvas, colocar, borda_papel, bbox_alfa, cartao_foto, fundo_papel,
fundo_carvao, grade, vinheta, torcao_radial."""
import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

R = 2
PLUGIN = Path(__file__).resolve().parents[3]
FONTES = PLUGIN / "skills" / "motion-vox" / "fontes"     # Inter e Fraunces (OFL), já vêm no plugin
CREME_PAPEL = (244, 240, 232)
VERMELHO = (168, 67, 75)              # o vermelho da luva: único acento do exemplo
MEDIDAS = {}
SAI = Path(".")


def fonte(arquivo, corpo, peso=None):
    """fonte variável do plugin no peso pedido (eixo wght), ou a padrão se não der"""
    f = ImageFont.truetype(str(FONTES / arquivo), int(corpo))
    if peso is not None:
        try:
            eixos = f.get_variation_axes()
            vals = []
            for e in eixos:
                nome = e.get("name", b"")
                nome = nome.decode() if isinstance(nome, bytes) else str(nome)
                if "eight" in nome:
                    vals.append(max(e["minimum"], min(e["maximum"], peso)))
                elif "ptical" in nome:
                    vals.append(max(e["minimum"], min(e["maximum"], corpo / R)))
                else:
                    vals.append(e["default"])
            f.set_variation_by_axes(vals)
        except (OSError, AttributeError, KeyError):
            pass
    return f


def canvas(w, h):
    return Image.new("RGBA", (int(w * R), int(h * R)), (0, 0, 0, 0))


def colocar(dst, src, escala, ponto_src, ponto_dst):
    """cola src (RGBA) em dst, com ponto_src (px de src) caindo em ponto_dst (px de dst, já em R x)"""
    w, h = max(1, round(src.width * escala)), max(1, round(src.height * escala))
    s2 = src.resize((w, h), Image.LANCZOS)
    ox = round(ponto_dst[0] - ponto_src[0] * escala)
    oy = round(ponto_dst[1] - ponto_src[1] * escala)
    x0, y0 = max(0, -ox), max(0, -oy)
    dst.alpha_composite(s2.crop((x0, y0, s2.width, s2.height)), (max(0, ox), max(0, oy)))
    return dst


def borda_papel(img, px, cor=CREME_PAPEL):
    """borda de tesoura: dilata o alfa e pinta de papel por baixo do recorte"""
    a = np.asarray(img.getchannel("A"))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    dil = cv2.GaussianBlur(cv2.dilate(a, k), (0, 0), 0.8)
    base = Image.new("RGBA", img.size, cor + (0,))
    base.putalpha(Image.fromarray(dil))
    base.alpha_composite(img)
    return base


def bbox_alfa(img, lim=8):
    a = np.asarray(img.getchannel("A"))
    ys, xs = np.where(a > lim)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def salvar(nome, img, **medidas):
    img.save(SAI / f"{nome}.png", optimize=True)
    MEDIDAS[nome] = {"px": list(img.size), "planejado": [img.size[0] / R, img.size[1] / R], **medidas}


def cartao_foto(img, larg, alt, margem=(20, 20, 20, 80), escuro=(0.16, 0.13, 0.11), claro=(0.93, 0.89, 0.80),
                papel=(241, 236, 224)):
    """foto P&B tingida e impressa num cartão com margem (esq, topo, dir, base), em px planejados"""
    me, mt, md, mb = margem
    fw, fh = larg - me - md, alt - mt - mb
    g = np.asarray(img.convert("L").resize((fw * R, fh * R), Image.LANCZOS)).astype(np.float32) / 255
    rgb = np.array(escuro) + g[..., None] * (np.array(claro) - np.array(escuro))
    c = Image.new("RGBA", (larg * R, alt * R), papel + (255,))
    c.paste(Image.fromarray((rgb * 255).astype(np.uint8)), (me * R, mt * R))
    return c


def torcao_radial(arr, graus, miolo=0.3):
    """gira a borda de uma peça (RGBA float) mais que o miolo: o "fica para trás e torce" do cérebro"""
    h, w = arr.shape[:2]
    ys, xs = np.where(arr[..., 3] > 30)
    cx, cy = xs.mean(), ys.mean()
    rb = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2).max()
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    dx, dy = gx - cx, gy - cy
    k = np.clip((np.sqrt(dx ** 2 + dy ** 2) / rb - miolo) / (1 - miolo), 0, 1)
    th = np.radians(graus) * k * k * (3 - 2 * k)
    mx = cx + dx * np.cos(-th) - dy * np.sin(-th)
    my = cy + dx * np.sin(-th) + dy * np.cos(-th)
    out = cv2.remap(arr, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return out, (cx, cy, rb)


# ------------------------------------------------------------------ base: fundos, grade e vinheta
def fundo_papel(cor=(222, 219, 203), w=1080, h=1920, semente=3):
    """papel creme com manchas largas e fibra fina (sem textura de terceiros)"""
    rng = np.random.default_rng(semente)
    larga = cv2.resize(rng.standard_normal((h // 120 + 2, w // 120 + 2)).astype(np.float32), (w, h),
                       interpolation=cv2.INTER_CUBIC) * 2.0
    media = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 3) * 3.0
    fina = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 0.8) * 2.2
    a = np.clip(np.array(cor, np.float32) + (larga + media + fina)[..., None], 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def fundo_carvao(cor=(35, 35, 37), w=1080, h=1920, semente=7):
    rng = np.random.default_rng(semente)
    n = cv2.GaussianBlur(rng.standard_normal((h, w)).astype(np.float32), (0, 0), 1.2) * 3.0
    a = np.clip(np.array(cor, np.float32) + n[..., None], 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def grade(nome, cor, alfa, w=2000, h=3000, cel=60):
    """grade em losango (célula em px planejados), só para dar escala ou medida"""
    im = Image.new("RGBA", (w * R, h * R), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = cor + (int(255 * alfa),)
    comp = (w + h) * R
    for k in range(-h * R, w * R + h * R, int(cel * R * math.sqrt(2))):
        d.line([(k, 0), (k + comp, comp)], fill=c, width=2 * R)
        d.line([(k, 0), (k - comp, comp)], fill=c, width=2 * R)
    salvar(nome, im, celula=cel)


def vinheta(w=1080, h=1920):
    gx, gy = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    r = np.sqrt(gx ** 2 + (gy * 0.78) ** 2)
    a = np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6 * 0.75
    im = np.zeros((h, w, 4), np.uint8)
    im[..., :3] = (18, 18, 18)
    im[..., 3] = (a * 255).astype(np.uint8)
    Image.fromarray(im).save(SAI / "vinheta.png", optimize=True)
    MEDIDAS["vinheta"] = {"px": [w, h], "planejado": [w, h]}


def base():
    fundo_papel().save(SAI / "fundo_papel.png", optimize=True)
    fundo_carvao().save(SAI / "fundo_carvao.png", optimize=True)
    grade("grade_papel", (111, 110, 107), 0.42)
    grade("grade_escuro", (76, 76, 76), 0.55)
    vinheta()


# ------------------------------------------------------------------ receitas do exemplo
def pessoa(gerados):
    """pessoa genérica gerada, vista de cima, separada em cabeça e ombros (GrabCut a partir de elipses medidas
    naquela imagem: ajuste centro e semieixos à sua). A cabeça gira em volta do pivô P (base do pescoço)."""
    src = Image.open(gerados / "pessoa_cima_recorte.png").convert("RGBA")
    arr = np.asarray(src).astype(np.float32)
    a = arr[..., 3]
    H, W = a.shape
    ys = np.where(a[:, 950:1150].max(axis=1) > 128)[0]
    nariz_y = ys.min()                                # nariz: o pixel opaco mais alto perto do meio
    P = (1042.0, 1005.0)                              # pivô medido na imagem
    s = 240.0 / (P[1] - nariz_y)                      # nariz 240 px à frente do pivô (planejado)
    mk = np.full((H, W), cv2.GC_BGD, np.uint8)        # o cabelo tem reflexo cinza: não sai por limiar
    mk[a > 30] = cv2.GC_PR_BGD
    cv2.ellipse(mk, (1049, 915), (365, 410), 0, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.ellipse(mk, (1049, 900), (270, 320), 0, 0, 360, cv2.GC_FGD, -1)
    mk[(a > 128) & (np.arange(H)[:, None] < 560)] = cv2.GC_FGD
    mk[(a > 30) & (np.arange(H)[:, None] > 1345)] = cv2.GC_BGD
    mk[a <= 30] = cv2.GC_BGD
    f = 0.5
    pq = cv2.resize(cv2.cvtColor(arr[..., :3].astype(np.uint8), cv2.COLOR_RGB2BGR), None, fx=f, fy=f,
                    interpolation=cv2.INTER_AREA)
    mq = cv2.resize(mk, (pq.shape[1], pq.shape[0]), interpolation=cv2.INTER_NEAREST)
    bgm, fgm = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(pq, mq, None, bgm, fgm, 6, cv2.GC_INIT_WITH_MASK)
    cab = cv2.resize(((mq == cv2.GC_FGD) | (mq == cv2.GC_PR_FGD)).astype(np.uint8), (W, H),
                     interpolation=cv2.INTER_LINEAR)
    orelhas = np.zeros_like(cab)
    cv2.ellipse(orelhas, (699, 996), (42, 78), 0, 0, 360, 1, -1)
    cv2.ellipse(orelhas, (1387, 1000), (42, 76), 0, 0, 360, 1, -1)
    cab = cab | (orelhas & (a > 30).astype(np.uint8))
    cab = cv2.morphologyEx(cab, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    cab = cv2.morphologyEx(cab, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    cnt, _ = cv2.findContours(cab, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cab = np.zeros_like(cab)
    cv2.drawContours(cab, [max(cnt, key=cv2.contourArea)], -1, 1, -1)
    cab &= (a > 20).astype(np.uint8)
    ac = cv2.GaussianBlur((cab * a).astype(np.float32), (0, 0), 1.0)
    cabeca = Image.fromarray(np.dstack([arr[..., :3], np.minimum(ac, a)]).astype(np.uint8))
    # ombros: tira a cabeça e fecha o buraco por dentro do tronco com inpaint
    resto = ((a > 128) & (cab == 0)).astype(np.uint8)
    tronco = np.zeros_like(resto)
    pts = np.argwhere(resto[int(P[1]) - 40:] > 0)[:, ::-1] + [0, int(P[1]) - 40]
    cv2.fillConvexPoly(tronco, cv2.convexHull(pts.astype(np.int32)), 1)
    buraco = (cab & tronco).astype(np.uint8)
    rgb = cv2.inpaint(arr[..., :3].astype(np.uint8), cv2.dilate(buraco, np.ones((7, 7), np.uint8)), 25,
                      cv2.INPAINT_TELEA)
    rgb = np.where(buraco[..., None] > 0, cv2.GaussianBlur(rgb, (0, 0), 6), rgb)
    ao = np.maximum(resto * 255, buraco * 255).astype(np.float32)
    ao = np.where(cab > 0, ao, np.minimum(ao, a))
    n, lb, st, _ = cv2.connectedComponentsWithStats((ao > 40).astype(np.uint8))
    ao = np.where(lb == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA]), ao, 0)
    ombros = Image.fromarray(np.dstack([rgb, ao]).astype(np.uint8))
    salvar("cabeca_cima", borda_papel(colocar(canvas(640, 640), cabeca, s * R, P, (320 * R, 320 * R)), 5 * R),
           pivo="centro", escala_src=round(s, 4), nariz_acima_px=240)
    salvar("ombros_cima", borda_papel(colocar(canvas(900, 380), ombros, s * R, P, (450 * R, 60 * R)), 5 * R),
           pivo_P_no_arquivo=[450, 60])
    return s


def luva(gerados):
    src = Image.open(gerados / "luva_recorte.png").convert("RGBA")
    x0, y0, x1, y1 = bbox_alfa(src, 40)
    s = 820.0 / y1                                    # o fundo da luva no pé do arquivo (y 820)
    salvar("luva", colocar(canvas(300, 820), src, s * R, ((x0 + x1) / 2, y1), (150 * R, 820 * R)), ancora=[150, 670])


def pino(gerados):
    src = Image.open(gerados / "colchete_recorte.png").convert("RGBA")
    x0, y0, x1, y1 = bbox_alfa(src, 40)
    s = 44.0 / (x1 - x0)
    salvar("pino", colocar(canvas(44, 44), src, s * R, ((x0 + x1) / 2, (y0 + y1) / 2), (22 * R, 22 * R)), pivo="centro")


def fita(gerados):
    """uma fita gerada, cortada em 4 comprimentos (25/50/75/100%); a ponteira vai sempre na ponta"""
    src = np.asarray(Image.open(gerados / "fita.png").convert("RGB")).astype(np.float32)
    y0, y1 = 405, 628                                 # a tira, medida na imagem gerada
    tira = src[y0:y1]
    x0cm, pxcm = 155, 105.4                           # 0 cm e px por cm, medidos nas marcas 10/20/30
    ponteira = tira[:, 3895:4040]
    for nome, frac in (("fita_25", .25), ("fita_50", .5), ("fita_75", .75), ("fita_100", 1.0)):
        comp = 12.0 * frac * pxcm                     # 12 cm do pino ao queixo, a 20 px/cm no plano
        peca = np.concatenate([tira[:, x0cm - 8: int(x0cm + comp)], ponteira], axis=1)
        im = Image.fromarray(peca.astype(np.uint8)).convert("RGBA").rotate(90, expand=True)
        s = 240.0 / (12 * pxcm)
        salvar(nome, colocar(canvas(640, 640), im, s * R, (im.width / 2, im.height - 8), (320 * R, 320 * R)),
               pivo="centro = 0 cm sob o pino", px_por_cm=20)


def chave(reais):
    """chave estrela CC0, espelhada para ter duas bocas; o número gravado é coberto com um trecho liso do cabo"""
    src = np.asarray(Image.open(reais / "chave_estrela.png").convert("RGBA")).astype(np.uint8).copy()
    src[290:413, 310:496] = src[290:413, 560:746]
    a = src[..., 3]
    cols = np.where(a[:, 1050:].max(axis=0) > 128)[0] + 1050
    rows = np.where(a[:, 1050:].max(axis=1) > 128)[0]
    cx, cy = (cols.min() + cols.max()) / 2, (rows.min() + rows.max()) / 2
    dupla = np.concatenate([src[:, ::-1], src], axis=1)
    aro1 = (src.shape[1] + cx, cy)
    dist = aro1[0] - (src.shape[1] - cx)
    im = Image.fromarray(dupla).rotate(-90, expand=True, resample=Image.BICUBIC)
    p1 = (dupla.shape[0] - aro1[1], aro1[0])          # depois do giro de -90°: (x, y) -> (H - y, x)
    s = 290.0 / dist
    salvar("chave", colocar(canvas(640, 640), im, s * R, p1, (320 * R, 320 * R)), pivo="centro = aro em volta do pino")


def interior(lizars, s_cabeca):
    """crânio e cérebro separados por separar_lizars.py; P = a linha das orelhas no arquivo de cada um
    (as subtrações são as caixas de recorte que o separar_lizars.py imprime)"""
    anel = Image.open(lizars / "cranio_anel.png")
    cer = Image.open(lizars / "cerebro_cima.png")
    P_anel = (1098 - 294, 1640 - 699)
    P_cer = (1098 - 568, 1640 - 872)
    s = (750 * s_cabeca) / anel.width                  # a mesma largura (com as orelhas) da cabeça da foto
    salvar("cranio_cima", colocar(canvas(640, 640), anel, s * R, P_anel, (320 * R, 320 * R)), pivo="centro")
    c = colocar(canvas(640, 640), cer, s * 0.9 * R, P_cer, (320 * R, 320 * R))   # 10% menor: folga para atrasar
    salvar("cerebro_cima", c, pivo="centro")
    arr = np.asarray(c).astype(np.float32)
    for nome, tmax in (("cerebro_torcido_1", -6.0), ("cerebro_torcido_2", -12.0)):
        out, (cx, cy, rb) = torcao_radial(arr, tmax)
        im = Image.fromarray(out.astype(np.uint8))
        if nome.endswith("2"):                         # fibras finas no vermelho do acento: linhas, nunca manchas
            d = ImageDraw.Draw(im)
            for j in range(8):
                fi = math.radians(-80 + j * 45 + (9 if j % 2 else -7))
                pts = []
                for t in np.linspace(0.32, 0.9, 24):
                    kk = min(max((t - 0.3) / 0.7, 0), 1)
                    ang = fi + math.radians(tmax) * kk * kk * (3 - 2 * kk)
                    rr = t * rb * (0.92 if abs(math.sin(fi)) < 0.5 else 1.0)
                    pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
                d.line(pts, fill=VERMELHO + (230,), width=3 * R, joint="curve")
        salvar(nome, im, pivo="centro", torcao_graus=tmax)


def foto_gancho(reais):
    src = Image.open(reais / "foto_1897.jpg")
    x0, w = 150, 900
    recorte = src.crop((x0, 0, x0 + w, round(w * 640 / 860)))
    salvar("foto_gancho", cartao_foto(recorte, 900, 740), credito="Library of Congress, 1897 (domínio público)")
    salvar("preto_foto", Image.new("RGBA", (860 * R, 640 * R), (17, 17, 17, 255)))


def artigo():
    """cartão da fonte: a CITAÇÃO tipografada (título, autores, revista, ano, doi), nunca a imagem da página"""
    W0, H0 = 860, 600
    f_meta = fonte("Inter[opsz,wght].ttf", 20 * R, 600)
    f_tit = fonte("Fraunces[SOFT,WONK,opsz,wght].ttf", 50 * R, 400)
    f_sub = fonte("Fraunces-Italic[SOFT,WONK,opsz,wght].ttf", 27 * R, 400)
    f_aut = fonte("Inter[opsz,wght].ttf", 22 * R, 600)
    tinta = (41, 41, 43)
    im = Image.new("RGBA", (W0 * R, H0 * R), (244, 240, 232, 255))
    d = ImageDraw.Draw(im)
    m = 56 * R
    d.text((m, 50 * R), "BRAIN  ·  VOL. 97  ·  1974  ·  PP. 633–654", font=f_meta, fill=(110, 108, 104))
    d.line([(m, 92 * R), (W0 * R - m, 92 * R)], fill=(170, 166, 158), width=2 * R)
    y = 128 * R
    for ln in ["Cerebral concussion and", "traumatic unconsciousness"]:
        d.text((m, y), ln, font=f_tit, fill=tinta)
        y += 64 * R
    y += 14 * R
    for ln in ["Correlation of experimental and clinical", "observations of blunt head injuries"]:
        d.text((m, y), ln, font=f_sub, fill=(90, 88, 86))
        y += 36 * R
    d.text((m, y + 30 * R), "A. K. OMMAYA  and  T. A. GENNARELLI", font=f_aut, fill=tinta)
    d.text((m, H0 * R - 70 * R), "doi:10.1093/brain/97.1.633", font=f_meta, fill=(130, 128, 124))
    salvar("artigo_0", im, fonte="doi 10.1093/brain/97.1.633")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["base", "exemplo"])
    ap.add_argument("saida_base", nargs="?", help="pasta das peças (modo base)")
    ap.add_argument("--reais", type=Path, help="fotos e gravuras baixadas (foto_1897.jpg, chave_estrela.png)")
    ap.add_argument("--gerados", type=Path, help="imagens geradas e recortadas (pessoa, luva, colchete, fita)")
    ap.add_argument("--lizars", type=Path, help="saída do separar_lizars.py (cranio_anel.png, cerebro_cima.png)")
    ap.add_argument("--saida", type=Path, help="pasta das peças (modo exemplo)")
    a = ap.parse_args()
    SAI = Path(a.saida_base or a.saida or "pecas")
    SAI.mkdir(parents=True, exist_ok=True)
    if a.modo == "base":
        base()
    else:
        if not (a.reais and a.gerados and a.lizars):
            ap.error("o modo exemplo precisa de --reais, --gerados e --lizars")
        s_cab = pessoa(a.gerados)
        luva(a.gerados); pino(a.gerados); fita(a.gerados); chave(a.reais)
        interior(a.lizars, s_cab)
        foto_gancho(a.reais); artigo()
    (SAI / "medidas.json").write_text(json.dumps(MEDIDAS, ensure_ascii=False, indent=1))
    print(json.dumps({k: v["px"] for k, v in MEDIDAS.items()}, ensure_ascii=False))
