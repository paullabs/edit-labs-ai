#!/usr/bin/env python3
"""Decupagem do respiro por script: encolhe pausas longas sem nunca cortar palavra.

    respiro.py <run-dir> [--min 0.40] [--manter 0.18] [--preservar t1,t2,...] [--gravar]

Para cada segmento dos candidatos (06-candidates.json):
1. envelope RMS (janela 20 ms, passo 10 ms) no áudio da run;
2. silêncio = ≥ 18 dB abaixo do nível de fala do segmento (p90);
3. pausa ≥ --min s vira corte: fica --manter s de ar (metade de cada lado),
   o resto sai. O corte cai no meio do silêncio — por construção, fora da palavra;
4. pausa que contém um instante de --preservar (em segundos do episódio) fica
   inteira: é a exceção editorial (antes do payoff, depois da punchline, riso).

Sem --gravar, só mostra o que faria (e compara com 11-edit-plans.json, se existir).
Com --gravar, escreve 11-respiro-script.json com a timeline por clipe.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from checar_cortes import carregar_wav, energia, rms_db  # noqa: E402

JAN, PASSO, ABAIXO = 0.02, 0.01, 18.0


def pausas(x, sr, a, b, minimo):
    ts = np.arange(a, b - JAN, PASSO)
    env = np.array([rms_db(x, sr, t, t + JAN) for t in ts])
    if not len(env):
        return []
    fala = np.percentile(env, 90)
    quieto = env <= fala - ABAIXO
    out, ini = [], None
    for t, q in zip(ts, quieto):
        if q and ini is None:
            ini = t
        elif not q and ini is not None:
            if t - ini >= minimo:
                out.append((ini, t))
            ini = None
    return out


def decupar(x, sr, segs, minimo, manter, preservar):
    """preservar: lista de instantes (float) ou intervalos (a, b) em segundos do episódio."""
    faixas = [(p, p) if isinstance(p, (int, float)) else (float(p[0]), float(p[1])) for p in preservar]
    novos, tirado, cortes = [], 0.0, 0
    for s in segs:
        a, b = float(s["source_start"]), float(s["source_end"])
        cursor = a
        for p0, p1 in pausas(x, sr, a, b, minimo):
            if any(p0 <= fb and p1 >= fa for fa, fb in faixas):
                continue
            meio_fim = p0 + manter / 2
            meio_ini = p1 - manter / 2
            if meio_fim <= cursor + 0.05:
                continue
            novos.append({**s, "source_start": round(cursor, 3), "source_end": round(meio_fim, 3)})
            tirado += meio_ini - meio_fim
            cortes += 1
            cursor = meio_ini
        novos.append({**s, "source_start": round(cursor, 3), "source_end": round(b, 3)})
    for i, s in enumerate(novos, 1):
        s["order"] = i
    return novos, tirado, cortes


def resumo(nome, x, sr, tl):
    dur = sum(float(s["source_end"]) - float(s["source_start"]) for s in tl)
    marcas = {"✅": 0, "⚠️": 0, "❌": 0}
    for s in tl:
        for t in (float(s["source_start"]), float(s["source_end"])):
            marcas[energia(x, sr, t)[0]] += 1
    return f"{nome}: {len(tl)} segmentos · {dur:.1f} s · bordas ✅{marcas['✅']} ⚠️{marcas['⚠️']} ❌{marcas['❌']}"


def reunir_cortes_do_agente(tl, cortes):
    """Desfaz os cortes de respiro que o agente fez (emenda os dois segmentos de volta)."""
    tl = [dict(s) for s in sorted(tl, key=lambda s: s.get("order", 0))]
    for c in cortes:
        ra, rb = [float(v) for v in c["removed_source"]]
        for i in range(len(tl) - 1):
            if abs(float(tl[i]["source_end"]) - ra) < 0.02 and abs(float(tl[i + 1]["source_start"]) - rb) < 0.02:
                tl[i]["source_end"] = tl[i + 1]["source_end"]
                del tl[i + 1]
                break
    return tl


def plano(run, x, sr, minimo, manter, gravar):
    """Base = plano do edit-director: mantém layout, cartelas e pausas preservadas por ele;
    troca os cortes de respiro dele pelos do script (no meio do silêncio medido)."""
    caminho = run / "11-edit-plans.json"
    doc = json.loads(caminho.read_text())
    for p in doc["plans"]:
        resp = p.get("respiro") or {}
        base = reunir_cortes_do_agente(p["timeline"], resp.get("cuts", []))
        preserv = [tuple(pr["source"]) for pr in resp.get("preserved", []) if pr.get("source")]
        dur0 = sum(float(s["source_end"]) - float(s["source_start"]) for s in base)
        novos, tirado, cortes = decupar(x, sr, base, minimo, manter, preserv)
        print(f"{p['clip_id']}: {len(resp.get('cuts', []))} cortes do agente desfeitos · {len(preserv)} pausas preservadas "
              f"· script: {cortes} cortes, tirou {tirado:.1f} s ({tirado / dur0:.0%}) · {resumo('final', x, sr, novos)}")
        p["timeline"] = novos
        p["respiro_script"] = {"cuts": cortes, "removed_seconds": round(tirado, 2), "min_pause_s": minimo,
                               "kept_air_s": manter, "preserved_from_director": preserv,
                               "note": "cortes de respiro do agente substituídos pelos do script (ferramentas/respiro.py)"}
    if gravar:
        backup = run / "11-edit-plans.diretor.json"
        if not backup.exists():
            backup.write_text(caminho.read_text())
        caminho.write_text(json.dumps(doc, ensure_ascii=False, indent=2))
        print(f"gravado: 11-edit-plans.json (original em {backup.name})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--min", type=float, default=0.40)
    ap.add_argument("--manter", type=float, default=0.18)
    ap.add_argument("--preservar", default="")
    ap.add_argument("--plano", action="store_true", help="aplica sobre o 11-edit-plans.json do edit-director")
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    x, sr = carregar_wav(run / "assets" / "audio-analysis.wav")
    if a.plano:
        plano(run, x, sr, a.min, a.manter, a.gravar)
        return
    preservar = [float(t) for t in a.preservar.split(",") if t.strip()]
    clipes = json.loads((run / "06-candidates.json").read_text())["clips"]
    planos = {}
    ep = run / "11-edit-plans.json"
    if ep.exists():
        planos = {p["clip_id"]: p for p in json.loads(ep.read_text()).get("plans", [])}
    saida = {}
    for c in clipes:
        segs = sorted(c["segments"], key=lambda s: s.get("order", 0))
        base = sum(float(s["source_end"]) - float(s["source_start"]) for s in segs)
        novos, tirado, cortes = decupar(x, sr, segs, a.min, a.manter, preservar)
        print(f"\n{c['id']} · antes {base:.1f} s")
        print("  " + resumo("script", x, sr, novos) + f" · {cortes} cortes · tirou {tirado:.1f} s ({tirado / base:.0%})")
        if c["id"] in planos:
            tl = planos[c["id"]]["timeline"]
            dur = sum(float(s["source_end"]) - float(s["source_start"]) for s in tl)
            print("  " + resumo("agente", x, sr, tl) + f" · tirou {base - dur:.1f} s ({(base - dur) / base:.0%})")
        saida[c["id"]] = [{k: v for k, v in s.items() if k in ("source_start", "source_end", "order", "role")} for s in novos]
    if a.gravar:
        (run / "11-respiro-script.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2))
        print("\ngravado: 11-respiro-script.json")


if __name__ == "__main__":
    main()
