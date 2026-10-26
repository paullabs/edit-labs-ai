# Régua do explicador Vox (medida)

Referência: Vox, **"Something weird happens when you keep squeezing"**
(https://www.youtube.com/watch?v=NqabT21d8VM). Foram medidos os trechos animados, com mais peso em 0:10–0:22
(objeto e força), 1:14–1:37 (diagrama), 7:11–7:42 (processo causal), 7:56–8:24 (transformação) e 10:01–10:30
(impacto na consequência). O vídeo da Vox **não vem no plugin**. Para conferir um número, assista no link.

A referência é 16:9 a 24 qps. A tradução para 9:16 foi feita pela proporção do lado curto (720 → 1080).

## Como medir uma referência nova (o mesmo método)

| medida | como |
| --- | --- |
| cadência e holds | diferença média entre quadros em cinza (320×180) contra o anterior; 0,0 = quadro repetido |
| cortes | diferença > 8 **e** correlação de fase < 0,15; conferir cada um na folha de contato |
| cor | mediana por região e k-means de 6 cores nos quadros-chave; escuro = luminância < 80; acento = saturação > 0,45 com luminância > 60 (imagem a 480×270) |
| texto | limiar de cor numa região e perfil de linhas → altura da maiúscula e caixa do texto |
| ocupação | pixels a mais de 45 de distância RGB da cor da borda do quadro |
| fala | palavras com tempo (faster-whisper, local) e loudness por `ffmpeg ebur128` |

## 1. Ritmo

| medida | valor |
| --- | --- |
| cortes secos | mediana **1,65 por 10 s** (faixa 0,34–4,6) |
| plano animado | mediana **7,6 s** (mín. 1,6, máx. 15,8) |
| eventos dentro do plano (entra, muda ou sai algo) | mediana **5,1 por 10 s**, ou 1 a cada ~2 s (faixa 3,1–10,5) |
| do corte ao 1º evento | mediana 0,5 s (0–1,3 s) |
| imagem × palavra que nomeia o evento | mediana **−0,18 s** (a imagem chega ~4 quadros antes); faixa −0,60 a +0,27 s; nada passou de +0,27 s |
| legível depois de pronto | processo 3,4–4,1 s; passo único **mínimo 1,2 s** |
| narração | 157–185 palavras/min |

Regra: um evento a cada ~2 s é o piso da referência. Se a régua do projeto pedir mais motion, suba a densidade,
mas mantenha os holds legíveis (≥ 1,2 s depois de pronto).

Regra de sincronia: o quadro do evento = início da palavra − 0,18 s, arredondado para quadro **par** (degrau de 12).
Mais de +0,27 s de atraso é erro.

Regra do fim: o último estado precisa de ≥ 1,2 s na tela. Se a fala acabar antes, estenda a imagem 0,5–1,0 s
depois da voz (cauda).

## 2. Densidade por quadro

Conta: elemento que **age** (objeto, entrada, reação, saída). O objeto feito de partes conta 1. Fundo, grade, grão e
vinheta não contam.

| medida | valor |
| --- | --- |
| máximo num processo causal | **4 elementos, num eixo só** (entrada → objeto → reação → saída) |
| mediana | 1–3 |
| respiro (um objeto sozinho) | **52% do tempo animado** (faixa 24–69%) |
| ocupação de pixels no estado completo | 17–32% do quadro; o resto é fundo liso |
| hold total (0,5 s sem nenhuma mudança) | 17% das janelas; nos processos, 0–4% |

Regras:
- Nunca dois grupos independentes no mesmo quadro.
- O esquema "pronto" continua vivo (tremulação no desenho de 2), mas nada novo entra enquanto ele é lido.
- No 9:16, use **no máximo 2 elementos por quadro fora a legenda** (o quadro é mais estreito).

## 3. Texto

| nível | maiúscula em 720 | % do lado curto | **em 9:16** |
| --- | --- | --- | --- |
| título do estado/resultado | 44–46 px | 6,1–6,4% | **maiúscula 66–69 px** (corpo ~92–96 numa grotesca pesada) |
| rótulo do objeto | 37 px | 5,1% | 55 px |
| rótulo de parte (preso a ela, gira com ela) | 24 px | 3,3% | 36 px (abaixo do mínimo de 50 do plugin: prefira não usar) |

Regras:
- 1–2 palavras por elemento, máximo 3. Texto que repete a fala inteira é legenda, não título.
- **No máximo 2 tamanhos de texto no mesmo quadro.**
- Grotesca pesada em caixa alta para título; serifa itálica cinza só em fórmula ou sub-rótulo.
- O título fica **sobre o próprio objeto**, perto do centro (y 600–1000 no 9:16). Nada em canto.
- ~12 caracteres por linha com entreletra larga, ~20 com entreletra normal.
- Entrada e saída em **fade de 5–8 quadros** (mediana 6). Nada de letra a letra, salto ou bounce.

## 4. Cor

| papel | valor medido |
| --- | --- |
| papel creme | **#DEDBCB** (74–86% do quadro nas cenas de papel) |
| grade no papel | #6F6E6B (cinza médio, não preto) |
| carvão | **#232325** no centro, #121212–#181818 nas bordas (vinheta) |
| grade no escuro | #4C4C4C |
| partes diferenciadas | tons dessaturados (saturação ~0,09): verde #B3C0AE, azul-cinza #A7B0B7 |
| **acento da ação** | um matiz saturado (na referência, violeta #4E15E1), **~2–5% da área** |
| texto no escuro | creme/branco #E0CAC2–#FFFCF9 |

Regras:
- **Um matiz saturado por quadro**, e ele marca a ação. Se voltar mais tarde, volta na mesma cor.
- **As partes se apresentam no papel e a ação acontece no escuro.** O fundo escurece durante a passagem para o
  processo (em ~1–5 s); só então o acento entra.
- Nos processos, a massa escura fica em ~77% dos pixels.

## 5. Movimento

| medida | valor |
| --- | --- |
| cadência | **89% do movimento no desenho de 2 (12 qps)**, 4% no de 1 |
| elemento pequeno entrando | 6–10 quadros |
| herói chegando | 30–40 quadros, com pouso desacelerado (ease-out) |
| saída | 10 quadros; título sai em fade de 18 |
| câmera | **parada durante a ação** (≤ 15 px em 6–11 s); anda só como beat com início e fim: empurrão de 20 quadros, rotação de ~6 s, recuo de 32 quadros |
| boil e grão no hold | a referência não ferve: o quadro parado é idêntico |

Regras:
- Desenho a 12 qps num relógio de 24, **e a câmera também em degraus de 2 quadros**. Fluido misturado com degrau
  denuncia o template.
- Câmera parada enquanto a coisa acontece. Sem zoom lento contínuo e sem tremor no impacto.
- Se o projeto pedir boil, use o mínimo (≤ 1 px na tela, ciclo lento).

## 6. Transições

| tipo | parte | quando |
| --- | --- | --- |
| corte seco | **~70%** | entre ideias |
| mergulho (empurrão para dentro do objeto) | 3 de 42 | para entrar "dentro" de algo |
| íris | 2 | logo depois do mergulho |
| flash radial | 2 | **só no evento-consequência** |
| rotação com escurecimento | 2 | das partes (papel) para o processo (escuro) |
| fusão, recuo, tela dividida | 1–2 cada | casos pontuais |

Regra: o corte seco é o padrão. Transição especial precisa de motivo.

## 7. Som

| medida | valor |
| --- | --- |
| trilha nas pausas | pelo menos 6 LU abaixo da voz, em geral **14 LU ou mais** |
| efeitos | não dá para contar sem separar as fontes; há indício de impacto só na consequência |

Regras do estilo (detalhe em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md` §7):
- **Efeitos 15–19 dB abaixo do momentâneo mediano da voz**, um por ação, no quadro do golpe.
- Trilha num nível fixo ~20–22 dB abaixo da voz; troca de parte só quando o assunto muda.
- O fecho pode ficar seco (voz + um golpe grave), com a trilha saindo na pausa anterior.

## 8. Tradução para 9:16 (1080×1920)

| na referência | no vertical |
| --- | --- |
| assunto + grade = 79–85% do lado curto; objeto sozinho 58–63% | grupo de 850–920 px; **objeto de 630–680 px**; centro em (540, 960) |
| margem de cima e de baixo 7–11% | margem lateral 78–119 px |
| o processo corre num eixo horizontal de 86% da largura | o eixo continua horizontal: a entrada vem **de fora da borda** e só os últimos ~350–450 px aparecem; a consequência vai em outro plano (corte ou mergulho) |
| título sobre o objeto | maiúscula 66–69 px, y 600–1000 |
| zona do assunto | y 560–1360; nada importante fora da margem do Reels (`REGRAS.md` §4) |

## O que faz parecer profissional

1. Uma cadeia causal, um eixo, poucos elementos, entrando um de cada vez.
2. Partes no papel, ação no escuro.
3. Um matiz saturado por quadro, na ação.
4. Texto curto, preso ao objeto, em no máximo 2 tamanhos.
5. Desenho a 12 qps e câmera parada na ação; a câmera só anda como beat.
6. Entradas curtas que pousam (6–10 quadros; herói 30–40).
7. A imagem chega junto com a palavra, um pouco antes (−0,18 s).
8. Depois de pronto, o esquema fica legível (≥ 1,2 s).
9. Corte seco como regra; flash só na consequência.
10. Muito fundo vazio (17–32% de ocupação).

## Sinais de amador

- Quadro lotado (o golpe, a cabeça, setas, eixo, interior, rótulos e título juntos).
- Dois acentos saturados ao mesmo tempo.
- Frase na tela no lugar de título de 1–3 palavras.
- Texto ou contato fora da zona; título no canto.
- Elemento a 24 qps fluido "de template", curva linear, letra a letra, bounce.
- Câmera que nunca para, tremor no impacto.
- Imagem atrasada em relação à palavra.
- Flash no golpe que "só empurra": o impacto é guardado para a consequência.
- Abstração no lugar da coisa (círculo vazio como "eixo", ícone genérico de cabeça).
- Fórmula que a voz não diz.
- Grade em todo quadro (só quando dá escala ou medida).
- Tudo claro ou tudo escuro.
- Último estado curto demais.
