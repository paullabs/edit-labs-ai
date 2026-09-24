# Exemplo mínimo

Este exemplo existe para testar o caminho determinístico do harness sem depender de um podcast real nem de um modelo.

- `transcript.srt`: transcript sintético de 12 segundos.
- `fixtures/`: saídas simuladas das etapas semânticas do Claude.
- `../../tests/smoke_test.sh`: gera uma mídia local, executa ingestão, auditoria, legenda, render e verificação.

Execute da raiz:

```bash
bash tests/smoke_test.sh
```

O teste usa `config/testing/smoke.yaml`, com preset rápido de renderização. Ele não avalia qualidade editorial do modelo; verifica contratos, timestamps, legenda, FFmpeg, organização e arquivos finais.
