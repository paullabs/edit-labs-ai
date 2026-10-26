"""
Família A + vídeo — o b-roll gerado (paisagem, cenário) entra na grade de 10 qps da série.

  video_clip   toca um trecho de um clipe de vídeo preenchendo a tela vertical, no mesmo relógio do resto do vídeo
               (um degrau a cada 3 quadros, sem interpolar), com a cor puxada para o look documental (dessaturada,
               contraste leve, vinheta). A câmera anda por cima (empurrão suave). Aceita `palavras_grandes`
               e `rodape`, como qualquer plano.

Parâmetros do plano:
  clip      caminho do .mp4 (absoluto ou relativo ao diretório de trabalho)
  ss        segundo do clipe em que o plano começa (padrão 0)
  vel       velocidade de reprodução (1.0; 0.8 estica um clipe curto)
  zoom      [z0, z1] empurrão extra da câmera sobre o clipe (padrão [1.0, 1.06])
  ponto     [x, y] do centro do empurrão na tela (padrão o meio)
  sat       saturação (0.82), ganho (1.0), vinheta (0.28), gama (1.0: >1 clareia a filmagem noturna)
  foco      vídeo horizontal (16:9) no quadro vertical: onde fica o recorte 9:16 na largura da fonte, 0 a 1. Um número
            (fixo) ou [[t, x], ...] para acompanhar a ação (t em segundos do plano, já contando `vel`). Sem `foco`,
            o recorte é o do meio (como antes).
  foco_y    altura do centro do recorte (0 a 1, padrão 0,5), quando `aproxima` > 1
  aproxima  zoom na fonte antes de escalar (1 = a altura inteira da fonte; 1,5 = 2/3 da altura); a fonte 4K aguenta
            ~1,8 sem perder nitidez no 1080x1920
  congela   segundo do plano em que a filmagem para (o quadro fica; a câmera e o desenho continuam) — o "congela e
            explica" da telestração (v12.7)
  desenhos  telestração por cima da filmagem, antes do empurrão da câmera: ver motor/desenho.py
O clipe congela no último quadro se o plano durar mais que o trecho disponível.

  tela_dividida  duas filmagens para comparar (v12.7: o carro nos jatos x o foguete pousando).
               `lados` = [{clip, ss, vel, foco, foco_y, aproxima, sat, gama, congela}, {...}].
               `modo` "lado_a_lado" (cada um 540x1920; `entra` faz o direito deslizar da direita; `divisor` = linha
               branca do meio), "empilhada" (1080x960 em cima e embaixo) ou "janela": o primeiro lado enche a tela e o
               segundo entra numa janela de cantos redondos (`caixa` [x, y, w, h], `raio`, `borda` branca, sombra),
               descendo de cima em `entra` quadros. Aceita `desenhos` (camada "cena") e palavras grandes.
"""
import subprocess

import cv2
import numpy as np

from familia_a import W, H
from familia_a.tempo import FPS
from familia_a import tempo
from planos import u, zoom_em
from familia_a import c5_movimentos as mv
import desenho
from familia_a.compor import sobre


def _vinheta():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return np.clip(r - 0.55, 0, None) ** 1.6


def _tamanho(caminho):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(caminho)], capture_output=True, text=True, check=True).stdout
    w, h = (int(v) for v in r.strip().split(",")[:2])
    return w, h


def _expr_foco(foco, vel, larg_fonte, larg_corte):
    """x do canto do recorte em função de t (segundos da fonte desde ss), interpolando os pontos [[t_plano, x], ...]."""
    pts = [(0.0, float(foco))] if isinstance(foco, (int, float)) else [(float(t) * vel, float(x)) for t, x in foco]
    px = [(t, x * larg_fonte - larg_corte / 2) for t, x in pts]
    lim = f"{larg_fonte - larg_corte:.2f}"
    if len(px) == 1:
        return f"clip({px[0][1]:.2f},0,{lim})"
    expr = f"{px[-1][1]:.2f}"
    for (t0, x0), (t1, x1) in reversed(list(zip(px[:-1], px[1:]))):
        expr = f"if(lt(t,{t1:.4f}),{x0:.2f}+({x1 - x0:.2f})*clip((t-{t0:.4f})/{t1 - t0:.4f},0,1),{expr})"
    return f"clip({expr},0,{lim})"


