"""O crânio que abre: a calota (tampa) sai e mostra o cérebro boiando no líquor. Todas as peças ficam no MESMO lugar
(camadas registradas), num .blend só, para o blender_giro renderizar tudo pela mesma câmera.

    "$BLENDER" --background --factory-startup --python cranio_blender.py -- \\
        <zanatomy_cranio.glb> <pasta bodyparts3d-partof-obj99> <saida.blend>

Fontes:
    crânio   Z-Anatomy (zanatomy_cranio.glb), CC BY-SA 4.0. O hioide (osso solto embaixo da mandíbula) fica de fora.
    cérebro  BodyParts3D 4.0 (part_of, OBJ 99), CC BY-SA 2.1 JP: hemisférios (FMA61819, FMA67292), cerebelo (FMA67944),
             ponte (FMA67943), bulbo (FMA62004) e mesencéfalo (FMA61993). O cérebro do .blend do Z-Anatomy NÃO é usado.

Prefixos no .blend:
    base__   o crânio abaixo do corte, com a face do corte (base__corte)
    tampa__  a calota acima do corte, com a face do corte por baixo (tampa__corte)
    cer__    hemisférios cerebrais
    cbl__    cerebelo e tronco
    liq__    o líquor: casca contínua 3,5 mm maior que o cérebro, presa por dentro do osso

O corte (como numa autópsia): plano 2 cm acima da margem supraorbital, inclinado 10° (mais baixo atrás). As duas peças
de cada osso cortado guardam as normais originais (sem costura quando a tampa está no lugar). A face do corte é um anel
fechado medido por raios no próprio plano (da tábua interna à externa) e pintado num marfim mais escuro.

O cérebro vai para o sistema do Z-Anatomy pelo alinhamento.json (corpo inteiro) e depois por um ICP rígido dos ossos do
neurocrânio do BodyParts3D (frontal, parietais, occipital, esfenoide) sobre os do Z-Anatomy, que leva o cérebro para a
cavidade deste crânio. Depois: escala 0,96 em volta do centro dele e um ajuste suave (≤ 3 mm) onde ainda encostaria
no osso da abóbada. Grava também <saida>_info.json com o plano, as transformações, as medidas e os centros."""
import json
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

args = sys.argv[sys.argv.index("--") + 1:]
GLB, BP3D, SAIDA = Path(args[0]), Path(args[1]), Path(args[2])
INFO = SAIDA.with_name(SAIDA.stem + "_info.json")
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene
col = cena.collection
info = {}

