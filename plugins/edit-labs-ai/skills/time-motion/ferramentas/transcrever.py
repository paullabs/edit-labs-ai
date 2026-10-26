#!/usr/bin/env python3
"""Transcrição palavra a palavra (faster-whisper large-v3-turbo) do áudio do corte.

    python3 transcrever.py <video_ou_audio> <saida.json> [idioma]      (idioma padrão: pt)

Saída: {"fonte", "palavras": [{"palavra", "ini", "fim", "prob"}]}. O tempo vem do áudio, nunca do roteiro.
Depois rode ilhas_fala.py: o whisper às vezes põe o início de uma palavra dentro da pausa anterior."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from faster_whisper import WhisperModel

ent, sai = sys.argv[1], Path(sys.argv[2])
lang = sys.argv[3] if len(sys.argv) > 3 else "pt"
with tempfile.TemporaryDirectory() as tmp:
    wav = Path(tmp) / "a.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-map", "0:a:0", "-ac", "1", "-ar", "16000", str(wav)],
                   check=True)
    m = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(wav), language=lang, word_timestamps=True, beam_size=5, vad_filter=False,
                              condition_on_previous_text=False)
    palavras = []
    for s in segs:
        for w in s.words:
            palavras.append({"palavra": w.word.strip(), "ini": round(w.start, 3), "fim": round(w.end, 3),
                             "prob": round(w.probability, 3)})
sai.parent.mkdir(parents=True, exist_ok=True)
sai.write_text(json.dumps({"fonte": Path(ent).name, "palavras": palavras}, ensure_ascii=False, indent=1))
for p in palavras:
    print(f"{p['ini']:6.2f}–{p['fim']:6.2f}  {p['prob']:.2f}  {p['palavra']}")
