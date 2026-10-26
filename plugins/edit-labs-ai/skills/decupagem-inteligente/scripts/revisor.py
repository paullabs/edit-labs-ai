"""Papel em processo separado (cegueira real nos dois hosts): `claude -p` com o papel como system prompt.

  di leigo F<N> <id> [--agora]         Revisor Leigo sobre laudos/pacote-leigo/F<N>/t<k>/<id>/ (monta o pacote se faltar)
  di diretor <C1|C2|C3|C4|D4> <id>     Diretor (D4: quem escreveu o plano não julga o plano)

O processo não vê o chat. Ferramenta: só Read (Leigo) ou Read/Grep/Glob (Diretor), com --add-dir
restrito à pasta do pacote (Leigo) ou do projeto (Diretor). O laudo volta como texto e é gravado por
`di laudo gravar` (que valida). ANTHROPIC_MODEL do ambiente é limpo antes da chamada.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from comum import REGUA_USUARIO, ROOT, DIError, achar_projeto, carregar, config, gravar_texto, job_marcar, lancar_job, tentativa_atual
from motion import MOTION_VOX

CLAUDE = Path(shutil.which("claude") or (Path.home() / ".local" / "bin" / "claude"))   # a CLI do Claude Code no PATH
FASE_DA_RUBRICA = {"C1": "F1", "C2": "F2", "C3": "F3", "C4": "F4", "D4": "F6"}


def _papel(nome: str) -> str:
    t = (ROOT / "papeis" / nome).read_text(encoding="utf-8")
    return t.split("---", 2)[2] if t.startswith("---") else t


def _rodar(system: str, prompt: str, cwd: Path, dirs: list[Path], tools: str, modelo: str | None) -> str:
    if not CLAUDE.exists():
        raise DIError("a CLI `claude` não está no PATH: use o passe (papeis/*.md) e grave com isolamento: passe")
    env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_MODEL") and k != "ANTHROPIC_DEFAULT_SONNET_MODEL"}
    cmd = [str(CLAUDE), "-p", "--tools", tools, "--system-prompt", system, "--permission-mode", "default"]
    for d in dirs:
        cmd += ["--add-dir", str(d)]
    if modelo:
        cmd += ["--model", modelo]
    # o prompt vai pela entrada padrão: --add-dir e --tools aceitam vários valores e engoliriam o argumento
    r = subprocess.run(cmd, cwd=str(cwd), env=env, input=prompt, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise DIError(f"claude -p falhou ({r.returncode}): {r.stderr.strip()[-400:]}")
    return r.stdout


def _extrair_laudo(texto: str) -> str:
    m = re.search(r"(?ms)^---\s*\n(.*?)\n---\s*$", texto)
    if not m:
        m = re.search(r"(?ms)```ya?ml\s*\n(?:---\s*\n)?(.*?)(?:\n---)?\s*```", texto)
    if not m:
        raise DIError("o revisor não devolveu um laudo com front matter YAML:\n" + texto[-800:])
    corpo = m.group(1).strip()
    return f"---\n{corpo}\n---\n"


def _gravar_com_correcao(projeto: Path, saida: str, de: str, vid, papel: str, cwd: Path, dirs: list, tools: str,
                         modelo, bruto: Path) -> Path:
    """Grava o laudo. Recusa de FORMATO ou COERÊNCIA (não de conteúdo, não de contaminação) volta uma vez ao
    mesmo papel com o próprio laudo e o erro: corrigir só aquilo, sem mudar achado nem severidade."""
    from laudo import gravar
    try:
        return gravar(projeto, _extrair_laudo(saida), de, vid)
    except DIError as e:
        msg = str(e)
        if "CONTAMINADO" in msg or "refeitura" in msg or "já existe" in msg:
            raise
        prompt = ("O laudo abaixo foi recusado pelo validador da skill. Corrija SÓ o que o erro aponta (formato YAML, ou "
                  "coerência entre o texto do achado, o campo `corrigido` e o `veredito`). Não mude achados, severidades, "
                  "nem o que você leu; não leia arquivo nenhum. Responda SÓ com o laudo corrigido (começando com ---).\n\n"
                  f"ERRO:\n{msg}\n\nLAUDO:\n{_extrair_laudo(saida)}")
        saida2 = _rodar(papel, prompt, cwd, dirs, tools, modelo)
        gravar_texto(bruto.with_suffix(".correcao.md"), saida2)
        return gravar(projeto, _extrair_laudo(saida2), de, vid)


def _leigo_um(projeto: Path, fase: str, vid: str, laudo: str, pac: Path, extra: str) -> Path:
    t = tentativa_atual(carregar(projeto), fase)
    arqs = sorted(str(p.relative_to(pac)) for p in pac.rglob("*") if p.is_file())
    prompt = (f"Pacote do {fase}, tentativa {t}, vídeo {vid}. {extra}Leia SÓ estes arquivos desta pasta: {', '.join(arqs)}. "
              f"Faça o teste de recontar e responda as perguntas fechadas do seu papel. Você LEU e OLHOU (nunca escreva 'ouvi'). "
              f"Separe problema do corte de problema do conteúdo (conteúdo é sempre LOW, tipo: conteudo). Responda SÓ com o laudo "
              f"(arquivo começando com ---). Use: laudo: {laudo} · fase: {fase} · tentativa: {t} · isolamento: processo · "
              f"alvo: {pac.relative_to(projeto)}/")
    saida = _rodar(_papel("revisor-leigo.md"), prompt, pac, [pac], "Read", config(projeto).get("revisor_modelo"))
    bruto = projeto / "laudos" / f".{fase}_{laudo}_leigo_t{t}_{vid}.bruto.md"
    gravar_texto(bruto, saida)
    return _gravar_com_correcao(projeto, saida, "leigo", vid, _papel("revisor-leigo.md"), pac, [pac], "Read",
                                config(projeto).get("revisor_modelo"), bruto)


def leigo(projeto: Path, fase: str, vid: str) -> Path:
    """F2–F4: um laudo L. F5–F7: dois passos — L1 só com imagem; L2 com as palavras e o próprio L1."""
    import pacote_leigo
    projeto = Path(projeto).resolve()
    if fase not in ("F5", "F6", "F7"):
        pac = pacote_leigo.pacote(projeto, fase, vid)   # sempre remontado: pacote velho na mesma tentativa engana o Leigo
        return _leigo_um(projeto, fase, vid, "L", pac, "")
    p1 = pacote_leigo.pacote(projeto, fase, vid, passo=1)
    l1 = _leigo_um(projeto, fase, vid, "L1", p1, "PASSO 1: só imagem, sem nenhuma palavra. Reconte o que cada quadro mostra. ")
    p2 = pacote_leigo.pacote(projeto, fase, vid, passo=2, laudo_l1=l1)
    return _leigo_um(projeto, fase, vid, "L2", p2, "PASSO 2: agora com a palavra dita sob cada quadro e o seu próprio passo 1 "
                                                   "(meu_passo1.md). O desenho bate com a fala naquela hora? ")


def diretor(projeto: Path, rub: str, vid: str | None) -> Path:
    from laudo import gravar
    fase = FASE_DA_RUBRICA[rub]
    t = tentativa_atual(carregar(projeto), fase)
    if vid is None and rub in ("C2", "C3"):
        vids = carregar(projeto).get("videos") or []
        partes = []
        for v in vids:
            partes.append({"C2": f"[{v}] 02_decupagem/{v}/MARCAS.md, 02_decupagem/{v}/roteiro_montado.txt, 02_decupagem/{v}/TOMADAS.jpg",
                           "C3": f"[{v}] 03_corte/{v}/VERIFICACAO.md, 03_corte/{v}/juntas.jpg, 03_corte/{v}/avisos.json, 02_decupagem/{v}/roteiro_montado.txt"}[rub])
        alvo_multi = "; ".join(partes) + f"; laudos/{fase}_V_verificador_t{t}.json"
        prompt = (f"Rubrica {rub} ({fase}, tentativa {t}) para os vídeos {', '.join(vids)}. Leia: {alvo_multi}. "
                  f"Responda a rubrica inteira para CADA vídeo (um achado cita o vídeo em `item` ou `observacao`). "
                  f"Um laudo só, `alvo` listando os vídeos. Responda SÓ com o laudo (arquivo começando com ---), "
                  f"com isolamento: processo, host: {carregar(projeto).get('host')}.")
        saida = _rodar(_papel("diretor.md"), prompt, projeto, [projeto], "Read,Grep,Glob", config(projeto).get("revisor_modelo"))
        bruto = projeto / "laudos" / f".{fase}_{rub}_diretor_t{t}.bruto.md"
        gravar_texto(bruto, saida)
        return _gravar_com_correcao(projeto, saida, "diretor", None, _papel("diretor.md"), projeto, [projeto], "Read",
                                    config(projeto).get("revisor_modelo"), bruto)
    alvo = {"C1": "02_decupagem/MAPA_DO_BRUTO.md, 02_decupagem/retakes.json (use o campo resumo e grupos), 01_transcript/digest.md",
            "C2": f"02_decupagem/{vid}/MARCAS.md, 02_decupagem/{vid}/roteiro_montado.txt, 02_decupagem/{vid}/TOMADAS.jpg, "
                  f"02_decupagem/{vid}/edl.json, laudos/F2_V_verificador_t{t}.json",
            "C3": f"03_corte/{vid}/VERIFICACAO.md, 03_corte/{vid}/juntas.jpg, 02_decupagem/{vid}/roteiro_montado.txt, "
                  f"03_corte/{vid}/avisos.json, laudos/F3_V_verificador_t{t}.json",
            "C4": f"motion/{vid}/00_brief/PLANO_MOTION.md, motion/{vid}/00_brief/VERIFICACAO_PLANO.md, "
                  f"motion/{vid}/00_brief/PROMPTS.md, motion/{vid}/00_brief/transcript_palavras.json (por trecho), "
                  f"motion/{vid}/00_brief/cortes.json, motion/{vid}/00_brief/avisos.json, "
                  f"motion/{vid}/00_brief/silencios_corte.json, a régua em {ROOT / 'memoria' / 'regua.yaml'} (modelo)"
                  f"{' coberta por ' + str(REGUA_USUARIO) + ' (respostas do usuário)' if REGUA_USUARIO.exists() else ''} e os "
                  f"registros em {MOTION_VOX / 'referencias' / 'registros.md'}"}.get(rub, "")
    prompt = (f"Rubrica {rub} ({fase}, tentativa {t}{', vídeo ' + vid if vid else ''}). Leia: {alvo}. Responda a rubrica inteira. "
              f"Responda SÓ com o laudo (arquivo começando com ---), com isolamento: processo, host: {carregar(projeto).get('host')}.")
    # rubrica de UM vídeo: a régua global e as referências da motion-vox também ficam legíveis; laudo e bruto levam o vídeo
    dirs = [projeto] + ([ROOT / "memoria", MOTION_VOX / "referencias"] + ([REGUA_USUARIO.parent] if REGUA_USUARIO.exists() else [])
                        if rub.startswith(("C4", "D")) else [])
    saida = _rodar(_papel("diretor.md"), prompt, projeto, dirs, "Read,Grep,Glob", config(projeto).get("revisor_modelo"))
    bruto = projeto / "laudos" / f".{fase}_{rub}_diretor_t{t}{'_' + vid if vid else ''}.bruto.md"
    gravar_texto(bruto, saida)
    return _gravar_com_correcao(projeto, saida, "diretor", vid, _papel("diretor.md"), projeto, dirs, "Read",
                                config(projeto).get("revisor_modelo"), bruto)


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog=f"di {cmd}")
    ap.add_argument("alvo", help="F<N> (leigo) ou rubrica C1–C4/D4 (diretor)")
    ap.add_argument("video", nargs="?")
    ap.add_argument("--agora", action="store_true")
    ap.add_argument("--forcar", action="store_true", help="chama o revisor com HIGH em aberto (diga por quê no DIARIO)")
    ap.add_argument("--esperar", type=int, default=0)
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    # Revisor não se gasta com o que o script já mediu: HIGH/BLOCKER em aberto e sem declaração escrita barra a
    # chamada (di autorrejeitar <fase> mostra a lista). Declarar é escrever o id do check com o motivo.
    from autorrejeitar import bloqueios
    fase_ = a.alvo.upper() if a.alvo.upper().startswith("F") else FASE_DA_RUBRICA.get(a.alvo.upper(), "")
    if fase_ and not a.forcar:
        blo = bloqueios(projeto, fase_, a.video)
        if blo:
            print(f"✗ não chamei o revisor: {len(blo)} check do Verificador em aberto sem declaração escrita "
                  f"em {fase_}:", *[f"  - {x}" for x in blo],
                  "  corrija, ou escreva o id e o motivo no decisoes.json/plano/DIARIO (di autorrejeitar "
                  f"{fase_}{' ' + a.video if a.video else ''} mostra a lista inteira).", sep="\n")
            return 1
    nome = f"{cmd}-{a.alvo}-{a.video or 'todos'}"
    if not a.agora:
        lancar_job(projeto, nome, [cmd, a.alvo] + ([a.video] if a.video else []) + ["--agora"])
        print(f"rodando em segundo plano ({nome}); acompanhe com di status")
        if a.esperar:
            fim = time.time() + min(300, a.esperar)
            while time.time() < fim and carregar(projeto)["jobs"][nome]["status"] == "rodando":
                time.sleep(5)
            print(carregar(projeto)["jobs"][nome]["status"])
        return 0
    try:
        p = leigo(projeto, a.alvo.upper(), a.video) if cmd == "leigo" else diretor(projeto, a.alvo.upper(), a.video)
        print(f"✓ laudo gravado: {p}")
        if os.environ.get("DI_JOB"):
            job_marcar(projeto, nome, "ok")
    except Exception as e:
        if os.environ.get("DI_JOB"):
            job_marcar(projeto, nome, "erro", nota=str(e)[:300])
        raise
    return 0
