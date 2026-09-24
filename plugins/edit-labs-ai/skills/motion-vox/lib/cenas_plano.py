#!/usr/bin/env python3
"""
Motor de cenas por dados (opcional ao compose_template). Cada cena é uma lista de BEATS; cada beat é uma lista de ITENS
ancorados em palavras do transcript do próprio clipe (`cenas.tp`). Toda a mecânica da identidade continua em `kit`,
`voxlab` e `cenas`; aqui só se junta.

Regras que o motor faz cumprir (referências da motion-vox):
- herói já em voo no quadro 0 do beat (item sem `at`);
- um beat = uma ideia, corte seco/flash entre beats (`cenas.sequencia`);
- texto só em PIL (marcador/etiqueta), nunca do gerador; número estimado vai a mão;
- overlay: objeto pequeno em canto livre (fora do rosto e da faixa da legenda), com sombra de "sobre vídeo".

Item (cutaway) — chaves comuns: `k` (tipo), `at` = segundos | (palavra, depois_de[, True p/ fim]), `lead` (quadros
de antecedência), `id` (para outros itens ancorarem):
  asset   name w (x,y) rot=0 queda=200 sombra="tall|card|paper" kind="obj|paper" slide=(dx,dy) slide_at=palavra
  logo    name w (x,y) rot disc=raio
  card    photo w (x,y) rot margin bottom circle=(fx,fy,rx,ry) circle_at=palavra
  etiqueta text (x,y) tam rot seed
  marcador text (x,y) tam cor seed
  circle  (x,y,rx,ry) cor seed
  arrow   pts cor seed dur
  cross   (x,y,s) cor
  strike  (x1,x2,y) cor
  pie     (x,y,r) frac
  bar     (x,y,w,h) cor  (barra de marcador hachurada)
  disc    (x,y) r
  stamp   text (x,y) corpo rot
Beat: dict(items=[...], at=None|palavra, bg="paper|dark", cam=(ganho, (fx,fy)), n=frames_da_camera, props=bool)
      ou dict(full="PH_x", vin=0.55, push=0.05, dim=0.0, focus=(0.5,0.5), items=[...])  # foto em tela cheia
      ou dict(video="08-B1", va=0.0, vel=1.0, vin=0.30, dim=0.0, items=[...])          # B-roll gerado em tela cheia
         (07_assets/broll/<video>.mp4; `va` = segundo do vídeo onde o beat começa, `vel` < 1 estica o trecho).
         O vídeo roda na cadência dele (o render passa a 24 qps dentro do beat); os itens por cima seguem nos 12.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from kit import *            # noqa: F401,F403
import kit as K
import voxlab as V
import cenas as S
from cenas import tp, fr

SOMBRAS = dict(tall=K.SH_TALL, card=K.SH_CARD, paper=K.SH_PAPER, onvid=K.SH_ONVID)
COR = dict(ink=INK, red=RED, yellow=YELLOW, blue=BLUE)


def T(a):
    """segundos do clipe: número, ou (palavra, depois_de[, fim])."""
    if isinstance(a, (int, float)):
        return float(a)
    return tp(a[0], a[1], bool(len(a) > 2 and a[2]))


def _cor(x):
    return COR.get(x, x) if isinstance(x, str) else (x or INK)


def _fa(it, t0):
    a = it.get("at")
    return -8.0 if a is None else fr(T(a), t0) - it.get("lead", 3)


# ---------------------------------------------------------------------------------------------- props
def _props(c, seed):
    if seed % 3 == 0:
        V.place(c, K.piece("A10_SCRAPS", seed % 4, 168, rotation=-9), (-58, 1560), shadow=SH_PAPER)
        V.place(c, K.piece("A04_CLIPS", 0, 120, rotation=24), (-30, 520), shadow=SH_PAPER)
    elif seed % 3 == 1:
        V.place(c, K.piece("A10_SCRAPS", seed % 4, 180, rotation=12), (900, 250), shadow=SH_PAPER)
        V.place(c, K.piece("A04_CLIPS", 1, 118, rotation=-20), (1000, 1560), shadow=SH_PAPER)
    else:
        V.place(c, K.piece("A10_SCRAPS", seed % 4, 170, rotation=-4), (-40, 300), shadow=SH_PAPER)


# ---------------------------------------------------------------------------------------------- itens
def _draw(c, it, f, t0, anch):
    k = it["k"]
    fa = _fa(it, t0)
    pr = K.p(f, fa - 4, fa + 6)
    if k in ("asset", "logo", "card", "santinho", "recorte"):
        if k == "santinho":
            layer = S.santinho(it["raw"], it["cargo"], it["w"], rot=it.get("rot", 0), foco_y=it.get("foco_y", 0.30))
            kind = "paper"
        elif k == "recorte":
            layer = S.recorte_pessoa(it["name"], it["w"], seed=it.get("seed", 3))
            kind = "obj"
        elif k == "asset":
            layer = K.asset(it["name"], it["w"], rotation=it.get("rot", 0))
            kind = it.get("kind", "obj")
        elif k == "logo":
            layer = S.cartao_logo(it["name"], it["w"], rot=it.get("rot", 0))
            kind = "paper"
        else:
            layer, geo = K.photo_card_custom(it["photo"], it["w"], margin=it.get("margin", 0.055),
                                             bottom=it.get("bottom", 0.16), rotation=it.get("rot", 0))
            kind = "paper"
        x, y = it["xy"]
        if it.get("slide") and it.get("slide_at"):
            s = K.p(f, fr(T(it["slide_at"]), t0) - 2, fr(T(it["slide_at"]), t0) + 14)
            x += it["slide"][0] * s * s
            y += it["slide"][1] * s * s
        if it.get("disc"):
            S.disco(c, x, y, it["disc"], K.p(f, fa - 6, fa + 4), seed=it.get("seed", 9))
        pos = S.pousa(c, layer, x, y, pr, sombra=SOMBRAS[it.get("sombra", "card" if k not in ("asset", "recorte") else "tall")],
                      queda=it.get("queda", 200), kind=kind)
        if pos is not None:
            anch[it.get("id", it.get("name", it.get("photo")))] = (pos, layer.size)
            if k == "card" and it.get("circle"):
                fx, fy, rx, ry = it["circle"]
                ca = fr(T(it["circle_at"]), t0) if it.get("circle_at") else fa + 6
                px, py, pw, ph = geo
                c.alpha_composite(V.hand_circle(c.size, pos[0] + px + pw * fx, pos[1] + py + ph * fy, pw * rx, ph * ry,
                                                progress=K.d(f, ca - 4, ca + 8), passes=2, width=9,
                                                color=_cor(it.get("cor", "yellow")), seed=31, amp=7))
    elif k == "etiqueta":
        S.etiqueta(c, it["text"], it["xy"][0], it["xy"][1], K.p(f, fa - 2, fa + 10), tam=it.get("tam", 66),
                   rot=it.get("rot", -1.5), seed=it.get("seed", 13), sombra=it.get("sombra", False))
    elif k == "marcador":
        S.marcador(c, it["text"], it["xy"][0], it["xy"][1], K.d(f, fa - 2, fa + it.get("dur", 12)),
                   tam=it.get("tam", 96), seed=it.get("seed", 21), cor=_cor(it.get("cor")) if it.get("cor") else None)
    elif k == "circle":
        x, y, rx, ry = it["xy"]
        c.alpha_composite(V.hand_circle(c.size, x, y, rx, ry, progress=K.d(f, fa - 4, fa + 8), passes=2, width=it.get("width", 8),
                                        color=_cor(it.get("cor", "yellow")), seed=it.get("seed", 31), amp=7))
    elif k == "arrow":
        c.alpha_composite(V.hand_arrow(c.size, it["pts"], progress=K.d(f, fa, fa + it.get("dur", 12)), width=it.get("width", 9),
                                       color=_cor(it.get("cor", "ink")), seed=it.get("seed", 43), head=it.get("head", 40)))
    elif k == "cross":
        x, y, s = it["xy"]
        col = _cor(it.get("cor", "red"))
        c.alpha_composite(V.hand_arrow(c.size, [(x - s, y - s), (x + s, y + s)], progress=K.d(f, fa, fa + 6), width=11,
                                       color=col, seed=61, head=0))
        c.alpha_composite(V.hand_arrow(c.size, [(x + s, y - s), (x - s, y + s)], progress=K.d(f, fa + 5, fa + 11), width=11,
                                       color=col, seed=63, head=0))
    elif k == "strike":
        x1, x2, y = it["xy"]
        c.alpha_composite(V.hand_underline(c.size, x1, x2, y, progress=K.d(f, fa, fa + 8), passes=2, width=it.get("width", 9),
                                           color=_cor(it.get("cor", "red")), seed=71))
    elif k == "pie":
        x, y, r = it["xy"]
        c.alpha_composite(V.hand_pie(c.size, x, y, r, frac=it["frac"], progress=K.d(f, fa - 4, fa + 16), width=7,
                                     color=INK, fill=_cor(it.get("cor", "yellow")), seed=it.get("seed", 9)))
    elif k == "bar":
        x, y, w, h = it["xy"]
        n = max(2, int(h // 20))
        prog = K.d(f, fa - 2, fa + it.get("dur", 14))
        for j in range(n):
            c.alpha_composite(V.hand_underline(c.size, x, x + w * prog, y + j * (h / n), progress=1.0, passes=1,
                                               width=int(h / n * 1.25), color=_cor(it.get("cor", "yellow")),
                                               seed=80 + j, amp=3))
    elif k == "disc":
        S.disco(c, it["xy"][0], it["xy"][1], it["r"], K.p(f, fa - 6, fa + 4), seed=it.get("seed", 9))
    elif k == "stamp":
        K.carimbo(c, it["text"], it["xy"][0], it["xy"][1], it.get("corpo", 70), it.get("rot", -8),
                  K.d(f, fa, fa + 8), K.d(f, fa + 4, fa + 12), cor=_cor(it.get("cor", "red")), seed=it.get("seed", 51))
    else:
        raise KeyError(k)


def _vinheta(im, forca):
    a = np.asarray(im.convert("RGB"), np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    m = 1.0 - forca * np.clip((r - 0.35) / 0.9, 0, 1) ** 1.4
    return Image.fromarray(np.clip(a * m[..., None], 0, 255).astype(np.uint8)).convert("RGBA")


_full = {}


def _foto_cheia(nome, focus):
    key = (nome, focus)
    if key not in _full:
        im = Image.open(K.CUT.parent / "raw" / f"{nome}.png").convert("RGB")
        s = max(W / im.width, H / im.height) * 1.12                       # sobra p/ o push
        im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
        x0 = int(np.clip(im.width * focus[0] - W / 2, 0, im.width - W))
        y0 = int(np.clip(im.height * focus[1] - H / 2, 0, im.height - H))
        _full[key] = im.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")
    return _full[key].copy()


_vid = {}


def _video_quadro(vid, t):
    """Quadro do B-roll `vid` no segundo `t` do vídeo (24 qps), em W x H. Guarda na memória um vídeo por vez."""
    import cv2
    if _vid.get("id") != vid:
        cap = cv2.VideoCapture(str(K.ROOT / "07_assets" / "broll" / f"{vid}.mp4"))
        qs = []
        while True:
            ok, q = cap.read()
            if not ok:
                break
            qs.append(q)
        cap.release()
        if not qs:
            raise FileNotFoundError(f"07_assets/broll/{vid}.mp4 sem quadros")
        _vid.clear()
        _vid.update(id=vid, qs=qs, fps=24.0, cache={})
    i = int(np.clip(math.floor(t * _vid["fps"] + 1e-6), 0, len(_vid["qs"]) - 1))
    if i not in _vid["cache"]:
        rgb = cv2.cvtColor(_vid["qs"][i], cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb)
        s = max(W / im.width, H / im.height)
        im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        if len(_vid["cache"]) > 8:
            _vid["cache"].clear()
        _vid["cache"][i] = im.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")
    return _vid["cache"][i].copy()


def beat(spec, t0):
    """fn(f) -> RGBA do beat que começa em t0 (segundos do clipe)."""
    def fn(f):
        anch = {}
        if spec.get("video"):
            c = _video_quadro(spec["video"], spec.get("va", 0.0) + max(0.0, f) / 24.0 * spec.get("vel", 1.0))
            if spec.get("dim"):
                c = Image.blend(c, Image.new("RGBA", c.size, (18, 18, 20, 255)), spec["dim"])
            c = _vinheta(c, spec.get("vin", 0.30))
            fq = math.floor(f / 2.0) * 2.0                    # desenho por cima no relógio de 12 qps
            for it in spec.get("items", []):
                _draw(c, it, fq, t0, anch)
            gan = spec.get("push", 0.0)
            return K.apply_camera(c, 1.0 + gan * K.p(f, 0, spec.get("n", 60)), focus=spec.get("cam_focus", (540, 960))) if gan else c
        if spec.get("full"):
            c = _foto_cheia(spec["full"], spec.get("focus", (0.5, 0.5)))
            if spec.get("dim"):
                c = Image.blend(c, Image.new("RGBA", c.size, (18, 18, 20, 255)), spec["dim"])
            c = _vinheta(c, spec.get("vin", 0.55))
            gan, foc = spec.get("push", 0.05), spec.get("cam_focus", (540, 960))
        else:
            c = S.fundo_escuro(spec.get("seed", 5)) if spec.get("bg") == "dark" else bg_paper()
            if spec.get("props", True) and spec.get("bg") != "dark":
                _props(c, spec.get("pseed", 0))
            gan, foc = spec.get("cam", (0.03, (540, 960)))
        for it in spec["items"]:
            _draw(c, it, f, t0, anch)
        return K.apply_camera(c, 1.0 + gan * K.p(f, 0, spec.get("n", 60)), focus=foc)
    return fn


def cena(beats, j, janela=4.0):
    """Cutaway: sequência de beats com flash entre eles. `j` = (t0, t1) da cena, em segundos do clipe."""
    def build(frame):
        itens = []
        for b in beats:
            tb = j[0] if b.get("at") is None else T(b["at"]) - b.get("lead", 0.06)
            itens.append((0 if b.get("at") is None else fr(tb, j[0]), beat(b, tb)))
        return S.sequencia(frame, itens, janela=janela)
    return build



# ---------------------------------------------------------------------------------------------- rosto (p/ posicionar overlay)
import subprocess, io
def _modelo_yunet():
    """YuNet (OpenCV Zoo, licença MIT): variável CV_YUNET (o mvpy do plugin exporta), cópia no projeto, ou a corte-viral."""
    import os
    from pathlib import Path
    cands = [os.environ.get("CV_YUNET", ""), str(K.ROOT / "models" / "face_detection_yunet_2023mar.onnx"),
             os.path.expanduser("~/.claude/skills/corte-viral/models/face_detection_yunet_2023mar.onnx")]
    for c in cands:
        if c and Path(c).exists():
            return c
    raise FileNotFoundError("modelo YuNet não encontrado: defina CV_YUNET com o caminho do .onnx")


_MODELO = None
_face = {}


def _rosto(j):
    """Retângulo (x0,y0,x1,y1) em 1080x1920 que cobre o rosto+cabelo nos 3 pontos do overlay (união). None se não achar."""
    import cv2
    if j in _face:
        return _face[j]
    det = cv2.FaceDetectorYN.create(_MODELO or _modelo_yunet(), "", (540, 960), 0.6, 0.3, 5000)
    xs = []
    for t in (j[0] + 0.15, (j[0] + j[1]) / 2, j[1] - 0.15):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(K.ROOT / "00_brief" / "fonte.mp4"), "-frames:v", "1",
                              "-vf", "scale=540:960", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        im = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if im is None:
            continue
        det.setInputSize((im.shape[1], im.shape[0]))
        _, faces = det.detect(im)
        for f in (faces if faces is not None else []):
            if f[2] * f[3] > 0.004 * im.shape[0] * im.shape[1]:
                xs.append((f[0] * 2, f[1] * 2, (f[0] + f[2]) * 2, (f[1] + f[3]) * 2))
    if not xs:
        _face[j] = None
    else:
        x0, y0 = min(a[0] for a in xs), min(a[1] for a in xs)
        x1, y1 = max(a[2] for a in xs), max(a[3] for a in xs)
        h = y1 - y0
        _face[j] = (x0 - 0.40 * (x1 - x0), y0 - 1.1 * h, x1 + 0.40 * (x1 - x0), y1 + 1.2 * h)   # cabelo, pescoço e ombros
    return _face[j]


def _canto(w, h, j, usados):
    """Canto livre (centro do objeto) com menor sobreposição ao rosto; fora da faixa da legenda (y > 1450) e do topo (y < 170)."""
    cands = [(w / 2 + 35, 330 + h / 2 - 90), (W - w / 2 - 35, 330 + h / 2 - 90), (w / 2 + 35, 1180), (W - w / 2 - 35, 1180)]
    fc = _rosto(j)
    melhor, ms = None, 1e18
    for i, (cx, cy) in enumerate(cands):
        if i in usados:
            continue
        box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        ov = 0.0
        if fc:
            ov = max(0, min(box[2], fc[2]) - max(box[0], fc[0])) * max(0, min(box[3], fc[3]) - max(box[1], fc[1]))
        if box[3] > 1450 or box[1] < 170:
            ov += 1e9
        if ov + i * 1e-3 < ms:
            melhor, ms = i, ov + i * 1e-3
    usados.add(melhor)
    return cands[melhor], melhor

# ---------------------------------------------------------------------------------------------- overlay
def overlay(spec, j):
    """Overlay sobre o rosto: fundo transparente. `spec`: dict(ident=(nome, sub)) ou dict(items=[...]) com
    itens `obj` (asset pequeno em canto livre, entra pelo lado), `etiqueta`, `marcador`, `arrow`, `circle`."""
    tot = int(round((j[1] - j[0]) * 24))

    def build(frame, overlay_only=True):
        if spec.get("ident"):
            return S.ident(frame, spec["ident"][0], spec["ident"][1], tot)
        c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        usados, ref = set(), {}
        for it in spec["items"]:                               # posição automática: canto livre do rosto
            if it["k"] == "obj" and it.get("xy") == "auto" or it.get("auto"):
                if "_xy" not in it:
                    if it.get("name"):
                        _im = K.asset(it["name"], it["w"]); hh = _im.height
                    else:
                        hh = it.get("h", it["w"] * 1.2)
                    it["_xy"], it["_c"] = _canto(it["w"], hh, j, usados)
        for it in spec["items"]:
            fa = _fa(it, j[0])
            if it["k"] == "obj" and "_xy" in it:
                it["xy"] = it["_xy"]
            if it["k"] != "obj" and it.get("rel"):
                o = next(x for x in spec["items"] if x["k"] == "obj" and "_xy" in x)
                it["xy"] = (o["_xy"][0] + it["rel"][0], o["_xy"][1] + it["rel"][1])
            if it["k"] == "obj":
                s = K.p(frame, fa - 4, fa + 8)
                if s <= 0:
                    continue
                if it.get("photo"):
                    layer, _g = K.photo_card_custom(it["photo"], it["w"], margin=it.get("margin", 0.055), bottom=it.get("bottom", 0.16), rotation=it.get("rot", 0))
                elif it.get("raw"):
                    layer = S.santinho(it["raw"], it["cargo"], it["w"], rot=it.get("rot", 0))
                elif it.get("logo"):
                    layer = S.cartao_logo(it["logo"], it["w"], rot=it.get("rot", 0))
                else:
                    layer = K.asset(it["name"], it["w"], rotation=it.get("rot", 0))
                lado = it.get("lado", "L" if it["xy"][0] < W / 2 else "R")
                dx = (-1 if lado == "L" else 1) * 150 * (1 - s)
                lay = K.fade(layer, min(1.0, s * 1.6))
                V.place(c, lay, V.centered(lay, it["xy"][0] + dx, it["xy"][1]), shadow=K.SH_ONVID)
                if it.get("disc"):
                    pass
            else:
                _draw(c, it, frame, j[0], {})
        sai = K.p(frame, tot - 8, tot)
        return K.fade(c, 1 - sai) if sai > 0 else c
    return build


# ---------------------------------------------------------------------------------------------- registro
def _st(j, mid):
    n = int(round((j[1] - j[0]) * 24))
    return {"START": 0, "MID": mid, "END": max(mid + 1, n - 9), "EXIT": n - 1}


HOLD_MIN, SAIDA_Q = 9.5, 4.0


def _fim_eventos(b, tb):
    """Maior quadro (24 fps, local do beat) em que algum evento do beat termina, medido no próprio código (kit.p/kit.d)."""
    import sys, linecache
    ev = []
    _p, _d = K.p, K.d

    def wrap(f):
        def g(frame, a, bb):
            cod = sys._getframe(1)
            linha = linecache.getline(cod.f_code.co_filename, cod.f_lineno)
            if "apply_camera" not in linha and "sai = " not in linha:
                ev.append(bb)
            return f(frame, a, bb)
        return g
    K.p, K.d = wrap(_p), wrap(_d)
    try:
        beat(b, tb)(9999)
    finally:
        K.p, K.d = _p, _d
    return max([e for e in ev if e < 9000] or [0])


def montar(defs, ajustar=True):
    """defs: lista de (nome, j, spec, cutaway). Se `ajustar`, estende a janela de cada cutaway até o último evento ter HOLD quadros
    de folga antes da saída, sem passar do espaço livre até a próxima cena (>= 1 s de rosto entre cutaways; overlay não invade).
    Devolve SCENES, CENAS (janelas p/ o render) e INFO por cena."""
    ordem = sorted(defs, key=lambda d: d[1][0])
    novos = {}
    for i, (nome, j, spec, cut) in enumerate(ordem):
        if cut and ajustar:
            b = spec[-1]
            tb = j[0] if b.get("at") is None else T(b["at"]) - b.get("lead", 0.06)
            f0 = 0.0 if b.get("at") is None else fr(tb, j[0])
            n = int(round((j[1] - j[0]) * 24))
            preciso = f0 + _fim_eventos(b, tb) + HOLD_MIN + SAIDA_Q
            if preciso > n:
                lim = 1e9
                for nome2, j2, sp2, cut2 in ordem[i + 1:]:
                    lim = min(lim, j2[0] - (1.0 if cut2 else 0.12))
                    break
                t1 = min(j[0] + preciso / 24.0 + 0.02, lim)
                if t1 > j[1]:
                    j = (j[0], round(t1, 3))
        novos[nome] = j
    scenes, cenas_, info = {}, [], {}
    for nome, j0, spec, cut in defs:
        j = novos[nome]
        if cut:
            fn, mid, fx = cena(spec, j), 24, FX_DESK
        else:
            fn, mid, fx = overlay(spec, j), 14, FX_PLATE
        scenes[nome] = (fn, _st(j, mid), fx)
        cenas_.append((nome, fn, j[0], j[1], cut))
        info[nome] = dict(j=j, j_plano=j0, spec=spec, cut=cut, video=_trechos_video(spec, j) if cut else [])
    cenas_.sort(key=lambda c: c[2])      # o mux concatena na ordem da lista: cena nova (B-roll) no fim do J quebra a ordem
    return scenes, cenas_, info


def _trechos_video(beats, j):
    """(início, fim) em segundos locais da cena de cada beat de vídeo: o render passa a 24 qps dentro deles."""
    ini = [0.0 if b.get("at") is None else T(b["at"]) - b.get("lead", 0.06) - j[0] for b in beats]
    fim = ini[1:] + [j[1] - j[0]]
    return [(round(max(0.0, a), 4), round(z, 4)) for b, a, z in zip(beats, ini, fim) if b.get("video")]


def gravar_estados(scenes, tag=""):
    """08_images/frames/<Cena>_<ESTADO>.png (usado pela `prancha` da skill e por `medir.py`)."""
    for nome, (fn, states, fx) in scenes.items():
        for st, frm in states.items():
            if nome.startswith("O"):
                img = fn(frm, overlay_only=True)
                base = Image.new("RGBA", img.size, (90, 90, 96, 255)); base.alpha_composite(img); img = base
            else:
                img = fn(frm)
            V.finish(img, **fx).convert("RGB").save(OUTF / f"{nome}{tag}_{st}.png")
        print(f"  [{nome}] estados gravados", flush=True)
