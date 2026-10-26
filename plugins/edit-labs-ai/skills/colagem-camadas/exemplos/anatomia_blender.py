"""Monta o corpo em camadas (Z-Anatomy, CC BY-SA 4.0) num .blend só, com nomes prefixados por camada e cores de prancha
de anatomia, para o blender_giro renderizar todas as camadas pela mesma câmera.

    "$BLENDER" --background --factory-startup --python anatomia_blender.py -- <pasta camadas GLB> <saida.blend>

Prefixos: pele__, musc__, osso__ (costelas, cartilagens e esterno entram com o nome original e a camada filtra),
org__ (órgãos sem o coração) e cor__ (coração)."""
import re
import sys
from pathlib import Path

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
pasta, saida = Path(args[0]), Path(args[1])
bpy.ops.wm.read_factory_settings(use_empty=True)

CORES = {                                     # albedo de prancha antiga, em sRGB (vira a aquarela no papelizar)
    "pele": (0.87, 0.71, 0.58),
    "musc": (0.74, 0.24, 0.21),
    "tendao": (0.90, 0.86, 0.76),
    "osso": (0.94, 0.90, 0.78),
    "cartilagem": (0.82, 0.86, 0.84),
    "coracao": (0.72, 0.15, 0.13),
    "pulmao": (0.90, 0.58, 0.55),
    "figado": (0.52, 0.20, 0.15),
    "estomago": (0.90, 0.64, 0.54),
    "intestino": (0.86, 0.62, 0.47),
    "traqueia": (0.88, 0.84, 0.76),
}
mats = {}


def mat(nome):
    if nome not in mats:
        m = bpy.data.materials.new(nome)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[nome]]   # sRGB -> linear
        m.diffuse_color = (*lin, 1.0)
        mats[nome] = m
    return mats[nome]


def importa(arquivo, prefixo, cor_de):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(pasta / arquivo))
    novos = [o for o in bpy.data.objects if o not in antes]
    for o in novos:
        if o.type != "MESH":
            continue
        cor = cor_de(o.name)
        pre = "cor" if cor == "coracao" and prefixo == "org" else prefixo
        o.name = f"{pre}__{o.name}"
        o.data.materials.clear()
        o.data.materials.append(mat(cor))
    return novos


def cor_musc(n):
    return "tendao" if re.search(r"retinacul|aponeuros|tendin|tarsus|trochlea|sheath|fascia", n, re.I) else "musc"


def cor_osso(n):
    return "cartilagem" if re.search(r"cartilag", n, re.I) else "osso"


def cor_org(n):
    for rx, c in ((r"atri|ventric|papillary|leaflet", "coracao"), (r"lung", "pulmao"), (r"liver", "figado"),
                  (r"stomach", "estomago"), (r"colon|taenia|duoden", "intestino"), (r"trachea", "traqueia")):
        if re.search(rx, n, re.I):
            return c
    return "intestino"


importa("zanatomy_pele.glb", "pele", lambda n: "pele")
importa("zanatomy_musculos.glb", "musc", cor_musc)
importa("zanatomy_esqueleto.glb", "osso", cor_osso)
importa("zanatomy_orgaos.glb", "org", cor_org)
# só malhas: os vazios do glTF ficam fora (o blender_giro carrega objetos soltos)
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.parent:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o)
contagem = {}
for o in bpy.data.objects:
    p = o.name.split("__")[0]
    contagem[p] = contagem.get(p, 0) + 1
print("objetos por prefixo:", contagem)
bpy.ops.wm.save_as_mainfile(filepath=str(saida), compress=True)
print("ok", saida)
