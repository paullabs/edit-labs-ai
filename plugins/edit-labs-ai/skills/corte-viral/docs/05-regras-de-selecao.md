# 5. Regras de seleção e scoring

## 5.1 Dois níveis de aprovação

### Gate editorial

O clipe precisa:

- ser fiel;
- ser compreensível;
- ter desenvolvimento;
- ter payoff;
- terminar corretamente;
- não depender do episódio original;
- não duplicar clipe melhor.

### Gate de feed

O clipe precisa:

- orientar rápido;
- comunicar promessa ou stakes no tempo do perfil;
- entregar primeiro valor;
- progredir;
- manter dívida de contexto aceitável;
- pagar a promessa.

Falhar em qualquer gate crítico impede `APPROVED`, mesmo com média alta.

## 5.2 Perfis

### `fast_answer`

Use para pergunta direta, tutorial, explicação, definição e opinião com razão clara.

Estrutura preferida:

```text
resposta/resultado → motivo → demonstração → limite/implicação
```

### `contrarian`

```text
crença comum → quebra → mecanismo → prova → nova regra
```

### `money`

```text
número/escala → comparação → mecanismo → consequência
```

Número sem contexto de escala não basta.

### `story`

```text
consequência/stakes → contexto mínimo → obstáculo → virada → resolução
```

### `humor`

```text
setup mínimo → expectativa → ruptura → reação
```

Não destruir timing com cortes excessivos.

### `transformation`

```text
antes/depois → ponto de mudança → processo → significado
```

### `long_clip`

Precisa de capítulos internos, múltiplos beats e valor acumulativo. Não é um Short lento.

## 5.3 Scores

Todos em 0–10:

- `orientation`;
- `hook`;
- `proposition_clarity`;
- `first_value_speed`;
- `context_efficiency`;
- `stakes`;
- `curiosity_integrity`;
- `progression`;
- `payoff`;
- `closure`;
- `self_contained`;
- `shareability`;
- `visual_opportunity`;
- `novelty`;
- `editability`;
- `truthfulness`.

## 5.4 Métricas de tempo

- `orientation_latency_seconds`;
- `proposition_latency_seconds`;
- `first_value_latency_seconds`;
- `first_turn_latency_seconds`;
- `payoff_latency_seconds`;
- `maximum_seconds_without_new_value`.

O modelo marca os eventos; o script calcula os intervalos.

## 5.5 Hard fails

Status `APPROVED` é proibido quando:

1. sujeito ou assunto central não pode ser entendido;
2. promessa não é paga;
3. frase inicial depende claramente de conteúdo anterior;
4. montagem altera significado;
5. highlight reaparece de forma crítica;
6. mais de 50% do clipe é duplicado de versão melhor;
7. final corta resolução;
8. transcript-chave não foi confirmado;
9. dívida de contexto é classificada como crítica;
10. não existe primeiro valor no limite máximo do perfil sem justificativa;
11. o clipe é apenas uma opinião sem razão, consequência ou tensão;
12. o clipe usa suspense genérico que poderia ser substituído por promessa específica;
13. o texto de tela afirma algo que o áudio não sustenta;
14. o clipe depende de asset visual inexistente para fazer sentido.

## 5.6 Fórmula de ranking

Ranking serve apenas depois dos gates.

Pesos default:

```text
hook                 0.10
proposition_clarity  0.10
first_value_speed    0.09
context_efficiency   0.10
curiosity_integrity  0.08
progression          0.10
payoff                0.13
self_contained       0.10
shareability         0.08
visual_opportunity   0.04
novelty              0.04
editability          0.04
```

`truthfulness` não recebe peso: é gate obrigatório.

A nota final recebe penalidade pelo menor score crítico:

```text
critical_floor = min(proposition_clarity, payoff, self_contained, truthfulness)
adjusted = weighted_score * (0.70 + 0.30 * critical_floor / 10)
```

## 5.7 Padrões de frase: candidatos, não garantias

### Bons sinais

- número concreto;
- comparação inesperada;
- “porque” com causalidade real;
- mudança de decisão;
- confissão específica;
- conflito;
- antes/depois;
- pergunta respondida;
- detalhe visual verificável;
- regra prática.

### Sinais de risco

- “isso”, “ele”, “aquilo” sem referente;
- “como eu falei”;
- lista longa de nomes;
- opinião circular;
- frase forte sem explicação;
- resposta que depende de gráfico não mostrado;
- conclusão fora do intervalo;
- exagero que o restante suaviza;
- contexto que começa antes do candidato detectado.

## 5.8 Quantidade

O sistema nunca cria um corte apenas para preencher `max_clips`. O relatório deve poder retornar zero aprovados.
