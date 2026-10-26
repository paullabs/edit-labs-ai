"""Conferência final de um reel: borrão fora das transições e texto pequeno.

    python3 -I conferir.py <pasta do projeto> <video.mp4>

Convenção: o projeto tem ferramentas/reel.py com pecas(), montar(pecas) -> (camadas, cam, {"trans": [...]}) e FIM
(último quadro, relógio de 24). Assim a conferência sabe onde estão as transições e as camadas."""
import sys
from collections import defaultdict
from pathlib import Path

pasta, video = Path(sys.argv[1]).resolve(), sys.argv[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(pasta / "ferramentas"))
sys.argv = ["reel"]
import motor as M
import qa
import reel as R

p = R.pecas()
r = R.montar(*p) if isinstance(p, tuple) else R.montar(p)
camadas, cam, extra = r
trans = extra.get("trans", ())
M.ajustar_texto(camadas, cam, R.FIM, trans)
janelas = [(t.q0 / 24, t.q1 / 24 + 0.15) for t in trans]
borrados = qa.suspeitos(video, janelas)
print(f"borrão fora das transições: {len(borrados)}", borrados[:12])
pequenos = []
for L in camadas:
    if L.mundo and L.texto_px:
        for f in range(max(L.ini, 0), min(L.fim, R.FIM), 12):
            if any(t.q0 <= f < t.q1 for t in trans):
                continue
            pp = L.props(f)
            C = M.perto(cam.matriz(f), L.prof)
            x, y = M.na_tela(C, (pp["x"], pp["y"]))
            if 0 < x < M.W and 0 < y < M.H and pp["op"] > 0.5:
                corpo = L.texto_px * pp["s"] * M.escala_de(C)
                if corpo < 0.75 * L.texto_min:
                    pequenos.append((L.nome, f, round(corpo)))
por = defaultdict(list)
for n, f, c in pequenos:
    por[n].append((f, c))
print("texto pequeno (<75% do mínimo):", {n: v[:3] for n, v in por.items()})
