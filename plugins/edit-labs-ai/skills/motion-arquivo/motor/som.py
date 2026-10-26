"""
Camada 7 — som. Efeitos e trilha sintetizados aqui mesmo (sem crédito, sem download), para
viajarem com a skill em kit/sfx e kit/trilhas.

O que as referências do estilo fazem (medido):
  trilha por baixo da voz, 7 a 14 dB abaixo (o preto com grave, só 3 dB);
  whoosh quando um objeto entra ou a câmera viaja; sub-boom nas transições do preto com grave;
  tique enquanto o contador roda (explicador de dados); master a -14 LUFS.

É a reserva do mixador quando o usuário não tem pasta de sons (EDITLABS_SONS): nada aqui vem de biblioteca de
terceiros, então tudo pode ser redistribuído com o plugin.

    python3 som.py            grava os efeitos em kit/sfx (as trilhas saem na hora, em mixar.py)
"""
import math
from pathlib import Path

import numpy as np

SR = 48000
KIT = Path(__file__).resolve().parent / "kit"


# ------------------------------------------------------------------ utilidades
def _env(n, ataque, decai, forma="exp"):
    t = np.arange(n) / SR
    a = np.clip(t / max(ataque, 1e-4), 0, 1)
    d = np.exp(-np.maximum(t - ataque, 0) / decai) if forma == "exp" else np.clip(1 - (t - ataque) / decai, 0, 1)
    return a * d


def _ruido_banda(n, centro, largura_oct, rng, nfft=2048, hop=256):
    """Ruido branco filtrado por uma banda gaussiana (em oitavas) cujo centro anda no tempo.
    centro: funcao u (0..1) -> Hz."""
    x = rng.standard_normal(n + nfft)
    win = np.hanning(nfft).astype(np.float32)
    f = np.fft.rfftfreq(nfft, 1 / SR)
    lf = np.log2(np.maximum(f, 20.0))
    out = np.zeros(n + nfft, np.float32)
    norm = np.zeros(n + nfft, np.float32)
    for i in range(0, n, hop):
        u = i / max(1, n)
        fc = centro(u)
        g = np.exp(-0.5 * ((lf - math.log2(fc)) / largura_oct) ** 2)
        X = np.fft.rfft(x[i:i + nfft] * win)
        out[i:i + nfft] += np.fft.irfft(X * g).astype(np.float32) * win
        norm[i:i + nfft] += win ** 2
    out = out / np.maximum(norm, 1e-3)
    return out[:n]


def _normaliza(x, pico=0.89):
    m = np.abs(x).max()
    return x * (pico / m) if m > 0 else x


def _estereo(l, r=None, largura=0.0):
    r = l if r is None else r
    if largura:
        meio = (l + r) / 2; lado = (l - r) / 2 * largura
        l, r = meio + lado, meio - lado
    return np.stack([l, r], 1).astype(np.float32)


def _ease(u, p=2.0):
    return u ** p / (u ** p + (1 - u) ** p)


# ------------------------------------------------------------------ efeitos
def whoosh(dur=0.5, f0=350.0, f1=3800.0, pico=0.62, seed=1, largura=0.6, oct_=0.9):
    """Ar passando: banda de ruído que sobe de f0 a f1 e some depois do pico (entrada de objeto,
    viagem de câmera)."""
    n = int(SR * dur)
    rng = np.random.default_rng(seed)
    cen = lambda u: f0 * (f1 / f0) ** _ease(min(1.0, u / max(pico, 1e-3)) if u < pico else 1.0, 1.6)
    l = _ruido_banda(n, cen, oct_, rng); r = _ruido_banda(n, cen, oct_, rng)
    t = np.arange(n) / n
    env = np.where(t < pico, (t / pico) ** 2.2, np.exp(-(t - pico) / ((1 - pico) * 0.38)))
    pan = np.linspace(-0.35, 0.35, n)                  # atravessa da esquerda para a direita
    return _normaliza(_estereo(l * env * (1 - pan), r * env * (1 + pan), largura))


