---
name: explicador-vox
description: Explicador curto no estilo Vox (30, 45 ou 60 s, 9:16) que responde "por que" ou "como acontece" com voz narrada — colagem de papel, um mundo maior que a tela filmado por uma câmera, desenho a 12 qps num relógio de 24, um único acento saturado, o fundo que troca de papel creme para carvão no momento da ação, legenda nativa sóbria e efeitos 15–19 dB abaixo da voz. Sai como timeline editável no invideo (faixas organizadas, chaves editáveis) e também como render local. O exemplo é o "soco no queixo" (por que um soco no queixo derruba). Use para "explicador estilo Vox", "por que X acontece em 30 segundos", "vídeo explicativo com narração", "mecanismo em motion", "monta no invideo", "no estilo do soco no queixo", e para continuar ou ajustar um desses. Não use para explicar algo por dentro em camadas que se descascam (colagem-camadas), reel de curiosidade histórica sem voz (colagem-historia), documentário de arquivo (motion-arquivo) nem motion sobre talking head (motion-vox).
---

# Explicador Vox — uma pergunta, um mecanismo, 30 segundos

Um explicador curto que mostra **a coisa acontecendo**: o objeto real entra, a força age, a consequência aparece, e
a conclusão fecha numa frase. Tudo é motion; não há rosto nem filmagem própria.

As regras comuns de produção estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md` (perguntas, ordem, margem, material, som,
crédito). **Leia antes de começar.** Aqui fica só o que é deste estilo.

| arquivo | quando ler |
| --- | --- |
| `${CLAUDE_SKILL_DIR}/referencias/regua.md` | antes do plano: os números medidos da referência e os sinais de amador |
| `${CLAUDE_SKILL_DIR}/referencias/plano-exemplo.md` | para ver um plano de batidas completo (o soco no queixo) |
| `${CLAUDE_SKILL_DIR}/referencias/invideo.md` | antes de montar no invideo |
| `${CLAUDE_SKILL_DIR}/exemplo/` | plano, transcrição e peças prontas do exemplo; `CREDITOS.md` |
| `${CLAUDE_PLUGIN_ROOT}/referencias/` | banco de referências de estilo, se o usuário quiser variar |

## O estilo em 10 regras

1. **Uma cadeia causal, um eixo.** Entrada → objeto → reação → saída, um elemento de cada vez. No 9:16, no máximo
   **2 elementos que agem por quadro** fora a legenda; o objeto feito de partes conta 1.
2. **Partes no papel, ação no escuro.** Apresente no papel creme `#DEDBCB`; no momento da ação o fundo escurece
   para carvão `#232325` com vinheta (em ~30 quadros). Grade em losango só quando dá escala ou medida.
3. **Um acento saturado só**, na ação (no exemplo, o vermelho da luva). Se voltar, volta na mesma cor.
4. **Mundo maior que a tela + câmera.** Os objetos vivem num mundo; a câmera fica **parada durante a ação** e só
   anda como beat com início e fim: empurrão (~12–20 quadros), aproximação, volta, mergulho para "dentro".
5. **12 qps sobre 24.** Todo movimento (camadas e câmera) anda em degraus de 2 quadros; toda chave em quadro par.
   Boil mínimo (≤ 1 px), grão e RGB leves no acabamento.
6. **A imagem chega um pouco antes da palavra** (−0,18 s; nunca mais de +0,27 s depois).
7. **Entradas curtas que pousam:** pequeno 6–10 quadros, herói 30–40 com ease-out, saída 10. Sem bounce, sem letra
   a letra, sem tremor no impacto. O flash fica para a consequência.
8. **Legível depois de pronto:** cada estado fica ≥ 1,2 s antes do próximo; o último também (cauda de ~1 s depois
   da voz).
9. **Material real:** objeto e pessoa como coisa de verdade (foto recortada, gravura, objeto gerado), nunca ícone ou
   círculo vazio. Fonte documental como **citação tipografada** num cartão, não print da página.
10. **Texto mínimo:** um título de 1–3 palavras no fim (maiúscula 66–69 px, y 600–1000, fade de 6 quadros) e a
    legenda. No máximo 2 tamanhos de texto no vídeo.

Neste estilo, duas coisas diferem das regras comuns, de propósito: a **legenda nativa faz parte do estilo** (o
`REGRAS.md` §3 tira a legenda do explicador em camadas; aqui ela é sóbria, frase por frase, e pode ser desligada se o
usuário preferir), e a **câmera não deriva** (fica parada na ação e anda só em beats, como mede a régua).

