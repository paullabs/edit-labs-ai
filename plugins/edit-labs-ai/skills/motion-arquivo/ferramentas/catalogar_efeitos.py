#!/usr/bin/env python3
"""
"Escuta" a biblioteca de efeitos do usuário por medida e por nome, e grava o que cada som é.

    python3 catalogar_efeitos.py [<pasta_de_sons>] [<saida.json>] [<saida.md>]

<pasta_de_sons> padrão: $EDITLABS_SONS. <saida.json> padrão: $EDITLABS_DATA/motion-arquivo/som_catalogo.json (fora
do plugin; o formato está em motor/kit/som_catalogo.modelo.json).

Para cada arquivo (pula ._* e .DS_Store): duração, trecho ativo, ataque, cauda, quantos golpes, onde está o pico
(começo, meio ou fim: riser), centróide, fração de grave (<200 Hz) e de agudo (>4 kHz), planura espectral (ruído x tom),
tonalidade (autocorrelação no trecho mais forte) e estabilidade do nível. Daí sai a FORMA:
  transiente  clique, toque, obturador (curto, ataque seco)
  tom         sino, bipe, pluck, notificação (tonal)
  impacto     golpe com grave e cauda longa (hit, boom, braam)
  whoosh      ar/ruído que cresce e passa
  riser       cresce até o fim (sobe para o corte)
  laço        muitos golpes regulares (digitar, tique, contador, sequência de câmera)
  ambiente    longo, contínuo (vento, cidade, água, salão)
  textura     o resto
Nada é copiado: o JSON guarda só o caminho relativo, as medidas e as etiquetas do nome.
A escuta de verdade é do usuário; a medida só diz o que cada arquivo parece ser e onde ele cabe.
"""
import _caminho  # noqa: F401
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 22050
HOP = 220            # 10 ms
EXT = (".wav", ".mp3", ".aif", ".aiff", ".flac", ".m4a")

# etiquetas tiradas do nome (bibliotecas comerciais costumam nomear "Autor - Pacote - Descrição")
ETIQUETAS = {
    "clique": r"click|clicking|button|tap\b|tapping|press",
    "mouse": r"mouse",
    "teclado": r"keyboard|typing|qwerty|key\b",
    "toque_tela": r"touch",
    "whoosh": r"whoosh|swoosh|swipe|sweep|gust|air motion|rushing air",
    "reverso": r"revers|backwards|rewind",
    "riser": r"riser|rise\b|rising",
    "impacto": r"impact|hit\b|boom|braam|strike|drop|slam",
    "grave": r"bass|sub\b|low\b|deep|rumbl",
    "papel": r"paper|page|newspaper|flipbook|flip book|crumpl",
    "camera": r"camera|shutter|flash|focus",
    "relogio": r"clock|tick",
    "contador": r"counter|calculation|telemetry|calculator|printing",
    "ui": r"\bui\b|interface|menu|app\b|hud|button|notification|alert",
    "sino": r"bell|chime|ping|pluck|chord|strum|tones?\b|beep|bleep",
    "positivo": r"positive|win|achievement|granted|major|success",
    "negativo": r"error|minor|denied|fail",
    "glitch": r"glitch|cyber|digital|data|robot|servo|sci fi|futuristic|tech",
    "dinheiro": r"cash|coin|banknote|register|jackpot",
    "vidro": r"glass|shatter|clink|bottle",
    "porta": r"door",
    "giz": r"chalk|pencil|pen\b|marker|scribbl|writing",
    "vento": r"wind|blizzard|gust|breeze",
    "agua": r"water|bubbl|liquid|drip|splash|wave|sea\b|ocean",
    "cidade": r"city|street|traffic|plaza|ambience|hall|chatter|crowd",
    "veiculo": r"car\b|driving|engine|airplane|airliner|aircraft|helicopter|drone|plane",
    "fogo": r"fire|explosion|crackl",
    "terra": r"earthquake|tremor|debris|crumbl",
    "metal": r"metal|metallic|sword|scrape",
    "voz": r"laugh|cry|breath|voice|grunt|whistle",
    "arma": r"weapon|gun|rifle|shoot|bullet",
}


def ler(arq):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32)


