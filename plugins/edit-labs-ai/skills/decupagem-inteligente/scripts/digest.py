"""O que o Editor lê em vez do transcript: uma linha por frase (§05, corte-viral `vch digest`).

  di digest                  escreve 01_transcript/digest.md (inteiro, ou por --parte N em bruto longo)
  di digest --janela a-b     imprime as palavras com tempo só daquele trecho (para cravar um ponto)
  di digest --parte N        só a parte N de leitura (≤ 10 min)

Marcas: ✓ tomada sugerida · G07 t2/4 grupo e tomada · ½+F024 metade (junto com a vizinha forma uma tomada) · B bastidor · c cauda de bastidor · x autocorreção
        … frase que morre em reticência · ~ alucinação suspeita · g gagueira · h hesitações · ?palavra em dúvida
"""
from __future__ import annotations

import argparse
from pathlib import Path

from comum import DIError, achar_projeto, check, gravar_texto, ler_json, mmss, registrar_checks

PARTE_S = 600
AVISO_TOK, BLOQ_TOK = 12000, 30000


def linhas(projeto: Path, t0: float = 0.0, t1: float = 1e9) -> list[str]:
    r = ler_json(projeto / "02_decupagem" / "retakes.json")
    pal = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    if not r:
        raise DIError("retakes.json ainda não existe (a leitura terminou? di status)")
    ntom = {g["id"]: len(g["tomadas"]) for g in r["grupos"]}
    metade = {t["frase"]: t["metade_com"] for g in r["grupos"] for t in g["tomadas"] if t.get("metade_com")}
    fr = {f["entre"][0]: f for f in r["fronteiras_sugeridas"]}
    parc = {p["frase_b"]: p for p in r["retakes_parciais"]}
    out = []
    ant = None
    for f in r["frases"]:
        if f["t"] < t0 or f["t"] > t1:
            continue
        if ant is not None and f["t"] - ant > 1.5:
            out.append(f"   · silêncio {f['t'] - ant:.1f} s")
        marcas = []
        if f.get("grupo"):
            marcas.append(f"{f['grupo']} t{f['tomada']}/{ntom[f['grupo']]}" + (" ✓" if f.get("sugerida") else "")
                          + (f" ½+F{metade[f['id']]:03d}" if f["id"] in metade else ""))
        for k, s in (("bastidor", "B"), ("cauda_bastidor", "c"), ("autocorrecao", "x"), ("reticencia", "…"),
                     ("alucinacao_suspeita", "~"), ("gagueira", "g")):
            if f.get(k):
                marcas.append(s)
        for r_ in f.get("repeticao_interna", []):
            marcas.append(f"r@{r_['repete_em']}")
        if f["n_fillers"]:
            marcas.append(f"h{f['n_fillers']}")
        if f["id"] in parc:
            p = parc[f["id"]]
            marcas.append(f"parcial←F{p['frase_a']:03d}@{p['palavra_em_a']}")
        amb = {k for k in f.get("ambiguas", [])}
        texto = " ".join(("?" + pal[k]["w"]) if k in amb else pal[k]["w"] for k in range(f["i0"], f["i1"] + 1))
        rms = f" {f['rms_db']:.0f}dB" if f.get("rms_db") is not None else ""
        out.append(f"[{mmss(f['t'])}–{mmss(f['e'])}] F{f['id']:03d} {' '.join(marcas)} «{texto}» p{f['p_media']:.2f}{rms} {f['pal_por_s']:.1f}p/s")
        if f["id"] in fr:
            x = fr[f["id"]]
            out.append(f"===== fronteira possível: silêncio {x['silencio_s']:.1f} s, {x['bastidor_perto']} frase(s) de bastidor perto =====")
        ant = f["e"]
    return out


def escrever(projeto: Path, parte: int | None = None) -> Path:
    projeto = Path(projeto)
    pal = ler_json(projeto / "01_transcript" / "palavras.json")
    dur = pal["duracao"]
    r = ler_json(projeto / "02_decupagem" / "retakes.json")
    cab = [f"# DIGEST — {projeto.name} · {mmss(dur)} · {pal['engine']} {pal['modelo'].split('/')[-1]}",
           f"{r['resumo']['frases']} frases · {r['resumo']['grupos']} grupos de tomada · {r['resumo']['parciais']} retakes parciais · "
           f"{r['resumo']['bastidor']} bastidor · {r['resumo']['fillers_isolados']} hesitações isoladas",
           "Legenda: ✓ sugerida · G07 t2/4 · B bastidor · c cauda · x autocorreção · … reticência · ~ alucinação · g gagueira · "
           "h hesitações · r@412 repete dentro da frase a partir da palavra 412 · ?palavra em dúvida · parcial←F012@340 = retake parcial (índice da palavra onde a repetição começa)",
           "Tempos no relógio do BRUTO. Janela com tempo por palavra: di digest --janela a-b", ""]
    if parte is not None:
        t0, t1 = parte * PARTE_S, (parte + 1) * PARTE_S
        corpo = linhas(projeto, t0, t1)
        destino = projeto / "01_transcript" / f"digest_parte{parte:02d}.md"
    else:
        corpo = linhas(projeto)
        destino = projeto / "01_transcript" / "digest.md"
    texto = "\n".join(cab + corpo) + "\n"
    gravar_texto(destino, texto)
    tok = len(texto) // 4
    if parte is None:
        registrar_checks(projeto, "F1", [check(
            "V13_digest", tok <= AVISO_TOK, "aviso" if tok <= BLOQ_TOK else "BLOCKER", medido=f"~{tok} tokens",
            esperado=f"≤ {AVISO_TOK} (acima: ler por --parte N; > {BLOQ_TOK} sem --parte = BLOCKER)")],
            alvo="01_transcript/digest.md")
        if tok > AVISO_TOK:
            for n in range(int(dur // PARTE_S) + 1):
                escrever(projeto, n)
    return destino


def janela(projeto: Path, a: float, b: float) -> str:
    pal = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    sil = (ler_json(projeto / "01_transcript" / "silencios.json") or {}).get("silencios", [])
    out = []
    for w in pal:
        if a <= w["t"] <= b:
            s = next((x for x in sil if w["e"] - 0.02 <= x["t"] <= w["e"] + 0.3), None)
            gap = f"  ⟂{s['d']:.2f}s" if s else ""
            flag = " ?" if w.get("ambigua") else ""
            out.append(f"{w['i']:>5} {w['t']:8.2f}–{w['e']:8.2f}  {w['w']}{flag}  p{w['p'] or 0:.2f}{gap}")
    return "\n".join(out)


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di digest")
    ap.add_argument("--janela", help="a-b em segundos do bruto")
    ap.add_argument("--parte", type=int)
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    if a.janela:
        x, y = (float(v) for v in a.janela.split("-"))
        print(janela(projeto, x, y))
        return 0
    p = escrever(projeto, a.parte)
    print(f"✓ {p} (~{len(p.read_text(encoding='utf-8')) // 4} tokens)")
    return 0
