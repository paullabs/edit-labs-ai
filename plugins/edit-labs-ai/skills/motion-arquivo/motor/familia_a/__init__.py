"""
Familia A (Hedy) — documentario de arquivo em papel.

Seis camadas independentes, medidas quadro a quadro na referencia
(o estudo das camadas do reel de referencia). Cada arquivo e uma camada; a cena so as combina.

    tempo          grade de 10 qps — o conteudo so muda a cada 3 quadros
    c1_background  papel cinza, preto
    c2_letras      palavra em serifa italica, rotulo de interface
    c3_style       paleta, caixa de interface, radar
    c4_filtro      scanline, RGB split, grao
    c5_movimentos  camera sobre a cena montada
    c6_motion      curvas de entrada, de saida e de pulso
"""
W, H = 1080, 1920
# Zona segura do Reels orgânico (Meta: 14% em cima, 6% dos lados; legenda e coluna de botões embaixo à direita).
# Texto e rosto ficam dentro; "meio" é onde o texto deve morar (regra do estilo: texto no meio). Ver ferramentas/zona_segura.py
ZONA = {"topo": 270, "base": 1520, "trilho_x": 930, "trilho_y": 880, "esquerda": 90, "direita": 990}
MEIO = (560, 1360)
