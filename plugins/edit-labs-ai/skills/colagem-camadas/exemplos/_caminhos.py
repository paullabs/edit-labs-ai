"""Caminhos comuns dos exemplos da colagem-camadas (nada absoluto, nada fora do que o usuário configurou).

    MOTOR         $EDITLABS_MOTOR, ou <plugin>/motor/colagem
    ASSETS        $EDITLABS_DATA/colagem/assets (padrão ~/.local/share/edit-labs-ai/colagem/assets): os pacotes da
                  release (Z-Anatomy, BodyParts3D, pranchas). Ver ../assets/RELEASE.md
    ASSETS_SKILL  <skill>/assets: o que é pequeno e livre e vem no plugin (luvas CC BY 3.0, crânio CC0)
    TRABALHO      $COLAGEM_TRABALHO, ou ./colagem-trabalho na pasta onde você rodou: renders, cache de papel, prévias
    trilha()      $COLAGEM_TRILHA (um arquivo de música seu) ou None (cama sintetizada pelo motor)
    LEGENDAS      $COLAGEM_LEGENDAS=1 liga a legenda de fala dos exemplos (desligada por padrão: REGRAS.md)"""
import os
import sys
from pathlib import Path

EXEMPLOS = Path(__file__).resolve().parent
SKILL = EXEMPLOS.parent
PLUGIN = SKILL.parents[1]
MOTOR = Path(os.environ.get("EDITLABS_MOTOR", str(PLUGIN / "motor" / "colagem")))
if str(MOTOR) not in sys.path:
    sys.path.insert(0, str(MOTOR))
DADOS = Path(os.environ.get("EDITLABS_DATA", "~/.local/share/edit-labs-ai")).expanduser() / "colagem"
ASSETS = DADOS / "assets"
ASSETS_SKILL = SKILL / "assets"
TRABALHO = Path(os.environ.get("COLAGEM_TRABALHO", str(Path.cwd() / "colagem-trabalho"))).expanduser().resolve()
PREVIA = TRABALHO / "previa"
LEGENDAS = os.environ.get("COLAGEM_LEGENDAS", "0") not in ("", "0", "nao", "não", "false")
TRILHA_LICENCA = os.environ.get("COLAGEM_TRILHA_LICENCA", "")
BLENDER = os.environ.get("BLENDER", "blender")


def trilha():
    t = os.environ.get("COLAGEM_TRILHA")
    return Path(t).expanduser() if t else None


def asset_3d(rel):
    """um arquivo 3D: primeiro o que vem no plugin (assets/3d), depois o da release ($EDITLABS_DATA/colagem/assets/3d)"""
    for base in (ASSETS_SKILL / "3d", ASSETS / "3d"):
        p = base / rel
        if p.exists():
            return p
    raise SystemExit(f"Falta o asset 3D '{rel}'. Baixe o pacote da release e descompacte em {DADOS} "
                     f"(instruções em {SKILL / 'assets' / 'RELEASE.md'}).")


def exige(*caminhos, como=""):
    """para com uma mensagem clara quando falta um arquivo de uma etapa anterior"""
    falta = [str(p) for p in caminhos if not Path(p).exists()]
    if falta:
        raise SystemExit("Falta: " + ", ".join(falta) + (f"\nComo gerar: {como}" if como else ""))


TRABALHO.mkdir(parents=True, exist_ok=True)
PREVIA.mkdir(parents=True, exist_ok=True)
