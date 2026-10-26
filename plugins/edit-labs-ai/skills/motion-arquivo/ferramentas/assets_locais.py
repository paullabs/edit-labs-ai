#!/usr/bin/env python3
"""
Assets REAIS que ja estao na maquina — antes de baixar, gerar ou desenhar qualquer coisa.

    mvpy assets_locais.py apps                          lista aplicativos com icone
    mvpy assets_locais.py icone "Adobe After Effects" <projeto> [--doc aep]
    mvpy assets_locais.py cursores                      lista cursores do sistema
    mvpy assets_locais.py cursor pointinghand <projeto>

icone   o .icns do proprio aplicativo instalado (o do app ou o de um tipo de documento:
        --doc aep pega o icone do arquivo .aep), em PNG 1024 -> assets/reais/
cursor  o vetor do cursor do macOS renderizado a 12x, com o hotspot em JSON ao lado
        (a ponta do dedo cai no clique) -> assets/reais/cursor_<nome>.png/.json

Icone de marca e marca registrada: uso nominativo (falar do produto), nunca como se fosse
a marca do canal. Registrar em assets/FONTES.md (o script registra sozinho).
"""
import glob, json, plistlib, subprocess, sys
from pathlib import Path

CURSORES = Path("/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/"
                "HIServices.framework/Versions/A/Resources/cursors")
AQUI = Path(__file__).resolve().parent


def _fontes(proj, nome, origem, nota):
    f = Path(proj) / "assets" / "FONTES.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    if not f.exists():
        f.write_text("# Fontes dos assets\n\n| arquivo | origem | licenca / uso | nota |\n| --- | --- | --- | --- |\n")
    with f.open("a") as h:
        h.write(f"| {nome} | {origem} | {nota} | local, sem download |\n")


def _apps():
    return sorted(glob.glob("/Applications/*.app") + glob.glob("/Applications/*/*.app") +
                  glob.glob("/System/Applications/*.app") + glob.glob("/System/Applications/Utilities/*.app"))


def icone(nome_app, proj, doc=None):
    cands = [a for a in _apps() if nome_app.lower() in Path(a).stem.lower()]
    if not cands:
        sys.exit(f"nenhum app com '{nome_app}' em /Applications")
    app = Path(sorted(cands, key=len)[0])
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    res = app / "Contents" / "Resources"
    if doc:
        icns = None
        for t in info.get("CFBundleDocumentTypes", []):
            exts = [e.lower() for e in t.get("CFBundleTypeExtensions", [])]
            if doc.lower() in exts and t.get("CFBundleTypeIconFile"):
                icns = res / t["CFBundleTypeIconFile"]
        if icns is None:
            achados = sorted(res.glob(f"*{doc.lower()}*.icns"))
            icns = achados[0] if achados else None
    else:
        nome = info.get("CFBundleIconFile", "")
        icns = res / (nome if nome.endswith(".icns") else nome + ".icns")
    if not icns or not Path(icns).exists():
        sys.exit(f"icone nao encontrado em {res}")
    dst = Path(proj) / "assets" / "reais"; dst.mkdir(parents=True, exist_ok=True)
    nome_png = f"icone_{app.stem.lower().replace(' ', '_')}{'_' + doc.lower() if doc else ''}.png"
    subprocess.run(["sips", "-s", "format", "png", str(icns), "--out", str(dst / nome_png)], check=True,
                   capture_output=True)
    _fontes(proj, nome_png, f"{icns}", "icone do app instalado (marca registrada: uso nominativo)")
    print(dst / nome_png)


def cursor(nome, proj, escala=12):
    pdf = CURSORES / nome / "cursor.pdf"
    if not pdf.exists():
        sys.exit(f"cursor '{nome}' nao existe; veja: mvpy assets_locais.py cursores")
    info = plistlib.loads((CURSORES / nome / "info.plist").read_bytes())
    dst = Path(proj) / "assets" / "reais"; dst.mkdir(parents=True, exist_ok=True)
    png = dst / f"cursor_{nome}.png"
    subprocess.run(["swift", str(AQUI / "pdf_png.swift"), str(pdf), str(png), str(escala)], check=True,
                   capture_output=True)
    meta = dict(hotspot_px=[info.get("hotx", 0) * escala, info.get("hoty", 0) * escala], px_por_pt=escala,
                sombra=dict(alfa=0.45, desfoque_pt=info.get("blur", 2), desloc_pt=[0, 1]))
    png.with_suffix(".json").write_text(json.dumps(meta, indent=1))
    _fontes(proj, png.name, str(pdf), "cursor do sistema macOS (elemento de interface)")
    print(png)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "apps":
        for p in _apps():
            print(Path(p).stem)
    elif a[0] == "cursores":
        print("\n".join(sorted(d.name for d in CURSORES.iterdir() if (d / "cursor.pdf").exists())))
    elif a[0] == "icone":
        doc = a[a.index("--doc") + 1] if "--doc" in a else None
        icone(a[1], a[2], doc)
    elif a[0] == "cursor":
        cursor(a[1], a[2])
