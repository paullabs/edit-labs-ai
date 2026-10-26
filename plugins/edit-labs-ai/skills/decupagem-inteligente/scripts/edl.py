"""F2: decisoes.json (escolhas do Editor) → edl.json + MARCAS.md + roteiro_montado.txt + pendencias.md.

  di edl <id> [--projeto P]

O modelo escreve só escolhas com motivo. Tempo, folga, resíduo, frame, escala e ganho saem daqui.
Régua (§05 5.3): junta dentro de silêncio medido, ≥ 0,15 s de qualquer palavra, teste de energia
(RMS 40 ms de cada lado ≥ 15 dB abaixo da palavra vizinha), resíduo 0,30–0,35 s, quantizado ao frame.
Sem ponto que passe: BLOCKER e o EDL não sai (nunca baixa a folga).
"""
from __future__ import annotations

import argparse
import math
import re
import statistics
from pathlib import Path

import silencio as SIL
from comum import (validar_schema, edl_assinatura, DIError, achar_projeto, agora, aplicar_correcoes, carregar, check, config, falhas,
                   gravar_json, gravar_texto, ler_json, mmss, norm_palavra, registrar_checks, salvar, tentativa_atual)

CONECTORES = {"mas", "entao", "ai", "e", "porque", "uhum", "olha", "agora", "cara", "tipo", "ne"}


def _q(t: float, fps: float, modo: str) -> float:
    f = t * fps
    f = math.ceil(f - 1e-6) if modo == "cima" else (math.floor(f + 1e-6) if modo == "baixo" else round(f))
    return f / fps


class Regua:
    def __init__(self, cfg: dict):
        self.folga = float(cfg.get("folga_palavra_s", 0.15))
        self.folga_sil = float(cfg.get("folga_silencio_s", 0.06))
        rs = cfg.get("residuo_s", [0.30, 0.35])
        self.res_min, self.res_max = float(rs[0]), float(rs[1])
        self.energia = float(cfg.get("energia_db", 15))
        self.pausa_max = float(cfg.get("pausa_max_s", 0.35))
        self.colapsar_min = float(cfg.get("colapsar_min_s", 0.6))
        pi = cfg.get("punch_in") or {}
        self.escala = float(pi.get("escala", 1.035))
        self.min_troca = float(pi.get("min_entre_trocas_s", 1.2))
        self.emendas = cfg.get("emendas", "punch_in")


def _mid(w: dict) -> float:
    return (w["t"] + w["e"]) / 2


def _silencios_entre(sil: list[dict], a: float, b: float, dmin: float) -> list[dict]:
    return [x for x in sil if x["e"] > a and x["t"] < b and min(x["e"], b) - max(x["t"], a) >= dmin]


def _energia_ok(c: float, ref_db: float, x, sr, R) -> tuple[bool, float]:
    """RMS nos 40 ms de cada lado ≥ 15 dB abaixo do nível da VOZ vizinha (medido, não a palavra do Whisper)."""
    a, d = SIL.energia_local(x, sr, c)
    return max(a, d) <= ref_db - R.energia, round(max(a, d), 1)


def _pico(x, sr, a: float, b: float) -> float:
    """Nível da palavra vizinha = o pico de RMS (janelas de 40 ms) no trecho de voz."""
    t, melhor = a, -120.0
    while t < b:
        melhor = max(melhor, SIL.rms_trecho(x, sr, t, t + 0.04))
        t += 0.02
    return melhor


def _respiro(vao: float) -> float:
    """Vão entre a voz e o silêncio medido. Até 0,15 s é a cauda da própria voz (decaimento); acima disso
    é inspiração/expiração que fica inteira no corte e não conta como silêncio sobrando."""
    return round(vao, 3) if vao >= 0.15 else 0.0


def resp_txt(ji: dict) -> str:
    if not ji.get("respiro"):
        return ""
    sil_ = round((ji.get("residuo") or 0) - ji["respiro"], 2)
    return f" = {sil_} silêncio + {ji['respiro']} respiro"


def _menor_energia(lo: float, hi: float, x, sr, fps: float, alvo: float | None = None) -> float | None:
    """Sem silêncio medido: o quadro mais quieto. Com `alvo`, o quadro mais perto do alvo entre os que
    ficam a até 6 dB do mais quieto (quieto o bastante, sem arrastar a pausa para longe da voz)."""
    cand = []
    t = _q(lo, fps, "cima")
    while t <= hi + 1e-9:
        cand.append((max(SIL.energia_local(x, sr, t)), t))
        t += 1 / fps
    if not cand:
        return None
    emin = min(e for e, _ in cand)
    if alvo is None:
        return min(cand)[1]
    return min((abs(t - alvo), t) for e, t in cand if e <= emin + 6.0)[1]


def ponto_saida(pal, a: int, prox_t: float, sil, x, sr, R, fps, alvo: float, limiar: float):
    """Corte DEPOIS da palavra a, pelo FIM REAL DA VOZ (envelope), não pela borda do Whisper,
    que cola palavras e às vezes as põe dentro do silêncio. O ponto fica no silêncio medido que
    começa quando a voz de `a` termina, ~0,16 s depois dela, ≥ 0,06 s da borda do silêncio."""
    prox_mid = (prox_t + pal[a + 1]["e"]) / 2 if a + 1 < len(pal) else prox_t + 1.0
    fim_voz = SIL.voz_fim(x, sr, pal[a]["t"], min(pal[a]["e"] + 0.25, prox_mid), limiar, acima=0.0)
    if fim_voz is None:
        fim_voz = pal[a]["e"]
    ref = _pico(x, sr, fim_voz - 0.5, fim_voz)
    for s_ in sil:
        if s_["t"] < fim_voz - 0.04 or s_["d"] < 0.12:
            continue
        if s_["t"] > fim_voz + 1.0:
            break
        c = _q(min(max(fim_voz + alvo, s_["t"] + R.folga_sil), s_["e"] - R.folga_sil), fps, "baixo")
        if c < max(s_["t"] + R.folga_sil - 0.02, fim_voz + 0.06):
            c = _q(max(s_["t"] + R.folga_sil, fim_voz + 0.06), fps, "cima")
        ok, db = _energia_ok(c, ref, x, sr, R)
        if ok and c <= s_["e"] - 0.02:
            return c, {"modo": "acustico", "voz": fim_voz, "silencio": [s_["t"], s_["e"]], "respiro": _respiro(s_["t"] - fim_voz),
                       "folga_silencio": round(min(c - s_["t"], s_["e"] - c), 3), "folga_voz": round(c - fim_voz, 3),
                       "rms_local_db": db, "ref_voz_db": round(ref, 1), "relaxado": False}, s_
    # o limite é a VOLTA MEDIDA da voz da próxima palavra, não o início do Whisper (que costuma vir adiantado)
    prox_voz = SIL.voz_inicio(x, sr, fim_voz + 0.04, max(prox_t, pal[a + 1]["e"] if a + 1 < len(pal) else prox_t),
                              limiar, acima=0.0)
    lim_fim = max(prox_t, prox_voz - 0.02) if prox_voz is not None else prox_t
    c = _menor_energia(fim_voz + 0.04, min(lim_fim, fim_voz + 0.5), x, sr, fps, alvo=fim_voz + alvo)
    if c is not None:
        ok, db = _energia_ok(c, ref, x, sr, R)
        if ok:
            return c, {"modo": "energia", "voz": fim_voz, "silencio": None, "folga_voz": round(c - fim_voz, 3),
                       "rms_local_db": db, "ref_voz_db": round(ref, 1), "relaxado": True}, None
    return None, f"a voz de '{pal[a]['w']}' ({mmss(fim_voz)}) emenda direto na próxima fala: sem silêncio para cortar", None


