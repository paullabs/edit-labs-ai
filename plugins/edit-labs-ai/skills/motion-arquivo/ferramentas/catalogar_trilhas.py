#!/usr/bin/env python3
"""
Mede as músicas da biblioteca do usuário e prepara a prova de escuta (nada é copiado para a skill).

    python3 catalogar_trilhas.py <saida_dir> <pasta_de_musicas> [<outra pasta> ...] [--clipes N] [--janela 25]

Por faixa: duração, estabilidade (desvio do nível em janelas de 0,5 s), pulso (força da batida), andamento,
centróide, parte de grave (<250 Hz) e de agudo (>4 kHz), e a janela mais estável de `--janela` s.
Saída: <saida_dir>/catalogo.json, catalogo.md e clipes/NN_<nome>.mp3 (todos com o mesmo nível, para comparar de ouvido).
A escuta é do usuário: a medida só ordena o que vale ouvir.
"""
import json, re, subprocess, sys
from pathlib import Path
import numpy as np

SR = 22050
N_FFT, HOP = 1024, 512


def ler(arq):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(pcm, np.float32)


def stft_mag(x):
    n = 1 + (len(x) - N_FFT) // HOP
    idx = np.arange(N_FFT)[None, :] + HOP * np.arange(n)[:, None]
    return np.abs(np.fft.rfft(x[idx] * np.hanning(N_FFT), axis=1))


def medir(arq, janela):
    x = ler(arq)
    dur = len(x) / SR
    fr = int(0.5 * SR)
    n = len(x) // fr
    rms = np.sqrt((x[:n * fr].reshape(n, fr) ** 2).mean(1)) + 1e-9
    db = 20 * np.log10(rms)
    corpo = db[int(n * 0.1): max(int(n * 0.1) + 4, int(n * 0.9))]
    S = stft_mag(x)
    f = np.fft.rfftfreq(N_FFT, 1 / SR)
    e = S.sum(0) + 1e-9
    centroide = float((f * e).sum() / e.sum())
    grave = float(e[f < 250].sum() / e.sum())
    agudo = float(e[f > 4000].sum() / e.sum())
    flux = np.maximum(0, np.diff(np.log1p(S * 10), axis=0)).sum(1)
    suave = np.convolve(flux, np.ones(43) / 43, "same")           # tira a tendência de ~1 s: sobra só o que bate
    flux = flux - suave
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    ac = ac / (ac[0] + 1e-9)
    lag0, lag1 = int(0.30 * SR / HOP), int(1.0 * SR / HOP)
    k = lag0 + int(np.argmax(ac[lag0:lag1]))
    pulso = float(ac[k] - np.median(ac[lag0:lag1]))              # pico sobre o fundo da própria faixa
    bpm = float(60.0 / (k * HOP / SR))
    # janela mais estável (nível) de `janela` s, fora dos 4 s iniciais e dos 8 s finais
    w = int(janela / 0.5)
    ini, fim = 8, max(8, n - w - 16)
    melhor, t0 = 1e9, 8
    for i in range(ini, max(ini + 1, fim)):
        seg = db[i:i + w]
        if len(seg) < w:
            break
        s = float(seg.std())
        if s < melhor:
            melhor, t0 = s, i
    return {"dur": round(dur, 1), "nivel_db": round(float(np.median(db)), 1), "estab_db": round(float(corpo.std()), 2),
            "dinamica_db": round(float(np.percentile(corpo, 90) - np.percentile(corpo, 10)), 1),
            "pulso": round(pulso, 2), "bpm": round(bpm), "centroide_hz": round(centroide), "grave": round(grave, 2),
            "agudo": round(agudo, 3), "janela_ini": round(t0 * 0.5, 1), "janela_estab_db": round(melhor, 2)}


def classe(m):
    if m["pulso"] >= 0.45 and m["centroide_hz"] < 3200:
        return "pulso"
    if m["grave"] > 0.55 or m["centroide_hz"] < 700:
        return "escura"
    if m["estab_db"] <= 2.2 and m["pulso"] < 0.38:
        return "cama"
    return "viva"


