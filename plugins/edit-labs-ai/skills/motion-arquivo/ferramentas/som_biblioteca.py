#!/usr/bin/env python3
"""
Recorta, da pasta de efeitos do PRÓPRIO usuário, o trecho útil de cada som que o mixador usa (ataque, pico,
cauda) e grava o mapa em JSON. Não copia nada: o mapa guarda só o caminho relativo, o recorte e a âncora
(referencias/som.md). Sem pasta de sons, o mixador usa os efeitos sintetizados de motor/som.py.

    python3 som_biblioteca.py [<pasta_de_sons>] [<saida.json>] [--escolha <escolha.json>]

<pasta_de_sons>  padrão: $EDITLABS_SONS. Qualquer organização de subpastas serve.
<saida.json>     padrão: $EDITLABS_SONS_MAPA ou $EDITLABS_DATA/motion-arquivo/som_biblioteca.json (fora do plugin).
--escolha        JSON {papel: "caminho/relativo.wav"} para fixar o arquivo de um papel (o resto é achado pelo nome).
                 Modelo: motor/kit/som_escolha.modelo.json.

Cada papel tem um padrão de busca no nome do arquivo (inglês e português, como as bibliotecas costumam nomear).
O script escolhe, entre os que casam, o som mais "limpo" (pico bem acima do próprio fundo). A escuta é do
usuário: rode prova_efeitos.py, ouça e fixe o que preferir em --escolha. Licença: a biblioteca é sua; nada dela
entra no plugin nem no repositório.
"""
import _caminho  # noqa: F401
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 48000
HOP = 240   # 5 ms
EXT = (".wav", ".mp3", ".aif", ".aiff", ".flac", ".m4a")

