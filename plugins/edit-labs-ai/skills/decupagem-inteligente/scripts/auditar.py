"""Auditoria frase a frase do corte — a primeira coisa a abrir antes de mandar a prévia e quando o usuário reprova.

  di auditar <id>

Para cada frase do corte: o tempo no corte e no bruto, o que o EDL diz, o que a retranscrição do render diz
e o que pode estar errado. Existe porque um falso começo pode passar pelo corte inteiro: o
Whisper engole a primeira passada dentro de um "criou" de 2,72 s, nenhum texto repetia, e ninguém olhou a
frase junto do tempo dela. Aqui cada frase é lida com o tempo, o vão e a voz medida — e com a vizinha.

Alertas (medidos, nunca "ouvidos"):
  ESTICADA      palavra mantida que dura > 1,2 s dentro do corte com voz em mais da metade (fala engolida)
  VÃO COM VOZ   vão > 0,6 s entre palavras vizinhas do bruto com voz em mais de 35 % dele
  REPETE        3 palavras seguidas que já apareceram na frase anterior ou na mesma (retake, falso começo)
  RENDER REPETE a retranscrição do render repete 3 palavras dentro da frase (falso começo que o texto não mostra)
  RENDER DIVERGE o que o render diz não bate com o que o EDL diz (semelhança < 80 %)
  INCERTA       palavra com confiança < 0,5
  EMENDA        a frase tem emenda no meio (informação: confira a prévia nesse ponto)
Saída: 03_corte/<id>/AUDITORIA.md e AUDITORIA.json.
"""
from __future__ import annotations

import argparse
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

import silencio as SIL
from comum import DIError, achar_projeto, gravar_json, gravar_texto, ler_json, mmss, norm_palavra

ESTICADA_S = 1.2
VAO_S = 0.6


def _voz(x, sr: int, a: float, b: float, lim: float) -> float:
    """Fração de janelas de 50 ms com energia acima do limiar de voz, entre a e b (segundos do bruto)."""
    if b - a <= 0.05:
        return 0.0
    w = np.asarray(x[int(a * sr):int(b * sr)], dtype=float)
    n = max(1, int(0.05 * sr))
    blocos = [w[k:k + n] for k in range(0, len(w) - n + 1, n)]
    if not blocos:
        return 0.0
    db = [20 * math.log10(math.sqrt(float(np.mean(bl ** 2))) + 1e-9) for bl in blocos]
    return sum(1 for d in db if d > lim) / len(db)


def _trigramas(ws: list[str]) -> list[tuple]:
    return [tuple(ws[k:k + 3]) for k in range(len(ws) - 2)]


