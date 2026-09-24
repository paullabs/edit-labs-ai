"""
Exemplo de bloco CLIPE do `render.py`, preenchido: um clipe vertical de 58,058s a
30000/1001, com sete motions (seis cutaways e um overlay) e um corte seco no meio.
Os valores sao ficticios, mas coerentes entre si: as janelas da legenda seguem as
regras de `lib/janelas_legenda.py` e cada destaque cai dentro de uma janela.

Serve para ver como os quatro valores da legenda sao escolhidos.
"""
from pathlib import Path
import captions as CAP

ROOT = Path(__file__).resolve().parent

SRC = ROOT / "00_brief" / "fonte.mp4"
DUR = 58.058
FPS_NUM, FPS_DEN = 30000, 1001

# Os sete motions do clipe. As JANELAS da legenda sao o COMPLEMENTO das cutaways.
#   nome, funcao, inicio, fim, frames24 do plano, cutaway?
SHOTS = [
    ("M0", None,  6.000,  9.000,  72, True),   # objeto na mesa + palavra-chave
    ("M1", None, 11.400, 14.600,  77, True),   # relogio + etiqueta
    ("M2", None, 18.000, 21.500,  84, True),   # CRT com terminal
    ("M3", None, 27.000, 29.500,  60, False),  # foto sobre o rosto, overlay
    ("M4", None, 31.000, 34.200,  77, True),   # dado desenhado a mao
    ("M5", None, 42.000, 47.400, 130, True),   # processo: antes -> depois
    ("M6", None, 48.200, 51.800,  86, True),   # comparacao: pouco -> muito
]

CAP.configurar(
    words_json=ROOT / "00_brief" / "transcript_palavras.json",

    # Janelas livres de cutaway, recuadas 0,15s das bordas para nao encostar na saida da
    # cena. O overlay (M3) nao cala a legenda: a janela 21,65-30,85 passa por baixo dele.
    # Repare no que FICOU DE FORA: o vao de 0,80s (47,40-48,20) entre M5 e M6, que
    # recuado sobra com 0,50s, abaixo do minimo de 0,6s. Legenda de meio segundo entre
    # dois cutaways pisca.
    janelas=[(0.15, 5.85), (9.15, 11.25), (14.75, 17.85), (21.65, 30.85),
             (34.35, 41.85), (51.95, 57.908)],

    # Uma enfase por janela, no maximo, e cor em DUAS do clipe inteiro. Na referencia
    # 94% das linhas sao brancas: o acento so funciona porque e raro. A chave e a
    # palavra como esta no transcript, em minusculas e COM a pontuacao ("agora,").
    destaque={
        ("noite", 2.10): dict(cor=None),                # serifa italica, branca
        ("prazo", 15.62): dict(cor=(201, 72, 80)),      # o unico vermelho da 1a metade
        ("resultado", 25.30): dict(cor=None),
        ("agora,", 37.10): dict(cor=(201, 72, 80)),     # a virada do clipe
    },

    # O clipe e a concatenacao de dois trechos do episodio e tem um corte seco em 36,40
    # ("e esse era o plano" | "faz isso agora,"). Sem isso um bloco escrevia "plano faz",
    # juntando o fim de uma frase com o comeco de outra.
    cortes=[36.40],
)
