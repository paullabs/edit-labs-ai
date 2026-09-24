#!/usr/bin/env python3
"""Testa pontos candidatos de borda OUVINDO: transcreve alguns segundos e mostra o que sobra.

    python3 testar_borda.py <video> in  <t1> <t2> ...   # transcreve [t, t+3,5 s]: começa na palavra certa?
    python3 testar_borda.py <video> out <t1> <t2> ...   # transcreve [t-4 s, t]: termina na palavra certa?

Nem o tempo por palavra do YouTube nem a energia do áudio acham a borda sozinhos.
Este é o juiz: o Whisper diz se a primeira/última palavra pretendida está inteira e
se sobrou pedaço da vizinha. Uma palavra que termina colada no fim do trecho
(< 60 ms) ou que dura < 80 ms é marcada como provável corte (✂).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

MODELO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def trecho(video: str, a: float, dur: float, dst: Path) -> None:
    ss = max(0.0, a - 2)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss:.3f}", "-i", video, "-ss", f"{a - ss:.3f}",
                    "-t", f"{dur:.3f}", "-vn", "-ac", "1", "-ar", "16000", str(dst)], check=True)


def main(video: str, lado: str, ts: list[float]) -> None:
    m = WhisperModel(MODELO, device="cpu", compute_type="int8")
    with tempfile.TemporaryDirectory() as tmp:
        for t in ts:
            a, dur = (t, 3.5) if lado == "in" else (t - 4.0, 4.0)
            wav = Path(tmp) / f"{t}.wav"
            trecho(video, a, dur, wav)
            segs, _ = m.transcribe(str(wav), language="pt", word_timestamps=True)
            ws = [(w.start, w.end, w.word.strip()) for s in segs for w in s.words]
            if lado == "in":
                mostra = ws[:6]
                suspeita = bool(ws) and (ws[0][1] - ws[0][0] < 0.08)
            else:
                mostra = ws[-6:]
                suspeita = bool(ws) and (dur - ws[-1][1] < 0.06 or ws[-1][1] - ws[-1][0] < 0.08)
            txt = " ".join(f"{w}({s:.2f}-{e:.2f})" for s, e, w in mostra)
            print(f"{lado} {t:.2f} {'✂ ' if suspeita else '  '}→ {txt}")


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[2] not in ("in", "out"):
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3:]])
