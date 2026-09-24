# Instalação (plugin `edit-labs-ai`)

Esta skill vem dentro do plugin `edit-labs-ai`. Não copie nada para `~/.claude/`:

1. No Claude Code: `/plugin marketplace add <repositório ou pasta do marketplace>` e `/plugin install edit-labs-ai@edit-labs-ai`.
2. Reinicie o Claude Code.
3. Peça ao Claude: "roda o editlabs-setup". Ele confere ffmpeg, yt-dlp, Deno e Python 3.10–3.12, cria os ambientes
   Python em `~/.local/share/edit-labs-ai/` (fora do plugin, para sobreviver a atualizações) e verifica tudo.

Comandos do plugin (no PATH do Claude): `vch` (este motor), `cvpy` (o Python deste ambiente), `cv-checar-cortes`,
`cv-ajustar-cortes`, `cv-testar-borda`, `cv-respiro`, `cv-preview`, `cv-retranscrever`, `editlabs-verificar`.

O `ffmpeg` sem libass só impede queimar legenda aqui — o padrão (vertical limpo → motion-vox) não é afetado.
