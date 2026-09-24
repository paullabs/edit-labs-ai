# 4. Pipeline passo a passo

## Etapa 0 — Brief

Entrada opcional: `templates/user-brief.yaml`.

Campos:

- público;
- plataformas;
- temas prioritários;
- temas proibidos;
- duração preferida;
- estilo de legenda;
- quantidade máxima;
- nomes dos participantes;
- palavras que exigem grafia específica;
- CTA permitido;
- restrições de montagem.

Quantidade máxima é teto, não meta.

## Etapa 1 — Preflight

Verifica:

- Python;
- FFmpeg;
- FFprobe;
- bibliotecas Python;
- backend opcional de transcrição;
- estrutura de pastas;
- schemas legíveis.

Saída: diagnóstico no terminal e no manifest.

## Etapa 2 — Init

Cria `workspace/runs/<timestamp>-<slug>/` e copia os parâmetros para `00-manifest.json`.

O run nunca sobrescreve outro run.

## Etapa 3 — Ingestion

### Vídeo

FFprobe captura:

- duração;
- resolução;
- frame rate;
- codec;
- canais de áudio;
- sample rate;
- rotação;
- timebase.

### Áudio

Cria WAV mono de análise, normalmente 16 kHz, sem substituir o áudio de render.

### Transcript

Ordem de preferência:

1. transcript fornecido com palavra e timestamp;
2. transcript fornecido por segmento;
3. faster-whisper local;
4. outro backend configurado;
5. falha explícita.

### Visual

Não entra na ingestão: `03-visual-index.json` é gravado como placeholder adiado. O índice visual — frames periódicos, frames de mudança de cena, contact sheets e índice de timestamps — é extraído depois da seleção, só nas janelas dos candidatos aprovados (`vch visual-index --windows`).

OCR e reconhecimento facial são opcionais e não devem ser necessários para o núcleo.

## Etapa 4 — Context Map

O agente percorre todo o transcript e cria:

- temas e subtemas;
- participantes;
- entidades;
- histórias;
- perguntas e respostas;
- conflitos;
- números;
- causalidades;
- setups e payoffs;
- referências anafóricas;
- mudanças de assunto;
- recursos visuais relevantes;
- unidades de contexto com início e fim.

Não cria candidatos.

## Etapa 5 — Viral Moments

O Clip Hunter marca momentos sem ainda fechar o corte.

Cada momento contém:

- quote literal;
- start/end;
- trigger primário;
- contexto necessário;
- possível payoff;
- perfil de clipe;
- risco de distorção;
- visual disponível;
- confiança.

Os momentos vão para o usuário, que escolhe quais viram corte. Só os escolhidos seguem.

## Etapa 6 — Candidate Builder

Para cada momento:

1. escolhe a promessa;
2. escolhe a estrutura de feed;
3. localiza o contexto mínimo;
4. localiza prova ou mecanismo;
5. localiza payoff;
6. monta timeline de segmentos reais;
7. marca intervalos removidos;
8. elimina replay do highlight;
9. estima duração;
10. cria transcript reconstruído.

A timeline pode ser descontínua, mas precisa manter verdade semântica.

## Etapa 7 — Technical Audit

Scripts validam:

- timestamps dentro da duração da mídia;
- start < end;
- ordem dos segmentos;
- duração final;
- highlight versus corpo;
- clipe versus outros clipes;
- gaps e sobreposições;
- existência das falas no transcript;
- densidade de fala;
- silêncio;
- schema.

## Etapa 8 — Rebuild

Motivos comuns:

- proposta lenta;
- contexto alto;
- payoff baixo;
- replay;
- segmento redundante;
- início dependente de pronome;
- corte no meio da ideia;
- clipe longo sem beats suficientes.

Cada tentativa é salva em `iterations/<clip-id>/attempt-N.json`.

## Etapa 9 — Deduplicação

### Temporal

Mede interseção e contenção.

### Semântica

Compara:

- pergunta central;
- revelação central;
- payoff;
- história;
- take-away.

Dois clipes podem ter zero sobreposição temporal e ainda dizer a mesma coisa.

## Etapa 10 — Preview e aprovação

Cada sobrevivente é cortado do bruto, horizontal, e o usuário assiste. Perguntas que decidem:

- entendi imediatamente?
- sei quem ou o que está em jogo?
- a promessa é específica?
- recebo valor cedo?
- cada parte progride?
- o payoff paga a promessa?
- algo parece enganoso?
- o final parece final?
- eu continuaria após 1, 3 e 8 segundos?

Sinais de problema: dívida de contexto, suspense vago, repetição semântica, frase de baixa densidade, promessa inflada, resposta atrasada, excesso de nomes.

A decisão fica em `human_approval` no candidato. Só os aprovados viram vertical.

## Etapa 11 — Edit Plan

Define:

- ordem;
- trim fino;
- crop anchor;
- punch-in;
- pausas preservadas;
- cards;
- B-roll existente;
- legenda;
- ênfase;
- áudio;
- saída.

## Etapa 12 — Finalização

Aplica gates, gera `13-final-clips.json` e separa rejeitados.

## Etapa 13 — Legendas

Mapeia timestamps de origem para timeline final, segmenta por sintaxe e gera SRT/ASS.

## Etapa 14 — Render

Gera:

- vídeo clean;
- vídeo legendado, quando `make_captioned_version` estiver ligado;
- thumb de referência;
- metadados;
- notas.

## Etapa 15 — Verificação de saída

Verifica:

- arquivo abre;
- resolução correta;
- duração esperada;
- áudio presente;
- legenda presente quando exigida;
- tamanho não zero;
- nome e pasta corretos;
- manifesto atualizado.


## Passagem final — pós-render

Após criar os MP4s, o harness executa `verify-output`. A entrega fica bloqueada quando faltam arquivos, a duração diverge da timeline, resolução/pixel format estão errados, não há áudio, as legendas são inválidas ou saem da safe zone, ou existe tela preta crítica nas bordas. O estado é preservado em `16-output-verification.json`.
