# Registros visuais

Tres cenas seguidas de "mesa + objeto + fita" leem como a mesma cena. **Alterne o
registro**, nao so o objeto. Cada registro tem um jeito proprio de compor, de anotar e
de animar.

| Registro | Quando usar | Heroi | Anotacao | Acento |
| --- | --- | --- | --- | --- |
| **Mesa de pesquisa** | objeto concreto sendo nomeado | objeto fotografado top-down | fita + marcador | amarelo |
| **Documentario retro** | "funcionando", "rodando", passagem de epoca | monitor CRT, aparelho antigo | nenhuma — a tela fala | fosforo ambar |
| **Foto em cartao** | pessoa, cena, prova de que alguem fez | copia impressa com margem branca | circulo manual | a cor da propria luz |
| **Dado a mao** | numero que o falante estima ou corrige | pizza/barra em hachura de marcador | o proprio numero, em marcador | amarelo da hachura |
| **Processo** | "de X para Y", transformacao | dois objetos + seta | seta longa | amarelo no fim |
| **Anotacao de campo** | faixa, ordem de grandeza, lembrete | cartao com escrita a mao | seta curta entre as palavras | nenhum |
| **Gráfico de barra** | progressão numérica **verificável** (2+ valores confirmados, ordem clara) | colunas crescendo/caindo, alinhadas na base | rótulo do valor em cima de cada barra | cor na barra final/maior |
| **Insert real** | nome de pessoa/marca/lugar citado | foto ou logo real, HERÓI da janela (`insert_hero`, ver `identidade.md`) | nenhuma — a prova é a foto/logo em si | a cor natural da marca/foto |
| **Storyboard / persona** | quem fala está **narrando uma história** com gente dentro (nomeada ou não) | figura de papel (`voxlab.persona()`), tinta de marcador | o objeto que a cena cita, herdado na mão da figura | amarelo no gesto |
| **Diagrama explicativo** | conceito **técnico ou científico** que a fala explica ("como funciona", "por que", estrutura, mecanismo) | ilustração composta (material por IA + corte/rótulo em PIL) | seta + rótulo apontando a parte | fósforo âmbar ou amarelo, igual ao resto |

| **Cartela de ano** | separador de capítulo numa cronologia | o ano em serif, tela cheia, sozinho | marca-texto ou sublinhado amarelo | amarelo |
| **Legenda de rodapé ▶** | dado numérico **secundário** sobre footage | nenhum — é anotação sobre a cena | o próprio triângulo amarelo | amarelo |
| **Lente amarela** | apontar uma região dentro de uma FOTOGRAFIA | a foto | círculo amarelo em multiply + linha de chamada | amarelo |

Regra pratica: **nao repita registro em cenas vizinhas**. Se M2 e mesa de pesquisa,
M3 nao pode ser.

## Cartela de ano · legenda ▶ · lente amarela

Os três vêm do estudo Porsche (`estudos/vox-porsche/ESTUDO.md`, §4 e §8), com as medidas de lá.

**Cartela de ano** (`kit.year_card`) — o ano em tela cheia, sozinho, como separador de
capítulo. A referência **alterna clara e escura**: bf05 mede 0,1% de massa escura, bf09
mede 98,5%. Duas claras seguidas desperdiçam o recurso; a escura é o que quebra uma
sequência pálida no miolo. Só para marco de capítulo — ano dito de passagem não ganha
cartela.

**Legenda de rodapé ▶** (`kit.footer_caption`) — serif itálica com triângulo amarelo, na
base do quadro, sobre footage. É onde vai o dado que enriquece mas não merece cena
própria ("210 km/h", "recorde de vendas da década"). Se o dado é o assunto da fala, ele é
cena. Máximo uma por cena, e nunca sobre cena que já tem tipografia própria.

**Lente amarela** (`kit.yellow_lens`) — círculo amarelo translúcido em multiply sobre a
região citada, mais linha de chamada fina até a etiqueta. Substitui a seta **em
fotografia**: colore a coisa citada em vez de só apontar para ela. Em objeto recortado
sobre papel o círculo à mão continua sendo o certo. Conta como o acento da cena.

## Storyboard / persona

**Narrativa também vira cena.** Quando quem fala conta uma história ou explica um
mecanismo, a janela é o material mais fácil de desenhar — e uma seleção que só aceita
frase com objeto ("entra a frase que tem objeto, não entra a que só tem conceito") perde
exatamente essas janelas. Quando a fala é uma NARRATIVA — "um cliente chegou e disse
que...", "aí ele saiu batendo a porta", "ela devolveu o presente" — tem sempre um personagem fazendo alguma coisa, mesmo que
ninguém tenha nome. Isso é storyboard, não é ilustração de objeto.

