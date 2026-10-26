# Colagem em camadas: a técnica

O objetivo: uma colagem de papel que **se monta e se desmonta**.
- A mesma folha tem camadas que encaixam (corpo → músculos → órgãos → esqueleto).
- As peças saem do lugar e mostram o que há embaixo (a luva sai da mão, e a mão está lá).
- Objetos 3D giram a 7 qps como stop-motion de recortes.

Motor: `${CLAUDE_PLUGIN_ROOT}/motor/colagem/` (ver o `LEIA.md` de lá). Exemplos: `../exemplos/`.

## Os exemplos

| exemplo | caminho | mecânicas | material |
| --- | --- | --- | --- |
| manequim de 1890 (`cena_manequim.py`), **a referência do estilo** | 2D real | 9 peças de verdade saem uma a uma (as grandes saem da tela, as pequenas ficam paradas no ar) e voltam em ordem inversa | boneco de papel de 1890, Wellcome (domínio público) |
| luva de boxe (`cena_luva.py`) | 3D | `levanta` (a luva sai), `janela` (a pele abre), osso que acende + caneta, `destaca` + `giro` + `pousa` (os ossos saem, giram e voltam), `janela` fechando e a luva voltando | Z-Anatomy + luva de J-Toastie (CC BY 3.0) |
| crânio (`cena_cranio.py`) | 3D | `giro` do crânio, a tampa descola e sai voando, o líquor enche como água, o cérebro `destaca` + `giro` + `pousa`, tranco do soco com o cérebro atrasado, a tampa volta e encaixa | Z-Anatomy (crânio) + BodyParts3D (cérebro) |
| estalar os dedos (`cena_estalar.py`) | 3D + voz | mão com esqueleto (dedos que dobram), `janela` na pele sobre o nó, a junta com a bolha que nasce, rajada e estalo no mesmo quadro | Z-Anatomy + junta própria |
| corpo humano (`cena_homem3.py`) | foto real + 3D | foto de arquivo recortada em peças, tchau com poses geradas a partir da própria foto, `janela_forma` no tronco, anatomia encaixada, coração que sai, gira e volta | foto CC0 + Z-Anatomy + BodyParts3D |
| Terra (`cena_terra.py`) | 3D próprio | `giro` a 7 qps, a fatia `levanta`, as cascas se separam (`explode`) | modelo próprio, sem licença de terceiros |
| teste rápido (`teste_rapido.py`) | código | `janela`, `levanta`, `pousa`, `pulsa`, carimbo | nada (confere a instalação) |

## As três ideias

1. **Camadas registradas:** as camadas têm o mesmo tamanho e a mesma âncora, então encaixam pixel a pixel. Vêm de:
   - **modelo 3D renderizado** pela mesma câmera (encaixe perfeito; o melhor caminho);
   - **fotos do mesmo objeto, tirando uma peça por vez** (o manequim de 1890): a peça é a diferença entre duas fotos;
   - **duas imagens alinhadas** por `registrar()` (ECC), quando as pranchas são gravuras separadas (Albinus).
2. **Revelar o que está embaixo** (`camadas.py`):

   | mecânica | o que se vê | quando usar |
   | --- | --- | --- |
   | `aba` | a camada abre como a aba de um livro de anatomia: gira na dobradiça, com perspectiva, escurece de lado e mostra o verso de papel | pele → músculo; abrir uma porta, uma capa, uma tampa |
   | `metades` + 2 `aba` | a camada corta ao meio e abre como duas portas | o peito que abre, um armário, um livro |
   | `janela` / `janela_forma` (com `fecha=`) | um buraco de papel rasgado cresce a partir de um ponto (ou com a forma de uma máscara), com a borda branca e sombra dentro; pode fechar de novo | "olhe aqui dentro": a mão, o crânio, o tronco |
   | `descasca` (com `volta=`) | uma borda rasgada atravessa a camada e leva o papel; pode voltar | trocar uma camada inteira de uma vez |
   | `levanta` | a peça descola (cresce e a sombra se afasta), sobe e sai girando | a luva sai da mão, as costelas saem do peito |
   | `destaca` / `pousa` | a peça descola e vem para o meio, crescendo; depois volta e assenta no papel | o coração sai do peito para girar e volta |
   | `explode` (com `desloc=`) | as camadas se separam (vista explodida ou grade) e voltam | mostrar as camadas lado a lado |
   | `pulsa` | a escala segue um padrão que se repete, sem mexer nas chaves de movimento | o coração bate, o pulmão respira |
   | `cortar_alfa` | tira uma peça do quadro registrado sem perder o lugar | toda peça que vai sair |

