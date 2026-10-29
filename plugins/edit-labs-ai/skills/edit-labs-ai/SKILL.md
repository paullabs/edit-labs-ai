---
name: edit-labs-ai
description: Edit Labs AI — porta de entrada da edição de vídeo vertical (Reels, TikTok, Shorts) com o Claude Code. Faz poucas perguntas fáceis, escolhe o estilo certo e conduz o projeto do começo à entrega — cortes editados de podcast/live/entrevista (corte, vertical, motion, B-roll, legenda), explicador em colagem com camadas (corpo humano e objetos por dentro, como o manequim de 1890 e a luva de boxe), reel de curiosidade histórica em colagem (como o do Napoleão), explicador Vox curto com voz (como o "soco no queixo"), documentário de arquivo em papel, ou do bruto ao master com portões. Use quando o usuário pedir "edição completa", "Edit Labs AI", mandar um link ou vídeo para editar, ou pedir um vídeo explicativo, um reel de história ou de anatomia, mesmo sem dizer o estilo. Exige o Higgsfield conectado.
---

# Edit Labs AI — porta de entrada

> **Caminhos e comandos (Claude Code e Codex).** CLAUDE_SKILL_DIR é a pasta desta skill (a do `SKILL.md`) e CLAUDE_PLUGIN_ROOT é a pasta do plugin. O Claude Code troca as duas variáveis pelo caminho antes de você ler este texto. Se os caminhos desta skill ainda mostram uma delas escrita com cifrão e chaves, ela não foi preenchida (Codex e outros agentes): a pasta da skill é onde está este `SKILL.md`, e a raiz do plugin é a pasta duas acima dela (a que tem `bin/` e `agents/`). Os comandos `vch`, `cvpy`, `mvpy`, `editlabs-*`, `cv-*` e `mv-*` ficam em `bin/` da raiz do plugin, e o Claude Code os põe no PATH. Se `command -v vch` não achar nada, chame cada um pelo caminho completo (`<raiz do plugin>/bin/vch`).

