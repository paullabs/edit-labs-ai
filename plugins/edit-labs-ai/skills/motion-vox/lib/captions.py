#!/usr/bin/env python3
"""
Legenda MOTION VOX v2 — MOTOR. Os dados do clipe entram por `configurar()`.

Padrao MEDIDO frame a frame numa referencia do estilo (talking head vertical, 1492
frames a 30fps, 720x1280) — nao estimado a olho. Os numeros abaixo sao o contrato.

O padrao NAO e um dispositivo de frases longas, alinhadas a esquerda em cascata, com
entrada animada: a medicao da referencia mostra outra coisa. O que foi medido, e nao
estimado:

  eixo horizontal   centro da linha 359,5px de 360  (desvio mediano 1,0px)  -> CENTRADO
  entrada           93% da massa ja no 1o frame; deslocamento vertical 0,7px;
                    variacao de escala 0,0%                                -> CORTE SECO
  duracao do bloco  mediana 10 frames a 30fps = 0,33s  (p25 0,20s / p75 0,53s)
  cadencia          2,45 blocos por segundo
  linhas por bloco  1 na maioria (41 de 54); 2 a 4 quando ha enfase
  corpo             glifo 38px a 720 de largura -> 57px a 1080 -> corpo ~78px
  enfase            2,1x o corpo  (nao 2,4x)
  cor               94% branco, 3,5% verde, 2,4% vermelho  -> A COR E RARA
  vertical          centro do bloco em 0,696H -> y=1337 em 1920
  largura de linha  p90 = 0,48W -> 520px de 1080

As duas regras que mais mudam o resultado:

  1. A FLUIDEZ NAO VEM DE EASING, VEM DE RITMO. Animar a entrada para nao "entrar
     duro" parece natural, mas a referencia nao anima nada. O que da fluidez e a
     CADENCIA — blocos curtos trocando 2,45 vezes por segundo, cada um no lugar exato
     da palavra. Animar a entrada de um bloco que dura 10 frames gasta metade da vida
     dele em transicao, e isso le como arrastado.

  2. A COR NAO E O DISPOSITIVO. Palavra-chave em vermelho em TODA frase mata o acento:
     na referencia 94% das linhas sao brancas. O acento so existe porque e raro.

O que NAO veio da referencia, e por que: a referencia e um talking head sem motion
graphics, entao legenda o video inteiro. Aqui boa parte do clipe e cutaway com
tipografia propria (as palavras-chave da cena) — duas tipografias no mesmo quadro
brigam. Entao a legenda corre nas JANELAS LIVRES e cala sob os motions. Janela menor
que 0,6 s fica de fora: legenda que pisca entre dois motions le como defeito.
"""
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

import voxlab as V

ROOT = Path(__file__).resolve().parent
W, H = V.W, V.H

# --- tipografia, dos numeros medidos ------------------------------------------------
CORPO = 80           # glifo 57px a 1080 / cap-ratio 0,73 do Archivo Black
ENFASE = 168         # 2,1x o corpo, medido dentro dos blocos multilinha
TRACKING = -0.022    # o black ja fecha sozinho; a referencia nao e apertada
LARGURA = 560        # p90 medido = 520px; 560 da folga sem virar linha longa
LEAD = 0.96          # entrelinha por TINTA. <1 = as linhas se tocam, como na referencia
CY = 1330            # centro vertical do bloco (0,693H). Medido: 0,696H
TETO = 1120          # o queixo desce ate y=1102 nos frames medidos: nada acima disto

if V.ORIENT == "H":
    # Horizontal (1920x1080): a referencia medida e vertical; estes valores sao PONTO DE
    # PARTIDA, a conferir no piloto H do projeto. Terco inferior, abaixo do queixo,
    # corpo ~5,7% da altura (a mesma leitura do vertical num monitor), linha de ate 40% W.
    CORPO = 62
    ENFASE = 130     # 2,1x o corpo, igual ao vertical
    LARGURA = 768    # 0,40W
    CY = 886         # 0,82H
    TETO = 760       # 0,70H

BRANCO = (250, 249, 246)
VERMELHO = (201, 72, 80)      # #C94850 da paleta. Raro por design.

# --- cadencia ------------------------------------------------------------------------
ALVO = 0.33          # duracao alvo do bloco (mediana medida)
MAXDUR = 0.62        # acima disso o bloco fica pendurado
MAXPAL = 2           # palavras por bloco (medido ~1,7) — 3 quebrava em 2 linhas com
                     # frequencia (corpo grande), pesado e mal centrado visualmente
