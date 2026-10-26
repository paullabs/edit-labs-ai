#!/usr/bin/env python3
"""Montagem nativa no invideo, por etapas e com registro dos ids: gera as operações do `edit_timeline` de cada
composição (timeline) e guarda os ids que o invideo devolve. As regras medidas do invideo (zoom relativo ao
encaixe, luz linear, clipe curto, ids criados) estão em
${CLAUDE_PLUGIN_ROOT}/skills/explicador-vox/referencias/invideo.md — leia antes.

    python3 montar.py <elementos.py> ops <tl> <etapa> [lote]            operações do lote (≤ 100) em JSON
    python3 montar.py <elementos.py> lotes <tl> <etapa>                 quantos lotes
    python3 montar.py <elementos.py> reg <tl> <etapa> <lote> '<created>' guarda os ids criados (lista "created")
    python3 montar.py <elementos.py> caminhos <tl> '<objetos>'           ids de caminho/pintura ([{"clip", "paths"}])
    python3 montar.py <elementos.py> set <chave.do.estado> '<valor json>'

Etapas: A (cria clipes), B (âncora, posição, zoom, rotação, faixas de chave, opacidade/rotação animadas, pena e
recorte de traço), C (chaves). Tudo em pixels da tela de cada composição; os gráficos andam em degraus de 2
quadros (12 qps a 24 qps).

<elementos.py> é do PROJETO, não do plugin. Ele importa este módulo e define:

    import montar as m
    CONFIG = {
        "fps": 24,
        "tam": {"principal": (1920, 1080), "cartao": (2112, 1272)},       px de cada composição
        "fonte_id": {"inter800": "f14", "serifa": "f15"},               ids das fontes no invideo
        "fonte_arq": {"inter800": "fontes/Inter-800.ttf"},              os mesmos arquivos, para medir a tinta
        "timelines": {"principal": "T1", "cartao": "T3"},               ids das timelines
        "tempos": "trabalho/tempos.json",                               saída do tempos.py
    }
    def cartao():
        e = m.EV                                                         {evento: quadro do degrau}
        return [m.forma("selo", "cartao", "@trilha:topo", e["live"], m.FIM, [m.caminho(m.ret(152, 152, 492, 252, 50),
                        "#C94850")], ancora=m.ancora_de("cartao", 322, 202),
                        lanes={"zoom_x": m.degraus(m.pop_in(e["live"])), "zoom_y": m.degraus(m.pop_in(e["live"]))})]
    ELEMENTOS = {"cartao": cartao}

Caminhos relativos do CONFIG são relativos ao arquivo de elementos; o estado (ids registrados) fica em
estado.json ao lado dele. Valores "@trilha:nome" e "@nome" são trocados pelos ids registrados com `set`.
"""
import importlib.util
import json
import math
import sys
from pathlib import Path

CFG = {"fps": 24, "tam": {}, "fonte_id": {}, "fonte_arq": {}, "timelines": {}}
EV, FIM, FPS = {}, 0, 24
EST, EST_ARQ = {}, None
ELEMENTOS = {}
POP = [0.70, 0.91, 0.973, 0.992, 1.0]          # pop medido do estilo arquivo: degraus de 2 quadros (0,4 s)


# ------------------------------------------------------------------ desenho (SVG em pixels da tela da composição)
def ret(x0, y0, x1, y1, r=0.0):
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    if r <= 0:
        return f"M {x0:.1f} {y0:.1f} H {x1:.1f} V {y1:.1f} H {x0:.1f} Z"
    return (f"M {x0 + r:.1f} {y0:.1f} H {x1 - r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x1:.1f} {y0 + r:.1f} V {y1 - r:.1f} "
            f"A {r:.1f} {r:.1f} 0 0 1 {x1 - r:.1f} {y1:.1f} H {x0 + r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x0:.1f} {y1 - r:.1f} "
            f"V {y0 + r:.1f} A {r:.1f} {r:.1f} 0 0 1 {x0 + r:.1f} {y0:.1f} Z")


def circ(cx, cy, r):
    """círculo começando no alto e girando no sentido horário (o recorte de traço enche de 12 para 1, 2...)"""
    return (f"M {cx:.1f} {cy - r:.1f} A {r:.1f} {r:.1f} 0 0 1 {cx + r:.1f} {cy:.1f} A {r:.1f} {r:.1f} 0 0 1 "
            f"{cx:.1f} {cy + r:.1f} A {r:.1f} {r:.1f} 0 0 1 {cx - r:.1f} {cy:.1f} A {r:.1f} {r:.1f} 0 0 1 "
            f"{cx:.1f} {cy - r:.1f}")


