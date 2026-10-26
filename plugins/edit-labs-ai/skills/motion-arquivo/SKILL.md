---
name: motion-arquivo
description: >-
  Edita um vídeo narrado no estilo "documentário de arquivo em papel" (Família A, medido quadro a quadro num reel
  sobre Hedy Lamarr): o quadro anda a 10 qps, a câmera nunca para (deriva lenta, revelação que assenta no sujeito,
  chicote de saída), cada palavra dita vira um evento na tela (palavra serifada no papel, gancho digitado letra a
  letra, caixas de interface, odômetro, folha que amassa) e o corte se esconde no movimento. Cobre o projeto inteiro:
  voz e batidas ancoradas na fala, um plano por batida a partir de um catálogo de tipos, assets reais primeiro
  (ícone do app instalado, cursor do sistema, acervo licenciado, print do site), geração no Higgsfield só do que
  falta, trípticos com laudo do Diretor, som e render. Use para "estilo documentário de arquivo", "família A",
  "história escondida", "aplica esse padrão de edição nesse roteiro/narração", reels de curiosidade, origem de
  produto, biografia, história, ciência, dinheiro ou saúde, e para reproduzir uma referência desse tipo com a mesma
  régua. NÃO use para talking head com legenda (motion-vox), corte de podcast (corte-viral) nem explicador em camadas
  de colagem (colagem-camadas).
---

# Documentário de arquivo em papel — Família A

> **Um documentário de arquivo que anda a 10 quadros por segundo, em que a câmera nunca para, cada palavra dita
> vira um evento na tela e o corte se esconde no movimento.**

As regras de produção comuns (perguntas fáceis, ordem da produção, margem do Reels, material real, "pode" antes de
gastar crédito, som) estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`. Leia antes. Aqui fica só o que é deste estilo.

Seis entregas em sequência. As que têm 👤 terminam num **portão**: mostre, pare e faça uma pergunta. Só emende
tudo numa run quando o usuário pedir ("vai até o fim").

| # | Entrega | O que sai | Leia |
| --- | --- | --- | --- |
| **0** | PROJETO 👤 | pasta, voz e brief | `fases/0-projeto.md` |
| **1** | VOZ | palavra a palavra + batidas na grade | `fases/1-voz.md` |
| **2** | PLANO 👤 | `plano.json` + lista de assets com origem e custo | `fases/2-plano.md` |
| **3** | ASSETS | reais → acervo → gerados → prontos + `FONTES.md` | `fases/3-assets.md` |
| **4** | CENAS 👤 | trípticos + laudo do Diretor | `fases/4-cenas.md` |
| **5** | RENDER | som, mp4 e laudo final (+ régua, se houver referência); **legenda por último** | `fases/5-render.md` |

> Leia só a fase em que você está. Para planejar, `referencias/gramatica.md` (o porquê do movimento) e
> `referencias/planos.md` (o catálogo) bastam.

## Perguntas do começo (múltipla escolha, no máximo 4)

1. **O que você tem?** a) a narração gravada · b) o roteiro em texto (precisa de voz) · c) um vídeo com fala ·
   d) um vídeo de referência para reproduzir.
2. **Para onde vai?** a) Reels/TikTok/Shorts 9:16 (recomendado) · b) outro.
3. **Gerar imagem no Higgsfield está liberado?** a) sim, com a lista e o custo antes (recomendado) · b) só material
   real e o que o motor desenha.
4. **Som:** a) a minha pasta de efeitos e músicas (me diga onde) · b) só os sons sintetizados do plugin.

O resto (fps, grade, níveis, margens) é decisão técnica: não pergunte.

## As quatro regras que decidem se funciona

**1. Três camadas de movimento ao mesmo tempo, em todo plano.** A câmera anda o plano inteiro (deriva de 2–8%,
revelação que abre 1,5–2,4× → 1× em torno do sujeito, ou chicote); um evento preso à fala acontece a cada
0,2–0,6 s; e tudo é amostrado a 10 qps. Plano sem uma das três fica parado ou liso demais — e deixa de ser este
estilo.

**2. Literal: uma batida, um objeto que a fala nomeia.** "Ninguém percebeu" é uma multidão de costas; "foi
recusada" é a folha indo para o lixo; "no seu bolso" é o celular subindo. Conceito abstrato vira objeto antes de
virar plano (`gramatica.md` §9 tem o mapa).

**3. Real primeiro.** O que existe no mundo vem do mundo: ícone do app instalado, cursor do sistema, documento,
foto licenciada, print do site. O motor desenha só o que é do estilo (texto, caixa, seta, anel, odômetro, papel,
onda). Gerar no Higgsfield só o que falta — com lista e custo antes — e nunca rosto de pessoa real
(`referencias/assets.md`).

**4. Texto no meio, nada embaixo da interface.** Texto em y 560–1360, fora da coluna de botões e do pé da tela
(`familia_a.ZONA`), dentro da margem do `REGRAS.md`. `ferramentas/zona_segura.py` confere todo texto antes da
entrega. Explicação vira desenho por cima da imagem (`motor/desenho.py`), não frase.

**A legenda entra por último.** A `legenda` global do `plano.json` (a frase falada com a palavra acesa) só é
escrita depois de planos, assets, desenhos e som fechados, e é opcional: nos planos de palavra no papel a própria
palavra já é a legenda (`sem_legenda`).

## Onde está cada coisa

```
motor/familia_a/         as seis camadas: tempo, fundo, letras, estilo, filtro, movimentos, curvas
motor/planos.py          os tipos de plano do arquivo em papel (TIPO(n, plano, ctx) -> quadro)
motor/planos_noticia.py  a notícia explicada (ranking, celular, centena, semana, botão de seguir...)
motor/planos_galeria.py  a galeria documental (moldura que entra, sujeito em cor com texto atrás, etiqueta
                         rasgada, jornais na mesa)
