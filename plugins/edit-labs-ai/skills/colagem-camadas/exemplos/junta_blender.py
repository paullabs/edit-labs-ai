"""A junta do dedo que estala (exemplo "O que acontece quando você estala os dedos?").

Parte da mão direita do teste da luva (Z-Anatomy, CC BY-SA 4.0): só os dois ossos da articulação metacarpofalângica do
indicador (o 2º metacarpo e a falange proximal). O resto é feito aqui, à mão:
- cápsula da articulação: uma "pílula" por trás dos ossos (e uma cópia translúcida por cima, no 2D);
- líquido sinovial: outra pílula âmbar, menor, entre a cápsula e os ossos;
- bolha: uma esfera que nasce no vão quando os ossos se afastam.

Os ossos são alinhados (a falange fica no eixo do metacarpo) para o dedo "puxar" em linha reta, e a câmera olha pelo
DORSO, o mesmo lado da vista da mão inteira: a lente de aumento mostra a mesma vista, só ampliada.

Animação (30 quadros; o 2D troca a 7 qps):
    1        repouso (vão pequeno)
    2-8      puxa: a falange sobe, a cápsula estica
    9-11     a bolha nasce (pequena → passa do ponto → assenta)
    12       o dedo relaxa um pouco
    13-30    a bolha some devagar (o "tempo" dos 20 minutos) e o vão fecha

    "$BLENDER" --background --factory-startup --python junta_blender.py -- <mao.blend> <saida.blend>"""
import math
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Matrix, Vector

entrada, saida = Path(sys.argv[sys.argv.index("--") + 1]), Path(sys.argv[sys.argv.index("--") + 2])
bpy.ops.wm.open_mainfile(filepath=str(entrada))

M = bpy.data.objects["osso__Second metacarpal bone.r"]
P = bpy.data.objects["osso__Proximal phalanx of second finger of hand.r"]
for o in list(bpy.data.objects):
    if o not in (M, P) and o.type != "CAMERA":
        bpy.data.objects.remove(o)
bpy.context.view_layer.update()


def verts(o):
    return [o.matrix_world @ v.co for v in o.data.vertices]


def centro(vs):
    return sum(vs, Vector((0, 0, 0))) / len(vs)


def eixo(vs):
    z0, z1 = min(v.z for v in vs), max(v.z for v in vs)
    return (centro([v for v in vs if v.z > z1 - 0.008]) - centro([v for v in vs if v.z < z0 + 0.008])).normalized()


# --- 1. o ponto da junta e o alinhamento dos dois ossos no eixo vertical (rotação só em torno de Y: a vista do dorso
#        não muda, o dedo só "endireita")
vm, vp = verts(M), verts(P)
J = Vector((-0.2957, 0.0372, -0.7690))
am = eixo(vm)
alfa = math.atan2(-am.x, am.z)
Rj = Matrix.Translation(J) @ Matrix.Rotation(alfa, 4, "Y") @ Matrix.Translation(-J)
T = Matrix.Translation(-J) @ Rj                                     # gira em torno de J e leva J para a origem
for o in (M, P):
    o.matrix_world = T @ o.matrix_world
bpy.context.view_layer.update()
vm, vp = verts(M), verts(P)
zm = max(v.z for v in vm)
cabeca = centro([v for v in vm if v.z > zm - 0.006])               # o centro da cabeça do metacarpo
ap = eixo(vp)
beta = math.atan2(-ap.x, ap.z)
Rp = Matrix.Translation(cabeca) @ Matrix.Rotation(beta, 4, "Y") @ Matrix.Translation(-cabeca)
P.matrix_world = Rp @ P.matrix_world                                # a falange fica no eixo do metacarpo
bpy.context.view_layer.update()
vm, vp = verts(M), verts(P)
zm = max(v.z for v in vm)
zp0 = min(v.z for v in vp)
print("eixo meta", eixo(vm).to_tuple(3), "eixo falange", eixo(vp).to_tuple(3))
print("cabeca meta z", round(zm, 4), "base falange z", round(zp0, 4), "cabeca x", round(cabeca.x, 4))

CORES = {"osso": (0.94, 0.90, 0.78), "liquido": (0.96, 0.70, 0.18), "capsula": (0.80, 0.50, 0.42),
         "bolha": (0.80, 0.93, 1.0)}