CORES = {                                             # sRGB (o material leva em linear)
    "osso": (0.95, 0.92, 0.82), "cartilagem": (0.80, 0.86, 0.86), "corte": (0.80, 0.74, 0.62),
    "hemisferio": (0.86, 0.64, 0.64), "cerebelo": (0.76, 0.52, 0.54), "tronco": (0.88, 0.74, 0.70),
    "liquor": (0.62, 0.80, 0.92),
}
lin = lambda c: [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
mats = {}


def mat(nome):
    if nome not in mats:
        m = bpy.data.materials.new(nome)
        m.diffuse_color = (*lin(CORES[nome]), 1.0)
        m.roughness = 0.6
        mats[nome] = m
    return mats[nome]


def malha_de(objs, matriz=None):
    """bmesh com as malhas (em coordenadas do mundo) de uma lista de objetos"""
    bm = bmesh.new()
    for o in objs:
        me = o.data.copy()
        me.transform((matriz or Matrix()) @ o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    return bm


def bvh_de(objs):
    bm = malha_de(objs)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def todos_hits(arvore, origem, d, maxd=0.3):
    """distâncias de todas as superfícies que o raio atravessa"""
    out, p = [], origem.copy()
    for _ in range(40):
        r = arvore.ray_cast(p, d, maxd)
        if r[0] is None:
            break
        out.append((r[0] - origem).length)
        p = r[0] + d * 1e-6
    return out


def ultimo_hit(arvore, origem, d, maxd=0.3):
    h = todos_hits(arvore, origem, d, maxd)
    return h[-1] if h else None


# ------------------------------------------------------------------ 1. crânio (Z-Anatomy)
bpy.ops.import_scene.gltf(filepath=str(GLB))
bpy.context.view_layer.update()
for o in list(bpy.data.objects):
    if o.type == "MESH":
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
for o in list(bpy.data.objects):
    if o.type != "MESH" or re.search(r"hyoid", o.name, re.I):     # o hioide fica solto embaixo da mandíbula: sai
        bpy.data.objects.remove(o)
cranio = []
for o in list(bpy.data.objects):                                # lista fixa: renomear reordena a coleção
    if o.data.users > 1:
        o.data = o.data.copy()
    o.data.transform(o.matrix_world)                               # tudo em coordenadas do mundo
    o.matrix_world = Matrix()
    for i, m in enumerate(o.data.materials):                       # cada slot vira osso ou cartilagem
        cart = re.search(r"cartilag", (m.name if m else "") + " " + o.name, re.I)
        o.data.materials[i] = mat("cartilagem" if cart else "osso")
    cn = np.zeros(len(o.data.loops) * 3, dtype=np.float32)        # as normais originais vão junto no corte
    o.data.corner_normals.foreach_get("vector", cn)
    at = o.data.attributes.new("nrm", "FLOAT_VECTOR", "CORNER")
    at.data.foreach_set("vector", cn)
    o.name = "osso__" + o.name
    cranio.append(o)
bpy.context.view_layer.update()
B_CRANIO = bvh_de(cranio)                                          # o crânio inteiro (antes do corte)

# ------------------------------------------------------------------ 2. corte da calota
Z_MARGEM = 1.613                  # margem supraorbital (medida por raios de frente, x = ±3 cm)
Y_TESTA = -0.087                  # a testa na altura do corte (perfil sagital)
INCL = math.radians(10)           # mais baixo atrás
P0 = Vector((0.0, Y_TESTA, Z_MARGEM + 0.020))
N = Vector((0.0, math.sin(INCL), math.cos(INCL)))                 # normal para cima (e para trás)
info["corte"] = {"ponto": list(P0), "normal": list(N), "inclinacao_graus": 10, "acima_da_margem_m": 0.020,
                 "z_frente": P0.z, "z_tras_y0.10": P0.z - math.tan(INCL) * (0.10 - Y_TESTA)}


def area_lados(me):
    """área de faces acima e abaixo do plano (pelo centro da face)"""
    a = [0.0, 0.0]
    for p in me.polygons:
        a[(p.center - P0).dot(N) > 0] += p.area
    return a


def restaura_normais(me):
    at = me.attributes.get("nrm")
    if at is None:
        return
    v = np.zeros(len(me.loops) * 3, dtype=np.float32)
    at.data.foreach_get("vector", v)
    v = v.reshape(-1, 3)
    v /= np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
    me.normals_split_custom_set(v.tolist())
    me.attributes.remove(me.attributes["nrm"])


def tira_fiapos(bm, area_min=1.5e-6):
    """componentes soltos minúsculos (< 1,5 mm²) que o corte deixa"""
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    visto, fora = set(), []
    for f0 in bm.faces:
        if f0.index in visto:
            continue
        comp, pilha = [], [f0]
        visto.add(f0.index)
        while pilha:
            f = pilha.pop()
            comp.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in visto:
                        visto.add(g.index)
                        pilha.append(g)
        if sum(f.calc_area() for f in comp) < area_min:
            fora += comp
    if fora:
        bmesh.ops.delete(bm, geom=fora, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    return len(fora)


cortados, inteiros, fiapos = [], {"base": [], "tampa": []}, 0
base_objs, tampa_objs = [], []
for o in cranio:
    nome = o.name.split("__", 1)[1]
    acima = [(v.co - P0).dot(N) for v in o.data.vertices]
    a_baixo, a_cima = area_lados(o.data)
    tot = a_baixo + a_cima
    # inteiro de um lado: nada do outro, ou só uma ponta interna (< 2% e < 0,5 cm²), como o seio frontal
    if max(acima) <= 0 or (a_cima < 0.02 * tot and a_cima < 5e-5):
        o.name = "base__" + nome
        restaura_normais(o.data)
        base_objs.append(o)
        inteiros["base"].append(nome)
        continue
    if min(acima) >= 0 or (a_baixo < 0.02 * tot and a_baixo < 5e-5):
        o.name = "tampa__" + nome
        restaura_normais(o.data)
        tampa_objs.append(o)
        inteiros["tampa"].append(nome)
        continue
    t = o.copy()
    t.data = o.data.copy()
    col.objects.link(t)
    for ob, lado in ((o, "base"), (t, "tampa")):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7, plane_co=P0,
                               plane_no=N, clear_inner=(lado == "tampa"), clear_outer=(lado == "base"))
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        fiapos += tira_fiapos(bm)
        bm.to_mesh(ob.data)
        bm.free()
        restaura_normais(ob.data)
        ob.name = f"{lado}__{nome}"
        (base_objs if lado == "base" else tampa_objs).append(ob)
    cortados.append({"osso": nome, "area_cima_cm2": round(a_cima * 1e4, 2), "area_baixo_cm2": round(a_baixo * 1e4, 2)})
info["corte"]["ossos_cortados"] = cortados
info["corte"]["inteiros_na_tampa"] = inteiros["tampa"]
info["corte"]["faces_de_fiapo_removidas"] = fiapos
print("cortados:", [c["osso"] for c in cortados], "| inteiros na tampa:", inteiros["tampa"], "| fiapos:", fiapos)

# ------------------------------------------------------------------ 3. a face do corte (anel fechado, medido por raios)
U = Vector((1.0, 0.0, 0.0))
W = N.cross(U).normalized()                       # no plano, para trás e para baixo
centro_anel = P0 + W * 0.095                     # ~ meio da cavidade no plano (a testa fica em P0)
M_RAIOS = 1440


def mede_anel(c, m):
    rin, rout = np.full(m, np.nan), np.full(m, np.nan)
    for i in range(m):
        a = 2 * math.pi * i / m
        d = (U * math.cos(a) + W * math.sin(a)).normalized()
        h = todos_hits(B_CRANIO, c, d, 0.2)
        if len(h) >= 2:
            rin[i], rout[i] = h[0], h[-1]
    return rin, rout


rin, rout = mede_anel(centro_anel, 360)                            # 1ª passada: recentra no meio da cavidade
ang = np.linspace(0, 2 * math.pi, 360, endpoint=False)
ok = ~np.isnan(rin)
pts = [centro_anel + (U * math.cos(a) + W * math.sin(a)) * r for a, r in zip(ang[ok], rin[ok])]
centro_anel = sum(pts, Vector()) / len(pts)
rin, rout = mede_anel(centro_anel, M_RAIOS)


def limpa(r, janela=9, lim=0.0015):
    """raio que passou por uma fresta (sutura, forame) volta para a mediana dos vizinhos"""
    m = len(r)
    out = r.copy()
    trocados = 0
    for i in range(m):
        viz = np.array([r[(i + k) % m] for k in range(-janela, janela + 1)])
        viz = viz[~np.isnan(viz)]
        med = np.median(viz)
        if np.isnan(r[i]) or abs(r[i] - med) > lim:
            out[i] = med
            trocados += 1
    return out, trocados


rin, t_in = limpa(rin)
rout, t_out = limpa(rout)
espessura = (rout - rin) * 1000
info["corte"]["anel"] = {"raios": M_RAIOS, "raios_corrigidos": [int(t_in), int(t_out)],
                         "espessura_mm": [round(float(espessura.min()), 2), round(float(np.median(espessura)), 2),
                                          round(float(espessura.max()), 2)],
                         "centro": list(centro_anel)}
print("anel: espessura do osso (mm) min/med/max", info["corte"]["anel"]["espessura_mm"], "corrigidos", t_in, t_out)


def faz_anel(nome, normal_para_cima):
    bm = bmesh.new()
    vin, vout = [], []
    for i in range(M_RAIOS):
        a = 2 * math.pi * i / M_RAIOS
        d = (U * math.cos(a) + W * math.sin(a)).normalized()
        vin.append(bm.verts.new(centro_anel + d * rin[i]))
        vout.append(bm.verts.new(centro_anel + d * rout[i]))
    for i in range(M_RAIOS):
        j = (i + 1) % M_RAIOS
        f = bm.faces.new((vin[i], vout[i], vout[j], vin[j]))
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    if (bm.faces[0].normal.dot(N) > 0) != normal_para_cima:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("corte"))
    ob = bpy.data.objects.new(nome, me)
    col.objects.link(ob)
    return ob


base_objs.append(faz_anel("base__corte", True))
tampa_objs.append(faz_anel("tampa__corte", False))

# remendos: no ptério o frontal, o parietal, o esfenoide e o temporal do Z-Anatomy não se encostam e sobra um furinho
# (~2 mm) 4 mm abaixo do corte; com o cérebro atrás ele virava um ponto rosa no osso (achado no render da vista A).
# Uma pastilha de osso (cilindro fechado de 1,2 mm: disco aberto faz sombra errada no Workbench) no meio da
# parede tapa o furo (dos dois lados) e fica escondida pelo osso no resto.
C_CAV = Vector((0.0, 0.005, 1.60))                      # ~ centro da cavidade


def remendo(furo, nome, raio=0.0025):
    eixo = (furo - C_CAV).normalized()
    t1 = eixo.orthogonal().normalized()
    t2 = eixo.cross(t1)
    meios = []
    for k in range(12):                                  # parede em volta do furo: tábua interna e externa
        a_ = 2 * math.pi * k / 12
        alvo = furo + (t1 * math.cos(a_) + t2 * math.sin(a_)) * 0.003
        d = (alvo - C_CAV).normalized()
        h = todos_hits(B_CRANIO, C_CAV, d, 0.2)
        if len(h) >= 2:
            meios.append((h[0] + h[1]) / 2)
    r = sorted(meios)[len(meios) // 2]
    centro = C_CAV + eixo * r
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=raio, radius2=raio, depth=0.0012,   # sólido
                          matrix=Matrix.Translation(centro) @ eixo.to_track_quat("Z", "Y").to_matrix().to_4x4())
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("osso"))
    ob = bpy.data.objects.new(nome, me)
    col.objects.link(ob)
    acima = max((ob.matrix_world @ v.co - P0).dot(N) for v in me.vertices)
    info.setdefault("corte", {}).setdefault("remendos", []).append(
        {"nome": nome, "centro": list(centro), "raio_mm": raio * 1000, "folga_ate_o_corte_mm": round(-acima * 1000, 2)})
    return ob


