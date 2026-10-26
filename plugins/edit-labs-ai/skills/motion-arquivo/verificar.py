#!/usr/bin/env python3
"""
Confere a instalacao e renderiza um quadro de cada tipo de plano num projeto sintetico
(assets de mentira gerados aqui: nenhum download, nenhum credito).

    mvpy verificar.py
"""
import importlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "motor"))
ok = True


def conf(nome, cond, dica=""):
    global ok
    print(("  ok   " if cond else "  FALTA ") + nome + ("" if cond else f"  -> {dica}"))
    ok &= bool(cond)


print("bibliotecas")
for m in ("numpy", "cv2", "PIL", "faster_whisper"):
    try:
        importlib.import_module(m); conf(m, True)
    except Exception:
        conf(m, False, "rode editlabs-setup (ou: mvpy -m pip install -r requirements.txt)")
print("programas")
conf("ffmpeg", shutil.which("ffmpeg"), "instale o ffmpeg")
conf("swift (cursor do sistema)", shutil.which("swift"), "xcode-select --install (opcional)")
print("fontes")
from familia_a import c2_letras as le  # noqa: E402
for f in ("InstrumentSerif-Italic.ttf", "InstrumentSerif-Regular.ttf", "Inter[opsz,wght].ttf",
          "OFL-InstrumentSerif.txt", "OFL-Inter.txt"):
    conf(f, (RAIZ / "motor" / "fontes" / f).exists(), "reinstale o plugin (fonte OFL e licença vêm juntas)")
conf(f"grotesca: {Path(le.GROTESCA).name}", le.GROTESCA != le.INTER, "sem Arial Bold: o gancho cai na Inter 800")
print("kit")
for k in ("moldura.png", "moldura_furo.npy", "papel_amassado.png"):
    conf(k, (RAIZ / "motor" / "kit" / k).exists())
import os  # noqa: E402
sfx = sorted((RAIZ / "motor" / "kit" / "sfx").glob("*.wav"))
conf(f"efeitos sintetizados ({len(sfx)})", len(sfx) >= 13, "rode: mvpy motor/som.py")
sons = os.environ.get("EDITLABS_SONS")
print("  info  pasta de sons do usuário: " + (sons if sons else "não definida (EDITLABS_SONS) — o mixador usa os sintetizados"))

