# Armadilhas

Cada uma é um retrabalho evitável. Confira antes de renderizar.

## Geometria

1. **Âncora sob rotação.** Fração medida no bitmap original não vale depois de
   `Image.rotate(expand=True)` — o referencial muda, e um círculo manual cai no centro
   do mostrador em vez do 12. Use `voxlab.rotate_anchor()`, verificado contra o
   PIL com erro < 1px. Vale para qualquer anotação presa a objeto rotacionado.

2. **Pan tem teto.** Push de N% dá apenas `N/2 %` da largura de folga lateral.
   Push 6% + pan 70px puxa borda preta para dentro do quadro. Calcule antes de
   prometer reframe: `pan_max = (escala − 1) × largura / 2`.

3. **Seta que volta.** Origem e destino na mesma coluna fazem a curva fechar um gancho
   sobre si mesma, sem direção legível. Alterne esquerda/direita.

4. **Polilinha sem spline vira ziguezague.** Traço manual não tem quina. Use Catmull-Rom.

## Recorte

5. **Sombra embutida.** Modelo de imagem sempre põe sombra de contato. Sombra é camada.
   Sinal que resolve: o objeto está de um lado do fundo em luminância e a sombra do
   outro, **lisa e neutra**. Deixe o fundo crescer só nessa faixa, com guarda de
   gradiente — aço escovado e tinta de gravura têm gradiente alto e ficam protegidos.

6. **A regra inverte para objeto escuro.** "Objeto é mais claro que o fundo" vale para
   papel e metal claro. Teclado charcoal (73) contra fundo cinza (144) seria comido
   inteiro. `dark_floor` troca o teto por uma faixa.

7. **Fundo transparente não existe.** Pedir "transparent background PNG" ao modelo
   devolve RGB sem alfa e um fundo cinza sólido.

8. **Fundo chroma custa spill.** Torna o matte trivial, mas contamina ~65% dos pixels de
   borda com a cor do fundo. Neste estilo a borda é a matéria. Prefira neutro escolhido
   pelo maior afastamento de luminância.

## Texto

9. **Máquina de escrever é template.** Revelar caractere a caractere em tipografia
   editorial é proibido. Bloco para editorial, write para marcador.

10. **Anchor "mm" usa a caixa da FONTE**, que inclui ascendente e descendente. Texto
    centrado nela escorrega para baixo e sai da faixa da fita. Use centro do *ink*.

11. **`text_width` subestima texto manual em até 20%** — soma avanços de fonte e ignora
    que o modo `hand` rotaciona e desloca cada caractere. Meça o desenho, não a fonte,
    ou o rótulo vaza para fora da etiqueta.

12. **A fita se dimensiona pela palavra**, nunca o contrário: `largura = texto / 0,62`.
    Com 41% de preenchimento a etiqueta lê como fita vazia com letras perdidas.

13. **Variação por caractere no marcador: ±1,4° e ±1,6% de baseline.** Com ±3,2° a
    palavra vira letras soltas. O marcador tem que ler "escrito de uma vez".

14. **Dois rótulos empilhados na mesma coluna viram um rótulo de duas linhas.**

## Acabamento

15. **Aberração cromática tem que ser radial**, nula no centro. Deslocamento horizontal
    uniforme franja toda letra de vermelho e ciano e lê como erro de render.

16. **Ruído de traço precisa de comprimento de correlação** (~26 pontos, interpolado),
    senão a linha vira corrente de contas em vez de traço de caneta.

17. **Grão aleatório por pixel e por frame é incompressível.** Sem correlação entre
    frames o x264 não prevê nada: 120 Mbps contra 4 Mbps do resto. Borre o campo
    (σ≈0,9 — grão de filme tem tamanho) e segure cada campo por 2 frames.

## Luz sem glow

