"""Monta o pacote cego do Revisor Leigo (§07.3). Só o produto: nunca plano, motivo, laudo nem EDL.

  di pacote-leigo F<N> <id>

F2: roteiro.txt (o roteiro montado).
F3: texto.txt (retranscrição do RENDER) + ritmo.txt + juntas/ (par de quadros por emenda, 300 px) + ponta_inicio/fim.
Em laudos/pacote-leigo/F<N>/t<k>/<id>/. O Editor nunca monta pacote à mão (é onde o contexto vaza).
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path

from comum import DIError, achar_projeto, carregar, check, gravar_texto, ler_json, norm_palavra, registrar_checks, tentativa_atual

PROIBIDOS = ("edl", "MARCAS", "decisoes", "motivo", "laudo", "digest", "retakes")


def sobre_pontas(projeto: Path, vid: str, edl: dict, pal: list) -> str:
    """Fato, não motivo: o começo/fim do roteiro é a primeira/última fala que o autor gravou para este vídeo?
    Sem isso o Leigo lê a abertura do próprio autor como "entrei no meio" e reprova um corte que não existe."""
    import yaml as _y
    mapa = (projeto / "02_decupagem" / "MAPA_DO_BRUTO.md")
    bl = None
    if mapa.exists():
        m_ = re.search(r"```yaml\n(.*?)```", mapa.read_text(encoding="utf-8"), re.S)
        if m_:
            bl = next((b for b in (_y.safe_load(m_.group(1)) or {}).get("blocos", []) if b.get("id") == vid), None)
    # O pacote NUNCA diz onde o corte cai dentro do bruto (armadilhas.md, Revisores): "o corte termina antes da
    # última fala gravada" é verdade em quase todo solo (sempre sobra bastidor depois) e planta no Leigo a ideia de
    # que faltou um pedaço — ele reprova por corte o que é buraco de conteúdo. O que ele precisa saber é só que
    # está vendo a peça inteira, não um trecho.
    return (f"duração: {edl['duracao']:.1f} s\ntrechos: {len(edl['segmentos'])}\n"
            "este é o vídeo inteiro, do começo ao fim — não é um trecho de algo maior\n")


def _cenas_do_plano(projeto: Path, vid: str) -> list[dict]:
    from verificar_plano import _col, _num, _tabela
    md = (projeto / "motion" / vid / "00_brief" / "PLANO_MOTION.md").read_text(encoding="utf-8")
    out = []
    for r in _tabela(md, r"B\."):
        t0, t1 = _num(_col(r, "entra")), _num(_col(r, "fim de cena"))
        if t0 is not None:
            out.append({"nome": _col(r, "m#").strip("* "), "t0": t0, "t1": t1, "aparece": _col(r, "o que aparece"),
                        "entra": _col(r, "entra")})
    return sorted(out, key=lambda c: c["t0"])


def _troca_corte(forma, pal) -> dict:
    """Forma que o Leigo lê para cada palavra do transcript do CORTE (F4–F7). O transcript do motion já sai com as
    correções do usuário e do glossário aplicadas (exportar), então aqui só se MASCARA dúvida em aberto
    ([palavra incerta]). Troca por forma escrita — nunca de palavra curta ("a" virava "horas" no vídeo inteiro)."""
    return {norm_palavra(w["w"]): "[palavra incerta]" for i, w in enumerate(pal)
            if forma(i) == "[palavra incerta]" and len(norm_palavra(w["w"])) >= 4}


def _plano_leigo(projeto: Path, vid: str, forma, pal) -> str:
    """F4: o texto do vídeo com ▶ onde cada desenho entra e o que aparece. Sem motivo, registro nem SFX."""
    tr = ler_json(projeto / "motion" / vid / "00_brief" / "transcript_palavras.json") or []
    troca = _troca_corte(forma, pal)
    cenas = _cenas_do_plano(projeto, vid)
    partes, k = [], 0
    for w in tr:
        while k < len(cenas) and w["t"] >= cenas[k]["t0"] - 0.05:
            c = cenas[k]
            ap_ = re.sub(r"\s*\((?:[^()]*\b)?A\d{2}_[A-Z0-9_]+[^()]*\)", "", c["aparece"])    # código de asset do kit
            ap_ = re.sub(r"\bA\d{2}_[A-Z0-9_]+\b", "", ap_)
            ap_ = re.sub(r"\(a confirmar:[^)]*\)", "([palavra incerta])", ap_)               # dúvida em aberto
            partes.append(f"\n▶ [{c['t0']:.1f} s] aparece: {ap_.strip()}\n")
            k += 1
        partes.append(troca.get(norm_palavra(w["w"]), w["w"]))
    return re.sub(r"(\d) ([.,]\d)", r"\1\2", " ".join(partes)).replace(" \n", "\n") + "\n"


def _motion_leigo(projeto: Path, vid: str, fase: str, passo: int, dest: Path, laudo_l1: Path | None, troca: dict) -> None:
    from PIL import Image
    mp = projeto / "motion" / vid
    tr = ler_json(mp / "00_brief" / "transcript_palavras.json") or []
    if fase == "F5":
        frames = mp / "08_images" / "frames"
        nomes = sorted({p.name.split("_")[0] for p in frames.glob("M*_END.png")})
        letras = {n: chr(ord("a") + i) for i, n in enumerate(nomes)}
        cenas = {c["nome"]: c for c in _cenas_do_plano(projeto, vid)} if (mp / "00_brief" / "PLANO_MOTION.md").exists() else {}
        for n, l in letras.items():
            for tag in ("", "_H"):
                for st in (["END"] if passo == 1 else ["START", "MID", "END", "EXIT"]):
                    src = frames / f"{n}{tag}_{st}.png"
                    if src.exists():
                        im = Image.open(src).convert("RGB")
                        im = im.resize((300, int(im.height * 300 / im.width)), Image.LANCZOS)
                        im.save(dest / (f"{l}{'_deitado' if tag else ''}.png" if passo == 1 else f"{l}{'_deitado' if tag else ''}_{st.lower()}.png"))
        if passo == 2:
            linhas = []
            for n, l in letras.items():
                c = cenas.get(n)
                if c:
                    ws = " ".join(troca.get(norm_palavra(w["w"]), w["w"]) for w in tr if c["t0"] - 0.05 <= w["t"] < (c["t1"] or c["t0"] + 3))
                    linhas.append(f"{l}: [{c['t0']:.1f} s] ele diz: {ws}")
            gravar_texto(dest / "falas.txt", "\n".join(linhas) + "\n")
    else:
        pasta = mp / "11_qa" / "tiras"
        prefixo = "piloto_" if fase == "F6" else "master_"
        for d in sorted(pasta.glob(f"{prefixo}*")):
            nome = d.name.replace(prefixo, "").replace("V", "em_pe").replace("H", "deitado")
            src = d / ("passo1_sem_texto.jpg" if passo == 1 else "passo2_com_palavra.jpg")
            if src.exists():
                shutil.copy(src, dest / f"tira_{nome}.jpg")
            if (d / "mudancas.txt").exists():
                shutil.copy(d / "mudancas.txt", dest / f"mudancas_{nome}.txt")
        if passo == 2:
            gravar_texto(dest / "texto.txt", " ".join(troca.get(norm_palavra(w["w"]), w["w"]) for w in tr) + "\n")
            jl = ler_json(mp / "05_motion" / "JANELAS_LEGENDA.json") or {}
            leg = [f"{a:.2f}–{b:.2f} s: " + " ".join(troca.get(norm_palavra(w["w"]), w["w"]) for w in tr if a <= w["t"] < b)
                   for a, b in jl.get("janelas", [])]
            gravar_texto(dest / "legenda.txt", "\n".join(leg or ["(sem legenda nesta tentativa)"]) + "\n")
    if passo == 2 and laudo_l1 and Path(laudo_l1).exists():
        shutil.copy(laudo_l1, dest / "meu_passo1.md")


def _leia_me(dest: Path, fase: str, passo: int) -> None:
    """
    O LEIA-ME é o índice do pacote. Sem ele o Leigo não sabe o que abrir: em host que
    só lhe dá leitura de arquivo (subagente com a ferramenta Read e nada mais) não existe
    listar pasta, e um pacote de imagens sem índice volta como "a pasta está vazia para
    mim".
    """
    itens = sorted(p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file())
    itens = [i for i in itens if i != "LEIA-ME.md"]
    if not itens:
        return
    # a frase sobre quadros só entra quando o pacote TEM imagem: num pacote só de texto (F2) o
    # Leigo leu "o índice fala de imagens e quadros, mas a pasta só tinha o texto"
    tem_imagem = any(i.lower().endswith((".png", ".jpg", ".jpeg")) for i in itens)
    ordem = ("Os quadros estão em ordem: a, b, c… é a ordem em que aparecem no vídeo. "
             "O que termina em `_deitado` é o MESMO quadro na versão horizontal — não é outra cena."
             if tem_imagem else "Aqui só tem texto: não há imagem nenhuma neste pacote.")
    # F2–F4 são pacote de TEXTO (roteiro, retranscrição, plano): "você vê só as imagens" ali
    # mandava o Leigo procurar quadro que não existe
    if fase in ("F2", "F3", "F4"):
        cab = f"# Pacote cego — {fase}"
        passo_txt = ("Leia o texto do que a pessoa fala no vídeo, do começo ao fim. Diga o que o vídeo conta, "
                     "se alguma frase aparece repetida, recomeça ou fica pela metade, e se alguma ideia pula.")
    else:
        cab = f"# Pacote cego — {fase}, passo {passo}"
        passo_txt = {
            1: "Você vê só as imagens, sem nenhuma palavra falada. Diga o que vê, o que puxa seu "
               "olho primeiro, e o que parece fora do lugar ou errado.",
            2: "Agora com as palavras: `falas.txt` (ou `texto.txt`) diz o que a pessoa fala em cada "
               "quadro. Veja se o que está escrito e o que aparece batem com o que é dito.",
        }.get(passo, "")
    gravar_texto(dest / "LEIA-ME.md", "\n".join([
        cab, "",
        "Você é um espectador distraído rolando o feed. Não procure nada fora desta pasta.",
        "", passo_txt, "", ordem, "", "## Arquivos", "",
        *[f"- `{i}`" for i in itens], "",
    ]) + "\n")


def pacote(projeto: Path, fase: str, vid: str, passo: int | None = None, laudo_l1: Path | None = None) -> Path:
    """F2/F3/F4: um pacote. F5/F6/F7: dois passos (`passo=1` só imagem; `passo=2` com as palavras e o L1)."""
    projeto = Path(projeto).resolve()
    t = tentativa_atual(carregar(projeto), fase)
    dest = projeto / "laudos" / "pacote-leigo" / fase / f"t{t}" / vid
    if fase in ("F5", "F6", "F7"):
        dest = dest / f"passo{passo or 1}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    pal = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    dec = ler_json(projeto / "02_decupagem" / vid / "decisoes.json") or {}
    pendentes = {a["palavra"] for a in dec.get("ambiguas", []) if a.get("status") != "confirmada" and isinstance(a.get("palavra"), int)}
    # o que o usuário já confirmou no portão sai da máscara: a pendência pode continuar "a confirmar" no decisoes.json
    # (o Editor não reescreve o arquivo a cada resposta), mas a correção está gravada no manifest e já entrou no
    # texto exportado. Sem isto o Leigo lê um buraco onde o vídeo tem a palavra certa.
    _conf = {norm_palavra(x) for c in (carregar(projeto).get("correcoes") or []) for x in (c.get("ouvido") or "").split()}
    pendentes = {i for i in pendentes if norm_palavra(pal[i]["w"]) not in _conf}
    confirmadas = {a["palavra"]: a.get("provavel") for a in dec.get("ambiguas", []) if a.get("status") == "confirmada"}

    por_forma = {norm_palavra(w["w"]): w["sugerido"] for w in pal if w.get("sugerido")}

    engolidas: set[int] = set()
    for i, w in enumerate(pal[:-1]):
        sug = w.get("sugerido")
        if sug and norm_palavra(sug) == norm_palavra(w["w"]) + norm_palavra(pal[i + 1]["w"]):
            engolidas.add(i + 1)  # a sugestão já inclui a palavra seguinte

    def forma(i: int) -> str:
        """O Leigo julga o corte, não a transcrição: sugestão do glossário entra no lugar; dúvida em aberto vira marca."""
        w = pal[i]
        if i in pendentes:
            return "[palavra incerta]"
        if i in confirmadas:
            return confirmadas[i]
        sug = w.get("sugerido") or por_forma.get(norm_palavra(w["w"]))
        if sug:
            pont = "".join(c for c in w["w"][::-1] if not c.isalnum())[::-1] if not w["w"][-1:].isalnum() else ""
            return sug + pont
        return w["w"]
    if fase == "F2":
        edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
        mant = set(edl["palavras_mantidas"])
        linhas = [" ".join(forma(i) for i in range(s_["palavra_in"], s_["palavra_out"] + 1) if i in mant and i not in engolidas)
                  for s_ in edl["segmentos"]]
        gravar_texto(dest / "sobre.txt", sobre_pontas(projeto, vid, edl, pal))
        gravar_texto(dest / "roteiro.txt", re.sub(r"(\d) ([.,]\d)", r"\1\2", "\n".join(linhas)) + "\n")
    elif fase == "F3":
        pasta = projeto / "03_corte" / vid
        pr = ler_json(pasta / "palavras_render.json")
        if not pr:
            raise DIError(f"{vid}: rode di verificar-corte primeiro (a retranscrição do render é o texto do Leigo)")
        edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
        # o render é retranscrito: a troca vai por forma ouvida (só as que o glossário/Editor já conhecem).
        # A tabela é POR SEGMENTO: a mesma forma pode ser pendência num trecho e decisão fechada noutro
        # ("Markdown" = a ferramenta em dois segmentos e o formato num terceiro); tabela única mascarava os três.
        # Cada palavra entra pela forma ouvida E pela forma provável, porque a retranscrição pode ter escrito
        # qualquer uma das duas. Ver armadilhas.md, Revisão.
        prov = {a["palavra"]: a.get("provavel") for a in dec.get("ambiguas", []) if isinstance(a.get("palavra"), int)}

        def tabela(i0: int, i1: int) -> dict:
            t_ = {}
            for i in range(i0, i1 + 1):
                # `por_forma` entra junto: o glossário marca `sugerido` só em algumas ocorrências da palavra, e o
                # MARCAS já dá as outras como "(glossário)". Sem isto o texto do Leigo dizia "Cloud" onde todo o
                # resto do projeto diz "Claude".
                if (i not in pendentes and i not in confirmadas and not pal[i].get("sugerido")
                        and norm_palavra(pal[i]["w"]) not in por_forma):
                    continue
                f_ = forma(i)
                for chave in (pal[i]["w"], pal[i].get("sugerido"), prov.get(i)):
                    if chave and len(norm_palavra(chave)) >= 4:
                        t_[norm_palavra(chave)] = f_
            return t_
        # ‖ marca onde houve emenda (fato do produto, não motivo): "faltou um pedaço" longe de um ‖ não é corte
        # posição pela palavra: a 1ª palavra mantida de cada segmento, alinhada à retranscrição; sem par, pelo tempo
        from difflib import SequenceMatcher
        R = pr["palavras"]
        mant_ = set(edl["palavras_mantidas"])
        seq = [i for s_ in edl["segmentos"] for i in range(s_["palavra_in"], s_["palavra_out"] + 1) if i in mant_]
        sm = SequenceMatcher(None, [norm_palavra(pal[i]["w"]) for i in seq], [norm_palavra(r["w"]) for r in R], autojunk=False)
        par = {seq[a_ + k]: b_ + k for a_, b_, n_ in sm.get_matching_blocks() for k in range(n_)}
        marca, tabs = set(), [(0, tabela(edl["segmentos"][0]["palavra_in"], edl["segmentos"][0]["palavra_out"]))]
        for s_ in edl["segmentos"][1:]:
            primeira = next((i for i in range(s_["palavra_in"], s_["palavra_out"] + 1) if i in mant_), None)
            k0 = (par[primeira] if primeira in par else
                  next((k for k, r in enumerate(R) if r["t"] >= s_["timeline_in"] - 0.12), len(R)))
            marca.add(k0)
            tabs.append((k0, tabela(s_["palavra_in"], s_["palavra_out"])))
        partes = []
        for k, w in enumerate(R):
            if k in marca:
                partes.append("‖")
            t_ = next((t for k0, t in reversed(tabs) if k >= k0), {})
            partes.append(t_.get(norm_palavra(w["w"]), w["w"]))
        gravar_texto(dest / "texto.txt", re.sub(r"(\d) ([.,]\d)", r"\1\2", " ".join(partes)) + "\n")
        n_j = len(edl["segmentos"]) - 1
        gravar_texto(dest / "sobre.txt", sobre_pontas(projeto, vid, edl, pal) + f"emendas: {n_j}\n")
        if (pasta / "ritmo.txt").exists():
            shutil.copy(pasta / "ritmo.txt", dest / "ritmo.txt")
        v = pasta / "corte_v01_V.mp4" if (pasta / "corte_v01_V.mp4").exists() else pasta / "corte_v01_H.mp4"
        (dest / "juntas").mkdir()
        fps = edl["fps"][0] / edl["fps"][1]
        for k, s in enumerate(edl["segmentos"][1:], 1):
            a, b = max(0, s["timeline_in_f"] - 1), s["timeline_in_f"]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf",
                            f"select='eq(n\\,{a})+eq(n\\,{b})',scale=300:-2,tile=2x1", "-frames:v", "1",
                            str(dest / "juntas" / f"emenda_{k:02d}.jpg")], check=True)
        for nome, n in (("ponta_inicio.jpg", 0), ("ponta_fim.jpg", edl["frames_total"] - 1)):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", f"select='eq(n\\,{n})',scale=300:-2",
                            "-frames:v", "1", str(dest / nome)], check=True)
    elif fase == "F4":
        gravar_texto(dest / "plano.txt", _plano_leigo(projeto, vid, forma, pal))
    elif fase in ("F5", "F6", "F7"):
        _motion_leigo(projeto, vid, fase, passo or 1, dest, laudo_l1, _troca_corte(forma, pal))
    else:
        raise DIError(f"pacote do Leigo para {fase} não existe")
    _leia_me(dest, fase, passo or 1)
    arquivos = [p.name for p in dest.rglob("*") if p.is_file()]
    vaz = [a for a in arquivos if any(x.lower() in a.lower() for x in PROIBIDOS)]
    registrar_checks(projeto, fase, [check(f"V42_pacote_cego_{fase}", not vaz, "BLOCKER", medido=arquivos, video=vid,
                                           esperado="só o produto: nada de EDL, motivo, laudo, digest")])
    return dest


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di pacote-leigo")
    ap.add_argument("fase")
    ap.add_argument("video")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    print(f"✓ {pacote(achar_projeto(a.projeto), a.fase.upper(), a.video)}")
    return 0
