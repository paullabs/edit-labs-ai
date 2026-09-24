#!/usr/bin/env python3
"""
Insumo do laudo D1: o Diretor responde os itens OLHANDO estes arquivos, citando cada um pelo nome.

    python3 checar_asset.py NOME [NOME ...]      # procura 07_assets/cutout/NOME.png (ou raw/)

Grava em 07_assets/qa/:
    NOME_tiles.png    4 tiles a 100 % (2x2) — texto de IA, "1993" de 8 px, halo e sombra somem reduzidos
    NOME_bordas.png   4 recortes de borda a 200 % — a borda e a materia nesta identidade (fibra, metal fosco)
    NOME_alfa.png     o canal alfa em preto e branco
    NOME_preto.png / NOME_branco.png   o recorte sobre preto e sobre branco (halo aparece)
    NOME_qa.json      saturacao media, percentil 5 de luminancia, alfa medio no anel de 3 px, lado maior
Sem limiar de aprovacao: aqui so se mede. Python 3.9.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path.cwd()
QA = ROOT / "07_assets" / "qa"


def achar(nome: str) -> Path:
    for d in ("cutout", "raw"):
        p = ROOT / "07_assets" / d / (nome if nome.endswith(".png") else f"{nome}.png")
        if p.exists():
            return p
    raise SystemExit(f"nao achei {nome} em 07_assets/cutout nem raw")


def medir(im: Image.Image) -> dict:
    rgba = np.asarray(im.convert("RGBA")).astype(np.float32)
    a = rgba[..., 3]
    vis = a > 128
    rgb = rgba[..., :3].astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    lum = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    ker = np.ones((3, 3), np.uint8)
    borda = (vis.astype(np.uint8) - cv2.erode(vis.astype(np.uint8), ker, iterations=3)).astype(bool)
    return {"lado_maior": int(max(im.size)), "saturacao_media": round(float(hsv[..., 1][vis].mean()) if vis.any() else 0, 1),
            "pretos_p5": round(float(np.percentile(lum[vis], 5)) if vis.any() else 0, 1),
            "alfa_medio_anel_3px": round(float(a[borda].mean()) if borda.any() else 0, 1),
            "cobertura_alfa": round(float(vis.mean()), 3)}


def checar(nome: str) -> dict:
    p = achar(nome)
    im = Image.open(p).convert("RGBA")
    QA.mkdir(parents=True, exist_ok=True)
    base = p.stem
    w, h = im.size
    t = min(w, h) // 2
    tiles = [im.crop((0, 0, t, t)), im.crop((w - t, 0, w, t)), im.crop((0, h - t, t, h)), im.crop((w - t, h - t, w, h))]
    sheet = Image.new("RGBA", (2 * t, 2 * t), (138, 138, 138, 255))
    for k, tl in enumerate(tiles):
        sheet.alpha_composite(tl, ((k % 2) * t, (k // 2) * t))
    sheet.save(QA / f"{base}_tiles.png")
    bb = im.getbbox() or (0, 0, w, h)
    s = max(32, min(w, h) // 8)
    cx, cy = (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2
    cortes = [(bb[0], cy - s // 2), (bb[2] - s, cy - s // 2), (cx - s // 2, bb[1]), (cx - s // 2, bb[3] - s)]
    bord = Image.new("RGBA", (4 * 2 * s, 2 * s), (255, 255, 255, 255))
    for k, (x, y) in enumerate(cortes):
        c = im.crop((x, y, x + s, y + s)).resize((2 * s, 2 * s), Image.NEAREST)
        bord.alpha_composite(c, (k * 2 * s, 0))
    bord.save(QA / f"{base}_bordas.png")
    im.getchannel("A").save(QA / f"{base}_alfa.png")
    for cor, nomecor in (((0, 0, 0, 255), "preto"), ((255, 255, 255, 255), "branco")):
        fundo = Image.new("RGBA", im.size, cor)
        fundo.alpha_composite(im)
        fundo.convert("RGB").save(QA / f"{base}_{nomecor}.png")
    m = medir(im)
    m["arquivos"] = [f"{base}_{x}.png" for x in ("tiles", "bordas", "alfa", "preto", "branco")]
    (QA / f"{base}_qa.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {base}: lado {m['lado_maior']} px · saturacao {m['saturacao_media']} · pretos p5 {m['pretos_p5']} · "
          f"alfa no anel {m['alfa_medio_anel_3px']} -> 07_assets/qa/{base}_*")
    return m


if __name__ == "__main__":
    for n in sys.argv[1:]:
        checar(n)
