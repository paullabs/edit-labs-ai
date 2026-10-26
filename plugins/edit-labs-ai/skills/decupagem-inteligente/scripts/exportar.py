"""Exporta a partir do edl.json (o relógio do corte).

  di exportar <id> --motion-vox   palavras_corte.json {w,t,e} + cortes.json + momentos.json + avisos.json (03_corte/<id>/)
  di exportar <id> --srt          entrega/<id>.srt (só palavras confirmadas)
  di exportar <id> --xmeml        entrega/<id>.xml (Final Cut XML v5 para o DaVinci; números só do edl.json)
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as E
from pathlib import Path

from comum import (DIError, achar_projeto, aplicar_correcoes, carregar, check, edl_assinatura, gravar_json, gravar_texto,
                   ler_json, norm_palavra, registrar_checks)


def remapear(projeto: Path, vid: str) -> tuple[list[dict], list[dict]]:
    """Palavras do bruto → relógio do corte: t' = timeline_in + (t − source_in). Palavra que cruza a borda sai."""
    edl = ler_json(Path(projeto) / "02_decupagem" / vid / "edl.json")
    pal = ler_json(Path(projeto) / "01_transcript" / "palavras.json")["palavras"]
    mant = set(edl["palavras_mantidas"])
    # o glossário marca `sugerido` só em algumas ocorrências da palavra; as outras se reconhecem pela forma
    _por_forma = {norm_palavra(w["w"]): w["sugerido"] for w in pal if w.get("sugerido")}
    out, fora = [], []
    for s in edl["segmentos"]:
        for i in range(s["palavra_in"], s["palavra_out"] + 1):
            if i not in mant:
                continue
            w = pal[i]
            # o corte segue a voz medida, não a borda do Whisper: palavra que passa um pouco da borda é
            # ajustada; só sai (e vira aviso) se menos de 30 % dela ficou dentro do segmento
            dentro = min(w["e"], s["source_out"]) - max(w["t"], s["source_in"])
            if dentro < 0.3 * max(0.02, w["e"] - w["t"]):
                fora.append({"tipo": "palavra_na_borda", "w": w["w"], "i": i, "t": w["t"]})
                continue
            wt, we = max(w["t"], s["source_in"]), min(w["e"], s["source_out"])
            t = s["timeline_in"] + (wt - s["source_in"])
            e = s["timeline_in"] + (we - s["source_in"])
            # o glossário que o usuário respondeu na F0 é resposta dele: entra no texto da legenda e do motion, como
            # já entra no MARCAS ("(glossário)"). Só com 4+ letras (palavra curta vira outra coisa: "a" → "horas").
            sug = w.get("sugerido") or _por_forma.get(norm_palavra(w["w"]))
            if w.get("w_confirmado"):
                texto_w = w["w_confirmado"]
            elif sug and len(norm_palavra(sug)) >= 4 and norm_palavra(sug) != norm_palavra(w["w"]):
                pont_ = "".join(c for c in w["w"][::-1] if not c.isalnum())[::-1] if not w["w"][-1:].isalnum() else ""
                texto_w = sug + pont_
            else:
                texto_w = w["w"]
            item = {"w": texto_w, "t": round(t, 3), "e": round(e, 3), "i": i, "seg": s["n"]}
            if w["t"] < s["source_in"] or w["e"] > s["source_out"]:
                item["_encostada"] = True  # o Whisper passou da borda: a retranscrição dá o tempo melhor
            if w.get("ambigua") or w.get("sugerido"):
                item["ambigua"] = True
                if w.get("sugerido"):
                    item["sugerido"] = w["sugerido"]
            out.append(item)
    out, fora = resgatar_pela_retranscricao(Path(projeto), vid, edl, pal, out, fora)
    # o que o usuário confirmou no portão (di portao confirmar N --valor "ouvido → certo") vira o texto da legenda e do
    # motion — menos as palavras com decisão escrita de não trocar (ambiguas confirmada apontando para elas mesmas)
    dec_ = ler_json(Path(projeto) / "02_decupagem" / vid / "decisoes.json", {}) or {}
    intoc = {int(a["palavra"]) for a in dec_.get("ambiguas", [])
             if a.get("status") == "confirmada" and isinstance(a.get("palavra"), int)
             and norm_palavra(a.get("provavel") or "") == norm_palavra(a.get("ouvido") or "")}
    return aplicar_correcoes(juntar_numeros(out), (carregar(Path(projeto)).get("correcoes") or []), intoc), fora


