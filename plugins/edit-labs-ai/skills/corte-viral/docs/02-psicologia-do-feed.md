# 2. Psicologia do feed e clipes de resposta rápida

## 2.1 “Dopamina rápida” não deve ser a variável do sistema

Dopamina participa de motivação, aprendizado, novidade, incerteza e busca de informação, mas não existe uma regra científica do tipo “um zoom a cada dois segundos libera dopamina e aumenta retenção”. O harness não mede neurotransmissores e não usa esse vocabulário como score.

Ele trabalha com fenômenos comportamentais mais observáveis:

- captura atencional;
- curiosidade por lacuna de informação;
- expectativa de recompensa informacional;
- fluência de processamento;
- relevância pessoal;
- surpresa e contraste;
- progressão;
- fechamento;
- valor social de compartilhar.

A literatura sobre curiosidade sugere que pessoas atribuem valor à informação capaz de reduzir incerteza, e que curiosidade pode recrutar circuitos associados a recompensa e memória. Isso apoia hooks com lacunas específicas, não suspense vazio. Ver fontes acadêmicas S10–S15.

## 2.2 O comportamento real que o clipe precisa vencer

No feed, o espectador não escolheu ativamente aquele vídeo. A alternativa é um gesto de menos de um segundo: deslizar.

Por isso o clipe enfrenta quatro perguntas silenciosas:

1. **O que está acontecendo?**
2. **Por que isso importa para mim?**
3. **O que vou ganhar continuando?**
4. **Está progredindo ou enrolando?**

O sistema traduz essas perguntas em métricas.

## 2.3 Mecanismos usados pelo harness

### 1. Orientação imediata

O primeiro frame e a primeira frase devem reduzir ambiguidade suficiente para o espectador localizar o assunto.

Isso não exige explicar tudo. Exige apresentar uma âncora:

- pessoa conhecida;
- objeto;
- número;
- conflito;
- pergunta;
- resultado;
- antes/depois;
- declaração contraditória.

Métrica: `orientation_score`.

### 2. Lacuna específica de informação

Uma boa lacuna contém:

- algo que o espectador já entende;
- algo específico que ainda não sabe;
- expectativa de que a resposta está próxima;
- consequência relevante.

Fraca:

> “Isso mudou tudo.”

Forte:

> “O preço não mudou. O que mudou foi o prazo de pagamento — e isso decidiu a venda.”

Métricas:

- `curiosity_specificity`;
- `answerability`;
- `promise_payoff_integrity`.

### 3. Primeiro valor

O espectador deve receber uma recompensa parcial antes da resolução final. Pode ser:

- número;
- mecanismo;
- comparação;
- prova;
- mudança de direção;
- detalhe inesperado;
- aplicação prática.

Métrica: `first_value_latency_seconds`.

### 4. Progressão informacional

Cada beat deve adicionar algo. Repetição temática pode reforçar; repetição literal ou parafraseada sem ganho produz sensação de lentidão.

Métricas:

- beats por minuto;
- maior intervalo sem novidade;
- proporção de frases removíveis;
- repetição semântica.

### 5. Fluência de processamento

Rapidez não é apenas falar depressa. O público processa mais rápido quando:

- pronomes têm referente claro;
- frases são curtas;
- uma ideia principal aparece por beat;
- legenda respeita unidades sintáticas;
- texto e imagem apontam para o mesmo significado;
- nomes desnecessários são removidos ou explicados.

Métrica: `context_debt` e `processing_fluency`.

### 6. Stakes e relevância

Conteúdo ganha força quando deixa claro o que pode ser ganho, perdido, evitado ou compreendido.

Tipos:

- dinheiro;
- tempo;
- reputação;
- transformação;
- risco;
- identidade;
- vantagem prática;
- conflito social.

Métrica: `stakes_clarity`.

### 7. Surpresa coerente

Surpresa funciona quando modifica um modelo mental:

> “Uma locadora de carros não ganha principalmente alugando; o aluguel ajuda a financiar a depreciação até a revenda.”

A surpresa precisa ser explicada. Sem mecanismo, vira apenas afirmação chamativa.

