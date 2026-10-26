"""Monta o garganta.blend do exemplo do espirro a partir do GLB do pacote da release (colagem-zanatomy-garganta).

    "$BLENDER" --background --factory-startup --python garganta_glb.py -- <zanatomy_garganta.glb> <saida.blend>

O GLB é o resultado de garganta_blender.py (o atlas Z-Anatomy completo cortado em camadas, CC BY-SA 4.0): cada peça já
em coordenadas do mundo e com o prefixo da camada (fora_pele__, fora_musc__, fora_faringe__, dentro_osso__, dentro_pulm__,
dentro_bronq__, dentro_via__, atras_...). O glTF não guarda a cor de exibição (a que o Workbench usa), então ela é
refeita aqui pelo nome do material, com as mesmas cores de prancha do garganta_blender.py."""
import re
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
glb, saida = args[0], args[1]

CORES = {                                       # sRGB de prancha antiga (vira a aquarela no papelizar)
    "pele": (0.87, 0.71, 0.58), "musc": (0.74, 0.24, 0.21), "faringe": (0.80, 0.33, 0.30),
    "osso": (0.94, 0.90, 0.78), "cartilagem": (0.80, 0.86, 0.84), "dente": (0.98, 0.96, 0.90),
    "mucosa": (0.93, 0.60, 0.58), "lingua": (0.88, 0.42, 0.42), "palato": (0.90, 0.50, 0.50),
    "gengiva": (0.90, 0.55, 0.52), "traqueia": (0.88, 0.84, 0.76), "esofago": (0.82, 0.50, 0.42),
    "bolso": (0.97, 0.45, 0.36), "pulmao": (0.90, 0.58, 0.55), "epiglote": (0.78, 0.88, 0.84),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
falta = set()
for m in bpy.data.materials:
    nome = re.sub(r"\.\d+$", "", m.name)
    if nome not in CORES:
        falta.add(m.name)
        continue
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[nome]]
    m.diffuse_color = (*lin, 1.0)
if falta:
    print("materiais sem cor de prancha:", sorted(falta))
# o glTF pode criar nós vazios (pais): ficam só as malhas, já no lugar
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.parent is not None:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o, do_unlink=True)
grupos = {}
for o in bpy.data.objects:
    p = o.name.split("__")[0]
    grupos[p] = grupos.get(p, 0) + 1
print("GRUPOS", grupos)
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida)