PAUSA = 0.34         # silencio que sempre fecha o bloco
# Palavra que começa/termina dentro do recuo de 0,15 s da janela ENTRA (com tolerância de 0,05 a palavra
# some — uma pergunta curta entre duas cutaways perde a 1ª e a última palavra). O bloco é preso na
# borda da janela + recuo, então nunca invade a cutaway vizinha.
BORDA = 0.16
VISIVEL = 0.08       # a palavra precisa caber >= isto dentro da área visível da janela


def _na_janela(x, ja, jb):
    """Mesma regra no bloco e na checagem: a palavra cabe na área visível [ja-BORDA, jb+BORDA]."""
    return x["t"] >= ja - BORDA - 0.10 and x["t"] <= jb + BORDA - VISIVEL and x["e"] <= jb + BORDA + 0.10

# Bloco de uma palavra so existe se ela CARREGA sentido. Na referencia as palavras
# sozinhas sao sempre de conteudo ("converter", "explicacoes"); uma conjuncao sozinha
# no meio da tela le como erro de corte.
_FRACAS = {"e", "o", "a", "os", "as", "um", "uma", "de", "do", "da", "em", "no", "na",
           "que", "se", "com", "para", "pra", "por", "ou", "mas", "ao", "aos", "as",
           "seu", "sua", "te", "me", "lhe", "ja", "já", "so", "só", "e,", "a,"}

# ---------------------------------------------------------------------- CONFIGURACAO
# Estes quatro valores sao DO CLIPE, nao da identidade. O render do projeto chama
# `configurar(...)` antes de qualquer outra coisa. Sem isso `blocos()` levanta erro em
# vez de devolver lista vazia — legenda que some silenciosamente e pior que erro.
#
#   words_json  caminho do transcript palavra-a-palavra (ver lib/transcrever.py)
#   janelas     [(inicio, fim)] em segundos, JA recuadas ~0,15s das bordas dos motions.
#               Janela menor que 0,6 s nao entra: legenda piscando entre dois motions le
#               como defeito.
#   destaque    {(palavra_minuscula, t): {"cor": None|RGB}} — a palavra ganha a serifa
#               italica e aparece SOZINHA no bloco. Na referencia so 6% das linhas tem
#               cor: use `cor` em duas ou tres do clipe inteiro, nao mais.
#   cortes      [t] pontos onde o bloco SEMPRE fecha. Todo corte seco do proprio clipe
#               precisa estar aqui, senao um bloco junta o fim de uma frase com o
#               comeco de outra e le como erro de decupagem.
WORDS_JSON = None
JANELAS = []
DESTAQUE = {}
CORTES = []


def configurar(words_json, janelas, destaque=None, cortes=None):
    global WORDS_JSON, JANELAS, DESTAQUE, CORTES, _WORDS
    WORDS_JSON = Path(words_json)
    JANELAS = list(janelas)
    DESTAQUE = dict(destaque or {})
    CORTES = list(cortes or [])
    _WORDS = None
    return WORDS_JSON


_WORDS = None


def palavras():
    global _WORDS
    if _WORDS is None:
        if WORDS_JSON is None:
            raise RuntimeError(
                "captions.configurar(words_json, janelas, ...) nao foi chamado. "
                "Ver lib/render_template.py e exemplo/exemplo_config.py.")
        _WORDS = json.load(open(WORDS_JSON))
    return _WORDS


def _chave(x):
    return (x["w"].lower(), round(x["t"], 2))


