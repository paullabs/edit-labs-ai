"""Banco de sons do motor, sem biblioteca de terceiros: cada classe é sintetizada em código, com variação a cada chamada.

    amostra(classe, rng)   -> np.float32 (n, 2) a 48 kHz
    cama(dur, rng)         -> trilha-leito calma (acorde lento), para quando o usuário não tem música

Classes: papel, amassar, folhear, ar (whoosh), ar_suave, reverso, grave, brilho, relogio, toque, baque, giz, obturador.

Pasta do usuário (opcional): se existir SONS/<classe>/ com .wav/.mp3/.flac/.ogg/.aif (SONS = $EDITLABS_SONS ou
$EDITLABS_DATA/colagem/sons), a amostra vem de lá (um arquivo diferente a cada vez). Use só sons cuja licença permita o
seu uso; o plugin não traz nenhum."""
import math
import subprocess

import cv2
import numpy as np

import recursos as R

SR = 48000
CLASSES = ("papel", "amassar", "folhear", "ar", "ar_suave", "reverso", "grave", "brilho", "relogio", "toque", "baque",
           "giz", "obturador")
_EXT = (".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff", ".m4a")
_cache_arq = {}


# ------------------------------------------------------------------ utilidades
def _ler(caminho, t=None):
    cmd = ["ffmpeg", "-v", "error", "-i", str(caminho)] + (["-t", str(t)] if t else []) + \
          ["-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
    return x.reshape(-1, 2).copy()


def arquivos_usuario(classe):
    pasta = R.SONS / classe
    if not pasta.is_dir():
        return []
    return sorted(p for p in pasta.iterdir() if p.suffix.lower() in _EXT)


def _bp(x, lo, hi):
    """passa-faixa aproximado (diferença de dois filtros gaussianos), em Hz"""
    x = np.ascontiguousarray(x, np.float32).reshape(-1, 1)
    a = cv2.GaussianBlur(x, (0, 0), SR / (2 * math.pi * hi)).ravel() if hi < SR / 2 else x.ravel()
    b = cv2.GaussianBlur(x, (0, 0), SR / (2 * math.pi * lo)).ravel()
    return a - b


def _lp(x, hz):
    x = np.ascontiguousarray(x, np.float32).reshape(-1, 1)
    return cv2.GaussianBlur(x, (0, 0), SR / (2 * math.pi * hz)).ravel()


def _norm(m):
    return (m / (np.abs(m).max() + 1e-9)).astype(np.float32)


def _estereo(m, largura=0.0, rng=None):
    """mono -> estéreo; largura > 0 descorrelaciona um pouco os lados (ruído fica mais 'aberto')"""
    m = _norm(m)
    if largura <= 0 or rng is None:
        return np.stack([m, m], axis=1)
    d = int(rng.integers(8, 40))
    r = np.concatenate([np.zeros(d, np.float32), m[:-d]]) if len(m) > d else m
    return np.stack([m, (1 - largura) * m + largura * r], axis=1).astype(np.float32)


def _env(n, ataque, queda, forma=1.0):
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(ataque, 1e-4)) * np.exp(-np.maximum(t - ataque, 0) / max(queda, 1e-4))
    return e ** forma


# ------------------------------------------------------------------ síntese por classe
def papel(rng, dur=None):
    """papel manuseado: estalinhos (fibras que dobram) sobre um chiado de 0,4–4 kHz"""
    dur = dur or rng.uniform(0.25, 0.45)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    taxa = rng.uniform(60, 180)
    k = int(taxa * dur)
    for t0 in rng.uniform(0, dur * 0.9, k):
        L = int(rng.uniform(0.002, 0.012) * SR)
        i = int(t0 * SR)
        if i + L >= n:
            continue
        burst = rng.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 4))
        out[i:i + L] += burst * float(np.exp(rng.normal(0, 0.7)))
    out = _bp(out, rng.uniform(900, 1500), rng.uniform(5500, 8000))
    chiado = _bp(rng.standard_normal(n).astype(np.float32), 400, 4000) * 0.25
    lento = 0.5 + 0.5 * np.abs(np.sin(np.linspace(0, rng.uniform(2, 5) * math.pi, n)))
    m = out + chiado * lento
    m *= _env(n, 0.004, dur * 0.6, 0.6)
    return _estereo(m, 0.3, rng)


def amassar(rng, dur=None):
    """papel sendo amassado: estalos densos e fortes que diminuem"""
    dur = dur or rng.uniform(0.5, 0.9)
    s = papel(rng, dur)[:, 0]
    n = len(s)
    extra = np.zeros(n, np.float32)
    for t0 in rng.uniform(0, dur * 0.7, int(rng.uniform(15, 30))):
        L = int(rng.uniform(0.006, 0.02) * SR)
        i = int(t0 * SR)
        if i + L < n:
            extra[i:i + L] += rng.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 3)) * \
                rng.uniform(0.6, 1.4)
    extra = _bp(extra, 600, 6000)
    return _estereo(s + _norm(extra) * 0.8, 0.35, rng)


