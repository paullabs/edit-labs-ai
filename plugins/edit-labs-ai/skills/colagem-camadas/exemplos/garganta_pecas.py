"""As camadas da garganta (3D do atlas, garganta_render.py) em gravura de papel, registradas pixel a pixel, em patamares de
escala (base, meio, peito, alto). Todas ficam no MESMO mundo: o px do patamar 'base' (3720 px/m) mais a margem do papel.

    MUNDO(y, z)                   (y, z) do atlas em metros → (x, y) do mundo
    camada(patamar, nome)         PIL RGBA da camada papelizada (cache em <trabalho>/espirro/garganta/papel/)
    cama(patamar)                 o fundo escuro (papel) com a forma do corpo (furos fechados)
    centro(patamar), esc(patamar) onde o centro da imagem do patamar cai no mundo e a escala (esc) que casa a densidade

O rosto fica à direita (o corte sagital visto do lado direito do corpo). Os renders vêm de preparar.py espirro.
O ouvido é opcional (tem_ouvido()): ver ouvido_blender.py."""
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import camadas as K, pecas as PC
from garganta_render import PATAMARES, GAR
PAPEL = GAR / "papel"
PAD = 14                                                  # a margem que o papelizar acrescenta (borda 10 + 4)
SEMENTES = {"pele": 11, "musc": 12, "faringe": 13, "osso": 14, "pulm": 15, "bronq": 16, "via": 17}
PXM_BASE = PATAMARES["base"][4]


def _tam(patamar):
    yc, zc, W, H, pxm, _ = PATAMARES[patamar]
    return round(pxm * W * 1.04), round(pxm * H * 1.04)


def MUNDO(y, z):
    """(y, z) do atlas → px do mundo (= px da imagem do patamar base, já com a margem do papel)"""
    yc, zc, W, H, pxm, _ = PATAMARES["base"]
    rx, ry = _tam("base")
    return rx / 2 + (yc - y) * pxm + PAD, ry / 2 - (z - zc) * pxm + PAD


def centro(patamar):
    yc, zc = PATAMARES[patamar][:2]
    return MUNDO(yc, zc)


def esc(patamar):
    """a imagem do patamar entra no mundo com este fator (a densidade do papel fica igual à do base)"""
    return PXM_BASE / PATAMARES[patamar][4]


def _cache(nome, faz):
    PAPEL.mkdir(parents=True, exist_ok=True)
    out = PAPEL / f"{nome}.png"
    if not out.exists():
        im = faz()
        tmp = out.with_suffix(".tmp.png")
        im.save(tmp)
        tmp.replace(out)
    return Image.open(out).convert("RGBA")


def _fecha_furos(alfa):
    """alfa do corpo sem furos (o ombro sem o braço deixava a janela transparente): só o contorno de fora"""
    al = (alfa > 128).astype(np.uint8)
    cont, _ = cv2.findContours(al, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cheio = np.zeros_like(al)
    cv2.drawContours(cheio, cont, -1, 1, -1)
    return cheio


def _render(patamar, nome):
    d = GAR / f"vistas_{patamar}" / nome
    cor = Image.open(d / "cor_v_000.png").convert("RGBA")
    luz = Image.open(d / "luz_v_000.png").convert("RGB")
    return cor, luz


def camada(patamar, nome):
    def faz():
        cor, luz = _render(patamar, nome)
        if nome == "pele":                                   # fecha o furo do ombro: pinta por dentro com a pele em volta
            a = np.asarray(cor).copy()
            l = np.asarray(luz).copy()
            cheio = _fecha_furos(a[..., 3])
            furo = ((cheio > 0) & (a[..., 3] < 128)).astype(np.uint8)
            furo = cv2.morphologyEx(furo, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
            furo = cv2.dilate(furo, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))).astype(bool)     # leva junto a borda do remendo
            furo &= cheio > 0
            h, w = furo.shape
            k = 8
            peq = (w // k, h // k)
            m = cv2.dilate(cv2.resize(furo.astype(np.uint8) * 255, peq, interpolation=cv2.INTER_NEAREST), np.ones((5, 5), np.uint8))
            for arr in (a, l):
                base = cv2.resize(np.ascontiguousarray(arr[..., :3]), peq, interpolation=cv2.INTER_AREA)
                dentro = cv2.inpaint(base, m, 9, cv2.INPAINT_TELEA)
                dentro = cv2.GaussianBlur(cv2.resize(dentro, (w, h), interpolation=cv2.INTER_CUBIC), (0, 0), 6)
                arr[furo, :3] = dentro[furo]
            a[furo, 3] = 255
            cor, luz = Image.fromarray(a), Image.fromarray(l)
        return K.papelizar(cor, luz=luz, registrado=True, semente=SEMENTES[nome], cor=1.0, borda=10, contraste=1.6)
    return _cache(f"{patamar}_{nome}", faz)


def cama(patamar):
    def faz():
        cor, _ = _render(patamar, "pele")
        cheio = _fecha_furos(np.asarray(cor)[..., 3])
        cheio = cv2.erode(cheio, np.ones((5, 5), np.uint8))
        w, h = cor.size
        papel = PC.textura_papel(w + 2 * PAD, h + 2 * PAD, (66, 33, 29), 61).convert("RGBA")
        m = np.pad(cheio, PAD)
        papel.putalpha(Image.fromarray((cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2) * 255).astype(np.uint8)))
        return papel
    return _cache(f"{patamar}_cama", faz)