def blocos():
    """
    Agrupa as palavras em blocos curtos. Regras, nesta ordem:
      - palavra de enfase SEMPRE forma bloco sozinha (na referencia a linha grande
        nunca divide espaco com texto de apoio no mesmo tempo);
      - fecha em pontuacao, em pausa > PAUSA, em MAXPAL palavras, ou quando ja passou
        de ALVO segundos;
      - o fim de um bloco e o INICIO do proximo: sem buraco, corte seco, como medido.
    """
    ws = palavras()
    out = []
    for ja, jb in JANELAS:
        n0 = len(out)
        grupo = [x for x in ws if _na_janela(x, ja, jb)]
        if not grupo:
            continue
        cur = []
        for i, x in enumerate(grupo):
            dest = DESTAQUE.get(_chave(x))
            if dest is not None and cur:
                out.append(_fecha(cur, None))
                cur = []
            cur.append(x)
            prox = grupo[i + 1] if i + 1 < len(grupo) else None
            dur = x["e"] - cur[0]["t"]
            gap = (prox["t"] - x["e"]) if prox else 99
            corta = prox is not None and any(x["e"] <= c <= prox["t"] + 0.02
                                             for c in CORTES)
            fim = (dest is not None or prox is None or corta or len(cur) >= MAXPAL
                   or dur >= ALVO or gap > PAUSA
                   or x["w"].rstrip()[-1:] in ".,!?;:"
                   or DESTAQUE.get(_chave(prox)) is not None)
            if fim:
                out.append(_fecha(cur, dest))
                cur = []
        if cur:
            out.append(_fecha(cur, None))
        for x in out[n0:]:                 # o bloco nunca passa da área visível da janela
            x["t"] = max(x["t"], ja - BORDA + 0.01)
            x["e"] = min(x["e"], jb + BORDA - 0.01)
    # junta bloco de uma palavra fraca ao seguinte (nunca a um bloco de enfase, que na
    # referencia sempre aparece sozinho)
    j, i = [], 0
    while i < len(out):
        x = out[i]
        prox = out[i + 1] if i + 1 < len(out) else None
        so_fraca = (len(x["txt"].split()) == 1
                    and x["txt"].strip(".,!?;:").lower() in _FRACAS and not x["enf"])
        if so_fraca and prox and not prox["enf"] and prox["t"] - x["e"] < PAUSA:
            prox["txt"] = x["txt"] + " " + prox["txt"]
            prox["t"] = x["t"]
        elif so_fraca and j and not j[-1]["enf"] and x["t"] - j[-1]["e"] <= PAUSA:   # nunca entre janelas
            j[-1]["txt"] += " " + x["txt"]
            j[-1]["e"] = x["e"]
        else:
            j.append(x)
        i += 1
    out = j
    # encosta cada bloco no seguinte quando nao ha pausa de verdade
    for i in range(len(out) - 1):
        a, b = out[i], out[i + 1]
        if 0 < b["t"] - a["e"] <= PAUSA:
            a["e"] = b["t"]
    # bloco que sobra pendurado numa pausa longa sai de cena em vez de segurar: com
    # mediana de 0,50s, um bloco de 1,0s le como travado.
    for x in out:
        x["e"] = min(x["e"], x["t"] + MAXDUR)
    # nenhum bloco pode invadir o seguinte: com sobreposicao o render escolhe o
    # primeiro que casa e o bloco de baixo entra atrasado — perde a sincronia que e
    # justamente o que faz o corte seco funcionar. Quando o proprio corte (sem pausa
    # nenhuma ate o bloco seguinte) devora quase todo o tempo visivel de um bloco —
    # palavra muito curta emendada direto na proxima — funde em vez de deixar a
    # palavra sumir da tela (o filtro de duracao minima logo abaixo apagaria um bloco
    # so porque o vizinho comecou em cima dele, nao porque a fala nao existiu).
    fundidos, i = [], 0
    while i < len(out):
        cur = out[i]
        nxt = out[i + 1] if i + 1 < len(out) else None
        if nxt is not None:
            nova_e = min(cur["e"], nxt["t"])
            if (nova_e - cur["t"] < 0.08 and not cur["enf"] and not nxt["enf"]
                    and nxt["t"] - cur["e"] <= PAUSA):                         # nunca entre janelas
                nxt["txt"] = cur["txt"] + " " + nxt["txt"]
                nxt["t"] = cur["t"]
                i += 1
                continue
            cur["e"] = nova_e
        fundidos.append(cur)
        i += 1
    return [x for x in fundidos if x["e"] - x["t"] >= 0.08]


def _fecha(cur, dest):
    txt = " ".join(x["w"] for x in cur)
    return dict(t=cur[0]["t"], e=cur[-1]["e"] + 0.10, txt=txt,
                enf=dest is not None, cor=(dest or {}).get("cor"))


# --- desenho -------------------------------------------------------------------------
def _f(enf):
    size = ENFASE if enf else CORPO
    return V.font(V.F_PLAY if enf else V.F_BLACK, size), size


def _trk(size):
    return TRACKING * size          # voxlab conta tracking em px por caractere


def _larg(f, txt, tk):
    return sum(f.getlength(c) + tk for c in txt)