def chicote(dur=0.34, seed=2):
    """Chicote de câmera (whip pan): whoosh curto e agudo, pico cedo."""
    return whoosh(dur, 700.0, 6000.0, 0.38, seed, 0.8, 0.7)


def swish(dur=0.28, seed=3):
    """Foco que assenta (o corte que entra desfocado): sopro curto, quase sem grave."""
    return whoosh(dur, 900.0, 2600.0, 0.35, seed, 0.4, 0.8) * 0.6


def sub_boom(dur=1.1, seed=4):
    """Impacto grave: senoide que cai de 70 para 38 Hz, saturada (para soar no celular), com estalo."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 38 + 32 * np.exp(-t / 0.08)
    fase = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(fase) * _env(n, 0.004, 0.28)
    s = np.tanh(2.2 * s) / np.tanh(2.2)
    rng = np.random.default_rng(seed)
    clk = rng.standard_normal(n) * _env(n, 0.0005, 0.006)
    clk = np.convolve(clk, [1, -0.97], "same")          # passa-alta simples
    x = 0.9 * s + 0.35 * clk
    return _normaliza(_estereo(x))


def baque(dur=0.32, seed=10):
    """Carimbo ou objeto pesado na mesa: grave curto (95 -> 55 Hz) + estalo de papel."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 55 + 40 * np.exp(-t / 0.02)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.07)
    s = np.tanh(1.8 * s) / np.tanh(1.8)
    rng = np.random.default_rng(seed)
    pap = _ruido_banda(n, lambda u: 2500.0, 1.2, rng) * _env(n, 0.001, 0.03)
    return _normaliza(_estereo(0.85 * s + 0.5 * pap))


def tique(dur=0.04, freq=2400.0, seed=5):
    """Tique de contador: senoide amortecida curta + clique."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    s = np.sin(2 * np.pi * freq * t) * np.exp(-t / 0.006)
    c = rng.standard_normal(n) * np.exp(-t / 0.0012)
    x = 0.8 * s + 0.25 * np.convolve(c, [1, -0.98], "same")
    return _normaliza(_estereo(x), 0.7)


def pop(dur=0.14, f0=1150.0, f1=520.0, seed=6):
    """Pop de interface (etiqueta, balão, botão): bolha que cai de tom."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t / 0.018)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 0.045)
    rng = np.random.default_rng(seed)
    s += 0.08 * rng.standard_normal(n) * _env(n, 0.001, 0.01)
    return _normaliza(_estereo(s), 0.8)


def papel(dur=0.42, seed=7):
    """Papel (foto ou folha que pousa): ruído de 1,5–7 kHz com estalos aleatórios."""
    n = int(SR * dur)
    rng = np.random.default_rng(seed)
    x = _ruido_banda(n, lambda u: 3200.0, 1.1, rng)
    est = np.zeros(n)
    for k in rng.integers(0, n, 26):
        est[k:k + 400] += np.exp(-np.arange(min(400, n - k)) / 60.0) * rng.uniform(0.3, 1.0)
    env = _env(n, 0.01, 0.16) + 0.6 * est
    return _normaliza(_estereo(x * env, None, 0.3), 0.7)


def glitch(dur=0.62, seed=8):
    """Barras de cor (quebra de capítulo): ruído picotado em degraus de 30 ms com tons e sopro."""
    n = int(SR * dur)
    rng = np.random.default_rng(seed)
    passo = int(SR * 0.03)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for i in range(0, n, passo):
        f = rng.uniform(180, 1400)
        seg = slice(i, min(n, i + passo))
        tt = t[seg] - t[i]
        x[seg] = (np.sign(np.sin(2 * np.pi * f * tt)) * 0.35 + rng.standard_normal(len(tt)) * 0.5) * rng.uniform(0.3, 1.0)
    x = np.round(x * 12) / 12                              # bitcrush
    env = np.minimum(1, t / 0.04) * np.exp(-np.maximum(0, t - dur * 0.6) / 0.08)
    w = whoosh(dur, 300, 4000, 0.5, seed + 1)[:, 0]
    return _normaliza(_estereo(x * env * 0.6 + w[:n] * 0.5, None, 0.5))