def linha(pts):
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def giz(cx, cy, rx, ry, semente=1):
    """círculo de marcador: começa em cima à esquerda, dá a volta e passa um pouco do ponto (não fecha certinho)"""
    pts = []
    n = 40
    for k in range(n + 1):
        a = math.radians(-120 + k * 385 / n)
        w = 1 + 0.035 * math.sin(3 * a + semente) + 0.02 * math.sin(7 * a + 2 * semente)
        pts.append((cx + rx * w * math.cos(a), cy + ry * w * math.sin(a) + 3 * k / n))
    return linha(pts)


def caminho(d, fill="#00000000", stroke=None):
    p = {"d": d, "fill": fill}
    if stroke:
        p["stroke"] = stroke
    return p


def traco(cor, w, cap="round", join="round", dash=None):
    s = {"color": cor, "width": w, "cap": cap, "join": join}
    if dash:
        s["dash"] = dash
    return s


# ------------------------------------------------------------------ texto: centro da tinta em (x, y)
def metr(fonte, corpo, texto):
    """deslocamento do centro da tinta em relação à caixa do texto (o invideo ancora pela caixa, não pela tinta)"""
    from fontTools.ttLib import TTFont
    from PIL import ImageFont
    arq = str(CFG["fonte_arq"][fonte])
    t = TTFont(arq); upm = t["head"].unitsPerEm
    A = t["hhea"].ascent / upm * corpo; D = -t["hhea"].descent / upm * corpo
    f = ImageFont.truetype(arq, max(1, int(round(corpo * 4))))
    l, tt, r, b = f.getbbox(texto, anchor="ls")
    adv = f.getlength(texto) / 4
    return ((l + r) / 2 / 4 - adv / 2), (A - D) / 2 + ((tt + b) / 2) / 4


# ------------------------------------------------------------------ chaves
def degraus(ks):
    """[(quadro, valor)] em degrau: segura cada valor até o próximo (par de chaves); o último segura até o fim"""
    out = []
    for i, (f, v) in enumerate(ks):
        out.append((f, v))
        if i + 1 < len(ks) and ks[i + 1][0] - f > 1:
            out.append((ks[i + 1][0] - 1, v))
    return out


def pop_in(f0, escala=1.0):
    return [(f0 + 2 * j, round(v * escala, 4)) for j, v in enumerate(POP)]


def enxuga(ks):
    """tira a chave do meio de três seguidas com o mesmo valor (o invideo segura o valor entre elas de todo jeito)"""
    out = []
    for i, (f, v) in enumerate(ks):
        if 0 < i < len(ks) - 1 and ks[i - 1][1] == v == ks[i + 1][1]:
            continue
        out.append((f, v))
    return out


class E:
    """Um elemento: como criar (op da etapa A) e o que ajustar depois (B) e animar (C)."""

    def __init__(self, nome, tl, cria, **kw):
        self.nome, self.tl, self.cria = nome, tl, cria
        self.ancora = kw.get("ancora")            # (x, y) em px do clipe a partir do centro
        self.pos = kw.get("pos")                  # (x, y) do centro do clipe a partir do centro da tela
        self.zoom = kw.get("zoom")                # zoom fixo (relativo ao encaixe: ver invideo.md)
        self.rot = kw.get("rot")                  # rotação fixa
        self.lanes = kw.get("lanes", {})          # {prop: [(quadro, valor)]} — já em degraus se for o caso
        self.opac = kw.get("opac")                # [(quadro, valor, ease)]
        self.rotk = kw.get("rotk")                # [(quadro, graus, ease)]
        self.trim = kw.get("trim")                # (índice do caminho, [(quadro, fim%)])
        self.feather = kw.get("feather")          # (índice do caminho, px)
        self.ini = kw.get("ini", cria.get("at_f", cria.get("start_f", 0)))
        self.texto = kw.get("texto")              # (fonte, corpo, x, y, pivô, texto) para âncora/posição pela tinta
        self.extra_b = kw.get("extra_b", [])      # ops estáticas extras (sem id novo): [(op, {campos})]


def forma(nome, tl, track, ini, fim, paths, opacity=None, **kw):
    W, H = CFG["tam"][tl]
    op = {"op": "add_shape", "track": track, "at_f": ini, "duration_f": fim - ini, "preset": "path", "width": W,
          "height": H, "x": 0, "y": 0, "paths": paths}
    if opacity is not None:
        op["opacity"] = opacity
    return E(nome, tl, op, ini=ini, **kw)


