#!/usr/bin/env python3
"""
"Ouve" uma trilha antes de usar: mede se ela serve de fundo para voz dramática e onde ela muda.

    python3 ouvir_trilha.py <saida.json> <música> [<música> ...] [--sem-voz]

Por faixa:
  andamento (bpm) e pulso    força da batida (pico da autocorrelação do fluxo espectral sobre o fundo)
  golpes/s                   densidade de ataques: acima de ~4/s soa frenético sob a voz
  tom e modo                 tônica e maior/menor (perfis de Krumhansl sobre o croma): menor = mais dramático
  centróide e grave          escuro x brilhante
  faixa da voz               fração da energia entre 300 Hz e 3,4 kHz: quanto menor, mais espaço para a narração
  voz cantada                faster-whisper no trecho mais cheio: se reconhece palavras, a faixa tem canto (briga com a narração)
  mapa                       nível e densidade a cada 2 s, e as partes (rala, média, cheia) com início e fim
A nota "vibe" junta a régua do estilo: dramática, pouco instrumento, sem ser frenética, com espaço para a voz.
A medida não substitui o ouvido; ela diz o que vale ouvir e qual trecho usar em cada parte do vídeo.
"""
import json
import subprocess
import tempfile
import sys
from pathlib import Path

import numpy as np

SR = 22050
N_FFT, HOP = 2048, 512
NOTAS = ["Dó", "Dó#", "Ré", "Ré#", "Mi", "Fá", "Fá#", "Sol", "Sol#", "Lá", "Lá#", "Si"]
MAIOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MENOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def ler(arq, sr=SR):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32)


def espectro(x):
    n = 1 + (len(x) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(x[idx] * np.hanning(N_FFT), axis=1))


def croma(S, f):
    C = np.zeros((S.shape[0], 12))
    ok = (f > 55) & (f < 2000)
    pc = np.round(12 * np.log2(f[ok] / 440.0) + 9).astype(int) % 12
    for k in range(12):
        C[:, k] = (S[:, ok][:, pc == k] ** 2).sum(1)
    return C


def tom(C):
    c = C.sum(0)
    c = (c - c.mean()) / (c.std() + 1e-9)
    melhor = None
    for t in range(12):
        for nome, perfil in (("maior", MAIOR), ("menor", MENOR)):
            p = np.roll(perfil, t)
            r = float(np.corrcoef(c, (p - p.mean()) / p.std())[0, 1])
            if melhor is None or r > melhor[0]:
                melhor = (r, NOTAS[t], nome)
    return melhor


