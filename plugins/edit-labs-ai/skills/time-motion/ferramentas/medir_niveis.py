#!/usr/bin/env python3
"""Mede cada efeito (a 0 dB) e calcula o ganho para ele cair N dB abaixo do momentâneo mediano da voz do corte.

    python3 medir_niveis.py <corte.mp4> <efeito.wav> [<efeito2.wav> ...] [--abaixo 17] [--saida niveis.json]

M400 = EBU R128 momentâneo (ffmpeg ebur128, janela de 400 ms). M200 = a mesma ponderação K numa janela de 200 ms:
o som curto (~140 ms) é diluído pela janela de 400 ms; 200 ms é o que o ouvido integra. O ganho usa o maior dos
dois. Regra do time: efeito 15–19 dB abaixo da voz (acento no limite de cima); som longo e de banda larga (giz,
whoosh) pede mais corte que um clique. Os efeitos vêm da pasta do usuário ($EDITLABS_SONS) ou dos sintetizados da
motion-arquivo (motor/kit/sfx/). Você não ouve: registre a conta e deixe "escuta pendente".
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000


def ebur(arq):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-i", str(arq), "-map", "0:a:0",
           "-af", "apad=pad_dur=0.5,ebur128=framelog=verbose", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True).stderr
    return np.array([float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", out)])


def ponderado_k(arq):
    cmd = ["ffmpeg", "-v", "error", "-i", str(arq), "-map", "0:a:0", "-ac", "2", "-ar", str(SR), "-af",
           "highshelf=f=1681.97:g=3.999:t=q:w=0.7072,highpass=f=38.135:p=2:t=q:w=0.5003", "-f", "f32le", "-"]
    pcm = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).reshape(-1, 2).astype(float)


def janela(x, w, hop=0.01):
    ms = (x ** 2).sum(1)
    c = np.concatenate([[0], np.cumsum(ms)]); n = int(w * SR); h = int(hop * SR)
    c = np.concatenate([c, np.full(n, c[-1])])
    idx = np.arange(0, len(ms), h)
    return -0.691 + 10 * np.log10((c[idx + n] - c[idx]) / n + 1e-12)


def main():
    a = sys.argv[1:]
    abaixo, saida = 17.0, None
    if "--abaixo" in a:
        i = a.index("--abaixo"); abaixo = float(a[i + 1]); del a[i:i + 2]
    if "--saida" in a:
        i = a.index("--saida"); saida = Path(a[i + 1]); del a[i:i + 2]
    corte, efeitos = a[0], a[1:]
    M = ebur(corte)
    voz = float(np.median(M[M > -40]))
    print(f"voz: momentâneo mediano (ebur128) {voz:.1f} LUFS · alvo dos efeitos: {voz - abaixo:.1f}")
    res = {}
    for arq in efeitos:
        Mm = ebur(arq)
        x = ponderado_k(arq)
        m400 = float(Mm.max()) if len(Mm) else -70.0
        m200 = float(janela(x, 0.2).max())
        pico = max(m400, m200)
        ganho = round((voz - abaixo) - pico, 1)
        res[Path(arq).name] = {"M400": round(m400, 1), "M200": round(m200, 1), "ganho_db": ganho}
        print(f"{Path(arq).name:32s} M400 {m400:6.1f}  M200 {m200:6.1f}  ganho {ganho:+.1f} dB")
    if saida:
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps({"voz_M_mediano": voz, "abaixo_db": abaixo, "efeitos": res}, indent=1,
                                    ensure_ascii=False))
        print("->", saida)


if __name__ == "__main__":
    main()
