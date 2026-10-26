"""Frases, tomadas repetidas, retake parcial, falso começo, bastidor, hesitação (§05 5.3).

SUGERE; não decide. A escolha é do Editor em decisoes.json, com motivo.
Só biblioteca padrão (difflib) + numpy já carregado pelo silencio.py.
"""
from __future__ import annotations

import argparse
import re
from difflib import SequenceMatcher
from pathlib import Path

from comum import (HESITACOES_ISOLADAS, achar_projeto, check, config, eh_hesitacao, gravar_json, ler_json, limpa,
                   norm_palavra, registrar_checks)

FINAL = re.compile(r"[.!?]+[\"”»')]*$")
RETICENCIA = re.compile(r"(\.\.\.|…)[\"”»')]*$")
GAP_FRASE = 0.5
SIM_RETAKE = 0.72
JANELA_FRASES, JANELA_S = 15, 90.0
PREP = {"o", "a", "os", "as", "um", "uma", "no", "na", "nos", "nas", "do", "da", "dos", "das", "de", "em", "pro", "pra",
        "para", "com", "por", "ao", "sobre", "e", "ou", "tipo"}
PROPRIOS = {"reels", "tiktok", "tik", "tok", "google", "youtube", "instagram", "pdf", "ia", "gpt", "chatgpt", "openai",
            "claude", "cloud", "fable", "notebook", "lm", "kimi", "glm", "gemini", "github", "codex", "cursor",
            "antigravity", "anthropic", "antropic", "dario", "k2", "marcola"}
FUNCAO = {"o", "a", "os", "as", "de", "do", "da", "dos", "das", "que", "e", "um", "uma", "em", "no", "na", "com",
          "pra", "para", "por", "se", "mas", "ou", "como", "eu", "voce", "ele", "ela", "isso", "esse", "essa", "quando"}
BASTIDOR = [r"\broteiros?\b", r"\bprolix", r"\bputa que pariu\b", r"\bcaralho\b", r"\bporra\b", r"\bta ligado\b",
            r"\bvou mudar (isso|aqui)\b", r"\bvamos mudar\b", r"\bdeixa eu ver\b", r"\bmandar uma mensagem\b", r"\bgravando\b", r"\bde novo\b", r"\bpera(i)?\b", r"\bcorta\b", r"\bmano\b",
            r"\bdepois a gente edita\b", r"\bvou fazer de novo\b", r"\bvou refazer\b", r"\berrei\b",
            r"\bnada a ver\b", r"\besquece\b", r"\bdeixa eu\b", r"\bcomecar de novo\b", r"\bta gravando\b",
            r"\bvamos la de novo\b", r"\bdo comeco\b", r"\bnao ficou bom\b", r"\bvou falar de novo\b"]
CAUDA = {"boa", "ok", "okay", "isso", "beleza", "foi", "essa ficou", "acho que foi", "pronto", "valeu", "show", "perfeito"}
AUTOCORRECAO = {"nao", "quer dizer", "digo", "ou melhor", "pera", "perai", "opa"}


def sim(a: list[str], b: list[str]) -> float:
    if not a or not b:
        return 0.0
    r = SequenceMatcher(None, a, b, autojunk=False).ratio()
    sa, sb = set(a), set(b)
    j = len(sa & sb) / len(sa | sb)
    curto, longo = sorted((len(a), len(b)))
    return max(r, j if curto / longo >= 0.5 else 0.0)