def canto(arq, ini, dur=20.0):
    """Tem voz cantada? Whisper no trecho mais cheio: palavras com probabilidade alta = canto."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    seg = Path(tempfile.gettempdir()) / f"_canto_{abs(hash(str(arq))) % 10 ** 8}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini:.2f}", "-t", f"{dur:.2f}", "-i", str(arq), "-ac", "1",
                    "-ar", "16000", str(seg)], check=True)
    m = WhisperModel("mobiuslabsgmbh/faster-whisper-large-v3-turbo", device="cpu", compute_type="int8")
    segs, info = m.transcribe(str(seg), word_timestamps=True, vad_filter=True, beam_size=1, condition_on_previous_text=False)
    ws = [w for s in segs for w in (s.words or []) if w.probability > 0.6]
    seg.unlink(missing_ok=True)
    return {"idioma": info.language, "prob_idioma": round(info.language_probability, 2), "palavras": len(ws),
            "amostra": " ".join(w.word.strip() for w in ws[:12])}


def ouvir(arq, sem_voz=False):
    x = ler(arq)
    dur = len(x) / SR
    S = espectro(x)
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    P = S ** 2
    e = P.sum(0) + 1e-12
    centroide = float((f * e).sum() / e.sum())
    grave = float(e[f < 200].sum() / e.sum())
    voz = float(e[(f >= 300) & (f <= 3400)].sum() / e.sum())
    # fluxo, golpes e pulso
    L = np.log1p(S * 10)
    flux = np.maximum(0, np.diff(L, axis=0)).sum(1)
    base = np.convolve(flux, np.ones(43) / 43, "same")
    d = flux - base
    thr = np.percentile(d, 75) + 1.5 * d.std()
    golpes = [i for i in range(1, len(d) - 1) if d[i] > thr and d[i] >= d[i - 1] and d[i] >= d[i + 1]]
    golpes_s = len(golpes) / dur
    ac = np.correlate(d, d, "full")[len(d) - 1:]
    ac = ac / (ac[0] + 1e-9)
    l0, l1 = int(0.3 * SR / HOP), int(1.2 * SR / HOP)
    k = l0 + int(np.argmax(ac[l0:l1]))
    pulso = float(ac[k] - np.median(ac[l0:l1]))
    bpm = 60.0 / (k * HOP / SR)
    while bpm > 140:
        bpm /= 2
    while bpm < 60:
        bpm *= 2
    r, tonica, modo = tom(croma(S, f))
    # mapa a cada 2 s
    fr = int(2.0 * SR / HOP)
    nb = len(flux) // fr
    rms = 10 * np.log10(P[: nb * fr].sum(1).reshape(nb, fr).mean(1) + 1e-12)
    dens = np.array([sum(1 for g in golpes if b * fr <= g < (b + 1) * fr) / 2.0 for b in range(nb)])
    rms_rel = rms - np.median(rms)
    estado = ["rala" if v < -4 else ("cheia" if v > 2.5 else "média") for v in rms_rel]
    partes = []
    for b, s in enumerate(estado):
        if partes and partes[-1]["estado"] == s:
            partes[-1]["fim"] = round((b + 1) * 2.0, 1)
        else:
            partes.append({"estado": s, "inicio": round(b * 2.0, 1), "fim": round((b + 1) * 2.0, 1)})
    partes = [p for p in partes if p["fim"] - p["inicio"] >= 4] or partes
    cheio = int(np.argmax(rms)) * 2.0
    vozc = None if sem_voz else canto(arq, max(0.0, cheio - 6), 20.0)
    # nota da vibe (0-10): dramática, pouco instrumento, sem frenesi, espaço para a voz, sem canto
    nota = 5.0
    nota += 1.5 if modo == "menor" else -0.5
    nota += 1.0 if centroide < 1400 else (-1.0 if centroide > 2400 else 0.0)
    nota -= 1.2 * max(0.0, golpes_s - 3.0)
    nota -= 0.6 * max(0.0, (bpm - 120) / 10)
    nota -= 8.0 * max(0.0, voz - 0.45)
    nota -= 0.8 * max(0.0, pulso - 0.6) * 5
    if vozc and vozc["palavras"] >= 6:
        nota -= 3.0
    return {"arquivo": str(arq), "nome": Path(arq).stem, "dur": round(dur, 1), "bpm": round(bpm), "pulso": round(pulso, 2),
            "golpes_s": round(golpes_s, 2), "tom": f"{tonica} {modo}", "tom_conf": round(r, 2), "centroide_hz": round(centroide),
            "grave": round(grave, 2), "faixa_voz": round(voz, 2), "canto": vozc, "partes": partes,
            "mapa_db": [round(float(v), 1) for v in rms_rel], "mapa_golpes": [round(float(v), 1) for v in dens],
            "nota_vibe": round(nota, 1)}


def main():
    a = sys.argv[1:]
    sem_voz = "--sem-voz" in a
    pos = [p for p in a if not p.startswith("--")]
    saida, arqs = Path(pos[0]), pos[1:]
    out = []
    for arq in arqs:
        r = ouvir(arq, sem_voz)
        out.append(r)
        c = r["canto"]
        cs = "sem canto" if not c or c["palavras"] < 6 else f"CANTO ({c['idioma']}: {c['amostra'][:40]})"
        print(f"{r['nota_vibe']:5.1f}  {r['nome'][:38]:38s} {r['dur']:6.1f}s {r['bpm']:3d} bpm  pulso {r['pulso']:.2f}  "
              f"{r['golpes_s']:.1f} golpes/s  {r['tom']:10s} cen {r['centroide_hz']:5d}  voz {r['faixa_voz']:.2f}  {cs}")
        print("        partes:", " ".join(f"{p['estado']}[{p['inicio']:.0f}-{p['fim']:.0f}]" for p in r["partes"]))
    saida.write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
