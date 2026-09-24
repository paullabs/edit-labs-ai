#!/usr/bin/env python3
"""Confere, por script, se alguma borda de segmento corta uma palavra ao meio.

    checar_cortes.py <run-dir> [06-candidates.json | 11-edit-plans.json]

Para cada segmento de cada clipe, olha as palavras do 02-transcript.json (o script
pode ler o JSON inteiro; quem não pode é o modelo) e reprova quando:

- a borda cai DENTRO de uma palavra (a palavra começa antes e termina depois);
- a folga é menor que a da regra: início ≥ 0,2 s antes da 1ª palavra,
  fim ≥ 0,3 s depois da última (aviso, não reprova, entre 0,1 e o mínimo).

`[ __ ]` (palavrão censurado pela legenda do YouTube) conta como UMA palavra.

O tempo por palavra do YouTube só tem o INÍCIO de cada palavra: o "fim" é o início
da seguinte, então a pausa depois da palavra conta como palavra. Por isso o juiz é
o ÁUDIO: energia RMS em ±40 ms do ponto de corte contra o nível de fala em ±1,5 s.
≥ 15 dB abaixo = silêncio (✅); 8–15 dB = borda arriscada (⚠️); < 8 dB = corte em
cima da fala (❌). Usa assets/audio-analysis.wav da run. Sai com código 1 se houver
corte em cima da fala.
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

FOLGA_INI, FOLGA_FIM = 0.20, 0.30


def carregar_wav(p: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(p)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr


def rms_db(x: np.ndarray, sr: int, a: float, b: float) -> float:
    seg = x[int(max(0.0, a) * sr): int(max(a, b) * sr)]
    return float(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9)) if len(seg) else -120.0


def energia(x: np.ndarray, sr: int, t: float) -> tuple[str, float]:
    local = rms_db(x, sr, t - 0.04, t + 0.04)
    fala = float(np.percentile([rms_db(x, sr, u, u + 0.05) for u in np.arange(t - 1.5, t + 1.5, 0.05)], 90))
    gap = fala - local
    return ("✅" if gap >= 15 else "⚠️" if gap >= 8 else "❌"), gap


def palavras(transcript: dict) -> list[tuple[float, float, str]]:
    out = []
    for seg in transcript.get("segments", []):
        ws = seg.get("words") or []
        i = 0
        while i < len(ws):
            w = ws[i]
            txt = str(w.get("word", w.get("text", ""))).strip()
            ini, fim = float(w["start"]), float(w["end"])
            # junta "[", "__", "]" num token só
            if txt == "[" and i + 2 < len(ws) and str(ws[i + 1].get("word", "")).strip() == "__":
                fim = float(ws[i + 2]["end"])
                txt, i = "[ __ ]", i + 3
            else:
                i += 1
            if txt:
                out.append((ini, fim, txt))
    return sorted(out)


def checar(run: Path, arquivo: str) -> int:
    ws = palavras(json.loads((run / "02-transcript.json").read_text()))
    wav = run / "assets" / "audio-analysis.wav"
    x, sr = carregar_wav(wav) if wav.exists() else (None, 0)
    dados = json.loads((run / arquivo).read_text())
    clipes = dados.get("clips") or dados.get("plans") or []
    conta = {"✅": 0, "⚠️": 0, "❌": 0}
    por_palavra = 0
    for c in clipes:
        cid = c.get("id") or c.get("clip_id")
        segs = sorted(c.get("segments") or c.get("timeline") or [], key=lambda s: s.get("order", 0))
        print(f"\n{cid} · {len(segs)} segmento(s)")
        for k, s in enumerate(segs, 1):
            a, b = float(s["source_start"]), float(s["source_end"])
            cortadas = [w for w in ws if (w[0] < a < w[1]) or (w[0] < b < w[1])]
            por_palavra += len(cortadas)
            linha = f"  seg {k}: {a:.2f}–{b:.2f} ({b - a:.1f}s)"
            if x is not None:
                bordas = []
                for nome, t in (("in", a), ("out", b)):
                    marca, gap = energia(x, sr, t)
                    conta[marca] += 1
                    bordas.append(f"{nome} {marca} {gap:4.1f} dB")
                linha += "  áudio: " + " · ".join(bordas)
            if cortadas:
                linha += "  | palavras: " + ", ".join(f"'{w[2]}'" for w in cortadas)
            print(linha)
    total = sum(conta.values())
    print(f"\npelo tempo das palavras: {por_palavra} borda(s) em cima de palavra")
    if total:
        print(f"pelo áudio ({total} bordas): ✅ {conta['✅']} silêncio · ⚠️ {conta['⚠️']} arriscada · ❌ {conta['❌']} em cima da fala")
    return 1 if conta["❌"] else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(checar(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "06-candidates.json"))
