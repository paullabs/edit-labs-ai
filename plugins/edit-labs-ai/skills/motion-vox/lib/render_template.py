#!/usr/bin/env python3
"""
TEMPLATE de render. Copie para o projeto como `render.py` e preencha o bloco CLIPE.

Duas decisoes que evitam problema, e que nao devem ser mexidas:

1. A timeline e escrita em frames de 24fps, mas o clipe roda na cadencia do fonte. Em
   vez de converter depois (o que gera judder), cada frame de saida e avaliado no seu
   tempo real: `frame24 = (t - inicio_do_plano) * 24`, com fracao. As curvas aceitam
   float.

2. A base de video e por CONCATENACAO (fonte + cutaways, blocos discretos), nao por
   overlay condicional encadeado — overlay com `enable='between(...)'` empilhado por
   varios shots vaza 1 frame de video cru no corte entre duas cutaways (a causa fica
   dentro do overlay filter do ffmpeg e nao e isolavel). Concat elimina a classe
   inteira do problema. So a legenda (RGBA, sempre ativa) continua overlay, por cima
   do resultado do concat. Ver referencias/transicoes.md.
   Audio: SFX_EVENTS define trechos e ganhos por evento. Sem eventos, copia o audio
   sem filtros/reencode; com SFX, preserva a fala e soma a camada (normalize=0).
   SFX_TIMES continua como compatibilidade legada. MD5 igual so vale sem mix/reencode.


    python3 render.py            # renderiza tudo e monta
    python3 render.py --frames   # so os frames
    python3 render.py CAP        # so a passada de legenda, e remonta
    python3 render.py M3 --frames            # uma cena so
    python3 render.py --janela 12.0 28.0     # PILOTO: so as cenas da janela + legenda, recortado

Quadro: MV_CANVAS=V (padrao) ou H escolhe o quadro do PROCESSO inteiro; a fonte e
00_brief/fonte_V.mp4 / fonte_H.mp4 (ou fonte.mp4), a saida vai para 10_sequences/<V|H>/ e
12_master/MASTER_<V|H>_v01.mp4. MV_FIM=flash|sem_flash forca o fim de cena de todas as
cutaways (a variante do piloto quando a regua do kit diz "decidir vendo").
"""
import os, subprocess, sys, shutil, math, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageFilter

import compose as C
import voxlab as V
import captions as CAP

ROOT = Path(__file__).resolve().parent


def _janelas_do_json():
    """Janelas de legenda calculadas por janelas_legenda.py (nunca a mao)."""
    p = ROOT / "05_motion" / "JANELAS_LEGENDA.json"
    return [tuple(x) for x in json.loads(p.read_text(encoding="utf-8"))["janelas"]] if p.exists() else []


# ======================================================================= CLIPE
# Tudo daqui para baixo ate a proxima barra e DO CLIPE. O resto do arquivo e motor.

SAIDA = V.ORIENT                           # "V" ou "H" (MV_CANVAS no ambiente)
SRC = ROOT / "00_brief" / f"fonte_{SAIDA}.mp4"   # o corte aprovado, no quadro desta saida
if not SRC.exists():
    SRC = ROOT / "00_brief" / "fonte.mp4"          # projeto de um quadro so
DUR = 58.058                               # PLACEHOLDER de exemplo: troque pela duracao
#   EXATA da fonte, em segundos (o preencher_render.py ja escreve o valor medido):
#   ffprobe -v error -show_entries format=duration -of csv=p=0 fonte.mp4
FPS_NUM, FPS_DEN = 30000, 1001             # cadencia EXATA da fonte:
#   ffprobe -v error -select_streams v -show_entries stream=r_frame_rate -of csv=p=0 f.mp4

# Legenda. Ver `exemplo/exemplo_config.py` para um caso preenchido.
CAP.configurar(
    words_json=ROOT / "00_brief" / "transcript_palavras.json",
    janelas=_janelas_do_json(),   # janelas_legenda.py: livres de cutaway, >= 0,6 s, recuo 0,15 s, sem duvida
    destaque={},       # {("palavra", t): {"cor": None}} — cor em 2-3 do clipe inteiro
    cortes=[],         # todo corte seco do proprio clipe
)

