"""Maquete de refinaria (modelo próprio, 1 unidade = 10 m), em três camadas para a colagem:
base (laje, tanques, esferas, tocha, rack de tubos) · trem1 (destilação, vácuo, forno, reatores) · trem2 (igual, à direita).
Mais 'andaime': o trem 2 só em estrutura (o esqueleto da obra), da mesma câmera.

    "$BLENDER" --background --factory-startup --python refinaria_blender.py -- <saida.blend>"""
import math
import sys

import bpy

saida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
mats = {}


def mat(nome, cor):
    if nome not in mats:
        m = bpy.data.materials.new(nome)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in cor]
        m.diffuse_color = (*lin, 1.0)
        mats[nome] = m
    return mats[nome]


def fin(o, nome, m):
    o.name = nome
    o.data.materials.clear()
    o.data.materials.append(m)
    return o


def cil(nome, r, h, x, y, z0=0.4, m=None, seg=40):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=seg, location=(x, y, z0 + h / 2))
    return fin(bpy.context.object, nome, m)


def caixa(nome, sx, sy, sz, x, y, z0=0.4, m=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z0 + sz / 2))
    o = bpy.context.object
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    return fin(o, nome, m)


def esfera(nome, r, x, y, z, m):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, z), segments=40, ring_count=20)
    bpy.ops.object.shade_smooth()
    return fin(bpy.context.object, nome, m)


ACO = mat("aco", (0.80, 0.81, 0.83))
ACO_E = mat("aco_e", (0.56, 0.58, 0.62))
LARANJA = mat("laranja", (0.88, 0.47, 0.20))
TIJOLO = mat("tijolo", (0.58, 0.27, 0.22))
LAJE = mat("laje", (0.66, 0.66, 0.62))
BRANCO = mat("branco", (0.93, 0.92, 0.88))
AMARELO = mat("amarelo", (0.94, 0.78, 0.22))
AZUL = mat("azul", (0.28, 0.46, 0.70))
VERM = mat("verm", (0.78, 0.18, 0.15))


def trem(pref, dx):
    """um trem de refino: coluna de destilação com plataformas, coluna de vácuo, forno com chaminés, 2 reatores"""
    cil(f"{pref}__coluna", 0.85, 9.0, -8 + dx, 2.0, m=ACO)
    for k in range(7):
        cil(f"{pref}__plat{k}", 1.15, 0.12, -8 + dx, 2.0, z0=1.6 + k * 1.15, m=LARANJA)
    esfera(f"{pref}__topo", 0.85, -8 + dx, 2.0, 9.4, ACO)
    cil(f"{pref}__vacuo", 1.2, 6.0, -5.2 + dx, 2.6, m=ACO_E)
    for k in range(4):
        cil(f"{pref}__vplat{k}", 1.45, 0.12, -5.2 + dx, 2.6, z0=1.5 + k * 1.3, m=LARANJA)
    esfera(f"{pref}__vtopo", 1.2, -5.2 + dx, 2.6, 6.4, ACO_E)
    caixa(f"{pref}__forno", 3.2, 2.2, 2.6, -8 + dx, -2.6, m=TIJOLO)
    for j, xx in enumerate((-8.8, -7.2)):
        cil(f"{pref}__chamine{j}", 0.26, 6.0, xx + dx, -2.6, z0=3.0, m=TIJOLO)
    for j, (xx, yy, hh) in enumerate(((-3.6, -0.6, 4.0), (-2.4, -2.6, 3.2))):
        cil(f"{pref}__reator{j}", 0.62, hh, xx + dx, yy, m=ACO)
        esfera(f"{pref}__rtopo{j}", 0.62, xx + dx, yy, 0.4 + hh, ACO)
    for j, (cor, zz) in enumerate(((AMARELO, 2.3), (BRANCO, 2.6), (AZUL, 2.9))):    # tubos que ligam as unidades
        bpy.ops.mesh.primitive_cylinder_add(radius=0.13, depth=6.0, location=(-5.5 + dx, -0.6, zz), rotation=(0, math.pi / 2, 0))
        fin(bpy.context.object, f"{pref}__tubo{j}", cor)
    for k in range(4):                                                           # pernas do rack
        caixa(f"{pref}__rack{k}", 0.16, 0.16, 2.9, -8.2 + k * 1.9 + dx, -0.6, m=ACO_E)


caixa("base__laje", 26.0, 15.0, 0.4, 0, 0.5, z0=0.0, m=LAJE)
for j, (xx, yy) in enumerate(((-10.0, 6.0), (-6.6, 6.0), (-3.2, 6.0), (0.2, 6.0))):
    cil(f"base__tanque{j}", 1.45, 2.0, xx, yy, m=BRANCO)
    bpy.ops.mesh.primitive_cone_add(radius1=1.48, depth=0.5, location=(xx, yy, 2.65), vertices=40)
    fin(bpy.context.object, f"base__teto{j}", ACO)
for j, xx in enumerate((4.2, 7.0)):
    esfera(f"base__esfera{j}", 1.25, xx, 6.0, 1.9, BRANCO)
    for k, (ox, oy) in enumerate(((-0.8, -0.8), (0.8, -0.8), (-0.8, 0.8), (0.8, 0.8))):
        caixa(f"base__perna{j}{k}", 0.14, 0.14, 1.4, xx + ox * 0.9, 6.0 + oy * 0.9, m=ACO_E)
cil("base__tocha", 0.2, 11.0, 11.6, 5.6, m=BRANCO)
for k in range(5):
    cil(f"base__faixa{k}", 0.22, 0.6, 11.6, 5.6, z0=1.0 + k * 2.1, m=VERM)
bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=22.0, location=(0.0, -5.6, 1.2), rotation=(0, math.pi / 2, 0))
fin(bpy.context.object, "base__tubolongo", AMARELO)
trem("trem1", 0.0)
trem("trem2", 11.0)
# o andaime: cópia do trem 2 em estrutura (modificador wireframe), cor de madeira/aço cru
for o in [o for o in bpy.data.objects if o.name.startswith("trem2__")]:
    a = o.copy()
    a.data = o.data.copy()
    a.name = o.name.replace("trem2__", "andaime__")
    bpy.context.scene.collection.objects.link(a)
    w = a.modifiers.new("w", "WIREFRAME")
    w.thickness = 0.07
    a.data.materials.clear()
    a.data.materials.append(mat("andaime", (0.72, 0.60, 0.42)))
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida, len(bpy.data.objects))
