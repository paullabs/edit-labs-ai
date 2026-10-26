"""Som do explicador Vox: banco de efeitos num WAV só, medida EBU R128 e ganho de cada efeito 15-19 dB abaixo
da voz, trilha num nível fixo e prévia do mix a -14 LUFS.

    python som.py banco  <lista.json> <saida_dir>
        lista.json: [{"nome", "arquivo", "ss", "dur", "fi", "fo", "espelho"?, "origem", "licenca"}]
        -> banco.wav (48 kHz estéreo, um som por espaço de 1 s, pico de cada som em -3 dBFS) + banco.json
    python som.py medir  <voz> <banco.wav> <banco.json>
        -> niveis.json ao lado do banco (voz: integrado e momentâneo mediano; efeito: M400, M200, M100)
    python som.py mixar  --plano plano.json --voz voz.wav --banco banco.wav --saida som/ [--trilha t.wav --trilha-queda 21]
        -> som/som.json (cada efeito com quadro de início, trecho do banco e ganho), efeitos_so.wav, previa.wav

O plano traz os sons: [{"id", "efeito" (nome no banco), "quadro" (o GOLPE, a 24 qps), "classe", "acao"}].
Regra do ganho: queda-alvo no M400 por classe (acento 16, ar e papel 18, giz 18,5, longo 19 dB abaixo do momentâneo
mediano da voz), com trava: na janela de 200 ms nenhum efeito fica a menos de 15 dB da voz. Os ganhos valem com a voz
a 0 dB no clipe; se a voz subir G dB na montagem, suba G dB em todos.
Quem roda isto mede, mas não escuta: a escuta é do usuário (fone e celular).
Nunca redistribua sons de bancos cuja licença proíbe (Artlist, Mixkit e afins): o banco fica no projeto do usuário."""
import argparse
import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np

SR, FPS = 48000, 24
ALVO = {"acento": 16.0, "ar": 18.0, "papel": 18.0, "giz": 18.5, "longo": 19.0}
TRAVA_M200 = 15.0
K_FILTRO = "highshelf=f=1681.97:g=3.999:t=q:w=0.7072,highpass=f=38.135:p=2:t=q:w=0.5003"   # ponderação K


def ler(arq, ss=None, t=None):
    cmd = ["ffmpeg", "-v", "error"]
    if ss is not None:
        cmd += ["-ss", f"{ss:.4f}", "-t", f"{t:.4f}"]
    cmd += ["-i", str(arq), "-map", "0:a:0", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).reshape(-1, 2).copy()


def gravar(x, arq):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-c:a",
                    "pcm_s16le", str(arq)], input=np.asarray(x, np.float32).tobytes(), check=True)


def ebur(sinal):
    """sinal estéreo float -> (momentâneo a cada 100 ms, integrado, true peak)"""
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
           "-af", "apad=pad_dur=0.5,ebur128=peak=true:framelog=verbose", "-f", "null", "-"]
    out = subprocess.run(cmd, input=np.asarray(sinal, np.float32).tobytes(), capture_output=True).stderr.decode()
    M = np.array([float(x) for x in re.findall(r"M:\s*(-?[\d.]+)", out)])
    I = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out)[-1])
    TP = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", out)[-1])
    return M, I, TP


def janela(x, w, hop=0.01):
    """loudness ponderado K numa janela de w segundos, a cada hop"""
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af", K_FILTRO, "-f",
           "f32le", "-"]
    k = np.frombuffer(subprocess.run(cmd, input=np.asarray(x, np.float32).tobytes(), capture_output=True,
                                     check=True).stdout, np.float32).reshape(-1, 2).astype(float)
    ms = (k ** 2).sum(1)
    c = np.concatenate([[0], np.cumsum(ms)])
    n, h = int(w * SR), int(hop * SR)
    c = np.concatenate([c, np.full(n, c[-1])])
    idx = np.arange(0, len(ms), h)
    return -0.691 + 10 * np.log10((c[idx + n] - c[idx]) / n + 1e-12)


def limitar(x, teto_db=-1.3):
    """limitador do master só para a prévia: 4x a taxa (pico verdadeiro), ataque 1 ms, soltura 60 ms"""
    cmd = ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-af",
           f"aresample={SR * 4},alimiter=limit={10 ** (teto_db / 20):.4f}:attack=1:release=60:level=disabled,"
           f"aresample={SR}", "-f", "f32le", "-"]
    y = np.frombuffer(subprocess.run(cmd, input=np.asarray(x, np.float32).tobytes(), capture_output=True,
                                     check=True).stdout, np.float32).reshape(-1, 2)
    return y[:len(x)] if len(y) >= len(x) else np.pad(y, ((0, len(x) - len(y)), (0, 0)))


