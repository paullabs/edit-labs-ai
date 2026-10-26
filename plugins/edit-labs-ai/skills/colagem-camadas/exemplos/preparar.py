"""Prepara os insumos de cada exemplo (monta o .blend e renderiza as camadas pela mesma câmera) na pasta de trabalho.

    clpy preparar.py manequim     peças por diferença entre fotos (pacote de pranchas da release)
    clpy preparar.py luva         mao.blend (Z-Anatomy + luva) e as vistas da mão e do giro dos ossos
    clpy preparar.py cranio       cranio.blend (Z-Anatomy + BodyParts3D), camadas, giros e a luva do soco
    clpy preparar.py estalar      mão em 2×, junta com a bolha, mão com esqueleto (precisa do passo luva antes)
    clpy preparar.py homem        texturas do terno, homem2.blend (Z-Anatomy + BodyParts3D), anatomia e coração
    clpy preparar.py terra        terra.blend (modelo próprio) e as 36 vistas
    clpy preparar.py espirro      garganta.blend (pacote Z-Anatomy da garganta) e os 4 patamares (+ o ouvido, se você montou)
    clpy preparar.py subsolo      subsolo.blend (bloco geológico próprio) e as vistas das camadas (exemplo cena_subsolo.py)

Variáveis: BLENDER (executável do Blender 4.x/5.x; padrão "blender"), EDITLABS_DATA (onde estão os assets da
release), COLAGEM_TRABALHO (pasta de trabalho; padrão ./colagem-trabalho). Nada é baixado aqui: os pacotes da release
são baixados uma vez, com a permissão do usuário (ver ../assets/RELEASE.md)."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM

EX = CM.EXEMPLOS
T = CM.TRABALHO
GIRO = CM.MOTOR / "blender_giro.py"


def blender(script, *args):
    cmd = [CM.BLENDER, "--background", "--factory-startup", "--python", str(script), "--"] + [str(a) for a in args]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def python(script, *args):
    cmd = [sys.executable, str(script)] + [str(a) for a in args]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def render(cfg_rel, **extra):
    """preenche o modelo de cfg (cfg/<exemplo>/*.json) e roda o blender_giro"""
    texto = (EX / "cfg" / cfg_rel).read_text()
    vals = {"TRABALHO": str(T), **{k: str(v) for k, v in extra.items()}}
    for k, v in vals.items():
        texto = texto.replace("{" + k + "}", v.replace("\\", "/"))
    cfg = json.loads(texto)
    destino = T / "cfg" / cfg_rel
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(cfg, ensure_ascii=False, indent=1))
    Path(cfg["saida"]).mkdir(parents=True, exist_ok=True)
    blender(GIRO, destino)


def luva_glb():
    return CM.asset_3d("luva-boxe-polypizza-jtoastie/boxing-glove-jtoastie.glb")


def manequim():
    CM.exige(CM.ASSETS / "pranchas" / "american-manikin-1890" / "c10.jpg",
             como="baixe o pacote de pranchas da release (assets/RELEASE.md)")
    python(EX / "manequim_pecas.py")


def luva():
    camadas = CM.asset_3d("z-anatomy/camadas/zanatomy_pele.glb").parents[2]      # .../assets/3d
    (T / "luva").mkdir(parents=True, exist_ok=True)
    blender(EX / "mao_blender.py", camadas, T / "luva" / "mao.blend", luva_glb())
    render("luva/cfg_mao.json")
    render("luva/cfg_giro.json")


def cranio():
    glb = CM.asset_3d("z-anatomy/camadas/zanatomy_cranio.glb")
    bp3d = CM.asset_3d("bodyparts3d-partof-obj99/alinhamento.json").parent
    (T / "cranio").mkdir(parents=True, exist_ok=True)
    blender(EX / "cranio_blender.py", glb, bp3d, T / "cranio" / "cranio.blend")
    for c in ("cfg_camadas.json", "cfg_giro_cranio.json", "cfg_giro_cerebro.json"):
        render("cranio/" + c)
    render("cranio/cfg_luva_soco.json", LUVA_GLB=luva_glb())


def estalar():
    mao = T / "luva" / "mao.blend"
    CM.exige(mao, como="clpy preparar.py luva")
    for p in ("mao", "junta", "rig"):
        (T / "estalar" / p).mkdir(parents=True, exist_ok=True)
    render("estalar/cfg_mao2x.json")
    blender(EX / "junta_blender.py", mao, T / "estalar" / "junta" / "junta.blend")
    render("estalar/cfg_junta.json")
    blender(EX / "mao_rig_blender.py", mao, T / "estalar" / "rig" / "mao_rig.blend", T / "estalar" / "rig" / "clipes.json")
    render("estalar/cfg_rig.json")


def homem():
    camadas = CM.asset_3d("z-anatomy/camadas/zanatomy_pele.glb").parent
    pele_bp = CM.asset_3d("bodyparts3d-partof-obj99/pele_bodyparts3d_no_sistema_zanatomy.glb")
    (T / "homem2").mkdir(parents=True, exist_ok=True)
    python(EX / "homem2_textura.py")
    blender(EX / "homem2_blender.py", camadas, T / "homem2", T / "homem2" / "homem2.blend", pele_bp)
    render("homem/cfg_anat.json")
    render("homem/cfg_coracao.json")
    CM.homem3("poses/repouso.png")                                    # o recorte e as poses: pacote colagem-homem3
    print("A foto e as poses vêm do pacote colagem-homem3 (homem3_poses_ia.py só para refazer as poses).")


def terra():
    (T / "terra").mkdir(parents=True, exist_ok=True)
    blender(EX / "terra_blender.py", T / "terra" / "terra.blend")
    render("terra/cfg.json")


def espirro():
    glb = CM.asset_3d("z-anatomy-garganta/zanatomy_garganta.glb")
    CM.homem3("poses/repouso.png")                                    # o homem de foto: pacote colagem-homem3
    gar = T / "espirro" / "garganta"
    gar.mkdir(parents=True, exist_ok=True)
    if not (gar / "garganta.blend").exists():
        blender(EX / "garganta_glb.py", glb, gar / "garganta.blend")
    pats = ["base", "meio", "peito", "alto"] + (["ouvido"] if (gar / "ouvido.blend").exists() else [])
    python(EX / "garganta_render.py", *pats)


def subsolo():
    (T / "subsolo").mkdir(parents=True, exist_ok=True)
    blender(CM.SKILL / "modelos" / "presal_blender.py", T / "subsolo" / "subsolo.blend")
    render("subsolo/cfg.json")
    python(EX / "subsolo_pecas.py")


PASSOS = {"manequim": manequim, "luva": luva, "cranio": cranio, "estalar": estalar, "homem": homem, "terra": terra,
          "espirro": espirro, "subsolo": subsolo}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in PASSOS:
        sys.exit(__doc__)
    PASSOS[sys.argv[1]]()
    print("ok:", sys.argv[1], "em", T)
