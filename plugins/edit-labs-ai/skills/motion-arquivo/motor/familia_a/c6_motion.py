"""
Camada 6 — motion. So curvas: quem chama decide onde aplicar.

palavra   entra a 70% e cresce em ease-out (1 - 0,30*e^(-t/0,083)), amostrado a 10 qps.
          Medido: Foundation 67 -> 93 -> 99 -> 100%; Technologies 74 -> 89 -> 96 -> 99 -> 100%.
caixa     ease-out exponencial ate o alvo, tau 0,392 s, partindo 408 px a direita
          (272 px em 720). As tres caixas vao para quase o mesmo alvo — a escada e so o
          efeito de cada uma ainda estar chegando.
camera    saida em ease-in EXPONENCIAL a partir de 21,67 s: o passo cresce 22 -> 29 -> 39
          -> 52 -> 70 px e o corte cai no chicote. Ajuste: erro 5,4 px nas caixas, 0,4 px nos aneis.
borrao    so acima de 45 px por passo: a borda do original fica nitida ate o penultimo
          passo (rampa 3-5 px) e borra no ultimo (13 px em 720).
radar     um anel ocupa o lugar do seguinte a cada 0,8 s.
"""
import math

PAL_INICIO = 0.70
PAL_TAU = 0.083

CX_AMPL = 408.0          # 272 px em 720
CX_TAU = 0.392
CAM_C = 2.388 * 1.5      # px de 1080
CAM_TAXA = 0.29          # por passo de 0,1 s
BORRAO_LIMIAR = 45.0     # px por passo @1080
BORRAO_GANHO = 0.75


def escala_palavra(t):
    if t < 0:
        return 0.0
    return 1 - (1 - PAL_INICIO) * math.exp(-t / PAL_TAU)


def entrada_caixa(t):
    """Quanto falta ate o alvo (px), t em segundos desde a entrada."""
    return CX_AMPL * math.exp(-t / CX_TAU) if t >= 0 else None


def saida_camera(passos):
    return -CAM_C * (math.exp(CAM_TAXA * max(0.0, passos)) - 1)


def borrao_saida(desloc_no_passo):
    return max(0.0, BORRAO_GANHO * (abs(desloc_no_passo) - BORRAO_LIMIAR))


def fase_radar(t, fase0, periodo=0.8):
    return (fase0 + t / periodo) % 1.0


# --- curvas do Hedy completo ---------------------------------------------------------
def odometro(n):
    """Ano mostrado no quadro n do plano dos anos (1940 -> 1990), medido no original."""
    pontos = [(503, 1940), (506, 1940), (509, 1941), (512, 1945), (515, 1952.5), (518, 1967.5),
              (521, 1977.5), (524, 1982.5), (527, 1985), (530, 1987.5), (533, 1990)]
    xs, ys = zip(*pontos)
    import numpy as _np
    return float(_np.interp(n, xs, ys))


def subida(t, dur=0.40, tau=0.10):
    """Objeto que sobe da borda e assenta (roteador, torpedo): fracao do caminho feito."""
    if t <= 0:
        return 0.0
    return min(1.0, 1 - math.exp(-t / tau)) if t < dur else 1.0


def queda(t, dur=0.50):
    """Torpedo caindo: rotacao (graus, horario) e deslocamento (px) em ease-in."""
    u = min(1.0, max(0.0, t / dur)) ** 2.2
    return 75.0 * u, -260.0 * u, 640.0 * u


def amassar(lay, prog, alvo, semente=5, escala=None, borda=None, rugas=1.0):
    """
    Papel amassando ate virar bola (0 -> 1): rugas crescentes, sombra nas dobras e
    encolhimento ate o ponto `alvo`. No original isso leva 4 degraus (0,4 s), de 15,0 a 15,4 s.

    `escala` troca a curva de encolhimento por um fator fixo; `borda` = (rx, ry, cx, cy) troca
    o contorno circular por um POLIGONO irregular (vertices sorteados em angulo) em
    coordenadas de TELA — o Hedy: a folha continua larga, o desenho quase limpo (`rugas`
    baixo) e so o contorno quebra antes de cair na lixeira.
    """
    import numpy as _np, cv2 as _cv2
    if prog <= 0:
        return lay
    H, W = lay.shape[:2]
    rng = _np.random.default_rng(semente)
    amp = 34.0 * prog ** 1.3 * rugas
    def campo():
        c = rng.normal(0, 1, (H // 60 + 2, W // 60 + 2)).astype(_np.float32)
        return _cv2.resize(c, (W, H), interpolation=_cv2.INTER_CUBIC)
    dx, dy = campo() * amp, campo() * amp
    yy, xx = _np.mgrid[0:H, 0:W].astype(_np.float32)
    out = _cv2.remap(lay, xx + dx, yy + dy, _cv2.INTER_LINEAR, borderMode=_cv2.BORDER_CONSTANT, borderValue=0)
    # dobras: escurece onde o campo de deslocamento muda rapido
    gx = _cv2.Sobel(dx, _cv2.CV_32F, 1, 0, ksize=5); gy = _cv2.Sobel(dy, _cv2.CV_32F, 0, 1, ksize=5)
    dobra = _np.clip(_np.abs(gx) + _np.abs(gy), 0, None); dobra /= (dobra.max() + 1e-6)
    out[..., :3] *= (1 - 0.45 * prog * min(1.0, rugas * 1.5) * dobra)[..., None]
    # borda irregular que fecha em direcao ao alvo
    r = _np.sqrt((xx - alvo[0]) ** 2 + (yy - alvo[1]) ** 2)
    ruido = _cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(_np.float32), (0, 0), 40) * 900
    if borda is None:
        raio = (1 - prog) * 1500 + 140
        out[..., 3] *= _np.clip((raio + ruido - r) / 40, 0, 1)
    # encolhe em direcao ao alvo
    s = (1 - 0.86 * prog ** 0.9) if escala is None else escala
    M = _np.float32([[s, 0, (1 - s) * alvo[0]], [0, s, (1 - s) * alvo[1]]])
    out = _cv2.warpAffine(out, M, (W, H), flags=_cv2.INTER_LINEAR, borderMode=_cv2.BORDER_CONSTANT, borderValue=0)
    if borda is not None:
        rx, ry, cx, cy = borda
        ux, uy = (xx - cx) / rx, (yy - cy) / ry
        rr = _np.sqrt(ux ** 2 + uy ** 2); th = _np.arctan2(uy, ux)
        pol = _np.random.default_rng(semente + 101)
        angs = _np.sort(pol.uniform(-_np.pi, _np.pi, 11)); raios = pol.uniform(0.78, 1.10, 11)
        lim = _np.interp(th, angs, raios, period=2 * _np.pi)
        out[..., 3] *= _np.clip((lim - rr) * min(rx, ry) / 3.0, 0, 1)
        beira = _np.clip(1 - (lim - rr) * min(rx, ry) / 60.0, 0, 1)        # dobra escura junto ao contorno
        out[..., :3] *= (1 - 0.22 * beira)[..., None]
    return out
