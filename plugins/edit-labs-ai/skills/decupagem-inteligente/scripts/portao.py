"""O checkpoint que recusa (§08.4). O modelo "acha" que revisou; este script não acha.

  di portao status
  di portao pode-avancar F<N>
  di portao abrir-tentativa F<N> --o-que-mudou "…" [--reprovado-por diretor|leigo|verificador|usuario] [--video ID[,ID…]]
  di portao fechar F<N> --aprovado-por usuario|interno [--palavra "…"] [--video ID]
  di portao responder --pergunta "…" --resposta "…" [--chave saida|glossario|modo|regua.densidade|…] [--escuta humana]
                      [--so-projeto]   (saida e regua.* também vão para a régua do usuário: não se perguntam de novo)
  di portao pendencia --o-que "…"   |   di portao confirmar N --valor "…"
  di portao proximo "texto do próximo passo"
  di autorizar-imagens N --portao F4 --video ID
  di diario --tipo DECISAO|RESPOSTA|TENTATIVA|NOTA --texto "…"
"""
from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path

import yaml

import estado
from comum import (FASES, NOME_FASE, DIError, achar_projeto, agora, carregar, config, diario, fase_fechada, vale_para,
                   fase_info, gravar_config, gravar_json, gravar_texto, jobs_atualizar, lembrar_resposta, ler_json,
                   pares_da_confirmacao, salvar, tentativa_atual, valor_da_resposta, valores_motion)

# quem assina o quê (§07.5 é a fonte única)
# Fluxo de TRÊS ENTREGAS ao usuário (regra: entrega rápida, sem rodadas de revisão em cascata):
# (1) corte decupado + prévia, (2) plano de motion, (3) vídeo completo. Entre uma e
# outra não há rodada de Diretor/Leigo em cascata — quem aprova é o usuário; o que corre por dentro
# é o Verificador (mede) e, no corte, a AUDITORIA frase a frase. A única rodada de Diretor que
# sobra é a ANÁLISE do plano já aprovado ("analisar se faz sentido"), uma vez, antes de criar.
REQ = {
    "F1": {"verif": True, "diretor": [], "leigo": None},
    "F2": {"verif": True, "diretor": [], "leigo": None},
    "F3": {"verif": True, "diretor": [], "leigo": None, "auditoria": True},
    "F4": {"verif": True, "diretor": [], "leigo": None},
    "F5": {"verif": True, "diretor": ["C4"], "leigo": None},   # C4 = análise do plano aprovado, uma vez
    "F6": {"verif": True, "diretor": [], "leigo": None},
    "F7": {"verif": True, "diretor": [], "leigo": None},
}
REGUA = ["densidade", "fim_de_cena", "motion_fps", "prints_oficiais"]


def portao_do_usuario(m: dict, fase: str) -> bool:
    """As três entregas: F3 (corte + prévia), F4 (plano) e F7 (vídeo completo). O resto corre sem parar."""
    modo = m.get("modo", "portoes")
    if fase in ("F3", "F7"):
        return True
    if fase == "F4":
        return modo == "portoes"
    return False


def _laudo(path: str) -> dict | None:
    try:
        t = Path(path).read_text(encoding="utf-8")
        _, fm, _ = t.lstrip().split("---", 2)
        return yaml.safe_load(fm) or {}
    except Exception:
        return None


