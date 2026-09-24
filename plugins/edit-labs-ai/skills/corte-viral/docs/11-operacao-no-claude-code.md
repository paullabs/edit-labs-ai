# 11. Operação no Claude Code

## Onde a skill mora

No plugin `edit-labs-ai`, nada é copiado para `~/.claude/`:

```text
<plugin>/skills/corte-viral/   a skill (`${CLAUDE_SKILL_DIR}`), roda de qualquer pasta
<plugin>/agents/               os 5 subagentes, registrados como `edit-labs-ai:<agente>`
```

A pasta `agentes/` dentro da skill é a **fonte**; `agents/` do plugin é a cópia
que o Claude Code registra, e as duas têm de ser idênticas. `editlabs-verificar`
acusa cópia ausente ou defasada. O ambiente Python se prepara com `editlabs-setup`.

## Como chamar

A skill é invocável pelo modelo — "corta esse podcast", "o que vira Short disso",
"deixa vertical". Diretamente:

```text
/corte-viral ~/Videos/podcast.mp4 --mode full
```

## Onde as runs ficam

Sempre no projeto, nunca dentro da skill:

```bash
vch init VIDEO.mp4 LEGENDA.vtt \
  --mode full --workspace <PASTA-DO-PROJETO>/runs
```

Sem `--workspace`, a run cai em `skills/corte-viral/workspace/runs/`, dentro da
pasta do plugin, e some da vista do projeto.

## Modos

| Modo | Faz |
| --- | --- |
| `analyze` | decupagem + seleção, sem render |
| `verify` | acrescenta auditoria técnica e dedupe |
| `render` | corta e renderiza o vertical |
| `full` | tudo |

## O lanchador

Todo comando passa por `vch`, que o plugin põe no PATH. Ele usa o ambiente
Python do plugin, criado pelo `editlabs-setup` — em muitos Macs, o `python3` do
PATH é o 3.9 do sistema, que não roda o pacote.

## Retomar uma run

```bash
vch init --run <run-dir>
```

Os artefatos numerados `00`–`16` dizem onde parou. Não recomece do zero: a
transcrição e o índice visual são a parte cara.