def clique(seed=14):
    """Clique de mouse: aperta e solta (dois estalos curtos, o segundo mais fraco, 70 ms depois)."""
    n = int(SR * 0.12)
    out = np.zeros(n)
    rng = np.random.default_rng(seed)
    for t0, amp, f in ((0.004, 1.0, 3400.0), (0.074, 0.55, 2900.0)):
        i = int(SR * t0)
        m = int(SR * 0.012)
        tt = np.arange(m) / SR
        c = (np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.0015) +
             0.6 * np.convolve(rng.standard_normal(m), [1, -0.97], "same") * np.exp(-tt / 0.0008))
        out[i:i + m] += amp * c
    return _normaliza(_estereo(out), 0.7)


def obturador(seed=15):
    """Obturador antigo: estalo de abertura, zumbido mecânico curto e estalo de fechamento."""
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for t0, amp in ((0.003, 1.0), (0.085, 0.7)):
        i = int(SR * t0)
        m = min(n - i, int(SR * 0.02))
        tt = np.arange(m) / SR
        x[i:i + m] += amp * np.convolve(rng.standard_normal(m), [1, -0.9], "same") * np.exp(-tt / 0.003)
    zum = np.sin(2 * np.pi * 180 * t) * ((t > 0.01) & (t < 0.085)) * 0.12
    return _normaliza(_estereo(x + zum), 0.7)


def giz(dur=0.36, seed=16):
    """Traço de giz ou marcador: ruído de 2–6 kHz com aspereza (modulação rápida) que nasce e some com o traço."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    x = _ruido_banda(n, lambda u: 3600.0 + 800.0 * u, 0.9, rng)
    aspero = 0.55 + 0.45 * np.abs(np.sin(2 * np.pi * rng.uniform(28, 40) * t + rng.uniform(0, 6)))
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6
    return _normaliza(_estereo(x * aspero * env, None, 0.2), 0.6)


def digitar(n_teclas=6, intervalo=0.07, seed=9):
    """Teclas (texto digitado): cliques curtos com variação."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * (n_teclas * intervalo + 0.08)))
    for k in range(n_teclas):
        i = int(SR * (k * intervalo + rng.uniform(0, 0.012)))
        c = tique(0.03, rng.uniform(1600, 3200), seed + k)[:, 0] * rng.uniform(0.5, 0.9)
        out[i:i + len(c)] += c[:len(out) - i]
    return _normaliza(_estereo(out), 0.6)


# ------------------------------------------------------------------ trilha
def _reverb(x, seg=2.2, seed=11):
    rng = np.random.default_rng(seed)
    n = int(SR * seg)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / (SR * seg / 6.0))
    ir[0] = 1.0
    ir /= np.abs(ir).sum() ** 0.5 * 4
    m = len(x) + n
    k = 1 << (m - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, k) * np.fft.rfft(ir, k), k)[:len(x)]


