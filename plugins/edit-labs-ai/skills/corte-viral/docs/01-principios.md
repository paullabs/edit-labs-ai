# 1. Princípios do sistema

## 1.1 As duas perguntas

Todo candidato precisa responder a duas perguntas diferentes:

- **este trecho consegue existir fora do episódio?** — contexto, independência,
  payoff e fidelidade;
- **este trecho sobrevive ao comportamento de rolagem?** — entrega valor rápido,
  progride, é editado de modo coerente e sai como arquivo publicável.

A primeira é o núcleo editorial. A segunda é o que o feed cobra por cima dele.

## 1.2 Núcleo editorial

### Entender antes de caçar

O Context Mapper roda antes do Clip Hunter. Isso impede um erro comum: escolher uma frase impactante cujo significado depende de algo dito vinte minutos antes.

### Distinguir frase viral de clipe viral

“Frase destacável” não é “vídeo completo”. Cada clipe exige hook, contexto, desenvolvimento e payoff.

### Reconstruir sem replay

Uma revelação pode abrir o clipe como highlight; a montagem volta ao contexto e continua depois do ponto já exibido. Repetir exatamente a mesma fala é o padrão amador que essa regra elimina.

### Julgar como conteúdo isolado

Quem conhece o episódio inteiro preenche mentalmente lacunas que o público não consegue preencher. O clipe é julgado como se o espectador não soubesse nada do episódio — é o que o usuário faz ao assistir o preview.

### Não maximizar quantidade

Um vídeo pode ter três, dez, vinte ou nenhum clipe excelente. O sistema não gera cortes artificiais para cumprir meta.

## 1.3 O que o sistema mede para o feed

### Promessa

Curiosidade vaga não é suficiente. O espectador precisa perceber rapidamente pelo menos uma destas coisas:

- o que vai descobrir;
- qual transformação está em jogo;
- qual número ou consequência importa;
- qual crença será contrariada;
- qual pergunta receberá resposta;
- por que aquela pessoa tem autoridade para falar.

`proposition_latency_seconds` mede o tempo até o espectador conseguir formular “este vídeo é sobre X e vale assistir porque Y”.

### Primeiro valor

Um hook pode prometer bem e ainda manter o público esperando demais. `first_value_latency_seconds` mede o tempo até a primeira informação que já recompensa parcialmente a permanência.

Exemplo ruim:

> “Você não vai acreditar no que aconteceu...”
> 18 segundos de preparação genérica.

Exemplo melhor:

> “O contrato era de dois anos — mas uma cláusula de três linhas mudou quem ficou com o lucro.”

A segunda versão abre uma lacuna específica e entrega valor parcial imediatamente.

### Dívida de contexto

“Dívida de contexto” é o número de entidades, relações e acontecimentos que o espectador precisa entender antes de receber valor.

Um clipe pode ser autocontido no total e ainda ser lento no início. Se os primeiros oito segundos servem apenas para apresentar quatro pessoas e duas empresas, ele perde para conteúdos mais fáceis de processar.

### Ritmo por tipo de clipe

Um tutorial, uma revelação e uma história não obedecem ao mesmo relógio.

- resposta rápida: pergunta ou resultado quase imediatamente;
- contradição: crença comum e quebra até o segundo 2–3;
- dinheiro: número ou escala cedo;
- história: consequência ou risco cedo, contexto depois;
- humor: setup curto, ruptura clara, reação preservada;
- long clip: valor acumulativo e capítulos internos.

### Microprogressão

Um clipe de 60 segundos não pode depender de um único payoff no final. Ele precisa produzir beats: prova, contraste, número, mudança, mini-resposta, reação, nova pergunta ou implicação.

O harness mede:

- `semantic_beat_count`;
- `average_seconds_per_beat`;
- `maximum_seconds_without_new_value`.

### Curiosidade legítima, não clickbait

O sistema verifica:

- a promessa é específica?
- o conteúdo realmente possui a resposta?
- a resposta é proporcional ao suspense?
- o highlight foi retirado de modo que distorce o significado?
- existe uma entrega parcial antes do payoff final?

## 1.4 O que sustenta a execução

### Contrato de entrada

Vídeo, transcript e modo (análise, verificação, render ou completo) são declarados no `init`.

### Estado persistente

Cada passagem produz um JSON próprio. Sem arquivos intermediários, o modelo poderia afirmar que realizou várias passagens dentro da mesma resposta, sem separação verificável.

### Matemática em código

Sobreposição, contenção, repetição, duração e validação não dependem de estimativa do LLM.

### Saída de edição

A run termina em plano de edição, SRT/ASS de decupagem, vertical limpo e organização por contexto — não num JSON editorial.

## 1.5 Falhas que o sistema impede

1. **Hook com contexto atrasado:** frase forte, mas sujeito desconhecido.
2. **Pergunta sem resposta rápida:** introdução longa antes de qualquer valor.
3. **Número sem mecanismo:** “ganhou milhões”, sem explicar como ou por quê.
4. **História sem stakes:** cronologia correta, porém sem razão para continuar.
5. **Falso suspense:** ocultar informação óbvia que poderia ser dita no início.
6. **Replay do highlight:** mesma fala aparece duas vezes.
7. **Clipes irmãos:** três cortes contam a mesma história com pequenas diferenças.
8. **Legenda decorativa:** texto rápido demais, mal segmentado ou concorrendo com o rosto.
9. **Overediting:** zoom e transição sem relação com mudança de significado.
10. **Montagem enganosa:** combinação de falas reais que altera sentido ou causalidade.

## 1.6 Síntese

O núcleo editorial não troca contexto por velocidade: **comprime o contexto até o mínimo suficiente, entrega valor antes e mantém progressão sem falsificar a fala**.
