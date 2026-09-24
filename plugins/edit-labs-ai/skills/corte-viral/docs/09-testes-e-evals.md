# 9. Testes e avaliação

## 9.1 Três tipos de teste

### Testes unitários

Validam funções determinísticas:

- parsing de timestamps;
- interseção;
- contenção;
- repetição;
- remapeamento temporal;
- chunks de legenda;
- schemas;
- comando FFmpeg.

### Evals editoriais

Usam um conjunto de episódios e clipes aprovados/rejeitados por humanos.

### Testes de plataforma

Publicação A/B para observar retenção real.

## 9.2 Golden set

Monte pelo menos:

- 20 clipes excelentes;
- 20 bons, mas lentos;
- 20 frases fortes sem contexto;
- 20 duplicatas;
- 20 histórias incompletas;
- 20 clips com replay;
- 20 casos longos justificáveis;
- 20 casos em que a edição mudaria o sentido.

Cada item deve ter decisão humana e justificativa.

## 9.3 Métricas do seletor

- precisão de `APPROVED`;
- recall de clipes excelentes;
- taxa de falso positivo;
- taxa de duplicata sobrevivente;
- taxa de hard fail em aprovados;
- concordância com editor humano;
- número médio de rebuilds;
- custo de tokens por hora de vídeo.

Priorizar precisão sobre recall. É melhor perder um clipe mediano do que entregar dez cortes ruins.

## 9.4 Métricas de render

- sucesso de abertura;
- resolução;
- duração;
- sincronização A/V;
- drift de legenda;
- frames pretos;
- clipping de áudio;
- texto fora da safe zone;
- artefatos no concat.

## 9.5 Testes A/B

Variáveis úteis:

- hook original vs highlight;
- resposta primeiro vs suspense;
- 30s vs 50s;
- legenda por chunk vs palavra;
- número no primeiro frame vs apenas áudio;
- crop estático vs punch-in moderado.

Não alterar várias dimensões ao mesmo tempo quando a intenção é aprender causalmente.

## 9.6 Métricas de plataforma

Quando disponíveis:

- retenção em 1s, 3s e 5s;
- average watch time;
- completion rate;
- rewatch;
- shares por mil views;
- saves por mil views;
- comentários por mil views;
- follows por mil views;
- curva de queda por frame/segundo.

Views isoladas não bastam.

## 9.7 Loop de aprendizagem

```text
PUBLICAÇÃO
↓
MÉTRICAS
↓
ASSOCIAR RESULTADO AO CLIP_ID
↓
COMPARAR PREVISÃO VS REALIDADE
↓
ATUALIZAR PESOS/PERFIS
↓
NÃO ALTERAR HARD FAILS DE VERDADE
```

O sistema pode aprender preferências editoriais, mas não deve aprender que distorção é aceitável apenas porque teve mais views.

## 9.8 Eval da Skill no Claude Code

Execute cada prompt em sessão nova, com e sem a Skill, como recomenda a documentação do Claude Code. Meça separadamente:

1. se a Skill foi invocada corretamente;
2. se o resultado respeitou o contrato.

Casos mínimos:

- vídeo + transcript;
- vídeo sem transcript;
- transcript sem vídeo;
- candidatos prontos;
- nenhum clipe bom;
- dois clipes contidos;
- highlight com 75% de replay;
- história de 110s justificável;
- transcript com timestamp inválido.
