"""
Digest do transcript — o insumo de leitura da fase 1.

O `02-transcript.json` guarda o timing de cada palavra e fica muitas vezes maior
que o texto com timestamp. O modelo escolhe TRECHO a partir do que foi dito e
mais ou menos quando. O timing por palavra e para os SCRIPTS: in/out preciso,
legenda, autoframe. Mandar `words[]` para um LLM e ocupar contexto com uma
informacao que ele nao usa.

Alem de compactar, marca janelas com sinal de clipe usando so heuristica
deterministica — nenhum LLM. Serve para o agente ler primeiro as janelas
marcadas, nao para decidir por ele: a decisao continua sendo do modelo, e o
digest completo continua disponivel.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# Sinais de docs/05-regras-de-selecao.md §5.7 que dao para detectar sem modelo.
_NUM = re.compile(r"\b\d[\d.,]*\s*(mil|milh(a|o)|bilh|%|reais|real|d[oó]lar|k\b)", re.I)
_DINHEIRO = re.compile(r"\bR\$|\bUS\$|\bcusto|\bfaturam|\blucro|\bpre[cç]o|\bsal[aá]rio", re.I)
_CAUSAL = re.compile(r"\bporque\b|\bpor isso\b|\bo motivo\b|\bacontece que\b", re.I)
_CONTRA = re.compile(r"\bmas na verdade\b|\btodo mundo (acha|pensa|fala)\b|\bmentira\b|"
                     r"\bengano\b|\bo contr[aá]rio\b|\bningu[eé]m (fala|conta)\b", re.I)
_HIST = re.compile(r"\bquando eu\b|\bum dia\b|\bna [eé]poca\b|\beu lembro\b|\baconteceu\b", re.I)
_CONFISSAO = re.compile(r"\beu nunca (contei|falei)\b|\bvou ser sincero\b|\bconfesso\b|"
                        r"\bpela primeira vez\b|\berrei\b|\bfracass", re.I)
_RISCO = re.compile(r"\bquebr(ei|ou|amos)\b|\bfali\b|\bd[ií]vida\b|\bprocesso\b|\bmedo\b", re.I)
_RISO = re.compile(r"\[risadas?\]|\bkkk|\bhaha", re.I)
# §5.7 "sinais de risco": referencia sem antecedente aberta a frase
_ORFAO = re.compile(r"^\s*(isso|isso a[ií]|ele|ela|aquilo|esse|essa|a[ií] ele)\b", re.I)

_PESO = [
    (_NUM, 3.0, "numero"),
    (_DINHEIRO, 2.0, "dinheiro"),
    (_CONTRA, 3.0, "contradicao"),
    (_CONFISSAO, 3.0, "confissao"),
    (_RISCO, 2.0, "risco"),
    (_HIST, 1.5, "historia"),
    (_CAUSAL, 1.0, "causal"),
    (_RISO, 1.0, "humor"),
]


def _mmss(t: float) -> str:
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}" if t < 3600 else f"{t // 3600}:{(t % 3600) // 60:02d}:{t % 60:02d}"


def blocos(segments: list[dict], janela: float = 20.0) -> list[dict]:
    """Agrupa segmentos em blocos de ~`janela` segundos, quebrando na troca de
    locutor. Bloco e a unidade de leitura: um segmento de 1,5s isolado nao diz
    nada, e paga o custo do timestamp mesmo assim."""
    out: list[dict] = []
    cur: dict | None = None
    for s in segments:
        spk = (s.get("speaker") or "").strip()
        texto = (s.get("text") or "").strip()
        if not texto:
            continue
        novo = (
            cur is None
            or spk != cur["speaker"]
            or float(s["start"]) - cur["start"] >= janela
        )
        if novo:
            if cur:
                out.append(cur)
            cur = {"start": float(s["start"]), "end": float(s["end"]),
                   "speaker": spk, "text": texto}
        else:
            cur["end"] = float(s["end"])
            cur["text"] += " " + texto
    if cur:
        out.append(cur)
    return out


def pontuar(b: dict) -> tuple[float, list[str]]:
    t = b["text"]
    score, marcas = 0.0, []
    for rx, peso, nome in _PESO:
        if rx.search(t):
            score += peso
            marcas.append(nome)
    # densidade: fala corrida costuma ser argumento; muito curta e transicao
    dur = max(b["end"] - b["start"], 0.1)
    palavras = len(t.split())
    if palavras / dur > 3.4:
        score += 0.5
    if palavras < 12:
        score -= 1.5
    if _ORFAO.match(t):
        score -= 1.0          # §5.7: abre em referencia sem antecedente
    return score, marcas


def construir(transcript: dict, janela: float = 20.0, marcar: float = 3.0) -> dict:
    bs = blocos(transcript.get("segments") or [], janela)
    for b in bs:
        b["score"], b["marcas"] = pontuar(b)
    return {"blocos": bs, "limiar": marcar}


def como_markdown(d: dict) -> str:
    linhas = [
        "# Digest do transcript",
        "",
        "Texto + timestamp por bloco. `»` marca bloco com sinal deterministico de",
        "clipe (numero, contradicao, confissao, risco, historia). **A marca e",
        "sugestao de ordem de leitura, nao selecao** — momento bom sem palavra-chave",
        "existe e e seu trabalho achar. Leia os marcados primeiro, depois varra o resto.",
        "",
    ]
    lim = d["limiar"]
    for b in d["blocos"]:
        marca = "»" if b["score"] >= lim else " "
        spk = f"{b['speaker']}: " if b["speaker"] else ""
        tag = f"  [{','.join(b['marcas'])}]" if b["score"] >= lim and b["marcas"] else ""
        linhas.append(f"{marca} {_mmss(b['start'])}–{_mmss(b['end'])} {spk}{b['text']}{tag}")
    return "\n".join(linhas) + "\n"


def palavras_em_janelas(transcript: dict, janelas: list[tuple[float, float]]) -> str:
    """Timing por palavra SO das janelas pedidas.

    A fase 2 precisa de timing por palavra para cravar in/out — mas so do trecho
    que virou candidato. Ler o transcript inteiro para cortar 60s tem o mesmo
    defeito do indice visual do video inteiro: paga o episodio para usar o minuto.
    """
    linhas: list[str] = []
    for a, b in janelas:
        linhas.append(f"\n## janela {_mmss(a)}–{_mmss(b)}  ({a:.2f}–{b:.2f}s)\n")
        for s in transcript.get("segments") or []:
            if float(s["end"]) < a or float(s["start"]) > b:
                continue
            for w in (s.get("words") or []):
                ws, we = float(w["start"]), float(w["end"])
                if we < a or ws > b:
                    continue
                linhas.append(f"{ws:.2f} {we:.2f} {w['word']}")
            if not (s.get("words") or []):
                linhas.append(f"{float(s['start']):.2f} {float(s['end']):.2f} "
                              f"[sem timing por palavra] {s.get('text','')}")
    return "\n".join(linhas) + "\n"


def escrever_janelas(run_dir: Path, spec: str) -> dict:
    """`spec` no mesmo formato do visual-index: "120-210,900-960"."""
    tp = run_dir / "02-transcript.json"
    transcript = json.loads(tp.read_text(encoding="utf-8"))
    janelas = []
    for parte in spec.split(","):
        a, b = parte.strip().split("-")
        janelas.append((float(a), float(b)))
    txt = palavras_em_janelas(transcript, janelas)
    out = run_dir / "02-palavras-janelas.txt"
    out.write_text(txt, encoding="utf-8")
    bruto = len(tp.read_text(encoding="utf-8"))
    return {
        "path": str(out),
        "janelas": len(janelas),
        "tokens_antes": bruto // 4,
        "tokens_depois": len(txt) // 4,
        "reducao": round(bruto / max(len(txt), 1), 1),
    }


def escrever(run_dir: Path, janela: float = 20.0, marcar: float = 3.0) -> dict:
    tp = run_dir / "02-transcript.json"
    if not tp.exists():
        raise FileNotFoundError(f"{tp} nao existe — rode `vch prepare` antes")
    transcript = json.loads(tp.read_text(encoding="utf-8"))
    d = construir(transcript, janela, marcar)
    md = como_markdown(d)
    out = run_dir / "02-digest.md"
    out.write_text(md, encoding="utf-8")

    bruto = len(tp.read_text(encoding="utf-8"))
    marcados = sum(1 for b in d["blocos"] if b["score"] >= marcar)
    return {
        "path": str(out),
        "blocos": len(d["blocos"]),
        "marcados": marcados,
        "tokens_antes": bruto // 4,
        "tokens_depois": len(md) // 4,
        "reducao": round(bruto / max(len(md), 1), 1),
    }