for lado, sx in (("r", -1), ("l", 1)):
    base_objs.append(remendo(Vector((sx * 0.0535, -0.0380, 1.6205)), f"base__remendo_pterio.{lado}"))
print("remendos:", info["corte"]["remendos"])

# a tampa é uma peça só? (componentes por topologia, unidos por proximidade de 1,5 mm, com o anel no meio)
bm = malha_de(tampa_objs)
bm.verts.ensure_lookup_table()
pai = list(range(len(bm.verts)))


def acha(i):
    while pai[i] != i:
        pai[i] = pai[pai[i]]
        i = pai[i]
    return i


for e in bm.edges:
    a_, b_ = acha(e.verts[0].index), acha(e.verts[1].index)
    if a_ != b_:
        pai[a_] = b_
celulas = {}
for v in bm.verts:
    k = tuple(int(math.floor(c / 0.0015)) for c in v.co)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                w = celulas.get((k[0] + dx, k[1] + dy, k[2] + dz))
                if w is not None:
                    a_, b_ = acha(v.index), acha(w)
                    if a_ != b_:
                        pai[a_] = b_
    celulas[k] = v.index
grupos = {}
for v in bm.verts:
    grupos.setdefault(acha(v.index), []).append(v.index)
tam = sorted((len(g) for g in grupos.values()), reverse=True)
info["corte"]["tampa_pecas_por_proximidade"] = tam[:10]
print("tampa: peças (vértices) por proximidade", tam[:10])
bm.free()

