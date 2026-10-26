"""O bloco do pré-sal em corte (modelo próprio, unidade = 1 km): mar, pós-sal em 3 faixas, sal, rocha do pré-sal com o
óleo na crista e o embasamento. Cada camada é um SÓLIDO entre duas superfícies (topo e base), com as paredes do corte
subdivididas para a cor por vértice (gradiente da água, grão das rochas, cristais do sal) aparecer na frente do bloco.
Espessuras (esquemáticas, coerentes com as descrições públicas do pré-sal): lâmina d'água ~2 km, pós-sal ~1 km, sal ~2 km, reservatório a
~5–6 km abaixo do nível do mar.

    "$BLENDER" --background --factory-startup --python presal_blender.py -- <saida.blend>"""
import math
import sys

import bmesh
import bpy
from mathutils import noise, Vector

saida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
X0, X1, Y0, Y1 = -2.4, 2.4, -1.0, 1.0


def ruido(x, y, z=0.0, esc=1.0):
    return noise.noise(Vector((x * esc, y * esc, z * esc)))


def z_fundo(x, y):                                     # o fundo do mar (topo do pós-sal)
    return -2.0 + 0.06 * math.sin(1.3 * x + 0.4) + 0.04 * ruido(x, y, 0, 1.6)


def z_sal_topo(x, y):                                  # domos de sal empurrando o pós-sal
    return (-3.3 + 0.55 * math.exp(-((x - 0.9) / 0.7) ** 2) + 0.35 * math.exp(-((x + 1.6) / 0.5) ** 2)
            + 0.04 * ruido(x, y, 3, 1.2))


def z_sal_base(x, y):                                  # a crista do reservatório (anticlinal) sob o sal
    return -5.4 + 0.6 * math.exp(-(x / 1.3) ** 2) + 0.03 * ruido(x, y, 7, 1.0)


def z_res_base(x, y):
    return -6.2 + 0.4 * math.exp(-(x / 1.5) ** 2)


Z_OLEO = -5.25                                         # contato óleo-água: acima dele, na crista, está o óleo


def faixa(f0, f1, a):
    return lambda x, y: f0(x, y) + (f1(x, y) - f0(x, y)) * a + 0.025 * ruido(x, y, 11 * a, 2.0)


def cor_agua(x, y, z):
    t = min(max(-z / 2.0, 0), 1)                       # 0 na superfície, 1 no fundo
    c0, c1 = (0.36, 0.66, 0.78), (0.05, 0.16, 0.30)
    return tuple(a + (b - a) * t ** 0.8 for a, b in zip(c0, c1))


def cor_grao(base, esc=9.0, forca=0.10, semente=0.0):
    def f(x, y, z):
        n = ruido(x + semente, y, z, esc) * 0.6 + ruido(x, y + semente, z, esc * 3.1) * 0.4
        return tuple(min(max(c * (1 + forca * n), 0), 1) for c in base)
    return f


def cor_sal(x, y, z):
    n = abs(ruido(x, y, z, 7.0))
    v = 0.86 + 0.12 * (1 - n)
    return (v, v * 0.985, v * 0.97)


def cor_res(x, y, z):                                  # carbonato bege com poros escuros
    n = ruido(x, y, z, 14.0)
    poro = 0.82 if n > 0.42 else 1.0
    b = (0.80, 0.69, 0.52)
    return tuple(c * poro * (1 + 0.06 * ruido(x, y, z, 5)) for c in b)


def cor_oleo(x, y, z):
    n = ruido(x, y, z, 10.0)
    return (0.10 + 0.04 * n, 0.07 + 0.03 * n, 0.05 + 0.02 * n)


def solido(nome, ftop, fbot, fcor, xr=(X0, X1), nx=200, ny=60, nz=48, empurra_frente=0.0):
    """sólido entre ftop e fbot sobre o retângulo xr × (Y0, Y1); paredes subdivididas; cor por vértice (fcor(x, y, z))"""
    me = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    xs = [xr[0] + (xr[1] - xr[0]) * i / nx for i in range(nx + 1)]
    ys = [Y0 + (Y1 - Y0) * j / ny for j in range(ny + 1)]
    yf = Y0 - empurra_frente
    cores = {}

    def v(x, y, z):
        vv = bm.verts.new((x, y, z))
        cores[vv] = fcor(x, y, z)
        return vv
    for f, para_cima in ((ftop, True), (fbot, False)):            # tampas de cima e de baixo
        g = [[v(x, y if y > Y0 else yf, f(x, y)) for x in xs] for y in ys]
        for j in range(ny):
            for i in range(nx):
                q = [g[j][i], g[j][i + 1], g[j + 1][i + 1], g[j + 1][i]]
                bm.faces.new(q if para_cima else q[::-1])
    # paredes: frente (y = Y0), fundo (Y1), esquerda (x0), direita (x1)
    def parede(pts, sentido):
        col = []
        for (x, y) in pts:
            zt, zb = ftop(x, y), fbot(x, y)
            col.append([v(x, y, zb + (zt - zb) * k / nz) for k in range(nz + 1)])
        for i in range(len(col) - 1):
            for k in range(nz):
                q = [col[i][k], col[i + 1][k], col[i + 1][k + 1], col[i][k + 1]]
                bm.faces.new(q if sentido else q[::-1])
    parede([(x, yf) for x in xs], True)
    parede([(x, Y1) for x in xs], False)
    parede([(xr[0], y if y > Y0 else yf) for y in ys], False)
    parede([(xr[1], y if y > Y0 else yf) for y in ys], True)
    bm.to_mesh(me)
    bm.free()
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for i, vv in enumerate(me.vertices):
        pass
    # cor por vértice: a ordem dos vértices do bmesh é a mesma da malha
    vs = list(cores.values())
    for i, c in enumerate(vs):
        lin = [cc / 12.92 if cc <= 0.04045 else ((cc + 0.055) / 1.055) ** 2.4 for cc in c]
        attr.data[i].color = (*lin, 1.0)
    me.color_attributes.active_color = attr
    ob = bpy.data.objects.new(nome, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


topo = lambda x, y: 0.0
solido("agua__mar", topo, z_fundo, cor_agua, nz=60)
p1 = faixa(z_sal_topo, z_fundo, 0.66)
p2 = faixa(z_sal_topo, z_fundo, 0.33)
solido("pos1__areia", z_fundo, p1, cor_grao((0.83, 0.66, 0.40), semente=1))
solido("pos2__folhelho", p1, p2, cor_grao((0.58, 0.41, 0.27), semente=2))
solido("pos3__marga", p2, z_sal_topo, cor_grao((0.55, 0.55, 0.45), semente=3))
solido("sal__sal", z_sal_topo, z_sal_base, cor_sal, nz=60)
solido("pre__reservatorio", z_sal_base, z_res_base, cor_res)
a = 1.3 * math.sqrt(-math.log((Z_OLEO + 5.4 + 0.03) / 0.6))   # onde a crista passa do contato óleo-água
solido("oleo__oleo", lambda x, y: z_sal_base(x, y) - 0.004, lambda x, y: min(max(Z_OLEO, z_sal_base(x, y) - 0.5), z_sal_base(x, y) - 0.012), cor_oleo,
       xr=(-a, a), nx=120, empurra_frente=0.004)
solido("emb__embasamento", z_res_base, lambda x, y: -7.0, cor_grao((0.42, 0.24, 0.20), esc=6, semente=4))
print("oleo x", -a, a)
bpy.ops.wm.save_as_mainfile(filepath=saida, compress=True)
print("ok", saida)
