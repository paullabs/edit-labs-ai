#!/usr/bin/env python3
"""Move cada borda de segmento que cai em cima da fala para o silêncio mais próximo.

    ajustar_cortes.py <run-dir> [06-candidates.json]

O agente decide o TRECHO; este script acerta a BORDA, pelo áudio — o tempo por
palavra do YouTube não tem precisão para isso (ver checar_cortes.py).

Para cada borda reprovada (energia a menos de 15 dB do nível de fala):
1. envelope RMS (janela 30 ms, passo 10 ms) em ±0,5 s da borda;
2. "silêncio" = trecho ≥ 15 dB abaixo do nível de fala local (p90 em ±1,5 s);
3. escolhe o trecho de silêncio mais próximo da borda original;
4. entrada: corta 0,08 s antes da volta da voz (ou no meio, se o vão for curto);
   saída: corta 0,12 s depois do fim da voz (idem).
Sem silêncio em ±0,5 s, a borda fica como está e é listada para revisão.

Grava o original em 06-candidates.antes-do-ajuste.json e registra cada mudança
em `boundary_adjustments` no próprio clipe.
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from checar_cortes import carregar_wav, energia, rms_db, palavras  # noqa: E402

JAN, PASSO, RAIO, LIMIAR = 0.03, 0.01, 0.5, 15.0
PRE_VOZ, POS_VOZ = 0.08, 0.12


def silencios(x, sr, t):
    fala = float(np.percentile([rms_db(x, sr, u, u + 0.05) for u in np.arange(t - 1.5, t + 1.5, 0.05)], 90))
    ts = np.arange(t - RAIO, t + RAIO, PASSO)
    quieto = [rms_db(x, sr, u - JAN / 2, u + JAN / 2) <= fala - LIMIAR for u in ts]
    runs, ini = [], None
    for u, q in zip(ts, quieto):
        if q and ini is None:
            ini = u
        if not q and ini is not None:
            runs.append((ini, u - PASSO))
            ini = None
    if ini is not None:
        runs.append((ini, ts[-1]))
    return runs


def novo_ponto(x, sr, t, lado):
    runs = silencios(x, sr, t)
    if not runs:
        return None
    # pausa de verdade (≥ 80 ms) ganha de micro-vão entre sílabas, mesmo um pouco mais longe:
    # o vão de 50 ms mais perto pode ficar DEPOIS do "Sim." de outra pessoa.
    longos = [r for r in runs if r[1] - r[0] >= 0.08] or runs
    a, b = min(longos, key=lambda r: 0 if r[0] <= t <= r[1] else min(abs(r[0] - t), abs(r[1] - t)))
    if b - a < PRE_VOZ + POS_VOZ:
        return (a + b) / 2
    return b - PRE_VOZ if lado == "in" else a + POS_VOZ


def ajustar(run: Path, arquivo: str) -> None:
    x, sr = carregar_wav(run / "assets" / "audio-analysis.wav")
    ws = palavras(json.loads((run / "02-transcript.json").read_text()))
    caminho = run / arquivo
    backup = run / arquivo.replace(".json", ".antes-do-ajuste.json")
    if not backup.exists():
        shutil.copy(caminho, backup)
    dados = json.loads(caminho.read_text())
    pendentes = 0
    for c in dados["clips"]:
        log = []
        for s in sorted(c["segments"], key=lambda s: s.get("order", 0)):
            for lado, chave in (("in", "source_start"), ("out", "source_end")):
                t = float(s[chave])
                marca, gap = energia(x, sr, t)
                if marca == "✅":
                    continue
                novo = novo_ponto(x, sr, t, lado)
                if novo is None:
                    pendentes += 1
                    log.append({"order": s.get("order"), "edge": lado, "from": t, "to": None,
                                "note": "sem silêncio em ±0,5 s — revisar à mão"})
                    continue
                antes = {w[2] for w in ws if w[0] < t and w[1] > t}
                s[chave] = round(novo, 3)
                m2, g2 = energia(x, sr, novo)
                log.append({"order": s.get("order"), "edge": lado, "from": round(t, 3), "to": round(novo, 3),
                            "delta_ms": round((novo - t) * 1000), "gap_db_before": round(gap, 1),
                            "gap_db_after": round(g2, 1), "words_at_old_edge": sorted(antes)})
        if log:
            c["boundary_adjustments"] = log
            c["estimated_final_duration_seconds"] = round(
                sum(float(s["source_end"]) - float(s["source_start"]) for s in c["segments"]), 2)
        cid = c["id"]
        for e in log:
            if e["to"] is None:
                print(f"{cid} seg{e['order']} {e['edge']}: ❌ sem silêncio perto — revisar")
            else:
                print(f"{cid} seg{e['order']} {e['edge']}: {e['from']:.2f} → {e['to']:.2f} "
                      f"({e['delta_ms']:+d} ms) · {e['gap_db_before']} → {e['gap_db_after']} dB")
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    print(f"\nbackup: {backup.name} · pendentes: {pendentes}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    ajustar(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "06-candidates.json")
