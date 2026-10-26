"""Renderiza vistas de um modelo 3D para a colagem (camadas registradas + giro a 7 qps).

    "$BLENDER" --background --factory-startup --python blender_giro.py -- config.json
    (BLENDER = o executável do Blender 4.x/5.x; no macOS, /Applications/Blender.app/Contents/MacOS/Blender)

config.json:
    {"modelo": "arquivo.glb|.gltf|.obj|.fbx|.stl|.blend" ou null (teste com formas primitivas),
     "saida": "pasta",
     "vistas": 36,                       # ângulos em volta do eixo (0..360)
     "res": [1200, 1400],
     "camadas": {"pele": ["regex", ...], "ossos": ["regex"]},   # nomes de objetos/coleções por camada; null = tudo
     "eixo": "Z", "elevacao": 6,         # graus da câmera acima do horizonte
     "lente": 70,                        # mm (perspectiva); 0 = ortográfica
     "motor": "WORKBENCH" | "EEVEE",
     "cores": {"pele": [0.86, 0.72, 0.62], "ossos": [0.92, 0.88, 0.78]},
     "giro_inicial": 0,
     "enquadrar": ["coracao"],           # opcional: camadas que definem o enquadramento e o pivô do giro (padrão: tudo)
     "ajuste": "caixa",                  # opcional, só ortográfica: encaixa a caixa X/Z (vista de frente) em vez da esfera
     "caixa_mundo": [x0, z0, x1, z1],    # opcional, com ajuste "caixa": o recorte do mundo a enquadrar (ex.: só o busto)
     "marcos": {"apice": [x, y, z]},     # opcional: pontos do mundo -> px na vista 0 (vão para vistas.json)
     "quadros": [1, 2, 3],               # opcional: quadros da animação (personagem com esqueleto) em vez de vistas
     "cor_tipo_camada": {"ext": "TEXTURE"}}   # opcional: tipo de cor do passe "cor" por camada
Saída: <saida>/<camada>/v_000.png ... (fundo transparente), e <saida>/vistas.json.
Todas as camadas usam a MESMA câmera e o MESMO enquadramento (a caixa de todas juntas): encaixam pixel a pixel."""
import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
cfg = json.loads(Path(args[0]).read_text())
saida = Path(cfg["saida"])
saida.mkdir(parents=True, exist_ok=True)

# cena limpa
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene

modelo = cfg.get("modelo")
if modelo:
    ext = Path(modelo).suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=modelo)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=modelo)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=modelo)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=modelo)
    elif ext == ".blend":
        with bpy.data.libraries.load(modelo, link=False) as (dados_de, dados_para):
            dados_para.objects = list(dados_de.objects)
        for ob in dados_para.objects:
            if ob is not None and ob.type in ("MESH", "EMPTY", "CURVE"):
                cena.collection.objects.link(ob)
    else:
        raise SystemExit(f"formato não suportado: {ext}")
else:                                              # teste: uma "pele" (esfera) com um "osso" dentro
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0), segments=64, ring_count=32)
    bpy.context.object.name = "pele_teste"
    bpy.ops.mesh.primitive_torus_add(major_radius=0.55, minor_radius=0.18, location=(0, 0, 0), rotation=(1.2, 0.3, 0))
    bpy.context.object.name = "osso_teste"
    bpy.ops.mesh.primitive_monkey_add(size=0.7, location=(0, 0, 0))
    bpy.context.object.name = "osso_macaco"

bpy.context.view_layer.update()                    # sem isto, matrix_world vem velha (caixa e pivô errados)
malhas = [o for o in cena.objects if o.type == "MESH"]
if not malhas:
    raise SystemExit("nenhuma malha importada")

# camadas: nome -> objetos
camadas_cfg = cfg.get("camadas") or {"tudo": [".*"]}
camadas = {}
for nome, padroes in camadas_cfg.items():
    rx = [re.compile(p, re.I) for p in padroes]
    sel = []
    for o in malhas:
        nomes = [o.name] + [c.name for c in o.users_collection]
        if any(r.search(n) for r in rx for n in nomes):
            sel.append(o)
    camadas[nome] = sel
    print(f"camada {nome}: {len(sel)} objetos")