def nota_cama(m):
    """Quanto serve de fundo para voz explicativa: estável, sem batida marcada, sem agudo duro."""
    s = 10.0 - 2.2 * m["janela_estab_db"] - 6.0 * max(0.0, m["pulso"] - 0.15) - 40.0 * max(0.0, m["agudo"] - 0.05)
    s -= 2.0 * max(0.0, m["dinamica_db"] - 8.0) / 4.0
    if m["centroide_hz"] > 3000:
        s -= 1.5
    return round(s, 2)


def main():
    a = sys.argv[1:]
    clipes = int(a[a.index("--clipes") + 1]) if "--clipes" in a else 14
    janela = float(a[a.index("--janela") + 1]) if "--janela" in a else 25.0
    pos = [p for i, p in enumerate(a) if not p.startswith("--") and (i == 0 or a[i - 1] not in ("--clipes", "--janela"))]
    saida, pastas = Path(pos[0]), [Path(p) for p in pos[1:]]
    (saida / "clipes").mkdir(parents=True, exist_ok=True)
    itens = []
    vistos = set()
    reuso = saida / "catalogo.json"
    if "--reusar" in a and reuso.exists():
        itens = json.loads(reuso.read_text())
    for pasta in ([] if itens else pastas):
        for arq in sorted(pasta.iterdir()):
            if arq.suffix.lower() not in (".mp3", ".wav", ".m4a", ".aif", ".aiff") or arq.name.startswith("."):
                continue
            chave = re.sub(r"\W+", "", arq.stem.lower())
            if chave in vistos:
                continue
            vistos.add(chave)
            try:
                m = medir(arq, janela)
            except Exception as ex:  # arquivo ilegível não derruba o catálogo
                print("pulou", arq.name, ex)
                continue
            m.update({"arquivo": str(arq), "nome": arq.stem, "pasta": pasta.name, "classe": classe(m), "nota_cama": nota_cama(m)})
            itens.append(m)
            print(f"{m['nota_cama']:6.2f} {m['classe']:6s} {m['nome'][:60]}")
    itens.sort(key=lambda m: -m["nota_cama"])
    # clipes: os melhores "cama" + os melhores das outras classes (para ter o que comparar)
    escolhidos = itens[:clipes - 3]
    escolhidos += [m for m in itens if m["classe"] == "pulso" and m not in escolhidos][:3]
    for k, m in enumerate(escolhidos, 1):
        nome = re.sub(r"[^\w\- ]+", "", m["nome"]).strip().replace(" ", "_")[:60]
        alvo = -24.0
        ganho = alvo - m["nivel_db"]
        out = saida / "clipes" / f"{k:02d}_{m['classe']}_{nome}.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(m["janela_ini"]), "-t", str(janela), "-i", m["arquivo"],
                        "-af", f"volume={ganho:.1f}dB,afade=t=in:d=1.0,afade=t=out:st={janela - 2.0}:d=2.0",
                        "-ac", "2", "-b:a", "160k", str(out)], check=True)
        m["clipe"] = out.name
    (saida / "catalogo.json").write_text(json.dumps(itens, ensure_ascii=False, indent=1))
    L = ["# Catálogo de trilhas (medido)", "",
         f"{len(itens)} faixas. `nota` = serve de fundo para voz explicativa (estável, sem batida, sem agudo duro). "
         "A escuta é do usuário.", "",
         "| nota | classe | faixa | pasta | dur | estab dB | pulso | bpm | centróide Hz | grave | clipe |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for m in itens:
        L.append(f"| {m['nota_cama']} | {m['classe']} | {m['nome']} | {m['pasta']} | {m['dur']:.0f}s | {m['janela_estab_db']} | "
                 f"{m['pulso']} | {m['bpm']} | {m['centroide_hz']} | {m['grave']} | {m.get('clipe', '')} |")
    (saida / "catalogo.md").write_text("\n".join(L) + "\n")
    print(f"\n{len(itens)} faixas, {len(escolhidos)} clipes em {saida / 'clipes'}")


if __name__ == "__main__":
    main()