**A figura.** `voxlab.persona()` desenha um pictograma de papel — cabeça, tronco, dois
braços, duas pernas — no MESMO traço de marcador das outras anotações (`stroke()`,
jitter, boil "ink"). Não é vetor liso, não é IA gerando gente: é a mesma mão que desenha
o círculo e a seta, desenhando uma pessoa. Isso resolve de saída a regra de nunca gerar
rosto sintético de gente real — a figura é deliberadamente abstrata, um boneco de linha,
nunca um retrato.

**Pose conta a ação.** `pose` aceita `stand` | `sit` | `walk` | `point` | `reject`, mais
`facing` (1 ou -1) e `arm` (ângulo do braço em graus, para apontar/empurrar/segurar).
Uma história com dois personagens (cliente e dono, ela e ele) é DUAS chamadas de
`persona()`, cada uma com seu próprio seed — nunca a mesma figura repetida como se
fosse duas pessoas.

**Objeto herdado na mão.** Quando a persona segura ou empurra algo que já tem asset no
projeto (o presente, a chave, a caneca), a figura carrega ESSE objeto — não inventa um
substituto. É a mesma regra de "objeto herdado" de `transicoes.md`, agora com gente.

**Não é cutscene.** Uma cena de persona ainda seguem a timeline de sempre — START/MID/
END/EXIT, eventos travados em palavra. A figura muda de pose entre eventos (ex.: entra
`walk`, para em `stand`, aponta em `point`) como qualquer outro elemento anima por
`progress`, nunca por interpolação de esqueleto — cada pose é um desenho discreto.

## Diagrama explicativo

**Quando a fala explica um mecanismo ou estrutura** — "por que existe margem", "como
funciona a crosta da Terra", "o estômago cabe X" — o registro certo não é o objeto
isolado da mesa de pesquisa, é um CORTE ou ESQUEMA que mostra a parte por dentro.

Divisão de trabalho igual a qualquer cena: a MATERIALIDADE (a pele, a rocha, o tecido)
é IA de imagem, gerada e recortada como qualquer objeto do kit (mesmo prompt-skeleton
de `prompts-asset.md` — fundo neutro, sem sombra embutida, sem texto). O CORTE, a seta,
o rótulo e a hachura de destaque são PIL, sempre. Um corte transversal de estômago ou
de camada de terra é, na prática, um objeto fotografado (a "fatia") + anotação por
cima — a mesma mecânica de `hand_circle`/`hand_arrow` já cobre a parte que aponta.

**Não é infográfico de dashboard.** A proibição de "dashboard SaaS" e "gradiente
decorativo" em `identidade.md` vale aqui igual a qualquer cena — o diagrama é desenhado
como se fosse de um caderno de campo, não uma lâmina de PowerPoint.

**Gráfico de barra vs. "dado a mão".** Mesma família (comparação de valores), critério
diferente: número que o falante **afirma com confiança** (não estima, não se corrige)
e tem 2+ pontos formando uma progressão ("de 20 pra 80, esse ano 120") vira **barra
limpa** — tipografia de dado, sem hachura de marcador. Número estimado/impreciso
continua em "dado a mão" (hachura). As duas competem pelo mesmo tipo de momento; nunca
as duas na mesma cena.

## Documentario retro — a tela

O conteudo da tela e desenhado por nos, **em blocos, nunca em texto**:

- a nota do editor costuma proibir interface falsa de aplicativo;
- escrever codigo na tela e inventar conteudo;
- no tamanho em que o aparelho aparece (~330px), nenhum caractere seria legivel.

Blocos de comprimento variavel, aparecendo linha a linha, com cursor piscando, leem
como "tem coisa rodando" sem afirmar nada. Some scanlines e vinheta do tubo.

O quadrilatero da tela precisa ser **medido** no recorte, nao estimado: o aparelho fica
em tres-quartos, a tela e um trapezio, e um paste reto denuncia. `cv2.approxPolyDP` no
contorno da regiao escura + `getPerspectiveTransform`. Ver `lib/crt.py`.

O registro retro e **tempero, nao idioma**. Uma cena por video.

## Dado a mao

Numero que o falante estima, arredonda ou corrige NAO vai em tipografia de dado limpo —
ganharia autoridade que a fala nao tem. Vai em **hachura de marcador**, com o numero
escrito a mao.

Ordem de desenho, que e a ordem da mao: contorno em duas passadas → raios → hachura.
Ver `voxlab.hand_pie()`.

Quando o falante se corrige ("90… 50%"), o numero que vale e o ULTIMO. Por o primeiro
na tela contradiz o audio.