# papel: modo, quantos recortes, motivo, padrão de busca no caminho (minúsculo) [, opções]
ESCOLHA = {
    "clique": ("clique_duplo", 1, "botão Seguir: o cursor real clica (aperta e solta)", r"mouse.*click|click.*mouse|mouse"),
    "baque": ("unico", 2, "carimbo na mesa: um golpe só, seco", r"door.*(bang|knock|fist)|thud|wood.*(hit|knock)|baque|soco"),
    "obturador": ("unico", 1, "foto de arquivo que entra: obturador antigo e macio", r"shutter|camera.*click|obturador"),
    "papel": ("fortes", 4, "página que vira, jornal que pousa", r"newspaper|page.*(flip|turn)|paper.*flip|jornal|pagina"),
    "folhear": ("inteiro", 1, "calendário e folhas passando rápido", r"flip ?book|flipping pages|folhear"),
    "amassar": ("inteiro", 1, "folha amassada antes do lixo", r"crumpl|amass"),
    "whoosh": ("passagem", 1, "câmera que viaja rápido ou chicote: ar curto, pico na metade do movimento",
               r"short.*(whoosh|swoosh)|(whoosh|swoosh).*short|whoosh"),
    "whoosh_suave": ("passagem", 1, "empurrão lento para dentro da moldura: ar macio, sem ataque",
                     r"(airy|soft|gentle).*(whoosh|swoosh)|(whoosh|swoosh).*(airy|soft)"),
    "reverso": ("passagem", 1, "corte de capítulo: o ar cresce e termina no corte", r"revers|backwards"),
    "tecla": ("fortes", 6, "letra digitada: uma tecla por degrau da grade", r"keyboard|typing|teclado|digita"),
    "tique": ("fortes", 2, "dia que acende, marca que conta: tique de relógio pequeno", r"clock.*tick|tick|relogio"),
    "contador": ("inteiro", 1, "número que rola ou barra que enche: laço do contador digital, cortado na duração",
                 r"counter|telemetry|calculat|contador"),
    "balao": ("unico", 1, "balão de conversa que aparece no celular", r"ui.*click|click.*(single|short)|bubble|balao"),
    "ponto": ("unico", 1, "dado que acende: etiqueta, fatia, o que falta", r"chime|ding|bell|plim"),
    "giz": ("tracos", 4, "traço feito à mão: círculo, sublinhado, X", r"chalk|marker|pencil|scribbl|giz|caneta"),
    "glitch": ("passagem", 1, "barras de cor entre capítulos", r"glitch"),
    "grave": ("unico_longo", 1, "revelação grande, fim de gancho: uma nota grave",
              r"(deep|low|bass).*(note|hit|boom)|sub ?boom|grave"),
    "pop": ("unico", 1, "ícone ou figura que aparece no papel: plink curto e quente (o mixador varia o tom)",
            r"pluck|ping|pop\b", {"max": 0.45}),
    "palavra": ("passagem", 1, "palavra que entra: ar curto e baixo, pico quando a palavra assenta", r"swoosh|swish"),
    "bloco": ("fortes", 4, "bloco da semana que vira: clique mecânico, um por bloco", r"mouse.*button|click.*button|clicking"),
    "impacto": ("unico_longo", 1, "gancho e quebra: golpe metálico com grave que segura (audível no celular)",
                r"impact|metal.*hit|braam|impacto"),
    "riser": ("passagem", 1, "sobe até a quebra (\"Só que...\"): o pico cai na palavra", r"riser|suction|rise\b"),
    "hud": ("inteiro", 1, "linha do HUD que acende", r"hud|window open|ui.*open"),
    "selecao": ("inteiro", 1, "caixa de seleção azul que fecha", r"button.*glitch|glitch.*button|select"),
    "negativo": ("unico", 1, "o que não vale: acorde menor", r"minor|error|denied|negativ", {"max": 0.9}),
    "positivo": ("inteiro", 1, "virou Seguindo: acorde que confirma", r"granted|success|positive|confirm"),
    "dinheiro": ("inteiro", 1, "nota de dinheiro na tela: o contador de cédulas (cortado na duração)",
                 r"banknote|cash|coin|dinheiro"),
    "relogio": ("inteiro", 1, "relógio na tela: tique-taque enquanto ele gira", r"clock|relogio"),
    "jato": ("passagem", 1, "jato de ar comprimido que dispara (o mixador varia o tom)", r"whoosh.*noise|air.*burst|jato",
             {"max": 0.3}),
    "ventilador": ("ambiente", 1, "ventilador girando: zumbido de motor, cortado na duração", r"fan\b|drone.*hover|buzz|motor"),
    # troca de cena: um ar curto diferente a cada corte (regra: toda troca de cena tem som)
    "corte_ar1": ("passagem", 1, "troca de cena: varrida curta", r"sweep"),
    "corte_ar2": ("passagem", 1, "troca de cena: ar que atravessa", r"space.*whoosh|whoosh.*stereo|transition"),
    "corte_ar3": ("passagem", 1, "troca de cena: ar grave", r"low.*whoosh"),
    "corte_ar4": ("passagem", 1, "troca de cena: ar sintético", r"synth.*whoosh|whoosh.*synth"),
    # ambiente por baixo do b-roll em vídeo (trecho estável de 8 s)
    "amb_vento": ("ambiente", 1, "paisagem aberta: vento", r"wind|vento"),
    "amb_cidade": ("ambiente", 1, "cidade e rua: trânsito ao longe", r"city|street|traffic|cidade|rua"),
    "amb_agua": ("ambiente", 1, "água: mar, baía, rio", r"water|stream|sea\b|ocean|river|agua"),
    "amb_caverna": ("ambiente", 1, "interior de pedra: gotas e eco", r"cave|drip|caverna"),
    "amb_industria": ("ambiente", 1, "fábrica, porto, máquinas: drone metálico", r"metallic.*drone|factory|industr"),
}


def arquivos(bib):
    """Todos os áudios da pasta (recursivo), em caminho relativo, sem ._* e .DS_Store."""
    return sorted(p.relative_to(bib).as_posix() for p in Path(bib).rglob("*")
                  if p.is_file() and p.suffix.lower() in EXT and not p.name.startswith("."))


