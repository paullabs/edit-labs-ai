"""
Teste de referencia — Hedy 18,87–23,27 s (quadros 566–697 do original).

(a frase que diz que a invencao virou base do Wi-Fi, do Bluetooth e do GPS)

Dois planos, os dois sem nenhuma imagem gerada:
  566–616  papel com uma palavra por vez
  617–697  radar no preto com tres caixas de interface

Os quadros de aparicao vem da regra medida — a palavra entra no primeiro degrau da
grade depois de comecar a ser dita — e conferem com o original quadro a quadro.
"""
from familia_a import W, H
from familia_a import c1_background as bg, c2_letras as le, c3_style as st
from familia_a import c5_movimentos as mv, c6_motion as mo
from familia_a.tempo import grade, FPS
from familia_a.compor import sobre

INICIO, FIM = 566, 698            # [INICIO, FIM)

# --- plano 1: papel. (texto, quadro em que a animacao comeca, visivel de, ate)
PALAVRAS = [
    ("Became",       563, 566, 572),   # comecou um degrau antes do corte
    ("the",          572, 572, 578),
    ("Foundation",   578, 578, 593),
    ("For",          593, 593, 596),   # sai seco: 3 quadros de papel vazio
    ("Technologies", 599, 599, 617),
]

# --- plano 2: radar. (texto, quadro de entrada, alvo x externo @1080, topo y @1080)
CAIXAS = [
    ("Wi-Fi",     620, 327.0, 745.0),
    ("Bluetooth", 647, 331.5, 907.0),
    ("GPS",       668, 354.0, 1067.0),
]
RADAR_INICIO = 617
RADAR_FASE0 = 0.673               # anel interno com 55 px no primeiro quadro
CAMERA_DESDE = 650

_papel = None


def estado(n):
    """Cena montada (antes dos filtros) para o quadro da grade n. Devolve (img, dx)."""
    global _papel
    if n < 617:
        if _papel is None:
            _papel = bg.papel()
        img = _papel.copy()
        for texto, ini, a, b in PALAVRAS:
            if a <= n < b:
                esc = mo.escala_palavra((n - ini) / FPS)
                img = sobre(img, le.palavra(texto, esc))
        return img, 0.0, None
    img = bg.preto()
    fase = mo.fase_radar((n - RADAR_INICIO) / FPS, RADAR_FASE0)
    img = sobre(img, st.radar(fase))
    for texto, ini, alvo, topo in CAIXAS:
        if n >= ini:
            x = alvo + mo.entrada_caixa((n - ini) / FPS)
            img = sobre(img, st.caixa_ui(texto), x, topo)
    dx = mo.saida_camera((n - CAMERA_DESDE) / 3.0)
    return img, dx, bg.PRETO


def borrao(n):
    """Borrao da saida: so quando o passo da camera passa do limiar medido."""
    if n < 617:
        return 0.0
    passo = mo.saida_camera((n - CAMERA_DESDE) / 3.0) - mo.saida_camera((n - 3 - CAMERA_DESDE) / 3.0)
    return mo.borrao_saida(passo)
