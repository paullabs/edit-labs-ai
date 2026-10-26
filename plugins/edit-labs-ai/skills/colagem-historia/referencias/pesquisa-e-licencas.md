# Pesquisa, fotos e licenças

Duas rodadas por reel: a **pesquisa** (fatos, roteiro e imagens) e os **objetos** (coisas concretas que aparecem,
se movem e explicam a cena). Podem rodar em paralelo, em subagentes, com este arquivo como brief. Nenhuma das duas
renderiza vídeo.

## 1. Fatos

- Cada afirmação precisa de **2 fontes confiáveis**: museu, universidade, enciclopédia, jornal sério ou livro.
- Se um detalhe é disputado ou é mito, diga isso no `roteiro.md` e escreva a frase de um jeito que continue
  verdadeiro ("ajudou a popularizar", e não "inventou"; "levou para casa", e não "roubou").
- Nada de inventar citação. Se a frase famosa tem versões, registre as versões e use "a frase que ficou".
- Número disputado: use o mais citado e diga "≈".

## 2. Roteiro (`roteiro.md`)

- **Gancho:** até 10 palavras, concreto e fácil, que dê vontade de ver o resto.
- **Batidas:** de 6 a 9. Cada batida tem:
  - o tempo aproximado (s);
  - o que aparece, de preferência uma **foto real** da lista;
  - a ação da **caneta vermelha**, quando houver;
  - a legenda, com **no máximo 8 palavras**, ou nenhuma.
- **Texto:** até ≈ 40–45 palavras no vídeo inteiro. Datas e nomes curtos viram etiqueta ou carimbo. As
  palavras-chave vão marcadas com `*asteriscos*`.
- **Fim:** marque qual batida é o fecho (a virada final).

## 3. Licenças

| aceito | condição |
| --- | --- |
| domínio público, Public Domain Mark, CC0 | de preferência; crédito de cortesia |
| CC BY | **crédito obrigatório** na descrição do post |
| CC BY-SA | crédito obrigatório; o recorte derivado também fica CC BY-SA |

**Nunca:** NC, ND, "fair use", sem licença clara, nem imagem gerada por IA no lugar de pessoa ou objeto histórico.

Armadilhas conhecidas:
- **Digitalizações da Gallica (BnF):** a BnF cobra o reuso comercial, mesmo de obra em domínio público. Para post
  com fim comercial ou anúncio pago, troque por um equivalente de acervo com Open Access.
- **British Museum:** o Commons às vezes marca domínio público, mas o museu publica as fotos como CC BY-NC-SA. Não
  use. Ache um equivalente (Wellcome Collection, Library of Congress).
- **Obra antiga marcada CC BY-SA no Commons** (a foto da página é de alguém): por segurança, credite.
- **Foto de objeto em museu** feita por um usuário do Commons: a licença é a da foto (em geral CC BY-SA), e o crédito
  vai para o fotógrafo, com o museu como cortesia.

## 4. Onde buscar

- **Wikimedia Commons**, pela API, com a licença conferida em `extmetadata`:
  `https://commons.wikimedia.org/w/api.php?action=query&titles=File:...&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=2000&format=json`,
  com um `User-Agent` que identifique o projeto. Se o original der erro 429, use o `thumburl` de 2000 px (a
  licença é a mesma).
- **The Met** (CC0): `https://collectionapi.metmuseum.org/public/collection/v1/search?hasImages=true&q=...`, só com
  `isPublicDomain`.
- **Smithsonian Open Access** (CC0), **Paris Musées** (CC0), **Rijksmuseum**, **Science Museum Group**.
- **Wellcome Collection** (IIIF, muitas imagens com Public Domain Mark): ótima para livros antigos, mapas e
  medicina.
- **Library of Congress** (gravuras, caricaturas, fotos antigas), **NASA** (domínio público), **Cornell** e
  **Flickr Commons** ("sem restrições conhecidas").

**Quantidade:** de 6 a 10 imagens por reel (pessoas que dê para recortar, documentos e jornais de época, mapas
antigos, lugares) e de 4 a 7 objetos (de preferência isolados, com fundo liso e ≥ 1200 px no lado maior).

## 5. Baixar e recortar

- **Antes de baixar, mostre a lista** (arquivo, origem, licença, tamanho) e espere o "pode" (REGRAS.md §8).
- Cada arquivo numa **pasta nova e vazia**: `baixados/<id>/arquivo.ext`. Use a versão de ~2000 px, ou o original se
  tiver menos de 15 MB. Leia com `python3 -I` e nunca execute nada que foi baixado.
- **Recorte local** (macOS 14+, sem rede e sem crédito):
  `swift "${CLAUDE_PLUGIN_ROOT}/motor/colagem/recorte.swift" baixados/<id>/arquivo.jpg pecas/<id>.png`.
  Fora do macOS, use a remoção de fundo do Higgsfield (com "pode").
- **Confira cada recorte** sobre fundo azul. Se ele pegar moldura, pedestal ou gente a mais, corte a entrada antes e
  refaça. Para tirar pedestal ou moldura embaixo, use `PC.recorte(..., corte_base=0.74)`. Um recorte ruim é pior que
  nenhum: descarte e diga.
- Se um objeto não existir em foto livre, diga isso e sugira um substituto real (ex.: sem sabre de oficial livre,
  vai o sabre de soldado do mesmo modelo).

## 6. O que entregar

- `roteiro.md`: fatos com fontes, gancho, batidas e legendas.
- `CREDITOS.md` (tabela): arquivo · o que é · origem (URL da página) · autor · licença · crédito. No fim vai a
  **linha pronta para a descrição do post**, só com os créditos obrigatórios (CC BY e CC BY-SA) e uma cortesia aos
  acervos.
- `pecas/`: os recortes PNG e as fotos JPG com os nomes que o `reel.py` espera.
- Uma folha de contato com todas as peças e o `id` de cada uma (`clpy ferramentas/reel.py --folha`).
