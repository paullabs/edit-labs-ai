#!/usr/bin/env python3
"""
Converte o `caption-map.json` que a skill corte-viral entrega no
`transcript_palavras.json` que esta skill exige. Nao rode Whisper de novo.

    python3 lib/words_from_corte_viral.py <clipe>/caption-map.json 00_brief/transcript_palavras.json

O mapa traz, por legenda, `start`/`end` em tempo DO CLIPE e `source_words` com
`source_start`/`source_end` em tempo DO EPISODIO. Cada legenda vive dentro de um trecho
continuo, entao o offset e por legenda: `t = source_start + (start - primeira.source_start)`.
Cortes secos do clipe (onde o offset muda) sao detectados e impressos — vao em `cortes=[]`
na configuracao da legenda (`captions.configurar`), senao um bloco atravessa o corte.
"""
import sys, json


def converter(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    caps = d["captions"] if isinstance(d, dict) else d
    words, cortes, prev_off = [], [], None
    for cap in caps:
        sw = cap.get("source_words") or []
        if not sw:
            continue
        off = float(cap["start"]) - float(sw[0]["source_start"])
        if prev_off is not None and abs(off - prev_off) > 0.05:
            cortes.append(round(float(cap["start"]), 3))
        prev_off = off
        # o `end` da legenda e a verdade do corte: num corte seco o Whisper marca palavras
        # ALEM dele (a fala continuava no episodio, nao no clipe). Clampa na janela da
        # legenda e descarta palavra que so comecaria depois do corte.
        c0, c1 = float(cap["start"]), float(cap["end"])
        for w in sw:
            t = float(w["source_start"]) + off
            e = float(w["source_end"]) + off
            txt = str(w.get("text", w.get("word", ""))).strip()
            if not txt or t >= c1 - 0.01:
                continue
            t, e = max(t, c0), min(max(e, t + 0.02), c1)
            words.append({"w": txt, "t": round(t, 3), "e": round(e, 3)})
    # blocos nunca se sobrepoem no tempo (armadilha 46)
    for i in range(len(words) - 1):
        words[i]["e"] = min(words[i]["e"], words[i + 1]["t"])
    json.dump(words, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    return words, cortes


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    words, cortes = converter(sys.argv[1], sys.argv[2])
    dur = words[-1]["e"] if words else 0
    print(f"{len(words)} palavras · {dur:.2f}s · {sys.argv[2]}")
    if cortes:
        print(f"cortes secos detectados (use em captions.configurar(cortes=...)): {cortes}")