def folhear(rng, dur=None):
    """páginas passando: uma série de 'fffp' curtos"""
    dur = dur or rng.uniform(0.5, 0.8)
    n = int(dur * SR)
    out = np.zeros(n, np.float32)
    t = 0.0
    while t < dur - 0.06:
        L = int(rng.uniform(0.04, 0.07) * SR)
        i = int(t * SR)
        seg = _bp(rng.standard_normal(L).astype(np.float32), 1500, 7000) * np.hanning(L)
        out[i:i + L] += seg[: max(0, min(L, n - i))] * rng.uniform(0.6, 1.0)
        t += rng.uniform(0.045, 0.08)
    return _estereo(out, 0.3, rng)


def _varredura(n, rng, f0, f1, f2, largura=0.6):
    """ruído filtrado cujo centro sobe de f0 a f1 e desce a f2 (blocos com sobreposição)"""
    bloco = 1024
    passo = bloco // 2
    ruido = rng.standard_normal(n + bloco).astype(np.float32)
    out = np.zeros(n + bloco, np.float32)
    jan = np.hanning(bloco).astype(np.float32)
    nb = max(1, n // passo)
    for b in range(nb):
        u = b / max(nb - 1, 1)
        fc = f0 + (f1 - f0) * (u / 0.45) if u < 0.45 else f1 + (f2 - f1) * ((u - 0.45) / 0.55)
        i = b * passo
        seg = ruido[i:i + bloco]
        seg = _bp(seg, fc * (1 - largura / 2), fc * (1 + largura))
        out[i:i + bloco] += seg * jan
    return out[:n]


def ar(rng, dur=None):
    """whoosh: ar que passa (sobe e desce de altura), com o pico a ~40% da duração"""
    dur = dur or rng.uniform(0.45, 0.8)
    n = int(dur * SR)
    m = _varredura(n, rng, rng.uniform(300, 500), rng.uniform(1400, 2400), rng.uniform(400, 700))
    t = np.linspace(0, 1, n)
    pico = rng.uniform(0.35, 0.45)
    env = np.where(t < pico, (t / pico) ** 2, np.exp(-(t - pico) / 0.18))
    return _estereo(m * env, 0.5, rng)


def ar_suave(rng, dur=None):
    s = ar(rng, dur or rng.uniform(0.6, 1.0))
    return _estereo(_lp(s[:, 0], 2500), 0.5, rng)


def reverso(rng, dur=None):
    """inspiração ao contrário: sobe devagar e corta seco (antes de um corte de cena)"""
    dur = dur or rng.uniform(0.7, 1.1)
    n = int(dur * SR)
    t = np.linspace(0, 1, n)
    m = _varredura(n, rng, 300, rng.uniform(1800, 2600), rng.uniform(2600, 3200), 0.8)
    tom = np.sin(2 * math.pi * np.cumsum(np.linspace(110, 220, n)) / SR) * 0.25
    env = t ** 2.5
    env[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return _estereo((m + tom) * env, 0.5, rng)


def grave(rng, dur=None):
    """nota grave de impacto: seno que cai de ~70 para ~42 Hz, com um harmônico e cauda longa"""
    dur = dur or rng.uniform(1.2, 1.8)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = rng.uniform(40, 46) + rng.uniform(20, 30) * np.exp(-t / 0.12)
    fase = 2 * math.pi * np.cumsum(f) / SR
    m = np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.08 * _lp(rng.standard_normal(n).astype(np.float32), 200)
    return _estereo(m * _env(n, 0.006, dur * 0.35), 0.0)


def brilho(rng, dur=None):
    """sininho curto (ponto de dado que acende): parciais inarmônicas com queda rápida"""
    dur = dur or rng.uniform(0.6, 0.9)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = rng.uniform(1100, 1600)
    m = sum(a * np.sin(2 * math.pi * f0 * r * t) * np.exp(-t / (q * dur))
            for a, r, q in ((1.0, 1.0, 0.35), (0.5, 2.01, 0.22), (0.3, 2.76, 0.15), (0.15, 4.07, 0.08)))
    return _estereo(m * _env(n, 0.002, dur), 0.2, rng)


def relogio(rng, dur=None):
    """um tique de relógio: clique metálico de 3 ms com uma ressonância curta"""
    n = int((dur or 0.12) * SR)
    t = np.arange(n) / SR
    clique = _bp(rng.standard_normal(n).astype(np.float32), 2500, 9000) * np.exp(-t / 0.0015)
    res = np.sin(2 * math.pi * rng.uniform(1800, 2600) * t) * np.exp(-t / 0.012) * 0.6
    return _estereo(clique + res, 0.0)


def toque(rng, dur=None):
    """clique de interface/madeira leve: tom curto de 700–1300 Hz"""
    n = int((dur or 0.08) * SR)
    t = np.arange(n) / SR
    m = np.sin(2 * math.pi * rng.uniform(700, 1300) * t) * np.exp(-t / 0.012)
    m += _bp(rng.standard_normal(n).astype(np.float32), 1500, 6000) * np.exp(-t / 0.002) * 0.4
    return _estereo(m, 0.0)


def baque(rng, dur=None):
    """batida abafada na mesa: corpo grave curto + estalo de madeira"""
    dur = dur or 0.35
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = rng.uniform(55, 70) + (rng.uniform(120, 160) - 60) * np.exp(-t / 0.025)
    corpo = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / rng.uniform(0.06, 0.1))
    estalo = _norm(_bp(rng.standard_normal(n).astype(np.float32), 400, 3500) * np.exp(-t / 0.006))
    return _estereo(corpo * 0.9 + estalo * rng.uniform(0.25, 0.4), 0.0)


def giz(rng, dur=None):
    """giz/caneta no papel: ruído de 1,3–5 kHz que vai e volta em traços de 70–130 ms"""
    dur = dur or rng.uniform(0.5, 0.9)
    n = int(dur * SR)
    t = np.arange(n) / SR
    banda = _bp(rng.standard_normal(n).astype(np.float32), rng.uniform(1300, 1900), rng.uniform(4200, 5600))
    vai = np.abs(np.sin(math.pi * t / rng.uniform(0.07, 0.13) + rng.uniform(0, 6.28))) ** 0.7
    return _estereo(banda * vai * _env(n, 0.02, dur), 0.2, rng)


def obturador(rng, dur=None):
    """obturador de câmera antiga: dois cliques secos com 40–70 ms entre eles"""
    n = int((dur or 0.2) * SR)
    m = np.zeros(n, np.float32)
    for k, a in ((0, 1.0), (int(rng.uniform(0.04, 0.07) * SR), 0.7)):
        L = int(0.012 * SR)
        if k + L < n:
            m[k:k + L] += _bp(rng.standard_normal(L).astype(np.float32), 1200, 8000) * np.exp(-np.arange(L) / 90) * a
    return _estereo(m, 0.0)


_SINT = {"papel": papel, "amassar": amassar, "folhear": folhear, "ar": ar, "ar_suave": ar_suave, "reverso": reverso,
         "grave": grave, "brilho": brilho, "relogio": relogio, "toque": toque, "baque": baque, "giz": giz,
         "obturador": obturador}


def amostra(classe, rng=None, dur=None):
    """um som da classe: da pasta do usuário (se houver) ou sintetizado; muda a cada chamada"""
    rng = rng if rng is not None else np.random.default_rng()
    arqs = arquivos_usuario(classe)
    if arqs:
        a = arqs[int(rng.integers(0, len(arqs)))]
        if a not in _cache_arq:
            _cache_arq[a] = _ler(a, t=70)
        x = _cache_arq[a]
        return x if dur is None else x[: int(dur * SR)]
    if classe not in _SINT:
        raise KeyError(f"classe de som desconhecida: {classe}")
    return _SINT[classe](rng, dur).astype(np.float32)


def cama(dur, rng=None, tom=55.0):
    """trilha-leito calma: acorde lento (fundamental, quinta, oitava, décima) com deriva de volume e um sopro filtrado.
    Serve de cama quando não há música licenciada; para publicar, prefira uma trilha sua."""
    rng = rng if rng is not None else np.random.default_rng(3)
    n = int(dur * SR)
    t = np.arange(n) / SR
    notas = [tom, tom * 1.5, tom * 2, tom * 2.52, tom * 3]
    m = np.zeros(n, np.float32)
    for i, f in enumerate(notas):
        lfo = 0.6 + 0.4 * np.sin(2 * math.pi * t / rng.uniform(7, 13) + rng.uniform(0, 6.28))
        det = 1 + rng.uniform(-0.002, 0.002)
        m += (np.sin(2 * math.pi * f * det * t) + 0.3 * np.sin(2 * math.pi * f * 2 * det * t)) * lfo / (1 + i * 0.6)
    sopro = _lp(_bp(rng.standard_normal(n).astype(np.float32), 200, 1200), 900)
    m = _norm(m) * 0.9 + _norm(sopro) * 0.08
    a, b = int(min(2.0, dur / 4) * SR), int(min(3.0, dur / 3) * SR)
    m[:a] *= np.linspace(0, 1, a) ** 2
    m[-b:] *= np.cos(np.linspace(0, math.pi / 2, b)) ** 2
    return _estereo(m, 0.4, rng)
