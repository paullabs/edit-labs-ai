# Style Bible do estilo Vox explainer (v1)

Documento de referência para criar imagens e animações verticais inspiradas na linguagem editorial dos vídeos explicativos da Vox, a partir da leitura de dez quadros de vídeos da Vox. Os quadros são de terceiros e **não vêm no repositório**; aqui fica só o texto da análise, com os números. É a "Style Bible" que a skill `motion-vox` cita como "Style Bible §n" (no código e nos `.md`) e cujas faixas o `lib/medir.py` usa.

> **Nome curto do padrão:** estilo Vox explainer.
>
> Quando ele for citado, aplicar todo o sistema abaixo. A aparência pode variar por tema, mas a gramática visual deve permanecer.

## 1. Diagnóstico principal

O “estilo Vox” não é um preset fixo. É uma gramática de explicação visual que aceita diferentes direções de arte. Nas referências há três famílias:

1. **Mesa de pesquisa / scrapbook científico** — quadros 1 a 7.
2. **Infográfico editorial limpo** — quadros 8 e 10.
3. **Documentário retrô / bumper de capítulo** — quadro 9.

O elemento comum não é uma textura ou uma fonte específica. É esta sequência:

**afirmação da narração → evidência visual → anotação que direciona o olhar → interpretação → pausa para compreensão.**

Cada cena deve funcionar como uma frase visual. Ela mostra uma ideia principal e não tenta resumir o vídeo inteiro.

## 2. Princípios que não podem mudar

### 2.1 Uma evidência dominante

- Cada quadro tem um único herói: objeto, fotografia, número, mapa, documento, diagrama ou pessoa.
- O herói ocupa aproximadamente **45% a 65% da área útil**.
- O restante dá contexto, aponta relações ou cria profundidade.
- Se dois objetos competem igualmente, a hierarquia falhou.

### 2.2 Anotação com função, nunca decoração

- Círculos identificam o ponto exato.
- Setas mostram causalidade ou sequência.
- Sublinhados dão ênfase sem criar outra manchete.
- Etiquetas nomeiam a evidência.
- Linhas conectam fonte e consequência.
- Marcadores, rabiscos e números de página sugerem investigação.

Todo elemento deve responder: **“o que isso ajuda o espectador a entender?”**

### 2.3 Evidência antes de estética

Arquivos, retratos, objetos reais, diagramas, mapas, páginas, recortes de matérias e instrumentos têm precedência sobre ilustrações genéricas. A cena precisa parecer pesquisada, não apenas bonita.

### 2.4 Imperfeição controlada

Há bordas rasgadas, rotações pequenas, linhas tortas, grão, fita e sombra irregular. Mas alinhamento, peso, contraste e ordem de leitura são rigorosos. A estética é artesanal; a composição não é aleatória.

### 2.5 Mistura de registro humano e técnico

- O **humano** entra por fotos, escrita de marcador, fita, papel e objetos.
- O **técnico** entra por diagramas, escalas, linhas finas, números, grades e tipografia funcional.
- A tensão entre os dois faz a ciência parecer compreensível sem perder credibilidade.

## 3. Peso e hierarquia do design

### Distribuição recomendada por quadro

| Camada | Peso visual | Função |
| --- | ---: | --- |
| Evidência/herói | 55–65% | Entregar a ideia principal |
| Contexto | 20–25% | Situar tempo, lugar, tema ou processo |
| Anotação | 10–15% | Direcionar a leitura |
| Ruído/material periférico | 5–10% | Dar mundo e profundidade |

### Distribuição de cor

- **75–85%** neutros: papel, branco, cinza, carvão.
- **10–18%** massa escura: foto, recorte, painel ou objeto.
- **3–7%** cor de atenção: amarelo, azul, vermelho ou verde.

Uma cena normalmente escolhe **uma cor principal de atenção**. Vermelho e verde podem coexistir quando codificam categorias de dados, não como enfeite.

### Densidade

