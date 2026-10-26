# F1 LEITURA

**Entrada obrigatória:** job `leitura` com `status: ok` em `di portao status` (transcrição, silêncios, retakes e digest prontos).
**Saída:** `02_decupagem/MAPA_DO_BRUTO.md` escrito pelo Editor; `pendencias[]` com as palavras que parecem nome ou número.
**Quem revisa:** Verificador (checks de F1, já gravados pela leitura). **Não para no usuário:** o mapa segue direto para a decupagem; o que ele vê é o corte com a prévia (entrega 1, F3).

## Passos

1. **Espere a leitura.** `di portao status` mostra "transcrevendo 41 %". Espere com `sleep 60` + status; nunca relance. `erro` → leia `00_fonte/_log/leitura.log` e refaça só a etapa (`di transcrever`, `di silencio`, `di retakes`, `di digest`).
2. **Leia `01_transcript/digest.md`**, uma linha por frase. Bruto longo: `di digest --parte N`, uma parte por vez no contexto. **Nunca** abra `palavras.json` inteiro; para cravar um trecho use `di digest --janela a-b`.
   Marcas: ✓ tomada sugerida · `G07 t2/4` grupo e tomada · `½+F024` metade (junto com a vizinha forma uma tomada) · B bastidor · c cauda de bastidor · x autocorreção · … abandonada · ~ alucinação suspeita · g gagueira · h hesitação · `?palavra` baixa confiança · `parcial←` retake parcial.
3. **Escreva `02_decupagem/MAPA_DO_BRUTO.md`**. É ele que define os vídeos (`<id>`) dentro do bruto:
   - bloco `yaml` com `blocos: [{id: NN-slug, assunto, t, e, regravacao?}]`;
   - tabela `trecho | o que é` cobrindo **100 %** do tempo: vídeo, bastidor, silêncio, alucinação, regravação (com o início exato da tomada que vale);
   - bastidores pontuais dentro de um vídeo, com tempo;
   - grupos que o script montou errado: metades que não são alternativas, grupos dentro de bastidor;
   - tabela "Palavras e números a confirmar": ouvido → provável → onde (frase e tempo) → vai para;
   - vozes declaradas com método (`multitrack | silencio_global | solo`).
4. **Pendências.** Cada palavra do mapa que parece nome ou número: `di portao pendencia --o-que "…"`. Palavra comum com `p` baixa não vira pendência (a retranscrição do render confirma).
5. **Sem rodada de revisor.** `di autorrejeitar F1` em ✓ basta.
6. **Vão com voz.** Todo vão > 1 s em que o áudio medido tem voz entra no mapa como "possível fala engolida" com tempo: a decupagem corta ou mantém com medida, nunca como pausa.
7. **Fecha e segue:** `di portao fechar F1 --aprovado-por interno`. Uma linha de progresso:
   `F1 LEITURA · pronto · <n> vídeos, <n> grupos de retake, <n> bastidores, <n> palavras a confirmar · piso <x> dB`

## Armadilhas desta fase

Leia `referencias/armadilhas.md` (seção Leitura) antes de escrever o mapa. As mais caras:
- O Whisper enche silêncio longo de "E aí" repetido (alucinação `~`): nunca é fala.
- Frase sem ponto final pode ser completa; frase colada na seguinte sem pausa também.
- Duas frases vizinhas num grupo podem ser metades de uma tomada (`½`), não alternativas.
- "Cloud" por "Claude", "Facebook" por "Fable": o glossário ajuda, mas o Editor confirma pelo contexto.

## Auto-rejeição de F1

Rode `di autorrejeitar F1` primeiro: ele traz os checks em aberto, os já declarados, as emendas coladas e o que só o olho pega. Revisor só depois do ✓.

- O mapa deixa algum segundo sem linha?
- Algum nome ou número com `?` na tomada que vale ficou fora da lista a confirmar?
- A regravação tem dois inícios diferentes no mapa?
- Algum grupo mistura frases de conteúdo diferente sem nota?

## Checklist de saída

```
[ ] MAPA_DO_BRUTO.md cobre 100 % e define os <id>
[ ] laudos/F1_V_verificador_t<k>.json sem BLOCKER
[ ] pendências gravadas
```
