"""O "homem comum" de terno em 3D (regra: a roupa tem que ser recortada e encaixada, nunca pintada sobre o corpo).

Roupa em camadas de verdade: CAMISA (com gravata e gola aberta na frente) por baixo e PALETÓ por cima, com um V
recortado na malha (a camisa aparece pelo V), lapela em relevo, tronco caindo reto (sem as reentrâncias do corpo),
ombro estruturado e manga folgada. Rosto com olhos (o atlas tem só os buracos), sobrancelhas, cabelo e um chapéu do
tamanho certo. O paletó também sai cortado em peças (tronco, braço, antebraço) para a versão 2D, de boneco de papel.

    "$BLENDER" --background --factory-startup --python homem2_blender.py -- <pasta camadas GLB> <pasta texturas> \
        <saida.blend> <pele_bodyparts3d_no_sistema_zanatomy.glb>

Texturas (homem2_textura.py): paleto.png e camisa.png, projetadas de frente, igual à câmera.

O terno é feito da pele inteira do BodyParts3D (uma malha só, alinhada ao atlas): a faixa do tronco e dos braços é
alisada (some o desenho dos músculos) e afastada 1 cm para fora; a textura (homem_textura.py) é projetada de frente, igual à câmera.
Só o exterior (terno, gola, chapéu, cabeça e mãos) tem esqueleto; o interior fica parado na pose de repouso, que é a
pose do quadro 1 (o exterior também está nela), então as camadas encaixam quando o paletó abre.

Ações (quadros da cena, um por desenho de 7 qps):
    1–28     respiro dos braços em laço (mexe 2–3°), quadro 1 = repouso
    101–124  tchau: o braço direito abre 45°, o antebraço sobe e acena duas vezes, e desce

Prefixos: musc__, osso__, org__, pul__ (pulmões), cor__ (coração), pelev__ (pele à vista), olho__, cabelo, paleto,
camisa, gola, chapeu__, e as peças 2D p2_tronco, p2_braco.R/L, p2_antebraco.R/L."""
import math
import re
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index("--") + 1:]
pasta, texturas, saida = Path(args[0]), Path(args[1]), Path(args[2])
TEX_PALETO, TEX_MANGA, TEX_CAMISA = texturas / "paleto.png", texturas / "manga.png", texturas / "camisa.png"
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene
TX0, TX1, TZ0, TZ1 = -0.40, 0.40, 0.64, 1.76                    # a área que a textura cobre (homem2_textura.py)

