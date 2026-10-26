# Retakes — como o agrupador funciona e como o Editor decide

`di retakes` **sugere**; o Editor decide em `decisoes.json`. Nada do que o script marca entra no corte sem o Editor pôr no `manter`.

## Frases

O transcript é quebrado em frases por:
- pontuação final do Whisper ou reticências;
- vão > 0,5 s entre palavras;
- palavra com inicial maiúscula colada no meio (o Whisper junta recomeços). Não quebra em nome próprio ou palavra de caixa mista; precisa de vão ≥ 0,3 s, `p` < 0,3, duração zero, ou três palavras antes sem preposição.

Cada frase ganha: `completa`, `gagueira`, `bastidor`, `cauda_bastidor`, `autocorrecao`, `alucinacao_suspeita`, `rms_db`, `pal_por_s`, `repeticao_interna` e as palavras em dúvida.

**Completa** quando: tem ponto final; ou tem vão ≥ 0,5 s depois, ≥ 4 palavras e não termina em palavra de função; ou emenda direto numa frase de **outro** grupo sem recomeçar (`continuada`, armadilha 5).

## Grupos de tomada

Duas frases até 15 posições e 90 s de distância entram no mesmo grupo quando:
- a semelhança (maior entre SequenceMatcher e Jaccard) é ≥ 0,72;
- as 4 primeiras palavras são iguais (recomeço); ou
- uma é prefixo da outra (falso começo).

Dentro do grupo, cada tomada é `completa`, `abandonada`, `falso_comeco` ou `metade`.
**Metade**: duas frases vizinhas que, somadas, batem com outra tomada do grupo melhor que cada uma sozinha (armadilha 6). No digest: `½+F024`.

**Sugestão (✓):** a última completa sem filler e sem gagueira; se não houver, a última completa; se não houver, a última. `empate_com` lista tomadas quase idênticas. `sem_tomada_limpa` vai para a mensagem de F3.

## Outros achados

- **Retake parcial:** as últimas palavras de A aparecem no começo de B (`parcial←` no digest). Sugestão: A até antes da repetição + B inteira, com `de_palavra`/`ate_palavra`.
- **Sobreposição:** 2–5 palavras vazadas entre vizinhas.
- **Bastidor:** palavra-meta ("roteiro", "gravando", "de novo", "peraí", "mano", "depois a gente edita", "prolixo"…) e cauda ("boa", "ok", "beleza", "essa ficou").
- **Fillers:** `fillers.json`; só são cortados com silêncio medido dos dois lados e as duas juntas passando na régua.

## Como o Editor decide

1. Leia o grupo inteiro no digest, com tempo, `p`, nível e velocidade.
2. Prefira a sugestão. Divergiu? O motivo diz por quê ("t2 é curta; t3 tem a frase inteira").
3. Tomada com nível > 3 dB abaixo ou velocidade > 20 % diferente da mediana do grupo: considere a outra, com motivo. O script não ouve entonação.
4. Metades: as duas juntas ou a inteira. Nunca uma metade sozinha.
5. Costura dentro de frase só com motivo e com as duas juntas passando na régua.
6. Solo: `padrao: remover` e só o que fica em `manter`. Podcast: `padrao: manter` e só o que sai em `remover`.