def auditar(projeto: Path, vid: str) -> Path:
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
    if not edl:
        raise DIError(f"sem edl.json para {vid}: rode di edl {vid}")
    pal = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    silj = ler_json(projeto / "01_transcript" / "silencios.json") or {}
    lim = float(silj.get("limiar_db", -40.0)) + 8
    x, sr = SIL.carregar_wav(projeto / "00_fonte" / "_audio_16k.wav")
    segs = edl["segmentos"]
    mant = [i for i in (edl.get("palavras_mantidas") or []) if 0 <= i < len(pal)]
    if not mant:
        mant = [i for s in segs for i in range(s["palavra_in"], s["palavra_out"] + 1)]
    seg_de = {}
    for s in segs:
        for i in range(s["palavra_in"], s["palavra_out"] + 1):
            seg_de[i] = s

    def no_corte(i: int, campo: str = "t") -> float:
        s = seg_de.get(i)
        if not s:
            return 0.0
        t = pal[i][campo] - s["source_in"] + s["timeline_in"]
        return min(max(t, s["timeline_in"]), s["timeline_out"])

    # frases do CORTE na unidade que a skill já usa (retakes.json, F001…): palavras mantidas seguidas da
    # mesma frase E do mesmo trecho. Quebrar só por pontuação juntava o vídeo inteiro numa "frase" (o
    # Whisper nem sempre põe ponto), e aí tudo parecia repetição.
    rt = ler_json(projeto / "02_decupagem" / "retakes.json") or {}
    frase_de = {}
    for f in rt.get("frases") or []:
        for i in range(f["i0"], f["i1"] + 1):
            frase_de[i] = f["id"]
    frases, atual, chave = [], [], None
    for i in mant:
        ch = (frase_de.get(i), id(seg_de.get(i)))
        if atual and (ch != chave or (frase_de.get(i) is None and re.search(r"[.?!]$", pal[atual[-1]]["w"]))):
            frases.append(atual)
            atual = []
        atual.append(i)
        chave = ch
    if atual:
        frases.append(atual)

    ren = ler_json(projeto / "03_corte" / vid / "palavras_render.json")
    rw = (ren or {}).get("palavras") or []
    out, ant_norm = [], []
    for k, idx in enumerate(frases):
        t0, t1 = no_corte(idx[0], "t"), no_corte(idx[-1], "e")
        b0, b1 = pal[idx[0]]["t"], pal[idx[-1]]["e"]
        texto = " ".join(pal[i]["w"] for i in idx)
        norm = [norm_palavra(pal[i]["w"]) for i in idx if norm_palavra(pal[i]["w"])]
        alertas = []
        # palavra esticada com voz, medida só no pedaço que ficou no corte
        for i in idx:
            s = seg_de.get(i)
            if not s:
                continue
            a0, a1 = max(pal[i]["t"], s["source_in"]), min(pal[i]["e"], s["source_out"])
            if a1 - a0 > ESTICADA_S:
                v = _voz(x, sr, a0, a1, lim)
                if v > 0.5:
                    alertas.append(f"ESTICADA: '{pal[i]['w']}' #{i} dura {a1 - a0:.2f} s no bruto ({mmss(a0)}–{mmss(a1)}) com voz em {100 * v:.0f} % — fala engolida pelo transcript")
            # o Whisper sempre estica a 1ª palavra ~0,1–0,4 s para trás (a entrada é pela voz medida): só
            # acusa quando o tempo do texto está BEM antes do trecho — sinal de palavra de outra passada
            if pal[i]["t"] < s["source_in"] - 0.8:
                alertas.append(f"TEMPO: '{pal[i]['w']}' #{i} tem no transcript o tempo {mmss(pal[i]['t'])}, antes do trecho mantido ({mmss(s['source_in'])}) — o texto vale pela tomada que ficou; confira na prévia")
            if (pal[i].get("p") or 1.0) < 0.5 and len(norm_palavra(pal[i]["w"])) >= 4:   # "e", "o", "se" com p baixa é ruído
                alertas.append(f"INCERTA: '{pal[i]['w']}' #{i} (confiança {pal[i]['p']:.2f})")
        # vão com voz entre vizinhas do bruto que ficaram juntas no corte
        for a, b in zip(idx, idx[1:]):
            if b != a + 1 or seg_de.get(a) is not seg_de.get(b):
                continue
            vao = pal[b]["t"] - pal[a]["e"]
            if vao > VAO_S:
                v = _voz(x, sr, pal[a]["e"], pal[b]["t"], lim)
                if v > 0.35:
                    alertas.append(f"VÃO COM VOZ: {vao:.2f} s entre '{pal[a]['w']}' e '{pal[b]['w']}' ({mmss(pal[a]['e'])}–{mmss(pal[b]['t'])}), voz em {100 * v:.0f} %")
        # repetição no texto: dentro da frase e contra a anterior
        tri = _trigramas(norm)
        vistos = set(_trigramas(ant_norm))
        rep = [" ".join(t) for n_, t in enumerate(tri) if t in vistos or t in tri[:n_]]
        if rep:
            alertas.append(f"REPETE: «{rep[0]}» já foi dito na mesma frase ou na anterior — retake ou falso começo?")
        # emenda no meio da frase
        cortes_meio = [s["timeline_in"] for s in segs if t0 + 0.05 < s["timeline_in"] < t1 - 0.05]
        if cortes_meio:
            alertas.append("EMENDA: dentro da frase em " + ", ".join(f"{c:.2f} s" for c in cortes_meio) + " — confira na prévia")
        # o que o render diz
        diz = ""
        if rw:
            # só a palavra cujo MEIO cai na frase: a janela folgada puxava a 1ª palavra da frase seguinte
            dentro = [w for w in rw if t0 <= (w["t"] + w["e"]) / 2 <= t1]
            diz = " ".join(w["w"] for w in dentro)
            rn = [norm_palavra(w["w"]) for w in dentro if norm_palavra(w["w"])]
            # grafia vizinha conta como a mesma palavra ("cloud"/"claude", "antropic"/"anthropic"): a
            # divergência que interessa é palavra que falta ou sobra, não ortografia do transcript
            rn = [next((e for e in norm if SequenceMatcher(None, e, r).ratio() >= 0.75), r) for r in rn]
            trn = _trigramas(rn)
            rrep = [" ".join(t) for n_, t in enumerate(trn) if t in trn[:n_]]
            if rrep and not rep:
                alertas.append(f"RENDER REPETE: o áudio do corte repete «{rrep[0]}» — falso começo que o texto do EDL não mostra")
            sim = SequenceMatcher(None, norm, rn, autojunk=False).ratio() if norm and rn else 1.0
            if sim < 0.8:
                alertas.append(f"RENDER DIVERGE: semelhança {100 * sim:.0f} % entre o EDL e o que o render diz")
        out.append({"n": k + 1, "frase": frase_de.get(idx[0]), "corte": [round(t0, 2), round(t1, 2)], "bruto": [round(b0, 2), round(b1, 2)],
                    "texto": texto, "render": diz, "alertas": alertas})
        ant_norm = norm

    com = [f for f in out if f["alertas"]]
    L = [f"# Auditoria frase a frase — {vid}", "",
         f"{len(out)} frases · {edl['duracao']:.2f} s · {len(segs)} trechos · **{len(com)} frase(s) com alerta**"
         + ("" if rw else " · sem retranscrição do render (rode `di verificar-corte " + vid + "` para ter a coluna «render diz»)"), "",
         "Tempos medidos; ninguém aqui ouve. Frase com alerta é onde a prévia tem de ser conferida primeiro.", "",
         "| # | frase | corte | bruto | texto (EDL) | render diz | alertas |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for f in out:
        fid = f"F{int(f['frase']):03d}" if f.get("frase") is not None else "—"
        L.append(f"| {f['n']} | {fid} | {f['corte'][0]:.2f}–{f['corte'][1]:.2f} | {mmss(f['bruto'][0])}–{mmss(f['bruto'][1])} | "
                 f"{f['texto']} | {f['render'] or '—'} | {len(f['alertas']) or ''} |")
    L += ["", "## Frases com alerta, no contexto", ""]
    if not com:
        L.append("- nenhuma")
    for f in com:
        n = f["n"] - 1
        ant = out[n - 1]["texto"] if n > 0 else "(começo do vídeo)"
        dep = out[n + 1]["texto"] if n + 1 < len(out) else "(fim do vídeo)"
        L += [f"### Frase {f['n']} — corte {f['corte'][0]:.2f}–{f['corte'][1]:.2f} s · bruto {mmss(f['bruto'][0])}–{mmss(f['bruto'][1])}", "",
              f"- antes: {ant}", f"- **esta: {f['texto']}**", f"- depois: {dep}"]
        if f["render"]:
            L.append(f"- render diz: {f['render']}")
        L += [f"- {a}" for a in f["alertas"]]
        L += [f"- cravar no bruto: `di digest --janela {max(0, f['bruto'][0] - 3):.0f}-{f['bruto'][1] + 3:.0f}`", ""]
    dest = projeto / "03_corte" / vid
    dest.mkdir(parents=True, exist_ok=True)
    gravar_texto(dest / "AUDITORIA.md", "\n".join(L) + "\n")
    gravar_json(dest / "AUDITORIA.json", {"video": vid, "frases": out, "com_alerta": len(com)})
    return dest / "AUDITORIA.md"


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di auditar")
    ap.add_argument("video")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    p = auditar(projeto, a.video)
    d = ler_json(p.with_suffix(".json"))
    print(f"✓ {p} — {len(d['frases'])} frases, {d['com_alerta']} com alerta")
    for f in d["frases"]:
        for al in f["alertas"]:
            print(f"  frase {f['n']} ({f['corte'][0]:.2f} s): {al}")
    return 0
