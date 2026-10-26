"""Som automático dos vídeos de colagem (sem voz, ou como base para somar a voz depois).

O que dá errado quando o som é feito à mão (medido): o mesmo punhado de amostras curtas repetido (dezenas de tiques
iguais), a lista de eventos escrita à mão e fora do compasso das imagens, um baque com pico em −0,4 dB, trilhas agitadas
(1,4–1,9 ataques por segundo) e mixagem em −14 LUFS (volume de vídeo com voz) num vídeo sem voz.

Regras deste módulo:
  - os eventos NASCEM DA CENA: carimbo, pouso, transição, virada de cartão, traço de caneta, contador e chicote de câmera
    são lidos das camadas e da câmera, então cada som cai no quadro do contato;
  - cada ocorrência soa diferente: todo som é sintetizado na hora (sons_sint) com altura e nível sorteados, ou sorteado
    da pasta de sons do usuário (recursos.SONS/<classe>/), se existir;
  - o nível é medido contra a MÚSICA no instante (pico do efeito = RMS da música na janela + um desconto por classe);
  - a música cede 2–3 dB quando um efeito entra (sidechain), então o efeito se ouve sem precisar ser alto;
  - trilha calma (poucos ataques, nível estável), comprimida de leve, e master a −20 LUFS com limite em −3 dBTP.

    mixar_auto(camadas, cam, trans, trilha, fim, pasta, inicio=...)  ->  pasta/mix.wav + som.json
    (trilha=None usa a cama sintetizada; para publicar, prefira uma trilha sua com licença)
"""
import json
import sys
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import motor as M
import som as S
import sons_sint as SS

SR = S.SR
FPS = 24.0

# classes do banco por papel; o rodízio alterna entre elas (ex.: ar e ar_suave), e cada chamada sintetiza um som novo
BIB = {
    "reverso": ["reverso"],
    "ar": ["ar", "ar", "ar_suave"],
    "grave": ["grave"],
    "brilho": ["brilho"],
    "relogio": ["relogio"],
    "toque": ["toque"],
}

# pico do efeito (RMS de 30 ms) em dB ACIMA do RMS da música na janela de 1 s. Antes o carimbo entrava no nível da música
# (−1 dB) com pico de −0,4 dBFS. Agora cada classe fica perto da música e a música cede um pouco.
PICO_REL = {"levanta": -2.0, "janela": -1.0, "descasca": -1.0, "giro": -6.0, "carimbo": 2.0, "mergulho": 0.0, "iris": -1.0, "rasgo": 0.0, "empurra": -1.0, "flash": -3.0, "pouso": -2.0,
            "desliza": -3.0, "vira": -3.0, "chicote": -5.0, "caneta": -11.0, "tique": -10.0, "estilhaco": -3.0,
            "impacto": -4.0}
# teto do PICO de amostra, em dB acima do RMS da música: o RMS de 30 ms deixa passar fatias de papel com picos curtos
# 15–20 dB acima da música (medido no 1º teste); este teto segura isso
PICO_MAX = {"levanta": 3.0, "janela": 3.0, "descasca": 3.0, "giro": 0.0, "carimbo": 6.0, "mergulho": 4.0, "iris": 3.0, "rasgo": 4.0, "empurra": 3.0, "flash": 3.0, "pouso": 3.0,
            "desliza": 2.0, "vira": 2.0, "chicote": 2.0, "caneta": -4.0, "tique": -4.0, "estilhaco": 2.0, "impacto": 2.0}
# prioridade quando dois efeitos caem juntos (o maior fica, o menor sai)
PRIO = {"levanta": 3, "janela": 3, "descasca": 3, "giro": 1, "mergulho": 5, "iris": 5, "rasgo": 5, "empurra": 5, "flash": 5, "carimbo": 4, "vira": 3, "estilhaco": 3, "pouso": 2,
        "desliza": 2, "chicote": 1, "caneta": 0, "tique": 0, "impacto": 0}
ESPACO = {"carimbo": 0.5, "pouso": 0.55, "desliza": 0.6, "vira": 0.5, "chicote": 1.2, "estilhaco": 0.5}   # mesmo tipo, s


# ------------------------------------------------------------------ amostras
_rng_banco = np.random.default_rng(11)


def carregar(classe):
    """um som novo da classe (sintetizado, ou da pasta do usuário)"""
    return SS.amostra(classe, _rng_banco)


