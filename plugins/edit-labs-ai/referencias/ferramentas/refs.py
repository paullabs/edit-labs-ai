"""Banco de referências: consulta, cadastro, validação e geração do CATALOGO.md. Só biblioteca padrão.
Acha o catálogo pela posição deste arquivo (../catalogo.json); roda de qualquer pasta.
O banco guarda só texto: título, autor, link, licença declarada e a nossa análise. Nada de mídia de terceiros.

    python3 -I refs.py listar [--estilo vox-clean] [--tema anatomia] [--mecanica marca-texto] [--tipo video] [--prof a-fundo]
    python3 -I refs.py ver R03-mariano-two-parties-vox
    python3 -I refs.py estilo vox-clean              refs do estilo + ficha
    python3 -I refs.py mecanica marca-texto          onde cada mecânica aparece
    python3 -I refs.py adicionar --id R23-... --titulo ... --autor ... --url ... --tipo video --tema anatomia \\
                       --estilo vox-clean --mecanica marca-texto --prof vista --licenca "..." --nota "..."
    python3 -I refs.py validar                       confere tags, link, licença, análises, ids repetidos
    python3 -I refs.py gerar                         reescreve CATALOGO.md a partir do catalogo.json"""
import argparse
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
CAT = AQUI / "catalogo.json"
PROF = {"a-fundo": 3, "vista": 2, "citada": 1}


def ler():
    return json.loads(CAT.read_text(encoding="utf-8"))


def gravar(d):
    CAT.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def filtra(refs, a):
    out = []
    for r in refs:
        if a.estilo and a.estilo not in r.get("estilo", []):
            continue
        if a.tema and a.tema not in r.get("tema", []):
            continue
        if a.mecanica and a.mecanica not in r.get("mecanica", []):
            continue
        if a.tipo and r.get("tipo") != a.tipo:
            continue
        if a.prof and r.get("profundidade") != a.prof:
            continue
        out.append(r)
    return sorted(out, key=lambda r: (-PROF.get(r.get("profundidade"), 0), r["id"]))


def linha(r):
    return f"{r['id']:<38} [{r.get('profundidade', '?'):<7}] {r['titulo'][:60]}  ({r.get('autor', '')[:34]})"


def link(r):
    """Link para abrir a referência (externo) ou caminho dentro do plugin; interno sem arquivo usa 'onde'."""
    return r.get("url") or r.get("onde") or ""


def cel(s):
    """Texto seguro para célula de tabela Markdown."""
    return str(s or "").replace("|", "\\|")


def md_titulo(r):
    u = r.get("url")
    return f"[{cel(r['titulo'])}]({u})" if u else f"{cel(r['titulo'])} ({cel(r.get('onde', 'sem link'))})"


def cmd_listar(a):
    d = ler()
    for r in filtra(d["refs"], a):
        print(linha(r))


def cmd_ver(a):
    r = next((x for x in ler()["refs"] if x["id"] == a.id), None)
    if not r:
        sys.exit("id não encontrado")
    for k, v in r.items():
        print(f"{k:>12}: {v}")
    print(f"{'abrir':>12}: {link(r)}")
    for e in r.get("estilo", []):
        print(f"{'ficha':>12}: fichas-de-estilo/{e}.md")


def cmd_estilo(a):
    a.tema = a.tipo = a.prof = a.mecanica = None
    d = ler()
    for r in filtra(d["refs"], a):
        print(linha(r))
    f = AQUI / "fichas-de-estilo" / f"{a.estilo}.md"
    print("\nFICHA:", f if f.exists() else "(sem ficha)")


def cmd_mecanica(a):
    d = ler()
    for r in filtra(d["refs"], a):
        print(linha(r))


def cmd_adicionar(a):
    d = ler()
    if any(r["id"] == a.id for r in d["refs"]):
        sys.exit("id já existe")
    r = {"id": a.id, "titulo": a.titulo, "autor": a.autor or "", "plataforma": a.plataforma or "", "url": a.url,
         "tipo": a.tipo, "tema": a.tema_l, "estilo": a.estilo_l, "mecanica": a.mecanica_l,
         "profundidade": a.prof, "licenca": a.licenca, "nota": a.nota or ""}
    d["refs"].append(r)
    d["atualizado"] = __import__("datetime").date.today().isoformat()
    gravar(d)
    print("adicionada:", a.id)
    cmd_validar(a)
    cmd_gerar(a)