# raiz que gira: um vazio no centro da caixa de tudo (ou só das camadas de 'enquadrar')
enq = cfg.get("enquadrar")
base_enq = [o for nome in enq for o in camadas[nome]] if enq else malhas
pts = [o.matrix_world @ Vector(c) for o in base_enq for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centro = (mn + mx) / 2
raio = max((p - centro).length for p in pts)
bpy.ops.object.empty_add(location=centro)
raiz = bpy.context.object
repouso = raiz.matrix_world.copy()
for o in malhas:
    if o.parent is None:
        mw = o.matrix_world.copy()
        o.parent = raiz
        o.matrix_world = mw
# objetos pais que não são malha (vazios do glTF) também vão para a raiz
for o in list(cena.objects):
    if o is not raiz and o.parent is None and o.type != "CAMERA":
        mw = o.matrix_world.copy()
        o.parent = raiz
        o.matrix_world = mw

# cores por camada (material simples) quando pedido
cores = cfg.get("cores") or {}
for nome, objs in camadas.items():
    if nome in cores:
        mat = bpy.data.materials.new(f"cor_{nome}")
        mat.diffuse_color = (*cores[nome], 1.0)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*cores[nome], 1.0)
            bsdf.inputs["Roughness"].default_value = 0.7
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(mat)
            o.color = (*cores[nome], 1.0)

# câmera: enquadra a caixa inteira (todas as camadas) com folga
eixo = cfg.get("eixo", "Z").upper()
elev = math.radians(cfg.get("elevacao", 6))
lente = cfg.get("lente", 70)
res = cfg.get("res", [1200, 1400])
cena.render.resolution_x, cena.render.resolution_y = res
cena.render.film_transparent = True
cam_dados = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_dados)
cena.collection.objects.link(cam)
cena.camera = cam
aspecto = res[0] / res[1]
if lente and lente > 0:
    cam_dados.lens = lente
    cam_dados.sensor_fit = "VERTICAL" if aspecto < 1 else "HORIZONTAL"
    fov = 2 * math.atan(cam_dados.sensor_height / 2 / lente) if aspecto < 1 else 2 * math.atan(cam_dados.sensor_width / 2 / lente)
    fov_menor = fov * (aspecto if aspecto < 1 else 1 / aspecto) if False else fov
    dist = raio * 1.08 / math.sin(min(fov, fov * (aspecto if aspecto < 1 else 1)) / 2)
else:
    cam_dados.type = "ORTHO"
    cam_dados.sensor_fit = "VERTICAL" if aspecto < 1 else "HORIZONTAL"
    if cfg.get("ajuste") == "caixa":                     # vista de frente: a caixa X/Z com 4% de folga
        if cfg.get("caixa_mundo"):
            x0, z0, x1, z1 = cfg["caixa_mundo"]
            mn, mx = Vector((x0, mn.y, z0)), Vector((x1, mx.y, z1))
            centro = (mn + mx) / 2
        larg, alt = (mx.x - mn.x) * 1.04, (mx.z - mn.z) * 1.04
        cam_dados.ortho_scale = max(alt, larg / aspecto) if aspecto < 1 else max(larg, alt * aspecto)
    else:
        cam_dados.ortho_scale = raio * 2.15 * (1 if aspecto < 1 else aspecto)
    dist = raio * 4
if eixo == "Z":
    cam.location = centro + Vector((0, -dist * math.cos(elev), dist * math.sin(elev)))
else:                                              # eixo Y para cima (glTF já vem convertido para Z, normalmente)
    cam.location = centro + Vector((0, -dist * math.cos(elev), dist * math.sin(elev)))
direcao = centro - cam.location
cam.rotation_euler = direcao.to_track_quat("-Z", "Y").to_euler()
cam_dados.clip_start = max(0.001, dist - raio * 2)
cam_dados.clip_end = dist + raio * 3

