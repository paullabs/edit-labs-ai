"""Traduz o plano.json (as mesmas camadas da prévia local) em operações do edit_timeline do invideo.

    clpy invideo_ops.py bin     --plano plano.json --pecas pecas/ --pasta invideo/
        -> invideo/bin.json com a lista do que subir; preencha os ids de mídia depois do add_media
    clpy invideo_ops.py criar   --plano plano.json --pecas pecas/ --pasta invideo/ [--som som.json]
        -> invideo/ops/criar_T2.json (MUNDO), criar_T1.json (TELA), criar_audio.json
    clpy invideo_ops.py reg     --pasta invideo/ <criar_XX.json> '<json do "created" que o invideo devolveu>'
        -> casa os ids criados com as camadas (invideo/estado.json)
    clpy invideo_ops.py chaves  --plano plano.json --pecas pecas/ --pasta invideo/
        -> invideo/ops/chaves.json: estáticos, faixas de chave e pontos (precisa do estado.json)

Regras medidas no invideo (ver referencias/invideo.md):
- duas timelines: T1 TELA 1080x1920 e T2 MUNDO 2160x3840 (o mundo em 2x), aninhada em T1; a câmera é o zoom e a
  posição do clipe MUNDO: zoom = 0,5*z; posição = -(cx-540)*z, -(cy-960)*z;
- place_media de imagem cria a caixa no tamanho NATIVO da imagem: nas faixas de chave, zoom 1 = pixel nativo;
- set_zoom recebe o zoom RELATIVO ao encaixe na tela (guarda valor x encaixe) e apaga a faixa de escala:
  estáticos numa chamada, faixas de chave em outra, depois;
- posição = centro do clipe, em px a partir do centro da timeline; rotação positiva = horário;
- o desenho anda em degraus de 2 quadros: chaves em pares (quadro-1 = valor velho, quadro = valor novo) ou
  set_keyframes com ease "hold";
- a mistura é em luz linear: um preto por cima escurece menos que no sRGB; para igualar, op' = 1 - (1 - op)^2,2;
- clipe de imagem de 2 quadros sai com 1 (a fonte arredonda a 30 qps): conferir e corrigir com trim_clip.
Este script não chama o invideo: ele escreve os lotes de operações que o agente manda pelo MCP."""
import argparse
import json
import math
import textwrap
from pathlib import Path

from PIL import Image

FPS = 24
CANVAS = {"T1": (1080, 1920), "T2": (2160, 3840)}


# ------------------------------------------------------------------ chaves (o mesmo cálculo do motor)
def curva(nome, t):
    t = min(max(t, 0.0), 1.0)
    if nome == "lin":
        return t
    if nome == "out":
        return 1 - (1 - t) ** 3
    if nome == "in":
        return t ** 3
    if nome == "io":
        return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
    if nome == "back":
        c1 = 1.70158
        return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2
    if nome == "segura":
        return 0.0
    raise KeyError(nome)


def valor(ks, f, padrao):
    if not ks:
        return padrao
    if f <= ks[0][0]:
        return ks[0][1]
    for (f0, v0, c0), (f1, v1, _) in zip(ks, ks[1:]):
        if f0 <= f < f1:
            return v0 + (v1 - v0) * curva(c0, (f - f0) / (f1 - f0))
    return ks[-1][1]


def r4(v):
    return round(float(v), 4)


