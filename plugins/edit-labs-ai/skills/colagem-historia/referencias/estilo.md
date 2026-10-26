# O estilo: colagem de papel antigo para curiosidade histórica

Cada regra traz o porquê. Os números já são o padrão do motor (`${CLAUDE_PLUGIN_ROOT}/motor/colagem/`).

## O formato

- 9:16, 1080×1920. O vídeo sai a 28 qps com **14 desenhos por segundo** (cada desenho dura 2 quadros). Os tempos do
  roteiro ficam em quadros de 24.
- **Duração:** de 20 a 32 s. Uma história com começo, virada e fim.
- **Sem voz** por padrão. Texto curto, música calma e efeitos de papel.
- **Público:** PT-BR simples, gente que vê no celular e muitas vezes enxerga mal. Nada pequeno nem abstrato.

## O material

- **Fotos reais impressas** em cartões de borda clara presos com fita (`PC.cartao`). Pessoas e objetos entram
  **recortados**, com a borda branca de tesoura (`PC.recorte`). Tudo vai sobre papel creme envelhecido.
  - **Regra:** quanto mais fotos reais e menos texto, melhor.
  - **Por quê:** a foto de época é a prova. Clip-art e texto explicando parecem aula.
- **Objetos concretos** explicam a cena sem palavra: o chapéu verdadeiro, a régua do rei, o navio, o baú, o
  microscópio. Faça uma rodada de busca só de objetos por reel (de 4 a 7).
- **Mapa antigo** para toda rota. **Página do documento** para toda medida ou citação.
- **Recorte local**, sem crédito: `swift "${CLAUDE_PLUGIN_ROOT}/motor/colagem/recorte.swift" entrada.jpg pecas/x.png`
  (macOS 14+). Confira sobre fundo azul. Se pegar moldura ou fundo, corte a entrada antes e refaça. Um recorte ruim é
  pior que nenhum.

## O mundo de papel

- A câmera viaja por um mundo grande (de 3400×4300 a 9400×5800 px), dividido em **áreas**, uma por parte da história.
- **Escala real** quando a história é de tamanho: régua de 10 px = 1 cm, chão numa linha fixa, cada pessoa com a
  sola no chão e o topo da cabeça na altura medida.
- **Áreas separadas na horizontal** quando há zoom aberto (z < 0,45). Senão, o rodapé de um plano mostra a área
  seguinte.
- **Papel carvão** (`C.papel_area`) marca os momentos dramáticos: a noite do roubo, o exílio, a morte, o domingo em
  que todos iam embora. Ele fica preso à área, com distância das vizinhas, e nunca é fundo global (vazava).

## A caneta vermelha

- **Em todo reel há um traço vermelho com sentido:** rota no mapa, medida na régua, contorno de um vão, fio de
  telefone, sublinhado no documento, X no número errado.
- A caneta é o **único acento de cor** (vermelho `PC.VERMELHO`). A tinta preta e o papel creme fazem o resto.
- Na rota, a **câmera segue a ponta** (`Camera.seguir(traco, q0, q1, z, tela=(x, y))`) e um objeto viaja nela
  (`C.segue`), virando de lado quando o traço volta.
- O traço tem tremor de mão baixo e lento, nunca reto de régua de computador.
- O traço de caneta faz som contínuo (não é um clique).

## Peças que se transformam

Batidas iguais (a câmera vai até um cartão parado, o cartão cai e fica) leem como slide. Varie:

| movimento | função no motor | exemplo |
| --- | --- | --- |
| cartão que vira | `C.vira` | o retrato vira a caricatura e volta; a foto da torre vira a capa da revista |
| multiplicar | `C.multiplica` | capas de jornal; telefones de parede ("todo mundo quis um") |
| estilhaçar | `C.estilhaca` | o cérebro em blocos que voam para os potes |
| seguir o traço | `C.segue` | o navio na rota; o relógio de bolso voando até o pulso |
| entrar deslizando | `C.desliza` | o granadeiro marchando; o imperador chegando |
| cair e pousar | `C.cai` | toda peça nova, com pouso macio |
| letras que se montam | `C.letras` | só a resposta ("1,69 m") |
| explosão radial | `C.rajada` | só no carimbo |
| ondas | `C.ondas` | a voz que sai do telefone |
| grade em losango | `PC.grade` | fundo claro atrás de um objeto, nunca na frente |