def ponto_no_vale(pal, a: int, x, sr, R, fps, motivo: str):
    """Saída DECLARADA pelo Editor (decisoes.json → saida_no_vale, com motivo) onde a fala emenda sem silêncio: o corte
    vai para o quadro mais quieto entre o fim de `a` e o começo da seguinte. Como o que vem depois do corte some, vale
    o lado de dentro: os 40 ms antes do corte ≥ 15 dB abaixo da voz e o próprio ponto (10 ms) ≥ 20 dB abaixo.
    Sai relaxada: crossfade 20 ms e V17_relaxada HIGH para o Diretor e para a escuta do usuário."""
    lo = pal[a]["e"] - 0.10
    hi = (pal[a + 1]["t"] + 0.10) if a + 1 < len(pal) else pal[a]["e"] + 0.30
    c = _menor_energia(lo, hi, x, sr, fps)
    if c is None:
        return None, f"saida_no_vale depois de '{pal[a]['w']}': janela vazia"
    ref = _pico(x, sr, c - 0.5, c)
    antes, _ = SIL.energia_local(x, sr, c)
    ponto = SIL.rms_trecho(x, sr, c - 0.005, c + 0.005)
    if antes > ref - R.energia or ponto > ref - R.energia - 5:
        return None, (f"saida_no_vale depois de '{pal[a]['w']}' ({mmss(c)}): vale raso — {antes:.1f} dB antes e {ponto:.1f} dB "
                      f"no ponto para voz a {ref:.1f} dB")
    return c, {"modo": "vale", "voz": None, "silencio": None, "folga_voz": None, "rms_local_db": round(antes, 1),
               "rms_ponto_db": round(ponto, 1), "ref_voz_db": round(ref, 1), "relaxado": True, "declarado": motivo}


def _depois_da_voz_em_curso(x, sr, lo: float, hi: float, limiar: float) -> float:
    """Se a janela de busca já começa com voz soando (cauda da palavra anterior, que o Whisper encurtou), o início
    da palavra b não é ali: pula até o primeiro quadro abaixo do limiar e busca o início real depois dele."""
    env, hop = SIL.env_cache(x, sr)
    i, fim = max(0, int(lo / hop)), min(len(env) - 1, int(hi / hop))
    if i >= fim or env[i] <= limiar:
        return lo
    while i < fim and env[i] > limiar:
        i += 1
    return i * hop if i < fim else lo


def voz_inicio_sustentada(x, sr, lo: float, hi: float, limiar: float, min_s: float = 0.25) -> float | None:
    """Primeiro início de voz que se SUSTENTA (≥ 70 % dos quadros acima do limiar nos min_s seguintes).
    Estalo de boca ou respiro curto antes da fala não conta. Usado só quando o Editor pede (entrada: voz_sustentada)."""
    env, hop = SIL.env_cache(x, sr)
    a, b = max(0, int(lo / hop)), min(len(env) - 1, int(hi / hop))
    n = max(1, int(min_s / hop))
    for i in range(a, b):
        if env[i] > limiar and (env[i:i + n] > limiar).mean() >= 0.7:
            return i * hop
    return None


def ponto_entrada(pal, b: int, ant_e: float, sil, x, sr, R, fps, alvo: float, limiar: float, sustentada: bool = False):
    """Corte ANTES da palavra b, pelo INÍCIO REAL DA VOZ: o silêncio medido que termina quando a voz
    de `b` começa; o ponto fica ~0,16 s antes dela, ≥ 0,06 s da borda do silêncio."""
    ant_mid = (pal[b - 1]["t"] + ant_e) / 2 if b > 0 else 0.0
    lo_ = _depois_da_voz_em_curso(x, sr, max(pal[b]["t"] - 0.45, ant_mid), pal[b]["e"] + 0.3, limiar)
    ini_voz = (voz_inicio_sustentada(x, sr, lo_, pal[b]["e"] + 0.3, limiar) if sustentada
               else SIL.voz_inicio(x, sr, lo_, pal[b]["e"] + 0.3, limiar, acima=0.0))
    if ini_voz is None:
        ini_voz = pal[b]["t"]
    ref = _pico(x, sr, ini_voz, ini_voz + 0.5)
    for s_ in reversed(sil):
        if s_["e"] > ini_voz + 0.04 or s_["d"] < 0.12:
            continue
        if s_["e"] < ini_voz - 1.0:
            break
        c = _q(max(min(ini_voz - alvo, s_["e"] - R.folga_sil), s_["t"] + R.folga_sil), fps, "cima")
        if c > min(s_["e"] - R.folga_sil + 0.02, ini_voz - 0.06):
            c = _q(min(s_["e"] - R.folga_sil, ini_voz - 0.06), fps, "baixo")
        ok, db = _energia_ok(c, ref, x, sr, R)
        if ok and c >= s_["t"] + 0.02:
            return c, {"modo": "acustico", "voz": ini_voz, "silencio": [s_["t"], s_["e"]], "respiro": _respiro(ini_voz - s_["e"]),
                       "folga_silencio": round(min(c - s_["t"], s_["e"] - c), 3), "folga_voz": round(ini_voz - c, 3),
                       "rms_local_db": db, "ref_voz_db": round(ref, 1), "relaxado": False}, s_
    c = _menor_energia(max(ant_e, ini_voz - 0.5), ini_voz - 0.04, x, sr, fps, alvo=ini_voz - alvo)
    if c is not None:
        ok, db = _energia_ok(c, ref, x, sr, R)
        if ok:
            return c, {"modo": "energia", "voz": ini_voz, "silencio": None, "folga_voz": round(ini_voz - c, 3),
                       "rms_local_db": db, "ref_voz_db": round(ref, 1), "relaxado": True}, None
    return None, f"a voz de '{pal[b]['w']}' ({mmss(ini_voz)}) sai direto da fala anterior: sem silêncio para cortar", None


VIZ = [lambda i: -20.0]  # trocado em montar() pelo RMS medido de cada palavra


