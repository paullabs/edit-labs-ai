#!/usr/bin/env python3
"""
Checagem de instalacao. Rode ANTES do primeiro projeto:

    editlabs-verificar

Verifica o que a skill precisa e o que ela carrega junto. Sai com codigo != 0 se algo
essencial faltar, para nao descobrir no meio de um render longo.
"""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
falhas, avisos = [], []


def ok(t):
    print(f"  \033[32mok\033[0m    {t}")


def erro(t):
    print(f"  \033[31mFALTA\033[0m {t}")
    falhas.append(t)


def aviso(t):
    print(f"  \033[33maviso\033[0m {t}")
    avisos.append(t)


print(f"MOTION VOX — verificacao\n  skill em {S}\n")

print("python")
if sys.version_info < (3, 8):
    erro(f"python {sys.version_info.major}.{sys.version_info.minor} — precisa 3.8+")
else:
    ok(f"python {sys.version_info.major}.{sys.version_info.minor}")

print("\nbibliotecas")
for mod, pip in [("PIL", "Pillow"), ("numpy", "numpy"), ("cv2", "opencv-python")]:
    try:
        importlib.import_module(mod)
        ok(pip)
    except ImportError:
        erro(f"{pip}   ->  pip install {pip}")
try:
    importlib.import_module("faster_whisper")
    ok("faster-whisper")
except ImportError:
    erro("faster-whisper   ->  pip install faster-whisper")

print("\nferramentas")
for exe in ("ffmpeg", "ffprobe"):
    if shutil.which(exe):
        v = subprocess.run([exe, "-version"], capture_output=True, text=True)
        ok(f"{exe}  {v.stdout.splitlines()[0].split(' version ')[-1][:24]}")
    else:
        erro(f"{exe}   ->  brew install ffmpeg  |  apt install ffmpeg")

print("\nfrontmatter do SKILL.md")
# Uma `description` em escalar YAML simples contendo ": " (ex.: "processo inteiro:
# escolher") e lida como inicio de um novo mapeamento: o arquivo parece perfeito e a
# skill simplesmente nao aparece na lista — sem erro nenhum. Escalar de bloco (>-) resolve.
try:
    import re
    import yaml
    txt = (S / "SKILL.md").read_text()
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        erro("SKILL.md nao tem frontmatter --- ... ---")
    else:
        fm = yaml.safe_load(m.group(1))
        if not isinstance(fm, dict) or "name" not in fm or "description" not in fm:
            erro("frontmatter sem `name` ou `description`")
        elif fm["name"] != "motion-vox":
            erro(f"name e {fm['name']!r}, deveria ser 'motion-vox'")
        else:
            ok(f"YAML valido, description com {len(fm['description'])} chars")
except ImportError:
    aviso("pyyaml ausente — nao deu para validar o frontmatter")
except Exception as e:
    erro(f"frontmatter INVALIDO ({type(e).__name__}) — a skill nao vai carregar: "
         f"{str(e).splitlines()[0]}")

print("\nkit que viaja com a skill")
fontes = sorted((S / "fontes").glob("*.ttf"))
# o kit leva 8 fontes, todas usadas pelo motor e com licença
(ok if len(fontes) >= 8 else erro)(f"{len(fontes)} fontes em fontes/ (esperado 8)")
assets = sorted((S / "assets").glob("*.png"))
(ok if len(assets) >= 16 else erro)(f"{len(assets)} assets em assets/ (esperado 16+)")
for f in ("lib/voxlab.py", "lib/captions.py", "lib/cutout.py", "lib/crt.py",
          "lib/night_photo.py", "lib/render_template.py", "lib/compose_template.py",
          "lib/transcrever.py", "referencias/legenda.md", "referencias/armadilhas.md",
          "IDENTIDADE.md", "lib/sfx.py", "referencias/som-local.md",
          "referencias/seedance-2.5.md"):
    (ok if (S / f).exists() else erro)(f)

print("\nmotor")
sys.path.insert(0, str(S / "lib"))
try:
    import voxlab as V
    f = V.font(V.F_BLACK, 80)
    w = V.text_width("MOTION", V.F_BLACK, 80, -1.8)
    ok(f"voxlab carrega e mede tipo ({w:.0f}px para 'MOTION' em 80px)")
    im = V.boil_full(V.text_layer((400, 200), "vox", V.F_BLACK, 90, (200, 100),
                                  anchor="mm"), 0.0, **V.BOIL_PRESETS["print"])
    ok(f"boil preset 'print' aplica ({im.size[0]}x{im.size[1]})")
except Exception as e:
    erro(f"voxlab: {type(e).__name__}: {e}")
try:
    import captions as CAP
    CAP.blocos()
    erro("captions deveria exigir configurar() e nao exigiu")
except RuntimeError:
    ok("captions exige configurar() antes de rodar")
except Exception as e:
    erro(f"captions: {type(e).__name__}: {e}")

print("\nmodelo de transcricao")
try:
    from huggingface_hub import scan_cache_dir
    nomes = [r.repo_id for r in scan_cache_dir().repos]
    if any("large-v3-turbo" in n for n in nomes):
        ok("large-v3-turbo em cache")
    else:
        aviso("large-v3-turbo nao esta em cache — baixa ~1,5 GB no primeiro uso")
except Exception:
    aviso("nao deu para checar o cache do modelo (baixa no primeiro uso)")

print()
if falhas:
    print(f"\033[31m{len(falhas)} item(ns) faltando.\033[0m Resolva antes de comecar.")
    sys.exit(1)
print("\033[32mTudo pronto.\033[0m Comece por SKILL.md, secao 'Ordem de execucao'."
      + (f"  ({len(avisos)} aviso(s))" if avisos else ""))
