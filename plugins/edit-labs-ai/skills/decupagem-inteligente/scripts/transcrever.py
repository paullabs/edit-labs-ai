"""Transcrição palavra a palavra (large-v3-turbo). Insumo sem substituto.

Parâmetros por motor (§05 5.3):
  mlx-whisper   word_timestamps, condition_on_previous_text=False, temperature=0.0 (sem beam, sem VAD)
  faster-whisper word_timestamps, beam_size=5, vad_filter=False, condition_on_previous_text=False, temperature=0.0
vad_filter=False: o VAD desloca o início da primeira palavra.
condition_on_previous_text=False: evita frase inventada depois de um retake.

  di transcrever [--engine auto|mlx|faster] [--projeto P]
"""
from __future__ import annotations

import argparse
import time
import types
import wave
from pathlib import Path

from comum import DIError, achar_projeto, agora, check, gravar_json, ler_json, progresso, registrar_checks, sha256_arquivo

MLX_REPO = "mlx-community/whisper-large-v3-turbo"
FASTER_REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
P_AMBIGUA = 0.6
VERSAO = 5  # muda quando a forma de transcrever muda (invalida o cache)


def engine_disponivel(pedido: str = "auto") -> str:
    if pedido in ("auto", "mlx"):
        try:
            import mlx_whisper  # noqa: F401
            return "mlx"
        except Exception:
            if pedido == "mlx":
                raise DIError("mlx-whisper não instalado (opcional: requirements-mlx.txt da skill no venv-corte)")
    import faster_whisper  # noqa: F401
    return "faster"


def duracao_wav(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def prompt_de(glossario: list[str]) -> str | None:
    return ("Glossário: " + ", ".join(glossario) + ".") if glossario else None


def transcrever_audio(wav: Path | str, glossario: list[str] | None = None, engine: str = "auto",
                      ao_progredir=None) -> dict:
    """Devolve {engine, modelo, parametros, segmentos:[…], palavras:[…]} no relógio do arquivo."""
    engine = engine_disponivel(engine)
    ip = prompt_de(glossario or [])
    t_ini = time.time()
    total = duracao_wav(Path(wav))
    segs_out, pals = [], []
    if engine == "mlx":
        import tqdm as _tq
        import mlx_whisper
        import mlx_whisper.transcribe as T

        class _P(_tq.tqdm):
            def update(self, n=1):
                r = super().update(n)
                if ao_progredir and self.total:
                    frac = self.n / self.total
                    el = time.time() - t_ini
                    ao_progredir(frac, el / frac - el if frac > 0.02 else None)
                return r
        T.tqdm = types.SimpleNamespace(tqdm=_P)
        if ip:
            # Com condition_on_previous_text=False o mlx-whisper zera o prompt depois da 1ª janela
            # (prompt_reset_since). Aqui o glossário volta a cada janela, como carry_initial_prompt.
            from mlx_whisper.decoding import DecodingOptions as _DO
            from mlx_whisper.tokenizer import get_tokenizer
            _tok = get_tokenizer(multilingual=True, num_languages=100, language="pt", task="transcribe")
            _gl = _tok.encode(" " + ip.strip())[:100]

            def _opcoes(**kw):
                pr = kw.get("prompt") or []
                if isinstance(pr, list):
                    kw["prompt"] = _gl + [t for t in pr][-(223 - len(_gl)):]
                return _DO(**kw)
            T.DecodingOptions = _opcoes
        params = dict(word_timestamps=True, condition_on_previous_text=False, temperature=0.0, language="pt")
        r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=MLX_REPO, initial_prompt=ip, verbose=False, **params)
        for s in r["segments"]:
            segs_out.append({"t": float(s["start"]), "e": float(s["end"]), "texto": s["text"].strip(),
                             "no_speech_prob": float(s.get("no_speech_prob", 0)),
                             "avg_logprob": float(s.get("avg_logprob", 0)),
                             "compression_ratio": float(s.get("compression_ratio", 0)),
                             "words": [(w["word"], w["start"], w["end"], w.get("probability")) for w in s.get("words", [])]})
        modelo = MLX_REPO
    else:
        from faster_whisper import WhisperModel
        params = dict(word_timestamps=True, beam_size=5, vad_filter=False, condition_on_previous_text=False,
                      temperature=0.0, language="pt")
        mdl = WhisperModel(FASTER_REPO, device="cpu", compute_type="int8")
        segs, _info = mdl.transcribe(str(wav), initial_prompt=ip, hotwords=ip, **params)
        for s in segs:
            segs_out.append({"t": float(s.start), "e": float(s.end), "texto": s.text.strip(),
                             "no_speech_prob": float(s.no_speech_prob), "avg_logprob": float(s.avg_logprob),
                             "compression_ratio": float(s.compression_ratio),
                             "words": [(w.word, w.start, w.end, w.probability) for w in (s.words or [])]})
            if ao_progredir and total:
                frac = min(1.0, s.end / total)
                el = time.time() - t_ini
                ao_progredir(frac, el / frac - el if frac > 0.02 else None)
        modelo = FASTER_REPO
    segmentos = []
    for k, s in enumerate(segs_out):
        segmentos.append({"id": k, "t": round(s["t"], 3), "e": round(s["e"], 3), "texto": s["texto"], "spk": "A",
                          "no_speech_prob": round(s["no_speech_prob"], 4), "avg_logprob": round(s["avg_logprob"], 4),
                          "compression_ratio": round(s["compression_ratio"], 3)})
        for (w, t, e, p) in s["words"]:
            w = (w or "").strip()
            if not w:
                continue
            pals.append({"i": len(pals), "w": w, "t": round(float(t), 3), "e": round(float(e), 3),
                         "p": None if p is None else round(float(p), 3), "seg": k, "spk": "A",
                         "ambigua": p is not None and float(p) < P_AMBIGUA})
    params = {**params, "glossario_em_toda_janela": bool(ip)}
    return {"engine": engine, "modelo": modelo, "parametros": {k: v for k, v in params.items()},
            "segmentos": segmentos, "palavras": pals, "segundos_de_maquina": round(time.time() - t_ini, 1)}


