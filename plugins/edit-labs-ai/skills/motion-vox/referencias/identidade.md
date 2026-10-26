# Identidade visual — estilo Vox explainer

Extrato operacional da identidade: o que o kit aplica em toda cena.

## Canvas

```yaml
canvas: 1080x1920
fps_timeline: 24          # o master pode sair em outra cadência
margens_laterais: 96px
exclusao_direita: 120px   # x > 960 — vale para TEXTO e herói, não para prop sangrando
exclusao_inferior: 260px  # y > 1660
espaco_negativo: 25-40% no registro research-desk
```

Fluxo vertical: 7–18% tema · 18–65% evidência · 55–78% anotação · 72–88% conclusão.

**Tamanho mínimo de um insert de identificação.** Logo pequeno sai ilegível: foto ou logo
que serve pra IDENTIFICAR quem/o que foi citado (rosto de pessoa, marca, símbolo)
precisa ser o **HERÓI da própria janela**, nunca um selo pequeno decorando outro objeto.

```yaml
insert_hero: 620px de largura      # ~57% do quadro — o mesmo porte do A05_CARD
insert_wordmark: 760px             # logos em texto largo/baixo (ex.: "SPACEX") pesam
                                    # menos por área que um icone — compense na largura
```

Se um logo só cabe pequeno ao lado de outro objeto, a resposta não é encolher o logo —
é dar a ele a **própria cena** (insert-burst, ver `transicoes.md`), do tamanho de
qualquer outro insert. Duas cenas de 1s cada, uma por vez, sempre lêem melhor que duas
coisas pequenas competindo no mesmo quadro.

**Sobre espaço negativo:** a faixa 25–40% descreve a família *research desk* — mesa
coberta de papéis sobrepostos. No registro *clean editorial*, com 4 a 6 objetos
discretos, 20–33% de ocupação é o que sai, e as referências aprovadas do kit são
igualmente arejadas. Não persiga o número; persiga a distribuição.

## Paleta

```yaml
paper:      "#D9D8D1"    light:  "#F4F0E8"
ink:        "#373639"    charcoal: "#29292B"
yellow:     "#DBD653"    blue:   "#2E82F7"
red:        "#C94850"    green:  "#31C25B"
tape:       "#BFBBAE"
```

Proporção: **80% neutros · 15% massa escura · 5% acento**. Um acento principal por cena.

Cenas de papel tendem a ficar sem massa escura (medido: 1,4% e 4,8%). Uma **fotografia
noturna** resolve — ver `luz sem glow` em `armadilhas.md`.

## Tipografia

| Função | Fonte (macOS) | Corpo |
| --- | --- | --- |
| Manchete condensada | `DIN Condensed Bold` | 80–112px |
| Etiqueta manual | `Bradley Hand Bold` + stroke | 46–124px |
| Mono técnica | `Menlo` | 22–38px |
| Serif expressiva | `Georgia Bold` | 96–152px |

Máximo três famílias por quadro, quatro funções no projeto.

**Modo de entrada do texto:**

- editorial → **bloco** (opacidade 0→1 + subida de ~14px, 6–10 frames)
- marcador → **write** (frente de revelação esquerda→direita, ponta de caneta)
- **nunca caractere a caractere** em tipografia editorial: é máquina de escrever, efeito
  de template, fora da identidade

## Etiqueta amarela

Etiqueta em papel amarelo (tipo marcador/sticky note) é o elemento mais repetido em toda
referência Vox (estudo Porsche: bf01, bf04, bf11, bf13, bf15, bf17, bf20). A **fita crepe
bege** do kit (`A03_TAPE`, RGB medido 184·167·145) não faz esse papel, e o amarelo
`#DBD653` só em sublinhado fino deixa o acento em 0,1–0,8% do quadro, contra os 3–7% da
faixa do estilo.

`kit.yellow_label(size, texto, ...)` desenha a faixa como **pincelada** (borda de baixa
frequência, leve rotação, grão) e entra como traço — esquerda→direita nos primeiros 55%
do progresso; o texto entra em bloco depois. `outline=True` fecha o retângulo fino de
tinta por cima (bf01, bf15). Faixa e texto compartilham a semente de boil: são um objeto.