3. **Giro 3D a 7 qps** (`camadas.giro` + `blender_giro.py`):
   - o Blender renderiza N vistas (36 = uma a cada 10°) de cada camada, todas pela mesma câmera;
   - `papelizar()` transforma cada vista em peça de papel (gravura pontilhada sépia colorida à mão), sempre com a borda
     branca de tesoura;
   - na tela, a vista troca 7 vezes por segundo, mesmo com a câmera a 14: parece um recorte girado à mão;
   - **a troca peça → giro é invisível:** câmera ortográfica nas duas, a vista 0 do giro é igual à peça, e a escala
     vem de `px_por_m` (`vistas.json`): `esc_giro = px_por_m_cena × E × aumento / px_por_m_giro`.

Todas as mecânicas andam em degraus de 7 qps (stop-motion), menos a câmera.

## Receita de um vídeo novo em camadas (3D)

1. **Montar o .blend com as camadas** (`anatomia_blender.py`, `mao_blender.py`, `cranio_blender.py`): importar os GLB,
   pôr prefixo por camada no nome (`pele__`, `osso__`...), cor de prancha em sRGB (o script converte para linear) e, se
   precisar, posicionar uma peça sobre a outra (a luva foi girada, espelhada e escalada pela caixa da mão).
2. **Renderizar** com `blender_giro.py` e um `cfg.json` (modelos em `exemplos/cfg/`, rodados por `preparar.py`):
   - `"lente": 0` (ortográfica), `"ajuste": "caixa"` e `"caixa_mundo"` para o recorte (ex.: só o busto);
   - `"passes": ["cor", "luz"]`; `"camadas"` por regex do nome;
   - para o giro: `"enquadrar": ["coracao"]`, 36 vistas.
3. **Papelizar** com `registrado=True` e guardar em cache. O nome do cache leva a pasta das vistas, porque o giro e a
   cena têm camadas com o mesmo nome. Grave o cache num temporário e renomeie (dois renders ao mesmo tempo corrompem
   o PNG).
4. **Cena**: uma função `mundo(x, z)` leva metros do modelo para px do mundo; a pilha vai de baixo para cima; câmera
   por `C.quadro(caixa(...))`; `M.ajustar_texto` antes de renderizar.
5. **Som**: `som_auto.mixar_auto` lê o `L.som` de cada mecânica (vira, descasca, levanta, janela, giro, pouso,
   caneta, chicote) e sintetiza um efeito por ação.

## Receita com fotos reais de um objeto que se desmonta (2D)

`exemplos/manequim_pecas.py`:
1. Recortar a figura do fundo liso (saturação + distância da cor do fundo, maior componente, buracos fechados).
2. Para cada par de estados (de cima → de baixo): diferença em Lab desfocada > 14, limpeza morfológica, buracos
   fechados. A peça é essa região recortada da foto de cima. Pular estados junta peças (cérebro + rosto).
3. Na cena, o estado de baixo aparece no mesmo quadro em que a peça começa a levantar: a troca não se vê. Na volta, o
   estado de cima reaparece quando a peça pousa.

## Bom gosto e vida

Regras: contraste para ver a diferença entre as partes; nada que cause estranheza; o mesmo ângulo em todas as camadas;
vida (um braço que mexe, um tchau antes de olhar dentro); sempre algo a mais.