18. A identidade proíbe neon, glow e bloom. Para "luz de tela chamativa":
    gere a foto com a tela como **única fonte**, pedindo explicitamente
    `no glow, no bloom, no halation, no volumetric rays`; meça o croma (numa foto real
    ele vem quase neutro, ~6); e **construa** a cor com mapa de gradiente sobre a
    luminância — sombras em carvão neutro, meios-tons na cor da paleta, núcleo da fonte
    quase branco. Nenhum pixel escuro é iluminado; só a curva muda.
    Normalize pelo percentil 2, não 0,4 — cortar mais baixo esmaga a silhueta.
    Borre o núcleo mais claro para matar interface legível.

19. **Foto escura sobre footage escuro precisa de cartão com margem branca grossa.**
    É a margem que separa. A proporção do corte tem que casar com a do cartão, senão
    a margem desaparece.

## Objeto vence palavra

26. **Ideia escrita a mao nao e o mesmo que ideia mostrada.** "CENTENAS -> MILHARES" em
    marcador acerta o conteudo e erra o registro: evidencia vem antes de estetica.
    Poucas notas -> maco de notas diz a mesma coisa sem uma
    letra. Antes de escrever uma palavra, pergunte que OBJETO diria aquilo.

27. **Cedula, documento e produto de marca: peca a impressao ILEGIVEL.** "printed design
    is an indistinct engraved pattern only, no readable numbers, no denomination, no
    portraits, no seals — not any real currency". Resolve a regra de nada-de-texto-de-IA
    e evita reproduzir dinheiro real. Gere variantes: e comum uma delas voltar com texto
    de IA visivel na nota.

28. **Legenda que troca de cor precisa trocar na hora certa.** A decisao claro/escuro
    nao pode usar a janela inteira da cena: durante a SAIDA o papel ja foi embora e o
    video ocupa o quadro. Tinta escura sobre video escuro deixa so o halo claro visivel
    e a legenda le como copia dupla fantasmada. O ponto de troca depende do tipo de
    saida — `push` 0%, `wipe` 30%, `slide` 50% da duracao da saida.

## Hierarquia e profundidade

> Detalhados em `hierarquia-e-profundidade.md`, que e leitura obrigatoria antes de compor.

48. **Carimbo ao lado do documento nao e carimbo.** Carimbo posto abaixo do documento
    encosta na borda dele — metade sobre o objeto, metade fora — e le como acidente de
    layout. Carimbo vai NO MEIO do documento, girado, com 60-75% da
    largura dele.

49. **Objetos do mesmo tamanho nao tem hierarquia.** Seis envelopes iguais em grade solta
    leem como "imagens jogadas": o olho nao acha o assunto. Varie escala e sobreponha —
    um grande na frente, os outros menores atras.

50. **Tangente achata.** Duas bordas que quase se tocam (ou se tocam sem sobrepor)
    impedem o olho de decidir o que esta na frente. Regra binaria: ou sobrepoe de
    verdade, com sombra de contato, ou afasta 40px. Nunca encostado.

51. **Duas fotos de tamanho parecido lado a lado sao o pior dos dois mundos.** Nem
    hierarquia, nem profundidade, e o conteudo de cada uma pequeno demais para ler.
    Uma foto em TELA CHEIA por vez, com vinheta, trocando a cada ~1s.

52. **Foto de tela cheia tem que ser GERADA em 9:16.** Recortar uma 4:3 para vertical
    joga fora ~58% da largura e destroi o enquadramento. Decida o uso antes do prompt.

53. **Cutaway longo nao e uma composicao que se acumula.** Oito segundos comportam quatro
    ideias; empilhar as quatro no mesmo quadro entope a composicao e mata a hierarquia.
    Decupe em beats com corte seco, na ordem da fala, cortando no silencio.

## Boil

32. **Boil no quadro inteiro nao e boil.** Aplicado ao comp, o fundo ondula e vira
    distorcao de lente. No AE o Turbulent Displace vai em CADA layer — aqui tambem.