class Camada:
    """modelo mínimo da camada do plano, no pixel da peça (as peças saem em 2x o tamanho planejado)"""

    def __init__(self, c, pecas):
        self.c, self.nome, self.ini, self.fim = c, c["nome"], c["ini"], c["fim"]
        self.mundo = c.get("mundo", True)
        tw, th = c["tamanho"]
        if c.get("forma"):
            self.px = (tw, th)                                # a forma nasce no tamanho planejado
        else:
            with Image.open(Path(pecas) / f"{c['arquivo']}.png") as im:
                self.px = im.size
        self.base = tw / self.px[0]
        if c.get("ancora", "centro") == "centro":
            self.ancora = (self.px[0] / 2, self.px[1] / 2)
        else:
            self.ancora = (c["ancora"][0] / self.base, c["ancora"][1] / self.base)
        self.ch = c["chaves"]

    def props(self, f):
        g = lambda k, d: valor(self.ch.get(k), f, d)
        op = g("op", 100) / 100.0
        if self.c.get("luz_linear"):
            op = 1 - (1 - op) ** 2.2
        return {"x": g("x", 540), "y": g("y", 960), "s": g("s", 1.0) * self.base, "rot": g("rot", 0.0), "op": op}

    def transformada(self, tl):
        """f -> (posX, posY, zoom nativo, rot, op) no sistema do invideo"""
        k = 2.0 if tl == "T2" else 1.0
        w, h = self.px
        W, H = CANVAS[tl]
        forma = bool(self.c.get("forma"))

        def fn(f):
            p = self.props(f)
            a = math.radians(p["rot"])
            dx, dy = (self.ancora[0] - w / 2) * p["s"], (self.ancora[1] - h / 2) * p["s"]
            cx = p["x"] - (dx * math.cos(a) - dy * math.sin(a))
            cy = p["y"] - (dx * math.sin(a) + dy * math.cos(a))
            zoom = p["s"] if forma else k * p["s"]           # a forma já nasce no tamanho de T2
            return (r4(cx * k - W / 2), r4(cy * k - H / 2), r4(zoom), r4(p["rot"]), r4(p["op"]))

        return fn


def amostra(fn, ini, fim, passo=2):
    """[(quadro, valores)] nos degraus em que algo muda, mais o primeiro"""
    out, ult = [], None
    for f in range(ini, fim, passo):
        v = fn(f)
        if ult is None or any(abs(a - b) > 1e-4 for a, b in zip(v, ult)):
            out.append((f, v))
            ult = v
    return out


def pares(serie, ini, idx):
    """série -> pontos de chave em degrau (par quadro-1 / quadro) para o componente idx, em segundos do clipe"""
    so = []
    for f, v in serie:
        if not so or abs(v[idx] - so[-1][1]) > 1e-4:
            so.append((f, v[idx]))
    pts = {}
    for j, (f, v) in enumerate(so):
        if j > 0:
            pts[round((f - 1 - ini) / FPS, 5)] = so[j - 1][1]
        pts[round((f - ini) / FPS, 5)] = v
    return [{"time_seconds": t, "value": v} for t, v in sorted(pts.items())]


def encaixe(w, h, tl):
    W, H = CANVAS[tl]
    return min(W / w, H / h)


# ------------------------------------------------------------------ faixas
def faixas(plano):
    """uma faixa por peça de mundo (camadas com o mesmo arquivo dividem a faixa), na ordem do plano; T1 na ordem:
    fundos, vinheta e peças de tela, MUNDO, título, legenda"""
    t2, t1 = {}, {}
    for c in plano["camadas"]:
        if c.get("mundo", True):
            chave = c.get("faixa") or c.get("arquivo") or c["nome"]
            t2.setdefault(chave, f"V{len(t2) + 1}")
    for fd in plano["fundos"]:
        t1.setdefault(fd["nome"], f"V{len(t1) + 1}")
    for c in plano["camadas"]:
        if not c.get("mundo", True):
            t1.setdefault(c.get("faixa") or c["nome"], f"V{len(t1) + 1}")
    for k in ("MUNDO", "TITULO", "LEGENDA"):
        t1.setdefault(k, f"V{len(t1) + 1}")
    return t2, t1


def faixa_t2(c, t2):
    return t2[c.get("faixa") or c.get("arquivo") or c["nome"]]


# ------------------------------------------------------------------ comandos
def cmd_bin(a, plano):
    pecas = sorted({c["arquivo"] for c in plano["camadas"] if c.get("arquivo")} |
                   {fd["arquivo"] for fd in plano["fundos"] if fd.get("arquivo")})
    modelo = {"pecas": {p: "" for p in pecas},
              "fontes": {"600": "", "800": ""},
              "audio": {"voz": "", "trilha": "", "banco": ""},
              "nota": "suba cada arquivo (start_upload + add_media) e escreva aqui o id de mídia que o invideo "
                      "devolver; fontes: o Inter do plugin (skills/motion-vox/fontes) ou pesos estáticos OFL"}
    arq = a.pasta / "bin.json"
    if arq.exists():
        velho = json.loads(arq.read_text())
        for k in modelo:
            if isinstance(modelo[k], dict):
                modelo[k].update({kk: vv for kk, vv in velho.get(k, {}).items() if vv})
    arq.write_text(json.dumps(modelo, ensure_ascii=False, indent=1))
    print("subir:", ", ".join(f"{p}.png" for p in pecas), "+ voz, trilha, banco de efeitos e as fontes")
    print("modelo em", arq)


