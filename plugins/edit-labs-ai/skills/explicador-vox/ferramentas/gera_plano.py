"""Plano de batidas do explicador Vox: escreve o plano.json (câmera, camadas com chaves, fundos, sons, legenda,
título) e confere orçamento de tela, degrau de 12 qps, zona segura e sincronia com a fala.

    python gera_plano.py exemplo  <saida/plano.json> [palavras.json]   -> o plano do exemplo "soco no queixo"
    python gera_plano.py conferir <plano.json> <palavras.json>          -> só confere um plano existente

Para um vídeo novo: copie este arquivo para a pasta do projeto, troque o conteúdo de plano_exemplo() pelo seu
(mesmos auxiliares K, S, lay, caminho) e rode "exemplo" de novo. O plano.json é a fonte da verdade para a prévia
local (previa.py) e para a timeline do invideo (invideo_ops.py).

Convenções (as mesmas da prévia e do invideo):
- tela 1080x1920 a 24 qps; o desenho anda em degraus de 2 quadros (12 qps): toda chave em quadro par;
- câmera: z = escala do mundo; (cx, cy) = ponto do mundo que cai no centro da tela (540, 960);
- x, y = onde a âncora da camada cai no mundo (mundo:true) ou na tela (mundo:false);
- rotação em graus, positiva = horário; escala 1,0 = o tamanho planejado ("tamanho");
- chave = [quadro, valor, curva]; a curva vale até a chave seguinte; "segura" = degrau;
- "grupo" serve à conta do orçamento: o objeto feito de partes conta 1; "fundo" e "ajuste" não contam."""
import json
import sys

FPS = 24
TELA = (1080, 1920)
ZONA_ASSUNTO = (560, 1360)          # régua: assunto, contato e título dentro desta faixa de y
ZONA_REELS = (260, 1420)            # margem segura do Reels (REGRAS.md): nada importante fora
SINC_MIN, SINC_MAX = -0.60, 0.27    # régua: a imagem chega até 0,60 s antes e no máximo 0,27 s depois da palavra
MAX_GRUPOS = 2                      # orçamento por quadro, fora a legenda (a referência aceita até 4 num eixo só)


def K(*pts, c="lin"):
    """chaves: pts = (q, v) ou (q, v, curva)"""
    return [[p[0], p[1], p[2] if len(p) > 2 else c] for p in pts]


def S(q, v):
    """valor parado desde o quadro q"""
    return [[q, v, "segura"]]


def lay(nome, arquivo, mundo, ini, fim, tam, grupo, ancora="centro", sombra=None, boil=None, descricao="", **ch):
    return {"nome": nome, "arquivo": arquivo, "mundo": mundo, "ini": ini, "fim": fim, "tamanho": tam,
            "ancora": ancora, "grupo": grupo, "sombra": sombra, "boil": boil, "descricao": descricao, "chaves": ch}


def caminho(pts):
    """pts = (q, x, y, rot[, curva]) -> chaves x, y, rot"""
    xs, ys, rs = [], [], []
    for p in pts:
        q, x, y, r = p[:4]
        c = p[4] if len(p) > 4 else "lin"
        xs.append([q, x, c]); ys.append([q, y, c]); rs.append([q, r, c])
    return xs, ys, rs


# sombra por material: (deslocamento y, desfoque, opacidade)
SOMBRA_RECORTE = [6, 14, 0.18]
SOMBRA_LUVA = [20, 32, 0.22]
SOMBRA_LUVA_ESCURO = [20, 32, 0.12]
SOMBRA_CARTAO = [11, 24, 0.25]


