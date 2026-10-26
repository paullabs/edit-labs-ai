"""Laudos: validar (V81/V81b), gravar (--de diretor|leigo) e render do JSON do Verificador (V79).

Formato: arquivo .md que começa com front matter YAML (o esqueleto da motion-vox) e pode ter
prosa depois. O `portao.py` só lê o YAML.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

from comum import (DIError, achar_projeto, agora, carregar, fase_info, gravar_texto, ler_json, norm_palavra, salvar,
                   tentativa_atual)

VEREDITOS = {"APROVADO", "APROVADO_COM_CORRECAO", "REPROVADO"}
SEVERIDADES = {"BLOCKER", "HIGH", "MEDIUM", "LOW"}
ISOLAMENTOS = {"subagente", "processo", "passe", "chat_novo"}
# verbos de escuta: só valem com `escuta: humana` gravada em respostas[] (V81)
# "assust" sozinho casava "servidor assusta quem não é da área" (medo, não som): só o passado
# do susto conta
# só a AFIRMAÇÃO de ter ouvido ("ouvi", "escutei", "soou", "estala"); "ouvir"/"ouvindo" falam da escuta do usuário
ESCUTA = [r"\bouvi(mos)?\b", r"\bescut(ei|amos)\b", r"\bassust(ou|ei|ava|aram)\b", r"\bestal(a|ou|ando|ido|os)\b",
          r"\bsoou\b", r"\bsoa(va)?\b", r"\b(muito|mais|meio|bem|um pouco|pouco) alto\b", r"\bclique incomod"]
# Leigo contaminado (V81b): vocabulário de Diretor/arquivo
CONTAMINA = [r"\bscrim\b", r"\bregistro\b", r"\brubrica\b", r"\b[CD][1-5]\b", r"\bitem \d", r"\.json\b",
             r"\bedl\b", r"\bkeyframe\b", r"\bPSNR\b", r"\bdBFS\b", r"\bhierarquia\b"]
# nomes de ARQUIVO que só são jargão em caixa alta: "MARCAS" é o arquivo da F2, "marcas" é
# palavra de todo dia ("umas marcas pequenininhas"). Casados sem re.I, senão o Leigo é
# descartado por falar português.
CONTAMINA_CS = [r"\bMARCAS\b", r"\bEDL\b", r"\bTOMADAS\.jpg\b"]


_CHAVE = re.compile(r"^(\s*(?:- )?)([A-Za-z_][\w]*): (.+)$")


def reparar_yaml(fm: str) -> str:
    """Texto livre sem aspas com ': ' no meio quebra o YAML (a lição da motion-vox). Reescreve cada valor
    simples de várias linhas, ou com ': ' dentro, como bloco dobrado `>-`, mantendo o texto igual."""
    linhas, out, i = fm.split("\n"), [], 0
    while i < len(linhas):
        m = _CHAVE.match(linhas[i])
        if not m or m.group(3)[:1] in ("'", '"', "|", ">", "[", "{"):
            out.append(linhas[i]); i += 1; continue
        pre, chave, valor = m.groups()
        ind = len(pre) + (0 if pre.strip() == "" else 0)
        cont, j = [valor], i + 1
        # continuação: linhas mais indentadas que a chave que não abrem outra chave nem item
        base = len(pre)
        while j < len(linhas) and linhas[j].strip() and (len(linhas[j]) - len(linhas[j].lstrip())) > base \
                and not _CHAVE.match(linhas[j]) and not linhas[j].lstrip().startswith("- "):
            cont.append(linhas[j].strip()); j += 1
        if len(cont) > 1 or ": " in valor or " #" in valor:
            filho = " " * (base + 2)
            out.append(f"{pre}{chave}: >-")
            out += [filho + c for c in cont]
        else:
            out.append(linhas[i])
        i = j
    return "\n".join(out)


def ler_laudo(texto: str) -> tuple[dict, str]:
    if not texto.lstrip().startswith("---"):
        raise DIError("laudo sem front matter YAML (o arquivo tem que começar com ---)")
    _, fm, corpo = texto.lstrip().split("---", 2)
    try:
        d = yaml.safe_load(fm) or {}
    except yaml.YAMLError:
        d = yaml.safe_load(reparar_yaml(fm)) or {}  # se ainda falhar, o erro sobe com a linha
    if not isinstance(d, dict):
        raise DIError("front matter do laudo não é um objeto YAML")
    return d, corpo


def papel_de(d: dict) -> str:
    k = str(d.get("laudo", ""))
    if k.startswith("L"):
        return "leigo"
    if k[:1] in ("C", "D"):
        return "diretor"
    if k.startswith("V"):
        return "verificador"
    raise DIError(f"campo `laudo` desconhecido: {k!r} (use C1–C4, D1–D5, L, L1, L2)")


def _texto_livre(d: dict) -> str:
    return yaml.safe_dump(d, allow_unicode=True)


def validar(d: dict, corpo: str, projeto: Path | None) -> list[str]:
    erros: list[str] = []
    papel = papel_de(d)
    for campo in ("laudo", "alvo", "fase", "tentativa", "veredito", "achados", "proxima_etapa", "nao_visto", "escopo"):
        if campo not in d or d[campo] in (None, ""):
            if not (campo == "achados" and d.get(campo) == []):
                erros.append(f"falta o campo `{campo}`")
    if d.get("veredito") not in VEREDITOS:
        erros.append(f"veredito inválido: {d.get('veredito')!r}")
    if papel in ("diretor", "leigo") and d.get("isolamento") not in ISOLAMENTOS:
        erros.append(f"`isolamento` tem que ser um de {sorted(ISOLAMENTOS)}")
    ach = d.get("achados") or []
    if not isinstance(ach, list):
        erros.append("`achados` tem que ser uma lista")
        ach = []
    for i, a in enumerate(ach, 1):
        if a.get("severidade") not in SEVERIDADES:
            erros.append(f"achado {i}: severidade inválida {a.get('severidade')!r}")
        if not a.get("observacao"):
            erros.append(f"achado {i}: falta `observacao`")
        if papel == "diretor" and not a.get("correcao"):
            erros.append(f"achado {i}: falta `correcao` (uma alteração, específica)")
    abertos = lambda s: [a for a in ach if a.get("severidade") == s and not a.get("corrigido")]
    if abertos("BLOCKER") and d.get("veredito") != "REPROVADO":
        erros.append("há BLOCKER aberto: o veredito tem que ser REPROVADO")
    if abertos("HIGH") and d.get("veredito") != "REPROVADO":
        erros.append("há HIGH não corrigido: o veredito tem que ser REPROVADO (ou marque `corrigido: true` depois de re-medir)")
    if any(a.get("corrigido") and a.get("severidade") in ("HIGH", "MEDIUM") for a in ach) and d.get("veredito") == "APROVADO":
        erros.append("houve HIGH/MEDIUM corrigido: o veredito é APROVADO_COM_CORRECAO")
    # nunca aprovar na primeira passagem sem achado (corte-viral regra 3)
    if papel == "diretor" and int(d.get("tentativa") or 1) == 1 and not ach and not d.get("procurei"):
        erros.append("laudo t1 sem achado: escreva `procurei: \"X, Y e Z\"` ou registre o achado")
    # escuta inventada (V81)
    livre = _texto_livre({k: v for k, v in d.items() if k not in ("nao_visto",)}) + corpo
    def _afirma(p_):  # "não ouvi", "nem ouvi" é negação, não afirmação
        return any(not re.search(r"\b(n[ãa]o|nem)\s+(\w+\s+)?$", livre[max(0, m_.start() - 16):m_.start()], flags=re.I)
                   for m_ in re.finditer(p_, livre, flags=re.I))
    if any(_afirma(p) for p in ESCUTA):
        ok = False
        if projeto:
            m = carregar(projeto)
            ok = any(r.get("escuta") == "humana" for r in m.get("respostas", []))
        if not ok:
            erros.append("verbo de escuta (ouvi, assustou, alto, estala…) sem `escuta: humana` do usuário gravada: "
                         "ninguém na skill ouve; use o número medido e 'escuta pendente'")
    # Leigo
    if papel == "leigo":
        if not d.get("o_que_entendi") and str(d.get("laudo")) in ("L", "L2"):
            erros.append("Revisor Leigo: falta `o_que_entendi` em palavras próprias")
        suja = [p for p in CONTAMINA if re.search(p, livre, flags=re.I)]
        suja += [p for p in CONTAMINA_CS if re.search(p, livre)]
        if suja:
            erros.append("CONTAMINADO: o Leigo usou vocabulário de Diretor/arquivo (" + ", ".join(suja[:4]) + ") — descartar e refazer")
    # Diretor D1/D2 (motion)
    if str(d.get("laudo")) == "D2" and not d.get("referencia_vista"):
        erros.append("D2 sem `referencia_vista:` (frame de REFERENCIAS-VISUAIS.md que a cena seguiu)")
    if str(d.get("laudo")) == "D1" and "07_assets/qa/" not in livre:
        erros.append("D1 sem citar os recortes de 07_assets/qa/ (checar_asset.py)")
    return erros


def _repeticao_de_fala(txt: str, pacote: Path | None) -> bool:
    """Regra 16 do Leigo, por código: o trecho citado repete 3+ palavras, mas NÃO uma atrás da outra, e as duas
    ocorrências estão na mesma linha do pacote (um trecho só, sem emenda ‖ no meio) → jeito de falar do autor."""
    q = max(re.findall(r'"([^"]+)"|“([^”]+)”', txt) or [("", "")], key=lambda x: len(x[0] or x[1]))
    ws = [norm_palavra(w) for w in re.split(r"[\s/‖]+", q[0] or q[1]) if norm_palavra(w)]
    for n in (5, 4, 3):
        pos: dict = {}
        for i in range(len(ws) - n + 1):
            pos.setdefault(tuple(ws[i:i + n]), []).append(i)
        rep = {g: p for g, p in pos.items() if len(p) >= 2}
        if not rep:
            continue
        if any(b - a <= n for p in rep.values() for a, b in zip(p, p[1:])):
            return False                                   # colada: o mesmo trecho dito duas vezes seguidas é CORTE
        if pacote is None:
            return False
        linhas = []
        for nome in ("roteiro.txt", "texto.txt", "plano.txt"):
            if (pacote / nome).exists():
                linhas += (pacote / nome).read_text(encoding="utf-8").splitlines()
        for g in rep:
            alvo = " ".join(g)
            for ln in linhas:
                partes = ln.split("‖")
                if any(" ".join(norm_palavra(w) for w in pt.split() if norm_palavra(w)).count(alvo) >= 2 for pt in partes):
                    return True
        return False
    return False


def nome_arquivo(d: dict, video: str | None) -> str:
    k, f, t = str(d["laudo"]), str(d["fase"]), int(d["tentativa"])
    papel = papel_de(d)
    base = f"{f}_{k}_{'leigo' if papel == 'leigo' else 'diretor'}_t{t}"
    return base + (f"_{video}" if video else "") + ".md"


def _pulo_de_cabeca(txt: str, projeto: Path, alvo: str | None) -> bool:
    """Regra 17 do Leigo, por código: reclamação de que o rosto/cabeça muda de tamanho ou de lugar NA EMENDA, num
    vídeo em que o Verificador já mediu o pulo (V37 → avisos.json). O pulo é próprio do corte entre tomadas: nenhuma
    remontagem o tira, e a skill já dá o dono — a cutaway do plano (F4). Vira `conteudo` LOW, com o número medido."""
    b = txt.lower()
    if not (re.search(r"\bros[t]o|cabe[çc]a|enquadrament|quadro\b", b) and
            re.search(r"pula|salta|escorrega|muda de lugar|troca de lugar|fica maior|fica menor|maior e", b) and
            re.search(r"emend|junta|corte", b)):
        return False
    for base in ([Path(projeto) / str(alvo)] if alvo else []) + list((Path(projeto) / "03_corte").glob("*")):
        av = (base if base.is_dir() else base.parent) / "avisos.json"
        if av.exists():
            if any(a.get("tipo") == "pulo_de_cabeca" for a in (ler_json(av, []) or [])):
                return True
    return False


def ajustar_leigo(d: dict, projeto: Path) -> bool:
    """Regras de código sobre o laudo do Leigo (o texto dele fica; muda tipo, severidade e veredito, com o original
    guardado em *_do_leigo). Devolve True se algo mudou."""
    antes = yaml.safe_dump(d, allow_unicode=True, sort_keys=True)
    ach = d.get("achados") or []
    alvo = Path(projeto) / str(d.get("alvo") or "") if d.get("alvo") else None
    for a in ach:  # [palavra incerta] já é pendência do usuário: nunca reprova o corte (§12 #8)
        if "palavra incerta" in f"{a.get('onde', '')} {a.get('observacao', '')}".lower() and a.get("tipo") != "pendencia":
            a["tipo_do_leigo"], a["tipo"] = a.get("tipo"), "pendencia"
        if a.get("tipo") == "corte" and _repeticao_de_fala(f"{a.get('onde', '')} {a.get('observacao', '')}",
                                                           alvo if alvo and alvo.is_dir() else None):
            a["tipo_do_leigo"], a["tipo"] = "corte", "conteudo"
            a["regra"] = "16: repetição não colada, dentro de um trecho sem emenda → jeito de falar do autor"
        if a.get("tipo") == "corte" and _pulo_de_cabeca(f"{a.get('onde', '')} {a.get('observacao', '')}",
                                                        Path(projeto), str(d.get("alvo") or "")):
            a["tipo_do_leigo"], a["tipo"] = "corte", "conteudo"
            a["regra"] = "17: pulo de cabeça na emenda, já medido pelo V37 → tarefa da F4 (cutaway), não remontagem"
        if a.get("tipo") in ("pendencia", "conteudo") and a.get("severidade") != "LOW":
            a["severidade_do_leigo"], a["severidade"] = a.get("severidade"), "LOW"
    abertos = [a for a in ach if a.get("severidade") in ("BLOCKER", "HIGH") and not a.get("corrigido")]
    certo = "REPROVADO" if abertos else "APROVADO"
    if d.get("veredito") != certo:
        d.setdefault("veredito_do_leigo", d.get("veredito"))
        d["veredito"] = certo
        d["veredito_ajustado"] = "pela regra: BLOCKER/HIGH aberto → REPROVADO; só LOW → APROVADO"
    return yaml.safe_dump(d, allow_unicode=True, sort_keys=True) != antes


def reaplicar(projeto: Path, arq: Path) -> bool:
    """Regra de código nova (ou corrigida) sobre um laudo do Leigo já gravado: reescreve só os campos que o código
    decide, com data e motivo; o que o Leigo escreveu não muda. Laudo de Diretor nunca passa por aqui."""
    d, corpo = ler_laudo(arq.read_text(encoding="utf-8"))
    if papel_de(d) != "leigo":
        raise DIError("reaplicar vale só para laudo do Leigo (o do Diretor não se reescreve)")
    if not ajustar_leigo(d, projeto):
        return False
    d["reaplicado"] = f"{agora()} — regras de código do Leigo reaplicadas (laudo.py)"
    gravar_texto(arq, f"---\n{yaml.safe_dump(d, allow_unicode=True, sort_keys=False)}---\n{corpo.lstrip()}")
    from comum import diario
    diario(projeto, "NOTA", f"{arq.name}: regras de código do Leigo reaplicadas → veredito {d['veredito']}"
                            f" (o Leigo escreveu {d.get('veredito_do_leigo')})")
    return True


def gravar(projeto: Path, texto: str, de: str, video: str | None) -> Path:
    d, corpo = ler_laudo(texto)
    if papel_de(d) != de:
        raise DIError(f"o laudo diz `{d.get('laudo')}` mas foi gravado --de {de}")
    if de == "leigo":  # o Leigo julga entendimento; a regra do veredito é aplicada por código
        ajustar_leigo(d, projeto)
    erros = validar(d, corpo, projeto)
    m = carregar(projeto)
    fase = str(d["fase"])
    fi = fase_info(m, fase)
    contaminado = any(e.startswith("CONTAMINADO") for e in erros)
    if contaminado:
        chave = f"{d['laudo']}_t{d['tentativa']}_{video or ''}"
        n = fi.setdefault("refeituras_leigo", {}).get(chave, 0) + 1
        fi["refeituras_leigo"][chave] = n
        salvar(projeto, m)
        if n < 3:
            raise DIError("\n".join(erros) + f"\n(refeitura {n} de 2: rode o Leigo de novo com o mesmo pacote)")
        d["invalido"] = True
        d.setdefault("achados", []).append({"severidade": "HIGH", "observacao": "Leigo contaminado nesta tentativa (3 refeituras)"})
        erros = [e for e in erros if not e.startswith("CONTAMINADO")]
    if erros:
        raise DIError("laudo recusado:\n  - " + "\n  - ".join(erros))
    nome = nome_arquivo(d, video)
    if str(d["laudo"]).startswith("D") and d.get("motion_id"):
        destino = Path(projeto) / "motion" / d["motion_id"] / "11_qa" / nome
    else:
        destino = Path(projeto) / "laudos" / nome
    if destino.exists():
        raise DIError(f"{destino.name} já existe: laudo não se sobrescreve; abra uma tentativa nova")
    fm = yaml.safe_dump(d, allow_unicode=True, sort_keys=False)
    gravar_texto(destino, f"---\n{fm}---\n{corpo.lstrip()}")
    rel = str(destino.relative_to(projeto))
    m = carregar(projeto)
    fi = fase_info(m, fase)
    if rel not in fi.setdefault("laudos", []):
        fi["laudos"].append(rel)
    salvar(projeto, m)
    return destino


def render_verificador(p: Path) -> Path:
    d = ler_json(p)
    if not d:
        raise DIError(f"{p} não existe")
    L = [f"# Verificação — {d.get('fase')} · {d.get('alvo') or ''}", "",
         f"`source: deterministic` · válido: **{'sim' if d.get('valid') else 'NÃO'}** · atualizado {d.get('atualizado')}", "",
         "| id | vídeo | junta | ok | severidade | medido | esperado | detalhe |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in d.get("checks", []):
        L.append(f"| {c['id']} | {c.get('video') or ''} | {c.get('junta') or ''} | {'✓' if c.get('ok') else '✗'} | "
                 f"{c.get('severidade')} | {c.get('medido')} | {c.get('esperado')} | {c.get('detalhe', '')} |")
    out = p.with_suffix(".md")
    gravar_texto(out, "\n".join(L) + "\n\n<!-- gerado por laudo.py só a partir do JSON (V79) -->\n")
    return out


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di laudo")
    ap.add_argument("acao", choices=["validar", "gravar", "render", "reaplicar"])
    ap.add_argument("arquivo", help="laudo .md (ou - para ler do stdin) / JSON do Verificador no render")
    ap.add_argument("--de", choices=["diretor", "leigo"])
    ap.add_argument("--video", help="id do vídeo quando o laudo é por vídeo (Leigo)")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    if a.acao == "render":
        print(render_verificador(Path(a.arquivo)))
        return 0
    if a.acao == "reaplicar":
        arq = Path(a.arquivo)
        mudou = reaplicar(achar_projeto(a.projeto), arq)
        print(f"✓ {arq.name}: " + ("regras reaplicadas" if mudou else "nada muda com as regras de hoje"))
        return 0
    texto = sys.stdin.read() if a.arquivo == "-" else Path(a.arquivo).read_text(encoding="utf-8")
    projeto = None
    try:
        projeto = achar_projeto(a.projeto)
    except DIError:
        if a.acao == "gravar":
            raise
    if a.acao == "validar":
        d, corpo = ler_laudo(texto)
        erros = validar(d, corpo, projeto)
        if erros:
            print("✗ laudo inválido:\n  - " + "\n  - ".join(erros))
            return 1
        print("✓ laudo válido")
        return 0
    if not a.de:
        raise DIError("gravar exige --de diretor|leigo")
    print(f"✓ gravado: {gravar(projeto, texto, a.de, a.video)}")
    return 0
