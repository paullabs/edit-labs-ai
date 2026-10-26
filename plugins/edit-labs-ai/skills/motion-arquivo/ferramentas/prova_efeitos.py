#!/usr/bin/env python3
"""
Prova de escuta dos efeitos: para cada papel do mixador (clique, baque, obturador...), o som ESCOLHIDO e até 3
alternativas que casam com o mesmo padrão na pasta de sons do usuário, cada um já recortado (o trecho que o
mixador usaria), com o mesmo pico, em <saida>/<papel>/NN_(ESCOLHIDO|alt)_<arquivo>.mp3, mais indice.md.

    python3 prova_efeitos.py <saida_dir> [<pasta_de_sons>] [--alt 3] [--escolha <escolha.json>]

<pasta_de_sons> padrão: $EDITLABS_SONS. Nada é copiado para o plugin. A escolha final é de ouvido: depois de
ouvir, fixe o arquivo do papel num escolha.json (modelo em motor/kit/som_escolha.modelo.json) e rode
`som_biblioteca.py --escolha escolha.json` de novo.
"""
import _caminho  # noqa: F401
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("som_biblioteca", AQUI / "som_biblioteca.py")
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)


def exportar(arq, modo, quantos, destino):
    rec = sb.recortes(arq, modo, quantos)[0]
    x = sb.ler(arq)
    a, b = int(rec["source_in"] * sb.SR), int(rec["source_out"] * sb.SR)
    seg = x[a:b]
    if len(seg) < 200:
        return False
    pico = np.abs(seg).max() + 1e-9
    seg = seg * (10 ** (-3 / 20) / pico)
    pcm = (np.clip(seg, -1, 1) * 32767).astype("<i2")
    p = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(sb.SR), "-ac", "2", "-i", "-",
                        "-af", "afade=t=in:d=0.003", "-b:a", "160k", str(destino)], input=pcm.tobytes(), capture_output=True)
    return p.returncode == 0


def main():
    a = sys.argv[1:]
    nalt, esc = 3, None
    if "--alt" in a:
        i = a.index("--alt"); nalt = int(a[i + 1]); del a[i:i + 2]
    if "--escolha" in a:
        i = a.index("--escolha"); esc = json.loads(Path(a[i + 1]).read_text()); del a[i:i + 2]
    saida = Path(a[0])
    bib = _caminho.pasta_sons(a[1] if len(a) > 1 else None)
    if bib is None or not bib.exists():
        sys.exit("Sem pasta de sons: passe o caminho ou defina EDITLABS_SONS.")
    todos = sb.arquivos(bib)
    escolhidos = sb.escolher(bib, esc)
    L = ["# Prova de escuta dos efeitos", "", "Cada pasta é um papel do mixador; `01_ESCOLHIDO` é o que o mapa usaria.",
         "Todos com o mesmo pico. A escolha é de ouvido.", ""]
    for papel, (modo, quantos, motivo, *_) in sb.ESCOLHA.items():
        atual = escolhidos.get(papel)
        if not atual:
            L += [f"## {papel}", f"_{motivo}_", "", "- nenhum arquivo casou: fica a reserva sintetizada", ""]
            continue
        pasta = saida / papel
        pasta.mkdir(parents=True, exist_ok=True)
        cands = [c for c in sb.candidatos(bib, papel, todos) if c != atual]
        cands = sorted(cands, key=lambda c: -sb.nitidez(bib / c))[:nalt]
        L += [f"## {papel}", f"_{motivo}_", ""]
        for k, rel in enumerate([atual] + cands):
            arq = bib / rel
            rotulo = "ESCOLHIDO" if k == 0 else "alt"
            nome = re.sub(r"[^\w\- ]+", "", arq.stem).strip().replace(" ", "_")[:70]
            dest = pasta / f"{k + 1:02d}_{rotulo}_{nome}.mp3"
            try:
                ok = exportar(arq, modo, quantos, dest)
            except Exception as ex:
                ok = False
                print("falhou", arq.name, ex)
            if ok:
                L.append(f"- {k + 1:02d} {rotulo}: `{rel}`")
        L.append("")
        print(papel, "ok")
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "indice.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
