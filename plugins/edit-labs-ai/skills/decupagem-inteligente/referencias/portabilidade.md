# Ambiente e isolamento

A skill vem dentro do plugin Edit Labs AI: `${CLAUDE_PLUGIN_ROOT}/skills/decupagem-inteligente/`. Não há
instalação própria.

## Onde mora cada coisa

| Coisa | Onde |
| --- | --- |
| lançador | `bin/di` do plugin (no PATH do Claude Code); exporta `DI_ROOT`, `CV_PY`, `MV_PY`, `EDITLABS_DATA` |
| Python da skill | `$EDITLABS_DATA/venv-corte` (o mesmo da corte-viral; criado por `editlabs-setup`) |
| Python do kit de motion | `$EDITLABS_DATA/venv-motion` (versões fixadas da motion-vox); `di mv` usa este |
| skills irmãs | `${CLAUDE_PLUGIN_ROOT}/skills/motion-vox` e `…/corte-viral` (o código acha pela própria pasta) |
| agentes | `${CLAUDE_PLUGIN_ROOT}/agents/di-diretor.md` e `di-revisor-leigo.md` → `edit-labs-ai:di-diretor`, `edit-labs-ai:di-revisor-leigo` |
| dados do usuário | `$EDITLABS_DATA/decupagem-inteligente/` (`projetos.json`, `regua.yaml`) — sobrevivem a atualização |
| projeto | a pasta onde o Claude Code foi aberto (`<bruto>-decupagem/`); `--projeto` muda |
| entrega | `<projeto>/FINAIS/`, ou `DI_FINAIS` |
| efeitos sonoros próprios | `DI_SFX` (opcional) |

O estado mora no projeto (`run-manifest.json`), nunca na memória do host. Os papéis são os mesmos `.md` em
`papeis/`; o laudo passa pelo mesmo `di laudo gravar`. A régua de corte, as checagens e os portões são código.

## Isolamento declarado no laudo

| `isolamento` | Como rodou | Cegueira |
| --- | --- | --- |
| `processo` | `claude -p --tools Read --system-prompt <papel> --add-dir <pacote>`, prompt por stdin (`di diretor`, `di leigo`) | real: o processo só vê o pacote |
| `subagente` | ferramenta Agent com `edit-labs-ai:di-diretor` / `edit-labs-ai:di-revisor-leigo` | real, se o Editor passar só o pacote |
| `passe` | o próprio chat lê o papel e o pacote, grava o laudo antes de abrir outro arquivo | declarada; o laudo diz a limitação |

## Medido

- `claude -p` com `--add-dir` variádico engolia o prompt posicional: o prompt vai por stdin.
- Variáveis `ANTHROPIC_MODEL*` do ambiente são removidas antes do processo do revisor (o modelo vem de `config.yaml: revisor_modelo`, se houver).
- Processo do Diretor com rubrica C1 leva ~4 min; o Leigo em F2, ~1 min.
- mlx-whisper (opcional, Apple Silicon: `requirements-mlx.txt` no venv-corte) transcreve 15 min de bruto em ~1 min; o realinhamento soma ~1 min. Sem ele, faster-whisper em CPU: 1 h de áudio ≈ 20–40 min.