```yaml
uso:        nomear a evidência · marcar a palavra da manchete · ano/marco de capítulo
nao_usar:   em toda cena — acento raro é acento (armadilha 45). Uma por cena, no máximo
fonte:      F_COND (manchete) ou F_SERIF (ano, número). Marcador continua na fita crepe
```

## Sombras — por classe de material

```yaml
papel:        dy 6   blur 14  opacidade 0.15
cartao:       dy 11  blur 24  opacidade 0.17
objeto_alto:  dy 20  blur 32  opacidade 0.20
fita:         dy 3   blur 9   opacidade 0.11
sobre_video:  dy 14  blur 26  opacidade 0.42   # precisa cravar mais, senão flutua
```

Nunca a mesma sombra em todas as camadas.

## Movimento

```yaml
entrada:        8-18 frames
overshoot:      2-4%
stagger:        2-4 frames entre objetos
camera_push:    100 -> 103-106%
hold_final:     8-18 frames
easing_pouso:   cubic-bezier(0.20, 0.80, 0.20, 1.00)
easing_traco:   velocidade quase constante — caneta não desacelera no fim
easing_saida:   aceleração (t^2.4)
motion_fps:     12     # um relógio só com boil e grão, não os fps
                       # reais da fonte — a vibe de stop-motion da Vox. Conteudo, boil e
                       # grao prendem juntos (um relogio so); flash de transicao fica fluido.
```

**Mínimo de 1 segundo no ar, sem exceção.** Qualquer elemento central de uma cena (o
herói, o dado, o símbolo que carrega a ideia) tem que ficar
**legível por pelo menos 1s corrido** — não 1s de janela total, 1s em que ele já está
totalmente resolvido na tela, dando tempo do cérebro processar antes de sumir. Um
símbolo que pisca em 0,5s e some é **reprovado na hora**, mesmo que o resto da cena
esteja certo. Isso é um teto duro sobre densidade: se a janela de tempo real disponível
(a fala + o silêncio ao redor) não cabe 1s de leitura depois do elemento estar pronto,
**a cena não existe** — não force um formato encolhido só para bater a régua de
densidade. Prefira nenhuma cena a uma cena rápida demais para ler.

**A abertura do clipe nunca é motion.** O primeiro quadro que o espectador vê é sempre
o rosto de quem fala — nunca um cutaway, nunca uma cartela cobrindo o vídeo. Se a
primeira fala já dá gancho pra motion (ex.: a pergunta-título do clipe), ele pode entrar
dentro do primeiro segundo, mas só como **overlay sem fundo**: o vídeo real continua
visível por baixo, o gráfico entra por cima (transparente, ancorado na fala), nunca uma
cutaway de mesa de papel substituindo o quadro inteiro. `09_plates/` guarda os frames
reais extraídos pra esse caso — ver `lib/render_template.py`, shots com `cutaway=False`.
Cutaway de tela cheia só depois que o vídeo real já apareceu pelo menos uma vez.

Verbos permitidos: pousar, deslizar, revelar, desenhar, conectar, comparar, aproximar,
afastar, segurar.

Câmera e objeto são operações **separadas**: ou a câmera aproxima, ou o objeto cresce.
Nunca as duas.

**Zoom por insert, não só por cena.** Quando uma cena mostra vários inserts em sequência
(`_swap_flash`, ver `transicoes.md`), cada insert ganha o **seu próprio** ciclo de
câmera — reinicia do zero no frame em que ELE entra, não um push único calculado sobre
o frame absoluto da cena inteira. Sem isso, o segundo/terceiro insert herda só a cauda
de um movimento que já ia longe, e lê como estático. `amt` de 0,05–0,08 (5–8% de
aproximação) e `dur` cobrindo a vida inteira do insert é a calibração do kit.

## Proibições

neon · glow · bloom · HDR · gradiente decorativo · 3D plástico · dashboard SaaS ·
card arredondado sem função · partículas de "IA" · glitch como transição · impacto de
câmera em toda frase · tudo centralizado · movimento constante · texto repetindo a
narração · objeto flutuando sem contato · linha ou seta que não leva a nada
