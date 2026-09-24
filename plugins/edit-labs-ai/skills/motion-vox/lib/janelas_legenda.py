#!/usr/bin/env python3
"""
Janelas de legenda por CODIGO. `captions.configurar()` so RECEBE `janelas=`; quem calcula e este helper.

    python3 janelas_legenda.py            # le render.py (SHOTS), 00_brief/{cortes,avisos,transcript}.json
                                          # e 00_brief/pendentes.json; escreve 05_motion/JANELAS_LEGENDA.json

Regras:
  - a legenda CALA sob cutaway (a cena tem tipografia propria) e CORRE fora dela; overlay (op=False) nao cala
  - janela >= 0,6 s, recuada 0,15 s das bordas; nunca atravessa uma emenda do corte (quebra nela)
  - frase com palavra em duvida nao confirmada sai INTEIRA (captions.check exige toda palavra dita na tela)
Compativel com o Python 3.9 da motion-vox.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
MIN_S, RECUO = 0.6, 0.15   # 0,6 e não 2,0: com 2,0 as falas entre duas cutaways (≥ 1 s de rosto) ficam sem legenda


def _norm(w):
    import unicodedata
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


def frases(pal, gap=0.15):
    """Oracoes pelo transcript: pontuacao (inclusive virgula) ou vao >= gap. Fala rapida quase nao tem
    pausa: cortar so em ponto final calaria o video inteiro por causa de uma palavra em duvida."""
    out, cur = [], []
    for k, w in enumerate(pal):
        cur.append(w)
        fim = re.search(r"[.,;:!?…]$", w["w"]) or (k + 1 < len(pal) and pal[k + 1]["t"] - w["e"] >= gap) or k + 1 == len(pal)
        if fim:
            out.append((cur[0]["t"], cur[-1]["e"], cur))
            cur = []
    return out


def calcular(shots, dur, cortes, pal, duvidosas):
    livres = [(0.0, dur)]
    for s in shots:
        name, t0, t1, cutaway = s[0], s[2], s[3], s[5]
        if not cutaway:
            continue
        nxt = []
        for a, b in livres:
            if t1 <= a or t0 >= b:
                nxt.append((a, b))
                continue
            if t0 > a:
                nxt.append((a, t0))
            if t1 < b:
                nxt.append((t1, b))
        livres = nxt
    # A emenda NÃO quebra a janela. Quebrar aqui e depois exigir a janela mínima apaga a legenda de trechos
    # inteiros de rosto (ex.: 4 s de rosto com duas emendas no meio ficam sem nenhuma legenda).
    # Quem respeita a emenda é o bloco: captions.blocos() fecha o bloco em todo corte de CORTES.
    partes = list(livres)
    # frase com palavra em duvida sai inteira
    fora = []
    for t0, t1, ws in frases(pal):
        if any(_norm(w["w"]) in duvidosas for w in ws):
            fora.append((t0, t1, " ".join(w["w"] for w in ws)))
    res, motivos = [], []
    for a, b in partes:
        segs = [(a, b)]
        for f0, f1, txt in fora:
            nx = []
            for x, y in segs:
                if f1 <= x or f0 >= y:
                    nx.append((x, y))
                    continue
                motivos.append({"janela": [round(x, 3), round(y, 3)], "motivo": "asr_duvida", "frase": txt})
                if f0 > x:
                    nx.append((x, f0))
                if f1 < y:
                    nx.append((f1, y))
            segs = nx
        for x, y in segs:
            x2, y2 = x + RECUO, y - RECUO
            if y2 - x2 >= MIN_S:
                res.append((round(x2, 3), round(y2, 3)))
            elif y - x > 0.05:
                motivos.append({"janela": [round(x, 3), round(y, 3)], "motivo": "curta"})
    return res, motivos


def main():
    sys.path.insert(0, str(ROOT))
    import render as R
    b = ROOT / "00_brief"
    pal = json.loads((b / "transcript_palavras.json").read_text(encoding="utf-8"))
    cortes = json.loads((b / "cortes.json").read_text(encoding="utf-8")).get("cortes", []) if (b / "cortes.json").exists() else []
    pend = json.loads((b / "pendentes.json").read_text(encoding="utf-8")) if (b / "pendentes.json").exists() else {}
    duvidosas = {_norm(k) for k in pend}
    jan, motivos = calcular(R.SHOTS, R.DUR, cortes, pal, duvidosas)
    for s in R.SHOTS:
        if s[5]:
            motivos.append({"janela": [s[2], s[3]], "motivo": "cala_cutaway", "cena": s[0]})
    out = ROOT / "05_motion" / "JANELAS_LEGENDA.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cob = sum(y - x for x, y in jan)
    out.write_text(json.dumps({"janelas": jan, "fora": motivos, "cobertura_s": round(cob, 2),
                               "pendentes": sorted(duvidosas)}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {len(jan)} janelas, {cob:.1f} s de legenda de {R.DUR:.1f} s -> {out}")
    for x, y in jan:
        print(f"    ({x:.3f}, {y:.3f})")


if __name__ == "__main__":
    main()
