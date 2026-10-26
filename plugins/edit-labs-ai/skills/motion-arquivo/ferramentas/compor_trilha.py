#!/usr/bin/env python3
"""
Compõe, em código, camas de música para voz explicativa (sem direitos autorais, sem depender de biblioteca):
pad quente + baixo + pluck leve (+ chiado de prato e bumbo suave nos estilos com pulso), reverb de cauda longa.

    python3 compor_trilha.py <saida_dir> [estilo ...] [--dur 96] [--semente 7]

estilos: curioso · dados · tensao · claro   (padrão: todos)
Saída: <saida_dir>/<estilo>.wav (48 kHz, estéreo, ~-24 dBFS RMS) — pronto para `mixar.py --trilha`.
A escuta é do usuário: o código controla andamento, harmonia e camadas, não o gosto.
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000

ESTILOS = {
    # acordes por compasso (MIDI), escala do arpejo, bpm, camadas
    "curioso": dict(bpm=92, prog=[[48, 55, 59, 64], [45, 52, 57, 64], [41, 48, 57, 64], [43, 50, 59, 64]],
                    escala=[60, 62, 64, 67, 69, 72, 74, 76], pad=0.9, baixo=0.8, pluck=0.9, hat=0.0, bumbo=0.0, brilho=5200,
                    arp=[0, 2, 4, 2, 5, 4, 2, 1]),
    "dados": dict(bpm=108, prog=[[50, 57, 60, 64], [46, 53, 58, 62], [43, 50, 58, 65], [45, 52, 57, 61]],
                  escala=[62, 65, 67, 69, 72, 74, 77, 79], pad=0.7, baixo=0.9, pluck=0.7, hat=0.5, bumbo=0.5, brilho=4600,
                  arp=[0, 3, 1, 4, 2, 5, 3, 1]),
    "tensao": dict(bpm=72, prog=[[45, 52, 57, 60], [41, 48, 55, 60], [38, 45, 53, 57], [40, 47, 52, 59]],
                   escala=[57, 60, 62, 64, 67, 69, 72, 74], pad=1.0, baixo=1.0, pluck=0.45, hat=0.0, bumbo=0.0, brilho=3000,
                   arp=[0, 4, 2, 5, 1, 3, 2, 6]),
    "claro": dict(bpm=100, prog=[[50, 57, 62, 66], [45, 52, 61, 64], [47, 54, 59, 62], [43, 50, 59, 66]],
                  escala=[62, 66, 69, 71, 74, 78, 81, 83], pad=0.8, baixo=0.7, pluck=1.0, hat=0.25, bumbo=0.0, brilho=6200,
                  arp=[0, 2, 3, 5, 3, 2, 4, 1]),
}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def filtro_passa_baixa(x, fc, ordem=2):
    """Passa-baixa estático por FFT (curva suave), por canal na última dimensão."""
    n = x.shape[-1]
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 1.0 / (1.0 + (f / fc) ** (2 * ordem))
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * g, n, axis=-1)


def filtro_passa_alta(x, fc):
    n = x.shape[-1]
    f = np.fft.rfftfreq(n, 1 / SR)
    g = 1.0 - 1.0 / (1.0 + (f / fc) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * g, n, axis=-1)


def reverb(x, rng, t60=2.4, mix=0.28):
    """Reverb por convolução com ruído decaindo (estéreo descorrelacionado), pré-atraso de 18 ms.
    O envio é passa-alta (200 Hz): a cauda de ruído tem ganho aleatório por frequência e uma nota grave pura
    ficava até 8 dB mais baixa que outra; o grave segue seco."""
    n = int(SR * t60)
    t = np.arange(n) / SR
    env = np.exp(-6.9 * t / t60)
    envio = filtro_passa_alta(x, 200.0)
    out = np.zeros_like(x)
    for c in range(2):
        ir = rng.standard_normal(n) * env
        ir = filtro_passa_baixa(ir, 4200, 1)
        ir[: int(0.018 * SR)] = 0
        ir /= np.sqrt((ir ** 2).sum()) + 1e-9
        L = 1
        while L < x.shape[1] + n:
            L *= 2
        y = np.fft.irfft(np.fft.rfft(envio[c], L) * np.fft.rfft(ir, L), L)[: x.shape[1]]
        out[c] = y
    return x + out * mix * 2.2


def pad(freqs, dur, rng, fade=1.0):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.07, 0.0, 0.07):
            ff = f * 2 ** (det / 12.0)
            ph = rng.random() * 2 * np.pi
            y += 2.0 * ((ff * t + ph / (2 * np.pi)) % 1.0) - 1.0       # serra
    y /= len(freqs) * 3
    a = min(len(t) // 2, int(fade * SR))              # fade linear nas pontas: dois acordes vizinhos somam 1 (sem "respiração" por compasso)
    env = np.ones_like(t)
    env[:a] = np.linspace(0, 1, a)
    env[-a:] *= np.linspace(1, 0, a)
    return y * env


def pluck_nota(f, dur=0.9):
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for h in range(1, 8):
        y += (1.0 / h ** 1.4) * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (3.0 + 2.2 * h))
    y *= np.minimum(1.0, t / 0.004)
    return y / (np.abs(y).max() + 1e-9)


def mallet_nota(f, dur=1.0):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * f * t) * np.exp(-t * 4.0) + 0.35 * np.sin(2 * np.pi * f * 3.97 * t) * np.exp(-t * 14.0)
    y *= np.minimum(1.0, t / 0.002)
    return y / (np.abs(y).max() + 1e-9)


def hat(rng):
    n = int(0.05 * SR)
    r = filtro_passa_alta(rng.standard_normal(n), 7000) * np.exp(-np.arange(n) / SR / 0.012)
    return r / (np.abs(r).max() + 1e-9)


def bumbo():
    n = int(0.22 * SR)
    t = np.arange(n) / SR
    f = 46 + 90 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.09)


def colar(dst, src, i, g=1.0, pan=0.0):
    if i < 0:                                   # nota que começa antes do 0: corta o que ficou para trás
        src = src[-i:]
        i = 0
    if i >= dst.shape[1] or len(src) == 0:
        return
    n = min(len(src), dst.shape[1] - i)
    gl, gr = g * np.cos((pan + 1) * np.pi / 4), g * np.sin((pan + 1) * np.pi / 4)
    dst[0, i:i + n] += src[:n] * gl
    dst[1, i:i + n] += src[:n] * gr


def compor(estilo, dur=96.0, semente=7):
    e = ESTILOS[estilo]
    rng = np.random.default_rng(semente + sum(map(ord, estilo)))
    beat = 60.0 / e["bpm"]
    comp = 4 * beat
    n = int(dur * SR)
    mix = np.zeros((2, n))
    nb = int(dur / comp)
    for b in range(nb):
        ac = e["prog"][b % len(e["prog"])]
        t0 = b * comp
        i0 = int(t0 * SR)
        sec = b // 8                       # seção de 8 compassos: a textura muda
        # pad: a cada compasso, com um pouco de sobreposição
        p = pad([hz(m) for m in ac[1:]], comp + 1.0, rng)
        colar(mix, p, i0 - int(0.5 * SR), 0.16 * e["pad"], -0.1)
        # baixo: raiz uma oitava abaixo, entra no 2º compasso
        if b >= 1:
            fb = hz(ac[0] - 12)
            nbz = int((comp + 0.4) * SR)
            tt = np.arange(nbz) / SR
            cf = 0.4                                                   # cruzamento linear entre notas do baixo
            ev = np.minimum(1, tt / cf) * np.minimum(1, (comp + cf - tt) / cf)
            bx = np.sin(2 * np.pi * fb * tt) * ev
            bx += 0.18 * np.sin(2 * np.pi * fb * 2 * tt) * ev
            colar(mix, bx, i0 - int(0.2 * SR), 0.18 * e["baixo"], 0.0)
        # pluck: colcheias, entra no 5º compasso; some nas seções ímpares curtas para respirar
        if b >= 4 and (b % 8) not in (7,):
            nota = mallet_nota if estilo == "claro" else pluck_nota
            for s in range(8):
                if rng.random() < (0.72 if sec % 2 == 0 else 0.5):
                    idx = e["arp"][(s + b) % 8]
                    m = e["escala"][idx]
                    ti = t0 + s * beat / 2 + rng.normal(0, 0.006)
                    v = 0.55 + 0.45 * rng.random()
                    colar(mix, nota(hz(m)), int(ti * SR), 0.075 * e["pluck"] * v, rng.uniform(-0.5, 0.5))
        # pratos e bumbo suaves (só estilos com pulso), entram no 9º compasso
        if b >= 8 and e["hat"] > 0:
            for s in range(8):
                if s % 2 == 1 or rng.random() < 0.3:
                    colar(mix, hat(rng), int((t0 + s * beat / 2) * SR), 0.035 * e["hat"], rng.uniform(-0.3, 0.3))
        if b >= 8 and e["bumbo"] > 0:
            colar(mix, bumbo(), i0, 0.10 * e["bumbo"], 0.0)
            colar(mix, bumbo(), int((t0 + 2.5 * beat) * SR), 0.06 * e["bumbo"], 0.0)
    mix = filtro_passa_baixa(mix, e["brilho"], 2)
    mix = reverb(mix, rng)
    # entrada e saída
    f = int(2.0 * SR)
    mix[:, :f] *= np.linspace(0, 1, f)
    mix[:, -f * 2:] *= np.linspace(1, 0, f * 2)
    mix = np.tanh(mix * 1.2) / 1.2
    rms = np.sqrt((mix ** 2).mean())
    mix *= 10 ** (-24 / 20) / (rms + 1e-9)
    return np.clip(mix, -0.98, 0.98)


def gravar_wav(caminho, x):
    pcm = (x.T * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def main():
    a = sys.argv[1:]
    dur = float(a[a.index("--dur") + 1]) if "--dur" in a else 96.0
    sem = int(a[a.index("--semente") + 1]) if "--semente" in a else 7
    pos = [p for i, p in enumerate(a) if not p.startswith("--") and (i == 0 or a[i - 1] not in ("--dur", "--semente"))]
    saida = Path(pos[0])
    saida.mkdir(parents=True, exist_ok=True)
    for est in (pos[1:] or list(ESTILOS)):
        x = compor(est, dur, sem)
        gravar_wav(saida / f"{est}.wav", x)
        print(f"{est}: {dur:.0f}s, {ESTILOS[est]['bpm']} bpm -> {saida / (est + '.wav')}")


if __name__ == "__main__":
    main()
