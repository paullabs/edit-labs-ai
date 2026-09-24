#!/usr/bin/env python3
"""
Tabela evento <-> palavra POR CODIGO. Roda ANTES de `render.py --frames`.

    python3 ancorar.py                 # 05_motion/ANCORAGEM.md + ANCORAGEM.json
    python3 ancorar.py --blueprints    # + 05_motion/M#_motion.md e 06_transitions/TRANSITION_MAP.md,
                                       #   gerados da tabela B do 00_brief/PLANO_MOTION.md + M#_EVENTS

Le render.py (SHOTS, EXIT_KIND, FPS), compose.py (M#_EVENTS, M#_STATES), o transcript do corte e
00_brief/silencios_corte.json. Nada aqui e escrito a mao: blueprint e mapa de transicoes sao GERADOS,
para a tabela B do plano ser a unica fonte.

Regras:
  evento travado na palavra      inicio do evento a <= 3 frames24 (0,125 s) do inicio de uma palavra  -> FORA = BLOCKER
  entrada da cena                t0 a <= 3 frames24 da palavra-ancora do plano                          -> HIGH
  saida da cutaway               t1 dentro de silencio medido, na fronteira de palavra ou numa emenda    -> BLOCKER
  hold antes da saida            8-18 frames24 entre o fim do ultimo evento e o fim da cena              -> MEDIUM
  END                            depois do ultimo evento                                                 -> HIGH
Compativel com o Python 3.9 da motion-vox.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path.cwd()
TOL24 = 3
CONTINUOS = {"camera", "hands", "drift", "exit", "line", "boot", "sweep", "grain", "push", "bg", "fundo"}


def _sem_acento(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _num(s):
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*s\b", s or "")
    return float(m.group(1).replace(",", ".")) if m else None


def tabela_b():
    p = ROOT / "00_brief" / "PLANO_MOTION.md"
    if not p.exists():
        return {}
    md = p.read_text(encoding="utf-8")
    m = re.search(r"^##\s*B\..*?$", md, re.M)
    if not m:
        return {}
    resto = md[m.end():]
    fim = re.search(r"^##\s", resto, re.M)
    linhas = [l.strip() for l in (resto[:fim.start()] if fim else resto).splitlines() if l.strip().startswith("|")]
    if len(linhas) < 3:
        return {}
    cab = [_sem_acento(c.strip().lower()) for c in linhas[0].strip("|").split("|")]
    out = {}
    for l in linhas[2:]:
        cel = [c.strip() for c in l.strip("|").split("|")]
        row = dict(zip(cab, cel + [""] * (len(cab) - len(cel))))
        nome = row.get("m#", "").strip("* ")
        if nome:
            out[nome] = row
    return out


def _col(row, nome):
    return next((v for k, v in row.items() if k.startswith(nome)), "")


def ancorar():
    sys.path.insert(0, str(ROOT))
    import render as R
    import compose as C
    pal = json.loads((ROOT / "00_brief" / "transcript_palavras.json").read_text(encoding="utf-8"))
    sj = ROOT / "00_brief" / "silencios_corte.json"
    sils = json.loads(sj.read_text(encoding="utf-8"))["silencios"] if sj.exists() else []
    cortes = []
    cj = ROOT / "00_brief" / "cortes.json"
    if cj.exists():
        cortes = json.loads(cj.read_text(encoding="utf-8")).get("cortes", [])
    plano = tabela_b()
    linhas, res = [], {"cenas": [], "fora": []}
    for name, fn, t0, t1, total24, cutaway in R.SHOTS:
        ev = getattr(C, f"{name}_EVENTS", {}) or {}
        st = getattr(C, f"{name}_STATES", {}) or {}
        cena = {"cena": name, "t0": t0, "t1": t1, "eventos": []}
        ultimo = 0
        for k, (a, b) in sorted(ev.items(), key=lambda kv: kv[1][0]):
            if k in CONTINUOS:
                continue
            ultimo = max(ultimo, b)
            if a < 0:      # herói já em voo no frame 0 (armadilha #62): começa antes do corte
                cena["eventos"].append({"evento": k, "f24": a, "t": round(t0 + a / 24, 3), "palavra": "(em voo no corte)",
                                        "delta_f24": 0.0, "delta_ms": 0, "ok": True})
                continue
            t = t0 + a / 24.0
            w = min(pal, key=lambda x: abs(x["t"] - t)) if pal else None
            d24 = (t - w["t"]) * 24 if w else 99
            ok = abs(d24) <= TOL24
            e = {"evento": k, "f24": a, "t": round(t, 3), "palavra": w["w"] if w else None,
                 "t_palavra": w["t"] if w else None, "delta_f24": round(d24, 1), "delta_ms": int(round(d24 / 24 * 1000)), "ok": ok}
            cena["eventos"].append(e)
            if not ok:
                res["fora"].append(f"{name}.{k}: f{a} ({t:.2f} s) a {d24:+.1f} f24 de '{w['w'] if w else '?'}'")
        # entrada: t0 perto da âncora do plano
        row = plano.get(name, {})
        anc = _col(row, "ancora")
        t_anc = _num(anc)
        if t_anc is not None:
            d = (t0 - t_anc) * 24
            cena["entrada"] = {"ancora": anc, "delta_f24": round(d, 1), "ok": abs(d) <= TOL24}
            if abs(d) > TOL24:
                res["fora"].append(f"{name}: entra a {d:+.1f} f24 da âncora ({anc})")
        # saída: silêncio, fronteira de palavra ou emenda
        if cutaway:
            eps = 0.005
            no_sil = any(s["t"] + 0.06 - eps <= t1 <= s["e"] - 0.06 + eps for s in sils)
            front = any(a["e"] - 0.04 - eps <= t1 <= b["t"] + 0.04 + eps for a, b in zip(pal, pal[1:])) or \
                any(abs(t1 - c) <= 0.04 + eps for c in cortes) or t1 >= R.DUR - 0.05
            cena["saida"] = {"t1": t1, "silencio": no_sil, "fronteira": front, "ok": no_sil or front}
            if not (no_sil or front):
                res["fora"].append(f"{name}: sai em {t1:.2f} s no meio de uma palavra")
        # hold e END
        hold = total24 - ultimo
        cena["hold_f24"] = round(hold, 1)
        cena["hold_ok"] = 8 <= hold <= 18
        if st:
            cena["end_ok"] = st.get("END", 0) >= ultimo
            if not cena["end_ok"]:
                res["fora"].append(f"{name}: END f{st.get('END')} antes do último evento f{ultimo}")
        res["cenas"].append(cena)
        for e in cena["eventos"]:
            linhas.append(f"| {name} | {e['evento']} | f{e['f24']} | {e['t']:.2f} | {e['palavra']} | {e['delta_f24']:+.1f} | "
                          f"{e['delta_ms']:+d} ms | {'OK' if e['ok'] else 'FORA'} |")
    out = ROOT / "05_motion"
    out.mkdir(exist_ok=True)
    (out / "ANCORAGEM.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# ANCORAGEM — gerada por ancorar.py (nunca a mão)", "",
          "| cena | evento | frame24 | tempo (s) | palavra mais próxima | Δ f24 | Δ ms | ok |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    md += linhas
    md += ["", "## Entrada, saída e hold", ""]
    for c in res["cenas"]:
        en, sa = c.get("entrada", {}), c.get("saida", {})
        md.append(f"- {c['cena']}: entrada {en.get('delta_f24', '—')} f24 da âncora · saída {c['t1']:.2f} s "
                  f"({'silêncio' if sa.get('silencio') else 'fronteira de palavra' if sa.get('fronteira') else 'NA SÍLABA'}) · "
                  f"hold {c['hold_f24']} f24 {'ok' if c['hold_ok'] else '(fora de 8–18)'}")
    md += ["", "## FORA", ""] + ([f"- {x}" for x in res["fora"]] or ["- nada"])
    (out / "ANCORAGEM.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"  {sum(len(c['eventos']) for c in res['cenas'])} eventos em {len(res['cenas'])} cenas; FORA: {len(res['fora'])}")
    for x in res["fora"]:
        print("   FORA", x)
    return res


def blueprints():
    """M#_motion.md e TRANSITION_MAP.md GERADOS da tabela B + M#_EVENTS (uma fonte só)."""
    sys.path.insert(0, str(ROOT))
    import render as R
    import compose as C
    plano = tabela_b()
    anc = json.loads((ROOT / "05_motion" / "ANCORAGEM.json").read_text(encoding="utf-8"))
    por = {c["cena"]: c for c in anc["cenas"]}
    tm = ["# TRANSITION_MAP — gerado por ancorar.py --blueprints (fonte: tabela B do plano)", "",
          "| cena | entra | t0 | sai | t1 | fim de cena (plano) | EXIT_KIND (render.py) |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, fn, t0, t1, total24, cutaway in R.SHOTS:
        row = plano.get(name, {})
        ev = por.get(name, {}).get("eventos", [])
        L = [f"# {name} — gerado de PLANO_MOTION.md (tabela B) e compose.py", "",
             f"referencia: {_col(row, 'referencia') or 'FALTA'}",
             f"registro: {_col(row, 'registro')}", f"janela: {t0:.2f}–{t1:.2f} s ({total24} frames24)",
             f"o que aparece: {_col(row, 'o que aparece')}", f"referente: {_col(row, 'referente')}",
             f"se mexe (plano): {_col(row, 'se mexe')}", f"layout H: {_col(row, 'layout h')}",
             f"motivo: {_col(row, 'motivo')}", "", "| evento | frame24 | tempo | palavra | Δ f24 |", "| --- | --- | --- | --- | --- |"]
        L += [f"| {e['evento']} | {e['f24']} | {e['t']:.2f} | {e['palavra']} | {e['delta_f24']:+.1f} |" for e in ev]
        (ROOT / "05_motion" / f"{name}_motion.md").write_text("\n".join(L) + "\n", encoding="utf-8")
        tm.append(f"| {name} | {_col(row, 'entra')[:40]} | {t0:.2f} | | {t1:.2f} | {_col(row, 'fim de cena')} | "
                  f"{getattr(R, 'EXIT_KIND', {}).get(name, 'slide') if cutaway else 'overlay'} |")
    d = ROOT / "06_transitions"
    d.mkdir(exist_ok=True)
    (d / "TRANSITION_MAP.md").write_text("\n".join(tm) + "\n", encoding="utf-8")
    print(f"  blueprints: {len(R.SHOTS)} cenas + TRANSITION_MAP.md")


if __name__ == "__main__":
    r = ancorar()
    if "--blueprints" in sys.argv:
        blueprints()
    sys.exit(1 if r["fora"] else 0)