def _decodificar(caminho, ss, qps_fonte, n_quadros, sat, p=None, alvo=(W, H)):
    """Quadros do clipe (n, h, w, 3) uint8, amostrados a `qps_fonte`, cobrindo `alvo` (a tela inteira, ou meia na tela
    dividida): corte central, ou o recorte guiado por `foco` / `aproxima` do plano."""
    p = p or {}
    AW, AH = alvo
    gama = float(p.get("gama", 1.0))
    cor = f"eq=saturation={sat}:contrast=1.04" + (f":gamma={gama:.3f}" if abs(gama - 1.0) > 1e-3 else "")
    if p.get("foco") is None and float(p.get("aproxima", 1.0)) == 1.0:
        filtro = (f"fps={qps_fonte:.4f},scale={AW}:{AH}:force_original_aspect_ratio=increase:flags=lanczos,crop={AW}:{AH},"
                  f"{cor}")
    else:
        lw, lh = _tamanho(caminho)
        ch = lh / float(p.get("aproxima", 1.0))
        cw = ch * AW / AH
        if cw > lw:
            cw = float(lw); ch = cw * AH / AW
        x = _expr_foco(p.get("foco", 0.5), float(p.get("vel", 1.0)), lw, cw)
        y = min(max(float(p.get("foco_y", 0.5)) * lh - ch / 2, 0.0), lh - ch)
        filtro = (f"fps={qps_fonte:.4f},crop={cw:.2f}:{ch:.2f}:'{x}':{y:.2f},scale={AW}:{AH}:flags=lanczos,{cor}")
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-i", str(caminho), "-vf", filtro,
                          "-frames:v", str(n_quadros), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(pcm, np.uint8)
    n = len(a) // (AW * AH * 3)
    if n == 0:
        raise RuntimeError(f"nenhum quadro decodificado de {caminho}")
    return a[: n * AW * AH * 3].reshape(n, AH, AW, 3)


def _degrau(n, p, lado=None):
    """Índice do quadro decodificado mostrado no quadro n (com `congela`: para naquele segundo do plano)."""
    k = max(0, (n - p["inicio"]) // tempo.PASSO)
    c = (lado or p).get("congela")
    if c is not None:
        k = min(k, int(round(float(c) * FPS / tempo.PASSO)))
    return k


def video_clip(n, p, ctx):
    passo = tempo.PASSO
    vel = float(p.get("vel", 1.0))
    ss = float(p.get("ss", 0.0))
    passos = (p["fim"] - p["inicio"]) // passo + 2
    qps_fonte = (FPS / passo) / vel
    quadros = ctx.cache("clip", lambda: _decodificar(p["clip"], ss, qps_fonte, passos, p.get("sat", 0.82), p))
    k = min(len(quadros) - 1, _degrau(n, p))
    img = quadros[k].astype(np.float32) * float(p.get("ganho", 1.0))
    vg = ctx.cache("vinheta", _vinheta)
    img *= (1.0 - float(p.get("vinheta", 0.28)) * vg)[..., None]
    img = desenho.aplicar(img, n, p, ctx, "cena")
    z0, z1 = p.get("zoom", (1.0, 1.06))
    z = z0 + (z1 - z0) * mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "s", 1.8)
    cx, cy = p.get("ponto", (W / 2, H / 2))
    return zoom_em(np.clip(img, 0, 255), z, (cx, cy))


def _lado(n, p, ctx, i, lado, alvo):
    passo = tempo.PASSO
    vel = float(lado.get("vel", 1.0))
    passos = (p["fim"] - p["inicio"]) // passo + 2
    quadros = ctx.cache(("lado", i), lambda: _decodificar(lado["clip"], float(lado.get("ss", 0.0)), (FPS / passo) / vel,
                                                          passos, lado.get("sat", 0.82), lado, alvo=alvo))
    k = min(len(quadros) - 1, _degrau(n, p, lado))
    return quadros[k].astype(np.float32) * float(lado.get("ganho", 1.0))


