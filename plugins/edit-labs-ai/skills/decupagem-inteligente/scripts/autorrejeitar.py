"""di autorrejeitar — a lista de auto-rejeição da fase, por código, antes de gastar uma rodada de revisor.

    di autorrejeitar F2 [<id>]        o que eu mesma reprovaria em F2 (todos os vídeos, ou um)
    di autorrejeitar F3 <id>

Devolve 0 quando está pronto para o revisor e 1 quando há HIGH/BLOCKER em aberto sem declaração escrita.
`di diretor` e `di leigo` chamam `bloqueios()` antes de lançar: revisor não se gasta com o que o script já mediu.

Declarar é escrever o id do check (V17, V19…) com o motivo em um destes lugares: o `decisoes.json` do vídeo, o
MAPA_DO_BRUTO.md, o PLANO_MOTION.md, o DIARIO.md ou a mensagem de portão. Declarado, o check sai do bloqueio e
vira assunto do laudo — que é onde ele deve ser julgado.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from comum import (DIError, achar_projeto, arquivo_verificador, carregar, ler_json, mmss, tentativa_atual)

# o que o Editor tem que OLHAR na fase (o script não olha quadro)
OLHAR = {
    "F1": ["01_transcript/digest.md (as marcas ~, ½, B e ? nas tomadas que ficam)"],
    "F2": ["02_decupagem/{v}/TOMADAS.jpg (olhar fora, mão no rosto, desfoque, gente no quadro)",
           "02_decupagem/{v}/MARCAS.md (cada emenda: folga à voz in/out · resíduo)"],
    "F3": ["03_corte/{v}/juntas.jpg (o quadro de depois da emenda é o mesmo plano?)",
           "03_corte/{v}/VERIFICACAO.md (linha a linha)"],
    "F4": ["motion/{v}/00_brief/PLANO_MOTION.md (cena a cena contra a régua)"],
}


def _declarados(projeto: Path, vids: list[str]) -> str:
    """Todo texto onde uma declaração vale. Lido uma vez; o id do check é procurado nele."""
    alvos = [projeto / "DIARIO.md", projeto / "02_decupagem" / "MAPA_DO_BRUTO.md"]
    alvos += [projeto / "02_decupagem" / v / "decisoes.json" for v in vids]
    alvos += [projeto / "motion" / v / "00_brief" / "PLANO_MOTION.md" for v in vids]
    alvos += sorted((projeto / "laudos").glob("PORTAO_*.md")) if (projeto / "laudos").exists() else []
    out = []
    for a in alvos:
        if a.exists():
            out.append(a.read_text(encoding="utf-8"))
    return "\n".join(out)


def _checks(projeto: Path, fase: str, vids: list[str]) -> list[dict]:
    """Os checks que valem na fase: o JSON da tentativa e, na F3, também o do corte renderizado de cada vídeo
    (verificacao.json), que é onde moram V24–V42."""
    m = carregar(projeto)
    out = list((ler_json(arquivo_verificador(projeto, fase, tentativa_atual(m, fase)), None) or {}).get("checks", []))
    if fase == "F3":
        for vd in vids:
            out += (ler_json(projeto / "03_corte" / vd / "verificacao.json", None) or {}).get("checks", [])
    if fase in ("F4", "F5", "F6", "F7"):
        for vd in vids:
            out += (ler_json(projeto / "motion" / vd / "00_brief" / "verificacao_plano.json", None) or {}).get("checks", [])
    return out


def bloqueios(projeto: Path, fase: str, video: str | None = None) -> list[str]:
    """HIGH/BLOCKER em aberto no Verificador da tentativa corrente, sem o id declarado por escrito."""
    m = carregar(projeto)
    vids = [video] if video else (m.get("videos") or [])
    cs = _checks(projeto, fase, vids)
    if not cs:
        return []
    texto = _declarados(projeto, vids)
    fora = []
    for c in cs:
        if c.get("ok") or c.get("severidade") not in ("BLOCKER", "HIGH"):
            continue
        if video and c.get("video") and c["video"] != video:
            continue
        cid = c["id"]
        if cid in texto or cid.split("_")[0] in texto:
            continue
        fora.append(f"{cid} ({c.get('severidade')}): {str(c.get('medido'))[:90]}")
    return fora


def _emendas_coladas(projeto: Path, vid: str) -> list[str]:
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json", None)
    if not edl:
        return []
    lim = 1.2
    juntas, t = [], 0.0
    for s in edl["segmentos"]:
        if t > 0:
            juntas.append(t)
        t += s["source_out"] - s["source_in"]
    return [f"emendas a {b - a:.2f} s uma da outra ({mmss(a)} e {mmss(b)}): só uma leva punch-in"
            for a, b in zip(juntas, juntas[1:]) if b - a < lim]


def relatorio(projeto: Path, fase: str, video: str | None) -> int:
    m = carregar(projeto)
    vids = [video] if video else (m.get("videos") or [])
    t = tentativa_atual(m, fase)
    print(f"# Auto-rejeição — {fase}, tentativa {t}{' · ' + video if video else ''}")
    blo = bloqueios(projeto, fase, video)
    cs = _checks(projeto, fase, vids)
    declarados = [f'{c["id"]}: {str(c.get("medido"))[:70]}' for c in cs
                  if not c.get("ok") and c.get("severidade") in ("BLOCKER", "HIGH")
                  and c["id"] not in " ".join(blo)]
    print("\n## Em aberto, sem declaração (isto bloqueia o revisor)")
    print("\n".join(f"- {x}" for x in blo) or "- nada")
    print("\n## Em aberto, já declarado por escrito (vai como assunto do laudo)")
    print("\n".join(f"- {x}" for x in declarados) or "- nada")
    avisos = [f"- {c['id']}: {str(c.get('medido'))[:90]}" for c in cs
              if not c.get("ok") and c.get("severidade") not in ("BLOCKER", "HIGH")]
    print("\n## Avisos e LOW (não bloqueiam)")
    print("\n".join(avisos) or "- nada")
    if fase in ("F2", "F3"):
        col = [x for vd in vids for x in _emendas_coladas(projeto, vd)]
        print("\n## Emendas a menos de 1,2 s")
        print("\n".join(f"- {x}" for x in col) or "- nada")
    print("\n## O script não olha — olhe você")
    for linha in OLHAR.get(fase, []):
        for vd in (vids or [""]):
            print(f"- {linha.format(v=vd)}")
    print("\n" + ("✗ NÃO chame o revisor ainda: declare ou corrija o que está acima." if blo
                  else "✓ pronto para o revisor."))
    return 1 if blo else 0


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog=f"di {cmd}")
    ap.add_argument("fase", help="F1…F7")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    fase = a.fase.upper()
    if not fase.startswith("F"):
        raise DIError("primeiro argumento é a fase (F1…F7)")
    return relatorio(achar_projeto(a.projeto), fase, a.video)