Métricas:

- `novelty`;
- `mechanism_present`;
- `evidence_present`.

### 8. Fechamento

O final precisa parecer final. Pode entregar:

- resposta;
- consequência;
- regra;
- punchline;
- decisão;
- transformação;
- pergunta nova intencional.

O clipe não deve acabar apenas porque o tempo ideal foi atingido.

Métrica: `closure_score`.

### 9. Valor social

As pessoas compartilham conteúdos que ajudam a:

- ensinar algo;
- confirmar identidade;
- surpreender alguém;
- iniciar debate;
- alertar;
- provocar humor;
- demonstrar repertório.

Métrica: `share_trigger` com categoria explícita.

## 2.4 Relógio comportamental

Os números abaixo são **defaults operacionais**, não leis universais.

| Evento | Resposta rápida | Contradição | Dinheiro | História | Humor |
|---|---:|---:|---:|---:|---:|
| Orientação | 0–1,5s | 0–1,5s | 0–1,5s | 0–2,0s | 0–2,0s |
| Proposta | até 2,5s | até 2,5s | até 3,0s | stakes até 5,0s | setup até 4,0s |
| Primeiro valor | até 6,0s | razão até 8,0s | mecanismo até 10s | primeira virada até 12s | payoff variável |
| Novo beat | 3–7s | 3–7s | 3–8s | 5–10s | depende do timing |
| Duração típica | 15–45s | 20–60s | 20–60s | 35–90s | 10–40s |

O perfil pode ultrapassar limites quando fica documentado por que a espera aumenta, em vez de reduzir, a expectativa.

## 2.5 Resposta rápida não significa responder tudo no primeiro segundo

Há três estruturas válidas.

### Answer first

```text
Resposta → mecanismo → prova → implicação
```

Boa para tutoriais, explicações e perguntas diretas.

### Answer preview

```text
Parte da resposta → pergunta restante → mecanismo → resposta completa
```

Boa para manter curiosidade sem frustrar.

### Stakes first

```text
Consequência → contexto mínimo → escalada → resolução
```

Boa para histórias.

O sistema escolhe a estrutura de acordo com o tipo de valor, não aplica suspense automaticamente.

## 2.6 Padrões linguísticos que indicam potencial

### Contradição

- “Todo mundo acha X, mas...”
- “O problema não é X.”
- “O dinheiro não está em X; está em Y.”
- “Parece que..., só que...”

### Número com escala

- “Eles pagaram...”
- “Isso custa...”
- “Em doze meses...”
- “Um cliente vale...”

### Causalidade

- “Isso só funciona porque...”
- “O motivo real é...”
- “A conta fecha quando...”
- “Foi aí que...”

### Transformação

- “Antes eu..., depois...”
- “Em X meses...”
- “Saí de... para...”

### Risco e conflito

- “Eu podia perder...”
- “A negociação acabou quando...”
- “Eles recusaram...”

### Aplicação

- “O passo que muda tudo é...”
- “Faça isso antes de...”
- “A forma mais simples é...”

Esses padrões são candidatos, não aprovação automática.

## 2.7 O que não funciona apesar de parecer estimulante

- gritar sem entregar;
- frases abstratas sem objeto;
- mistério sem pergunta definida;
- cortes a cada meio segundo sem mudança semântica;
- palavra colorida demais na legenda;
- esconder a resposta até o fim quando ela poderia organizar o clipe;
- usar reação de outra parte como se fosse reação à fala atual;
- começar com “fica até o final”;
- apagar pausas que dão peso emocional ou timing cômico;
- comprimir tanto que o espectador não consegue formar causalidade.

## 2.8 Hipótese testável, não promessa de viralização

O harness deve produzir previsões como:

> “Este clipe possui proposta em 1,8s, primeiro valor em 4,9s, payoff em 31s e nenhuma dívida crítica de contexto. É publicável e adequado a teste A/B.”

Ele não deve dizer:

> “Este vídeo vai viralizar.”

O desempenho real depende de audiência, conta, tema, distribuição, momento, competição, capa, descrição e variabilidade do algoritmo.
