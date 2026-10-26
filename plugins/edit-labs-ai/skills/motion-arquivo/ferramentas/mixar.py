#!/usr/bin/env python3
"""
Camada 7 — som. Voz + trilha por baixo + efeitos presos aos eventos do plano, master a -14 LUFS.

    python3 mixar.py <projeto> <video.mp4> <saida.mp4>
        [--trilha <música.wav|mp3> | pad_documental | pad_dados | pad_explicador | grave_808 | nenhuma]
        [--trilha-inicio <s>] [--abaixo <dB>] [--sem-efeitos] [--lufs -14] [--biblioteca <pasta>] [--mapa <json>]

Níveis medidos nas referências do estilo (régua: mediana do RMS de 10 ms, fala x miolo das pausas):
trilha 15-20 dB abaixo da voz na galeria documental, 13-14 no arquivo em papel e no explicador claro, 8 no preto com
grave (que soa mais baixo). Padrão: 15,5 dB abaixo (no miolo das pausas a régua dá ~20 dB), e mais 3 dB enquanto a voz
fala. Todas as referências saem a -14 LUFS.

Som original do vídeo real (plano video_clip com `audio_original`: caminho do áudio, ou true para o do próprio clipe):
o trecho que a imagem mostra (mesmo `ss`, mesma `vel`, esticado sem mudar o tom), `audio_nivel` dB abaixo da voz
(padrão -9), abaixando `audio_abaixa` dB (6) enquanto a voz fala; `audio_ate` corta antes de um ponto da fonte (trilha do
vídeo etc.). Régua: no gancho, o som real ~7 dB abaixo da voz (RMS do plano); nos outros, ~9.
No plano com som original não entra o ambiente sintético. Com `congela` (o quadro para e o desenho explica), o som
original para junto (fade de 0,12 s). Na tela_dividida, `audios` = [{"arquivo" (ou true = o clipe do lado), "lado",
"nivel", "abaixa", "ate"}] — cada lado com o seu som, no tempo da sua imagem.
Telestração (v12.7): cada desenho tem o seu som (traço/seta/círculo = giz, fluxo de ar = whoosh suave, ventilador =
laço, cronômetro = relógio até parar + clique, contador, balão, recorte entrando = whoosh, rótulo = pop).

Efeitos: da pasta de sons do próprio usuário (--biblioteca ou $EDITLABS_SONS), pelo mapa de recortes feito por
som_biblioteca.py (--mapa, $EDITLABS_SONS_MAPA ou $EDITLABS_DATA/motion-arquivo/som_biblioteca.json); sem pasta ou sem
mapa, os sintetizados de motor/som.py (motor/kit/sfx). Papel que a pasta não tem também cai na reserva sintetizada. O mapa do que entrou (fonte, recorte, âncora, ganho, motivo) fica em
<projeto>/som/SFX_MAP.json. A escuta é do usuário: este script mede, não aprova.
"""
import _caminho  # noqa: F401
import argparse
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

import som

SR = 48000
FPS = 30
KIT = _caminho.MOTOR / "kit"

# nível de cada papel, em dB relativos ao nível da voz (mediana do RMS de 10 ms nos trechos com fala)
NIVEL = {"clique": -8, "baque": -7, "obturador": -12, "papel": -14, "folhear": -15, "amassar": -13,
         "whoosh": -15, "whoosh_suave": -17, "reverso": -14, "tecla": -19, "tique": -17, "contador": -23,
         "balao": -15, "ponto": -18, "giz": -15, "glitch": -12, "grave": -9,
         # v12.4: uma ação da tela, um som (abaixo da voz o bastante para não disputar com ela)
         "impacto": -8, "riser": -15, "pop": -17, "palavra": -22, "bloco": -16, "hud": -18, "selecao": -18,
         "negativo": -15, "positivo": -17, "dinheiro": -19, "relogio": -23,
         "jato": -21, "ventilador": -24,
         "corte_ar1": -19, "corte_ar2": -19, "corte_ar3": -19, "corte_ar4": -19}
NIVEL_CORTE = {"obturador": -16, "papel": -18, "glitch": -18}   # o som de corte quando é um papel já existente
NIVEL_AMBIENTE = -25          # ambiente por baixo do b-roll em vídeo

PRIORIDADE = ["impacto", "clique", "baque", "riser", "grave", "glitch", "reverso", "obturador", "amassar", "negativo",
              "positivo", "folhear", "papel", "ponto", "giz", "dinheiro", "contador", "relogio", "balao", "selecao", "hud",
              "bloco", "jato", "ventilador", "pop", "whoosh", "whoosh_suave", "tecla", "tique", "palavra"]

# ritmo: o mesmo papel não volta antes de N quadros (palavras seguidas não viram metralhadora)
INTERVALO = {"jato": 3, "palavra": 21, "pop": 6, "bloco": 3, "hud": 6, "giz": 6, "tique": 6, "ponto": 6}

# variação de tom (semitons) para o som que se repete muito
VARIA_TOM = {"pop": [0, 4, -3, 7, 2, -5], "bloco": [0, 2, -2, 3], "jato": [0, 3, -2, 5, 1, -4, 2, 6, -1, 4]}

# fades (entrada, saída) dos sons cortados na duração do evento
FADE_LACO = {"relogio": (0.03, 0.15), "dinheiro": (0.01, 0.12), "ventilador": (0.15, 0.2)}

# ambiente do b-roll pelo nome do clipe (o plano pode forçar com "ambiente": "amb_x" ou desligar com false)
AMBIENTE_POR_NOME = [(r"cidade|rua|comercio|farmacia|avenida|transito", "amb_cidade"),
                     (r"praia|mar|baia|cargueiro|navio|rio\b|lago|agua", "amb_agua"),
                     (r"chamine|fabrica|industria|porto|guindaste|usina", "amb_industria"),
                     (r"porta|corredor|caverna|tunel|porao", "amb_caverna")]

