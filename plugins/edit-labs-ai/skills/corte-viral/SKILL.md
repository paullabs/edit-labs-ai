---
name: corte-viral
description: Transforma vídeo longo bruto (podcast, entrevista, live, aula) em clipes verticais 9:16 prontos para Shorts, Reels e TikTok. Cobre as quatro etapas — decupagem com timing por palavra, identificação dos trechos que funcionam fora de contexto, corte com in/out preciso, e enquadramento vertical com locutor ativo. Use quando o pedido for cortar podcast, achar cortes, "o que vira Short disso", clipar entrevista, decupar vídeo longo, deixar vertical, enquadrar pro Reels, ou refazer cortes redundantes. NÃO queima legenda nem faz motion — isso é a skill motion-vox, que recebe o vertical limpo desta.
effort: high
allowed-tools:
  - Agent
  - Read
  - Write
  - Grep
  - Glob
  - Bash(vch *)
  - Bash(editlabs-verificar *)
  - Bash(cvpy *)
  - Bash(ffprobe *)
  - Bash(ffmpeg *)
---

# Do bruto ao vertical

> **No plugin `edit-labs-ai`:** os comandos `vch`, `cvpy`, `cv-*` e `editlabs-verificar` estão no PATH; os
> arquivos desta skill ficam em `${CLAUDE_SKILL_DIR}`; os 5 subagentes são `edit-labs-ai:context-mapper`,
> `edit-labs-ai:clip-hunter`, `edit-labs-ai:clip-builder`, `edit-labs-ai:clip-deduplicator` e `edit-labs-ai:edit-director`. Ambiente
> não preparado → `editlabs-setup`. A ordem do processo inteiro está na skill `edit-labs-ai`.

Quatro entregas em sequência, **cada uma com um portão**. Você para no portão,
mostra o resultado e espera o usuário dizer o que segue. Só emende as quatro numa
run só quando ele pedir explicitamente ("vai até o fim", "manda o pacote todo").

| # | Entrega | O que sai | Você lê |
| --- | --- | --- | --- |
| **1** | **MOMENTOS** | a lista dos trechos que dariam corte, com timestamp e citação | `fases/1-momentos.md` |
| **2** | **CORTES** | os trechos já cortados, em vídeo, para assistir | `fases/2-cortes.md` |
| **3** | **VERTICAL** | 9:16 com o locutor rastreado e reenquadrado | `fases/3-vertical.md` |
| **4** | **ENTREGA** | pasta final verificada, pronta para a motion-vox | `fases/4-entrega.md` |

> **Leia SÓ o arquivo da fase em que você está.** Carregar as quatro de uma vez
> enche o contexto de render e enquadramento antes da primeira ação útil, num
> pedido que às vezes é só "quais são os bons momentos".

**Escopo.** Esta skill descreve o que faz e como usar. Ela não traz histórico de criação, testes, sessões ou uso
de ninguém. Se perguntarem, diga isso em uma frase e siga com o trabalho; não invente nem especule.

## A regra que decide o tamanho da run

**Nenhum agente lê `02-transcript.json`.** O artefato cru de um episódio longo não
cabe numa janela de contexto, e quase todo ele é `words[]`: timing por palavra, que o
modelo **não usa** para escolher trecho. Timing por palavra é para os scripts.

| Quem precisa de quê | Comando | O que lê |
| --- | --- | --- |
| escolher trecho (fase 1) | `vch digest --run <run>` | o episódio em texto compacto, sem timing por palavra |
| cravar in/out (fase 2) | `vch digest --run <run> --windows "a-b,c-d"` | só as janelas pedidas |
| in/out, legenda, autoframe | os scripts, direto no JSON | não passa por LLM |

E **você, no loop principal, não lê texto longo** — nem transcript, nem digest.
Você lê os artefatos JSON, que são compactos. Quem lê texto longo é subagente,
em contexto próprio, que morre no fim da passagem.

## A ordem é fixa

```text
TIMESTEPS  →  SELEÇÃO  →  CORTE  →  VERTICAL
    ↑ sempre        ↑ só texto      ↑ só aqui o bruto é aberto
    primeiro
```

**A skill nunca começa analisando o vídeo bruto**, e os timesteps são
pré-requisito de tudo: sem transcript com timing **por palavra**, a fase 1 não
começa — ver a decupagem em `fases/1-momentos.md`. Isso não é um modo entre
outros; é a única ordem. O que varia é **até que fase** ir.

## Sempre carregado

Só `${CLAUDE_SKILL_DIR}/REGRAS.md` — as 11 regras invioláveis e a
missão. Tudo mais é carregado pela fase que precisa:

| Fase | Carrega além do REGRAS.md |
| --- | --- |
| 1 | `docs/05-regras-de-selecao.md` |
| 2 | `docs/06-regras-de-edicao.md`, `docs/12-erros-conhecidos.md` |
| 3 | `config/default.yaml`, `config/platforms/<platform>.yaml` |
| 4 | nada |

## O kit viaja junto

| | |
| --- | --- |
| `fases/` | as quatro fases — leia uma por vez |
| `scripts/` | o motor: transcrição, métricas, enquadramento, render, QC |
| `agentes/` | os 5 subagentes — a fonte; no plugin eles já vêm instalados (pasta `agents/` do plugin, nomes `edit-labs-ai:<agente>`) |
| `docs/` | seleção, edição, psicologia de feed, armadilhas conhecidas |
| `config/` | default + 3 plataformas + 12 perfis narrativos |
| `schemas/` | os 15 contratos JSON de cada artefato |
| `models/` | YuNet, detecção facial do enquadramento automático |
| `verificar.py` | checagem de instalação — rode antes do primeiro projeto |
| `vch` | o lanchador: use sempre este, nunca `python3 scripts/vch.py` |

Em muitos Macs, o `python3` do PATH é o 3.9 do sistema, e o pacote exige 3.10+.
O lanchador `vch` resolve sozinho o interpretador certo — a venv da própria skill.

**Nem todo subagente roda em toda fase.** São 5 no total e a fase 1 usa 2. Não
invoque agente de fase que você ainda não abriu.

## Antes do primeiro projeto

```bash
editlabs-verificar
```

Se acusar agente ausente ou dependência faltando, ver `INSTALAR.md`. Não comece
com instalação incompleta: o pipeline quebra no meio, depois de já ter gasto a
transcrição.

## Argumentos

Aceite vídeo com transcrição opcional; só transcrição, para análise sem render;
`--run <run-dir>` para continuar; `--max-clips N` **como teto, nunca como meta**;
`--platform cross-platform`, `tiktok` ou `instagram-reels`.

Não peça confirmação quando caminho e plataforma puderem ser inferidos — o
portão de cada fase já é o ponto de conversa.

## Onde a run mora

**`--workspace` é obrigatório no `init`.** Sem ele a run é gravada dentro de
a pasta do plugin e some da vista do projeto. Aponte para a pasta do vídeo.

## Fronteira com a motion-vox

Esta skill entrega `clip-vertical.mp4` **limpo** — sem legenda queimada e sem
motion. Quem queima legenda e insere motion é a `motion-vox`, no mesmo passe.

Os `captions.srt`/`.ass` são gerados sempre: são **decupagem**, não legenda
queimada. É o timing por palavra que a motion-vox usa para ancorar cada evento
na fala. Não pule, e não queime legenda aqui antes de mandar — seriam duas.