def _nota(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def pad(dur, acordes, seg_acorde=4.0, corte=(700.0, 1600.0), seed=12, sub=0.22, ar=0.10):
    """Pad suave: cada nota é uma soma de harmônicos (dente de serra limitada) desafinados, com
    passa-baixa que respira; acordes cruzam em 1,2 s; grave em senoide; "ar" de ruído agudo;
    reverb longo. O pad documental da galeria (sem batida) é isto."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros((n, 2))
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * t / 9.0)
    cut = corte[0] + (corte[1] - corte[0]) * lfo
    for k in range(int(math.ceil(dur / seg_acorde)) + 1):
        notas = acordes[k % len(acordes)]
        t0 = k * seg_acorde - 0.6
        a = np.clip((t - t0) / 1.2, 0, 1) * np.clip((t0 + seg_acorde + 1.2 - t) / 1.2, 0, 1)
        if a.max() <= 0:
            continue
        idx = np.nonzero(a > 0)[0]
        tt = t[idx]
        for j, m in enumerate(notas):
            f0 = _nota(m)
            for canal, detune in ((0, -0.004), (1, 0.004)):
                f = f0 * (1 + detune + rng.uniform(-0.002, 0.002))
                s = np.zeros(len(idx))
                for h in range(1, 24):
                    fh = f * h
                    if fh > 9000:
                        break
                    w = 1.0 / h / (1 + (fh / cut[idx]) ** 2)
                    s += w * np.sin(2 * np.pi * fh * tt + rng.uniform(0, 6.28))
                out[idx, canal] += s * a[idx] * (0.45 if j == 0 else 0.35)
        if sub:
            fb = _nota(notas[0] - 12)
            out[idx, 0] += sub * np.sin(2 * np.pi * fb * tt) * a[idx]
            out[idx, 1] += sub * np.sin(2 * np.pi * fb * tt) * a[idx]
    if ar:
        for c in range(2):
            out[:, c] += ar * _ruido_banda(n, lambda u: 4500.0, 1.0, rng) * (0.6 + 0.4 * np.sin(2 * np.pi * t / 7.0 + c))
    for c in range(2):
        out[:, c] = 0.7 * out[:, c] + 0.5 * _reverb(out[:, c], 2.4, seed + c)
    fade = np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 2.0)
    out *= fade[:, None]
    return _normaliza(out.astype(np.float32), 0.7)


BANDAS = ((20, 120), (120, 500), (500, 2000), (2000, 8000))


def bandas(x):
    """Fração da energia em cada banda (a mesma régua usada para medir as referências)."""
    m = x.mean(1) if x.ndim > 1 else x
    win = 4096
    jan = np.hanning(win)
    f = np.fft.rfftfreq(win, 1 / SR)
    P = np.zeros(win // 2 + 1)
    for i in range(0, max(1, len(m) - win), 2048):
        P += np.abs(np.fft.rfft(m[i:i + win] * jan)) ** 2
    e = np.array([P[(f >= lo) & (f < hi)].sum() for lo, hi in BANDAS])
    return e / max(e.sum(), 1e-12)


def equalizar(x, alvo, passos=3):
    """Leva o equilíbrio de bandas de x ao alvo (frações das 4 bandas, medidas na trilha da referência
    nas pausas da fala). Ganho suave em log-frequência, de fase zero, limitado a ±24 dB."""
    alvo = np.asarray(alvo, float); alvo = alvo / alvo.sum()
    centros = np.log2([np.sqrt(lo * hi) for lo, hi in BANDAS])
    for _ in range(passos):
        atual = bandas(x)
        g_db = np.clip(10 * np.log10(alvo / np.maximum(atual, 1e-9)), -24, 24)
        k = 1 << (len(x) - 1).bit_length()
        f = np.fft.rfftfreq(k, 1 / SR)
        curva = np.interp(np.log2(np.maximum(f, 10.0)), centros, g_db)
        g = 10 ** (curva / 20)
        x = np.stack([np.fft.irfft(np.fft.rfft(x[:, c], k) * g, k)[:len(x)] for c in range(x.shape[1])], 1)
    return _normaliza(x.astype(np.float32), 0.7)


def grave_808(dur, bpm=80.0, notas=(33, 33, 31, 36), seed=13):
    """Grave do preto com régua: 808 longo na batida (sem bateria), com um pad escuro por cima."""
    n = int(SR * dur)
    out = np.zeros((n, 2))
    beat = 60.0 / bpm
    k = 0
    while k * beat * 2 < dur:
        t0 = k * beat * 2
        i0 = int(t0 * SR)
        m = notas[k % len(notas)]
        tt = np.arange(min(n - i0, int(SR * beat * 2))) / SR
        f = _nota(m) * (1 + 0.6 * np.exp(-tt / 0.03))
        s = np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / (beat * 1.4))) / np.tanh(2.5)
        out[i0:i0 + len(s), 0] += s; out[i0:i0 + len(s), 1] += s
        k += 1
    p = pad(dur, [[45, 52, 57, 60], [41, 48, 57, 60], [43, 50, 55, 62], [40, 47, 55, 59]], 4 * beat, (400, 900), seed, sub=False)
    out = out * 0.8 + p * 0.35
    return _normaliza(out.astype(np.float32), 0.75)


TRILHAS = {
    # documental (Família A: arquivo em papel e galeria): lá menor, sem batida
    "pad_documental": dict(acordes=[[45, 52, 57, 60, 64], [41, 48, 57, 60, 64], [36, 43, 52, 55, 60], [43, 50, 55, 59, 62]]),
    # dados (Família D): ré menor, mais escuro e mais lento
    "pad_dados": dict(acordes=[[38, 45, 50, 53, 57], [34, 41, 50, 53, 58], [36, 43, 48, 52, 55], [33, 40, 48, 52, 57]],
                      seg_acorde=5.0, corte=(500.0, 1200.0)),
    # explicador (Família B): dó maior aberto, claro, grave forte
    "pad_explicador": dict(acordes=[[48, 55, 60, 64, 67], [45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [43, 50, 55, 59, 62]],
                           corte=(900.0, 2000.0), sub=0.45),
}

# equilíbrio de bandas (20-120, 120-500, 500-2000, 2000-8000 Hz) da trilha de cada referência, medido no miolo
# das pausas da fala (o agudo da média das pausas é respiração do narrador; no miolo fica 15-20 dB abaixo do médio-grave)
ALVOS = {
    "pad_documental": (0.19, 0.60, 0.08, 0.012),   # galeria documental
    "pad_dados": (0.19, 0.65, 0.066, 0.010),       # explicador de dados (Família D)
    "pad_explicador": (0.43, 0.35, 0.086, 0.012),  # explicador claro (Família B)
    "grave_808": (0.80, 0.076, 0.024, 0.005),      # preto com régua
}


def trilha(nome, dur):
    if nome == "grave_808":
        x = grave_808(dur)
    elif nome in TRILHAS:
        x = pad(dur, **TRILHAS[nome])
    else:
        raise ValueError(f"trilha desconhecida: {nome}")
    return equalizar(x, ALVOS[nome])


EFEITOS = {"whoosh": whoosh, "chicote": chicote, "swish": swish, "sub_boom": sub_boom, "baque": baque, "tique": tique,
           "pop": pop, "papel": papel, "glitch": glitch, "digitar": digitar, "clique": clique, "obturador": obturador,
           "giz": giz}


def _bordas(x, ent=0.001, sai=0.025):
    """Sem estalo: rampa de 1 ms na entrada e cosseno de 25 ms na saída."""
    x = x.copy()
    a, b = int(SR * ent), min(len(x) // 2, int(SR * sai))
    if a:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    x[-b:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b)))[:, None]
    return x


def efeito(nome, **kw):
    return _bordas(EFEITOS[nome](**kw))


def grava(caminho, x):
    import wave
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(pcm.shape[1] if pcm.ndim > 1 else 1)
        w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    # as trilhas não vão para o kit (40 s = 7,7 MB cada): o mixador as gera na duração do vídeo
    (KIT / "sfx").mkdir(parents=True, exist_ok=True)
    for nome in EFEITOS:
        grava(KIT / "sfx" / f"{nome}.wav", efeito(nome))
        print("sfx", nome)
