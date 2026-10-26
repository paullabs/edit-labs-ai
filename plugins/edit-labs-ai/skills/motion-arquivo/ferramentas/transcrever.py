#!/usr/bin/env python3
"""
Narracao -> palavras com inicio e fim (faster-whisper large-v3-turbo).

    mvpy transcrever.py <audio-ou-video> <projeto>/transcricao.json [idioma]

O tempo vem do AUDIO, nunca do roteiro. Modelo menor erra o inicio da palavra em ate
~0,15 s — meio degrau da grade de 10 qps; nao trocar.
"""
import json, os, subprocess, sys, tempfile
from faster_whisper import WhisperModel

ent, sai = sys.argv[1], sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else None
with tempfile.TemporaryDirectory() as d:
    wav = os.path.join(d, "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ent, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    m = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")
    segs, info = m.transcribe(wav, language=lang, word_timestamps=True, beam_size=5, vad_filter=False,
                              condition_on_previous_text=False)
    palavras = [dict(w=w.word.strip(), t=round(w.start, 3), e=round(w.end, 3)) for s in segs for w in (s.words or [])]
json.dump(dict(idioma=info.language, palavras=palavras), open(sai, "w"), ensure_ascii=False, indent=1)
print(f"{len(palavras)} palavras ({info.language}) -> {sai}")