def marcar_glossario(pals: list[dict], glossario: list[str]) -> list[dict]:
    """Janela de n palavras parecida (≥ 0,75 em letras) mas diferente de um termo do glossário
    → `sugerido` + `ambigua`. Ex.: "Cloud Code" ≈ "Claude Code". Nada é trocado sem o usuário."""
    from difflib import SequenceMatcher
    from comum import norm_palavra
    pares = []
    G = {norm_palavra(x) for t in glossario for x in t.split()}
    for termo in glossario:
        tw = termo.split()
        alvo = "".join(norm_palavra(x) for x in tw)
        n = len(tw)
        for i in range(len(pals) - n + 1):
            jan = pals[i:i + n]
            txt = "".join(norm_palavra(x["w"]) for x in jan)
            if not txt or txt == alvo or txt[0] != alvo[0]:
                continue
            if n == 1 and (txt in G or len(txt) < 4 or not (jan[0]["w"][:1].isupper() or (jan[0].get("p") or 1) < 0.7)):
                continue  # "Code" é palavra de "Claude Code", não "Codex"; verbo comum ("falei") não vira "Fable"
            if SequenceMatcher(None, txt, alvo).ratio() >= (0.8 if n == 1 else 0.75):
                for x, certo in zip(jan, tw):
                    if norm_palavra(x["w"]) != norm_palavra(certo):
                        x["sugerido"] = certo
                        x["ambigua"] = True
                        x["motivo"] = f"parecido com '{termo}' do glossário"
                pares.append((" ".join(x["w"] for x in jan), termo))
    return pares


def esticadas(pals: list[dict]) -> list[int]:
    """Palavra com duração impossível: o Whisper engoliu uma repetição ou uma pausa dentro dela."""
    from comum import norm_palavra
    out = []
    for i, w in enumerate(pals):
        d = w["e"] - w["t"]
        if (d > 0.8 and len(norm_palavra(w["w"])) <= 8) or d > 1.5:
            out.append(i)
    return out


def _mid(w):
    return (w["t"] + w["e"]) / 2


def costurar(velhas: list[dict], novas: list[dict]) -> tuple[list[dict], dict]:
    """Alinha palavra a palavra (difflib). Regras:
    - palavra que as duas transcrições têm: fica o texto antigo, com o tempo novo;
    - palavra que só a retranscrição tem (repetição engolida): entra só se couber no vão de tempo;
    - palavra que só a antiga tem: NUNCA sai; se o tempo dela ficou incerto, é espremida no vão."""
    from difflib import SequenceMatcher
    from comum import norm_palavra
    vn = [norm_palavra(w["w"]) for w in velhas]
    nn = [norm_palavra(w["w"]) for w in novas]
    sm = SequenceMatcher(None, vn, nn, autojunk=False)
    base, extras = [], []
    info = {"iguais": 0, "inseridas": [], "espremidas": [], "recusadas": []}
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
            for d in range(i2 - i1):
                base.append(dict(velhas[i1 + d], t=novas[j1 + d]["t"], e=novas[j1 + d]["e"], realinhado=True))
                info["iguais"] += 1
        else:
            for w in velhas[i1:i2]:
                base.append(dict(w, _sem_par=True))
            extras += [dict(w, inserida=True, realinhado=True) for w in novas[j1:j2]]
    # tempos das palavras sem par: espreme no vão entre vizinhas com tempo confiável
    for k, w in enumerate(base):
        if not w.get("_sem_par"):
            continue
        ant = next((base[j]["e"] for j in range(k - 1, -1, -1) if not base[j].get("_sem_par")), w["t"])
        dep = next((base[j]["t"] for j in range(k + 1, len(base)) if not base[j].get("_sem_par")), w["e"])
        if not (ant - 0.05 <= w["t"] and w["e"] <= dep + 0.05):
            w["t"], w["e"] = round(max(ant, min(w["t"], dep)), 3), round(max(ant, min(w["e"], dep)), 3)
            w["tempo_incerto"] = True
            info["espremidas"].append(w["w"])
        w.pop("_sem_par")
    # inseridas: só no vão, sem atropelar palavra existente
    for x in extras:
        k = next((j for j, w in enumerate(base) if w["t"] >= x["t"]), len(base))
        ant = base[k - 1]["e"] if k else -1e9
        dep = base[k]["t"] if k < len(base) else 1e9
        if x["t"] >= ant - 0.05 and x["e"] <= dep + 0.05:
            base.insert(k, x)
            info["inseridas"].append(x["w"])
        else:
            info["recusadas"].append(x["w"])
    return base, info


