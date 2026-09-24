#!/usr/bin/env python3
"""
Desfaz a tela dividida de um vertical feito com o antigo layout `split` (quadro inteiro em cima, plano do locutor
embaixo), sem mexer em tempo nem áudio: nos quadros divididos, a metade de baixo vira a tela toda, num recorte 9:16
centrado no rosto (YuNet), ampliado para o tamanho do vertical. O QR code da gravação fica fora do recorte quando dá
para deixar o rosto com folga. Os quadros divididos são achados no próprio vídeo pela emenda horizontal, quadro a
quadro (numeração exata, sem duplicar quadro na leitura), e cada trecho é partido nos cortes de câmera.

    cv-desdividir ENTRADA.mp4 SAIDA.mp4 [--medir]

--medir só mede e imprime os trechos. A emenda fica na altura natural do quadro inteiro em cima (608 px para fonte
1920x1080 num vertical 1080x1920); ajuste TOP se a fonte tiver outro aspecto.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

MOD = os.environ.get("CV_YUNET") or str(Path(__file__).resolve().parents[1] / "models" / "face_detection_yunet_2023mar.onnx")
TOP, W, H = 608, 1080, 1920
BW = int(round((H - TOP) * 9 / 16 / 2)) * 2          # 738: largura 9:16 da metade de baixo


def emendas(src):
    """Razão emenda/fundo por quadro, na faixa y 596–620 (largura reduzida só na horizontal)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-fps_mode", "passthrough", "-vf", "crop=1080:24:0:596,scale=270:24,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 24, 270).astype(np.float32)
    seam = np.abs(a[:, 11] - a[:, 12]).mean(1)
    fundo = (np.abs(a[:, 3] - a[:, 4]).mean(1) + np.abs(a[:, 19] - a[:, 20]).mean(1)) / 2 + 1.0
    return seam / fundo


def cortes_baixo(src):
    """Quadros onde a metade de baixo troca de plano (corte seco): diferença média entre quadros vizinhos em baixa resolução."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-fps_mode", "passthrough", "-vf", f"crop={W}:{H - TOP}:0:{TOP},scale=135:164,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 164, 135).astype(np.float32)
    d = np.r_[0.0, np.abs(np.diff(a, axis=0)).mean((1, 2))]
    lim = max(18.0, 5.0 * float(np.median(d)))
    return set(np.nonzero(d > lim)[0].tolist())


def trechos(r, lim=3.0, min_q=6):
    """Sequências de quadros divididos (razão > lim), fechando buracos de até 2 quadros."""
    m = r > lim
    for i in range(1, len(m) - 2):                      # buraco curto dentro de um trecho dividido
        if not m[i] and m[i - 1] and (m[i + 1] or m[i + 2]):
            m[i] = True
    out, i = [], 0
    while i < len(m):
        if m[i]:
            j = i
            while j + 1 < len(m) and m[j + 1]:
                j += 1
            if j - i + 1 >= min_q:
                out.append([i, j])
            i = j + 1
        else:
            i += 1
    return out


def quadro(src, n, fps):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{n / fps:.4f}", "-i", str(src), "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True).stdout
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


def enquadrar(src, a, b, fps):
    """x0 do recorte (largura BW) para o trecho [a, b]: centro no maior rosto; QR code fora quando possível, esteja
    ele à esquerda ou à direita do rosto, desde que o rosto fique com folga dentro do recorte."""
    det = cv2.FaceDetectorYN.create(MOD, "", (540, 656), 0.6, 0.3, 5000)
    qr = cv2.QRCodeDetector()
    cxs, qr_esq, qr_dir = [], W, 0
    for n in np.linspace(a, b, 5).astype(int):
        im = quadro(src, int(n), fps)
        if im is None:
            continue
        baixo = im[TOP:H]
        _, f = det.detect(cv2.resize(baixo, (540, 656)))
        if f is not None and len(f):
            g = max(f, key=lambda r: r[2] * r[3])
            cxs.append((g[0] + g[2] / 2) * 2)
        ok, pts = qr.detect(baixo)
        if ok and pts is not None:
            qr_esq = min(qr_esq, int(pts[0][:, 0].min()) - 12)
            qr_dir = max(qr_dir, int(pts[0][:, 0].max()) + 12)
    cx = float(np.median(cxs)) if cxs else W / 2
    x0 = int(np.clip(cx - BW / 2, 0, W - BW))
    folga = 0.10 * BW
    if qr_dir and qr_dir <= cx:                         # QR à esquerda do rosto: o recorte começa depois dele
        if x0 < qr_dir <= W - BW and cx - qr_dir >= folga:
            x0 = qr_dir
    elif qr_dir and qr_esq >= cx:                       # QR à direita do rosto: o recorte termina antes dele
        if x0 + BW > qr_esq >= BW and qr_esq - cx >= folga:
            x0 = qr_esq - BW
    return x0 // 2 * 2, round(cx), (max(qr_esq, 0), qr_dir) if qr_dir else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 1 or ("--medir" not in sys.argv and len(args) < 2):
        sys.exit(__doc__)
    src = Path(args[0]).resolve()
    fps_s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of",
                            "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip()
    num, den = (int(x) for x in fps_s.split("/"))
    fps = num / den
    r = emendas(src)
    cz = cortes_baixo(src)
    tr = []
    for a, b in trechos(r):
        ini = a
        for c in sorted(x for x in cz if a < x <= b):
            if c - ini >= 3:
                tr.append((ini, c - 1)); ini = c
        if tr and b - ini < 3 and tr[-1][1] == ini - 1:
            tr[-1] = (tr[-1][0], b)
        else:
            tr.append((ini, b))
    info = []
    for a, b in tr:
        x0, cx, q = enquadrar(src, a, b, fps)
        info.append(dict(q0=a, q1=b, t0=round(a / fps, 3), t1=round((b + 1) / fps, 3), x0=x0, rosto_x=cx, qr=q))
    print(f"{src.name}: {len(info)} trechos divididos, {sum(x['q1'] - x['q0'] + 1 for x in info) / fps:.2f} s de {len(r) / fps:.1f} s")
    for x in info:
        qr = f"QR em x {x['qr'][0]}–{x['qr'][1]}" if x["qr"] else "sem QR"
        print(f"   {x['t0']:7.2f}–{x['t1']:7.2f} s  x0={x['x0']}  rosto_x={x['rosto_x']}  {qr}")
    if "--medir" in sys.argv:
        return
    dst = Path(args[1]).resolve()
    if not info:
        shutil.copy2(src, dst)
        return
    xexpr = str(info[-1]["x0"])
    for x in reversed(info[:-1]):
        xexpr = f"if(between(n,{x['q0']},{x['q1']}),{x['x0']},{xexpr})"
    en = "+".join(f"between(n,{x['q0']},{x['q1']})" for x in info)
    fc = (f"[0:v]split=2[a][b];[b]crop={BW}:{H - TOP}:'{xexpr}':{TOP},scale={W}:{H}:flags=lanczos,setsar=1[c];"
          f"[a][c]overlay=0:0:enable='{en}',format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-c:a", "copy", "-movflags", "+faststart", str(dst)],
                   check=True)
    print(f"   -> {dst}")


if __name__ == "__main__":
    main()
