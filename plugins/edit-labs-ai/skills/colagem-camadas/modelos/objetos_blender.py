"""Objetos 3D próprios (sem licença de terceiros), para comparações e cortes:
  moeda      moeda dourada com aro e miolo em relevo (pilhas de moedas lado a lado)
  maco       maço de notas verdes com a cinta de papel (pilhas de dinheiro)
  navio_*    petroleiro em corte: casco inteiro (fora), casco cortado (o lado de perto aberto), tanques e a carga

    "$BLENDER" --background --factory-startup --python objetos_blender.py -- <saida.blend>"""
import math
import sys

import bmesh
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


OURO, OURO_E = mat("ouro", (0.90, 0.72, 0.28)), mat("ouro_e", (0.74, 0.56, 0.18))
# ---------------- moeda (em x = 100, longe do resto)
bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=0.16, vertices=96, location=(100, 0, 0.08))
fin(bpy.context.object, "moeda__corpo", OURO)
bpy.ops.mesh.primitive_torus_add(major_radius=0.93, minor_radius=0.06, location=(100, 0, 0.165), major_segments=96)
fin(bpy.context.object, "moeda__aro", OURO_E)
bpy.ops.mesh.primitive_cylinder_add(radius=0.62, depth=0.03, vertices=96, location=(100, 0, 0.17))
fin(bpy.context.object, "moeda__miolo", OURO_E)
for k in range(12):                                                         # raios em relevo no miolo
    a = 2 * math.pi * k / 12
    bpy.ops.mesh.primitive_cube_add(size=1, location=(100 + 0.38 * math.cos(a), 0.38 * math.sin(a), 0.19))
    o = bpy.context.object
    o.scale = (0.22, 0.035, 0.02)
    o.rotation_euler = (0, 0, a)
    fin(o, f"moeda__raio{k}", OURO)
# ---------------- maço de notas (em x = 200)
VERDE, VERDE_E, CINTA = mat("verde", (0.62, 0.74, 0.55)), mat("verde_e", (0.40, 0.55, 0.38)), mat("cinta", (0.92, 0.86, 0.66))
bpy.ops.mesh.primitive_cube_add(size=1, location=(200, 0, 0.13))
o = bpy.context.object
o.scale = (1.56, 0.66, 0.26)
bpy.ops.object.transform_apply(scale=True)
fin(o, "maco__notas", VERDE)
for k in range(9):                                                          # as bordas das notas (riscas na lateral)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(200, -0.332, 0.03 + k * 0.025))
    o = bpy.context.object
    o.scale = (1.54, 0.004, 0.006)
    fin(o, f"maco__risca{k}", VERDE_E)
bpy.ops.mesh.primitive_cube_add(size=1, location=(200, 0, 0.13))
o = bpy.context.object
o.scale = (0.30, 0.68, 0.28)
fin(o, "maco__cinta", CINTA)
bpy.ops.mesh.primitive_cube_add(size=1, location=(200 - 0.5, 0, 0.262))       # o retrato oval da nota de cima
o = bpy.context.object
o.scale = (0.30, 0.36, 0.004)
fin(o, "maco__retrato", VERDE_E)
# ---------------- petroleiro (em x = 0), proa para +x
L, B, D, LIN = 24.0, 4.0, 2.6, 1.15                 # comprimento, boca, pontal, linha d'água


def contorno(n=60):
    """o casco visto de cima: popa reta, costado paralelo e a proa curva"""
    pts = []
    for i in range(n + 1):                            # bordo de bombordo (y>0), da popa à proa
        x = -L / 2 + L * i / n
        y = B / 2 if x < L / 2 - 5 else B / 2 * math.sqrt(max(0.0, 1 - ((x - (L / 2 - 5)) / 5) ** 2))
        pts.append((x, y))
    return pts + [(x, -y) for x, y in reversed(pts[:-1])]


