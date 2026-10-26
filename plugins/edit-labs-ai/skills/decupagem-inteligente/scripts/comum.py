"""Utilidades comuns da decupagem-inteligente.

Caminhos, manifest (`run-manifest.json`, a única verdade do estado), achar o projeto,
jobs desanexados, registro do Verificador, diário e normalização de texto.
Nada aqui decide nada: só lê, grava e mede.
"""
from __future__ import annotations

import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("DI_ROOT") or Path(__file__).resolve().parent.parent)   # <plugin>/skills/decupagem-inteligente
PLUGIN_ROOT = ROOT.parent.parent                                                    # <plugin>
MEMORIA = ROOT / "memoria"                     # MODELOS (vêm com o plugin; nunca se grava aqui)
# Dados do usuário ficam fora do plugin (sobrevivem a atualização): ~/.local/share/edit-labs-ai/decupagem-inteligente/
EDITLABS_DATA = Path(os.environ.get("EDITLABS_DATA") or (Path.home() / ".local" / "share" / "edit-labs-ai"))
DADOS = EDITLABS_DATA / "decupagem-inteligente"
PROJETOS = DADOS / "projetos.json"             # lista de projetos (escrita por di preparar e di portao)
REGUA_USUARIO = DADOS / "regua.yaml"           # as respostas do usuário à régua; o modelo é memoria/regua.yaml
# skills irmãs, dentro do mesmo plugin
MOTION_VOX = Path(os.environ.get("DI_MOTION_VOX") or (PLUGIN_ROOT / "skills" / "motion-vox"))
CORTE_VIRAL = Path(os.environ.get("DI_CORTE_VIRAL") or (PLUGIN_ROOT / "skills" / "corte-viral"))
# biblioteca de efeitos sonoros do usuário (opcional): DI_SFX=/caminho/da/pasta
SFX_LIB = Path(os.environ["DI_SFX"]) if os.environ.get("DI_SFX") else None
MANIFEST = "run-manifest.json"


def pasta_finais(projeto: Path) -> Path:
    """Onde a entrega copia os masters: DI_FINAIS, se definida; senão <projeto>/FINAIS."""
    return Path(os.environ["DI_FINAIS"]).expanduser() if os.environ.get("DI_FINAIS") else Path(projeto) / "FINAIS"
FASES = ["F0", "F1", "F2", "F3", "F4", "F5", "F6", "F7"]
NOME_FASE = {"F0": "BRIEF", "F1": "LEITURA", "F2": "DECUPAGEM", "F3": "CORTE BASE",
             "F4": "PLANO", "F5": "RABISCOS", "F6": "MOTION", "F7": "MASTER"}


class DIError(Exception):
    """Erro com mensagem para o usuário (português, com o que fazer)."""


# ---------------------------------------------------------------- tempo e texto
def agora() -> str:
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def hora_curta(iso: str | None) -> str:
    if not iso:
        return "?"
    try:
        d = datetime.datetime.fromisoformat(iso)
        return d.strftime("%d/%m %H:%M")
    except ValueError:
        return iso