def texto(nome, tl, track, ini, fim, txt, fonte, corpo, x, y, cor, pivo=None, **kw):
    st = {"font": CFG["fonte_id"][fonte], "font_size": corpo, "color": cor, "align": "center"}
    return E(nome, tl, {"op": "add_text", "track": track, "start_f": ini, "end_f": fim, "text": txt, "style": st},
             ini=ini, texto=(fonte, corpo, x, y, pivo, txt), **kw)


def ancora_de(tl, cx, cy):
    W, H = CFG["tam"][tl]
    return (round(cx - W / 2, 2), round(cy - H / 2, 2))


# ------------------------------------------------------------------ etapas
def _subst(v, tl):
    if isinstance(v, str) and v.startswith("@trilha:"):
        return EST[tl]["trilhas"][v.split(":", 1)[1]]
    if isinstance(v, str) and v.startswith("@"):
        k = v[1:]
        return EST.get("timelines", {}).get(k) or EST.get("midia", {}).get(k) or CFG["timelines"][k]
    return v


def cid(tl, nome, e):
    if e.cria.get("op") == "existente":
        return e.cria["id"]
    return EST[tl]["clipes"][nome]


def ini_clip(tl, e):
    """quadro de início do clipe na linha do tempo (as chaves de faixa contam a partir dele)"""
    return EST.get(tl, {}).get("ini", {}).get(e.nome, e.ini)


def etapa_ops(tl, et):
    els = ELEMENTOS[tl]()
    ops, quem = [], []
    if et == "A":
        for e in els:
            if e.cria.get("op") == "existente":
                continue
            ops.append({k: _subst(v, tl) for k, v in e.cria.items()}); quem.append(("clip", e.nome))
    elif et == "B":
        for e in els:
            c = cid(tl, e.nome, e)
            for nome_op, campos in e.extra_b:
                ops.append(dict({"op": nome_op, "clip": c}, **campos)); quem.append(None)
            if e.texto:
                fonte, corpo, x, y, pivo, txt = e.texto
                dx, dy = metr(fonte, corpo, txt)
                W, H = CFG["tam"][tl]
                ax, ay = dx, dy
                if pivo:
                    ax, ay = dx + (pivo[0] - x), dy + (pivo[1] - y)
                ops.append({"op": "set_anchor", "clip": c, "x": round(ax, 2), "y": round(ay, 2)}); quem.append(None)
                ops.append({"op": "set_position", "clip": c, "x": round(x - W / 2 - dx, 2),
                            "y": round(y - H / 2 - dy, 2)}); quem.append(None)
            if e.ancora:
                ops.append({"op": "set_anchor", "clip": c, "x": e.ancora[0], "y": e.ancora[1]}); quem.append(None)
            if e.pos:
                ops.append({"op": "set_position", "clip": c, "x": e.pos[0], "y": e.pos[1]}); quem.append(None)
            if e.zoom:
                ops.append({"op": "set_zoom", "clip": c, "x": e.zoom, "y": e.zoom}); quem.append(None)
            if e.rot is not None:
                ops.append({"op": "set_rotation", "clip": c, "degrees": e.rot}); quem.append(None)
            # set_zoom/set_position apagam a faixa da mesma propriedade: as faixas vêm depois dos estáticos
            for prop, ks in e.lanes.items():
                ops.append({"op": "add_keyframe_lane", "parent": c, "parent_kind": "video_clip", "property": prop,
                            "default_value": ks[0][1]})
                quem.append(("lane", f"{e.nome}.{prop}"))
            if e.opac:
                ops.append({"op": "set_keyframes", "clip": c, "property": "opacity",
                            "points": [{"at_f": f, "value": v, "ease": z} for f, v, z in e.opac]})
                quem.append(("lane", f"{e.nome}.opacity"))          # o set_keyframes cria a faixa
            if e.rotk:
                ops.append({"op": "set_keyframes", "clip": c, "property": "rotation",
                            "points": [{"at_f": f, "value": v, "ease": z} for f, v, z in e.rotk]})
                quem.append(("lane", f"{e.nome}.rotation"))
            if e.feather:
                i, px = e.feather
                pid, lid = EST[tl]["caminhos"][e.nome][i]
                ops.append({"op": "set_shape_paint", "clip": c, "path": pid, "layer": lid, "at_seconds": 0,
                            "values": {"feather": px}}); quem.append(None)
            if e.trim:
                i, ks = e.trim
                pid, _ = EST[tl]["caminhos"][e.nome][i]
                ops.append({"op": "trim_shape_path", "clip": c, "path": pid, "at_seconds": 0, "enabled": True,
                            "start": 0, "end": ks[0][1]}); quem.append(None)
                ops.append({"op": "create_shape_keyframe_lane", "clip": c, "path": pid, "parameter": "trim.end",
                            "at_seconds": 0}); quem.append(("lane", f"{e.nome}.trim"))
    elif et == "C":
        for e in els:
            c0 = ini_clip(tl, e)
            for prop, ks in e.lanes.items():
                lane = EST[tl]["lanes"][f"{e.nome}.{prop}"]
                for f, v in enxuga(ks):
                    if f < c0:
                        continue
                    ops.append({"op": "add_keyframe", "lane": lane, "time_seconds": round((f - c0) / FPS, 5),
                                "value": v}); quem.append(None)
            if e.trim:
                lane = EST[tl]["lanes"][f"{e.nome}.trim"]
                for f, v in degraus(e.trim[1]):
                    if f < c0:
                        continue
                    ops.append({"op": "add_keyframe", "lane": lane, "time_seconds": round((f - c0) / FPS, 5),
                                "value": round(v, 3)}); quem.append(None)
    else:
        sys.exit(f"etapa desconhecida: {et} (A, B ou C)")
    return ops, quem


