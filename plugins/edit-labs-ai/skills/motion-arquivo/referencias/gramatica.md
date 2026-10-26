# Gramática do movimento — Família A (arquivo em papel)

**Índice**
1. Tempo · 2. Ritmo de corte · 3. Câmera · 4. Objetos · 5. Texto · 6. Passagem de plano
7. Composição e cor · 8. Acabamento · 9. Batida → plano (o mapa para qualquer assunto)
10. Números (consulta rápida)

Tudo aqui saiu de medição quadro a quadro do reel da Hedy Lamarr (32 s, 23 planos), com a
mesma régua nos dois lados: o nosso passa pela mesma entrega do original (720p, x264
~1,26 Mbps) antes de medir. Cada regra diz o porquê. O que o estilo **é**, em uma frase:

> **Um documentário de arquivo que anda a 10 quadros por segundo, em que a câmera nunca
> para, cada palavra dita vira um evento na tela e o corte se esconde no movimento.**

A dinâmica são três camadas de movimento ao mesmo tempo, sempre:

| camada | o que faz | ritmo |
| --- | --- | --- |
| **câmera** | deriva lenta ou revelação que assenta no sujeito | contínua, o plano inteiro |
| **eventos** | palavra, letra, objeto, cursor, caixa entram | a cada 0,2–0,6 s, presos à fala |
| **grade** | tudo isso amostrado a 10 qps | a cada 0,1 s |

Plano sem uma das três fica "parado" ou "liso demais" — e já não é a Família A.

---

## 1. Tempo

- **O quadro inteiro anda a 10 qps**: o conteúdo só muda nos quadros `n % 3 == 2` (entrega a
  30 qps, cada estado dura 3 quadros) e o **corte também cai nessa grade**.
  Por quê: medido quadro a quadro no Hedy; é o que dá o ar de arquivo animado à mão e
  esconde a costura de composição. O grão congela junto com o quadro.
- **A palavra aparece no primeiro degrau da grade depois que começa a ser dita.**
  Por quê: confere em 4 de 5 palavras do trecho medido; adiantar parece legenda, atrasar
  parece erro de sincronia. `ferramentas/batidas.py` calcula esse degrau para cada palavra.
- **Fade contínuo amostrado na grade**: quando uma palavra entra com fade, o fade começa no
  instante EXATO da fala (não no degrau) e dura 0,2 s; a grade só amostra.
  Por quê: no roteador, BEHIND chega a 41%, YOUR a 8% e WI-FI. a 6% no primeiro degrau — cada
  uma numa fase diferente. Um fade linear de 6 quadros a partir do início da fala reproduz
  os três (`planos.fade_palavra`).
- **Elemento de lista antecipa a fala** em 2–7 quadros (a caixa já vem deslizando quando a
  palavra começa); **palavra no papel chega depois** (degrau seguinte).

## 2. Ritmo de corte

- **Gancho: três cortes em 1,6 s** (0,67 / 0,40 / 0,50 s). Depois, plano mediano de 1,3 s
  (0,7–2,7 s). Plano longo existe (3,7 s), mas troca de evento a cada 0,2–0,6 s por dentro.
  Por quê: 21 cortes medidos em 32 s. O plano de 3,7 s passa quatro palavras soltas e depois
  a torre entra deslizando.
- **Um plano = uma ideia = um elemento dominante.** Se a frase tem duas ideias, são dois planos.
- **Nada fica parado mais de ~0,5 s.** Ou a câmera anda, ou entra palavra, objeto ou cursor.
- Pausa na fala vira **papel vazio** de 1 degrau (não estica a palavra anterior).
  Por quê: "For" sai seco e ficam 3 quadros de papel vazio antes de "Technologies".

## 3. Câmera — todo plano anda

A câmera move a **cena montada**, depois vêm os filtros. Três movimentos, e só eles:

**a) Deriva lenta** — o padrão de foto e papel. Zoom de 2–8% no plano inteiro, com
deslocamento diagonal de ±60–120 px, ease-out suave (potência 1,3–1,8) ou linear.
Números do Hedy: WW2 1,78 → 1,30 com ±72/±59 px · Ziegfeld 1,08 → 1,045 com ±120 px ·
soldados 1,08 → 1,075 · torpedo 1 → 0,964 · Sansão 1 → 1,049 · editor 1,15 → 1,045 ·
multidão: pan em S de 167 px.
Por quê: foto parada lê como slide; a deriva é o que faz arquivo parecer filmado.

**b) Revelação** — a assinatura da família. A câmera **abre de 1,5–2,4× para 1×** em ease-out
exponencial (τ 4–10 quadros) em torno do **sujeito**: o sujeito fica parado na tela e o mundo
encolhe em volta dele.
Números: roteador 1,70 → 1 (tabela `REVELA_ZOOM`) · moldura 1,75 → 1 (τ 10 q) · lixeira
2,25 → 1 (τ 10,5 q) · ícone 2,43 → 1 · gancho é a mesma curva ao contrário (0,764 → 1).
Por quê: medido pelo tamanho de um objeto conhecido por degrau (corpo do roteador 446 → 303
px; largura da lixeira 349 → 249 px; período da grade do papel 35,3 → 46,05 px). Texto,
objeto, cursor e fundo escalam JUNTOS: é uma câmera só, não animação de cada peça.

