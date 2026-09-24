# Fase 1 — MOMENTOS

> **A entrega é uma lista, não um vídeo.** Nenhum frame é decodificado nesta
> fase. Termina com os momentos apresentados ao usuário e a run parada.

**Carregue:** `docs/05-regras-de-selecao.md`. Só isso, além do `REGRAS.md`.
Não abra `06-regras-de-edicao` (in/out), `12-erros-conhecidos` (render) nem
`config/` — são das fases 2 e 3.

**Subagentes desta fase:** `context-mapper` e `clip-hunter`. **Só esses dois.**
Os outros três (`clip-builder`, `clip-deduplicator`, `edit-director`) são de
fases que você ainda não abriu.

---

## 1. Preparação

```bash
vch preflight
vch init <VIDEO> [TRANSCRIPT] \
  --mode full --platform cross-platform \
  --workspace <PASTA-DO-PROJETO>/runs
```

Leia o `RUN_DIR=` emitido. Depois:

```bash
vch prepare --run <run-dir>
```

`prepare` gera metadados, áudio de análise e transcript normalizado.

**O índice visual fica de fora, e isso é a regra, não uma otimização.**
`03-visual-index.json` é gravado como placeholder adiado. Gerá-lo decodifica o
vídeo inteiro duas vezes (frames periódicos + detecção de cena); num vídeo longo
isso trava a run antes de você sequer saber que trecho interessa. Índice visual
só na fase 2, e escopado às janelas dos candidatos.

## 2. Decupagem — o timing por palavra é pré-requisito

Transcrição com granularidade de 1 segundo **não serve**: erra nome, número e
palavra, e não diz onde a palavra começa. Três fontes, nesta ordem:

1. **Legenda automática do YouTube**, se o vídeo estiver lá (mesmo já publicado).
   O VTT traz `<00:12:04.520><c>palavra</c>` — timing por palavra de graça.
   ```bash
   yt-dlp "ytsearch3:TITULO DO VIDEO" --print "%(id)s | %(duration)s | %(channel)s"
   # confirmar pela duração batendo com o arquivo local, depois:
   yt-dlp --write-auto-subs --sub-langs "pt-orig,pt" --sub-format vtt \
     --skip-download -o "video.%(ext)s" "https://youtube.com/watch?v=ID"
   ```
   `prepare` aceita o `.vtt` direto: o parser extrai o timestamp real de cada
   palavra, remove a duplicação da cue rolante e usa o `>>` como fronteira de
   troca de locutor.
2. **faster-whisper** com `word_timestamps=True` — o que `prepare` roda sozinho
   quando não há transcript.
3. Sem nenhum dos dois: **pare aqui** e entregue o diagnóstico de dependência.
   Não invente transcript.

Se o usuário já colou transcript com timestamps, use o dele e pule a geração.

## 3. Digest — o texto que os agentes leem

```bash
vch digest --run <run-dir>
```

Gera `02-digest.md`: texto + timestamp por bloco de ~20s, quebrando na troca de
locutor. **É isto que os agentes leem. Ninguém lê `02-transcript.json`.**

O transcript cru é muitas vezes maior que o digest, e quase todo o volume é
`words[]`, que o modelo **não usa** para escolher trecho — timing por palavra é
para os scripts (in/out, legenda, autoframe). Ler o transcript cru para escolher
assunto é carregar o episódio inteiro por uma informação que não entra na
decisão; num episódio longo, ele nem cabe na janela de um agente.

O digest marca com `»` os blocos com sinal determinístico de clipe (número,
contradição, confissão, risco, história). **A marca é ordem de leitura, não
seleção.** Momento bom sem palavra-chave existe; leia os marcados primeiro e
depois varra o resto.

> **Você, no loop principal, não lê nem o transcript nem o digest inteiro.**
> Você lê os artefatos JSON, que são compactos. Quem lê texto longo é subagente,
> em contexto próprio, que morre no fim da passagem.

## 4. Context Mapper

Subagente `context-mapper`. Entrada: **`02-digest.md`** e `01-media.json`. **Sem `03-visual-index.json`** — nesta fase ele
não existe, e isso é esperado: o mapeamento roda inteiro a partir do transcript.
`visual_events` aqui vem do que a fala descreve (print citado, reação
mencionada), não de frame extraído.

Saída: `04-context-map.json`.

```bash
vch validate-artifact --run <run-dir> --file 04-context-map.json
```

Não gere clipes nesta passagem.

## 5. Clip Hunter

Subagente `clip-hunter`. Saída: `05-viral-moments.json`, validado em seguida.

Encontre todos os momentos defensáveis, **sem forçar quantidade**. Cada momento
precisa de citação literal, timestamps e perfil provável.

**Critério de escolha:** não é a importância do trecho dentro do episódio. É a
chance de alguém cair nele **sem contexto nenhum** e continuar assistindo.

### As três perguntas, respondidas pelo TEXTO

- **Hook** — que frase/fato específico prende sem nenhum contexto anterior?
  (`trigger`)
- **Desenvolvimento** — o que sustenta entre o hook e o payoff: mecanismo,
  prova, virada, contra-argumento? Se não há nada sustentando, o momento é raso
  — vira observação, não candidato.
- **Payoff** — o que fecha a promessa do hook? (`payoff_candidate`)

Se as três respostas não existem no texto, o momento **não está pronto**. Ele
volta pra leitura do transcript, não pro vídeo, e não é adiável pra fase 2.

## 6. Apresente e PARE

Mostre ao usuário, por momento:

| | |
| --- | --- |
| timestamp | `in`–`out` aproximados, em `mm:ss` |
| citação | o trecho **literal**, não paráfrase |
| hook / desenvolvimento / payoff | uma linha cada |
| perfil | o perfil narrativo provável |
| duração | estimada |

Ordene por força, não por ordem cronológica — a pergunta dele é "quais
prestam", não "o que acontece no episódio".

Diga quantos momentos você descartou e por quê, em uma linha. Momento
descartado com motivo evita refazer a discussão depois.

**Pare aqui.** Não rode `visual-index`, não invoque `clip-builder`, não corte
nada. A fase 2 só começa depois que o usuário disser quais momentos viram corte
— e ele pode cortar metade da sua lista, que é justamente por isso que o corte
não foi feito antes.