# reserva sintetizada (sem a biblioteca do usuário)
RESERVA = {"clique": "clique", "baque": "baque", "obturador": "obturador", "papel": "papel", "folhear": "papel",
           "amassar": "papel", "whoosh": "chicote", "whoosh_suave": "whoosh", "reverso": "swish", "tecla": "tique",
           "tique": "tique", "contador": "digitar", "balao": "pop", "ponto": "pop", "giz": "giz",
           "glitch": "glitch", "grave": "sub_boom", "impacto": "sub_boom", "riser": "swish", "pop": "pop",
           "palavra": "whoosh", "bloco": "tique", "hud": "glitch", "selecao": "pop", "negativo": "pop", "positivo": "pop",
           "dinheiro": "papel", "relogio": "tique", "corte_ar1": "whoosh", "corte_ar2": "swish", "corte_ar3": "whoosh",
           "corte_ar4": "swish", "jato": "swish", "ventilador": "whoosh"}

# som de troca de cena pelo tipo do plano que ENTRA
CORTE_FOTO = {"foto_pullout", "foto_recorte", "etiqueta_rasgada", "moldura_entra", "galeria", "duas_molduras", "encontro",
              "dupla_retratos", "cartao_rotulo"}
CORTE_PAPEL = {"carimbo", "jornais_mesa", "palavra_no_papel", "linha_no_papel", "odometro", "documento_digitado",
               "amassar_lixeira", "calendario", "linha_do_tempo"}

# telestração: o som de cada desenho (motor/desenho.py)
SOM_DESENHO = {"traco": "giz", "seta": "giz", "circulo": "giz", "carrinho": "giz", "proibido": "giz", "fluxo": "whoosh_suave",
               "rotulo": "pop", "balao": "balao", "recorte": "whoosh"}
CORTE_GLITCH = {"hud_texto", "terminal"}


# ------------------------------------------------------------------ áudio
def ler(arq, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.4f}"]
    if t is not None:
        cmd += ["-t", f"{t:.4f}"]
    cmd += ["-i", str(arq), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    pcm = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).reshape(-1, 2).copy()


def ler_trecho(arq, ss, dur_saida, vel=1.0, ate=None):
    """O áudio do trecho que o plano mostra: `dur_saida` segundos na tela = `dur_saida*vel` da fonte a partir de `ss`,
    esticado/comprimido pelo atempo (o tom não muda). `ate` para antes desse segundo da fonte."""
    t_fonte = dur_saida * vel
    if ate is not None:
        t_fonte = min(t_fonte, max(0.0, ate - ss))
    if t_fonte <= 0.02:
        return np.zeros((0, 2), np.float32)
    filtros, v = [], float(vel)
    while v < 0.5:
        filtros.append("atempo=0.5"); v /= 0.5
    while v > 2.0:
        filtros.append("atempo=2.0"); v /= 2.0
    filtros.append(f"atempo={v:.5f}")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss:.4f}", "-t", f"{t_fonte:.4f}", "-i", str(arq), "-vn",
           "-af", ",".join(filtros), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    pcm = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).reshape(-1, 2).copy()


def duracao(arq):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                                capture_output=True, text=True).stdout)


def rms_10ms(x):
    m = x.mean(1) if x.ndim > 1 else x
    n = len(m) // 480
    return 20 * np.log10(np.sqrt((m[:n * 480].reshape(-1, 480) ** 2).mean(1)) + 1e-9)


def nivel_fala(voz):
    r = rms_10ms(voz)
    viva = r[r > max(np.percentile(r, 95) - 30, -60)]
    return float(np.median(viva)), r


def nivel_efeito(x):
    r = rms_10ms(x)
    if len(r) == 0:
        return -60.0
    return float(10 * np.log10(np.mean(10 ** (r[r > r.max() - 30] / 10))))


def fades(x, ent, sai):
    x = x.copy()
    a, b = min(len(x), int(SR * ent)), min(len(x), int(SR * sai))
    if a > 1:
        x[:a] *= np.linspace(0, 1, a)[:, None]
    if b > 1:
        x[-b:] *= (0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b)))[:, None]
    return x


# ------------------------------------------------------------------ trilha
def janela_estavel(arq, dur):
    """Começo do trecho de `dur` segundos com o nível mais estável (sem a introdução que cresce)."""
    x = ler(arq)
    m = x.mean(1)
    n = len(m) // SR
    r = 20 * np.log10(np.sqrt((m[:n * SR].reshape(-1, SR) ** 2).mean(1)) + 1e-9)
    w = int(math.ceil(dur))
    if n <= w + 1:
        return 0.0
    med = np.median(r)
    melhor, s_melhor = None, 0
    for s in range(0, n - w):
        j = r[s:s + w]
        nota = j.std() + 0.5 * max(0, med - np.median(j) - 3) + 0.3 * max(0, j.max() - j.min() - 12)
        if melhor is None or nota < melhor:
            melhor, s_melhor = nota, s
    return float(s_melhor)


def faz_trilha(nome, dur, inicio=None):
    if nome in som.TRILHAS or nome == "grave_808":
        return som.trilha(nome, dur), {"trilha": nome, "fonte": "motor/som.py (sintetizada)"}
    arq = Path(nome)
    if inicio is None:
        inicio = janela_estavel(arq, dur)
    x = ler(arq, ss=inicio, t=dur)
    if len(x) < int(dur * SR):
        x = np.vstack([x, np.zeros((int(dur * SR) - len(x), 2), np.float32)])
    return fades(x[:int(dur * SR)], 1.0, 2.5), {"trilha": arq.name, "fonte": str(arq), "inicio_s": inicio}