**c) Chicote de saída** — ease-in exponencial (passo 22 → 29 → 39 → 52 → 70 px por degrau) e o
corte cai no maior passo. Borrão direcional **só acima de 45 px por passo**
(`0,75 · (passo − 45)`).
Por quê: no original a borda fica nítida até o penúltimo passo e só borra no último.

- O que **não** escala com a câmera: fundo de cor que é da tela (o domo teal do roteador).
- Câmera parada só em revelação que já assentou e no close emocional.

## 4. Objetos

- **Chegar**: sobe da borda de baixo em ease-out (τ ~0,1 s; o roteador ainda sobe 420 px com
  τ 6 quadros DENTRO da revelação) ou desliza da direita (caixa de interface: ease-out τ
  0,392 s, 408 px).
- **Dar errado**: o objeto troca para VERMELHO e cai girando (0,5 s, curva u^2,2: 75°,
  −260 px x, +640 px y). A cor é a notícia; a queda é a consequência.
- **Ser descartado**: a folha do plano anterior amassa — continua LARGA, o contorno quebra em
  polígono e fecha de cima e de baixo, o desenho fica quase limpo — e no degrau seguinte já
  está dentro da lixeira, que afasta com a boca parada na tela.
- **Ser usado** (interface): cursor de mão REAL entra da borda, aproxima em ease-out, agarra e
  arrasta acelerando (−7 → −19 → −49 → −142 px por degrau) até o corte. O cursor escala com a
  câmera — ele é parte da cena, não sobreposição.
- **Contar o tempo**: odômetro (números rolando de 5 em 5) que acelera no meio e assenta:
  0 → 2 → 10 → 25 → 55 → 75 → 85 → 90 → 95 → 100% em 1 s.
- **Listar**: itens entram um por vez em caixas azuis sobre um radar que pulsa (um anel a
  cada 0,8 s), em escada.

## 5. Texto — quatro registros, cada um com um papel

| registro | quando | fonte e cor | entrada | saída |
| --- | --- | --- | --- | --- |
| **palavra de narração** | a fala em si, no papel | serifa itálica (Instrument Serif Italic) corpo 86, tinta quase preta | escala 70 → 91 → 97 → 99% (`1 − 0,30 e^(−t/0,083)`) | seca, quando entra a próxima |
| **gancho / afirmação** | 1ª palavra, frase forte | grotesca bold (Arial/Helvetica Bold), tracking apertado (−0,12 da maiúscula), cinza 194 no escuro | digita; só a letra nova se mexe: cai 14–26 px e acende 79–91% | escorrega 40 px com borrão 14 px |
| **legenda de cena** | frase curta sobre foto/objeto | serifa (ou grotesca no escuro), 1–2 linhas centradas sob o sujeito | palavra a palavra: fade de 0,2 s na fase da fala, ou 45% → 100% em 2 degraus | com o plano |
| **rótulo** | nome técnico, item de lista | Inter 800 branco em caixa azul (21,126,190) com filete e sombra sólida de 12 px | desliza da direita | com o plano |

E dois detalhes de registro: **anotação à mão** (rótulo serifado pequeno + seta desenhada
apontando o sujeito) e **termo-chave em documento** (frase digitada com cursor; o termo
ganha seleção azul e a câmera mergulha no cursor).

- Texto nunca sobre rosto; acima ou abaixo do sujeito.
- Palavra única centrada pela **caixa da tinta**, não pela linha de base.
- A grotesca do gancho é Arial/Helvetica Bold, não Inter.
  Por quê: perfil de colunas contra o original: Helvetica 0,92, Arial 0,90, Inter 0,70.

## 6. Passagem de plano — como esconder o corte

O corte seco na grade é o padrão. Quando ele precisa sumir:

- **Casar escala**: o plano termina mergulhado num detalhe (patente: 1,85× no cursor e abre
  1,85 → 1,35 em 3 quadros) e o seguinte começa ampliado e abre.
- **Casar foco**: termina desfocando (σ → 14 px em 0,3 s) e o seguinte começa desfocado (σ 12)
  e firma em ~4 degraus (12 → 10 → 8,5 → 6 → 2 → 1 → 0).
- **Chicote**: a câmera acelera para um lado e o corte cai no passo maior, com borrão.
- **Objeto atravessa**: o cursor arrasta o arquivo para fora; o plano seguinte é onde ele chega.
- **Continuidade de conteúdo**: o desenho do plano anterior vira a folha que amassa.

## 7. Composição e cor

- Fundo: **papel cinza neutro chapado (194)**, **preto (7)** ou foto de arquivo cheia. É o
  mesmo papel em todos os planos de papel.
- **Uma cor de acento por plano, numa coisa só**: a figura vermelha na multidão P&B, o
  torpedo que fica vermelho, a lixeira verde, a onda teal, a caixa azul, a seleção azul.
- Foto de arquivo: P&B, ou cor dessaturada e escurecida (ganho 0,55–0,8), com grão próprio
  (5,0). A cor média do plano é casada **por canal** contra a referência quando há uma.
