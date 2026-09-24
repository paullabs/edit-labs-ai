#!/usr/bin/env python3
"""
Biblioteca de assets sob medida (referencias/assets-sob-medida.md §6): o que foi gerado e aprovado num projeto
fica disponível para os próximos, com o que é, as tags, o prompt e onde já foi usado.

    python3 biblioteca.py buscar "manual"                      # procura em o_que, tags e nome
    python3 biblioteca.py listar                               # tudo, com contagem de usos
    python3 biblioteca.py registrar 07_assets/cutout/NOME.png --o-que "bloco espiral aberto" --tags "papel,manual" \
        [--prompt "..."] [--prompt-arquivo 00_brief/PROMPTS.md] [--d1 aprovado]
    python3 biblioteca.py usar NOME                            # copia para 07_assets/cutout/ e anota o uso

O acervo mora na motion-vox global (MOTION_VOX ou ~/.claude/skills/motion-vox/biblioteca/), não no projeto.
Logo e foto real NUNCA entram aqui (licença é por projeto: 07_assets/ATRIBUICOES.md). Python 3.9.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

GLOBAL = Path(os.environ.get("MOTION_VOX") or (Path.home() / ".claude" / "skills" / "motion-vox"))
BIB = GLOBAL / "biblioteca"
CAT = BIB / "CATALOGO.json"
ROOT = Path.cwd()


def _agora() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _ler() -> dict:
    if CAT.exists():
        return json.loads(CAT.read_text(encoding="utf-8"))
    return {"schema": "motion-vox-biblioteca/1", "assets": []}


def _gravar(d: dict) -> None:
    BIB.mkdir(parents=True, exist_ok=True)
    tmp = CAT.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(CAT)


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def buscar(termo: str) -> list:
    t = _norm(termo)
    out = [a for a in _ler()["assets"] if t in _norm(" ".join([a["nome"], a["o_que"], " ".join(a.get("tags", []))]))]
    for a in out:
        usos = a.get("usos", [])
        print(f"  {a['nome']:24s} {a['o_que']}  · tags {', '.join(a.get('tags', []))} · D1 {a.get('d1', '?')} · "
              f"{len(usos)} uso(s)" + (f", último em {Path(usos[-1]['projeto']).name}" if usos else ""))
    if not out:
        print(f"  nada para '{termo}': gere sob medida (referencias/assets-sob-medida.md §4)")
    return out


def registrar(arquivo: str, o_que: str, tags: str, prompt: str = "", prompt_arquivo: str = "", d1: str = "pendente") -> dict:
    src = Path(arquivo)
    if not src.exists():
        raise SystemExit(f"{src} não existe")
    if re.match(r"^(LOGO_|FOTO_)", src.name, re.I):
        raise SystemExit("logo e foto real não entram na biblioteca (licença é por projeto)")
    d = _ler()
    nome = src.stem
    if any(a["nome"] == nome for a in d["assets"]):
        raise SystemExit(f"{nome} já está na biblioteca (dê outro nome à variante nova)")
    if prompt_arquivo and not prompt:
        txt = Path(prompt_arquivo).read_text(encoding="utf-8")
        base = re.sub(r"_v\d+$", "", nome)
        m = re.search(rf"##\s*{re.escape(base)}.*?```\n(.*?)```", txt, re.S)
        prompt = m.group(1).strip() if m else ""
    (BIB / "png").mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, BIB / "png" / src.name)
    reg = {"nome": nome, "arquivo": f"png/{src.name}", "o_que": o_que.strip(),
           "tags": [x.strip() for x in tags.split(",") if x.strip()], "prompt": prompt, "d1": d1,
           "origem": str(ROOT), "data": _agora(), "usos": [{"projeto": str(ROOT), "data": _agora()}]}
    d["assets"].append(reg)
    _gravar(d)
    print(f"✓ {nome} na biblioteca ({reg['o_que']})")
    return reg


def usar(nome: str) -> Path:
    d = _ler()
    a = next((x for x in d["assets"] if x["nome"] == nome), None)
    if not a:
        raise SystemExit(f"{nome} não está na biblioteca (python3 biblioteca.py buscar …)")
    outros = [u for u in a.get("usos", []) if u["projeto"] != str(ROOT)]
    if outros:
        print(f"  ⚠ {nome} já apareceu em {len(outros)} projeto(s), o último {Path(outros[-1]['projeto']).name}: "
              f"se for o vídeo anterior da série, gere uma variante nova (assets-sob-medida.md §2)")
    dst = ROOT / "07_assets" / "cutout" / Path(a["arquivo"]).name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BIB / a["arquivo"], dst)
    a.setdefault("usos", []).append({"projeto": str(ROOT), "data": _agora()})
    _gravar(d)
    print(f"✓ {nome} → {dst.relative_to(ROOT)}")
    return dst


def listar() -> None:
    d = _ler()
    for a in d["assets"]:
        print(f"  {a['nome']:24s} {a['o_que'][:60]:60s} {len(a.get('usos', []))} uso(s) · D1 {a.get('d1', '?')}")
    print(f"  {len(d['assets'])} asset(s) em {BIB}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="biblioteca.py")
    ap.add_argument("acao", choices=["buscar", "listar", "registrar", "usar"])
    ap.add_argument("alvo", nargs="?")
    ap.add_argument("--o-que", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--prompt", default="")
    ap.add_argument("--prompt-arquivo", default="")
    ap.add_argument("--d1", default="pendente")
    a = ap.parse_args()
    if a.acao == "buscar":
        buscar(a.alvo or "")
    elif a.acao == "listar":
        listar()
    elif a.acao == "registrar":
        if not (a.alvo and a.o_que):
            raise SystemExit("registrar ARQUIVO --o-que '…' --tags '…'")
        registrar(a.alvo, a.o_que, a.tags, a.prompt, a.prompt_arquivo, a.d1)
    else:
        usar(a.alvo or "")
