# F7 VÍDEO COMPLETO — entrega 3

**Entrada obrigatória:** F6 fechada; toda cena com `.done` em cada saída (o mux recusa sem).
**Saída, por vídeo:** `motion/<id>/12_master/MASTER_V_v01.mp4` e `MASTER_H_v01.mp4`, `05_motion/JANELAS_LEGENDA.json`, `11_qa/verificacao_master_<S>.json`, cópias em `<projeto>/FINAIS/` (ou na pasta de `DI_FINAIS`), `entrega/RESUMO.md`.
**Quem revisa:** Verificador (`di verificar-motion --master`). **Entrega 3 ao usuário:** o vídeo completo em V e H, em todo modo.

## Passos

1. **Legenda, por último.** Só agora, com corte, cenas, B-roll e som fechados (qualquer mudança neles obriga a recalcular):
   - janelas por código: `di mv <id> --agora janelas_legenda.py` (cala sob cutaway com tipografia própria, nunca atravessa emenda, cala a oração com palavra pendente);
   - passada da legenda: `di mv <id> --saida V render.py CAP --frames` e `--saida H`.
2. Montagem: `di mv <id> --saida V render.py --mux` e `--saida H` (a legenda fica por cima de tudo).
3. `di verificar-motion <id> --saida V --master` e `--saida H`: duração e cadência iguais ao corte (V68), fala preservada (V69), áudio intocado quando não há SFX (V70, MD5), pico ≤ −1 dBTP e loudness (V71), formato e quadro preto (V73), tiras (V74).
4. Sem rodada de revisor: o Verificador sem BLOCKER basta para mandar.
5. Mensagem de portão (formato de `fases/3-corte.md`), com a linha "NÃO verificado: escuta e movimento em tempo real — fica com o usuário". Uma pergunta: "(a) aprovado · (b) tem um ajuste em…".
6. Resposta "aprovado" → `di portao fechar F7 --aprovado-por usuario --palavra "…"` → `di entregar <id>` (cópia com sha256 para FINAIS como `<data>_<bruto>_<id>_<V|H>.mp4`, `entrega/RESUMO.md` de 5 linhas; no macOS o Finder abre no arquivo).
   Ajuste pedido que mexe em cena ou som → refaça a cena, e a legenda de novo (passo 1) antes do mux.

## Auto-rejeição de F7

- Legenda desenhada antes de cena, B-roll ou som mudarem pela última vez?
- Legenda aparecendo sob uma cena com tipografia própria, ou cobrindo o queixo no H?
- Duração ou quadros diferentes do corte aprovado?
- Pico acima de −1 dBTP?
- Cena sem `.done` entrou no mux?

## Checklist de saída

```
[ ] legenda feita por último (janelas + CAP depois das cenas)
[ ] masters V e H verificados sem BLOCKER
[ ] palavra do usuário na entrega
[ ] FINAIS com sha256 igual ao master; RESUMO.md com "NÃO verificado"
```
