"""A mão do atlas com esqueleto: os dedos dobram e soltam (exemplo "estalar os dedos").

Regra: mão parada com só os ossos mexendo dentro da janela fica simples demais; os dedos precisam se mover. Aqui a pele (Z-Anatomy, CC BY-SA 4.0) ganha um esqueleto feito dos próprios ossos dos dedos:
- 3 ossos por dedo (falanges), 3 no polegar, a palma e o antebraço (que gira, para virar a mão de lado);
- as articulações saem das pontas dos ossos medidos no Blender (nada suposto): MCP = entre a cabeça do metacarpo e a base
  da falange proximal, PIP e DIP = entre as pontas das falanges;
- pesos por distância inversa aos segmentos dos ossos (a mesma ideia do boneco de terno, com a pele toda numa malha só: as
  costuras entre dorso, palma e dedos pesam igual porque os vértices coincidem).

Clipes (quadros do Blender; o 2D troca a 7 qps):
    A    1–18   o gancho: estala os 4 dedos um a um (mão virada 36°) e gira de volta para as costas da mão
    B   21–56   a mão esquerda (a do estudo do médico): estala dedo atrás de dedo, 3 ciclos (virada 30°)
    C   61–85   as duas mãos: fecham e abrem juntas (virada 18°)
    D   91–99   gira para as costas e dá o último estalo do indicador
    E  101      a mão parada virada 30° (a direita, o "controle")
    G  105–109  a mão gira das costas para 30°
    F  111–140  o indicador puxado, de costas: a pele acompanha o osso puxado na janela

    "$BLENDER" --background --factory-startup --python mao_rig_blender.py -- <mao.blend> <saida.blend> <clipes.json>"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

entrada, saida, saida_json = (Path(a) for a in sys.argv[sys.argv.index("--") + 1:][:3])
bpy.ops.wm.open_mainfile(filepath=str(entrada))


def vs(o):
    return np.array([(o.matrix_world @ v.co)[:] for v in o.data.vertices])


def eixo(o):
    """(base, ponta) do osso: o eixo principal da malha, orientado para cima (+Z)"""
    p = vs(o)
    c = p.mean(0)
    _, _, vt = np.linalg.svd(p - c, full_matrices=False)
    ax = vt[0] if vt[0][2] > 0 else -vt[0]
    t = (p - c) @ ax
    return Vector(c + ax * t.min()), Vector(c + ax * t.max())


def osso(nome):
    return bpy.data.objects[f"osso__{nome}"]


# ------------------------------------------------------------------ 1. as articulações, medidas nos ossos
NOMES = {"2": "second", "3": "third", "4": "fourth", "5": "fifth"}
ORD = {"2": "Second", "3": "Third", "4": "Fourth", "5": "Fifth"}
art = {}
for k, n in NOMES.items():
    pb, pt = eixo(osso(f"Proximal phalanx of {n} finger of hand.r"))
    mb, mt = eixo(osso(f"Middle phalanx of {n} finger of hand.r"))
    db, dt = eixo(osso(f"Distal phalanx of {n} finger of hand.r"))
    _, cab = eixo(osso(f"{ORD[k]} metacarpal bone.r"))
    ponta = dt + (dt - db).normalized() * 0.004                         # a polpa passa 4 mm do osso
    art[k] = [(cab + pb) / 2, (pt + mb) / 2, (mt + db) / 2, ponta]       # MCP, PIP, DIP, ponta
c1b, c1t = eixo(osso("First metacarpal bone.r"))
p1b, p1t = eixo(osso("Proximal phalanx of first finger of hand.r"))
d1b, d1t = eixo(osso("Distal phalanx of first finger of hand.r"))
art["1"] = [c1b, (c1t + p1b) / 2, (p1t + d1b) / 2, d1t + (d1t - d1b).normalized() * 0.004]   # CMC, MCP, IP, ponta
peles = [o for o in bpy.data.objects if o.name.startswith("pele__")]
fa = np.concatenate([vs(o) for o in peles if "forearm" in o.name or "wrist" in o.name])
sel = fa[(fa[:, 2] > -0.93) & (fa[:, 2] < -0.89)]
cx, cy = float(sel[:, 0].mean()), float(sel[:, 1].mean())               # o eixo do antebraço
PUNHO = Vector((cx, cy, -0.856))

# ------------------------------------------------------------------ 2. só a pele (uma malha), sem ossos e sem luva
for o in list(bpy.data.objects):
    if not o.name.startswith("pele__") and o.type == "MESH":
        bpy.data.objects.remove(o)
bpy.ops.object.select_all(action="DESELECT")
for o in peles:
    o.select_set(True)
bpy.context.view_layer.objects.active = peles[0]
bpy.ops.object.join()
pele = bpy.context.view_layer.objects.active
pele.name = "pele"
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 3. o esqueleto
arm_d = bpy.data.armatures.new("mao_rig")
arm = bpy.data.objects.new("mao_rig", arm_d)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_d.edit_bones


def osso_novo(nome, a, b, pai=None):
    e = eb.new(nome)
    e.head, e.tail = Vector(a), Vector(b)
    if pai:
        e.parent = eb[pai]
    return e


osso_novo("braco", (cx, cy, -1.15), PUNHO)
palma_topo = sum((art[k][0] for k in "2345"), Vector()) / 4
osso_novo("palma", PUNHO, palma_topo, "braco")
for k in "2345":
    osso_novo(f"{k}p", art[k][0], art[k][1], "palma")
    osso_novo(f"{k}m", art[k][1], art[k][2], f"{k}p")
    osso_novo(f"{k}d", art[k][2], art[k][3], f"{k}m")
osso_novo("1c", art["1"][0], art["1"][1], "palma")
osso_novo("1p", art["1"][1], art["1"][2], "1c")
osso_novo("1d", art["1"][2], art["1"][3], "1p")
bpy.ops.object.mode_set(mode="OBJECT")

# ------------------------------------------------------------------ 4. pesos: distância inversa aos segmentos
seg = [("braco", Vector((cx, cy, -1.15)), PUNHO)]
for k in "2345":
    seg.append(("palma", PUNHO, art[k][0]))                              # as linhas dos metacarpos
for a, b in (("2", "3"), ("3", "4"), ("4", "5")):
    seg.append(("palma", art[a][0], art[b][0]))                          # a linha dos nós dos dedos
seg.append(("palma", PUNHO, art["1"][0]))
for k in "2345":
    for i, s in enumerate("pmd"):
        seg.append((f"{k}{s}", art[k][i], art[k][i + 1]))
for i, s in enumerate("cpd"):
    seg.append((f"1{s}", art["1"][i], art["1"][i + 1]))
A = np.array([s[1][:] for s in seg])
B = np.array([s[2][:] for s in seg])
P_ = vs(pele)
AB = B - A
den = (AB ** 2).sum(1)
dist = np.empty((len(P_), len(seg)))
for j in range(len(seg)):
    t = np.clip(((P_ - A[j]) @ AB[j]) / den[j], 0, 1)
    dist[:, j] = np.linalg.norm(P_ - (A[j] + t[:, None] * AB[j]), axis=1)
w = 1.0 / (dist + 0.002) ** 3
nomes_osso = [s[0] for s in seg]
nomes_unicos = sorted(set(nomes_osso))
W = np.zeros((len(P_), len(nomes_unicos)))
for j, n in enumerate(nomes_osso):
    W[:, nomes_unicos.index(n)] += w[:, j]
W /= W.sum(1, keepdims=True)
for n in nomes_unicos:
    pele.vertex_groups.new(name=n)
for i in range(len(P_)):
    top = np.argsort(-W[i])[:4]
    tot = W[i, top].sum()
    for ti in top:
        if W[i, ti] / tot > 0.015:
            pele.vertex_groups[nomes_unicos[ti]].add([i], float(W[i, ti] / tot), "REPLACE")
pele.parent = arm
mod = pele.modifiers.new("Armature", "ARMATURE")
mod.object = arm
bpy.ops.object.select_all(action="DESELECT")
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 5. eixos de flexão (no plano de cada dedo)
pb = arm.pose.bones
for b in pb:
    b.rotation_mode = "QUATERNION"
EIXO = {}
for k in "2345":
    d = (art[k][3] - art[k][0]).normalized()
    ax = d.cross(Vector((0, 1, 0))).normalized()                         # perpendicular ao dedo, no plano da palma
    # sinal: a flexão leva a ponta para o lado da palma (+Y)
    q = Quaternion(ax, math.radians(30))
    if (q @ (art[k][3] - art[k][0])).y < (art[k][3] - art[k][0]).y:
        ax = -ax
    EIXO[k] = ax
d1 = (art["1"][3] - art["1"][1]).normalized()
ax1 = d1.cross(Vector((0, 1, 0))).normalized()
if (Quaternion(ax1, math.radians(30)) @ (art["1"][3] - art["1"][1])).y < (art["1"][3] - art["1"][1]).y:
    ax1 = -ax1
EIXO["1"] = ax1


def local(nome, eixo_mundo, graus):
    """quaternion no espaço do osso para girar 'graus' em volta de um eixo do mundo"""
    R = arm_d.bones[nome].matrix_local.to_3x3()
    return Quaternion(R.inverted() @ eixo_mundo, math.radians(graus))


FULL = (64, 96, 54)          # a flexão máxima de nó, meio e ponta (graus)


def pose(f, az=0.0, flex=None, abre=None, pulgar=0.0):
    """flex: {dedo: fator} (1 = punho cerrado; <0 = estica além do reto); abre: leque (graus) entre os dedos"""
    flex = flex or {}
    for b in pb:
        b.rotation_quaternion = Quaternion((1, 0, 0, 0))
    pb["braco"].rotation_quaternion = Quaternion((0, 1, 0), math.radians(az))   # em volta do eixo do antebraço
    for k in "2345":
        fator = flex.get(k, 0.0)
        pb[f"{k}p"].rotation_quaternion = local(f"{k}p", EIXO[k], FULL[0] * fator)
        pb[f"{k}m"].rotation_quaternion = local(f"{k}m", EIXO[k], FULL[1] * fator)
        pb[f"{k}d"].rotation_quaternion = local(f"{k}d", EIXO[k], FULL[2] * fator)
        if abre:
            lado = {"2": -1.0, "3": -0.3, "4": 0.4, "5": 1.2}[k]
            pb[f"{k}p"].rotation_quaternion = local(f"{k}p", Vector((0, 1, 0)), abre * lado) @ pb[f"{k}p"].rotation_quaternion
    if pulgar:
        pb["1c"].rotation_quaternion = local("1c", EIXO["1"], 28 * pulgar)
        pb["1p"].rotation_quaternion = local("1p", EIXO["1"], 30 * pulgar)
        pb["1d"].rotation_quaternion = local("1d", EIXO["1"], 25 * pulgar)
    for b in pb:
        b.keyframe_insert("rotation_quaternion", frame=f)


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def estala(t):
    """o fator de flexão de UM dedo que estala, t = quadros desde o começo do ciclo: dobra, aperta, solta além do reto"""
    return {0: 0.0, 1: 0.62, 2: 1.0, 3: -0.2}.get(t, 0.0)


clipes = {}
# A: o gancho (18 quadros): os 4 dedos estalam um a um, escalonados de 3 em 3 quadros; a mão gira de volta
fa_ = list(range(1, 19))
for f in fa_:
    ordem = {"2": 1, "3": 4, "4": 7, "5": 10}
    flex = {k: estala(f - ini) for k, ini in ordem.items()}
    az = 36.0 * (1 - suave((f - 11) / 7))
    pose(f, az=az, flex=flex)
clipes["A"] = fa_
# B: a mão esquerda do médico (36 quadros = 3 ciclos de 12): estala dedo atrás de dedo, virada 30°
fb = list(range(21, 57))
for f in fb:
    flex = {}
    for k, off in {"2": 0, "3": 3, "4": 6, "5": 9}.items():
        flex[k] = estala((f - 21 - off) % 12)
    pose(f, az=30.0, flex=flex)
clipes["B"] = fb
# C: as duas mãos fecham e abrem juntas (25 quadros), viradas 18°
fc = list(range(61, 86))
ciclo = [0.0, 0.45, 0.85, 1.0, 1.0, 0.7, 0.2, -0.12, -0.05, 0.0, 0.0, 0.0]            # fecha, segura, abre em leque
for i, f in enumerate(fc):
    v = ciclo[i % 12] if i < 24 else 0.0
    flex = {k: v * (1 - 0.06 * j) for j, k in enumerate("2345")}
    pose(f, az=18.0, flex=flex, abre=10.0 * max(0.0, -v) * 6, pulgar=max(v, 0.0) * 0.8)
clipes["C"] = fc
# D: a mão gira de 18° para as costas (3 quadros) e dá o último estalo do indicador (9 quadros)
fd = list(range(91, 100))
for i, f in enumerate(fd):
    pose(f, az=18.0 * (1 - suave(i / 2)), flex={"2": estala(i - 3)})
clipes["D"] = fd
# E: a mão parada virada 30° (a direita, o "controle")
pose(101, az=30.0)
clipes["E"] = [101]
# G: a mão gira das costas para 30° (5 quadros)
fg = list(range(105, 110))
for i, f in enumerate(fg):
    pose(f, az=30.0 * suave(i / 4))
clipes["G"] = fg
# F: o indicador puxado, de costas (30 quadros = os 30 da junta): a pele do dedo acompanha o osso puxado na janela
D_REP, D_PUXA = 0.0045, 0.0125
def d_junta(f):
    if f == 1:
        return D_REP
    if f <= 8:
        return D_REP + (D_PUXA - D_REP) * suave((f - 1) / 7)
    if f <= 11:
        return D_PUXA
    if f == 12:
        return D_PUXA - 0.0010
    t = (f - 12) / 18
    return (D_PUXA - 0.0010) + (D_REP - (D_PUXA - 0.0010)) * suave(t)
ff = list(range(111, 141))
for i, f in enumerate(ff):
    pose(f, az=0.0)
    delta = d_junta(i + 1) - D_REP                                      # em m, ao longo do dedo
    pb["2p"].location = (0, delta, 0)
    pb["2p"].keyframe_insert("location", frame=f)
clipes["F"] = ff

bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(saida), compress=True)
json.dump({k: v for k, v in clipes.items()}, open(saida_json, "w"))
print("ok", saida, {k: len(v) for k, v in clipes.items()})