def medir(x):
    n = len(x) // HOP
    if n < 3:
        return None
    fr = x[: n * HOP].reshape(n, HOP)
    env = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    pk = float(env.max())
    viva = np.nonzero(env > pk - 40)[0]
    a, b = int(viva[0]), int(viva[-1])
    imax = int(np.argmax(env))
    # golpes: subida de >= 9 dB em 30 ms, acima de pico-35, separados por >= 80 ms
    golpes = []
    for i in range(3, n):
        if env[i] > pk - 35 and env[i] - env[i - 3] >= 9 and (not golpes or i - golpes[-1] >= 8):
            golpes.append(i)
    # ataque do primeiro golpe: do começo ativo ao máximo local nos 600 ms seguintes
    j = a + int(np.argmax(env[a:min(n, a + 60)]))
    ataque = (j - a) * 10
    queda = np.nonzero(env[imax:] < env[imax] - 30)[0]
    cauda = int(queda[0]) * 10 if len(queda) else (n - imax) * 10
    # espectro do trecho ativo
    seg = x[a * HOP:(b + 1) * HOP]
    N = 2048
    if len(seg) < N:
        seg = np.pad(seg, (0, N - len(seg)))
    k = (len(seg) - N) // 1024 + 1
    idx = np.arange(N)[None, :] + 1024 * np.arange(k)[:, None]
    S = np.abs(np.fft.rfft(seg[idx] * np.hanning(N), axis=1)) ** 2
    w = S.sum(1)
    S = S[w > w.max() * 1e-3] if (w > w.max() * 1e-3).any() else S
    f = np.fft.rfftfreq(N, 1 / SR)
    e = S.sum(0) + 1e-12
    centroide = float((f * e).sum() / e.sum())
    grave = float(e[f < 200].sum() / e.sum())
    agudo = float(e[f > 4000].sum() / e.sum())
    planura = float(np.mean(np.exp(np.mean(np.log(S + 1e-12), 1)) / (np.mean(S, 1) + 1e-12)))
    # tonalidade: autocorrelação normalizada nos 100 ms mais fortes, período de 1 a 12,5 ms
    c = imax * HOP
    t = x[max(0, c - 1100):c + 1100]
    t = t - t.mean()
    ac = np.correlate(t, t, "full")[len(t) - 1:]
    tonal = float(ac[22:276].max() / (ac[0] + 1e-12)) if len(ac) > 276 else 0.0
    corpo = env[a:b + 1]
    estab = float(corpo[corpo > pk - 30].std()) if (corpo > pk - 30).sum() > 5 else 0.0
    return {"dur": round(len(x) / SR, 2), "dur_ativa": round((b - a + 1) / 100, 2), "pico_db": round(pk, 1),
            "ataque_ms": ataque, "cauda_ms": cauda, "golpes": len(golpes),
            "pico_em": round((imax - a) / max(1, b - a), 2), "centroide_hz": round(centroide), "grave": round(grave, 2),
            "agudo": round(agudo, 3), "planura": round(planura, 3), "tonal": round(tonal, 2), "estab_db": round(estab, 1)}


def forma(m):
    d = m["dur_ativa"]
    if d >= 6 and m["golpes"] / d < 1.2 and m["planura"] >= 0.08:
        return "ambiente"
    if d >= 1.5 and m["golpes"] >= 6:
        return "laço"
    if d >= 1.0 and m["pico_em"] >= 0.7 and m["ataque_ms"] >= 300:
        return "riser"
    if m["ataque_ms"] <= 40 and m["cauda_ms"] >= 600 and m["grave"] >= 0.25:
        return "impacto"
    if d <= 0.45 and m["ataque_ms"] <= 30:
        return "transiente" if m["tonal"] < 0.6 else "tom"
    if m["tonal"] >= 0.6:
        return "tom"
    if m["ataque_ms"] >= 60 and m["planura"] >= 0.08 and d <= 5:
        return "whoosh"
    return "textura"


def etiquetas(nome):
    s = nome.lower()
    return [k for k, rx in ETIQUETAS.items() if re.search(rx, s)]


def main():
    a = sys.argv[1:]
    bib = _caminho.pasta_sons(a[0] if a else None)
    if bib is None or not bib.exists():
        sys.exit("Sem pasta de sons: passe o caminho ou defina EDITLABS_SONS.")
    saida = Path(a[1]) if len(a) > 1 else _caminho.DADOS / "som_catalogo.json"
    md = Path(a[2]) if len(a) > 2 else None
    itens = []
    for arq in sorted(bib.rglob("*")):
        if not arq.is_file() or arq.name.startswith(".") or arq.suffix.lower() not in EXT:
            continue
        try:
            m = medir(ler(arq))
        except subprocess.CalledProcessError:
            m = None
        if m is None:
            continue
        rel = str(arq.relative_to(bib))
        descr = arq.stem.split(" - ")[-1].strip() if " - " in arq.stem else arq.stem
        m.update({"arquivo": rel, "pasta": arq.parent.name, "descricao": descr, "etiquetas": etiquetas(rel)})
        m["forma"] = forma(m)
        itens.append(m)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({"biblioteca": str(bib), "sons": itens}, ensure_ascii=False, indent=1))
    if md:
        L = ["# O que tem na biblioteca de efeitos (medido)", "",
             f"`{bib}` — {len(itens)} arquivos. Forma = o que o som parece ser pela medida; etiquetas = o que o nome diz.",
             "Ataque e cauda em ms; pico_em 0 = começo, 1 = fim (riser); planura alta = ruído (ar, vento), baixa = tom.", ""]
        for pasta in sorted({i["pasta"] for i in itens}, key=str.lower):
            L += [f"## {pasta}", "", "| forma | descrição | dur | ataque | cauda | golpes | centróide | grave | planura | tonal | etiquetas |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
            for i in [i for i in itens if i["pasta"] == pasta]:
                L.append(f"| {i['forma']} | {i['descricao'][:58]} | {i['dur_ativa']}s | {i['ataque_ms']} | {i['cauda_ms']} | "
                         f"{i['golpes']} | {i['centroide_hz']} | {i['grave']} | {i['planura']} | {i['tonal']} | "
                         f"{', '.join(i['etiquetas'])} |")
            L.append("")
        md.write_text("\n".join(L))
    cont = {}
    for i in itens:
        cont[i["forma"]] = cont.get(i["forma"], 0) + 1
    print(f"{len(itens)} sons: {cont}")


if __name__ == "__main__":
    main()