## Perguntas (no começo, todas de múltipla escolha)

Faça no máximo estas quatro, juntas, com a recomendada em primeiro e um "outro" livre:

1. **Qual a pergunta do vídeo?** Ofereça 3 formulações curtas de "Por que…/Como…" a partir do que o usuário
   disse, mais "outra".
2. **Duração:** 30 s (recomendado: ~65 palavras, uma consequência) · 45 s · 60 s.
3. **Saída:** montar no invideo como timeline editável (recomendado, se o conector do invideo estiver ligado) ·
   renderizar aqui (MP4 local) · os dois.
4. **Voz:** gere **3 amostras** curtas (a primeira frase do roteiro) em vozes diferentes e deixe escolher; ou "tenho
   a minha voz/arquivo". Gerar voz gasta crédito: mostre o custo e espere o "pode".

Tudo o mais (fps, cores, nível de som, margem, tamanhos) é decisão sua, pela régua.

## Fluxo: o time de motion

Se a skill `time-motion` e os agentes `tm-*` do plugin estiverem disponíveis, rode os quatro primeiros papéis em
paralelo (Referências, Diretor de Motion, Caçador de Insets, Som); senão, faça os mesmos passos aqui, em ordem.
Cada passo termina num arquivo na pasta do projeto (`time/`).

| # | passo | entrega | portão |
| --- | --- | --- | --- |
| 1 | **Roteiro** com fontes: pergunta, mecanismo (contraste), consequência, conclusão. Frases curtas. Confira a afirmação na fonte primária | `roteiro.md` + `FONTES.md` | o usuário aprova o texto |
| 2 | **Voz** escolhida e gerada (com "pode"); transcrição palavra a palavra (faster-whisper, como na `motion-vox`) | `audio/voz.wav`, `time/palavras.json` | — |
| 3 | **Régua de referência medida:** use `referencias/regua.md`; se o usuário trouxer outra referência, meça com o mesmo método e escreva a régua dela | `time/REGUA.md` | — |
| 4 | **Plano de batidas palavra a palavra:** cada evento numa palavra, −0,18 s, quadro par; elenco com tamanhos e pivôs; câmera; fundos; sons no quadro do golpe; legenda; título. Copie `ferramentas/gera_plano.py` para o projeto e escreva o seu plano no lugar do exemplo | `time/plano.json` + `PLANO.md` | — |
| 5 | **Insets e assets com licença:** para cada coisa citada, o material real (domínio público, CC0, CC BY com crédito) ou a geração com fundo transparente (custo + "pode"). Lista para aprovar de uma vez | `INSETS.md`, `CREDITOS.md` | o usuário aprova downloads e gerações |
| 6 | **Peças:** recorte, borda de papel, tamanho planejado em 2×, pivô no centro de tudo que gira (`pecas.py`; gravura em camadas: `separar_lizars.py` como modelo) | `pecas/` + `medidas.json` | **quadro-chave** no estilo final (1 quadro) |
| 7 | **Conferência do plano:** `gera_plano.py conferir` (degrau, orçamento, zona, sincronia) e quadros soltos (`previa.py --quadros`) | quadros de prova | — |
| 8 | **Som:** banco de efeitos do projeto, medida e ganho (`som.py banco/medir/mixar`), trilha num nível fixo | `som/som.json`, `previa.wav` | escuta do usuário (fone e celular) |
| 9 | **Montagem:** timeline no invideo (`invideo_ops.py`, ver `referencias/invideo.md`) e/ou render local (`previa.py`) | link da timeline / `previa/` | — |
| 10 | **Legenda por último** (ver abaixo) | legenda na timeline / no render | — |
| 11 | **Revisão contra a régua:** meça o resultado (cadência, sincronia, cor, acento, zona, níveis) e liste os achados por severidade; corrija os HIGH antes de entregar | `REVISAO.md` | o usuário assiste e aprova |

Regra: **a legenda entra por último**, depois de motion, B-roll/insets e som fechados. Ela depende do corte final da
fala e de onde os objetos caem na tela; mudar qualquer coisa antes obriga a refazer as janelas. Até lá, renderize e
monte com `--sem-legenda`.

