"""Som das colagens sem voz: a trilha é a referência, poucos efeitos onde a tela mostra a ação.

    mixar(eventos, trilha, dur, pasta, inicio=0.0)  -> pasta/mix.wav (−14 LUFS, pico ≤ −1 dBTP depois do AAC) + som.json
    juntar(video_mudo, mix, saida)                  -> MP4 final com AAC, e a medida (LUFS, pico)

Regra: cada efeito entra com o ganho MEDIDO contra a trilha no instante dele (REL, em dB). Um pico fixo deixa os efeitos
20–30 dB abaixo da trilha, inaudíveis.
Os efeitos vêm de sons_sint (sintetizados em código) ou da pasta de sons do usuário (recursos.SONS/<classe>/).
A trilha é um arquivo seu (com licença que permita o uso) ou None: aí entra sons_sint.cama (acorde calmo)."""
import json
import re
import subprocess
from pathlib import Path

import numpy as np

import recursos as Rc
import sons_sint as SS

SR = SS.SR
# nome do efeito -> classe do banco (sons_sint / pasta do usuário)
FX = {"papel": "papel", "folhear": "folhear", "amassar": "amassar", "whoosh": "ar", "whoosh_suave": "ar_suave",
      "tique": "relogio", "relogio": "relogio", "baque": "baque", "giz": "giz", "grave": "grave",
      "obturador": "obturador", "clique": "toque", "ponto": "brilho"}
TRILHAS = Rc.TRILHAS          # coloque aqui as suas trilhas (o plugin não traz música)
# nível de cada efeito contra a trilha no mesmo instante (RMS da parte ativa − RMS da trilha na janela dele)
REL = {"papel": -5, "folhear": -6, "amassar": -6, "whoosh": -7, "whoosh_suave": -9, "tique": -9, "relogio": -8,
       "baque": -1, "giz": -5, "grave": -8, "obturador": -4, "clique": -6, "ponto": -7}
GOLPE = {"whoosh": 0.20, "whoosh_suave": 0.30}      # o ponto alto do whoosh cai no meio do movimento


def ler(caminho, t=None, ss=0.0):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(ss), "-i", str(caminho)] + (["-t", str(t)] if t else []) + \
          ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
    return x.reshape(-1, 2).copy()


def gravar(x, caminho):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(caminho)], input=x.astype(np.float32).tobytes(), check=True)


def medir(caminho):
    """LUFS integrado e pico real (dBTP) pelo ebur128 do ffmpeg"""
    r = subprocess.run(["ffmpeg", "-v", "info", "-nostats", "-i", str(caminho), "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    resumo = r[r.rfind("Summary:"):]
    return (float(re.search(r"I:\s+(-?[\d.]+) LUFS", resumo).group(1)),
            float(re.search(r"Peak:\s+(-?[\d.]+) dBFS", resumo).group(1)))


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(np.square(x))) + 1e-9)


def ativo(s):
    m = np.abs(s).max(axis=1)
    return s[m > m.max() * 10 ** (-30 / 20)]


