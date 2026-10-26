# Ficha de estilo: recorte-ritmo-textura

**Quando usar:** quando a ideia é **ritmo e textura de recorte** (retrato recortado, jornal rasgado, meio-tom, contraste forte), sem se prender ao assunto. Boa para **abertura e transições** de qualquer vídeo.

**Evidência:** R09 Fakeplastictree (vista, 2 quadros), R10 Gilliam (citada: origem), R21 (citada, só ritmo).

## O sistema
| item | regra |
|---|---|
| fundo | **preto** com papéis claros recortados; contraste forte |
| elementos | retrato em B&W recortado, **jornal rasgado**, textura de **meio-tom**, pequenos acentos de cor (vermelho, amarelo) |
| movimento | **cortes rítmicos**: cada peça entra no beat, pequenas rotações, escalas |
| origem | Terry Gilliam: gravura vitoriana recortada em **articulações** (braço, boca) |

## No nosso motor
Já temos `C.cai`, `C.desliza`, `Transicao`. Falta: **fundo preto com grão** (existe `fundo_escuro`) e **jornal rasgado** como textura (PNG com alfa).

## Riscos
- Não é anatomia: usar só como **moldura** (abertura de 3 s, fecho). O miolo continua em outro estilo.