def candidatos(bib, papel, todos=None):
    """Os arquivos cujo caminho casa com o padrão do papel."""
    pad = re.compile(ESCOLHA[papel][3], re.I)
    return [r for r in (todos if todos is not None else arquivos(bib)) if pad.search(r.replace("_", " "))]


def nitidez(arq):
    """Quanto o som se destaca do próprio fundo: pico menos a mediana do envelope (maior = mais limpo)."""
    try:
        db = envelope_db(ler(arq))
    except Exception:
        return -1e9
    return float(db.max() - np.median(db))


def escolher(bib, fixos=None, max_medir=12):
    """{papel: caminho relativo}: o fixo do usuário, senão o candidato mais limpo entre os primeiros `max_medir`."""
    fixos = fixos or {}
    todos = arquivos(bib)
    out = {}
    for papel in ESCOLHA:
        if fixos.get(papel):
            out[papel] = fixos[papel]
            continue
        cs = candidatos(bib, papel, todos)[:max_medir]
        if cs:
            out[papel] = max(cs, key=lambda r: nitidez(Path(bib) / r))
    return out


def ler(arq):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32).reshape(-1, 2)


def envelope_db(x):
    m = x.mean(1)
    n = len(m) // HOP
    return 20 * np.log10(np.sqrt((m[:n * HOP].reshape(-1, HOP) ** 2).mean(1)) + 1e-9)


def ataques(db, faixa=40, subida=9, min_sep=16):
    pk = db.max()
    out = []
    for i in range(3, len(db)):
        if db[i] > pk - faixa and db[i] - db[i - 3] >= subida and (not out or i - out[-1] > min_sep):
            out.append(i)
    return out


def fim_do_evento(db, i, ate, queda=40):
    """Primeiro ponto depois do pico em que o envelope cai `queda` dB abaixo do pico (ou `ate`)."""
    seg = db[i:ate]
    k = int(np.argmax(seg))
    abaixo = np.nonzero(seg[k:] < seg[k] - queda)[0]
    return i + k + (abaixo[0] if len(abaixo) else len(seg) - k)


