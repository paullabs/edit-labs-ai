# F3 CORTE + PRÉVIA — entrega 1

> O usuário recebe o corte decupado e a prévia. Nada anda sem a palavra dele aqui.

**Entrada:** EDL sem BLOCKER (`di edl <id>`). F1 e F2 não param: correm até aqui.
**Saída, por vídeo (`03_corte/<id>/`):** `corte_v01_V.mp4` e/ou `corte_v01_H.mp4`, `preview_v01.mp4`, `verificacao.json` + `VERIFICACAO.md`, `palavras_render.json`, **`AUDITORIA.md`**; `entrega/<id>.srt` e `.xml`.
**Quem revisa:** Verificador (V24–V42) e a **auditoria frase a frase**. Sem rodada de Diretor/Leigo. **Portão do usuário.**

## Passos, por `<id>`

1. **Render** (desanexado): `di render <id>`. Espere com `run_in_background` + `di portao status`.
2. **Verificação:** `di verificar-corte <id>` (retranscreve o render: é ela que dá a coluna «render diz»). BLOCKER → volte às decisões, nunca renderize o mesmo EDL de novo.
3. **Auditoria:** `di auditar <id>` → `AUDITORIA.md`. Abra **toda frase com alerta** e resolva antes de mandar:
   - ESTICADA / VÃO COM VOZ / RENDER REPETE → fala que o transcript engoliu. Retranscreva o trecho isolado do bruto, meça os silêncios e corte com `cortar_trecho` (F2). Nunca declare como pausa.
   - REPETE → duas tomadas da mesma frase ficaram: tire uma.
   - RENDER DIVERGE → o render não diz o que o EDL diz: confira a emenda mais próxima.
   - EMENDA / TEMPO → informação: diga na mensagem onde o usuário deve olhar.
4. **Exportar:** `di exportar <id> --srt --xmeml`.
5. **Mensagem ao usuário** (formato abaixo) com a prévia anexada e o caminho dos cortes. Grave em `laudos/PORTAO_F3_t<k>.md`.
   Se o modo tem motion e a régua ainda tem item sem resposta (`di portao pode-avancar F4` lista o que falta), as perguntas da régua vão **nesta mesma mensagem**, no fim, de múltipla escolha, com o padrão marcado — o texto de cada uma está em `memoria/regua.yaml` (`pergunta`, `opcoes`, `padrao`). Item já respondido (régua do usuário ou `respostas[]`) não entra. Tudo respondido → o bloco some.
6. **Resposta → primeira ação:**
   - "aprovado" → `di portao fechar F3 --aprovado-por usuario --palavra "<literal>"` e siga para o plano (F4).
   - respostas da régua → uma por item: `di portao responder --pergunta "<pergunta>" --resposta "<opção escolhida, por extenso>" --chave regua.<item>`. Elas vão para a régua do usuário e valem para os próximos projetos (só desta vez: `--so-projeto`). "vai" = os padrões, gravados por extenso.
   - **reprovado** (ou "tem um erro em…") → `di portao responder …` e **refaça pela auditoria, frase por frase**:
     1. ache a frase citada no `AUDITORIA.md` pelo tempo ou pelo texto; se ele não disse onde, percorra as frases em ordem com a prévia;
     2. leia a frase com a anterior e a seguinte; crave o trecho no bruto com `di digest --janela a-b` (tempo por palavra, silêncio medido);
     3. na dúvida sobre o que foi dito, retranscreva só aquele trecho do bruto — é o que revela palavra engolida;
     4. corrija as **decisões** (`decisoes.json`), `di edl <id>`, `di render <id>`, `di verificar-corte <id>`, `di auditar <id>`;
     5. mande a prévia nova dizendo o que era, onde estava e como ficou. Uma tentativa por reprovação: `di portao abrir-tentativa F3 --reprovado-por usuario --video <id> --o-que-mudou "…"`.
7. **O corte aprovado vira base congelada.** `corte_v02` só por pedido do usuário.

## Mensagem ao usuário (curta; bloco sem conteúdo = "nada")

```
ENTREGA 1 · CORTE · vídeo <n> (<id>) · tentativa <k>
Prévia: <anexo> · cortes: 03_corte/<id>/corte_v01_V.mp4 (e _H)
O que saiu do bruto: <n> tomadas repetidas, <n> falsos começos, <n> bastidores. <dur> de <dur do bruto>.
Conferi frase por frase: <n> frases; <nada com alerta | frase X em Y s: o que era e como ficou>.
Onde olhar primeiro: <emendas no meio de frase, com tempo | nada>.
NÃO verificado: a escuta — é com você.
Preciso que você decida: o corte está aprovado? (a) aprovado · (b) tem um erro em… <palavras a confirmar, no máximo 5>
Régua do motion (só o que falta; responda com as letras ou "vai" para os padrões):
  <n>. <pergunta> (a) <padrão> — padrão · (b) … · (c) …
```

Regras: nada de "ouvi", "soa", "estala"; tempos no relógio do corte (o que ele vê na prévia).

## Auto-rejeição de F3 (antes de mandar)

- Alguma frase com alerta ESTICADA, VÃO COM VOZ, REPETE ou RENDER REPETE sem resolver?
- Abre em conector (mas, então, aí, e, porque, agora) sem ser o gancho?
- Última frase cortada antes do fim da respiração (V33)?
- Duas emendas a menos de 1,2 s?

## Checklist de saída

```
[ ] corte_v01 + preview por vídeo
[ ] verificacao.json sem BLOCKER · AUDITORIA.md sem alerta de fala engolida ou repetição
[ ] mensagem em laudos/PORTAO_F3_t<k>.md; resposta do usuário gravada com a palavra literal
```