CORES = {                                                       # sRGB; contraste alto entre as partes
    "musc": (0.72, 0.20, 0.17), "tendao": (0.92, 0.88, 0.78), "osso": (0.95, 0.92, 0.82),
    "cartilagem": (0.80, 0.86, 0.86), "coracao": (0.62, 0.06, 0.08), "pulmao": (0.95, 0.66, 0.62),
    "figado": (0.50, 0.20, 0.15), "estomago": (0.95, 0.76, 0.62), "intestino": (0.92, 0.72, 0.44),
    "traqueia": (0.90, 0.88, 0.80), "pele": (0.86, 0.68, 0.55), "feltro": (0.30, 0.26, 0.23), "fita": (0.10, 0.09, 0.09),
    "cabelo": (0.20, 0.15, 0.12), "sobrancelha": (0.24, 0.17, 0.13), "esclera": (0.95, 0.94, 0.90),
    "iris": (0.36, 0.24, 0.16), "pupila": (0.05, 0.04, 0.04),
}
lin = lambda c: [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
mats = {}


def mat(nome, imagem=None):
    """material com a cor (modo MATERIAL do Workbench) e, para o exterior, uma imagem (modo TEXTURE)"""
    chave = nome + (str(imagem) if imagem else "")
    if chave in mats:
        return mats[chave]
    m = bpy.data.materials.new(nome)
    if nome in CORES:
        m.diffuse_color = (*lin(CORES[nome]), 1.0)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    if imagem is None:                                          # imagem 4×4 da cor chapada (o exterior usa TEXTURE)
        img = bpy.data.images.new(f"cor_{nome}", 4, 4)
        img.pixels = [*CORES[nome], 1.0] * 16                  # a imagem é sRGB: vai a cor como está
        img.pack()
    else:
        img = bpy.data.images.load(str(imagem))
        img.pack()
    tex.image = img
    nt.links.new(tex.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes.active = tex
    mats[chave] = m
    return m


def importa(arquivo, prefixo, cor_de):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(pasta / arquivo))
    bpy.context.view_layer.update()
    novos = [o for o in bpy.data.objects if o not in antes]
    out = []
    for o in novos:
        if o.type != "MESH":
            continue
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        nome = o.name
        cor, pre = cor_de(nome)
        o.name = f"{pre or prefixo}__{nome}"
        o.data.materials.clear()
        o.data.materials.append(mat(cor))
        out.append(o)
    for o in novos:
        if o.type != "MESH":
            bpy.data.objects.remove(o)
    return out


def cor_musc(n):
    return ("tendao" if re.search(r"retinacul|aponeuros|tendin|tarsus|trochlea|sheath|fascia", n, re.I) else "musc"), None


def cor_osso(n):
    return ("cartilagem" if re.search(r"cartilag", n, re.I) else "osso"), None


def cor_org(n):
    for rx, c, pre in ((r"atri|ventric|papillary|leaflet", "coracao", "cor"), (r"lung", "pulmao", "pul"),
                       (r"liver", "figado", None), (r"stomach", "estomago", None),
                       (r"colon|taenia|duoden", "intestino", None), (r"trachea", "traqueia", None)):
        if re.search(rx, n, re.I):
            return c, pre
    return "intestino", None


pele = importa("zanatomy_pele.glb", "pele", lambda n: ("pele", None))
importa("zanatomy_musculos.glb", "musc", cor_musc)
importa("zanatomy_esqueleto.glb", "osso", cor_osso)
importa("zanatomy_orgaos.glb", "org", cor_org)
bpy.context.view_layer.update()

# ------------------------------------------------------------------ classificar a pele
BRACO = re.compile(r"(Deltoid region|region of arm|bicipital groove|region of elbow|Cubital fossa|forearm)\.(r|l)$")
MAO = re.compile(r"(wrist|Dorsum of hand|Palm|digits of hand|Radial foveola)\.(r|l)$")
PESCOCO = re.compile(r"(neck|Sternocleidomastoid|Carotid triangle|Submental|Submandibular)")
PERNA = re.compile(r"(thigh|Urogenital|Femoral|knee|leg|foot|toe|ankle|heel|sole|Popliteal|Calf|crural|patell|tarsal|"
                   r"malleol|digits of foot|Plantar|Dorsum of foot)", re.I)


def centro(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return sum(pts, Vector()) / 8


grupos = {"braco_R": [], "braco_L": [], "mao": [], "pescoco": [], "cabeca": [], "tronco": []}
for o in pele:
    n = o.name.split("__", 1)[1]
    c = centro(o)
    if BRACO.search(n):
        grupos["braco_R" if n.endswith(".r") else "braco_L"].append(o)
    elif MAO.search(n):
        grupos["mao"].append(o)
    elif PESCOCO.search(n):
        grupos["pescoco"].append(o)
    elif c.z > 1.47:
        grupos["cabeca"].append(o)
    elif c.z > 0.84 and not PERNA.search(n):
        grupos["tronco"].append(o)
print({k: len(v) for k, v in grupos.items()})


J = {"S_R": Vector((-0.172, 0.030, 1.378)), "E_R": Vector((-0.226, 0.028, 1.100)), "W_R": Vector((-0.262, 0.010, 0.862)),
     "F_R": Vector((-0.290, -0.060, 0.700))}
for k in list(J):
    J[k[:-1] + "L"] = Vector((-J[k].x, J[k].y, J[k].z))


def suave(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


HEM = 0.855                                                             # a barra do paletó (a mesma altura do punho;
#                                                                         abaixo do começo do pulso: sem brecha na mão)


def v_meia(z):
    """meia-largura do V do paletó na altura z (abre do botão de cima, 1,175 m, até a gola). RETA: é a mesma reta do
    corte (bisect); com uma curva aqui o corte e a escolha das faces discordavam e a borda saía serrilhada"""
    return 0.058 * min(1.0, (z - 1.175) / (1.47 - 1.175)) if z > 1.175 else 0.0


def lapela_fora(z):
    """borda de fora da lapela (do botão até o entalhe)"""
    if z < 1.175:
        return 0.0
    return 0.004 + 0.086 * min(1.0, (z - 1.175) / (1.368 - 1.175)) + (0.02 * (z - 1.368) / 0.1 if z > 1.368 else 0)


def ponto_eixo(p, lado):
    """(distância relativa ao raio do braço, ponto mais perto no eixo, fração ao longo do braço 0..1)"""
    melhor = None
    S, E, W = J[f"S_{lado}"], J[f"E_{lado}"], J[f"W_{lado}"]
    l1, l2 = (E - S).length, (W - E).length
    for a_, b_, r, t0, tl in ((S, E, 0.075, 0.0, l1), (E, W, 0.062, l1, l2)):
        ab = b_ - a_
        t = max(0.0, min(1.0, (p - a_).dot(ab) / ab.length_squared))
        q = a_ + ab * t
        d = (p - q).length
        if melhor is None or d / r < melhor[0]:
            melhor = (d / r, q, (t0 + t * tl) / (l1 + l2))
    return melhor


def importa_pele_inteira(arquivo, nome):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(arquivo))
    bpy.context.view_layer.update()
    novos = [o for o in bpy.data.objects if o not in antes]
    ob = next(o for o in novos if o.type == "MESH")
    mw = ob.matrix_world.copy()
    ob.parent = None
    ob.matrix_world = mw
    for o in novos:
        if o is not ob:
            bpy.data.objects.remove(o)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    ob.name = nome
    return ob


def pertenca(bm):
    """marca cada vértice: braço R/L (perto do eixo e virado para fora, crescendo pelas arestas), ombro (R?/L?, a
    esfera em volta da junta) ou tronco; corta as faces que ligam o antebraço ao quadril e as ilhas soltas"""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    mem, rel_de = {}, {}
    for v in bm.verts:
        lado = "R" if v.co.x < 0 else "L"
        if (v.co - J[f"S_{lado}"]).length < 0.11:
            mem[v.index] = lado + "?"
            continue
        rel, q, _ = ponto_eixo(v.co, lado)
        rel_de[v.index] = rel
        if rel < 0.85 and v.normal.dot(v.co - q) > 0:
            mem[v.index] = lado
    pilha_ = [bm.verts[i] for i, m in mem.items() if m in ("R", "L")]
    while pilha_:
        v = pilha_.pop()
        for e in v.link_edges:
            w = e.other_vert(v)
            if w.index not in mem and rel_de.get(w.index, 9) < 1.1:
                mem[w.index] = mem[v.index]
                pilha_.append(w)
    # a ponte braço-tronco só é cortada LONGE do ombro (o antebraço encostado no quadril). Perto do ombro (axila) ela
    # fica: apagar ali abre um buraco que o braço esconde no repouso e mostra quando sobe
    perto_ombro = lambda f: min((f.calc_center_median() - J["S_R"]).length,
                                (f.calc_center_median() - J["S_L"]).length) < 0.20
    ponte = [f for f in bm.faces if not perto_ombro(f) and
             len({mem.get(v.index, "T").rstrip("?") if not mem.get(v.index, "").endswith("?")
                  else "S" for v in f.verts} - {"S"}) > 1]
    codigo = {"R": 1, "L": 2, "R?": 3, "L?": 4}
    cm = bm.verts.layers.int.get("mem") or bm.verts.layers.int.new("mem")
    for v in bm.verts:
        v[cm] = codigo.get(mem.get(v.index, ""), 0)
    bmesh.ops.delete(bm, geom=ponte, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.verts.ensure_lookup_table()
    visto = set()
    for v0 in list(bm.verts):
        if not v0.is_valid or v0.index in visto:
            continue
        ilha, pilha_ = [v0], [v0]
        visto.add(v0.index)
        while pilha_:
            v = pilha_.pop()
            for e in v.link_edges:
                w = e.other_vert(v)
                if w.index not in visto:
                    visto.add(w.index)
                    ilha.append(w)
                    pilha_.append(w)
        if len(ilha) < 400:
            bmesh.ops.delete(bm, geom=ilha, context="VERTS")
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    return cm


def corta_faixa(bm, z0, z1):
    for z, baixo in ((z0, True), (z1, False)):
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(0, 0, z), plane_no=(0, 0, 1),
                               clear_inner=baixo, clear_outer=not baixo)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.verts.ensure_lookup_table()


def corta_costas(bm, so=lambda f: True):
    """as costas saem com UM corte reto no meio da profundidade do corpo (plano y = mediana), não pela normal: nas
    dobras do quadril a fronteira "normal.y > 0,35" ficava serrilhada e abria frestas, e virava lasca na barra do
    paletó. Vai depois de alisar e afastar (o corte reto é o último passo da forma)"""
    ys = sorted(v.co.y for f in bm.faces if so(f) for v in f.verts)
    if not ys:
        return
    y_meio = ys[len(ys) // 2]
    geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(0, y_meio, 0), plane_no=(0, 1, 0))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y > y_meio and so(f)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()


def alisa(bm, n, so=None):
    for _ in range(n):
        vs = [v for v in bm.verts if not v.is_boundary and (so is None or so(v))]
        bmesh.ops.smooth_vert(bm, verts=vs, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()


def casco_convexo(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts
    cruz = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    baixo, cima = [], []
    for p_ in pts:
        while len(baixo) >= 2 and cruz(baixo[-2], baixo[-1], p_) <= 0:
            baixo.pop()
        baixo.append(p_)
    for p_ in reversed(pts):
        while len(cima) >= 2 and cruz(cima[-2], cima[-1], p_) <= 0:
            cima.pop()
        cima.append(p_)
    return baixo[:-1] + cima[:-1]


def raio_casco(casco, c, ang):
    """distância do centro c até a borda do casco na direção ang"""
    d = Vector((math.cos(ang), math.sin(ang)))
    melhor = 0.0
    n = len(casco)
    for i in range(n):
        a_, b_ = Vector(casco[i]) - c, Vector(casco[(i + 1) % n]) - c
        den = d.x * (b_ - a_).y - d.y * (b_ - a_).x
        if abs(den) < 1e-12:
            continue
        t = (a_.x * (b_ - a_).y - a_.y * (b_ - a_).x) / den
        u = (a_.x * d.y - a_.y * d.x) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6:
            melhor = max(melhor, t)
    return melhor


def uv_frente(bm):
    uv = bm.loops.layers.uv.new("frente")
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = ((lp.vert.co.x - TX0) / (TX1 - TX0), (lp.vert.co.z - TZ0) / (TZ1 - TZ0))


def limpa_normais(ob):
    """o importador de glTF guarda as normais da malha original (custom normals): depois de editar a malha, o
    sombreado continuava desenhando o corpo de antes (o volume na calça, o peitoral no paletó)"""
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception as e:                                              # (sem normais guardadas: nada a limpar)
        print("normais:", ob.name, e)
    ob.data.shade_smooth()


def fecha_malha(ob, bm, textura):
    bm.to_mesh(ob.data)
    bm.free()
    limpa_normais(ob)
    for u in list(ob.data.uv_layers):
        if u.name != "frente":
            ob.data.uv_layers.remove(ob.data.uv_layers[u.name])
    ob.data.uv_layers.active = ob.data.uv_layers["frente"]
    ob.data.uv_layers["frente"].active_render = True
    ob.data.materials.clear()
    ob.data.materials.append(mat(ob.name, textura))


def grupos_pertenca(ob):
    """passa a camada 'mem' do bmesh para grupos de vértices mem_R/L e ombro_R/L"""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    cm = bm.verts.layers.int.get("mem")
    lst = {c: [v.index for v in bm.verts if v[cm] == c] for c in (1, 2, 3, 4)} if cm else {1: [], 2: [], 3: [], 4: []}
    bm.free()
    for c, nome in ((1, "mem_R"), (2, "mem_L"), (3, "ombro_R"), (4, "ombro_L")):
        vg = ob.vertex_groups.new(name=nome)
        vg.add(lst[c], 1.0, "REPLACE")


def faz_camisa(arquivo):
    """camisa: só o tronco da pele inteira, alisado e 4 mm para fora (as mangas ficam dentro do paletó)"""
    ob = importa_pele_inteira(arquivo, "camisa")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    corta_faixa(bm, 0.68, 1.475)
    # em cima: na frente sobe até a gola (senão a pele do pescoço aparece no V); nos ombros fica abaixo do paletó
    acima = lambda v: v.co.z > (1.462 if abs(v.co.x) < 0.075 and v.co.y < 0 else 1.440)     # a gola cobre a borda
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(acima(v) for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    cm = pertenca(bm)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(v[cm] in (1, 2) for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    mao = [f for f in bm.faces if any(abs(v.co.x) > 0.195 and v.co.z < 0.90 for v in f.verts)]   # as mãos não
    bmesh.ops.delete(bm, geom=mao, context="FACES")                                                 # são camisa
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # a calça: a faixa do meio abaixo da barra do paletó sai (as pernas saem separadas por baixo do paletó, como
    # numa calça vista de frente). Achatar a profundidade NÃO resolve: de frente o contorno da virilha continuava
    # aparecendo (apagar faces aqui abre furos na calça). Achatar deixava o contorno no sombreado; apagar faces abria furos;
    # remendar não apagava a forma (o alisamento só age em milímetros). O que funciona: a faixa do meio abaixo da barra
    # sai com CORTES RETOS (bisect em x = ±0,045 e z = 0,875): as pernas saem separadas por baixo do paletó, com a
    # borda limpa
    for plano_co, plano_no in (((0.045, 0, 0), (1, 0, 0)), ((-0.045, 0, 0), (1, 0, 0)), ((0, 0, 0.875), (0, 0, 1))):
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=plano_co, plane_no=plano_no)
    meio = [f for f in bm.faces if abs(f.calc_center_median().x) < 0.045 and f.calc_center_median().z < 0.875]
    bmesh.ops.delete(bm, geom=meio, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    alisa(bm, 25)
    # as costas saem: da frente nunca se veem, e por uma abertura (o V, a cava) elas apareceriam no lugar errado
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.004
    bm.normal_update()
    corta_costas(bm)
    # o que sobrou do pulso e da mão (apagado face a face, borda serrilhada) virava lasca azul ao lado do punho, na barra
    # do paletó. Corte reto em x = ±0,19 abaixo de 0,95, como ÚLTIMO passo da forma
    for sx in (-1, 1):
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(sx * 0.19, 0, 0), plane_no=(1, 0, 0))
    lado = [f for f in bm.faces if abs(f.calc_center_median().x) > 0.19 and f.calc_center_median().z < 0.95]
    bmesh.ops.delete(bm, geom=lado, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()
    uv_frente(bm)
    fecha_malha(ob, bm, TEX_CAMISA)
    return ob


def faz_paleto(arquivo):
    """paletó: o tronco cai reto (casco convexo por fatia), ombro estruturado, manga em tubo folgado, V recortado e
    lapela em relevo; tudo 1,2–1,4 cm para fora da pele"""
    ob = importa_pele_inteira(arquivo, "paleto")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    corta_faixa(bm, HEM, 1.465)
    cm = pertenca(bm)
    # a manga termina no pulso (0,865), mesmo com a barra mais baixa: corte reto e o que fica fora do tronco sai
    geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(0, 0, HEM), plane_no=(0, 0, 1))
    abaixo = [f for f in bm.faces if f.calc_center_median().z < HEM and abs(f.calc_center_median().x) > 0.205]
    bmesh.ops.delete(bm, geom=abaixo, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.verts.ensure_lookup_table()
    braco = lambda v: v[cm] in (1, 2)

    def corte_lateral():
        for sx in (-1, 1):
            geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
            bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(sx * 0.205, 0, 0), plane_no=(1, 0, 0))
        fora = [f for f in bm.faces if f.calc_center_median().z < 1.0 and abs(f.calc_center_median().x) > 0.205
                and sum(1 for v in f.verts if braco(v)) * 2 < len(f.verts)]
        bmesh.ops.delete(bm, geom=fora, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # o que sobra do tronco ao lado do pulso sai ANTES do casco: senão a fatia de baixo inclui esses vértices, o casco
    # vai até o pulso e o quadril abre em abas na direção do punho (lascas largas na barra)
    corte_lateral()
    # 1) o tronco cai reto: cada fatia de 1 cm vai até o casco convexo dela
    fatias = {}
    for v in bm.verts:
        if not braco(v):
            fatias.setdefault(int(v.co.z * 100), []).append(v)
    for vs in fatias.values():
        casco = casco_convexo([(round(v.co.x, 5), round(v.co.y, 5)) for v in vs])
        if len(casco) < 3:
            continue
        c = sum((Vector(p_) for p_ in casco), Vector((0, 0))) / len(casco)
        for v in vs:
            d = Vector((v.co.x, v.co.y)) - c
            if d.length < 1e-6:
                continue
            r = raio_casco(casco, c, math.atan2(d.y, d.x))
            if r > d.length:
                novo = c + d.normalized() * r
                v.co.x, v.co.y = novo.x, novo.y
    # 2) manga em tubo: ninguém fica mais perto do eixo que o raio da manga (afina do ombro ao punho)
    for v in bm.verts:
        if braco(v):
            lado = "R" if v[cm] == 1 else "L"
            _, q, t = ponto_eixo(v.co, lado)
            r_min = 0.050 + (0.044 - 0.050) * t                              # folga sem estufar o ombro
            d = v.co - q
            if 1e-6 < d.length < r_min:
                v.co = q + d.normalized() * r_min
    # 3) ombro de alfaiataria: em cima, nada passa da reta que desce do pescoço até a ponta do ombro (o deltoide
    #    arredondava o ombro e ele parecia estufado)
    bm.normal_update()
    for v in bm.verts:
        ax = abs(v.co.x)
        if 0.06 < ax < 0.26 and v.co.z > 1.33 and v.normal.z > 0.15:
            teto = 1.462 - (ax - 0.06) * 0.30
            if v.co.z > teto:
                v.co.z = teto
    # a lateral do tronco perto da barra não passa da costura (o casco puxava uma "cauda" para o lado do antebraço,
    # que aparecia na barra quando o braço subia)
    # (prender os vértices em x = ±0,205 esmagava faces e a quina da barra ficava esfiapada: corte reto no lugar)
    corte_lateral()
    alisa(bm, 18)
    for v in bm.verts:
        v.co += v.normal * (0.006 if braco(v) else 0.014)
    bm.normal_update()
    # a barra e o punho são cortados DE NOVO depois de alisar e afastar do corpo: alisar e deslocar pela normal entortam
    # a borda da malha, e as faces dobradas viravam lascas na barra e no punho. Regra: o corte reto é
    # sempre o ÚLTIMO passo da forma
    geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
    # (na MESMA altura do 1º corte: 6 mm acima abriu uma fresta entre o punho e a mão)
    bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=(0, 0, HEM), plane_no=(0, 0, 1))
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().z < HEM], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.normal_update()
    # 4) o V: primeiro a malha é cortada exatamente nas duas retas do V (borda limpa, sem serrilhado), depois a frente
    #    entre as lapelas sai (a camisa aparece por ele)
    for sx in (-1, 1):
        a_, b_ = Vector((0.0, 0.0, 1.175)), Vector((sx * 0.058, 0.0, 1.47))
        d_ = b_ - a_
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=a_, plane_no=Vector((d_.z, 0.0, -d_.x)).normalized())
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    v_fora = [f for f in bm.faces if f.normal.y < -0.2 and abs(f.calc_center_median().x) < v_meia(f.calc_center_median().z)
              and f.calc_center_median().z < 1.48 and f.calc_center_median().y < 0]
    bmesh.ops.delete(bm, geom=v_fora, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    # 5) lapela em relevo (a faixa entre o V e a borda da lapela vem 3 mm para frente)
    bm.normal_update()
    for v in bm.verts:
        if v.normal.y < -0.2 and v_meia(v.co.z) <= abs(v.co.x) < lapela_fora(v.co.z):
            v.co.y -= 0.003
    bm.normal_update()
    # as costas do tronco saem (pelo V e pela cava apareceria o avesso das costas, pintado com a cor errada)
    # (só a faixa do meio, atrás do V: cortar o ombro no meio da profundidade deixava pontas na altura da axila)
    corta_costas(bm, so=lambda f: all(v[cm] not in (1, 2) for v in f.verts) and abs(f.calc_center_median().x) < 0.12)
    uv_frente(bm)
    fecha_malha(ob, bm, TEX_PALETO)
    ob.data.materials.append(mat("manga", TEX_MANGA))
    # manga = material 1 (a textura com o punho). Marcado DEPOIS dos materiais: materials.clear() zera o índice de
    # todas as faces (o punho sumia)
    vals = [d.value for d in ob.data.attributes["mem"].data]
    for pol in ob.data.polygons:
        pol.material_index = 1 if any(vals[i] in (1, 2) for i in pol.vertices) else 0
    grupos_pertenca(ob)
    return ob


def gola_anel(pecas):
    """a gola da camisa: um anel em volta do pescoço, aberto na frente (onde fica o nó da gravata)"""
    pts = [o.matrix_world @ v.co for o in pecas for v in o.data.vertices]
    faixa = [p for p in pts if 1.47 < p.z < 1.49]                     # o pescoço mesmo (mais baixo ele já abre no ombro)
    cx = (max(p.x for p in faixa) + min(p.x for p in faixa)) / 2
    cy = (max(p.y for p in faixa) + min(p.y for p in faixa)) / 2
    rx = (max(p.x for p in faixa) - min(p.x for p in faixa)) / 2 + 0.007
    ry = (max(p.y for p in faixa) - min(p.y for p in faixa)) / 2 + 0.007
    bm = bmesh.new()
    n, aneis = 72, [(1.430, 1.0), (1.452, 0.99), (1.472, 0.975)]
    for z, k in aneis:
        for i in range(n):
            a = 2 * math.pi * i / n
            bm.verts.new((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a), z))
    bm.verts.ensure_lookup_table()
    frente = lambda i: abs(math.degrees(2 * math.pi * i / n) - 270) < 10       # o ângulo de 270° aponta para -Y
    for r in range(len(aneis) - 1):
        for i in range(n):
            j = (i + 1) % n
            if frente(i) and frente(j):
                continue
            bm.faces.new([bm.verts[r * n + i], bm.verts[r * n + j], bm.verts[(r + 1) * n + j], bm.verts[(r + 1) * n + i]])
    uv_frente(bm)
    me = bpy.data.meshes.new("gola")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("gola", me)
    cena.collection.objects.link(ob)
    me.uv_layers.active = me.uv_layers["frente"]
    me.materials.append(mat("gola", TEX_CAMISA))
    return ob


camisa = faz_camisa(Path(args[3]))
paleto = faz_paleto(Path(args[3]))
gola = gola_anel(grupos["pescoco"])

# ------------------------------------------------------------------ rosto: olhos, sobrancelhas e cabelo
visivel = grupos["cabeca"] + grupos["pescoco"] + grupos["mao"]
for o in visivel:
    n = o.name.split("__", 1)[1]
    o.name = "pelev__" + n
    o.data.materials.clear()
    o.data.materials.append(mat("sobrancelha" if n.startswith("Eyebrow") else "pele"))
for o in pele:
    if o not in visivel:
        bpy.data.objects.remove(o)
# a pele do pescoço abaixo da borda de cima da gola sai (ela descia até a clavícula e furava a camisa no V)
for o in grupos["pescoco"]:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    mw = o.matrix_world
    fora = [f for f in bm.faces if all((mw @ v.co).z < 1.468 for v in f.verts)]
    bmesh.ops.delete(bm, geom=fora, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()


def esfera(nome, centro_, r, cor):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    cena.collection.objects.link(ob)
    ob.location = centro_
    me.materials.append(mat(cor))
    return ob


def disco(nome, centro_, r, cor):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=32, radius=r)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    cena.collection.objects.link(ob)
    ob.location = centro_
    ob.rotation_euler = (math.radians(90), 0, 0)                       # de frente para a câmera (-Y)
    me.materials.append(mat(cor))
    return ob


cabeca_pts = [o.matrix_world @ v.co for o in grupos["cabeca"] for v in o.data.vertices]
olhos = []
for nome, x in (("olho__R", -0.0275), ("olho__L", 0.032)):
    perto = [p for p in cabeca_pts if abs(p.x - x) < 0.022 and abs(p.z - 1.5925) < 0.014]
    y_palp = min(p.y for p in perto)                                   # a frente da pálpebra
    c = Vector((x, y_palp + 0.0125, 1.5925))
    olhos.append(esfera(nome, c, 0.0118, "esclera"))
    olhos.append(disco(nome + "_iris", (x, c.y - 0.0118 + 0.0004, 1.5918), 0.0068, "iris"))
    olhos.append(disco(nome + "_pupila", (x, c.y - 0.0118 - 0.0001, 1.5918), 0.0028, "pupila"))


def faz_cabelo():
    """cabelo curto: as peças do couro cabeludo acima da linha do cabelo, 4 mm para fora"""
    escalpo = [o for o in grupos["cabeca"] if re.search(r"(Frontal|Parietal|Temporal|Occipital|Mastoid) region",
                                                       o.name)]
    copias = []
    for o in escalpo:
        c = o.copy()
        c.data = o.data.copy()
        cena.collection.objects.link(c)
        copias.append(c)
    bpy.ops.object.select_all(action="DESELECT")
    for c in copias:
        c.select_set(True)
    bpy.context.view_layer.objects.active = copias[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = "cabelo"
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.002)

    def linha(v):                                                      # altura da linha do cabelo em volta da cabeça
        ang = abs(math.degrees(math.atan2(v.co.x, -(v.co.y + 0.005))))  # 0 = frente, 180 = nuca
        pontos = [(0, 1.664), (35, 1.650), (60, 1.628), (90, 1.606), (125, 1.585), (180, 1.548)]
        for (a0, z0), (a1, z1) in zip(pontos, pontos[1:]):
            if a0 <= ang <= a1:
                return z0 + (z1 - z0) * (ang - a0) / (a1 - a0)
        return 1.548
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(v.co.z < linha(v) for v in f.verts)], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.004
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.clear()
    ob.data.materials.append(mat("cabelo"))
    return ob


cabelo = faz_cabelo()


# ------------------------------------------------------------------ chapéu (fedora do tamanho da cabeça)
def chapeu_peca(nome, r, h, z, sy, afina=1.0, cor="feltro", seg=64, amassa=0.0, aba_cai=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=True, segments=seg, radius1=r, radius2=r * afina, depth=h)
    for v in bm.verts:
        v.co.y *= sy
        if amassa and abs(v.co.x) < 1e-6 and abs(v.co.y) < 1e-6 and v.co.z > 0:
            v.co.z -= amassa                                               # o vinco do alto da copa
        if aba_cai and v.co.y < 0:
            v.co.z -= aba_cai * (-v.co.y / (r * sy))                       # a aba desce na frente
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    cena.collection.objects.link(ob)
    ob.location = (0.0, -0.006, z + h / 2)
    me.materials.append(mat(cor))
    return ob


chapeu = [chapeu_peca("chapeu__copa", 0.0875, 0.102, 1.652, 1.16, afina=0.86, amassa=0.016),
          chapeu_peca("chapeu__aba", 0.148, 0.006, 1.650, 1.12, aba_cai=0.010),
          chapeu_peca("chapeu__fita", 0.0890, 0.024, 1.655, 1.16, cor="fita")]
inclina = Matrix.Translation((0, 0, 1.66)) @ Matrix.Rotation(math.radians(-5), 4, "X") @ \
    Matrix.Rotation(math.radians(3), 4, "Y") @ Matrix.Translation((0, 0, -1.66))
bpy.context.view_layer.update()
for o in chapeu:
    o.matrix_world = inclina @ o.matrix_world
bpy.context.view_layer.update()
for o in chapeu:
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ------------------------------------------------------------------ peças 2D do paletó (boneco de papel)
def plano_cotovelo(lado):
    S, E, W = J[f"S_{lado}"], J[f"E_{lado}"], J[f"W_{lado}"]
    return E, (W - S).normalized()


def separa_cotovelo(ob):
    """boneco de papel de uma junta só: o paletó é cortado RETO no plano do cotovelo (bisect) e vira duas peças: o
    corpo (tronco e braço até o cotovelo, parado) e o antebraço de cada lado (gira no cotovelo, por cima do corpo).
    O ombro não gira: girar o braço inteiro mostrava a axila e o corte serrilhado da manga"""
    c = ob.copy()
    c.data = ob.data.copy()
    cena.collection.objects.link(c)
    bm = bmesh.new()
    bm.from_mesh(c.data)
    cm = bm.verts.layers.int.get("mem")
    for lado in ("R", "L"):
        E, n = plano_cotovelo(lado)
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geo, dist=1e-6, plane_co=E, plane_no=n)
    bm.normal_update()
    partes = {"p2_corpo": [], "p2_antebraco.R": [], "p2_antebraco.L": [], "p2_mangas": []}
    for f in bm.faces:
        ms = [v[cm] for v in f.verts]
        m = max(set(ms), key=ms.count)
        c_ = f.calc_center_median()
        if m in (1, 2):
            partes["p2_mangas"].append(f.index)
            lado = "R" if m == 1 else "L"
            E, n = plano_cotovelo(lado)
            if (c_ - E).dot(n) > 0:
                partes[f"p2_antebraco.{lado}"].append(f.index)
                continue
        partes["p2_corpo"].append(f.index)
    bm.to_mesh(c.data)
    bm.free()
    feitos = []
    for nome, idx in partes.items():
        d = c.copy()
        d.data = c.data.copy()
        d.name = nome
        cena.collection.objects.link(d)
        bm = bmesh.new()
        bm.from_mesh(d.data)
        bm.faces.ensure_lookup_table()
        manter = set(idx)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in manter], context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(d.data)
        bm.free()
        for vg in list(d.vertex_groups):
            d.vertex_groups.remove(vg)
        feitos.append(d)
    bpy.data.objects.remove(c)
    return feitos