33. **Campo unico para o quadro todo le como tremor de camera.** Cada elemento precisa
    da propria semente, estavel entre frames. Semear por ordem de desenho quebra quando
    um objeto condicional aparece ou some — semeie pela linha que chamou.

34. **Elemento fisicamente unico precisa de campo unico.** Fita e a palavra escrita sobre
    ela sao um objeto so; com campos separados a etiqueta descola do papel.

35. **Objeto fotografado aguenta metade do que a tinta aguenta.** amount 6 no marcador
    le como redesenho; os mesmos 6 num relogio leem como derretimento, proibido pela
    identidade. Mede antes: `obj 3 · paper 4 · type 2 · ink 6`.

36. **Estado implicito vaza entre passadas.** `_BOIL["frame"]` fica setado depois que a
    cena termina. Qualquer passada seguinte que desenhe texto herda o campo CONGELADO do
    ultimo frame — deformado e parado, o pior dos dois mundos. Zere no inicio de cada
    passada que nao deve boilar.

## Frase de impacto

37. **Legenda corrida briga com o motion.** Cena que ja tem uma palavra na tela nao
    aguenta uma segunda tipografia por cima. Frase de impacto entra so em janela SEM
    motion — e ha um `check()` que falha se colidir.

38. **Medir a posicao no frame do meio erra.** A pessoa se mexe durante a frase: o que
    estava livre no meio pode estar ocupado no fim. Meca o PIOR frame da janela.

39. **Energia de borda nao distingue paleto de microfone desfocado.** Os dois dao
    "calmo". Renderize a frase no inicio E no fim da janela e decida no olho.

40. **"Faixa mais calma" pode ser o rosto.** Energia de borda baixa nao significa
    espaco livre — pele lisa em close da o menor ruido do quadro. Detecte a face e
    coloque o texto abaixo do queixo mais baixo da janela.

41. **Inversao falha em tom medio.** Negativo de ~128 e ~128. Serve sobre escuro; sobre
    pele, piora. Quando nao ha area escura nem faixa livre, use tarja.

42. **Tipografia pede ruido FINO, objeto pede ruido grosso.** O mesmo preset nos dois
    erra: ruido grosso na letra deforma a forma; ruido fino no objeto nao aparece. Para
    texto use `size` pequeno (~22) — erode a borda como tinta em papel aspero.

43. **Textura nao deve escalar junto com intensidade.** `BOIL_SCALE` regula tremor;
    baixar o tremor dos objetos nao pode apagar a erosao de impressao da tipografia.

44. **Medir a referencia, nao imitar a impressao dela.** Uma legenda que "parece entrar
    animada" pode ser corte seco puro, com a fluidez vindo da cadencia: imitar a impressao
    acrescenta 4 frames de easing que a referencia nao tem. Antes de reproduzir um estilo, extraia os frames e meca:
    massa de tinta por frame, deslocamento, escala, bbox, cor.

45. **Acento raro e acento.** Pintar a palavra-chave em toda frase mata o dispositivo.
    Medido na referencia: 94% das linhas em branco puro.

46. **Blocos de legenda nao podem se sobrepor no tempo.** O render escolhe o primeiro
    que casa e o seguinte entra atrasado — perde a sincronia que faz o corte seco
    funcionar. Trunque `e` no `t` do proximo.

47. **Bloco de legenda nunca atravessa um corte do clipe.** Junta o fim de uma frase com
    o comeco de outra e le como erro de decupagem.

## Entrada da cena

62. **`p(0, 0, N)` devolve ZERO — o heroi fica invisivel no frame 0.** A regra do cutaway
    e que ele ja esteja em voo ali: o corte E a revelacao, nao o comeco de uma animacao.
    Escrever o evento de entrada como `(0, 12)` parece certo e produz exatamente o defeito
    que a regra existe pra evitar. Comece NEGATIVO: `(-8, 10)` poe o objeto 83% pousado no
    frame 0, ainda descendo; numa entrada longa, `(0, 30)` vira `(-8, 22)`.

