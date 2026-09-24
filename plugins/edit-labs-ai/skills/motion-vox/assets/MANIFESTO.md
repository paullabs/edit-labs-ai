# Kit de assets — MOTION-VOX v1

Estes são **a identidade**, não exemplos. Reaproveite-os; gere novos só quando a cena
pedir um objeto que não existe aqui.

Todos recortados com alfa, sem sombra embutida, sem texto. Reduzidos para 1400px no
lado maior — o suficiente para heróis de 800px em quadro 1080×1920.

## Props recorrentes — usar em todas as cenas

| Arquivo | O que é | Papel |
| --- | --- | --- |
| `BG_PAPER.png` | papel marfim pontilhado, 1080×1920 | fundo de toda cena de mesa |
| `A03_TAPE.png` | 4 tiras de fita crepe rasgadas | etiqueta, fixação |
| `A04_CLIPS.png` | 3 clipes de papel | prop periférico |
| `A10_SCRAPS.png` | 4 retalhos (milimetrado, manilha, branco, marfim) | contexto cortado nas bordas |
| `A05_CARD.png` | cartão de algodão branco, bordas rasgadas | montagem de foto, folha do wipe |

Style Bible §12 pede 2–3 props recorrentes em todo o vídeo. São estes.

## Objetos de cena

| Arquivo | O que é | Usado em |
| --- | --- | --- |
| `A02_CLOCK.png` | despertador, mostrador **sem números** | ponteiros desenhados em PIL |
| `A07_IDEA.png` | papel amassado com rabisco abstrato | ~~"ideia"~~ — **fere o E5 da Régua de gosto do kit (nada abstrato)**; só entra como papel amassado de verdade (rascunho jogado fora), nunca como símbolo de "ideia" |
| `A08_BOX.png` | caixa de papelão sem marca | "produto" |
| `A09_STACK.png` | pilha de cartões com clipe | alternativa a `A08` (prefira a `A08`) |
| `A12_KEYBOARD.png` | teclado gasto, teclas ilegíveis | programar, digitar |
| `A14_CRT.png` + `A14_CRT_screen.npy` | monitor CRT bege, tela apagada; `.npy` = quadrilátero da tela | terminal em perspectiva |
| `A15_MONEY_STACK.png` | maço de notas, impressão ilegível | ordem de grandeza |
| `A17_MONEY_FEW.png` | poucas notas soltas | ordem de grandeza |
| `A06_CAVE.png` | gravura de caverna em papel envelhecido | não usar — metáfora, não referente |

## Fotografias tratadas

| Arquivo | O que é | Tratamento |
| --- | --- | --- |
| `A11_NIGHT.png` | pessoa imersa no notebook, luz da tela | duotone azul `#2E82F7` |
| `A13_EMPTY.png` | mesma mesa vazia, máquina apagada | duotone cinza neutro |

O par é de contraste: **a cor é a diferença** entre quem está fazendo e quem não está.

## Ao gerar asset novo

O kit é a identidade, não o elenco: cada cena ganha o objeto da própria fala (`referencias/assets-sob-medida.md`),
e o que for aprovado vai para `biblioteca/` (`lib/biblioteca.py`). Siga `referencias/prompts-asset.md`. Regras que não podem faltar: fundo neutro escolhido
pelo maior afastamento de luminância, `no cast shadow on the backdrop`, e nenhum texto,
número, logo ou marca. Recorte com `lib/cutout.py`, tolerância lida no platô da varredura.

Um asset novo só entra no kit depois de passar a rubrica D1.