def cmd_validar(_a=None):
    d = ler()
    v = d["vocabulario"]
    ids, erros = set(), []
    for r in d["refs"]:
        if r["id"] in ids:
            erros.append(f"{r['id']}: id repetido")
        ids.add(r["id"])
        for campo, vocab in (("tema", "tema"), ("mecanica", "mecanica"), ("estilo", "estilo")):
            for t in r.get(campo, []):
                if t not in v[vocab]:
                    erros.append(f"{r['id']}: {campo} desconhecido '{t}'")
        if r.get("tipo") not in v["tipo"]:
            erros.append(f"{r['id']}: tipo desconhecido '{r.get('tipo')}'")
        if r.get("profundidade") not in PROF:
            erros.append(f"{r['id']}: profundidade inválida")
        if r.get("tipo") != "interno" and not str(r.get("url") or "").startswith("http"):
            erros.append(f"{r['id']}: referência externa precisa de link http(s)")
        if r.get("tipo") == "interno" and not (r.get("url") or r.get("onde")):
            erros.append(f"{r['id']}: interna precisa de 'url' (caminho no plugin) ou 'onde'")
        if r.get("tipo") == "interno" and r.get("url") and not (AQUI / r["url"]).exists():
            erros.append(f"{r['id']}: caminho interno não existe: {r['url']}")
        if not r.get("licenca"):
            erros.append(f"{r['id']}: sem licença declarada (use 'desconhecida' se a fonte não diz)")
        if r.get("analise") and not (AQUI / r["analise"]).exists():
            erros.append(f"{r['id']}: análise não existe: {r['analise']}")
        if r.get("paleta") and r["paleta"] not in json.loads((AQUI / "paletas" / "paletas.json").read_text()):
            erros.append(f"{r['id']}: paleta não existe: {r['paleta']}")
        if r.get("profundidade") == "a-fundo" and r.get("tipo") != "interno" and not r.get("analise"):
            erros.append(f"{r['id']}: 'a-fundo' precisa de análise")
    for e in v["estilo"]:
        if not (AQUI / "fichas-de-estilo" / f"{e}.md").exists():
            erros.append(f"estilo sem ficha: {e}")
    sem_ref = [e for e in v["estilo"] if not any(e in r.get("estilo", []) for r in d["refs"])]
    for e in sem_ref:
        erros.append(f"estilo sem nenhuma referência: {e}")
    print(f"{len(d['refs'])} referências, {len(v['estilo'])} estilos, {len(erros)} problemas")
    for e in erros:
        print("  -", e)
    return not erros


def cmd_gerar(_a=None):
    d = ler()
    L = ["# Catálogo de referências", "",
         f"Gerado de `catalogo.json` em {d['atualizado']}. **Não editar à mão.** " + d["nota"], ""]
    for e in d["vocabulario"]["estilo"]:
        rs = [r for r in d["refs"] if e in r.get("estilo", [])]
        rs.sort(key=lambda r: (-PROF[r["profundidade"]], r["id"]))
        L += [f"## Estilo: {e}", "", f"Ficha: [{e}](fichas-de-estilo/{e}.md)", "",
              "| id | título | autor | licença declarada | prof. | análise | mecânicas |",
              "|---|---|---|---|---|---|---|"]
        for r in rs:
            an = f"[análise]({r['analise']})" if r.get("analise") else "—"
            L.append(f"| {r['id']} | {md_titulo(r)} | {cel(r.get('autor'))} | {cel(r.get('licenca'))} | "
                     f"{r['profundidade']} | {an} | {', '.join(r.get('mecanica', []))} |")
        L.append("")
    sem = [r for r in d["refs"] if not r.get("estilo")]
    if sem:
        L += ["## Sem estilo definido", "", "| id | título | autor | licença declarada | prof. | nota |",
              "|---|---|---|---|---|---|"]
        for r in sem:
            L.append(f"| {r['id']} | {md_titulo(r)} | {cel(r.get('autor'))} | {cel(r.get('licenca'))} | "
                     f"{r['profundidade']} | {cel(r.get('nota'))} |")
        L.append("")
    L += ["## Por mecânica", "", "| mecânica | referências (a fundo primeiro) |", "|---|---|"]
    for m in d["vocabulario"]["mecanica"]:
        rs = sorted([r for r in d["refs"] if m in r.get("mecanica", [])], key=lambda r: (-PROF[r["profundidade"]], r["id"]))
        if rs:
            L.append(f"| {m} | " + ", ".join(r["id"].split("-")[0] for r in rs) + " |")
    L += ["", "## Por tema", "", "| tema | referências |", "|---|---|"]
    for t in d["vocabulario"]["tema"]:
        rs = sorted([r for r in d["refs"] if t in r.get("tema", [])], key=lambda r: (-PROF[r["profundidade"]], r["id"]))
        if rs:
            L.append(f"| {t} | " + ", ".join(r["id"].split("-")[0] for r in rs) + " |")
    (AQUI / "CATALOGO.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("CATALOGO.md gerado")


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    for nome in ("listar", "mecanica", "estilo"):
        s = sp.add_parser(nome)
        if nome in ("mecanica", "estilo"):
            s.add_argument(nome)
        for f in ("estilo", "tema", "mecanica", "tipo", "prof"):
            if nome == f:
                continue
            s.add_argument(f"--{f}")
    s = sp.add_parser("ver"); s.add_argument("id")
    s = sp.add_parser("adicionar")
    for f in ("id", "titulo", "url", "tipo", "prof"):
        s.add_argument(f"--{f}", required=True)
    s.add_argument("--licenca", "--direitos", dest="licenca", required=True,
                   help="licença declarada pela fonte (ex.: 'todos os direitos reservados', 'CC BY 4.0', 'domínio público')")
    for f in ("autor", "plataforma", "nota"):
        s.add_argument(f"--{f}")
    for f in ("tema", "estilo", "mecanica"):
        s.add_argument(f"--{f}", action="append", default=[], dest=f + "_l")
    sp.add_parser("validar"); sp.add_parser("gerar")
    a = p.parse_args()
    if a.cmd == "mecanica":
        a.mecanica, a.estilo, a.tema, a.tipo, a.prof = a.mecanica, getattr(a, "estilo", None), a.tema, a.tipo, a.prof
    if a.cmd == "estilo":
        a.mecanica, a.tema, a.tipo, a.prof = None, None, None, None
    {"listar": cmd_listar, "ver": cmd_ver, "estilo": cmd_estilo, "mecanica": cmd_mecanica, "adicionar": cmd_adicionar,
     "validar": lambda a: sys.exit(0 if cmd_validar() else 1), "gerar": cmd_gerar}[a.cmd](a)


if __name__ == "__main__":
    main()