def faltas_para_fechar(projeto: Path, m: dict, fase: str, aprovado_por: str | None) -> list[str]:
    faltas: list[str] = []
    if fase == "F0":
        if not m.get("inputs", {}).get("saida"):
            faltas.append("saída (V/H/ambas) não gravada")
        return faltas
    req = REQ[fase]
    t = tentativa_atual(m, fase)
    lau = Path(projeto) / "laudos"
    for n, j in (m.get("jobs") or {}).items():
        if j.get("status") == "rodando":
            faltas.append(f"job `{n}` ainda rodando (espere com di status)")
    if req["verif"]:
        v = ler_json(lau / f"{fase}_V_verificador_t{t}.json")
        if not v:
            faltas.append(f"JSON do Verificador ausente (laudos/{fase}_V_verificador_t{t}.json)")
        elif not v.get("valid"):
            bl = [c["id"] for c in v["checks"] if not c.get("ok") and c.get("severidade") == "BLOCKER"]
            faltas.append("Verificador com BLOCKER: " + ", ".join(bl))
    if req.get("auditoria"):
        # a prévia só vai ao usuário com a auditoria frase a frase escrita para cada vídeo
        for v_ in (m.get("videos") or []):
            if not (Path(projeto) / "03_corte" / v_ / "AUDITORIA.md").exists():
                faltas.append(f"auditoria frase a frase ausente para {v_} (di auditar {v_})")
    vids_ = m.get("videos") or []
    ts_d = fase_info(m, fase).get("tentativas") or []
    for rub in req["diretor"]:
        if rub.startswith(("C4", "D")) and len(vids_) > 1:
            # rubrica de UM vídeo: cada vídeo precisa do laudo da última tentativa que valeu para ele
            for v in vids_:
                vals = [x["t"] for x in ts_d if vale_para(x, v)]
                tv = max(vals) if vals else t
                cand = [c for k in range(tv, 0, -1) for c in
                        glob.glob(str(lau / f"{fase}_{rub}_diretor_t{k}_{v}.md")) +
                        glob.glob(str(Path(projeto) / "motion" / v / "11_qa" / f"{fase}_{rub}_diretor_t{k}*.md")) +
                        [c for c in glob.glob(str(lau / f"{fase}_{rub}_diretor_t{k}.md"))
                         if f"motion/{v}/" in ((_laudo(c) or {}).get("alvo") or "")]][:1]
                if not cand:
                    faltas.append(f"laudo {rub} do Diretor (t{tv}) faltando para: {v}")
                    continue
                d = _laudo(cand[0]) or {}
                if d.get("veredito") not in ("APROVADO", "APROVADO_COM_CORRECAO"):
                    faltas.append(f"laudo {rub} do Diretor de {v} está {d.get('veredito')}: tentativa nova para {v}")
            continue
        cand = glob.glob(str(lau / f"{fase}_{rub}_diretor_t{t}*.md")) + \
            glob.glob(str(Path(projeto) / "motion" / "*" / "11_qa" / f"{fase}_{rub}_diretor_t{t}*.md"))
        if not cand:
            faltas.append(f"laudo {rub} do Diretor (t{t}) ausente")
            continue
        for c in cand:
            d = _laudo(c) or {}
            if d.get("veredito") not in ("APROVADO", "APROVADO_COM_CORRECAO"):
                faltas.append(f"laudo {rub} do Diretor está {d.get('veredito')}: abra tentativa nova")
    vids = m.get("videos") or []
    if req["leigo"] and not (fase in ("F4", "F5", "F6") and m.get("modo") == "so_corte"):
        passos = ["L"] if req["leigo"] == "L" else ["L1", "L2"]
        ts_ = fase_info(m, fase).get("tentativas") or []

        def t_do_video(v):  # a última tentativa que valeu para este vídeo (tentativa com `video` vale só para ele)
            vals = [x["t"] for x in ts_ if vale_para(x, v)]
            return max(vals) if vals else t
        for ps in passos:
            if len(vids) > 1:
                for v in vids:
                    tv = t_do_video(v)
                    achados = glob.glob(str(lau / f"{fase}_{ps}_leigo_t{tv}_{v}.md"))
                    if not achados:
                        faltas.append(f"laudo {ps} do Leigo (t{tv}) faltando para: {v}")
                        continue
                    d = _laudo(achados[0]) or {}
                    if d.get("veredito") == "REPROVADO":
                        faltas.append(f"Revisor Leigo REPROVOU ({Path(achados[0]).name}): tentativa nova para {v}")
                continue
            achados = glob.glob(str(lau / f"{fase}_{ps}_leigo_t{t}*.md"))
            if not achados:
                faltas.append(f"laudo {ps} do Revisor Leigo (t{t}) ausente")
                continue
            for a in achados:
                d = _laudo(a) or {}
                if d.get("veredito") == "REPROVADO":
                    faltas.append(f"Revisor Leigo REPROVOU ({Path(a).name}): tentativa nova (desacordo com o Diretor abre t2, §07.7)")
    if portao_do_usuario(m, fase) and aprovado_por != "usuario":
        faltas.append("este é portão do usuário: feche com --aprovado-por usuario --palavra \"<a palavra dele>\"")
    fi = fase_info(m, fase)
    if any(x.get("veredito") == "REPROVADO" for x in fi.get("tentativas", [])):
        txt = (Path(projeto) / "DIARIO.md").read_text(encoding="utf-8") if (Path(projeto) / "DIARIO.md").exists() else ""
        if not re.search(rf"TENTATIVA.*\n.*{fase}", txt):
            faltas.append(f"houve reprovação em {fase} sem entrada TENTATIVA no DIARIO")
    if fase == "F4":
        faltas += falta_regua(m)
    return faltas


