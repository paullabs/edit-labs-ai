# Ficha de estilo: vox-clean

**Quando usar:** explicar dado, mecanismo ou comparação com pessoas, gráficos e documentos; tom editorial, sério, limpo. É o estilo do "Two Parties" e do "Epigenetics". Bom para **números do corpo** (pressão, doses, comparações entre grupos) e para **pessoas sem rosto**.

**Evidência:** R03 (a fundo, medido), R25 Porsche estilo Vox (a fundo, medido), R24 Vox squeezing (a fundo), R02 (vista), I02 e I03 (guias internos). Paleta: `paletas/paletas.json` → `vox-two-parties`.

## O sistema
| item | regra |
|---|---|
| papel | `#F7F6ED`, liso; **~86% da tela vazia**; grão só nos objetos |
| cor | preto/cinza para o objeto + **no máximo 4 acentos**, cada um com um **significado fixo** no vídeo |
| personagem | **foto real em preto e branco**, recortada, **meio-tom nos cinzas**, **sem rosto**, **cabeça em cor sólida com degradê que some no peito** |
| sombra | elipse cinza achatada no chão, sem desfoque grande |
| texto | **dois estilos só**: serifada pesada e condensada (títulos, números, em moldura preta quando for tese) e **manuscrita rosa com seta** para anotar |
| gráficos | objetos: barras com eixo, **textura como dado** (padrão de carinhas, meio-tom), mapa em **cor chapada com contorno fino escuro** |
| documentos | **fotocópia em tela cheia**, letras enormes de meio-tom ao fundo, **marca-texto amarelo que cresce** da esquerda para a direita em ~0,4 s |
| composição | uma coisa por vez; **grade regular** para multidão (3×6, 2×5); marcas de régua pontilhadas nos cantos |
| movimento | **entrar em fila com pop curto**, **trocar no lugar** (rosca vira figuras), mudar de cor, reagrupar; a figura quase não anda; confete amarelo no clímax |
| tremor | muito leve (2–3 px a cada ~0,4 s) |

## No nosso motor
- Fundo: `PC.papel_mundo` trocado para `#F7F6ED` liso (hoje é o bege `#E9DDC0`); desligar a vinheta de papel e deixar só a de câmera a ~2%.
- Personagem: `papelizar` com `borda=0`, `cor` em cinza, **máscara de degradê** do topo (acento sólido → transparente em ~1/3 do corpo); sombra `(6, 14, 0.15)` achatada (`sombra` com `sdy` pequeno).
- Boil `obj` com amplitude menor que a atual (≈0,5 px).
- Marca-texto: camada `Traco` amarela com `trim` (cresce); texto por `C.legenda`/rótulo no estilo manuscrito.
- Grade: `K.pilha` ou várias `C.fixo` com `entrada em fila` (`q` por pessoa a cada 3–4 quadros).

## No invideo
Imagens com alfa e chaves com `hold`; marca-texto como forma retangular com `trim_shape_path`; textura de dados como imagem; o degradê do personagem já vem no PNG.

## Riscos
- Sem rosto: bom para dados, **ruim para emoção** (não usar quando a pessoa precisa ser reconhecida).
- Muito vazio: exige que **cada cena tenha um centro óbvio**; se o objeto for pequeno demais ele some (regra: herói ≥ 600 px).
- O Vox é da Vox: **aprender o sistema, não copiar as imagens**.