# O DESENHO segura em degraus de MOTION_FPS — a regua do projeto (a do kit: 12).
MOTION_FPS = 16
# Um relogio so (estudo Porsche §8 #1, adotado pela regua do kit): boil e grao seguem o MOTION_FPS;
# False volta aos dois relogios legados (boil 9 fps, grao on twos).
RELOGIO_UNICO = True

# ======================================================================= /CLIPE

OUT = ROOT / "12_master"
FPS = FPS_NUM / FPS_DEN
FIM = os.environ.get("MV_FIM", "").strip().lower()   # "", "flash" ou "sem_flash"
VERSAO = os.environ.get("MV_VERSAO", "v01").strip() or "v01"   # MV_VERSAO=v02 grava ao lado da v01, sem sobrescrever
# Cada variante do piloto desenha num diretorio proprio. Com um so por saida, "V flash" e
# "V sem_flash" rodando juntos apagam (rmtree) e reescrevem os mesmos PNG: um morre com
# FileNotFoundError e o outro pode muxar quadros da variante errada. O master (sem
# MV_FIM) segue no diretorio de sempre, onde o .done e conferido.
SEQ_BASE = ROOT / "10_sequences" / SAIDA
SEQ = SEQ_BASE / f"_var_{FIM}" if FIM else SEQ_BASE
if RELOGIO_UNICO:
    V.BOIL_FPS = float(MOTION_FPS)

FX_DESK = dict(grain=0.050, vignette=0.06, chroma=1.0, sat=0.92)

# Intensidade do boil. 1.0 e a calibracao medida (tinta 6px, objeto 3px); 0.5 e o
# valor de uso — a 3px o objeto fotografado ja perde circunferencia.
V.BOIL_SCALE = 0.5

# SAIDA DESLIZANTE dos cutaways.
#
# Cortar seco de uma composicao cheia direto para o rosto le como tranco. Segurar mais
# tempo nao resolve: a cena precisa de um GESTO de saida. A mesa inteira e puxada para
# fora do quadro e o video aparece atras dela — um "papel wipe" que usa um objeto que
# ja existe no mundo da cena: a propria mesa.
#
# Por isso os cutaways sao renderizados em RGBA: a area que a mesa liberou fica
# transparente e o `overlay` do ffmpeg deixa o video original passar por baixo.
EXIT_SLIDE = 13          # frames de saida (a 29.97fps ~0,43s)
EXIT_DIR = (-1.06, 0.0)  # para a esquerda, um pouco alem da largura para limpar o quadro

# QUATRO tipos de saida. Repetir a mesma saida em todas as cenas vira tique.
#
#   slide  a mesa e puxada para fora e o video aparece atras
#   wipe   uma folha atravessa a lente; atras dela o video ja esta la
#   push   a camera acelera para dentro e o corte acontece na velocidade
#   flash  desfoca + estoura em branco; o corte cai escondido no pico do flash
#
# "flash" e o que a regua do kit pede para cortar entre inserts (rosto de alguem
# citado, logo de marca, foto de epoca): nada de arrastar pro lado — desfoca, estoura,
# e ja esta na proxima. ENTRY_KIND e o espelho na entrada (comeca desfocado/branco e
# resolve) — so funciona entre duas cutaways controladas por PIL; a entrada vinda do
# talking-head cru fica so com a saida desfocada (o plate nunca e reprocessado).
EXIT_KIND = {"M0": "slide", "M1": "wipe", "M2": "push",
             "M4": "slide", "M5": "wipe", "M6": "push"}
ENTRY_KIND = {}          # {"NOME": "flash"} — default "hard" (corte seco)
PUSH_TO = 1.34           # escala no ultimo frame do push
FLASH_BLUR = 26          # raio maximo do desfoque do flash, em px
ENTRY_FLASH = 22         # frames de entrada quando ENTRY_KIND == "flash"

# O DESENHO segura em degraus de MOTION_FPS (bloco CLIPE) — a vibe Vox de stop-motion,
# nunca smooth de 60fps. So o conteudo (fn(f24)) prende; o flash de saida/entrada e o grao
# continuam fluidos, senao a propria transicao parece travada.


