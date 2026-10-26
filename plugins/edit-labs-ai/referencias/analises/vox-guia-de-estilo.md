# Guia de estilo Vox: matéria sob pressão

Análise nossa de **Something weird happens when you keep squeezing**, do canal **Vox** (R24 no catálogo), com destaque para **7:18**. O vídeo é da Vox (todos os direitos reservados): aqui fica só o texto da análise; para ver, **abra o link**.

[Vídeo original](https://www.youtube.com/watch?v=NqabT21d8VM&t=438s). Os 20 trechos com tempo, o que se vê e como aplicar: [`vox-squeezing-trechos.json`](vox-squeezing-trechos.json), cada um com o link no segundo certo.

## Ideia central

**Explicação editorial com colagem tátil: o movimento revela como algo funciona.** Pessoas, objetos reais, papel, diagramas e elementos em volume convivem no mesmo mundo. Uma imagem apresenta a coisa; a próxima revela uma relação, uma transformação ou uma mudança de escala. O desenho segue o raciocínio da narração.

## O que foi observado

### Materialidade e composição

- Papel claro levemente amarelado e papel escuro com grão; superfícies irregulares também nos objetos. Moléculas parecem bolas de papel amassado, com relevo e sombras. Isso é uma descrição da aparência, não uma confirmação do processo de produção.
- Pessoas, mãos, animais e equipamentos recortados convivem com cenários montados em planos. O apresentador vira guia dentro da ilustração, especialmente na descida pelo oceano e pelo interior da Terra.
- Grades finas, frequentemente giradas em losango, dão escala aos objetos. São suporte ao raciocínio, com menos contraste que o assunto principal.
- Um objeto isolado ganha bastante espaço quando precisa ser reconhecido. Comparações usam colunas ou tela dividida; o universo microscópico pode preencher toda a tela.
- Há volume e transparência nos cubos e nas camadas, mas a textura mantém o conjunto próximo de uma maquete artesanal.

### Cor

- Papel creme e carvão são bases recorrentes. Azul acompanha a atmosfera e o oceano; castanhos, ferrugem e laranja acompanham as camadas quentes; vermelho e branco diferenciam componentes moleculares.
- O laser violeta é um acento de alta saturação sobre fundo escuro, concentrado na ação.
- A régua superior muda de azul/verde para tons quentes ao longo da progressão. A cor acompanha uma variável, em vez de mudar sem motivo.
- Valores iniciais sugeridos para nossas composições, aproximados visualmente e não extraídos de um manual oficial: creme `#E8E5D3`, carvão `#202321`, azul `#5680AA`, petróleo `#15313B`, ferrugem `#925431`, amarelo `#D3B94D`, vermelho `#B94F59`, verde pálido `#A9C7B6`, violeta `#6A20FF`. Ajustar ao lado dos frames antes de aprovar.

### Tipografia

- Títulos e nomes de materiais em caixa alta, sem serifa, muito pesados e curtos. Informações auxiliares menores e discretas.
- Fórmula e nomenclatura científica usam também serifa/itálico. A diferença de fonte tem função editorial.
- Rótulos pertencem ao objeto: no esquema do laser, acompanham a rotação das camadas. A hierarquia continua clara durante o movimento.
- Identificações de entrevistados usam nome forte e pequenas faixas de informação abaixo. Títulos sobre filmagens aparecem em pontos com contraste suficiente.
- A fonte exata não foi identificada. Selecionar uma equivalente pela forma, peso e largura, sem apresentar a escolha como fonte oficial da Vox.

### Movimento e transições

- A câmera aproxima, recua e percorre um ambiente para revelar relações de escala. O ponto de posição e a régua preservam orientação.
- Objetos recorrentes voltam transformados: hidrogênio, sódio e água são acompanhados ao longo da viagem. A comparação fica fácil porque a identidade é preservada.
- Uma mudança conceitual pode virar mudança de enquadramento: objeto → estrutura interna; experimento filmado → esquema; amostra → planeta.
- Recortes se multiplicam para representar quantidade e direção, como a analogia da pressão atmosférica com pessoas ao redor do corpo.
- Textura irregular e variação entre imagens dão caráter artesanal; algumas passagens têm desfoque radial, rastros e explosões gráficas. Isso não justifica aplicar glitch a tudo.
- O arquivo baixado é **24 fps**. A cadência de cada elemento animado não foi medida. **Não afirmar que este vídeo inteiro foi animado a 12 fps.**

### Estrutura narrativa

1. Começar com um objeto familiar e uma pergunta demonstrável: a seringa.
2. Construir uma viagem com uma variável contínua: pressão crescente.
3. Repetir amostras e analogias para comparar estados.
4. Entrar no mecanismo microscópico quando a observação externa já estiver clara.
5. Intercalar pessoas, evidência filmada e esquemas explicativos.
6. Voltar ao ponto concreto de partida para encerrar.

## Estudo prioritário: 7:11–7:42

Ver o **trecho 14** em `vox-squeezing-trechos.json` e abrir o vídeo em 7:11. O ponto de destaque é 7:18, logo antes da entrada do laser. A inspeção adicional usa aproximadamente duas imagens por segundo; os tempos abaixo são aproximados.

| Intervalo | O que acontece | Como transferir a lógica |
|---|---|---|
| 7:11–7:14 | Três camadas aparecem frontalmente sobre papel claro e grade; a amostra ganha nome. | Primeiro estabelecer as partes e sua relação espacial. |
| 7:14–7:18 | Conjunto gira até a disposição lateral; o fundo escurece e o volume fica legível. | Girar objeto, grade e rótulos como um conjunto; preservar a identidade. |
| 7:19–7:20 | Feixe violeta chega pela direita à camada azul. | Mostrar de onde vem a ação antes de mostrar a consequência. |
| 7:21–7:25 | Pontas claras/amareladas se expandem na superfície atingida. | Concentrar o evento visual no contato; preservar o resto do esquema. |
| 7:25–7:30 | Entrevistada explica a relação entre plasma e pressão. | Uma pausa humana pode sustentar a compreensão do mecanismo. |
| 7:30–7:35 | Retorno ao mesmo esquema; faixa de alteração atravessa a amostra da direita para a esquerda. | Animar a propagação na direção correta e depois do impacto. |
| 7:36–7:42 | Camada verde é identificada como janela; linhas onduladas passam para a esquerda. | Nomear a saída quando ela passa a ter função na história. |

Estrutura editável sugerida para uma futura recriação: fundo; grade; grupo das três camadas; rótulos vinculados às camadas; feixe de entrada; formas de plasma; faixa de propagação; ondas de saída; textura final. Essa é uma proposta de implementação, não acesso ao projeto original.

## Biblioteca de recursos para nossos vídeos

| Recurso | Exemplos no original | Uso futuro |
|---|---|---|
| Objeto recortado + força | 0:10–0:22; 1:14–1:37 | Explicar ação, resistência ou relação de tamanho. |
| Guia humano dentro da cena | 1:37–3:14; 3:44–4:17 | Dar escala e continuidade a uma viagem abstrata. |
| Régua persistente | Descida e comparação entre planetas | Comparar crescimento, custo, tempo ou capacidade, com unidade explícita. |
| Comparação de estados | 3:17–3:44; 4:17–4:38 | Mostrar antes/depois e o mecanismo que causou a mudança. |
| Macro e micro simultâneos | 3:30–3:44; 4:28–4:34 | Relacionar resultado visível e estrutura interna. |
| Processo em camadas | 7:11–7:42 | Explicar entrada, processamento e saída com causa e efeito. |
| Unidades táteis repetidas | 8:04–8:23; 8:41–9:05 | Representar organização, rede ou transferência com objetos concretos. |
| Escala conectada | 9:05–10:01 | Comparar ordens de grandeza sem perder a referência. |
| Fonte documental | 4:35–4:38; 5:41–5:48; 10:30–10:40 | Inserir a evidência real no momento em que sustenta a afirmação. |
| Retorno visual | 10:40–11:05 | Encerrar a explicação retomando sua trajetória. |

## Direção para um vídeo novo

- Consultar o exemplo correspondente antes de desenhar cada cena. Escrever a frase da narração, o objeto que a representa, a mudança visual e o instante que dispara essa mudança.
- Produzir assets ligados ao assunto concreto do nosso vídeo. A grade e a textura apoiam esses assets; não substituem informação.
- Preservar os mesmos objetos, cores e unidades durante comparações. Um elemento muda quando há motivo na explicação.
- Montar entrada → ação → consequência → pausa de leitura. Setas, partículas e resultados devem surgir no momento causal correto.
- Para vertical, recompor o enquadramento e a comparação; não cortar simplesmente as laterais do original 16:9. A orientação atual vale para o vocabulário visual, não determina o formato do próximo vídeo.
- Construir elementos separados e editáveis. Os vídeos de referência são achatados, para estudo, não templates editáveis.
- Rever a sequência em movimento antes de aprovar: a imagem estática não demonstra ritmo, sincronismo ou leitura.

## Preferências do estilo, separadas da observação

As skills do plugin usam por padrão cadência de 12 fps em motion, grão/RGB sutil, imagens concretas, logos oficiais e ausência de música, salvo pedido. São escolhas do estilo, sujeitas ao briefing de cada vídeo; não são características verificadas integralmente neste vídeo. Se usadas, testar a cadência no motion sem reduzir automaticamente a fluidez da filmagem. O áudio original é só referência, nunca trilha para novas produções.

## Cobertura e limites desta análise

Análise visual dos 100 frames selecionados por mudança de cena, mais 139 amostras distribuídas pelo vídeo inteiro e 65 imagens do trecho 7:10–7:42; imagens inspecionadas em painéis cronológicos. Legendas nativas lidas para relacionar imagem e explicação. Total: **304 imagens de análise**, além das capas dos trechos.

O vídeo tem 11min35s, por isso a seleção automática isolada era esparsa; a cobertura uniforme e o estudo focal complementaram essa seleção. Não houve medição quadro a quadro das curvas de animação nem audição detalhada de efeitos sonoros. As legendas automáticas contêm erros. Não há confirmação de software, plugins, fonte exata, técnica de confecção dos objetos ou cadência interna. Os 20 trechos são um catálogo dos principais blocos, não uma lista de cada keyframe. Para qualquer transição breve que a amostragem não capture, abrir o vídeo original no link.

## Regra: storytelling simples

Cenas limpas e histórias fáceis de entender. Em cada roteiro: um acontecimento, frases curtas, objetos recorrentes e uma consequência visível. Cabeçalhos, réguas, grades e blocos de texto não entram por padrão; só quando a informação precisa deles. A câmera deve acompanhar a ação e revelar relações. Referências novas não substituem a preferência pela colagem tátil do vídeo original.