def faz_trilha_partes(partes, dur):
    """Trilha que muda com o roteiro: [{"quadro", "musica" (arquivo | "silencio"), "ss", "cruza", "ganho"}].
    Cada parte é nivelada à mesma referência; entre partes, cruzamento de `cruza` s (0 = corte seco)."""
    n = int(round(dur * SR))
    bed = np.zeros((n, 2), np.float32)
    info = []
    for i, pt in enumerate(partes):
        a = int(round(pt["quadro"] / FPS * SR))
        b = int(round(partes[i + 1]["quadro"] / FPS * SR)) if i + 1 < len(partes) else n
        if b <= a or pt.get("musica") in (None, "silencio"):
            info.append({"quadro": pt["quadro"], "musica": "silencio"})
            continue
        cz = int(pt.get("cruza", 0.3) * SR) if i + 1 < len(partes) else 0
        x = ler(pt["musica"], ss=pt.get("ss", 0.0), t=(b - a + cz) / SR)
        if len(x) < 10:
            continue
        r = rms_10ms(x)
        viva = r[r > r.max() - 30]
        x = x * 10 ** ((-20.0 - float(np.median(viva)) + pt.get("ganho", 0.0)) / 20)
        x = fades(x, pt.get("entra", 0.04), max(0.04, cz / SR))
        fim = min(n, a + len(x))
        bed[a:fim] += x[:fim - a]
        info.append({"quadro": pt["quadro"], "musica": Path(pt["musica"]).name, "ss": pt.get("ss", 0.0)})
    return fades(bed, 0.5, 2.5), {"trilha": "por partes", "partes": info}


def abaixa_sob_a_voz(rv, V, n_amostras, db=3.0, ataque=0.03, solta=0.35):
    """Ganho da trilha: -db quando a voz fala (envelope de 10 ms, ataque/soltura de um polo)."""
    alvo = np.clip((rv - (V - 18)) / 8, 0, 1)
    g = np.zeros_like(alvo)
    a_at, a_so = math.exp(-0.01 / ataque), math.exp(-0.01 / solta)
    v = 0.0
    for i, a in enumerate(alvo):
        k = a_at if a > v else a_so
        v = k * v + (1 - k) * a
        g[i] = v
    ganho = 10 ** (-db * g / 20)
    t_q = (np.arange(len(ganho)) + 0.5) * 480
    return np.interp(np.arange(n_amostras), t_q, ganho).astype(np.float32)


# ------------------------------------------------------------------ eventos do plano
def ambiente_do_clipe(caminho):
    nome = Path(str(caminho)).stem.lower()
    for rx, papel in AMBIENTE_POR_NOME:
        if re.search(rx, nome):
            return papel
    return "amb_vento"


