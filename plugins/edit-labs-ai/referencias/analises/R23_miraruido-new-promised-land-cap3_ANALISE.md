# Análise: "The New Promised Land. Chapter 3." (MiraRuido) (versão 2: vídeo inteiro em movimento)

**O que é.** Terceiro de três vídeos de animação para um documentário web (interativo) sobre cinco jovens refugiados sírios. Este capítulo acompanha Nour depois da chegada à Alemanha. Publicado no Vimeo em 19/03/2016, 1:39 (98,96 s), 1920×1080, autor **MiraRuido**. Sem créditos de equipe na página; licença não verificada (tratar como todos os direitos reservados). Link: [vimeo.com/159601006](https://vimeo.com/159601006).

**Como medi (versão 2).** Reproduzi o vídeo inteiro no navegador e amostrei **a cada 0,25 s** (395 amostras, 0 s a 98,75 s), em 160×90 px de luminância. Para cada amostra: diferença bruta com o quadro anterior, **alinhamento** com o quadro anterior (busca de ±5 px) e o erro que sobra depois do alinhamento; e a posição de uma linha horizontal forte. Também amostrei **a cada 0,04 s** num trecho de 1 s para ver o tremor entre quadros vizinhos. **Não ouvi o áudio.** Amostragem de 4 por segundo pode perder cortes de menos de 0,25 s.

## Resumo em números
| medida | valor |
|---|---|
| cortes (grupos de amostras com erro ≥ 60) | **30 em 99 s** (≈3 a cada 10 s) |
| intervalo entre cortes | **mediana 2,75 s**; mínimo 0,5 s; máximo 9,25 s |
| tempo em trecho **estável** (erro < 25) | **66%** |
| tempo em **movimento** (erro 25 a 60) | **21%** |
| tempo em **corte** (erro ≥ 60) | **10%** |
| congelado no fim | 96,75 s a 98,75 s (≈2 s) |
| deriva de câmera nos trechos estáveis | **~1 px a cada 0,25 s, sempre para a esquerda** (≈ 40 a 50 px/s em 1080p) |
| tarja horizontal fixa | **não confirmada** (ver abaixo) |

Ritmo por dez segundos (cortes): 0–10 s: 4; 10–20: 1; 20–30: 3; 30–40: 3; 40–50: 4; 50–60: 2; 60–70: 4; 70–80: 3; 80–90: 3; 90–99: 3.

## Filtros
1. **Foto P&B granulada com meio-tom.** Retratos, multidões, janela com luz forte. O grão é visível e as sombras são fechadas.
2. **Papel de jornal amarelado** como fundo, quase sempre, com texto ilegível em miniatura.
3. **Moldura de negativo preta**, cantos levemente arredondados.
4. **Vermelho só como anotação**: manuscrito, carimbo e marcações. 0,32% dos pixels são vermelhos; mediana `#C35853`.
5. **Vinheta leve** (centro 111, borda 104 de 255).
6. **Mancha de tinta escura** (fumaça ou impacto) em meio-tom, em alguns cortes.
7. **Tremor de quadro a quadro.** Medido a cada 0,04 s: a diferença entre quadros vizinhos alterna entre cerca de **10 e 5 níveis** de luminância. Ou seja, **a imagem treme a cada quadro**, mais que o Two Parties. É o efeito de "fotocópia viva", e não uma troca de desenho a cada 0,4 s.

## Movimentos
- **Corte seco** entre planos, a cada 2 a 3 s em média. A maioria é corte direto, sem transição.
- **Foto que entra deslizando e crescendo** em cerca de **0,75 a 1 s**. Confirmado no trecho 92,0 → 93,5 s: corte para o papel, depois a moldura desliza e assenta.
- **Palavra que surge por frase** ("when? how? how long?", "Everything will change"). Ocorre em planos com fundo estático.
- **Deriva de câmera (confirmada)**. Nos trechos estáveis, o conteúdo inteiro, papel e foto juntos, desloca **1 px a cada 0,25 s, sempre para a esquerda** (ou seja, a câmera vai para a direita). No 1080p isso dá **~40 a 50 px/s** em quase todos os trechos. Há variação: entre 82 e 86 s desce para ~0,5 px por amostra, e entre 93 e 96 s para ~0,2. Não é tremor: é deslocamento uniforme e contínuo.
- **Tremor** (item 7 dos filtros): sobreposto à deriva.
- **Fim congelado** de ~2 s, depois do último texto.

## Tarja horizontal: não confirmada
As linhas horizontais existem (são linhas de documento e uma régua), mas **não têm altura fixa**. A linha mais frequente fica perto do topo (y≈9 de 90 px, provavelmente a borda do quadro); as demais caem em alturas diferentes (38, 64, 81). Não há varredura contínua. Concluo: **não é tarja fixa**; são linhas do próprio documento em posições variadas.

## Ritmo de entrada das fotos
Corte para o plano, pausa de 0,5 a 1 s com a foto entrando, e depois **trecho estável de 2 a 3 s** com a deriva lenta. É um ciclo: **corte → entrada (~1 s) → deriva lenta (2 a 3 s) → corte**. Essa estrutura é o que dá o tom de documentário dramático: cada foto tem tempo para ser lida antes do corte.

## Assets (sem mudança em relação à versão 1)
| asset | origem | uso |
|---|---|---|
| retratos e multidões de refugiados | pessoas reais, do projeto; **não reutilizar** | o tema, com grão |
| gravura de nervos nas costas, com mapa de faculdades em vermelho | gravura antiga, provavelmente domínio público; origem exata não confirmada | o assunto: o sistema nervoso como mapa |
| papel de jornal e de documento | textura fotográfica de papel impresso | ambientação |
| figura mascarada com faca e carimbo "CORPS FILE" | foto de arquivo ou composição, origem não identificada | cena de tensão |
| objetos sobre mesa | foto de mesa | documento pessoal |

## Paleta medida (19 quadros de 480×270; ±3 níveis por compressão)
- **Papel:** `#E7D6B9`, `#D8C7A9`, `#F4E4C9`.
- **Sombras:** `#1D2228`, `#181D23`, `#24282B` (preto azulado, frio).
- **Cinzas quentes:** `#978978`, `#A79986`, `#877A69`.
- **Vermelho do acento:** `#C35853`.
- **Luminância:** 34% escuro, 38% médio, 28% claro.

## Comparação com o Two Parties
O Two Parties tem 86% de papel vazio e sombra quase neutra; o Chapter 3 é mais denso, mais escuro (34% de pixels escuros contra menos de 10% no Two Parties), com **cortes a cada 2,75 s** e **deriva contínua** de câmera. O Two Parties é quase parado entre entradas; o Chapter 3 nunca está parado (há sempre deriva ou tremor). A limpeza do Chapter 3 vem do enquadramento e de uma moldura por assunto, não do vazio.

## Como usar no nosso vídeo
- **Cena de medo ou espera:** foto P&B granulada em moldura de negativo, sobre papel de jornal, com **deriva lenta da câmera** (~40 px/s) e uma palavra que entra.
- **Cena de anatomia (nervos, cérebro):** gravura antiga com marcação vermelha desenhada, no papel. O mapa de faculdades é o precedente.
- **Ritmo:** corte a cada 2 a 3 s; entrada de 1 s; deriva lenta durante a leitura.
- **Tremor:** leve e por quadro, sobre tudo (é o nosso boil, mais forte que o Two Parties).
- **Acento:** `#C35853`, só para anotação e carimbo.

## Riscos
- **Pessoas reais:** nunca reutilizar fotos de refugiados. O estilo se copia; a imagem não.
- **Peso emocional:** o estilo funciona para drama, mas pesa em assunto leve.
- **Documento falso:** jornal e carimbo podem passar por fato; em anatomia, deixar fontes claras.
- **Ainda não verificado:** o áudio (narração e trilha). Não ouvi.
