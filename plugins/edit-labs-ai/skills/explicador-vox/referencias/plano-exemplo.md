# Exemplo do estilo: "Por que um soco no queixo apaga uma pessoa?"

Um plano completo de explicador Vox, para servir de modelo: 29,9 s em 9:16, só narração, sem rosto, o vídeo inteiro
é motion. Copie a forma (ideia em uma frase, elenco, mapa de batidas, orçamento, legenda, som), não o assunto. O
plano com cada chave está em `${CLAUDE_SKILL_DIR}/exemplo/plano.json` (gerado por `ferramentas/gera_plano.py
exemplo`); as peças, em `exemplo/pecas/`; a transcrição palavra a palavra, em `exemplo/palavras.json`.

> Por que um soco no queixo apaga uma pessoa? Um soco reto, no meio do rosto, só empurra a cabeça para trás. Já o
> gancho, de lado no queixo, passa longe do eixo. A cabeça não recua, gira. O queixo fica longe do eixo. Vira
> alavanca. Quanto mais longe, mais giro. E o cérebro está solto lá dentro. Quando o crânio gira, ele fica para trás
> e estica. Não é a força, é o giro.

- 28,9 s de voz, 137 palavras/min, mais 1 s de cauda para o título (q694 → q718).
- Timeline de 24 qps; desenho e câmera em degraus de 2 quadros (12 qps); toda chave em quadro par.
- Cada evento começa ~4 quadros antes da palavra (mediana −0,17 s; faixa −0,44 a +0,12 s).

## 1. A ideia em uma frase

Uma pessoa vista de cima leva dois socos: o reto só a empurra; o gancho gira a cabeça em volta de um pino no
pescoço. Quando a cabeça vira crânio, o cérebro solto lá dentro fica para trás e torce.

Arco de cor (régua: partes no papel, ação no escuro):

| trecho | fundo |
| --- | --- |
| a pergunta e o soco reto | papel #DEDBCB |
| "Já o gancho" (q182–q212) | escurece para carvão #232325, com vinheta |
| gancho, alavanca, interior e fim | carvão (~75% do vídeo) |

## 2. Elenco

Pivô P em (540, 900); na cabeça a 0°, nariz e queixo ficam 240 px acima de P. Escala: ~20 px por cm.

| camada | o que é | material | tamanho (px planejados) |
| --- | --- | --- | --- |
| `FOTO_GANCHO` + `PRETO_FOTO` | foto de 1897 de um gancho no queixo, impressa como cartão; um preto escurece a foto no "apaga" | foto de arquivo em domínio público | 900×740 |
| `OMBROS`, `CABECA`, `PINO` | a pessoa de cima (conta 1); o pino é um colchete de latão: a articulação do boneco de papel = o eixo | pessoa **genérica gerada** (não é ninguém real), com borda de papel; colchete gerado | 900×380, 640×640, 44×44 |
| `LUVA_*` | a mesma luva nas três entradas | gerada, vermelha abafada, sem marca | 300×820 |
| `FITA_*` | fita métrica do pino até o queixo, em 4 estados | gerada; os estados saem por máscara | 640×640 |
| `CHAVE` | chave estrela: a boca abraça o pino e o cabo vai até o queixo | foto CC0 | 640×640 |
| `CRANIO`, `CEREBRO`, `CEREBRO_TORCIDO_*` | o interior visto de cima (conta 1) | gravura anatômica de 1826, CC BY 4.0, separada em duas camadas | 640×640 |
| `ARTIGO` | cartão da fonte: a citação tipografada, limpa | texto próprio | 860×600 |
| título | "É O GIRO" | texto nativo, Inter 800, corpo 96 (maiúscula ~68 px), #F2EEE6 | ~540 de largura |
| `GRADE_*`, `VINHETA`, fundos | grade em losango só onde dá escala; vinheta do escuro | procedurais (`pecas.py base`) | — |

