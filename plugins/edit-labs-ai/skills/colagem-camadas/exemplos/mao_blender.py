"""Monta a mão direita levantada (dedos para cima, costas para a câmera) com a luva de boxe encaixada por cima,
num .blend só, para o blender_giro renderizar luva, pele e ossos pela mesma câmera.

    "$BLENDER" --background --factory-startup --python mao_blender.py -- <pasta 3d> <saida.blend> [<luva.glb>]

<pasta 3d>: a pasta assets/3d da release (com z-anatomy/camadas/). <luva.glb>: a luva que vem no plugin
(skills/colagem-camadas/assets/3d/luva-boxe-polypizza-jtoastie/boxing-glove-jtoastie.glb); sem ela, procura em <pasta 3d>.

Fontes: pele e ossos do Z-Anatomy (CC BY-SA 4.0); luva "Boxing Glove" de J-Toastie (Poly Pizza, CC BY 3.0), que é
de mão esquerda: aqui ela é espelhada para vestir a direita.
Prefixos: pele__, osso__ (mão e antebraço), luva__."""
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
base, saida = Path(args[0]), Path(args[1])
bpy.ops.wm.read_factory_settings(use_empty=True)

CORES = {"pele": (0.87, 0.71, 0.58), "osso": (0.94, 0.90, 0.78), "luva": (0.66, 0.13, 0.10)}   # sRGB
mats = {}


def mat(nome):
    if nome not in mats:
        m = bpy.data.materials.new(nome)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[nome]]
        m.diffuse_color = (*lin, 1.0)
        mats[nome] = m
    return mats[nome]


def importa(arquivo, prefixo, manter=None):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(arquivo))
    bpy.context.view_layer.update()
    novos = [o for o in bpy.data.objects if o not in antes]
    out = []
    for o in novos:
        if o.type == "MESH" and (manter is None or re.search(manter, o.name)):
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
            o.name = f"{prefixo}__{o.name}"
            o.data.materials.clear()
            o.data.materials.append(mat(prefixo))
            out.append(o)
    for o in novos:
        if o not in out:
            bpy.data.objects.remove(o)
    return out


za = base / "z-anatomy" / "camadas"
pele = importa(za / "zanatomy_pele.glb", "pele",
               r"(arm|elbow|Cubital fossa|wrist|Dorsum of hand|Palm|digits of hand|Radial foveola)\.r$")
ossos = importa(za / "zanatomy_mao_direita_ossos.glb", "osso")
ossos += importa(za / "zanatomy_esqueleto.glb", "osso", r"^(Radius|Ulna)\.r$")
bpy.context.view_layer.update()

# braço levantado: 180° em X (dedos para cima, as costas da mão para a câmera, que olha de -Y)
R = Matrix.Rotation(math.pi, 4, "X")
for o in pele + ossos:
    o.matrix_world = R @ o.matrix_world
bpy.context.view_layer.update()


def caixa(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


mao = [o for o in pele if re.search(r"(Dorsum of hand|Palm|digits of hand)", o.name)]
mn, mx = caixa(mao)
print("mão:", mn, mx)

# a luva: costas para a câmera (90° em Z), espelhada (mão direita), na altura dos dedos até cobrir o punho
luva = importa(Path(args[2]) if len(args) > 2 else base / "luva-boxe-polypizza-jtoastie" / "boxing-glove-jtoastie.glb",
               "luva")
for o in luva:
    o.matrix_world = Matrix.Rotation(math.radians(90), 4, "Z") @ o.matrix_world
    o.matrix_world = Matrix.Scale(-1, 4, Vector((1, 0, 0))) @ o.matrix_world
bpy.context.view_layer.update()
ln, lx = caixa(luva)
comp_mao = (mx.z - mn.z) + 0.022                   # da ponta dos dedos (+2 cm) até o punho
esc = comp_mao / ((lx.z - ln.z) * 0.64)            # a parte acolchoada é ~64% da altura da luva; o resto é o punho
S = Matrix.Scale(esc, 4)
for o in luva:
    o.matrix_world = S @ o.matrix_world
bpy.context.view_layer.update()
ln, lx = caixa(luva)
alvo = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mx.z + 0.022))
desl = alvo - Vector(((ln.x + lx.x) / 2, (ln.y + lx.y) / 2, lx.z))
for o in luva:
    o.matrix_world = Matrix.Translation(desl) @ o.matrix_world
bpy.context.view_layer.update()
ln, lx = caixa(luva)
print("luva:", ln, lx, "escala", esc)
quinto = next(o for o in ossos if o.name.startswith("osso__Fifth metacarpal"))
qn, qx = caixa([quinto])
print("quinto metacarpo:", qn, qx)

for o in list(bpy.data.objects):
    if o.type != "MESH":
        bpy.data.objects.remove(o)
bpy.ops.wm.save_as_mainfile(filepath=str(saida), compress=True)
print("ok", saida)
