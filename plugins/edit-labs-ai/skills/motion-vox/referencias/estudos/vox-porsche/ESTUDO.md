# Estudo — "VOX-Style Animated Documentary | The History of Porsche"

Peça de portfólio de Hanna Herasimova (MOTION LADY, Ucrânia).
3min16s, 1920x1080 a 30fps, feita inteira em After Effects. Declara na própria peça que
a base é "o famoso estilo de animação do canal VOX".

Procedência: `https://www.behance.net/gallery/221556905` · vídeo `youtube.com/watch?v=FwRtt4nhCDE`

Material de apoio (não vem com o plugin): 32 styleframes (bf01–bf32), vídeo completo,
transcript e legendas, grades de contato e rajadas de frame.

**Por que este estudo existe.** É a peça mais próxima do que a skill tenta fazer, feita
por alguém de fora, com as escolhas todas visíveis. Serve para duas coisas: confirmar o
que já está certo em `identidade.md` / `registros.md` / `boil.md`, e medir o que a skill
hoje só estima. As seções finais separam o que é confirmação do que é proposta.

---

## 1. Narrativa — a cronologia é o esqueleto

463 palavras em 196s. A história cobre 123 anos (1900 → 2023) e é contada em **capítulos
marcados por ano**, sempre na mesma ordem interna:

```
ANO em tela cheia  →  o que aconteceu  →  a prova (foto/documento)  →  a ficha do carro
```

Os capítulos: abertura conceitual (0:00) · Stuttgart e o fundador (0:11) · 1900, o
híbrido (0:22) · 1948, Ferry e o 356 (0:32) · 1963, o 911 (0:55) · expansão e os
modelos 914/924/928/944 (1:14) · 1996, Boxster (1:50) · 2002, Cayenne e a virada de SUV
(2:10) · Taycan e os $43bi (2:39) · fecho em "Legacy" (2:58).

**O ano é o único elemento que sempre ganha a tela inteira.** 1900, 1948, 1963, 1969,
1996 — cada um em cartela própria, sem competir com nada. É o que deixa o espectador
saber onde está sem que a narração precise dizer "agora vamos para".

**O refrão.** A "ficha de modelo" — nome em marca-texto amarelo, preço de lançamento em
serif menor, carro recortado em silhueta lateral sobre papel claro — repete **seis vezes
idêntica** (356, 914, 924, Panamera, Macan, Boxster). Repetição deliberada: vira a
unidade de medida da peça. Quando ela aparece, o espectador já sabe que é "mais um
modelo entrando na linha", e a narração pode ser curta.

**A abertura não é cronológica.** Os primeiros 11 segundos são cinco palavras soltas —
*passion, speed, innovation, style, quality* — cada uma sobre um vídeo real diferente,
uma por cena. Só depois disso a história começa. É a promessa antes do primeiro dado.

---

## 2. O dado mais importante: a fala é lenta, a imagem é rápida

```yaml
ritmo_de_fala:      141 palavras/min      # pausado, quase conversa
cortes_por_minuto:  33                    # um corte a cada 1,8s
duracao_mediana:    1.23 s
cenas_abaixo_1.5s:  61%
cenas_acima_4s:     10%
palavras_por_cena:  4.3
```

Medido com detecção de cena (`ffmpeg select=gt(scene,0.30)`, 108 cortes).

**4,3 palavras por cena.** É a régua que sustenta a peça inteira. Nenhuma imagem precisa
carregar mais de uma oração — e por isso nenhuma imagem precisa ser complicada. Uma
cena = um substantivo.

A distribuição importa mais que a média: 61% abaixo de 1,5s convivendo com 10% acima de
4s. Os planos longos são exatamente os que **não** têm o que ler — footage real correndo,
mesa de pesquisa em pan. Cena com texto é curta; cena sem texto respira.

---

## 3. Movimento — 12 fps, medido

Diferença de luminância frame a frame, quatro trechos de 2s (`t=37,2s / 78 / 112 / 150`):

```yaml
frames_identicos_ao_anterior:  56% – 78%
intervalo_entre_redesenhos:    alterna 2 e 3 frames
fps_efetivo:                   11.8 · 15.0 · 12.1 · 13.4   -> ~12 fps
razao_frame_parado/movente:    ~80x
```

O trecho mais limpo (t=112s) dá 12 intervalos de 2 frames e 11 de 3 frames — **nada
mais**. Isso é 12fps servido sobre uma timeline de 30fps pela alternância 3-2-3-2, que é
a única forma inteira de fazer 30/12 = 2,5.

**Consequência prática:** entre dois redesenhos o quadro é *bit a bit idêntico*. Não há
micro-movimento, não há easing contínuo, não há grão que respira sozinho. Tudo — objeto,
tipografia, câmera, grão — segura junto e salta junto.

