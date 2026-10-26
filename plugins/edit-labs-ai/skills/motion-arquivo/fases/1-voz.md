# Fase 1 — Voz e batidas

**Entrega:** `transcricao.json` palavra a palavra e `batidas.md` com cada palavra no degrau
da grade em que vai aparecer.

```bash
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/transcrever.py <projeto>/audio/narracao.wav <projeto>/transcricao.json pt
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/batidas.py <projeto>
```

- O tempo vem do **áudio**, nunca do roteiro. Timestamp de roteiro é descartado.
- `quadro` de cada palavra = primeiro degrau da grade (`n % 3 == 2`) depois que ela começa a
  ser dita. `t` = o instante exato (com fração), para fades contínuos.
- O `plano_rascunho.json` sugere um tipo por batida — é ponto de partida. A escolha é da fase 2.
- Confira a transcrição: nome próprio e número errados viram texto errado na tela. Corrija
  o texto no JSON sem mexer nos tempos.