def mat(nome):
    m = bpy.data.materials.new(nome)
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[nome]]
    m.diffuse_color = (*lin, 1.0)
    return m


for o in (M, P):
    o.data.materials.clear()
    o.data.materials.append(mat("osso"))
    for p in o.data.polygons:
        p.use_smooth = True

# --- 2. a pílula (cápsula e líquido): esfera esticada em duas hastes, com shape key "estica" (o topo sobe d_max)
X0 = cabeca.x                                                        # o eixo do dedo
D_REPOUSO, D_PUXA = 0.0045, 0.0125                                  # quanto a falange sobe (m) além do pose de repouso do modelo


def pilula(nome, raio, meia_haste, z_baixo, extra, material, profundidade=0.55):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=56, ring_count=28)
    ob = bpy.context.object
    ob.name = nome
    me = ob.data
    bpy.ops.object.shade_smooth()
    base, estica = [], []
    for v in me.vertices:
        s = 1.0 if v.co.z > 0 else -1.0
        x, y, z = v.co.x * raio, v.co.y * raio * profundidade, v.co.z * raio
        base.append((x + X0, y + 0.0, z + s * meia_haste + z_baixo + meia_haste))
        estica.append((x + X0, y + 0.0, z + s * meia_haste + z_baixo + meia_haste + (extra if s > 0 else 0.0)))
    ob.shape_key_add(name="base")
    sk = ob.shape_key_add(name="estica")
    for i, v in enumerate(me.vertices):
        ob.data.shape_keys.key_blocks["base"].data[i].co = base[i]
        sk.data[i].co = estica[i]
        v.co = base[i]
    ob.data.materials.clear()
    ob.data.materials.append(mat(material))
    return ob, sk


Z_BAIXO = -0.0185                                                    # o fundo da cápsula, abaixo da junta
capsula, sk_cap = pilula("capsula", 0.0138, 0.0105, Z_BAIXO, D_PUXA, "capsula")
liquido, sk_liq = pilula("liquido", 0.0112, 0.0085, Z_BAIXO + 0.003, D_PUXA, "liquido")

bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=48, ring_count=24, location=(X0, -0.0005, 0))
bolha = bpy.context.object
bolha.name = "bolha"
bpy.ops.object.shade_smooth()
bolha.data.materials.append(mat("bolha"))

# --- 3. a animação
QUADROS = 30


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def estado(f):
    """(d da falange em m, raio da bolha em m) no quadro f"""
    if f == 1:
        return D_REPOUSO, 0.0
    if f <= 8:
        return D_REPOUSO + (D_PUXA - D_REPOUSO) * suave((f - 1) / 7), 0.0
    if f == 9:
        return D_PUXA, 0.0012
    if f == 10:
        return D_PUXA, 0.0046
    if f == 11:
        return D_PUXA, 0.0040
    if f == 12:
        return D_PUXA - 0.0010, 0.0040
    t = (f - 12) / (QUADROS - 12)
    return (D_PUXA - 0.0010) + (D_REPOUSO - (D_PUXA - 0.0010)) * suave(t), 0.0040 * (1 - suave(t) ** 0.8)


for f in range(1, QUADROS + 1):
    d, rb = estado(f)
    P.delta_location = (0, 0, d)
    P.keyframe_insert("delta_location", frame=f)
    v = (d - D_REPOUSO) / (D_PUXA - D_REPOUSO)
    for sk in (sk_cap, sk_liq):
        sk.value = max(0.0, v)
        sk.keyframe_insert("value", frame=f)
    gap_c = (zm + (zp0 + d)) / 2
    # delta_location (e não location): o blender_giro prende tudo a um vazio no centro e uma "location" absoluta
    # animada ficaria deslocada desse centro (a bolha apareceria sobre o osso)
    bolha.delta_location = (0.0, 0.0, gap_c)
    bolha.scale = (max(rb, 1e-5), max(rb, 1e-5) * 0.8, max(rb, 1e-5))
    bolha.keyframe_insert("delta_location", frame=f)
    bolha.keyframe_insert("scale", frame=f)
# (uma chave em CADA quadro inteiro: a interpolação não é usada, o 2D troca de quadro a 7 qps)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(saida), compress=True)
print("ok", saida, "zm", round(zm, 4), "zp0", round(zp0, 4))
