# F4 PLANO

**Entrada obrigatória:** F3 fechada pelo usuário e a régua completa (`di portao pode-avancar F4`). A régua é o modelo `memoria/regua.yaml` coberto pelas respostas do usuário (`$EDITLABS_DATA/decupagem-inteligente/regua.yaml`): o que já foi respondido nunca se pergunta de novo; o que faltar foi perguntado uma vez, no portão do corte (F3).
**Saída, por vídeo:** `motion/<id>/` (projeto motion-vox padrão), `00_brief/PLANO_MOTION.md` no formato fixo, `00_brief/PROMPTS.md`, `00_brief/VERIFICACAO_PLANO.md`.
**Quem revisa:** Verificador (`di verificar-plano`, regras E1–E9). **Entrega 2 ao usuário** em `portoes`: o plano, o crédito de imagem e os logos a baixar. A análise do Diretor (C4) vem DEPOIS da aprovação, no começo da F5.

## Passos, por `<id>`

1. `di iniciar-motion <id>` — cria `motion/<id>/` a partir do corte aprovado: kit copiado, `fonte_V.mp4`/`fonte_H.mp4`, transcript e emendas no relógio do corte, silêncios medidos no próprio corte, `render.py` com `DUR`, `FPS`, `cortes=` e `MOTION_FPS` da régua (12, relógio único).
2. Leia `${CLAUDE_PLUGIN_ROOT}/skills/motion-vox/SKILL.md` §2 (escolher frases) e a **régua do usuário** (as regras de estilo E1–E9 de `memoria/regua.yaml`, com as respostas dele por cima). Elas decidem o que entra:
   - **E3** o elemento é o que de fato foi dito · **E4** marca citada → logo oficial · **E5** nada abstrato (círculo vazio, forma sem referente)
   - **E6** situação com gente mostra a pessoa (corpo, mãos, figura, foto — negociação = duas mãos apertando) · **E7** título sempre com um elemento que faz parte dele · **E8** toda cena com bastante motion, nada parado, nada clichê
   - densidade 65–75 % do corte, ≥ 1 s de rosto entre blocos (ou cenas coladas em rajada), gatilho < 1 s depois da palavra desenhável
3. Copie `memoria/templates/PLANO_MOTION.md` para `motion/<id>/00_brief/` e escreva a tabela B, uma linha por cena, com as 14 colunas. Tempos das palavras: `00_brief/transcript_palavras.json`, só por trecho (nunca o arquivo inteiro no contexto); vãos entre palavras e silêncios em `00_brief/silencios_corte.json`.
   - **Fim de cena (t1)**: no silêncio medido, na fronteira entre palavras ou numa emenda — nunca na sílaba. Fala rápida quase não tem silêncio: a fronteira de palavra vale. Sair **na** emenda esconde o pulo de cabeça (o rosto de antes nunca cola no de depois); sair 0,05–0,15 s antes dela entrega o pulo (V50).
   - **Layout H**: obrigatório quando a saída tem horizontal. Não é o vertical esticado: split vira lado a lado, pilha vira coluna à esquerda com o texto à direita.
   - Palavra em dúvida (pendência aberta) não sustenta cena: a cena espera a resposta do usuário (V49).
4. `di verificar-plano <id>` até não sobrar BLOCKER (a trava de V49 só cai com a resposta do usuário; o resto é do Editor).
5. **Provas reais (seção F)**: logo oficial de cada marca citada, foto real para pessoa nomeada (`motion-vox/referencias/fotos-reais.md`). **Baixar arquivo pede a permissão do usuário** (nome, origem, tamanho) — liste na mensagem de portão.
6. **Lista de geração (seção G = `PROMPTS.md`)**: todo substantivo desenhável sem prova real vira **asset sob medida** (`motion-vox/referencias/assets-sob-medida.md`): o objeto da fala, no mesmo mundo do kit. Procure antes na biblioteca (`di mv <id> --agora biblioteca.py buscar …`). O kit entra só quando é literalmente o objeto dito — herói do kit em 1 cena por vídeo, cartão A05 em 2 (E9) e no máximo 40 % das cenas apoiadas no kit (E10). Declare a origem de cada objeto em "O que aparece" (kit Axx, gerado NOME, logo, PIL). 2–3 variantes por herói, ferramenta, chamadas, custo.
7. Sem rodada de revisor antes do usuário: `di verificar-plano <id>` sem BLOCKER/HIGH e o plano vão direto na entrega 2. A análise C4 (E1–E9 cena por cena) roda uma vez, depois da aprovação, no começo da F5.
8. Portão do usuário (modo `portoes`), formato fixo de `fases/3-corte.md`. Uma pergunta só, de múltipla escolha, com o custo à vista: "posso gastar N imagens (lista G, ~X créditos) e baixar estes logos (lista F)? (a) pode, como está · (b) pode, sem os itens … · (c) ajustar o plano". Resposta → `di autorizar-imagens N --portao F4 --video <id> --palavra "<literal>"` e `di portao fechar F4 --aprovado-por usuario --palavra "…"`.

## Auto-rejeição de F4

- Alguma cena mostra coisa abstrata, ícone genérico ou palavra solta onde havia gente ou marca?
- Alguma marca citada sem logo e sem motivo na seção C?
- Algum título sozinho, sem o elemento que faz parte dele?
- Alguma cena com um beat só, ou com trecho parado?
- Algum t1 no meio de uma palavra?
- Faltou o layout H de alguma cena (saída `ambas`)?

## Checklist de saída

```
[ ] PLANO_MOTION.md sem BLOCKER no di verificar-plano (V49 só com resposta do usuário)
[ ] autorização de imagens e downloads gravada (di autorizar-imagens) — nada gerado antes
[ ] DIARIO: DECISÃO por cena que diverge de momentos.json; o que ficou de fora com motivo
```