| o que causa estranheza | por quê | a regra |
| --- | --- | --- |
| costura branca do meio desde o primeiro quadro | parece defeito | a abertura segue uma borda real (o paletó abre pelo botão) |
| abas que viram "fantasmas" de papel com formato de meio corpo | sobra sem sentido | o que abre mostra o verso real (forro) e fica aberto como na vida |
| rosto de músculo, sem olhos | assusta | a cabeça fica; só o peito abre |
| câmera que vai e volta (zoom in, zoom out) | indecisão | um caminho só: busto → tronco → peito → detalhe → volta |
| chicote seco para uma grade de corpos pequenos | quebra e coisa pequena | tudo volta para o lugar no mesmo corpo |
| ossos girando em cima da mão parada | ângulos diferentes um sobre o outro | o que gira sai antes para o papel limpo, e a câmera vai junto |
| coração girando em cima dos pulmões | fundo poluído | o coração vai para o lado, no papel limpo |
| texto que entra antes da coisa aparecer | o texto adianta o olho | o rótulo entra depois que a revelação termina |
| close do peito cortando o rosto no nariz | corte feio | o close corta num limite natural (o colarinho, o queixo) |
| câmera que chega antes da peça e sobra um quadro vazio | buraco no olhar | a câmera anda junto com a peça: começa e termina com a viagem do `destaca`/`pousa` (30% e 75% da duração), na mesma curva `io` |
| figura pequena no plano aberto | difícil de ver | a figura ocupa a região segura; ≥ 600 px |
| peças pequenas sumindo no corpo inteiro | invisível | as peças pequenas saem um pouco e ficam paradas no ar (vista explodida) até voltar |

- **Contraste:** fundo do corpo em papel quase preto; cada órgão numa cor bem diferente (pulmão salmão, coração carmim,
  fígado chocolate, intestino ocre, osso marfim); `papelizar(contraste=1.6, cor=1.0)` deixa o contorno de tinta mais
  firme e a aquarela sem desbotar.
- **Vida:** esqueleto de animação no Blender renderizado a 7 qps; respiro em laço de 28 desenhos; `camadas.pulsa` faz o
  pulmão respirar e o coração bater (70 por minuto) sem brigar com as chaves de movimento (`sm` no motor).
- **Mesmo ângulo:** só o exterior se mexe; o interior aparece pela abertura do tronco parado; o que gira sai antes.
- **Regra da profundidade:** o que viaja (coração, costelas) é uma cópia por cima de tudo. A peça que fica no peito
  continua na profundidade certa e some enquanto a cópia viaja; senão a peça passa por trás da roupa.

### Personagem 3D: o que deixa um boneco "deformado e estranho"

| problema | por quê | a regra |
| --- | --- | --- |
| rosto de manequim careca, olhos vazios | o atlas tem buracos no lugar dos olhos | globos oculares com íris e pupila, sobrancelhas e cabelo |
| chapéu grande, flutuando | maior que a cabeça | do tamanho da cabeça, assentado na testa |
| gola em tubo (colar cervical) | larga e alta demais | anel justo medido no pescoço, aberto na frente |
| terno colado no corpo, com peito e barriga desenhados | parece roupa de mergulho | o tronco cai reto; manga folgada; ombro reto de alfaiataria |
| lapela e camisa pintadas por cima do paletó | não "encaixa" | camisa é outra malha, por baixo; o paletó tem o V recortado na malha |
| o paletó abre num retângulo | não é recortado na roupa | as portas são a frente do paletó pelas bordas reais |
| ombro que quebra no tchau | braço alto com pele colada | braço a 30°, o antebraço faz o aceno; manga folgada |

Mesmo corrigido, **para gente, foto real de arquivo recortada em camadas** lê melhor que personagem 3D feito sobre o
atlas. O boneco 3D fica para quando não houver foto.

## Como não repetir as quebras

