"""Render local do explicador Vox: lê o plano.json, monta as camadas no motor de colagem e renderiza a 24 qps com o
desenho a 12 qps (cada desenho dura 2 quadros).

    python previa.py --plano plano.json --pecas pecas/ --saida previa/ [--audio mix.wav] [--sem-legenda]
    python previa.py ... --quadros 0,120,330      -> previa/quadros/qNNNN.png (olhar antes do vídeo inteiro)
    python previa.py --exemplo                    -> o "soco no queixo" do exemplo, sem áudio, em ./previa_exemplo/

O mesmo plano (camada, âncora, chaves) é o que invideo_ops.py traduz para a timeline do invideo.
O motor vem de ${CLAUDE_PLUGIN_ROOT}/motor/colagem (ou da variável EDITLABS_MOTOR)."""
import argparse
import inspect
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SKILL = Path(__file__).resolve().parents[1]
PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(PLUGIN / "motor" / "colagem")))
import motor as M  # noqa: E402

FONTES = PLUGIN / "skills" / "motion-vox" / "fontes"
INTER = "Inter[opsz,wght].ttf"
# o estilo anda a 12 desenhos por segundo num relógio de 24 (o motor vem a 14/28 por padrão)
if hasattr(M, "DESENHOS"):
    M.FPS_SAIDA, M.DESENHOS = 24, 12


