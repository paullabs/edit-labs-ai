"""Conferência do vídeo pronto: quadros borrados fora do lugar e saltos bruscos.

    clpy qa.py video.mp4 [inicio-fim de transição em s, ...]

Mede a nitidez (variância do Laplaciano) de cada desenho em resolução reduzida e aponta os desenhos com menos de 45% da
nitidez mediana do segundo em volta, fora das janelas de transição informadas."""
import sys
import subprocess

import cv2
import numpy as np


def nitidez(video, w=270, h=480):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt",
                          "gray", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w)
    return np.array([cv2.Laplacian(f, cv2.CV_32F).var() for f in fr])


def suspeitos(video, janelas=(), fps=28):
    v = nitidez(video)
    out = []
    for i in range(0, len(v), 2):
        t = i / fps
        if any(a - 0.05 <= t <= b + 0.05 for a, b in janelas):
            continue
        viz = v[max(0, i - fps):i + fps]
        if v[i] < 0.45 * np.median(viz):
            out.append((round(t, 2), round(float(v[i]), 1), round(float(np.median(viz)), 1)))
    return out


if __name__ == "__main__":
    jan = [tuple(map(float, x.split("-"))) for x in sys.argv[2:]]
    for s in suspeitos(sys.argv[1], jan):
        print(s)