pecas2d = separa_cotovelo(paleto)


def junta(nome, c, r):
    """esfera com o tecido do paletó no cotovelo: arredonda a ponta do antebraço (como o rebite do boneco)"""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
    for v in bm.verts:
        v.co += c
    uv_frente(bm)
    me = bpy.data.meshes.new(nome)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nome, me)
    cena.collection.objects.link(ob)
    me.uv_layers.active = me.uv_layers["frente"]
    me.materials.append(mat("manga", TEX_MANGA))
    return ob


for lado in ("R", "L"):
    junta(f"p2_junta_cotovelo.{lado}", J[f"E_{lado}"] + Vector((0, -0.004, 0)), 0.046)

# ------------------------------------------------------------------ esqueleto de animação (versão 3D)
arm_dados = bpy.data.armatures.new("rig")
rig = bpy.data.objects.new("rig", arm_dados)
cena.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
eb = arm_dados.edit_bones
tr = eb.new("tronco"); tr.head, tr.tail = (0, 0.03, 0.95), (0, 0.03, 1.45)
cb = eb.new("cabeca"); cb.head, cb.tail = (0, 0.02, 1.50), (0, 0.02, 1.66); cb.parent = tr
for s_ in ("R", "L"):
    b = eb.new(f"braco.{s_}"); b.head, b.tail = J[f"S_{s_}"], J[f"E_{s_}"]; b.parent = tr
    a = eb.new(f"antebraco.{s_}"); a.head, a.tail = J[f"E_{s_}"], J[f"W_{s_}"]; a.parent = b
    m = eb.new(f"mao.{s_}"); m.head, m.tail = J[f"W_{s_}"], J[f"F_{s_}"]; m.parent = a
