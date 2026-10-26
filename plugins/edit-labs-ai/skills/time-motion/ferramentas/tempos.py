#!/usr/bin/env python3
"""Tabela palavra -> quadro, a partir da transcrição ajustada (transcrever.py + ilhas_fala.py).

    python3 tempos.py <palavras.json> <ancoras.json> <saida/tempos.json> [--fps 24]

<ancoras.json> é do projeto (o Diretor de Motion escreve a partir do PLANO_MOTION.md):
    {
      "fim": 412,                         quadro do fim do corte (opcional; padrão: fim da última palavra)
      "emendas": [161],                   quadros onde o corte emenda dois trechos (a legenda não atravessa)
      "eventos": {"nome": ["palavra", 0]},             palavra-âncora e ocorrência (0 = a primeira)
      "corrige": {"palavra#0": 5.81},                  início medido na onda quando o whisper erra (s)
      "legenda": [["frase que abre", "palavra", 0]]    frases e a palavra que abre cada uma (opcional)
    }

Regras: o evento gráfico cai no primeiro quadro PAR em/depois da palavra (degraus de 2 quadros, um relógio só);
a legenda cai no primeiro quadro em/depois da palavra e fica até a próxima frase abrir (ou até a emenda / o fim).
A legenda é a ÚLTIMA coisa montada: esta tabela só reserva as janelas.
"""
import json
import math
import sys
from pathlib import Path


def _norm(w):
    return w.strip().strip(".,;:!?…\"'“”").lower()


def inicio(P, corrige, palavra, ocorr=0):
    alvo = _norm(palavra)
    n = 0
    for p in P:
        if _norm(p["palavra"]) == alvo:
            if n == ocorr:
                return corrige.get(f"{alvo}#{ocorr}", corrige.get(f"{palavra}#{ocorr}", p["ini"]))
            n += 1
    raise KeyError(f"palavra não achada: {palavra!r} (ocorrência {ocorr})")


def quadro(t, fps):
    """primeiro quadro em/depois de t (tolerância de 10 ms a 24 qps)"""
    return int(math.ceil(t * fps - 0.25))


def degrau(t, fps):
    """primeiro quadro PAR em/depois de t"""
    q = quadro(t, fps)
    return q + (q % 2)


def main():
    a = sys.argv[1:]
    fps = 24
    if "--fps" in a:
        i = a.index("--fps"); fps = int(a[i + 1]); del a[i:i + 2]
    P = json.loads(Path(a[0]).read_text())["palavras"]
    cfg = json.loads(Path(a[1]).read_text())
    saida = Path(a[2])
    corrige = {k.lower(): v for k, v in cfg.get("corrige", {}).items()}
    fim = int(cfg.get("fim") or quadro(P[-1]["fim"], fps))
    emendas = sorted(int(e) for e in cfg.get("emendas", []))

    ev = {}
    for nome, (w, o) in cfg.get("eventos", {}).items():
        t = inicio(P, corrige, w, o)
        ev[nome] = {"palavra": w, "t": round(t, 3), "quadro": quadro(t, fps), "degrau": degrau(t, fps)}
    leg = []
    for txt, w, o in cfg.get("legenda", []):
        t = inicio(P, corrige, w, o)
        leg.append({"texto": txt, "t": round(t, 3), "ini": quadro(t, fps)})
    for i, s in enumerate(leg):
        prox = leg[i + 1]["ini"] if i + 1 < len(leg) else fim
        corta = [e for e in emendas if s["ini"] < e < prox]
        s["fim"] = corta[0] if corta else prox
    ruins = [s["texto"] for s in leg if any(s["ini"] < e < s["fim"] for e in emendas)]
    if ruins:
        sys.exit(f"frase atravessa a emenda: {ruins}")

    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({"fps": fps, "eventos": ev, "legenda": leg, "fim": fim, "emendas": emendas},
                                ensure_ascii=False, indent=1))
    print("evento          palavra           t (s)   quadro  degrau")
    for k, v in ev.items():
        print(f"{k:15s} {v['palavra']:16s} {v['t']:6.2f}  {v['quadro']:5d}  {v['degrau']:5d}")
    if leg:
        print("\nlegenda (quadros) — monta por último")
        for s in leg:
            print(f"{s['ini']:4d}–{s['fim']:4d}  {s['texto']}")
    print("\n->", saida)


if __name__ == "__main__":
    main()