def falta_regua(m: dict) -> list[str]:
    dt = m.get("decisoes_travadas") or {}
    dv = set(m.get("decidir_vendo") or [])
    sem = [k for k in REGUA if k not in dt and k not in dv]
    return [f"régua de motion sem resposta do usuário: {', '.join(sem)} (V43): pergunte uma vez, de múltipla escolha (memoria/regua.yaml)"] if sem else []


def proxima(fase: str) -> str | None:
    i = FASES.index(fase)
    return FASES[i + 1] if i + 1 < len(FASES) else None


def cmd_status(projeto: Path) -> int:
    m = carregar(projeto)
    if jobs_atualizar(m):
        salvar(projeto, m)
    texto, editado = estado.gerar(projeto, m)
    if editado:
        print("⚠ ESTADO.md tinha sido editado à mão; regenerei do manifest (nunca se edita à mão).")
    print(texto.split("\n<!--")[0].strip())
    return 0


def cmd_pode(projeto: Path, fase: str) -> int:
    m = carregar(projeto)
    anterior = FASES[FASES.index(fase) - 1] if fase != "F0" else None
    faltas: list[str] = []
    if anterior and not fase_fechada(m, anterior):
        faltas.append(f"{anterior} {NOME_FASE[anterior]} não está fechada:")
        faltas += ["  " + f for f in faltas_para_fechar(projeto, m, anterior, None)]
    if anterior and fase_fechada(m, anterior) and portao_do_usuario(m, anterior) and \
            fase_info(m, anterior).get("aprovado_por") != "usuario":
        faltas.append(f"{anterior} é portão do usuário e foi fechada sem ele")
    if fase == "F4":
        faltas += falta_regua(m)
    if faltas:
        print(f"✗ não pode avançar para {fase}. Falta:")
        print("\n".join(f"  - {f}" for f in faltas))
        return 1
    print(f"✓ pode avançar para {fase} {NOME_FASE[fase]}")
    return 0