# ------------------------------------------------------------------ 4. cérebro (BodyParts3D)
al = json.loads((BP3D / "alinhamento.json").read_text())["transformacao"]
ESC = np.array([t["escala"] for t in al])
DES = np.array([t["desloc"] for t in al])
PASTA_OBJ = BP3D / "partof_BP3D_4.0_obj_99"


def le_obj(f):
    """OBJ do BodyParts3D (mm) -> vértices no sistema do Z-Anatomy (alinhamento.json), faces e nome em inglês"""
    vs, fs, nome = [], [], f.stem
    for l in open(f, encoding="latin-1"):
        if l.startswith("v "):
            vs.append(l.split()[1:4])
        elif l.startswith("f "):
            fs.append([int(t.split("/")[0]) - 1 for t in l.split()[1:]])
        elif l.startswith("# English name"):
            nome = l.split(":", 1)[1].strip()
    v = np.array(vs, dtype=float) * ESC + DES
    return v, fs, nome


# 4a. ICP rígido: ossos do neurocrânio do BP3D -> os mesmos ossos do Z-Anatomy (o cérebro vai junto)
PARES = {"FJ3200": "Frontal bone", "FJ3274": "Parietal bone.l", "FJ3380": "Parietal bone.r",
         "FJ3309": "Occipital bone", "FJ3394": "Sphenoid bone"}
