"""Mapa de papel com ALFINETES e PAINÉIS (a mecânica do exemplo cena_mapa.py, para qualquer mapa).

Países recortados dos contornos do Natural Earth (domínio público; dados/mapa/ne_110m_admin_0_countries.geojson, ver
dados/mapa/CREDITOS.md), cada um com projeção local (equirretangular com o x corrigido pelo cosseno da latitude do
centro), em papel colorido com borda de tesoura, sobre uma folha de oceano.

    Pais(nome_geojson, px_por_grau, centro_no_mundo, lat_centro, cor, filtro)   o país em papel; .mundo_xy(lon, lat)
    pinta_oceano(fundo, regiao)            a folha azul do oceano (borda esquerda rasgada, grade fraca) no papel do mundo
    alfinete(texto)                        alfinete de papel com número ou sigla
    rotulo(linhas) / valor(texto)          etiqueta em caixa alta / número em carimbo vermelho numa tira de papel
    painel(...) + brota(...) + encolhe(...) a folha do assunto nasce do alfinete, mostra UMA coisa e volta para ele
    lider(...) / rota(...)                 a linha de tinta do alfinete ao painel / a rota tracejada entre lugares
    distancia_km(a, b)                     distância de círculo máximo entre dois (lon, lat): números calculados, não inventados

Regras do sistema (o mapa nunca acumula etiquetas): cada lugar tem um alfinete; o assunto aparece num painel que brota
dele num canto vazio (o oceano); quando a câmera segue, o painel encolhe de volta; entre lugares, a câmera vai devagar
ou por transição de zoom, nunca correndo pelo mapa."""
import json
import math
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
import motor as M, pecas as PC, cena as C

GEO = Path(__file__).resolve().parent / "dados" / "mapa" / "ne_110m_admin_0_countries.geojson"
TINTA = PC.TINTA
OCEANO = (86, 128, 170)
CREME = (240, 233, 214)


def _partes(nome, filtro):
    d = json.loads(GEO.read_text())
    for f in d["features"]:
        if f["properties"].get("ADMIN") != nome:
            continue
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        out = []
        for poly in polys:
            anel = poly[0]
            mlon = sum(p[0] for p in anel) / len(anel)
            mlat = sum(p[1] for p in anel) / len(anel)
            if filtro(mlon, mlat):
                out.append(anel)
        return out
    raise KeyError(f"país '{nome}' não está no geojson (use o nome do campo ADMIN)")