def cmd_abrir(projeto: Path, fase: str, o_que_mudou: str, reprovado_por: str | None, video: str | None,
              autorizado_usuario: str | None = None) -> int:
    if not o_que_mudou or not o_que_mudou.strip():
        raise DIError("--o-que-mudou é obrigatório: a tentativa nova tem que dizer o que muda")
    m = carregar(projeto)
    anterior = FASES[FASES.index(fase) - 1] if FASES.index(fase) > 1 else None
    if anterior and not fase_fechada(m, anterior):
        raise DIError(f"{anterior} não está fechada: não se abre tentativa de {fase} antes (di portao pode-avancar)")
    fi = fase_info(m, fase)
    ts = fi.setdefault("tentativas", [])
    if ts and ts[-1].get("o_que_mudou", "").strip().lower() == o_que_mudou.strip().lower():
        raise DIError("o_que_mudou igual ao da tentativa anterior: repetir não é tentar de novo")
    if ts:
        ts[-1]["status"] = "reprovada"
        ts[-1]["veredito"] = "REPROVADO"
        ts[-1]["reprovado_por"] = reprovado_por or ts[-1].get("reprovado_por") or "?"
    # pedido de mudança do usuário não é falha do Editor e abre um ciclo novo: só contam as tentativas depois dele
    ult_usuario = max((k for k, x in enumerate(ts) if x.get("reprovado_por") == "usuario"), default=-1)
    contam = [x for x in ts[ult_usuario + 1:] if x.get("reprovado_por") != "usuario"]
    t_novo = (ts[-1]["t"] + 1) if ts else 2
    # teto de 3 por escalada; cada tentativa que o usuário autorizou depois de uma escalada abre mais uma
    teto = 3 + sum(1 for x in ts if x.get("autorizada_por_usuario"))
    if autorizado_usuario:
        if not any(autorizado_usuario.strip().lower() in (r.get("resposta") or "").lower() for r in m.get("respostas", [])):
            raise DIError("--autorizado-usuario precisa ser a palavra literal já gravada com di portao responder")
        teto += 1
    if reprovado_por != "usuario" and len(contam) >= teto:
        raise DIError(f"{fase} já teve {len(contam)} tentativas: escale ao usuário com as tentativas lado a lado e UMA recomendação")
    if not ts:  # a t1 implícita vira registro
        ts.append({"t": 1, "status": "reprovada", "veredito": "REPROVADO", "reprovado_por": reprovado_por or "?"})
    vids_t = [v.strip() for v in (video or "").split(",") if v.strip()]
    desconhecidos = [v for v in vids_t if v not in (m.get("videos") or [])]
    if desconhecidos:
        raise DIError(f"--video desconhecido: {', '.join(desconhecidos)}")
    ts.append({"t": t_novo, "o_que_mudou": o_que_mudou.strip(), "status": "em_curso", "inicio": agora(),
               **({"video": vids_t[0]} if len(vids_t) == 1 else ({"videos": vids_t} if vids_t else {})),
               **({"autorizada_por_usuario": autorizado_usuario.strip()} if autorizado_usuario else {})})
    m["fase_atual"] = fase
    salvar(projeto, m)
    diario(projeto, "TENTATIVA", f"{fase} t{t_novo - 1} reprovada por {reprovado_por or '?'}. t{t_novo}: {o_que_mudou.strip()}")
    print(f"✓ {fase} tentativa {t_novo} aberta — {o_que_mudou.strip()}")
    return 0