A referência usa **um relógio só, a 12** — é o que o kit adota (§8, proposta 1).

**Zoom em degraus, não push contínuo.** Numa rajada de frames do trecho 44,3–45,7s, a
mesma foto do 356 salta de escala e de enquadramento a cada passo — ora tela cheia, ora
card com borda amarela sobre papel quadriculado. O que a detecção de cena leu como "20
cortes em 5 segundos" são saltos de escala da mesma imagem. É movimento por degrau
visível, não por interpolação.

---

## 4. Como se explica uma coisa — quatro mecanismos, e só

Nenhum diagrama novo é inventado. Tudo é **material de arquivo real + anotação por cima**.

**a) Marca-texto amarelo sobre o que já está escrito.** O mecanismo mais usado da peça.
Jornal de época, anúncio, manual — o documento entra inteiro e o amarelo marca as três ou
quatro palavras que importam (`bf13`, `bf20`). Em `bf20` são três marcações em cascata na
mesma página: manchete, depois uma frase do corpo, depois a data. Guia a leitura de um
documento real sem redesenhar nada.

**b) Lente amarela circular.** Círculo amarelo translúcido em multiply sobre a região
relevante de uma foto, mais linha de chamada preta fina até uma etiqueta em marca-texto
(`bf19` "rear-engine design", `bf22` "powerful six-cylinder engine"). Substitui a seta.
Funciona melhor que seta porque **colore** a coisa citada em vez de só apontar para ela —
a parte relevante fica amarela e o resto continua como estava.

**c) Círculo desenhado à mão.** Duas passadas visíveis, jitter de mão (`bf10` marcando
Ferry Porsche numa foto de dois homens, `bf23` marcando o platô de 1998–2001 no gráfico,
`bf25` circulando o ano). Usado para **selecionar dentro de um conjunto** — qual dos
dois, quais dos oito anos.

**d) Legenda de rodapé com ▶.** Serif itálica, triângulo amarelo à esquerda, na base do
quadro, sobre footage real correndo: *"Porsche 911 had a top speed of around 210 km/h"*.
É onde vai o dado numérico **secundário** — o que enriquece mas não merece cena própria.
Aparece pelo menos seis vezes.

**A regra por trás dos quatro:** a prova é sempre um material real; a anotação é sempre
amarela; e a anotação nunca redesenha o que a foto já mostra.

---

## 5. Registros visuais observados

| Registro | Onde | Observação |
| --- | --- | --- |
| Cartela de ano | `bf05` `bf09` `bf12` `bf25` | tela inteira, ano em serif, sempre sozinho |
| Ficha de modelo | `bf11` `bf18` `bf21` | o refrão — nome + preço + carro em papel claro |
| Documento de época | `bf13` `bf20` | jornal/anúncio real com marca-texto |
| Foto de arquivo anotada | `bf10` `bf19` | lente amarela ou círculo à mão |
| Mapa | `bf03` `bf04` `bf09` | do mundo → do país → da cidade, em zoom sucessivo |
| Diagrama técnico | `bf22` | line art de manual + lente amarela + chamada |
| Gráfico de barra | `bf23` | barras carvão, grade amarela, fonte citada, círculo à mão |
| Footage real com legenda ▶ | `bf07` `bf08` `bf30` | card com cantos arredondados, halftone |
| Registro escuro | `bf09` `bf26` | massa preta, um único ponto luminoso |
| CRT / TV retrô | `bf01` `bf15` `bf16` | duas variantes: moldura de tubo e aparelho ilustrado |
| Mesa de pesquisa | `bf31` `bf32` | fotos, fita amarela, caneta — em perspectiva, foco raso |
| Citação | `bf06` `bf24` | serif itálica + recorte da pessoa com halo amarelo |

**A mesa de pesquisa não é o chão da peça — é o fecho.** Aparece nos últimos 15 segundos,
em pan, em dois ângulos, recolhendo os modelos já citados (911, 356, Macan) como quem
espalha o material na bancada no fim. Na skill ela é o registro-base; aqui é a coda.

**Regra de alternância confirmada.** Em nenhum momento dois registros iguais se seguem —
exceto a ficha de modelo, que é refrão declarado e sempre separada por outro registro.

---

## 6. Estética — o que está medido no pixel

**Paleta.** Um amarelo só (≈`#EDE300`, mais saturado e mais verde que o `#DBD653` da
skill), papel bege/marfim, tinta carvão-azulada, e o preto profundo do registro escuro.
Nenhuma segunda cor de acento na peça inteira — não há azul, não há vermelho, exceto
`bf23` onde o círculo de anotação é vinho escuro e os rótulos numéricos idem.

