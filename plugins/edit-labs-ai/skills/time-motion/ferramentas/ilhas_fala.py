#!/usr/bin/env python3
"""Ilhas de fala/silêncio do corte (envelope RMS de 10 ms na faixa da voz) e ajuste do início das palavras que o
whisper põe dentro de um silêncio.

    python3 ilhas_fala.py <corte.mp4> <palavras.json> <saida.json> [--limiar -30]

Cada palavra ganha "ini_whisper" (o original) e "ajustado" (true se o início foi empurrado para o começo da
próxima ilha de fala). Confira as ajustadas de ouvido ou na onda antes de prender gráfico nelas."""
import json
import subprocess
import sys

import numpy as np

a = sys.argv[1:]
limiar = -30.0
if "--limiar" in a:
    i = a.index("--limiar"); limiar = float(a[i + 1]); del a[i:i + 2]
arq, pal, sai = a[0], a[1], a[2]
SR = 16000
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", arq, "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                      "-af", "highpass=f=150,lowpass=f=4000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(pcm, dtype=np.float32)
H = int(0.01 * SR)
n = len(x) // H
rms = np.sqrt(np.mean(x[:n * H].reshape(n, H) ** 2, axis=1) + 1e-12)
db = 20 * np.log10(rms / rms.max())
fala = db > limiar                                # limiar relativo ao pico


def fechar(m, k):
    """fecha buracos < k janelas (oclusivas) entre trechos de fala"""
    m = m.copy(); i = 0
    while i < len(m):
        if not m[i]:
            j = i
            while j < len(m) and not m[j]:
                j += 1
            if 0 < i and j < len(m) and (j - i) < k:
                m[i:j] = True
            i = j
        else:
            i += 1
    return m


fala = fechar(fala, 6)
ilhas = []
i = 0
while i < n:
    if fala[i]:
        j = i
        while j < n and fala[j]:
            j += 1
        if j - i >= 5:                            # ilha < 50 ms é ruído
            ilhas.append([round(i * 0.01, 2), round(j * 0.01, 2)])
        i = j
    else:
        i += 1
print("ilhas de fala:", " ".join(f"{a_:.2f}–{b:.2f}" for a_, b in ilhas))
P = json.load(open(pal))["palavras"]
for p in P:
    s = p["ini"]
    p["ini_whisper"] = s
    # início dentro de silêncio -> empurra para o começo da próxima ilha (se ela começa antes do fim da palavra)
    if not any(a_ - 0.02 <= s < b for a_, b in ilhas):
        prox = [a_ for a_, b in ilhas if a_ > s]
        if prox and prox[0] < p["fim"]:
            p["ini"] = prox[0]
    p["ajustado"] = abs(p["ini"] - s) > 1e-6
json.dump({"ilhas": ilhas, "palavras": P}, open(sai, "w"), ensure_ascii=False, indent=1)
for p in P:
    m = " <- ajustado de %.2f" % p["ini_whisper"] if p["ajustado"] else ""
    print(f"{p['ini']:6.2f}–{p['fim']:6.2f}  {p['palavra']}{m}")
