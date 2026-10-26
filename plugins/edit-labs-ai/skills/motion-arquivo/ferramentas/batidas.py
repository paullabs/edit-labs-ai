#!/usr/bin/env python3
"""
Transcricao -> batidas ancoradas na grade de 10 qps + rascunho do plano.

    mvpy batidas.py <projeto>

Le <projeto>/transcricao.json e escreve:
  <projeto>/batidas.md           tabela legivel: batida, palavras, quadro de cada palavra
  <projeto>/plano_rascunho.json  um plano por batida, com tipo SUGERIDO e tempos prontos

Regras (referencias/gramatica.md):
  - a palavra aparece no 1o degrau da grade (n % 3 == 2) DEPOIS que comeca a ser dita;
  - o corte cai no degrau da 1a palavra da batida (ou um antes);
  - batida = uma ideia: quebra em pausa > 0,25 s, pontuacao forte, ou 2,7 s de fala;
  - a 1a batida e o gancho (1-2 palavras).
O tipo sugerido e so ponto de partida: quem escolhe o plano e o mapa batida -> plano.
"""
import json, math, re, sys
from pathlib import Path

FPS = 30


def degrau_depois(t):
    n = math.ceil(t * FPS - 1e-6)
    while n % 3 != 2:
        n += 1
    return n


def batidas(ps, pausa=0.25, max_dur=2.7):
    bs, cur = [], []
    for i, w in enumerate(ps):
        if cur:
            gap = w["t"] - cur[-1]["e"]
            forte = re.search(r"[.!?;:]$", cur[-1]["w"]) is not None
            longa = w["e"] - cur[0]["t"] > max_dur
            gancho = len(bs) == 0 and len(cur) >= 1 and (gap > 0.12 or forte or len(cur) >= 2)
            if gap > pausa or forte or longa or gancho:
                bs.append(cur); cur = []
        cur.append(w)
    if cur:
        bs.append(cur)
    return bs


def sugerir(i, ws):
    txt = " ".join(w["w"] for w in ws)
    if i == 0:
        return "gancho_digitado"
    if re.search(r"\b(1[5-9]|20)\d{2}\b", txt):
        return "odometro"
    if txt.count(",") >= 2 or re.search(r"\b(e|and|ou|or)\b", txt) and txt.count(",") >= 1:
        return "lista_ui"
    return "palavra_no_papel"


def main(proj):
    proj = Path(proj)
    tr = json.loads((proj / "transcricao.json").read_text())
    ps = tr["palavras"]
    bs = batidas(ps)
    fim_audio = ps[-1]["e"]
    linhas = ["| # | inicio | palavras (quadro em que aparece) | sugestao |", "| --- | --- | --- | --- |"]
    planos = []
    for i, ws in enumerate(bs):
        ini = 0 if i == 0 else max(degrau_depois(ws[0]["t"]) - 3, planos[-1]["inicio"] + 3)
        tipo = sugerir(i, ws)
        palavras = [dict(texto=w["w"], quadro=degrau_depois(w["t"]), t=round(w["t"] * FPS, 2)) for w in ws]
        planos.append(dict(tipo=tipo, inicio=ini, palavras=palavras))
        linhas.append(f"| {i + 1} | {ini} ({ini / FPS:.2f} s) | " +
                      " ".join(f"{p['texto']}@{p['quadro']}" for p in palavras) + f" | {tipo} |")
    fim = degrau_depois(fim_audio + 0.5)
    for a, b in zip(planos, planos[1:] + [dict(inicio=fim)]):
        a["fim"] = b["inicio"]
    (proj / "batidas.md").write_text("\n".join(linhas) + "\n")
    rasc = dict(audio=str(Path("audio") / "narracao.wav"), quadros=fim, planos=planos)
    (proj / "plano_rascunho.json").write_text(json.dumps(rasc, ensure_ascii=False, indent=1))
    print(f"{len(planos)} batidas, {fim} quadros ({fim / FPS:.1f} s) -> batidas.md, plano_rascunho.json")


if __name__ == "__main__":
    main(sys.argv[1])