print("render de um quadro de cada tipo (assets sinteticos)")
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import planos as PL, projeto  # noqa: E402
from familia_a.c4_filtro import acabamento  # noqa: E402
with tempfile.TemporaryDirectory() as d:
    d = Path(d); pr = d / "assets" / "prontos"; pr.mkdir(parents=True)
    rng = np.random.default_rng(1)

    def img(nome, w, h, cor, alfa=True):
        a = np.zeros((h, w, 4), np.uint8); a[..., :3] = cor; a[..., 3] = 255
        if alfa:
            a[: h // 8] = 0; a[-h // 8:] = 0; a[:, : w // 8] = 0; a[:, -w // 8:] = 0
        a[..., :3] = np.clip(a[..., :3] + rng.normal(0, 12, (h, w, 1)), 0, 255)
        Image.fromarray(a).save(pr / nome)
    img("foto.png", 1520, 2688, (120, 110, 100), alfa=False)
    img("obj.png", 841, 663, (230, 230, 232)); img("fig.png", 1344, 570, (40, 40, 44))
    img("doc.png", 2343, 3410, (220, 215, 205), alfa=False); img("lixeira.png", 1520, 2688, (40, 140, 60), alfa=False)
    img("icone.png", 1024, 1024, (30, 30, 120)); img("cursor.png", 384, 384, (250, 250, 250))
    mk = np.zeros((2688, 1520), np.uint8); mk[700:2300, 460:1060] = 255           # mascara do sujeito (galeria)
    Image.fromarray(mk).save(pr / "foto_mascara.png")
    planos = [
        dict(tipo="gancho_digitado", inicio=0, fim=20, texto="TESTE"),
        dict(tipo="cartao_rotulo", inicio=20, fim=32, foto="foto.png", rotulo="rotulo"),
        dict(tipo="figura_e_palavras", inicio=32, fim=47, figura="fig.png", palavras=[dict(texto="um", quadro=35, x=300)]),
        dict(tipo="documento_digitado", inicio=47, fim=92, documento="doc.png", frase="UMA FRASE DE TESTE",
             destaque="TESTE", quadro_digitar=50, quadro_selecao=70, quadro_zoom=70),
        dict(tipo="objeto_revela", inicio=92, fim=122, objeto="obj.png",
             legenda=dict(palavras=[dict(texto="UM", t=93.0), dict(texto="TESTE", t=97.0)])),
        dict(tipo="foto_pullout", inicio=122, fim=161, foto="foto.png", texto=dict(texto="Em 1952", quadro=125)),
        dict(tipo="palavra_no_papel", inicio=161, fim=200, palavras=[dict(texto="Palavra", quadro=161)]),
        dict(tipo="palavras_e_figura", inicio=200, fim=260, quadro_figura=221, figura="obj.png",
             palavras=[dict(texto="antes", quadro=203)], titulo=dict(texto="Um Titulo", quadro=230)),
        dict(tipo="queda_objeto", inicio=260, fim=302, objeto="obj.png", rotulo="um rotulo"),
        dict(tipo="amassar_lixeira", inicio=302, fim=356, lixeira="lixeira.png"),
        dict(tipo="odometro", inicio=356, fim=389, de=1980, ate=2020),
        dict(tipo="objeto_na_parede", inicio=389, fim=419, objeto="foto.png"),
        dict(tipo="lista_ui", inicio=419, fim=500, saida_desde=470, itens=[dict(texto="Um", quadro=422), dict(texto="Dois", quadro=440)]),
        dict(tipo="moldura_legenda", inicio=500, fim=566, foto="foto.png", legenda=[[dict(texto="uma", quadro=512)]]),
        dict(tipo="icone_cursor", inicio=566, fim=626, icone="icone.png", cursor="cursor.png"),
        dict(tipo="site_url", inicio=626, fim=680, url="teste.com"),
        # v8 / v9: explicativo em papel e tinta
        dict(tipo="barras_placar", inicio=680, fim=740, quadro_selo=700, selo="25/10",
             barras=[dict(valor=47.0, foto="foto.png", ponto=[760, 1100], lado=700),
                     dict(valor=45.0, foto="foto.png", ponto=[760, 1100], lado=700)]),
        dict(tipo="dezena", inicio=740, fim=800, tema="papel", linhas=[dict(predio="camara", valor=5.07, inicio=0, y=700)]),
        dict(tipo="dupla_retratos", inicio=800, fim=860, fotos=["foto.png", "foto.png"], pontos=[[760, 1100], [760, 1100]]),
        dict(tipo="calendario", inicio=860, fim=920, mes="outubro", dia=25, dia_antes=24, quadro_troca=881),
        dict(tipo="hemiciclo", inicio=920, fim=980, total=513, acende=dict(de=923, ate=950, k=260), metade=dict(quadro=950)),
        dict(tipo="pizza", inicio=980, fim=1040, valor=0.53, acende=dict(de=983, ate=1013)),
        dict(tipo="carimbo", inicio=1040, fim=1100, texto="APROVADA", quadro_carimbo=1058),
        dict(tipo="selecao_digitada", inicio=1100, fim=1160, texto="DIAP", letras=[1103, 1106, 1109, 1112], quadro_selecao=1121),
        dict(tipo="duas_molduras", inicio=1160, fim=1220, tamanho_ouro=[410, 490], x=[305, 775], ys=[800, 800],
             itens=[dict(foto="foto.png", ponto=[760, 1100], quadro=1163, legenda="A"),
                    dict(foto="foto.png", ponto=[760, 1100], quadro=1178, legenda="B")]),
        dict(tipo="encontro", inicio=1220, fim=1280, fotos=["foto.png", "foto.png"], pontos=[[760, 1100], [760, 1100]]),
        dict(tipo="objeto_no_papel", inicio=1280, fim=1340, objeto="obj.png"),
        dict(tipo="baloes", inicio=1340, fim=1400),
        dict(tipo="termometro", inicio=1400, fim=1460, valor=6, limite=dict(valor=6, quadro=1430, texto="6/10")),
        dict(tipo="dois_lados", inicio=1460, fim=1520, quadro_pessoa=1463, quadro_congresso=1466, quadro_ida=1472,
             quadro_volta=1484),
        # v10: looks
        dict(tipo="galeria", inicio=1520, fim=1580, itens=[dict(foto="foto.png", ponto=[760, 1100], quadro=1523, legenda="A"),
                                                             dict(foto="foto.png", ponto=[760, 1100], quadro=1529, legenda="B")],
             povo=dict(quadro=[1535, 1539], n=[47, 45], voce=dict(quadro=1553, x=540, y=1500, r=30)),
             baloes=[dict(inicio=1540, cada=3)]),
        dict(tipo="hud_texto", inicio=1580, fim=1640, linhas=[dict(texto="TESTE", quadro=1583, corpo=150, caixa=True)]),
        dict(tipo="canvas_objeto", inicio=1640, fim=1700, objeto="obj.png", palavras=[dict(texto="um", quadro=1646, x=300, y=500)]),
        dict(tipo="pictograma", inicio=1700, fim=1760, quadro_pessoa=1703, quadro_fantasmas=1721),
        # v11: noticia explicada
        dict(tipo="ranking", inicio=1760, fim=1820, vagas=2, titulo=dict(texto="RANKING", quadro=1763),
             itens=[dict(pos=1, texto="Um", quadro=1763, cor="cinza", marcas=[dict(tipo="cai", quadro=1790)]),
                    dict(pos=2, texto="Dois", quadro=1772, cor="azul")], trocas=[dict(quadro=1781, ordem=["Dois", "Um"])]),
        dict(tipo="terminal", inicio=1820, fim=1880, linhas=[dict(texto="$ teste", quadro=1823),
                                                             dict(texto="1  um", quadro=1835, destaque=1841)]),
        dict(tipo="podio", inicio=1880, fim=1940, etiquetas=[dict(pos=1, texto="Um", quadro=1883)],
             circulos=[dict(pos=1, quadro=1895)]),
        dict(tipo="barras", inicio=1940, fim=2000, itens=[dict(rotulo="A", valor=15, texto="US$ 15", cor="azul", quadro=1943),
                                                         dict(rotulo="B", valor=32, texto="US$ 32", quadro=1952)]),
        dict(tipo="centena", inicio=2000, fim=2060, forma="quadrado",
             grupos=[dict(de=0, ate=15, cor="vermelho", quadro=2003)], um=dict(indice=54, quadro=2012)),
        dict(tipo="pizzas", inicio=2060, fim=2120, pizzas=[dict(centro=[480, 860], raio=300, fatias=[
            dict(valor=0.53, cor="azul", quadro=2063, rotulo="A", destaque=2081), dict(valor=0.47, quadro=2069, rotulo="B")],
            fora=dict(quadro=2063, texto="nulos", pos=[840, 1290]))]),
        dict(tipo="celular", inicio=2120, fim=2180, aviao=2135, cabecalho=dict(titulo="IA", sub="no aparelho"),
             conversa=[dict(lado="eu", texto="Uma pergunta?", quadro=2123), dict(lado="ia", texto="Não sei.", quadro=2135,
                                                                                 pensa=2129, marcas=[dict(tipo="certo", quadro=2141)])],
             carimbo=dict(texto="TESTE", quadro=2150), etiqueta=dict(texto="GRÁTIS", quadro=2126)),
        dict(tipo="icones", inicio=2180, fim=2240, divisor=dict(y=960), itens=[
            dict(icone="nota", pos=[300, 600], tam=300, quadro=2183, rotulo=dict(texto="nota", quadro=2183)),
            dict(icone="wifi", pos=[780, 600], tam=300, quadro=2183, risco=2192),
            dict(icone="cadeado", pos=[300, 1300], tam=240, quadro=2183, certo=2192),
            dict(icone="camara", pos=[780, 1300], tam=300, quadro=2183, xis=2192)],
             setas=[dict(de=[400, 960], para=[680, 960], quadro=2186, xis=2195)]),
        dict(tipo="semana", inicio=2240, fim=2300, dias=[["QUI", 8], ["SEX", 9], ["SÁB", 10]], ativo=9, riscados=[8], quadro=2246),
        dict(tipo="linha_no_papel", inicio=2300, fim=2360, palavras=[dict(texto="promessa", quadro=2303),
                                                                     dict(texto="≠", quadro=2309, cor="vermelho"),
                                                                     dict(texto="entrega", quadro=2315, risco=2330)]),
        dict(tipo="botao_cta", inicio=2360, fim=2420, quadro_clique=2375, palavras=[dict(texto="a próxima", quadro=2384)]),
        # v12: galeria documental
        dict(tipo="moldura_entra", inicio=2420, fim=2480, foto="foto.png", legenda=[dict(texto="Teste", corpo=80, dy=80)],
             frases=[dict(texto="uma frase", quadro=2423)]),
        dict(tipo="foto_recorte", inicio=2480, fim=2540, foto="foto.png", mascara="foto_mascara.png",
             bloco=dict(x=280, y0=495, passo=96, corpo=100, linhas=[[dict(texto="um", quadro=2483)]]),
             virada=dict(quadro=2498, frase=dict(texto="do fim.", centro=[790, 662], corpo=128),
                         sublinhado=dict(x0=560, x1=1030, y=740))),
        dict(tipo="etiqueta_rasgada", inicio=2540, fim=2600, foto="foto.png", etiqueta=dict(quadro=2543, x=318, y=825, larg=431, alt=260),
             textos=[dict(palavras=[dict(texto="Três anos", quadro=2546)], rel=[0.12, 0.27], corpo=78)]),
        dict(tipo="jornais_mesa", inicio=2600, fim=2660, titulo=dict(palavras=[dict(texto="Trezentos", quadro=2603)], y=540, corpo=130),
             laco=dict(quadro=2606, centro=[540, 905]), jornais=[dict(nome="Diário", centro=[540, 930], manchete=["25 MILHÕES"])]),
    ]
    # v12.3-v12.7: vídeo na grade (recorte, congela), telestração em todos os tipos de desenho, tela dividida e linha do
    # tempo — com um clipe sintético do próprio ffmpeg (testsrc)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30", "-t", "3",
                    "-pix_fmt", "yuv420p", str(d / "clipe.mp4")], check=True)
    img("recorte.png", 600, 900, (180, 150, 130))
    clip = str(d / "clipe.mp4")
    q0 = 2663
    planos += [
        dict(tipo="video_clip", inicio=2660, fim=2720, clip=clip, ss=0.0, foco=0.5, aproxima=1.2, congela=0.6,
             palavras_grandes=[dict(texto="ATRÁS", quadro=q0, y=900, atras=dict(limiar=[90, 170], regiao=[0, 0, 1080, 1000]))],
             desenhos=[dict(tipo="escurece", quadro=q0, desfoca=6),
                       dict(tipo="traco", quadro=q0, pts=[[200, 600], [800, 600]], tracejado=[20, 12], ponta=True),
                       dict(tipo="traco", quadro=q0, linhas=[[[200, 640], [230, 610]], [[260, 640], [290, 610]]]),
                       dict(tipo="seta", quadro=q0, de=[540, 1200], para=[540, 1000], cor="forca"),
                       dict(tipo="fluxo", quadro=q0, pts=[[300, 700], [300, 1000]], segue=[[2660, 0, 0], [2720, 40, 0]]),
                       dict(tipo="circulo", quadro=q0, centro=[540, 900], rx=120),
                       dict(tipo="ventilador", quadro=q0, centro=[540, 700]),
                       dict(tipo="carrinho", quadro=q0, centro=[540, 1300], pista=True, gira=dict(de=q0, ate=2690)),
                       dict(tipo="rotulo", quadro=q0, texto="rótulo", pos=[540, 500], linha=[[540, 520], [540, 560]]),
                       dict(tipo="balao", quadro=q0, centro=[600, 1100], larg=400, alt=160, ponta=[400, 1200], texto="olá"),
                       dict(tipo="recorte", quadro=q0, imagem="recorte.png", largura=400, pos=[300, 1700], camada="tela"),
                       dict(tipo="proibido", quadro=q0, centro=[540, 960], r=200),
                       dict(tipo="cronometro", quadro=q0, centro=[540, 400], para=2690),
                       dict(tipo="numero", quadro=q0, de=1, ate=10, pos=[540, 960])]),
        dict(tipo="tela_dividida", inicio=2720, fim=2780, entra=6,
             lados=[dict(clip=clip, ss=0.0), dict(clip=clip, ss=1.0, congela=0.5)]),
        dict(tipo="tela_dividida", inicio=2780, fim=2840, modo="janela", caixa=[140, 300, 800, 450], entra=6,
             lados=[dict(clip=clip, ss=0.0), dict(clip=clip, ss=1.0)]),
        dict(tipo="tela_dividida", inicio=2840, fim=2900, modo="empilhada", lados=[dict(clip=clip, ss=0.0), dict(clip=clip, ss=1.0)]),
        dict(tipo="linha_do_tempo", inicio=2900, fim=2960, anos=[2016.5, 2028.6], x=[150, 850], y=1000, quadro_linha=2903,
             rotulos=[dict(ano=2017, quadro=2903)], marcas=[dict(ano=2026.8, quadro=2903, texto="hoje", abaixo=True)],
             cursor=dict(de=2026.8, ate=2028, quadro=2906, chega=2920),
             destaque=dict(ano=2028, quadro=2920, desce=2926, rotulo="produção"),
             foto=dict(imagem="foto.png", ano=2017, x=290, y=600, quadro=2903, legenda="foto"),
             promessa=dict(de=2017, ate=2020, quadro=2903, texto="promessa"), risco=dict(ano=2020, quadro=2903, quadro_x=2906),
             atraso=dict(de=2020, ate=2028, quadro=2906, texto="+8 anos")),
    ]
    (d / "plano.json").write_text(json.dumps(dict(audio="audio/x.wav", planos=planos)))
    cena = projeto.carregar(d)
    for p in planos:
        try:
            q = p["inicio"] + 2 + 3 * ((p["fim"] - p["inicio"]) // 6)
            q -= (q - 2) % 3
            im, _, _ = cena.estado(q)
            acabamento(im, semente=q)
            conf(f"{p['tipo']:20s} q{q}", im.shape == (1920, 1080, 3))
        except Exception as e:
            conf(f"{p['tipo']:20s}", False, f"{type(e).__name__}: {e}")
print("\nTUDO CERTO" if ok else "\nHA PENDENCIAS ACIMA")
sys.exit(0 if ok else 1)