def reamostrar(x, f):
    """altera altura e velocidade juntas (f > 1: mais agudo e mais curto)"""
    n = max(8, int(len(x) / f))
    idx = np.linspace(0, len(x) - 1, n)
    return np.stack([np.interp(idx, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], axis=1).astype(np.float32)


def fade(x, ent=0.004, sai=0.02):
    n_e, n_s = int(ent * SR), int(sai * SR)
    x = x.copy()
    if n_e:
        x[:n_e] *= np.linspace(0, 1, n_e)[:, None]
    if n_s and len(x) > n_s:
        x[-n_s:] *= np.linspace(1, 0, n_s)[:, None]
    return x


def env30(x, janela=0.03):
    """RMS de 30 ms (dB), a cada 10 ms"""
    m = np.mean(x, axis=1) if x.ndim == 2 else x
    h, w = int(0.01 * SR), int(janela * SR)
    n = max(1, (len(m) - w) // h + 1)
    return 10 * np.log10(np.array([np.mean(m[i * h: i * h + w] ** 2) for i in range(n)]) + 1e-12), h / SR


def instante(x, modo):
    """segundos, dentro da amostra, que devem cair no instante do evento"""
    e, passo = env30(x)
    if modo == "fim":
        return len(x) / SR
    if modo == "pico":
        return float(np.argmax(e)) * passo
    pico = e.max()
    i = int(np.argmax(e > pico - 10))                    # 'inicio': o ataque (10 dB abaixo do pico)
    return max(0.0, i * passo - 0.004)


def pan(x, a, b):
    """panorama de a (−1 esquerda … 1 direita) a b ao longo da amostra"""
    p = np.linspace(a, b, len(x))
    ang = (p + 1) * math.pi / 4
    mono = np.mean(x, axis=1)
    return np.stack([mono * np.cos(ang), mono * np.sin(ang)], axis=1).astype(np.float32)


def fatia_papel(rng, dur):
    """um pedaço novo de papel (manuseado ou amassado) a cada chamada, escolhido onde há som de verdade"""
    fonte = SS.amostra("amassar" if rng.random() < 0.5 else "papel", rng, dur=max(dur * 2.5, 0.5))
    e, passo = env30(fonte, 0.05)
    bons = np.where(e > np.percentile(e, 70))[0]
    i = int(rng.choice(bons)) * passo
    a = int(max(0, i - 0.02) * SR)
    return fade(fonte[a: a + int(dur * SR)], 0.006, 0.05)


def _bp(x, lo, hi):
    """passa-faixa por diferença de dois filtros gaussianos (hz aproximados)"""
    s_lo = SR / (2 * math.pi * lo)
    s_hi = SR / (2 * math.pi * hi)
    a = cv2.GaussianBlur(x.reshape(-1, 1), (0, 0), s_hi).ravel()
    b = cv2.GaussianBlur(x.reshape(-1, 1), (0, 0), s_lo).ravel()
    return a - b


def carimbo_sint(rng):
    """carimbo de borracha na mesa: um baque abafado (140→60 Hz) + um estalo curto de papel; muda a cada vez"""
    n = int(0.34 * SR)
    t = np.arange(n) / SR
    f0, f1 = rng.uniform(120, 165), rng.uniform(52, 70)
    f = f1 + (f0 - f1) * np.exp(-t / 0.028)
    corpo = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t / rng.uniform(0.06, 0.09))
    estalo = _bp(rng.standard_normal(n).astype(np.float32), 500, 3200) * np.exp(-t / 0.007)
    estalo = estalo / (np.abs(estalo).max() + 1e-9)
    mono = corpo * 0.85 + estalo * rng.uniform(0.22, 0.4)
    s = np.stack([mono, mono], axis=1).astype(np.float32)
    return fade(s, 0.001, 0.05)


def caneta_sint(dur, rng, pan_a=-0.3, pan_b=0.3):
    """caneta/marcador no papel: ruído de 1,5–5 kHz que vai e volta (traços de 70–130 ms), sempre diferente"""
    n = int(dur * SR)
    t = np.arange(n) / SR
    ruido = rng.standard_normal(n).astype(np.float32)
    banda = _bp(ruido, rng.uniform(1300, 1900), rng.uniform(4200, 5600))
    periodo = rng.uniform(0.07, 0.13)
    fase = rng.uniform(0, 2 * math.pi)
    vai_e_volta = np.abs(np.sin(math.pi * t / periodo + fase)) ** 0.7
    lento = cv2.GaussianBlur(rng.standard_normal(n).astype(np.float32).reshape(-1, 1), (0, 0), SR * 0.12).ravel()
    lento = 0.65 + 0.35 * np.tanh(lento / (np.std(lento) + 1e-9))
    mono = banda * vai_e_volta * lento
    mono = mono / (np.abs(mono).max() + 1e-9)
    s = pan(np.stack([mono, mono], axis=1), pan_a, pan_b)
    ent, sai = min(0.05, dur / 3), min(0.09, dur / 3)
    return fade(s, ent, sai)


# ------------------------------------------------------------------ eventos a partir da cena
def eventos_da_cena(camadas, cam, trans, fim):
    ev = []
    for L in camadas:
        nome = L.nome
        sons = [x for x in [getattr(L, "som", None)] + list(getattr(L, "sons", ())) if x]   # vários: abre e fecha
        for som in sons:
            if som[0] == "pouso" and L.tam and min(L.tam) >= 200 and L.texto_px is None \
                    and not nome.startswith(("ET_", "c_")) and som[1] >= 8:
                ev.append({"cls": "pouso", "t": som[1] / FPS, "q": som[1], "nome": nome})
            elif som[0] == "desliza" and L.tam and min(L.tam) >= 200:
                ev.append({"cls": "desliza", "t": som[1] / FPS, "q": som[1], "nome": nome, "dir": som[2]})
            elif som[0] == "vira":
                ev.append({"cls": "vira", "t": som[1] / FPS, "q": som[1], "nome": nome})
            elif som[0] == "levanta":
                ev.append({"cls": "levanta", "t": som[1] / FPS, "q": som[1], "nome": nome})
            elif som[0] in ("janela", "descasca"):
                ev.append({"cls": som[0], "t": som[1] / FPS, "q": som[1], "nome": nome, "dur": (som[2] - som[1]) / FPS})
            elif som[0] == "giro":
                ev.append({"cls": "giro", "t": som[1] / FPS, "q": som[1], "nome": nome})
        if sons:
            continue
        if L.boil == "print" and nome.startswith("c_"):
            ev.append({"cls": "carimbo", "t": (L.ini + 2) / FPS, "q": L.ini + 2, "nome": nome})
        elif L.boil == "ink" and "trim" in L.chaves and not nome.startswith(("RAJ_", "ONDAS", "GRADE")):
            ch = L.chaves["trim"]
            if len(ch) >= 2 and ch[1][0] - ch[0][0] >= 8:
                ev.append({"cls": "caneta", "t": ch[0][0] / FPS, "q": ch[0][0], "nome": nome,
                           "dur": (ch[1][0] - ch[0][0]) / FPS})
        elif nome in ("RELOGIO", "ANOS") or nome.startswith("CONT"):
            ch = L.chaves.get("trim", [])
            if len(ch) >= 2:
                ev.append({"cls": "tique", "t": ch[0][0] / FPS, "q": ch[0][0], "nome": nome,
                           "dur": (ch[-1][0] - ch[0][0]) / FPS})
        elif nome == "BLOCO_0":
            ev.append({"cls": "estilhaco", "t": L.ini / FPS, "q": L.ini, "nome": nome})
    for tr in trans:
        ev.append({"cls": {"mergulho": "mergulho", "iris": "iris", "rasgo": "rasgo", "empurra": "empurra",
                            "flash": "flash", "recua": "mergulho"}[tr.tipo], "t": (tr.q0 + tr.q1) / 2 / FPS, "q": tr.q0, "q1": tr.q1,
                   "nome": "transição " + tr.tipo, "dir": tr.direcao})
    # chicotes de câmera: viradas rápidas entre enquadramentos que NÃO são transição
    centro = np.array([M.W / 2, M.H / 2, 1.0])
    vel = []
    for f in range(2, int(fim), 2):
        Ma, Mb = cam.matriz(f - 2), cam.matriz(f)
        pw = np.linalg.inv(Mb) @ centro
        d = float(np.hypot(*(Mb @ pw - Ma @ pw)[:2]))
        z = abs(math.log(M.escala_de(Mb) / max(M.escala_de(Ma), 1e-6)))
        vel.append((f, d + 900 * z))
    i = 0
    while i < len(vel):
        if vel[i][1] > 150:
            j = i
            while j + 1 < len(vel) and vel[j + 1][1] > 150:
                j += 1
            pico = max(v for _, v in vel[i:j + 1])
            meio = (vel[i][0] + vel[j][0]) / 2
            if pico >= 250 and not any(tr.q0 - 6 <= meio <= tr.q1 + 6 for tr in trans):
                ev.append({"cls": "chicote", "t": meio / FPS, "q": meio, "nome": "câmera", "forca": pico})
            i = j + 1
        else:
            i += 1
    return ev


def filtrar(ev):
    """tira o que é redundante: um evento menor colado num maior sai; o mesmo tipo respeita um espaço mínimo"""
    ev = sorted(ev, key=lambda e: (-PRIO[e["cls"]], e["t"]))
    mantidos = []
    for e in ev:
        if e["cls"] in ("caneta", "tique"):
            mantidos.append(e)
            continue
        if any(m["cls"] not in ("caneta", "tique") and abs(m["t"] - e["t"]) < 0.28 for m in mantidos):
            continue
        if any(m["cls"] == e["cls"] and abs(m["t"] - e["t"]) < ESPACO.get(e["cls"], 0.4) for m in mantidos):
            continue
        mantidos.append(e)
    return sorted(mantidos, key=lambda e: e["t"])


# ------------------------------------------------------------------ síntese de cada evento
class Rodizio:
    def __init__(self):
        self.i = {}

    def pega(self, classe):
        lista = BIB[classe]
        k = self.i.get(classe, 0)
        self.i[classe] = k + 1
        return lista[k % len(lista)]


def sintetizar(e, rng, rod):
    """devolve (sinal estéreo, modo de alinhamento, descrição). Só materiais, sem ganho (o ganho vem da música)."""
    c = e["cls"]
    if c == "carimbo":
        s = carimbo_sint(rng)
        if rng.random() < 0.5:                                           # às vezes um estalo de papel junto
            p = fatia_papel(rng, 0.09)
            s = s.copy(); s[: len(p)] += p * 0.5
        return s, "inicio", "carimbo sintético"
    if c == "pouso":
        p = fatia_papel(rng, rng.uniform(0.18, 0.3))
        return reamostrar(p, rng.uniform(0.85, 1.15)), "inicio", "fatia de papel"
    if c == "desliza":
        a = reamostrar(carregar(rod.pega("ar")), rng.uniform(0.95, 1.2))
        a = fade(a[: int(0.45 * SR)], 0.01, 0.2)
        return pan(a, 0.7 * e["dir"], 0.0), "pico", "ar curto"
    if c == "vira":
        p = fatia_papel(rng, 0.2)
        t = reamostrar(carregar(rod.pega("toque"))[: int(0.12 * SR)], rng.uniform(0.9, 1.1))
        out = p.copy(); out[: len(t)] += t * 0.5
        return out, "inicio", "papel que vira"
    if c == "levanta":                                                   # papel descolando + ar curto subindo
        p = fatia_papel(rng, 0.22)
        a = fade(reamostrar(carregar(rod.pega("ar")), rng.uniform(1.05, 1.25))[: int(0.4 * SR)], 0.01, 0.2) * 0.5
        out = np.zeros((max(len(p), len(a) + int(0.08 * SR)), 2), np.float32)
        out[: len(p)] += p
        out[int(0.08 * SR): int(0.08 * SR) + len(a)] += a
        return out, "inicio", "papel descolando"
    if c in ("janela", "descasca"):                                      # rasgo do tamanho da abertura
        n_p = max(2, int(e.get("dur", 0.6) / 0.12))
        p = np.concatenate([fatia_papel(rng, 0.12) for _ in range(min(n_p, 8))])
        return (pan(p, 0.6, -0.6) if c == "descasca" else p), "inicio", "papel rasgando"
    if c == "giro":
        a = reamostrar(carregar(rod.pega("ar")), rng.uniform(0.8, 0.95))
        return fade(a[: int(0.8 * SR)], 0.05, 0.4), "inicio", "ar leve do giro"
    if c == "estilhaco":
        p = np.concatenate([fatia_papel(rng, 0.14) for _ in range(3)])
        return p, "inicio", "papel em pedaços"
    if c == "mergulho":
        r = reamostrar(carregar(rod.pega("reverso")), rng.uniform(0.92, 1.08))
        g = fade(carregar(rod.pega("grave"))[: int(1.0 * SR)], 0.002, 0.7)
        return r, "fim", "reverso + (impacto)", g
    if c == "iris":
        a = reamostrar(carregar(rod.pega("ar")), rng.uniform(0.9, 1.1))
        return fade(a[: int(0.9 * SR)], 0.02, 0.3), "pico", "ar"
    if c == "rasgo":
        p = np.concatenate([fatia_papel(rng, 0.12) for _ in range(4)])
        ar = fade(reamostrar(carregar(rod.pega("ar")), 1.1)[: int(0.5 * SR)], 0.01, 0.2) * 0.35
        out = p.copy(); out[: len(ar)] += ar[: len(out)]
        return pan(out, 0.8, -0.8), "pico", "rasgo de papel (da direita p/ a esquerda)"
    if c == "empurra":
        a = reamostrar(carregar(rod.pega("ar")), rng.uniform(1.0, 1.25))
        return fade(a[: int(0.55 * SR)], 0.01, 0.2), "pico", "ar"
    if c == "flash":
        b = reamostrar(carregar(rod.pega("brilho")), rng.uniform(0.95, 1.1))
        a = fade(reamostrar(carregar(rod.pega("ar")), 1.2)[: int(0.5 * SR)], 0.02, 0.25) * 0.5
        out = np.zeros((max(len(a), len(b)), 2), np.float32)
        out[: len(a)] += a; out[: len(b)] += b * 0.7
        return out, "pico", "ar + brilho"
    if c == "chicote":
        a = reamostrar(carregar(rod.pega("ar")), rng.uniform(0.9, 1.15))
        return fade(a[: int(0.6 * SR)], 0.01, 0.25), "pico", "ar de câmera"
    if c == "caneta":
        return caneta_sint(e["dur"], rng), "inicio", "caneta no papel"
    if c == "tique":
        n = int(e["dur"] * SR)
        out = np.zeros((n + SR, 2), np.float32)
        passo = 0.5                                                      # um tique-taque a cada meio segundo
        base = carregar(rod.pega("relogio"))[: int(0.12 * SR)]
        k = 0
        t = 0.0
        while t < e["dur"]:
            tq = reamostrar(base, 1.0 if k % 2 == 0 else 0.86) * (1.0 if k % 2 == 0 else 0.75)
            a = int(t * SR)
            out[a: a + len(tq)] += tq
            t += passo; k += 1
        return out[:n], "inicio", "relógio (tique-taque a 2 Hz)"
    raise KeyError(c)


# ------------------------------------------------------------------ música e mixagem
def preparar_trilha(trilha, dur, inicio, pasta, trilha_lufs=-24.0, fade_in=0.6, fade_out=2.2):
    """recorta, comprime de leve (tira os acentos), tira o agudo duro e o subgrave, nivela e dá fade.
    trilha=None: usa a cama sintetizada (sons_sint.cama)"""
    pasta = Path(pasta)
    bruta = pasta / "_tr_bruta.wav"
    gerada = None
    if not trilha:
        gerada = trilha = pasta / "_cama.wav"
        S.gravar(SS.cama(dur + inicio + 0.6), gerada)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(inicio), "-t", str(dur + 0.2), "-i", str(trilha), "-af",
                    "highpass=f=45,lowpass=f=11000,acompressor=threshold=0.05:ratio=3:attack=35:release=350:makeup=1.5",
                    "-ac", "2", "-ar", str(SR), "-c:a", "pcm_f32le", str(bruta)], check=True)
    x = S.ler(bruta)
    n = int(round(dur * SR))
    x = np.pad(x, ((0, max(0, n - len(x))), (0, 0)))[:n]
    i, _ = S.medir(bruta)
    x = x * 10 ** ((trilha_lufs - i) / 20)
    env = np.ones(n, np.float32)
    a, b = int(fade_in * SR), int(fade_out * SR)
    env[:a] = np.linspace(0, 1, a) ** 1.5
    env[-b:] = np.cos(np.linspace(0, math.pi / 2, b)) ** 2
    bruta.unlink()
    if gerada:
        gerada.unlink()
    return (x * env[:, None]).astype(np.float32)


