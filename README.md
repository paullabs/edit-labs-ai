# Edit Labs AI — plugin para o Claude Code

Do link de um podcast ao vertical pronto para Reels, TikTok e Shorts: corte, enquadramento, motion design,
B-roll em vídeo, legenda queimada e verificação. O Claude Code faz o trabalho; você decide nos portões.

## Antes de instalar: Higgsfield

O plugin **exige uma conta no Higgsfield** conectada ao Claude: é por ela que saem as imagens, a remoção de fundo
e os B-rolls em vídeo. Crie a sua por este link:

**https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf**

Depois conecte o Higgsfield no Claude: claude.ai → Configurações → Conectores.

## Instalar (uma vez por computador)

**1. Programas** (Mac, com Homebrew):

```bash
brew install ffmpeg yt-dlp deno python@3.12
```

**2. O plugin**, dentro do Claude Code (o repositório é público: não precisa de conta no GitHub):

```
/plugin marketplace add paullabs/edit-labs-ai
/plugin install edit-labs-ai@edit-labs-ai
```

Pelo terminal: `claude plugin marketplace add paullabs/edit-labs-ai` e `claude plugin install edit-labs-ai@edit-labs-ai`.
Sem GitHub, a partir de uma pasta com este repositório: `/plugin marketplace add /caminho/para/a/pasta`.

**3. Reinicie o Claude Code** e peça: *"roda o editlabs-setup"*. Ele confere os programas, cria os ambientes
Python em `~/.local/share/edit-labs-ai/`, fora do plugin para sobreviverem às atualizações, e verifica tudo.

**4. Confira o Higgsfield**: o Claude checa o conector no começo de cada projeto e, se ele não estiver ligado,
para e manda o link acima.

## Usar

Abra o Claude Code numa pasta vazia e peça, um por vez:

1. "Baixa esse vídeo para a pasta do projeto: [link]"
2. "Acha os melhores momentos" → **você escolhe**
3. "Corta os momentos 1, 9 e 15" → **você assiste o preview e aprova**
4. "Faz o vertical dos três"
5. "Faz a motion dos clipes aprovados" → **você autoriza os créditos e aprova as pranchas**
6. "Coloca B-roll nos clipes" → **você aprova as imagens e autoriza os vídeos**
7. "Renderiza, verifica e entrega" → **você assiste e publica**

Detalhes e combinados: `plugins/edit-labs-ai/README.md`.

## Atualizar e remover

- Atualizar: `/plugin update edit-labs-ai@edit-labs-ai` e reinicie. Os ambientes Python e a biblioteca de assets
  ficam em `~/.local/share/edit-labs-ai/` e não se perdem.
- Remover: `/plugin uninstall edit-labs-ai@edit-labs-ai`. Para apagar também os ambientes:
  `rm -rf ~/.local/share/edit-labs-ai`.
