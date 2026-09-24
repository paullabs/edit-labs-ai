#!/usr/bin/env python3
"""
Transcript DA LEGENDA (00_brief/transcript_legenda.json), separado do transcript de ANCORAGEM
(transcript_palavras.json, que o compose usa e que fica intacto). Aplica, nesta ordem:
  1. remover: palavra que o Whisper inventou (emenda conferida em janela isolada; alucinação no fade)
  2. trocar: grafia confirmada (nome, marca, vocativo)
  3. mascarar palavrão: 1ª vogal depois da 1ª letra vira '*' (p*rra, c*ralho)
Uso, da pasta do projeto:  python3 legenda_transcript.py
Lê 00_brief/legenda_correcoes.json: {"remover": [[palavra, t], ...], "trocar": [[palavra, t, nova], ...]}
"""
import json
import re
import unicodedata
from pathlib import Path

B = Path.cwd() / "00_brief"
PALAVROES = ("porra", "caralh", "puta", "puto", "putari", "merda", "foda", "fode", "fodi", "cacete",
             "bosta", "buceta", "arrombad")
VOGAIS = "aeiouáéíóúâêôãõà"


def _n(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def mascara(w):
    m = re.match(r"^(\W*)(\w+)(\W*)$", w)
    if not m or not any(_n(m.group(2)).startswith(p) for p in PALAVROES):
        return w
    ini, corpo, fim = m.groups()
    for i in range(1, len(corpo)):
        if corpo[i].lower() in VOGAIS:
            return ini + corpo[:i] + "*" + corpo[i + 1:] + fim
    return w


def _acha(ws, palavra, t):
    k = [i for i, w in enumerate(ws) if _n(w["w"]) == _n(palavra) and abs(w["t"] - t) < 0.15]
    if len(k) != 1:
        raise SystemExit(f"'{palavra}' em {t}s: {len(k)} ocorrências (esperava 1)")
    return k[0]


def main():
    ws = json.loads((B / "transcript_palavras.json").read_text(encoding="utf-8"))
    cor = json.loads((B / "legenda_correcoes.json").read_text(encoding="utf-8"))
    for palavra, t, nova in cor.get("trocar", []):
        ws[_acha(ws, palavra, t)]["w"] = nova
    fora = sorted({_acha(ws, p, t) for p, t in cor.get("remover", [])}, reverse=True)
    for i in fora:
        ws.pop(i)
    n_mask = 0
    for w in ws:
        m = mascara(w["w"])
        n_mask += m != w["w"]
        w["w"] = m
    (B / "transcript_legenda.json").write_text(json.dumps(ws, ensure_ascii=False), encoding="utf-8")
    print(f"  legenda: {len(ws)} palavras · {len(fora)} removidas · {len(cor.get('trocar', []))} trocadas"
          f" · {n_mask} palavrões mascarados")


if __name__ == "__main__":
    main()
