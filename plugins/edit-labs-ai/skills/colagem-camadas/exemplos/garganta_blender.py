"""Monta a "garganta" (cabeça, pescoço e peito de cima) em camadas a partir do atlas Z-Anatomy completo (CC BY-SA 4.0),
num .blend só, com cada peça já em coordenadas do mundo, prefixada pela camada e com a cor de prancha.

Você NÃO precisa rodar isto para o exemplo: o resultado já vem exportado em GLB no pacote colagem-zanatomy-garganta da
release (preparar.py espirro usa garganta_glb.py). Este script fica como receita para cortar OUTRA região do atlas.
Ele lê o Z-Anatomy_Startup.blend (baixe você mesmo em https://github.com/Z-Anatomy/Models-of-human-anatomy). Atenção:
o atlas completo tem partes com licença não comercial (rim, orelha interna, ossículos) e um cérebro sem licença
declarada; este corte só pega peças CC BY-SA (pele, músculos, ossos, cartilagens, vias aéreas, pulmão, esôfago).

    "$BLENDER" --background --factory-startup --disable-autoexec --python garganta_blender.py -- <Z-Anatomy_Startup.blend> <saida.blend>

Dois grupos, para a MESMA câmera lateral (câmera do lado direito do corpo, olhando para o lado esquerdo):
  fora__pele / fora__musc / fora__faringe : as camadas de fora, inteiras (o que se descasca)
  dentro__osso / dentro__pulm / dentro__via : o corte sagital (metade esquerda, x >= 0): o ar passa pelo canal aberto
  atras__...                                : a laringe vista por trás, com a parede de trás aberta (metade da frente)

Peça que o atlas NÃO tem e que é MODELO PRÓPRIO (declarar no crédito): o seio piriforme (o bolsinho de cada lado da entrada
da laringe), medido pelas peças vizinhas do próprio atlas. O esôfago e os brônquios do atlas são curvas com bisel e entram
pela avaliação do objeto."""
import json
import math
import re
import sys

import bmesh
import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
fonte, saida = args[0], args[1]
bpy.ops.wm.open_mainfile(filepath=fonte)
dg = bpy.context.evaluated_depsgraph_get()

ZCORTE = 1.12                                   # o corte de baixo: o peito de cima
YCORTE_ATRAS = -0.0035                          # o corte da parede de trás da faringe (a vista por trás fica com a metade da frente)

CORES = {                                       # sRGB de prancha antiga (vira a aquarela no papelizar)
    "pele": (0.87, 0.71, 0.58), "musc": (0.74, 0.24, 0.21), "faringe": (0.80, 0.33, 0.30),
    "osso": (0.94, 0.90, 0.78), "cartilagem": (0.80, 0.86, 0.84), "dente": (0.98, 0.96, 0.90),
    "mucosa": (0.93, 0.60, 0.58), "lingua": (0.88, 0.42, 0.42), "palato": (0.90, 0.50, 0.50),
    "gengiva": (0.90, 0.55, 0.52), "traqueia": (0.88, 0.84, 0.76), "esofago": (0.82, 0.50, 0.42),
    "bolso": (0.97, 0.45, 0.36), "pulmao": (0.90, 0.58, 0.55), "epiglote": (0.78, 0.88, 0.84),
}
mats = {}


def mat(nome):
    if nome not in mats:
        m = bpy.data.materials.new(nome)
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in CORES[nome]]
        m.diffuse_color = (*lin, 1.0)
        mats[nome] = m
    return mats[nome]


col_dest = bpy.data.collections.new("GARGANTA")
bpy.context.scene.collection.children.link(col_dest)
src = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.polygons) > 0]
por_nome = {o.name: o for o in src}


def malha_mundo(o):
    oe = o.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(oe, preserve_all_data_layers=False, depsgraph=dg)
    me.transform(o.matrix_world)
    return me


def corta(me, co, no):
    """fica com o lado para onde a normal aponta"""
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, clear_inner=True, clear_outer=False)
    bm.to_mesh(me)
    bm.free()


def novo(nome, me, cor):
    if len(me.polygons) == 0:
        bpy.data.meshes.remove(me)
        return None
    me.materials.clear()
    me.materials.append(mat(cor))
    o = bpy.data.objects.new(nome, me)
    col_dest.objects.link(o)
    return o


contagem = {}


def pega(o, prefixo, cor, x_ge0=False, y_ate=None):
    me = malha_mundo(o)
    corta(me, (0, 0, ZCORTE), (0, 0, 1))
    if x_ge0:
        corta(me, (0, 0, 0), (1, 0, 0))
    if y_ate is not None:
        corta(me, (0, y_ate, 0), (0, -1, 0))
    n = novo(f"{prefixo}__{o.name}", me, cor)
    if n:
        contagem[prefixo] = contagem.get(prefixo, 0) + 1
    return n