def lotes(ops, quem, n=100):
    return [(ops[i:i + n], quem[i:i + n]) for i in range(0, len(ops), n)]


def _grava_estado():
    EST_ARQ.write_text(json.dumps(EST, ensure_ascii=False, indent=1))


def registrar(tl, et, lote, criados):
    ops, quem = etapa_ops(tl, et)
    _, q = lotes(ops, quem)[lote]
    est = EST.setdefault(tl, {})
    for k in ("clipes", "lanes", "caminhos", "trilhas", "ini"):
        est.setdefault(k, {})
    itens = [c for c in criados if c["kind"] not in ("gap", "track", "audio_track")]
    esperados = [x for x in q if x]
    if len(itens) != len(esperados):
        sys.exit(f"criados {len(itens)} != esperados {len(esperados)}: {itens} / {esperados}")
    for (tipo, nome), c in zip(esperados, itens):
        est["clipes" if tipo == "clip" else "lanes"][nome] = c["id"]
    _grava_estado()
    print(f"registrados {len(itens)} em {tl}/{et}/{lote}")


def carregar(arq_elementos):
    """Lê o arquivo de elementos do projeto, o CONFIG, os tempos e o estado."""
    global EV, FIM, FPS, EST, EST_ARQ, ELEMENTOS
    arq = Path(arq_elementos).resolve()
    sys.modules.setdefault("montar", sys.modules[__name__])      # o projeto faz "import montar" e acha este
    spec = importlib.util.spec_from_file_location("elementos_do_projeto", arq)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    CFG.update(getattr(mod, "CONFIG", {}))
    base = arq.parent
    CFG["fonte_arq"] = {k: (base / v) for k, v in CFG.get("fonte_arq", {}).items()}
    FPS = int(CFG.get("fps", 24))
    if CFG.get("tempos"):
        tempos = json.loads((base / CFG["tempos"]).read_text())
        EV.update({k: v["degrau"] for k, v in tempos.get("eventos", {}).items()})
        FIM = int(tempos.get("fim", 0))
    EST_ARQ = base / "estado.json"
    EST.update(json.loads(EST_ARQ.read_text()) if EST_ARQ.exists() else {})
    CFG["timelines"].update(EST.get("timelines", {}))
    ELEMENTOS.update(mod.ELEMENTOS)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    carregar(sys.argv[1])
    cmd, a = sys.argv[2], sys.argv[3:]
    if cmd in ("ops", "lotes"):
        tl, et = a[0], a[1]
        ops, quem = etapa_ops(tl, et)
        ls = lotes(ops, quem)
        if cmd == "lotes":
            print(len(ls), "lotes,", len(ops), "operações")
        else:
            k = int(a[2]) if len(a) > 2 else 0
            print(json.dumps(ls[k][0], ensure_ascii=False, separators=(",", ":")))
    elif cmd == "reg":
        registrar(a[0], a[1], int(a[2]), json.loads(a[3]))
    elif cmd == "caminhos":
        tl = a[0]
        objs = json.loads(a[1])                      # [{"clip": nome, "paths": [[path_id, paint_id], ...]}]
        est = EST.setdefault(tl, {}); est.setdefault("caminhos", {})
        for o in objs:
            est["caminhos"][o["clip"]] = o["paths"]
        _grava_estado()
        print("ok")
    elif cmd == "set":                               # set <chave.do.estado> <valor json>
        ref = EST
        partes = a[0].split(".")
        for p in partes[:-1]:
            ref = ref.setdefault(p, {})
        ref[partes[-1]] = json.loads(a[1])
        _grava_estado()
        print("ok")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