def cmd_criar(a, plano):
    BIN = json.loads((a.pasta / "bin.json").read_text())
    falta = [k for k, v in BIN["pecas"].items() if not v]
    if falta:
        raise SystemExit(f"bin.json sem id para: {', '.join(falta)}")
    t2f, t1f = faixas(plano)
    fim = plano["fim"]
    t2, t1, au, o2, o1, oa = [], [], [], [], [], []
    curtos = []
    for c in plano["camadas"]:
        dur = c["fim"] - c["ini"]
        if dur <= 2:
            curtos.append({"camada": c["nome"], "quadros": dur})
        if not c.get("mundo", True):
            continue
        if c.get("forma"):
            t2.append({"op": "add_shape", "track": faixa_t2(c, t2f), "at_f": c["ini"], "duration_f": dur,
                       "preset": c["forma"].get("tipo", "rectangle"), "width": c["tamanho"][0] * 2,
                       "height": c["tamanho"][1] * 2, "x": 0, "y": 0, "fill": c["forma"]["cor"]})
        else:
            t2.append({"op": "place_media", "asset": BIN["pecas"][c["arquivo"]], "track": faixa_t2(c, t2f),
                       "at_f": c["ini"], "source_start_seconds": 0, "source_end_seconds": round(dur / FPS, 6),
                       "mode": "overwrite", "linked_audio": False})
        o2.append(c["nome"])
    for fd in plano["fundos"]:
        t1.append({"op": "place_media", "asset": BIN["pecas"][fd["arquivo"]], "track": t1f[fd["nome"]],
                   "at_f": fd["ini"], "source_start_seconds": 0, "source_end_seconds": round((fd["fim"] - fd["ini"]) / FPS, 6),
                   "mode": "overwrite", "linked_audio": False})
        o1.append(fd["nome"])
    for c in plano["camadas"]:
        if c.get("mundo", True):
            continue
        t1.append({"op": "place_media", "asset": BIN["pecas"][c["arquivo"]], "track": t1f[c.get("faixa") or c["nome"]],
                   "at_f": c["ini"], "source_start_seconds": 0, "source_end_seconds": round((c["fim"] - c["ini"]) / FPS, 6),
                   "mode": "overwrite", "linked_audio": False})
        o1.append(c["nome"])
    t1.append({"op": "nest_timeline", "timeline": "T2", "track": t1f["MUNDO"], "start_f": 0, "end_f": fim})
    o1.append("MUNDO")
    for i, t in enumerate(plano.get("titulo", [])):
        t1.append({"op": "add_text", "track": t1f["TITULO"], "start_f": t["ini"], "end_f": t["fim"], "text": t["texto"],
                   "style": {"font": BIN["fontes"][str(t.get("peso", 800))], "font_size": t["corpo"],
                             "color": t["cor"], "align": "center"}})
        o1.append(f"TITULO_{i:02d}")
    # a legenda é a última etapa: só entra quando motion, B-roll e som estão fechados
    if not a.sem_legenda:
        for i, lg in enumerate(plano.get("legenda", [])):
            st = {"font": BIN["fontes"][str(lg.get("peso", 600))], "font_size": lg.get("corpo", 50), "color": lg["cor"],
                  "align": "center"}
            if lg.get("sombra"):
                st.update({"shadow": True, "shadow_color": "#0A0A0AA6", "shadow_blur": 14})
            t1.append({"op": "add_text", "track": t1f["LEGENDA"], "start_f": lg["ini"], "end_f": lg["fim"],
                       "text": "\n".join(textwrap.wrap(lg["texto"], width=30)), "style": st})
            o1.append(f"LEGENDA_{i:02d}")
    dur = round(fim / FPS, 6)
    for nome, faixa in (("voz", "A1"), ("trilha", "A2")):
        if BIN["audio"].get(nome):
            au.append({"op": "place_media", "asset": BIN["audio"][nome], "track": faixa, "at_f": 0,
                       "source_start_seconds": 0, "source_end_seconds": dur, "mode": "overwrite", "linked_audio": False})
            oa.append(nome.upper())
    if a.som and BIN["audio"].get("banco"):
        som = json.loads(Path(a.som).read_text())
        for e in som["eventos"]:
            if not e.get("ligado", True):
                continue
            au.append({"op": "place_media", "asset": BIN["audio"]["banco"], "track": "A3", "at_f": e["quadro_inicio"],
                       "source_start_seconds": e["banco_ini_s"], "source_end_seconds": e["banco_fim_s"],
                       "mode": "place_on_top", "linked_audio": False})
            oa.append(f"SFX_{e['id']}_{e['som']}|{e['ganho_db']}")
    ops = a.pasta / "ops"
    ops.mkdir(parents=True, exist_ok=True)
    for nome, lote, ordem in (("criar_T2", t2, o2), ("criar_T1", t1, o1), ("criar_audio", au, oa)):
        (ops / f"{nome}.json").write_text(json.dumps({"ops": lote, "ordem": ordem}, ensure_ascii=False))
        print(nome, len(lote), "ops")
    if curtos:
        (ops / "curtos.json").write_text(json.dumps(curtos, ensure_ascii=False, indent=1))
        print(f"{len(curtos)} clipes de até 2 quadros: confira a duração no get_timeline e corrija com trim_clip "
              "(lista em ops/curtos.json)")
    print("faixas T2:", t2f)
    print("faixas T1:", t1f)