63. **Cena que vem de PUSH nao pode abrir vazia.** Vindo de `flash` o estouro cobre os
    primeiros frames e o vazio nao aparece; vindo de `push` o corte e limpo e o vazio fica
    exposto: um grafico de fecho que abre com 0,25s de papel vazio comeca a cena mais
    importante da peca com nada. Ancore a ENTRADA do elemento de chao (eixo, fundo,
    linha) em frame negativo e so a informacao na palavra.

## Texto sobre imagem

58. **Contraste interno e contraste externo sao problemas diferentes.** A tinta pode ler
    perfeitamente contra a faixa que tem por tras (interno 8,9) e o bloco inteiro sumir
    na foto (externo 1,0). O primeiro decide se da pra LER; o segundo, se da pra NOTAR.
    Corrigir a cor do texto nao resolve o segundo — o que resolve e separar o bloco da
    imagem. Meca os dois: `python3 lib/legibilidade.py com.png sem.png`.

59. **Legenda sobre footage precisa de scrim, e sombra nao basta.** Legenda creme com
    sombra projetada sobre carroceria vermelha mede contraste externo de **1,02** —
    invisivel. Com `kit.scrim_inferior(altura=560, forca=0.62)` o mesmo bloco vai a
    **7,00**. O scrim nao e gradiente decorativo (proibido pela identidade): e a
    vinheta do proprio `finish`, assimetrica. Gradiente decorativo e faixa sobreposta;
    isto e a foto perdendo luz na borda, que e o que uma lente faz.

60. **O WCAG subestima bloco de cor saturada — some o croma.** Etiqueta amarela sobre
    carroceria vermelha mede razao de luminancia 2,7 (que "reprovaria") e o olho separa
    as duas sem esforco: a diferenca esta no matiz, nao no brilho. Regra: para o TEXTO
    ser lido so luminancia serve (o interno); para o BLOCO ser notado, luminancia **ou**
    croma Lab >= 28 basta. `legibilidade.py` mede os dois — nao reprove um bloco amarelo
    so porque a razao de luminancia e baixa.

61. **Etiqueta amarela sobre FOTO precisa de sombra; sobre papel, nao.** Sem
    `yellow_label(sombra=True)` a faixa fica colada na imagem e o croma sozinho carrega
    o trabalho. Sobre papel a sombra de contato da fita ja resolve e a sombra extra
    engorda a cena.

## Recorte de foto do mundo real

55. **Objeto fotografado em ambiente nao e objeto sobre fundo neutro — e outro problema.**
    `cutout.py` pressupoe fundo chapado escolhido por luminancia. Numa foto de museu, rua
    ou salao, o fundo tem a MESMA cor de partes do objeto: o cromo, o farol e o numero
    branco de um carro tem a luminancia e a saturacao do piso branco. Nenhuma regra
    automatica separa os dois — nem saturacao, nem luminancia, nem as duas juntas: ou a
    placa do museu vem junto, ou a grade do radiador vai embora.
    **A resposta nao e insistir no matte: e trocar de registro.** Foto de ambiente entra
    como `foto em cartao` (a margem branca isola o fundo) ou `foto em tela cheia`. Recorte
    e para objeto fotografado DE PROPOSITO sobre fundo neutro.

56. **Componente conectado: abra ANTES, feche DEPOIS.** Fechar a mascara antes de rotular
    componentes ponteia o objeto no que estiver perto — uma sombra de 2px basta para
    grudar a placa do museu no carro. Ordem certa: `OPEN` (tira ruido) -> `connectedComponents` ->
    maior -> `CLOSE` -> preenche buracos.

57. **Preencha os buracos do componente escolhido.** Cromo, farol, raio de roda e numero
    branco sao INTERIORES do objeto que falham no teste de cor e viram componentes
    separados — descartados junto com o fundo, o objeto sai oco. Flood a partir das quatro
    bordas no negativo; o que o flood nao alcanca e buraco e volta. Isso recupera o que
    esta CERCADO — o que toca a silhueta (uma grade na ponta do capo) nao volta, e e o
    sinal de que o matte nao serve.