def cmd_fechar(projeto: Path, fase: str, aprovado_por: str, palavra: str | None, video: str | None) -> int:
    m = carregar(projeto)
    if aprovado_por == "usuario" and not palavra:
        raise DIError("fechar por usuario exige --palavra com o que ele disse, literal")
    faltas = faltas_para_fechar(projeto, m, fase, aprovado_por)
    if faltas:
        print(f"✗ {fase} não fecha. Falta:")
        print("\n".join(f"  - {f}" for f in faltas))
        return 1
    fi = fase_info(m, fase)
    veredito = "APROVADO"
    for lp in fi.get("laudos", []):
        d = _laudo(str(Path(projeto) / lp)) or {}
        if d.get("fase") == fase and d.get("veredito") == "APROVADO_COM_CORRECAO":
            veredito = "APROVADO_COM_CORRECAO"
    if video:
        fi.setdefault("por_id", {})[video] = {"veredito": veredito, "aprovado_por": aprovado_por, "data": agora(), "palavra": palavra}
        vids = m.get("videos") or []
        if not all(v in fi["por_id"] for v in vids):
            salvar(projeto, m)
            print(f"✓ {fase} fechada para {video}; faltam: {', '.join(v for v in vids if v not in fi['por_id'])}")
            return 0
    fi.update(veredito=veredito, aprovado_por=aprovado_por, data=agora(), palavra_do_usuario=palavra)
    ts = fi.get("tentativas") or []
    if ts and ts[-1].get("status") == "em_curso":
        ts[-1].update(status="fechada", veredito=veredito)
    nxt = proxima(fase)
    if m.get("modo") == "so_corte" and fase == "F3":
        nxt = "F7"
    if nxt:
        m["fase_atual"] = nxt
        m["proximo_passo"] = f"começar {nxt} {NOME_FASE[nxt]} (carregar fases/{nxt[1]}-*.md)"
    m["falta"] = []
    salvar(projeto, m)
    if aprovado_por == "usuario":
        diario(projeto, "RESPOSTA", f"{fase} aprovada pelo usuário: \"{palavra}\"", quem="usuário")
    print(f"✓ {fase} {NOME_FASE[fase]} fechada ({aprovado_por}) → agora {m['fase_atual']}")
    return 0


def cmd_responder(projeto: Path, a) -> int:
    m = carregar(projeto)
    n = len(m.setdefault("respostas", [])) + 1
    r = {"n": n, "pergunta": a.pergunta, "resposta": a.resposta, "data": agora()}
    if a.chave:
        r["chave"] = a.chave
    if a.video:
        r["video"] = a.video
    if a.escuta:
        r["escuta"] = a.escuta
    m["respostas"].append(r)
    cfg = config(projeto)
    if a.chave == "saida":
        txt_ = a.resposta.strip().lower()
        val = {"vertical": "V", "v": "V", "horizontal": "H", "h": "H", "as duas": "ambas", "ambas": "ambas"}.get(txt_)
        if val is None:  # resposta literal em frase: "as duas fases: vertical e horizontal"
            tem_v, tem_h = "vertical" in txt_, "horizontal" in txt_
            val = "ambas" if (tem_v and tem_h) or "as duas" in txt_ else ("V" if tem_v else ("H" if tem_h else a.resposta))
        m.setdefault("inputs", {})["saida"] = val
        cfg["saida"] = val
        if not a.so_projeto:   # preferência: o próximo projeto herda e não pergunta de novo
            lembrar_resposta("saida", a.resposta, val)
    elif a.chave == "glossario":
        termos = [x.strip() for x in re.split(r"[,;\n]", a.resposta) if x.strip()]
        gravar_texto(Path(projeto) / "00_fonte" / "glossario.txt", "\n".join(termos) + "\n")
        gravar_texto(Path(projeto) / "00_fonte" / ".glossario_ok", agora())
    elif a.chave == "modo":
        m["modo"] = a.resposta
    elif a.chave and a.chave.startswith("regua."):
        k = a.chave.split(".", 1)[1]
        valor = valor_da_resposta(k, a.resposta)
        if valor == "decidir_vendo":
            m.setdefault("decidir_vendo", []).append(k)
        else:
            m.setdefault("decisoes_travadas", {})[k] = a.resposta
            cfg.setdefault("motion", {})[k] = a.resposta
            cfg["motion"].update(valores_motion({k: {"valor": valor}}))
        if not a.so_projeto:   # preferência: o próximo projeto herda e não pergunta de novo
            lembrar_resposta(k, a.resposta, valor)
    elif a.chave == "tipo":
        m.setdefault("inputs", {})["tipo"] = a.resposta
    gravar_config(projeto, cfg)
    salvar(projeto, m)
    diario(projeto, "RESPOSTA", f"{a.pergunta} — \"{a.resposta}\"", quem="usuário")
    print(f"✓ resposta #{n} gravada")
    return 0