def casco(nome, z0, z1, m, corta_perto=False):
    me = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    pts = contorno()
    if corta_perto:                                   # tira o costado de perto (y < 0): a cavidade aparece
        pts = [(x, max(y, 0.0)) for x, y in pts]
    vb = [bm.verts.new((x, y, z0)) for x, y in pts]
    vt = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        if corta_perto and pts[i][1] <= 0.0 and pts[j][1] <= 0.0:
            continue
        bm.faces.new([vb[i], vb[j], vt[j], vt[i]])
    if not corta_perto:
        bm.faces.new(vt)
        bm.faces.new(list(reversed(vb)))
    else:
        bm.faces.new(list(reversed(vb)))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(m)
    return ob


VERMELHO, PRETO, CONVES = mat("casco_v", (0.66, 0.18, 0.14)), mat("casco_p", (0.16, 0.16, 0.18)), mat("conves", (0.42, 0.50, 0.42))
BRANCO, JANELA, DIESEL = mat("branco", (0.93, 0.92, 0.88)), mat("janela", (0.20, 0.26, 0.32)), mat("diesel", (0.95, 0.76, 0.18))
INTERIOR = mat("interior", (0.52, 0.52, 0.50))
casco("navio_fora__baixo", 0.0, LIN, VERMELHO)
casco("navio_fora__alto", LIN, D, PRETO)
casco("navio_corte__baixo", 0.0, LIN, VERMELHO, corta_perto=True)
casco("navio_corte__alto", LIN, D, PRETO, corta_perto=True)
# fundo e parede de longe por dentro (cinza), para a cavidade ler como tanque
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.6, B / 4, 0.08))
o = bpy.context.object
o.scale = (17.0, B / 2 * 0.96, 0.12)
fin(o, "navio_corte__fundo", INTERIOR)
for k in range(6):                                  # anteparas: 5 tanques de carga
    x = -7.2 + k * 3.4
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, B / 4, D / 2))
    o = bpy.context.object
    o.scale = (0.12, B / 2, D)
    fin(o, f"navio_tanques__antepara{k}", INTERIOR)
for k in range(5):                                  # o diesel em cada tanque (a altura sobe no 2D)
    x = -7.2 + 1.7 + k * 3.4
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, B / 4 - 0.02, D * 0.46))
    o = bpy.context.object
    o.scale = (3.25, B / 2 - 0.06, D * 0.9)
    fin(o, f"navio_diesel__d{k}", DIESEL)
# convés por cima do casco inteiro, superestrutura na popa, chaminé e a tubulação do convés
for pref in ("navio_fora", "navio_corte"):
    me_alvo = None
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0.0, D + 0.03))
o = bpy.context.object
o.scale = (L - 4.5, B * 0.96, 0.06)
fin(o, "navio_fora__conves", CONVES)
for k in range(3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-9.4, 0.0, D + 0.55 + k * 0.95))
    o = bpy.context.object
    o.scale = (3.0 - k * 0.4, B * 0.86, 0.9)
    fin(o, f"navio_ponte__andar{k}", BRANCO)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-9.4 + 0.02, -B * 0.43 - 0.01, D + 0.62 + k * 0.95))
    o = bpy.context.object
    o.scale = (2.6 - k * 0.4, 0.02, 0.22)
    fin(o, f"navio_ponte__janelas{k}", JANELA)
bpy.ops.mesh.primitive_cylinder_add(radius=0.45, depth=2.0, location=(-10.6, 0.0, D + 3.6))
fin(bpy.context.object, "navio_ponte__chamine", PRETO)
bpy.ops.mesh.primitive_cylinder_add(radius=0.47, depth=0.35, location=(-10.6, 0.0, D + 4.1))
fin(bpy.context.object, "navio_ponte__faixa", VERMELHO)
for j, yy in enumerate((-0.5, 0.0, 0.5)):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=16.5, location=(0.5, yy, D + 0.2), rotation=(0, math.pi / 2, 0))
    fin(bpy.context.object, f"navio_ponte__tubo{j}", mat("tubo", (0.86, 0.80, 0.30)))
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida, len(bpy.data.objects))
