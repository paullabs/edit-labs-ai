#!/usr/bin/env python3
"""Corta o preview horizontal de cada candidato, com os segmentos emendados.

    preview.py <run-dir> [ID ...]

- Um input por segmento, com busca híbrida: `-ss` rápido até 3 s antes (keyframe)
  e `trim` exato dentro do filtro. Exato no quadro, sem decodificar o episódio
  desde o começo (a receita da fase 2 só oferece rápido-impreciso ou exato-lento).
- Emenda os segmentos em ordem (`concat`) — a receita da fase 2 corta um in/out só
  e não serve para clipe com corte interno.
- Horizontal, como está: sem reenquadrar, sem legenda, sem normalizar.

Saída: <run>/preview/NN-<id>.mp4
"""
import json
import subprocess
import sys
import time
from pathlib import Path

PRE = 3.0  # segundos de folga para a busca rápida


def cortar(video: str, segs: list[dict], saida: Path) -> float:
    args, filtros, pares = ["ffmpeg", "-y", "-v", "error"], [], []
    for i, s in enumerate(segs):
        a, b = float(s["source_start"]), float(s["source_end"])
        ss = max(0.0, a - PRE)
        args += ["-ss", f"{ss:.3f}", "-t", f"{b - ss + 0.5:.3f}", "-i", video]
        off, dur = a - ss, b - a
        filtros.append(f"[{i}:v]trim=start={off:.3f}:duration={dur:.3f},setpts=PTS-STARTPTS[v{i}]")
        filtros.append(f"[{i}:a]atrim=start={off:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS[a{i}]")
        pares.append(f"[v{i}][a{i}]")
    filtros.append("".join(pares) + f"concat=n={len(segs)}:v=1:a=1[v][a]")
    args += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(saida)]
    t0 = time.time()
    subprocess.run(args, check=True)
    return time.time() - t0


def main(run: Path, ids: list[str]) -> None:
    manifest = json.loads((run / "00-manifest.json").read_text())
    video = manifest.get("video_path") or manifest.get("inputs", {}).get("video_path")
    clipes = json.loads((run / "06-candidates.json").read_text())["clips"]
    (run / "preview").mkdir(exist_ok=True)
    for n, c in enumerate(clipes, 1):
        if ids and c["id"] not in ids:
            continue
        segs = sorted(c["segments"], key=lambda s: s.get("order", 0))
        saida = run / "preview" / f"{n:02d}-{c['id']}.mp4"
        dt = cortar(video, segs, saida)
        dur = sum(float(s["source_end"]) - float(s["source_start"]) for s in segs)
        print(f"{saida.name}: {len(segs)} segmento(s), {dur:.1f}s de clipe, render {dt:.1f}s")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(Path(sys.argv[1]), sys.argv[2:])