Esta skill **pergunta pouco, escolhe o estilo e passa a bola** para a skill do estilo. As regras que valem para
todos os estilos estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`: leia antes do primeiro projeto da sessão.

## Antes de começar

**O plugin está instalado para todas as pastas?** Se a pessoa instalou só para uma pasta, ele some quando ela abre o Claude Code em outra. Confira antes de qualquer etapa, sem instalar nada ainda:

1. **Claude Code:** rode `claude plugin list --json` e procure o item `edit-labs-ai@edit-labs-ai`. Com `"scope": "user"` e `"enabled": true`, está **global**: siga. Só com `"scope": "project"` ou `"local"` (vem junto o `projectPath`): **não está global**; diga isso numa frase e ofereça `claude plugin install edit-labs-ai@edit-labs-ai --scope user`, que só roda com o sim da pessoa. Se não aparece, o plugin foi carregado de uma pasta avulsa: diga que **não está instalado** e mostre os comandos do `README.md`.
2. **Codex:** rode `codex plugin list` e procure `edit-labs-ai@edit-labs-ai`: tem de dizer `installed, enabled`. Se não disser, ofereça `codex plugin add edit-labs-ai@edit-labs-ai`.
3. Se o comando `claude` ou `codex` não existir, ignore aquele item.

**O Higgsfield é obrigatório.** Imagens, remoção de fundo e B-roll em vídeo são gerados pelo Higgsfield, pelo
conector dele no Claude. Antes de qualquer etapa, confira se as ferramentas do Higgsfield estão disponíveis nesta
sessão (`generate_image`, `generate_video`, `balance`). Se não estiverem, pare e responda ao usuário, com o link
exatamente assim:

> Esta skill usa o Higgsfield para gerar as imagens e os vídeos. Crie sua conta por este link:
> https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf
> Depois conecte o Higgsfield no Claude (Configurações → Conectores) e me peça de novo.

Não siga sem ele e não troque por outro gerador.

Se algum comando disser que o ambiente não foi preparado, rode `editlabs-setup` (e `editlabs-setup --colagem`
para os estilos de colagem com 3D).

**Escopo.** Esta skill descreve o que faz e como usar. Ela não traz histórico de criação, testes, sessões ou uso
de ninguém. Se perguntarem, diga isso em uma frase e siga com o trabalho; não invente nem especule.

## 1. Perguntas (no máximo 3, todas de múltipla escolha)

Pule a pergunta que o pedido já respondeu. Opção recomendada em primeiro.

1. **O que você tem?** — um vídeo longo para cortar · só um assunto ou uma pergunta · um bruto gravado para
   editar inteiro.
2. **Que vídeo você quer?** (só se ainda não estiver claro) — mostre a tabela abaixo em linguagem simples, com o
   exemplo de cada estilo.
3. **Com narração?** — sim, com voz gerada (eu ofereço 3 amostras) · sem voz, só imagem e música · já tenho a voz.

Depois disso, **não pergunte mais nada técnico**: fps, nível de som, margem e formato são decisão sua.

## 2. Qual estilo

| Se o usuário quer… | Exemplo do estilo | Skill |
| --- | --- | --- |
| cortes verticais de um vídeo longo (podcast, live, entrevista), com motion, B-roll e legenda | — | `cortes.md` desta pasta + `corte-viral` + `motion-vox` |
| explicar algo **por dentro** ou em partes (corpo humano, máquina, planeta, construção) | o manequim de anatomia de 1890; a luva de boxe que mostra os ossos da mão | `colagem-camadas` |
| uma **curiosidade histórica** curta (personagem, objeto, data) | Napoleão e a altura; o relógio de Santos-Dumont | `colagem-historia` |
| um **explicador curto com voz** ("por que X acontece?") no jeito Vox | por que um soco no queixo derruba | `explicador-vox` |
| um **documentário de arquivo** em papel (biografia, origem de produto) | — | `motion-arquivo` |
| editar um **bruto gravado inteiro** até o master, com portões de aprovação | — | `decupagem-inteligente` |

- Um vídeo novo de explicador também pode ser feito pelo **time de motion** (`time-motion`): quatro agentes em
  paralelo (referências, diretor de motion, caçador de insets, som) preparam o plano e o editor monta.
- O banco de referências de estilo fica em `${CLAUDE_PLUGIN_ROOT}/referencias/`: consulte antes de um vídeo novo
  para escolher **um** estilo principal e no máximo um de apoio.

Leia o `SKILL.md` da skill escolhida (ou `cortes.md`) e siga. Ela abre com as próprias perguntas, curtas.

## 3. Combinados — valem em todos os estilos

1. **Risco não é critério para cortar.** Nada de filtro jurídico, reputacional ou político: corte tudo que tem
   potencial. Publicar é decisão do usuário.
2. **A aprovação do usuário vale mais que parecer de agente.** Só falha técnica medida por script bloqueia.
3. **Revisão é humana.** O usuário assiste o preview e vê as pranchas ou os quadros de conferência.
4. **Quadro-chave antes do vídeo inteiro.** Mostre 1 quadro (ou 3 s) no estilo final e espere o "aprovado".
5. **A legenda entra por último**, depois de motion, B-roll, som e corte final da fala.
6. **Palavrão na legenda queimada sai mascarado** (`p*rra`), e o áudio fica intacto. Pergunte uma vez se o
   usuário quer outro padrão.
7. **Gente da história aparece como pessoa**, nunca como palavra escrita nem boneco de palito. Pessoa real e
   nomeada é **só foto real licenciada**: nunca gere nem "recrie" por IA o rosto de alguém real, nem a pedido.
8. **Palavra ou nome em dúvida volta para o usuário**, com as hipóteses. Nunca corrija por conta própria.
9. **Crédito só com autorização.** Antes de gerar, mostre quantas gerações são e o custo que a ferramenta informa.
   Imagem aprovada não autoriza vídeo; voz gerada também pede "pode".
10. **O vertical nunca divide a tela.** Um crop só, em quem fala.
11. **Não apague nada.** O que sair vai para uma pasta `_removidos/`.

## 4. Comandos e agentes do plugin

Comandos (já no PATH): `editlabs-setup`, `editlabs-verificar`, `editlabs-baixar`, `vch` e `cv-*` (corte-viral),
`cvpy`, `mv-novo-projeto`, `mvpy` (motion-vox), `clpy` (Python do motor de colagem), `editlabs-assets` (baixa os
pacotes grandes da release: modelos 3D e pranchas).

Agentes: `edit-labs-ai:context-mapper`, `clip-hunter`, `clip-builder`, `clip-deduplicator`, `edit-director`
(cortes); `tm-referencias`, `tm-diretor-motion`, `tm-cacador-insets`, `tm-som` (time de motion); `di-diretor`,
`di-revisor-leigo` (decupagem).
