---
name: decupagem-inteligente
description: >-
  Edita um vídeo bruto do começo ao fim, em fases com portões (F0–F7): lê palavra por palavra,
  tira retakes, falsos começos e bastidores, monta o corte no silêncio entre palavras, audita
  frase por frase, planeja o motion por escrito, anima com a motion-vox, põe a legenda por último
  e entrega o master em V e H. Use para "edita", "decupa", "limpa esse bruto", "monta esse vídeo",
  "do bruto ao master", vídeo solo gravado com erros ou podcast; e para retomar: "continua",
  "retoma", "onde parou", "segue". Clipes curtos de podcast são da corte-viral; o kit de motion é
  a motion-vox. Exige o Higgsfield conectado para gerar imagens do motion.
allowed-tools:
  - Agent
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash(di *)
  - Bash(editlabs-verificar *)
  - Bash(ffmpeg *)
  - Bash(ffprobe *)
  - Bash(open *)
---

# decupagem-inteligente

Todo comando abaixo é `di <comando>` (o lançador `bin/di` do plugin, no PATH do Claude Code). Nada de método
aqui: o método mora em `fases/`. As regras comuns do plugin estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`; aqui
fica só o que é desta skill.

**Ambiente.** A skill roda no ambiente da corte-viral (`venv-corte`) e o kit de motion no da motion-vox
(`venv-motion`), os dois em `$EDITLABS_DATA` (padrão `~/.local/share/edit-labs-ai`). Se `di` disser que o
ambiente não foi preparado: rode `editlabs-setup`. Dados do usuário (lista de projetos e as respostas da régua)
ficam em `$EDITLABS_DATA/decupagem-inteligente/`, nunca dentro do plugin. O projeto nasce na pasta onde o
Claude Code foi aberto.

## Duas regras que não se dobram

1. **Perguntas ao usuário: poucas, fáceis, de múltipla escolha**, com o padrão marcado (responder "vai" aceita
   os padrões). Uma mensagem por portão, nunca uma pergunta por mensagem. **Preferência já respondida não se
   pergunta de novo:** é para isso que serve a régua (`memoria/regua.yaml` é o modelo com as perguntas e os
   padrões; as respostas do usuário ficam na régua dele e todo projeto novo herda). Antes de perguntar, confira
   a régua e `respostas[]`.
2. **A legenda entra por último.** Ela depende do corte final, das cutaways, das cenas, do B-roll e do som; só
   se desenha na F7, depois de tudo fechado, e qualquer mudança anterior obriga a refazê-la.

## 1. Retomada (antes de qualquer outra ação)

Leia `memoria/RETOMADA.md` e siga os 11 passos. Resumo:
- Caminho dado → use. Sem caminho → pasta atual com `run-manifest.json`; senão a lista de projetos do usuário
  (`$EDITLABS_DATA/decupagem-inteligente/projetos.json`): um ativo → use; vários → os 3 mais recentes com a fase,
  pergunte só "qual? (a) … (b) … (c) …"; nenhum → F0.
- `di portao status` → leia `ESTADO.md` → responda com a linha de estado → carregue **só** `fases/<N>-*.md` da fase atual.
- Não refaça o que está aprovado. Não pergunte o que está em `respostas[]` nem na régua.
- **A primeira ação depois de qualquer resposta do usuário é `di portao responder` ou `di portao fechar`.** Nenhum trabalho antes.

## 2. Três entregas — e onde eu paro

O usuário recebe **três coisas**, nesta ordem, e nada anda sem a palavra dele em cada uma. Regra: entrega
rápida; nada de rodadas de revisão em cascata entre uma entrega e outra.

1. **Corte decupado + prévia.** F0 → F1 → F2 → F3 correm sem parar; antes de mandar, `di auditar <id>` confere o corte **frase por frase, timestamp por timestamp**. Aprovado → segue. Reprovado → volto à auditoria, acho o erro no contexto da frase, corto certo, mando a prévia de novo. As perguntas da régua que ainda faltarem vão nesta mesma mensagem.
2. **Plano de motion.** F4. Aprovado → **análise** (Diretor C4, uma vez: faz sentido? cabe no tempo, nas marcas, no crédito?) e só então **criar** (F5 assets e composição, F6 cenas renderizadas), sem parar.
3. **Vídeo completo.** F7: legenda por último, montagem, verificação, V e H.

| Fase | Arquivo | Para no usuário? |
| --- | --- | --- |
| F0 BRIEF | `fases/0-brief.md` | uma vez, só o que falta |
| F1 LEITURA | `fases/1-leitura.md` | não — segue |
| F2 DECUPAGEM | `fases/2-decupagem.md` | não — segue |
| F3 CORTE + PRÉVIA | `fases/3-corte.md` | **sim — entrega 1**, em todo modo |
| F4 PLANO | `fases/4-plano.md` | **sim — entrega 2** (`portoes`) · pula (`so_corte`) |
| F5 ANÁLISE + CRIAÇÃO | `fases/5-rabiscos.md` | não — análise C4 uma vez e segue |
| F6 MOTION | `fases/6-motion.md` | não — segue (fim de cena vem do plano aprovado) |
| F7 VÍDEO COMPLETO | `fases/7-master.md` | **sim — entrega 3**, em todo modo |

Rodada de Diretor e Leigo em cascata antes de cada entrega não existe: fazia um vídeo levar horas e não pegava
o erro que o usuário pegava. Por dentro corre o Verificador (mede) e, no corte, a auditoria. Revisor, só quando
uma medida não fecha e eu não sei decidir sozinha.

Modo só muda com as palavras do usuário: "vai até o fim" → `ate_o_fim`; "só o corte" / "sem motion" → `so_corte`. Gravado com `di portao responder --chave modo`.

## 3. Papéis

- **Editor**: você, o chat. Decide; nunca aprova o próprio trabalho.
- **Verificador**: os scripts (`source: deterministic`). Mede; não opina.
- **Diretor** (`papeis/diretor.md`) e **Revisor Leigo** (`papeis/revisor-leigo.md`):
  - com a ferramenta Agent: subagente `edit-labs-ai:di-diretor` / `edit-labs-ai:di-revisor-leigo` (vêm com o plugin), só com o pacote do alvo;
  - para cegueira real (processo separado): `di diretor C1|C2|C3|C4|D4 [<id>]` e `di leigo F<N> <id>` (usam a CLI `claude -p`);
  - se o processo falhar: passe lendo o papel, laudo gravado antes de abrir outro arquivo, `isolamento: passe`.
- O laudo sempre passa por `di laudo gravar --de diretor|leigo` (valida e numera). D4 nunca por quem escreveu o plano. Regra de código nova sobre laudo do Leigo já gravado: `di laudo reaplicar <laudo>` (nunca rodar o Leigo de novo para mudar veredito).

## 4. Comandos

```
verificar                                    instalação (ffmpeg, módulos, skills irmãs, agentes)
preparar BRUTO [--glossario "…"]             F0: projeto + leitura em segundo plano
digest [--parte N] [--janela a-b]            F1–F2: o que o Editor lê
retakes · silencio · transcrever --realinhar F1: refazer uma etapa da leitura
amostrar <id> · edl <id>                     F2: TOMADAS.jpg · EDL + MARCAS + roteiro
render <id> [--saida V|H|ambas] [--preview]  F3 (recusa sem pode-avancar F3)
verificar-corte <id> · auditar <id> · exportar <id> --motion-vox|--srt|--xmeml
iniciar-motion <id>                          F4: motion/<id>/ a partir do corte aprovado (V e H)
verificar-plano <id>                         F4: PLANO_MOTION.md contra V43–V52 e a régua E1–E9
mv <id> [--saida V|H] <script> [args]        F5–F7: roda o kit (compose.py, ancorar.py, prancha.py,
                                             checar_asset.py, render.py M# --frames | CAP --frames | --mux,
                                             janelas_legenda.py — este só na F7)