# ------------------------------------------------------------------ banco
def cmd_banco(lista, saida):
    sons = json.loads(Path(lista).read_text(encoding="utf-8"))
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    pos, slots = 0, {}
    for s in sons:
        slots[s["nome"]] = pos
        pos += max(1, math.ceil(s["dur"] + 0.05))            # 1 s por som (os longos ocupam mais)
    banco = np.zeros((SR * (pos + 1), 2), np.float32)
    meta = {}
    for s in sons:
        seg = ler(s["arquivo"], s.get("ss", 0.0), s["dur"])
        if s.get("espelho"):
            seg = seg[:, ::-1].copy()                          # troca esquerda e direita (varrida espelhada)
        n = len(seg)
        fi, fo = int(s.get("fi", 0.004) * SR), int(s.get("fo", 0.06) * SR)
        if fi:
            seg[:fi] *= np.linspace(0, 1, fi)[:, None]
        if fo:
            seg[n - fo:] *= np.linspace(1, 0, fo)[:, None]
        seg *= 10 ** (-3 / 20) / (np.abs(seg).max() + 1e-9)  # pico em -3 dBFS
        h = int(0.01 * SR)
        m = len(seg) // h
        env = np.sqrt(np.mean((seg[:m * h] ** 2).reshape(m, h, 2), axis=(1, 2)) + 1e-12)
        golpe = float(np.argmax(env) * h / SR)                # o golpe = pico do envelope de 10 ms
        k = slots[s["nome"]]
        banco[k * SR:k * SR + n] = seg
        meta[s["nome"]] = {"ini": float(k), "dur": round(n / SR, 4), "golpe": round(golpe, 4),
                           "origem": s.get("origem", Path(s["arquivo"]).name), "licenca": s.get("licenca", "")}
        print(f"{s['nome']:14s} espaço {k:2d} s  dur {n / SR:.2f} s  golpe +{golpe:.3f} s")
    gravar(banco, saida / "banco.wav")
    (saida / "banco.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(saida / "banco.wav")


# ------------------------------------------------------------------ medir
def cmd_medir(voz, banco, banco_json):
    meta_p = Path(banco_json)
    meta = json.loads(meta_p.read_text())
    M, I, TP = ebur(ler(voz))
    fala = M[M > I - 20]                                       # blocos de fala
    voz_m = float(np.median(fala))
    print(f"voz: integrado {I:.1f} LUFS, pico {TP:.1f} dBTP, momentâneo mediano na fala {voz_m:.1f} LUFS")
    res = {}
    for nome, m in meta.items():
        x = ler(banco, m["ini"], m["dur"] + 0.4)
        Mm, _, _ = ebur(x)
        res[nome] = {"M400": float(Mm.max()), "M200": float(janela(x, 0.2).max()), "M100": float(janela(x, 0.1).max())}
        print(f"{nome:14s} M400 {res[nome]['M400']:6.1f}  M200 {res[nome]['M200']:6.1f}")
    out = meta_p.with_name("niveis.json")
    out.write_text(json.dumps({"voz_I": I, "voz_TP": TP, "voz_M_mediano": voz_m, "efeitos": res},
                              ensure_ascii=False, indent=1))
    print(out)


# ------------------------------------------------------------------ mixar
def ganho(n, classe, voz_m):
    g = round(voz_m - ALVO[classe] - n["M400"])
    if voz_m - (n["M200"] + g) < TRAVA_M200:
        g = math.floor(voz_m - TRAVA_M200 - n["M200"])
    return int(g)


def cmd_mixar(a):
    plano = json.loads(Path(a.plano).read_text(encoding="utf-8"))
    banco_p = Path(a.banco)
    B = json.loads(banco_p.with_suffix(".json").read_text())
    N = json.loads(banco_p.with_name("niveis.json").read_text())
    voz_m = N["voz_M_mediano"]
    dur = plano["fim"] / plano.get("fps", FPS)
    voz = ler(a.voz).astype(float)
    nS = int(round(dur * SR))
    voz = np.pad(voz, ((0, max(0, nS - len(voz))), (0, 0)))[:nS]
    bank = ler(banco_p)
    so = np.zeros_like(voz)
    linhas = []
    for e in plano.get("sons", []):
        b, n = B[e["efeito"]], N["efeitos"][e["efeito"]]
        g = ganho(n, e["classe"], voz_m)
        ini_q = round(e["quadro"] - b["golpe"] * FPS, 2)          # o golpe cai no quadro pedido
        seg = bank[int(b["ini"] * SR):int((b["ini"] + b["dur"]) * SR)].astype(float) * 10 ** (g / 20)
        i0 = int(round(ini_q / FPS * SR))
        if i0 < 0 or i0 + len(seg) > nS:
            raise SystemExit(f"{e['id']}: o efeito sai do vídeo (aumente 'fim' no plano ou mova o quadro)")
        so[i0:i0 + len(seg)] += seg
        linhas.append({**e, "som": e["efeito"], "quadro_inicio": ini_q, "t_inicio_s": round(ini_q / FPS, 3),
                       "banco_ini_s": b["ini"], "banco_fim_s": round(b["ini"] + b["dur"], 4), "ganho_db": g,
                       "abaixo_da_voz_M400_db": round(voz_m - (n["M400"] + g), 1),
                       "abaixo_da_voz_M200_db": round(voz_m - (n["M200"] + g), 1), "ligado": True})
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    gravar(so, saida / "efeitos_so.wav")
    tr = np.zeros_like(voz)
    trilha = None
    if a.trilha:                                                # trilha num nível fixo, sem ducker
        x = ler(a.trilha).astype(float)[:nS]
        fim_t = a.trilha_fim if a.trilha_fim else len(x) / SR
        x = x[:int(fim_t * SR)]
        f = int(0.4 * SR)
        x[-f:] *= np.linspace(1, 0, f)[:, None]
        _, It, _ = ebur(x)
        g = (N["voz_I"] - a.trilha_queda) - It
        tr[:len(x)] = x * 10 ** (g / 20)
        gravar(tr, saida / "trilha_no_nivel.wav")
        trilha = {"arquivo": str(a.trilha), "queda_db": a.trilha_queda, "ganho_db": round(g, 1), "fim_s": round(fim_t, 3)}
    mix = voz + so + tr
    _, I, _ = ebur(mix)
    gm = -14.0 - I
    for _ in range(2):                                          # o limitador tira loudness: corrige e repete
        out = limitar(mix * 10 ** (gm / 20))
        _, I2, TP2 = ebur(out)
        gm += -14.0 - I2
    gravar(out, saida / "previa.wav")
    res = {"voz_M_mediano": voz_m, "criterio": {"alvo_M400": ALVO, "trava_M200": TRAVA_M200,
                                                "nota": "ganhos com a voz a 0 dB no clipe"},
           "eventos": linhas, "trilha": trilha, "previa": {"I": round(I2, 1), "TP": round(TP2, 1)},
           "por_segundo": round(len(linhas) / dur, 2)}
    (saida / "som.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    for l in linhas:
        print(f"{l['id']} {l['som']:12s} q{l['quadro']:4d} ganho {l['ganho_db']:+4d} dB  "
              f"{l['abaixo_da_voz_M400_db']:4.1f} dB abaixo da voz (M400)")
    print(f"prévia: {I2:.1f} LUFS, pico {TP2:.1f} dBTP -> {saida / 'previa.wav'}  (escuta pendente)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="modo", required=True)
    b = sub.add_parser("banco"); b.add_argument("lista"); b.add_argument("saida")
    m = sub.add_parser("medir"); m.add_argument("voz"); m.add_argument("banco"); m.add_argument("banco_json")
    x = sub.add_parser("mixar")
    x.add_argument("--plano", required=True); x.add_argument("--voz", required=True)
    x.add_argument("--banco", required=True); x.add_argument("--saida", required=True)
    x.add_argument("--trilha"); x.add_argument("--trilha-queda", type=float, default=21.0)
    x.add_argument("--trilha-fim", type=float, help="s; a trilha sai antes do fecho seco (ex.: antes da última frase)")
    a = ap.parse_args()
    if a.modo == "banco":
        cmd_banco(a.lista, a.saida)
    elif a.modo == "medir":
        cmd_medir(a.voz, a.banco, a.banco_json)
    else:
        cmd_mixar(a)
