# 8. Entregáveis e organização

## 8.1 Estrutura de um run

```text
workspace/runs/<run-id>/
├── 00-manifest.json
├── 01-media.json
├── 02-transcript.json
├── 03-visual-index.json
├── 04-context-map.json
├── 05-viral-moments.json
├── 06-candidates.json
├── 08-technical-audit.json
├── 10-deduplication.json
├── 11-edit-plans.json
├── 13-final-clips.json
├── 14-rejected-clips.json
├── 15-run-report.md
├── 16-output-verification.json     # full/render
├── assets/
│   ├── audio-analysis.wav
│   ├── frames/
│   └── contact-sheets/
├── iterations/
└── output/
    ├── context-index.md
    └── final-clips/
```

Os números 07, 09 e 12 não são gerados por nenhuma etapa (ver `REGRAS.md`).

## 8.2 Estrutura por contexto

```text
output/final-clips/<primary-context>/<clip-id>-<slug>/
├── clip-vertical.mp4
├── clip-clean.mp4
├── captions.srt
├── captions.ass
├── caption-map.json
├── edit-plan.json
├── metadata.json
├── transcript.txt
├── editor-notes.md
└── preview.jpg
```

## 8.3 Contextos primários

- `dinheiro`;
- `contradicao`;
- `resposta-rapida`;
- `historia`;
- `revelacao`;
- `opiniao`;
- `humor`;
- `autoridade`;
- `transformacao`;
- `tutorial`;
- `conflito`;
- `long-clip`;
- `outro`.

Um clipe pode ter tags adicionais, mas apenas um contexto primário determina a pasta.

## 8.4 Metadata

Cada `metadata.json` contém:

- título interno;
- contexto;
- tags;
- duração;
- segmentos de origem;
- scores;
- métricas de velocidade;
- status;
- versão;
- checksum do arquivo;
- data de geração;
- limitações;
- texto de legenda social sugerido, quando solicitado.

## 8.5 Relatório humano

`15-run-report.md` deve mostrar:

- resumo do episódio;
- quantidade por status;
- clipes aprovados em ordem de prioridade;
- duplicatas e qual versão venceu;
- clipes reconstruídos;
- rejeições e motivo;
- dependências ausentes;
- alertas de verdade/contexto;
- localização dos arquivos.

## 8.6 Entrega parcial

Quando renderização não for possível, o run ainda deve entregar:

- JSON final;
- SRT quando timestamps existirem;
- edit plan;
- relatório;
- diagnóstico claro.

Nunca declarar que há MP4 quando não há.
