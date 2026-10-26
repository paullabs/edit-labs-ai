"""F3: renderiza o corte base a partir do edl.json. Aqui o vídeo bruto é aberto pela primeira vez.

  di render <id> [--saida V|H|ambas] [--preview] [--agora] [--esperar N]

Sem --agora, roda desanexado (volta em < 5 s; acompanhe com di status).
- crop vertical MEDIDO pelo rosto (YuNet da corte-viral), nunca do template;
- trim com reencode e seek exato (rápido até 2 s antes, exato no resto);
- ganho por segmento (iguala a fala à mediana do vídeo), fade 5 ms (20 ms em junta relaxada);
- punch-in: escala do segmento (1,00 / 1,035) centrada no rosto;
- frames exatos por segmento (-frames:v) e concat sem reencode.
"""
from __future__ import annotations

import argparse
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from comum import (fase_fechada, edl_assinatura, CORTE_VIRAL, DIError, achar_projeto, agora, carregar, check, config, gravar_config, gravar_json,
                   gravar_texto, job_marcar, lancar_job, ler_json, mmss, registrar_checks, salvar)

YUNET = CORTE_VIRAL / "models" / "face_detection_yunet_2023mar.onnx"
PRE_SEEK = 2.0


def fonte_de(projeto: Path) -> tuple[str, dict]:
    f = ler_json(projeto / "00_fonte" / "fonte.json")
    if len(f["arquivos"]) > 1:
        raise DIError("bruto em vários arquivos: junte em 00_fonte/fonte_seq.mp4 antes (a confirmar no primeiro caso)")
    return f["arquivos"][0], f


def quadro(src: str, t: float, largura: int = 960) -> np.ndarray:
    """Um quadro em t com seek exato: busca rápida até 2 s antes e decodifica o resto."""
    pre = max(0.0, t - PRE_SEEK)
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{pre:.3f}", "-i", src, "-ss", f"{t - pre:.3f}", "-frames:v", "1",
           "-vf", f"scale={largura}:-2", "-f", "image2pipe", "-vcodec", "png", "-"]
    import cv2
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)


def rostos(img: np.ndarray) -> list[tuple[float, float, float, float, float]]:
    import cv2
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), 0.6, 0.3, 50)
    _, faces = det.detect(img)
    if faces is None:
        return []
    return [(float(f[0]), float(f[1]), float(f[2]), float(f[3]), float(f[14])) for f in faces]


