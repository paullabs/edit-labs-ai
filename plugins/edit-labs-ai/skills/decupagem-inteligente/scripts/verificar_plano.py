"""V43–V52 e as regras de estilo do usuário (E1–E9) sobre motion/<id>/00_brief/PLANO_MOTION.md.

  di verificar-plano <id>

Lê a tabela B (uma linha por cena), as seções C, F e G, o transcript do corte, as emendas, os silêncios
medidos no corte, avisos e pendências, a régua (config.yaml: motion.*) e o render.py do projeto.
Grava os checks em laudos/F4_V_verificador_t<k>.json (com `video`) e 00_brief/VERIFICACAO_PLANO.md.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from comum import (MOTION_VOX, DIError, achar_projeto, carregar, check, config, gravar_texto, ler_json, norm_palavra,
                   registrar_checks, sem_acento)

# ---------------------------------------------------------------- vocabulário das regras
ABSTRATO = [r"c[ií]rculos?\s+vazi", r"formas?\s+(geom[eé]tric|abstrat)", r"\babstrat", r"\bgen[eé]ric", r"placeholder",
            r"\bbolinhas?\b", r"\bblobs?\b", r"\bgradientes?\b", r"s[ií]mbolo\s+gen", r"[ií]cone\s+(simples|qualquer)"]
CLICHE = [r"l[aâ]mpadas?", r"engrenage", r"foguete", r"c[eé]rebro", r"\bcheck\b", "✓", "✔", r"cifr[aã]o", r"trof[eé]u",
          r"alvo com (flecha|dardo)", r"gr[aá]fico subindo", r"setas? subindo", r"aperto de m[aã]o gen[eé]rico"]
CORPO = r"m[aã]os?|pessoas?|figuras?|persona|personagem|corpo|bra[cç]os?|dedos?|rosto|gente|homem|mulher|foto|silhueta de"
ELEMENTO = (r"logo|foto|objeto|m[aã]os?|print|tela|papel|cart[aã]o|monitor|teclado|rel[oó]gio|documento|livro|celular|"
            r"notebook|computador|seta|mesa|caixa|pilha|figura|pessoa|bandeira|mapa|gr[aá]fico|barra|pizza|carimbo|"
            r"janela|interface|terminal|arquivo|pasta|folha|nota|etiqueta sobre|recorte")
GENTE_NA_FALA = (r"negocia|cliente|equipe|chefe|vendedor|comprador|usu[aá]rios?|amigos?|funcion[aá]rio|pessoas?|gente|"
                 r"algu[eé]m|profissional|programador|desenvolvedor|m[aã]e\b|pai\b|fam[ií]lia")
MOTIVO_VAZIO = [r"d[aá] din[aâ]mica", r"dinamismo", r"deixar din[aâ]mico", r"fica bonito", r"preencher"]
TIPOS_REFERENTE = {"marca", "pessoa", "objeto", "mecanismo", "numero", "titulo"}
FINS = {"flash", "push", "slide", "wipe", "volta"}
PARADAS = set("de do da dos das o a os as um uma uns umas que e em no na nos nas com por para pra pro se ao aos "
              "mais muito isso esse essa este esta aqui ali la voce ele ela eles elas nos eu tu seu sua seus suas "
              "como quando onde porque mas ou ja so tambem entao agora depois antes ate sobre entre pelo pela sao "
              "foi ser ter tem vai vou esta estao acabou fazer faz pode pode".split())
SIGLAS_COMUNS = {"ia", "ai", "eua", "usa", "tv", "pdf", "url", "ok", "cpf", "cnpj", "ong", "rh", "ti", "ux", "ui", "faq"}
MARCAS_CONHECIDAS = {"claude", "anthropic", "antropic", "fable", "github", "gemini", "google", "notebooklm", "tiktok", "reels",
                     "youtube", "instagram", "cursor", "codex", "antigravity", "glm", "kimi", "openai", "chatgpt", "gpt",
                     "whatsapp", "facebook", "apple", "microsoft", "meta", "tesla", "netflix", "spotify", "amazon"}


def _num(s: str) -> float | None:
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*s\b", s)
    return float(m.group(1).replace(",", ".")) if m else None


def _tabela(md: str, titulo_re: str) -> list[dict]:
    """Linhas da primeira tabela depois do cabeçalho de seção que casa `titulo_re`."""
    m = re.search(rf"^##\s*{titulo_re}.*?$", md, re.M | re.I)
    if not m:
        return []
    resto = md[m.end():]
    fim = re.search(r"^##\s", resto, re.M)
    bloco = resto[:fim.start()] if fim else resto
    linhas = [l.strip() for l in bloco.splitlines() if l.strip().startswith("|")]
    if len(linhas) < 2:
        return []
    cab = [sem_acento(c.strip().lower()) for c in linhas[0].strip("|").split("|")]
    out = []
    for l in linhas[2:]:
        cel = [c.strip() for c in l.strip("|").split("|")]
        if len(cel) < len(cab):
            cel += [""] * (len(cab) - len(cel))
        out.append(dict(zip(cab, cel)))
    return out


def _col(row: dict, *nomes: str) -> str:
    for n in nomes:
        for k, v in row.items():
            if k.startswith(n):
                return v
    return ""


def _registros() -> set[str]:
    txt = (MOTION_VOX / "referencias" / "registros.md").read_text(encoding="utf-8")
    return {sem_acento(m.group(1).strip().lower()) for m in re.finditer(r"^\|\s*\*\*(.+?)\*\*", txt, re.M)}


def _refs_ok(ref: str) -> bool:
    txt = (MOTION_VOX / "referencias" / "REFERENCIAS-VISUAIS.md").read_text(encoding="utf-8")
    toks = re.findall(r"bf\d+|p\.\s?\d+|IMG_\d+|clipe \d+ M\d+|odesignerjoao|Storyboard", ref, re.I)
    return any(re.search(re.escape(t.replace(" ", "")), txt.replace(" ", ""), re.I) for t in toks)


def _marcas_na_janela(pal: list[dict], t0: float, t1: float, extra: set[str], duvidosas: set[str] = frozenset()) -> list[str]:
    out = []
    for w in pal:
        if w["e"] <= t0 or w["t"] >= t1:
            continue
        raw = w["w"].strip(".,;:!?…\"'()")
        n = norm_palavra(raw)
        misto = bool(re.search(r"[a-z][A-Z]", raw))           # GitHub, NotebookLM, TikTok
        sigla = len(raw) >= 2 and raw.isupper() and raw.isalpha()   # GLM, KIMI
        if n in duvidosas:
            continue   # palavra em dúvida do ASR ("Facebook" por "Fable") é V49, não marca
        if n and (n in MARCAS_CONHECIDAS or n in extra or misto or (sigla and n not in SIGLAS_COMUNS)):
            out.append(raw)
    return list(dict.fromkeys(out))


def pares_pendentes(m: dict) -> dict[str, str]:
    """Pares ouvido → provável das pendências abertas ("«Facebook»; provável «Fable»", "Antropic→Anthropic")."""
    out = {}
    for p in m.get("pendencias") or []:
        if p.get("estado") != "aberta":
            continue
        txt = str(p.get("o_que", ""))
        for a, b in re.findall(r"([\wÀ-ú][\wÀ-ú .]*?)\s*→\s*([\wÀ-ú][\wÀ-ú .]*?)(?=,|;|$)", txt):
            pa, pb = a.split(), b.split()
            pares = [(pa[0], pb[0])] if len(pa) == 1 else (list(zip(pa, pb)) if len(pa) == len(pb) else [])
            for x, y in pares:                # só a palavra que MUDA é dúvida; maiúscula ("KIMI"→"Kimi") não cala legenda
                if norm_palavra(x) != norm_palavra(y):
                    out[norm_palavra(x)] = norm_palavra(y)
        q = re.findall(r"«([^»]+)»", txt)
        if len(q) == 2:
            qa, qb = q[0].split(), q[1].split()
            for x, y in (zip(qa, qb) if len(qa) == len(qb) else ([(qa[0], qb[0])] if len(qa) == 1 else [])):
                if norm_palavra(x) != norm_palavra(y):
                    out[norm_palavra(x)] = norm_palavra(y)
    return out


def _palavras_janela(pal: list[dict], t0: float, t1: float) -> list[str]:
    return [norm_palavra(w["w"]) for w in pal if w["e"] > t0 and w["t"] < t1]


def verificar(projeto: Path, vid: str) -> list[dict]:
    projeto = Path(projeto).resolve()
    mp = projeto / "motion" / vid
    b = mp / "00_brief"
    plano_p = b / "PLANO_MOTION.md"
    if not plano_p.exists():
        raise DIError(f"{plano_p} não existe (modelo em memoria/templates/PLANO_MOTION.md)")
    md = plano_p.read_text(encoding="utf-8")
    m = carregar(projeto)
    mot = config(projeto).get("motion") or {}
    saida = config(projeto).get("saida") or "V"
    pal = ler_json(b / "transcript_palavras.json") or []
    cortes = (ler_json(b / "cortes.json") or {}).get("cortes", [])
    sils = (ler_json(b / "silencios_corte.json") or {}).get("silencios", [])
    momentos = ler_json(b / "momentos.json") or []
    avisos = ler_json(b / "avisos.json") or []
    fonte = (b / "FONTE.md").read_text(encoding="utf-8") if (b / "FONTE.md").exists() else ""
    dur = float(re.search(r"duração: ([0-9.]+)", fonte).group(1)) if "duração" in fonte else (pal[-1]["e"] if pal else 1.0)
    glos = (projeto / "00_fonte" / "glossario.txt")
    extra = {norm_palavra(x) for x in glos.read_text(encoding="utf-8").split()} if glos.exists() else set()
    regs = _registros()
    pend = pares_pendentes(m)
    duvidosas = {norm_palavra(a_.get("w", "")) for a_ in avisos if a_.get("tipo") == "asr_duvida"
                 and re.search(r"→\s*\S", a_.get("detalhe", "")) and len(norm_palavra(a_.get("w", ""))) >= 3} | set(pend)
    C: list[dict] = []

    # V43 régua
    dt = m.get("decisoes_travadas") or {}
    falta = [k for k in ("densidade", "fim_de_cena", "motion_fps", "prints_oficiais")
             if k not in dt and k not in (m.get("decidir_vendo") or [])]
    C.append(check("V43_regua", not falta, "BLOCKER", medido=falta or "completa", esperado="4 itens respondidos ou 'decidir vendo'"))

    cenas = _tabela(md, r"B\.")
    C.append(check("V44_tem_cenas", bool(cenas), "BLOCKER", medido=len(cenas), esperado="≥ 1 linha na tabela B"))
    prova_real = [sem_acento(str(x.get("prova_real", "")).lower()) for x in momentos]
    rows = []
    for r in cenas:
        nome = _col(r, "m#").strip("* ")
        anc, reg, ref = _col(r, "ancora"), _col(r, "registro"), _col(r, "referencia")
        oque, refe, entra = _col(r, "o que aparece"), _col(r, "referente"), _col(r, "entra")
        mexe, fim, leg = _col(r, "se mexe"), _col(r, "fim de cena"), _col(r, "legenda")
        cobre, lay_h, mot_ = _col(r, "cobre emenda"), _col(r, "layout h"), _col(r, "motivo")
        t_anc = _num(anc) if anc else None
        t0 = _num(entra) if entra else None
        kind = (re.match(r"\s*(\w+)", sem_acento(fim.lower())) or [None, None])[1] if fim else None
        t1 = _num(fim) if fim else None
        rows.append(dict(nome=nome, t0=t0, t1=t1, reg=sem_acento(reg.strip("* ").lower()), kind=kind, leg=leg,
                         oque=oque, refe=refe, anc=anc, t_anc=t_anc, mexe=mexe, cobre=cobre, lay_h=lay_h, mot=mot_))
        base = dict(video=vid, cena=nome)
        # V44: âncora, registro, referência, objeto dito, motivo
        C.append(check("V44_ancora", bool(re.search(r'"[^"]+"', anc)) and t_anc is not None and bool(re.search(r"\bf\d+", anc)),
                       "BLOCKER", medido=anc or "vazia", esperado='"palavra" · t s · f<n>', **base))
        C.append(check("V44_registro", sem_acento(reg.strip("* ").lower()) in regs, "HIGH", medido=reg or "vazio",
                       esperado="nome de motion-vox/referencias/registros.md", **base))
        C.append(check("V44_referencia", _refs_ok(ref), "HIGH", medido=ref or "vazia",
                       esperado="frame citado em REFERENCIAS-VISUAIS.md (ex.: Porsche bf06, Bible p.8)", **base))
        ok_t = t0 is not None and t1 is not None and t1 > t0
        C.append(check("V44_janela", ok_t, "BLOCKER", medido=f"t0 {t0} · t1 {t1}", esperado="t0 em Entra, t1 em Fim de cena, t1 > t0", **base))
        texto_cena = sem_acento((oque + " " + refe).lower())
        if ok_t:
            ditas = [w for w in _palavras_janela(pal, t0, t1) if len(w) >= 4 and w not in PARADAS]
            dito = any(w[:5] in texto_cena for w in ditas) or any(p and p[:6] in texto_cena for p in prova_real)
            C.append(check("V44_objeto_dito", dito, "BLOCKER", medido=ditas[:10] or "janela sem substantivo",
                           esperado="'O que aparece' casa com uma palavra dita na janela ou com prova_real", **base))
        C.append(check("V44_motivo", bool(mot_.strip()) and not any(re.search(p, mot_.lower()) for p in MOTIVO_VAZIO), "HIGH",
                       medido=mot_[:80] or "vazio", esperado="uma frase com o porquê; 'dá dinâmica' não é motivo", **base))
        # E3 referente · E5 abstrato · E8 clichê e beats
        tipos_ref = {sem_acento(x.strip().lower()) for x in re.findall(r"(?:^|\+)\s*([A-Za-zçãéíú]+)\s*:", refe)}
        tipo_ref = next(iter(sorted(tipos_ref & TIPOS_REFERENTE)), "")
        C.append(check("E3_referente", bool(tipos_ref) and tipos_ref <= TIPOS_REFERENTE, "HIGH", medido=refe or "vazio",
                       esperado="tipo: o quê — tipo ∈ marca, pessoa, objeto, mecanismo, numero, titulo", **base))
        abst = [p for p in ABSTRATO if re.search(p, sem_acento((oque + " " + mexe).lower()))]
        C.append(check("E5_nada_abstrato", not abst, "BLOCKER", medido=abst or 0,
                       esperado="coisa de verdade; nada de círculo vazio, forma abstrata ou ícone genérico", **base))
        cli = [p for p in CLICHE if re.search(p, sem_acento((oque + " " + mexe).lower()))]
        C.append(check("E8_sem_cliche", not cli, "HIGH", medido=cli or 0, esperado="nada clichê (lâmpada, engrenagem, foguete, ✓…)", **base))
        beats = [re.search(rf"{k}[^·]*?\bf(-?\d+)", sem_acento(mexe.lower())) for k in ("prova", "detalhe", "conclus")]
        fr = [int(x.group(1)) for x in beats if x]
        C.append(check("E8_tres_beats", len(fr) == 3 and fr == sorted(fr), "BLOCKER", medido=fr or mexe[:60] or "vazio",
                       esperado="prova → detalhe → conclusão, cada um com frame, em ordem", **base))
        # E4 marca citada → logo
        if ok_t:
            marcas = _marcas_na_janela(pal, t0, t1, extra, duvidosas)
            if marcas:
                com_logo = ("logo" in texto_cena or "print" in texto_cena) and "marca" in tipos_ref
                C.append(check("E4_marca_vira_logo", com_logo, "HIGH", medido=marcas, esperado="marca citada na janela → logo oficial dela", **base))
            gente = re.findall(GENTE_NA_FALA, " ".join(_palavras_janela(pal, t0, t1)))
            if gente and "pessoa" not in tipos_ref:
                C.append(check("E6_gente_na_fala", False, "MEDIUM", medido=gente[:4], esperado="fala com gente → a pessoa aparece (corpo, mãos)", **base))
        if "pessoa" in tipos_ref:
            C.append(check("E6_pessoa_aparece", bool(re.search(CORPO, sem_acento(oque.lower()))), "HIGH", medido=oque[:80],
                           esperado="a pessoa de fato: corpo, mãos, figura, foto — nunca só palavra", **base))
        if "titulo" in tipos_ref or re.search(r"\b(titulo|manchete|palavra|texto|letreiro)\b", sem_acento(oque.lower())):
            C.append(check("E7_titulo_com_elemento", bool(re.search(ELEMENTO, sem_acento(oque.lower()))), "HIGH", medido=oque[:80],
                           esperado="título acompanhado de um elemento que faz parte dele", **base))
        C.append(check("V_legenda_coluna", leg.strip().lower() in ("corre", "cala"), "MEDIUM", medido=leg or "vazia",
                       esperado="corre | cala", **base))
        if kind:
            C.append(check("V_fim_de_cena", kind in FINS, "HIGH", medido=fim, esperado="flash | push | slide | wipe | volta · t1 s", **base))
        if saida in ("ambas", "H"):
            C.append(check("V_layout_h", bool(lay_h.strip()) and lay_h.strip() not in ("—", "-"), "HIGH", medido=lay_h[:60] or "vazio",
                           esperado="como a cena se arruma no 16:9 (a saída tem H)", **base))

    # V45 densidade · V46 rosto mínimo · V47 vizinhas
    vals = [r for r in rows if r["t0"] is not None and r["t1"] is not None]
    vals.sort(key=lambda r: r["t0"])
    cob = sum(r["t1"] - r["t0"] for r in vals) / max(dur, 1e-6)
    lo, hi = (mot.get("densidade_alvo") or [0.65, 0.75])
    C.append(check("V45_densidade", lo - 0.05 <= cob <= hi + 0.05, "HIGH", medido=f"{100 * cob:.0f} %",
                   esperado=f"{100 * lo:.0f}–{100 * hi:.0f} % do corte coberto por motion", video=vid))
    min_r = float(mot.get("min_rosto_s") or 1.0)
    curtos = [f"{a['nome']}→{b_['nome']} {b_['t0'] - a['t1']:.2f} s" for a, b_ in zip(vals, vals[1:]) if 0 < b_["t0"] - a["t1"] < min_r]
    C.append(check("V46_rosto_entre_blocos", not curtos, "HIGH", medido=curtos or 0, esperado=f"≥ {min_r} s de rosto entre blocos (ou colados: rajada)", video=vid))
    rep = [f"{a['nome']}/{b_['nome']} {x}" for a, b_ in zip(vals, vals[1:]) for x, k in (("registro", "reg"), ("fim", "kind"))
           if a[k] and a[k] == b_[k]]
    C.append(check("V47_vizinhas_repetem", not rep, "HIGH", medido=rep or 0, esperado="registro e fim de cena variam entre vizinhas", video=vid))
    # V48 provas reais (seção F)
    secF = _tabela(md, r"F\.")
    nomesF = {_col(x, "cena").strip() for x in secF if _col(x, "origem") and _col(x, "licenca")}
    precisa = [r["nome"] for r in rows if r["refe"].lower().startswith("marca") or "insert real" in r["reg"]]
    semF = [n for n in precisa if n not in nomesF]
    C.append(check("V48_prova_real_listada", not semF, "HIGH", medido=semF or 0, esperado="logo/foto real com origem e licença na seção F", video=vid))
    # V49 palavra em dúvida
    abertas = [sem_acento(str(p.get("o_que", "")).lower()) for p in (m.get("pendencias") or []) if p.get("estado") == "aberta"]
    duv = []
    for a_ in avisos:
        if a_.get("tipo") != "asr_duvida":
            continue
        w = norm_palavra(a_.get("w", ""))
        sug = norm_palavra((re.search(r"→\s*([^?]+)", a_.get("detalhe", "")) or [None, ""])[1]) or pend.get(w, "")
        formas = [x for x in (w, sug) if x and len(x) >= 3]
        for r in vals:
            txt = sem_acento((r["oque"] + " " + r["anc"] + " " + r["refe"]).lower())
            palavras_txt = set(re.findall(r"[a-z0-9]+", txt))
            if r["t0"] - 0.1 <= a_["t"] <= r["t1"] + 0.1 and any(f in palavras_txt for f in formas) \
                    and w in pend:
                duv.append(f"{r['nome']}: '{a_.get('w')}'" + (f" (→ {sug})" if sug else ""))
    for r in vals:   # palavra pendente dita na janela, sem aviso próprio (ex.: "Cloud" → Claude)
        txt = set(re.findall(r"[a-z0-9]+", sem_acento((r["oque"] + " " + r["anc"] + " " + r["refe"]).lower())))
        for w in pal:
            n = norm_palavra(w["w"])
            if n in pend and r["t0"] - 0.1 <= w["t"] <= r["t1"] + 0.1 and (n in txt or pend[n] in txt):
                it = f"{r['nome']}: '{w['w'].strip('.,')}' (→ {pend[n]})"
                if not any(it.split(" (")[0].lower() == d.split(" (")[0].lower() for d in duv):
                    duv.append(it)
    C.append(check("V49_asr_duvida", not duv, "BLOCKER", medido=duv or 0, esperado="cena não se apoia em palavra não confirmada pelo usuário", video=vid))
    # V50 emendas e t1 no silêncio
    e50, avisos50 = [], []
    for r in vals:
        dentro = [c for c in cortes if r["t0"] < c < r["t1"]]
        diz_sim = r["cobre"].lower().startswith("sim")
        if dentro and not diz_sim:
            e50.append(f"{r['nome']} cobre a emenda {dentro[0]:.2f} e diz 'não'")
        # sair NA emenda (±1 quadro) esconde o pulo; sair pouco ANTES dela mostra o rosto e o pulo logo em seguida
        if not dentro and any(0.045 < c - r["t1"] < 0.15 for c in cortes):
            e50.append(f"{r['nome']} termina a < 0,15 s antes de uma emenda (saia na emenda ou 0,15 s antes)")
        eps = 0.005
        no_sil = any(s["t"] + 0.06 - eps <= r["t1"] <= s["e"] - 0.06 + eps for s in sils)
        na_fronteira = any(a["e"] - 0.04 - eps <= r["t1"] <= b_["t"] + 0.04 + eps for a, b_ in zip(pal, pal[1:])) or \
            any(abs(r["t1"] - c) <= 0.04 + eps for c in cortes)
        if not no_sil and not na_fronteira and r["t1"] < dur - 0.05:
            e50.append(f"{r['nome']} t1 {r['t1']:.2f} no meio de uma palavra")
        elif not no_sil and r["t1"] < dur - 0.05:
            avisos50.append(f"{r['nome']} t1 {r['t1']:.2f} na fronteira de palavra (sem silêncio medido)")
    C.append(check("V50_emendas_e_silencio", not e50, "HIGH", medido=e50 or 0,
                   esperado="cobre emenda declarada; t1 no silêncio do corte ou na fronteira entre palavras, nunca na sílaba", video=vid))
    C.append(check("V50b_corte_sem_silencio", not avisos50, "aviso", medido=avisos50 or 0,
                   esperado="silêncio medido é o ideal; fala rápida deixa só a fronteira de palavra", video=vid))
    # V52 lista de geração
    secG = _tabela(md, r"G\.")
    ruins = [_col(x, "asset") for x in secG if not (_col(x, "ferramenta") and _col(x, "chamadas") and _col(x, "custo"))]
    C.append(check("V52_lista_de_geracao", not ruins, "BLOCKER", medido=ruins or f"{len(secG)} item(ns)",
                   esperado="ferramenta, chamadas e custo por imagem a gerar", video=vid))
    # E4 também fora das cenas: marca dita sem cena e sem linha em C
    secC = " ".join(sem_acento(" ".join(x.values()).lower()) for x in _tabela(md, r"C\."))
    todas = _marcas_na_janela(pal, 0, dur, extra, duvidosas)
    cobertas = {norm_palavra(x) for r in vals for x in _marcas_na_janela(pal, r["t0"], r["t1"], extra, duvidosas)}
    orfas = [x for x in todas if norm_palavra(x) not in cobertas and norm_palavra(x)[:5] not in secC]
    C.append(check("E4_marca_sem_cena", not orfas, "MEDIUM", medido=orfas or 0,
                   esperado="toda marca citada vira logo numa cena, ou vai para a seção C com motivo", video=vid))
    # E1/E2 acabamento no render.py do projeto
    rp = (mp / "render.py").read_text(encoding="utf-8") if (mp / "render.py").exists() else ""
    g = lambda pat, d=None: (re.search(pat, rp, re.M) or [None, d])[1]
    mfps = g(r"^MOTION_FPS\s*=\s*(\d+)")
    fx = re.search(r"FX_DESK\s*=\s*dict\(grain=([0-9.]+),\s*vignette=([0-9.]+),\s*chroma=([0-9.]+)", rp)
    boil = g(r"^V\.BOIL_SCALE\s*=\s*([0-9.]+)")
    e1 = []
    if str(mfps) != str(mot.get("fps", 12)):
        e1.append(f"MOTION_FPS {mfps} ≠ régua {mot.get('fps')}")
    if "RELOGIO_UNICO = True" not in rp:
        e1.append("relógio único desligado")
    if not fx or not (0.03 <= float(fx.group(1)) <= 0.08):
        e1.append("grão fora de 0,03–0,08")
    if not fx or not (0 < float(fx.group(3)) <= 1.2):
        e1.append("RGB (chroma) fora do mínimo (0 < chroma ≤ 1,2)")
    C.append(check("E1_acabamento", not e1, "HIGH", medido=e1 or f"12 fps · grão {fx.group(1) if fx else '?'} · chroma {fx.group(3) if fx else '?'}",
                   esperado="12 fps, relógio único, grão, RGB mínimo", video=vid))
    C.append(check("E2_turbulencia_leve", boil is not None and 0 < float(boil) <= 0.6, "HIGH", medido=f"BOIL_SCALE {boil}",
                   esperado="Turbulent Displace leve: 0 < BOIL_SCALE ≤ 0,6", video=vid))
    # E9/E10 — assets sob medida (motion-vox/referencias/assets-sob-medida.md §2): nada de kit repetido nem de cena
    # inteira apoiada no kit. Conta o que o PLANO declara e, quando o compose.py já existe, o que ele de fato usa.
    HEROIS = {"A02_CLOCK", "A06_CAVE", "A07_IDEA", "A08_BOX", "A09_STACK", "A11_NIGHT", "A12_KEYBOARD", "A13_EMPTY",
              "A14_CRT", "A15_MONEY_STACK", "A17_MONEY_FEW"}
    gerados = {re.sub(r"[^A-Z0-9_]", "", (_col(x, "asset") or "").split("(")[0].strip().upper()) for x in secG}
    gerados.discard("")
    por_cena_plano = {r["nome"]: set(re.findall(r"\bA\d\d_[A-Z_]+", r.get("oque", ""))) for r in rows}
    por_cena = {k: set(v) for k, v in por_cena_plano.items()}
    cp = mp / "compose.py"
    if cp.exists():
        # cada função de topo → os assets do kit que ela usa (direto ou pelo nome do arquivo); a cena herda os das
        # funções auxiliares que chama (frente(), folha(), logo_cartao()…)
        src = cp.read_text(encoding="utf-8")
        partes = re.split(r"^def (\w+)\(", src, flags=re.M)
        corpo = {partes[k]: partes[k + 1] for k in range(1, len(partes) - 1, 2)}
        def diretos(txt: str) -> set:
            u = set(re.findall(r'(?:asset|piece|asset_anchor|clip_asset|load_cutout)\(\s*"(A\d\d_[A-Z_]+)"', txt))
            u |= set(re.findall(r'"(A\d\d_[A-Z_]+)\.png"', txt))
            if "photo_card(" in txt:
                u.add("A11_NIGHT")
            if re.search(r"\bCRT\.crt\(|\bcrt\(", txt):
                u.add("A14_CRT")
            return u
        dir_ = {f: diretos(b) for f, b in corpo.items()}
        for f, b in corpo.items():
            if not f.startswith("build_M"):
                continue
            usados = set(dir_[f])
            for h in re.findall(r"\b(\w+)\(", b):
                if h in dir_ and h != f and not h.startswith("build_"):
                    usados |= dir_[h]
            nome = f.replace("build_", "")
            por_cena[nome] = por_cena.get(nome, set()) | usados
    cont: dict = {}
    for nome, cods in por_cena.items():
        for c_ in cods:
            cont.setdefault(c_, []).append(nome)
    rep = [f"{c_} em {', '.join(sorted(v))}" for c_, v in sorted(cont.items())
           if (c_ in HEROIS and len(v) > 1) or (c_ == "A05_CARD" and len(v) > 2)]
    C.append(check("E9_heroi_repetido", not rep, "HIGH", medido=rep or 0,
                   esperado="cada herói do kit em 1 cena no máximo; o cartão A05 em 2 no máximo — o resto sob medida "
                            "(assets-sob-medida.md §2)", video=vid))
    kit_only = [r["nome"] for r in rows if (por_cena_plano.get(r["nome"]) & (HEROIS | {"A05_CARD"}))
                and not any(g_ and g_ in (r.get("oque") or "").upper() for g_ in gerados)
                and "logo" not in sem_acento((r.get("oque") or "").lower())]
    frac = len(kit_only) / max(1, len(rows))
    C.append(check("E10_sob_medida", frac <= 0.40, "HIGH", medido=f"{100 * frac:.0f} % ({', '.join(kit_only) or 'nenhuma'})",
                   esperado="≤ 40 % das cenas com o objeto principal tirado do kit (assets-sob-medida.md §1)", video=vid))
    return C


def relatorio(projeto: Path, vid: str, C: list[dict]) -> Path:
    L = [f"# Verificação do plano — {vid}", "", "| check | cena | ok | severidade | medido | esperado |", "| --- | --- | --- | --- | --- | --- |"]
    for c in C:
        L.append(f"| {c['id']} | {c.get('cena', '')} | {'✓' if c['ok'] else '✗'} | {c['severidade']} | {c.get('medido')} | {c.get('esperado') or ''} |")
    p = Path(projeto) / "motion" / vid / "00_brief" / "VERIFICACAO_PLANO.md"
    gravar_texto(p, "\n".join(L) + "\n")
    return p


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di verificar-plano")
    ap.add_argument("video")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    C = verificar(projeto, a.video)
    registrar_checks(projeto, "F4", C, alvo=f"motion/{a.video}/00_brief/PLANO_MOTION.md")
    p = relatorio(projeto, a.video, C)
    ruins = [c for c in C if not c["ok"] and c["severidade"] in ("BLOCKER", "HIGH")]
    for c in ruins:
        print(f"  ✗ {c['id']} {c.get('cena', '')} {c['severidade']}: {c.get('medido')}")
    print(f"{'✗' if any(c['severidade'] == 'BLOCKER' for c in ruins) else '✓'} {len(C)} checks, {len(ruins)} BLOCKER/HIGH → {p}")
    return 1 if any(c["severidade"] == "BLOCKER" for c in ruins) else 0