bpy.ops.object.mode_set(mode="OBJECT")


def pesa(ob, func):
    """func(v_co, grupos_do_vertice) -> {osso: peso}"""
    nomes = {g.index: g.name for g in ob.vertex_groups}
    alvos = {}
    for v in ob.data.vertices:
        mem = {nomes[g.group]: g.weight for g in v.groups if g.group in nomes}
        for osso, w in func(v.co, mem).items():
            if w > 1e-4:
                alvos.setdefault(osso, []).append((v.index, w))
    for osso, lst in alvos.items():
        vg = ob.vertex_groups.get(osso) or ob.vertex_groups.new(name=osso)
        for i, w in lst:
            vg.add([i], w, "REPLACE")
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = rig


def pesos_paleto(co, mem):
    for s_ in ("R", "L"):
        S, E, W = J[f"S_{s_}"], J[f"E_{s_}"], J[f"W_{s_}"]
        du = (E - S).normalized()
        dm = (W - S).normalized()
        f = suave(-0.03, 0.03, (co - E).dot(dm))
        if mem.get(f"mem_{s_}", 0) > 0.5:
            a = suave(-0.045, 0.025, (co - S).dot(du))
            return {"tronco": 1 - a, f"braco.{s_}": a * (1 - f), f"antebraco.{s_}": a * f}
        if mem.get(f"ombro_{s_}", 0) > 0.5:
            # só a CABEÇA do ombro (acima da axila) acompanha o braço; a lateral do tronco fica parada (com peso ali o
            # paletó era arrastado para cima no tchau)
            a = suave(-0.02, 0.06, (co - S).dot(du)) * suave(0.13, 0.19, abs(co.x)) * suave(S.z - 0.09, S.z - 0.02, co.z)
            return {"tronco": 1 - a, f"braco.{s_}": a}
    return {"tronco": 1.0}


