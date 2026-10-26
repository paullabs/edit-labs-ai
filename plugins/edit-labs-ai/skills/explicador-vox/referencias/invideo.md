# Montar o explicador como timeline editável no invideo

O mesmo `plano.json` que gera a prévia local vira uma timeline nativa no invideo, organizada por faixas e com
chaves editáveis. Depois da montagem, **o invideo é a fonte da verdade**: o usuário edita lá. Se refizer algo
aqui, suba como versão nova, nunca por cima do que ele editou.

## Organização

| timeline | tamanho | o que tem |
| --- | --- | --- |
| **T1 TELA** | 1080×1920, 24 qps | de baixo para cima: fundo papel, fundo carvão, vinheta, peças de tela (cartão da fonte), **MUNDO** (T2 aninhada), título, legenda, ajuste de textura; áudio: voz, trilha, efeitos |
| **T2 MUNDO** | 2160×3840 (o mundo em 2×) | uma faixa por peça, na ordem do plano (camadas com o mesmo PNG dividem a faixa) |

- **A câmera é o clipe MUNDO dentro de T1:** zoom = 0,5·z; posição = −(cx − 540)·z, −(cy − 960)·z.
- Para mexer num objeto, abra o MUNDO. Para mexer no enquadramento, mexa nas chaves do clipe MUNDO em T1.
- Nomeie as faixas com o nome da camada do plano, para o usuário achar.

## Regras medidas (sem elas a montagem sai errada)

1. **Caixa do clipe.** `place_media` de imagem cria a caixa no **tamanho nativo** da imagem; `insert_media` cria a
   caixa do tamanho da tela. Nos dois, o que aparece = encaixe(imagem na caixa) × zoom.
2. **Zoom estático × faixa de zoom.** `set_zoom` recebe o zoom **relativo ao encaixe** na tela e guarda
   valor × encaixe. As faixas `zoom_x`/`zoom_y` (`add_keyframes`) guardam o multiplicador **nativo**. Para pixel
   nativo com `set_zoom`, mande 1/encaixe. Ex.: imagem de 1280² numa tela de 2160×3840: encaixe 1,6875.
   Errar isso deixa peças 1,7–2,3× maiores.
3. **`set_zoom` e `set_position` apagam a faixa de chave da mesma propriedade.** Mande os estáticos numa chamada
   e as faixas de chave depois, em outra.
4. **Posição** = centro do clipe, em px a partir do centro da timeline. **Rotação** positiva = horário.
5. **Degrau de 12 qps.** Posição e zoom: pares de chave (quadro − 1 com o valor velho, quadro com o novo). Rotação e
   opacidade: `set_keyframes` com `ease: "hold"`, só onde o valor muda. Toda chave em quadro par. A câmera também.
6. **Luz linear.** O invideo mistura em luz linear: um preto por cima escurece muito menos que no motor (sRGB). Para
   escurecer igual, use opacidade = 1 − (1 − op)^2,2 (o plano marca essas camadas com `"luz_linear": true`).
7. **Clipe curto.** Um clipe de imagem de 2 quadros (0,083 s) sai com 1, porque a fonte arredonda a 30 qps. Depois
   de criar, confira no `get_timeline` e corrija com `trim_clip` (cauda); no fim da faixa, `close_gap`.
8. **Ids criados.** O retorno `created` traz também `gap` e `keyframe_lane`. Case os ids só pelos `clip` e
   `audio_clip`, na ordem das operações (é o que `invideo_ops.py reg` faz).
9. **Faixas.** Confira com `get_timeline` quais faixas já existem antes de criar; se a timeline já vier com faixas,
   o número inicial muda.

## Passo a passo (com `ferramentas/invideo_ops.py`)

1. `invideo_ops.py bin --plano plano.json --pecas pecas/ --pasta invideo/` → lista do que subir.
2. Suba as peças, a voz, a trilha, o banco de efeitos e as fontes (`start_upload` + `add_media`) e escreva os ids
   no `invideo/bin.json`. Fontes: o Inter do plugin (`${CLAUDE_PLUGIN_ROOT}/skills/motion-vox/fontes/`, OFL); se o
   invideo não aceitar a fonte variável, use os pesos estáticos 600 e 800 do Inter (também OFL).
3. Crie o projeto e as duas timelines (T2 2160×3840 e T1 1080×1920, ambas a 24 qps).
4. `invideo_ops.py criar ... --som som/som.json --sem-legenda` → `ops/criar_T2.json`, `criar_T1.json`,
   `criar_audio.json`. Mande cada lote pelo `edit_timeline` e registre os ids:
   `invideo_ops.py reg --pasta invideo/ criar_T2.json '<created>'` (idem T1 e áudio).
5. `invideo_ops.py chaves ...` → `ops/chaves.json`: mande `estaticas_T2` e `estaticas_T1`; depois `lanes_*`; depois
   os `add_keyframes` com `pontos_*` (na mesma ordem das lanes).
6. Corrija os clipes curtos (`ops/curtos.json`).
7. **Legenda por último:** quando motion, B-roll e som estiverem aprovados, rode `criar` de novo sem
   `--sem-legenda` e mande só as operações de legenda (ou monte a legenda nativa direto no invideo).
8. `capture()` em ~12 instantes e compare com os quadros da prévia local (`previa.py --quadros`). Só entregue se bater,
   ou com cada diferença anotada.

## Textura (ajuste no topo de T1)

Um ajuste (`add_adjustment`) com shader próprio serve de acabamento global. O do exemplo tinha 4 controles
editáveis no painel: **grão 2,2**, **RGB 1,2 px** (aberração cromática), **tremor 0,9 px** e **12 degraus/s**
(tudo muda só a cada desenho, pelo tempo da timeline). Zerar o tremor tira o boil; grão 0 tira o grão. Escreva o
shader conferindo a ajuda do invideo (`get_help`) e teste num trecho antes de aplicar ao vídeo todo.

## Som

| faixa | nível |
| --- | --- |
| voz | 0 dB no clipe |
| trilha | já gravada ~21 dB abaixo da voz (`som.py mixar` grava `trilha_no_nivel.wav`); uma trilha alternativa pode ficar numa faixa muda |
| efeitos | um trecho do banco por clipe, começando no `quadro_inicio`; o ganho de cada clipe vem do `som.json` |

O export vai a −14 LUFS (`target_lufs`); o limitador do invideo segura o pico em −1 dB. Se a voz precisar de muito
ganho, o limitador corta os picos: ponha um compressor leve na voz antes.

## Edições comuns (para o usuário)

- **Texto da legenda:** clique no texto e edite; as quebras de linha estão no próprio texto.
- **Um objeto entra cedo ou tarde:** dentro do MUNDO, mova o clipe e as chaves juntos. Mantenha as chaves em
  quadros pares.
- **Trocar a trilha:** tire o mudo da alternativa e ponha mudo na atual.
- **Exportar:** vídeo, 1080, 24 qps, −14 LUFS.