class Pais:
    def __init__(self, nome, s, centro, lat0, cor, filtro=lambda lon, lat: True, semente=5):
        self.nome, self.s, self.lat0, self.cor = nome, s, lat0, cor
        self.partes = _partes(nome, filtro)
        lons = [p[0] for a in self.partes for p in a]
        lats = [p[1] for a in self.partes for p in a]
        self.lon0, self.lon1, self.lat1, self.lat_b = min(lons), max(lons), max(lats), min(lats)
        self.k = math.cos(math.radians(lat0))
        self.w = int((self.lon1 - self.lon0) * s * self.k) + 1
        self.h = int((self.lat1 - self.lat_b) * s) + 1
        self.centro = centro
        self.img = self._papel(semente)

    def px(self, lon, lat):
        """lon/lat -> px dentro do recorte (antes da borda)"""
        return ((lon - self.lon0) * self.s * self.k, (self.lat1 - lat) * self.s)

    def _papel(self, semente):
        S = 3
        m = Image.new("L", (self.w * S, self.h * S), 0)
        d = ImageDraw.Draw(m)
        for anel in self.partes:
            d.polygon([(x * S, y * S) for x, y in (self.px(lon, lat) for lon, lat in anel)], fill=255)
        m = m.resize((self.w, self.h), Image.LANCZOS)
        al = np.asarray(m)
        tex = np.asarray(PC.textura_papel(self.w, self.h, self.cor, semente).convert("RGB")).astype(np.float32)
        rng = np.random.default_rng(semente)                              # relevo leve: aguada, para não ficar chapado
        man = cv2.GaussianBlur(rng.random((self.h // 16 + 2, self.w // 16 + 2)).astype(np.float32), (0, 0), 1.2)
        man = cv2.resize(man, (self.w, self.h))
        tex *= (0.9 + 0.12 * man[..., None])
        borda = cv2.morphologyEx((al > 127).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((5, 5), np.uint8)).astype(np.float32)
        borda = cv2.GaussianBlur(borda, (0, 0), 0.7)
        rgb = tex * (1 - borda[..., None] * 0.85) + np.array(TINTA, np.float32) * borda[..., None] * 0.85
        im = Image.fromarray(np.dstack([rgb.clip(0, 255), al]).astype(np.uint8))
        out = PC.recorte(im, borda=12, envelhece=False, semente=semente)
        # PC.recorte corta no contorno: o px do recorte ganha (borda + 4) em cada lado; a caixa do alfa começa em 0
        caixa = im.getchannel("A").getbbox()
        self.pad = 16 - caixa[0]
        self._pady = 16 - caixa[1]
        return out

    def mundo_xy(self, lon, lat):
        x, y = self.px(lon, lat)
        return (self.centro[0] - self.img.width / 2 + self.pad + x, self.centro[1] - self.img.height / 2 + self._pady + y)

    def camada(self, nome=None, ini=0):
        return C.fixo(nome or f"PAIS_{self.nome}", self.img, self.centro[0], self.centro[1], ini=ini, boil=None,
                      sombra=(10, 24, 0.3))


def distancia_km(a, b):
    """distância de círculo máximo entre (lon, lat) e (lon, lat), em km (Terra de raio médio 6371 km)"""
    l1, f1, l2, f2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin((l2 - l1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def km_texto(km, passo=10):
    """1934,2 → '1.930 KM' (arredondado: o número na tela não finge precisão)"""
    return f"{int(round(km / passo) * passo):,} KM".replace(",", ".")


def pinta_oceano(fundo, regiao):
    """pinta a folha do oceano (papel azul, borda esquerda rasgada, grade em losango bem fraca) no papel do mundo"""
    x0, y0, x1, y1 = regiao
    w, h = x1 - x0, y1 - y0
    mar = PC.textura_papel(w, h, OCEANO, 77).convert("RGBA")
    a = np.asarray(mar).astype(np.float32)
    yy = np.linspace(0, 1, h)[:, None]
    a[..., :3] *= (1.0 - 0.10 * yy)[..., None]                        # mais fundo embaixo
    mar = Image.fromarray(a.astype(np.uint8))
    mar.alpha_composite(PC.grade(w, h, passo=150, cor=(232, 240, 244), op=0.10))
    al = np.full((h, w), 255, np.uint8)
    rng = np.random.default_rng(78)
    r = np.cumsum(rng.normal(0, 1.4, h))
    r = (r - r.mean()) / max(np.abs(r).max(), 1e-6) * 30 + 30
    for y in range(h):
        al[y, :int(r[y])] = 0
    fundo.paste(mar.convert("RGB"), (x0, y0), Image.fromarray(al))
    return fundo


def alfinete(texto, cor=PC.VERMELHO, tam=120):
    """alfinete de mapa: disco de papel com número ou sigla em caixa alta e a ponta (a ponta fica embaixo, no centro)"""
    S = 3
    T = tam * S
    im = Image.new("RGBA", (T, int(T * 1.45)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(T * 0.28, T * 0.7), (T * 0.72, T * 0.7), (T * 0.5, T * 1.42)], fill=cor + (255,))
    d.ellipse([0, 0, T - 1, T - 1], fill=cor + (255,))
    d.ellipse([T * 0.12, T * 0.12, T * 0.88, T * 0.88], fill=(246, 240, 226, 255))
    fo = PC.fonte("ArchivoBlack-Regular.ttf", int(T * (0.5 if len(texto) <= 2 else 0.32)))
    d.text((T / 2, T / 2 + T * 0.02), texto, font=fo, fill=TINTA + (255,), anchor="mm")
    im = im.resize((tam, int(tam * 1.45)), Image.LANCZOS)
    out = PC.recorte(im, borda=6, envelhece=False, semente=len(texto) + 3)
    out.info["texto_px"] = int(tam * (0.5 if len(texto) <= 2 else 0.32))
    out.info["texto_min"] = 40
    return out


def rotulo(linhas, semente=4, corpo=(48, 30), fundo=(246, 240, 226), cor=TINTA):
    """etiqueta do estilo: nome em caixa alta, pesado e curto; a 2ª linha (opcional) menor"""
    return PC.etiqueta(linhas, corpo=corpo[:len(linhas)], semente=semente, fundo=fundo, cor=cor)


def valor(texto, semente=6, corpo=64, cor=PC.VERMELHO):
    """o número que importa: carimbo vermelho numa tira de papel claro"""
    car = PC.carimbo(texto, corpo=corpo, semente=semente, cor=cor)
    pap = PC.textura_papel(car.width + 10, car.height + 4, (246, 240, 226), semente)
    pap = PC.rasgar(pap.convert("RGBA"), amp=4, passo=14, semente=semente)
    pap.alpha_composite(car, (5, 2))
    pap.info["texto_px"] = corpo
    pap.info["texto_min"] = 54
    return pap


# ---------------------------------------------------------------- o painel que brota do alfinete
def painel(nome, cx, cy, w, h, q0, cor=CREME, semente=5):
    """a folha do painel (papel com borda rasgada e sombra)"""
    pg = PC.rasgar(PC.textura_papel(int(w), int(h), cor, semente).convert("RGBA"), amp=18, passo=34, semente=semente)
    return C.fixo(nome, pg, cx, cy, ini=q0, sombra=(14, 34, 0.38), boil=None)


def brota(camadas, q0, q1, origem, centro):
    """o painel nasce do alfinete: cada camada vem de origem + (pos − centro)·0,05 (e escala 0,05) até o lugar dela"""
    q1 = max(q1, q0 + 14)
    for L in camadas:
        x1 = M.valor(L.chaves.get("x"), q1, 0)
        y1 = M.valor(L.chaves.get("y"), q1, 0)
        s1 = M.valor(L.chaves.get("s"), q1, 1.0)
        f = 0.05
        for ch, a, b in (("x", origem[0] + (x1 - centro[0]) * f, x1), ("y", origem[1] + (y1 - centro[1]) * f, y1),
                         ("s", s1 * f, s1)):
            depois = [c for c in L.chaves.get(ch, []) if c[0] > q1]
            L.chaves[ch] = [(q0, a, "out"), (q1, b, "segura")] + depois
        L.ini = min(L.ini, q0)
    return camadas


def encolhe(camadas, q0, q1, alvo, centro, f=0.04):
    """o painel volta para o alfinete: tudo escala em volta do centro do grupo até 'alvo' e some"""
    q0 = min(q0, q1 - 14)
    for L in camadas:
        x0 = M.valor(L.chaves.get("x"), q0, 0)
        y0 = M.valor(L.chaves.get("y"), q0, 0)
        s0 = M.valor(L.chaves.get("s"), q0, 1.0)
        for ch, a, b in (("x", x0, alvo[0] + (x0 - centro[0]) * f), ("y", y0, alvo[1] + (y0 - centro[1]) * f),
                         ("s", s0, s0 * f)):
            L.chaves[ch] = [c for c in L.chaves.get(ch, [(0, a, "segura")]) if c[0] < q0] + [(q0, a, "in"), (q1, b, "segura")]
        L.fim = min(L.fim, q1 + 1)
    return camadas


def lider(nome, de, para, q0, fim=10 ** 6):
    """linha de tinta do alfinete ao painel"""
    return C.Traco(nome, [de, ((de[0] + para[0]) / 2, min(de[1], para[1]) - 80), para], q0, q0 + 6, espessura=12, cor=TINTA,
                   curva="out", tremor=1.0, fim=fim, suave=True).camada


def rota(nome, pts, q0, q1, cor=TINTA, esp=12, fim=10 ** 6):
    """rota tracejada que se desenha de q0 a q1 (o objeto C.Traco: .camada, .ponta(f))"""
    return C.Traco(nome, pts, q0, q1, espessura=esp, cor=cor, tracejado=(34, 22), curva="io", suave=True, fim=fim, tremor=1.0)
