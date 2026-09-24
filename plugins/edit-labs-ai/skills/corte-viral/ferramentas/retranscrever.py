#!/usr/bin/env python3
"""Transcreve de novo cada arquivo renderizado e compara com o texto pretendido.

    python3 retranscrever.py <run-dir> <pasta-com-mp4> [candidatos.json]

Para cada <NN>-<ID>.mp4: Whisper (large-v3-turbo, palavra a palavra) no arquivo
renderizado → <arquivo>.palavras.json, e compara com o `reconstructed_transcript`
do candidato:
- primeiras e últimas palavras (o corte começa e termina onde devia?);
- concordância de palavras (difflib), ignorando pontuação, "[ __ ]" e rótulos de
  locutor ("Fulano:", "[Fulano?]:");
- o que o Whisper ouviu onde a legenda do YouTube tinha "[ __ ]".
"""
import json
import re
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

from faster_whisper import WhisperModel

MODELO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"

# Rótulo de locutor no texto pretendido ("Fulano:", "[Fulano?]:", "Convidado 2:") não é fala.
# Entre colchetes vale em qualquer lugar; sem colchetes, só no começo da linha ou logo depois
# de um fim de frase — "o problema é este:" no meio da frase continua sendo fala, e dois-pontos
# seguido de número ("às 10:30") é hora, não rótulo.
ROTULO_LOCUTOR = re.compile(
    r"(?:\[[^\]\n]{1,40}\]\s*|(?:^|(?<=[.!?…]))\s*[^\W\d_]+(?: \w+)?\??):(?!\d)", re.M)


def norm(t: str) -> list[str]:
    t = re.sub(r"\[ ?__ ?\]", " ", t.lower())
    t = ROTULO_LOCUTOR.sub(" ", t)
    return re.findall(r"[a-zà-ú0-9]+", t)


def main(run: Path, pasta: Path, arq: str) -> None:
    clipes = {c["id"]: c for c in json.loads((run / arq).read_text())["clips"]}
    m = WhisperModel(MODELO, device="cpu", compute_type="int8")
    for mp4 in sorted(pasta.glob("*.mp4")):
        cid = next((k for k in clipes if k in mp4.stem), None)
        t0 = time.time()
        segs, _ = m.transcribe(str(mp4), language="pt", word_timestamps=True, vad_filter=False)
        ws = [{"w": w.word.strip(), "t": round(w.start, 3), "e": round(w.end, 3)} for s in segs for w in s.words]
        dt = time.time() - t0
        mp4.with_suffix(".palavras.json").write_text(json.dumps(ws, ensure_ascii=False, indent=0))
        ouvido = [w["w"] for w in ws]
        print(f"\n=== {mp4.name} · {len(ws)} palavras · Whisper {dt:.0f}s")
        print("  começa:", " ".join(ouvido[:8]))
        print("  termina:", " ".join(ouvido[-8:]))
        if cid:
            alvo = norm(clipes[cid].get("reconstructed_transcript", ""))
            got = norm(" ".join(ouvido))
            sm = SequenceMatcher(a=alvo, b=got, autojunk=False)
            print(f"  concordância com o texto pretendido: {sm.ratio():.0%} ({len(alvo)} pretendidas, {len(got)} ouvidas)")
            falta = [" ".join(alvo[i1:i2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("delete", "replace") and i2 - i1 >= 3]
            if falta:
                print("  trechos pretendidos que não foram ouvidos (≥3 palavras):", falta[:6])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    main(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "06-candidates.json")