def montar(projeto: Path, vid: str) -> dict:
    projeto = Path(projeto)
    dd = projeto / "02_decupagem" / vid
    dec = ler_json(dd / "decisoes.json")
    if dec:
        validar_schema("decisoes", dec, f"02_decupagem/{vid}/decisoes.json")
    if not dec:
        raise DIError(f"{dd / 'decisoes.json'} não existe: o Editor escreve as escolhas primeiro")
    doc = ler_json(projeto / "01_transcript" / "palavras.json")
    pal = doc["palavras"]
    rt = ler_json(projeto / "02_decupagem" / "retakes.json")
    silj = ler_json(projeto / "01_transcript" / "silencios.json")
    sil = silj["silencios"]
    fonte = ler_json(projeto / "00_fonte" / "fonte.json")
    fps = fonte["fps"][0] / fonte["fps"][1]
    cfg = config(projeto)
    R = Regua(cfg)
    x, sr = SIL.carregar_wav(projeto / "00_fonte" / "_audio_16k.wav")
    rms = {r["i"]: r["db"] for r in silj.get("rms_palavras", [])}
    frases = {f["id"]: f for f in rt["frases"]}
    grupos = {g["id"]: g for g in rt["grupos"]}
    fillers = {f["i"]: f for f in (ler_json(projeto / "02_decupagem" / "fillers.json") or {}).get("fillers", [])}
    checks, pend = [], []

    # 1) palavras mantidas, com motivo
    motivo_de: dict[int, str] = {}
    ordem_editor: list[int] = []
    sustenta: set[int] = set()
    for m_ in dec.get("manter", []):
        if "de_palavra" in m_:
            a, b = int(m_["de_palavra"]), int(m_["ate_palavra"])
        elif "grupo" in m_:
            g = grupos.get(m_["grupo"])
            if not g:
                raise DIError(f"grupo {m_['grupo']} não existe em retakes.json")
            tom = next((t for t in g["tomadas"] if t["tomada"] == int(m_["tomada"])), None)
            if not tom:
                raise DIError(f"{m_['grupo']} não tem tomada {m_['tomada']}")
            f = frases[tom["frase"]]
            a, b = f["i0"], f["i1"]
        elif "frase" in m_:
            f = frases.get(int(m_["frase"]))
            if not f:
                raise DIError(f"frase F{int(m_['frase']):03d} não existe")
            a, b = f["i0"], f["i1"]
        else:
            raise DIError(f"item de manter sem frase/grupo/de_palavra: {m_}")
        if not m_.get("motivo"):
            raise DIError(f"item de manter sem motivo: {m_}")
        if m_.get("entrada") == "voz_sustentada":
            sustenta.add(a)
        for i in range(a, b + 1):
            if i not in motivo_de:
                ordem_editor.append(i)
            motivo_de[i] = m_["motivo"]
    vetados = {int(v["palavra"]) for v in dec.get("fillers_vetados", [])}
    tirados = []
    for i in list(motivo_de):
        fl = fillers.get(i)
        if fl and i not in vetados:
            tirados.append(i)
            del motivo_de[i]
    ordem = [i for i in ordem_editor if i in motivo_de]  # a ordem do vídeo é a da lista `manter`
    voltas = [f"{mmss(pal[b]['t'])} depois de {mmss(pal[a]['t'])}" for a, b in zip(ordem, ordem[1:]) if b < a]
    checks.append(check("V16_ordem", not voltas, "aviso", medido=voltas or "cronológica",
                        detalhe="tomada gravada antes usada depois: normal em retake; o Diretor confere causa e sentido"))
    if not ordem:
        raise DIError("nada mantido em decisoes.json")

    # V15: duas tomadas inteiras do mesmo grupo mantidas = retake vazado no papel
    from retakes import sim as _sim
    vaz, declaradas = [], []
    intencional = set()
    for m_ in dec.get("manter", []):
        if m_.get("repeticao_intencional"):
            if "frase" in m_:
                intencional.add(int(m_["frase"]))
            elif "grupo" in m_:
                t_ = next((t for t in rt["grupos"][[g["id"] for g in rt["grupos"]].index(m_["grupo"])]["tomadas"]
                           if t["tomada"] == int(m_["tomada"])), None) if m_["grupo"] in [g["id"] for g in rt["grupos"]] else None
                if t_:
                    intencional.add(t_["frase"])
    for g in rt["grupos"]:
        inteiras = [t for t in g["tomadas"] if all(i in motivo_de for i in range(frases[t["frase"]]["i0"], frases[t["frase"]]["i1"] + 1))]
        for x_, y_ in ((x_, y_) for k_, x_ in enumerate(inteiras) for y_ in inteiras[k_ + 1:]):
            if _sim(frases[x_["frase"]]["norm"], frases[y_["frase"]]["norm"]) >= 0.72:  # as duas dizem a mesma coisa
                par_ = f"{g['id']} t{x_['tomada']}+t{y_['tomada']}"
                (declaradas if (x_["frase"] in intencional or y_["frase"] in intencional) else vaz).append(par_)
    checks.append(check("V15b_repeticao_declarada", True, "aviso", medido=declaradas or 0,
                        detalhe="repetição que o Editor declarou intencional (repeticao_intencional, com motivo): o Diretor julga"))
    checks.append(check("V15_retake_no_papel", not vaz, "BLOCKER", medido=vaz or 0, esperado="nenhum grupo com 2 tomadas inteiras"))

    # 2) juntas: A (salto) e B (pausa colapsada entre frases)
    fim_frase = {f["i1"] for f in rt["frases"]}
    preserva = {int(p["apos_palavra"]): p.get("funcao", "") for p in dec.get("pausas_preservar", [])}
    colapsa_intra = {int(p["apos_palavra"]) for p in dec.get("pausas_colapsar_intra", [])}
    seco = {int(p["apos_palavra"]): p.get("motivo", "") for p in dec.get("emendas_seco", [])}
    saida_vale = {int(p["apos_palavra"]): p.get("motivo", "") for p in dec.get("saida_no_vale", [])}
    if any(not v.strip() for v in saida_vale.values()):
        raise DIError("saida_no_vale sem motivo: diga por que a emenda sem silêncio é aceitável (ex.: pedido do usuário)")
    # Corte DENTRO do que o Whisper deu como vizinhas: a fala abandonada entre #a e #a+1 não tem
    # palavra própria (ele a engoliu numa palavra esticada), então o ponto sai dos tempos MEDIDOS
    # no bruto, não do transcript (armadilhas 60). #a+1 passa a valer pela tomada que recomeça.
    trecho = {int(p["apos_palavra"]): p for p in dec.get("cortar_trecho", [])}
    for k_, p_ in trecho.items():
        if not str(p_.get("motivo", "")).strip() or not all(c in p_ for c in ("abandona_de", "abandona_ate", "retoma_em")):
            raise DIError("cortar_trecho precisa de apos_palavra, abandona_de, abandona_ate, retoma_em (tempos do bruto, medidos) e motivo")
    cortes = []  # (a, b, tipo)
    pausas_mantidas = []
    def sil_medido(a: int, b: int):
        """Maior silêncio MEDIDO entre o meio da palavra a e o meio da b: o Whisper cola palavras e esconde a pausa."""
        lo, hi = (pal[a]["t"] + pal[a]["e"]) / 2, (pal[b]["t"] + pal[b]["e"]) / 2
        cand = [s_ for s_ in sil if lo <= (s_["t"] + s_["e"]) / 2 < hi]
        return max(cand, key=lambda s_: s_["d"]) if cand else None

    for a, b in zip(ordem, ordem[1:]):
        if a in trecho:
            if b != a + 1:
                raise DIError(f"cortar_trecho após #{a}: a palavra mantida seguinte tem de ser #{a + 1}, veio #{b}")
            cortes.append((a, b, "A"))
            continue
        vao = pal[b]["t"] - pal[a]["e"]
        faixa = (pal[a]["e"], pal[b]["t"])
        if b == a + 1:
            # Entre vizinhas, pausa é o silêncio MEDIDO, não o vão do Whisper: ele erra a borda em
            # até 0,15 s e inventa vão onde a voz é contínua. Já houve três "pausas"
            # declaradas com função sem nenhuma medida — uma escondia um falso começo (armadilhas 60)
            # e as outras duas eram voz contínua (0,00 s e 0,13 s sem voz).
            sm = sil_medido(a, b)
            vao, faixa = (sm["d"], (sm["t"], sm["e"])) if sm else (0.0, faixa)
        if b != a + 1:
            cortes.append((a, b, "A"))
        elif a in preserva:
            pausas_mantidas.append({"apos_palavra": a, "vao": round(vao, 2), "funcao": preserva[a], "_faixa": faixa})
        elif vao >= R.colapsar_min and (a in fim_frase or a in colapsa_intra):
            cortes.append((a, b, "B"))
        elif vao > R.pausa_max:
            pausas_mantidas.append({"apos_palavra": a, "vao": round(vao, 2), "funcao": "(não listada)", "_faixa": faixa})
    # 3) pontos de corte: dentro de silêncio MEDIDO (o Whisper cola palavras vizinhas e engole a pausa)
    VIZ[0] = lambda i: rms.get(i, -20.0)
    meia = (R.res_min + R.res_max) / 4  # ~0,16 s de silêncio de cada lado
    bloq = []
    ini = ordem[0]
    ant_e = pal[ini - 1]["e"] if ini > 0 else 0.0
    fala = sorted(v for v in rms.values() if v > silj["limiar_db"] + 10)
    mediana_fala = fala[len(fala) // 2] if fala else -20.0
    lim = max(silj["limiar_db"] + 8, mediana_fala - 20)  # voz = acima disto; respiração fica abaixo
    tin, ii, _ = ponto_entrada(pal, ini, ant_e, sil, x, sr, R, fps, 0.25, lim, ini in sustenta)
    if tin is None:
        tin, ii = _q(max(0.0, pal[ini]["t"] - 0.25), fps, "baixo"), {"modo": "sem_silencio", "relaxado": True}
    seg = {"i0": ini, "in": tin, "junta_in": {"tipo": "inicio", **ii}}
    segs = []
    for (a, b, tipo) in cortes:
        prox_t = pal[a + 1]["t"] if a + 1 < len(pal) else pal[a]["e"] + 1.0
        ant_b = pal[b - 1]["e"] if b > 0 else 0.0
        pal_in = pal
        if a in trecho:
            tr_ = trecho[a]
            prox_t = float(tr_["abandona_de"])      # a saída procura silêncio antes da fala abandonada
            ant_b = float(tr_["abandona_ate"])      # e a entrada, depois dela
            pal_in = list(pal)
            pal_in[b] = dict(pal[b], t=float(tr_["retoma_em"]))
        out, io, s_out = ponto_saida(pal, a, prox_t, sil, x, sr, R, fps, meia, lim)
        if out is None and a in saida_vale:
            out, io = ponto_no_vale(pal, a, x, sr, R, fps, saida_vale[a])
        # saída colada no vale não deixa silêncio do lado de fora: o resíduo da junta (V19) fica todo na entrada
        alvo_in = (R.res_min + R.res_max) / 2 if isinstance(io, dict) and io.get("modo") == "vale" else meia
        tin, ii, _ = ponto_entrada(pal_in, b, ant_b, sil, x, sr, R, fps, alvo_in, lim, b in sustenta)
        if a in trecho and isinstance(ii, dict):
            ii = {**ii, "cortar_trecho": trecho[a]["motivo"]}
        if tipo == "B" and (out is None or tin is None or tin - out < 2 / fps):
            pausas_mantidas.append({"apos_palavra": a, "vao": round(pal[b]["t"] - pal[a]["e"], 2),
                                    "funcao": "(sem silêncio limpo para encurtar: fica)"})
            continue
        if out is None or tin is None:
            bloq.append(f"junta {mmss(pal[a]['e'])}→{mmss(pal[b]['t'])} ('{pal[a]['w']}' | '{pal[b]['w']}'): {io if out is None else ii}")
            continue
        seg.update(i1=a, out=out, junta_out={"tipo": tipo, **io})
        segs.append(seg)
        seg = {"i0": b, "in": tin, "junta_in": {"tipo": tipo, **ii}}
    fim = ordem[-1]
    prox_t = pal[fim + 1]["t"] if fim + 1 < len(pal) else pal[fim]["e"] + 1.0
    out, io, _ = ponto_saida(pal, fim, prox_t, sil, x, sr, R, fps, 0.35, lim)
    if out is None:
        out, io = _q(pal[fim]["e"] + 0.3, fps, "cima"), {"modo": "sem_silencio", "relaxado": True}
    seg.update(i1=fim, out=out, junta_out={"tipo": "fim", **io})
    segs.append(seg)
    checks.append(check("V17_junta_em_silencio", not bloq, "BLOCKER", medido=len(bloq), esperado="0 juntas sem ponto válido",
                        detalhe=" · ".join(bloq[:6])))
    # V18: no modo acústico a margem é contra a borda do silêncio medido (≥ 0,06 s, 0,04 depois de quantizar);
    # a borda do Whisper não conta, porque ele cola palavras e erra ~0,15 s justamente aí.
    margens = [j.get("folga_silencio") for s_ in segs for j in (s_["junta_in"], s_["junta_out"])
               if j.get("modo") == "acustico" and j.get("tipo") not in ("inicio", "fim")]
    menor = min(margens) if margens else None
    checks.append(check("V18_folga_silencio", menor is None or menor >= R.folga_sil - 0.02 - 1e-6, "BLOCKER",
                        medido=menor, esperado=f"≥ {R.folga_sil - 0.02:.2f} s da borda do silêncio medido"))
    relax = [s for s in segs if s["junta_in"].get("relaxado") or s["junta_out"].get("relaxado")]
    if relax:
        checks.append(check("V17_relaxada", False, "HIGH", medido=len(relax), detalhe="junta fora de silêncio medido com energia ok: crossfade 20 ms"))

    # 4) timeline em frames, escala (punch-in), ganho
    tl = 0
    fala_db = []
    for n, s in enumerate(segs, 1):
        fr = int(round((s["out"] - s["in"]) * fps))
        s.update(n=n, frames=fr, timeline_in_f=tl, timeline_out_f=tl + fr)
        tl += fr
        dbs = [rms[i] for i in range(s["i0"], s["i1"] + 1) if i in rms and i in motivo_de]
        s["_fala_db"] = statistics.median(dbs) if dbs else None
        fala_db.append(s["_fala_db"])
    med = statistics.median([v for v in fala_db if v is not None]) if any(v is not None for v in fala_db) else None
    escala_ant = 1.0
    for k, s in enumerate(segs):
        if k == 0:
            s["escala"], cob = 1.0, None
        else:
            a = segs[k - 1]["i1"]
            dur_prev = (segs[k - 1]["out"] - segs[k - 1]["in"])
            if R.emendas != "punch_in":
                cob = "seco"
            elif a in seco:
                cob = "seco"
            elif dur_prev < R.min_troca or (s["out"] - s["in"]) < R.min_troca:
                cob = "seco"
            else:
                cob = "punch_in"
            s["escala"] = (R.escala if escala_ant == 1.0 else 1.0) if cob == "punch_in" else escala_ant
            s["junta_in"]["cobertura"] = cob
            if a in seco:
                s["junta_in"]["motivo_seco"] = seco[a]
        escala_ant = s["escala"]
        s["ganho_db"] = round(max(-6.0, min(6.0, med - s["_fala_db"])), 1) if (med is not None and s["_fala_db"] is not None) else 0.0
        s["residuo"] = None
    nivelar_juntas(segs, x, sr, silj["limiar_db"])
    for k in range(1, len(segs)):
        a, b = segs[k - 1], segs[k]
        vo, vi = a["junta_out"].get("voz"), b["junta_in"].get("voz")
        r_out = a["out"] - (vo if vo is not None else pal[a["i1"]]["e"])
        r_in = (vi if vi is not None else pal[b["i0"]]["t"]) - b["in"]
        b["junta_in"]["residuo"] = round(max(0.0, r_out) + max(0.0, r_in), 3)
        # respiração que fica inteira (antes da voz ou depois dela) não é silêncio sobrando: é a fala respirando
        b["junta_in"]["respiro"] = round(min(b["junta_in"]["residuo"], (a["junta_out"].get("respiro") or 0.0) + (b["junta_in"].get("respiro") or 0.0)), 3)
    res = [s["junta_in"]["residuo"] for s in segs[1:]]
    sil_res = [round(s["junta_in"]["residuo"] - s["junta_in"]["respiro"], 3) for s in segs[1:]]
    fora = [r for r in sil_res if not (R.res_min - 0.04 <= r <= R.res_max + 0.04)]
    grave = [f"{r:.2f} (respiro {r - q:.2f})" if r != q else f"{r:.2f}" for r, q in zip(res, sil_res) if q < 0.20 or q > 0.60 or r > 0.95]
    checks.append(check("V19_residuo", not grave, "HIGH" if grave else "aviso",
                        medido=f"{min(res):.2f}–{max(res):.2f} s" if res else "sem juntas",
                        esperado=f"silêncio sobrando {R.res_min:.2f}–{R.res_max:.2f} s (a calibrar ouvindo); HIGH se o silêncio < 0,20 ou > 0,60, ou se silêncio + respiro > 0,95",
                        detalhe=("fora: " + ", ".join(grave)) if grave else ((f"{len(fora)} fora do alvo: " + ", ".join(f"{r:.2f}" for r in fora)) if fora else "")))

    # 5) textos e auditorias de papel
    kept_words = [i for s in segs for i in range(s["i0"], s["i1"] + 1) if i in motivo_de]
    norm_k = [norm_palavra(pal[i]["w"]) for i in kept_words]
    rep5 = []
    for j in range(len(norm_k) - 4):
        for j2 in range(j + 5, len(norm_k) - 4):
            if pal[kept_words[j2]]["t"] - pal[kept_words[j]]["t"] > 30:
                break
            if norm_k[j:j + 5] == norm_k[j2:j2 + 5]:
                rep5.append(" ".join(norm_k[j:j + 5]))
                break
    pos_junta = []
    for k in range(1, len(segs)):
        idx = kept_words.index(segs[k]["i0"]) if segs[k]["i0"] in kept_words else None
        if idx is not None:
            ant, dep = norm_k[max(0, idx - 8):idx], norm_k[idx:idx + 8]
            for n3 in range(len(dep) - 2):
                tri = dep[n3:n3 + 3]
                if any(ant[m:m + 3] == tri for m in range(len(ant) - 2)):
                    pos_junta.append(f"'{' '.join(tri)}' em {mmss(pal[segs[k]['i0']]['t'])}")
                    break
    checks.append(check("V22c_repeticao", not rep5 and not pos_junta, "HIGH", medido=(rep5 + pos_junta)[:6] or 0,
                        esperado="nenhuma frase repetida (5 palavras em 30 s; 3 palavras a ±8 de uma junta)"))
    primeira = norm_palavra(pal[kept_words[0]]["w"])
    kept_set_ = set(kept_words)
    # vazamento: o ponto de corte leva o começo da palavra seguinte do bruto (ou o fim da anterior), que ficou de fora
    vaz_ = []
    for sg in segs:
        nx, pv = sg["i1"] + 1, sg["i0"] - 1
        if nx < len(pal) and nx not in kept_set_ and pal[nx]["t"] < sg["out"] - 0.02 and \
                SIL.voz_inicio(x, sr, max(pal[nx]["t"], (sg["junta_out"].get("voz") or 0.0) + 0.06, sg["out"] - 0.5), sg["out"], lim, acima=0.0) is not None:
            vaz_.append(f"fim do seg {sg['n'] if 'n' in sg else '?'} leva '{pal[nx]['w']}' ({pal[nx]['t']:.2f} < out {sg['out']:.2f})")
        if pv >= 0 and pv not in kept_set_ and pal[pv]["e"] > sg["in"] + 0.02 and \
                SIL.voz_fim(x, sr, sg["in"], min(pal[pv]["e"], (sg["junta_in"].get("voz") or 9e9) - 0.06, sg["in"] + 0.5), lim, acima=0.0) is not None:
            vaz_.append(f"início do seg {sg['n'] if 'n' in sg else '?'} leva '{pal[pv]['w']}' ({pal[pv]['e']:.2f} > in {sg['in']:.2f})")
    checks.append(check("V18b_vazamento", not vaz_, "HIGH", medido=vaz_[:6] or 0,
                        detalhe="o corte pega pedaço de palavra que ficou de fora: troque a tomada ou mantenha a palavra"))
    # palavra mantida que o Whisper pôs ≥ 50 % dentro de silêncio medido: o tempo dela é duvidoso (a voz está em outro lugar)
    fora_da_voz = []
    kept_set_ = set(kept_words)
    aberturas = {sg["i0"] for sg in segs}  # a 1ª palavra do segmento entra pela voz medida; o Whisper sempre a estica para trás
    for i in kept_words:
        if i in aberturas:
            continue
        d_ = max(0.02, pal[i]["e"] - pal[i]["t"])
        dentro = sum(max(0.0, min(pal[i]["e"], s_["e"]) - max(pal[i]["t"], s_["t"])) for s_ in sil if s_["e"] > pal[i]["t"] and s_["t"] < pal[i]["e"])
        if dentro / d_ >= 0.5 and d_ >= 0.12:
            fora_da_voz.append(f"'{pal[i]['w']}' #{i} {mmss(pal[i]['t'])}")
    checks.append(check("V20b_palavra_no_silencio", not fora_da_voz, "aviso", medido=fora_da_voz[:8] or 0,
                        detalhe="o Whisper pôs a palavra dentro de silêncio medido: confira com di digest --janela; pausa escondida ou palavra em outro tempo (escuta pendente)"))
    gancho = "gancho" in (motivo_de.get(kept_words[0]) or "").lower()
    checks.append(check("V22b_abre_em_conector", primeira not in CONECTORES or gancho, "HIGH", medido=pal[kept_words[0]]["w"],
                        detalhe=("abre em conector, declarado gancho no motivo" if gancho else
                                 "abre em conector: frase pela metade? Se é o gancho (\"Agora você…\"), diga \"gancho\" no motivo do primeiro item de manter")))
    def _dentro(p):  # o quanto da pausa sobra DENTRO do corte (a entrada pela voz sustentada pode ter tirado o silêncio)
        t0, t1 = p.get("_faixa", (0.0, 0.0))
        return max([min(t1, sg["out"]) - max(t0, sg["in"]) for sg in segs] + [0.0])
    pausas_grandes = [p for p in pausas_mantidas if p["funcao"] == "(não listada)" and _dentro(p) > R.pausa_max]
    listada_fora = [p for p in pausas_mantidas if p["funcao"] != "(não listada)" and _dentro(p) < 0.12]
    checks.append(check("V20c_pausa_listada_fora", not listada_fora, "MEDIUM",
                        medido=[f"depois de '{pal[p['apos_palavra']]['w']}' #{p['apos_palavra']}" for p in listada_fora] or 0,
                        detalhe="pausa em pausas_preservar que o ponto de corte já tirou: tire da lista (o papel tem que dizer o que o render diz)"))
    pausas_mantidas = [p for p in pausas_mantidas if p not in listada_fora]
    for p in pausas_mantidas:
        p.pop("_faixa", None)
    checks.append(check("V20_pausas_preservadas", not pausas_grandes, "HIGH",
                        medido=[f"{p['vao']:.2f} s após '{pal[p['apos_palavra']]['w']}' #{p['apos_palavra']} {mmss(pal[p['apos_palavra']]['e'])}" for p in pausas_grandes] or 0,
                        detalhe=f"{len(pausas_grandes)} pausa(s) > {R.pausa_max} s mantidas sem função listada (pausas_preservar ou pausas_colapsar_intra)"))
    # V20d: palavra mantida que, DENTRO do corte, dura mais de 1,2 s com voz em mais da metade.
    # É o jeito de o Whisper engolir um falso começo inteiro numa palavra só: nenhuma palavra
    # repete no transcript, então V22c/V29 não têm o que achar (armadilhas 60).
    import numpy as _np20
    esticadas = []
    n20 = max(1, int(0.05 * sr))
    for i in kept_words:
        for sg in segs:
            a0, b0 = max(pal[i]["t"], sg["in"]), min(pal[i]["e"], sg["out"])
            if b0 - a0 <= 1.2:
                continue
            w_ = _np20.asarray(x[int(a0 * sr):int(b0 * sr)], dtype=float)
            db = [20 * math.log10(math.sqrt(float(_np20.mean(w_[k:k + n20] ** 2))) + 1e-9)
                  for k in range(0, max(0, len(w_) - n20 + 1), n20)]
            voz = sum(1 for d in db if d > lim) / max(1, len(db))
            if voz > 0.5:
                esticadas.append(f"'{pal[i]['w']}' #{i} {mmss(a0)}–{mmss(b0)} ({b0 - a0:.2f} s, voz {100 * voz:.0f} %)")
    checks.append(check("V20d_palavra_esticada_com_fala", not esticadas, "BLOCKER", medido=esticadas[:6] or 0,
                        esperado="nenhuma palavra mantida com > 1,2 s e voz em mais da metade",
                        detalhe="o transcript deu a uma palavra só um trecho longo com voz: falso começo ou retake engolido. "
                                "Retranscreva o trecho isolado e corte com cortar_trecho; nunca declare como pausa"))
    dur_mantida = sum(pal[i]["e"] - pal[i]["t"] for i in kept_words)
    pausas_rem = sum(max(0.0, (pal[b]["t"] - pal[a]["e"]) - (R.res_min + R.res_max) / 2) for (a, b, t) in cortes if t == "B")
    fill_rem = sum(pal[i]["e"] - pal[i]["t"] for i in tirados)
    pct = 100 * (pausas_rem + fill_rem) / max(1.0, dur_mantida)
    checks.append(check("V21_pausas_fillers", pct <= 15, "HIGH", medido=f"{pct:.1f} %", esperado="≤ 15 % (motivo no DIARIO acima)"))
    amb = [i for i in kept_words if pal[i].get("sugerido") or (pal[i].get("ambigua") and (pal[i]["w"][:1].isupper() or re.search(r"\d", pal[i]["w"])))]
    perto = [i for i in amb for s in segs if abs(pal[i]["t"] - s["in"]) < 0.1 or abs(pal[i]["e"] - s["out"]) < 0.1]
    checks.append(check("V22_ambigua_na_borda", not perto, "aviso", medido=[pal[i]["w"] for i in perto] or 0))
    contiguo = all(segs[k]["timeline_in_f"] == segs[k - 1]["timeline_out_f"] for k in range(1, len(segs)))
    checks.append(check("V23_frames", contiguo and segs[-1]["timeline_out_f"] == sum(s["frames"] for s in segs), "BLOCKER",
                        medido=segs[-1]["timeline_out_f"], esperado="contíguo, soma = total"))
    checks.append(check("V14_cobertura", True, "BLOCKER", medido=f"padrão {dec.get('padrao', 'remover')} + {len(dec.get('manter', []))} exceções",
                        detalhe=f"{len(kept_words)} palavras mantidas de {len(pal)} do bruto"))

    edl = {"schema": "di-edl/1", "fonte": fonte["path"], "fps": fonte["fps"], "id": vid, "titulo": dec.get("titulo"),
           "canvas_V": [1080, 1920], "crop_x": None, "criado": agora(),
           "segmentos": [{"n": s["n"], "source_in": round(s["in"], 3), "source_out": round(s["out"], 3),
                          "timeline_in_f": s["timeline_in_f"], "timeline_out_f": s["timeline_out_f"], "frames": s["frames"],
                          "timeline_in": round(s["timeline_in_f"] / fps, 3), "timeline_out": round(s["timeline_out_f"] / fps, 3),
                          "palavra_in": s["i0"], "palavra_out": s["i1"],
                          "texto": " ".join(pal[i]["w"] for i in range(s["i0"], s["i1"] + 1) if i in motivo_de),
                          "escala": s["escala"], "ganho_db": s["ganho_db"], **({"ganho_ajuste_junta": s["ganho_ajuste_junta"]} if s.get("ganho_ajuste_junta") else {}), "crop_x": None,
                          "junta_in": s["junta_in"], "junta_out": s["junta_out"],
                          "motivo": " ‖ ".join(dict.fromkeys(motivo_de[i] for i in range(s["i0"], s["i1"] + 1)
                                                             if i in motivo_de))} for s in segs],
           "palavras_mantidas": kept_words, "fillers_tirados": tirados,
           "pausas_preservadas": [p for p in pausas_mantidas if p["funcao"] != "(não listada)"],
           "removido": {"pct_do_bruto": round(100 * (1 - (segs[-1]["timeline_out_f"] / fps) / fonte["duracao"]), 1),
                        "pausas_s": round(pausas_rem, 2), "fillers_s": round(fill_rem, 2)},
           "duracao": round(segs[-1]["timeline_out_f"] / fps, 3), "frames_total": segs[-1]["timeline_out_f"]}
    from comum import arquivo_verificador
    arqv = arquivo_verificador(projeto, "F2")
    velho = ler_json(arqv)
    if velho:
        velho["checks"] = [c for c in velho["checks"] if c.get("video") != vid]
        gravar_json(arqv, velho)
    d = registrar_checks(projeto, "F2", [dict(c, video=vid) for c in checks], alvo="02_decupagem/<id>/edl.json (um por vídeo; cada check tem `video`)")
    bl = [c for c in checks if not c["ok"] and c["severidade"] == "BLOCKER"]
    if bl:
        gravar_json(dd / "edl.rejeitado.json", edl)
        raise DIError("EDL não sai (BLOCKER):\n  - " + "\n  - ".join(f"{c['id']}: {c.get('detalhe') or c['medido']}" for c in bl))
    gravar_json(dd / "edl.json", edl)
    # roteiro montado
    rot = []
    cor = carregar(projeto).get("correcoes") or []      # a grafia que o usuário confirmou vale também no roteiro
    for s in edl["segmentos"]:
        # com o índice de cada palavra: sem "i", a lista de intocáveis nunca casava e o roteiro trocava
        # também o «Markdown» que é o formato (armadilhas 53)
        _mant = set(edl.get("palavras_mantidas") or [])
        ws = [{"w": pal[i]["w"], "i": i, "seg": s["n"]} for i in range(s["palavra_in"], s["palavra_out"] + 1)
              if not _mant or i in _mant] or [{"w": w, "seg": s["n"]} for w in s["texto"].split()]
        # palavra com decisão escrita de NÃO trocar (ambígua confirmada apontando para ela mesma, ex.:
        # «Markdown» o formato ao lado de MarkItDown a ferramenta) fica como está — armadilhas 53
        from comum import norm_palavra as _nrm
        _intoc = {int(a_["palavra"]) for a_ in dec.get("ambiguas", [])
                  if a_.get("status") == "confirmada" and isinstance(a_.get("palavra"), int)
                  and _nrm(a_.get("provavel") or "") == _nrm(a_.get("ouvido") or "")}
        rot.append(f"[{s['n']}] " + " ".join(w["w"] for w in aplicar_correcoes(ws, cor, _intoc)))
    gravar_texto(dd / "roteiro_montado.txt", "\n".join(rot) + "\n")
    # pendências (no máximo 10 vão ao portão)
    pend = []
    vistos = set()
    for i in amb:
        k = (pal[i]["w"], pal[i].get("sugerido"))
        if k in vistos:
            continue
        vistos.add(k)
        pend.append(f"- '{pal[i]['w']}' aos {mmss(pal[i]['t'])} (bruto)" + (f" → '{pal[i]['sugerido']}'?" if pal[i].get("sugerido") else " (confiança baixa)"))
    for a_ in dec.get("ambiguas", []):
        pend.append(f"- '{a_.get('ouvido')}' (palavra {a_.get('palavra')}) → '{a_.get('provavel')}'? — marcada pelo Editor")
    gravar_texto(dd / "pendencias.md", f"# Palavras a confirmar — {vid}\n\nNo portão F3 vão no máximo 10; sem resposta, a legenda cala a frase inteira.\n\n"
                 + ("\n".join(pend) if pend else "nenhuma") + "\n")
    sem_motivo = escrever_marcas(projeto, vid, edl, dec, rt, pal, cortes, tirados)
    registrar_checks(projeto, "F2", [check("V14b_conteudo_sem_motivo", not sem_motivo, "HIGH", medido=sem_motivo or 0, video=vid,
                                           detalhe="trecho de conteúdo (não é retake, bastidor nem alucinação) tirado sem motivo em remover[]")])
    rj = ler_json(projeto / "03_corte" / vid / "render.json")
    tem_render = any((projeto / "03_corte" / vid / f"corte_v01_{x}.mp4").exists() for x in ("V", "H"))
    if tem_render and (not rj or rj.get("edl_assinatura") != edl_assinatura(edl)):
        m_ = carregar(projeto)
        for a_ in m_.get("artefatos", []):
            if a_["caminho"].startswith(f"03_corte/{vid}/") and a_.get("estado") == "valido":
                a_["estado"] = "substituido"
        salvar(projeto, m_)
        print(f"  ⚠ o render de 03_corte/{vid}/ é de um EDL anterior: marcado substituído; rode di render {vid} de novo")
    m = carregar(projeto)
    if vid not in m.setdefault("videos", []):
        m["videos"].append(vid)
        m["videos"].sort()
    arts = m.setdefault("artefatos", [])
    rel = f"02_decupagem/{vid}/edl.json"
    for a_ in arts:
        if a_["caminho"] == rel:
            a_["estado"] = "substituido"
    arts.append({"caminho": rel, "fase": "F2", "estado": "valido", "data": agora()})
    salvar(projeto, m)
    return edl


def nivelar_juntas(segs: list, x, sr, limiar_db: float, alvo: float = 2.5, extra_max: float = 1.5) -> None:
    """Depois do ganho pela mediana: a voz 1,2 s antes e 1,2 s depois de cada junta (as mesmas janelas da V31b)
    não pode saltar mais que `alvo` dB. Ajuste pequeno e limitado (±extra_max por segmento), repartido entre os
    dois lados; o que sobrar vai para a V31b no render, para o usuário ouvir."""
    import numpy as _np
    env, hop = SIL.env_cache(x, sr)
    lim_voz = max(limiar_db + 8, -35)

    def voz(t0, t1, g):  # quadros até 15 dB abaixo do mais alto da janela: a escolha não muda com o ganho (igual à V31b)
        fr = env[max(0, int(t0 / hop)):max(0, int(t1 / hop))]
        fr = fr[(fr > lim_voz) & (fr >= (fr.max() if len(fr) else 0) - 15.0)]
        return float(_np.median(fr)) + g if len(fr) else None
    base = [s_["ganho_db"] for s_ in segs]
    for _ in range(4):
        mexeu = False
        for k in range(1, len(segs)):
            a, b = segs[k - 1], segs[k]
            va = voz(max(a["in"], a["out"] - 1.2), a["out"], a["ganho_db"])
            vb = voz(b["in"], min(b["out"], b["in"] + 1.2), b["ganho_db"])
            if va is None or vb is None:
                continue
            d = va - vb
            if abs(d) <= alvo:
                continue
            falta = (abs(d) - alvo) * (1 if d > 0 else -1)  # d > 0: antes mais alto → baixa a, sobe b
            for s_, sinal in ((a, -0.5), (b, 0.5)):
                i_ = segs.index(s_)
                novo = s_["ganho_db"] + sinal * falta
                novo = max(base[i_] - extra_max, min(base[i_] + extra_max, novo))
                novo = max(-6.0, min(6.0, round(novo, 1)))
                if novo != s_["ganho_db"]:
                    s_["ganho_db"], mexeu = novo, True
        if not mexeu:
            break
    for s_, g0 in zip(segs, base):
        if s_["ganho_db"] != g0:
            s_["ganho_ajuste_junta"] = round(s_["ganho_db"] - g0, 1)


def _faixas_itens(itens: list[dict], fr: dict, grupos: dict) -> list[tuple[int, int, dict]]:
    out = []
    for m_ in itens:
        if "de_palavra" in m_:
            out.append((int(m_["de_palavra"]), int(m_["ate_palavra"]), m_))
        elif "grupo" in m_ and m_.get("grupo") in grupos:
            t_ = next((t for t in grupos[m_["grupo"]]["tomadas"] if t["tomada"] == int(m_.get("tomada", 0))), None)
            if t_:
                out.append((fr[t_["frase"]]["i0"], fr[t_["frase"]]["i1"], m_))
        elif "frase" in m_ and int(m_["frase"]) in fr:
            f_ = fr[int(m_["frase"])]
            out.append((f_["i0"], f_["i1"], m_))
    return out


def _duvidas(pal: list[dict], idx: list[int], dec: dict, correcoes: list[dict] | None = None) -> list[str]:
    amb = {int(a_["palavra"]): a_ for a_ in dec.get("ambiguas", []) if isinstance(a_.get("palavra"), int)}
    # palavra com decisão escrita de NÃO trocar (ambígua confirmada apontando para ela mesma): a lista
    # não pode dizer que o usuário confirmou a troca ali — casa pelo ÍNDICE, como o roteiro (armadilhas 53)
    intoc = {i for i, a_ in amb.items() if a_.get("status") == "confirmada"
             and norm_palavra(a_.get("provavel") or "") == norm_palavra(a_.get("ouvido") or "")}
    por_forma = {norm_palavra(w["w"]): w["sugerido"] for w in pal if w.get("sugerido")}
    out, cobertas = [], set()
    seq = [norm_palavra(pal[i]["w"]) for i in idx]
    for c in sorted(correcoes or [], key=lambda c: -len(c["ouvido"].split())):   # o que o usuário confirmou no portão
        ouv = [norm_palavra(x) for x in c["ouvido"].split()]
        if set(ouv) <= cobertas:
            continue                   # "Cloud" já dito dentro de "Cloud Code"
        if any(seq[k:k + len(ouv)] == ouv and not any(i_ in intoc for i_ in idx[k:k + len(ouv)])
               for k in range(len(seq) - len(ouv) + 1)):
            out.append(f"'{c['ouvido']}' → '{c['certo']}' (confirmado pelo usuário)")
            cobertas |= set(ouv)
    for k, i in enumerate(idx):
        w = pal[i]
        if norm_palavra(w["w"]) in cobertas:
            continue
        if i in intoc:
            out.append(f"'{w['w']}' fica como está (decisão escrita: não é a palavra corrigida em outro ponto)")
        elif i in amb and amb[i].get("status") == "confirmada":
            out.append(f"'{w['w']}' → '{amb[i].get('provavel')}' (confirmada pelo usuário)")
        elif i in amb:
            out.append(f"'{w['w']}' → '{amb[i].get('provavel')}'? ({amb[i].get('status')}; escuta pendente)")
        elif w.get("sugerido") or norm_palavra(w["w"]) in por_forma:
            out.append(f"'{w['w']}' → '{w.get('sugerido') or por_forma[norm_palavra(w['w'])]}' (glossário)")
        elif k + 1 < len(idx) and re.search(r"\d$", w["w"]) and re.match(r"^[.,]\d", pal[idx[k + 1]]["w"]):
            out.append(f"'{w['w']} {pal[idx[k + 1]]['w']}' → '{w['w']}{pal[idx[k + 1]]['w']}' (número partido; exportar junta)")
    return list(dict.fromkeys(out))


def escrever_marcas(projeto: Path, vid: str, edl: dict, dec: dict, rt: dict, pal: list[dict], cortes, tirados) -> list[str]:
    """Gera MARCAS.md. Devolve os trechos de conteúdo removidos sem motivo (V14b)."""
    fr = {f["id"]: f for f in rt["frases"]}
    grupos = {g["id"]: g for g in rt["grupos"]}
    mant = set(edl["palavras_mantidas"])
    itens = _faixas_itens(dec.get("manter", []), fr, grupos)
    rem_itens = _faixas_itens(dec.get("remover", []), fr, grupos)
    L = [f"# MARCAS — {vid} · {edl.get('titulo') or ''}", "",
         f"{len(edl['segmentos'])} segmentos · {len(edl['segmentos']) - 1} emendas · {edl['duracao']:.2f} s ({edl['frames_total']} frames) · "
         f"gerado por edl.py (nenhum número digitado pelo modelo)", "", "## Fica", "",
         "| seg | frase | tomadas no bruto | escolhida | motivo | in → out (fonte) | folga à voz in/out · resíduo | emenda |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    usados, duv = set(), []
    correcoes = carregar(projeto).get("correcoes") or []
    for s in edl["segmentos"]:
        f_ids = sorted({f["id"] for f in rt["frases"] if f["i0"] <= s["palavra_out"] and f["i1"] >= s["palavra_in"]})
        g = next((fr[i].get("grupo") for i in f_ids if fr[i].get("grupo") and any(k in mant for k in range(fr[i]["i0"], fr[i]["i1"] + 1))), None)
        if g:
            usados.add(g)
        toms = " · ".join(f"t{t['tomada']} {mmss(t['t'])} {t['tipo']}" for t in grupos[g]["tomadas"]) if g else ""
        conc = [c for (i0, i1, m_) in itens if i0 <= s["palavra_out"] and i1 >= s["palavra_in"] for c in m_.get("concorrentes", [])]
        if conc:
            toms = (toms + " · " if toms else "") + " · ".join(f"F{int(c):03d} {mmss(fr[int(c)]['t'])} outra versão" for c in conc if int(c) in fr)
        esc = next((f"{g} t{fr[i]['tomada']}" for i in f_ids if g and fr[i].get("grupo") == g), "única" if not conc else "escolhida")
        # Escolha por palavra: o papel mostra a escolha na MESMA unidade em que ela foi feita. A coluna de tomadas
        # vem das frases do retakes.json, e quando as tentativas atravessam a fronteira de frase (armadilha da
        # tomada que atravessa a frase) o tempo da frase não é o começo da tomada — imprimi-lo aqui manda o corte para dentro da palavra
        # anterior. Ver armadilhas.md, Corte.
        por_pal = [m_ for (i0, i1, m_) in itens
                   if i0 <= s["palavra_out"] and i1 >= s["palavra_in"] and m_.get("de_palavra") is not None]
        if por_pal:
            toms = " · ".join(f"palavras {int(m_['de_palavra'])}–{int(m_['ate_palavra'])} "
                              f"{mmss(pal[int(m_['de_palavra'])]['t'])}→{mmss(pal[int(m_['ate_palavra'])]['e'])}"
                              for m_ in por_pal)
            esc = "por palavra"
        ji, jo = s["junta_in"], s["junta_out"]
        if ji["tipo"] == "A":
            em = "A salto"
        elif ji["tipo"] == "B":
            vao = pal[s["palavra_in"]]["t"] - pal[s["palavra_in"] - 1]["e"]
            em = f"B pausa de {vao:.2f} s encurtada"
        else:
            em = "início"
        if ji.get("relaxado") or jo.get("relaxado"):
            lados = "/".join(x for x, j in (("entrada", ji), ("saída", jo)) if j.get("relaxado"))
            em += f" · {lados} fora de silêncio medido: crossfade 20 ms"
        em += f" · {ji.get('cobertura') or ''} {s['escala']:.3f}".rstrip()
        L.append(f"| {s['n']} | {s['texto'][:70]}{'…' if len(s['texto']) > 70 else ''} | {toms or '—'} | {esc} | {s['motivo']} | "
                 f"{mmss(s['source_in'])} → {mmss(s['source_out'])} | {ji.get('folga_voz', '')}/{jo.get('folga_voz', '')}"
                 f"{' · ' + str(ji.get('residuo')) if ji.get('residuo') is not None else ''}{resp_txt(ji)} | {em} |")
        d_ = _duvidas(pal, [i for i in range(s["palavra_in"], s["palavra_out"] + 1) if i in mant], dec, correcoes)
        if d_:
            duv.append(f"- seg {s['n']}: " + " · ".join(d_))
    L += ["", "## Palavras em dúvida e confirmadas (a retranscrição da F3 confere; legenda cala só o que o usuário não confirmou)",
          ""] + (duv or ["- nenhuma"])
    L += ["", "## Sai", "", "| trecho (fonte) | tipo | motivo | texto |", "| --- | --- | --- | --- |"]
    sem_motivo = []
    for (a, b, tipo) in cortes:
        if tipo != "A":
            continue
        fora = [i for i in range(a + 1, b) if i not in mant]
        if not fora:
            continue
        fs = sorted({f["id"] for f in rt["frases"] if f["i0"] <= fora[-1] and f["i1"] >= fora[0]})
        if all(fr[i].get("alucinacao_suspeita") for i in fs):
            marca, mot = "alucinação", "silêncio que o Whisper encheu"
        elif any(fr[i].get("bastidor") for i in fs) and not any(not fr[i].get("bastidor") and not fr[i].get("grupo") and len(fr[i]["norm"]) >= 4 for i in fs):
            marca, mot = "bastidor", "comentário fora do vídeo"
        elif all(fr[i].get("grupo") or fr[i].get("bastidor") or len(fr[i]["norm"]) < 4 for i in fs):
            vale = sorted({fr[i]["grupo"] for i in fs if fr[i].get("grupo")})
            marca, mot = "retake", "outra tomada de " + ", ".join(vale) if vale else "falso começo"
        else:
            marca, mot = "conteúdo", ""
        dm = [m_["motivo"] for (i0, i1, m_) in rem_itens if i0 <= fora[-1] and i1 >= fora[0]]
        if dm:
            mot = "; ".join(dict.fromkeys(dm))
        dur = pal[fora[-1]]["e"] - pal[fora[0]]["t"]
        if marca == "conteúdo" and not dm and dur >= 1.0:
            sem_motivo.append(f"{mmss(pal[fora[0]]['t'])}–{mmss(pal[fora[-1]]['e'])}")
            mot = "(sem motivo: escreva em remover[])"
        txt = " ".join(pal[i]["w"] for i in fora)
        s_ant = next((sg for sg in edl["segmentos"] if sg["palavra_out"] == a), None)
        s_seg = next((sg for sg in edl["segmentos"] if sg["palavra_in"] == b), None)
        t0 = s_ant["source_out"] if s_ant else pal[fora[0]]["t"]
        t1 = s_seg["source_in"] if s_seg and s_seg["source_in"] > t0 else pal[fora[-1]]["e"]
        L.append(f"| {mmss(t0)}–{mmss(t1)} | {marca} | {mot} | {txt[:100]}{'…' if len(txt) > 100 else ''} |")
    for ct in dec.get("cortar_trecho", []):
        # o falso começo que o transcript engoliu não tem palavra própria: a linha sai dos tempos medidos
        mot_ = str(ct["motivo"])
        L.append(f"| {mmss(float(ct['abandona_de']))}–{mmss(float(ct['abandona_ate']))} | falso começo | "
                 f"{mot_[:160]}{'…' if len(mot_) > 160 else ''} | (engolido pelo transcript dentro de '{pal[int(ct['apos_palavra']) + 3]['w'] if int(ct['apos_palavra']) + 3 < len(pal) else '?'}'; ver retranscrição isolada) |")
    for i in tirados:
        L.append(f"| {mmss(pal[i]['t'])} | hesitação | filler isolado | {pal[i]['w']} |")
    L += ["", "## Pausas preservadas (dentro do corte)", ""]
    pp = [f"- depois de '{pal[p['apos_palavra']]['w']}' ({mmss(pal[p['apos_palavra']]['e'])}) · {p['vao']} s · {p['funcao']}" for p in edl["pausas_preservadas"]]
    pp += [f"- respiro na entrada do seg {sg['n']} ({mmss(sg['source_in'])}) · {sg['junta_in']['respiro']} s · inspiração antes da fala, fica inteira"
           for sg in edl["segmentos"] if (sg["junta_in"].get("respiro") or 0) >= 0.35]
    pp += [f"- respiro na saída do seg {sg['n']} ({mmss(sg['source_out'])}) · {sg['junta_out']['respiro']} s · expiração depois da fala, fica inteira"
           for sg in edl["segmentos"] if (sg["junta_out"].get("respiro") or 0) >= 0.35]
    L += pp or ["- nenhuma listada"]
    emp = [f"{g['id']} (t{','.join(str(x) for x in g['empate_com'])} × t{g['sugerida']})" for g in rt["grupos"] if g.get("empate_com") and g["id"] in usados]
    L += ["", "## Rodapé", "", f"- removido do bruto: {edl['removido']['pct_do_bruto']} % (retakes e bastidor são o normal num solo)",
          f"- pausas colapsadas: {edl['removido']['pausas_s']} s · hesitações: {edl['removido']['fillers_s']} s",
          f"- empates de tomada neste vídeo: {', '.join(emp) if emp else 'nenhum'} (empate = duas tomadas completas quase idênticas: ≥ 95 % iguais e a mesma extensão ±1 palavra; tomada completa mais longa ou mais curta não é empate, é escolha com motivo)",
          f"- sem tomada limpa: {', '.join(g for g in sorted(usados) if grupos[g]['sem_tomada_limpa']) or 'nada'}"]
    gravar_texto(Path(projeto) / "02_decupagem" / vid / "MARCAS.md", "\n".join(L) + "\n")
    return sem_motivo


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di edl")
    ap.add_argument("video", help="id do vídeo, ex.: 01-claude-code")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    e = montar(achar_projeto(a.projeto), a.video)
    print(f"✓ {a.video}: {len(e['segmentos'])} segmentos, {e['duracao']:.2f} s ({e['frames_total']} frames) → edl.json, MARCAS.md, roteiro_montado.txt")
    return 0