def _cantos(w, h, r):
    m = np.ones((h, w), np.float32)
    yy, xx = np.mgrid[:h, :w].astype(np.float32)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        canto = ((xx < r) if cx == r else (xx > w - r - 1)) & ((yy < r) if cy == r else (yy > h - r - 1))
        d = np.hypot(xx - cx, yy - cy)
        m[canto] = np.clip(r - d[canto] + 0.5, 0, 1)
    return m


def tela_dividida(n, p, ctx):
    modo = p.get("modo", "lado_a_lado")
    entra = int(p.get("entra", 0))
    g_ent = mv.suavizar_curva(min(1.0, (n - p["inicio"]) / float(entra)), "saida", 3.0) if entra else 1.0
    if modo == "janela":
        img = _lado(n, p, ctx, 0, p["lados"][0], (W, H))
        x, y, w, h = [int(v) for v in p["caixa"]]
        jan = _lado(n, p, ctx, 1, p["lados"][1], (w, h))
        r, b = int(p.get("raio", 28)), int(p.get("borda", 8))
        y = int(round(y - (1 - g_ent) * (y + h + 60)))                 # desce de cima
        m = ctx.cache(("cantos", w, h, r), lambda: _cantos(w, h, r))
        mb = ctx.cache(("cantos", w + 2 * b, h + 2 * b, r + b), lambda: _cantos(w + 2 * b, h + 2 * b, r + b))
        som = ctx.cache(("sombra", w, h, b), lambda: cv2.GaussianBlur(np.pad(mb, 40), (0, 0), 16.0))
        xs, ys = x - b - 40 + 10, y - b - 40 + 22
        xa, ya, xb, yb = max(0, xs), max(0, ys), min(W, xs + som.shape[1]), min(H, ys + som.shape[0])
        if xa < xb and ya < yb:
            img[ya:yb, xa:xb] *= (1 - 0.55 * som[ya - ys:yb - ys, xa - xs:xb - xs])[..., None]
        lay = np.zeros((h + 2 * b, w + 2 * b, 4), np.float32)
        lay[..., :3] = (244.0, 242.0, 234.0)
        lay[..., 3] = mb
        lay[b:b + h, b:b + w, :3] = lay[b:b + h, b:b + w, :3] * (1 - m[..., None]) + jan * m[..., None]
        sobre(img, lay, x - b, y - b)
    else:
        img = np.zeros((H, W, 3), np.float32)
        if modo == "empilhada":
            for i, lado in enumerate(p["lados"]):
                q = _lado(n, p, ctx, i, lado, (W, H // 2))
                img[i * (H // 2):(i + 1) * (H // 2)] = q
        else:
            meia = W // 2
            for i, lado in enumerate(p["lados"]):
                q = _lado(n, p, ctx, i, lado, (meia, H))
                x0 = i * meia if i == 0 else int(round(meia + (1 - g_ent) * meia))
                if x0 < W:
                    img[:, x0:min(W, x0 + meia)] = q[:, :min(meia, W - x0)]
        vg = ctx.cache("vinheta", _vinheta)
        img *= (1.0 - float(p.get("vinheta", 0.22)) * vg)[..., None]
        esp = int(p.get("divisor", 8))
        if esp and modo == "empilhada":
            img[H // 2 - esp // 2:H // 2 + esp - esp // 2] = (244.0, 242.0, 234.0)
        elif esp:
            xm = int(round(W // 2 + (1 - g_ent) * W // 2))
            img[:, max(0, xm - esp // 2):min(W, xm + esp - esp // 2)] = (244.0, 242.0, 234.0)
    if modo == "janela":
        vg = ctx.cache("vinheta", _vinheta)
        img *= (1.0 - float(p.get("vinheta", 0.18)) * vg)[..., None]
    img = desenho.aplicar(img, n, p, ctx, "cena")
    z0, z1 = p.get("zoom", (1.0, 1.03))
    z = z0 + (z1 - z0) * mv.suavizar_curva(u(n, p["inicio"], p["fim"]), "s", 1.8)
    return zoom_em(np.clip(img, 0, 255), z, tuple(p.get("ponto", (W / 2, H / 2))))


TIPOS_VIDEO = {"video_clip": video_clip, "tela_dividida": tela_dividida}
