#!/usr/bin/env python3
"""
Mede um frame contra a faixa da Style Bible — massa escura, acento e vazio.

    python3 lib/medir.py 08_images/frames/M*_END.png
    python3 lib/medir.py frame.png --json

Um laudo que existe para verificar nao pode conter numero nao verificado — e a olho
ninguem acerta massa escura, acento nem vazio. Mesma metrica aplicada a referencia
Porsche (30 frames): escuro 15%, acento 5,0%, vazio 33% — dentro da Bible nos tres.

  massa escura   pixels com luminancia < 80                       Bible 10–18%
  acento         pixels saturados (sat > 0,45) e nao escuros       Bible  3–7%
  vazio          pixels na cor mediana do fundo e sem gradiente    Bible 25–40%

Duas ressalvas:

  `vazio`   e o menos confiavel: composicao papel-sobre-papel le como vazio mesmo cheia.
  `acento`  NAO distingue "cor de destaque com funcao" de "o assunto e saturado". Uma
            foto de tela cheia de um carro vermelho mede 34% de acento sem ter um unico
            elemento amarelo — nesse registro o numero nao quer dizer nada. Ele so vale
            em cena de papel, onde o saturado e mesmo o acento.

`escuro` e o unico robusto nos dois casos.
"""
import sys, json, glob
import numpy as np
from PIL import Image

FAIXA = {"escuro": (0.10, 0.18), "acento": (0.03, 0.07), "vazio": (0.25, 0.40)}


def medir(path):
    im = Image.open(path).convert("RGB")
    im = im.resize((270, 480) if im.height > im.width else (480, 270))
    a = np.asarray(im).astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    med = np.median(a.reshape(-1, 3), axis=0)
    dist = np.sqrt(((a - med) ** 2).sum(axis=2))
    gy, gx = np.gradient(lum)
    grad = np.sqrt(gx * gx + gy * gy)
    return dict(escuro=float((lum < 80).mean()),
                acento=float(((sat > 0.45) & (lum > 60)).mean()),
                vazio=float(((dist < 28) & (grad < 6)).mean()))


def veredito(m):
    out = {}
    for k, (lo, hi) in FAIXA.items():
        v = m[k]
        out[k] = "ok" if lo <= v <= hi else ("baixo" if v < lo else "alto")
    return out


def main(argv):
    paths = [p for a in argv if not a.startswith("--") for p in (glob.glob(a) or [a])]
    if not paths:
        print(__doc__); return 2
    rows = []
    for p in paths:
        m = medir(p); v = veredito(m)
        rows.append(dict(frame=p, **m, **{f"v_{k}": v[k] for k in v}))
    if "--json" in argv:
        print(json.dumps(rows, indent=1)); return 0
    print(f"{'frame':40s} {'escuro':>8s} {'acento':>8s} {'vazio':>8s}   veredito")
    for r in rows:
        nome = r["frame"][-40:]
        flags = [f"{k}:{r['v_'+k]}" for k in FAIXA if r["v_" + k] != "ok"]
        print(f"{nome:40s} {100*r['escuro']:7.1f}% {100*r['acento']:7.1f}% "
              f"{100*r['vazio']:7.0f}%   {'  '.join(flags) or 'dentro da faixa'}")
    print(f"\nfaixa Bible: escuro 10–18% · acento 3–7% · vazio 25–40% (vazio e o menos confiavel)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
