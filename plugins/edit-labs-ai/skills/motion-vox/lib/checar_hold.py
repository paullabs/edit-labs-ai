#!/usr/bin/env python3
"""
Trava de hold: todo evento de uma cena (pouso, traço, etiqueta) termina pelo menos HOLD quadros
(24 fps) antes da saída — da cena inteira ou, num insert-burst, antes do flash da troca.
A prancha não pega isso: o estado END fica 14 quadros antes do fim e mostra o evento pela metade
sem dizer quanto tempo ele fica na tela. Aqui o número sai do próprio código da cena.

Como: instrumenta kit.p / kit.d (todo evento passa por eles), roda o último quadro de cada trecho
e mede folga = último quadro − fim do evento. Câmera (apply_camera) e a saída da cartela não contam.

A saída da cutaway (flash/push do render.py, EXIT_SLIDE quadros no fps do master) come o fim da
janela: o hold conta até o COMEÇO dela. SAIDA24 = EXIT_SLIDE / fps × 24 (10 q a 59,94 = 4 q de 24).

Uso, da pasta do projeto:  python3 checar_hold.py [HOLD] [SAIDA24]   (padrão: 8 e 4)
Sai com código 1 se alguma cena ficar abaixo.
"""
import linecache
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
import kit as K     # noqa: E402
import cenas as S   # noqa: E402

HOLD = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0
SAIDA24 = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
_OFF = [0.0]        # início do insert em curso (sequencia chama o insert em quadro local)
_EVT = []           # (a, b, arquivo, linha) do quadro avaliado
_SEQ = []           # itens da última sequencia chamada


def _instrumenta(f, nome):
    def g(frame, a, b):
        cod = sys._getframe(1)
        linha = linecache.getline(cod.f_code.co_filename, cod.f_lineno)
        if "apply_camera" not in linha and "sai = " not in linha:
            _EVT.append((nome, a + _OFF[0], b + _OFF[0], Path(cod.f_code.co_filename).name,
                         cod.f_lineno, linha.strip()))
        return f(frame, a, b)
    return g


K.p = _instrumenta(K.p, "p")
K.d = _instrumenta(K.d, "d")
_seq_orig = S.sequencia


def _sequencia(frame, itens, janela=4.0):
    itens = sorted(itens, key=lambda x: x[0])
    _SEQ[:] = [(f0, janela) for f0, _ in itens]
    k = 0
    for i, (f0, _) in enumerate(itens):
        if frame >= f0:
            k = i
    _OFF[0] = itens[k][0]
    try:
        return _seq_orig(frame, itens, janela)
    finally:
        _OFF[0] = 0.0


S.sequencia = _sequencia

import compose as C  # noqa: E402


def avalia(fn, quadro):
    _EVT.clear()
    fn(quadro)
    return list(_EVT)


def main():
    ruins = 0
    for nome, fn, t0, t1, cut in C.CENAS:
        if not cut:
            continue
        n = int(round((t1 - t0) * 24))
        _SEQ.clear()
        fim = avalia(fn, n - 1)
        trechos = [(n - 1 - SAIDA24, fim, "saída da cena")]
        seq = list(_SEQ)
        for i in range(len(seq) - 1):
            f_prox, janela = seq[i + 1]
            ultimo = int(f_prox - janela)          # o flash da troca começa aqui
            trechos.append((ultimo, avalia(fn, ultimo), f"troca {i + 1}→{i + 2}"))
        for ultimo, evts, oque in trechos:
            pior = None
            for e in evts:
                if e[1] <= 0 and e[2] <= 8:       # pouso de entrada (herói em voo no quadro 0)
                    continue
                folga = ultimo - e[2]
                if pior is None or folga < pior[0]:
                    pior = (folga, e)
            if pior is None:
                continue
            folga, e = pior
            marca = "OK " if folga >= HOLD else "✗  "
            if folga < HOLD:
                ruins += 1
            print(f"{marca}{nome:3s} {oque:14s} folga {folga:5.1f} q ({folga / 24:4.2f}s)"
                  f"  ← {e[3]}:{e[4]}  {e[5][:70]}")
    print(f"\n{ruins} trecho(s) abaixo de {HOLD:.0f} quadros de hold")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