def fim_de(name):
    """Fim de cena desta cutaway, com a variante do piloto (MV_FIM) por cima do EXIT_KIND."""
    k = EXIT_KIND.get(name, "slide")
    if FIM == "flash":
        return "flash"
    if FIM == "sem_flash" and k == "flash":
        return "push"
    return k

# nome, funcao, inicio no clipe, fim no clipe, frames24 do plano, cutaway?
#
# Valores de EXEMPLO (seis cutaways e um overlay) — troque pelas cenas do projeto; o
# preencher_render.py gera esta lista a partir do compose.CENAS. Cada janela e
# escolhida em cima do transcript: comeca antes da palavra-ancora e segura depois dela.
SHOTS = [
    ("M0", C.build_M0,  6.000,  9.000,  72, True),   # objeto na mesa + palavra-chave
    ("M1", C.build_M1, 11.400, 14.600,  77, True),   # relogio + etiqueta
    ("M2", C.build_M2, 18.000, 21.500,  84, True),   # CRT com terminal + varredura
    ("M3", C.build_M3, 27.000, 29.500,  60, False),  # foto sobre o rosto, overlay
    ("M4", C.build_M4, 31.000, 34.200,  77, True),   # dado desenhado a mao
    ("M5", C.build_M5, 42.000, 47.400, 130, True),   # processo: antes -> depois
    ("M6", C.build_M6, 48.200, 51.800,  86, True),   # comparacao: pouco -> muito
]

# Varie o REGISTRO visual entre as cenas. Tres cenas seguidas de "mesa + objeto + fita"
# leem como a mesma cena; alterne mesa de pesquisa, documentario retro, foto montada em
# cartao, dado desenhado a mao, processo e anotacao de campo.


_sheet = {}


def wipe_sheet(size):
    """A folha que atravessa a lente. Papel de algodao frio — material diferente do
    fundo marfim, senao a passagem nao le."""
    if "im" not in _sheet:
        im = Image.open(ROOT / "07_assets" / "cutout" / "A05_CARD.png").convert("RGBA")
        _sheet["im"] = im.resize(size, Image.LANCZOS)
    return _sheet["im"]


def _flash(img, sl):
    """Desfoca + estoura em branco conforme `sl` (0=nitido, 1=flash total). Usado na
    saida (sl crescendo) e na entrada (sl decrescendo) — a mesma curva, dois sentidos."""
    im = img.convert("RGBA")
    r = FLASH_BLUR * sl
    if r > 0.4:
        im = im.filter(ImageFilter.GaussianBlur(r))
    if sl <= 0:
        return im
    white = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.blend(im, white, min(0.97, sl))


def exit_frame(img, kind, sl):
    """Um frame da saida. `sl` vai de 0 a 1 ao longo dos EXIT_SLIDE frames."""
    w, h = img.size
    if kind == "push":
        # camera acelera para dentro; o quadro segue opaco e o corte cai na velocidade
        return C.apply_camera(img, 1.0 + (PUSH_TO - 1.0) * sl, focus=(V.W / 2, V.H * 0.47))
    if kind == "flash":
        # desfoca + estoura em branco; o corte para o proximo shot cai escondido no
        # pico (sl perto de 1) — nao arrasta pro lado, so pisca e ja era
        return _flash(img, sl)

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if kind == "wipe":
        # a folha varre da esquerda para a direita; atras dela nao ha mais cena
        sw = int(w * 0.62)
        x = int(-sw + (w + sw) * sl)
        keep = img.convert("RGBA").copy()
        m = Image.new("L", (w, h), 255)
        ImageDraw.Draw(m).rectangle([0, 0, x + sw, h], fill=0)
        keep.putalpha(ImageChops.multiply(keep.getchannel("A"), m))
        canvas.alpha_composite(keep)
        canvas.alpha_composite(wipe_sheet((sw, h)), (x, 0))
        return canvas

    canvas.alpha_composite(img.convert("RGBA"),
                           (int(EXIT_DIR[0] * w * sl), int(EXIT_DIR[1] * h * sl)))
    return canvas


