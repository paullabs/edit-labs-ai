# -*- coding: utf-8 -*-
"""
Autoframe: preenche crop_anchor_x e zoom por segmento usando LOCUTOR ATIVO.

Alimenta o renderer que ja existe (scripts/render.py) em vez de criar um caminho
paralelo: a saida sao entradas de `timeline` validas pelo edit-plans.schema.json.

Cadeia de decisao por segmento:
    corte de camera -> tipo de plano -> locutor ativo -> anchor + zoom

Uso:
    python3 scripts/autoframe.py --video V.mp4 --segments segs.json --out plano.json
    python3 scripts/autoframe.py --video V.mp4 --edit-plans 11-edit-plans.json --in-place
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # como pacote (scripts.autoframe)
    from scripts.framing import plan_range, SRC_W, SRC_H, CROP_W, CROP_H  # noqa: E402
except ImportError:  # executado de dentro de scripts/
    from framing import plan_range, SRC_W, SRC_H, CROP_W, CROP_H  # noqa: E402

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "models" / "face_detection_yunet_2023mar.onnx"


def detect_silences(video, noise_db=-32, min_dur=0.18):
    r = subprocess.run(["ffmpeg","-nostdin","-hide_banner","-i",str(video),"-vn",
                        "-af",f"silencedetect=noise={noise_db}dB:d={min_dur}","-f","null","-"],
                       capture_output=True, text=True)
    out=[]; cur=None
    for line in (r.stderr or "").splitlines():
        m=re.search(r"silence_start: ([\d.]+)", line)
        if m: cur=float(m.group(1))
        m=re.search(r"silence_end: ([\d.]+)", line)
        if m and cur is not None: out.append((cur,float(m.group(1)))); cur=None
    return out


def anchor_from_cx(cx, zoom, out_w=1080, out_h=1920, src_w=SRC_W, src_h=SRC_H):
    """Converte centro-x em pixels da fonte para crop_anchor_x (0..1) do renderer."""
    s = max(out_w*zoom/src_w, out_h*zoom/src_h)
    scaled_w = src_w*s
    denom = scaled_w - out_w
    if denom <= 0: return 0.5
    return float(min(1.0, max(0.0, (s*cx - out_w/2)/denom)))


MECANICOS = {"source_start", "source_end", "crop_anchor_x", "zoom"}


def _normalizar(segments):
    """Aceita [(a,b)] ou [{"source_start":..,"source_end":..,...}].

    Devolve (a, b, herdaveis) onde herdaveis sao os campos EDITORIAIS do segmento
    de origem - layout, framing_reason, transition_in, preserve_pause, order.
    """
    saida = []
    for item in segments:
        if isinstance(item, dict):
            a, b = float(item["source_start"]), float(item["source_end"])
            herda = {k: v for k, v in item.items() if k not in MECANICOS}
        else:
            a, b = float(item[0]), float(item[1])
            herda = {}
        saida.append((a, b, herda))
    return saida


def plan_segments(video, segments, model=None, silences=None, zones=None):
    """segments: [(start,end)] ou [{...}] -> subsegmentos com anchor/zoom.

    O autoframe decide ENQUADRAMENTO MECANICO (para onde apontar, quanto fechar).
    A decisao editorial do Edit Director - o motivo do
    enquadramento - e herdada intacta por cada subsegmento. Sobrescreve-la
    apagaria a etapa anterior.
    """
    model = str(model or DEFAULT_MODEL)
    if silences is None:
        silences = detect_silences(video)
    timeline=[]; report=[]
    for (a,b,herda) in _normalizar(segments):
        keys, diags = plan_range(str(video), float(a), float(b), model, silences, zones)
        # keys = [(t, crop_x_px, crop_w_px)] -> agrupa em subsegmentos constantes
        bounds=[]
        for i,(t,x,w) in enumerate(keys):
            t_end = keys[i+1][0] if i+1 < len(keys) else b
            if t_end - t < 0.15: continue
            bounds.append((max(a,t), min(b,t_end), x, w))
        merged=[]
        for (s0,e0,x,w) in bounds:
            if merged and merged[-1][2]==x and merged[-1][3]==w and abs(merged[-1][1]-s0)<0.05:
                merged[-1][1]=e0
            else:
                merged.append([s0,e0,x,w])
        for (s0,e0,x,w) in merged:
            zoom = round(CROP_W/float(w), 4) if w else 1.0
            zoom = max(1.0, min(2.0, zoom))
            cx = x + w/2.0
            timeline.append({**herda,
                             "source_start": round(s0,3), "source_end": round(e0,3),
                             "crop_anchor_x": round(anchor_from_cx(cx, zoom),4),
                             "zoom": zoom})
        report.append({"segmento": [round(a,3), round(b,3)],
                       "subsegmentos": len(merged), "planos": diags})
    return timeline, report


def main():
    ap=argparse.ArgumentParser(description="Enquadramento automatico por locutor ativo")
    ap.add_argument("--video", required=True)
    ap.add_argument("--segments", help='JSON: [[inicio,fim],...]')
    ap.add_argument("--edit-plans", help="11-edit-plans.json para enriquecer")
    ap.add_argument("--out"); ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--model", default=str(DEFAULT_MODEL))
    ap.add_argument("--exclude-zones", help='JSON: [[x0,y0,x1,y1],...] normalizado (ex.: telas do cenario)')
    a=ap.parse_args()

    if not Path(a.model).exists():
        print(f"ERRO: modelo YuNet ausente em {a.model}", file=sys.stderr); return 2
    zones=json.loads(a.exclude_zones) if a.exclude_zones else None
    sil=detect_silences(a.video)

    if a.edit_plans:
        doc=json.loads(Path(a.edit_plans).read_text())
        for plan in doc.get("plans",[]):
            segs=plan.get("timeline",[])
            tl,_=plan_segments(a.video,segs,a.model,sil,zones)
            plan["timeline"]=tl
        dest=Path(a.edit_plans if a.in_place else (a.out or "edit-plans.autoframed.json"))
        dest.write_text(json.dumps(doc,ensure_ascii=False,indent=1))
        print(f"edit-plans atualizado: {dest}")
        return 0

    segs=json.loads(Path(a.segments).read_text()) if Path(a.segments).exists() else json.loads(a.segments)
    tl,rep=plan_segments(a.video,segs,a.model,sil,zones)
    out={"schema_version":"1.0","timeline":tl,"report":rep}
    if a.out:
        Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=1)); print(f"gravado: {a.out}")
    else:
        print(json.dumps(out,ensure_ascii=False,indent=1))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