src, idx, arvores = [], [], []
for k, (fj, za) in enumerate(PARES.items()):
    v, _, _ = le_obj(PASTA_OBJ / f"{fj}.obj")
    src.append(v[::3])
    idx += [k] * len(v[::3])
    arvores.append(bvh_de([o for o in base_objs + tampa_objs if o.name.split("__", 1)[1] == za]))
src, idx = np.vstack(src), np.array(idx)
T = np.eye(4)
P = src.copy()
hist_icp = []
for it in range(40):
    Q = np.zeros_like(P)
    D = np.zeros(len(P))
    for i in range(len(P)):
        q, _, _, d = arvores[idx[i]].find_nearest(Vector(P[i]))
        Q[i], D[i] = q, d
    ok = D <= np.percentile(D, 70)                       # ICP aparado: os 70% mais próximos
    mp, mq = P[ok].mean(0), Q[ok].mean(0)
    U_, S_, Vt = np.linalg.svd((Q[ok] - mq).T @ (P[ok] - mp))
    Dm = np.diag([1, 1, np.sign(np.linalg.det(U_ @ Vt))])
    R = U_ @ Dm @ Vt
    t = mq - R @ mp
    P = (R @ P.T).T + t
    M4 = np.eye(4)
    M4[:3, :3], M4[:3, 3] = R, t
    T = M4 @ T
    if it in (0, 39):
        hist_icp.append(round(float(np.median(D)) * 1000, 2))
ang_icp = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(T[:3, :3]) - 1) / 2))))
info["cerebro"] = {"icp": {"matriz": T.tolist(), "rotacao_graus": round(ang_icp, 2),
                           "dist_mediana_mm_antes_depois": hist_icp, "ossos": PARES}}
print("ICP: dist mediana (mm)", hist_icp, "rot", round(ang_icp, 2))

# 4b. as peças do cérebro
linhas = [l.rstrip("\n").split("\t") for l in open(BP3D / "download/partof_element_parts.txt", encoding="utf-8")][1:]
conceito = {}
for c, nm, f in linhas:
    conceito.setdefault(c, (nm, []))[1].append(f)
GRUPOS = [("FMA61819", "cer", "hemisferio"), ("FMA67292", "cer", "hemisferio"), ("FMA67944", "cbl", "cerebelo"),
          ("FMA67943", "cbl", "tronco"), ("FMA62004", "cbl", "tronco"), ("FMA61993", "cbl", "tronco")]
cerebro, usados, cx0 = [], [], []
for fma, pre, cor in GRUPOS:
    for fj in conceito[fma][1]:
        v, fs, nome = le_obj(PASTA_OBJ / f"{fj}.obj")
        cx0 += [v.min(0), v.max(0)]
        v = (T[:3, :3] @ v.T).T + T[:3, 3]
        me = bpy.data.meshes.new(f"{pre}__{fj}")
        me.from_pydata(v.tolist(), [], fs)
        me.validate()
        me.shade_smooth()
        me.materials.append(mat(cor))
        ob = bpy.data.objects.new(f"{pre}__{fj} {nome}", me)
        col.objects.link(ob)
        cerebro.append(ob)
        usados.append({"arquivo": f"{fj}.obj", "nome": nome, "conceito": f"{fma} {conceito[fma][0]}", "prefixo": pre})
info["cerebro"]["arquivos"] = usados


def pontos(objs):
    return np.array([v.co[:] for o in objs for v in o.data.vertices])


pc = pontos(cerebro)
C_CER = Vector(((pc.min(0) + pc.max(0)) / 2).tolist())
c0 = (np.min(cx0, 0) + np.max(cx0, 0)) / 2
info["cerebro"]["icp"]["centro_do_cerebro_moveu_mm"] = [round(float(x) * 1000, 2) for x in (np.array(C_CER) - c0)]
print("ICP: o centro do cérebro andou (mm)", info["cerebro"]["icp"]["centro_do_cerebro_moveu_mm"])


