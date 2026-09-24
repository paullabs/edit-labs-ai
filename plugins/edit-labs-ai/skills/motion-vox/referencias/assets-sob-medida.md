# Assets sob medida — cada cena com o objeto da própria fala

O kit (16 PNGs, `assets/MANIFESTO.md`) é a **identidade**, não o elenco. Ele dá o mundo — papel, fita, clipe,
mesa — e alguns objetos que servem quando são **literalmente** o que foi dito. O herói de cada cena é feito para
aquela fala.

## 1. De onde vem o herói (nesta ordem)

1. **Prova real** — marca, pessoa ou lugar nomeado: logo oficial ou foto licenciada (`fotos-reais.md`). Nunca gerado.
2. **Asset sob medida** — o substantivo que a pessoa disse, fotografado no estilo do kit (§3), gerado para esta cena.
3. **Biblioteca** — um asset sob medida de outro projeto (`biblioteca/CATALOGO.json`), só se ele **é** o objeto dito
   e ainda não apareceu neste vídeo nem no vídeo anterior da série.
4. **Kit** — só quando o asset do kit é literalmente o objeto dito (o teclado quando se fala de digitar, o relógio
   quando se fala de horas). Nunca como substituto genérico: a caixa de papelão não é "uma ferramenta", o cartão de
   algodão não é "um manual", as notas do kit não são "mais barato".

Pergunta de controle, cena a cena: *se eu tirar o áudio, o objeto na tela diz a palavra?* Se precisa de legenda
para ser entendido, é substituto — gere o objeto certo.

## 2. Contra a repetição (o verificador conta: E9 e E10)

| Regra | Limite | Onde se mede |
| --- | --- | --- |
| Herói do kit (A02, A06–A09, A11–A17) | no máximo **1 cena por vídeo** cada | `E9_heroi_repetido` |
| Papel de base (A05_CARD) | no máximo **2 cenas por vídeo**; o resto é papel sob medida | `E9_heroi_repetido` |
| Cenas cujo objeto principal é do kit | no máximo **40 %** das cenas | `E10_sob_medida` |
| Props recorrentes (A03 fita, A04 clipes, A10 retalhos, BG_PAPER) | livres — são o mundo, não o herói | — |

