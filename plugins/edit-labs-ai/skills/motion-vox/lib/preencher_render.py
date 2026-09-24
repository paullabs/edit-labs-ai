#!/usr/bin/env python3
"""
Preenche o render.py (cópia do render_template da motion-vox) a partir do compose.py do projeto.
Rodar da pasta do projeto, depois de `cp render_template.py render.py`:  python3 preencher_render.py
O que ele muda no template:
  - SHOTS saem de compose.CENAS (uma fonte de janelas só) — só as cutaways; a cartela de abertura
    (overlay sobre o rosto) é composta na camada da legenda, que já é RGBA de duração total.
    No template, overlay entra no concat e o ffmpeg derruba o alfa: a cartela sairia com fundo preto.
  - cache por passo de MOTION_FPS: a 12 fps num master de 59,94, cada desenho repete ~5 quadros
    idênticos; o quadro repetido vira hardlink (a imagem não muda, o render fica ~5× mais rápido).
  - EXIT_SLIDE = 0,17 s no fps da fonte (o 13 do template vale para 29,97).
  - cadência lida da fonte (ffprobe), não fixa.
  - o vídeo da fonte pode começar alguns ms depois do áudio (a corte-viral entrega assim): o mux devolve
    esse início, senão o vídeo inteiro fica adiantado em relação à voz.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path.cwd()
p = ROOT / "render.py"
s = p.read_text(encoding="utf-8")
FONTE = str(ROOT / "00_brief" / "fonte.mp4")
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            FONTE], capture_output=True, text=True).stdout)
num, den = (int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                             "stream=r_frame_rate", "-of", "csv=p=0", FONTE],
                                            capture_output=True, text=True).stdout.strip().split("/"))
saida_q = max(4, round(0.167 * num / den))

CLIPE = f'''# ======================================================================= CLIPE
# Tudo daqui para baixo ate a proxima barra e DO CLIPE. O resto do arquivo e motor.

SAIDA = V.ORIENT                           # "V" ou "H" (MV_CANVAS no ambiente)
SRC = ROOT / "00_brief" / "fonte.mp4"      # o clipe vertical aprovado na corte-viral
DUR = {dur:.6f}                           # ffprobe format=duration da fonte
FPS_NUM, FPS_DEN = {num}, {den}             # cadência exata da fonte (ffprobe)

# Legenda: transcript DA LEGENDA (correções + palavrão mascarado), não o de ancoragem
CAP.configurar(
    words_json=ROOT / "00_brief" / "transcript_legenda.json",
    janelas=_janelas_do_json(),   # janelas_legenda.py: livres de cutaway, >= 0,6 s, recuo 0,15 s, sem duvida
    destaque={{}},
    cortes=json.loads((ROOT / "00_brief" / "cortes.json").read_text(encoding="utf-8"))["cortes"],
)

MOTION_FPS = 12                            # régua do criador: desenho a 12 fps
RELOGIO_UNICO = True

# ======================================================================= /CLIPE'''
s = re.sub(r"# =+ CLIPE\n.*?# =+ /CLIPE", lambda m: CLIPE, s, count=1, flags=re.S)

s = s.replace("EXIT_SLIDE = 13          # frames de saida (a 29.97fps ~0,43s)",
              f"EXIT_SLIDE = {saida_q}          # frames de saida = 0,17 s no fps da fonte (o hold conta até aqui)")

EXITS = '''_CUTS = [c for c in C.CENAS if c[4]]
# flash e push alternados (nunca arrastar pro lado); o último fecha a ideia com push
EXIT_KIND = {n: ("push" if (len(_CUTS) - 1 - k) % 2 == 0 else "flash")
             for k, (n, *_r) in enumerate(_CUTS)}'''
s = re.sub(r'EXIT_KIND = \{"M0": "slide".*?\n.*?"M6": "push"\}', lambda m: EXITS, s, count=1, flags=re.S)

SHOTS = '''# nome, funcao, inicio no clipe, fim no clipe, frames24 do plano, cutaway? — janelas vêm do compose
SHOTS = [(n, fn, t0, t1, int(round((t1 - t0) * 24)), True) for n, fn, t0, t1, cut in C.CENAS if cut]
# overlay sobre o rosto (cartela de abertura): composto na camada da legenda, não no concat
OVERLAYS = [(n, fn, t0, t1, int(round((t1 - t0) * 24))) for n, fn, t0, t1, cut in C.CENAS if not cut]'''
s = re.sub(r"# nome, funcao, inicio no clipe.*?\nSHOTS = \[.*?\n\]\n", lambda m: SHOTS + "\n", s, count=1, flags=re.S)

RENDER = '''def render(name, fn, t0, t1, total24, cutaway):
    d = SEQ / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    n = int(round((t1 - t0) * FPS))
    entry = ENTRY_KIND.get(name, "hard")
    k = n - EXIT_SLIDE
    chave, base, salvo = None, None, None
    for i in range(n):
        t = i / FPS                                    # tempo local, em segundos
        # dentro de um beat de vídeo (B-roll, cenas_plano.py) o quadro anda a 24 qps, a cadência do próprio vídeo
        passo_fps = 24.0 if any(a <= t < b for a, b in getattr(C, "INFO", {}).get(name, {}).get("video", [])) else MOTION_FPS
        t_step = math.floor(t * passo_fps) / passo_fps
        f24 = min(total24, t_step * 24.0)              # frame na timeline de 24fps
        passo = int(math.floor(t * MOTION_FPS)) if RELOGIO_UNICO else i // 2
        out = d / f"{i:04d}.png"
        if (f24, passo) != chave:                      # desenho novo só a cada passo de MOTION_FPS
            chave, salvo = (f24, passo), None
            base = V.finish(fn(f24), seed=1000 + passo, **FX_DESK)
        if i >= k:
            sl = V.ease_in((i - k + 1) / EXIT_SLIDE)
            exit_frame(base, fim_de(name), sl).convert("RGBA").save(out)
        elif entry == "flash" and i < ENTRY_FLASH:
            _flash(base, 1.0 - V.ease_in((i + 1) / ENTRY_FLASH)).convert("RGBA").save(out)
        elif salvo is not None:
            os.link(salvo, out)                        # mesmo passo: quadro idêntico
        else:
            base.convert("RGBA").save(out)
            salvo = out
        if i % 60 == 0:
            print(f"  {name} {i:4d}/{n}", flush=True)
    print(f"  {name}: {n} frames -> {d}")
    return n


def render_captions():
    """Legenda MOTION VOX v2 (blocos curtos, centrados, corte seco, nas janelas livres de motion)
    + a cartela de abertura (OVERLAYS) por cima, na mesma camada RGBA de duração total."""
    V.boil_ctx(None)
    d = SEQ / "CAP"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    ph = CAP.check(SHOTS)
    total = int(round(DUR * FPS))
    blank = Image.new("RGBA", (V.W, V.H), (0, 0, 0, 0))
    janelas = [(int(round(x["t"] * FPS)), int(round(x["e"] * FPS)), k) for k, x in enumerate(ph)]
    feitos = {}                                        # chave -> primeiro arquivo salvo (hardlink)
    for i in range(total):
        cur = next((k for a, b, k in janelas if a <= i < b), None)
        t = i / FPS
        ov = None
        for name, fn, t0, t1, tot in OVERLAYS:
            if t0 <= t < t1:
                ov = (name, min(tot, math.floor((t - t0) * MOTION_FPS) / MOTION_FPS * 24.0))
        passo = int(t * V.BOIL_FPS) if cur is not None else 0
        key = (cur, passo, ov)
        out = d / f"{i:04d}.png"
        if key in feitos:
            os.link(feitos[key], out)
            continue
        img = CAP.draw(ph[cur], frame=i * 24.0 / FPS).convert("RGBA") if cur is not None else blank.copy()
        if ov is not None:
            fn = next(o[1] for o in OVERLAYS if o[0] == ov[0])
            img.alpha_composite(fn(ov[1], overlay_only=True))
        img.save(out)
        feitos[key] = out
    cobertos = sum(b - a for a, b, _ in janelas)
    print(f"  CAP: {total} frames, {len(ph)} blocos, {cobertos} frames com legenda "
          f"({100*cobertos/total:.0f}% do clipe), {len(feitos)} imagens distintas")
    return total
'''
s = re.sub(r"def render\(name, fn, t0, t1, total24, cutaway\):.*?\n    return total\n", lambda m: RENDER, s,
           count=1, flags=re.S)
INICIO = """    # O vídeo da fonte pode começar DEPOIS do áudio (21–38 ms na saída da corte-viral);
    # o concat zera isso e adiantaria o vídeo inteiro em relação à voz. Devolve.
    v0 = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=start_time", "-of", "csv=p=0", str(SRC)],
                              capture_output=True, text=True).stdout.strip() or 0)
    if v0 > 1e-4:
        chains.append(f"{saida_v}setpts=PTS+{v0:.6f}/TB[vsync]")
        saida_v = "[vsync]"
"""
alvo = """    else:
        saida_v = "[vbase]"
"""
if "stream=start_time" not in s:
    assert s.count(alvo) == 1, "template mudou: não achei o fim da montagem do vídeo"
    s = s.replace(alvo, alvo + INICIO)
assert "OVERLAYS" in s and "os.link(salvo, out)" in s and f"DUR = {dur:.6f}" in s and "MOTION_FPS = 12" in s
p.write_text(s, encoding="utf-8")
print(f"  render.py preenchido: DUR {dur:.3f}s · {num}/{den} fps · saída {saida_q} quadros")