## Etiqueta amarela

54. **`progress` logo acima de 0,55 nao e "texto quase pronto" — e quase nada.**
    `yellow_label` reparte o progresso em duas fases (0-55% pinta a faixa, 55-100% revela
    o texto): `progress=0,62` da 15,6% de revelacao do texto, nao 62%. Com `mode="block"`
    a opacidade e literalmente `alpha_original * progress` (`text_layer`, `voxlab.py`),
    entao 15,6% e uma mancha quase invisivel — tinta escura sobre amarelo em opacidade
    baixa lê como "sumiu por baixo da faixa", nao como "escrevendo". Para o estado final
    de uma cena, use `progress=1.0`. Para um MID real, calcule contra a curva: o texto so
    fica legivel (ainda que suave) a partir de uns 75-80% do progresso total.

## Empacotar identidade

29. **Fonte de sistema trava a identidade numa maquina.** As do macOS nao podem ser
    redistribuidas. Use fontes de licenca livre e coloque-as DENTRO da skill, com os
    arquivos de licenca. Ao trocar, meca: Archivo Narrow e 1,35x mais larga que DIN
    Condensed, e o mesmo corpo estoura a composicao.

30. **Fonte variavel abre no peso padrao.** `ImageFont.truetype` de um `[wght].ttf` da
    Regular, nao o peso que a identidade pede. Trave o eixo com `set_variation_by_axes`.
    `getname()` continua reportando o nome base — nao serve de verificacao; mede densidade
    de tinta.

31. **Teste de instalacao limpa e obrigatorio.** Monte um diretorio vazio so com o que a
    skill entrega e renderize um frame. Isso pega defeitos invisiveis na leitura:
    constante fora do modulo compartilhado, `__all__` definido antes das funcoes
    existirem, nome de arquivo divergindo entre o kit e o codigo.

## Manutencao do kit

68. **Correcao gravada numa copia que nao roda se perde.** Duas copias da skill (a
    instalada e uma copia dentro de uma pasta de projeto) divergem rapido: cada uma fica
    com correcoes que a outra nao tem, e as mais importantes podem estar justamente na que
    nao carrega. Grave toda correcao na copia instalada, e so nela; se precisar da skill
    em outro lugar, use link, nao copia.

69. **Helper que nasce num projeto sobe para `lib/kit.py` antes do projeto seguinte.**
    Funcao criada dentro de um `compose.py` e aprovada (trama de jornal, borda rasgada,
    balao de fala, carimbo, contagem manual) e reinventada em cada projeto novo se ficar
    la. Correcao que so vive num projeto e reativa: volta a acontecer no proximo.

## Estado e processo

20. **`END` amostrado antes do último evento** mostra texto pela metade. Confira
    programaticamente: `END >= max(fim de evento)`.

21. **`EXIT` além do fim do plano** sugere um estado que nunca vai ao ar.

22. **`str.replace()` falha em silêncio.** Confirme cada patch por `grep -cF`.

23. **Métrica global engana.** Um rótulo de 270×90px num quadro 1080×1920 move menos de
    0,2% dos pixels: aparece como "parado" numa média global. Meça **dentro da caixa do
    elemento**.

24. **Objeto parado por segundos morre em cena.** Relógio congelado nega a própria ideia
    de tempo correndo. Dê ao menos um movimento lento e contínuo.

25. **Mostrador às 6h vira linha reta**, indistinguível de 12h em tela de celular.
    Prefira uma hora que forme L.

## Relógio, formato horizontal, recorte e render

64. **Dois relógios (desenho 16 + boil 9) não são o estilo medido.** A referência Porsche salta tudo junto a 12 fps,
    e o kit usa 12. `MOTION_FPS = 12` + `RELOGIO_UNICO = True` no bloco CLIPE; `V.BOIL_FPS` segue o relógio,
    e o grão troca a cada passo dele. As transições (flash, push) continuam fluidas.
