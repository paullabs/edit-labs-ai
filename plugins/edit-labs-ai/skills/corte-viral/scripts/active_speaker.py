# -*- coding: utf-8 -*-
"""
Active-speaker-aware vertical framing.

Por que existe: detectar rosto nao basta. Numa mesa com 4 pessoas o enquadramento
precisa seguir QUEM ESTA FALANDO. Este modulo:

  1. detecta rostos com YuNet (CNN) em amostragem densa;
  2. associa deteccoes em tracks (identidade ao longo do plano);
  3. mede energia de movimento da regiao da boca por track;
  4. usa o audio como gate (so pontua onde ha fala);
  5. elege o locutor ativo e devolve um caminho de crop suavizado.

Efeito colateral desejado: uma FOTO de rosto (ex.: uma arte numa tela do
cenario) tem movimento de boca ~0, entao e descartada automaticamente.
"""
from __future__ import annotations
import subprocess, json, math
from dataclasses import dataclass, field

import cv2
import numpy as np

DET_W, DET_H = 960, 540          # resolucao de deteccao (2x menor = 2x mais rapido)
SAMPLE_FPS   = 5.0
SCORE_MIN    = 0.55
TRACK_MAX_D  = 90.0              # px (no espaco DET_W) para associar deteccao a track
MIN_TRACK_FRAMES = 3


@dataclass
class Track:
    cx: float; cy: float; w: float; h: float
    frames: list = field(default_factory=list)      # (t, cx, cy, w, h)
    mouth_prev: np.ndarray | None = None
    motion: list = field(default_factory=list)      # (t, energia)
    misses: int = 0

    def update(self, t, cx, cy, w, h):
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.frames.append((t, cx, cy, w, h)); self.misses = 0


def _mouth_patch(gray, cx, cy, w, h):
    """Regiao da boca: terco inferior central da caixa do rosto."""
    x0 = int(cx - 0.25*w); x1 = int(cx + 0.25*w)
    y0 = int(cy + 0.05*h); y1 = int(cy + 0.42*h)
    x0, y0 = max(0,x0), max(0,y0)
    x1, y1 = min(gray.shape[1],x1), min(gray.shape[0],y1)
    if x1-x0 < 6 or y1-y0 < 6: return None
    p = gray[y0:y1, x0:x1]
    return cv2.resize(p, (32,24)).astype(np.float32)


def analyze_shot(src, t0, t1, model_path, silences=None, det_w=DET_W, det_h=DET_H):
    """Devolve (tracks, escala) para o intervalo [t0,t1]."""
    dur = max(0.05, t1 - t0)
    cmd = ["ffmpeg","-nostdin","-ss",f"{t0:.3f}","-i",src,"-t",f"{dur:.3f}",
           "-vf",f"fps={SAMPLE_FPS},scale={det_w}:{det_h}",
           "-f","rawvideo","-pix_fmt","bgr24","-"]
    p = subprocess.run(cmd, capture_output=True)
    fsize = det_w*det_h*3
    n = len(p.stdout)//fsize
    if n == 0: return [], 1.0

    det = cv2.FaceDetectorYN.create(model_path,"",(det_w,det_h),
                                    score_threshold=SCORE_MIN, nms_threshold=0.3, top_k=20)
    tracks: list[Track] = []
    for i in range(n):
        t = t0 + i/SAMPLE_FPS
        frame = np.frombuffer(p.stdout[i*fsize:(i+1)*fsize], np.uint8).reshape(det_h,det_w,3)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        det.setInputSize((det_w,det_h))
        _, faces = det.detect(frame)
        dets = []
        if faces is not None:
            for f in faces:
                x,y,w,h = f[:4]
                dets.append((x+w/2, y+h/2, w, h))
        # associacao gulosa por proximidade
        used=set()
        for tr in tracks:
            best=None; bestd=TRACK_MAX_D
            for j,(cx,cy,w,h) in enumerate(dets):
                if j in used: continue
                d = math.hypot(cx-tr.cx, cy-tr.cy)
                if d < bestd: bestd=d; best=j
            if best is None:
                tr.misses += 1
                continue
            used.add(best)
            cx,cy,w,h = dets[best]
            tr.update(t,cx,cy,w,h)
            patch = _mouth_patch(gray,cx,cy,w,h)
            if patch is not None:
                if tr.mouth_prev is not None and tr.mouth_prev.shape==patch.shape:
                    e = float(np.mean(np.abs(patch - tr.mouth_prev)))
                    tr.motion.append((t,e))
                tr.mouth_prev = patch
        for j,(cx,cy,w,h) in enumerate(dets):
            if j in used: continue
            tr = Track(cx,cy,w,h); tr.update(t,cx,cy,w,h)
            tr.mouth_prev = _mouth_patch(gray,cx,cy,w,h)
            tracks.append(tr)
    tracks = [t for t in tracks if len(t.frames) >= MIN_TRACK_FRAMES]
    return tracks, det_w


