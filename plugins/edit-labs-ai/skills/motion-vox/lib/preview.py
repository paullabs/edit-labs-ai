#!/usr/bin/env python3
"""
Preview de um trecho, para julgar boil e entrada de legenda em MOVIMENTO.
Renderiza so a janela pedida e monta sobre o clipe original.

    python3 preview.py 7.0 16.0 saida.mp4 [escala_do_boil]
"""
import sys, subprocess, shutil
from pathlib import Path
from PIL import Image
import voxlab as V, compose as C, captions as CAP, render as R

t0, t1 = float(sys.argv[1]), float(sys.argv[2])
dst = Path(sys.argv[3])
V.BOIL_SCALE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

TMP = Path("11_preview"); shutil.rmtree(TMP, ignore_errors=True); TMP.mkdir()
FPS = R.FPS
ph = CAP.build(R.WORDS_JSON, R.SEG_SRC)
shots = [s for s in R.SHOTS if s[3] > t0 and s[2] < t1]
n = int(round((t1 - t0) * FPS))
print(f"  {n} frames, boil x{V.BOIL_SCALE}, cenas: {[s[0] for s in shots]}", flush=True)

src = [f"{TMP}/plate_%04d.png"]
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0),
                "-i", str(R.SRC), f"{TMP}/plate_%04d.png"], check=True)

for i in range(n):
    t = t0 + i / FPS
    base = Image.open(f"{TMP}/plate_{i+1:04d}.png").convert("RGBA")
    for name, fn, a, b, tot, cut in shots:
        if not (a <= t < b):
            continue
        f24 = min(tot, (t - a) * 24.0)
        if cut:
            im = V.finish(fn(f24), seed=1000 + i // 2, **R.FX_DESK)
            k = int(round((b - a) * FPS)) - R.EXIT_SLIDE
            j = int(round((t - a) * FPS))
            if j >= k:
                im = R.exit_frame(im, R.EXIT_KIND.get(name, "slide"),
                                  V.ease_in((j - k + 1) / R.EXIT_SLIDE))
        else:
            im = fn(f24, overlay_only=True)
        base.alpha_composite(im.convert("RGBA"))
    V.boil_ctx(None)
    cur = next((k for k, x in enumerate(ph) if x["t"] <= t < x["e"]), None)
    if cur is not None:
        x = ph[cur]
        frac = {"push": 0.0, "wipe": 0.30, "slide": 0.50}
        dark = any(aa <= t < bb - frac.get(R.EXIT_KIND.get(nm), 0.5) * R.EXIT_SLIDE / FPS
                   for nm, _, aa, bb, _, cu in R.SHOTS if cu)
        base.alpha_composite(CAP.draw(x["lines"], min(1.0, (t - x["t"]) / 0.34),
                                      dark, stylized=(cur % 2 == 1)))
    base.convert("RGB").save(f"{TMP}/out_{i:04d}.png")
    if i % 40 == 0:
        print(f"  {i}/{n}", flush=True)

subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", f"{R.FPS_NUM}/{R.FPS_DEN}",
                "-i", f"{TMP}/out_%04d.png", "-ss", str(t0), "-t", str(t1 - t0),
                "-i", str(R.SRC), "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "medium", "-crf", "22",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", str(dst)], check=True)
shutil.rmtree(TMP, ignore_errors=True)
print(f"  -> {dst}")