- Manter **25–40% de espaço negativo**.
- Usar de **3 a 6 elementos relevantes** por quadro.
- Objetos parcialmente cortados nas bordas fazem a mesa parecer maior que o enquadramento.
- O vazio é parte da explicação: permite que o olho entenda o que entrou e o que mudou.

## 4. Família A — Mesa de pesquisa / scrapbook científico

### 4.1 Câmera e composição

- Vista superior, próxima de **90° top-down**.
- Perspectiva discreta; a mesa deve parecer fotografada, não uma colagem totalmente plana.
- Composição assimétrica e modular.
- Herói geralmente no centro ou no terço superior, deixando área para conclusão ou continuação abaixo.
- Elementos principais entre **0° e 3°** de rotação; secundários entre **2° e 8°**.
- Evitar o mesmo ângulo em todos os recortes.
- Canetas, tubos, clipes ou papéis devem entrar cortados pelas margens, nunca todos inteiros e perfeitamente centralizados.

### 4.2 Camadas de profundidade

| Plano | Conteúdo | Tratamento |
| --- | --- | --- |
| D0 | Papel-base pontilhado ou quadriculado | Baixo contraste, quase fosco |
| D1 | Páginas, fotos e notas de contexto | Leve rotação; sombra mínima |
| D2 | Cartão, foto ou diagrama principal | Maior contraste e sombra de contato |
| D3 | Etiquetas, clipes, fita, seta, círculo | Cruza a borda do herói e prova materialidade |
| D4 | Caneta, marca-texto, tubo, placa transparente | Mais nítido ou com leve desfoco, conforme a altura |
| D5 | Grão, vinheta e aberração cromática | Aplicados ao conjunto, com intensidade baixa |

Profundidade vem principalmente de **sobreposição, escala, sombra de contato e transparência**, não de desfoque cinematográfico pesado.

### 4.3 Materiais

- Papel pontilhado cinza-claro.
- Papel quadriculado escolar.
- Cartão branco envelhecido ou marfim com borda irregular.
- Fotografias impressas com margem branca espessa.
- Papel preto fosco para diagramas científicos.
- Fita crepe semitransparente, bege e levemente enrugada.
- Clipes metálicos reais, finos, sem acabamento 3D brilhante.
- Etiquetas em papel amarelo tipo marcador/sticky note.
- Caneta preta, marca-texto amarelo e tubos laboratoriais translúcidos.
- Placa de Petri ou acrílico transparente para criar sobreposição física.
- Recortes com textura de jornal, gravura ou xerox.

### 4.4 Bordas e sombras

- Recortes não usam contorno vetorial perfeito.
- Borda de papel: irregularidade de **2–8 px em 1080p**.
- Sombra do cartão: preto quente, **12–20% de opacidade**, deslocamento vertical de **8–14 px**, blur de **18–30 px**.
- Sombra de objetos altos: ligeiramente mais definida.
- Fita e papel fino quase não projetam sombra.
- Evitar sombras igualmente fortes em todas as camadas.

### 4.5 Textura e acabamento

- Grão fino global: **4–8%**.
- Halftone/xerox em fotos e ilustrações: **8–18%**, preservando rosto e informação.
- Leve vinheta: **3–6%**.
- Aberração cromática nas bordas: **0,5–1,5 px em 1080p**.
- Altas luzes um pouco lavadas; pretos foscos, não esmagados.
- Saturação geral reduzida, com os acentos ainda vivos.
- Nitidez orgânica: evitar sharpen digital agressivo e HDR.

### 4.6 Paleta aproximada extraída das referências

Os valores abaixo são alvos de produção derivados dos frames comprimidos, não tokens oficiais da Vox.

