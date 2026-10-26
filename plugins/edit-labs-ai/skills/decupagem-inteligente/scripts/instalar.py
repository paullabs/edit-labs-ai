"""di verificar — a lista única de checagens de instalação da decupagem-inteligente.

  di verificar [--projeto P]       sai com código ≠ 0 se faltar algo essencial
  di instalar                      não instala nada: o ambiente vem do `editlabs-setup` do plugin; só verifica

No plugin Edit Labs AI os ambientes Python moram em $EDITLABS_DATA (venv-corte roda a skill; venv-motion roda o
kit da motion-vox) e os agentes di-diretor e di-revisor-leigo vêm junto, em <plugin>/agents/.
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import importlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from comum import CORTE_VIRAL, DADOS, EDITLABS_DATA, MOTION_VOX, PLUGIN_ROOT, ROOT, SFX_LIB, DIError, achar_projeto

AGENTS = PLUGIN_ROOT / "agents"     # os agentes vêm com o plugin (edit-labs-ai:di-diretor, edit-labs-ai:di-revisor-leigo)
PAPEIS = {"diretor.md": "di-diretor.md", "revisor-leigo.md": "di-revisor-leigo.md"}
NOMES_PROIBIDOS = [r"\bdi init\b", r"texto_pretendido", r"01_leitura/", r"07_entrega", r"PORTAO-F3", r"duvida: true",
                   r"verificar_master\.py", r"\bdi motion\b", r"pacote_cego", r"DECISOES\.md", r"ARMADILHAS-PROJETO"]


def motion_vox_python() -> str:
    """O Python do venv-motion (versões fixadas do kit). O lançador `di` exporta MV_PY."""
    return os.environ.get("MV_PY") or str(EDITLABS_DATA / "venv-motion" / "bin" / "python")


class Relatorio:
    def __init__(self):
        self.linhas, self.erros = [], 0

    def ok(self, n, texto):
        self.linhas.append(f"  ✓ {n:>2} {texto}")

    def aviso(self, n, texto):
        self.linhas.append(f"  ⚠ {n:>2} {texto}")

    def erro(self, n, texto):
        self.linhas.append(f"  ✗ {n:>2} {texto}")
        self.erros += 1


def verificar(projeto: Path | None = None) -> int:
    r = Relatorio()
    # 1 ffmpeg
    try:
        filtros = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
        faltam = [f for f in ("silencedetect", "blackdetect", "afade", "ebur128", "concat")
                  if not re.search(rf"\s{f}\s", filtros)]
        tem_ass = bool(re.search(r"\sass\s", filtros))
        (r.erro if faltam else r.ok)(1, "ffmpeg/ffprobe" + (f" — faltam filtros: {faltam}" if faltam else " com silencedetect, blackdetect, afade, ebur128, concat")
                                     + ("" if tem_ass else " (sem libass: legenda é Pillow, não afeta)"))
    except FileNotFoundError:
        r.erro(1, "ffmpeg não está no PATH")
    # 2 interpretador
    v = sys.version_info
    if v < (3, 10):
        r.erro(2, f"interpretador {sys.executable} é {v.major}.{v.minor}; precisa ≥ 3.10 (rode editlabs-setup --refazer)")
    else:
        r.ok(2, f"interpretador {sys.executable} ({v.major}.{v.minor})")
    # 3 módulos
    falt = []
    for mod in ("faster_whisper", "numpy", "PIL", "cv2", "yaml", "jsonschema"):
        try:
            importlib.import_module(mod)
        except Exception:
            falt.append(mod)
    (r.erro if falt else r.ok)(3, "módulos: " + ("faltam " + ", ".join(falt) + " (rode editlabs-setup)" if falt else "faster_whisper, numpy, PIL, cv2, yaml, jsonschema"))
    try:
        importlib.import_module("mlx_whisper")
        r.ok(3, "mlx-whisper presente (15 min de bruto ≈ 1 min)")
    except Exception:
        r.aviso(3, "sem mlx-whisper: transcrição em CPU (1 h de áudio ≈ 20–40 min). Opcional, Apple Silicon: "
                    f"{sys.executable} -m pip install -r {ROOT / 'requirements-mlx.txt'}")
    # 4 modelo
    hub = Path.home() / ".cache" / "huggingface" / "hub"
    mods = [d.name for d in hub.glob("models--*large-v3-turbo")] if hub.exists() else []
    (r.ok if mods else r.aviso)(4, "large-v3-turbo em cache: " + (", ".join(mods) if mods else "não — o primeiro uso baixa ~1,5 GB"))
    # 5 motion-vox
    mv = MOTION_VOX
    pngs = list((mv / "assets").glob("*.png"))
    npys = list((mv / "assets").glob("*.npy"))
    fontes = list((mv / "fontes").glob("*.ttf"))
    novos = [x for x in ("ancorar.py", "janelas_legenda.py", "prancha.py", "checar_asset.py") if not (mv / "lib" / x).exists()]
    ok5 = not novos and (mv / "lib" / "voxlab.py").exists() and (mv / "lib" / "captions.py").exists() and \
        (mv / "lib" / "cutout.py").exists() and (mv / "lib" / "render_template.py").exists() and \
        len(fontes) >= 8 and len(pngs) >= 16 and npys and (mv / "referencias" / "rubricas-diretor.md").exists()
    (r.ok if ok5 else r.erro)(5, f"motion-vox em {mv}: {len(pngs)} png, {len(npys)} npy, {len(fontes)} fontes, helpers da decupagem"
                                + ("" if ok5 else f" — INCOMPLETA{(' (faltam ' + ', '.join(novos) + ')') if novos else ''}"))
    # 6 interpretador da motion-vox
    mvp = motion_vox_python()
    t = subprocess.run([mvp, "-c", "import PIL, numpy, cv2"], capture_output=True, text=True)
    (r.ok if t.returncode == 0 else r.erro)(6, f"motion_vox_python = {mvp}" + ("" if t.returncode == 0 else f" não importa PIL/numpy/cv2: {t.stderr.strip()[-120:]}"))
    # 7 corte-viral
    yunet = CORTE_VIRAL / "models" / "face_detection_yunet_2023mar.onnx"
    ok7 = yunet.exists() and (CORTE_VIRAL / "scripts" / "framing.py").exists()
    (r.ok if ok7 else r.erro)(7, "corte-viral: YuNet + framing.py" + ("" if ok7 else " ausentes (saída V precisa)")
                                + (" · vch presente" if (CORTE_VIRAL / "vch").exists() else " · sem vch (clipes de podcast)"))
    # 8 papéis: o texto em papeis/ (para o passe e o processo separado) e o agente do plugin
    for src, dst in PAPEIS.items():
        s, d = ROOT / "papeis" / src, AGENTS / dst
        if not s.exists():
            r.erro(8, f"papeis/{src} ausente")
        elif not d.exists():
            r.erro(8, f"agente {dst} ausente em {AGENTS} (reinstale o plugin)")
        else:
            r.ok(8, f"papel {src} e agente edit-labs-ai:{dst[:-3]} presentes")
    # 9 dados do usuário (fora do plugin)
    r.ok(9, f"dados do usuário em {DADOS} " + ("(existe)" if DADOS.exists() else "(criada no primeiro projeto)"))
    # 10 frontmatter
    sk = (ROOT / "SKILL.md").read_text(encoding="utf-8") if (ROOT / "SKILL.md").exists() else ""
    try:
        import yaml
        fm = yaml.safe_load(sk.split("---", 2)[1]) if sk.startswith("---") else None
        bad = []
        if not fm or fm.get("name") != "decupagem-inteligente":
            bad.append("name")
        if fm and not fm.get("description"):
            bad.append("description")
        (r.erro if bad else r.ok)(10, "frontmatter do SKILL.md" + (": " + "; ".join(bad) if bad else " válido"))
    except Exception as e:
        r.erro(10, f"frontmatter do SKILL.md inválido: {e}")
    # 12 schemas
    import json
    sch_bad = []
    for s in (ROOT / "schemas").glob("*.json"):
        try:
            json.loads(s.read_text())
        except Exception:
            sch_bad.append(s.name)
    (r.erro if sch_bad else r.ok)(12, f"schemas carregam ({len(list((ROOT / 'schemas').glob('*.json')))})" + (f" — inválidos: {sch_bad}" if sch_bad else ""))
    # 13 nomes
    achados = []
    for f in [ROOT / "SKILL.md", *sorted((ROOT / "fases").glob("*.md")), *sorted((ROOT / "papeis").glob("*.md"))]:
        if f.exists():
            txt = f.read_text(encoding="utf-8")
            achados += [f"{f.name}: {p}" for p in NOMES_PROIBIDOS if re.search(p, txt)]
    (r.erro if achados else r.ok)(13, "nomes só da tabela-mestra §10.7" + (" — fora: " + "; ".join(achados[:5]) if achados else ""))
    # 14 FINAIS
    r.ok(14, "entrega em " + (os.environ["DI_FINAIS"] if os.environ.get("DI_FINAIS") else "<projeto>/FINAIS (DI_FINAIS muda)"))
    # 15 SFX (opcional)
    if SFX_LIB is None:
        r.aviso(15, "sem biblioteca de SFX própria (DI_SFX): o som usa o banco da motion-vox")
    else:
        (r.ok if SFX_LIB.exists() else r.aviso)(15, f"biblioteca de SFX {'montada' if SFX_LIB.exists() else 'não encontrada em ' + str(SFX_LIB)}")
    # 16 claude CLI
    cl = Path(shutil.which("claude") or (Path.home() / ".local" / "bin" / "claude"))
    (r.ok if cl.exists() else r.aviso)(16, "claude CLI " + ("presente (Leigo e D4 por processo)" if cl.exists() else "ausente: Leigo e D4 caem no passe"))
    # 18 lib do projeto
    if projeto:
        defas = []
        for d in (projeto / "motion").glob("*"):
            for py in (MOTION_VOX / "lib").glob("*.py"):
                alvo = d / py.name
                if alvo.exists() and py.name not in ("compose.py", "render.py") and not filecmp.cmp(py, alvo, shallow=False):
                    defas.append(f"{d.name}/{py.name}")
        (r.aviso if defas else r.ok)(18, "lib da motion-vox no projeto " + ("defasada: " + ", ".join(defas) + " (di mv <id> --sync)" if defas else "igual à do plugin"))
    print("di verificar — decupagem-inteligente\n" + "\n".join(r.linhas))
    print(f"\n{'✓ tudo certo' if not r.erros else f'✗ {r.erros} problema(s) — a skill não começa assim'}")
    return 1 if r.erros else 0


def instalar() -> int:
    """No plugin não há instalação própria: os ambientes vêm do `editlabs-setup` e os agentes vêm com o plugin."""
    print("A decupagem-inteligente usa os ambientes do Edit Labs AI (editlabs-setup). Nada a instalar; verificando:")
    return verificar(None)


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog=f"di {cmd}")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    if cmd == "instalar":
        return instalar()
    proj = None
    if a.projeto:
        proj = achar_projeto(a.projeto)
    return verificar(proj)
