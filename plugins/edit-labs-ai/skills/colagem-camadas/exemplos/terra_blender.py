"""Constrói a Terra em camadas no Blender e salva terra.blend (sem licença de terceiros).
Camadas (raio relativo ao da Terra): núcleo interno 0,19 · núcleo externo 0,546 · manto 0,985 · crosta 1,0 (crosta
engrossada para aparecer). Cada camada é uma CASCA (esfera menos a esfera de dentro), cortada por um octante virado para
a câmera; o pedaço retirado ('fatia_*') é guardado à parte para sair voando. Cores por vértice (continentes por ruído)."""
import math
import sys
import bpy
import bmesh
from mathutils import Vector, noise

saida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene

CAMADAS = [("nucleo_interno", 0.19, (0.98, 0.86, 0.45)), ("nucleo_externo", 0.546, (0.93, 0.55, 0.18)),
           ("manto", 0.955, (0.78, 0.30, 0.16)), ("crosta", 1.0, None)]


def esfera(nome, r, seg=128):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=seg, ring_count=seg // 2)
    o = bpy.context.object
    o.name = nome
    bpy.ops.object.shade_smooth()
    return o


def octante(nome, r):
    """cubo que cobre o octante x>0, y<0, z>0 (virado para a câmera, que olha de -y e um pouco de cima)"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(r * 0.6, -r * 0.6, r * 0.6))
    c = bpy.context.object
    c.name = nome
    c.scale = (r * 1.2, r * 1.2, r * 1.2)
    bpy.ops.object.transform_apply(scale=True)
    return c


def booleana(alvo, ferramenta, op):
    m = alvo.modifiers.new("b", "BOOLEAN")
    m.object = ferramenta
    m.operation = op
    m.solver = "EXACT"
    bpy.context.view_layer.objects.active = alvo
    bpy.ops.object.modifier_apply(modifier="b")


def pinta(o, cor_fn):
    me = o.data
    if not me.color_attributes:
        me.color_attributes.new("cor", "FLOAT_COLOR", "POINT")
    attr = me.color_attributes[0]
    me.color_attributes.active_color = attr
    for v in me.vertices:
        attr.data[v.index].color = (*cor_fn(v.co), 1.0)


def cor_crosta(co):
    p = co.normalized()
    h = noise.fractal(p * 1.9, 0.6, 2.2, 5)                      # continentes
    lat = abs(p.z)
    if lat > 0.86:
        return (0.93, 0.95, 0.96)                                  # gelo nos polos
    if h > 0.05:
        return (0.42, 0.55, 0.28) if h < 0.42 else (0.62, 0.52, 0.36)
    return (0.20, 0.42, 0.66)                                      # oceano


r_dentro = 0.0
for nome, r, cor in CAMADAS:
    casca = esfera(nome, r)
    if r_dentro > 0:
        miolo = esfera(nome + "_miolo", r_dentro * 0.999)
        booleana(casca, miolo, "DIFFERENCE")
        bpy.data.objects.remove(miolo)
    # o pedaço que sai (fatia) é a mesma casca intersectada com o octante
    bpy.ops.object.select_all(action="DESELECT")
    casca.select_set(True)
    bpy.context.view_layer.objects.active = casca
    bpy.ops.object.duplicate()
    fatia = bpy.context.object
    fatia.name = "fatia_" + nome
    cubo = octante("oct_" + nome, 1.05)
    booleana(casca, cubo, "DIFFERENCE")
    booleana(fatia, cubo, "INTERSECT")
    bpy.data.objects.remove(cubo)
    for o in (casca, fatia):
        if cor is None:
            pinta(o, lambda co: cor_crosta(co) if co.length > 0.985 else (0.55, 0.40, 0.30))
        else:
            pinta(o, lambda co, c=cor: c)
    r_dentro = r
bpy.ops.wm.save_as_mainfile(filepath=saida)
print("ok", [o.name for o in cena.objects])