pesa(paleto, pesos_paleto)
bpy.context.view_layer.objects.active = paleto
bpy.ops.object.mode_set(mode="WEIGHT_PAINT")
bpy.ops.object.vertex_group_smooth(group_select_mode="ALL", factor=0.5, repeat=6)
bpy.ops.object.vertex_group_normalize_all(lock_active=False)
bpy.ops.object.mode_set(mode="OBJECT")
for o in (camisa, gola):
    pesa(o, lambda co, mem: {"tronco": 1.0})
for o in grupos["mao"]:
    pesa(o, lambda co, mem, lado=("R" if o.name.endswith(".r") else "L"): {f"antebraco.{lado}": 1.0})
for o in grupos["cabeca"] + chapeu + olhos + [cabelo]:
    pesa(o, lambda co, mem: {"cabeca": 1.0})
for o in grupos["pescoco"]:
    pesa(o, lambda co, mem: {"cabeca": suave(1.47, 1.56, co.z), "tronco": 1 - suave(1.47, 1.56, co.z)})


# ------------------------------------------------------------------ ações
def gira_mundo(pb, eixo, graus):
    """rotação em torno de um eixo do MUNDO, passada para o espaço do osso"""
    M_ = pb.bone.matrix_local.to_3x3()
    R = Matrix.Rotation(math.radians(graus), 3, eixo)
    return (M_.inverted() @ R @ M_).to_quaternion()