**Tipografia: serif, não condensada.** A diferença mais visível para a skill atual. Toda
a peça roda em **serif de alto contraste** (família didone/Playfair) — títulos, anos,
fichas, citações. A itálica da mesma família faz as legendas ▶ e as etiquetas de chamada.
Não há sans condensada em lugar nenhum; a única sans é o rótulo "Ferry Porsche" em
`bf10`. A skill usa Archivo Narrow (condensada) como manchete e Fraunces (serif) só para
número — aqui a hierarquia é o inverso.

**Acabamento — a assinatura é a aberração cromática.** Muito mais forte que a "radial
leve, nula no centro" da skill: em `bf31`/`bf32` o deslocamento RGB é visível em todo o
quadro, inclusive no centro, com franja ciano/laranja de vários pixels nas bordas de cada
foto. Some a isso:

```yaml
halftone:            trama de pontos visível sobre TODA imagem fotográfica
grao:                pesado, presente também nas áreas chapadas
vinheta:             forte nas cartelas, orgânica (riscos e queimado) no registro de arquivo
moldura_CRT:         curvatura de tubo + franja RGB nas quatro bordas
halo_amarelo:        contorno irregular, à mão, em recortes de pessoa
cantos_de_corte:     crop marks em L, tracejados, como marca de diagramação
```

**Superfície de papel de verdade.** `bf17` não é uma textura chapada: é papel amassado
fotografado, com dobras que produzem sombra real, e o texto assentado por cima seguindo
as dobras. A peça usa papel como *objeto*, não como fundo.

---

## 7. O que este estudo confirma na skill

- **Alternância de registro** (`registros.md`) — a peça obedece sem exceção.
- **Nunca caractere a caractere** (`identidade.md`) — a legenda da rajada de frames entra em
  blocos de palavras com fundo amarelo, nunca letra a letra.
- **Gráfico de barra para número confiável** (`registros.md`) — `bf23` faz exatamente isso,
  e acrescenta duas coisas que a skill não pede: **a fonte citada** sob o título
  (`stuttcars.com`) e **o círculo à mão** marcando qual parte da série a fala comenta.
- **Insert como herói da janela** (`identidade.md`) — toda foto de pessoa ou documento
  ocupa metade do quadro para cima. Nenhum selo pequeno decorando outro objeto.
- **Registro escuro resolve a massa** (`armadilhas.md`, "luz sem glow") — `bf09` e `bf26`
  são as duas únicas cenas de massa escura, e ambas trazem um único ponto luminoso.
- **Boil como salto, não como ondulação** (`boil.md`) — confirmado: os frames entre
  redesenhos são idênticos, não há evolução contínua.

## 8. O que este estudo propõe mudar — para laudo

Proposta vira regra por laudo escrito do Diretor, não por gosto (`IDENTIDADE.md`), e
mudança de fonte/paleta/acabamento sobe a versão. As propostas 1, 2, 3 e 6 já estão no
kit: relógio único a 12 fps (`MOTION_FPS = 12`, `RELOGIO_UNICO = True`),
`kit.footer_caption`, `kit.yellow_lens` e `kit.year_card` (ver `registros.md`).

| # | Proposta | Custo | Sobe versão? |
| --- | --- | --- | --- |
| 1 | **Um relógio só a 12fps** em vez de `motion_fps: 16` + boil 9fps | recalibrar `voxlab` | não (método) |
| 2 | **Legenda de rodapé `▶`** como registro novo, para dado numérico secundário | asset + regra | não |
| 3 | **Lente amarela circular** como alternativa à seta em foto real | função nova em `voxlab` | não |
| 4 | **Marca-texto sobre documento real** — 2-3 marcações em cascata guiando a leitura | regra | não |
| 5 | **Fonte citada no gráfico de barra**, sob o título | regra em `registros.md` | não |
| 6 | **Cartela de ano/marco em tela cheia** como separador de capítulo | regra | não |
| 7 | Hierarquia tipográfica **serif-first** em vez de condensada-first | fontes | **sim, v2** |
| 8 | Aberração cromática **forte e uniforme** em vez de radial-leve | acabamento | **sim, v2** |

As seis primeiras são método e regra — cabem na v1. As duas últimas mudam o visual e são
outra identidade, não um ajuste: valem como estudo, não como correção.

**O que NÃO copiar.** A peça tem 3min16s de narração contínua sem locutor em quadro, com
footage licenciado de sobra. A skill trabalha com talking head e cutaway sobre fala real,
e a régua de 4,3 palavras por cena aplicada a uma fala espontânea produziria corte a cada
segundo em cima de alguém falando — que é tique, não ritmo. A lição transferível é a
**proporção** (fala calma, imagem rápida), não o número absoluto.