Cada quebra tem causa, regra e, quando dá, uma checagem automática (`motor/colagem/conferir_figura.py`, que roda ANTES
do vídeo). O vídeo só sai com zero problemas, ou com cada achado explicado (vão natural entre braço e corpo, osso fino
de verdade).

| quebra vista | causa raiz | regra | checagem |
| --- | --- | --- | --- |
| axila rasgando no tchau | faces de ligação perto do ombro apagadas para separar braço e tronco | nunca apagar face perto de junta que deforma; o corte só vale longe dela (> 20 cm) | `buracos` |
| cunhas brancas no ombro quando o paletó abre | a frente tirada (uma máscara) não era a porta devolvida (outra máscara) | tirar e devolver da MESMA imagem com a MESMA máscara | `composto` |
| franja branca no V | o avesso das costas, pintado de branco, aparecia pelo V | apagar as faces de costas; o que fica atrás de uma abertura é escuro | `composto` |
| borda branca esfiapada nas juntas do 2D | o corte interno ganhava a borda de tesoura | borda branca só por fora da silhueta da figura inteira (`papelizar(silhueta=)`) | `composto` |
| mão cortada | a caixa do render acabava no quadril | a caixa contém todas as peças em todas as poses | `cortados` |
| calombo na virilha | normais personalizadas do glTF e faces dobradas | limpar as normais depois de editar a malha; separar com corte reto | olho |
| punho sumindo | `materials.clear()` zera o índice de material | marcar os índices DEPOIS de criar os materiais | olho |
| V serrilhado | a curva que escolhia as faces era outra que a reta do corte | cortar na mesma reta que escolhe as faces | `lascas` |
| lascas na barra, no punho e embaixo do braço | corte reto feito ANTES de alisar e afastar a malha | o corte reto é sempre o ÚLTIMO passo da forma; `apara_lascas` no alfa antes do papel | `lascas` |
| peça passando por trás da roupa | a peça que viaja estava na profundidade dela | o que viaja é uma cópia por cima; a original some enquanto isso | olho |
| traço que engrossa na troca do giro para as camadas | o giro tinha outro px/m | papelizar o giro na densidade das camadas; centro do giro MEDIDO por casamento de alfa (IoU ≥ 0,99) | casamento de alfa |
| dente na borda da porta aberta | a manga era tirada da porta pixel a pixel | a borda de fora segue a manga e desce em reta; só a peça principal fica | máscara isolada |
| "image file is truncated" | dois renders escreviam o mesmo cache | gravar num temporário e renomear (atômico) | — |
| ponta branca no cotovelo do boneco 2D | a silhueta da borda vinha de outra pose | a silhueta da borda é a das PRÓPRIAS peças, na mesma pose | `faltando` |
| furo do osso com borda branca por dentro | furo pequeno e fechado no alfa mostra o fundo | `fecha_vazados`: o furo vira sombra escura antes do papel | `composto` |
| etiqueta encostando na figura | o ajuste de leitura aumentou a etiqueta DEPOIS de posicionada | a etiqueta nasce no tamanho de leitura e só depois é posicionada | `ajustar_texto` não imprime nada |

Falsos alarmes conhecidos do `composto`: punho e camisa brancos, lisos como o papel; a borda rasgada de propósito da
janela; a ponta fina do vão natural entre o braço e o corpo. Cada achado gera uma imagem `_defeito_*.png`: olhar a
marca antes de descartar.

**Revisão de espectador (o que a conferência automática não pega).** Uma figura "limpa" de furo e lasca ainda pode
estar estranha: olhos esbugalhados, pele granulada, paletó de super-herói, portas que viram asas, tronco sem cabeça,
janela de músculo que vira bola vermelha, líquido que pinta o órgão de lilás e fica em pé, um soco que não se vê.
Antes de entregar, montar a folha de quadros no tamanho da tela (um a cada ~1,5 s) e responder por escrito
(`portao-de-qualidade.md`).