def centro(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return [(min(p[i] for p in pts) + max(p[i] for p in pts)) / 2 for i in range(3)]


def colecao(o):
    return o.users_collection[0].name if o.users_collection else ""


# ---------- classes
BRACO = re.compile(r"\barm\b|elbow|forearm|deltoid|bicipital|cubital|wrist|\bhand\b|axillary fossa", re.I)
PELE_FORA = re.compile(r"hair|eyelash|\bline\b|lines$", re.I)
FASCIA = re.compile(r"fascia|bursa|aponeuros|tendinous ring|tarsus|trochlea|tendon\b", re.I)
COSTAS_FUNDO = re.compile(r"intercostal|serratus|latissimus|rotatores|levatores|multifidus|iliocostalis|longissimus thoracis|"
                          r"spinalis thoracis|interspinales|semispinalis thoracis|transversus|subscap|supraspin|infraspin|teres|"
                          r"coracobrachial|subclavius|pectoralis minor|abdominal part|rhomboid|serratus", re.I)
OLHO_LINGUA = re.compile(r"rectus muscle|oblique muscle|levator palpebrae|genioglossus|hyoglossus|geniohyoid|medial pterygoid|"
                         r"pterygoid|rectus (anterior|lateralis|posterior)|obliquus|longus|interspinales|longissimus|"
                         r"spinalis|multifidus colli|corrugator|palatopharyngeus|stylopharyngeus|constrictor|crico|thyro-|"
                         r"ary-|arytenoid|transverse arytenoid", re.I)
FARINGE = re.compile(r"pharyngeal constrictor|palatopharyngeus|stylopharyngeus|cricothyroid|cricopharyngeal", re.I)

OSSO_NOMES = re.compile(r"^(Occipital bone|Parietal bone\.l|Frontal bone|Temporal bone\.l|Sphenoid bone|Ethmoid bone|Maxilla\.l|"
                        r"Zygomatic bone\.l|Palatine bone\.l|Vomer|Nasal bone\.l|Lacrimal bone\.l|Inferior nasal concha bone\.l|"
                        r"Mandible|Hyoid bone|Atlas \(C1\)|Axis \(C2\)|Vertebra [CT]\d+|Body of sternum|Manubrium of sternum|"
                        r"Xiphoid process|Clavicle\.l|.* rib\.l|Costal cartilage of .*\.l|Nasal septal cartilage|"
                        r"Major alar cartilage\.l|Lateral process of nasal septal cartilage\.l)$")
DENTE = re.compile(r"^(Upper|Lower) .*(incisor|canine|premolar|molar).*\.l$|^(Upper|Lower) medial incisor\.l$")
CARTILAGEM = re.compile(r"^(Thyroid cartilage|Cricoid cartilage|Arytenoid cartilage\.l|Corniculate cartilage\.l|"
                        r"Nasal septal cartilage|Major alar cartilage\.l|Lateral process of nasal septal cartilage\.l|"
                        r"Costal cartilage of .*\.l)$")

# ---------- grupo FORA (inteiro, os dois lados)
for o in src:
    n, c = o.name, colecao(o)
    cx, cy, cz = centro(o)
    if c.startswith("9:") and not (BRACO.search(n) or PELE_FORA.search(n)):
        pega(o, "fora_pele", "pele")
    elif c.startswith("4:") and abs(cx) <= 0.13 and cz >= 1.18:
        if FARINGE.search(n):
            pega(o, "fora_faringe", "faringe")
        elif not (FASCIA.search(n) or COSTAS_FUNDO.search(n) or OLHO_LINGUA.search(n) or BRACO.search(n)
                  or n.startswith("Epicranial")):
            pega(o, "fora_musc", "musc")

# ---------- grupo DENTRO (corte sagital: metade esquerda, x >= 0)
LUMEN = {"Mucosa of nasal cavity": "mucosa", "Nasopharynx": "mucosa", "Oropharynx": "mucosa", "Laryngopharynx": "mucosa",
         "Tongue": "lingua", "Soft palate": "palato", "Uvula of palate": "palato", "Gingiva": "gengiva",
         "Trachea": "traqueia", "Epiglottis": "epiglote"}
for o in src:
    n, c = o.name, colecao(o)
    if c.startswith("1:") and OSSO_NOMES.match(n) and not re.search(r"Scapula|Humerus", n):
        if re.search(r"\.r$", n):
            continue
        cor = "cartilagem" if CARTILAGEM.match(n) else "osso"
        pega(o, "dentro_osso", cor, x_ge0=True)
    elif c.startswith("1:") and DENTE.match(n):
        pega(o, "dentro_osso", "dente", x_ge0=True)
    elif n in ("Thyroid cartilage", "Cricoid cartilage", "Arytenoid cartilage.l", "Corniculate cartilage.l"):
        pega(o, "dentro_osso", "cartilagem", x_ge0=True)
    elif n in LUMEN:
        pega(o, "dentro_via", LUMEN[n], x_ge0=True)
    elif n in ("Superior lobe of left lung", "Inferior lobe of left lung"):
        pega(o, "dentro_pulm", "pulmao", x_ge0=True)

# ---------- o atlas tem o esôfago e os brônquios como CURVAS com bisel (não são malhas): entram no corte sagital
curvas = {o.name: o for o in bpy.data.objects if o.type == "CURVE"}
pega(curvas["Oesophagus"], "dentro_via", "esofago", x_ge0=True)
for nm, o in curvas.items():
    if re.search(r"bronch", nm, re.I) and centro(o)[0] >= -0.012:
        pega(o, "dentro_bronq", "traqueia", x_ge0=True)

# ---------- peça própria: o seio piriforme (o atlas não tem; medido pelas peças vizinhas)
# seio piriforme esquerdo: bolso achatado ao lado da entrada da laringe (z do osso hioide ao cricoide)
BOLSO = {"cx": 0.0135, "cy": -0.0125, "cz": 1.4815, "rx": 0.0050, "ry": 0.0085, "rz": 0.0150}


def bolso(nome, lado=1, prefixo="dentro_via"):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=20, radius=1.0)
    for v in bm.verts:
        t = (v.co.z + 1) / 2                         # 0 embaixo (ápice), 1 em cima (boca larga)
        sx, sy = 0.65 + 0.55 * t, 0.55 + 0.6 * t
        v.co = Vector((lado * BOLSO["cx"] + v.co.x * BOLSO["rx"] * sx, BOLSO["cy"] + v.co.y * BOLSO["ry"] * sy,
                       BOLSO["cz"] + v.co.z * BOLSO["rz"]))
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    return novo(f"{prefixo}__{nome}", me, "bolso")


