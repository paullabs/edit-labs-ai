"""F0 BRIEF: cria o projeto a partir do bruto e lança a leitura (F1) desanexada.

  di preparar BRUTO [BRUTO2…] [--projeto PASTA] [--glossario "a, b"] [--saida V|H|ambas]
             [--modo portoes|ate_o_fim|so_corte] [--host claude|codex] [--gerador higgsfield|image_gen|nenhum]
             [--esperar N] [--sem-espera]

Nunca decodifica o vídeo: só ffprobe e extração do áudio. Transcript primeiro, vídeo por último.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from comum import (aplicar_regua, regua_global, DIError, agora, carregar, diario, ffprobe, gravar_config, gravar_json, gravar_texto, job_marcar,
                   lancar_job, ler_json, mmss, progresso, registrar_checks, check, salvar, sha256_arquivo, MANIFEST)

ESPERA_GLOSSARIO_S = 90


def _fps(s: str) -> tuple[int, int]:
    n, d = (s or "0/1").split("/")
    return int(n), int(d or 1)


def sonda(p: Path) -> dict:
    j = ffprobe(p)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    auds = [s for s in j["streams"] if s["codec_type"] == "audio"]
    if not v:
        raise DIError(f"{p.name} não tem faixa de vídeo")
    r, a = _fps(v.get("r_frame_rate")), _fps(v.get("avg_frame_rate"))
    w, h = int(v["width"]), int(v["height"])
    rot = int((v.get("tags") or {}).get("rotate", 0) or 0)
    if rot in (90, 270):
        w, h = h, w
    return {"path": str(p), "codec": v.get("codec_name"), "width": w, "height": h,
            "orientacao": "V" if h > w else "H", "fps": list(r), "r_frame_rate": v.get("r_frame_rate"),
            "avg_frame_rate": v.get("avg_frame_rate"), "cfr": r == a,
            "nb_frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
            "duracao": float(j["format"]["duration"]), "tamanho": int(j["format"]["size"]),
            "creation_time": (j["format"].get("tags") or {}).get("creation_time"),
            "audio": [{"index": s["index"], "codec": s.get("codec_name"), "canais": s.get("channels"),
                       "taxa": int(s.get("sample_rate", 0))} for s in auds]}


def sequencia(p: Path, info: dict) -> list[Path]:
    """CLIP0001 → CLIP0002 …: mesma câmera, mesmo codec/resolução/fps, creation_time contíguo."""
    m = re.match(r"^(.*?)(\d+)$", p.stem)
    if not m:
        return [p]
    pre, num = m.group(1), m.group(2)
    out, cur, ci = [p], int(num), info
    while True:
        cand = [x for x in p.parent.iterdir() if x.stem == f"{pre}{cur + 1:0{len(num)}d}" and x.suffix.lower() == p.suffix.lower()]
        if not cand:
            break
        nx = sonda(cand[0])
        if (nx["codec"], nx["width"], nx["height"], nx["fps"]) != (ci["codec"], ci["width"], ci["height"], ci["fps"]):
            break
        try:
            import datetime as dt
            t0 = dt.datetime.fromisoformat(ci["creation_time"].replace("Z", "+00:00"))
            t1 = dt.datetime.fromisoformat(nx["creation_time"].replace("Z", "+00:00"))
            if abs((t1 - t0).total_seconds() - ci["duracao"]) > 10:
                break
        except Exception:
            break
        out.append(cand[0])
        cur, ci = cur + 1, nx
    return out


def detectar_host() -> str:
    if any(k in os.environ for k in ("CODEX_SANDBOX", "CODEX_THREAD_ID", "CODEX_SESSION_ID")):
        return "codex"
    return "claude"


def preparar(a) -> Path:
    brutos = [Path(x).expanduser().resolve() for x in a.bruto]
    for b in brutos:
        if not b.exists():
            raise DIError(f"bruto não encontrado: {b}")
    info0 = sonda(brutos[0])
    if len(brutos) == 1:
        brutos = sequencia(brutos[0], info0)
    # o projeto nasce na pasta onde o usuário abriu o Claude Code (nunca dentro do plugin nem ao lado do bruto num disco externo)
    projeto = Path(a.projeto).expanduser().resolve() if a.projeto else Path.cwd().resolve() / f"{brutos[0].stem}-decupagem"
    if (projeto / MANIFEST).exists():
        print(f"projeto já existe: {projeto}\n(retomada: di status --projeto \"{projeto}\")")
        return projeto
    for d in ("00_fonte/_log", "01_transcript", "02_decupagem", "03_corte", "laudos/pacote-leigo", "entrega"):
        (projeto / d).mkdir(parents=True, exist_ok=True)
    fonte = projeto / "00_fonte" / "bruto.mp4"
    if len(brutos) == 1:
        if fonte.is_symlink() or fonte.exists():
            fonte.unlink()
        fonte.symlink_to(brutos[0])
    infos = [info0] + [sonda(b) for b in brutos[1:]]
    duracao = sum(i["duracao"] for i in infos)
    tipo = "podcast" if len(info0["audio"]) >= 2 else "solo"
    fonte_json = {**info0, "path": str(brutos[0]), "arquivos": [str(b) for b in brutos], "duracao": duracao,
                  "fingerprint": sha256_arquivo(brutos[0], parcial=True), "sequencia": len(brutos) > 1}
    gravar_json(projeto / "00_fonte" / "fonte.json", fonte_json)
    host = a.host or detectar_host()
    gerador = a.gerador or ("image_gen" if host == "codex" else "higgsfield")
    import yaml
    tpl = Path(__file__).resolve().parent.parent / "memoria" / "templates" / "config.yaml"
    cfg = yaml.safe_load(tpl.read_text(encoding="utf-8")) if tpl.exists() else {}
    cfg["saida"] = a.saida or cfg.get("saida")
    if info0["orientacao"] == "V":
        cfg["saida"], cfg["crop_vertical"] = "V", "none"
    cfg["pausa_max_s"] = 1.0 if tipo == "podcast" else 0.35
    rg = regua_global()
    if not cfg.get("saida") and (rg.get("saida") or {}).get("valor"):
        cfg["saida"] = rg["saida"]["valor"]  # respondido uma vez pelo usuário: não se pergunta de novo
    gravar_config(projeto, cfg)
    m = {"schema": "di-manifest/1", "run_id": f"{brutos[0].stem}-{time.strftime('%Y%m%d-%H%M%S')}",
         "projeto": brutos[0].stem, "created_at": agora(), "host": host, "modo": a.modo,
         "inputs": {"bruto": str(brutos[0]), "arquivos": [str(b) for b in brutos], "tipo": tipo,
                    "saida": cfg.get("saida"), "gerador": gerador},
         "videos": [], "fase_atual": "F0", "tentativa": 1, "fases": {}, "respostas": [], "autorizacoes": [],
         "pendencias": [], "decisoes_travadas": {}, "artefatos": [], "jobs": {}, "errors": [], "warnings": [],
         "proximo_passo": "F0: perguntar ao usuário saída e glossário (uma mensagem, os dois com padrão)"}
    aplicar_regua(m, cfg, rg)
    gravar_config(projeto, cfg)
    gravar_json(projeto / MANIFEST, m)
    for nome in ("DIARIO.md",):
        t = Path(__file__).resolve().parent.parent / "memoria" / "templates" / nome
        if t.exists() and not (projeto / nome).exists():
            shutil.copy(t, projeto / nome)
    if a.glossario:
        termos = [x.strip() for x in re.split(r"[,;\n]", a.glossario) if x.strip()]
        gravar_texto(projeto / "00_fonte" / "glossario.txt", "\n".join(termos) + "\n")
        gravar_texto(projeto / "00_fonte" / ".glossario_ok", agora())
    elif a.sem_espera:
        gravar_texto(projeto / "00_fonte" / ".glossario_ok", agora() + " (sem glossário)")
    salvar(projeto, m)
    diario(projeto, "DECISÃO", f"Projeto criado de {', '.join(b.name for b in brutos)} "
                               f"({mmss(duracao)}, {info0['width']}×{info0['height']}, {info0['fps'][0]}/{info0['fps'][1]} fps, "
                               f"{len(info0['audio'])} faixa(s) de áudio). Host {host}, gerador {gerador}, modo {a.modo}.")
    registrar_checks(projeto, "F1", [
        check("V07_cfr", info0["cfr"], "info", medido=f"{info0['r_frame_rate']} vs {info0['avg_frame_rate']}",
              esperado="iguais", detalhe="VFR não é falha: o render corta em CFR por segmento"),
        check("V07b_sequencia", True, "info", medido=len(brutos), detalhe="arquivos da mesma câmera em sequência"),
        check("V08_faixas", True, "info", medido=len(info0["audio"]),
              detalhe="2+ faixas ligam o caminho multitrack" if tipo == "podcast" else "1 faixa: solo até prova em contrário"),
    ], alvo="00_fonte/fonte.json")
    lancar_job(projeto, "leitura", ["_pipeline", "--inicio", str(time.time())])
    return projeto


def estimativa_min(duracao_s: float) -> float:
    try:
        import mlx_whisper  # noqa: F401
        return duracao_s / 60 * 0.15 + 0.5
    except Exception:
        return duracao_s / 60 * 0.6 + 1


def pipeline(projeto: Path, inicio: float) -> None:
    """Roda desanexado: áudio → silêncios → (espera glossário) → transcrição → retakes → digest."""
    import silencio, transcrever, retakes, digest  # noqa: E401
    fonte = ler_json(projeto / "00_fonte" / "fonte.json")
    try:
        wav = projeto / "00_fonte" / "_audio_16k.wav"
        if not wav.exists():
            progresso(projeto, "extraindo áudio", 0.0)
            arquivos = fonte["arquivos"]
            entrada = ["-i", arquivos[0]] if len(arquivos) == 1 else \
                ["-f", "concat", "-safe", "0", "-i", str(_lista_concat(projeto, arquivos))]
            subprocess.run(["ffmpeg", "-v", "error", "-y", *entrada, "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                            "-c:a", "pcm_s16le", str(wav) + ".tmp.wav"], check=True)
            os.replace(str(wav) + ".tmp.wav", wav)
        progresso(projeto, "medindo silêncios", 0.0)
        silencio.medir(projeto)
        ok = projeto / "00_fonte" / ".glossario_ok"
        while not ok.exists() and time.time() - inicio < ESPERA_GLOSSARIO_S:
            progresso(projeto, "esperando glossário (até 90 s)", None,
                      eta_s=ESPERA_GLOSSARIO_S - (time.time() - inicio))
            time.sleep(3)
        transcrever.transcrever_projeto(projeto)
        progresso(projeto, "realinhando palavras esticadas", 0.0)
        transcrever.realinhar(projeto)
        progresso(projeto, "medindo vãos e energia", 0.0)
        silencio.medir(projeto, com_palavras=True)
        progresso(projeto, "agrupando tomadas", 0.0)
        retakes.analisar(projeto)
        progresso(projeto, "escrevendo digest", 0.0)
        digest.escrever(projeto)
        progresso(projeto, "leitura pronta", 1.0, status="ok")
        m = carregar(projeto)
        m["fase_atual"] = "F1"
        m["proximo_passo"] = "F1: Editor lê 01_transcript/digest.md e escreve 02_decupagem/MAPA_DO_BRUTO.md; depois Diretor C1"
        salvar(projeto, m)
        job_marcar(projeto, "leitura", "ok")
    except Exception as e:  # o erro fica no log e no manifest; nunca some em silêncio
        import traceback
        traceback.print_exc()
        progresso(projeto, f"erro: {e}", None, status="erro")
        job_marcar(projeto, "leitura", "erro", nota=str(e)[:300])
        raise


def _lista_concat(projeto: Path, arquivos: list[str]) -> Path:
    p = projeto / "00_fonte" / "_concat.txt"
    gravar_texto(p, "".join(f"file '{x}'\n" for x in arquivos))
    return p


def esperar(projeto: Path, segundos: int) -> None:
    fim = time.time() + min(300, segundos)
    while time.time() < fim:
        j = carregar(projeto).get("jobs", {}).get("leitura", {})
        if j.get("status") in ("ok", "erro"):
            break
        time.sleep(5)


def main(cmd: str, argv: list[str]) -> int:
    if cmd == "_pipeline":
        ap = argparse.ArgumentParser()
        ap.add_argument("--inicio", type=float, default=time.time())
        ap.add_argument("--projeto", required=True)
        a = ap.parse_args(argv)
        pipeline(Path(a.projeto), a.inicio)
        return 0
    ap = argparse.ArgumentParser(prog="di preparar")
    ap.add_argument("bruto", nargs="+")
    ap.add_argument("--projeto")
    ap.add_argument("--glossario")
    ap.add_argument("--saida", choices=["V", "H", "ambas"])
    ap.add_argument("--modo", default="portoes", choices=["portoes", "ate_o_fim", "so_corte"])
    ap.add_argument("--host", choices=["claude", "codex"])
    ap.add_argument("--gerador", choices=["higgsfield", "image_gen", "nenhum"])
    ap.add_argument("--esperar", type=int, default=0)
    ap.add_argument("--sem-espera", action="store_true", help="não esperar 90 s pelo glossário")
    a = ap.parse_args(argv)
    t0 = time.time()
    projeto = preparar(a)
    f = ler_json(projeto / "00_fonte" / "fonte.json")
    m = carregar(projeto)
    print(f"Recebi {Path(f['path']).name}" + (f" (+{len(f['arquivos']) - 1} arquivo(s) em sequência)" if f.get("sequencia") else "")
          + f" · {mmss(f['duracao'])} · {f['width']}×{f['height']} · {f['fps'][0]}/{f['fps'][1]} fps"
          + f" · {len(f['audio'])} faixa(s) de áudio · {'CFR' if f['cfr'] else 'VFR'}")
    print(f"Projeto: {projeto}")
    print(f"Host: {m['host']} · gerador de imagem: {m['inputs']['gerador']} · modo: {m['modo']} · saída: {m['inputs'].get('saida') or 'a perguntar'}")
    print(f"Leitura lançada em segundo plano (~{estimativa_min(f['duracao']):.0f} min). Acompanhe: di status")
    if a.esperar:
        esperar(projeto, a.esperar)
        print(carregar(projeto)["jobs"]["leitura"]["status"])
    print(f"({time.time() - t0:.1f} s)")
    return 0