Ordem de conferência de uma figura nova:
1. `python3 -I conferir_figura.py lascas <pasta dos renders>`, `buracos` (com o repouso de referência) e `cortados`.
2. A cena com `--conferir` (quando houver): só a figura sobre magenta, nos quadros de risco (abrir, fechar, tchau,
   troca de camada).
3. Os quadros de risco do vídeo pronto em resolução cheia. O olho é a última palavra, mas só olha depois das checagens.

## Articulação de uma foto real (o tchau do homem de terno)

O que NÃO funciona: girar o recorte do braço (vira um palito em V, porque a manga está colada no corpo); completar com a
textura da própria foto (o braço continua fino); usar a mão de outra fonte, como o atlas (não combina com a pessoa).

O que funciona (`homem3_poses_ia.py`):
1. **Calcular as juntas.** Marcar ombro, cotovelo e punho e conferir com as proporções humanas (Drillis & Contini:
   braço 0,186·H, antebraço 0,146·H, mão 0,108·H, ombros 0,259·H). Um pivô fora do lugar denuncia o erro.
2. **Gerar as poses da parte que mexe com IA de imagem, a partir da PRÓPRIA foto** (Higgsfield, com a foto como
   referência e "mude SÓ o braço", mesma pessoa, roupa, luz e grão). Duas poses bastam ("meio" e "alto");
   alternadas, já são o aceno.
3. **Compor sobre a original:** registro por SIFT + RANSAC só no rosto e no tronco; tom casado por quantis no corpo
   INTEIRO; da gerada entra só o lado do braço; o rosto e o resto do corpo são sempre os pixels da foto.
4. **Animar trocando as poses em degraus** (stop-motion), sem girar recorte.

Regras: pessoa real nunca tem o rosto gerado; nunca usar peça de outra fonte num personagem de foto; o crédito diz que
o braço foi gerado por IA a partir da foto.

## Reel narrado em camadas: seis passos (exemplo do estalo)

1. **Roteiro** falado: frases curtas, cada número conferido na fonte (PubMed/PMC, artigo original) antes de a voz
   falar. O que não tem fonte não entra.
2. **Voz:** 3 amostras curtas para o usuário escolher; só depois, com "pode", a narração inteira.
3. **Decupagem:** transcrição palavra a palavra (faster-whisper) e tabela das pausas. Nenhuma pausa passa de ~0,6 s;
   se passar, cortar o silêncio antes de animar. Daqui saem as âncoras (a palavra em que cada coisa acontece).
4. **Plano de cenas:** para cada frase, o que aparece e que técnica chama atenção; no máximo 2 elementos gráficos. O
   momento forte junta som, rajada e tremor de câmera no MESMO quadro.
5. **Motion:** `q(t) = 10 + 24·t` põe cada evento no quadro da palavra; a voz entra no quadro 10.
6. **Vistoria:** checagens automáticas, folha de quadros (revisão de espectador) e conferência do som (voz −16 LUFS,
   trilha ~18 dB abaixo com ducking, efeitos 15–19 dB abaixo da voz).

Lições técnicas:
- **Duas escalas registradas:** a junta foi renderizada a 16.483 px/m e a mão a 9.615 px/m; o zoom de 3,2× da câmera
  deixa as duas em ~1:1. O ponto da articulação sai do Blender (`marcos`) e o ângulo (14°) sai de uma sobreposição de
  teste, nunca de suposição.
- **Peça animada no Blender com o `blender_giro`:** ele prende tudo a um vazio no centro; posição ABSOLUTA animada fica
  deslocada desse centro. Animar com `delta_location`.
- **Janela redonda só dentro da pele:** o interior é recortado pelo disco da janela E pela silhueta da pele.
- **Em escala de câmera:** traço e etiquetas no mundo se multiplicam pelo zoom. Elementos de tela vão em coordenadas da
  tela (`mundo=False`), posição `tela = 540 + Δx·z`.
- **Antebraço:** a imagem da mão vai bem além do punho; senão o corte reto aparece quando a câmera se mexe.
- **Estalo:** sintetizado (ruído curto, tom de 2,6 kHz e baque de 170 Hz), no quadro exato em que a bolha nasce.