def penetracao(objs, c):
    """quanto o cérebro passa da tábua interna, por raios saindo do centro (abóbada: elevação -20° a 88°)"""
    bm = malha_de(objs)
    arv = BVHTree.FromBMesh(bm)
    bm.free()
    pen = []
    for el in range(-20, 90, 4):
        for az in range(0, 360, 4):
            d = Vector((math.cos(math.radians(el)) * math.sin(math.radians(az)),
                        -math.cos(math.radians(el)) * math.cos(math.radians(az)), math.sin(math.radians(el))))
            r = B_CRANIO.ray_cast(c, d, 0.3)
            rb = ultimo_hit(arv, c, d)
            if r[0] is not None and rb is not None:
                pen.append(rb - (r[0] - c).length)
    a = np.array(pen) * 1000
    return {"raios": len(a), "max_mm": round(float(a.max()), 2), "p99_mm": round(float(np.percentile(a, 99)), 2),
            "pct_encostando": round(float((a > 0).mean() * 100), 1), "folga_mediana_mm": round(float(np.median(-a)), 2)}


info["cerebro"]["penetracao_sem_escala"] = penetracao(cerebro, C_CER)
ESCALA = 0.96
Ms = Matrix.Translation(C_CER) @ Matrix.Scale(ESCALA, 4) @ Matrix.Translation(-C_CER)
for o in cerebro:
    o.data.transform(Ms)
info["cerebro"]["escala"] = ESCALA
info["cerebro"]["penetracao_escala"] = penetracao(cerebro, C_CER)

# 4c. onde ainda encostaria na abóbada, o cérebro assenta no osso (compressão suave, folga de 1 mm)
FOLGA, FAIXA = 0.0010, 0.0015
mexidos, maior = 0, 0.0
cache = {}
for o in cerebro:
    me = o.data
    for v in me.vertices:
        d = v.co - C_CER
        r = d.length
        if r < 1e-6:
            continue
        d /= r
        if math.degrees(math.asin(max(-1.0, min(1.0, d.z)))) < -25:   # base do crânio: raios do centro não servem
            continue
        chave = (round(d.x, 3), round(d.y, 3), round(d.z, 3))
        if chave not in cache:
            h = B_CRANIO.ray_cast(C_CER, d, 0.3)
            cache[chave] = (h[0] - C_CER).length if h[0] is not None else None
        rin_ = cache[chave]
        if rin_ is None:
            continue
        lim = rin_ - FOLGA
        if r > lim - FAIXA:
            novo = lim - FAIXA * math.exp(-(r - (lim - FAIXA)) / FAIXA)
            maior = max(maior, r - novo)
            v.co = C_CER + d * novo
            mexidos += 1
    me.update()
info["cerebro"]["assentado"] = {"vertices": mexidos, "maior_desloc_mm": round(maior * 1000, 2)}
info["cerebro"]["penetracao_final"] = penetracao(cerebro, C_CER)
print("cérebro: penetração", info["cerebro"]["penetracao_sem_escala"], "->", info["cerebro"]["penetracao_escala"],
      "->", info["cerebro"]["penetracao_final"], "| assentado", info["cerebro"]["assentado"])
# 4d. o bulbo termina no forame magno (abaixo dele ficaria um toco pendurado embaixo do crânio, sem a coluna)
def forame():
    """básio e opístio: as bordas do forame magno na linha do meio (raios descendo por dentro do crânio)"""
    ys = [k / 2000 for k in range(-20, 160)]
    zs = []
    for y in ys:
        h = B_CRANIO.ray_cast(Vector((0.0, y, 1.62)), Vector((0, 0, -1)), 0.2)
        zs.append(None if h[0] is None else h[0].z)
    furo = [i for i, z in enumerate(zs) if z is None]
    i0, i1 = furo[0] - 1, furo[-1] + 1
    return Vector((0.0, ys[i0], zs[i0])), Vector((0.0, ys[i1], zs[i1]))


BASIO, OPISTIO = forame()
tf = (OPISTIO - BASIO).normalized()
NF = Vector((0.0, -tf.z, tf.y))
if NF.z < 0:
    NF = -NF
PF = (BASIO + OPISTIO) / 2 - NF * 0.002                     # 2 mm abaixo da borda de dentro: o corte some no furo
info["cerebro"]["forame_magno"] = {"basio": list(BASIO), "opistio": list(OPISTIO), "plano_ponto": list(PF),
                                   "plano_normal": list(NF)}