65. **Corte horizontal em 4K quebra o concat.** O corte H sai no tamanho da fonte (3840×2160), e as cenas
    desenham em 1920×1080: o `concat` falha em silêncio (exit 234). Reduza o corte H para o quadro do kit antes
    de compor (`scale=1920:1080:flags=lanczos`, áudio copiado); compor em 4K amoleceria os assets de 1400 px.
66. **Legenda calada demais em fala rápida.** Com frase = até o ponto final, "frase inteira sai" cala o vídeo
    inteiro por um nome pendente, porque o Whisper quase não pontua. `janelas_legenda.py` corta em oração
    (vírgula ou vão ≥ 0,15 s).
67. **O layout H não é o vertical encolhido.** Reaproveitar o layout vertical no H corta a pilha no topo e deixa o
    texto pequeno. Cada cena escolhe o layout por `ORIENT` (pilha à esquerda e texto à direita, split lado a lado),
    com posição em `X()`/`Y()` e tamanho em `U`.

**punch_bg fura o próprio objeto quando ele tem peça lisa da cor do fundo**
- Sintoma: buraco transparente no meio de uma peça de metal (a luva do conector do MAO_CABO), com contorno de ameba, visível nos quatro QA (_branco, _preto, _alfa, _tiles).
- Causa: a P3 do `cutout.py` fura fundo encapsulado por cor + gradiente. Metal escovado liso na luminância do fundo é indistinguível de fundo cercado.
- Correção: `punch_bg` só quando o fundo cercado é o único jeito (miolo de clipe, olhal de etiqueta) **e** o objeto não tem área lisa e neutra na faixa do fundo. Ilha solta sai com `min_area`, que não fura nada.

**Resto de fundo colado no objeto não sai por punch_bg nem por min_area**
- Sintoma: placa cinza chapada sob os dedos fechados, com aresta reta e degrau em escada.
- Causa: o resto **toca** o objeto: o flood não entra (não é borda) e o `min_area` não solta (não é ilha).
- Correção: apagar por medida no canal alfa — pixel neutro (max−min < 12), luminância na faixa do fundo, laplaciano baixo, componentes acima de um mínimo, dilatados e restritos ao que já era neutro. **Com limite de posição**: nada que toque a região do herói entra na regra, senão come o objeto.

**Legenda com 0 janelas não pode derrubar o mux**
- Sintoma: as cenas renderizam todas, o log diz "0 janelas de legenda configuradas (deliberado) — nada a verificar", e aí o ffmpeg morre com `Could find no file or sequence with path .../CAP/%04d.png`. Perde-se o render completo no último passo.
- Causa: um `mux()` que soma a pasta CAP como entrada e o `overlay` como filtro sempre, mesmo sem nenhum quadro de legenda.
- Correção: `tem_cap` decide a entrada, o overlay, o `base_idx` do áudio e o rótulo mapeado (`[vout]` com legenda, `[vbase]` sem).

**Duas variantes do piloto em paralelo apagam os quadros uma da outra**
- Sintoma: com várias variantes do piloto disparadas juntas, parte delas morre com `FileNotFoundError: '0065.png'` dentro de `shutil.rmtree`; as outras saem com a duração certa, mas podem ter muxado quadros da variante errada (um "com flash" com a saída de cena do "sem flash").
- Causa: `SEQ = 10_sequences/<SAIDA>` é o mesmo diretório para `--fim flash` e `--fim sem_flash`; cada `render()` começa com `rmtree` da pasta da cena e reescreve os PNG por cima do outro processo.
- Correção: `SEQ = 10_sequences/<SAIDA>/_var_<FIM>` quando há `MV_FIM`; o PILOTO continua em `10_sequences/<SAIDA>/`; o master (sem `MV_FIM`) segue no diretório de sempre. Num `render.py` sem essa separação, rode as variantes da MESMA saída uma de cada vez.
