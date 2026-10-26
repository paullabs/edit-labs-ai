#!/usr/bin/env python3
"""
Projeto -> mp4 1080x1920 com a narracao.

    python3 render.py <projeto> [saida.mp4] [--de Q] [--ate Q] [--crf 14]

Cada quadro mostra o estado do ultimo degrau da grade de 10 qps; o estado e montado uma
vez e reaproveitado nos tres quadros (o grao congela junto, como no original). Audio:
mp4/m4a/aac da origem e COPIADO bit a bit; wav vira AAC 192k. Trecho (--de/--ate) e so
para conferir — entrega e sempre a peca inteira.
"""
import _caminho  # noqa: F401
import subprocess, sys, time
from pathlib import Path
import numpy as np
from familia_a import W, H
from familia_a.tempo import grade, FPS
from familia_a.c4_filtro import acabamento
from familia_a.c5_movimentos import camera, borrao_direcional
import projeto

a = sys.argv[1:]
proj = a[0]
saida = a[1] if len(a) > 1 and not a[1].startswith("--") else str(Path(proj) / "saida" / "render_1080.mp4")
cena = projeto.carregar(proj)
de = int(a[a.index("--de") + 1]) if "--de" in a else cena.INICIO
ate = int(a[a.index("--ate") + 1]) if "--ate" in a else cena.FIM
Path(saida).parent.mkdir(parents=True, exist_ok=True)
aud = cena.audio
inteira = de == cena.INICIO == 0 and ate == cena.FIM
if inteira and aud.suffix.lower() in (".mp4", ".m4a", ".aac", ".mov"):
    ent_a, cod_a = ["-i", str(aud)], ["-c:a", "copy"]
else:
    ent_a, cod_a = ["-ss", f"{de / FPS:.4f}", "-t", f"{(ate - de) / FPS:.4f}", "-i", str(aud)], ["-c:a", "aac", "-b:a", "192k"]
ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-"] + ent_a +
                      ["-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-preset", "slow",
                       "-crf", (a[a.index("--crf") + 1] if "--crf" in a else "14"),
                       "-pix_fmt", "yuv420p"] + cod_a + [saida], stdin=subprocess.PIPE)
cache, t = {}, time.time()
for n in range(de, ate):
    g = max(cena.INICIO, cena.grade(n) if hasattr(cena, "grade") else grade(n))
    if g not in cache:
        cache.clear()
        img, dx, fundo = cena.estado(g)
        if dx:
            img = camera(img, dx=dx, fundo=fundo)
        img = borrao_direcional(img, cena.borrao(g))
        cache[g] = np.clip(acabamento(img, semente=g), 0, 255).astype(np.uint8)
    ff.stdin.write(cache[g].tobytes())
ff.stdin.close(); ff.wait()
print(f"{ate - de} quadros em {time.time() - t:.1f}s -> {saida}")