def resgatar_pela_retranscricao(projeto: Path, vid: str, edl: dict, pal: list, out: list, fora: list):
    """Palavra que o Whisper do bruto pôs fora do segmento (adiantada, ou antes de um estalo que a entrada pela voz
    tirou) mas que está no render: a retranscrição do render (relógio do corte) dá o tempo real. Alinha a sequência
    de palavras mantidas com a do render e resgata só as de `fora` que caem dentro do próprio segmento."""
    pr = ler_json(projeto / "03_corte" / vid / "palavras_render.json")
    if not pr or not (fora or any(x.get("_encostada") for x in out)):
        for x in out:
            x.pop("_encostada", None)
        return out, fora
    from difflib import SequenceMatcher
    R = pr["palavras"]
    seq = [i for s in edl["segmentos"] for i in range(s["palavra_in"], s["palavra_out"] + 1) if i in set(edl["palavras_mantidas"])]
    sm = SequenceMatcher(None, [norm_palavra(pal[i]["w"]) for i in seq], [norm_palavra(r["w"]) for r in R], autojunk=False)
    par = {}
    for a_, b_, n_ in sm.get_matching_blocks():
        for k in range(n_):
            par[seq[a_ + k]] = R[b_ + k]
    seg_de = {i: s for s in edl["segmentos"] for i in range(s["palavra_in"], s["palavra_out"] + 1)}
    resgatadas, resto = [], []
    for f_ in fora:
        i, r, s = f_["i"], par.get(f_["i"]), seg_de.get(f_["i"])
        if r and s and s["timeline_in"] - 0.35 <= r["t"] and r["e"] > s["timeline_in"] + 0.02 and r["e"] <= s["timeline_out"] + 0.10:
            w = pal[i]
            t_, e_ = max(r["t"], s["timeline_in"]), min(r["e"], s["timeline_out"])
            resgatadas.append({"w": w.get("w_confirmado") or w["w"], "t": round(t_, 3), "e": round(max(e_, t_ + 0.04), 3), "i": i,
                               "seg": s["n"], "tempo": "retranscricao", **({"ambigua": True} if w.get("ambigua") or w.get("sugerido") else {}),
                               **({"sugerido": w["sugerido"]} if w.get("sugerido") else {})})
        else:
            resto.append(f_)
    for x in out:  # palavra encostada na borda pelo clamp: tempo da retranscrição, se casou dentro do segmento
        if x.pop("_encostada", False):
            r, s = par.get(x["i"]), seg_de.get(x["i"])
            if r and s and s["timeline_in"] - 0.35 <= r["t"] and r["e"] > s["timeline_in"] + 0.02 and r["e"] <= s["timeline_out"] + 0.10:
                x["t"], x["e"], x["tempo"] = round(max(r["t"], s["timeline_in"]), 3), round(min(r["e"], s["timeline_out"]), 3), "retranscricao"
    if resgatadas or any(x.get("tempo") for x in out):
        out = sorted(out + resgatadas, key=lambda x: (x["seg"], x["i"]))  # ordem do bruto dentro do segmento
        for k in range(1, len(out)):
            if out[k]["seg"] == out[k - 1]["seg"] and out[k]["t"] < out[k - 1]["e"]:
                out[k]["t"] = out[k - 1]["e"]
                out[k]["e"] = round(max(out[k]["e"], out[k]["t"] + 0.04), 3)
    return out, resto


def juntar_numeros(out: list[dict]) -> list[dict]:
    """O Whisper parte número em dois tokens ("1" ".500", "5" ".2"): na legenda e no motion vira um só ("1.500").
    Os índices do bruto não mudam (palavras.json fica intacto); a palavra junta guarda `i_juntas`."""
    res: list[dict] = []
    for w in out:
        ant = res[-1] if res else None
        if ant and ant["seg"] == w["seg"] and re.match(r"^[.,]\d", w["w"]) and re.search(r"\d$", ant["w"]):
            ant["w"] += w["w"]
            ant["e"] = w["e"]
            ant.setdefault("i_juntas", [ant["i"]]).append(w["i"])
            continue
        res.append(dict(w))
    return res