def medir_enquadramento(projeto: Path, vid: str, edl: dict, fonte: dict, src: str) -> dict:
    W, H = fonte["width"], fonte["height"]
    cw = int(round(H * 9 / 16)) // 2 * 2
    amostras = []
    for s in edl["segmentos"]:
        dur = s["source_out"] - s["source_in"]
        ts = [s["source_in"] + k * 2.0 + 0.5 for k in range(max(1, int(dur // 2)))]
        for t in ts:
            img = quadro(src, t)
            esc = W / img.shape[1]
            fs = rostos(img)
            if not fs:
                amostras.append({"t": round(t, 2), "seg": s["n"], "rosto": None})
                continue
            x, y, w, h, sc = max(fs, key=lambda f: f[2] * f[3])  # solo: o maior rosto é o apresentador
            amostras.append({"t": round(t, 2), "seg": s["n"], "cx": round((x + w / 2) * esc), "cy": round((y + h / 2) * esc),
                             "w": round(w * esc), "h": round(h * esc), "score": round(sc, 2)})
    com = [a for a in amostras if a.get("cx") is not None]
    if not com:
        raise DIError(f"{vid}: nenhum rosto encontrado nas amostras; F3 para (mostre 3 quadros com a caixa proposta ao usuário)")
    cxs = [a["cx"] for a in com]
    med = statistics.median(cxs)
    crop_x = int(min(max(0, med - cw / 2), W - cw)) // 2 * 2
    disp = (max(cxs) - min(cxs)) / W
    por_seg = {}
    for s in edl["segmentos"]:
        cs = [a["cx"] for a in com if a["seg"] == s["n"]]
        if cs:
            por_seg[s["n"]] = int(min(max(0, statistics.median(cs) - cw / 2), W - cw)) // 2 * 2
    fora = [a for a in com if a["cx"] - a["w"] / 2 < crop_x + 80 or a["cx"] + a["w"] / 2 > crop_x + cw - 80]
    usar_por_seg = bool(fora) and len(por_seg) > 1
    d = {"crop_w": cw, "crop_h": H, "crop_x": crop_x, "por_segmento": por_seg if usar_por_seg else {},
         "dispersao_pct": round(100 * disp, 1), "amostras": amostras,
         "cy_mediana": int(statistics.median([a["cy"] for a in com])),
         "rosto_fora_da_margem": len(fora), "medido": agora()}
    gravar_json(projeto / "03_corte" / vid / "enquadramento.json", d)
    return d


def _filtro_video(s: dict, saida: str, fonte: dict, enq: dict | None) -> str:
    W, H = fonte["width"], fonte["height"]
    esc = float(s.get("escala") or 1.0)
    cy = (enq or {}).get("cy_mediana", H // 2)
    if saida == "V":
        cw, ch = enq["crop_w"], enq["crop_h"]
        cx0 = enq["por_segmento"].get(str(s["n"]), enq["por_segmento"].get(s["n"], enq["crop_x"])) if enq["por_segmento"] else enq["crop_x"]
        w2, h2 = int(round(cw / esc)) // 2 * 2, int(round(ch / esc)) // 2 * 2
        x2 = int(cx0 + (cw - w2) / 2) // 2 * 2
        y2 = int(min(max(0, cy - h2 / 2), ch - h2)) // 2 * 2 if esc > 1.0 else 0
        return f"crop={w2}:{h2}:{x2}:{y2},scale=1080:1920:flags=lanczos,setsar=1"
    if esc > 1.0:
        w2, h2 = int(round(W / esc)) // 2 * 2, int(round(H / esc)) // 2 * 2
        cx = (enq or {}).get("crop_x", (W - int(H * 9 / 16)) // 2) + (enq or {}).get("crop_w", int(H * 9 / 16)) / 2
        x2 = int(min(max(0, cx - w2 / 2), W - w2)) // 2 * 2
        y2 = int(min(max(0, cy - h2 / 2), H - h2)) // 2 * 2
        return f"crop={w2}:{h2}:{x2}:{y2},scale={W}:{H}:flags=lanczos,setsar=1"
    return "setsar=1"


def render_segmento(src: str, s: dict, fps: float, fonte: dict, saida: str, enq, destino: Path) -> None:
    """Trim por FILTRO (trim/atrim) depois de uma busca rápida 2 s antes: vídeo e áudio cortados no
    mesmo ponto, exatos. (Com `-ss` de saída + `-t`, o áudio perdia os 2 s da pré-busca e o resto
    virava silêncio digital — pego pela V30 no primeiro teste.)"""
    dur = s["frames"] / fps
    pre = max(0.0, s["source_in"] - PRE_SEEK)
    y = s["source_in"] - pre
    fi = 0.020 if s["junta_in"].get("relaxado") else 0.005
    fo = 0.020 if s["junta_out"].get("relaxado") else 0.005
    af = (f"atrim=start={y:.5f}:duration={dur:.5f},asetpts=PTS-STARTPTS,volume={s.get('ganho_db', 0.0)}dB,"
          f"afade=t=in:d={fi},afade=t=out:st={dur - fo:.5f}:d={fo}")
    vf = (f"trim=start={y:.5f}:duration={dur:.5f},setpts=PTS-STARTPTS," + _filtro_video(s, saida, fonte, enq)
          + (f",fps={fps}" if not fonte.get("cfr", True) else "") + ",format=yuv420p")
    br = "40M" if saida == "V" else "80M"
    # decodificação por software: o VideoToolbox falhou com o H.264 4K desta câmera
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{pre:.3f}", "-i", src, "-map", "0:v:0", "-map", "0:a:0",
           "-vf", vf, "-af", af, "-frames:v", str(s["frames"]),
           "-c:v", "h264_videotoolbox", "-b:v", br, "-pix_fmt", "yuv420p", "-r", f"{fps}",
           "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(destino)]
    subprocess.run(cmd, check=True)


def concatenar(partes: list[Path], destino: Path) -> None:
    lista = destino.with_suffix(".txt")
    gravar_texto(lista, "".join(f"file '{Path(p).resolve()}'\n" for p in partes))
    tmp = destino.with_name(destino.stem + ".tmp.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-map", "0:v", "-map", "0:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(destino)
    lista.unlink(missing_ok=True)


def duracao(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def render(projeto: Path, vid: str, saidas: list[str], preview: bool) -> list[Path]:
    projeto = Path(projeto).resolve()
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
    if not edl:
        raise DIError(f"{vid}: edl.json não existe (F2)")
    src, fonte = fonte_de(projeto)
    fps = fonte["fps"][0] / fonte["fps"][1]
    pasta = projeto / "03_corte" / vid
    (pasta / "segmentos").mkdir(parents=True, exist_ok=True)
    enq = None
    if "V" in saidas and fonte["orientacao"] == "H":
        enq = medir_enquadramento(projeto, vid, edl, fonte, src)
        edl["crop_x"] = enq["crop_x"]
        for s in edl["segmentos"]:
            s["crop_x"] = enq["por_segmento"].get(s["n"]) if enq["por_segmento"] else None
        gravar_json(projeto / "02_decupagem" / vid / "edl.json", edl)
        cfg = config(projeto)
        cfg.setdefault("crop_vertical_por_video", {})[vid] = enq["crop_x"]
        gravar_config(projeto, cfg)
    feitos = []
    checks = []
    for saida in saidas:
        partes = []
        for s in edl["segmentos"]:
            p = pasta / "segmentos" / f"{saida}_{s['n']:03d}.mov"
            render_segmento(src, s, fps, fonte, saida, enq if saida == "V" else enq, p)
            partes.append(p)
        final = pasta / f"corte_v01_{saida}.mp4"
        concatenar(partes, final)
        esperado = edl["frames_total"] / fps
        d = duracao(final)
        ok = abs(d - esperado) <= 1 / fps + 0.010
        checks.append(check("V25_duracao_concat", ok, "BLOCKER", medido=round(d, 3), esperado=f"{esperado:.3f} ± 1 frame",
                            video=vid, saida=saida))
        feitos.append(final)
    if preview and feitos:
        base = feitos[0]
        prev = pasta / "preview_v01.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(base), "-vf", "scale=-2:960", "-c:v", "h264_videotoolbox",
                        "-b:v", "4M", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(prev)], check=True)
        feitos.append(prev)
    registrar_checks(projeto, "F3", checks, alvo=f"03_corte/{vid}/")
    gravar_json(pasta / "render.json", {"edl_assinatura": edl_assinatura(edl), "saidas": saidas, "data": agora(),
                                        "arquivos": [f.name for f in feitos]})
    m = carregar(projeto)
    for f in feitos:
        rel = str(f.relative_to(projeto))
        for a in m.setdefault("artefatos", []):
            if a["caminho"] == rel:
                a["estado"] = "substituido"
        m["artefatos"].append({"caminho": rel, "fase": "F3", "estado": "valido", "data": agora()})
    if fase_fechada(m, "F2"):  # render adiantado (--agora de teste) não mexe na fase
        m["fase_atual"] = "F3"
    salvar(projeto, m)
    return feitos


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di render")
    ap.add_argument("video")
    ap.add_argument("--saida", choices=["V", "H", "ambas"])
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--agora", action="store_true", help="roda em primeiro plano (o job desanexado usa isto)")
    ap.add_argument("--esperar", type=int, default=0)
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    import os
    projeto = achar_projeto(a.projeto)
    saida = a.saida or config(projeto).get("saida") or "ambas"
    saidas = ["V", "H"] if saida == "ambas" else [saida]
    if not os.environ.get("DI_JOB"):
        from portao import cmd_pode, faltas_para_fechar
        if cmd_pode(projeto, "F3") != 0:
            # A prévia é o que o usuário precisa VER para aprovar a F2 (portão dele em `portoes`): ela
            # sai quando a única coisa que falta é a palavra dele. Sem isso o portão pede aprovação de
            # um corte que ninguém pode assistir. O render completo continua esperando a F2 fechar.
            from comum import carregar as _carregar
            faltas_f2 = faltas_para_fechar(projeto, _carregar(projeto), "F2", "usuario")
            if not (a.preview and not faltas_f2):
                raise DIError("render recusado: F2 não está fechada (di portao pode-avancar F3)"
                              + (" — a prévia sai quando só faltar a palavra do usuário" if a.preview else ""))
            print("prévia liberada: os revisores fecharam a F2 e falta só a palavra do usuário — é isto que ele vai ver")
    if not a.agora:
        nome = f"render-{a.video}"
        lancar_job(projeto, nome, ["render", a.video, "--saida", saida, "--agora"] + (["--preview"] if a.preview else []))
        print(f"rodando em segundo plano ({nome}); acompanhe com di status")
        if a.esperar:
            fim = time.time() + min(300, a.esperar)
            while time.time() < fim and carregar(projeto)["jobs"][nome]["status"] == "rodando":
                time.sleep(5)
            print(carregar(projeto)["jobs"][nome]["status"])
        return 0
    nome = f"render-{a.video}"
    try:
        for f in render(projeto, a.video, saidas, a.preview):
            print(f"✓ {f}")
        if carregar(projeto).get("jobs", {}).get(nome, {}).get("status") == "rodando":
            job_marcar(projeto, nome, "ok")
    except Exception as e:
        if carregar(projeto).get("jobs", {}).get(nome):
            job_marcar(projeto, nome, "erro", nota=str(e)[:300])
        raise
    return 0
