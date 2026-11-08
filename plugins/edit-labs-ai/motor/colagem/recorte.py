"""Recorte local do sujeito (PNG com alfa), sem assinatura e sem crédito. Funciona no macOS, no Linux e no Windows.

    clpy recorte.py entrada.jpg saida.png                 um arquivo
    clpy recorte.py pasta_entrada pasta_saida             todas as imagens da pasta
    clpy recorte.py entrada.jpg mascara.png --mascara     só a máscara (cinza), para quem precisa dela

Como escolhe o motor:
  1. macOS com `swift`: o Vision da Apple (recorte.swift, rápido, sem instalar nada).
  2. `rembg` (pip; `editlabs-setup --recorte`): qualquer sistema. Modelo em EDITLABS_RECORTE_MODELO
     (padrão isnet-general-use; objetos e produtos. Para pessoas: u2net_human_seg).
  3. Nenhum dos dois: diz o que instalar. Dá para recortar em qualquer ferramenta de "remover fundo" e salvar o PNG
     com alfa; o motor só precisa do PNG pronto (`pecas.recorte`).
`--rembg` força o motor 2 mesmo no Mac; `--vision` força o 1.
"""
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _vision(entrada: Path, saida: Path) -> bool:
    """Vision (macOS 14+). True se recortou."""
    swift = "swift"
    r = subprocess.run([swift, str(AQUI / "recorte.swift"), str(entrada), str(saida)], capture_output=True, text=True)
    return r.returncode == 0 and saida.exists()


_SESSAO = {}


def _rembg(entrada: Path, saida: Path) -> bool:
    try:
        from rembg import new_session, remove
        from PIL import Image
    except ImportError:
        return False
    modelo = os.environ.get("EDITLABS_RECORTE_MODELO", "isnet-general-use")
    if modelo not in _SESSAO:
        _SESSAO[modelo] = new_session(modelo)
    img = Image.open(entrada).convert("RGBA")
    remove(img, session=_SESSAO[modelo]).save(saida)
    return True


def _so_mascara(png: Path) -> None:
    from PIL import Image
    im = Image.open(png).convert("RGBA")
    im.getchannel("A").save(png)


def recortar(entrada: Path, saida: Path, motor: str = "auto", mascara: bool = False) -> str:
    saida.parent.mkdir(parents=True, exist_ok=True)
    tem_swift = platform.system() == "Darwin" and (AQUI / "recorte.swift").exists() and shutil.which("swift") is not None
    ordem = {"vision": ["vision"], "rembg": ["rembg"], "auto": (["vision"] if tem_swift else []) + ["rembg"]}[motor]
    for m in ordem:
        if (_vision if m == "vision" else _rembg)(entrada, saida):
            if mascara:
                _so_mascara(saida)
            return m
    sys.exit("Sem motor de recorte neste computador.\n"
             "  Instale o recorte local (grátis):  editlabs-setup --recorte\n"
             "  ou recorte a imagem em qualquer ferramenta de 'remover fundo' e salve o PNG com alfa.")


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) != 2:
        print(__doc__)
        return 2
    motor = "rembg" if "--rembg" in flags else "vision" if "--vision" in flags else "auto"
    ent, sai = Path(pos[0]).expanduser(), Path(pos[1]).expanduser()
    pares = [(ent, sai)]
    if ent.is_dir():
        pares = [(p, sai / (p.stem + ".png")) for p in sorted(ent.iterdir()) if p.suffix.lower() in EXT]
    for e, s in pares:
        print(f"ok {s.name} ({recortar(e, s, motor, '--mascara' in flags)})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