motor/planos_objeto.py   objeto real em ação (salto, de cabeça, ventilador, jatos)
motor/planos_video.py    vídeo real ou gerado na grade (recorte 9:16, congela) e a tela dividida
motor/planos_desenho.py  linha do tempo (promessa x realidade)
motor/desenho.py         telestração: o desenho que explica por cima de qualquer plano
motor/projeto.py         plano.json -> cena que o render entende
motor/som.py             efeitos e trilhas sintetizados (reserva, sem crédito, redistribuíveis)
motor/kit/               moldura dourada (com furo), papel amassado, sfx/ sintetizados, som_*.modelo.json
motor/fontes/            Instrument Serif e Inter (OFL, com as licenças)
ferramentas/             transcrever · batidas · assets_locais · buscar_assets · baixar_asset · melhorar ·
                         triptico · render · mixar · som_biblioteca · catalogar_efeitos · catalogar_trilhas ·
                         compor_trilha · prova_efeitos · ouvir_trilha · recorte.swift · pdf_png.swift · comparar ·
                         montar_entrega · cenas_iguais · zona_segura · folha_quadros
referencias/             gramatica · planos · assets · texto · som · armadilhas · rubricas-diretor · medir-referencia
exemplo/                 hedy/ (estudo de medida de uma referência) e plano_teste_pipeline.json (o formato mínimo)
```

Rode as ferramentas com `mvpy` (o Python do ambiente da motion-vox, que já tem o `faster_whisper` da transcrição):
`mvpy ${CLAUDE_SKILL_DIR}/ferramentas/<script>.py ...`. Elas acham o motor sozinhas. O projeto do usuário fica na pasta onde ele abriu o Claude Code.

## Som do usuário

O plugin não traz efeitos nem músicas de terceiros. Com uma pasta de sons própria:

```bash
export EDITLABS_SONS="<pasta de efeitos do usuário>"
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/som_biblioteca.py          # mapa em $EDITLABS_DATA/motion-arquivo/
```

Sem pasta, o `mixar.py` usa os 13 efeitos sintetizados de `motor/som.py` e os pads/camas compostos em código.
Detalhes em `referencias/som.md`.

## Requisitos

Dependências em `requirements.txt` (o `editlabs-setup` instala). Rode `mvpy ${CLAUDE_SKILL_DIR}/verificar.py` antes do primeiro
projeto: confere bibliotecas, ffmpeg, swift, fontes, kit e renderiza um quadro de cada tipo. A grotesca do gancho é
a Arial Bold do sistema (macOS/Windows) ou a Liberation Sans Bold (Linux, mesma métrica); sem nenhuma, o gancho cai
na Inter 800. Nenhuma fonte de sistema vai no pacote. Instalação manual: `INSTALAR.md`.

## Armadilhas

`referencias/armadilhas.md` — as que custaram tempo de verdade na reprodução medida (medir depois da compressão,
fundo "preto" com textura, fonte de olho, asset desenhado quando existe o real, âncora pela tinta, fade fixo). Leia
antes da fase 2.

## Referências estudadas (crédito; nenhuma mídia delas vem no plugin)

- Família A: um reel curto sobre Hedy Lamarr e a invenção do salto de frequência (medido quadro a quadro como
  estudo de medida; os direitos do vídeo são do autor original).
- Galeria documental: a abertura do vídeo "Netflix In 2022", do canal "Viral Instagram Growth Tips".
- Explicador claro e preto com régua: os vídeos "Priming" e "Outreach", usados só como régua de look e de som.

As medidas viraram números no código; vídeos, quadros e áudio dessas referências nunca entram no plugin. Para
reproduzir uma referência nova, o vídeo fica na pasta do projeto do usuário (`referencias/medir-referencia.md`).
