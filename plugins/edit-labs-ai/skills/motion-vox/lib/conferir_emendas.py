#!/usr/bin/env python3
"""
Confere cada emenda do clipe OUVINDO de novo, numa janela curta e isolada (±1,3 s).

Por que existe: o Whisper rodado no clipe inteiro "completa" a emenda com palavras que ninguém disse —
uma frase curta inteira pode entrar no transcript e ir para a legenda queimada. Em janela curta, sem
o contexto anterior, ele não inventa.

Uso, da pasta do projeto (precisa de 00_brief/fonte.mp4, cortes.json e transcript_palavras.json):
    python3 conferir_emendas.py
Para cada emenda, mostra o que o transcript do clipe inteiro tem e o que a janela isolada ouviu, e marca
com ✗ as palavras que só existem no primeiro. Palavra marcada: confira e, se for invenção, ponha em
`00_brief/legenda_correcoes.json` → "remover" (o legenda_transcript.py aplica).
Cuidado com falso alarme na BORDA da janela: palavra cortada no começo ou no fim da janela some do
isolado sem ter sido inventada — na dúvida, rode de novo só aquele trecho, com a janela deslocada.
"""
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

B = Path.cwd() / "00_brief"
MODELO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def _n(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


def main():
    from faster_whisper import WhisperModel
    ws = json.loads((B / "transcript_palavras.json").read_text(encoding="utf-8"))
    cortes = json.loads((B / "cortes.json").read_text(encoding="utf-8"))["cortes"]
    idioma = sys.argv[1] if len(sys.argv) > 1 else "pt"
    m = WhisperModel(MODELO, device="cpu", compute_type="int8")
    suspeitas = 0
    for c in cortes:
        a, b = max(0.0, c - 1.3), c + 1.3
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", str(B / "fonte.mp4"),
                              "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
        segs = list(m.transcribe(np.frombuffer(raw, np.float32), language=idioma, word_timestamps=True,
                                 condition_on_previous_text=False, beam_size=5)[0])
        iso = [w.word.strip() for s in segs for w in s.words]
        cheio = [(w["w"], w["t"]) for w in ws if a + 0.25 <= w["t"] <= b - 0.25]
        so_cheio = [(p, t) for p, t in cheio if _n(p) not in {_n(x) for x in iso}]
        print(f"emenda {c:7.2f} s")
        print(f"   clipe inteiro : {' '.join(p for p, _ in cheio)}")
        print(f"   janela isolada: {' '.join(iso)}")
        if so_cheio:
            suspeitas += 1
            print("   ✗ só no clipe inteiro: " + ", ".join(f"{p} ({t:.2f} s)" for p, t in so_cheio))
    print(f"\n{suspeitas} emenda(s) com palavra suspeita de {len(cortes)}")


if __name__ == "__main__":
    main()
