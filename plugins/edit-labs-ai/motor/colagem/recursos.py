"""Onde o motor acha fontes, texturas, sons e dados (nenhum caminho absoluto: tudo relativo ao motor ou a variáveis).

    MOTOR      esta pasta (motor/colagem)
    PLUGIN     a raiz do plugin (duas pastas acima)
    DADOS      $EDITLABS_DATA/colagem  (padrão ~/.local/share/edit-labs-ai/colagem): assets baixados da release,
               sons e trilhas do usuário. Fica fora do plugin e sobrevive a atualização.
    FONTES     $EDITLABS_FONTES, ou as fontes OFL que já vêm no plugin (skills/motion-vox/fontes), ou motor/colagem/fontes
    KIT        motor/colagem/kit (papel antigo, domínio público/sem restrições: ver kit/CREDITOS.md)
    SONS       $EDITLABS_SONS, ou DADOS/sons: uma subpasta por classe (papel, ar, grave...). Se não houver, o som é
               sintetizado em código (sons_sint.py)."""
import os
from functools import lru_cache
from pathlib import Path

from PIL import ImageFont

MOTOR = Path(__file__).resolve().parent
PLUGIN = MOTOR.parents[1]
DADOS = Path(os.environ.get("EDITLABS_DATA", "~/.local/share/edit-labs-ai")).expanduser() / "colagem"
KIT = MOTOR / "kit"
SONS = Path(os.environ.get("EDITLABS_SONS", str(DADOS / "sons"))).expanduser()
TRILHAS = Path(os.environ.get("EDITLABS_TRILHAS", str(DADOS / "trilhas"))).expanduser()


def _pasta_fontes():
    for p in (os.environ.get("EDITLABS_FONTES"), PLUGIN / "skills" / "motion-vox" / "fontes", MOTOR / "fontes"):
        if p and Path(p).expanduser().is_dir():
            return Path(p).expanduser()
    raise FileNotFoundError("fontes não encontradas: defina EDITLABS_FONTES ou instale o plugin completo "
                            "(skills/motion-vox/fontes)")


FONTES = _pasta_fontes()

# nomes antigos (fontes estáticas) -> arquivo que existe no plugin + peso no eixo 'wght' da fonte variável
_VARIAVEIS = {"Inter": "Inter[opsz,wght].ttf"}


@lru_cache(maxsize=128)
def fonte(nome, corpo):
    """ImageFont pelo nome do arquivo. 'Inter-800.ttf' (estática) vira a Inter variável no peso 800."""
    p = FONTES / nome
    if p.exists():
        return ImageFont.truetype(str(p), corpo)
    base, _, resto = nome.partition("-")
    if base in _VARIAVEIS and (FONTES / _VARIAVEIS[base]).exists():
        peso = int("".join(c for c in resto if c.isdigit()) or 400)
        f = ImageFont.truetype(str(FONTES / _VARIAVEIS[base]), corpo)
        try:
            eixos = f.get_variation_axes()
            vals = []
            for e in eixos:
                nm = e.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if nm.lower().startswith("weight") or nm.lower() == "wght":
                    vals.append(peso)
                elif "optical" in nm.lower() or nm.lower() == "opsz":
                    vals.append(min(max(corpo / 2, e["minimum"]), e["maximum"]))
                else:
                    vals.append(e.get("default", e["minimum"]))
            f.set_variation_by_axes(vals)
        except Exception:                       # FreeType sem suporte a variação: fica no peso padrão
            pass
        return f
    raise FileNotFoundError(f"fonte {nome} não está em {FONTES}")
