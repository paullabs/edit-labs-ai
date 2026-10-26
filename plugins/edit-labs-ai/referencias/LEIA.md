# Banco de referências de estilo

O que é: o catálogo das obras que servem de régua de estilo para as skills de colagem e de explicador (Vox, gravura,
papel cortado, livro de abas, documentário). Cada referência tem **título, autor, link, licença declarada e a nossa
análise**. Só texto: nenhuma imagem, vídeo ou som de terceiros vem aqui. Para ver a obra, abra o link.

Guia completo: `LEIA-ME.md`. Catálogo legível: `CATALOGO.md`.

## Antes de um vídeo novo
1. Escolha o estilo pela tabela "Escolher o estilo" do `LEIA-ME.md` (um principal, no máximo um de apoio).
2. Veja as referências e a ficha do estilo:
   ```
   python3 -I ${CLAUDE_PLUGIN_ROOT}/referencias/ferramentas/refs.py estilo vox-clean
   python3 -I ${CLAUDE_PLUGIN_ROOT}/referencias/ferramentas/refs.py ver R03-mariano-two-parties-vox
   ```
3. Leia a ficha (`fichas-de-estilo/<estilo>.md`) e a análise das referências `a-fundo` (`analises/`).
4. Copie `modelo/BRIEF_DE_ESTILO_modelo.md` para a pasta do vídeo, preencha e peça a aprovação do usuário antes do
   roteiro.

## Adicionar uma referência
```
python3 -I ${CLAUDE_PLUGIN_ROOT}/referencias/ferramentas/refs.py adicionar \
  --id R26-autor-obra --titulo "..." --autor "..." --url https://... --tipo video --prof vista \
  --tema geral --estilo vox-clean --mecanica marca-texto --licenca "todos os direitos reservados" --nota "o que ensina"
```
- **Link e licença são obrigatórios.** Licença é a que a fonte declara; se não diz, `desconhecida; tratar como todos
  os direitos reservados`.
- **Não baixe mídia de terceiros** para o banco. Escreva o que viu e mediu; para virar `a-fundo`, crie a análise em
  `analises/` e aponte o campo `analise` no `catalogo.json`.
- Depois de editar o JSON à mão, rode `refs.py validar` e `refs.py gerar`.