def sim_chars(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0.0


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def f(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def u(self, a, b):
        self.p[self.f(a)] = self.f(b)


def quebrar_frases(pal: list[dict], nomes: set[str] | None = None) -> list[list[int]]:
    """Fecha frase em pontuação final, reticência, vão > 0,5 s, ou maiúscula colada sem pontuação antes
    que não seja nome (vão ≥ 0,3 s, confiança < 0,3 ou palavra de duração zero: o Whisper colou duas falas)."""
    nomes = nomes or set()
    frases, cur = [], []
    for k, w in enumerate(pal):
        if cur:
            gap = w["t"] - pal[k - 1]["e"]
            ant = pal[k - 1]["w"]
            nw = norm_palavra(w["w"])
            maius = w["w"][:1].isupper() and nw not in nomes and nw not in PROPRIOS and not re.search(r"[.!?,;:…]$", ant)
            nome_misto = any(c.isupper() for c in w["w"][1:])  # TikTok, GitHub, GLM
            colada = maius and not nome_misto and (
                gap >= 0.3 or (w.get("p") or 1) < 0.3 or w["e"] - w["t"] < 0.03
                # o Whisper maiusculiza cada recomeço dentro de um trecho sem pontuação
                or (len(cur) >= 3 and norm_palavra(ant) not in PREP))
            if gap > GAP_FRASE or colada:
                frases.append(cur)
                cur = []
        cur.append(k)
        if FINAL.search(w["w"]) or RETICENCIA.search(w["w"]):
            frases.append(cur)
            cur = []
    if cur:
        frases.append(cur)
    return frases


def analisar(projeto: Path) -> dict:
    projeto = Path(projeto)
    doc = ler_json(projeto / "01_transcript" / "palavras.json")
    sil = ler_json(projeto / "01_transcript" / "silencios.json") or {}
    cfg = config(projeto)
    pal, segs = doc["palavras"], doc["segmentos"]
    rms = {r["i"]: r["db"] for r in sil.get("rms_palavras", [])}
    gl = {norm_palavra(g) for g in (doc.get("glossario") or [])}
    alucina = {s["id"] for s in segs if s["no_speech_prob"] > 0.6 or s["compression_ratio"] > 2.4 or s["avg_logprob"] < -1.0}

    nomes = {norm_palavra(x) for t in (doc.get("glossario") or []) for x in t.split()}
    frases = []
    blocos_frases = quebrar_frases(pal, nomes)
    for n, ids in enumerate(blocos_frases, 1):
        ws = [pal[k]["w"] for k in ids]
        pares = [(norm_palavra(pal[k]["w"]), k) for k in ids if norm_palavra(pal[k]["w"])]
        norm_full = [x for x, _ in pares]
        hes = {k for k in ids if eh_hesitacao(pal[k]["w"])}
        norm = [x for x, k in pares if k not in hes]
        idx_norm = [k for x, k in pares if k not in hes]
        t, e = pal[ids[0]]["t"], pal[ids[-1]]["e"]
        texto_n = " ".join(norm_full)
        ult = ws[-1]
        gag = any(norm_full[j:j + k] == norm_full[j + k:j + 2 * k] for k in (1, 2, 3)
                  for j in range(len(norm_full) - 2 * k + 1) if norm_full[j] not in ("que", "e", "o", "a"))
        vaos = [pal[k + 1]["t"] - pal[k]["e"] for k in ids[:-1]]
        rep = []
        for n4 in (6, 5, 4):
            for j in range(len(norm) - n4 + 1):
                for j2 in range(j + n4, len(norm) - n4 + 1):
                    if norm[j:j + n4] == norm[j2:j2 + n4] and not any(r_["repete_em"] <= idx_norm[j2] <= r_["repete_em"] + 6 for r_ in rep):
                        rep.append({"de": idx_norm[j], "repete_em": idx_norm[j2], "n": n4, "texto": " ".join(norm[j:j + n4])})
                        break
        fillers = list(hes)
        prox = pal[ids[-1] + 1]["t"] - pal[ids[-1]]["e"] if ids[-1] + 1 < len(pal) else 9.0
        frases.append({
            "id": n, "i0": ids[0], "i1": ids[-1], "t": t, "e": e, "texto": " ".join(ws), "norm": norm,
            "_idx": idx_norm, "_chars": "".join(norm),
            "completa": (bool(FINAL.search(ult)) and not RETICENCIA.search(ult)) or
                        (not RETICENCIA.search(ult) and prox >= GAP_FRASE and bool(norm_full) and norm_full[-1] not in FUNCAO
                         and len(norm) >= 4),
            "reticencia": bool(RETICENCIA.search(ult)),
            "p_media": round(sum(pal[k]["p"] or 0 for k in ids) / len(ids), 3),
            "n_fillers": len(fillers), "gagueira": gag,
            "bastidor": next((re.sub(r"\\b", "", b) for b in BASTIDOR if re.search(b, texto_n)), None),
            "cauda_bastidor": len(norm_full) <= 4 and texto_n in CAUDA,
            "autocorrecao": len(norm_full) <= 2 and texto_n in AUTOCORRECAO,
            "alucinacao_suspeita": any(pal[k]["seg"] in alucina for k in ids),
            "rms_db": round(sum(rms.get(k, -60) for k in ids) / len(ids), 1) if rms else None,
            "pal_por_s": round(len(norm_full) / max(0.2, e - t), 2),
            "maior_pausa_interna": round(max(vaos), 2) if vaos else 0.0,
            "repeticao_interna": rep,
            "ambiguas": [k for k in ids if pal[k].get("ambigua") and (pal[k]["w"][:1].isupper() or any(c.isdigit() for c in pal[k]["w"])
                                                                   or norm_palavra(pal[k]["w"]) in gl)],
        })
    F = frases
    uf = UF(len(F))
    rel: dict[tuple[int, int], str] = {}
    for a in range(len(F)):
        if F[a]["alucinacao_suspeita"] or F[a]["cauda_bastidor"]:
            continue
        for b in range(a + 1, min(len(F), a + 1 + JANELA_FRASES)):
            if F[b]["t"] - F[a]["e"] > JANELA_S:
                break
            if F[b]["alucinacao_suspeita"]:
                continue
            na, nb = F[a]["norm"], F[b]["norm"]
            if len(na) >= 3 and len(nb) >= 3 and sim(na, nb) >= SIM_RETAKE:
                uf.u(a, b)
                rel[(a, b)] = "retake"
            elif len(na) >= 4 and len(nb) >= 4 and na[:4] == nb[:4]:
                uf.u(a, b)  # recomeço: mesma abertura de 4 palavras = outra tentativa da mesma frase
                rel[(a, b)] = "retake"
            elif 2 <= len(na) < len(nb) and (SequenceMatcher(None, na, nb[:len(na)], autojunk=False).ratio() >= 0.75
                                             or sim_chars(F[a]["_chars"], F[b]["_chars"][:len(F[a]["_chars"])]) >= 0.8):
                uf.u(a, b)
                rel[(a, b)] = "falso_comeco"
    grupos_idx: dict[int, list[int]] = {}
    for k in range(len(F)):
        grupos_idx.setdefault(uf.f(k), []).append(k)
    # frase que emenda direto na seguinte (vão < GAP_FRASE) sem recomeçar = fala continuada, não abandonada:
    # o Whisper não põe ponto e o vão é curto, mas quem abandona recomeça a mesma frase (mesmo grupo)
    for k in range(len(F) - 1):
        f, g = F[k], F[k + 1]
        if f["completa"] or f["reticencia"] or len(f["norm"]) < 4 or not f["norm"] or f["norm"][-1] in FUNCAO:
            continue
        if g["t"] - f["e"] < GAP_FRASE and uf.f(k) != uf.f(k + 1) and not g["bastidor"] and not g["alucinacao_suspeita"]:
            f["completa"], f["continuada"] = True, True
    grupos, gid = [], 0
    for membros in sorted((v for v in grupos_idx.values() if len(v) > 1), key=lambda v: F[v[0]]["t"]):
        gid += 1
        nome = f"G{gid:02d}"
        tomadas = []
        for pos, k in enumerate(sorted(membros, key=lambda k: F[k]["t"]), 1):
            fk = F[k]
            tipo = "falso_comeco" if any(rel.get((k, j)) == "falso_comeco" for j in membros) else \
                ("completa" if fk["completa"] else "abandonada")
            fk["grupo"], fk["tomada"] = nome, pos
            tomadas.append({"frase": fk["id"], "tomada": pos, "t": fk["t"], "e": fk["e"], "tipo": tipo,
                            "gagueira": fk["gagueira"], "n_fillers": fk["n_fillers"], "p_media": fk["p_media"],
                            "rms_db": fk["rms_db"], "pal_por_s": fk["pal_por_s"]})
        # metades: duas frases vizinhas que, juntas, batem com outra tomada = UMA tomada partida, não duas alternativas
        ids_m = sorted(membros)
        for k in ids_m:
            if k + 1 not in membros:
                continue
            junto = F[k]["norm"] + F[k + 1]["norm"]
            for c in ids_m:
                if c in (k, k + 1):
                    continue
                sj = sim(junto, F[c]["norm"])
                if sj >= SIM_RETAKE and sj >= max(sim(F[k]["norm"], F[c]["norm"]), sim(F[k + 1]["norm"], F[c]["norm"])) + 0.1:
                    for x in tomadas:
                        if x["frase"] in (F[k]["id"], F[k + 1]["id"]):
                            x["tipo"], x["metade_com"] = "metade", F[k + 1]["id"] if x["frase"] == F[k]["id"] else F[k]["id"]
                    break
        # metade com o fecho FORA do grupo: t3 «…quando o limite acabar» + F032 «ela muda…» ≈ t1 inteira
        for k in ids_m:
            if k + 1 >= len(F) or k + 1 in membros or F[k + 1]["bastidor"] or F[k + 1]["alucinacao_suspeita"]:
                continue
            x_ = next(x for x in tomadas if x["frase"] == F[k]["id"])
            if x_.get("metade_com"):
                continue
            junto = F[k]["norm"] + F[k + 1]["norm"]
            for c in ids_m:
                if c == k:
                    continue
                sj, so = sim(junto, F[c]["norm"]), sim(F[k]["norm"], F[c]["norm"])
                if sj >= SIM_RETAKE and sj >= so + 0.1 and len(F[c]["norm"]) >= len(F[k]["norm"]) + 3:
                    x_["tipo"], x_["metade_com"], x_["fecho_fora_do_grupo"] = "metade", F[k + 1]["id"], True
                    break
        boas = [x for x in tomadas if x["tipo"] == "completa" and not x["gagueira"] and x["n_fillers"] == 0
                and not F[x["frase"] - 1]["bastidor"]]
        regra = "ultima_completa_sem_filler_sem_gagueira"
        if not boas:
            boas = [x for x in tomadas if x["tipo"] == "completa"]
            regra = "ultima_completa (nenhuma limpa)"
        if not boas:
            boas, regra = tomadas, "ultima (nenhuma completa)"
        ult = boas[-1]
        empate = [x["tomada"] for x in boas if x is not ult and abs(len(F[x["frase"] - 1]["norm"]) - len(F[ult["frase"] - 1]["norm"])) <= 1
                  and sim(F[x["frase"] - 1]["norm"], F[ult["frase"] - 1]["norm"]) >= 0.95]
        for x in tomadas:
            F[x["frase"] - 1]["sugerida"] = x is ult
        grupos.append({"id": nome, "tomadas": tomadas, "sugerida": ult["tomada"], "frase_sugerida": ult["frase"],
                       "regra": regra, "sem_tomada_limpa": regra != "ultima_completa_sem_filler_sem_gagueira",
                       "empate_com": empate})
    # retake parcial e sobreposição entre frases vizinhas
    parciais, sobre = [], []
    for a in range(len(F) - 1):
        for b in range(a + 1, min(len(F), a + 3)):
            if F[b]["t"] - F[a]["e"] > 30:
                break
            na, nb = F[a]["norm"], F[b]["norm"]
            achou = False
            if uf.f(a) == uf.f(b):  # tomada inteira repetida: é retake, não parcial
                continue
            for n in range(min(len(na) - 2, 12), 2, -1):
                suf = na[-n:]
                for s in range(0, min(len(nb) - n, 2) + 1):
                    if nb[s:s + n] == suf or SequenceMatcher(None, nb[s:s + n], suf, autojunk=False).ratio() >= 0.85:
                        parciais.append({"frase_a": F[a]["id"], "frase_b": F[b]["id"], "n": n,
                                         "palavra_em_a": F[a]["_idx"][-n], "palavra_em_b": F[b]["_idx"][s],
                                         "texto_a": " ".join(na[-n:]), "sugestao": "A até antes da repetição + B"})
                        achou = True
                        break
                if achou:
                    break
            if not achou and len(na) >= 2 and len(nb) >= 2:
                for n in (5, 4, 3, 2):
                    if len(na) > n and na[-n:] == nb[:n]:
                        sobre.append({"frase_a": F[a]["id"], "frase_b": F[b]["id"], "n": n,
                                      "palavra_em_a": F[a]["_idx"][-n], "texto": " ".join(na[-n:])})
                        break
    # hesitações isoladas por silêncio
    fillers = []
    for k, w in enumerate(pal):
        if eh_hesitacao(w["w"]) or limpa(w["w"]) in HESITACOES_ISOLADAS:
            antes = w["t"] - pal[k - 1]["e"] if k else 9.0
            depois = pal[k + 1]["t"] - w["e"] if k + 1 < len(pal) else 9.0
            if antes >= 0.15 and depois >= 0.15:
                fillers.append({"i": k, "w": w["w"], "t": w["t"], "e": w["e"], "folga_antes": round(antes, 3),
                                "folga_depois": round(depois, 3), "cortavel": None})
    # fronteiras de bloco sugeridas (o Editor decide no MAPA)
    gap_bloco = float(cfg.get("bloco_gap_s", 3.0))
    fronteiras = []
    for a in range(len(F) - 1):
        g = F[a + 1]["t"] - F[a]["e"]
        viz = F[max(0, a - 2):a + 3]
        bast = sum(1 for x in viz if x["bastidor"] or x["cauda_bastidor"] or x["autocorrecao"])
        if g >= gap_bloco:
            fronteiras.append({"entre": [F[a]["id"], F[a + 1]["id"]], "t": round(F[a]["e"], 2), "silencio_s": round(g, 2),
                               "bastidor_perto": bast, "score": round(g + 2 * bast, 2)})
    fronteiras.sort(key=lambda x: -x["score"])
    for f in F:
        f.pop("_chars", None)
        f.pop("_idx", None)
    out = {"schema": "di-retakes/1", "relogio": "bruto", "frases": F, "grupos": grupos,
           "retakes_parciais": parciais, "sobreposicoes": sobre,
           "falsos_comecos": [{"frase_a": F[a]["id"], "frase_b": F[b]["id"]} for (a, b), r in rel.items() if r == "falso_comeco"],
           "fronteiras_sugeridas": fronteiras[:12],
           "resumo": {"frases": len(F), "grupos": len(grupos), "parciais": len(parciais), "sobreposicoes": len(sobre),
                      "bastidor": sum(1 for f in F if f["bastidor"]), "caudas": sum(1 for f in F if f["cauda_bastidor"]),
                      "alucinacao_suspeita": sum(1 for f in F if f["alucinacao_suspeita"]), "fillers_isolados": len(fillers)}}
    gravar_json(projeto / "02_decupagem" / "retakes.json", out, indent=None)
    gravar_json(projeto / "02_decupagem" / "fillers.json", {"schema": "di-fillers/1", "fillers": fillers}, indent=None)
    sem_limpa = [g["id"] for g in grupos if g["sem_tomada_limpa"]]
    registrar_checks(projeto, "F1", [
        check("V10b_alucinacao", True, "info", medido=out["resumo"]["alucinacao_suspeita"],
              detalhe="frases fora do agrupamento e de manter; marcadas ~ no digest"),
        check("V12_grupo_sem_tomada_limpa", not sem_limpa, "aviso", medido=sem_limpa, esperado="nenhum",
              detalhe="costura (retake parcial) com motivo, ou frase perdida; entra na linha 'Sem tomada limpa' do portão F3"),
    ], alvo="02_decupagem/retakes.json")
    return out


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di retakes")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    r = analisar(achar_projeto(a.projeto))
    print(" · ".join(f"{k} {v}" for k, v in r["resumo"].items()))
    return 0
