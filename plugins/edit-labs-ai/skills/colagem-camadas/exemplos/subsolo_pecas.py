"""O bloco do subsolo em papel (exemplo cena_subsolo.py): as 8 camadas do modelo próprio (modelos/presal_blender.py),
renderizadas pela mesma câmera (<trabalho>/subsolo/vistas), viram peças de gravura colorida registradas pixel a pixel
(cache em <trabalho>/subsolo/papel). marcos() devolve onde cada ponto do modelo cai na imagem (px).

Antes: preparar.py subsolo.

    clpy subsolo_pecas.py      papeliza as camadas e grava previa/subsolo_bloco.jpg (o bloco montado, para conferir)"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM
import camadas as K

V = CM.TRABALHO / "subsolo" / "vistas"
P = CM.TRABALHO / "subsolo" / "papel"
ORDEM = ["emb", "pre", "oleo", "sal", "pos3", "pos2", "pos1", "agua"]          # de baixo para cima (ordem de empilhar)
COR = {"agua": 1.0, "sal": 0.9, "oleo": 1.0}
BORDA = 9


def camada(nome):
    CM.exige(V / "vistas.json", como="clpy preparar.py subsolo")
    P.mkdir(parents=True, exist_ok=True)
    arq = P / f"{nome}.png"
    if not arq.exists():
        im = K.papelizar(V / nome / "cor_v_000.png", luz=V / nome / "luz_v_000.png", registrado=True, borda=BORDA,
                         semente=ORDEM.index(nome) + 3, cor=COR.get(nome, 0.85), contraste=1.3)
        if nome == "sal":                                      # o sal é branco: o pontilhado sépia o deixava cinza
            a = np.asarray(im).astype(np.float32)
            a[..., :3] = 255 - (255 - a[..., :3]) * 0.5
            im = Image.fromarray(a.astype(np.uint8))
        tmp = arq.with_suffix(".tmp.png")
        im.save(tmp)
        os.replace(tmp, arq)                                   # gravação atômica (dois renders no mesmo cache)
    return Image.open(arq).convert("RGBA")


def pecas_bloco():
    """cada camada recortada no próprio contorno: {nome: (peça, (cx, cy))}, com (cx, cy) = centro da peça em px da
    imagem registrada (para pôr no mundo: origem + (cx, cy))"""
    out = {}
    for n in ORDEM:
        im = camada(n)
        peca, (dx, dy) = K.cortar_alfa(im, margem=4)
        out[n] = (peca, (im.width / 2 + dx, im.height / 2 + dy))
    return out


def marcos():
    """px na imagem PAPELIZADA (a borda de tesoura soma BORDA + 4 px em cada lado) e px por km"""
    d = json.loads((V / "vistas.json").read_text())
    pad = BORDA + 4
    return {k: (v[0] + pad, v[1] + pad) for k, v in d["marcos"].items()}, d["px_por_m"] / 1000.0


if __name__ == "__main__":
    import time
    t = time.time()
    ims = {n: camada(n) for n in ORDEM}
    print("papelizado em", round(time.time() - t, 1), "s", ims["agua"].size)
    base = Image.new("RGBA", ims["agua"].size, (233, 221, 192, 255))
    for n in ORDEM:
        base.alpha_composite(ims[n])
    (CM.PREVIA).mkdir(parents=True, exist_ok=True)
    base.convert("RGB").resize((base.width // 3, base.height // 3), Image.LANCZOS).save(CM.PREVIA / "subsolo_bloco.jpg",
                                                                                       quality=90)
    print(marcos())