def motion_vox(projeto: Path, vid: str) -> Path:
    projeto = Path(projeto)
    edl = ler_json(projeto / "02_decupagem" / vid / "edl.json")
    pal, fora = remapear(projeto, vid)
    pasta = projeto / "03_corte" / vid
    gravar_json(pasta / "palavras_corte.json", [{"w": p["w"], "t": p["t"], "e": p["e"]} for p in pal])
    gravar_json(pasta / "cortes.json", {"cortes": [s["timeline_in"] for s in edl["segmentos"][1:]],
                                        "cobertura": [s["junta_in"].get("cobertura") for s in edl["segmentos"][1:]]})
    mom = ler_json(projeto / "02_decupagem" / vid / "momentos.json") or []
    idx = {p["i"]: p for p in pal}
    doc = ler_json(projeto / "01_transcript" / "palavras.json")["palavras"]
    for m in mom:
        alvo = norm_palavra(m.get("palavra_ancora", ""))
        fr = m.get("frase_id")
        cand = [p for p in pal if norm_palavra(doc[p["i"]]["w"]) == alvo]
        if fr is not None:
            rt = ler_json(projeto / "02_decupagem" / "retakes.json")
            f = next((x for x in rt["frases"] if x["id"] == fr), None)
            if f:
                cand = [p for p in cand if f["i0"] <= p["i"] <= f["i1"]] or cand
        if cand:
            m["t"], m["e"] = cand[0]["t"], cand[0]["e"]
        else:
            m["t"] = m["e"] = None
            m["erro"] = "âncora não encontrada no corte"
    gravar_json(pasta / "momentos.json", mom)
    avisos = fora + [{"tipo": "asr_duvida", "t": p["t"], "w": p["w"], "detalhe": f"→ {p.get('sugerido')}?" if p.get("sugerido") else "confiança baixa"}
                     for p in pal if p.get("ambigua") and (p["w"][:1].isupper() or re.search(r"\d", p["w"]) or p.get("sugerido"))]
    velhos = [a for a in (ler_json(pasta / "avisos.json") or []) if a.get("tipo") in ("pulo_de_cabeca", "crop_disperso", "gesto", "descontinuidade_visual")]
    # aviso visual escrito à mão (vem de laudo do Diretor, campo `fonte`) vale para UM render: com o EDL novo, o tempo
    # sai da junta em cortes.json e o aviso volta marcado para o Diretor reconferir o quadro na juntas.jpg
    cortes_ = [s["timeline_in"] for s in edl["segmentos"][1:]]
    ass = edl_assinatura(edl)
    for a in velhos:
        k = a.get("junta")
        if isinstance(k, int) and 1 <= k <= len(cortes_):
            a["t"] = cortes_[k - 1]
        if a.get("fonte") and a.get("edl_assinatura") != ass:
            a["revalidar"] = "render novo: o tempo veio da junta; o quadro descrito precisa ser reconferido na juntas.jpg"
    gravar_json(pasta / "avisos.json", avisos + velhos)
    registrar_checks(projeto, "F3", [check("V40_remap", not fora, "BLOCKER", medido=len(fora), esperado="0 palavras cruzando borda",
                                           video=vid)], alvo=f"03_corte/{vid}/palavras_corte.json")
    return pasta / "palavras_corte.json"