def pose(f, thR=0.0, phR=0.0, thL=0.0, phL=0.0, incl=0.0, vira=0.0):
    pbs = rig.pose.bones
    for pb in pbs:
        pb.rotation_mode = "QUATERNION"
    pbs["braco.R"].rotation_quaternion = gira_mundo(pbs["braco.R"], "Y", thR)
    pbs["antebraco.R"].rotation_quaternion = gira_mundo(pbs["antebraco.R"], "Y", phR)
    pbs["braco.L"].rotation_quaternion = gira_mundo(pbs["braco.L"], "Y", -thL)
    pbs["antebraco.L"].rotation_quaternion = gira_mundo(pbs["antebraco.L"], "Y", -phL)
    pbs["cabeca"].rotation_quaternion = gira_mundo(pbs["cabeca"], "Z", vira) @ gira_mundo(pbs["cabeca"], "Y", incl)
    for pb in pbs:
        pb.keyframe_insert("rotation_quaternion", frame=f)


TCHAU = (30.0, 120.0, 14.0)   # braço, antebraço (relativo), aceno ±. Braço a 30°: a 45° o ombro do paletó subia numa dobra
io = lambda t: t * t * (3 - 2 * t)


def tchau(k):
    """o tchau em 24 desenhos (7 qps): sobe (o antebraço dobra antes), acena duas vezes, desce"""
    th_, ph_, ac = TCHAU
    if k <= 5:
        t = io(k / 5)
        return th_ * t, ph_ * io(min(1.0, k / 3.0)), -3 * t
    if k <= 17:
        a = 2 * math.pi * (k - 6) / 6
        return th_ + 2 * math.sin(a), ph_ + ac * math.sin(a), -3.0
    t = io((k - 18) / 5)
    return th_ * (1 - t), ph_ * (1 - io(max(0.0, (k - 19) / 4.0))), -3 * (1 - t)


def respiro(i):
    a = 2 * math.pi * i / 28
    return (2.0 * math.sin(a), 1.6 * math.sin(a + 0.8), 1.8 * math.sin(a + 1.3), 1.4 * math.sin(a + 2.0),
            1.0 * math.sin(a + 0.5), 1.2 * math.sin(a + 2.0))


pose(0)
for i in range(28):
    thR, phR, thL, phL, inc, vir = respiro(i)
    pose(1 + i, thR=thR, phR=phR, thL=thL, phL=phL, incl=inc, vira=vir)
for k in range(24):
    th, ph, inc = tchau(k)
    pose(101 + k, thR=th, phR=ph, incl=inc, vira=2.5 * math.sin(math.pi * min(k, 18) / 18))
cena.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(saida), compress=True)
print("ok", saida, sorted({o.name for o in bpy.data.objects if not o.name.startswith(("musc", "osso", "org", "pul", "cor",
                                                                                    "pelev"))}))