def rms_db(x):
    return 10 * np.log10(np.mean(np.square(x)) + 1e-12)


def duck(musica, sfx, profundidade=2.8):
    """a música cede até 'profundidade' dB quando o efeito toca (ataque rápido, volta devagar)"""
    h = int(0.01 * SR)
    n = len(sfx) // h
    e = np.max(np.abs(sfx[: n * h]).reshape(n, h, 2), axis=(1, 2))
    e_db = 20 * np.log10(e + 1e-9)
    m = np.clip((e_db - (-48.0)) / 18.0, 0, 1)
    g = np.zeros(n)
    for i in range(n):                                                 # ataque 20 ms, soltura 300 ms
        a = 0.5 if m[i] > g[i - 1 if i else 0] else 0.035
        g[i] = g[i - 1] + (m[i] - g[i - 1]) * a if i else m[i]
    gdb = -profundidade * g
    curva = np.interp(np.arange(len(musica)) / SR, np.arange(n) * h / SR, gdb)
    return (musica * (10 ** (curva / 20))[:, None]).astype(np.float32)


def mixar_auto(camadas, cam, trans, trilha, fim, pasta, inicio=0.0, alvo_lufs=-20.0, trilha_lufs=-24.0, semente=7,
               licenca=""):
    pasta = Path(pasta); pasta.mkdir(parents=True, exist_ok=True)
    dur = fim / FPS
    n = int(round(dur * SR))
    rng = np.random.default_rng(semente)
    musica = preparar_trilha(trilha, dur, inicio, pasta, trilha_lufs)
    ev = filtrar(eventos_da_cena(camadas, cam, trans, fim))
    rod = Rodizio()
    sfx = np.zeros_like(musica)
    rel = []
    for e in ev:
        res = sintetizar(e, rng, rod)
        s, modo, desc = res[0], res[1], res[2]
        extra = res[3] if len(res) > 3 else None
        ref = instante(s, modo)
        t0 = e["t"] - ref
        # janela de música ao redor, para medir o nível
        a, b = int(max(0, e["t"] - 0.5) * SR), int(min(n, (e["t"] + 0.5) * SR))
        mus = rms_db(musica[a:b]) if b > a else -40.0
        env, _ = env30(s)
        pico = float(env.max())
        ganho = mus + PICO_REL[e["cls"]] - pico
        pico_amostra = 20 * np.log10(np.abs(s).max() + 1e-9)
        ganho = min(ganho, mus + PICO_MAX[e["cls"]] - pico_amostra)
        g = 10 ** (ganho / 20)
        i0 = int(round(t0 * SR))
        trecho = s * g
        if i0 < 0:
            trecho, i0 = trecho[-i0:], 0
        j = min(n, i0 + len(trecho))
        if j > i0:
            sfx[i0:j] += trecho[: j - i0]
        if extra is not None:                                            # mergulho: um impacto grave baixinho no corte
            gi = extra
            envg, _ = env30(gi)
            gg = 10 ** (min(mus + PICO_REL["impacto"] - float(envg.max()),
                            mus + PICO_MAX["impacto"] - 20 * np.log10(np.abs(gi).max() + 1e-9)) / 20)
            k0 = int(round((e["t"] - 0.02) * SR))
            k1 = min(n, k0 + len(gi))
            if k1 > k0 and k0 >= 0:
                sfx[k0:k1] += gi[: k1 - k0] * gg
        rel.append({"classe": e["cls"], "t": round(e["t"], 3), "quadro": int(round(e["t"] * FPS)), "nome": e["nome"],
                    "material": desc, "ganho_db": round(float(ganho), 1), "pico_sobre_musica_db": PICO_REL[e["cls"]]})
    mus_duck = duck(musica, sfx)
    mix = mus_duck + sfx
    S.gravar(mix, pasta / "_mix.wav")
    i_mix, tp_mix = S.medir(pasta / "_mix.wav")
    g = alvo_lufs - i_mix
    # limitador a 4× a taxa (pega o pico entre amostras); teto −3,3 dB: o AAC sobe o pico real em ~0,9 dB
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(pasta / "_mix.wav"), "-af",
                    f"volume={g:.2f}dB,aresample=192000,"
                    f"alimiter=limit={10 ** (-3.3 / 20):.4f}:attack=1:release=80:level=disabled,aresample={SR}",
                    "-ar", str(SR), "-c:a", "pcm_s24le", str(pasta / "mix.wav")], check=True)
    i_fim, tp_fim = S.medir(pasta / "mix.wav")
    S.gravar(sfx, pasta / "efeitos_so.wav")
    S.gravar(musica, pasta / "trilha_no_nivel.wav")
    (pasta / "_mix.wav").unlink()
    cont = {}
    for r in rel:
        cont[r["classe"]] = cont.get(r["classe"], 0) + 1
    out = {"trilha": {"arquivo": str(trilha) if trilha else "cama sintetizada (sons_sint.cama)", "inicio_s": inicio,
                      "lufs_antes_do_master": trilha_lufs,
                      "licenca": licenca if trilha else "própria (gerada em código)"},
           "alvo_lufs": alvo_lufs, "efeitos": rel, "contagem": cont, "mix_antes": {"I": i_mix, "TP": tp_mix},
           "master": {"I": i_fim, "TP": tp_fim}}
    (pasta / "som.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out
