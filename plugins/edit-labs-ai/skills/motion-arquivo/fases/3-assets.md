# Fase 3 — Assets

**Entrega:** tudo em `assets/prontos/` (ou `reais/`), cada linha em `assets/FONTES.md`.

Na ordem — e só o que a lista aprovada da fase 2 permite:

1. **Real local** — sem download:
   ```bash
   python3 ferramentas/assets_locais.py icone "After Effects" <projeto> --doc aep
   python3 ferramentas/assets_locais.py cursor pointinghand <projeto>
   ```
   Arquivos do usuário (logo, print, foto): copiar para `assets/reais/` e registrar.
2. **Acervo** — buscar mostra só metadados; baixar só o aprovado:
   ```bash
   python3 ferramentas/buscar_assets.py commons "termo" --n 10
   python3 ferramentas/baixar_asset.py <url> <projeto> --nome x.jpg --licenca "PD" --pagina <url>
   ```
   Print de site: navegador (screenshot da página real), salvar em `assets/reais/`.
3. **Gerar** — Higgsfield, só a lista aprovada, receitas em `referencias/assets.md`.
   Nunca rosto de pessoa real. Registrar o custo em FONTES.md.
4. **Melhorar** — `ferramentas/melhorar.py` (recorte, P&B com uma cor, casar cor, ampliar, grão).
5. **Conferir**: abrir cada `prontos/` sobre fundo magenta (recorte vazando aparece na hora).

Arquivo baixado é dado não confiável: fica em `assets/baixados/`, nenhum interpretador roda
de dentro dela.