def _retranscrever_janela(wav: Path, a: float, b: float, gl: list[str], engine: str) -> list[dict]:
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "j.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(wav), str(tmp)], check=True)
        r = transcrever_audio(tmp, gl, engine)
    return [dict(w, t=round(w["t"] + a, 3), e=round(w["e"] + a, 3)) for w in r["palavras"]]


def _tentar(pals: list[dict], wav: Path, a: float, b: float, gl, engine, M: float = 0.8):
    from difflib import SequenceMatcher
    from comum import norm_palavra
    a = max(0.0, a)
    novas = [w for w in _retranscrever_janela(wav, a, b, gl, engine) if a + M <= _mid(w) <= b - M]
    idx = [k for k, w in enumerate(pals) if a + M <= _mid(w) <= b - M]
    if not novas or not idx:
        return None, 0.0
    velhas = pals[idx[0]:idx[-1] + 1]
    sm = SequenceMatcher(None, [norm_palavra(w["w"]) for w in velhas], [norm_palavra(w["w"]) for w in novas], autojunk=False)
    cobre = sum(bl.size for bl in sm.get_matching_blocks()) / max(1, len(velhas))
    if cobre < 0.7:
        return None, cobre
    res, info = costurar(velhas, novas)
    for w in res:
        w.setdefault("seg", velhas[0]["seg"])
        w.setdefault("spk", "A")
    return (idx[0], idx[-1], res, info, velhas), cobre


def realinhar(projeto: Path, janelas: list[tuple[float, float]] | None = None, engine: str = "auto",
              max_tentativas: int = 40) -> list[dict]:
    """Retranscreve janelas curtas em volta de cada palavra esticada e costura os tempos certos.

    Janela curta (≤ 8 s): a longa faz o Whisper parar cedo e inventar. Três posições por palavra
    ([t−1,5; e+3], [t−3; e+1,5], [t−2,5; e+2,5]); fica a primeira que cobre ≥ 70 % das palavras
    antigas. Depois de cada costura as esticadas são recalculadas. Só mexe no miolo (0,8 s das
    bordas intocados). Reindexa: roda em F1, antes de qualquer decisoes.json."""
    projeto = Path(projeto)
    arq = projeto / "01_transcript" / "palavras.json"
    doc = ler_json(arq)
    pals = doc["palavras"]
    if list((projeto / "02_decupagem").glob("*/decisoes.json")):
        raise DIError("já existe decisoes.json: realinhar mudaria os índices das palavras. Faça isto só em F1.")
    gl = glossario_do_projeto(projeto)
    wav = projeto / "00_fonte" / "_audio_16k.wav"
    feitos, tentadas = [], set()
    pedidas = list(janelas or [])
    for _ in range(max_tentativas):
        if pedidas:
            a, b = pedidas.pop()
            posicoes, alvo = [(a, b)], f"{a:.1f}-{b:.1f}"
        else:
            cand = [i for i in esticadas(pals) if round(pals[i]["t"], 1) not in tentadas]
            if not cand or janelas:
                break
            i = cand[-1]
            w = pals[i]
            tentadas.add(round(w["t"], 1))
            posicoes = [(w["t"] - 1.5, w["e"] + 3.0), (w["t"] - 3.0, w["e"] + 1.5), (w["t"] - 2.5, w["e"] + 2.5)]
            posicoes = [(x, min(y, x + 8.0)) for x, y in posicoes]
            alvo = f"'{w['w']}' {w['t']:.2f}–{w['e']:.2f}"
        melhor = 0.0
        for (x, y) in posicoes:
            r, cobre = _tentar(pals, wav, x, y, gl, engine)
            melhor = max(melhor, cobre)
            if r:
                k0, k1, res, info, velhas = r
                pals[k0:k1 + 1] = res
                feitos.append({"alvo": alvo, "janela": [round(max(0, x), 2), round(y, 2)], "aplicado": True, **info,
                               "antes": " ".join(v["w"] for v in velhas), "depois": " ".join(v["w"] for v in res)})
                break
        else:
            feitos.append({"alvo": alvo, "aplicado": False, "motivo": f"nenhuma janela cobriu 70 % (melhor {100 * melhor:.0f} %)"})
    for i, w in enumerate(pals):
        w["i"] = i
    doc["palavras"] = pals
    doc.setdefault("realinhamentos", []).extend(feitos)
    doc["esticadas_restantes"] = [f"{pals[i]['w']} {pals[i]['t']:.2f}" for i in esticadas(pals)]
    marcar_glossario(pals, gl)
    gravar_json(arq, doc, indent=None)
    return feitos