verificar-motion <id> --saida V|H --trecho t0 t1 | --master · entregar <id>
autorrejeitar F<N> [<id>]                    o que eu mesma reprovaria, por código, ANTES do revisor
pacote-leigo F<N> <id> · leigo F<N> <id> · diretor <rubrica> [<id>]
portao status|pode-avancar|abrir-tentativa|fechar|responder|pendencia|confirmar|proximo|decidir-vendo
diario --tipo DECISAO|TENTATIVA|NOTA --texto "…" · autorizar-imagens N --portao F4 --video <id> --palavra "…"
```

Fechar portão do usuário: `di portao fechar F<N> --aprovado-por usuario --palavra "<o que ele disse, literal>"`.
Fase interna: `--aprovado-por interno`.

Três regras:
1. Nenhum render, geração de imagem ou mensagem de portão sem `di portao pode-avancar` ter passado.
1b. Nenhum revisor sem `di autorrejeitar F<N> [<id>]` fechar em ✓: HIGH/BLOCKER em aberto sem o id declarado por escrito barra a chamada (o `di diretor`/`di leigo` recusa). Rodada de revisor é o recurso caro da skill; ela não se gasta com o que o script já mediu.
2. Comando demorado volta na hora ("rodando"). Espere com `run_in_background` + `di portao status`; nunca relance.
3. Mensagem de portão no formato fixo de `fases/3-corte.md`, gravada em `laudos/PORTAO_F<N>_t<k>.md`.

## 5. Fronteiras e custo

- Motion é a skill irmã `${CLAUDE_PLUGIN_ROOT}/skills/motion-vox`, só por `di mv` (nunca `python3` solto, nunca copiar). Clipes de podcast: `${CLAUDE_PLUGIN_ROOT}/skills/corte-viral`.
- Nunca leia `01_transcript/palavras.json` inteiro: digest, `--janela`, `--parte`.
- Correção de método vai em `referencias/armadilhas.md` da skill, nunca numa cópia de projeto.
- Ninguém dentro da skill ouve nem assiste. Verbo de escuta só com `escuta: humana` gravada.
- Crédito de imagem e vídeo gerado: só com `di autorizar-imagens` depois da resposta do usuário ("pode"), com o custo mostrado antes. Baixar logo ou foto real também pede a palavra dele.
- Régua: `memoria/regua.yaml` (modelo: perguntas, opções e padrões; regras de estilo E1–E9 do motion: 12 fps, um relógio só, grão, RGB mínimo, turbulência leve). As respostas do usuário ficam em `$EDITLABS_DATA/decupagem-inteligente/regua.yaml`, gravadas por `di portao responder --chave saida|regua.<item>`; todo projeto novo herda e nada se pergunta de novo.
- Entrega: `<projeto>/FINAIS/` (ou a pasta de `DI_FINAIS`). Biblioteca própria de efeitos sonoros: `DI_SFX` (opcional).
