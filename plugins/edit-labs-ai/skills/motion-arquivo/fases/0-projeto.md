# Fase 0 — Projeto

**Entrega:** a pasta do projeto montada e o brief confirmado. 👤 portão.

## Entrada (uma destas)

| o usuário traz | o que fazer |
| --- | --- |
| **áudio da narração** (wav, mp3, m4a) | é a fonte do tempo; copia para `audio/` |
| **vídeo** com a fala (talking head, aula, podcast) | o áudio sai dele; a imagem pode virar `foto_pullout`/insert, mas o estilo é o da narração em arquivo |
| **roteiro em texto** | precisa de voz: gravação dele (preferida) ou TTS. `say -v Luciana` do macOS só serve para testar tempo — nunca para entrega |
| **um vídeo de referência para reproduzir** | é o caso Hedy: medir antes (`referencias/medir-referencia.md`) |

## Pasta

```
<projeto>/
  plano.json         (fase 2)
  audio/narracao.*   a voz
  transcricao.json   (fase 1)
  assets/ reais/ baixados/ gerados/ prontos/ FONTES.md
  saida/             render, tripticos, laudos
```

## Brief (perguntar só o que faltar)

- **Assunto e a história escondida**: o que todo mundo usa / quem ninguém lembra / o porquê.
- **Formato**: vertical 1080×1920, 30 qps entregue (10 de conteúdo). Duração = a da voz.
- **Idioma do texto na tela** (o da fala, salvo pedido).
- **Fecho**: para onde leva (perfil, site, produto) — define os planos `icone_cursor`/`site_url`.
- **Orçamento**: pode baixar de acervo? quanto crédito de geração? (a lista com custo vem na fase 2).

Não comece a fase 1 sem o brief: o mapa batida → plano depende da história, não só do texto.