def recortes(arq, modo, quantos):
    x = ler(arq)
    db = envelope_db(x)
    n = len(db)
    t = lambda i: round(i * HOP / SR, 4)
    ats = ataques(db)
    if modo in ("unico", "unico_longo", "clique_duplo"):
        # o ataque mais forte (o primeiro entre os empatados a 1 dB)
        fortes = sorted(ats, key=lambda i: -db[i:i + 6].max())[:quantos]
        out = []
        for i in fortes:
            prox = [j for j in ats if j > i]
            base = i
            if modo == "clique_duplo":                      # aperta + solta: o segundo ataque, se vier em < 250 ms
                solta = [j for j in prox if j - i <= 50]
                base = solta[0] if solta else i
                prox = [j for j in prox if j > base]
            ate = n if modo == "unico_longo" else (prox[0] if prox else n)
            f = fim_do_evento(db, base, ate, 45 if modo == "unico_longo" else 40)
            out.append({"source_in": t(max(0, i - 1)), "source_out": t(min(n, f + 2)), "anchor_at": t(i),
                        "fade_in": 0.002, "fade_out": 0.02 if modo != "unico_longo" else 0.4})
        return out
    if modo == "fortes":
        cand = []
        for k, i in enumerate(ats):
            ate = ats[k + 1] if k + 1 < len(ats) else n
            f = fim_do_evento(db, i, min(ate, i + 80), 35)
            cand.append((db[i:i + 6].max(), i, f))
        cand.sort(key=lambda c: -c[0])
        out = []
        for _, i, f in cand[:quantos]:
            out.append({"source_in": t(max(0, i - 1)), "source_out": t(min(n, f + 2)), "anchor_at": t(i),
                        "fade_in": 0.002, "fade_out": 0.015})
        return sorted(out, key=lambda r: r["source_in"])
    if modo == "tracos":
        cand = []
        for k, i in enumerate(ats):
            ate = ats[k + 1] if k + 1 < len(ats) else n
            dur = (ate - i) * HOP / SR
            if 0.22 <= dur <= 0.7:
                cand.append((db[i:ate].mean(), i, ate))
        cand.sort(key=lambda c: -c[0])
        return sorted([{"source_in": t(max(0, i - 1)), "source_out": t(a), "anchor_at": t(i), "fade_in": 0.004, "fade_out": 0.05}
                       for _, i, a in cand[:quantos]], key=lambda r: r["source_in"])
    if modo == "passagem":
        # o trecho acima de pico-35 dB, âncora no pico do envelope alisado (30 ms)
        k = np.convolve(db, np.ones(6) / 6, "same")
        p = int(np.argmax(k))
        viva = np.nonzero(k > k[p] - 35)[0]
        return [{"source_in": t(viva[0]), "source_out": t(min(n, viva[-1] + 2)), "anchor_at": t(p),
                 "fade_in": 0.01, "fade_out": 0.05}]
    if modo == "ambiente":
        # o trecho de 8 s mais estável (nível perto da mediana, sem golpe que salta)
        w = int(8.0 * SR / HOP)
        if n <= w:
            return [{"source_in": 0.0, "source_out": t(n), "anchor_at": 0.0, "fade_in": 0.05, "fade_out": 0.08}]
        med = np.median(db)
        melhor, i0 = None, 0
        for i in range(0, n - w, 20):
            j = db[i:i + w]
            nota = j.std() + 0.5 * abs(np.median(j) - med) + 0.2 * max(0.0, j.max() - np.median(j) - 10)
            if melhor is None or nota < melhor:
                melhor, i0 = nota, i
        return [{"source_in": t(i0), "source_out": t(i0 + w), "anchor_at": t(i0), "fade_in": 0.05, "fade_out": 0.08}]
    if modo == "inteiro":
        viva = np.nonzero(db > db.max() - 45)[0]
        return [{"source_in": t(viva[0]), "source_out": t(min(n, viva[-1] + 2)), "anchor_at": t(viva[0]),
                 "fade_in": 0.005, "fade_out": 0.05}]
    raise ValueError(modo)


def main():
    a = sys.argv[1:]
    esc = None
    if "--escolha" in a:
        i = a.index("--escolha")
        esc = json.loads(Path(a[i + 1]).read_text())
        del a[i:i + 2]
    bib = _caminho.pasta_sons(a[0] if a else None)
    if bib is None or not bib.exists():
        sys.exit("Sem pasta de sons: passe o caminho ou defina EDITLABS_SONS. Sem ela, o mixador usa os efeitos "
                 "sintetizados (motor/som.py) e nada precisa ser feito.")
    saida = _caminho.mapa_sons(a[1] if len(a) > 1 else None)
    saida.parent.mkdir(parents=True, exist_ok=True)
    mapa = {"biblioteca": str(bib), "sons": {}}
    for papel, rel in escolher(bib, esc).items():
        modo, quantos, motivo, _, *op = ESCOLHA[papel]
        arq = bib / rel
        if not arq.exists():
            print(f"FALTA {papel}: {rel}")
            continue
        rs = recortes(arq, modo, quantos)
        mx = (op[0] if op else {}).get("max")
        if mx:                                           # corta a cauda longa (o mixador faz o fade de saída)
            for r in rs:
                if r["source_out"] - r["anchor_at"] > mx:
                    r["source_out"] = round(r["anchor_at"] + mx, 4)
                    r["fade_out"] = 0.12
        mapa["sons"][papel] = {"arquivo": rel, "motivo": motivo, "recortes": rs}
        print(f"{papel:13s} {rel}  {len(rs)} recorte(s)")
    faltam = [p for p in ESCOLHA if p not in mapa["sons"]]
    if faltam:
        print("sem arquivo na pasta (vai a reserva sintetizada):", ", ".join(faltam))
    saida.write_text(json.dumps(mapa, indent=1, ensure_ascii=False))
    print("mapa:", saida)


if __name__ == "__main__":
    main()
