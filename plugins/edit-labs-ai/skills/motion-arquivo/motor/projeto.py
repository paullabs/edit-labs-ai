"""
Um projeto da Familia A e uma pasta:

    plano.json        os planos (tipo, inicio, fim, textos, assets, tempos ancorados)
    audio/            a narracao (wav ou o mp4 de origem)
    transcricao.json  palavra a palavra com inicio e fim (ferramentas/transcrever.py)
    assets/           reais/ baixados/ gerados/ prontos/ + FONTES.md (origem, licenca, custo)
    saida/            render, pranchas, laudos

Este modulo transforma o plano numa CENA que o render entende: INICIO, FIM, estado(n), borrao(n).
"""
import json
from pathlib import Path
from familia_a import W, H
from familia_a import c2_letras as le, c3_style as st, c6_motion as mo, c4_filtro as fi, tempo
import planos as PL
import desenho

CINZA = (150.0, 150.0, 150.0)
# Zona segura do Reels (ver familia_a.ZONA e ferramentas/zona_segura.py): o crédito sai do pé da tela (1796, embaixo
# da legenda do Instagram) e vai para o alto à esquerda, logo abaixo do cabeçalho; o rótulo desce para dentro dela.
RODAPE_POS = (96, 300)
ROTULO_POS = (96, 352)


def _matte_atras(img, at):
    """Máscara do que fica NA FRENTE da palavra (palavra atrás do objeto): o claro da imagem (luma entre os limiares),
    só dentro de `regiao` [x0, y0, x1, y1]."""
    import numpy as np, cv2
    lo, hi = at.get("limiar", (70.0, 150.0))
    luma = img[..., 0] * 0.299 + img[..., 1] * 0.587 + img[..., 2] * 0.114
    m = np.clip((luma - lo) / max(1.0, hi - lo), 0, 1).astype(np.float32)
    x0, y0, x1, y1 = at.get("regiao", (0, 0, W, H))
    fora = np.ones_like(m, bool)
    fora[int(y0):int(y1), int(x0):int(x1)] = False
    m[fora] = 0.0
    if at.get("abre", 2):
        k = int(at.get("abre", 2)) * 2 + 1
        m = cv2.dilate(m, np.ones((k, k), np.uint8))
    return cv2.GaussianBlur(m, (0, 0), float(at.get("suave", 1.5)))


def _camada_comum(img, n, p, legenda, ctx=None):
    """Desenhos de tela (telestração), palavras grandes (1 a 3, so onde a palavra carrega a ideia), rotulo, rodape e
    legenda (estes tres so quando o projeto pede: por padrao a cena e feita de figuras, nao de texto).
    Desenhados ANTES do acabamento: levam a mesma scanline e o mesmo RGB split da cena.
    Palavra grande: `y` e `x` (centro da tinta; x padrão o meio), `ate`, `cor`, `sombra`, e `atras` = {limiar, regiao}
    para a palavra passar ATRÁS do objeto claro da filmagem (o carro cruza na frente dela); `atras_ate` = quadro em que
    ela volta para a frente (a fumaça do pouso não engole a palavra)."""
    img = desenho.aplicar(img, n, p, ctx if ctx is not None else PL.Ctx(), "tela")
    for w in p.get("palavras_grandes", []):
        if w["quadro"] <= n < w.get("ate", 10 ** 9):
            corpo = w.get("corpo") or PL._corpo_cabe(w["texto"], 800.0, 150)
            esc = mo.escala_palavra((n - w["quadro"]) / PL.FPS)
            xc, yc = w.get("x", W / 2), w.get("y", 960)
            antes = img.copy() if w.get("atras") and n < w.get("atras_ate", 10 ** 9) else None
            if p["tipo"] in ("foto_pullout", "video_clip", "tela_dividida") and w.get("sombra", True):  # legivel sobre foto
                import numpy as np, cv2
                m, _ = le.mascara(w["texto"], le.SERIFA, corpo * esc, None, 1.0 * esc)
                mw, mh = m.size
                sh = np.zeros((H, W), np.float32)
                x0 = int(round(xc - mw / 2)); y0 = int(round(yc - mh / 2))
                a = np.asarray(m, np.float32) / 255.0
                ya, xa = max(0, y0), max(0, x0); yb, xb = min(H, y0 + mh), min(W, x0 + mw)
                if ya < yb and xa < xb:
                    sh[ya:yb, xa:xb] = a[ya - y0:yb - y0, xa - x0:xb - x0]
                    sh = cv2.GaussianBlur(sh, (0, 0), 10.0)
                    img *= (1 - 0.62 * np.clip(sh * 2.0, 0, 1))[..., None]
            le.escrever(img, w["texto"], centro=(xc, yc), fonte=le.SERIFA, corpo=corpo,
                        cor=tuple(w.get("cor", (238.0, 236.0, 232.0))), contorno=1.0, escala=esc)
            if antes is not None:
                mt = _matte_atras(antes, w["atras"])[..., None]
                img[:] = img * (1 - mt) + antes * mt
    if p.get("rotulo") and p["tipo"] != "cartao_rotulo":           # no cartão, "rotulo" é a etiqueta da foto
        le.escrever(img, p["rotulo"], esquerda=tuple(p.get("rotulo_pos", ROTULO_POS)), fonte=le.GROTESCA, corpo=30,
                    cor=CINZA, peso=le.GROTESCA_PESO, tracking=3.0)
    if p.get("rodape"):
        x, y = p.get("rodape_pos", RODAPE_POS)
        import numpy as np, cv2
        m, _ = le.mascara(p["rodape"], le.GROTESCA, 26, le.GROTESCA_PESO)
        mw, mh = m.size
        a = cv2.GaussianBlur(np.pad(np.asarray(m, np.float32) / 255.0, 12), (0, 0), 5.0)
        x0, y0 = int(round(x)) - 12, int(round(y - mh / 2)) - 12
        h_, w_ = a.shape
        xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w_), min(H, y0 + h_)
        claro = xa < xb and ya < yb and float(img[ya:yb, xa:xb].mean()) > 140.0     # papel: tinta escura, sem sombra
        if xa < xb and ya < yb and not claro:
            img[ya:yb, xa:xb] *= (1 - 0.55 * np.clip(a[ya - y0:yb - y0, xa - x0:xb - x0] * 2, 0, 1))[..., None]
        le.escrever(img, p["rodape"], esquerda=(x, y), fonte=le.GROTESCA, corpo=26,
                    cor=(84.0, 82.0, 86.0) if claro else (214.0, 212.0, 208.0), peso=le.GROTESCA_PESO, alfa=0.92)
    if legenda and not p.get("sem_legenda"):
        for ch in legenda:
            if ch["inicio"] <= n < ch["fim"]:
                _linha_acesa(img, ch["palavras"], n, W / 2, p.get("y_legenda", 1560), 56)
                break


