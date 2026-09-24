# Legenda — padrão MOTION VOX v2

> Este é o padrão corrente da legenda. Cascata à esquerda, entrada animada em 4 frames,
> palavra-chave pintada em toda frase e legenda no clipe inteiro ficam fora: leem como
> arrastadas e competem com os motions.

Tudo abaixo foi **medido frame a frame** numa referência do estilo (talking head vertical,
1492 frames a 30fps, 720x1280), não estimado a olho. Os números são o contrato.

| parâmetro | medido | como |
| --- | --- | --- |
| eixo horizontal | centro da linha em **359,5px de 360** (desvio mediano 1,0px) | bbox por linha, 54 blocos |
| entrada | **93% da massa no 1º frame**; deslocamento 0,7px; escala 0,0% | perfil de massa nos 6 primeiros frames |
| duração do bloco | mediana **10 frames a 30fps = 0,33s** (p25 0,20 / p75 0,53) | segmentação por IoU |
| cadência | **2,45 blocos/s** | 122 blocos em 49,7s |
| linhas por bloco | 1 na maioria (41 de 54) | perfil de linhas |
| corpo | glifo 38px@720 → **57px@1080** → corpo ~78px | altura de tinta |
| ênfase | **2,1×** o corpo | razão maior/menor linha dentro do bloco |
| cor | **94% branco**, 3,5% verde, 2,4% vermelho | classificação por pixel |
| vertical | centro do bloco em **0,696H** | bbox do bloco |
| largura de linha | p90 = **0,48W** | bbox por linha |

## As duas regras que mais mudam o resultado

**1. A fluidez não vem de easing, vem de ritmo.** A referência não anima nada — é corte
seco. O que dá fluidez é a CADÊNCIA: blocos curtos trocando ~2,45 vezes por segundo, cada
um no tempo exato da palavra. Animar a entrada (subida + fade em 4 frames) de um bloco que
dura 10 frames gasta metade da vida dele em transição, e lê como arrastado.

**2. A cor não é o dispositivo.** Pintar a palavra-chave em toda frase mata o acento. Na
referência 94% das linhas são brancas. O acento só funciona porque é raro — no clipe
inteiro, duas palavras.

## Diagramação

- **Centrado**, nunca cascata alinhada à esquerda.
- Empilhamento **por tinta**, não pela métrica da fonte: mede-se a bbox real de cada
  linha e usa-se entrelinha `LEAD ≈ 0,96`. Só assim uma entrelinha menor que 1 fica
  previsível em vez de colidir. As linhas se tocando é a diagramação da referência.
- Dois registros: grotesco **black** para o corpo, **serifa itálica** de alto contraste
  para a ênfase. A palavra de ênfase aparece **sozinha** no bloco.
- Branco com **sombra projetada** (blur 7, offset y+5, alpha 0,62). Sem tarja e sem
  inversão de cor: a legibilidade vem da ALTURA (peito, sobre roupa escura), não de
  tratamento do fundo.
- Bloco de uma palavra só existe se ela **carrega sentido** — conjunção sozinha no meio
  da tela lê como erro de corte.

## Densidade do bloco

Blocos de 3 palavras em corpo grande (80px) frequentemente ultrapassam `LARGURA` e
quebram em 2 linhas — tecnicamente ainda centrado (a matemática de centralização não muda
com a largura), mas o BLOCO fica visualmente pesado, quebra uma frase no meio ("quando
as" / "pessoas") e lê como errado mesmo sem estar fora da margem seca. Por isso
`MAXPAL = 2`: mais perto do `~1,7 palavras/bloco` medido na referência, e evita o wrap de
2 linhas na maioria dos casos.

## Onde a legenda entra

A referência é talking head puro e legenda o vídeo inteiro. Com motion graphics o caso
muda: cutaway que já tem tipografia própria não pode receber legenda por cima — duas
tipografias no mesmo quadro brigam. Então a legenda **corre nas janelas livres e cala sob
os motions**. Janela menor que 2s fica de fora: legenda que pisca entre dois motions lê
como defeito.

Bloco **nunca atravessa um corte** do próprio clipe: junta o fim de uma frase com o começo
de outra e lê como erro de decupagem. Corte conhecido entra em `CORTES`.

## A tipografia também é impressa

**A frase de impacto também leva boil:** na referência a tipografia é impressa em papel
áspero — a borda da letra é **erodida**, não limpa.

Mas não é o boil dos objetos. O preset `ink` tem ruído grosso e deformaria a FORMA da
letra. Para tipografia existe **`print`**: ruído fino (`size 22`, `amount 3.0`) que erode
a BORDA sem desmanchar o desenho. `print` **não escala** com `BOIL_SCALE` — é textura de
impressão, não intensidade de tremor.

`boil_ctx(None)` é obrigatório antes da passada de legenda: sem ele o texto herdaria o
campo congelado do último frame da última cena.

## Sincronia

Exige transcrição **palavra a palavra** (faster-whisper com `word_timestamps=True`).
Sem ela não há corte seco possível — o corte seco só funciona porque cai no tempo exato
da palavra. Blocos não podem se sobrepor no tempo: com sobreposição o render escolhe o
primeiro que casa e o bloco seguinte entra atrasado, destruindo justamente a sincronia.
