"""Poe o motor da skill no sys.path (familia_a, planos, projeto) e diz onde ficam os dados do usuario.
Importe antes de tudo.

Variaveis de ambiente (todas opcionais):
  EDITLABS_DATA       pasta persistente do plugin (padrao ~/.local/share/edit-labs-ai); a skill usa a subpasta
                      motion-arquivo/ para o mapa e o catalogo de sons do usuario
  EDITLABS_SONS       pasta com os efeitos sonoros do proprio usuario (qualquer organizacao de subpastas)
  EDITLABS_SONS_MAPA  o mapa de recortes feito por som_biblioteca.py (padrao <dados>/som_biblioteca.json)
Sem pasta de sons, o mixador usa os efeitos sintetizados de motor/som.py (motor/kit/sfx).
"""
import os
import sys
from pathlib import Path

MOTOR = Path(__file__).resolve().parent.parent / "motor"
if str(MOTOR) not in sys.path:
    sys.path.insert(0, str(MOTOR))

DADOS = Path(os.environ.get("EDITLABS_DATA", str(Path.home() / ".local" / "share" / "edit-labs-ai"))) / "motion-arquivo"


def pasta_sons(arg=None):
    """A pasta de efeitos do usuario: o argumento, senao EDITLABS_SONS, senao None."""
    v = arg or os.environ.get("EDITLABS_SONS")
    return Path(v).expanduser() if v else None


def mapa_sons(arg=None):
    """Onde fica (ou vai ficar) o mapa de recortes da biblioteca do usuario."""
    v = arg or os.environ.get("EDITLABS_SONS_MAPA")
    return Path(v).expanduser() if v else DADOS / "som_biblioteca.json"