def eventos(planos):
    """(quadro, papel, duração em quadros ou None, motivo[, nível]) de cada plano, só dentro do próprio plano,
    e a lista de ambientes [(início, fim, papel, motivo)] dos b-rolls em vídeo."""
    ev, amb, cortes = [], [], []
    for idx, p in enumerate(planos):
        if idx > 0 and p.get("corte_som", True) is not False:           # troca de cena: sempre tem som
            t_ = p["tipo"]
            if isinstance(p.get("corte_som"), str):
                pc = p["corte_som"]
            elif t_ in CORTE_FOTO:
                pc = "obturador"
            elif t_ in CORTE_PAPEL:
                pc = "papel"
            elif t_ in CORTE_GLITCH:
                pc = "glitch"
            else:
                pc = f"corte_ar{len(cortes) % 4 + 1}"
            cortes.append((int(p["inicio"]), pc, None, f"{t_}: troca de cena", NIVEL_CORTE.get(pc), True))
        if p.get("som") is False:
            continue
        ini, fim, t = p["inicio"], p["fim"], p["tipo"]

        def add(q, papel, dur=None, motivo=""):
            if isinstance(q, (int, float)) and not isinstance(q, bool) and ini <= q < fim:
                ev.append((int(q), papel, dur, f"{t}: {motivo or papel}"))

        g = p.get
        if t == "carimbo":
            add(ini + 2, "papel", motivo="a folha entra")
            add(g("quadro_carimbo"), "baque", motivo="carimbo")
        elif t == "botao_cta":
            add(g("quadro_clique"), "clique", motivo="clique no Seguir")
            if isinstance(g("quadro_clique"), int):
                add(g("quadro_clique") + 4, "positivo", motivo="virou Seguindo")
            for w in g("palavras") or []:
                add(w.get("quadro"), "palavra", motivo=w.get("texto", ""))
        elif t == "celular":
            for c in g("conversa") or []:
                add(c.get("quadro"), "balao", motivo="balão")
                for m in c.get("marcas") or []:
                    add(m.get("quadro"), "giz", motivo=f"marca {m.get('tipo', '')}")
            if g("carimbo"):
                add(g("carimbo").get("quadro"), "baque", motivo="carimbo na tela")
            canal = g("canal") or {}
            add(canal.get("derrubado"), "baque", motivo="canal derrubado")
            add(canal.get("volta"), "ponto", motivo="canal volta")
            conta = canal.get("conta") or {}
            if isinstance(conta.get("de"), int) and isinstance(conta.get("ate"), int) and conta["ate"] > conta["de"]:
                add(conta["de"], "contador", conta["ate"] - conta["de"], "contador de seguidores")
            dl = g("download") or {}
            add(dl.get("pronto"), "ponto", motivo="download pronto")
            if g("etiqueta"):
                add(g("etiqueta").get("quadro"), "ponto", motivo="etiqueta")
        elif t == "centena":
            for gr in g("grupos") or []:
                add(gr.get("quadro"), "contador", max(6, gr.get("duracao", 6)), "quadrados acendendo")
            if g("um"):
                add(g("um").get("quadro"), "ponto", motivo="o um que importa")
        elif t == "barras":
            for it in g("itens") or []:
                add(it.get("quadro"), "contador", 12, "barra que cresce")
                if it.get("muda"):
                    add(it["muda"].get("quadro"), "contador", 12, "barra que muda")
            if g("linha"):
                add(g("linha").get("quadro"), "tique", motivo="linha tracejada")
            if g("sobreposicao"):
                add(g("sobreposicao").get("quadro"), "pop", motivo="zona do empate")
            add(g("quadro_margem"), "tique", motivo="faixa da margem")
        elif t == "pizza":
            ac = g("acende") or {}
            if isinstance(ac.get("de"), int) and isinstance(ac.get("ate"), int):
                add(ac["de"], "contador", max(6, ac["ate"] - ac["de"]), "pizza enchendo")
            if g("metade"):
                add(g("metade").get("quadro"), "tique", motivo="metade")
        elif t == "pizzas":
            for pz in g("pizzas") or []:
                ac = pz.get("acende") or {}
                if isinstance(ac.get("de"), int) and isinstance(ac.get("ate"), int):
                    add(ac["de"], "contador", max(6, ac["ate"] - ac["de"]), "pizza enchendo")
                for f in pz.get("fatias") or []:
                    add(f.get("quadro"), "ponto", motivo="fatia")
                if pz.get("fora"):
                    add(pz["fora"].get("quadro"), "ponto", motivo="fatia que sai")
        elif t == "hemiciclo":
            for fg in g("figuras") or []:
                ac = fg.get("acende") or {}
                if isinstance(ac.get("de"), int) and isinstance(ac.get("ate"), int) and ac["ate"] - ac["de"] > 2:
                    add(ac["de"], "contador", max(6, ac["ate"] - ac["de"]), "cadeiras acendendo")
                if fg.get("falta"):
                    add(fg["falta"].get("quadro"), "ponto", motivo="a cadeira que falta")
                if fg.get("contra"):
                    add(fg["contra"].get("quadro"), "negativo", motivo="voto contra")
                for lm in fg.get("limiares") or []:
                    add(lm.get("quadro"), "tique", motivo="linha de corte")
                for nm in fg.get("numerais") or []:
                    add(nm.get("quadro"), "palavra", motivo=nm.get("texto", ""))
        elif t == "dezena":
            for ln in g("linhas") or []:
                q0 = ln.get("inicio")
                if isinstance(q0, int) and q0 > -900:
                    add(ini + q0, "contador", max(6, int(math.ceil(ln.get("valor", 1))) * ln.get("passo", 3)), "gente acendendo")
            for m in g("marcas") or []:
                add(m.get("quadro"), "tique", motivo="marca")
            for m in g("falta") or []:
                add(m.get("quadro"), "ponto", motivo="o que falta")
        elif t == "semana":
            add(g("quadro"), "tique", motivo="dia que acende")
            sq = g("sequencia")
            if sq and isinstance(sq.get("de"), int):
                for k in range(len(g("dias") or [0] * 7)):
                    add(sq["de"] + sq.get("passo", 3) * k, "tique", motivo="dia marcado")
        elif t == "escala_semana":
            add(ini + 2, "bloco", motivo="os blocos da semana")
            mu = g("muda")
            if mu:
                k = 0
                for r, est in enumerate(g("semanas") or []):
                    alvo = mu["semanas"][r]
                    for j in range(7):
                        if alvo[j] != est[j]:
                            add(mu["quadro"] + 3 * k, "bloco", motivo="bloco que vira")
                            k += 1
            ne = g("nome_escala")
            if ne:
                add(ne.get("quadro", ini), "palavra", motivo=ne.get("texto", ""))
            if g("destaque"):
                add(g("destaque").get("quadro"), "giz", motivo="círculo no dia")
            if g("legenda"):
                add(g("legenda").get("quadro", ini), "pop", motivo="legenda trabalho/folga")
            for tx in g("textos") or []:
                add(tx.get("quadro"), "palavra", motivo=tx.get("texto", ""))
        elif t == "icones":
            for it in g("itens") or []:
                q, nome = it.get("quadro"), it.get("icone")
                if nome == "nota":
                    add(q, "dinheiro", 18, "nota de dinheiro")
                elif nome == "relogio" and isinstance(q, int):
                    add(q, "pop", motivo="relógio")
                    add(q + 2, "relogio", max(6, fim - q - 2), "relógio girando")
                else:
                    add(q, "pop", motivo=f"ícone {nome}")
                rt = it.get("rotulo")
                if rt and isinstance(rt.get("quadro"), int) and isinstance(q, int) and rt["quadro"] - q >= 3:
                    add(rt["quadro"], "palavra", motivo=f"rótulo {rt.get('texto', '')}")
                add(it.get("certo"), "ponto", motivo="✓")
                add(it.get("xis"), "giz", motivo="X à mão")
                add(it.get("risco"), "giz", motivo="risco à mão")
            for tx in g("textos") or []:
                add(tx.get("quadro"), "palavra", motivo=tx.get("texto", ""))
            for sa in g("setas") or []:
                add(sa.get("quadro"), "giz", motivo="seta à mão")
                add(sa.get("xis"), "giz", motivo="X na seta")
            for lg in g("ligacoes") or []:
                add(lg.get("quadro"), "tique", motivo="ligação da rede")
            if g("divisor"):
                add(g("divisor").get("quadro", ini), "giz", motivo="divisor")
        elif t == "linha_no_papel":
            for w in g("palavras") or []:
                add(w.get("quadro"), "palavra", motivo=w.get("texto", ""))
                add(w.get("risco"), "giz", motivo="risco")
            if g("seta"):
                add(g("seta").get("quadro"), "giz", motivo="seta à mão")
        elif t == "palavra_no_papel":
            for w in g("palavras") or []:
                add(w.get("quadro"), "whoosh" if w.get("queda") else "palavra", motivo=w.get("texto", ""))
            if g("seta"):
                add(g("seta").get("quadro"), "giz", motivo="seta à mão")
        elif t == "hud_texto":
            for L in g("linhas") or []:
                add(L.get("quadro"), "hud", motivo=L.get("texto", ""))
                if L.get("caixa") and isinstance(L.get("quadro"), int):
                    add(L["quadro"] + 4, "selecao", motivo="caixa de seleção")
        elif t == "foto_pullout":
            if g("foto"):
                add(ini + 1, "obturador", motivo="foto de arquivo entra")
            for c in g("caixas") or []:
                add(c.get("quadro"), "pop", motivo="caixa")
        elif t == "video_clip":
            papel = False if g("audio_original") else g("ambiente")
            if papel is not False:
                papel = papel or ambiente_do_clipe(g("clip", ""))
                amb.append((ini, fim, papel, f"video_clip: ambiente de {Path(str(g('clip', ''))).stem}"))
        elif t == "salto":
            sa = g("saltador") or {}
            add(sa.get("decola"), "whoosh", motivo="decola")
            add(sa.get("giro_de"), "whoosh_suave", motivo="gira no ar")
            add(sa.get("pousa"), "baque", motivo="pouso")
        elif t == "de_cabeca":
            add(ini + 2, "whoosh_suave", motivo="anda de cabeça para baixo")
            add(g("quadro_ar"), "palavra", motivo="ar puxado")
        elif t == "ventilador":
            qv = g("quadro_ventilador")
            if isinstance(qv, int):
                add(qv, "ventilador", max(6, fim - qv), "ventilador girando")
            add(g("quadro_ar"), "palavra", motivo="ar puxado")
            add(g("quadro_gruda"), "pop", motivo="grudado")
            add(g("vira"), "whoosh", motivo="a cena vira")
        elif t == "jatos":
            q0, ps = g("quadro"), g("passo", 3)
            if isinstance(q0, int):
                for k in range(g("n", 10)):
                    add(q0 + ps * k, "jato", motivo=f"jato {k + 1}")
            add(g("sobe"), "whoosh_suave", motivo="todos os jatos: o carro sobe")
        elif t == "odometro":
            add(ini + 3, "contador", max(6, int(g("duracao", 30)) - 3), "o ano rolando")
        elif t == "linha_do_tempo":
            add(g("quadro_linha", ini), "giz", motivo="o eixo dos anos")
            for mk in g("marcas") or []:
                add(mk.get("quadro"), "ponto", motivo=f"marca {mk.get('texto', '')}")
            cu = g("cursor") or {}
            if isinstance(cu.get("quadro"), int) and isinstance(cu.get("chega"), int):
                add(cu["quadro"], "contador", max(6, cu["chega"] - cu["quadro"]), "o ano rolando no cursor")
            de_ = g("destaque") or {}
            add(de_.get("quadro"), "palavra", motivo=f"ano {de_.get('texto', de_.get('ano', ''))}")
            add(de_.get("desce"), "whoosh_suave", motivo="o ano desce para o eixo")
            fo = g("foto") or {}
            add(fo.get("quadro"), "obturador", motivo="foto alfinetada")
            pr = g("promessa") or {}
            add(pr.get("quadro"), "giz", motivo="seta da promessa")
            rs = g("risco") or {}
            add(rs.get("quadro"), "giz", motivo="círculo no prazo")
            add(rs.get("quadro_x"), "negativo", motivo="X no prazo")
            at_ = g("atraso") or {}
            add(at_.get("quadro"), "giz", motivo="chave do atraso")
        elif t == "lista_ui":
            for it in g("itens") or []:
                add(it.get("quadro"), "balao", motivo=it.get("texto", "item"))
        elif t == "jornais_mesa":
            add(ini + 1, "papel", motivo="jornais pousam")
            if g("laco"):
                add(g("laco").get("quadro"), "giz", motivo="laço à mão")
        elif t == "calendario":
            add(g("quadro_troca"), "folhear", 12, "folha do calendário")
        elif t == "galeria":
            for it in g("itens") or []:
                add(it.get("quadro"), "obturador", motivo="foto que entra")
            if g("meio"):
                add(g("meio").get("quadro"), "ponto", motivo="objeto do meio")
            for w in g("palavras") or []:
                add(w.get("quadro"), "palavra", motivo=w.get("texto", ""))
            for sa in g("setas") or []:
                add(sa.get("quadro"), "giz", motivo="seta à mão")
        elif t == "ranking":
            for tr in g("trocas") or []:
                add(tr.get("quadro"), "whoosh", motivo="troca de posição")
            for it in g("itens") or []:
                add(it.get("quadro"), "pop", motivo=f"entra {it.get('texto', '')}")
                for m in it.get("marcas") or []:
                    add(m.get("quadro"), "giz", motivo="marca à mão")
        elif t == "podio":
            for e in g("etiquetas") or []:
                add(e.get("quadro"), "ponto", motivo="etiqueta")
            for c in g("circulos") or []:
                add(c.get("quadro"), "giz", motivo="círculo à mão")
        elif t == "canvas_objeto":
            if g("circulo"):
                add(g("circulo").get("quadro"), "giz", motivo="círculo à mão")
        elif t == "amassar_lixeira":
            add(ini + 3, "amassar", min(fim - ini - 3, 40), "folha amassada")
        elif t == "selecao_digitada":
            for q in sorted(set(g("letras") or [])):
                add(q, "tecla", motivo="letra")
            add(g("quadro_selecao"), "selecao", motivo="seleção")
        elif t == "terminal":
            for ln in g("linhas") or []:
                q0, lpd = ln.get("quadro"), ln.get("letras_por_degrau")
                if q0 is None:
                    continue
                if lpd:
                    for k in range(math.ceil(len(ln.get("texto", "")) / lpd)):
                        add(q0 + 3 * k, "tecla", motivo="letra")
                else:
                    add(q0, "tecla", motivo="linha")
                add(ln.get("destaque"), "balao", motivo="destaque")
        # telestração em qualquer plano: o som de cada desenho
        for d in g("desenhos") or []:
            td, qd = d.get("tipo"), d.get("quadro")
            if td == "escurece":
                if g("congela") is not None or any(l_.get("congela") is not None for l_ in g("lados") or []):
                    add(qd, "obturador", motivo="a imagem congela")
            elif td == "ventilador" and isinstance(qd, int):
                add(qd, "ventilador", max(6, min(fim, d.get("ate", fim)) - qd), "ventilador girando")
            elif td == "cronometro" and isinstance(qd, int):
                para = d.get("para", fim)
                add(qd, "relogio", max(6, min(fim, para) - qd), "cronômetro correndo")
                if para < fim:
                    add(para, "clique", motivo="cronômetro para")
            elif td == "numero" and isinstance(qd, int):
                add(qd, "contador", max(6, (int(d.get("ate", 1)) - int(d.get("de", 1))) * int(d.get("passo", 3))), "contagem")
            elif td in SOM_DESENHO:
                add(qd, SOM_DESENHO[td], motivo=f"desenho {td}")
        # palavras grandes em qualquer plano; no primeiro plano do vídeo, a última (a que fecha o gancho) leva o golpe
        pg = g("palavras_grandes") or []
        for k, w in enumerate(pg):
            add(w.get("quadro"), "impacto" if (idx == 0 and k == len(pg) - 1) else "palavra", motivo=f"palavra {w.get('texto', '')}")
        # câmera que viaja grande: ar com o pico na metade do caminho
        cam = g("camera")
        ks = sorted([k for k in cam if isinstance(k, dict)], key=lambda k: k["quadro"]) if isinstance(cam, list) else []
        for a, b in zip(ks, ks[1:]):
            d = b["quadro"] - a["quadro"]
            escala = abs(math.log(max(b["z"], 1e-3) / max(a["z"], 1e-3)))
            desloc = a["z"] * math.dist(a["ancora"], b["ancora"])
            if 4 <= d <= 45 and (escala >= 0.25 or desloc >= 300):
                add((a["quadro"] + b["quadro"]) // 2, "whoosh" if d <= 15 else "whoosh_suave", None, "câmera viaja")
        # pedidos explícitos do plano (gancho, quebra): sempre entram
        for s_ in (g("som") if isinstance(g("som"), list) else []):
            ev.append((int(s_["quadro"]), s_["papel"], s_.get("dur"), f"{t}: pedido no plano", s_.get("nivel"), True))
    # um som por instante: no grupo de quadros vizinhos (<= 1) fica o papel mais importante
    pri = lambda e: PRIORIDADE.index(e[1]) if e[1] in PRIORIDADE else 99
    fixos = [e for e in ev if len(e) > 5 and e[5]]
    grandes = [f for f in fixos if f[1] in ("impacto", "riser", "baque", "clique")]
    fixos += [c for c in cortes if not any(abs(c[0] - f[0]) <= 2 for f in grandes)]
    ev = [e for e in ev if not (e[1] == "obturador" and any(c[1] == "obturador" and 0 <= e[0] - c[0] <= 3 for c in cortes))]
    soltos = sorted([e for e in ev if not (len(e) > 5 and e[5])], key=lambda e: e[0])
    grupos, out = [], []
    for e in soltos:
        if grupos and e[0] - grupos[-1][-1][0] <= 1:
            grupos[-1].append(e)
        else:
            grupos.append([e])
    ult = {}
    for gr in grupos:
        e = min(gr, key=pri)
        if any(abs(e[0] - f[0]) <= 1 for f in fixos):
            continue
        if e[1] in INTERVALO and e[0] - ult.get(e[1], -10 ** 6) < INTERVALO[e[1]]:
            continue
        ult[e[1]] = e[0]
        out.append(e)
    return sorted(out + fixos, key=lambda e: e[0]), amb


# ------------------------------------------------------------------ banco de sons
class Banco:
    def __init__(self, biblioteca=None, mapa=None):
        self.mapa = None
        arq = _caminho.mapa_sons(mapa)
        if arq.exists():
            m = json.loads(arq.read_text())
            bib = _caminho.pasta_sons(biblioteca) or Path(m.get("biblioteca", ""))
            if str(bib) and bib.exists():
                self.mapa, self.bib = m, bib
        self.cache, self.giro = {}, {}

    @property
    def origem(self):
        return "pasta de sons do usuário" if self.mapa else "reserva sintetizada (motor/som.py + kit/sfx)"

    def pega(self, papel, dur_s=None):
        """(som estéreo 48 kHz, âncora em s dentro dele, registro para o SFX_MAP)."""
        x, anc, reg = self._pega(papel, dur_s)
        tons = VARIA_TOM.get(papel)
        if tons:                                          # o mesmo som em outro tom (reamostragem: muda tom e duração)
            st = tons[(self.giro[papel] - 1) % len(tons)]
            if st:
                f = 2 ** (st / 12.0)
                n2 = max(2, int(len(x) / f))
                i = np.linspace(0, len(x) - 1, n2)
                x = np.stack([np.interp(i, np.arange(len(x)), x[:, c]) for c in range(2)], 1).astype(np.float32)
                anc = anc / f
                reg["semitons"] = st
        return x, anc, reg

    def _pega(self, papel, dur_s=None):
        k = self.giro.get(papel, 0)
        self.giro[papel] = k + 1
        if self.mapa and papel in self.mapa["sons"]:
            s = self.mapa["sons"][papel]
            r = s["recortes"][k % len(s["recortes"])]
            chave = (papel, k % len(s["recortes"]))
            if chave not in self.cache:
                x = ler(self.bib / s["arquivo"], ss=r["source_in"], t=r["source_out"] - r["source_in"])
                self.cache[chave] = x
            x = self.cache[chave]
            if dur_s is not None:                         # laço cortado na duração do evento
                x = x[:int(dur_s * SR)] if len(x) >= int(dur_s * SR) else np.tile(x, (int(dur_s * SR) // len(x) + 1, 1))[:int(dur_s * SR)]
                fi, fo = FADE_LACO.get(papel, (0.05, 0.08) if papel.startswith("amb_") else (0.02, 0.06))
                x = fades(x, fi, fo)
            else:
                x = fades(x, r["fade_in"], r["fade_out"])
            reg = {"source": s["arquivo"], "source_in": r["source_in"], "source_out": r["source_out"],
                   "anchor_at": r["anchor_at"], "fade_in": r["fade_in"], "fade_out": r["fade_out"], "reason": s["motivo"]}
            return x, r["anchor_at"] - r["source_in"], reg
        nome = RESERVA.get(papel)
        if nome is None:                                  # ambiente sem a biblioteca: silêncio
            return np.zeros((int((dur_s or 0.1) * SR), 2), np.float32), 0.0, {"source": "sem ambiente", "reason": papel}
        if nome.endswith(".wav"):
            x = ler(KIT / "sfx" / nome)
        else:
            x = som.efeito(nome).astype(np.float32)
        if dur_s is not None:
            x = np.tile(x, (int(dur_s * SR) // len(x) + 1, 1))[:int(dur_s * SR)]
            x = fades(x, 0.02, 0.06)
        return x, 0.0, {"source": f"reserva:{nome}", "reason": papel}


# ------------------------------------------------------------------ master
def medir(raw, filtro):
    err = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw),
                          "-af", f"{filtro},ebur128=peak=true" if filtro else "ebur128=peak=true", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    i = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    pk = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    return i, pk


def cadeia(g):
    """Ganho + limitador a 4x a taxa (pega o pico entre amostras: a 48 kHz o clique seco passava de -1 dBTP)."""
    return (f"volume={g:.2f}dB,aresample=192000,alimiter=limit=0.84:attack=5:release=60:level=false:latency=true,"
            f"aresample={SR}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto"); ap.add_argument("video"); ap.add_argument("saida")
    ap.add_argument("--trilha", default="pad_documental")
    ap.add_argument("--trilha-inicio", type=float, default=None)
    ap.add_argument("--abaixo", type=float, default=15.5)
    ap.add_argument("--sem-efeitos", action="store_true")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--biblioteca", default=None, help="pasta de sons do usuário (padrão: $EDITLABS_SONS)")
    ap.add_argument("--mapa", default=None, help="mapa de recortes de som_biblioteca.py (padrão: $EDITLABS_SONS_MAPA)")
    ap.add_argument("--guardar-mix", action="store_true", help="grava a soma antes do master em <projeto>/som/mix_pre.f32")
    a = ap.parse_args()

    proj = Path(a.projeto)
    plano = json.loads((proj / "plano.json").read_text())
    D = duracao(a.video)
    n = int(round(D * SR))
    voz = ler(proj / plano["audio"])
    voz = np.vstack([voz, np.zeros((max(0, n - len(voz)), 2), np.float32)])[:n]
    V, rv = nivel_fala(voz)
    mix = voz.copy()
    rel = {"video": a.video, "duracao_s": round(D, 2), "voz_nivel_db": round(V, 1)}

    if a.trilha != "nenhuma":
        if a.trilha == "partes":
            bed, info = faz_trilha_partes(plano["trilha_partes"], D)
        else:
            bed, info = faz_trilha(a.trilha, D, a.trilha_inicio)
        bed = np.vstack([bed, np.zeros((max(0, n - len(bed)), 2), np.float32)])[:n]
        B = float(np.median(rms_10ms(bed[int(1.0 * SR):max(int(1.0 * SR) + SR, n - int(2.5 * SR))])))
        g = 10 ** (((V - a.abaixo) - B) / 20)
        bed = bed * g * abaixa_sob_a_voz(rv, V, n)[:, None]
        mix += bed
        info.update({"abaixo_da_voz_db": a.abaixo, "abaixa_sob_a_voz_db": 3.0, "ganho_db": round(20 * math.log10(g), 1)})
        rel["trilha"] = info

    mapa = []
    if not a.sem_efeitos:
        banco = Banco(a.biblioteca, a.mapa)
        rel["efeitos_origem"] = banco.origem
        evs, ambs = eventos(plano["planos"])
        for (i0, i1, papel, motivo) in ambs:              # ambiente do b-roll: corta com a imagem
            x, _, reg = banco.pega(papel, (i1 - i0) / FPS)
            ganho = (V + NIVEL_AMBIENTE) - nivel_efeito(x)
            x = x * 10 ** (ganho / 20)
            a0 = int(round(i0 / FPS * SR)); a1 = min(n, a0 + len(x))
            if a1 > a0:
                mix[a0:a1] += x[:a1 - a0]
            reg.update({"timeline_at": round(i0 / FPS, 3), "quadro": i0, "papel": papel, "nivel_voz_db": NIVEL_AMBIENTE,
                        "gain_db": round(ganho, 1), "evento": motivo, "dur_s": round((i1 - i0) / FPS, 2)})
            mapa.append(reg)
        origs = []
        for p_ in plano["planos"]:                        # som original do vídeo real, no tempo da imagem
            trechos = []
            ao = p_.get("audio_original")
            if p_.get("tipo") == "video_clip" and ao:
                trechos.append({"arq": p_["clip"] if ao is True else ao, "ss": float(p_.get("audio_ss", p_.get("ss", 0.0))),
                                "vel": float(p_.get("vel", 1.0)), "ate": p_.get("audio_ate"), "congela": p_.get("congela"),
                                "nivel": float(p_.get("audio_nivel", -9.0)), "abaixa": float(p_.get("audio_abaixa", 6.0))})
            for au in p_.get("audios") or []:              # tela dividida: um som por lado
                lado = (p_.get("lados") or [{}])[int(au.get("lado", 0))]
                trechos.append({"arq": lado["clip"] if au.get("arquivo", True) is True else au["arquivo"],
                                "ss": float(au.get("ss", lado.get("ss", 0.0))), "vel": float(lado.get("vel", 1.0)),
                                "ate": au.get("ate"), "congela": lado.get("congela"),
                                "nivel": float(au.get("nivel", -9.0)), "abaixa": float(au.get("abaixa", 6.0))})
            for tr in trechos:
                dur = (p_["fim"] - p_["inicio"]) / FPS
                ate = tr["ate"]
                if tr["congela"] is not None:             # a imagem para: o som original para junto
                    fim_c = tr["ss"] + float(tr["congela"]) * tr["vel"]
                    ate = fim_c if ate is None else min(ate, fim_c)
                x = ler_trecho(tr["arq"], tr["ss"], dur, tr["vel"], ate)
                if len(x) < SR * 0.05:
                    continue
                x = fades(x, 0.03, 0.12)
                ganho = (V + tr["nivel"]) - nivel_efeito(x)
                a0 = int(round(p_["inicio"] / FPS * SR)); a1 = min(n, a0 + len(x))
                env = abaixa_sob_a_voz(rv, V, n, db=tr["abaixa"])[a0:a1]
                mix[a0:a1] += x[:a1 - a0] * 10 ** (ganho / 20) * env[:, None]
                reg = {"timeline_at": round(p_["inicio"] / FPS, 3), "quadro": p_["inicio"], "papel": "audio_original",
                       "source": str(tr["arq"]), "source_in": round(tr["ss"], 3), "vel": tr["vel"], "nivel_voz_db": tr["nivel"],
                       "gain_db": round(ganho, 1), "dur_s": round(len(x) / SR, 2), "evento": "som original do vídeo real"}
                mapa.append(reg); origs.append(reg)
        if origs:
            rel["audio_original"] = [{k: o[k] for k in ("timeline_at", "source", "source_in", "vel", "gain_db", "dur_s")}
                                     for o in origs]
        for e in evs:
            q, papel, dur, motivo = e[:4]
            nivel = e[4] if len(e) > 4 and e[4] is not None else NIVEL.get(papel, -16)
            x, ancora, reg = banco.pega(papel, dur / FPS if dur else None)
            ganho = (V + nivel) - nivel_efeito(x)
            x = x * 10 ** (ganho / 20)
            ini = int(round((q / FPS - ancora) * SR))
            if ini < 0:
                x, ini = x[-ini:], 0
            fim = min(n, ini + len(x))
            if fim > ini:
                mix[ini:fim] += x[:fim - ini]
            reg.update({"timeline_at": round(q / FPS, 3), "quadro": q, "papel": papel, "nivel_voz_db": nivel,
                        "gain_db": round(ganho, 1), "evento": motivo})
            mapa.append(reg)
        cont = {}
        for m in mapa:
            cont[m["papel"]] = cont.get(m["papel"], 0) + 1
        rel["efeitos"] = cont

    with tempfile.TemporaryDirectory() as tmp:
        raw = (proj / "som" / "mix_pre.f32") if a.guardar_mix else Path(tmp) / "mix.f32"
        raw.parent.mkdir(exist_ok=True)
        mix.astype("<f4").tofile(raw)
        i0, _ = medir(raw, None)
        g = a.lufs - i0
        for _ in range(3):
            i1, pk = medir(raw, cadeia(g))
            if abs(i1 - a.lufs) <= 0.2:
                break
            g += a.lufs - i1
        rel["master"] = {"lufs_antes": round(i0, 1), "ganho_db": round(g, 2), "lufs": round(i1, 1), "true_peak_db": round(pk, 1)}
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw),
                        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-af", cadeia(g), "-c:a", "aac", "-b:a", "192k",
                        "-t", f"{D:.3f}", "-movflags", "+faststart", a.saida], check=True)

    (proj / "som").mkdir(exist_ok=True)
    (proj / "som" / "SFX_MAP.json").write_text(json.dumps(mapa, indent=1, ensure_ascii=False))
    (proj / "som" / "mix.json").write_text(json.dumps(rel, indent=1, ensure_ascii=False))
    print(json.dumps(rel, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