| Papel/função | Hex | Uso |
| --- | --- | --- |
| Papel base | `#D9D8D1` | Fundo dominante |
| Papel claro | `#E6E5DD` | Recortes e margens |
| Papel frio | `#D0D1CF` | Variação de fundo |
| Fita/papel envelhecido | `#BFBBAE` | Fita e folhas antigas |
| Grafite | `#373639` | Texto, linha e painel |
| Carvão | `#2A2B2D` | Fundo científico escuro |
| Amarelo principal | `#DBD653` | Etiqueta, círculo, marcador |
| Amarelo vivo | `#F0DD36` | Destaque breve ou bumper |
| Vermelho de dado | `#BF4A50` | Categoria/alerta |
| Verde de dado | `#36C25B` | Categoria/ativação |
| Azul editorial | `#2E82F7` | Dado principal em versão limpa |
| Azul pálido | `#BFD8FC` | Área preenchida/fundo técnico |

Não usar todas as cores juntas. Em geral: neutros + amarelo; neutros + azul; ou neutros + amarelo + vermelho/verde quando houver codificação científica.

## 5. Tipografia

As capturas não permitem provar a família exata usada na produção. O sistema tipográfico, porém, é identificável e deve ser replicado por função.

| Função | Linguagem | Alternativas práticas | Peso |
| --- | --- | --- | ---: |
| Manchete/conclusão | Sans compacta e editorial | Archivo Narrow, Franklin Gothic Condensed, Inter Tight | 700–900 |
| Texto funcional | Grotesca neutra | Balto, Alright Sans, Inter, Arial | 400–700 |
| Número editorial | Serif expressiva | Cooper Black, Fraunces, Georgia Bold | 700–900 |
| Etiqueta manual | Marcador irregular | Permanent Marker, Kalam Bold ou lettering próprio | 600–800 |
| Legenda técnica | Mono estreita | IBM Plex Mono, Roboto Mono | 400–500 |

Historicamente, a Vox comunicou o uso de **Balto** e **Alright Sans** no produto editorial. Isso não significa que todos os vídeos ou estas cenas usem essas fontes exatas.

### Regras tipográficas para vertical 1080 × 1920

- Manchete: **80–112 px**, line-height de 0,92–1,02.
- Número principal: **96–152 px**.
- Etiqueta manual: **46–64 px**.
- Legenda: **28–38 px**.
- Microtexto técnico: **22–28 px**.
- No máximo **três famílias no mesmo quadro**: uma editorial, uma manual e uma técnica.
- No máximo **duas linhas** por etiqueta.
- Texto manual deve parecer escrito de uma vez, com pequenas variações de largura e baseline.
- Sublinhado em duas passadas irregulares; círculo em duas ou três voltas, nunca um vetor perfeito.

## 6. Família B — Infográfico editorial limpo

### Aparência

- Fundo branco ou branco com azul muito pálido.
- Grande quantidade de espaço negativo.
- Fotografia ou gravura em preto e branco, recortada com máscara editorial.
- Uma única cor intensa para quantificação ou foco.
- Linhas de chamada muito finas, pontos de ancoragem e marcas de registro.
- Microlegendas nos cantos dão sensação de atlas, ficha científica ou sistema de medição.
- O corte da imagem pode ser abrupto e blocado na base; isso evita o aspecto de recorte publicitário perfeito.

### Composição de retrato quantificado

- Perfil humano ocupa **55–70% da altura útil**.
- Elemento colorido ocupa **8–18% do herói**.
- Callout fica fora da anatomia e se conecta por linha fina.
- Microinformações permanecem secundárias e com baixo contraste.
- Azul recomendado: `#2E82F7`; preenchimento pálido: `#BFD8FC`.

### Composição de processo horizontal ou vertical

- Uma linha contínua é a espinha dorsal.
- Cada etapa recebe um objeto real ou recorte, não apenas um ícone.
- Escala visual dos objetos é normalizada para que um estágio não domine sem motivo.
- Legendas ficam alinhadas numa mesma linha-base.
- Para vertical, converter a linha em percurso descendente com alternância esquerda/direita, mantendo no máximo **cinco etapas por cena**.

## 7. Família C — Documentário retrô

