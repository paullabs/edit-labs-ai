#!/usr/bin/env python3
"""
Procura QR code visível num vídeo. Transmissão de podcast costuma ter arte fixa no canto de uma das câmeras
(QR de patrocínio, Pix da live), e o recorte vertical desse plano pode carregá-la sem ninguém perceber.

    cv-conferir-qr VIDEO.mp4 [--qps 10] [--min 1]

Lê o vídeo a --qps quadros por segundo, em meia resolução, e junta os quadros com QR em trechos. Um trecho só é
acusado se o QR for decodificado em resolução cheia em algum quadro dele, ou se durar pelo menos --min segundos:
o detector sozinho dá falso positivo de um quadro em textura (papel, tecido, grade). Sai com código 1 se acusar
algum trecho, 0 se o vídeo estiver limpo.
"""
import argparse
import json
import subprocess
import sys

import cv2
import numpy as np


def sonda(video):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "json", video], capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def quadro_cheio(video, t):
    png = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    if not png:
        return None
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


def main():
    ap = argparse.ArgumentParser(description="Procura QR code visível num vídeo.")
    ap.add_argument("video")
    ap.add_argument("--qps", type=float, default=10.0, help="quadros lidos por segundo (padrão 10)")
    ap.add_argument("--min", type=float, default=1.0, dest="minimo",
                    help="duração mínima, em s, para acusar um QR que não foi decodificado (padrão 1)")
    a = ap.parse_args()
    video, qps, minimo = a.video, a.qps, a.minimo
    w, h = sonda(video)
    w2, h2 = w // 4 * 2, h // 4 * 2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={qps},scale={w2}:{h2},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    quadros = np.frombuffer(raw, np.uint8).reshape(-1, h2, w2)
    det = cv2.QRCodeDetector()
    hits = [i for i, q in enumerate(quadros) if det.detect(q)[0]]

    trechos = []                                         # quadros com QR, tolerando 1 amostra de buraco
    for i in hits:
        if trechos and i - trechos[-1][1] <= 2:
            trechos[-1][1] = i
        else:
            trechos.append([i, i])

    acusados = []
    for i0, i1 in trechos:
        t0, t1 = i0 / qps, (i1 + 1) / qps
        texto = ""
        for t in sorted({t0 + 0.5 / qps, (t0 + t1) / 2, t1 - 0.5 / qps}):
            im = quadro_cheio(video, t)
            if im is None:
                continue
            txt, pts, _ = det.detectAndDecode(im)
            if txt:
                texto = txt
                break
        if texto or t1 - t0 >= minimo:
            acusados.append((t0, t1, texto))

    print(f"{video}: {len(quadros)} quadros lidos a {qps:g} qps; "
          f"{'nenhum QR' if not acusados else f'{len(acusados)} trecho(s) com QR'}")
    for t0, t1, texto in acusados:
        if texto:
            print(f"   {t0:7.2f}–{t1:7.2f} s  QR decodificado: {texto[:70]!r}")
        else:
            print(f"   {t0:7.2f}–{t1:7.2f} s  QR provável (visto por {t1 - t0:.1f} s, não decodificado)")
    sys.exit(1 if acusados else 0)


if __name__ == "__main__":
    main()
