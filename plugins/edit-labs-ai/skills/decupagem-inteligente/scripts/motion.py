"""F4–F7: orquestra a motion-vox. Nada do kit é copiado para a skill; o projeto de motion é um projeto
motion-vox PADRÃO em motion/<id>/, criado a partir do corte aprovado.

  di iniciar-motion <id>                                  monta motion/<id>/ ("Começar um projeto" da motion-vox)
  di mv <id> [--saida V|H] [--agora] <script> [args]      roda um script da motion-vox dentro do projeto
  di mv <id> --sync                                       ressincroniza lib da motion-vox (plugin) → projeto (nunca o contrário)
  di verificar-plano <id>                                 V43–V52 + as regras de estilo do usuário (E1–E9)
  di verificar-motion <id> [--saida V|H] --trecho t0 t1 | --master
  di entregar <id>                                        FINAIS + RESUMO.md

O interpretador da motion-vox é fixo (`motion_vox_python`); a lib do projeto é sincronizada por hash antes de
qualquer comando; `cutout.py`, `prancha.py` e `render.py --frames` recusam PNG gerado sem autorização (V53b);
cena renderizada ganha `.done` só com a contagem de quadros certa (V67b) e o mux recusa cena sem `.done`.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from comum import (MOTION_VOX, DIError, achar_projeto, agora, carregar, config, diario, ffprobe, gravar_json,
                   gravar_texto, job_marcar, lancar_job, ler_json, salvar)

PASTAS = ["00_brief", "05_motion", "06_transitions", "07_assets/raw", "07_assets/cutout", "07_assets/qa", "07_assets/sfx",
          "08_images/frames", "09_plates", "10_sequences", "11_qa", "12_master"]
DO_PROJETO = {"compose.py", "render.py"}          # o projeto é dono destes; a sync nunca os toca
TRAVADOS = {"cutout.py", "prancha.py"}             # + render.py --frames: recusam PNG gerado sem autorização


def motion_vox_python() -> str:
    from instalar import motion_vox_python as mvp
    return mvp()   # o Python do venv-motion do Edit Labs AI (MV_PY)


def pasta_motion(projeto: Path, vid: str) -> Path:
    return Path(projeto) / "motion" / vid


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def conferir_kit() -> None:
    lib, assets = MOTION_VOX / "lib", MOTION_VOX / "assets"
    falta = [x for x in ("voxlab.py", "kit.py", "captions.py", "cutout.py", "render_template.py", "compose_template.py")
             if not (lib / x).exists()]
    pngs, npys = list(assets.glob("*.png")), list(assets.glob("*.npy"))
    if falta or len(pngs) < 16 or not npys or not (MOTION_VOX / "fontes").exists():
        raise DIError(f"motion-vox incompleta em {MOTION_VOX}: faltam {falta or ''} · {len(pngs)} PNG · {len(npys)} npy. "
                      "Atualize o plugin Edit Labs AI e rode editlabs-setup antes de começar o motion.")


# ------------------------------------------------------------------ iniciar-motion
def iniciar(projeto: Path, vid: str) -> Path:
    projeto = Path(projeto).resolve()
    if not os.environ.get("DI_JOB"):
        from portao import cmd_pode
        if cmd_pode(projeto, "F4") != 0:
            raise DIError("o motion não começa: F3 sem a palavra do usuário ou régua incompleta (di portao pode-avancar F4)")
    conferir_kit()
    corte = projeto / "03_corte" / vid
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
    if not edl or not (corte / "palavras_corte.json").exists():
        raise DIError(f"{vid}: falta o pacote do corte (di exportar {vid} --motion-vox)")
    mp = pasta_motion(projeto, vid)
    novo = not mp.exists()
    for d in PASTAS:
        (mp / d).mkdir(parents=True, exist_ok=True)
    for py in (MOTION_VOX / "lib").glob("*.py"):
        if py.name not in DO_PROJETO:
            shutil.copy2(py, mp / py.name)
    if not (mp / "fontes").exists():
        shutil.copytree(MOTION_VOX / "fontes", mp / "fontes")
    for a in list((MOTION_VOX / "assets").glob("*.png")) + list((MOTION_VOX / "assets").glob("*.npy")):
        dst = mp / "07_assets" / ("raw" if a.name == "BG_PAPER.png" else "cutout") / a.name
        if not dst.exists():
            shutil.copy2(a, dst)
    if not (mp / "compose.py").exists():
        shutil.copy2(MOTION_VOX / "lib" / "compose_template.py", mp / "compose.py")
    b = mp / "00_brief"
    saidas = [s for s in ("V", "H") if (corte / f"corte_v01_{s}.mp4").exists()]
    if not saidas:
        raise DIError(f"{vid}: nenhum corte_v01_V/H.mp4 em 03_corte/{vid}/")
    quadro = {"V": (1080, 1920), "H": (1920, 1080)}   # o quadro do kit; o corte H pode ter saído em 4K
    for s in saidas:
        src, dst = corte / f"corte_v01_{s}.mp4", b / f"fonte_{s}.mp4"
        marca = b / f".fonte_{s}.origem"
        if dst.exists() and marca.exists() and marca.read_text().strip() == _sha(src):
            continue
        vs_ = next(x for x in ffprobe(src)["streams"] if x["codec_type"] == "video")
        if (int(vs_["width"]), int(vs_["height"])) == quadro[s]:
            shutil.copy2(src, dst)
        else:   # reduz para o quadro do kit (lanczos), áudio intocado
            w_, h_ = quadro[s]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale={w_}:{h_}:flags=lanczos,setsar=1",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy",
                            "-movflags", "+faststart", str(dst)], check=True)
        marca.write_text(_sha(src))
    shutil.copy2(corte / "palavras_corte.json", b / "transcript_palavras.json")
    for nome in ("cortes.json", "momentos.json", "avisos.json"):
        if (corte / nome).exists():
            shutil.copy2(corte / nome, b / nome)
    gravar_json(b / "edl.json", edl)
    # silêncios MEDIDOS no próprio corte: o t1 de cada cutaway cai dentro de um deles (ancorar.py)
    import silencio as SIL
    wav = b / ".audio_16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(b / f"fonte_{saidas[0]}.mp4"), "-ac", "1", "-ar", "16000",
                    str(wav)], check=True)
    x, sr = SIL.carregar_wav(wav)
    lim = (ler_json(projeto / "01_transcript" / "silencios.json") or {}).get("limiar_db", -40.0)
    gravar_json(b / "silencios_corte.json", {"limiar_db": lim, "relogio": "corte", "silencios": SIL.silencios(x, sr, lim, 0.12)})
    wav.unlink()
    info = ffprobe(b / f"fonte_{saidas[0]}.mp4")
    vs = next(s_ for s_ in info["streams"] if s_["codec_type"] == "video")
    fnum, fden = (int(v) for v in vs["r_frame_rate"].split("/"))
    dur = float(info["format"]["duration"])
    cortes = (ler_json(b / "cortes.json") or {}).get("cortes", [])
    mot = config(projeto).get("motion") or {}
    mfps = int(mot.get("fps") or 16)
    if not (mp / "render.py").exists():   # depois de criado, o render.py é do projeto
        t = (MOTION_VOX / "lib" / "render_template.py").read_text(encoding="utf-8")
        t = re.sub(r"^DUR = [0-9.]+.*$", f"DUR = {dur:.4f}                              # medido por iniciar_motion.py", t, 1, re.M)
        t = re.sub(r"^FPS_NUM, FPS_DEN = .*$", f"FPS_NUM, FPS_DEN = {fnum}, {fden}             # medido por iniciar_motion.py", t, 1, re.M)
        t = t.replace("    cortes=[],         # todo corte seco do proprio clipe",
                      f"    cortes={json.dumps(cortes)},   # emendas do corte (cortes.json) — nunca à mão")
        t = re.sub(r"^MOTION_FPS = 16$", f"MOTION_FPS = {mfps}          # régua do usuário (decupagem-inteligente)", t, 1, re.M)
        t = re.sub(r"^EXIT_KIND = \{.*?\}\n(?=ENTRY_KIND)", "EXIT_KIND = {}          # da coluna 'Fim de cena' do plano\n", t, 1, re.S | re.M)
        t = re.sub(r"^SHOTS = \[.*?^\]\n", "SHOTS = []          # nasce da tabela B do PLANO_MOTION.md\n", t, 1, re.S | re.M)
        (mp / "render.py").write_text(t, encoding="utf-8")
    md5 = {s: subprocess.run(["ffmpeg", "-v", "error", "-i", str(b / f"fonte_{s}.mp4"), "-map", "0:a", "-f", "md5", "-"],
                             capture_output=True, text=True).stdout.strip() for s in saidas}
    gravar_texto(b / "FONTE.md", "\n".join([
        f"# FONTE — {vid}", "",
        f"- duração: {dur:.4f} s · {fnum}/{fden} fps · {int(round(dur * fnum / fden))} quadros",
        *[f"- fonte_{s}.mp4: {'1080×1920' if s == 'V' else '1920×1080'} · áudio {md5[s]}" for s in saidas],
        f"- régua: MOTION_FPS {mfps} · densidade {mot.get('densidade_alvo')} · fim de cena {mot.get('fim_de_cena')} · "
        f"logos oficiais {mot.get('logos_oficiais')} · estilo {', '.join(mot.get('estilo') or [])}",
        f"- interpretador: {motion_vox_python()}",
        f"- criado por di iniciar-motion em {agora()}", ""]))
    m = carregar(projeto)
    m.setdefault("motion", {})[vid] = {"pasta": str(mp.relative_to(projeto)), "saidas": saidas, "criado": agora()}
    salvar(projeto, m)
    diario(projeto, "NOTA", f"motion/{vid}/ {'criado' if novo else 'atualizado'}: saídas {'+'.join(saidas)}, "
                            f"{dur:.2f} s, MOTION_FPS {mfps}, {len(cortes)} emendas.")
    return mp


# ------------------------------------------------------------------ di mv
def sync(projeto: Path, vid: str) -> list[str]:
    """lib global → projeto, por hash; compose.py e render.py são do projeto."""
    mp = pasta_motion(projeto, vid)
    trocados = []
    for py in (MOTION_VOX / "lib").glob("*.py"):
        if py.name in DO_PROJETO:
            continue
        dst = mp / py.name
        if not dst.exists() or _sha(dst) != _sha(py):
            shutil.copy2(py, dst)
            trocados.append(py.name)
    if trocados:
        diario(projeto, "NOTA", f"motion/{vid}: lib sincronizada da motion-vox global: {', '.join(trocados)}")
    return trocados


def trava_credito(projeto: Path, vid: str) -> None:
    """V53b: PNG gerado em 07_assets/raw/ antes da autorização, ou além de N → recusa."""
    mp = pasta_motion(projeto, vid)
    kit = {a.name for a in (MOTION_VOX / "assets").glob("*.png")}
    reais = set((ler_json(mp / "07_assets" / "reais.json") or {}).get("arquivos", []))   # foto/logo real, com licença
    gerados = [p for p in (mp / "07_assets" / "raw").glob("*.png") if p.name not in kit and p.name not in reais]
    if not gerados:
        return
    aut = ler_json(mp / "07_assets" / ".autorizado.json")
    if not aut:
        raise DIError(f"{len(gerados)} imagem(ns) gerada(s) em 07_assets/raw/ sem autorização do usuário "
                      f"(di autorizar-imagens N --portao F4 --video {vid})")
    t_aut = _dt.datetime.fromisoformat(aut["data"]).timestamp()
    antes = [p.name for p in gerados if p.stat().st_mtime < t_aut - 60]
    if antes:
        raise DIError(f"imagem gerada ANTES da autorização: {', '.join(antes[:5])}")
    n_aut = int(aut.get("n_imagens", aut.get("n", 0)))   # `n` é o número da autorização; a quantidade é n_imagens
    if len(gerados) > n_aut:
        raise DIError(f"{len(gerados)} imagens geradas, autorização para {n_aut}: peça ao usuário antes de seguir")


def _shots(projeto: Path, vid: str, saida: str):
    mp = pasta_motion(projeto, vid)
    code = ("import json,render as R;print(json.dumps([[n,t0,t1,op] for n,_,t0,t1,_,op in R.SHOTS]));"
            "print(R.FPS_NUM, R.FPS_DEN)")
    r = subprocess.run([motion_vox_python(), "-c", code], cwd=mp, capture_output=True, text=True,
                       env={**os.environ, "MV_CANVAS": saida})
    if r.returncode != 0:
        raise DIError(f"render.py não importa: {r.stderr.strip()[-400:]}")
    linhas = r.stdout.strip().splitlines()
    return json.loads(linhas[-2]), tuple(int(v) for v in linhas[-1].split())


def marcar_done(projeto: Path, vid: str, saida: str, nomes: list[str]) -> list[str]:
    """V67b: cena com a contagem de PNG certa ganha .done com hash; a retomada re-renderiza o resto."""
    mp = pasta_motion(projeto, vid)
    shots, (fn, fd) = _shots(projeto, vid, saida)
    faltas = []
    for n, t0, t1, _ in shots:
        if nomes and n not in nomes:
            continue
        d = mp / "10_sequences" / saida / n
        esp = int(round((t1 - t0) * fn / fd))
        pngs = sorted(d.glob("*.png")) if d.exists() else []
        if esp > 0 and len(pngs) == esp:
            h = hashlib.sha256()
            for p in (pngs[0], pngs[len(pngs) // 2], pngs[-1]):
                h.update(p.read_bytes())
            gravar_json(d / ".done", {"frames": esp, "hash": h.hexdigest()[:16], "data": agora()})
        else:
            if d.exists():
                (d / ".done").unlink(missing_ok=True)
            faltas.append(f"{n}: {len(pngs)}/{esp} quadros")
    return faltas


def mux_pronto(projeto: Path, vid: str, saida: str) -> list[str]:
    mp = pasta_motion(projeto, vid)
    shots, _ = _shots(projeto, vid, saida)
    return [n for n, *_ in shots if not (mp / "10_sequences" / saida / n / ".done").exists()]


def mv(projeto: Path, vid: str, saida: str, script: str, args: list[str], agora_: bool, fim: str = "") -> int:
    mp = pasta_motion(projeto, vid)
    if not mp.exists():
        raise DIError(f"motion/{vid}/ não existe (di iniciar-motion {vid})")
    sync(projeto, vid)
    from verificar_plano import pares_pendentes     # palavra em dúvida nunca vira legenda (janelas_legenda.py)
    gravar_json(mp / "00_brief" / "pendentes.json", pares_pendentes(carregar(projeto)))
    if script in TRAVADOS or (script == "render.py" and ("--frames" in args or "--janela" in args or not args)):
        trava_credito(projeto, vid)
    if script == "render.py" and "--mux" in args:
        sem = mux_pronto(projeto, vid, saida)
        if sem:
            raise DIError(f"mux recusado: cena sem .done ({', '.join(sem)}) — renderize de novo só essas")
    job = os.environ.get("DI_JOB")
    if script in ("render.py", "verificar_motion.py") and not agora_ and not job:
        nome = f"mv_{vid}_{saida}_{script.replace('.py', '')}"
        nome += f"_{fim}" if fim else ""
        lancar_job(projeto, nome, ["mv", vid, "--saida", saida, "--agora", *(["--fim", fim] if fim else []), script, *args])
        print(f"rodando em segundo plano ({nome}); acompanhe com di portao status")
        return 0
    r = subprocess.run([motion_vox_python(), script, *args], cwd=mp, env={**os.environ, "MV_CANVAS": saida, "MV_FIM": fim})
    rc = r.returncode
    if script == "render.py" and rc == 0 and "--mux" not in args and "--janela" not in args:
        faltas = marcar_done(projeto, vid, saida, [a for a in args if re.fullmatch(r"M\d+[A-Za-z]?", a)])
        if faltas:
            print("✗ cena sem todos os quadros (sem .done): " + "; ".join(faltas))
            rc = 1
    if job:
        job_marcar(projeto, job, "ok" if rc == 0 else "erro")
    return rc


# ------------------------------------------------------------------ CLI
def main(cmd: str, argv: list[str]) -> int:
    if cmd == "iniciar-motion":
        ap = argparse.ArgumentParser(prog="di iniciar-motion")
        ap.add_argument("video")
        ap.add_argument("--projeto")
        a = ap.parse_args(argv)
        print(f"✓ {iniciar(achar_projeto(a.projeto), a.video)}")
        return 0
    if cmd == "mv":
        ap = argparse.ArgumentParser(prog="di mv")
        ap.add_argument("video")
        ap.add_argument("--saida", choices=["V", "H"], default="V")
        ap.add_argument("--agora", action="store_true")
        ap.add_argument("--sync", action="store_true")
        ap.add_argument("--fim", choices=["flash", "sem_flash"], default="", help="variante de fim de cena do piloto")
        ap.add_argument("--projeto")
        a, resto = ap.parse_known_args(argv)
        projeto = achar_projeto(a.projeto)
        if a.sync:
            t = sync(projeto, a.video)
            print("✓ lib sincronizada: " + (", ".join(t) if t else "nada mudou"))
            return 0
        if not resto:
            raise DIError("uso: di mv <id> [--saida V|H] [--agora] <script> [args]")
        return mv(projeto, a.video, a.saida, resto[0], resto[1:], a.agora, a.fim)
    if cmd == "verificar-plano":
        import verificar_plano
        return verificar_plano.main(cmd, argv)
    if cmd == "entregar":
        import entregar
        return entregar.main(cmd, argv)
    if cmd == "verificar-motion":        # mora na skill: retranscreve com o Whisper da venv dela
        import verificar_motion
        return verificar_motion.main(cmd, argv)
    raise DIError(f"comando desconhecido: {cmd}")