# ------------------------------------------------------------------------------------------------ o exemplo
def plano_exemplo():
    """'Por que um soco no queixo apaga uma pessoa?' (29,9 s). Ver referencias/plano-exemplo.md."""
    FIM = 718                                      # a voz acaba em q694; 1 s de cauda para o título ficar legível
    L = []

    # tela: vinheta do escuro
    L.append(lay("VINHETA", "vinheta", False, 182, FIM, [1080, 1920], "fundo",
                 descricao="vinheta radial: centro transparente, bordas #121212",
                 x=S(182, 540), y=S(182, 960), op=K((182, 0), (212, 100, "segura"))))
    # grades: só onde dão referência ao empurrão, ao giro e à medida
    L.append(lay("GRADE_PAPEL", "grade_papel", True, 70, 212, [2000, 3000], "fundo",
                 descricao="grade em losango, linha 2 px #6F6E6B, célula 60 px",
                 x=S(70, 540), y=S(70, 960), op=K((70, 100, "segura"), (182, 100), (212, 0, "segura"))))
    L.append(lay("GRADE_ESCURO", "grade_escuro", True, 182, 496, [2000, 3000], "fundo",
                 descricao="grade em losango, linha 2 px #4C4C4C, célula 60 px",
                 x=S(182, 540), y=S(182, 960), op=K((182, 0), (212, 100, "segura"), (488, 100), (494, 0, "segura"))))
    for g in L[-2:]:
        g["previa_reduz"] = 2                      # a grade só aparece com zoom <= 1,15: a prévia usa meia resolução

    # A: a foto impressa e o "apaga"
    L.append(lay("FOTO_GANCHO", "foto_gancho", True, 0, 70, [900, 740], "foto", sombra=SOMBRA_CARTAO,
                 descricao="foto de arquivo de 1897 (domínio público) impressa como cartão com margem #F1ECE0",
                 x=S(0, 540), y=S(0, 900), rot=S(0, -2), s=K((0, 1.03, "out"), (4, 1.0, "segura")), op=S(0, 100)))
    preto = lay("PRETO_FOTO", None, True, 0, 70, [860, 640], "ajuste",
                descricao="retângulo #111111 do tamanho da foto, sem a margem",
                x=S(0, 539), y=S(0, 870), rot=S(0, -2), s=K((0, 1.03, "out"), (4, 1.0, "segura")),
                op=K((0, 0, "segura"), (32, 15, "segura"), (34, 30, "segura"), (36, 45, "segura"), (38, 58, "segura"),
                     (40, 70, "segura"), (42, 78, "segura"), (44, 85, "segura")))
    preto["forma"] = {"tipo": "rectangle", "cor": "#111111"}
    preto["luz_linear"] = True                     # o invideo mistura em luz linear: corrige a opacidade do preto
    L.append(preto)

    # B-E: a pessoa vista de cima (ombros, cabeça e pino contam 1)
    push_cab = [(134, 900), (136, 920), (138, 945), (140, 965), (142, 982), (144, 993), (146, 999),
                (148, 1000, "segura"), (168, 1000), (170, 980), (172, 950), (174, 922), (176, 906), (178, 900, "segura")]
    push_omb = [(q, round(1030 + (v - 900) * 0.6), *rest) for (q, v, *rest) in push_cab]
    L.append(lay("OMBROS", "ombros_cima", True, 70, 496, [900, 380], "pessoa", sombra=SOMBRA_RECORTE, boil="obj",
                 descricao="pessoa genérica gerada, vista de cima, só o tronco, com borda de papel",
                 x=S(70, 540), y=K((70, 1030, "segura"), *push_omb),
                 op=K((70, 100, "segura"), (488, 100), (494, 0, "segura"))))
    # o interior fica por baixo da cabeça desde o mergulho
    L.append(lay("CRANIO", "cranio_cima", True, 488, 652, [640, 640], "interior", boil="paper",
                 descricao="anel do crânio de uma gravura anatômica CC BY 4.0, tingido de osso; a nuca refeita em arco",
                 x=S(488, 540), y=S(488, 900),
                 rot=K((488, 0, "segura"), (562, -8), (564, -17), (566, -25), (568, -32), (570, -37),
                       (572, -40, "segura")),
                 op=K((488, 100, "segura"), (644, 100), (650, 0, "segura"))))
    balanco = [(488, 540, "segura"), (508, 550, "segura"), (512, 533, "segura"), (516, 544, "segura"),
               (520, 540, "segura"), (524, 542, "segura"), (528, 538, "segura"), (532, 542, "segura"),
               (536, 538, "segura"), (540, 540, "segura")]
    L.append(lay("CEREBRO", "cerebro_cima", True, 488, 608, [640, 640], "interior", boil="obj",
                 descricao="o cérebro da mesma gravura, separado do crânio, 10% menor (folga para atrasar)",
                 x=K(*balanco), y=S(488, 900),
                 rot=K((488, 0, "segura"), (508, 3, "segura"), (512, -2, "segura"), (516, 1, "segura"),
                       (520, 0, "segura"), (562, 0), (566, -2), (572, -3), (582, -4), (590, -5), (598, -6),
                       (604, -8, "segura")),
                 op=S(488, 100)))
    L.append(lay("CEREBRO_TORCIDO_1", "cerebro_torcido_1", True, 608, 610, [640, 640], "interior", boil="obj",
                 descricao="o mesmo cérebro, torção 50% (borda +6°, miolo 0°)",
                 x=S(608, 540), y=S(608, 900), rot=S(608, -8), op=S(608, 100)))
    L.append(lay("CEREBRO_TORCIDO_2", "cerebro_torcido_2", True, 610, 652, [640, 640], "interior", boil="obj",
                 descricao="torção 100% (borda +12°) e 8 fibras finas no vermelho da luva",
                 x=S(610, 540), y=S(610, 900), rot=S(610, -8),
                 op=K((610, 100, "segura"), (644, 100), (650, 0, "segura"))))

    rot_cab = [(70, 0, "segura"),
               (318, -10), (320, -22), (322, -32), (324, -39), (326, -43), (328, -45), (330, -47), (332, -45, "segura"),
               (416, -36), (418, -27), (420, -18), (422, -9), (424, -3), (426, 0, "segura"),
               (444, -5), (446, -11), (448, -15), (450, -10), (452, -4), (454, 0, "segura"),
               (464, -12), (466, -24), (468, -33), (470, -39), (472, -43), (474, -45), (476, -47), (478, -45, "segura"),
               (482, -36), (484, -24), (486, -12), (488, -4), (490, 0, "segura")]
    L.append(lay("CABECA", "cabeca_cima", True, 70, 502, [640, 640], "pessoa", sombra=SOMBRA_RECORTE, boil="obj",
                 descricao="a cabeça da mesma pessoa, nariz para o topo; o pivô P no centro do arquivo",
                 x=S(70, 540), y=K((70, 900, "segura"), *push_cab), rot=K(*rot_cab),
                 op=K((70, 100, "segura"), (494, 100), (500, 0, "segura"))))

    # D: fita e chave (rotação -45 = a da cabeça virada)
    for nome, arq, a, b in [("FITA_25", "fita_25", 346, 348), ("FITA_50", "fita_50", 348, 350),
                            ("FITA_75", "fita_75", 350, 352), ("FITA_50_VOLTA", "fita_50", 396, 398)]:
        L.append(lay(nome, arq, True, a, b, [640, 640], "fita", descricao="fita métrica gerada, estado por máscara",
                     x=S(a, 540), y=S(a, 900), rot=S(a, -45), op=S(a, 100)))
    L.append(lay("FITA_100", "fita_100", True, 352, 396, [640, 640], "fita", sombra=[3, 6, 0.2],
                 descricao="fita inteira: do pino até o queixo (240 px)",
                 x=K((352, 540, "segura"), (360, 536, "segura"), (362, 540, "segura")),
                 y=K((352, 900, "segura"), (360, 896, "segura"), (362, 900, "segura")), rot=S(352, -45),
                 op=S(352, 100)))
    L.append(lay("CHAVE", "chave", True, 396, 438, [640, 640], "chave", sombra=[8, 14, 0.25],
                 descricao="chave estrela CC0: a boca abraça o pino, o cabo vai até o queixo",
                 x=S(396, 540), y=S(396, 900),
                 rot=K((396, -45, "segura"), (416, -36), (418, -27), (420, -18), (422, -9), (424, -3),
                       (426, 0, "segura")),
                 s=K((396, 1.35), (398, 1.12), (400, 1.03), (402, 1.0, "segura"), (404, 1.02), (406, 1.0, "segura"),
                     (432, 1.0), (434, 1.12), (436, 1.25, "segura")),
                 op=K((396, 0), (398, 60), (400, 100, "segura"), (432, 100), (434, 50), (436, 0, "segura"))))
    L.append(lay("PINO", "pino", True, 262, 502, [44, 44], "pessoa", sombra=[4, 6, 0.3],
                 descricao="colchete bailarina de latão gerado, de cima: a articulação do boneco de papel = o eixo",
                 x=S(262, 540), y=S(262, 900), s=K((262, 1.6), (264, 1.15), (266, 1.0, "segura")),
                 op=K((262, 100, "segura"), (494, 100), (500, 0, "segura"))))

    # luvas: o mesmo PNG, âncora no centro da luva
    LUVA = "luva vermelha abafada gerada, sem marca, apontando para baixo, com o antebraço"
    AN = [150, 670]
    reta_y = [(74, -300), (76, -60), (78, 160), (80, 320), (82, 410, "segura"), (84, 395), (86, 380, "segura"),
              (106, 430), (108, 470), (110, 500), (112, 510, "segura"),
              (134, 510), (136, 530), (138, 555), (140, 575), (142, 592), (144, 603), (146, 609), (148, 610, "segura"),
              (150, 600), (152, 560), (154, 470), (156, 330), (158, 120), (160, -160, "segura")]
    L.append(lay("LUVA_RETA", "luva", True, 74, 162, [300, 820], "luva", ancora=AN, sombra=SOMBRA_LUVA, boil="obj",
                 descricao=LUVA, x=S(74, 540), y=K(*reta_y), rot=S(74, 0), op=S(74, 100)))
    gx, gy, gr = caminho([(182, 1400, 400, 40), (184, 1260, 470, 42), (186, 1140, 520, 44), (188, 1060, 550, 45),
                          (190, 1010, 560, 45, "segura"), (204, 1030, 545, 42, "segura"), (216, 1010, 560, 45, "segura"),
                          (218, 940, 610, 60), (220, 870, 660, 75), (222, 815, 690, 86), (224, 787, 700, 90, "segura"),
                          (300, 779, 700, 90, "segura"), (318, 760, 698, 92), (320, 740, 695, 92, "segura"),
                          (324, 790, 680, 85), (326, 880, 640, 70), (328, 990, 590, 55), (330, 1120, 530, 45),
                          (332, 1280, 460, 40), (334, 1450, 400, 40, "segura")])
    L.append(lay("LUVA_GANCHO", "luva", True, 182, 336, [300, 820], "luva", ancora=AN, sombra=SOMBRA_LUVA_ESCURO,
                 boil="obj", descricao=LUVA, x=gx, y=gy, rot=gr, op=S(182, 100)))
    ax, ay, ar = caminho([(438, 1300, 800, 90), (440, 1100, 800, 90), (442, 950, 800, 90), (444, 846, 800, 90, "segura"),
                          (446, 900, 800, 90), (448, 1000, 800, 90), (450, 1050, 780, 90), (452, 1050, 740, 90),
                          (454, 1050, 700, 90, "segura"), (456, 1080, 700, 90), (458, 1110, 700, 90, "segura"),
                          (460, 960, 700, 90), (462, 850, 700, 90), (464, 787, 700, 90), (466, 765, 698, 92),
                          (468, 760, 698, 92, "segura"), (470, 840, 720, 90), (472, 960, 760, 90), (474, 1100, 800, 90),
                          (476, 1260, 840, 90), (478, 1420, 880, 90, "segura")])
    L.append(lay("LUVA_ALAVANCA", "luva", True, 438, 480, [300, 820], "luva", ancora=AN, sombra=SOMBRA_LUVA_ESCURO,
                 boil="obj", descricao=LUVA, x=ax, y=ay, rot=ar, op=S(438, 100)))

    # F: a pessoa volta (por baixo do cartão da fonte)
    L.append(lay("OMBROS_F", "ombros_cima", True, 650, FIM, [900, 380], "pessoa", sombra=SOMBRA_RECORTE, boil="obj",
                 x=S(650, 540), y=S(650, 1030), op=K((650, 0), (656, 100, "segura"))))
    L.append(lay("CABECA_F", "cabeca_cima", True, 650, FIM, [640, 640], "pessoa", sombra=SOMBRA_RECORTE, boil="obj",
                 x=S(650, 540), y=S(650, 900),
                 rot=K((650, 0, "segura"), (678, -10), (680, -22), (682, -32), (684, -39), (686, -43), (688, -46),
                       (690, -45, "segura")),
                 op=K((650, 0), (656, 100, "segura"))))
    L.append(lay("PINO_F", "pino", True, 650, FIM, [44, 44], "pessoa", sombra=[4, 6, 0.3],
                 x=S(650, 540), y=S(650, 900), op=K((650, 0), (656, 100, "segura"))))

    # F: o cartão da fonte (tela), limpo, sem marcador: sobe pela base, fica legível e sai por baixo
    L.append(lay("ARTIGO", "artigo_0", False, 640, 682, [860, 600], "artigo", sombra=[11, 24, 0.3],
                 descricao="citação tipografada do artigo-fonte (título, autores, revista, ano, doi)",
                 x=S(640, 540),
                 y=K((640, 2300), (642, 1250), (644, 820), (646, 826), (648, 820, "segura"),
                     (674, 820), (676, 900), (678, 1150), (680, 1700), (682, 2400, "segura")),
                 rot=K((640, -6), (642, -4), (644, -3, "segura")), op=S(640, 100)))

    camera = {
        "z": K((0, 1.0, "segura"), (22, 1.0, "out"), (34, 1.3, "segura"), (70, 1.0, "segura"),
               (242, 1.0, "io"), (262, 1.12, "segura"), (286, 1.12, "io"), (298, 1.0, "segura"),
               (336, 1.0, "out"), (346, 1.15, "segura"), (406, 1.15, "io"), (414, 1.0, "segura"),
               (488, 1.0, "out"), (508, 2.0, "segura"), (650, 1.0, "segura")),
        "cx": K((0, 540, "segura"), (22, 540, "out"), (34, 523, "segura"), (70, 540, "segura"),
                (336, 540, "out"), (346, 470, "segura"), (406, 470, "io"), (414, 540, "segura")),
        "cy": K((0, 960, "segura"), (22, 960, "out"), (34, 705, "segura"), (70, 960, "segura"),
                (242, 960, "io"), (262, 900, "segura"), (286, 900, "io"), (298, 960, "segura"),
                (336, 960, "out"), (346, 900, "segura"), (406, 900, "io"), (414, 960, "segura"),
                (488, 960, "out"), (508, 900, "segura"), (650, 860, "segura")),
    }
    fundos = [
        {"nome": "PAPEL", "arquivo": "fundo_papel", "cor": "#DEDBCB", "ini": 0, "fim": 212,
         "op": K((0, 100, "segura"), (182, 100), (212, 0, "segura"))},
        {"nome": "CARVAO", "arquivo": "fundo_carvao", "cor": "#232325", "ini": 182, "fim": FIM,
         "op": K((182, 0), (212, 100, "segura"))},
    ]
    # som: quadro do GOLPE (pico do efeito) e a classe que define a queda abaixo da voz (som.py)
    sons = [
        {"id": "e01", "efeito": "abre_papel", "quadro": 2, "classe": "papel", "acao": "o cartão da foto pousa"},
        {"id": "e02", "efeito": "soco_ar", "quadro": 108, "classe": "ar", "acao": "o reto desce pela linha do meio"},
        {"id": "e03", "efeito": "soco_baque", "quadro": 112, "classe": "acento", "acao": "o reto encosta no nariz"},
        {"id": "e04", "efeito": "empurra", "quadro": 136, "classe": "ar", "acao": "a cabeça é empurrada para trás"},
        {"id": "e05", "efeito": "gancho_ar", "quadro": 220, "classe": "ar", "acao": "o arco do gancho, da direita"},
        {"id": "e06", "efeito": "soco_baque", "quadro": 224, "classe": "acento", "acao": "o gancho acerta o queixo"},
        {"id": "e08", "efeito": "gira", "quadro": 320, "classe": "ar", "acao": "a cabeça gira 45° no pino"},
        {"id": "e09", "efeito": "alavanca", "quadro": 400, "classe": "papel", "acao": "a chave pousa no pino"},
        {"id": "e10", "efeito": "mais_giro", "quadro": 466, "classe": "ar", "acao": "o toque longe: giro de 45°"},
        {"id": "e11", "efeito": "mergulho", "quadro": 500, "classe": "acento", "acao": "o mergulho: a cabeça vira crânio"},
        {"id": "e12", "efeito": "gira", "quadro": 564, "classe": "ar", "acao": "o crânio gira 40° (rima com o e08)"},
        {"id": "e13", "efeito": "estica", "quadro": 610, "classe": "longo", "acao": "o cérebro fica para trás e torce"},
        {"id": "e14", "efeito": "cartao", "quadro": 648, "classe": "papel", "acao": "o cartão da fonte assenta"},
        {"id": "e15", "efeito": "giro_final", "quadro": 682, "classe": "acento", "acao": "a cabeça gira e o título entra"},
    ]
    TINTA, CREME = "#29292B", "#F2EEE6"
    blocos = [("Por que um soco no queixo", 2, 36), ("apaga uma pessoa?", 36, 72), ("Um soco reto,", 76, 104),
              ("no meio do rosto,", 104, 134), ("só empurra a cabeça para trás.", 134, 182), ("Já o gancho,", 186, 210),
              ("de lado no queixo,", 210, 244), ("passa longe do eixo.", 244, 286), ("A cabeça não recua,", 288, 322),
              ("gira.", 322, 344), ("O queixo fica longe do eixo.", 346, 398), ("Vira alavanca.", 398, 430),
              ("Quanto mais longe,", 430, 458), ("mais giro.", 458, 490), ("E o cérebro está solto lá dentro.", 490, 548),
              ("Quando o crânio gira,", 552, 584), ("ele fica para trás e estica.", 584, 640),
              ("Não é a força,", 640, 672)]       # calada no título: quem diz "é o giro" é o título
    legenda = []
    for t, a, b in blocos:
        escuro = a >= 196                          # o fundo já está no carvão
        legenda.append({"texto": t, "ini": a, "fim": b,
                        "y": 440 if b <= 72 else 1372,      # no ato A a foto cobre a faixa de baixo: legenda no papel
                        "cor": CREME if escuro else TINTA, "sombra": escuro, "corpo": 50, "peso": 600})
    titulo = [{"texto": "É O GIRO", "ini": 682, "fim": FIM, "x": 540, "y": 640, "peso": 800, "corpo": 96,
               "maiuscula_px": 68, "cor": CREME, "op": K((682, 0), (684, 33), (686, 66), (688, 100, "segura"))}]
    sincronia = [("queixo", 1, 22, "empurrão até o contato da foto"), ("apaga", 1, 32, "a foto apaga"),
                 ("um", 2, 74, "a luva reta entra"), ("rosto", 1, 112, "contato do reto"),
                 ("empurra", 1, 134, "empurrão"), ("já", 1, 182, "o gancho entra e o fundo escurece"),
                 ("queixo", 2, 218, "arco do gancho"), ("eixo", 1, 262, "o pino desce"),
                 ("cabeça", 2, 286, "a câmera volta"), ("recua", 1, 300, "a luva aperta"),
                 ("gira", 1, 318, "a cabeça gira"), ("queixo", 3, 346, "a fita desenrola"),
                 ("longe", 2, 360, "a ponteira"), ("vira", 1, 396, "a chave desce"),
                 ("giro", 1, 464, "toque longe e giro"), ("cérebro", 1, 488, "mergulho"),
                 ("solto", 1, 508, "o cérebro balança"), ("gira", 2, 562, "o crânio gira"),
                 ("ele", 1, 582, "o cérebro atrasa"), ("estica", 1, 608, "torção"), ("não", 2, 640, "o cartão sobe"),
                 ("giro", 2, 678, "a cabeça gira"), ("giro", 2, 682, "o título entra")]
    return {"fps": FPS, "fim": FIM, "voz_fim": 694, "tela": list(TELA), "mundo_escala": 2,
            "convencoes": {
                "mundo_tela": "mundo:true anda com a câmera; mundo:false fica parado na tela",
                "camera": "z = escala do mundo; (cx, cy) = ponto do mundo no centro da tela (540, 960)",
                "posicao": "x, y = onde fica a âncora da camada (centro do arquivo, ou o ponto [x, y] em px planejados)",
                "rotacao": "graus, positivo = horário na tela",
                "escala": "1.0 = tamanho planejado; o PNG da peça é feito em 2x esse tamanho",
                "curva": "vale do quadro da chave até a chave seguinte; 'segura' = degrau",
                "degrau": "o desenho anda em degraus de 2 quadros (12 qps); toda chave em quadro par",
                "ordem": "camadas de baixo para cima, acima dos fundos; 'grupo' é só para a conta do orçamento"},
            "camera": camera, "camadas": L, "fundos": fundos, "sons": sons, "legenda": legenda, "titulo": titulo,
            "sincronia": [{"palavra": w, "n": n, "quadro": q, "evento": e} for w, n, q, e in sincronia]}