def render(name, fn, t0, t1, total24, cutaway):
    d = SEQ / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    n = int(round((t1 - t0) * FPS))
    entry = ENTRY_KIND.get(name, "hard")
    k = n - EXIT_SLIDE
    for i in range(n):
        t = i / FPS                                    # tempo local, em segundos
        # o DESENHO segura em degraus de MOTION_FPS (a "vibe" da Vox — stop-motion,
        # nunca smooth de 60fps) — o grao continua em cima disso na sua propria
        # cadencia "on twos", entao a imagem segura mas a textura cintila.
        # dentro de um beat de vídeo (B-roll, cenas_plano.py) o quadro anda a 24 qps, a cadência do próprio vídeo;
        # o resto segue no passo do desenho
        passo_fps = 24.0 if any(a <= t < b for a, b in getattr(C, "INFO", {}).get(name, {}).get("video", [])) else MOTION_FPS
        t_step = math.floor(t * passo_fps) / passo_fps
        f24 = min(total24, t_step * 24.0)              # frame na timeline de 24fps
        if cutaway:
            # grao "on twos": cada campo de grao segura 2 frames. E o mesmo recurso que
            # a identidade ja pede para os props (12fps dentro de 24), cintila como
            # filme, e reduz pela metade o numero de campos novos que o codec precisa
            # engolir.
            passo = int(math.floor(t * MOTION_FPS)) if RELOGIO_UNICO else i // 2
            img = V.finish(fn(f24), seed=1000 + passo, **FX_DESK)
            if i >= k:
                sl = V.ease_in((i - k + 1) / EXIT_SLIDE)
                img = exit_frame(img, fim_de(name), sl)
            elif entry == "flash" and i < ENTRY_FLASH:
                # espelho da saida: comeca no pico do flash (sl=1) e resolve pra
                # nitido (sl=0) — so cabe fora da janela de saida (shots curtos nao
                # tem entrada+saida se espremendo no mesmo frame)
                sl = 1.0 - V.ease_in((i + 1) / ENTRY_FLASH)
                img = _flash(img, sl)
        else:
            img = fn(f24, overlay_only=True)           # plate intocado
        img.convert("RGBA").save(d / f"{i:04d}.png")
        if i % 30 == 0:
            print(f"  {name} {i:4d}/{n}", flush=True)
    print(f"  {name}: {n} frames -> {d}")
    return n


def render_captions():
    """
    Legenda MOTION VOX v2, no padrao medido frame a frame na referencia: blocos curtos,
    CENTRADOS, em CORTE SECO, correndo nas janelas livres de motion.

    Sem extracao de plate: nada de ler o fundo para inverter a cor ou escurecer uma
    tarja. Nenhuma das duas coisas existe no padrao medido — a referencia usa branco
    com sombra projetada, sempre, e resolve a legibilidade pela ALTURA (peito, sobre a
    roupa escura) em vez de por tratamento do fundo.
    """
    # O boil da tipografia e o preset "print", aplicado DENTRO de CAP.draw. O estado
    # global e zerado aqui de proposito: sem isso o texto herdaria o campo congelado do
    # ultimo frame da ultima cena, deformado e parado.
    V.boil_ctx(None)

    d = SEQ / "CAP"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    ph = CAP.check(SHOTS)
    total = int(round(DUR * FPS))
    blank = Image.new("RGBA", (V.W, V.H), (0, 0, 0, 0))
    janelas = [(int(round(x["t"] * FPS)), int(round(x["e"] * FPS)), k)
               for k, x in enumerate(ph)]

    # cada bloco e IDENTICO em todos os seus frames a menos do boil, que anda a 9fps:
    # renderiza uma vez por passo de boil e reaproveita. Sem isso seriam dezenas de blocos
    # x ~13 frames de desenho repetido.
    cache = {}
    for i in range(total):
        cur = next((k for a, b, k in janelas if a <= i < b), None)
        if cur is None:
            blank.save(d / f"{i:04d}.png")
            continue
        passo = int(i / FPS * V.BOIL_FPS)
        key = (cur, passo)
        if key not in cache:
            cache.clear()
            cache[key] = CAP.draw(ph[cur], frame=i * 24.0 / FPS)
        cache[key].save(d / f"{i:04d}.png")
    cobertos = sum(b - a for a, b, _ in janelas)
    print(f"  CAP: {total} frames, {len(ph)} blocos, {cobertos} frames com legenda "
          f"({100*cobertos/total:.0f}% do clipe)")
    return total


