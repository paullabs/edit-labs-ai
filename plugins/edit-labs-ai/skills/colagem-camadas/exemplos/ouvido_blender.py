"""OPCIONAL. O ouvido esquerdo do atlas Z-Anatomy para a cena da perda de audição do exemplo do espirro: pavilhão (pele),
osso temporal, membrana timpânica, os três ossinhos (martelo, bigorna, estribo) e a cóclea com o vestíbulo. Vista de lado
(a câmera do lado esquerdo do corpo; o rosto fica à esquerda), sem corte: o pavilhão sai, aparecem o tímpano, os
ossinhos e a cóclea.

LICENÇA: no atlas, a orelha interna e os ossículos são CC BY-NC-SA 4.0 (University of Dundee), não CC BY-SA. Por isso
este ouvido NÃO vem em nenhum pacote da release e o exemplo roda sem ele (a cena fica na traqueia). Se você montar o
ouvido com o seu Z-Anatomy_Startup.blend, o vídeo passa a ter partes de uso NÃO comercial: credite "Orelha interna e
ossículos: University of Dundee, CC BY-NC-SA 4.0" e não use em conteúdo comercial (monetizado, anúncio, cliente).

    "$BLENDER" --background --factory-startup --disable-autoexec --python ouvido_blender.py -- <Z-Anatomy_Startup.blend> \
        <trabalho>/espirro/garganta/ouvido.blend
    clpy garganta_render.py ouvido"""
import re
import sys

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
fonte, saida = args[0], args[1]
bpy.ops.wm.open_mainfile(filepath=fonte)
dg = bpy.context.evaluated_depsgraph_get()
YCORTE = 0.001

CORES = {"pele": (0.87, 0.71, 0.58), "osso": (0.94, 0.90, 0.78), "membr": (0.93, 0.72, 0.66), "ossic": (0.99, 0.97, 0.90),
         "coclea": (0.92, 0.55, 0.50), "vest": (0.86, 0.46, 0.42), "tuba": (0.88, 0.60, 0.56)}
mats = {}


def mat(n):
    if n not in mats:
        m = bpy.data.materials.new(n)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[n]]
        m.diffuse_color = (*lin, 1.0)
        mats[n] = m
    return mats[n]


col = bpy.data.collections.new("OUVIDO")
bpy.context.scene.collection.children.link(col)
src = {o.name: o for o in bpy.data.objects if o.type == "MESH" and len(o.data.polygons) > 0}


def pega(nome, prefixo, cor, corta_y=False):
    o = src[nome]
    oe = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(oe, preserve_all_data_layers=False, depsgraph=dg)
    me.transform(o.matrix_world)
    if corta_y:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, YCORTE, 0), plane_no=(0, 1, 0),
                               clear_inner=True, clear_outer=False)
        bm.to_mesh(me)
        bm.free()
    if len(me.polygons) == 0:
        return
    me.materials.clear()
    me.materials.append(mat(cor))
    ob = bpy.data.objects.new(f"{prefixo}__{nome}", me)
    col.objects.link(ob)


pega("Temporal bone.l", "ouv_osso", "osso")
pega("Tympanic membrane.l", "ouv_membr", "membr")
for n in ("Malleus.l", "Incus.l", "Stapes.l"):
    pega(n, "ouv_ossic", "ossic")
pega("Cochlea.l", "ouv_coclea", "coclea")
pega("Vestibule.l", "ouv_coclea", "vest")
if "Auditory tube.l" in src:
    pega("Auditory tube.l", "ouv_osso", "tuba")
AURICULA = r"^(Helix|Antihelix|Antitragus|Tragus|Concha of auricle|Cavity of concha|Cymba conchae|Eminentia .*|Fossa antihelica|Scapha|Lobule of auricle|Crura of antihelix|Triangular fossa|Intertragic incisure|Anterior notch of auricle|Apex of auricle|Auricular tubercle|Auricular region|Posterior auricular groove)\.l$"
for n in src:
    if re.match(AURICULA, n):
        pega(n, "ouv_pele", "pele")

# marcador do centro (pivô da câmera): um triângulo minúsculo em (x, y, z) = (0,070, 0,005, 1,585)
me = bpy.data.meshes.new("ref")
me.from_pydata([(0.070, 0.005, 1.585), (0.0701, 0.005, 1.585), (0.070, 0.0051, 1.585)], [], [(0, 1, 2)])
me.materials.append(mat("pele"))
ref = bpy.data.objects.new("ouv_ref__centro", me)
col.objects.link(ref)
for o in list(bpy.data.objects):
    if o.name not in col.objects:
        bpy.data.objects.remove(o, do_unlink=True)
for c in list(bpy.data.collections):
    if c is not col:
        bpy.data.collections.remove(c)
for bloco in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves, bpy.data.lights, bpy.data.cameras):
    for b in list(bloco):
        if b.users == 0:
            bloco.remove(b)
cont = {}
for o in col.objects:
    p = o.name.split("__")[0]
    cont[p] = cont.get(p, 0) + 1
print("GRUPOS", cont)
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida)