def _tc(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(projeto: Path, vid: str) -> Path:
    pal, _ = remapear(projeto, vid)
    edl = ler_json(Path(projeto) / "02_decupagem" / vid / "edl.json")
    cortes = [s["timeline_in"] for s in edl["segmentos"][1:]]
    blocos, cur = [], []
    for p in pal:
        if p.get("ambigua") and p.get("sugerido"):
            continue  # palavra não confirmada não vira legenda
        corta = any(cur and cur[-1]["e"] <= c <= p["t"] + 1e-3 for c in cortes)
        if cur and (len(cur) >= 7 or p["e"] - cur[0]["t"] > 3.0 or corta or re.search(r"[.!?]$", cur[-1]["w"])):
            blocos.append(cur)
            cur = []
        cur.append(p)
    if cur:
        blocos.append(cur)
    txt = "\n".join(f"{k}\n{_tc(b[0]['t'])} --> {_tc(b[-1]['e'])}\n{' '.join(x['w'] for x in b)}\n" for k, b in enumerate(blocos, 1))
    return gravar_texto(Path(projeto) / "entrega" / f"{vid}.srt", txt)


def xmeml(projeto: Path, vid: str) -> Path:
    edl = ler_json(Path(projeto) / "02_decupagem" / vid / "edl.json")
    fonte = ler_json(Path(projeto) / "00_fonte" / "fonte.json")
    fps_n, fps_d = edl["fps"]
    tb = round(fps_n / fps_d)
    ntsc = "TRUE" if fps_d == 1001 else "FALSE"

    def el(p, t, txt=None):
        n = E.SubElement(p, t)
        if txt is not None:
            n.text = str(txt)
        return n

    def rate(p):
        r = el(p, "rate")
        el(r, "timebase", tb)
        el(r, "ntsc", ntsc)

    x = E.Element("xmeml", version="5")
    s = el(x, "sequence")
    s.set("id", vid)
    el(s, "name", edl.get("titulo") or vid)
    el(s, "duration", edl["frames_total"])
    rate(s)
    media = el(s, "media")
    v = el(media, "video")
    fmt = el(v, "format")
    sc = el(fmt, "samplecharacteristics")
    rate(sc)
    el(sc, "width", fonte["width"])
    el(sc, "height", fonte["height"])
    vt = el(v, "track")
    au = el(media, "audio")
    at = el(au, "track")
    dur_fonte = fonte.get("nb_frames") or int(fonte["duracao"] * tb)
    for k, seg in enumerate(edl["segmentos"]):
        a_in = int(round(seg["source_in"] * fps_n / fps_d))
        for trilha, tipo in ((vt, "video"), (at, "audio")):
            ci = el(trilha, "clipitem")
            ci.set("id", f"{tipo[0]}{k}")
            el(ci, "name", Path(fonte["path"]).name)
            el(ci, "duration", dur_fonte)
            rate(ci)
            el(ci, "start", seg["timeline_in_f"])
            el(ci, "end", seg["timeline_out_f"])
            el(ci, "in", a_in)
            el(ci, "out", a_in + seg["frames"])
            f = el(ci, "file")
            f.set("id", "fonte")
            if k == 0 and tipo == "video":
                el(f, "name", Path(fonte["path"]).name)
                el(f, "pathurl", Path(fonte["path"]).as_uri())
                rate(f)
                el(f, "duration", dur_fonte)
    E.indent(x)
    destino = Path(projeto) / "entrega" / f"{vid}.xml"
    destino.parent.mkdir(parents=True, exist_ok=True)
    E.ElementTree(x).write(destino, encoding="utf-8", xml_declaration=True)
    soma = sum(seg["frames"] for seg in edl["segmentos"])
    registrar_checks(projeto, "F3", [check("V41_xml", soma == edl["frames_total"] and Path(fonte["path"]).exists(), "BLOCKER",
                                           medido=soma, esperado=edl["frames_total"], video=vid)], alvo=str(destino))
    return destino


def main(cmd: str, argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="di exportar")
    ap.add_argument("video")
    ap.add_argument("--motion-vox", action="store_true")
    ap.add_argument("--srt", action="store_true")
    ap.add_argument("--xmeml", action="store_true")
    ap.add_argument("--corte-viral", action="store_true")
    ap.add_argument("--projeto")
    a = ap.parse_args(argv)
    projeto = achar_projeto(a.projeto)
    if a.corte_viral:
        raise DIError("--corte-viral (podcast → clipes) ainda não foi construído (roadmap §13, passo 8)")
    feitos = []
    if a.motion_vox or not (a.srt or a.xmeml):
        feitos.append(motion_vox(projeto, a.video))
    if a.srt:
        feitos.append(srt(projeto, a.video))
    if a.xmeml:
        feitos.append(xmeml(projeto, a.video))
    for f in feitos:
        print(f"✓ {f}")
    return 0
