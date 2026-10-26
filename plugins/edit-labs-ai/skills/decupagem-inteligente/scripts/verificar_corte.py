"""F3: verifica por máquina o corte renderizado (V24–V39). Mede; nunca opina.

  di verificar-corte <id> [--agora] [--esperar N]

Saídas em 03_corte/<id>/: verificacao.json (+ VERIFICACAO.md gerado só dele), palavras_render.json,
juntas.jpg, juntas_audio/, ritmo.txt. O JSON do Verificador da fase fica em laudos/F3_V_verificador_t<k>.json.
Nenhum papel ouve: a prova de "não cortou sílaba" é o teste de energia do F2; a retranscrição confere.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
import time
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

import silencio as SIL
import transcrever as TR
from comum import (edl_assinatura, DIError, achar_projeto, agora, carregar, check, config, gravar_json, gravar_texto, job_marcar,
                   lancar_job, ler_json, mmss, norm_palavra, registrar_checks, arquivo_verificador, salvar)
from render_corte import _filtro_video, fonte_de, quadro, rostos


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
    return d[-1]


def wer(ref: list[str], hip: list[str]) -> float:
    if not ref:
        return 0.0
    d = list(range(len(hip) + 1))
    for i, r in enumerate(ref, 1):
        p, d[0] = d[0], i
        for j, h in enumerate(hip, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r != h))
    return d[-1] / len(ref)


def extrair_audio(video: Path, destino: Path, sr: int = 16000) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-map", "0:a:0", "-ac", "1", "-ar", str(sr),
                    "-c:a", "pcm_s16le", str(destino)], check=True)
    return destino


def quadro_n(video: Path, n: int, largura: int = 540) -> np.ndarray:
    import cv2
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select=eq(n\\,{n}),scale={largura}:-2",
                          "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)


def quadros_n(video: Path, ns: list[int], largura: int = 540) -> dict[int, np.ndarray]:
    """Vários quadros por índice numa passada só (decodificar do começo para cada um custava minutos)."""
    import cv2
    ns = sorted(set(max(0, n) for n in ns))
    if not ns:
        return {}
    td = Path(tempfile.mkdtemp())
    expr = "+".join(f"eq(n\\,{n})" for n in ns)
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"select='{expr}',scale={largura}:-2", "-fps_mode", "passthrough",
                    str(td / "q%05d.png")], check=True)
    arqs = sorted(td.glob("q*.png"))
    return {n: cv2.imread(str(a)) for n, a in zip(ns, arqs)}


def quadros_fps(video: Path, fps_amostra: float, largura: int = 540) -> list[tuple[float, np.ndarray]]:
    import cv2
    td = Path(tempfile.mkdtemp())
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps_amostra},scale={largura}:-2", str(td / "a%05d.jpg")], check=True)
    return [((k + 0.5) / fps_amostra, cv2.imread(str(a))) for k, a in enumerate(sorted(td.glob("a*.jpg")))]


def quadro_fonte_filtrado(src: str, t: float, vf: str, largura: int = 540) -> np.ndarray:
    import cv2
    pre = max(0.0, t - 2.0)
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{pre:.3f}", "-i", src, "-ss", f"{t - pre:.3f}", "-frames:v", "1",
                          "-vf", f"{vf},scale={largura}:-2", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.shape != b.shape:
        return 0.0
    mse = float(np.mean((a.astype(np.float32) - b.astype(np.float32)) ** 2))
    return 99.0 if mse == 0 else round(10 * np.log10(255 ** 2 / mse), 1)


def verificar(projeto: Path, vid: str) -> dict:
    projeto = Path(projeto).resolve()
    pasta = projeto / "03_corte" / vid
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
    fonte_src, fonte = fonte_de(projeto)
    fps = fonte["fps"][0] / fonte["fps"][1]
    cfg = config(projeto)
    enq = ler_json(pasta / "enquadramento.json")
    if enq and enq.get("por_segmento"):
        enq["por_segmento"] = {int(k): v for k, v in enq["por_segmento"].items()}
    rj = ler_json(pasta / "render.json")
    if not rj or rj.get("edl_assinatura") != edl_assinatura(edl):
        raise DIError(f"{vid}: o render em 03_corte/{vid}/ não é deste edl.json (EDL mudou depois do render): rode di render {vid}")
    renders = [p for p in (pasta / "corte_v01_V.mp4", pasta / "corte_v01_H.mp4") if p.exists()]
    if not renders:
        raise DIError(f"{vid}: nenhum corte renderizado em {pasta}")
    principal = renders[0]
    saida_p = "V" if principal.name.endswith("_V.mp4") else "H"
    C: list[dict] = []
    segs = edl["segmentos"]
    juntas = [s["timeline_in"] for s in segs[1:]]
    # ---- V24 frames por segmento · V26 duração e frames do render
    for s in segs:
        p = pasta / "segmentos" / f"{saida_p}_{s['n']:03d}.mov"
        if p.exists():
            n = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                                    "stream=nb_read_frames", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)
            if n != s["frames"]:
                C.append(check("V24_frames_segmento", False, "BLOCKER", medido=n, esperado=s["frames"], junta=s["n"]))
    C.append(check("V24_frames_segmento", not any(c["id"] == "V24_frames_segmento" for c in C), "BLOCKER",
                   medido="todos iguais ao EDL" if not C else "divergentes", esperado="frames do EDL"))
    for r in renders:
        pr = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                             "stream=codec_type,width,height,nb_read_frames,pix_fmt,r_frame_rate,sample_rate:format=duration",
                             "-of", "json", str(r)], capture_output=True, text=True).stdout
        import json
        j = json.loads(pr)
        v = next(x for x in j["streams"] if x["codec_type"] == "video")
        a = next((x for x in j["streams"] if x["codec_type"] == "audio"), {})
        d = float(j["format"]["duration"])
        esp = edl["frames_total"] / fps
        sd = "V" if r.name.endswith("_V.mp4") else "H"
        C.append(check("V26_duracao", abs(d - esp) <= 1 / fps + 0.01 and int(v["nb_read_frames"]) == edl["frames_total"], "BLOCKER",
                       medido=f"{d:.3f} s · {v['nb_read_frames']} frames", esperado=f"{esp:.3f} s · {edl['frames_total']} frames", saida=sd))
        fmt_ok = (v["pix_fmt"] == "yuv420p" and a.get("sample_rate") == "48000" and
                  ((int(v["width"]), int(v["height"])) == ((1080, 1920) if sd == "V" else (fonte["width"], fonte["height"]))))
        C.append(check("V36_formato", fmt_ok, "BLOCKER", medido=f"{v['width']}×{v['height']} {v['pix_fmt']} {v['r_frame_rate']} · {a.get('sample_rate')} Hz",
                       saida=sd))
    # ---- áudio do render
    td = Path(tempfile.mkdtemp())
    wav16 = extrair_audio(principal, td / "r16.wav")
    wav48 = extrair_audio(principal, td / "r48.wav", 48000)
    x16, sr16 = SIL.carregar_wav(wav16)
    x48, sr48 = SIL.carregar_wav(wav48)
    silj = ler_json(projeto / "01_transcript" / "silencios.json")
    # ---- V27 retranscrição × roteiro montado (mesma engine, mesmo glossário)
    gl = TR.glossario_do_projeto(projeto)
    rr = TR.transcrever_audio(wav16, gl, "auto")
    gravar_json(pasta / "palavras_render.json", {"schema": "di-palavras/1", "relogio": "corte", "engine": rr["engine"],
                                                 "palavras": rr["palavras"]}, indent=None)
    pal_bruto = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    ref = [norm_palavra(pal_bruto[i]["w"]) for i in edl["palavras_mantidas"]]
    ref = [w for w in ref if w]
    hip = [norm_palavra(w["w"]) for w in rr["palavras"] if norm_palavra(w["w"])]
    w_total = wer(ref, hip)
    maior = max(segs, key=lambda s: s["frames"])
    pseg = pasta / "segmentos" / f"{saida_p}_{maior['n']:03d}.mov"
    base = 0.0
    if pseg.exists():
        rb = TR.transcrever_audio(extrair_audio(pseg, td / "base.wav"), gl, "auto")
        rb_ref = [norm_palavra(pal_bruto[i]["w"]) for i in edl["palavras_mantidas"] if maior["palavra_in"] <= i <= maior["palavra_out"]]
        base = wer([w for w in rb_ref if w], [norm_palavra(w["w"]) for w in rb["palavras"] if norm_palavra(w["w"])])
    limiar = max(0.03, 2 * base)
    sm = SequenceMatcher(None, ref, hip, autojunk=False)
    diffs = [f"{tag}: '{' '.join(ref[i1:i2])}' → '{' '.join(hip[j1:j2])}'" for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != "equal"][:12]
    C.append(check("V27_retranscricao", w_total <= limiar, "HIGH", medido=f"WER {100 * w_total:.1f} %", esperado=f"≤ {100 * limiar:.1f} % (2× a base {100 * base:.1f} %, mín. 3 %)",
                   detalhe=" · ".join(diffs)))
    # ---- V28 palavras em volta de cada junta
    rw = rr["palavras"]
    falhas28 = []
    for k, s in enumerate(segs[1:], 1):
        j = s["timeline_in"]
        ant_esp = [norm_palavra(pal_bruto[i]["w"]) for i in edl["palavras_mantidas"] if segs[k - 1]["palavra_in"] <= i <= segs[k - 1]["palavra_out"]][-3:]
        dep_esp = [norm_palavra(pal_bruto[i]["w"]) for i in edl["palavras_mantidas"] if s["palavra_in"] <= i <= s["palavra_out"]][:3]
        ant_ach = [norm_palavra(w["w"]) for w in rw if w["e"] <= j + 0.15 and w["e"] >= j - 2.5][-5:]
        dep_ach = [norm_palavra(w["w"]) for w in rw if w["t"] >= j - 0.15 and w["t"] <= j + 2.5][:5]
        ok_a = sum(1 for p in ant_esp if any(lev(p, q) <= 2 for q in ant_ach)) >= min(2, len(ant_esp))
        ok_d = sum(1 for p in dep_esp if any(lev(p, q) <= 2 for q in dep_ach)) >= min(2, len(dep_esp))
        if not (ok_a and ok_d):
            falhas28.append(k)
            (pasta / "juntas_audio").mkdir(exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, j - 1):.3f}", "-t", "2", "-i", str(wav48),
                            str(pasta / "juntas_audio" / f"junta_{k:02d}.wav")], check=True)
    C.append(check("V28_palavras_na_junta", not falhas28, "HIGH", medido=falhas28 or f"{len(segs) - 1} juntas ok",
                   detalhe="áudio das juntas marcadas em juntas_audio/ para o usuário ouvir" if falhas28 else ""))
    # ---- V29 / V29b repetição
    rep = []
    for a in range(len(rw) - 4):
        for b in range(a + 5, len(rw) - 4):
            if rw[b]["t"] - rw[a]["t"] > 60:
                break
            if [norm_palavra(w["w"]) for w in rw[a:a + 5]] == [norm_palavra(w["w"]) for w in rw[b:b + 5]]:
                rep.append(f"{mmss(rw[a]['t'])} e {mmss(rw[b]['t'])}: {' '.join(w['w'] for w in rw[a:a + 5])}")
                break
    C.append(check("V29_frase_repetida", not rep, "HIGH", medido=rep[:4] or 0))
    rep3 = []
    for j in juntas:
        k = next((i for i, w in enumerate(rw) if w["t"] >= j - 0.15), None)
        if k is None:
            continue
        ant = [norm_palavra(w["w"]) for w in rw[max(0, k - 8):k]]
        dep = [norm_palavra(w["w"]) for w in rw[k:k + 8]]
        for n in range(len(dep) - 2):
            if any(ant[m:m + 3] == dep[n:n + 3] for m in range(len(ant) - 2)):
                rep3.append(f"{mmss(j)}: '{' '.join(dep[n:n + 3])}'")
                break
    C.append(check("V29b_vazamento_na_junta", not rep3, "HIGH", medido=rep3 or 0))
    # ---- V30 silêncio e resíduo por junta
    sil_r = SIL.silencios(x16, sr16, silj["limiar_db"], 0.12)
    grandes = [s for s in sil_r if s["d"] > cfg.get("pausa_max_s", 0.35) + 0.05 and s["t"] > 0.3 and s["e"] < edl["duracao"] - 0.3]
    preserv = []
    for p in edl.get("pausas_preservadas", []):
        for s in segs:
            if s["palavra_in"] <= p["apos_palavra"] <= s["palavra_out"]:
                # A pausa declarada é procurada na FAIXA da palavra e da seguinte, não no ponto do fim da palavra:
                # o Whisper estica palavra (V20b) e põe a pausa dentro do span dela — ancorar no fim da palavra
                # faz o verificador procurar a pausa declarada segundos depois de onde ela está.
                a = p["apos_palavra"]
                b = min(a + 1, len(pal_bruto) - 1)
                preserv.append((s["timeline_in"] + pal_bruto[a]["t"] - s["source_in"],
                                s["timeline_in"] + pal_bruto[b]["e"] - s["source_in"]))
    sem_funcao = [s for s in grandes
                  if not any(t0 - 0.3 <= (s["t"] + s["e"]) / 2 <= t1 + 0.3 for (t0, t1) in preserv)]
    res_err = []
    for k, s in enumerate(segs[1:], 1):
        j = s["timeline_in"]
        m_ = [x for x in sil_r if x["t"] - 0.05 <= j <= x["e"] + 0.05]
        med = m_[0]["d"] if m_ else 0.0
        decl = s["junta_in"].get("residuo") or 0
        if med > decl + 0.10:
            res_err.append(f"junta {k} ({mmss(j)}): {med:.2f} s medido > {decl:.2f} declarado")
    C.append(check("V30_silencio", not sem_funcao and not res_err, "HIGH",
                   medido=[f"{mmss(s['t'])} {s['d']:.2f}s" for s in sem_funcao][:6] + res_err[:4] or 0,
                   esperado=f"nenhum silêncio > {cfg.get('pausa_max_s', 0.35)} s fora das pausas preservadas; resíduo ≤ declarado + 0,10"))
    # ---- V31 estalo · V31b salto de nível
    est, nivel = [], []
    lim_voz = max(silj["limiar_db"] + 8, -35)
    for k, j in enumerate(juntas, 1):
        a, b = int((j - 0.02) * sr48), int((j + 0.02) * sr48)
        trecho = x48[a:b]
        if len(trecho) > 10:
            rms = float(np.sqrt(np.mean(trecho ** 2))) or 1e-6
            razao = float(np.max(np.abs(np.diff(trecho)))) / rms
            if razao > 6 and 20 * np.log10(rms) > -45:
                est.append(f"junta {k}: {razao:.1f}")

        def voz_rms(t0, t1):  # quadros até 15 dB abaixo do mais alto da janela: estável com o ganho (igual ao edl.py)
            env, hop = SIL.env_cache(x16, sr16)
            fr = env[max(0, int(t0 / hop)):max(0, int(t1 / hop))]
            fr = fr[(fr > lim_voz) & (fr >= (fr.max() if len(fr) else 0) - 15.0)]
            return float(np.median(fr)) if len(fr) else None
        va, vb = voz_rms(max(0, j - 1.2), j), voz_rms(j, j + 1.2)
        if va is not None and vb is not None:
            nivel.append((k, j, va - vb))
    # linha de base: o mesmo salto nas trocas de frase SEM corte (dentro dos segmentos); fim de frase cai de nível
    # naturalmente, e a emenda só é defeito quando salta mais que a fala dele salta sozinha
    rt_ = ler_json(projeto / "02_decupagem" / "retakes.json") or {}
    base_d = []
    for f_ in rt_.get("frases", []):
        for s in segs:
            if s["palavra_in"] < f_["i0"] <= s["palavra_out"]:
                tb = s["timeline_in"] + (pal_bruto[f_["i0"]]["t"] - s["source_in"])
                if tb - 1.2 >= s["timeline_in"] and tb + 1.2 <= s["timeline_out"]:
                    va, vb = voz_rms(tb - 1.2, tb), voz_rms(tb, tb + 1.2)
                    if va is not None and vb is not None:
                        base_d.append(abs(va - vb))
    lim_nivel = max(3.0, float(np.percentile(base_d, 90))) if len(base_d) >= 4 else 3.0
    nivel = [f"junta {k} ({mmss(j)}): {d:+.1f} dB" for k, j, d in nivel if abs(d) > lim_nivel]
    C.append(check("V31_estalo", not est, "MEDIUM", medido=est or 0, esperado="salto/RMS ≤ 6 nos ±20 ms"))
    C.append(check("V31b_nivel_na_junta", not nivel, "HIGH", medido=nivel or 0,
                   esperado=f"ΔRMS da voz ≤ {lim_nivel:.1f} dB (maior entre 3 dB e o p90 de {len(base_d)} trocas de frase sem corte)"))
    # ---- V32 quadro preto · V35 loudness
    bd = subprocess.run(["ffmpeg", "-v", "info", "-i", str(principal), "-vf", "blackdetect=d=0.04:pix_th=0.10", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    pretos = re.findall(r"black_start:([\d.]+)", bd)
    C.append(check("V32_quadro_preto", not pretos, "BLOCKER", medido=pretos or 0))
    lu = subprocess.run(["ffmpeg", "-v", "info", "-i", str(principal), "-af", "ebur128=peak=true", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", lu)
    TP = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lu)
    tp = float(TP[-1]) if TP else None
    C.append(check("V35_loudness", tp is None or tp <= -1.0, "LOW", medido=f"{I[-1] if I else '?'} LUFS · pico {tp} dBTP",
                   detalhe="aviso: a mixagem final é da motion-vox"))
    # ---- V33 pontas
    if rw:
        # pela voz medida no áudio do corte (o Whisper costuma dar 0,00 s para a primeira palavra)
        lim_v = max(silj["limiar_db"] + 8, -35)
        pri = SIL.voz_inicio(x16, sr16, 0.0, min(3.0, edl["duracao"]), lim_v, acima=0.0) or rw[0]["t"]
        ult = SIL.voz_fim(x16, sr16, max(0.0, edl["duracao"] - 3.0), edl["duracao"], lim_v, acima=0.0) or rw[-1]["e"]
        ok33 = 0.15 <= pri <= 0.60 and edl["duracao"] - 0.8 <= ult <= edl["duracao"] - 0.15
        C.append(check("V33_pontas", ok33, "HIGH", medido=f"voz começa {pri:.2f} s · termina {ult:.2f} s de {edl['duracao']:.2f}",
                       esperado="1ª entre 0,15 e 0,60 s; última entre dur−0,8 e dur−0,15"))
    # ---- V34 quadro na junta = quadro da fonte (mesmo recorte) · V37 pulo de cabeça
    import cv2
    ps, pulos, linhas = [], [], []
    idx = [n for s in segs[1:] for n in (s["timeline_in_f"] - 1, s["timeline_in_f"], s["timeline_in_f"] + 1)] + [0, edl["frames_total"] - 1]
    Q = quadros_n(principal, idx)
    for k, s in enumerate(segs[1:], 1):
        vf = _filtro_video(s, saida_p, fonte, enq)
        rend = Q.get(s["timeline_in_f"])
        font = quadro_fonte_filtrado(fonte_src, s["source_in"], vf)
        rend1 = Q.get(s["timeline_in_f"] + 1)
        font1 = quadro_fonte_filtrado(fonte_src, s["source_in"] + 1 / fps, vf)
        p0, p1 = psnr(rend, font), psnr(rend1, font1)
        if min(p0, p1) < 35:
            ps.append(f"junta {k}: {p0}/{p1} dB")
        antes = Q.get(max(0, s["timeline_in_f"] - 1))
        fa, fd = rostos(antes), rostos(rend)
        if fa and fd:
            ca = max(fa, key=lambda f: f[2] * f[3])
            cd = max(fd, key=lambda f: f[2] * f[3])
            dx = abs((ca[0] + ca[2] / 2) - (cd[0] + cd[2] / 2)) / antes.shape[1]
            if dx > 0.05:
                pulos.append({"tipo": "pulo_de_cabeca", "t": s["timeline_in"], "junta": k, "dx_pct": round(100 * dx, 1)})
        linhas.append(np.hstack([cv2.resize(antes, (270, 480)), cv2.resize(rend, (270, 480)), cv2.resize(font, (270, 480))]))
    C.append(check("V34_quadro_da_fonte", not ps, "HIGH", medido=ps or "todas ≥ 35 dB", esperado="PSNR ≥ 35 dB em timeline_in e +1"))
    C.append(check("V37_pulo_de_cabeca", True, "aviso", medido=[f"junta {p['junta']} ({p['dx_pct']} %)" for p in pulos] or 0,
                   detalhe="vira tarefa do plano (F4): cutaway por cima"))
    # ---- V37b rosto dentro do recorte (só V)
    if saida_p == "V":
        n_ok = n_tot = 0
        piores = []
        for t, img in quadros_fps(principal, 2.0):
            fs = rostos(img)
            if not fs:
                continue
            n_tot += 1
            x, y, w, h, _ = max(fs, key=lambda f: f[2] * f[3])
            W_, H_ = img.shape[1], img.shape[0]
            # margem lateral de 5 %, topo da cabeça dentro do quadro, CENTRO do rosto acima de 0,60 H (a legenda mora
            # embaixo); a borda de baixo da caixa (queixo) passa de 0,60 quando ele se inclina e não é defeito
            ok = x >= 0.05 * W_ and x + w <= 0.95 * W_ and y >= 0.02 * H_ and (y + h / 2) <= 0.60 * H_
            n_ok += ok
            if not ok:
                piores.append(round(float(t), 1))
        frac = n_ok / max(1, n_tot)
        C.append(check("V37b_rosto_no_recorte", frac >= 0.99, "HIGH", medido=f"{100 * frac:.1f} % de {n_tot} amostras",
                       esperado="≥ 99 % com margem lateral ≥ 5 %, topo no quadro e centro do rosto acima de 0,60 H", detalhe=f"piores: {piores[:6]}" if piores else ""))
    # ---- V39 palavras em dúvida confirmadas pela retranscrição
    pend, confirmadas = [], []
    cor = carregar(projeto).get("correcoes") or []
    ouvidas = {norm_palavra(x) for c in cor for x in c["ouvido"].split()}
    for i in edl["palavras_mantidas"]:
        w = pal_bruto[i]
        if w.get("sugerido") or (w.get("ambigua") and (w["w"][:1].isupper() or re.search(r"\d", w["w"]))):
            (confirmadas if norm_palavra(w["w"]) in ouvidas else pend).append(w["w"] + (f"→{w['sugerido']}" if w.get("sugerido") else ""))
    C.append(check("V39_ambiguas", True, "info", medido=sorted(set(pend))[:10] or 0,
                   detalhe=("até 10 vão ao portão F3; sem resposta a legenda cala a frase"
                            + (f" · confirmadas pelo usuário (correcoes do manifest): {', '.join(sorted(set(confirmadas))[:10])}" if confirmadas else ""))))
    # ---- juntas.jpg: por junta [antes | depois (render) | fonte no mesmo recorte] + 1º e último quadro
    if linhas:
        primeiro, ultimo = Q.get(0), Q.get(edl["frames_total"] - 1)
        topo = np.hstack([cv2.resize(primeiro, (270, 480)), cv2.resize(ultimo, (270, 480)), np.full((480, 270, 3), 30, np.uint8)])
        cv2.imwrite(str(pasta / "juntas.jpg"), np.vstack([topo, *linhas]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    # ---- ritmo para o Revisor Leigo (ele não ouve: lê número)
    dur = edl["duracao"]
    pmin_corte = 60 * len(hip) / dur
    t_br = sum(pal_bruto[i]["e"] - pal_bruto[i]["t"] for i in edl["palavras_mantidas"])
    pausas_min = 60 * sum(1 for s in sil_r if s["d"] > 0.3) / dur
    gravar_texto(pasta / "ritmo.txt", f"palavras por minuto no corte: {pmin_corte:.0f}\npausas acima de 0,3 s por minuto: {pausas_min:.1f}\n"
                                      f"duração: {dur:.1f} s · emendas: {len(juntas)}\n")
    av = ler_json(pasta / "avisos.json") or []
    av = [a for a in av if a.get("tipo") != "pulo_de_cabeca"] + pulos
    gravar_json(pasta / "avisos.json", av)
    for c in C:
        c["video"] = vid
    arqv = arquivo_verificador(projeto, "F3")
    velho = ler_json(arqv)
    if velho:
        velho["checks"] = [c for c in velho["checks"] if c.get("video") != vid or c["id"] in ("V25_duracao_concat", "V40_remap", "V41_xml")]
        gravar_json(arqv, velho)
    d = registrar_checks(projeto, "F3", C, alvo=f"03_corte/{vid}/")
    mine = [c for c in d["checks"] if c.get("video") == vid]
    gravar_json(pasta / "verificacao.json", {"schema": "di-verificacao/1", "source": "deterministic", "video": vid,
                                             "valid": not any(not c["ok"] and c["severidade"] == "BLOCKER" for c in mine),
                                             "checks": mine, "criado": agora()})
    from laudo import render_verificador
    render_verificador(pasta / "verificacao.json")
    return {"checks": mine}


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di verificar-corte")
    ap.add_argument("video")
    ap.add_argument("--agora", action="store_true")
    ap.add_argument("--esperar", type=int, default=0)
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    nome = f"verificar-{a.video}"
    if not a.agora:
        lancar_job(projeto, nome, ["verificar-corte", a.video, "--agora"])
        print(f"rodando em segundo plano ({nome}); acompanhe com di status")
        if a.esperar:
            fim = time.time() + min(300, a.esperar)
            while time.time() < fim and carregar(projeto)["jobs"][nome]["status"] == "rodando":
                time.sleep(5)
            print(carregar(projeto)["jobs"][nome]["status"])
        return 0
    try:
        r = verificar(projeto, a.video)
        for c in r["checks"]:
            if not c["ok"]:
                print(f"  {'✗' if c['severidade'] in ('BLOCKER', 'HIGH') else '·'} {c['id']} [{c['severidade']}] {c['medido']}")
        print(f"✓ {a.video}: verificação em 03_corte/{a.video}/verificacao.json")
        if os.environ.get("DI_JOB"):
            job_marcar(projeto, nome, "ok")
    except Exception as e:
        if os.environ.get("DI_JOB"):
            job_marcar(projeto, nome, "erro", nota=str(e)[:300])
        raise
    return 0
