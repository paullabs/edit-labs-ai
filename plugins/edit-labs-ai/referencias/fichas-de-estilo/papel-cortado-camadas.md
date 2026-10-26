# Ficha de estilo: papel-cortado-camadas

**Quando usar:** o corpo (ou qualquer objeto) feito **como pilha de papéis cortados**, cada camada de uma cor, com **sombra entre elas**, como se fosse um relevo. É o nosso "camadas registradas" levado ao extremo da arte; combina com **abas que levantam**.

**Evidência:** R13 Gildersleeve (**citada**: li o artigo; **não vi as imagens**), I01 manequim 1890 (a fundo, nosso). Esta ficha é um **ponto de partida a confirmar** olhando o livro.

## O sistema
| item | regra |
|---|---|
| construção | cada órgão ou sistema é uma **pilha de recortes** (silhueta → forma interna → detalhe), cada um em **um bloco de cor** (Gildersleeve: "layered paper and blocks of colour") |
| cor | poucos blocos por obra, com contraste entre camadas vizinhas |
| sombra | **sombra projetada pequena entre cada camada** (profundidade física) |
| movimento | as camadas **se afastam e voltam** (explode / monta) com a sombra crescendo; a **camada de baixo é mais interessante que a de cima** |
| fidelidade | **consultor científico** para cada peça (R13 usou) |

## No nosso motor
- Já temos: `K.explode`, `K.levanta`, `K.destaca/pousa` e o 3D renderizado em camadas registradas (Blender, skill `colagem-camadas`).
- Novo: **recorte de órgão como silhueta em degraus de cor** (3 a 5 níveis) e **sombra entre níveis** (`sombra` por camada, animada por `sdy/sbl/sop`).
- Boil leve por camada, **borda de tesoura fina** (papel cortado a laser seria mais limpo: boil quase zero).

## Riscos
- Gerar a pilha em 3D (Blender) e papelizar em degraus é trabalho novo; começar por **um órgão** (coração) para validar o olho.
- Parece "ilustração", não "gravura": decidir cedo se é este ou o `gravura-bw-acento`.
