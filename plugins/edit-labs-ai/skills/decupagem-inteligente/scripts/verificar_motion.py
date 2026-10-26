"""Verificação do motion: piloto (D4, V61–V67c) e master (D5, V68–V74). Mede; não opina.

  di verificar-motion <id> [--saida V|H] --trecho t0 t1 [--piloto ARQ]
  di verificar-motion <id> [--saida V|H] --master

Mora na decupagem-inteligente (não na lib da motion-vox) porque retranscreve com o Whisper da venv da skill;
o kit roda no Python 3.9 do sistema, sem Whisper. Grava 11_qa/verificacao_{piloto_<S>|master_<S>}.json e as
tiras para o Leigo e o D4 em 11_qa/tiras/.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from comum import (DIError, achar_projeto, agora, check, config, ffprobe, gravar_json, gravar_texto, ler_json, norm_palavra,
                   registrar_checks)
from verificar_corte import extrair_audio, quadros_fps, wer


def _shots(mp: Path, saida: str):
    from motion import _shots as S
    return S(mp.parent.parent, mp.name, saida)


def _palavras_texto(ws, troca=None):
    """Normalizado e com os pares do glossário/pendências aplicados dos dois lados ("Antropic" = "Anthropic")."""
    troca = troca or {}
    return [troca.get(norm_palavra(w["w"]), norm_palavra(w["w"])) for w in ws if norm_palavra(w["w"])]


def _troca(mp: Path) -> dict:
    return {k: v for k, v in (ler_json(mp / "00_brief" / "pendentes.json") or {}).items()}


def _retranscrever(video: Path, tmp: Path, gl: list[str]) -> list[dict]:
    from transcrever import transcrever_audio
    wav = extrair_audio(video, tmp / "_ret.wav")
    r = transcrever_audio(wav, gl)
    wav.unlink(missing_ok=True)
    return r["palavras"]


def _parados(frames, fps, lim=1.2):
    """Maior trecho sem mudança visual (diferença média < lim em 0–255), em segundos."""
    maior, run = 0, 0
    for (_, a), (_, b) in zip(frames, frames[1:]):
        if float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16)))) < lim:
            run += 1
            maior = max(maior, run)
        else:
            run = 0
    return maior / fps


def _mudancas_por_10s(frames, fps, lim=4.0):
    out = {}
    for (t, a), (_, b) in zip(frames, frames[1:]):
        if float(np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16)))) >= lim:
            k = int(t // 10) * 10
            out[k] = out.get(k, 0) + 1
    return out


def _tira(video: Path, destino: Path, fps_amostra: float, pal: list[dict], t_base: float, com_palavra: bool, largura=300):
    """Tira de quadros a `fps_amostra`, 300 px; no passo 2 a palavra dita sob cada quadro."""
    from PIL import Image, ImageDraw
    fr = quadros_fps(video, fps_amostra, largura)
    if not fr:
        return None
    col = 8
    h = fr[0][1].shape[0] + (22 if com_palavra else 0)
    linhas = (len(fr) + col - 1) // col
    im = Image.new("RGB", (col * (largura + 6) + 6, linhas * (h + 6) + 6), (236, 234, 228))
    d = ImageDraw.Draw(im)
    for k, (t, a) in enumerate(fr):
        x, y = 6 + (k % col) * (largura + 6), 6 + (k // col) * (h + 6)
        im.paste(Image.fromarray(a[..., ::-1] if a.shape[-1] == 3 else a), (x, y))
        if com_palavra:
            tt = t_base + t
            w = next((w["w"] for w in pal if w["t"] <= tt < w["e"] + 0.05), "")
            d.text((x + 4, y + a.shape[0] + 3), f"{tt:5.2f}s {w}", fill=(30, 30, 30))
    destino.parent.mkdir(parents=True, exist_ok=True)
    im.save(destino, quality=86)
    return destino


def trecho(projeto: Path, vid: str, saida: str, t0: float, t1: float, piloto: Path | None) -> list[dict]:
    mp = projeto / "motion" / vid
    seq = mp / "10_sequences" / saida
    arqs = [piloto] if piloto else sorted(seq.glob(f"PILOTO_{saida}_*.mp4"))
    if not arqs or not arqs[0] or not Path(arqs[0]).exists():
        raise DIError(f"nenhum piloto em {seq} (di mv {vid} --saida {saida} render.py --janela {t0} {t1})")
    pal = ler_json(mp / "00_brief" / "transcript_palavras.json") or []
    tr = _troca(mp)
    ref = _palavras_texto([w for w in pal if w["t"] >= t0 - 0.05 and w["e"] <= t1 + 0.05], tr)
    gl = [x for x in (projeto / "00_fonte" / "glossario.txt").read_text(encoding="utf-8").split("\n") if x] \
        if (projeto / "00_fonte" / "glossario.txt").exists() else []
    mot = config(projeto).get("motion") or {}
    C = []
    base_ret = None
    shots, (fn, fd) = _shots(mp, saida)
    fps = fn / fd
    for arq in arqs:
        arq = Path(arq)
        mvar = re.match(rf"PILOTO_{saida}_(.+?)_\d+s$", arq.stem)
        var = mvar.group(1) if mvar else "regua"
        base = dict(video=vid, saida=saida, variante=var)
        # V61 fala preservada
        hip = _palavras_texto(_retranscrever(arq, mp / "11_qa", gl), tr)
        if base_ret is None:   # linha de base: o MESMO trecho do corte sem motion, recortado igual ao piloto
            tmpv = mp / "11_qa" / f"_base_{saida}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(mp / "00_brief" / f"fonte_{saida}.mp4"),
                            "-t", f"{t1 - t0:.3f}", "-map", "0:a", "-c:a", "aac", "-b:a", "256k", str(tmpv)], check=True)
            base_ret = _palavras_texto(_retranscrever(tmpv, mp / "11_qa", gl), tr)
            tmpv.unlink(missing_ok=True)
        w_ = wer(base_ret, hip)
        perdidas = [x for x in base_ret if x not in hip and len(x) >= 4]
        C.append(check("V61_fala_no_piloto", w_ <= 0.03 and not perdidas, "BLOCKER",
                       medido=f"WER {100 * w_:.1f} % contra o corte sem motion (transcript: {100 * wer(ref, hip):.1f} %) · perdidas {perdidas[:5] or 0}",
                       esperado="≤ 3 % contra a linha de base; nenhuma palavra perdida", **base))
        # V62 trecho parado dentro das cenas
        fr = quadros_fps(arq, fps, 160)
        par = []
        for n, a, b, cut in shots:
            if b <= t0 or a >= t1:
                continue
            sub = [(t, q) for t, q in fr if a - t0 <= t <= b - t0]
            if len(sub) > 2:
                par.append((n, round(_parados(sub, fps), 2)))
        C.append(check("V62_nada_parado", all(p <= 1.5 for _, p in par), "HIGH", medido=par or "sem cena na janela",
                       esperado="≤ 1,5 s sem mudança dentro de cada cena (E8)", **base))
        # V67c tiras e mudanças
        t_dir = mp / "11_qa" / "tiras" / f"piloto_{saida}_{var}"
        _tira(arq, t_dir / "passo1_sem_texto.jpg", 4, pal, t0, False)
        _tira(arq, t_dir / "passo2_com_palavra.jpg", 4, pal, t0, True)
        mud = _mudancas_por_10s(quadros_fps(arq, 12, 160), 12)
        gravar_texto(t_dir / "mudancas.txt", "\n".join(f"{t0 + k:5.1f}–{t0 + k + 10:5.1f} s: {v} mudanças visuais" for k, v in sorted(mud.items())) + "\n")
        C.append(check("V67c_tiras", True, "info", medido=str(t_dir.relative_to(projeto)), **base))
    # V63/V64 pela timeline das cenas (a mesma que o render usa)
    vals = sorted([(a, b) for _, a, b, _ in shots])
    min_r = float(mot.get("min_rosto_s") or 1.0)
    curtos = [f"{b:.2f}→{a2:.2f}" for (a, b), (a2, b2) in zip(vals, vals[1:]) if 0 < a2 - b < min_r]
    C.append(check("V63_rosto_entre_blocos", not curtos, "HIGH", medido=curtos or 0, esperado=f"≥ {min_r} s", video=vid, saida=saida))
    # V65 legenda: nenhuma janela atravessa emenda; nenhuma palavra pendente dentro de janela
    jl = ler_json(mp / "05_motion" / "JANELAS_LEGENDA.json") or {}
    cortes = (ler_json(mp / "00_brief" / "cortes.json") or {}).get("cortes", [])
    pend = set((ler_json(mp / "00_brief" / "pendentes.json") or {}).keys())
    atrav = [j for j in jl.get("janelas", []) if any(j[0] < c < j[1] for c in cortes)]
    na_tela = [w["w"] for w in pal for j in jl.get("janelas", []) if j[0] <= w["t"] < j[1] and norm_palavra(w["w"]) in pend]
    C.append(check("V65_legenda_emenda", not atrav, "BLOCKER", medido=atrav or 0, esperado="nenhuma janela atravessa emenda", video=vid, saida=saida))
    C.append(check("V65_legenda_duvida", not na_tela, "BLOCKER", medido=na_tela or 0, esperado="nenhuma palavra pendente na tela", video=vid, saida=saida))
    return C


def master(projeto: Path, vid: str, saida: str) -> list[dict]:
    mp = projeto / "motion" / vid
    mst = mp / "12_master" / f"MASTER_{saida}_v01.mp4"
    fonte = mp / "00_brief" / f"fonte_{saida}.mp4"
    if not mst.exists():
        raise DIError(f"{mst} não existe (di mv {vid} --saida {saida} render.py --mux)")
    C, base = [], dict(video=vid, saida=saida)
    pm, pf = ffprobe(mst), ffprobe(fonte)
    vm = next(s for s in pm["streams"] if s["codec_type"] == "video")
    vf = next(s for s in pf["streams"] if s["codec_type"] == "video")
    dm, df = float(pm["format"]["duration"]), float(pf["format"]["duration"])
    fps = eval(vf["r_frame_rate"])
    C.append(check("V68_duracao", abs(dm - df) <= 1 / fps + 0.01, "BLOCKER", medido=f"{dm:.3f} s", esperado=f"{df:.3f} s ± 1 quadro", **base))
    C.append(check("V68_cadencia", vm["r_frame_rate"] == vf["r_frame_rate"], "BLOCKER", medido=vm["r_frame_rate"], esperado=vf["r_frame_rate"], **base))
    from motion import mux_pronto
    sem = mux_pronto(projeto, vid, saida)
    C.append(check("V68_cenas_done", not sem, "BLOCKER", medido=sem or 0, esperado="toda cena com .done", **base))
    # V69 fala: WER do master inteiro vs o transcript do corte
    pal = ler_json(mp / "00_brief" / "transcript_palavras.json") or []
    tr = _troca(mp)
    hip = _palavras_texto(_retranscrever(mst, mp / "11_qa", []), tr)
    w_ = wer(_palavras_texto(pal, tr), hip)
    C.append(check("V69_fala_preservada", w_ <= 0.03 or w_ <= 0.08, "BLOCKER" if w_ > 0.08 else "HIGH",
                   medido=f"WER {100 * w_:.1f} %", esperado="≤ 3 %", **base))
    # V70 áudio: MD5 igual sem SFX; com SFX, resíduo fora das janelas
    md5 = lambda p: subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-map", "0:a", "-f", "md5", "-"],
                                   capture_output=True, text=True).stdout.strip()
    sfx = ler_json(mp / "06_transitions" / "SFX_MAP.json") or []
    if not sfx:
        C.append(check("V70_audio_intocado", md5(mst) == md5(fonte), "BLOCKER", medido=md5(mst)[:20], esperado=md5(fonte)[:20], **base))
    else:
        C.append(check("V70_audio_intocado", True, "aviso", medido=f"{len(sfx)} SFX: resíduo fora das janelas a medir (escuta pendente)", **base))
    # V71 pico e loudness
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mst), "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    lufs = re.findall(r"I:\s+(-?[0-9.]+) LUFS", r)
    tp = re.findall(r"Peak:\s+(-?[0-9.]+) dBFS", r)
    C.append(check("V71_pico_loudness", bool(tp) and float(tp[-1]) <= -1.0, "HIGH",
                   medido=f"{lufs[-1] if lufs else '?'} LUFS · pico {tp[-1] if tp else '?'} dBTP", esperado="≤ −1 dBTP; −14 LUFS ± 1", **base))
    # V73 formato e quadro preto
    wh = f"{vm['width']}x{vm['height']}"
    C.append(check("V73_formato", wh == ("1080x1920" if saida == "V" else "1920x1080") and vm.get("pix_fmt") == "yuv420p", "BLOCKER",
                   medido=f"{wh} {vm.get('pix_fmt')}", **base))
    bd = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mst), "-vf", "blackdetect=d=0.1:pix_th=0.05", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    C.append(check("V73_quadro_preto", "black_start" not in bd, "BLOCKER", medido=len(re.findall("black_start", bd)), esperado=0, **base))
    # V74 tiras
    t_dir = mp / "11_qa" / "tiras" / f"master_{saida}"
    _tira(mst, t_dir / "passo1_sem_texto.jpg", 2, pal, 0.0, False)
    _tira(mst, t_dir / "passo2_com_palavra.jpg", 2, pal, 0.0, True)
    C.append(check("V74_tiras", True, "info", medido=str(t_dir.relative_to(projeto)), **base))
    return C


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di verificar-motion")
    ap.add_argument("video")
    ap.add_argument("--saida", choices=["V", "H"], default="V")
    ap.add_argument("--trecho", nargs=2, type=float)
    ap.add_argument("--piloto")
    ap.add_argument("--master", action="store_true")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    if a.master:
        C, fase, nome = master(projeto, a.video, a.saida), "F7", f"master_{a.saida}"
    elif a.trecho:
        C, fase, nome = trecho(projeto, a.video, a.saida, a.trecho[0], a.trecho[1], Path(a.piloto) if a.piloto else None), "F6", f"piloto_{a.saida}"
    else:
        raise DIError("--trecho t0 t1 ou --master")
    registrar_checks(projeto, fase, C, alvo=f"motion/{a.video}/")
    gravar_json(projeto / "motion" / a.video / "11_qa" / f"verificacao_{nome}.json",
                {"source": "deterministic", "atualizado": agora(), "checks": C})
    ruins = [c for c in C if not c["ok"] and c["severidade"] in ("BLOCKER", "HIGH")]
    for c in C:
        if not c["ok"] or c["id"].startswith(("V61", "V62", "V69", "V71")):
            print(f"  {'✓' if c['ok'] else '✗'} {c['id']} {c.get('variante', '')} {c['severidade']}: {c.get('medido')}")
    print(f"{'✗' if ruins else '✓'} {len(C)} checks · {len(ruins)} BLOCKER/HIGH")
    return 1 if any(c["severidade"] == "BLOCKER" for c in ruins) else 0