def audio_envelope(src, t0, t1, fps=SAMPLE_FPS):
    """Envelope RMS do audio amostrado na MESMA taxa dos frames."""
    dur = max(0.05, t1-t0)
    sr = 16000
    cmd=["ffmpeg","-nostdin","-ss",f"{t0:.3f}","-i",src,"-t",f"{dur:.3f}",
         "-vn","-ac","1","-ar",str(sr),"-f","s16le","-"]
    p=subprocess.run(cmd,capture_output=True)
    a=np.frombuffer(p.stdout,np.int16).astype(np.float32)/32768.0
    if a.size==0: return np.zeros(0)
    hop=int(sr/fps)
    n=a.size//hop
    return np.array([float(np.sqrt(np.mean(a[i*hop:(i+1)*hop]**2)+1e-12)) for i in range(n)])


def _corr(x, y):
    """Pearson; 0 se variancia nula."""
    n=min(len(x),len(y))
    if n < 4: return 0.0
    x=np.asarray(x[:n],float); y=np.asarray(y[:n],float)
    sx, sy = x.std(), y.std()
    if sx < 1e-9 or sy < 1e-9: return 0.0
    return float(np.mean((x-x.mean())*(y-y.mean()))/(sx*sy))


def _speaking(t, silences):
    if not silences: return True
    for a,b in silences:
        if a <= t <= b: return False
    return True


def score_tracks(tracks, silences, env=None, t0=None):
    """Pontua cada track por CORRELACAO entre movimento de boca e energia do audio.

    Movimento alto sozinho nao basta: uma tela do cenario exibindo video tambem
    'mexe a boca'. O que distingue o locutor real e a boca se mover
    QUANDO o audio sobe e parar QUANDO o audio cai."""
    out=[]
    for tr in tracks:
        vals=[e for (t,e) in tr.motion if _speaking(t,silences)]
        motion = 0.0
        if vals:
            vals=sorted(vals); k=max(1,int(len(vals)*0.4))
            motion=float(np.mean(vals[k:]))

        corr=0.0
        if env is not None and len(env)>0 and tr.motion:
            idx=[int(round((t-t0)*SAMPLE_FPS)) for (t,_) in tr.motion]
            m=[e for (_,e) in tr.motion]
            a=[env[i] for i in idx if 0<=i<len(env)]
            m=[m[j] for j,i in enumerate(idx) if 0<=i<len(env)]
            corr=_corr(m,a)

        area=float(np.mean([w*h for (_,_,_,w,h) in tr.frames]))
        # score final: correlacao manda; movimento entra como desempate leve
        score = corr*1.0 + min(motion,30.0)/30.0*0.25
        out.append({"track":tr,"score":score,"corr":corr,"speech_motion":motion,
                    "area":area,"n":len(tr.frames),
                    "cx":float(np.median([c for (_,c,_,_,_) in tr.frames])),
                    "cy":float(np.median([c for (_,_,c,_,_) in tr.frames]))})
    return out