## Transições

Cada passagem tem uma transição **diferente** (`M.Transicao`) e sai **do ponto onde o olho está**:

- **mergulho:** a câmera afunda num detalhe (o vão da moldura, a cabeça, o mostrador) e sai de dentro da cena
  seguinte (`centro`, `centro_b`);
- **íris:** um círculo abre a partir de um ponto, com aro de papel;
- **rasgo:** uma borda de papel rasgado varre a tela;
- **empurra:** uma cena empurra a outra, com rastro (`direcao`);
- **flash:** a imagem passa pelo papel claro.

Entre o `q0` e o `q1` de uma transição, a câmera precisa ter um plano em cada ponta. O motor mostra a câmera em `q0`
saindo e a câmera em `q1` entrando.

## Câmera e movimento

- Um plano por batida, enquadrado pela **região segura** (`C.quadro(caixa, regiao)`), com **deriva lenta** (zoom
  ×1,02–1,04 até o próximo plano).
- **Borrão** só nos chicotes muito rápidos, e leve. **Nunca atravessa um corte:** o 1º desenho depois de uma
  transição é sempre nítido. (O rastro aplicado sobre o salto de câmera esticava o personagem.)
- **Pouso macio** dos objetos, cruzamento longo no mergulho, rastro só nas viradas rápidas.

## Acabamento (o padrão do motor; comece leve)

- **Boil** (o tremor das bordas): ~1 px **na tela**, ciclo de 3 formas e uma troca a cada 4 desenhos (3,5 por
  segundo, um ritmo de FPS baixo). Se ainda parecer rápido, use `BOIL_SEGURA = 6` (2,3 por segundo).
  - **Por quê:** o boil aplicado antes do zoom virava 6–7 px na tela, e o sorteio a cada desenho lia como vibração.
- **Filme Fuji leve:** grão de ~4,6/255 trocando 7 vezes por segundo (abaixo de ~4 o H.264 apaga), aberração RGB
  radial de ~1,8 px nos cantos, vinheta de câmera de 5% + vinheta de papel a 0,2 (cantos ~15% mais escuros). Preto
  lavado, sombras levemente verde-azuladas, altas luzes quentes, saturação um pouco menor.
  - **Regra:** sempre "bem pouco". Meça antes de mexer.

## Texto

- **≈ 40 palavras de legenda no vídeo inteiro**, até 8 por frase, com as palavras-chave em vermelho (`*palavra*`).
- A **legenda** é uma tira de papel, sempre no mesmo lugar (y 1320), com corpo de 64 px e até 880 px de largura. Ela
  quebra sozinha, e número e unidade nunca se separam.
- **Nomes e datas** viram **etiqueta** (tira de papel presa ao objeto) ou **carimbo** vermelho, e não frase.
- O **carimbo** pode ocupar o lugar da legenda no fecho ("ACIMA DA MÉDIA").
- Texto e carimbos entram **por último** (modelos: `--sem-texto` até a fase final).

## Conferências antes de entregar

1. `--margens`: objetos cortados ou fora da região segura.
2. `M.ajustar_texto` (roda sozinho): aumenta a etiqueta ou o carimbo que ficar menor que 50–58 px na tela e lista o
   que mudou.
3. Folha de quadros a cada 1,5 s com as perguntas do REGRAS.md §10.
4. `conferir.py <projeto> previa/sem_som.mp4`: desenhos borrados fora das transições e texto ainda pequeno. Os únicos
   alarmes aceitáveis são o cartão virando (ele estreita de propósito) e a legenda entrando.