Papel é o que mais se repete. Tenha um **conjunto de papelaria** sob medida e revezado: folha A4 impressa, resma,
ficha pautada, bloco espiral, pasta manila, envelope, post-it, recibo de caixa, página de caderno, cartão de visita.
Cada um entra quando a fala pede *aquele* papel ("manual" → bloco espiral aberto; "bilhete" → post-it; "linhas
de prompt" → folha A4 impressa).

## 3. O mesmo mundo — DNA visual dos assets

Medido nos 16 PNGs do kit com `lib/checar_asset.py`:

| Medida | Faixa do kit | Asset novo deve ficar |
| --- | --- | --- |
| saturação média | 1–106 (mediana 43) | ≤ 110; acima disso é cor de propaganda |
| pretos p5 (luminância) | 16–235 | coerente com o material (papel claro ~120–235, eletrônico ~15–60) |
| alfa médio no anel de 3 px | 221–232 | 215–235 (abaixo = halo, acima = borda de tesoura) |
| lado maior | 1087–1400 px | ≥ 1400 px antes do recorte (gere em 2k) |

O que não pode faltar em todo asset:
- **fotografia documental de objeto**, vista de cima (top-down), luz difusa uniforme, sem sombra projetada no fundo;
- **matéria visível** — fibra de papel, metal escovado gasto, tecido, plástico fosco com uso; nada novo de loja;
- **cor abafada** (80 % neutros), acabamento fosco, sem brilho especular;
- **fundo liso neutro** escolhido pelo contraste de luminância (#8A8A8A para objeto claro, #D8D8D8 para escuro);
- **nenhum texto, número, logo ou marca** — o que precisar ser escrito entra depois, em PIL, a marcador ou impresso;
- **mão de gente** quando a fala tem gente fazendo algo (Régua de gosto do kit, E6): a mão entra pela borda, pulso cortado.

## 4. Esqueletos por família (gpt_image_2 · 1:1 · 2k · high · 2–3 variantes)

Todos terminam com o bloco fixo:

```
Even soft diffuse light, no cast shadow on the backdrop, subject fully within frame (except where it enters from an
edge), clear separation from background. Muted desaturated color, matte finish, no glossy highlights. Documentary
object photograph. No text, no letters, no numbers, no symbols, no brand, no logo anywhere. No glossy 3D render,
no neon, no glow, no gradients, no HDR, no AI-polished look.
```

| Família | Começo do prompt (troque o que está entre < >) |
| --- | --- |
| **Mão com objeto** | `Single isolated subject centered on a completely flat plain neutral <medium gray #8A8A8A \| light gray #D8D8D8> backdrop. A real human hand entering from the <left \| bottom> edge of the frame, <gesto: holding / pinching / pushing / typing on> <objeto e estado>, photographed straight from directly overhead, perfect top-down view. Natural skin texture, <material do objeto e desgaste>.` |
| **Duas mãos** (negociar, entregar, cumprimentar) | `…Two real human hands, one entering from the left edge and one from the right, <shaking hands / passing a folded sheet of paper / pointing at the same spot>, photographed straight from directly overhead…` |
| **Papelaria** | `Single isolated object… <a thick ream of blank printed-looking A4 sheets, slightly fanned / an open spiral-bound notebook with blank ruled pages / a small square sticky note, muted pale yellow, one corner curling / a kraft price tag with a cotton string / a manila folder, slightly open / a paper receipt, curled>, photographed straight from directly overhead. Slightly worn uncoated paper with visible fiber, soft uneven edges. All surfaces completely blank, no printing.` |
| **Eletrônico** | `Single isolated object on light gray #D8D8D8… <a smartphone / a laptop / a wired computer mouse / a USB cable>, top-down, screen completely dark and blank, switched off, no reflections of any interface, <muted graphite body with worn edges>. Keys or buttons worn to illegible smudges.` |
| **Dinheiro e preço** | `…a few folded banknotes with illegible worn printing / a small pile of worn coins / a kraft price tag with string…` — preço escrito depois em PIL ("$$$" × "$"), nunca pedir número ao gerador |
| **Ferramenta e casa** | `…<a worn wrench / a padlock / a key on a ring / a coffee mug / a desk lamp switched off>, top-down, <material> with honest signs of use…` |
| **Papel impresso** (a folha cheia, o recorte de texto) | como a papelaria, mas o bloco fixo troca "no text, no letters" por **"No readable text, no headline"**: com a forma original o modelo devolve a folha em branco — a proibição briga com o "tiny illegible printed text" do corpo do prompt. **E a folha pede sempre "clear white margins on all four sides" + "separated paragraph blocks with the last line of each shorter"**: sem isso o modelo enche de borda a borda e, a 300 px, a página lê como retângulo listrado, não como página — ninguém lê a letra num preview, o que faz reconhecer é a margem e o ritmo do parágrafo. Asset já gerado sem margem se remonta no código sobre a folha do kit, com recortes da própria tinta |
| **Mostrador** | `…plain unmarked dial with only twelve small thin tick marks, absolutely no numbers…` — ponteiros redesenhados em PIL |

Pessoa inteira (corpo, rosto) só por foto real licenciada ou pela figura de papel do kit (`voxlab.persona`). Rosto
de gente real **nunca** é gerado.

## 5. Brief de asset (seção G do plano e `00_brief/PROMPTS.md`)

Uma linha por asset, antes de gerar:

| asset | cena · palavra | o que é, literalmente | família | fundo | variantes | substitui (kit) | custo |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MANUAL_ESPIRAL | M3 · "o manual" | bloco espiral aberto, páginas pautadas em branco | papelaria | #8A8A8A | 2 | A05_CARD | <créditos × variantes> |

Nome em MAIÚSCULAS, o que é (não para que serve), e `_v1…_v3` para as variantes.

**Nome não pode começar com `LOGO_` nem `FOTO_`**: esses dois prefixos são de prova real, e a biblioteca recusa
qualquer arquivo com eles (licença é por projeto). Foto impressa *gerada* chama-se `PAPEL_FOTO_*`, não `FOTO_*` —
com `FOTO_*` a biblioteca recusa o registro.

## 5b. Os dois parâmetros que se erram uma vez

- **`resolution`**, não `size`: no gpt_image_2 o parâmetro é `resolution` ("1k" \| "2k" \| "4k"). `size` é aceito e
  descartado **em silêncio**, e a geração sai em 1k (1024 px), abaixo dos 1400 px desta página. `quality: "high"` é
  campo à parte. Confira o lado maior da primeira imagem antes de mandar o resto.
- **A proibição de texto**: veja a família "papel impresso" na §4.

## 6. Depois de gerar

1. `cutout.py --sweep NOME_v1` → platô → `cutout.py NOME_v1 NOME_v2 …`
2. `checar_asset.py NOME_v1 …` — as medidas da §3 dentro da faixa; tiles a 100 % sem texto de IA.
3. D1 do Diretor escolhe a variante (cita `07_assets/qa/`). Reprovou: uma alteração no prompt, até 3 vezes.
4. **Biblioteca:** o aprovado vai para `biblioteca/` com `python3 lib/biblioteca.py registrar 07_assets/cutout/NOME_v1.png --o-que "…" --tags "…" --prompt-arquivo 00_brief/PROMPTS.md`.
   Antes de gerar, procure: `python3 lib/biblioteca.py buscar "manual"`. Usar do acervo: `python3 lib/biblioteca.py usar NOME`
   (copia para `07_assets/cutout/` e anota o uso — é o que impede o mesmo asset em vídeos seguidos).

## 7. Por que isto existe

Um vídeo que apoia o objeto no mesmo cartão de algodão (A05_CARD) em quase toda cena — logo, páginas, cartões de
passo, manual, fichas, bilhete — faz quem assiste ler "cartão" como "cartão", não como manual, prompt ou bilhete,
e a repetição pesa. O objeto certo, fotografado no mesmo mundo, resolve os dois de uma vez.
