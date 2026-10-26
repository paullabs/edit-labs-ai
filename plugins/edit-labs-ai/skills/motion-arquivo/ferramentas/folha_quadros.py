#!/usr/bin/env python3
"""
Folha de quadros escolhidos do projeto, já com o acabamento, com a zona segura do Reels por cima (opcional).

    python3 folha_quadros.py <projeto> <q1,q2,...> <saida.png> [--zona] [--escala 0.25] [--colunas 6]

Cada quadro vira o degrau da grade que o render mostra. É a conferência rápida de texto, desenho e enquadramento sem
renderizar o vídeo inteiro (zona_segura.py mede; esta folha mostra).
"""
import _caminho  # noqa: F401
import argparse

import numpy as np
from PIL import Image, ImageDraw

from familia_a import W, H
from familia_a.c4_filtro import acabamento
import projeto
from zona_segura import guia


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto"); ap.add_argument("quadros"); ap.add_argument("saida")
    ap.add_argument("--zona", action="store_true")
    ap.add_argument("--escala", type=float, default=0.25)
    ap.add_argument("--colunas", type=int, default=6)
    a = ap.parse_args()
    cena = projeto.carregar(a.projeto)
    qs = [int(x) for x in a.quadros.split(",")]
    tw, th = int(W * a.escala), int(H * a.escala)
    cols = min(a.colunas, len(qs)); lin = (len(qs) + cols - 1) // cols
    folha = Image.new("RGB", (cols * (tw + 4), lin * (th + 18)), (20, 20, 20))
    d = ImageDraw.Draw(folha)
    for i, q in enumerate(qs):
        g = max(cena.INICIO, cena.grade(q))
        img, _, _ = cena.estado(g)
        im = Image.fromarray(np.clip(acabamento(img, semente=g), 0, 255).astype(np.uint8))
        if a.zona:
            im = guia(im)
        x0, y0 = (i % cols) * (tw + 4), (i // cols) * (th + 18)
        folha.paste(im.resize((tw, th), Image.LANCZOS), (x0, y0 + 18))
        p = cena.plano_de(g)
        d.text((x0 + 3, y0 + 3), f"q{g} p{cena.planos.index(p) + 1} {p['tipo']}", fill=(230, 230, 230))
    folha.save(a.saida)
    print(a.saida)


if __name__ == "__main__":
    main()
