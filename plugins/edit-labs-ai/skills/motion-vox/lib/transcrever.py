#!/usr/bin/env python3
"""
Transcript palavra a palavra — o insumo sem substituto.

Sem timestamp POR PALAVRA nao existe motion ancorado nem legenda em corte seco: os dois
dependem de saber em que frame cada palavra foi dita. Transcript por frase nao serve.

    python3 lib/transcrever.py fonte.mp4 00_brief/transcript_palavras.json [--pt]

Saida: `[{"w": "palavra", "t": 12.28, "e": 12.54}, ...]` em segundos do CLIPE (nao do
episodio original). E o formato que `lib/captions.py` le.

O modelo baixa na primeira execucao (~1,5 GB) e fica em cache. `large-v3-turbo` e o
modelo da calibracao; modelos menores erram o inicio da palavra em ate ~0,15s, o que a
30fps ja e meio bloco de legenda fora de lugar.
"""
import json
import subprocess
import sys
from pathlib import Path

MODELO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def transcrever(video, destino, lang="pt", modelo=MODELO):
    video, destino = Path(video), Path(destino)
    wav = destino.parent / "_audio_16k.wav"
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video),
                    "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faltou `pip install faster-whisper`")

    m = WhisperModel(modelo, device="cpu", compute_type="int8")
    # vad_filter=False: o VAD corta respiracao e desloca o inicio da primeira palavra.
    # condition_on_previous_text=False: evita o modelo "continuar" uma frase inventada
    # quando o clipe comeca no meio de uma fala, que e o caso normal num corte.
    segs, _ = m.transcribe(str(wav), language=lang, word_timestamps=True, beam_size=5,
                           vad_filter=False, condition_on_previous_text=False)
    words = [dict(w=w.word.strip(), t=round(w.start, 3), e=round(w.end, 3))
             for s in segs for w in (s.words or [])]
    wav.unlink(missing_ok=True)
    if not words:
        raise SystemExit("nenhuma palavra reconhecida — confira idioma e audio")
    json.dump(words, open(destino, "w"), ensure_ascii=False, indent=0)
    print(f"{len(words)} palavras  {words[0]['t']:.2f} -> {words[-1]['e']:.2f}s"
          f"  -> {destino}")
    print(" ".join(x["w"] for x in words))
    return words


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    lang = "pt" if "--pt" in sys.argv or True else "pt"
    transcrever(sys.argv[1], sys.argv[2], lang=lang)
