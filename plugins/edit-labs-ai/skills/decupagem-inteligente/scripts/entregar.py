"""F7: entrega. Copia cada master aprovado para FINAIS (<projeto>/FINAIS ou DI_FINAIS) com nome que diz o que é, confere sha256, abre o Finder
e escreve entrega/RESUMO.md (5 linhas + "NÃO verificado").

  di entregar <id> [--saida V|H|ambas]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from comum import DIError, pasta_finais, achar_projeto, agora, carregar, check, config, diario, fase_fechada, gravar_texto, \
    registrar_checks, salvar, sha256_arquivo


def entregar(projeto: Path, vid: str, saidas: list[str]) -> list[Path]:
    projeto = Path(projeto).resolve()
    m = carregar(projeto)
    if not fase_fechada(m, "F7"):
        raise DIError("F7 sem a palavra do usuário: a entrega não sai (di portao fechar F7 --aprovado-por usuario --palavra …)")
    FINAIS = pasta_finais(projeto)
    FINAIS.mkdir(parents=True, exist_ok=True)
    data = time.strftime("%Y-%m-%d")
    bruto = Path(m["inputs"]["bruto"]).stem
    feitos, C = [], []
    for s in saidas:
        src = projeto / "motion" / vid / "12_master" / f"MASTER_{s}_v01.mp4"
        if not src.exists():
            raise DIError(f"{src} não existe")
        dst = FINAIS / f"{data}_{bruto}_{vid}_{s}.mp4"
        shutil.copy2(src, dst)
        ok = sha256_arquivo(src) == sha256_arquivo(dst)
        C.append(check("V76_entrega", ok, "BLOCKER", medido=str(dst), esperado="sha256 da cópia = master", video=vid, saida=s))
        feitos.append(dst)
    registrar_checks(projeto, "F7", C)
    if shutil.which("open"):   # macOS: mostra o arquivo no Finder
        subprocess.run(["open", "-R", str(feitos[0])], check=False)
    ver = [f"{s}: {config(projeto).get('motion', {}).get('fps', 12)} fps" for s in saidas]
    gravar_texto(projeto / "entrega" / "RESUMO.md", "\n".join([
        f"# Entrega — {vid}", "",
        f"1. {len(feitos)} arquivo(s) em {FINAIS}: " + ", ".join(p.name for p in feitos),
        f"2. Motion no estilo da motion-vox · {' · '.join(ver)} · régua de {m.get('regua_origem', 'memoria/regua.yaml')}",
        "3. Verificado por máquina: duração e quadros = corte aprovado, fala preservada, formato, sem quadro preto (laudos/F7_V_*.json)",
        f"4. Aprovado pelo usuário: \"{m['fases']['F7'].get('palavra_do_usuario')}\" em {m['fases']['F7'].get('data')}",
        "5. NÃO verificado: escuta e movimento em tempo real — fica com o usuário", ""]))
    m.setdefault("entregas", []).append({"video": vid, "arquivos": [str(p) for p in feitos], "data": agora()})
    salvar(projeto, m)
    diario(projeto, "NOTA", f"entregue {vid}: " + ", ".join(p.name for p in feitos))
    return feitos


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di entregar")
    ap.add_argument("video")
    ap.add_argument("--saida", choices=["V", "H", "ambas"])
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    s = a.saida or config(projeto).get("saida") or "V"
    for p in entregar(projeto, a.video, ["V", "H"] if s == "ambas" else [s]):
        print(f"✓ {p}")
    return 0