**Um matiz saturado só:** o vermelho da luva (~#A8434B). Ele volta nas fibras do cérebro, na mesma cor. O resto é
neutro: osso creme, latão fosco, marfim, aço. Créditos na descrição do post, não na tela.

## 3. Mapa de batidas

### A — a pergunta (q0–q70) · papel

| âncora → q | o que acontece | som (golpe) |
| --- | --- | --- |
| início → q0 | o cartão da foto pousa (escala 103 → 100% em 4 quadros) | papel → q2 |
| "queixo" 1,17 → q22 | beat de câmera: empurra até o contato luva-queixo, z 1,0 → 1,3 (q22–q34, ease-out), e para | — |
| "apaga" 1,50 → q32 | **a foto apaga:** o preto vai de 0 a 85% em 7 degraus; a margem fica | — |
| pausa → q70 | corte seco para a vista de cima | — |

### B — o reto (q70–q182) · papel + grade

| âncora → q | o que acontece | som |
| --- | --- | --- |
| "Um" 3,24 → q74 | a luva entra pelo topo e arma acima do nariz | — |
| "rosto" 4,82 → q106 | desce **reto pela linha que passa por P** e encosta no nariz em q112 | ar → q108 · golpe → q112 |
| "empurra" 5,74 → q134 | a cabeça vai 100 px para trás, os ombros 60 px. **Nada gira** | ar grave → q136 |
| "trás" → q148 | a luva sai pelo topo; a pessoa volta; **respiro** q160–q186 | — |

### C — o gancho (q182–q346) · escurece

| âncora → q | o que acontece | som |
| --- | --- | --- |
| "Já" 7,77 → q182 | **o fundo escurece** (q182–q212); a mesma luva entra pela direita, de cima, e arma | — |
| "queixo" 9,52 → q218 | arco de 4 degraus até o contato **no lado do queixo** em q224; o tempo congela; sem tremor | varrida → q220 · golpe → q224 |
| "passa" → q242 | beat de câmera: até P, z 1,0 → 1,12 (q242–q262) | — |
| "eixo" 11,12 → q262 | o pino desce de cima (escala 1,6 → 1,0 em 4 quadros) | — |
| "cabeça" → q286 | a câmera volta; a luva aperta 8 px e a cabeça **não sai do lugar** | — |
| "gira" 13,46 → q318 | **a cabeça gira −45° em volta do pino**; os ombros ficam; a luva sai pelo arco | giro → q320 |

### D — a alavanca (q336–q488) · escuro

| âncora → q | o que acontece | som |
| --- | --- | --- |
| pausa → q336 | beat de câmera **antes** da ação (z 1,15) | — |
| "queixo" 14,62 → q346 | a fita desenrola do pino até o queixo em 4 estados | — |
| "Vira" 16,64 → q396 | a fita volta; a **chave** desce no mesmo lugar, a boca no pino | papel → q400 |
| q416 | cabeça e chave giram juntas de volta a 0° (a chave gira o "parafuso" do pescoço) | — |
| "Quanto" → q432 | a chave sobe e some (legível 1,25 s) | — |
| q438–q454 | toque **perto** do pino: a cabeça gira só −15° e volta | — |
| "giro" 19,52 → q464 | toque **no queixo**: a cabeça gira −45° | ar largo → q466 |

### E — lá dentro (q488–q640)

| âncora → q | o que acontece | som |
| --- | --- | --- |
| "cérebro" 20,64 → q488 | **mergulho** de 20 quadros até z 2,0; a foto da cabeça dissolve e mostra o crânio aberto com o cérebro | mergulho → q500 |
| "solto" → q508 | o cérebro balança dentro do crânio (4 degraus) e assenta; câmera parada | — |
| "gira" 23,62 → q562 | o **crânio** gira −40°; o cérebro só −3° | giro → q564 (rima com q320) |
| "ele" → q582 | o cérebro **fica para trás**, devagar | — |
| "estica" 25,66 → q608 | torção em 2 estados; pronto em q610, segura até q640 | vento que sobe → q610 |

### F — a conclusão (q640–q718)

| âncora → q | o que acontece | som |
| --- | --- | --- |
| "Não" 26,74 → q640 | o cartão da fonte sobe pela base e fica legível até q674; por baixo, a pessoa volta | papel → q648 |
| "é" → q674 | o cartão sai pela base | — |
| "giro" 28,30 → q678 | a cabeça gira −45°, sem luva | golpe grave → q682 |
| q682 | "É O GIRO" entra em fade de 6 quadros, acima da cabeça; segura até q718 | — |

## 4. Orçamento de tela (conferido pelo `gera_plano.py`)

| regra | resultado |
| --- | --- |
| ≤ 2 elementos por quadro, fora a legenda | nenhum quadro passa de 2 |
| respiro a cada ~6 s | q0–q76, q160–q186, q332–q346, q476–q488, q500–q642 (o interior inteiro) |
| texto | 2 tamanhos no vídeo: título e legenda; sem rótulos, sem crédito na tela |
| leitura ≥ 1,2 s depois de pronto | luva do gancho 3,9 s; fita 1,8 s; chave, cérebro torcido, cartão e título 1,25 s |
| câmera | parada na ação; 6 beats com início e fim |
| zona | tudo o que importa entre y 560 e 1360; legenda em y 1372 (no ato A, y 440, porque a foto cobre a faixa de baixo) |

## 5. Legenda (entra por último)

18 blocos, frase por frase, Inter 600 corpo 50, corte seco. Tinta #29292B no papel; creme #F2EEE6 com sombra suave
no escuro. Cada bloco começa no quadro par em ou logo antes da palavra e sai no começo do próximo. **Calada no
título:** "é o giro" não tem legenda, quem diz é o título.

## 6. Som

14 efeitos em 29,9 s (~0,5 por segundo), um por ação, cada um no quadro do golpe da tabela acima e 15,8–19 dB abaixo
do momentâneo mediano da voz (medido com `som.py`). Pico de 2 por segundo, só nos pares "ar + golpe" dos socos. Trilha
num nível fixo ~21 dB abaixo da voz, com troca de parte na entrada do cérebro; ela sai na pausa antes de "é o giro" e
o fecho fica seco. Sem som no pino de propósito (nenhum clique servia).

Os efeitos do exemplo vieram de um banco de efeitos com licença que **não permite redistribuir**: eles não vêm no
plugin. Monte o seu banco com `som.py banco` a partir de sons que você tem direito de usar.

## 7. Cuidados do estilo

| cuidado | regra |
| --- | --- |
| peça que gira | não pode ter borda reta de recorte: ela vira diagonal no giro. Feche em arco (no exemplo, a nuca espelha a frente) |
| zoom e legenda | em cada beat de câmera, confira onde a parte de baixo do assunto cai em relação à faixa da legenda |
| ritmo da câmera | se o desenho anda a 12 qps, a câmera também anda em degraus de 2 quadros |
| cartão de fonte | só a citação, limpa; não sublinhe nem marque o que a voz não diz |
| fecho | silêncio digital sob o título só se for escolha de escuta; senão a trilha segue com fade até o fim |
| picos da voz | compressor leve na voz (3:1, ataque 5 ms) antes do limitador do master, para o limitador não cortar a fala |
| tamanho do assunto | objeto principal com 630–680 px de largura; menor que isso perde força no celular |

## 8. Fontes das peças (para refazer com `pecas.py exemplo`)

| arquivo esperado | o que é |
| --- | --- |
| `reais/foto_1897.jpg` | "A hook punch to the point of the jaw", 1897, Library of Congress (domínio público), via Wikimedia Commons |
| `reais/chave_estrela.png` | "Llave estrella", Wikimedia Commons (CC0) |
| prancha do Lizars → `separar_lizars.py` → `lizars/` | Wellcome Collection V0008410, CC BY 4.0 |
| `gerados/pessoa_cima_recorte.png`, `luva_recorte.png`, `colchete_recorte.png`, `fita.png` | gerados (imagem + remoção de fundo) |

Fonte documental citada no cartão: Ommaya, A. K.; Gennarelli, T. A. "Cerebral concussion and traumatic
unconsciousness". *Brain* 97 (1974): 633–654. doi:10.1093/brain/97.1.633.