Uso ideal: abertura, mudança de capítulo, salto temporal ou apresentação de arquivo.

### Aparência

- Moldura de TV CRT arredondada.
- Fundo técnico em creme, com desenhos de engenharia em baixa opacidade.
- Distorção de lente/barril discreta.
- Scanlines, ruído analógico e pequena separação RGB.
- Herói recortado com cor quente e forte.
- Faixa amarela atrás do título, como marca-texto físico.

### Paleta

- Creme/sepia: `#D9CABD`
- Papel antigo: `#C0B19A`
- Carvão: `#2D2628`
- Amarelo: `#F0DD36`
- Laranja/vermelho: `#CC4516`

### Limite

É um tempero, não o idioma inteiro. Se usado continuamente, o CRT vira efeito e perde função narrativa.

## 8. Leitura quadro a quadro das referências

| Quadro | Função narrativa | O que deve ser preservado |
| --- | --- | --- |
| 1 | Apresentar o objeto de estudo | Um herói isolado; círculo amarelo atrás; props cortados nas bordas; amplo vazio |
| 2 | Mostrar método e escala | Instrumento → amostra/diagrama → ampliação → número; linha conecta a relação |
| 3 | Definir um conceito | Cartão escuro único; diagrama simples; etiqueta física presa por clipe |
| 4 | Inserir entrevista | Vídeo dentro de fotografia/cartão; nome em etiqueta; a entrevista pertence ao mesmo universo visual |
| 5 | Ligar biografia e processo | Foto de pessoas + amostra física + placa transparente + seta e rótulo |
| 6 | Transformar evidência em pergunta | Evidência acima; pergunta grande abaixo; seta desenhada cria tensão causal |
| 7 | Abrir ou nomear um tema | Palavra híbrida manual + editorial; composição central; objetos laboratoriais periféricos |
| 8 | Quantificar uma ideia abstrata | Retrato monocromático; um setor azul; linha e percentual; microdados no vazio |
| 9 | Abrir capítulo com personalidade | CRT, faixa amarela, objeto colorido, textura analógica e fundo técnico |
| 10 | Explicar cadeia/processo | Linha espinha dorsal; cinco estágios; recortes reais; legenda uniforme |

## 9. Movimento e animação

### 9.1 Princípio

O movimento acompanha o raciocínio. Nada deve estar se mexendo apenas para “dar dinâmica”. Em uma frase, a animação deve revelar na mesma ordem em que o espectador entende.

### 9.2 Sequência-padrão de entrada

1. Fundo e contexto já existem ou entram em pan lento.
2. Evidência principal pousa ou é revelada.
3. Etiqueta nomeia a evidência.
4. Círculo, seta ou linha é desenhado.
5. Número ou conclusão aparece por último.
6. Quadro segura tempo suficiente para leitura.

### 9.3 Timing recomendado em 24 fps

| Ação | Duração |
| --- | ---: |
| Recorte pousando | 8–12 frames |
| Foto/cartão entrando | 12–18 frames |
| Etiqueta colocada | 8–12 frames |
| Linha/seta desenhada | 8–14 frames |
| Círculo manual | 10–16 frames |
| Texto curto aparecendo | 6–10 frames |
| Pausa de leitura | 24–60 frames |
| Saída | 6–10 frames |

- Stagger entre objetos: **2–4 frames**.
- Overshoot máximo: **2–4%** de escala ou **1–2°** de rotação.
- Curva-base: `cubic-bezier(0.20, 0.80, 0.20, 1.00)`.
- Evitar bounce elástico grande.

### 9.4 Sensação de stop motion

- Props e recortes podem ser animados “on twos”, equivalendo a **12 fps dentro de uma composição de 24 fps**.
- Texto pequeno, câmera e linhas finas permanecem fluidos a 24 fps para preservar leitura.
- Pequenos saltos de posição de **1–2 px** podem existir em papel, nunca em toda a câmera ao mesmo tempo.

### 9.5 Movimento de câmera