def _linha_layer(txt, f, tk, cor):
    """Uma linha desenhada num layer justo. Devolve (layer recortado na tinta)."""
    w = int(_larg(f, txt, tk)) + 2 * ENFASE
    h = int(f.size * 2.4) + 40
    lay = Image.new("RGBA", (max(8, w), max(8, h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x, y = ENFASE, 20
    for c in txt:
        d.text((x, y), c, font=f, fill=cor + (255,))
        x += f.getlength(c) + tk
    bb = lay.getbbox()
    return lay.crop(bb) if bb else lay


def _linhas(txt, enf):
    """Quebra em linhas que caibam em LARGURA. Palavra sozinha nunca quebra."""
    f, size = _f(enf)
    tk = _trk(size)
    out, cur = [], []
    for p in txt.split():
        if cur and _larg(f, " ".join(cur + [p]), tk) > LARGURA:
            out.append(" ".join(cur))
            cur = [p]
        else:
            cur.append(p)
    if cur:
        out.append(" ".join(cur))
    return out, f, tk


def draw(bloco, progress=1.0, backdrop=None, frame=0.0):
    """
    Uma legenda. `progress` existe so por compatibilidade e e IGNORADO: a referencia
    entra em CORTE SECO — 93% da massa ja no primeiro frame, deslocamento vertical de
    0,7px e variacao de escala de 0,0%, tudo medido. Animar a entrada de um bloco que
    dura 10 frames gastaria metade da vida dele em transicao.

    A tipografia leva boil no preset "print": ruido fino que erode a BORDA da letra,
    como tinta em papel aspero. Nao e o boil dos objetos — aquele tem ruido grosso e
    deformaria a forma da letra.
    """
    linhas, f, tk = _linhas(bloco["txt"], bloco["enf"])
    cor = bloco.get("cor") or BRANCO
    caps = [_linha_layer(l, f, tk, cor) for l in linhas]

    # empilha por TINTA, nao por metrica da fonte: so assim uma entrelinha < 1 fica
    # previsivel em vez de colidir. E a entrelinha apertada e a diagramacao da referencia.
    passos = [caps[i].height * LEAD for i in range(len(caps) - 1)]
    total = sum(passos) + caps[-1].height

    tinta = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y = max(TETO, CY - total / 2)
    for i, c in enumerate(caps):
        tinta.alpha_composite(c, (int((W - c.width) / 2), int(y)))
        if i < len(passos):
            y += passos[i]

    # sombra: a referencia tem uma, e sem ela o branco some no pescoco iluminado
    a = tinta.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(
        lambda v: int(v * 0.62))
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sombra.putalpha(ImageChops.offset(a, 0, 5))

    out = Image.alpha_composite(sombra, tinta)
    return V.boil_full(out, frame, seed=int(frame * 9 / 24) * 131 + 7,
                       **V.BOIL_PRESETS["print"])


def build(*_a, **_kw):
    return blocos()


def check(shots=None):
    if WORDS_JSON is None:
        raise RuntimeError("captions.configurar() nao foi chamado")
    if not JANELAS:
        print("  0 janelas de legenda configuradas (deliberado) — nada a verificar")
        return []
    b = blocos()
    ws = palavras()
    print(f"{len(b)} blocos em {sum(j[1] - j[0] for j in JANELAS):.1f}s de janela livre")
    dur = [x["e"] - x["t"] for x in b]
    dur.sort()
    print(f"  duracao: med {dur[len(dur)//2]:.2f}s  min {dur[0]:.2f}  max {dur[-1]:.2f}")
    print(f"  cadencia: {len(b)/sum(j[1]-j[0] for j in JANELAS):.2f} blocos/s "
          f"(referencia 2,45)")
    npal = [len(x["txt"].split()) for x in b]
    print(f"  palavras/bloco: med {sorted(npal)[len(npal)//2]}  "
          f"media {sum(npal)/len(npal):.2f} (referencia ~1,7)")
    enf = [x for x in b if x["enf"]]
    print(f"  enfase: {len(enf)} ({100*len(enf)/len(b):.0f}%)  "
          f"com cor: {len([x for x in enf if x['cor']])} "
          f"({100*len([x for x in enf if x['cor']])/len(b):.0f}%, referencia 6%)")
    # nenhuma palavra falada dentro de janela pode sumir
    faladas = []
    for ja, jb in JANELAS:
        faladas += [x["w"] for x in ws if _na_janela(x, ja, jb)]
    na_tela = " ".join(x["txt"] for x in b).split()
    assert faladas == na_tela, f"palavra perdida: {set(faladas) ^ set(na_tela)}"
    print(f"  OK: as {len(faladas)} palavras das janelas estao todas na tela")
    # sobreposicao com motion
    if shots:
        for name, _, t0, t1, *_ in shots:
            for x in b:
                assert x["e"] <= t0 + 0.01 or x["t"] >= t1 - 0.01, \
                    f"{x['txt']!r} invade {name}"
        print("  OK: nenhum bloco invade janela de motion")
    return b


if __name__ == "__main__":
    check()