## Mão com esqueleto: dedos que se mexem (`mao_rig_blender.py`)

Mão parada com só os ossos mexendo dentro da janela fica simples demais. Como se faz:
1. **Articulações dos ossos medidos** (PCA de cada falange): MCP entre a cabeça do metacarpo e a base da proximal; PIP
   e DIP entre as pontas.
2. **Pesos por distância inversa** (p = 3) aos segmentos dos ossos, com a pele numa malha só. O repouso fica idêntico
   à mão original.
3. **Eixo de flexão** perpendicular ao dedo, no plano da palma; o sinal conferido numericamente.
4. **Girar a mão de lado** (30–40°) mostra a flexão; de costas, dobrar o dedo só o encurta.
5. **Clipes em quadros de 7 qps**, renderizados pelo `blender_giro` e colados em degraus.
6. **A pele acompanha o osso na janela** (osso que sobe dentro de pele parada não existe).
7. **A rajada sai onde o dedo mudou** (a diferença entre dois quadros), com o estalinho no mesmo quadro.
8. **A outra mão é a mesma espelhada**: os dois lados sempre simétricos.

Cuidados: todas as vistas com o MESMO enquadramento do repouso; sem um quadro de repouso entre dois clipes, a mão pula.

## Figura 3D em camadas, em vez de imagens avulsas

Cartões de gravura, raio X e pictogramas em sequência leem como slide. O certo é montar o vídeo em cima de UMA figura
(o modelo 3D em camadas registradas) e a ação morar nela.

- **Patamares de escala:** cada patamar (figura inteira, cabeça e pescoço, detalhe) é papelizado na sua densidade
  nativa (1 px de ponto). No mundo, `esc = px_por_m_base / px_por_m_patamar`. Base até zoom ~1,4; meio até ~3; alto
  acima. Troca de patamar com fade de 6 quadros enquanto a câmera anda.
- **`enquadrar`** define o pivô E a profundidade de corte da câmera ortográfica: com um marcador minúsculo as peças
  viram fatias finas; use uma camada de tamanho real.
- **Close-up nítido:** traço, círculo, ondas e partículas desenhados K vezes maiores e escalados de volta.
- **Ordem da lista = ordem de empilhar:** interior primeiro, músculo, pele por último. Marca-texto amarelo sobre o
  interior (a caneta vermelha some sobre o rosa).
- **Peça que o atlas não tem** vira modelo próprio, declarado no crédito.
- **Cena nova = canto novo do papel.** As transições usam a câmera em q0 (saindo) e em q1 (entrando); a cena que entra
  existe desde o começo da transição, e a que sai até o fim dela.
- **Carimbo sobre fundo ocupado** não lê: imprimir numa tira de papel.
- **Créditos:** camada de tela de 2,3 s no fim, com cada licença do vídeo.

## O que aprendemos nos testes

- **Dobradiça à vista:** a aba só parece porta se a câmera mostra a dobradiça.
- **Caneta vermelha some no vermelho:** sobre o coração, tinta escura; a volta passa por fora.
- **Fundo do corpo:** sob órgãos e ossos, uma silhueta de papel vinho escuro (contraste e profundidade da janela).
- **Nudez:** corpo cortado no quadril (busto), para o vídeo não ser barrado nas redes.
- **Blender:** `view_layer.update()` depois de carregar o .blend; render em "Standard" (o AgX desbota as cores chapadas).
- **Janela:** a sombra de dentro do buraco só cai onde há papel; fora da silhueta vira um halo cinza.
- **Giro 3D só quando a forma importa** (coração, mão de ossos, Terra), nunca de enfeite. Parar no ângulo que explica.
- **Terminar montando:** o fim mais forte é tudo voltar ao lugar.

## Fontes

- 3D: `FONTES_3D.md`. Pranchas: `FONTES_PRANCHAS.md`. Créditos e licenças: `../assets/CREDITOS.md`.