def mmss(t: float) -> str:
    t = max(0.0, float(t))
    m = int(t // 60)
    return f"{m:02d}:{t - 60 * m:04.1f}"


# hesitação pura: comparada em minúsculas COM acento ("é" verbo ≠ "eh" hesitação)
HESITACOES = {"eh", "ehh", "éh", "éé", "ééé", "hã", "hãã", "ha", "hum", "humm", "hmm", "ahn", "ã", "ah", "ahh"}
# viram hesitação só quando isoladas por silêncio dos dois lados (fillers.json)
HESITACOES_ISOLADAS = {"é", "né", "tipo", "assim"}
FILLERS_PUROS = HESITACOES  # compatibilidade


def limpa(w: str) -> str:
    """minúsculas, sem pontuação, COM acento."""
    return re.sub(r"[^\wà-ÿ]+", "", w.lower())


def eh_hesitacao(w: str) -> bool:
    return limpa(w) in HESITACOES


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_palavra(w: str) -> str:
    w = sem_acento(w.lower())
    return re.sub(r"[^\w]+", "", w)


def pares_da_confirmacao(txt: str) -> list[tuple[str, str]]:
    """"Cloud Code → Claude Code; Antropic → Anthropic" → [(ouvido, certo), …]. Aceita → e ->."""
    out = []
    for parte in re.split(r"[;\n]", txt or ""):
        m_ = re.match(r"\s*[«\"']?(.+?)[»\"']?\s*(?:→|->)\s*[«\"']?(.+?)[»\"']?\s*$", parte)
        if m_ and m_.group(1).strip() and m_.group(2).strip():
            out.append((m_.group(1).strip(), m_.group(2).strip()))
    return out


def aplicar_correcoes(pal: list[dict], correcoes: list[dict], intocaveis: set | None = None) -> list[dict]:
    """Troca, na lista de palavras {w,t,e,…} do corte, cada trecho ouvido pelo que o usuário confirmou.
    Compara sem acento, caixa e pontuação; mantém a pontuação final da palavra original; frase mais longa primeiro.
    Mesmo número de palavras: tempos 1:1. Número diferente: o trecho [t0, e] é dividido pelo tamanho de cada palavra."""
    pares = sorted(((c["ouvido"].split(), c["certo"].split()) for c in correcoes or [] if c.get("ouvido") and c.get("certo")),
                   key=lambda x: -len(x[0]))
    if not pares:
        return pal
    res, i = [], 0
    while i < len(pal):
        for ouv, cer in pares:
            n = len(ouv)
            trecho = pal[i:i + n]
            if len(trecho) == n and [norm_palavra(w["w"]) for w in trecho] == [norm_palavra(x) for x in ouv] and \
                    len({w.get("seg") for w in trecho}) == 1 and \
                    not any(w.get("i") in (intocaveis or set()) for w in trecho):
                # palavra com decisão escrita de NÃO trocar (ambiguas status confirmada apontando para ela mesma)
                # fica fora da correção: "Markdown" é a ferramenta em dois pontos e o formato num terceiro.
                pont = re.search(r"[^\w]*$", trecho[-1]["w"]).group(0)
                if len(cer) == n:
                    novos = [dict(w, w=c + (re.search(r"[^\w]*$", w["w"]).group(0) if not re.search(r"[^\w]$", c) else ""))
                             for w, c in zip(trecho, cer)]
                else:
                    t0, e1 = trecho[0]["t"], trecho[-1]["e"]
                    tot = sum(len(c) for c in cer) or 1
                    novos, acc = [], t0
                    for k, c in enumerate(cer):
                        fim = e1 if k == len(cer) - 1 else round(acc + (e1 - t0) * len(c) / tot, 3)
                        novos.append({**trecho[0], "w": c, "t": round(acc, 3), "e": fim})
                        acc = fim
                    if pont and not re.search(r"[^\w]$", cer[-1]):
                        novos[-1]["w"] += pont
                for w in novos:
                    w.pop("ambigua", None)
                    w.pop("sugerido", None)
                    w["confirmado"] = True
                res += novos
                i += n
                break
        else:
            res.append(pal[i])
            i += 1
    return res


def norm_texto(palavras: list[str], tirar_fillers: bool = True) -> list[str]:
    out = []
    for w in palavras:
        n = norm_palavra(w)
        if not n or (tirar_fillers and eh_hesitacao(w)):
            continue
        out.append(n)
    return out


# ---------------------------------------------------------------- json
def ler_json(p: Path | str, padrao=None):
    p = Path(p)
    if not p.exists():
        return padrao
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def gravar_json(p: Path | str, obj, indent: int | None = 1) -> Path:
    """Grava em temporário e renomeia: chat morto no meio nunca deixa arquivo pela metade."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    # temporário com nome próprio por processo: dois jobs gravando juntos nunca misturam o mesmo .tmp
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=p.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)
        f.write("\n")
    os.replace(tmp, p)
    return p


_TRAVA: dict = {"n": 0, "f": None}


@contextlib.contextmanager
def trava_manifest(projeto: Path):
    """Trava exclusiva (flock) em volta de ler→mudar→gravar o manifest: job que termina enquanto outro começa não
    apaga a mudança do outro. Reentrante no mesmo processo."""
    if _TRAVA["n"] == 0:
        f = open(Path(projeto) / ".manifest.lock", "a")
        fcntl.flock(f, fcntl.LOCK_EX)
        _TRAVA["f"] = f
    _TRAVA["n"] += 1
    try:
        yield
    finally:
        _TRAVA["n"] -= 1
        if _TRAVA["n"] == 0:
            fcntl.flock(_TRAVA["f"], fcntl.LOCK_UN)
            _TRAVA["f"].close()
            _TRAVA["f"] = None


def gravar_texto(p: Path | str, texto: str) -> Path:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(texto, encoding="utf-8")
    os.replace(tmp, p)
    return p


def sha256_arquivo(p: Path, parcial: bool = False) -> str:
    """sha256; `parcial` = tamanho + primeiros e últimos 8 MB (bruto de 7 GB)."""
    h = hashlib.sha256()
    p = Path(p)
    with open(p, "rb") as f:
        if parcial and p.stat().st_size > 32 * 2**20:
            h.update(str(p.stat().st_size).encode())
            h.update(f.read(8 * 2**20))
            f.seek(-8 * 2**20, os.SEEK_END)
            h.update(f.read(8 * 2**20))
        else:
            for bloco in iter(lambda: f.read(2**20), b""):
                h.update(bloco)
    return ("parcial:" if parcial else "") + h.hexdigest()


# ---------------------------------------------------------------- projeto e manifest
def achar_projeto(arg: str | None = None) -> Path:
    """--projeto > pasta atual (ou acima) com manifest > memoria/projetos.json."""
    if arg:
        p = Path(arg).expanduser().resolve()
        if (p / MANIFEST).exists():
            return p
        raise DIError(f"não há {MANIFEST} em {p}")
    c = Path.cwd().resolve()
    for d in [c, *c.parents]:
        if (d / MANIFEST).exists():
            return d
    lst = (ler_json(PROJETOS, {}) or {}).get("projetos", [])
    ativos = [x for x in lst if x.get("estado") != "entregue" and Path(x["caminho"], MANIFEST).exists()]
    if len(ativos) == 1:
        return Path(ativos[0]["caminho"])
    if not ativos:
        raise DIError("nenhum projeto ativo. Comece com: di preparar <caminho do bruto>")
    ativos.sort(key=lambda x: x.get("data", ""), reverse=True)
    linhas = "\n".join(f"  {x['caminho']}  ·  {x.get('fase', '?')}  ·  {hora_curta(x.get('data'))}"
                       for x in ativos[:3])
    raise DIError("há mais de um projeto ativo. Qual? (use --projeto)\n" + linhas)


def carregar(projeto: Path) -> dict:
    m = ler_json(Path(projeto) / MANIFEST)
    if m is None:
        raise DIError(f"manifest ausente em {projeto}")
    return m


def salvar(projeto: Path, m: dict, estado: bool = True) -> None:
    m["updated_at"] = agora()
    gravar_json(Path(projeto) / MANIFEST, m)
    registrar_projeto(projeto, m)
    if estado:
        import estado as _estado  # import tardio: estado importa comum
        _estado.gerar(projeto, m)


def registrar_projeto(projeto: Path, m: dict) -> None:
    d = ler_json(PROJETOS, {"projetos": []}) or {"projetos": []}
    lst = [x for x in d.get("projetos", []) if x.get("caminho") != str(projeto)]
    fase = m.get("fase_atual", "F0")
    entregue = m.get("fases", {}).get("F7", {}).get("veredito") in ("APROVADO", "APROVADO_COM_CORRECAO")
    lst.append({"caminho": str(projeto), "bruto": m.get("inputs", {}).get("bruto"),
                "fase": f"{fase} {NOME_FASE.get(fase, '')}".strip(), "data": agora(),
                "host": m.get("host"), "estado": "entregue" if entregue else "ativo"})
    gravar_json(PROJETOS, {"projetos": lst})


def fase_info(m: dict, fase: str) -> dict:
    return m.setdefault("fases", {}).setdefault(fase, {"veredito": None, "tentativas": [], "laudos": []})


def tentativa_atual(m: dict, fase: str) -> int:
    ts = fase_info(m, fase).get("tentativas", [])
    return ts[-1]["t"] if ts else 1


def videos_da_tentativa(x: dict) -> list[str]:
    """Vídeos a que uma tentativa se restringe ([] = vale para todos)."""
    return list(x.get("videos") or ([x["video"]] if x.get("video") else []))


def vale_para(x: dict, vid: str) -> bool:
    vs = videos_da_tentativa(x)
    return not vs or vid in vs


def fase_fechada(m: dict, fase: str) -> bool:
    return fase_info(m, fase).get("veredito") in ("APROVADO", "APROVADO_COM_CORRECAO")


def config(projeto: Path) -> dict:
    import yaml
    p = Path(projeto) / "config.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def gravar_config(projeto: Path, cfg: dict) -> None:
    import yaml
    cab = "# Régua do projeto. Campos de motion ficam SEM valor até o usuário responder (ou herdar da régua dele).\n"
    gravar_texto(Path(projeto) / "config.yaml", cab + yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False))


def ids_videos(projeto: Path) -> list[str]:
    d = Path(projeto) / "02_decupagem"
    return sorted(p.name for p in d.iterdir() if p.is_dir() and re.match(r"^\d\d-", p.name)) if d.exists() else []


# ---------------------------------------------------------------- diário
def diario(projeto: Path, tipo: str, texto: str, quem: str = "skill") -> int:
    p = Path(projeto) / "DIARIO.md"
    atual = p.read_text(encoding="utf-8") if p.exists() else "# DIÁRIO\n\nDECISÃO · RESPOSTA · TENTATIVA · NOTA — numeradas, só acrescentadas.\n"
    n = len(re.findall(r"^## #\d+", atual, flags=re.M)) + 1
    atual = atual.rstrip("\n") + f"\n\n## #{n} {tipo.upper()} ({quem}, {hora_curta(agora())})\n{texto.strip()}\n"
    gravar_texto(p, atual)
    return n


# ---------------------------------------------------------------- jobs desanexados
def _vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def jobs_atualizar(m: dict) -> bool:
    """Job `rodando` cujo processo morreu vira `erro`. Devolve True se mudou algo."""
    mudou = False
    for nome, j in m.get("jobs", {}).items():
        if j.get("status") == "rodando" and j.get("pid") and not _vivo(int(j["pid"])):
            j["status"] = "erro"
            j["nota"] = "o processo terminou sem marcar ok; ver o log"
            mudou = True
    return mudou


def lancar_job(projeto: Path, nome: str, argv: list[str]) -> int:
    """Roda `di <argv>` em segundo plano (nohup), log em 00_fonte/_log/<nome>.log."""
    projeto = Path(projeto)
    log = projeto / "00_fonte" / "_log" / f"{nome}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DI_ROOT=str(ROOT), PYTHONPATH=str(ROOT / "scripts"), DI_JOB=nome)
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n===== {agora()} di {' '.join(argv)}\n")
        f.flush()
        p = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "di.py"), *argv, "--projeto", str(projeto)],
                             stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             cwd=str(projeto), env=env, start_new_session=True)
    with trava_manifest(projeto):
        m = carregar(projeto)
        m.setdefault("jobs", {})[nome] = {"pid": p.pid, "status": "rodando", "log": str(log.relative_to(projeto)),
                                          "inicio": agora(), "argv": argv}
        salvar(projeto, m)
    return p.pid


def job_marcar(projeto: Path, nome: str, status: str, **extra) -> None:
    with trava_manifest(projeto):
        m = carregar(projeto)
        j = m.setdefault("jobs", {}).setdefault(nome, {})
        j.update(status=status, fim=agora(), **extra)
        salvar(projeto, m)


def progresso(projeto: Path, etapa: str, pct: float | None = None, eta_s: float | None = None,
              status: str = "rodando") -> None:
    gravar_json(Path(projeto) / "01_transcript" / ".progresso.json",
                {"etapa": etapa, "pct": None if pct is None else round(100 * pct, 1),
                 "eta_s": None if eta_s is None else int(eta_s), "pid": os.getpid(),
                 "status": status, "atualizado": agora()}, indent=None)


# ---------------------------------------------------------------- Verificador
SEVS = ["BLOCKER", "HIGH", "MEDIUM", "LOW", "aviso", "info"]


def arquivo_verificador(projeto: Path, fase: str, t: int | None = None) -> Path:
    if t is None:
        t = tentativa_atual(carregar(projeto), fase)
    return Path(projeto) / "laudos" / f"{fase}_V_verificador_t{t}.json"


def registrar_checks(projeto: Path, fase: str, checks: list[dict], alvo: str | None = None,
                     t: int | None = None) -> dict:
    """Acrescenta/atualiza checagens no JSON do Verificador da fase (source: deterministic)."""
    p = arquivo_verificador(projeto, fase, t)
    d = ler_json(p, None)
    if d is None:
        d = {"schema": "di-verificacao/1", "source": "deterministic", "fase": fase,
             "alvo": alvo, "checks": [], "errors": [], "warnings": []}
        # tentativa nova: herda as checagens das etapas que não rodaram de novo (marcadas), a mais recente primeiro
        import glob as _g
        ants = sorted(_g.glob(str(Path(projeto) / "laudos" / f"{fase}_V_verificador_t*.json")),
                      key=lambda q: int(re.search(r"_t(\d+)\.json$", q).group(1)))
        if ants:
            prev = ler_json(Path(ants[-1]), None) or {}
            tk = re.search(r"_t(\d+)\.json$", ants[-1]).group(1)
            # tentativa de UM vídeo: esse vídeo é medido de novo, nada dele é herdado (só os intocados herdam)
            ts_ = fase_info(carregar(projeto), fase).get("tentativas") or []
            v_novos = set(videos_da_tentativa(ts_[-1])) if ts_ else set()
            # exceção: a checagem do render (V25) segue valendo se o render do vídeo é o do EDL atual (mesma assinatura)
            mesmo_render = set()
            for v_novo in (v_novos if fase == "F3" else ()):
                rj = ler_json(Path(projeto) / "03_corte" / v_novo / "render.json", None) or {}
                ej = ler_json(Path(projeto) / "02_decupagem" / v_novo / "edl.json", None)
                if ej and rj.get("edl_assinatura") == edl_assinatura(ej):
                    mesmo_render.add(v_novo)
            d["checks"] = [{**c, "herdado_de": c.get("herdado_de") or f"t{tk}"} for c in prev.get("checks", [])
                           if c.get("video") not in v_novos
                           or (c.get("video") in mesmo_render and c["id"] == "V25_duracao_concat")]
    chave = lambda c: (c["id"], c.get("video"), c.get("junta"))
    novos = {chave(c): c for c in checks}
    d["checks"] = [c for c in d["checks"] if chave(c) not in novos] + list(novos.values())
    d["checks"].sort(key=lambda c: (c["id"], str(c.get("video")), c.get("junta") or 0))
    d["valid"] = not any((not c.get("ok", True)) and c.get("severidade") == "BLOCKER" for c in d["checks"])
    d["atualizado"] = agora()
    if alvo:
        d["alvo"] = alvo
    if fase == "F3":  # o JSON da fase cobre todos os vídeos; cada check diz o seu
        d["alvo"] = "03_corte/<id>/ (um por vídeo; cada check tem `video`)"
    gravar_json(p, d)
    if fase == "F3":
        for v in sorted({c.get("video") for c in checks if c.get("video")}):
            _verificacao_md_do_video(Path(projeto), v, d, p)
    return d


def _verificacao_md_do_video(projeto: Path, vid: str, d: dict, origem: Path) -> None:
    """03_corte/<id>/VERIFICACAO.md = TODAS as checagens de F3 desse vídeo (render, verificação, exportação, pacote),
    tiradas do JSON da fase. Gerado só do JSON (V79), com data e tentativa."""
    pasta = projeto / "03_corte" / vid
    if not pasta.exists():
        return
    cs = [c for c in d.get("checks", []) if c.get("video") == vid]
    bl = any((not c.get("ok", True)) and c.get("severidade") == "BLOCKER" for c in cs)
    L = [f"# Verificação — F3 · {vid}", "",
         f"`source: deterministic` · válido: **{'NÃO' if bl else 'sim'}** · atualizado {d.get('atualizado')} · origem `{origem.relative_to(projeto)}`", "",
         "| id | saída | ok | severidade | medido | esperado | detalhe |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for c in cs:
        L.append(f"| {c['id']}{' (herdado ' + c['herdado_de'] + ')' if c.get('herdado_de') else ''} | {c.get('saida') or ''} | "
                 f"{'✓' if c.get('ok') else '✗'} | {c.get('severidade')} | {c.get('medido')} | {c.get('esperado') or ''} | {c.get('detalhe', '')} |")
    gravar_texto(pasta / "VERIFICACAO.md", "\n".join(L) + "\n\n<!-- gerado só a partir do JSON do Verificador (V79) -->\n")


def check(id_: str, ok: bool, severidade: str, medido=None, esperado=None, detalhe: str = "", **extra) -> dict:
    c = {"id": id_, "ok": bool(ok), "severidade": severidade, "medido": medido, "esperado": esperado}
    if detalhe:
        c["detalhe"] = detalhe
    c.update(extra)
    return c


def falhas(checks: list[dict], sev: str | None = None) -> list[dict]:
    return [c for c in checks if not c.get("ok", True) and (sev is None or c.get("severidade") == sev)]


# ---------------------------------------------------------------- mídia
def ffprobe(p: Path | str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def rodar(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def validar_schema(nome: str, obj, onde: str = "") -> None:
    """Valida contra schemas/<nome>.schema.json. Erro vira DIError em português, com o caminho do campo."""
    try:
        import jsonschema
    except Exception:
        return
    sch = json.loads((ROOT / "schemas" / f"{nome}.schema.json").read_text(encoding="utf-8"))
    erros = sorted(jsonschema.Draft202012Validator(sch).iter_errors(obj), key=lambda e: list(e.path))
    if erros:
        linhas = [f"  - {'/'.join(str(p) for p in e.path) or '(raiz)'}: {e.message}" for e in erros[:8]]
        raise DIError(f"{onde or nome} não passa no schema {nome}:\n" + "\n".join(linhas))


def edl_assinatura(edl: dict) -> str:
    """Assinatura do que o corte É (pontos, frames, escala, ganho), sem o crop que o render grava de volta."""
    base = [(round(s["source_in"], 3), round(s["source_out"], 3), s["frames"], s.get("escala"), s.get("ganho_db"))
            for s in edl.get("segmentos", [])]
    return hashlib.sha256(json.dumps(base).encode()).hexdigest()[:16]


REGUA_ITENS = ("densidade", "fim_de_cena", "motion_fps", "prints_oficiais")


def _yaml(p: Path) -> dict:
    import yaml
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


def regua_global() -> dict:
    """A régua que vale para todo projeto: o modelo (memoria/regua.yaml, com as perguntas e os padrões) coberto
    pelas respostas do usuário (REGUA_USUARIO). Item sem `literal` é pergunta em aberto: vai na pergunta única da F0/F3,
    uma vez. Item respondido nunca se pergunta de novo."""
    modelo, usu = _yaml(MEMORIA / "regua.yaml"), _yaml(REGUA_USUARIO)
    out = dict(modelo)
    for k, v in usu.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **{a: b for a, b in v.items() if b is not None}}
        elif v is not None:
            out[k] = v
    return out


def valor_da_resposta(k: str, resposta: str):
    """Resposta literal (a opção escolhida) → valor que o código usa. Sem casar, devolve o literal."""
    t = (resposta or "").strip().lower()
    if t in ("decidir vendo", "quero decidir vendo", "decidir_vendo"):
        return "decidir_vendo"
    if k == "saida":
        tem_v, tem_h = "vertical" in t or t == "v", "horizontal" in t or t == "h"
        return "ambas" if (tem_v and tem_h) or "duas" in t or "ambas" in t else ("V" if tem_v else ("H" if tem_h else resposta))
    if k == "motion_fps":
        m_ = re.search(r"\d+", t)
        return int(m_.group(0)) if m_ else resposta
    if k == "densidade":
        if any(x in t for x in ("padrão", "padrao", "doutrina", "65", "bastante", "alta")):
            return "doutrina_motion_vox"
        if "moderad" in t:
            return [0.35, 0.50]
        if "pouco" in t:
            return [0.15, 0.25]
        return resposta
    if k == "prints_oficiais":
        return "logos_nao" if t.startswith("não") or t.startswith("nao") else "logos_sim"
    if k == "fim_de_cena":
        return "sem_flash" if "sem" in t else ("flash" if "flash" in t else resposta)
    return resposta


def lembrar_resposta(k: str, literal: str, valor=None) -> Path:
    """Grava a resposta do usuário na régua dele (fora do plugin): o próximo projeto herda e não pergunta de novo."""
    import yaml
    d = _yaml(REGUA_USUARIO)
    d[k] = {"literal": literal, "valor": valor if valor is not None else valor_da_resposta(k, literal),
            "respondido_em": datetime.date.today().isoformat()}
    d["respondido_em"] = datetime.date.today().isoformat()
    cab = ("# Respostas do usuário à régua da decupagem-inteligente (gravadas por `di portao responder`).\n"
           "# Cobrem o modelo do plugin (skills/decupagem-inteligente/memoria/regua.yaml). Para mudar: responda de novo,\n"
           "# ou apague a linha do item para ele voltar a ser perguntado.\n")
    return gravar_texto(REGUA_USUARIO, cab + yaml.safe_dump(d, allow_unicode=True, sort_keys=False))


def valores_motion(rg: dict) -> dict:
    """Valores que o código usa (config.yaml: motion.*), tirados da régua. Sem resposta, fica sem valor."""
    out = {}
    fps = (rg.get("motion_fps") or {}).get("valor")
    if isinstance(fps, int) or (isinstance(fps, str) and fps.isdigit()):
        out["fps"] = int(fps)
    den = (rg.get("densidade") or {}).get("valor")
    if den == "doutrina_motion_vox":
        out["densidade_alvo"] = [0.65, 0.75]
    elif isinstance(den, (list, tuple)) and len(den) == 2:
        out["densidade_alvo"] = [float(den[0]), float(den[1])]
    pr = (rg.get("prints_oficiais") or {}).get("valor")
    if pr:
        out["logos_oficiais"] = pr in ("logos_sim", "sim", True)
    fim = (rg.get("fim_de_cena") or {}).get("valor")
    if fim:
        out["fim_de_cena"] = fim
    if rg.get("estilo"):
        out["estilo"] = [r["id"] for r in rg["estilo"].get("regras", [])]
    return out


def aplicar_regua(m: dict, cfg: dict, rg: dict | None = None) -> None:
    """Projeto novo herda a régua global: literal em decisoes_travadas, 'decidir vendo' em decidir_vendo, valores em cfg."""
    rg = rg if rg is not None else regua_global()
    if not rg:
        return
    dt = m.setdefault("decisoes_travadas", {})
    for k in REGUA_ITENS:
        it = rg.get(k) or {}
        if it.get("valor") == "decidir_vendo":
            if k not in m.setdefault("decidir_vendo", []):
                m["decidir_vendo"].append(k)
        elif it.get("literal"):
            dt.setdefault(k, it["literal"])
    cfg.setdefault("motion", {}).update({k: v for k, v in valores_motion(rg).items()})
    m.setdefault("regua_origem", f"régua do usuário ({REGUA_USUARIO.name}, respondida em {rg.get('respondido_em') or '—'})"
                 if REGUA_USUARIO.exists() else "modelo do plugin (memoria/regua.yaml), sem respostas ainda")
