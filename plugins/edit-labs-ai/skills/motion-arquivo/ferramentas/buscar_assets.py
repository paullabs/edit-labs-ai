#!/usr/bin/env python3
"""
Busca assets REAIS em acervos abertos — so METADADOS (titulo, licenca, autor, tamanho, URL).
Nao baixa nada: a lista vai para o usuario aprovar, e so entao baixar_asset.py baixa.

    mvpy buscar_assets.py commons  "Hedy Lamarr 1940" [--n 10]
    mvpy buscar_assets.py openverse "radio tower vintage" [--n 10]
    mvpy buscar_assets.py nasa "apollo 11 launch" [--n 10]

commons    Wikimedia Commons (arquivos), licenca do extmetadata
openverse  agregador de imagens CC (Flickr, museus...) — so licencas de uso comercial
nasa       NASA Image Library (em geral dominio publico)
"""
import json, re, sys, urllib.parse, urllib.request

UA = {"User-Agent": "motion-arquivo/1.0 (busca de assets licenciados)"}


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.loads(r.read().decode())


def commons(q, n):
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6"
         f"&gsrlimit={n}&gsrsearch={urllib.parse.quote(q)}&prop=imageinfo&iiprop=url|size|mime|extmetadata"
         "&iiurlwidth=400")
    d = _get(u)
    out = []
    for p in (d.get("query", {}).get("pages", {}) or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        val = lambda k: re.sub(r"<[^>]+>", "", str((m.get(k, {}) or {}).get("value", ""))).strip()
        out.append(dict(titulo=p["title"], licenca=val("LicenseShortName"), autor=val("Artist")[:80],
                        tam=f"{ii.get('width')}x{ii.get('height')}", bytes=ii.get("size"), tipo=ii.get("mime"),
                        url=ii.get("url"), pagina=ii.get("descriptionurl")))
    return out


def openverse(q, n):
    d = _get(f"https://api.openverse.org/v1/images/?q={urllib.parse.quote(q)}&license_type=commercial&page_size={n}")
    return [dict(titulo=r.get("title"), licenca=f"{r.get('license')} {r.get('license_version') or ''}".strip(),
                 autor=(r.get("creator") or "")[:80], tam=f"{r.get('width')}x{r.get('height')}", bytes=r.get("filesize"),
                 tipo=r.get("filetype"), url=r.get("url"), pagina=r.get("foreign_landing_url")) for r in d.get("results", [])]


def nasa(q, n):
    d = _get(f"https://images-api.nasa.gov/search?q={urllib.parse.quote(q)}&media_type=image")
    out = []
    for it in d.get("collection", {}).get("items", [])[:n]:
        dt = (it.get("data") or [{}])[0]
        out.append(dict(titulo=dt.get("title"), licenca="NASA (em geral dominio publico; conferir a pagina)",
                        autor=(dt.get("photographer") or dt.get("center") or "")[:80], tam="?", bytes=None,
                        tipo="image", url=(it.get("links") or [{}])[0].get("href"),
                        pagina=f"https://images.nasa.gov/details/{dt.get('nasa_id')}"))
    return out


if __name__ == "__main__":
    fonte, q = sys.argv[1], sys.argv[2]
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 10
    res = {"commons": commons, "openverse": openverse, "nasa": nasa}[fonte](q, n)
    for i, r in enumerate(res, 1):
        mb = f"{r['bytes'] / 1e6:.1f} MB" if r.get("bytes") else "? MB"
        print(f"{i:2d}. {r['titulo']}\n    licenca: {r['licenca']} | autor: {r['autor']} | {r['tam']} | {mb}\n"
              f"    arquivo: {r['url']}\n    pagina:  {r['pagina']}")