def hexa(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def fonte(corpo, peso):
    """Inter variável do plugin no peso pedido"""
    f = ImageFont.truetype(str(FONTES / INTER), int(corpo))
    try:
        vals = []
        for e in f.get_variation_axes():
            nome = e.get("name", b"")
            nome = nome.decode() if isinstance(nome, bytes) else str(nome)
            if "eight" in nome:
                vals.append(max(e["minimum"], min(e["maximum"], peso)))
            elif "ptical" in nome:
                vals.append(max(e["minimum"], min(e["maximum"], 32)))
            else:
                vals.append(e["default"])
        f.set_variation_by_axes(vals)
    except (OSError, AttributeError, KeyError):
        pass
    return f


class Previa:
    def __init__(self, plano, pecas):
        self.plano, self._cache = plano, {}
        self.pecas = [Path(p) for p in (pecas if isinstance(pecas, (list, tuple)) else [pecas])]

    def achar(self, nome):
        """a peça na primeira pasta que a tiver"""
        for d in self.pecas:
            if (d / f"{nome}.png").exists():
                return d / f"{nome}.png"
        return None

    def img(self, nome, reduz=1):
        k = (nome, reduz)
        if k not in self._cache:
            arq = self.achar(nome)
            if arq is None:
                sys.exit(f"peça '{nome}.png' não achada em: {', '.join(map(str, self.pecas))}")
            im = Image.open(arq).convert("RGBA")
            if reduz > 1:
                im = im.resize((im.width // reduz, im.height // reduz), Image.LANCZOS)
            self._cache[k] = im
        return self._cache[k]

    @staticmethod
    def chaves(c):
        out = {}
        for prop, ks in c.get("chaves", {}).items():
            if prop == "op":
                ks = [[q, v / 100.0, cv] for q, v, cv in ks]
            out[prop] = [tuple(k) for k in ks]
        return out

    def camada(self, c):
        tw, th = c["tamanho"]
        if c.get("forma"):                                    # retângulo de cor (ex.: o preto do "apaga")
            im = Image.new("RGBA", (int(tw), int(th)), hexa(c["forma"]["cor"]) + (255,))
        else:
            im = self.img(c["arquivo"], int(c.get("previa_reduz", 1)))
        base = tw / im.width                                  # 1,0 no plano = tamanho planejado
        if c.get("ancora", "centro") == "centro":
            anc = (im.width / 2, im.height / 2)
        else:
            anc = (c["ancora"][0] / base, c["ancora"][1] / base)
        ch = self.chaves(c)
        s = ch.get("s") or [(c["ini"], 1.0, "segura")]
        ch["s"] = [(q, v * base, cv) for q, v, cv in s]
        sombra = tuple(c["sombra"]) if c.get("sombra") else "nenhuma"
        return M.Camada(c["nome"], im, c["ini"], c["fim"], ancora=anc, chaves=ch, boil=c.get("boil"),
                        sombra=sombra, mundo=c.get("mundo", True))

    def fundo(self, fd):
        arq = self.achar(fd["arquivo"]) if fd.get("arquivo") else None
        if arq is not None:
            return Image.open(arq).convert("RGB").resize((M.W, M.H))
        return Image.new("RGB", (M.W, M.H), hexa(fd["cor"]))

    @staticmethod
    def texto(txt, corpo, peso, cor, largura=30, sombra=False, entrelinha=1.28):
        f = fonte(corpo, peso)
        linhas = textwrap.wrap(txt, width=largura) or [txt]
        w = max(f.getlength(l) for l in linhas)
        passo = int(corpo * entrelinha)
        im = Image.new("RGBA", (int(w) + 60, passo * len(linhas) + 50), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i, l in enumerate(linhas):
            d.text((im.width / 2, 25 + i * passo), l, font=f, fill=hexa(cor) + (255,), anchor="ma")
        if sombra:                                           # sombra suave: lê sobre o escuro e sobre a pele
            a = np.asarray(im.getchannel("A"), dtype=np.float32)
            sa = M.cv2.GaussianBlur(np.roll(a, 3, axis=0), (0, 0), 7) * 0.65
            sh = Image.new("RGBA", im.size, (10, 10, 10, 0))
            sh.putalpha(Image.fromarray(np.clip(sa, 0, 255).astype(np.uint8)))
            sh.alpha_composite(im)
            im = sh
        return im

    def montar(self, legenda=True):
        P, camadas = self.plano, []
        for fd in P["fundos"]:                                # fundos de tela cheia, parados na tela
            ch = {"op": [(q, v / 100.0, cv) for q, v, cv in fd.get("op", [[fd["ini"], 100, "segura"]])]}
            L = M.Camada(fd["nome"], self.fundo(fd).convert("RGBA"), fd["ini"], fd["fim"], chaves=ch, mundo=False,
                         degrau=True)
            L.fundo = True                                    # o motor desenha esta camada de tela POR BAIXO do mundo
            camadas.append(L)
        for c in P["camadas"]:
            camadas.append(self.camada(c))
        for t in P.get("titulo", []):                         # título: texto nativo no invideo; aqui, Inter
            im = self.texto(t["texto"], t["corpo"], t.get("peso", 800), t["cor"], largura=40)
            ch = {"x": [(t["ini"], t["x"], "segura")], "y": [(t["ini"], t["y"], "segura")],
                  "op": [(q, v / 100.0, cv) for q, v, cv in t["op"]]}
            camadas.append(M.Camada("TITULO", im, t["ini"], t["fim"], chaves=ch, mundo=False, boil="type"))
        if legenda:                                           # a legenda é a última etapa: só liga no fim
            for i, lg in enumerate(P.get("legenda", [])):
                im = self.texto(lg["texto"], lg.get("corpo", 50), lg.get("peso", 600), lg["cor"],
                                sombra=lg.get("sombra", False))
                ch = {"x": [(lg["ini"], 540, "segura")], "y": [(lg["ini"], lg["y"], "segura")]}
                camadas.append(M.Camada(f"LEGENDA_{i:02d}", im, lg["ini"], lg["fim"], chaves=ch, mundo=False,
                                        degrau=False))
        kw = {"degrau": True} if "degrau" in inspect.signature(M.Camera).parameters else {}
        cam = M.Camera({k: [tuple(x) for x in v] for k, v in P["camera"].items()}, **kw)
        return camadas, cam


def render(plano, pecas, saida, audio=None, quadros=None, legenda=True):
    pv = Previa(plano, pecas)
    camadas, cam = pv.montar(legenda)
    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    fundo = Image.new("RGB", (M.W, M.H), hexa(plano["fundos"][-1]["cor"]))
    params = inspect.signature(M.render).parameters
    kw = {k: v for k, v in {"borrao": False, "filme": False}.items() if k in params}   # sem rastro: a câmera anda em degrau
    if quadros:
        M.render(camadas, cam, fundo, plano["fim"], saida / "quadros", quadros=quadros, **kw)
        print("quadros em", saida / "quadros")
        return
    mudo = saida / "previa_sem_audio.mp4"
    M.render(camadas, cam, fundo, plano["fim"], mudo, **kw)
    if audio:
        final = saida / "previa.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mudo), "-i", str(audio), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart",
                        str(final)], check=True)
        print("prévia em", final)
    else:
        print("prévia (sem áudio) em", mudo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plano", type=Path)
    ap.add_argument("--pecas", type=Path, action="append", help="pasta das peças (pode repetir)")
    ap.add_argument("--saida", type=Path, default=Path("previa"))
    ap.add_argument("--audio", type=Path, help="mix final (voz + trilha + efeitos), ex.: a saída do som.py")
    ap.add_argument("--quadros", help="lista de quadros a 24 qps, ex.: 0,120,330")
    ap.add_argument("--sem-legenda", action="store_true")
    ap.add_argument("--exemplo", action="store_true", help="renderiza o exemplo do soco no queixo")
    a = ap.parse_args()
    if a.exemplo:
        a.plano = a.plano or SKILL / "exemplo" / "plano.json"
        if a.saida == Path("previa"):
            a.saida = Path("previa_exemplo")
        base_dir = a.saida / "pecas_base"                  # fundos, grades e vinheta saem do pecas.py, fora do plugin
        if not (base_dir / "vinheta.png").exists():
            subprocess.run([sys.executable, str(SKILL / "ferramentas" / "pecas.py"), "base", str(base_dir)], check=True)
        a.pecas = (a.pecas or []) + [SKILL / "exemplo" / "pecas", base_dir]
    if not (a.plano and a.pecas):
        ap.error("informe --plano e --pecas (ou use --exemplo)")
    plano = json.loads(a.plano.read_text(encoding="utf-8"))
    qs = [int(x) for x in a.quadros.split(",")] if a.quadros else None
    render(plano, a.pecas, a.saida, audio=a.audio, quadros=qs, legenda=not a.sem_legenda)
