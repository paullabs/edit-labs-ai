# Edit Labs AI — edição de vídeo vertical com o Claude Code

Vídeo vertical pronto para Reels, TikTok e Shorts, em vários estilos: cortes editados de podcast, explicadores em
colagem com camadas, curiosidades históricas, explicador Vox com voz, documentário de arquivo e decupagem do bruto
ao master. O Claude Code faz o trabalho; você decide nos portões.

**Comece pela porta de entrada:** peça *"quero fazer um vídeo"* (ou `/edit-labs-ai:edit-labs-ai`). O Claude faz
no máximo 3 perguntas de múltipla escolha e escolhe o estilo. As regras que valem para todos os estilos estão em
`REGRAS.md`: poucas perguntas e fáceis, **um quadro aprovado antes do vídeo inteiro** e **a legenda sempre por
último**.

O roadmap do processo está em `docs/roadmap.md` e o desenho em `docs/roadmap-processo.excalidraw` (abra em
excalidraw.com → Abrir).

## Requisito: Higgsfield

O plugin exige o Higgsfield conectado ao Claude (claude.ai → Configurações → Conectores): imagens, remoção de fundo
e B-roll em vídeo saem dele. Sem conta? Crie por este link:
**https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf**

O Claude confere o conector no começo de cada projeto e, se ele não estiver ligado, para e manda esse link.

## Os estilos

| Estilo | Exemplo | Skill |
| --- | --- | --- |
| Cortes de vídeo longo (podcast, live, entrevista): corte, vertical, motion, B-roll, legenda | — | `edit-labs-ai` (`cortes.md`) + `corte-viral` + `motion-vox` |
| Explicador em colagem com **camadas registradas** (o que tem por dentro) | o manequim de anatomia de 1890; a luva de boxe que mostra os ossos da mão; o crânio | `colagem-camadas` |
| Curiosidade **histórica** em colagem de papel, com caneta que mede e traça rotas | Napoleão e a altura; Santos-Dumont e o relógio | `colagem-historia` |
| **Explicador Vox** curto com voz, montado no invideo ou renderizado local | por que um soco no queixo derruba | `explicador-vox` |
| **Documentário de arquivo** em papel | — | `motion-arquivo` |
| Do **bruto ao master** com fases e portões | — | `decupagem-inteligente` |
| **Time de motion**: 4 agentes em paralelo preparam o plano de um vídeo novo | — | `time-motion` |

## O que vem no plugin

| Peça | O que é |
| --- | --- |
| skill `edit-labs-ai` | **a porta de entrada**: perguntas, escolha do estilo, combinados; `cortes.md` é o estilo de cortes |
| `REGRAS.md` | regras de produção comuns a todos os estilos |
| skills de estilo | `corte-viral`, `motion-vox`, `colagem-camadas`, `colagem-historia`, `explicador-vox`, `motion-arquivo`, `decupagem-inteligente`, `time-motion` |
| `motor/colagem/` | motor de colagem compartilhado: camadas com chaves, câmera sobre o mundo, boil, traço de caneta, mecânicas (levanta, janela, descasca, aba, explode, giro 3D a 7 qps), conferências e som sintetizado |
| `referencias/` | banco de referências de estilo: catálogo com link e licença, fichas de estilo, paletas medidas, análises e a ferramenta `refs.py` (sem mídia de terceiros) |
| 11 agentes | cortes: `context-mapper`, `clip-hunter`, `clip-builder`, `clip-deduplicator`, `edit-director`; time de motion: `tm-referencias`, `tm-diretor-motion`, `tm-cacador-insets`, `tm-som`; decupagem: `di-diretor`, `di-revisor-leigo` (todos com o prefixo `edit-labs-ai:`) |
| comandos (`bin/`, no PATH do Claude) | `editlabs-setup`, `editlabs-verificar`, `editlabs-baixar`, `editlabs-assets`, `vch`, `cv-*`, `cvpy`, `mv-novo-projeto`, `mvpy`, `clpy`, `di` |
| release `assets-v2` | pacotes grandes baixados sob demanda com `editlabs-assets`: pranchas antigas (domínio público), camadas 3D do Z-Anatomy (CC BY-SA 4.0) e BodyParts3D (CC BY-SA 2.1 JP) |

A revisão é sua: o plugin não usa revisor de IA no meio do processo.

## Instalar

Ver o `README.md` da raiz do marketplace: conta no Higgsfield → `brew install ffmpeg yt-dlp deno python@3.12` →
`/plugin marketplace add …` → `/plugin install edit-labs-ai@edit-labs-ai` → reiniciar → *"roda o editlabs-setup"* →
conectar o Higgsfield.

Para os estilos de colagem e o explicador Vox, rode também `editlabs-setup --colagem` (cria o ambiente do motor;
o Blender só é preciso para modelos 3D próprios).

## Usar o estilo de cortes: sete pedidos, cinco decisões

Abra o Claude Code numa **pasta vazia** (vai ser a pasta do projeto) e peça, um por vez:

| # | Você diz | O Claude faz | Você decide |
| --- | --- | --- | --- |
| 1 | "Baixa esse vídeo para a pasta do projeto: [link]" | consulta, baixa vídeo + legenda + metadados, confere | |
| 2 | "Acha os melhores momentos" (ou `/edit-labs-ai:edit-labs-ai`) | prepara a transcrição, roda os agentes, escreve `MOMENTOS.md` | **escolhe os números** |
| 3 | "Corta os momentos 1, 9 e 15" | monta os cortes, confere cada borda pelo ouvido, tira as pausas, gera o preview | **assiste e aprova** |
| 4 | "Faz o vertical dos três" | enquadra pelo rosto de quem fala (nunca divide a tela), confere se não entrou QR da transmissão, renderiza e verifica | |
| 5 | "Faz a motion dos clipes aprovados" | planeja, busca fotos reais, mostra o custo, gera, compõe, mede, mostra as pranchas | **autoriza os créditos e aprova as pranchas** |
| 6 | "Coloca B-roll nos clipes" | planeja os B-rolls, gera as imagens de partida, propõe os vídeos com o custo, gera, revisa cada vídeo e monta | **aprova as imagens e autoriza os vídeos** |
| 7 | "Renderiza, verifica e entrega" | legenda, render, verificação de sincronia e áudio, entrega com créditos | **assiste e publica** |

## Os combinados (o Claude já segue)

- Risco não é critério para cortar: o Claude corta tudo que tem potencial, e publicar é decisão sua.
- Sua aprovação vale mais que parecer de agente. Só falha técnica medida bloqueia.
- Revisão é humana: nenhum revisor de IA no meio.
- Palavrão na legenda sai mascarado (*p\*rra*); o áudio fica intacto.
- Gente da história aparece como **pessoa**. Anônima = pessoa fictícia gerada. Real e nomeada = só foto real
  licenciada. Rosto real nunca é gerado por IA. No B-roll, ninguém tem o rosto identificável.
- Palavra ou nome em dúvida volta para você, com as hipóteses.
- O vertical nunca divide a tela.
- Crédito só com autorização, com o custo informado antes. Imagem aprovada não autoriza vídeo.
- Prancha antes de render. Nada é apagado.

## Publicar

- Foto CC BY-SA exige atribuição na descrição: o `CREDITOS.md` de cada entrega traz a linha pronta.
- Pessoa gerada realista e B-roll gerado pedem o selo de "conteúdo gerado por IA" da plataforma: o `CREDITOS.md`
  lista o que foi gerado.

## Usar os outros estilos

Abra o Claude Code numa pasta vazia e diga o que quer ("um vídeo explicando o que tem dentro de um joelho", "um
reel sobre a altura do Napoleão", "por que a gente boceja, no estilo Vox"). O Claude pergunta o mínimo, mostra
**um quadro-chave** no estilo para você aprovar, monta, mostra os quadros de conferência e só então gera o vídeo,
o som e, por último, a legenda e os créditos. Voz e geração de imagem pedem o seu "pode", com o custo antes.

## Referências visuais

O banco em `referencias/` traz, de cada referência, título, autor, link, licença declarada e a nossa análise.
Imagens, vídeos e áudios de terceiros **não vêm no plugin**: abra o link. Para montar as suas, ver
`referencias/LEIA.md` e `skills/motion-vox/referencias/REFERENCIAS-VISUAIS.md`.

## Licenças dos assets

Fontes OFL/Apache com a licença ao lado; papel e pranchas em domínio público; modelos 3D CC0, CC BY e CC BY-SA
com crédito (cada pasta tem um `CREDITOS.md`; cada pacote da release, um `LEIA.md`). Efeitos sonoros do plugin
são sintetizados em código. Músicas e efeitos de bancos que proíbem redistribuir não vêm junto: use os seus.

## Se der problema

| Sintoma | Causa provável | Saída |
| --- | --- | --- |
| o Claude para e manda o link do Higgsfield | o conector do Higgsfield não está ligado nesta sessão | crie a conta pelo link, conecte em Configurações → Conectores e peça de novo |
| "O ambiente do Edit Labs AI ainda não foi preparado" | falta rodar o setup neste computador | peça "roda o editlabs-setup" |
| o Claude não acha `vch`, `mvpy`… | plugin desativado ou Claude Code não reiniciado | `/plugin` → ative `edit-labs-ai`; reinicie |
| yt-dlp não baixa do YouTube | falta o Deno, ou o yt-dlp está velho | `brew install deno` · `brew upgrade yt-dlp` |
| pip falha no numpy | só há Python 3.13+ | `brew install python@3.12` e `editlabs-setup --refazer` |
| "O motor de colagem ainda não foi preparado" | falta o ambiente da colagem | `editlabs-setup --colagem` |
| um exemplo de colagem avisa que falta pacote | pranchas ou modelos 3D não baixados | `editlabs-assets` lista; `editlabs-assets colagem-pranchas` baixa (com o seu "pode") |
| legenda sem palavras no começo ou no fim de um trecho | projeto criado com uma versão anterior do motor | `mv-novo-projeto . --forcar` na pasta do projeto |