Legenda do estilo: frase por frase, Inter 600 corpo 50, corte seco, centrada em y ~1372 (faixa própria, dentro da
margem do Reels); tinta `#29292B` no papel, creme `#F2EEE6` com sombra suave no escuro. Quando um objeto ocupa a
faixa de baixo, suba a legenda para um espaço livre. **Calada no título:** a última frase, dita pelo título, não
ganha legenda.

## As duas saídas

### Timeline editável no invideo

Duas timelines: **T1 TELA** (1080×1920, 24 qps: fundos, vinheta, MUNDO aninhado, cartão, título, legenda,
textura, áudio) e **T2 MUNDO** (2160×3840, uma faixa por peça). A câmera é o zoom e a posição do clipe MUNDO.
Regras que precisam ser seguidas (detalhe em `referencias/invideo.md`):

- **Zoom relativo ao encaixe:** `set_zoom` recebe o zoom relativo ao encaixe na tela e guarda valor × encaixe; as
  faixas de chave guardam o multiplicador nativo. Estático numa chamada, faixas em outra: `set_zoom`/`set_position`
  apagam a faixa.
- **Caixa nativa do `place_media`:** a imagem posta assim tem a caixa no tamanho nativo; zoom 1 nas faixas = pixel
  nativo. Posição = centro do clipe a partir do centro da timeline.
- **Opacidade em luz linear:** um preto por cima escurece menos que no sRGB; use 1 − (1 − op)^2,2.
- **Clipe de 2 quadros vira 1:** confira e corrija com `trim_clip`.
- **Degrau:** posição e zoom em pares de chave (quadro − 1 / quadro); rotação e opacidade com `ease: "hold"`.

`ferramentas/invideo_ops.py` escreve os lotes (`bin`, `criar`, `reg`, `chaves`); você manda pelo MCP do invideo,
confere com `capture()` contra os quadros da prévia e entrega o link.

### Render local

```
clpy ${CLAUDE_SKILL_DIR}/ferramentas/previa.py --plano time/plano.json --pecas pecas/ --saida previa/ \
       [--audio som/previa.wav] [--sem-legenda] [--quadros 0,120,330]
```

Usa o motor de colagem do plugin (`${CLAUDE_PLUGIN_ROOT}/motor/colagem/`) a 24 qps com 12 desenhos por segundo.
Para ver o exemplo: `clpy ${CLAUDE_SKILL_DIR}/ferramentas/previa.py --exemplo` (sem áudio; fundos e grades saem do `pecas.py base`).

## Ferramentas (`${CLAUDE_SKILL_DIR}/ferramentas/`)

Rode com `clpy` (o Python do motor de colagem do plugin, que já põe o motor no caminho; dependências em
`requirements.txt` desta pasta) e o ffmpeg no PATH: `clpy ${CLAUDE_SKILL_DIR}/ferramentas/<script>.py ...`.

| script | faz |
| --- | --- |
| `gera_plano.py` | `exemplo` escreve o plano do soco (modelo para copiar); `conferir` checa degrau, orçamento (≤ 2 por quadro), respiros, zona e sincronia contra a régua |
| `pecas.py` | `base`: fundos, grades e vinheta; `exemplo`: as receitas das peças do soco (recorte por GrabCut, borda de papel, fita por máscara, torção radial, foto em cartão, cartão da fonte) |
| `separar_lizars.py` | separa uma gravura vista de cima em crânio e cérebro (modelo para gravuras em camadas) |
| `previa.py` | render local e quadros soltos |
| `invideo_ops.py` | traduz o plano em operações do invideo |
| `som.py` | banco de efeitos num WAV só, medida R128, ganho de cada efeito pela régua, trilha e prévia a −14 LUFS |

## Som do estilo

Um efeito por ação, no quadro do golpe, **15–19 dB abaixo do momentâneo mediano da voz** (acento 16, ar e papel 18,
longo 19; trava: nenhum a menos de 15 dB na janela de 200 ms). O mesmo som pode rimar duas ações iguais (o giro da
cabeça e o giro do crânio). Ações decorativas ficam sem som. Trilha num nível fixo ~20–22 dB abaixo da voz, trocando
de parte só quando o assunto muda; o fecho pode ficar seco. A escuta é do usuário: declare-a pendente.

## Antes de entregar

- `gera_plano.py conferir` passou; quadros a cada 1,5 s vistos como espectador (`REGRAS.md` §9).
- Nenhuma peça que gira mostra borda reta de recorte; a legenda não cai sobre o assunto em nenhum beat de câmera.
- `CREDITOS.md` com cada imagem, música e efeito, e a linha de crédito pronta para a descrição.