# luz e motor
motor = cfg.get("motor", "WORKBENCH").upper()
if motor == "WORKBENCH":
    cena.render.engine = "BLENDER_WORKBENCH"
    sh = cena.display.shading
    sh.light = "STUDIO"
    sh.color_type = cfg.get("cor_tipo", "MATERIAL")          # "VERTEX" para modelos com cor por vértice
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_shadows = True
    sh.shadow_intensity = 0.35
    sh.show_specular_highlight = True
else:
    try:
        cena.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        cena.render.engine = "BLENDER_EEVEE"
    mundo = bpy.data.worlds.new("mundo")
    cena.world = mundo
    mundo.use_nodes = True
    mundo.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    for nome, en, rot in (("chave", 4.0, (math.radians(50), 0, math.radians(35))),
                          ("preenche", 1.2, (math.radians(60), 0, math.radians(-60))),
                          ("recorte", 2.5, (math.radians(120), 0, math.radians(180)))):
        ld = bpy.data.lights.new(nome, "SUN")
        ld.energy = en
        lo = bpy.data.objects.new(nome, ld)
        lo.rotation_euler = rot
        cena.collection.objects.link(lo)
cena.view_settings.view_transform = "Standard"     # cor fiel (o AgX padrão desbota o passe de cor)
cena.render.image_settings.file_format = "PNG"
cena.render.image_settings.color_mode = "RGBA"

# render: cada ângulo, cada camada (só a camada visível)
n = int(cfg.get("vistas", 36))
giro0 = math.radians(cfg.get("giro_inicial", 0))
info = {"vistas": n, "res": res, "camadas": list(camadas), "centro": list(centro), "raio": raio}
if cam_dados.type == "ORTHO":                            # px por metro (vale para todas as vistas)
    info["px_por_m"] = (res[1] if aspecto < 1 else res[0]) / cam_dados.ortho_scale
if cfg.get("marcos"):                                    # onde cada ponto do mundo cai na vista 0, em px
    from bpy_extras.object_utils import world_to_camera_view
    raiz.rotation_euler = (0, 0, giro0)
    bpy.context.view_layer.update()
    info["marcos"] = {}
    for nome_m, pt in cfg["marcos"].items():
        v = world_to_camera_view(cena, cam, raiz.matrix_world @ repouso.inverted() @ Vector(pt))
        info["marcos"][nome_m] = [v.x * res[0], (1 - v.y) * res[1]]
# passes (só Workbench): "cor" = cor chapada sem sombra (vira a aquarela) e "luz" = sombra em branco (vira o pontilhado)
passes = cfg.get("passes") if motor == "WORKBENCH" else None
sh = cena.display.shading


def ajusta_passe(passe, camada=None):
    if passe == "cor":
        sh.light = "FLAT"
        sh.color_type = (cfg.get("cor_tipo_camada") or {}).get(camada, cfg.get("cor_tipo", "MATERIAL"))
        sh.show_cavity = False
        sh.show_shadows = False
        sh.show_specular_highlight = False
    elif passe == "luz":
        sh.light = "STUDIO"
        sh.color_type = "SINGLE"
        sh.single_color = (0.9, 0.9, 0.9)
        sh.show_cavity = True
        sh.show_shadows = True
        sh.show_specular_highlight = False


quadros = cfg.get("quadros")
tomadas = [(f, "q", f) for f in quadros] if quadros else [(None, "v", i) for i in range(n)]
for quadro, letra, i in tomadas:
    if quadro is not None:
        cena.frame_set(quadro)
    else:
        raiz.rotation_euler = (0, 0, giro0 + 2 * math.pi * i / n)
    for nome, objs in camadas.items():
        for o in malhas:
            o.hide_render = o not in objs
        pasta = saida / nome
        pasta.mkdir(exist_ok=True)
        for passe in (passes or [None]):
            if passe:
                ajusta_passe(passe, nome)
            cena.render.filepath = str(pasta / (f"{passe}_{letra}_{i:03d}.png" if passe else f"{letra}_{i:03d}.png"))
            bpy.ops.render.render(write_still=True)
    print(f"{'quadro' if quadro is not None else 'vista'} {i}")
(saida / "vistas.json").write_text(json.dumps(info, indent=1))
print("ok")