def corta_e_fecha(ob, pco, pno):
    """tira o que está abaixo do plano e fecha a boca do corte"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-7, plane_co=pco, plane_no=pno,
                           clear_inner=True)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bordas = [e for e in bm.edges if e.is_boundary]
    novas = bmesh.ops.holes_fill(bm, edges=bordas, sides=0)["faces"]
    if novas:
        bmesh.ops.triangulate(bm, faces=novas)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.shade_smooth()
    return len(bordas)


cortes_bulbo = {}
for o in cerebro:
    if any((v.co - PF).dot(NF) < 0 for v in o.data.vertices):
        if re.search(r"medulla", o.name, re.I):
            cortes_bulbo[o.name] = corta_e_fecha(o, PF, NF)
        else:
            cortes_bulbo[o.name] = "abaixo do plano, não cortado"
info["cerebro"]["corte_do_bulbo"] = cortes_bulbo
print("forame magno:", [round(x, 4) for x in BASIO], [round(x, 4) for x in OPISTIO], "| corte:", cortes_bulbo)

pc = pontos(cerebro)
info["cerebro"]["caixa"] = [pc.min(0).tolist(), pc.max(0).tolist()]
info["cerebro"]["centro_caixa"] = ((pc.min(0) + pc.max(0)) / 2).tolist()

# ------------------------------------------------------------------ 5. o líquor (casca de 3,5 mm, presa no osso)
OFFSET = 0.0035
for o in cerebro:
    o.select_set(False)
bm = malha_de(cerebro)
me = bpy.data.meshes.new("liq__liquor")
bm.to_mesh(me)
bm.free()
liq = bpy.data.objects.new("liq__liquor", me)
col.objects.link(liq)
ng = bpy.data.node_groups.new("casca_sdf", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
nd = ng.nodes
gi, go = nd.new("NodeGroupInput"), nd.new("NodeGroupOutput")
# fechamento morfológico: dilata 9 mm, alisa, erode 5,5 mm, alisa -> casca lisa (sem o desenho dos giros) a +3,5 mm
DILATA = 0.009
n_sdf = nd.new("GeometryNodeMeshToSDFGrid")
n_sdf.inputs["Voxel Size"].default_value = 0.0008
n_sdf.inputs["Band Width"].default_value = 16
cadeia = [n_sdf]
for dist, larg, it in ((DILATA, 1, 2), (OFFSET - DILATA, 2, 3)):
    n_o = nd.new("GeometryNodeSDFGridOffset")
    n_o.inputs["Distance"].default_value = dist
    n_m = nd.new("GeometryNodeSDFGridMean")
    n_m.inputs["Width"].default_value = larg
    n_m.inputs["Iterations"].default_value = it
    cadeia += [n_o, n_m]
n_mesh = nd.new("GeometryNodeGridToMesh")
n_mesh.inputs["Threshold"].default_value = 0.0
cadeia.append(n_mesh)
ng.links.new(gi.outputs[0], n_sdf.inputs["Mesh"])
for a_, b_ in zip(cadeia, cadeia[1:]):
    ng.links.new(a_.outputs[0], b_.inputs[0])
ng.links.new(n_mesh.outputs[0], go.inputs[0])
mod = liq.modifiers.new("casca", "NODES")
mod.node_group = ng
bpy.context.view_layer.objects.active = liq
liq.select_set(True)
bpy.ops.object.modifier_apply(modifier="casca")
bpy.data.node_groups.remove(ng)
# assenta por dentro da abóbada: raios saindo do centro do cérebro (elevação >= -25°), compressão suave até 0,3 mm
# da tábua interna (o cérebro fica a 1 mm: a casca sempre o cobre); depois alisa (tira o facetado do osso e os vincos) e assenta de novo. Na base do crânio a casca
# fica como saiu do SDF: lá os raios batem em cristas e forames e amassariam a casca (fiapos); ela fica escondida
# pelo osso nas vistas de cima.
FX = 0.0006
me = liq.data
cache_liq = {}


def assenta_liquor(mole):
    n_ = 0
    for v in me.vertices:
        d = v.co - C_CER
        r = d.length
        if r < 1e-6:
            continue
        d /= r
        if math.degrees(math.asin(max(-1.0, min(1.0, d.z)))) < -25:
            continue
        chave = (round(d.x, 3), round(d.y, 3), round(d.z, 3))
        if chave not in cache_liq:
            h = B_CRANIO.ray_cast(C_CER, d, 0.3)
            cache_liq[chave] = (h[0] - C_CER).length if h[0] is not None else None
        if cache_liq[chave] is None:
            continue
        lim = cache_liq[chave] - 0.0003
        if mole and r > lim - FX:
            v.co = C_CER + d * (lim - FX * math.exp(-(r - (lim - FX)) / FX))
            n_ += 1
        elif not mole and r > lim:
            v.co = C_CER + d * lim
            n_ += 1
    me.update()
    return n_


presos = assenta_liquor(True)
bm = bmesh.new()
bm.from_mesh(me)
for _ in range(8):
    bmesh.ops.smooth_vert(bm, verts=bm.verts[:], factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.to_mesh(me)
bm.free()
presos_2 = assenta_liquor(False)
corta_e_fecha(liq, PF, NF)
me = liq.data
me.materials.clear()
me.materials.append(mat("liquor"))
info["liquor"] = {"offset_mm": OFFSET * 1000, "fechamento_mm": [DILATA * 1000, (OFFSET - DILATA) * 1000],
                  "voxel_mm": 0.8, "faces": len(me.polygons), "vertices_assentados_no_osso": presos,
                  "reassentados_depois_de_alisar": presos_2}
print("líquor:", info["liquor"])

# ------------------------------------------------------------------ 6. centros e gravação
pb = pontos([o for o in base_objs + tampa_objs])
pt = pontos(tampa_objs)
info["centros"] = {"cerebro": info["cerebro"]["centro_caixa"],
                   "cranio": ((pb.min(0) + pb.max(0)) / 2).tolist(),
                   "tampa": ((pt.min(0) + pt.max(0)) / 2).tolist(),
                   "tampa_topo": pt[np.argmax(pt[:, 2])].tolist()}
info["caixas"] = {"cranio": [pb.min(0).tolist(), pb.max(0).tolist()], "tampa": [pt.min(0).tolist(), pt.max(0).tolist()]}

# ------------------------------------------------------------------ 7. enquadramento da vista A (para o blender_giro)
# A vista 3/4 escolhida (teste de 25°, 35°, 45° e -35°): giro 35° e elevação 12° mostram o rosto inteiro (as duas
# órbitas) e a tampa como cúpula, com a linha do corte descendo para trás. Os giros usam o mesmo ângulo e elevação.
GIRO_A, ELEV, ALT_A = 35.0, 12.0, 2000
todos = [o for o in bpy.data.objects if o.type == "MESH"]
cantos = np.array([list(v) for o in todos for v in o.bound_box])            # como o blender_giro acha a raiz
R0 = (cantos.min(0) + cantos.max(0)) / 2
g, e = math.radians(GIRO_A), math.radians(ELEV)
Rz = np.array([[math.cos(g), -math.sin(g), 0], [math.sin(g), math.cos(g), 0], [0, 0, 1]])


def projeta(pts_):
    q = (Rz @ (pts_ - R0).T).T + R0
    return q[:, 0], q[:, 1] * math.sin(e) + q[:, 2] * math.cos(e)


sx, sy = projeta(pontos(todos))
W_, H_ = sx.max() - sx.min(), sy.max() - sy.min()
xc = (sx.max() + sx.min()) / 2
zc = ((sy.max() + sy.min()) / 2 - R0[1] * math.sin(e)) / math.cos(e)
sxc, syc = projeta(pb)
info["vista_A"] = {"giro_inicial": GIRO_A, "elevacao": ELEV, "res": [int(round(ALT_A * W_ / H_)), ALT_A],
                   "caixa_mundo": [xc - W_ / 2, zc - H_ / 2, xc + W_ / 2, zc + H_ / 2],
                   "obs": "caixa justa em tudo (crânio, cérebro e líquor) na vista girada; o blender_giro soma 4%",
                   "cranio_ocupa_da_caixa": [round(float((sxc.max() - sxc.min()) / W_), 3),
                                             round(float((syc.max() - syc.min()) / H_), 3)]}
info["marcos"] = {"centro_cerebro": info["centros"]["cerebro"], "centro_cranio": info["centros"]["cranio"],
                  "centro_tampa": info["centros"]["tampa"], "tampa_topo": info["centros"]["tampa_topo"],
                  "corte_testa": list(P0)}
print("vista A:", info["vista_A"])

contagem = {}
for o in bpy.data.objects:
    p = o.name.split("__")[0]
    contagem[p] = contagem.get(p, 0) + 1
info["objetos_por_prefixo"] = contagem
print("objetos por prefixo:", contagem)
INFO.write_text(json.dumps(info, indent=1, ensure_ascii=False))
bpy.ops.wm.save_as_mainfile(filepath=str(SAIDA), compress=True)
print("ok", SAIDA)
