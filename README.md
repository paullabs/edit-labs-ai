# Edit Labs AI — plugin para o Claude Code

Vídeo vertical pronto para Reels, TikTok e Shorts, em vários estilos: **cortes editados de podcast** (corte,
enquadramento, motion, B-roll, legenda), **explicador em colagem com camadas** (corpo humano e objetos por
dentro), **curiosidade histórica** em colagem, **explicador Vox** com voz, **documentário de arquivo** e
**decupagem do bruto ao master**. O Claude Code faz o trabalho, pergunta pouco e você decide nos portões.

Roda no **Mac, no Windows e no Linux**, e **não exige assinatura de nenhum serviço**.

## Gerador de imagem e de vídeo: opcional

Nenhuma conta é necessária. O plugin trabalha com foto real licenciada (Wikimedia Commons, NASA, Smithsonian,
Pexels…), com as imagens que você mandar, com recorte local e com cenas em código. **Se** a sua sessão do Claude já
tiver um gerador de imagem ou de vídeo conectado (Higgsfield, OpenArt ou outro), o Claude o usa para o que faltar,
mostrando o custo antes e esperando o seu "pode". Sem gerador, ele lista o que faltaria ("O que falta") e segue.

Opcional, para quem quiser gerar dentro do Claude: Higgsfield, em
https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf (Claude → Configurações → Conectores).

## Instalar (uma vez por computador)

**1. Programas.** O plugin precisa de `ffmpeg`, `yt-dlp`, `deno` e Python 3.10–3.12.

| Sistema | Comando |
| --- | --- |
| **Mac** (Homebrew) | `brew install ffmpeg yt-dlp deno python@3.12` |
| **Windows** (PowerShell) | `winget install Git.Git Python.Python.3.12 Gyan.FFmpeg yt-dlp.yt-dlp DenoLand.Deno` |
| **Linux** (Debian/Ubuntu) | `sudo apt install ffmpeg python3.12 python3.12-venv` · `pipx install yt-dlp` · deno: https://deno.com |

No Windows, o Claude Code usa o **Git Bash** (vem com o Git for Windows): é nele que os comandos do plugin
rodam. Depois de instalar, **feche e abra o Claude Code de novo** para o PATH novo valer. Detalhes e problemas
comuns: `plugins/edit-labs-ai/docs/WINDOWS.md`.

**2. O plugin**, dentro do Claude Code (o repositório é público: não precisa de conta no GitHub):

```
/plugin marketplace add paullabs/edit-labs-ai
/plugin install edit-labs-ai@edit-labs-ai
```

Pelo terminal: `claude plugin marketplace add paullabs/edit-labs-ai` e `claude plugin install edit-labs-ai@edit-labs-ai --scope user`.
Se o Claude perguntar o escopo, escolha o de usuário (`user`): é o que vale para todas as suas pastas. Para conferir, `claude plugin list` tem de mostrar `Scope: user`. Se mostrar `project` ou `local`, o plugin só vale naquela pasta: rode o `install` de novo com `--scope user`.
No Codex: `codex plugin marketplace add paullabs/edit-labs-ai` e `codex plugin add edit-labs-ai@edit-labs-ai`; `codex plugin list` tem de mostrar `installed, enabled`. Os subagentes do plugin (`edit-labs-ai:context-mapper` e os outros) são do Claude Code.
Sem GitHub, a partir de uma pasta com este repositório: `/plugin marketplace add /caminho/para/a/pasta` (no Windows, `C:/caminho/para/a/pasta`).

**3. Reinicie o Claude Code** e peça: *"roda o editlabs-setup"* (para os estilos de colagem e o explicador Vox:
*"roda o editlabs-setup --colagem"*; para recortar imagens sem assinatura em qualquer sistema: acrescente
`--recorte`). Ele confere os programas, cria os ambientes Python em `~/.local/share/edit-labs-ai/` (no Windows,
`C:\Users\<você>\.local\share\edit-labs-ai\`), fora do plugin para sobreviverem às atualizações, e verifica tudo.

## Usar

Abra o Claude Code numa pasta vazia e diga que vídeo quer: a porta de entrada (`edit-labs-ai`) pergunta o mínimo
e escolhe o estilo. Os estilos e as regras estão em `plugins/edit-labs-ai/README.md` e `plugins/edit-labs-ai/REGRAS.md`.

Para cortes de um vídeo longo, peça, um por vez:

1. "Baixa esse vídeo para a pasta do projeto: [link]"
2. "Acha os melhores momentos" → **você escolhe**
3. "Corta os momentos 1, 9 e 15" → **você assiste o preview e aprova**
4. "Faz o vertical dos três"
5. "Faz a motion dos clipes aprovados" → **você aprova as pranchas** (e, se houver gerador, autoriza os créditos)
6. "Coloca B-roll nos clipes" → **você aprova as imagens** (B-roll em vídeo só com gerador de vídeo ou vídeo livre)
7. "Renderiza, verifica e entrega" → **você assiste e publica**

Detalhes e combinados: `plugins/edit-labs-ai/README.md`.

## Atualizar e remover

- Atualizar: `/plugin update edit-labs-ai@edit-labs-ai` e reinicie. Os ambientes Python e a biblioteca de assets
  ficam em `~/.local/share/edit-labs-ai/` e não se perdem.
- Remover: `/plugin uninstall edit-labs-ai@edit-labs-ai`. Para apagar também os ambientes:
  `rm -rf ~/.local/share/edit-labs-ai` (no Git Bash do Windows, o mesmo comando serve).