def main(cmd: str, argv: list[str]) -> int:
    if cmd == "status":
        argv = ["status", *argv]
    if cmd == "autorizar-imagens":
        ap = argparse.ArgumentParser(prog="di autorizar-imagens")
        ap.add_argument("n", type=int)
        ap.add_argument("--portao", default="F4")
        ap.add_argument("--video", required=True)
        ap.add_argument("--palavra", required=True, help="o que o usuário disse, literal")
        ap.add_argument("--projeto")
        a = ap.parse_args(argv)
        projeto = achar_projeto(a.projeto)
        m = carregar(projeto)
        k = len(m.setdefault("autorizacoes", [])) + 1
        reg = {"n": k, "o_que": f"gerar até {a.n} imagens ({a.video})", "n_imagens": a.n, "portao": a.portao,
               "video": a.video, "data": agora(), "palavra": a.palavra}
        m["autorizacoes"].append(reg)
        # autorização nova SOMA à anterior do mesmo vídeo: a trava (V53b) compara com o total e com a PRIMEIRA data,
        # senão o que foi gerado com a primeira palavra do usuário passaria a contar como "gerado antes"
        arq = Path(projeto) / "motion" / a.video / "07_assets" / ".autorizado.json"
        ant = ler_json(arq) or {}
        if ant:
            hist = ant.get("historico") or [{k_: ant[k_] for k_ in ("n", "n_imagens", "data", "palavra") if k_ in ant}]
            reg_arq = {**ant, "n_imagens": int(ant.get("n_imagens", 0)) + a.n, "historico": hist + [reg],
                       "o_que": f"gerar até {int(ant.get('n_imagens', 0)) + a.n} imagens ({a.video}) em {len(hist) + 1} autorizações"}
        else:
            reg_arq = reg
        gravar_json(arq, reg_arq)
        salvar(projeto, m)
        diario(projeto, "RESPOSTA", f"autorizou {a.n} imagens para {a.video}: \"{a.palavra}\"", quem="usuário")
        print(f"✓ autorização #{k}: {a.n} imagens para {a.video} (total autorizado: {reg_arq['n_imagens']})")
        return 0
    if cmd == "diario":
        ap = argparse.ArgumentParser(prog="di diario")
        ap.add_argument("--tipo", required=True, choices=["DECISAO", "DECISÃO", "RESPOSTA", "TENTATIVA", "NOTA"])
        ap.add_argument("--texto", required=True)
        ap.add_argument("--quem", default="Editor")
        ap.add_argument("--projeto")
        a = ap.parse_args(argv)
        n = diario(achar_projeto(a.projeto), a.tipo.replace("DECISAO", "DECISÃO"), a.texto, a.quem)
        print(f"✓ DIARIO #{n}")
        return 0
    ap = argparse.ArgumentParser(prog="di portao")
    ap.add_argument("acao", choices=["status", "pode-avancar", "abrir-tentativa", "fechar", "responder",
                                     "pendencia", "confirmar", "proximo", "decidir-vendo"])
    ap.add_argument("alvo", nargs="?", help="F<N>, texto do próximo passo, ou número da pendência")
    ap.add_argument("--o-que-mudou")
    ap.add_argument("--reprovado-por", choices=["diretor", "leigo", "verificador", "usuario"])
    ap.add_argument("--autorizado-usuario", help="depois de escalada: a palavra literal do usuário que autorizou a tentativa")
    ap.add_argument("--aprovado-por", choices=["usuario", "interno"])
    ap.add_argument("--palavra")
    ap.add_argument("--video")
    ap.add_argument("--pergunta")
    ap.add_argument("--resposta")
    ap.add_argument("--chave")
    ap.add_argument("--escuta", choices=["humana"])
    ap.add_argument("--so-projeto", action="store_true",
                    help="com --chave saida|regua.*: vale só para este projeto (não grava na régua do usuário)")
    ap.add_argument("--o-que")
    ap.add_argument("--valor")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    fase = (a.alvo or "").upper() if a.acao in ("pode-avancar", "abrir-tentativa", "fechar") else None
    if a.acao == "pode-avancar" and not a.alvo:
        fase = proxima(carregar(projeto).get("fase_atual", "F0")) or "F7"
    if a.acao == "fechar" and not a.alvo:
        fase = carregar(projeto).get("fase_atual", "F0")
    if fase is not None and fase not in FASES:
        raise DIError(f"fase inválida: {a.alvo!r} (use F0…F7)")
    if a.acao == "status":
        return cmd_status(projeto)
    if a.acao == "pode-avancar":
        return cmd_pode(projeto, fase)
    if a.acao == "abrir-tentativa":
        return cmd_abrir(projeto, fase, a.o_que_mudou or "", a.reprovado_por, a.video, a.autorizado_usuario)
    if a.acao == "fechar":
        if not a.aprovado_por:
            raise DIError("fechar exige --aprovado-por usuario|interno")
        return cmd_fechar(projeto, fase, a.aprovado_por, a.palavra, a.video)
    if a.acao == "responder":
        if not (a.pergunta and a.resposta is not None):
            raise DIError("responder exige --pergunta e --resposta (literal)")
        return cmd_responder(projeto, a)
    m = carregar(projeto)
    if a.acao == "pendencia":
        n = len(m.setdefault("pendencias", [])) + 1
        m["pendencias"].append({"n": n, "o_que": a.o_que or a.alvo, "estado": "aberta", "data": agora()})
        salvar(projeto, m)
        print(f"✓ pendência #{n}")
        return 0
    if a.acao == "confirmar":
        n = int(a.alvo)
        if not a.valor:
            raise DIError("confirmar exige --valor com o que o usuário confirmou (\"ouvido → certo; …\" vira correção do texto)")
        achou = False
        for p in m.get("pendencias", []):
            if p["n"] == n:
                p.update(estado="confirmada", valor=a.valor, data_confirmacao=agora())
                achou = True
        if not achou:
            raise DIError(f"pendência #{n} não existe")
        pares = pares_da_confirmacao(a.valor)
        cor = [c for c in m.get("correcoes") or [] if c.get("pendencia") != n]
        cor += [{"ouvido": x, "certo": y, "pendencia": n, "data": agora()} for x, y in pares]
        m["correcoes"] = cor
        salvar(projeto, m)
        diario(projeto, "RESPOSTA", f"pendência #{n} confirmada: {a.valor}", quem="usuário")
        print(f"✓ pendência #{n} confirmada: {a.valor}" + (f" · {len(pares)} correção(ões) no texto (refaça di exportar)" if pares else ""))
        return 0
    if a.acao == "decidir-vendo":
        k = (a.alvo or "").replace("regua.", "")
        if k not in REGUA:
            raise DIError(f"decidir-vendo exige um item da régua: {', '.join(REGUA)}")
        if k in (m.get("decisoes_travadas") or {}):
            raise DIError(f"{k} já tem resposta do usuário: não se decide vendo o que ele respondeu")
        if not a.o_que:
            raise DIError("decidir-vendo exige --o-que com o motivo (ex.: 'o usuário não respondeu; o piloto sai nas duas')")
        m.setdefault("decidir_vendo", [])
        if k not in m["decidir_vendo"]:
            m["decidir_vendo"].append(k)
        salvar(projeto, m)
        diario(projeto, "DECISÃO", f"régua.{k} sem resposta do usuário → o piloto de motion sai nas duas versões, lado a lado, para ele escolher vendo. {a.o_que}")
        print(f"✓ {k}: decidir vendo no piloto (decisão do Editor, no DIARIO)")
        return 0
    if a.acao == "proximo":
        m["proximo_passo"] = a.alvo
        salvar(projeto, m)
        print("✓ próximo passo gravado")
        return 0
    return 1