# New projects: define SFX_EVENTS in the CLIPE block; see referencias/som-local.md.
# No default here: absence preserves old SFX_TIMES; [] explicitly disables SFX.
SFX_DIR = ROOT / "07_assets" / "sfx"
# pool intercalado (clique de camera / giz) — a ordem alternada ja evita dois do mesmo
# tipo em sequencia, e o SFX_OFFSET de cada clipe (definido no bloco CLIPE) desloca o
# ponto de partida pra dois clipes vizinhos nao abrirem com o mesmo som.
SFX_POOL = ["click1", "chalk1", "click2", "chalk2", "click3", "chalk3", "click4"]


def _sfx_sequence(times, offset=0):
    return [SFX_POOL[(offset + i) % len(SFX_POOL)] for i in range(len(times))]


def mux(shots=None, dst=None):
    shots = SHOTS if shots is None else shots
    OUT.mkdir(exist_ok=True)
    dst = dst or OUT / f"MASTER_{SAIDA}_{VERSAO}.mp4"
    render_dst = dst.with_name(dst.stem + ".rendering" + dst.suffix)
    ins = []
    for name, *_ in shots:
        ins += ["-framerate", f"{FPS_NUM}/{FPS_DEN}", "-i", str(SEQ / name / "%04d.png")]
    # a legenda so entra se existir quadro dela: com 0 janelas configuradas a pasta CAP
    # fica vazia e o ffmpeg morre em "Could find no file or sequence with path" — o
    # render inteiro se perde no ultimo passo, depois de todas as cenas prontas
    tem_cap = (SEQ / "CAP").exists() and any((SEQ / "CAP").glob("*.png"))
    if tem_cap:
        ins += ["-framerate", f"{FPS_NUM}/{FPS_DEN}", "-i", str(SEQ / "CAP" / "%04d.png")]

    # base de video: fonte + cutaways CONCATENADOS, nunca overlay-com-enable encadeado.
    # Overlay com N shots em sequencia (`enable='between(t,t0,t1)'`, eof_action=pass) e
    # FRAGIL: com 5+ shots encadeados o video cru vaza por 1 frame bem no corte entre
    # duas cutaways — um piscar visivel — mesmo com t1 calculado frame-exato. A causa
    # fica dentro do overlay filter do ffmpeg e so aparece com a cadeia completa, nao
    # com 2 shots isolados. Concat elimina a classe inteira do problema: cada trecho e um
    # bloco discreto, sem janela de tempo condicional nenhuma.
    segs, prev_end = [], 0.0
    for k, (name, _, t0, t1, _, _) in enumerate(shots, start=1):
        n = int(round((t1 - t0) * FPS))
        t1x = t0 + n / FPS       # extremo EXATO do numero de frames realmente renderizado
        if t0 > prev_end + 1e-6:
            segs.append(("gap", prev_end, t0))
        segs.append(("shot", k))
        prev_end = max(prev_end, t1x)
    segs.append(("gap", prev_end, DUR))

    chains, labels, gi = [], [], 0
    for seg in segs:
        if seg[0] == "gap":
            _, a, b = seg
            if b - a < 1 / FPS:   # sobreposicao residual entre shots encadeados — pula
                continue
            lab = f"g{gi}"
            gi += 1
            chains.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,"
                          f"format=yuv420p[{lab}]")
        else:
            k = seg[1]
            lab = f"s{k}"
            chains.append(f"[{k}:v]setpts=PTS-STARTPTS,format=yuv420p[{lab}]")
        labels.append(lab)
    chains.append("".join(f"[{l}]" for l in labels) +
                  f"concat=n={len(labels)}:v=1:a=0[vbase]")
    # legenda por ultimo: fica acima de tudo
    if tem_cap:
        kc = len(shots) + 1
        chains.append(f"[vbase][{kc}:v]overlay=0:0:eof_action=pass[vout]")
        saida_v = "[vout]"
    else:
        saida_v = "[vbase]"

    # Explicit cues take priority; an empty new map means no SFX.
    base_idx = len(shots) + (2 if tem_cap else 1)
    if "SFX_EVENTS" in globals():
        from sfx import build_audio
        if globals().get("SFX_TIMES", []):
            raise ValueError("Use SFX_EVENTS or legacy SFX_TIMES, not both")
        events = SFX_EVENTS
        ins_a, audio_filters, audio_map, audio_codec = build_audio(events, base_idx, ROOT, DUR)
        chains.extend(audio_filters)
        effective_map = events
    else:
        # Legacy projects already contain prepared quiet synthetic WAVs.
        times = globals().get("SFX_TIMES", [])
        sfx_names = _sfx_sequence(times, globals().get("SFX_OFFSET", 0))
        ins_a, amix_labels = [], ["0:a:0"]
        effective_map = []
        for j, (nm, t) in enumerate(zip(sfx_names, times)):
            ins_a += ["-i", str(SFX_DIR / f"{nm}.wav")]
            effective_map.append(dict(mode="legacy_prepared", source=str(SFX_DIR / f"{nm}.wav"), timeline_start=t))
            idx = base_idx + j
            ms = max(0, int(round(t * 1000)))
            chains.append(f"[{idx}:a]aformat=channel_layouts=stereo,adelay={ms}|{ms}[sfx{j}]")
            amix_labels.append(f"sfx{j}")
        if times:
            labels = "".join(f"[{label}]" for label in amix_labels)
            chains.append(f"{labels}amix=inputs={len(amix_labels)}:duration=first:"
                          f"dropout_transition=0:normalize=0,alimiter=limit=0.95:level=false:latency=true[aout]")
            audio_map, audio_codec = "[aout]", ["-c:a", "aac", "-b:a", "256k"]
        else:
            audio_map, audio_codec = "0:a:0", ["-c:a", "copy"]

    cmd = (["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC)] +
           ins + ins_a +
           ["-filter_complex", ";".join(chains), "-map", saida_v, "-map", audio_map,
            # CRF 20: o grao de filme e caro de codificar e a plataforma reencoda tudo
            # de novo — a 18 o master fica bem maior e so gasta banda sem ganhar imagem.
            "-c:v", "libx264", "-preset", "slow", "-crf", "20",
            "-pix_fmt", "yuv420p"] + audio_codec +
           ["-movflags", "+faststart", str(render_dst)])
    print("  montando...", flush=True)
    subprocess.run(cmd, check=True)
    render_dst.replace(dst)
    # Publish an effective map on every success, including legacy/no-SFX runs.
    import json
    map_path = ROOT / "06_transitions" / "SFX_MAP.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_temp = map_path.with_suffix('.json.tmp')
    map_temp.write_text(json.dumps(effective_map, ensure_ascii=False, indent=2, default=str))
    map_temp.replace(map_path)
    print(f"  master -> {dst}")
    return dst


def piloto(t0, t1):
    """O mesmo caminho do master (cenas, legenda, audio, mux), so com as cenas que tocam
    a janela, recortado em [t0, t1]. Nao e um preview a parte: prova o que o master fara."""
    ativos = [s_ for s_ in SHOTS if s_[3] > t0 and s_[2] < t1]
    for name, fn, a, b, tot, op in ativos:
        render(name, fn, a, b, tot, op)
    render_captions()
    var = FIM or "regua"
    cheio = OUT / f".piloto_{SAIDA}_{var}_cheio.mp4"
    mux(ativos, cheio)
    dst = SEQ_BASE / f"PILOTO_{SAIDA}_{var}_{int(round(t1 - t0))}s.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{t0:.3f}", "-i", str(cheio),
                    "-t", f"{t1 - t0:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(dst)],
                   check=True)
    cheio.unlink()
    print(f"  piloto -> {dst}")
    return dst


if __name__ == "__main__":
    if "--janela" in sys.argv:
        k = sys.argv.index("--janela")
        piloto(float(sys.argv[k + 1]), float(sys.argv[k + 2]))
        sys.exit(0)
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--mux" not in sys.argv:
        for name, fn, t0, t1, tot, op in SHOTS:
            if not only or name in only:
                render(name, fn, t0, t1, tot, op)
        if not only or "CAP" in only:
            render_captions()
    if "--frames" not in sys.argv:
        mux()
