# Edit Labs AI — edição completa com o Claude Code

Do link de um podcast ao vertical pronto para Reels, TikTok e Shorts: corte, enquadramento, motion design,
B-roll em vídeo, legenda queimada e verificação. O Claude Code faz o trabalho; você decide nos portões.

O roadmap do processo está em `docs/roadmap.md` e o desenho em `docs/roadmap-processo.excalidraw` (abra em
excalidraw.com → Abrir).

## Requisito: Higgsfield

O plugin exige o Higgsfield conectado ao Claude (claude.ai → Configurações → Conectores): imagens, remoção de fundo
e B-roll em vídeo saem dele. Sem conta? Crie por este link:
**https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf**

O Claude confere o conector no começo de cada projeto e, se ele não estiver ligado, para e manda esse link.

## O que vem no plugin

| Peça | O que é |
| --- | --- |
| skill `edit-labs-ai` | **a que você usa**: a ordem das 7 tasks, as travas, os combinados |
| skill `corte-viral` | motor dos cortes: transcrição, momentos, cortes, vertical |
| skill `motion-vox` | motor da motion: kit visual (16 objetos, fontes livres), cenas, B-roll, legenda, render, verificação |
| 5 agentes | `edit-labs-ai:context-mapper`, `edit-labs-ai:clip-hunter`, `edit-labs-ai:clip-builder`, `edit-labs-ai:clip-deduplicator`, `edit-labs-ai:edit-director` |
| comandos (`bin/`, no PATH do Claude) | `editlabs-setup`, `editlabs-verificar`, `editlabs-baixar`, `vch`, `cv-checar-cortes`, `cv-ajustar-cortes`, `cv-testar-borda`, `cv-respiro`, `cv-preview`, `cv-retranscrever`, `cv-conferir-qr`, `cv-desdividir`, `cvpy`, `mv-novo-projeto`, `mvpy` |

A revisão é sua: o plugin não usa revisor de IA no meio do processo.

## Instalar

Ver o `README.md` da raiz do marketplace: conta no Higgsfield → `brew install ffmpeg yt-dlp deno python@3.12` →
`/plugin marketplace add …` → `/plugin install edit-labs-ai@edit-labs-ai` → reiniciar → *"roda o editlabs-setup"* →
conectar o Higgsfield.

## Usar: sete pedidos, cinco decisões

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

## Referências visuais

Referências visuais de terceiros (quadros da Vox e de outros criadores) não vêm no plugin. Monte as suas: ver
`skills/motion-vox/referencias/REFERENCIAS-VISUAIS.md`, seção "Monte as suas referências".

## Se der problema

| Sintoma | Causa provável | Saída |
| --- | --- | --- |
| o Claude para e manda o link do Higgsfield | o conector do Higgsfield não está ligado nesta sessão | crie a conta pelo link, conecte em Configurações → Conectores e peça de novo |
| "O ambiente do Edit Labs AI ainda não foi preparado" | falta rodar o setup neste computador | peça "roda o editlabs-setup" |
| o Claude não acha `vch`, `mvpy`… | plugin desativado ou Claude Code não reiniciado | `/plugin` → ative `edit-labs-ai`; reinicie |
| yt-dlp não baixa do YouTube | falta o Deno, ou o yt-dlp está velho | `brew install deno` · `brew upgrade yt-dlp` |
| pip falha no numpy | só há Python 3.13+ | `brew install python@3.12` e `editlabs-setup --refazer` |
| legenda sem palavras no começo ou no fim de um trecho | projeto criado com uma versão anterior do motor | `mv-novo-projeto . --forcar` na pasta do projeto |
