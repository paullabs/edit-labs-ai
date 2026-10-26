#!/usr/bin/env python3
"""
Baixa UM asset ja APROVADO pelo usuario e registra a origem em assets/FONTES.md.

    python3 baixar_asset.py <url> <projeto> --nome arquivo.jpg --licenca "PD" [--autor "..."] [--pagina URL]

Vai para <projeto>/assets/baixados/ (pasta propria: arquivo baixado e dado nao confiavel).
Nao rode sem a aprovacao da lista (arquivo, fonte, tamanho, licenca).
"""
import sys, urllib.request
from pathlib import Path

a = sys.argv[1:]
url, proj = a[0], Path(a[1])
op = lambda k, d="": a[a.index(k) + 1] if k in a else d
nome = op("--nome", url.rsplit("/", 1)[-1].split("?")[0])
dst = proj / "assets" / "baixados"; dst.mkdir(parents=True, exist_ok=True)
req = urllib.request.Request(url, headers={"User-Agent": "motion-arquivo/1.0"})
with urllib.request.urlopen(req, timeout=120) as r, open(dst / nome, "wb") as f:
    f.write(r.read())
tam = (dst / nome).stat().st_size
fontes = proj / "assets" / "FONTES.md"
if not fontes.exists():
    fontes.write_text("# Fontes dos assets\n\n| arquivo | origem | licenca / uso | nota |\n| --- | --- | --- | --- |\n")
with fontes.open("a") as h:
    h.write(f"| {nome} | {op('--pagina', url)} | {op('--licenca', '?')} | {op('--autor', '')} · {tam / 1e6:.1f} MB |\n")
print(f"{dst / nome} ({tam / 1e6:.1f} MB) — registrado em {fontes}")
