#!/usr/bin/env python3
"""
Prancha de contato: uma linha por cena, os 4 estados a 300 px de largura, + M#_estados.jpg por
cena e REVISAR.html (um clique por cena), para o usuário revisar.

    python3 prancha.py            # quadro do processo (MV_CANVAS=V|H)
    python3 prancha.py --ambos    # V e H lado a lado na mesma linha, quando os dois existem

Le 08_images/frames/M#{,_H}_{START,MID,END,EXIT}.png (gerados por `compose.py`). Python 3.9.
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import voxlab as V

ROOT = Path.cwd()
F = ROOT / "08_images" / "frames"
ESTADOS = ["START", "MID", "END", "EXIT"]
LARG = 300


def _cenas(tag):
    nomes = set()
    for p in F.glob(f"M*{tag}_START.png"):
        m = re.match(rf"(M\d+[A-Za-z]?){re.escape(tag)}_START\.png$", p.name)
        if m:
            nomes.add(m.group(1))
    return sorted(nomes, key=lambda n: (int(re.sub(r"\D", "", n) or 0), n))


def _mini(p, larg=LARG):
    im = Image.open(p).convert("RGB")
    return im.resize((larg, int(im.height * larg / im.width)), Image.LANCZOS)


def linha(nome, tags):
    tiles = []
    for tag in tags:
        for st in ESTADOS:
            p = F / f"{nome}{tag}_{st}.png"
            if p.exists():
                tiles.append((f"{nome}{tag} {st}", _mini(p)))
    if not tiles:
        return None
    h = max(t.height for _, t in tiles) + 26
    w = sum(t.width for _, t in tiles) + 10 * (len(tiles) + 1)
    im = Image.new("RGB", (w, h), (236, 234, 228))
    d = ImageDraw.Draw(im)
    x = 10
    for rot, t in tiles:
        im.paste(t, (x, 22))
        d.text((x + 2, 4), rot, fill=(40, 40, 40))
        x += t.width + 10
    im.save(F.parent / f"{nome}_estados.jpg", quality=88)
    return im


def main():
    ambos = "--ambos" in sys.argv
    tags = ["", "_H"] if ambos else (["_H"] if V.ORIENT == "H" else [""])
    nomes = sorted(set(_cenas(tags[0]) + (_cenas(tags[1]) if len(tags) > 1 else [])),
                   key=lambda n: (int(re.sub(r"\D", "", n) or 0), n))
    linhas = [(n, linha(n, tags)) for n in nomes]
    linhas = [(n, im) for n, im in linhas if im]
    if not linhas:
        raise SystemExit("nenhum estado em 08_images/frames/ (rode compose.py primeiro)")
    W = max(im.width for _, im in linhas)
    Hh = sum(im.height for _, im in linhas)
    pr = Image.new("RGB", (W, Hh), (236, 234, 228))
    y = 0
    for _, im in linhas:
        pr.paste(im, (0, y))
        y += im.height
    suf = "" if not ambos else "_VH"
    out = F.parent / f"PRANCHA{suf if ambos else ('_H' if tags == ['_H'] else '')}.jpg"
    pr.save(out, quality=88)
    itens = "".join(f'<section id="{n}"><h2>{html.escape(n)}</h2><img src="{n}_estados.jpg" loading="lazy"></section>'
                    for n, _ in linhas)
    (F.parent / "REVISAR.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Revisar rabiscos</title>"
        "<style>body{font:14px system-ui;background:#eceae4;margin:16px}img{max-width:100%;height:auto}"
        "nav a{margin-right:10px}section{margin:18px 0}</style><nav>"
        + "".join(f'<a href="#{n}">{n}</a>' for n, _ in linhas) + "</nav>" + itens, encoding="utf-8")
    print(f"  {len(linhas)} cenas -> {out} + REVISAR.html")


if __name__ == "__main__":
    main()
