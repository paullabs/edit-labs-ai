# F2 DECUPAGEM

**Entrada obrigatória:** F1 fechada (`di portao pode-avancar F2` passa).
**Saída, por vídeo (`02_decupagem/<id>/`):** `decisoes.json` (o único JSON que o Editor escreve), `edl.json`, `MARCAS.md`, `roteiro_montado.txt`, `pendencias.md`, `TOMADAS.jpg`.
**Quem revisa:** Verificador (checks de `di edl`). **Não para no usuário:** o EDL sem BLOCKER segue direto para o render e a auditoria (entrega 1, F3).

## Passos, por `<id>` do mapa

1. **Antes de decidir:** leia `referencias/armadilhas.md` (Corte e Retakes) e `referencias/regras-de-corte.md`.
2. **Leia o bloco no digest.** Para cravar tempo ou palavra: `di digest --janela a-b` (palavras com índice, tempo, `?` e ⟂silêncio).
3. **Escreva `02_decupagem/<id>/decisoes.json`**, na ordem em que o vídeo vai ser dito:
   ```json
   {"bloco": "03-prompt-claude", "titulo": "…", "padrao": "remover",
    "manter": [
      {"frase": 201, "motivo": "abertura limpa da segunda gravação"},
      {"grupo": "G24", "tomada": 2, "motivo": "a única completa"},
      {"de_palavra": 812, "ate_palavra": 840, "motivo": "costura dentro da frase: …"}],
    "pausas_preservar": [{"apos_palavra": 1335, "funcao": "respiro antes do número"}],
    "pausas_colapsar_intra": [],
    "fillers_vetados": [],
    "emendas_seco": [],
    "ambiguas": [{"palavra": 1473, "ouvido": "Facebook", "provavel": "Fable", "status": "a confirmar"}]}
   ```
   - `manter` segue a **sua** ordem: retake pode voltar no tempo (V16 avisa, não bloqueia).
   - Todo item tem `motivo`. Divergiu da sugestão (✓)? O motivo diz por quê.
   - `½` no digest: as duas metades juntas **ou** a tomada inteira, nunca uma metade sozinha.
   - Pausa entre 0,35 e 0,6 s que fica: liste em `pausas_preservar` com a função. Abaixo de 0,6 s não compensa emenda.
   - Palavra ambígua que entra no corte: em `ambiguas` com `status: a confirmar`.
   - Saída sem silêncio (a fala emenda direto na seguinte) só quando o usuário pediu para tirar o que vem depois: `"saida_no_vale": [{"apos_palavra": N, "motivo": "pedido do usuário: …"}]`. O corte vai para o vale de energia entre as duas palavras, com crossfade de 20 ms e V17_relaxada HIGH; a mensagem do portão diz que a emenda é colada e só o usuário ouve.
   - Falso começo que o Whisper engoliu numa palavra esticada (V20d BLOCKER, ou vão com voz no digest): retranscreva o trecho isolado, meça os silêncios e corte sem mexer no transcript: `"cortar_trecho": [{"apos_palavra": N, "abandona_de": t, "abandona_ate": t, "retoma_em": t, "motivo": "…"}]` (tempos do bruto). #N+1 passa a valer pela tomada que recomeça. **Nunca** declare esse vão em `pausas_preservar`.
   - Estalo ou respiro curto antes da fala abrindo o segmento cedo (V20 acusa a pausa logo depois da 1ª palavra): `"entrada": "voz_sustentada"` no item, com o motivo. A retranscrição do render confere se a palavra ficou.
4. **Gere o EDL:** `di edl <id>`. BLOCKER = o EDL não sai (`edl.rejeitado.json` diz a junta). Corrija **as decisões**, nunca a régua: sem ponto limpo, troque a tomada ou a costura.
5. **Leia `MARCAS.md`** inteiro. Confira cada emenda: "folga à voz in/out · resíduo (respiro)".
6. **`di amostrar <id>`** → `TOMADAS.jpg`: um quadro por tomada escolhida. Olhe: olhar fora, mão no rosto, desfoque, gente no quadro.
7. **Sem rodada de revisor.** `di autorrejeitar F2` em ✓. **Nenhuma pausa entra em `pausas_preservar` com voz medida dentro dela** — pausa com voz é fala que o transcript não viu, não "suspense".
8. **Fecha e segue para o render:** `di portao fechar F2 --aprovado-por interno`. Quem aprova o corte é o usuário, na prévia (F3).

## O que o Leigo reprova e o que não reprova

- `tipo: corte` BLOCKER/HIGH (frase repetida, frase pela metade, ideia que pula) → o veredito é REPROVADO, aplicado por código.
- `tipo: conteudo` (nome desconhecido, número sem escala) e `tipo: pendencia` (`[palavra incerta]`) → sempre LOW. Vão para o portão F3 como informação, não reabrem F2.

## Auto-rejeição de F2

Rode `di autorrejeitar F2` primeiro: ele traz os checks em aberto, os já declarados, as emendas coladas e o que só o olho pega. Revisor só depois do ✓.

- Alguma emenda abre em conector ("mas", "então", "aí", "e", "porque", "agora")?
- Algum grupo com duas tomadas inteiras no `manter` (V15)?
- Alguma metade `½` entrou sozinha?
- Alguma pausa > 0,35 s ficou sem função listada (V20)?
- Alguma junta relaxada (V17_relaxada) sem eu ter conferido a janela no digest?

## Checklist de saída

```
[ ] edl.json sem BLOCKER para todo <id>
[ ] pendencias.md por vídeo; pendências gravadas no manifest
[ ] DIARIO: DECISÃO para cada tomada que diverge da sugestão; TENTATIVA para cada reprovação
```