def cmd_reg(a, arq, created):
    est_arq = a.pasta / "estado.json"
    est = json.loads(est_arq.read_text()) if est_arq.exists() else {"clipes": {}}
    d = json.loads((a.pasta / "ops" / arq).read_text())
    ids = [c["id"] for c in json.loads(created) if c["kind"] in ("clip", "audio_clip")]   # ignora gap e faixa
    assert len(ids) == len(d["ordem"]), (len(ids), len(d["ordem"]))
    est["clipes"].update(dict(zip(d["ordem"], ids)))
    est_arq.write_text(json.dumps(est, ensure_ascii=False, indent=1))
    print(dict(zip(d["ordem"], ids)))


def cmd_chaves(a, plano):
    est = json.loads((a.pasta / "estado.json").read_text())["clipes"]
    por_nome = {c["nome"]: c for c in plano["camadas"]}
    estaticas = {"T1": [], "T2": []}
    lanes = {"T1": [], "T2": []}
    for nome, cid in est.items():
        if nome not in por_nome:
            continue
        L = Camada(por_nome[nome], a.pecas)
        tl = "T2" if L.mundo else "T1"
        serie = amostra(L.transformada(tl), L.ini, L.fim, 2)
        v0 = serie[0][1]
        # estático primeiro (set_position e set_zoom apagam faixas de chave); faixas depois, noutra chamada
        estaticas[tl].append({"op": "set_position", "clip": cid, "x": v0[0], "y": v0[1]})
        w, h = L.px if not L.c.get("forma") else (L.px[0] * 2, L.px[1] * 2)
        z0 = r4(v0[2] / encaixe(w, h, tl))                    # set_zoom é relativo ao encaixe na tela
        estaticas[tl].append({"op": "set_zoom", "clip": cid, "x": z0, "y": z0})
        for idx, props in ((0, ["position_x"]), (1, ["position_y"]), (2, ["zoom_x", "zoom_y"])):
            if len({round(v[idx], 4) for _, v in serie}) > 1:
                pts = pares(serie, L.ini, idx)                  # as faixas guardam o multiplicador nativo
                for prop in props:
                    lanes[tl].append((cid, prop, pts))
        for idx, prop, padrao in ((3, "rotation", 0.0), (4, "opacity", 1.0)):
            vals = [v[idx] for _, v in serie]
            if len(set(vals)) == 1:
                if abs(vals[0] - padrao) > 1e-4:
                    op = {"op": "set_rotation", "clip": cid, "degrees": vals[0]} if prop == "rotation" else \
                         {"op": "set_opacity", "clip": cid, "opacity": vals[0]}
                    estaticas[tl].append(op)
            else:
                pts, ult = [], None
                for f, v in serie:                              # "hold" = degrau exato de 12 qps
                    if ult is None or abs(v[idx] - ult) > 1e-4:
                        pts.append({"at_f": f, "value": v[idx], "ease": "hold"})
                        ult = v[idx]
                estaticas[tl].append({"op": "set_keyframes", "clip": cid, "property": prop, "points": pts})
    for nome, cid in est.items():
        if nome.startswith("TITULO_"):
            t = plano["titulo"][int(nome.split("_")[1])]
            estaticas["T1"].append({"op": "set_position", "clip": cid, "x": t["x"] - 540, "y": t["y"] - 960})
            estaticas["T1"].append({"op": "set_keyframes", "clip": cid, "property": "opacity",
                                    "points": [{"at_f": q, "value": v / 100, "ease": "hold"} for q, v, _ in t["op"]]})
        elif nome.startswith("LEGENDA_"):
            lg = plano["legenda"][int(nome.split("_")[1])]
            estaticas["T1"].append({"op": "set_position", "clip": cid, "x": 0, "y": lg["y"] - 960})
        elif nome in [fd["nome"] for fd in plano["fundos"]]:
            fd = next(x for x in plano["fundos"] if x["nome"] == nome)
            pts, ult = [], None
            for f in range(fd["ini"], fd["fim"], 2):
                v = r4(valor(fd.get("op"), f, 100) / 100)
                if v != ult:
                    pts.append({"at_f": f, "value": v, "ease": "hold"})
                    ult = v
            if len(pts) > 1:
                estaticas["T1"].append({"op": "set_keyframes", "clip": cid, "property": "opacity", "points": pts})
    # câmera: zoom e posição do clipe MUNDO, em degraus de 2 quadros como as camadas
    if "MUNDO" in est:
        cam = plano["camera"]

        def camf(f):
            z = valor(cam.get("z"), f, 1.0)
            cx, cy = valor(cam.get("cx"), f, 540), valor(cam.get("cy"), f, 960)
            return (r4(-(cx - 540) * z), r4(-(cy - 960) * z), r4(0.5 * z), 0.0, 1.0)

        serie = amostra(camf, 0, plano["fim"], 2)
        for idx, props in ((0, ["position_x"]), (1, ["position_y"]), (2, ["zoom_x", "zoom_y"])):
            pts = pares(serie, 0, idx)
            for prop in props:
                lanes["T1"].append((est["MUNDO"], prop, pts))
    audio = [{"op": "set_audio_gain", "target": cid, "gain_db": float(nome.split("|")[1])}
             for nome, cid in est.items() if nome.startswith("SFX_")]
    out = {"estaticas_T2": estaticas["T2"], "estaticas_T1": estaticas["T1"] + audio}
    for tl in ("T2", "T1"):
        out[f"lanes_{tl}"] = [{"op": "add_keyframe_lane", "parent": c, "parent_kind": "video_clip", "property": p,
                               "default_value": pts[0]["value"]} for c, p, pts in lanes[tl]]
        out[f"pontos_{tl}"] = [pts for c, p, pts in lanes[tl]]
    (a.pasta / "ops").mkdir(parents=True, exist_ok=True)
    (a.pasta / "ops" / "chaves.json").write_text(json.dumps(out, ensure_ascii=False))
    for k, v in out.items():
        print(k, len(v))
    print("ordem: estaticas_T2 e estaticas_T1; depois lanes_*; depois add_keyframes com pontos_* (mesma ordem das lanes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("modo", choices=["bin", "criar", "reg", "chaves"])
    ap.add_argument("extra", nargs="*", help="no modo reg: <arquivo de ops> '<created json>'")
    ap.add_argument("--plano", type=Path)
    ap.add_argument("--pecas", type=Path)
    ap.add_argument("--pasta", type=Path, default=Path("invideo"))
    ap.add_argument("--som", type=Path, help="som.json do som.py (efeitos com quadro, trecho do banco e ganho)")
    ap.add_argument("--sem-legenda", action="store_true", help="monta sem legenda (ela entra por último)")
    a = ap.parse_intermixed_args()
    a.pasta.mkdir(parents=True, exist_ok=True)
    if a.modo == "reg":
        if len(a.extra) != 2:
            ap.error("reg precisa de <arquivo de ops> e do json 'created'")
        cmd_reg(a, *a.extra)
    else:
        if not (a.plano and a.pecas):
            ap.error("informe --plano e --pecas")
        p = json.loads(a.plano.read_text(encoding="utf-8"))
        {"bin": cmd_bin, "criar": cmd_criar, "chaves": cmd_chaves}[a.modo](a, p)