- Sujeito no centro óptico; a câmera ancora nele.

## 8. Acabamento — por cima de tudo, igual em todos os planos

`suavizar 1,05 → RGB split ±1,6 px (R à esquerda, B à direita) → scanline multiplicativa
(senoide de 8,07 px; R 1,6% · G 8,6% · B 7,0%) → grão 1,9`.
Calibrar sempre DEPOIS da entrega 720p: a compressão come metade do split, a cor da
scanline e o ruído do escuro.

## 9. Batida → plano: o mapa que leva o estilo para qualquer assunto

A Família A conta **uma história escondida**: algo que todo mundo usa, alguém que ninguém
lembra, o porquê. Qualquer roteiro nesse formato cabe neste mapa — tecnologia, saúde,
dinheiro, comida, esporte, ciência, marca.

| batida (o que a fala faz) | plano | no Hedy | em outra área |
| --- | --- | --- | --- |
| **gancho** — uma palavra que abre | `gancho_digitado` | EVERYONE | "NINGUÉM" · "TODO DIA" · "R$ 1" |
| **contraste** — como é visto | `cartao_rotulo` | her beauty | "o rosto da marca", "só um remédio" |
| **ninguém percebeu** | `figura_e_palavras` | almost no one realized | multidão, plateia, fila, cidade |
| **prova** — documento | `documento_digitado` | patente + SHE HELPED CREATE THE TECHNOLOGY | contrato, artigo, receita, balanço |
| **está aqui hoje** | `objeto_revela` | roteador + "por trás do seu Wi-Fi" | celular, cartão, remédio, chuteira |
| **contexto histórico** | `foto_pullout` + texto | caminhões + During WW2 | foto da época + "Em 1975" |
| **a pessoa / a época** | `foto_pullout` | retrato Ziegfeld | retrato licenciado, fachada, produto antigo |
| **fala que se explica** | `palavra_no_papel` | wasn't just making films | uma ideia por palavra |
| **mecanismo** | `palavras_e_figura` | torre + Communication System | diagrama, mapa, esquema, gráfico simples |
| **uso / aplicação** | `queda_objeto` | torpedo + jamming torpedoes | o produto em ação, com rótulo |
| **recusa / fracasso** | `amassar_lixeira` | a Marinha engavetou | ideia recusada, projeto cancelado |
| **o tempo passa** | `odometro` | 1940 → 1990 | anos, preço, contagem |
| **ambiente** | `objeto_na_parede` | lousa | quadro, cartaz, tela |
| **legado** — lista | `lista_ui` | Wi-Fi, Bluetooth, GPS | o que nasceu disso |
| **virada emocional** | `foto_pullout` (cor, desfoque de saída) | Sansão, close | a pessoa em cor |
| **conclusão** | `moldura_legenda` | history remembers her for her brain. | a frase que fecha |
| **para quem** | `foto_pullout` + palavra | Editors | o público em cena |
| **ação** | `icone_cursor` | arquivo .aep arrastado | o app, o arquivo, o botão |
| **destino** | `site_url` | site + URL digitada | a página, o perfil |

**Regra do literal**: o plano mostra o objeto que a fala nomeia, nunca o conceito. "Ninguém
percebeu" é uma multidão de costas; "foi recusada" é a folha indo para o lixo.

## 10. Números (consulta rápida)

| item | valor |
| --- | --- |
| grade | conteúdo em `n % 3 == 2` (10 qps em 30) |
| palavra no papel | escala `1 − 0,30·e^(−t/0,083)` · corpo 86 |
| fade de palavra | linear, 6 quadros, a partir do instante da fala |
| gancho | maiúscula 67,4 px, tracking −7,8 px, letras 1/8 → 5/8 → 7/8 → 8/8 por degrau |
| câmera do gancho | `1 − 0,236·e^(−q/4,3)` (q em quadros) |
| revelação | 1,70 → 1 (`REVELA_ZOOM`) · moldura `1 + 0,75·e^(−q/10)` · lixeira `1,2·(1 + 0,4·e^(−q/10,5))` |
| deriva | 2–8% de zoom, ±60–120 px, ease-out p 1,3–1,8 |
| chicote | `−3,58·(e^(0,29·passos) − 1)` px · borrão `0,75·(passo − 45)` acima de 45 px |
| caixa de interface | ease-out τ 0,392 s, 408 px, antecipa 2–7 quadros |
| subida de objeto | τ 0,10 s (ou 420 px com τ 6 q dentro da revelação) |
| queda | 0,5 s, `u^2,2`: 75°, −260 px x, +640 px y |
| radar | anel a cada 82,5 px, um período a cada 0,8 s |
| odômetro | 0/0/2/10/25/55/75/85/90/95/100% em 1 s |
| foco puxado | σ 12 → 10 → 8,5 → 6 → 2 → 1 → 0 px por degrau |
| papel / preto | 194 / 7 |
| acabamento | suavizar 1,05 · split ±1,6 px · scanline 8,07 px (1,6/8,6/7,0%) · grão 1,9 (foto 5,0) |
