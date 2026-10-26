"""Gera ESTADO.md a partir do run-manifest.json. ESTADO.md nunca se edita à mão (V80)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from comum import (FASES, NOME_FASE, carregar, fase_fechada, fase_info, hora_curta, ler_json, gravar_texto,
                   tentativa_atual)


def linha_estado(m: dict) -> str:
    fase = m.get("fase_atual", "F0")
    t = tentativa_atual(m, fase)
    ultimo = None
    for f in FASES:
        fi = m.get("fases", {}).get(f, {})
        if fi.get("veredito") in ("APROVADO", "APROVADO_COM_CORRECAO"):
            ultimo = (f, fi.get("aprovado_por", "interno"), fi.get("data"))
    apr = "nada" if not ultimo else f"{ultimo[0]} ({'usuário' if ultimo[1] == 'usuario' else 'interno'}, {hora_curta(ultimo[2])})"
    return f"{fase} {NOME_FASE.get(fase, '')} · tentativa {t} de 3 · aprovado até: {apr} · modo: {m.get('modo', 'portoes')}"


def _progresso(projeto: Path) -> str | None:
    p = ler_json(Path(projeto) / "01_transcript" / ".progresso.json")
    if not p or p.get("status") != "rodando":
        return None
    s = f"{p.get('etapa')}"
    if p.get("pct") is not None:
        s += f" {p['pct']:.0f} %"
    if p.get("eta_s"):
        s += f" (faltam ~{max(1, round(p['eta_s'] / 60))} min)"
    return s


def texto_estado(projeto: Path, m: dict) -> str:
    ins = m.get("inputs", {})
    fase = m.get("fase_atual", "F0")
    vids = m.get("videos") or []
    L = [f"# ESTADO — {m.get('projeto')} ({ins.get('tipo', '?')}, {len(vids) or '?'} vídeo(s), saída: {ins.get('saida', '?')}) · modo: {m.get('modo')} · host: {m.get('host')}",
         "", f"**{linha_estado(m)}**", ""]
    fi = fase_info(m, fase)
    ts = fi.get("tentativas", [])
    em_curso = ts[-1] if ts and ts[-1].get("status") == "em_curso" else None
    L.append(f"Fase atual: {fase} {NOME_FASE.get(fase, '')}" + (f" — tentativa {em_curso['t']} em curso ({em_curso.get('o_que_mudou', '')})" if em_curso else ""))
    aprov = []
    for f in FASES:
        x = m.get("fases", {}).get(f, {})
        if fase_fechada(m, f):
            quem = "usuário" if x.get("aprovado_por") == "usuario" else "interno"
            pal = f', "{x["palavra_do_usuario"]}"' if x.get("palavra_do_usuario") else ""
            aprov.append(f"{f} ✓ ({quem}, {hora_curta(x.get('data'))}{pal})")
    L.append("Aprovado: " + (" · ".join(aprov) if aprov else "nada"))
    rodando = [f"{n} ({j.get('log')})" for n, j in m.get("jobs", {}).items() if j.get("status") == "rodando"]
    erro = [f"{n} → ver {j.get('log')}" for n, j in m.get("jobs", {}).items() if j.get("status") == "erro"]
    prog = _progresso(projeto)
    L.append("Rodando: " + (", ".join(rodando) + (f" — {prog}" if prog else "") if rodando else "nada"))
    if erro:
        L.append("Com erro: " + ", ".join(erro))
    L.append(f"Próximo passo: {m.get('proximo_passo') or '—'}")
    if m.get("falta"):
        L.append("Falta para fechar " + fase + ": " + " · ".join(m["falta"]))
    resp = m.get("respostas", [])
    L.append("Respostas já dadas: " + (" · ".join(f"#{r['n']} {r['pergunta'][:40]} = {str(r['resposta'])[:40]}" for r in resp) if resp else "nenhuma"))
    aut = m.get("autorizacoes", [])
    L.append("Autorizações: " + (" · ".join(f"#{a['n']} {a['o_que']}" for a in aut) if aut else "nenhuma"))
    pend = [p for p in m.get("pendencias", []) if p.get("estado") == "aberta"]
    L.append("Pendências: " + (" · ".join(f"#{p['n']} {p['o_que']}" for p in pend) if pend else "nenhuma"))
    dt = m.get("decisoes_travadas") or {}
    L.append("Decisões travadas: " + (" · ".join(f"{k} = {v}" for k, v in dt.items()) if dt else "nenhuma (régua de motion ainda não respondida)"))
    val = [a["caminho"] for a in m.get("artefatos", []) if a.get("estado") == "valido"][-6:]
    rep = [a["caminho"] for a in m.get("artefatos", []) if a.get("estado") == "reprovado"][-4:]
    L.append("Versões válidas: " + (" · ".join(val) if val else "—") + ("  — reprovadas: " + " · ".join(rep) if rep else ""))
    corpo = "\n".join(L) + "\n"
    h = hashlib.sha256(corpo.encode()).hexdigest()[:16]
    return corpo + f"\n<!-- gerado por estado.py a partir de run-manifest.json · corpo:{h} · não edite à mão -->\n"


def _editado_a_mao(antes: str) -> bool:
    corpo, sep, rodape = antes.rpartition("\n<!-- gerado por estado.py")
    if not sep or "corpo:" not in rodape:
        return True
    h = rodape.split("corpo:")[1].split()[0]
    return hashlib.sha256(corpo.encode()).hexdigest()[:16] != h


def gerar(projeto: Path, m: dict | None = None) -> tuple[str, bool]:
    """Regenera ESTADO.md. Devolve (texto, estava_editado_a_mao) — V80."""
    m = m or carregar(projeto)
    novo = texto_estado(projeto, m)
    p = Path(projeto) / "ESTADO.md"
    editado = p.exists() and _editado_a_mao(p.read_text(encoding="utf-8"))
    gravar_texto(p, novo)
    return novo, editado