def _linha_acesa(img, palavras, n, xc, yc, corpo):
    """Uma linha centrada; palavra ja dita em branco, a dizer em cinza escuro."""
    texto = " ".join(w["w"] for w in palavras)
    cheio, (ox, oy) = le.mascara(texto, le.GROTESCA, corpo, le.GROTESCA_PESO)
    f = le._fonte(le.GROTESCA, int(round(corpo * le.SS)), le.GROTESCA_PESO)
    xx = xc - cheio.size[0] / 2
    topo = yc - cheio.size[1] / 2 + oy
    pos = 0
    for w in palavras:
        i = texto.index(w["w"], pos); pos = i + len(w["w"])
        m, (mx, my) = le.mascara(w["w"], le.GROTESCA, corpo, le.GROTESCA_PESO)
        cor = (238.0, 236.0, 232.0) if n >= w["quadro"] else (88.0, 88.0, 92.0)
        le.tingir(img, m, xx + ox + f.getlength(texto[:i]) / le.SS - mx, topo - my, cor)


class Cena:
    def __init__(self, pasta):
        self.pasta = Path(pasta).resolve()
        self.plano = json.loads((self.pasta / "plano.json").read_text())
        tempo.configurar(self.plano.get("cadencia", 10))
        fi.configurar(self.plano.get("acabamento", "hedy"))
        st.usar_assets(self.pasta / "assets")
        self.planos = sorted(self.plano["planos"], key=lambda p: p["inicio"])
        self.INICIO = self.planos[0]["inicio"]
        self.FIM = self.planos[-1]["fim"]
        self.audio = self.pasta / self.plano.get("audio", "audio/narracao.wav")
        self._ctx = {}
        for p in self.planos:
            if p["tipo"] not in PL.TIPOS:
                raise ValueError(f"tipo de plano desconhecido: {p['tipo']} (ver referencias/planos.md)")

    def plano_de(self, n):
        for p in self.planos:
            if p["inicio"] <= n < p["fim"]:
                return p
        return self.planos[-1]

    def estado(self, n):
        p = self.plano_de(n)
        ctx = self._ctx.setdefault(id(p), PL.Ctx())
        img = PL.TIPOS[p["tipo"]](n, p, ctx)
        _camada_comum(img, n, p, self.plano.get("legenda"), ctx)
        po = p.get("pouso")                       # galeria: o corte entra desfocado e foca
        if po:
            q = n - p["inicio"]
            dur = po.get("quadros", 9)
            if q < dur:
                img = fi.desfocar(img, po.get("sigma", 9.0) * (1 - q / dur) ** po.get("curva", 1.6))
        return img, 0.0, None

    def borrao(self, n):
        return 0.0

    def grade(self, n):
        """Degrau mostrado no quadro n. Um plano pode pedir trechos a 30 qps ("trechos_30qps": [[a, b]] em
        quadros relativos ao inicio): na galeria, o empurrao rapido na moldura e o pouso dos jornais."""
        p = self.plano_de(n)
        for a, b in p.get("trechos_30qps", []):
            if p["inicio"] + a <= n < p["inicio"] + b:
                return n
        if self.plano.get("fase_por_plano"):           # galeria: cada plano conta os degraus do proprio corte
            return n - ((n - p["inicio"]) % tempo.PASSO)
        return tempo.grade(n)

    def cortes(self):
        return [p["inicio"] for p in self.planos] + [self.FIM]


def carregar(pasta):
    return Cena(pasta)