def suaviza_bordas(im, px=70):
    """a imagem do patamar some devagar perto das bordas do quadro: sem a quina reta aparecendo quando a câmera abre e o patamar de baixo
    (outra densidade) fica em volta"""
    a = np.asarray(im.convert("RGBA")).astype(np.float32)
    h, w = a.shape[:2]
    rx = np.clip(np.minimum(np.arange(w), w - 1 - np.arange(w)) / px, 0, 1)
    ry = np.clip(np.minimum(np.arange(h), h - 1 - np.arange(h)) / px, 0, 1)
    a[..., 3] *= (ry[:, None] * rx[None, :]) ** 0.8
    return Image.fromarray(a.astype(np.uint8))


# ---------------------------------------------------------------- o ouvido (vista de lado, 28000 px/m): ouvido_blender.py
OUV = {"pxm": 28000, "res": (2184, 2621)}


def tem_ouvido():
    """o ouvido só existe se você o montou (ouvido_blender.py + preparar.py espirro); sem ele, a cena pula o ouvido"""
    return (GAR / "vistas_ouvido" / "vistas.json").exists()


def ouvido(nome):
    """pele (o pavilhão), membr, ossic, coclea, cama (a forma do osso temporal em papel escuro): PIL RGBA com a margem do papel"""
    def faz():
        d = GAR / "vistas_ouvido"
        if nome == "cama":
            cor = Image.open(d / "osso" / "cor_v_000.png").convert("RGBA")
            cheio = _fecha_furos(np.asarray(cor)[..., 3])
            w, h = cor.size
            papel = PC.textura_papel(w + 2 * PAD, h + 2 * PAD, (66, 33, 29), 61).convert("RGBA")
            papel.putalpha(Image.fromarray((cv2.GaussianBlur(np.pad(cheio, PAD).astype(np.float32), (0, 0), 1.2) * 255).astype(np.uint8)))
            return papel
        cor = Image.open(d / nome / "cor_v_000.png").convert("RGBA")
        luz = Image.open(d / nome / "luz_v_000.png").convert("RGB")
        return K.papelizar(cor, luz=luz, registrado=True, semente=30 + len(nome), cor=1.0, borda=10, contraste=1.6)
    return _cache(f"ouvido_{nome}", faz)


def esc_ouvido():
    return PXM_BASE / OUV["pxm"]


if __name__ == "__main__":
    import time
    for p in sys.argv[1:] or ["base"]:
        for n in PATAMARES[p][5] + ["cama"]:
            t = time.time()
            im = cama(p) if n == "cama" else camada(p, n)
            print(p, n, im.size, f"{time.time() - t:.1f}s")