- Drift constante muito discreto: **0,3–0,8% por segundo**.
- Push-in de leitura: **100% → 104–106%** em 2–4 s.
- Pan entre evidências: **3–8% da largura do quadro** em 1,5–3 s.
- A câmera pode atravessar uma mesa contínua, fazendo cada nova evidência parecer estar fisicamente ao lado da anterior.
- Parallax relativo: fundo `0,2×`; papéis `0,5×`; herói `1×`; objeto alto `1,15×`.

### 9.6 Transições preferidas

- Match cut entre formas semelhantes.
- Papel ou fotografia que cruza a lente e vira wipe.
- Zoom para dentro de uma imagem, saindo dentro do próximo documento.
- Linha ou seta que continua na cena seguinte.
- Pan pela mesma mesa contínua.
- Círculo desenhado que vira máscara de zoom.

Evitar glitch aleatório, whip pan constante, flashes brancos, zooms com impacto em toda frase e transições de template.

### 9.7 Som que reforça o material

- Papel pousando: impacto curto e seco.
- Caneta/linha: scribble sutil.
- Clipe ou instrumento: click discreto.
- Mudança de foco: whoosh curto, sem subgrave exagerado.
- CRT: estalo, hiss e hum apenas em bumper retrô.

## 10. Adaptação vertical — 1080 × 1920

> Para Reels, a margem que vale nas skills é a de `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`; os números abaixo são a leitura da referência.

Não esticar um quadro 4:3. Reorganizar a leitura para cima → centro → baixo.

### Grid e segurança

- Margens laterais de composição: **72–96 px**.
- Área crítica sem interface: aproximadamente **x = 72–930 px** e **y = 140–1600 px**.
- Evitar texto importante nos **120 px da direita** e nos **260 px inferiores** quando o destino for Shorts/Reels.
- Unidade-base de espaçamento: **8 px**.
- Gaps principais: **24, 40, 64 e 96 px**.

### Estrutura vertical recomendada

| Região | Uso |
| --- | --- |
| 7–18% | Palavra-tema, origem ou pergunta curta |
| 18–65% | Evidência principal |
| 55–78% | Anotação, zoom ou relação causal |
| 72–88% | Número, conclusão ou próxima pergunta |
| Bordas | Props parcialmente cortados e contexto |

### Tamanhos práticos

- Herói principal: **560–820 px de largura**.
- Cartão de evidência: **680–900 px de largura**.
- Etiqueta amarela: **520–760 × 100–150 px**.
- Traço manual: **3–6 px**.
- Linha técnica: **1,5–2,5 px**.
- Círculo manual: duas ou três passadas com deslocamento de **3–8 px**.

## 11. Fórmula de uma cena vertical

### Cena de evidência física

1. Papel-base pontilhado.
2. Dois recortes periféricos com baixa relevância.
3. Herói central com margem branca irregular.
4. Etiqueta amarela cruzando parte da borda.
5. Um clipe ou fita conectando materialmente as camadas.
6. Uma seta/círculo manual apontando o detalhe exato.
7. Uma conclusão curta em sans/serif forte.

### Cena de dado limpo

1. Fundo branco ou azul quase branco.
2. Herói monocromático grande.
3. Uma área azul codifica o dado.
4. Uma linha fina leva ao percentual ou conclusão.
5. Microtexto técnico ocupa os cantos sem competir.

### Cena de processo

1. Linha vertical contínua.
2. Três a cinco estágios alternando lados.
3. Um recorte real por estágio.
4. Legendas uniformes e curtas.
5. Cor aparece na linha ou no estágio atual, não em todos ao mesmo tempo.

## 12. Regras de consistência entre imagens

Para uma sequência parecer do mesmo vídeo:

- Manter o mesmo papel-base e a mesma intensidade de grão.
- Usar uma paleta de acento definida por bloco narrativo.
- Repetir a mesma espessura de linha, sombra e etiqueta.
- Limitar a duas direções de papel e três famílias tipográficas.
- Manter o mesmo tipo de recorte: xerox/halftone ou foto limpa, sem alternar aleatoriamente.
- Reaproveitar dois ou três props recorrentes, como caneta preta, marca-texto amarelo e clipe.
- Variar a composição sem trocar o sistema.

## 13. O que mata o estilo

- Brilho neon, bloom, glow ou reflexo futurista.
- 3D plástico genérico.
- Gradientes de aplicativo/SaaS.
- Cards digitais com cantos muito arredondados.
- Sombras idênticas em todas as camadas.
- Tudo perfeitamente centralizado e simétrico.
- Texturas aplicadas com a mesma intensidade em cada objeto.
- Texto demais; parágrafos no quadro.
- Mais de uma ideia principal por cena.
- Uso de amarelo, vermelho, verde e azul sem função informacional.
- Recortes perfeitos demais ou borda branca digital uniforme.
- Movimento constante em todos os objetos.
- Zoom de impacto, glitch e whoosh em cada frase.
- Saturação/HDR altos ou nitidez artificial.
- Elementos “bonitos” que não têm ligação com a narração.

## 14. Prompt-base para gerar imagens — modo scrapbook

> Vertical 9:16 editorial explainer frame, tactile top-down research desk, warm gray dotted paper background, one dominant evidence object, layered archival photo cutouts and scientific diagrams with rough cream paper edges, masking tape, metal paper clips, black marker annotations, hand-drawn arrows and imperfect double circles, yellow highlighter labels, charcoal ink, restrained red and green data accents only when meaningful, real laboratory props partially cropped at the edges, soft contact shadows, physical overlap and transparent materials creating depth, newsprint halftone, subtle xerox texture, fine film grain, slight chromatic fringing, muted saturation, asymmetrical modular composition, generous negative space, intelligent documentary information design, controlled handmade imperfection, no logos, no glossy 3D, no neon, no glow, no gradients, no rounded SaaS cards, no clutter, no HDR, no AI-polished look.

## 15. Prompt-base para gerar imagens — modo editorial limpo

> Vertical 9:16 clean editorial explainer graphic, high-key white and very pale blue background, one large monochrome archival portrait or real object cutout, black-and-white engraving texture, a single vivid blue quantified area, ultra-thin measurement callout lines, tiny technical labels and registration marks in the margins, strict Swiss grid, strong asymmetrical hierarchy, 35 percent negative space, subtle halftone and print grain, blocky imperfect crop at the base, restrained scientific atlas aesthetic, no glossy 3D, no gradients, no neon, no UI cards, no decorative icons, no clutter.

## 16. Critério de aprovação

Antes de aprovar qualquer imagem, responder “sim” a estas perguntas:

1. Entendo a ideia principal em menos de um segundo?
2. Existe uma evidência dominante?
3. A anotação aponta algo específico?
4. O vazio ajuda a leitura?
5. Os materiais parecem físicos ou editoriais, não genéricos?
6. A cor de destaque tem uma função?
7. A cena poderia existir dentro da mesma mesa/sistema das demais?
8. Há profundidade por sobreposição e sombra de contato?
9. O quadro continua legível em uma tela de celular?
10. Tirar qualquer elemento deixaria a explicação pior? Se não, esse elemento deve sair.

## 17. Resumo operacional

**Assinatura visual:** documentário editorial + mesa de pesquisa + infográfico científico + imperfeição física controlada.

**Regra-mãe:** mostrar uma prova, apontar o detalhe e concluir — nesta ordem.

**Proporção de peso:** 60% evidência, 25% contexto, 15% anotação.

**Proporção de cor:** 80% neutros, 15% massa escura, 5% acento.

**Movimento:** pousar, desenhar, conectar, segurar; nunca mover tudo ao mesmo tempo.

**Resultado desejado:** parecer que um jornalista desmontou um assunto complexo sobre uma mesa e guiou o espectador por cada evidência.
