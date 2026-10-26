"""Renderiza as camadas da garganta (<trabalho>/espirro/garganta/garganta.blend) em patamares de escala, todos pela MESMA
câmera lateral (a câmera do lado direito do corpo, olhando o corte sagital; o rosto fica à direita).

    clpy garganta_render.py base meio peito alto [ouvido]      (preparar.py espirro já chama este passo)

Cada patamar é um recorte do mundo (y, z) com a sua densidade de px/m. O encaixe vem de uma fórmula só (a vista é a 0 da raiz
girada 90°, com a raiz no centro da pele: Px = 0, Py = 0,002):
    u = res_x/2 + (yc - y) * pxm          v = res_y/2 - (z - zc) * pxm
(y e z do atlas, em metros). A 'marcos' do vistas.json confere.
O patamar 'ouvido' é opcional: só roda se existir <trabalho>/espirro/garganta/ouvido.blend (ver ouvido_blender.py)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _caminhos as CM

GAR = CM.TRABALHO / "espirro" / "garganta"
GIRO = CM.MOTOR / "blender_giro.py"
PY = 0.002                                          # y do centro da pele (a raiz que gira)

# nome: (yc, zc, W, H, px/m, camadas)
TODAS = ["pele", "musc", "faringe", "osso", "pulm", "bronq", "via"]
PATAMARES = {
    "base": (0.002, 1.43, 0.30, 0.62, 3720, TODAS),
    "meio": (-0.012, 1.495, 0.30, 0.46, 8000, TODAS),
    "peito": (-0.005, 1.36, 0.30, 0.52, 7000, ["osso", "pulm", "bronq", "via"]),
    "alto": (-0.020, 1.470, 0.16, 0.24, 16000, ["faringe", "osso", "via"]),
}
CAMADAS = {
    "pele": ["^fora_pele__"], "musc": ["^fora_musc__"], "faringe": ["^fora_faringe__"],
    "osso": ["^dentro_osso__"], "pulm": ["^dentro_pulm__"], "bronq": ["^dentro_bronq__"], "via": ["^dentro_via__"],
}
MARCOS = {"narina": [0, -0.113, 1.560], "boca": [0, -0.101, 1.531], "laringe": [0, -0.015, 1.480],
          "traqueia_topo": [0, 0.0, 1.461], "carina": [0, 0.012, 1.355], "piriforme": [0.0135, -0.0125, 1.4815],
          "c7": [0, 0.04, 1.452]}


def cfg(nome):
    yc, zc, W, H, pxm, camadas = PATAMARES[nome]
    res = [round(pxm * W * 1.04), round(pxm * H * 1.04)]
    cxb = PY - yc
    return {
        "modelo": str(GAR / "garganta.blend"), "saida": str(GAR / f"vistas_{nome}"),
        "vistas": 1, "giro_inicial": 90, "res": res, "lente": 0, "elevacao": 0, "ajuste": "caixa",
        "caixa_mundo": [cxb - W / 2, zc - H / 2, cxb + W / 2, zc + H / 2], "enquadrar": ["pele"],
        "motor": "WORKBENCH", "cor_tipo": "MATERIAL", "passes": ["cor", "luz"],
        "camadas": {c: CAMADAS[c] for c in dict.fromkeys(["pele"] + camadas)}, "marcos": MARCOS,   # a pele define o pivô
    }


def cfg_ouvido():
    """o ouvido esquerdo (ouvido_blender.py), de lado, a 28000 px/m"""
    return {
        "modelo": str(GAR / "ouvido.blend"), "saida": str(GAR / "vistas_ouvido"), "vistas": 1, "giro_inicial": -90,
        "res": [2184, 2621], "lente": 0, "elevacao": 0, "ajuste": "caixa", "caixa_mundo": [0.0365, 1.54, 0.1115, 1.63],
        "enquadrar": ["pele"], "motor": "WORKBENCH", "cor_tipo": "MATERIAL", "passes": ["cor", "luz"],
        "camadas": {c: [f"^ouv_{c}__"] for c in ("pele", "osso", "membr", "ossic", "coclea", "ref")},
    }


def mapeia(nome):
    """(y, z) do atlas → px do patamar"""
    yc, zc, W, H, pxm, _ = PATAMARES[nome]
    rx, ry = (round(pxm * W * 1.04), round(pxm * H * 1.04))
    return lambda y, z: (rx / 2 + (yc - y) * pxm, ry / 2 - (z - zc) * pxm)


def renderiza(nome):
    c = cfg_ouvido() if nome == "ouvido" else cfg(nome)
    Path(c["saida"]).mkdir(parents=True, exist_ok=True)
    arq = GAR / f"cfg_{nome}.json"
    arq.write_text(json.dumps(c, indent=1))
    cmd = [CM.BLENDER, "--background", "--factory-startup", "--python", str(GIRO), "--", str(arq)]
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    if nome == "ouvido":
        return
    # a pele fica em todos os patamares: dela sai a forma da cama escura
    v = json.load(open(Path(c["saida"]) / "vistas.json"))
    f = mapeia(nome)
    for k, (y, z) in {"narina": (-0.113, 1.560), "laringe": (-0.015, 1.480), "carina": (0.012, 1.355)}.items():
        print("  marco", k, [round(t) for t in v["marcos"][k]], "fórmula", [round(t) for t in f(y, z)])


if __name__ == "__main__":
    CM.exige(GAR / "garganta.blend", como="clpy preparar.py espirro")
    for nome in sys.argv[1:] or ["base", "meio", "peito", "alto"]:
        renderiza(nome)
