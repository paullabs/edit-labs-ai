#!/usr/bin/env python3
"""
Mesma regua nos dois: cortes, cadencia e luz/cor/layout por plano. So faz sentido quando ha
uma REFERENCIA (reproduzir um video) — num projeto novo, a regua e o triptico + o Diretor.

    mvpy comparar.py <quadros_ref_720> <quadros_nosso_720> <projeto>

Os quadros sao PNG 720x1280 numerados de 0000; o nosso SEMPRE extraido de um render que
passou pela mesma entrega do original (720p, x264 ~1,26 Mbps). Os cortes vem do plano.json.
"""
import _caminho  # noqa: F401
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image

A, B, proj = sys.argv[1], sys.argv[2], Path(sys.argv[3])
planos = sorted(json.loads((proj / "plano.json").read_text())["planos"], key=lambda p: p["inicio"])
CORTES = [p["inicio"] for p in planos] + [planos[-1]["fim"]]
N = CORTES[-1]


def lo(p, n):
    return cv2.resize(np.asarray(Image.open(f"{p}/{n:04d}.png").convert("RGB")).astype(np.float32), (90, 160),
                      interpolation=cv2.INTER_AREA)


fa = [lo(A, n) for n in range(N)]; fb = [lo(B, n) for n in range(N)]


def cortes(fs):
    d = [0] + [float(np.abs(fs[i] - fs[i - 1]).mean()) for i in range(1, N)]
    h = [0] + [0.5 * np.abs(np.histogram(fs[i].mean(2), 32, (0, 255))[0] / 14400.0 -
                            np.histogram(fs[i - 1].mean(2), 32, (0, 255))[0] / 14400.0).sum() for i in range(1, N)]
    med = [np.median(d[max(1, k - 8):k + 9]) for k in range(N)]
    ev = []
    for k in [k for k in range(1, N) if d[k] > max(8, 4 * med[k]) and h[k] > 0.2]:
        if not ev or k - ev[-1] > 3:
            ev.append(k)
    return ev, d


ca, da = cortes(fa); cb, db = cortes(fb)
dif = [min(cb, key=lambda x: abs(x - k)) - k if cb else None for k in ca]
print(f"cortes: referencia {len(ca)}, nosso {len(cb)}; reproduzidos a <=1 quadro: "
      f"{sum(1 for e in dif if e is not None and abs(e) <= 1)}/{len(ca)}  diferencas {dif}")
ma = "".join("1" if x > 0.6 else "." for x in da[1:]); mb = "".join("1" if x > 0.6 else "." for x in db[1:])
print(f"cadencia: {sum(1 for x, y in zip(ma, mb) if x == y)}/{N - 1} quadros com o mesmo padrao de mudanca")
print("plano  quadros    luz ref/nosso   cor ref / nosso                 layout")
for i, (a, b) in enumerate(zip(CORTES, CORTES[1:]), 1):
    xa = np.stack(fa[a:b]); xb = np.stack(fb[a:b])
    la, lb = xa.mean(), xb.mean()
    ga = xa.mean(0).mean(2); gb = xb.mean(0).mean(2)
    cor = np.corrcoef(ga.ravel(), gb.ravel())[0, 1] if ga.std() > 1e-3 and gb.std() > 1e-3 else float("nan")
    print(f"{i:5d}  [{a:4d}-{b:4d})  {la:5.0f}/{lb:5.0f}   {tuple(xa.reshape(-1, 3).mean(0).round().astype(int).tolist())} / "
          f"{tuple(xb.reshape(-1, 3).mean(0).round().astype(int).tolist())}   {cor:+.2f}")