# ------------------------------------------------------------------------------------------------ conferência
def valor(keys, q):
    if not keys:
        return None
    if q <= keys[0][0]:
        return keys[0][1]
    for (q0, v0, c), (q1, v1, _) in zip(keys, keys[1:]):
        if q0 <= q < q1:
            return v0 if c == "segura" else v0 + (v1 - v0) * (q - q0) / (q1 - q0)
    return keys[-1][1]


def conferir(plano, palavras=None):
    """imprime e devolve a lista de problemas (vazia = passou)"""
    L, FIM = plano["camadas"], plano["fim"]
    problemas = []
    for l in L:
        for nome, ks in l["chaves"].items():
            problemas += [f"{l['nome']}: chave de {nome} em quadro ímpar {k[0]}" for k in ks if k[0] % 2]
        if l["ini"] % 2 or l["fim"] % 2:
            problemas.append(f"{l['nome']}: início/fim em quadro ímpar")
    for prop, ks in plano["camera"].items():
        problemas += [f"câmera: chave de {prop} em quadro ímpar {k[0]}" for k in ks if k[0] % 2]

    nao_conta = {"fundo", "ajuste"}
    por_quadro = {}
    for q in range(0, FIM, 2):
        grupos = set()
        for l in L:
            if l["grupo"] in nao_conta or not (l["ini"] <= q < l["fim"]):
                continue
            op = valor(l["chaves"].get("op"), q)
            if op is not None and op <= 0:
                continue
            x, y = valor(l["chaves"].get("x"), q), valor(l["chaves"].get("y"), q)
            if l["mundo"] and x is not None and (x < -150 or x > 1230 or y < -150 or y > 2070):
                continue
            if not l["mundo"] and y is not None and y > 2200:
                continue
            grupos.add(l["grupo"])
        for t in plano.get("titulo", []):
            if t["ini"] <= q < t["fim"] and valor(t["op"], q) > 0:
                grupos.add("titulo")
        por_quadro[q] = sorted(grupos)
    lotado = [(q, g) for q, g in por_quadro.items() if len(g) > MAX_GRUPOS]
    if lotado:
        problemas.append(f"{len(lotado)} quadros com mais de {MAX_GRUPOS} elementos, ex.: {lotado[:3]}")
    respiro = [q for q, g in por_quadro.items() if len(g) <= 1]
    faixas = []
    for q in respiro:
        if faixas and q == faixas[-1][1] + 2:
            faixas[-1][1] = q
        else:
            faixas.append([q, q])

    for t in plano.get("titulo", []):
        if not ZONA_ASSUNTO[0] <= t["y"] <= ZONA_ASSUNTO[1]:
            problemas.append(f"título '{t['texto']}' em y {t['y']}, fora de {ZONA_ASSUNTO}")
    for lg in plano.get("legenda", []):
        if not ZONA_REELS[0] <= lg["y"] <= ZONA_REELS[1]:
            problemas.append(f"legenda '{lg['texto']}' em y {lg['y']}, fora da margem do Reels {ZONA_REELS}")

    print("degrau e orçamento:", "ok" if not problemas else "")
    for p in problemas:
        print("  -", p)
    print(f"respiro (<= 1 elemento): {len(respiro)} de {len(por_quadro)} desenhos; faixas:",
          [(a, b + 2) for a, b in faixas])

    if palavras:
        pal = palavras["palavras"]

        def inicio(w, n):
            k = 0
            for p in pal:
                if p["palavra"].strip(",.?!:;").lower() == w:
                    k += 1
                    if k == n:
                        return p["ini"]
            return None

        print("sincronia (evento - palavra, em s; régua: de -0,60 a +0,27, mediana ~ -0,18):")
        difs = []
        for s in plano.get("sincronia", []):
            t = inicio(s["palavra"], s["n"])
            if t is None:
                problemas.append(f"sincronia: palavra '{s['palavra']}' #{s['n']} não achada")
                continue
            d = s["quadro"] / plano["fps"] - t
            difs.append(d)
            marca = "" if SINC_MIN <= d <= SINC_MAX else "  <- fora da régua"
            if marca:
                problemas.append(f"sincronia: {s['evento']} {d:+.2f} s")
            print(f"  {s['evento']:34s} q{s['quadro']:<4d} '{s['palavra']}'#{s['n']} {t:6.2f}  {d:+.2f}{marca}")
        if difs:
            difs.sort()
            print(f"  mediana {difs[len(difs) // 2]:+.2f} s")
    print("RESULTADO:", "passou" if not problemas else f"{len(problemas)} problema(s)")
    return problemas


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("exemplo", "conferir"):
        sys.exit(__doc__)
    if sys.argv[1] == "exemplo":
        plano = plano_exemplo()
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(plano, f, ensure_ascii=False, indent=1)
        print("plano gravado em", sys.argv[2])
        pal = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else None
    else:
        plano = json.load(open(sys.argv[2], encoding="utf-8"))
        pal = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else None
    sys.exit(1 if conferir(plano, pal) else 0)