bolso("Seio piriforme .l (modelo proprio)")

# ---------- grupo ATRÁS: a laringe vista por trás, com a parede de trás aberta (fica a metade da frente, y <= YCORTE_ATRAS)
ATRAS = {"Laryngopharynx": "mucosa", "Oropharynx": "mucosa", "Epiglottis": "epiglote", "Tongue": "lingua",
         "Thyroid cartilage": "cartilagem", "Cricoid cartilage": "cartilagem", "Arytenoid cartilage.l": "cartilagem",
         "Arytenoid cartilage.r": "cartilagem", "Corniculate cartilage.l": "cartilagem", "Corniculate cartilage.r": "cartilagem",
         "Hyoid bone": "osso", "Trachea": "traqueia", "Soft palate": "palato", "Uvula of palate": "palato"}
for nm, cor in ATRAS.items():
    o = por_nome[nm]
    nome = "atras_via" if cor in ("mucosa", "epiglote", "lingua", "palato", "traqueia") else "atras_osso"
    pega(o, nome, cor, y_ate=YCORTE_ATRAS)
pega(por_nome["Cricoid cartilage"], "atras_osso", "cartilagem", y_ate=YCORTE_ATRAS)
for lado, nome in ((1, "Seio piriforme .l (modelo proprio)"), (-1, "Seio piriforme .r (modelo proprio)")):
    bolso(nome, lado=lado, prefixo="atras_via")
for o in src:
    if FARINGE.search(o.name) and colecao(o).startswith("4:"):
        pega(o, "atras_faringe", "faringe")

# ---------- limpa: fica só a coleção GARGANTA
for o in list(bpy.data.objects):
    if o.name not in col_dest.objects:
        bpy.data.objects.remove(o, do_unlink=True)
for col in list(bpy.data.collections):
    if col is not col_dest:
        bpy.data.collections.remove(col)
for bloco in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.armatures, bpy.data.curves, bpy.data.lights,
              bpy.data.cameras):
    for b in list(bloco):
        if b.users == 0:
            bloco.remove(b)

info = {}
for o in col_dest.objects:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    p = o.name.split("__")[0]
    d = info.setdefault(p, {"n": 0, "mn": [9, 9, 9], "mx": [-9, -9, -9]})
    d["n"] += 1
    for i in range(3):
        d["mn"][i] = min(d["mn"][i], min(q[i] for q in pts))
        d["mx"][i] = max(d["mx"][i], max(q[i] for q in pts))
for k, v in sorted(info.items()):
    print("GRUPO", k, v["n"], [round(x, 3) for x in v["mn"]], [round(x, 3) for x in v["mx"]])
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida)
