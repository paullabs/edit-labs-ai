"""F2: TOMADAS.jpg — 1 quadro no meio de cada segmento escolhido (seek exato, 480 px de altura).

  di amostrar <id>

Única olhada no vídeo antes de F3, escopada às tomadas escolhidas (exceção à regra 1, como o
`vch visual-index --windows` da corte-viral). Serve para o Editor/Diretor ver defeito visual:
olhar fora, mão no rosto, desfoque, gente no quadro.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from comum import DIError, achar_projeto, ler_json, mmss
from render_corte import fonte_de, quadro


def amostrar(projeto: Path, vid: str) -> Path:
    import cv2
    edl = ler_json(Path(projeto) / "02_decupagem" / vid / "edl.json")
    if not edl:
        raise DIError(f"{vid}: rode di edl primeiro")
    src, _ = fonte_de(Path(projeto))
    cols = []
    for s in edl["segmentos"]:
        t = (s["source_in"] + s["source_out"]) / 2
        img = quadro(src, t, 854)
        img = cv2.resize(img, (int(img.shape[1] * 480 / img.shape[0]), 480))
        cv2.putText(img, f"{s['n']} {mmss(t)}", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cols.append(img)
    linhas = [np.hstack(cols[i:i + 4] + [np.zeros_like(cols[0])] * (4 - len(cols[i:i + 4]))) for i in range(0, len(cols), 4)]
    out = Path(projeto) / "02_decupagem" / vid / "TOMADAS.jpg"
    cv2.imwrite(str(out), np.vstack(linhas), [cv2.IMWRITE_JPEG_QUALITY, 82])
    return out


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di amostrar")
    ap.add_argument("video")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    print(f"✓ {amostrar(achar_projeto(a.projeto), a.video)}")
    return 0
