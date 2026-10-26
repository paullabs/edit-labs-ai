# F6 MOTION

**Entrada obrigatória:** F5 fechada.
**Saída, por vídeo:** todas as cenas renderizadas com `.done`, em cada saída; tiras em `11_qa/tiras/`. **Sem legenda ainda:** ela entra por último, na F7.
**Quem revisa:** Verificador (`di verificar-motion`). **Não para no usuário:** sem piloto; o fim de cena é o do plano aprovado. Renderize as cenas uma saída de cada vez (variantes da mesma saída nunca em paralelo).

## Passos

1. **Sem piloto.** O fim de cena é o do plano aprovado (coluna "Fim de cena"); `--fim` não se usa.
2. Render das cenas, **pelo nome, uma saída de cada vez** (V, depois H — duas variantes da mesma saída em paralelo apagam os quadros uma da outra):
   `di mv <id> --saida V render.py M1 M2 … --frames` (o `di mv` confere a contagem de quadros e grava `.done`; a retomada refaz só a cena sem `.done`). Repita em H.
   Dê sempre os nomes das cenas: `render.py --frames` sem nome também desenha a legenda, e a legenda é da F7.
3. Efeitos sonoros (se o plano pediu) fecham aqui, junto das cenas: um por ação visível, nível medido abaixo da voz.

## Auto-rejeição de F6

- Alguma cena parada mais de 1,5 s (V62)?
- Algum SFX sem ação visível?
- Desenhei a legenda antes de as cenas estarem fechadas?

## Checklist de saída

```
[ ] todas as cenas com .done em V e H
[ ] nenhuma passada de legenda ainda (10_sequences/<S>/CAP vazia ou ausente)
```
