"""Silêncio, vãos e energia (§05 5.3). Mede; não decide.

Piso de ruído = percentil 10 do RMS em janelas de 50 ms. Limiar = piso + 6 dB (limitado a −50…−25).
Silêncio < 5 % ou > 60 % do arquivo recalibra uma vez e avisa.
Teste de energia local: RMS nos 40 ms de cada lado do ponto ≥ 15 dB abaixo da palavra vizinha.
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

from comum import achar_projeto, check, gravar_json, ler_json, registrar_checks

_CACHE: dict[str, tuple[np.ndarray, int]] = {}


def carregar_wav(p: Path | str) -> tuple[np.ndarray, int]:
    k = str(p)
    if k not in _CACHE:
        with wave.open(k) as w:
            sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
            x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
        if ch > 1:
            x = x.reshape(-1, ch).mean(axis=1)
        _CACHE[k] = (x, sr)
    return _CACHE[k]


def db(v: float) -> float:
    return float(20 * np.log10(max(v, 1e-6)))


def rms_trecho(x: np.ndarray, sr: int, t0: float, t1: float) -> float:
    a, b = max(0, int(t0 * sr)), min(len(x), int(t1 * sr))
    if b <= a:
        return -120.0
    return db(float(np.sqrt(np.mean(x[a:b] ** 2))))


def energia_local(x: np.ndarray, sr: int, t: float, lado: float = 0.04) -> tuple[float, float]:
    """(dB nos 40 ms antes, dB nos 40 ms depois) do ponto t."""
    return rms_trecho(x, sr, t - lado, t), rms_trecho(x, sr, t, t + lado)


def envelope(x: np.ndarray, sr: int, win: float = 0.02, hop: float = 0.01) -> tuple[np.ndarray, float]:
    """RMS em dB por janela, via soma acumulada (sem matriz de índices: 15 min de áudio cabem folgados)."""
    w, h = int(win * sr), int(hop * sr)
    cs = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    ini = np.arange(0, max(1, len(x) - w + 1), h)
    e = (cs[ini + w] - cs[ini]) / w
    return 20 * np.log10(np.maximum(np.sqrt(e), 1e-6)), hop


def silencios(x: np.ndarray, sr: int, limiar_db: float, min_s: float = 0.12) -> list[dict]:
    env, hop = envelope(x, sr)
    baixo = env < limiar_db
    out, i, n = [], 0, len(baixo)
    while i < n:
        if baixo[i]:
            j = i
            while j < n and baixo[j]:
                j += 1
            t, e = i * hop, j * hop + 0.01
            if e - t >= min_s:
                out.append({"t": round(t, 3), "e": round(e, 3), "d": round(e - t, 3)})
            i = j
        else:
            i += 1
    return out


def medir(projeto: Path, com_palavras: bool = False) -> dict:
    projeto = Path(projeto)
    x, sr = carregar_wav(projeto / "00_fonte" / "_audio_16k.wav")
    dur = len(x) / sr
    w = int(0.05 * sr)
    blocos = x[: len(x) // w * w].reshape(-1, w)
    rms50 = 20 * np.log10(np.maximum(np.sqrt(np.mean(blocos ** 2, axis=1)), 1e-6))
    vivos = rms50[rms50 > -100]
    piso = float(np.percentile(vivos, 10)) if len(vivos) else -60.0
    limiar = float(np.clip(piso + 6, -50, -25))
    sil = silencios(x, sr, limiar)
    pct = sum(s["d"] for s in sil) / dur
    recal = None
    if pct < 0.05 or pct > 0.60:
        novo = float(np.clip(limiar + (4 if pct < 0.05 else -4), -50, -25))
        sil2 = silencios(x, sr, novo)
        pct2 = sum(s["d"] for s in sil2) / dur
        recal = {"de": round(limiar, 1), "para": round(novo, 1), "pct_antes": round(100 * pct, 1)}
        limiar, sil, pct = novo, sil2, pct2
    d = {"schema": "di-silencios/1", "relogio": "bruto", "piso_db": round(piso, 1), "limiar_db": round(limiar, 1),
         "min_s": 0.12, "janela_ms": 20, "pct_silencio": round(100 * pct, 1), "recalibrado": recal, "silencios": sil}
    if com_palavras:
        pal = (ler_json(projeto / "01_transcript" / "palavras.json") or {}).get("palavras", [])
        d["vaos"] = [{"i": a["i"], "d": round(b["t"] - a["e"], 3)} for a, b in zip(pal, pal[1:])]
        d["rms_palavras"] = [{"i": p["i"], "db": round(rms_trecho(x, sr, p["t"], p["e"]), 1)} for p in pal]
    gravar_json(projeto / "01_transcript" / "silencios.json", d, indent=None)
    if not com_palavras:
        registrar_checks(projeto, "F1", [check(
            "V11_silencio", 5 <= 100 * pct <= 60, "LOW", medido=f"{100 * pct:.1f} % · piso {piso:.1f} dB · limiar {limiar:.1f} dB",
            esperado="5–60 % do arquivo", detalhe=("recalibrado: " + str(recal)) if recal else "")],
            alvo="01_transcript/silencios.json")
    return d


_ENV: dict[str, tuple] = {}


def env_cache(x: np.ndarray, sr: int) -> tuple[np.ndarray, float]:
    k = f"{id(x)}:{sr}"
    if k not in _ENV:
        _ENV[k] = envelope(x, sr)
    return _ENV[k]


def voz_inicio(x, sr, lo: float, hi: float, limiar_db: float, acima: float = 8.0) -> float | None:
    """Primeiro instante com voz (envelope > limiar + 8 dB, sustentado 30 ms) em [lo, hi]."""
    env, hop = env_cache(x, sr)
    a, b = max(0, int(lo / hop)), min(len(env) - 3, int(hi / hop))
    for i in range(a, b):
        if env[i] > limiar_db + acima and env[i + 1] > limiar_db + acima and env[i + 2] > limiar_db + acima:
            return round(i * hop, 3)
    return None


def voz_fim(x, sr, lo: float, hi: float, limiar_db: float, acima: float = 8.0) -> float | None:
    """Último instante com voz (sustentada 30 ms) em [lo, hi]."""
    env, hop = env_cache(x, sr)
    a, b = max(2, int(lo / hop)), min(len(env) - 1, int(hi / hop))
    for i in range(b, a, -1):
        if env[i] > limiar_db + acima and env[i - 1] > limiar_db + acima and env[i - 2] > limiar_db + acima:
            return round(i * hop + 0.02, 3)
    return None


def silencio_em(sil: list[dict], t: float) -> dict | None:
    """O silêncio medido que contém t (busca linear; listas pequenas)."""
    for s in sil:
        if s["t"] <= t <= s["e"]:
            return s
        if s["t"] > t:
            break
    return None


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di silencio")
    ap.add_argument("--com-palavras", action="store_true")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    d = medir(achar_projeto(a.projeto), a.com_palavras)
    print(f"piso {d['piso_db']} dB · limiar {d['limiar_db']} dB · silêncio {d['pct_silencio']} % · {len(d['silencios'])} trechos")
    return 0