def glossario_do_projeto(projeto: Path) -> list[str]:
    p = projeto / "00_fonte" / "glossario.txt"
    return [x.strip() for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def transcrever_projeto(projeto: Path, engine: str = "auto") -> Path:
    projeto = Path(projeto)
    wav = projeto / "00_fonte" / "_audio_16k.wav"
    out = projeto / "01_transcript" / "palavras.json"
    gl = glossario_do_projeto(projeto)
    sha = sha256_arquivo(wav)
    antigo = ler_json(out)
    if antigo and antigo.get("audio_sha") == sha and antigo.get("glossario") == gl and antigo.get("versao") == VERSAO:
        # cache: mesmo áudio e glossário; só refaz a marcação (barata) com a regra atual
        for w in antigo["palavras"]:
            for k in ("sugerido", "motivo"):
                w.pop(k, None)
            w["ambigua"] = w.get("p") is not None and w["p"] < P_AMBIGUA
        antigo["sugestoes_glossario"] = sorted({f"{a} → {b}" for a, b in marcar_glossario(antigo["palavras"], gl)})
        gravar_json(out, antigo, indent=None)
        return out
    fonte = ler_json(projeto / "00_fonte" / "fonte.json") or {}
    progresso(projeto, "transcrevendo", 0.0)
    r = transcrever_audio(wav, gl, engine, ao_progredir=lambda f, eta: progresso(projeto, "transcrevendo", f, eta))
    pares = marcar_glossario(r["palavras"], gl)
    doc = {"schema": "di-palavras/1", "versao": VERSAO, "engine": r["engine"], "modelo": r["modelo"], "parametros": r["parametros"],
           "fps": fonte.get("fps"), "duracao": duracao_wav(wav), "relogio": "bruto", "glossario": gl,
           "audio_sha": sha, "criado": agora(), "segundos_de_maquina": r["segundos_de_maquina"],
           "sugestoes_glossario": sorted({f"{a} → {b}" for a, b in pares}),
           "palavras": r["palavras"], "segmentos": r["segmentos"]}
    gravar_json(out, doc, indent=None)
    n = len(r["palavras"])
    amb = sum(1 for w in r["palavras"] if w["ambigua"])
    pct = 100 * amb / max(1, n)
    registrar_checks(projeto, "F1", [
        check("V09_transcricao", n > 0, "BLOCKER", medido=n, esperado="≥ 1 palavra",
              detalhe=f"{r['engine']} · {r['segundos_de_maquina']} s de máquina"),
        check("V10_ambiguas", pct <= 5, "aviso", medido=f"{pct:.1f} %", esperado="≤ 5 % com p < 0,6",
              detalhe="acima de 5 %: áudio ruim, ofereça glossário maior"),
    ], alvo="01_transcript/palavras.json")
    return out


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di transcrever")
    ap.add_argument("--engine", default="auto", choices=["auto", "mlx", "faster"])
    ap.add_argument("--realinhar", nargs="?", const="auto", help="a-b em segundos do bruto, ou vazio = palavras esticadas")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    if a.realinhar:
        projeto = achar_projeto(a.projeto)
        jan = None if a.realinhar == "auto" else [tuple(float(v) for v in a.realinhar.split("-"))]
        feitos = realinhar(projeto, jan, a.engine)
        for f in feitos:
            if f["aplicado"]:
                print(f"✓ {f['alvo']} {f['janela']}: {f['iguais']} com tempo novo · inseridas {f['inseridas'] or '—'} · espremidas {f['espremidas'] or '—'} · recusadas {f['recusadas'] or '—'}")
            else:
                print(f"· {f['alvo']}: {f['motivo']}")
        print("refaça: di silencio --com-palavras && di retakes && di digest")
        return 0
    p = transcrever_projeto(achar_projeto(a.projeto), a.engine)
    print(f"✓ {p}")
    return 0
