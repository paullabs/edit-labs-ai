"""Os objetos 3D próprios em papel (gravura colorida, borda de tesoura), com cache em <trabalho>/3d/papel_obj.
Renders esperados (blender_giro.py sobre objetos_blender.py e refinaria_blender.py): <trabalho>/3d/<pasta>/<camada>/.
Peças:
moeda, maço de dinheiro, petroleiro em corte (camadas registradas) e a maquete da refinaria (camadas registradas).
Também monta torres (moedas e maços empilhados) como camadas que caem uma a uma."""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "exemplos"))
import _caminhos as CM
AQUI = CM.TRABALHO                                                # pasta de trabalho do projeto (fora do plugin)
sys.path.insert(0, str(CM.MOTOR))
import camadas as K
import cena as C
import motor as M

D3 = AQUI / "3d"
P = D3 / "papel_obj"
BORDA = 8
# quanto cada peça sobe na tela por unidade empilhada (px do render): espessura × cos(elevação) × px/m
DY_MOEDA = 0.16 * math.cos(math.radians(38)) * 229.5 + 1.5
DY_MACO = 0.26 * math.cos(math.radians(32)) * 434.3 + 2.0


def _papel(pasta, nome, semente, cor=0.9, registrado=True):
    P.mkdir(parents=True, exist_ok=True)
    arq = P / f"{pasta}_{nome}.png"
    if not arq.exists():
        im = K.papelizar(D3 / pasta / nome / "cor_v_000.png", luz=D3 / pasta / nome / "luz_v_000.png", registrado=registrado,
                         borda=BORDA, semente=semente, cor=cor, contraste=1.3)
        tmp = arq.with_suffix(".tmp.png")
        im.save(tmp)
        os.replace(tmp, arq)
    return Image.open(arq).convert("RGBA")


def moeda():
    im = _papel("v_moeda", "moeda", 11, cor=1.0)
    return K.cortar_alfa(im, margem=2)[0]


def maco():
    im = _papel("v_maco", "maco", 12, cor=1.0)
    return K.cortar_alfa(im, margem=2)[0]


def registradas(pasta, nomes, semente0, cor=0.9):
    """camadas da mesma câmera, cortadas na MESMA caixa (a união): {nome: peça}, todas do mesmo tamanho"""
    ims = {n: _papel(pasta, n, semente0 + i, cor=cor) for i, n in enumerate(nomes)}
    caixas = [im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox() for im in ims.values()]
    x0 = max(min(c[0] for c in caixas) - 6, 0)
    y0 = max(min(c[1] for c in caixas) - 6, 0)
    x1 = max(c[2] for c in caixas) + 6
    y1 = max(c[3] for c in caixas) + 6
    return {n: im.crop((x0, y0, x1, y1)) for n, im in ims.items()}


def navio():
    return registradas("v_navio", ["corte", "tanques", "diesel", "fora", "ponte"], 20)


def refinaria():
    return registradas("v_ref", ["base", "trem1", "trem2", "andaime", "frente"], 30, cor=0.85)


def junta(ims, nomes):
    """camadas registradas compostas numa peça só (a ordem de nomes é a de empilhar)"""
    out = Image.new("RGBA", ims[nomes[0]].size, (0, 0, 0, 0))
    for n in nomes:
        out.alpha_composite(ims[n])
    return out


def tinge(im, cor, forca=0.85):
    """recolore uma camada (o diesel amarelo vira óleo cru escuro), mantendo o pontilhado e a borda"""
    a = np.asarray(im).astype(np.float32)
    lum = a[..., :3].mean(axis=2, keepdims=True) / 255
    alvo = np.array(cor, np.float32)[None, None, :] * (0.55 + 0.6 * lum)
    a[..., :3] = a[..., :3] * (1 - forca) + alvo * forca
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def enche(img, q0, q1, de=0.0, ate=1.0, curva="out", sete=True, onda=6.0):
    """fonte: a camada aparece de baixo para cima (um líquido enchendo, uma obra subindo) da fração 'de' até 'ate' da
    altura do que tem nela; a borda de cima tem uma ondinha"""
    a0 = np.asarray(img.convert("RGBA")).astype(np.float32) / 255
    h, w = a0.shape[:2]
    lin = np.where(a0[..., 3].max(axis=1) > 0.05)[0]
    ytop, ybot = (lin.min(), lin.max()) if len(lin) else (0, h)
    xs = np.arange(w)
    cache = {}

    def fonte(fd, p):
        t = min(max((fd - q0) / max(q1 - q0, 1), 0), 1)
        if sete and t < 1:
            n = max((q1 - q0) / K.PASSO_7, 1)
            t = math.floor(t * n) / n
        f = de + (ate - de) * M.curva(curva, t)
        chave = round(f, 3)
        if chave not in cache:
            nivel = ybot - (ybot - ytop) * f + onda * np.sin(xs / 37.0 + fd * 0.0)
            m = (np.arange(h)[:, None] >= nivel[None, :]).astype(np.float32)
            o = a0.copy()
            o[..., 3] *= m
            cache[chave] = Image.fromarray((o * 255).astype(np.uint8))
        return cache[chave]
    fonte.tam = (w, h)
    return fonte


def torre(nome, sprite, n, base, q0, passo, dy, esc=1.0, jitter=6.0, rot=2.0, semente=3, de_y=-260, fim=10 ** 6,
          sombra=(8, 16, 0.28)):
    """n peças empilhadas de baixo para cima a partir de 'base' (x, y do centro da peça de baixo), uma a cada 'passo'
    quadros, cada uma caindo de 'de_y'"""
    rng = np.random.default_rng(semente)
    out = []
    for i in range(n):
        x = base[0] + rng.uniform(-jitter, jitter) * esc
        y = base[1] - i * dy * esc
        out.append(C.cai(f"{nome}_{i}", sprite, q0 + i * passo, x, y, rot=rng.uniform(-rot, rot), de_y=de_y, esc=esc,
                         sombra=sombra if i == 0 else (3, 6, 0.22), fim=fim))
    return out


if __name__ == "__main__":
    import pecas as PC
    pecas = [("moeda", moeda()), ("maco", maco())]
    nv = navio()
    pecas += [("navio_fora", junta(nv, ["fora", "ponte"])), ("navio_corte", junta(nv, ["corte", "tanques", "diesel", "ponte"]))]
    rf = refinaria()
    pecas += [("ref", junta(rf, ["base", "trem1", "trem2", "frente"])), ("ref_obra", junta(rf, ["base", "trem1", "andaime", "frente"]))]
    for n, im in pecas:
        print(n, im.size)
    PC.folha(pecas, AQUI / "previa" / "folha_3d.jpg")
