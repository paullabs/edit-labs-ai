#!/usr/bin/env python3
"""
Esqueleto de cena. Copie para o projeto como `compose.py` e escreva uma build_M# por cena.

Toda a mecanica da identidade vem de `kit`. Aqui fica so CONTEUDO: que objeto entra,
onde, em que frame, ancorado em que palavra.

PRINCIPIO: nao existe "imagem do START" e "imagem do END" desenhadas a mao. Existe UMA
timeline em frames por cena, e cada estado e essa timeline avaliada num frame. Por isso
os estados sao coerentes por construcao.
"""
import sys, math
from kit import *          # noqa: F401,F403  — mecanica da identidade
import kit as K
import voxlab as V


# =====================================================================  M1 (exemplo)
# Substitua por cenas reais. Cada evento ancorado numa palavra do transcript:
#   frame24 = (t_palavra - t_inicio_do_plano) * 24
M1_STATES = {"START": 0, "MID": 36, "END": 58, "EXIT": 70}
M1_EVENTS = dict(hero=(0, 10), tape=(8, 15), label=(15, 29), headline=(32, 43),
                 circle=(40, 51), arrow=(51, 58), line=(4, 52), camera=(30, 64))


def build_M1(frame):
    c = bg_paper()
    E = M1_EVENTS

    # props periféricos cortados pelas bordas — dao mundo sem somar elemento relevante
    place(c, piece("A10_SCRAPS", 1, 168, rotation=-9), (-58, 1560), shadow=SH_PAPER)
    place(c, piece("A04_CLIPS", 0, 124, rotation=24), (-34, 524), shadow=SH_PAPER)

    # linha de continuidade: MESMA altura e MESMO desenho em todas as cenas
    c.alpha_composite(blue_line(c.size, [(-60, 392), (250, 420), (560, 382),
                                         (870, 412), (1140, 396)],
                                progress=d(frame, *E["line"]), width=7))

    # HERO pousando de cima, com overshoot e sombra crescendo junto
    hp = p(frame, *E["hero"])
    clock, dial, dr = clock_at(9.0 * hp, 600, rotation=-3 + 1.5 * hp)
    pos = centered(clock, 540, 852 - (1 - hp) * 740 + math.sin(hp * math.pi) * 18)
    place(c, clock, pos, shadow=dict(dy=int(5 + 15 * hp), blur=int(12 + 20 * hp),
                                     opacity=0.05 + 0.15 * hp))
    dcx, dcy = pos[0] + dial[0], pos[1] + dial[1]

    # manchete em BLOCO — nunca caractere a caractere
    c.alpha_composite(text_layer(c.size, "UMA NOITE", F_COND, 80, (540, 214),
                                 color=INK, anchor="mt", tracking=3, mode="block",
                                 progress=p(frame, *E["headline"])))

    # etiqueta: a fita e dimensionada PELA PALAVRA, e o texto vai no centro optico dela
    lab_w = hand_width("PRAZO", F_MARKER, 118, 4, 21, 3) + 118 * 0.20
    strip = piece("A03_TAPE", 0, int(lab_w / 0.64), rotation=-2.2)
    tp = p(frame, *E["tape"])
    spos = centered(strip, 540, 1452 - (1 - tp) * 46)
    if tp > 0:
        place(c, fade(strip, tp), spos, shadow=SH_TAPE)
    icx, icy = ink_center(strip)
    c.alpha_composite(text_layer(c.size, "PRAZO", F_MARKER, 118, (spos[0] + icx, spos[1] + icy),
                                 color=INK, anchor="mm", stroke_w=3, tracking=4,
                                 hand=True, seed=21, mode="write", optical=True,
                                 progress=d(frame, *E["label"])))

    # anotacao: circulo marca o ponto, seta liga causa e efeito — e TOCA o alvo
    c.alpha_composite(hand_circle(c.size, dcx, dcy - dr * 0.99, 72, 56,
                                  progress=d(frame, *E["circle"]),
                                  passes=2, width=7, color=INK, seed=31, amp=7))
    c.alpha_composite(hand_arrow(c.size, [(566, dcy + dr + 56), (556, 1290),
                                          (542, spos[1] + icy - 118 * 0.70)],
                                 progress=d(frame, *E["arrow"]),
                                 width=8, color=INK, seed=41, head=42))

    return apply_camera(c, 1.0 + 0.030 * p(frame, *E["camera"]), focus=(548, 1120))


# =====================================================================
SCENES = {"M1": (build_M1, M1_STATES, FX_DESK)}


def render(scene, tag="", **kw):
    fn, states, fx = SCENES[scene]
    for st, fr in states.items():
        finish(fn(fr, **kw), **fx).convert("RGB").save(OUTF / f"{scene}{tag}_{st}.png")
        print(f"  {scene}{tag}_{st}.png  (frame {fr})")


def check():
    """END tem que cair DEPOIS do ultimo evento, senao o estado mostra texto pela metade."""
    for sc, (fn, st, fx) in SCENES.items():
        ev = globals()[sc + "_EVENTS"]
        last = max(b for k, (a, b) in ev.items()
                   if k not in ("camera", "hands", "drift", "exit", "line", "boot", "sweep"))
        print(f"  {sc}: ultimo evento {last:3d}  END {st['END']:3d}  "
              f"{'OK' if st['END'] >= last else 'END ANTES DO FIM <<<'}")


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        # estados por quadro: M1_START.png (vertical) e M1_H_START.png (horizontal, MV_CANVAS=H)
        tag = "_H" if V.ORIENT == "H" else ""
        for s in (sys.argv[1:] or list(SCENES)):
            print(f"[{s}{tag}]")
            render(s, tag=tag)