def tiques(traco_fracao, q0, q1, total, cada):
    """um tique de relógio cada vez que a contagem passa um múltiplo de 'cada' (no degrau de 2 quadros)"""
    ev, ant = [], 0
    for f in range(q0, q1 + 1, 2):
        n = int(total * traco_fracao(f) // cada)
        if n > ant:
            ev.append(("tique", f / 24.0, f"passa {n * cada}"))
            ant = n
    return ev


def trilha_ou_cama(trilha, dur, inicio=0.0, semente=3):
    """lê a trilha (arquivo) ou, sem trilha, sintetiza a cama calma de sons_sint"""
    if trilha:
        return ler(trilha, dur + 0.1, inicio)
    return SS.cama(dur + 0.1, np.random.default_rng(semente))


def mixar(eventos, trilha, dur, pasta, inicio=0.0, fade_out=1.6, trilha_lufs=-16.0, rel=None, licenca="", semente=5):
    """trilha: arquivo de música (licença sua) ou None (cama sintetizada)"""
    pasta = Path(pasta); pasta.mkdir(parents=True, exist_ok=True)
    rel = {**REL, **(rel or {})}
    n = int(round(dur * SR))
    rng = np.random.default_rng(semente)
    tr = trilha_ou_cama(trilha, dur, inicio)[:n]
    tr = np.pad(tr, ((0, n - len(tr)), (0, 0)))
    env = np.ones(n, np.float32)
    a = int(0.02 * SR); env[:a] = np.linspace(0, 1, a)
    a = int(fade_out * SR); env[-a:] = np.cos(np.linspace(0, np.pi / 2, a)) ** 2
    tr *= env[:, None]
    gravar(tr, pasta / "_tr.wav")
    i_tr, _ = medir(pasta / "_tr.wav")
    tr *= 10 ** ((trilha_lufs - i_tr) / 20)
    fx = np.zeros_like(tr)
    lista = []
    for nome, t, papel in sorted(eventos, key=lambda e: e[1]):
        s = SS.amostra(FX[nome], rng)
        i0 = int(round((t - GOLPE.get(nome, 0.0)) * SR))
        if i0 < 0:
            s, i0 = s[-i0:], 0
        janela = tr[i0: i0 + max(len(s), int(0.15 * SR))]
        ganho = rms_db(janela) + rel[nome] - rms_db(ativo(s))
        s = s * 10 ** (ganho / 20)
        j = min(n, i0 + len(s))
        fx[i0:j] += s[: j - i0]
        lista.append({"efeito": nome, "t": round(t, 3), "quadro": round(t * 24), "contra_a_trilha_db": rel[nome],
                      "ganho_db": round(float(ganho), 1), "na_tela": papel})
    gravar(tr + fx, pasta / "_mix.wav")
    i_mix, tp_mix = medir(pasta / "_mix.wav")
    g = -14.0 - i_mix
    # limitador a 4× a taxa (pega o pico ENTRE amostras) e teto em −2,6 dB: o AAC ainda sobe o pico real (um limitador
    # comum a 48 kHz chegou a deixar −0,7 dBTP depois do AAC)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pasta / "_mix.wav"), "-af",
                    f"volume={g:.2f}dB,aresample=192000,"
                    f"alimiter=limit={10 ** (-2.6 / 20):.4f}:attack=1:release=60:level=disabled,aresample={SR}",
                    "-ar", str(SR), "-c:a", "pcm_s24le", str(pasta / "mix.wav")], check=True)
    i_fim, tp_fim = medir(pasta / "mix.wav")
    gravar(fx, pasta / "efeitos_so.wav")
    for p in (pasta / "_tr.wav", pasta / "_mix.wav"):
        p.unlink()
    rel_json = {"trilha": {"arquivo": str(trilha) if trilha else "cama sintetizada (sons_sint.cama)", "inicio_s": inicio,
                           "fade_out_s": fade_out, "licenca": licenca if trilha else "própria (gerada em código)"},
                "efeitos": lista, "mix_antes": {"I": i_mix, "TP": tp_mix}, "ganho_master_db": round(g, 2),
                "master": {"I": i_fim, "TP": tp_fim}}
    (pasta / "som.json").write_text(json.dumps(rel_json, ensure_ascii=False, indent=1))
    return rel_json


def juntar(video, mix, saida, teto=-1.2):
    """MP4 final com AAC; se o pico real passar do teto depois do AAC, baixa o ganho pelo excesso e refaz"""
    ganho = 0.0
    for _ in range(3):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(mix), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-af", f"volume={ganho:.2f}dB", "-c:a", "aac", "-b:a", "256k", "-ar", str(SR),
                        "-shortest", "-movflags", "+faststart", str(saida)], check=True)
        i, tp = medir(saida)
        if tp <= teto + 0.05:
            return i, tp
        ganho -= tp - teto
    return i, tp



def acentos(trilha, dur=40.0, inicio=0.0, minimo_db=6.0, espaco=0.3):
    """os golpes fortes da trilha (s, contados do início do trecho): onde a energia de 20 ms salta mais que minimo_db
    sobre a média dos 300 ms anteriores. Para pôr carimbos e pousos em cima de um golpe de verdade (a estimativa de
    bpm oscilou entre medidas; o golpe medido não)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(inicio), "-t", str(dur), "-i", str(trilha), "-ac", "1",
                          "-ar", "22050", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    h = 441                                              # 20 ms
    n = len(x) // h
    e = 10 * np.log10(np.mean(x[: n * h].reshape(n, h) ** 2, axis=1) + 1e-10)
    out = []
    for i in range(15, n):
        salto = e[i] - np.mean(e[i - 15:i])
        if salto >= minimo_db and e[i] > e.max() - 30 and (not out or i * 0.02 - out[-1][0] >= espaco):
            out.append((round(i * 0.02, 2), round(float(salto), 1)))
    return out
