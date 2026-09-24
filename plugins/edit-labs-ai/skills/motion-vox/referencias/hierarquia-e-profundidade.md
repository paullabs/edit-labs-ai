# Hierarquia, profundidade e decupagem

> Três defeitos de composição são problema de método, não de cena: quando aparecem,
> aparecem em todas as cenas ao mesmo tempo. Leia este documento junto de `identidade.md`
> **antes de compor**, e reveja depois de compor.

Os três: nenhum elemento manda na cena, bordas tangentes achatam a composição, e as
imagens entram jogadas, sem ordem de leitura.

---

## 1. Hierarquia — um elemento manda, os outros obedecem

**Toda cena tem UM dominante.** Não dois. Se dois elementos têm o mesmo tamanho, o mesmo
contraste e o mesmo peso, o olho não sabe onde pousar e a cena lê como "coisas jogadas".

Exemplos de erro:

| Caso | O erro | O que fazer |
| --- | --- | --- |
| objetos iguais | seis envelopes **do mesmo tamanho** em grade solta — nenhum é o assunto | pilha com variação de escala: um na frente, grande; os outros menores atrás |
| tudo disputando | duas fotos de tamanho parecido + dois objetos, todos disputando | uma foto por vez, em tela cheia |
| subordinado sumido | um cartão gigante e uma anotação minúscula — hierarquia existe, mas o subordinado fica ilegível | anotação proporcional ao que ela aponta |

Teste rápido: **desfoque o frame até só restarem manchas.** Se sobrar uma mancha
dominante, há hierarquia. Se sobrarem várias iguais, não há.

### Anotação nunca disputa com o herói

**O carimbo/rótulo vai SOBRE o objeto que ele qualifica, não ao lado dele.** Carimbo
posto abaixo do documento encosta na borda dele — metade em cima do objeto, metade fora —
e lê como acidente de layout, não como carimbo.

Carimbo é marca aplicada a um documento: vai **no meio do documento**, girado, com
largura de 60–75% da largura dele. Nunca sangrando para fora.

---

## 2. Profundidade — proibido tangenciar

**Tangente** é quando duas bordas quase se tocam, ou se tocam sem sobrepor. É o erro
clássico que achata composição: o olho não consegue decidir o que está na frente, e o
quadro vira recorte de papel colado sem volume.

Regra binária, sem meio-termo:

> Dois elementos ou **se sobrepõem de verdade** (com sombra de contato marcando quem
> está na frente), ou ficam **claramente separados** (folga ≥ 40px). Nunca encostados.

O que constrói profundidade, em ordem de força:

1. **Sobreposição com sombra de contato** — a única que cria camada de verdade
2. **Variação de escala** — objetos iguais em tamanhos diferentes leem como perto/longe
3. **Vinheta** — escurecer as bordas empurra o centro para frente
4. **Desfoque diferencial** — o de trás um pouco mais macio

Cena de objetos todos do mesmo tamanho, todos chapados no mesmo plano, com sombras
iguais: **isso é flat, por construção.** Varie escala e sombra por camada — a
`identidade.md` já proíbe "a mesma sombra em todas as camadas", e é exatamente por isso.

---

## 3. Fotografia em tela cheia

Fotos impressas **não precisam ser sempre cartão sobre a mesa, e nunca devem ser uma
atrás da outra.** Empilhar duas instantâneas de tamanho parecido produz o pior dos dois
mundos: nem tem hierarquia, nem tem profundidade, e o conteúdo de cada uma fica pequeno
demais para ser lido.

Alternativa, e às vezes a melhor escolha:

```yaml
registro: foto em tela cheia
quadro:   a fotografia cobre 1080x1920 inteiro, sem moldura, sem mesa
vinheta:  escura, 0.45-0.65 — é ela que dá profundidade e separa da legenda
camera:   push lento de 100 -> 104-106% ao longo do plano
duracao:  ~1s por foto quando em sequencia; ate 3s quando e a foto principal
corte:    seco entre fotos, na palavra
```

**Isso exige gerar a foto em 9:16.** Recortar uma 4:3 para 9:16 joga fora ~58% da
largura e destrói o enquadramento. Se a foto vai ocupar a tela inteira, peça vertical
desde o prompt.

---

## 4. Decupagem — beats dentro do plano, não só planos

O erro é tratar um cutaway de 8 segundos como **uma** composição que vai se acumulando.
Oito segundos comportam quatro ideias; acumular as quatro no mesmo quadro entope a
composição e mata a hierarquia (defeito 1) — é o caso "tudo disputando" da tabela acima.

**Um cutaway longo é uma sequência de beats, com corte seco entre eles.**

- cada beat = uma frase da fala, e **na ordem em que ela é dita**
- 1–1,5s para beat de contexto (lugar, época), 3s+ para beat de argumento
- o corte cai no **silêncio entre palavras**, não em cima da sílaba
- beat novo pode trocar de registro (tela cheia → mesa → tela cheia): a troca É a
  dinâmica

Densidade não resolve isso. Aumentar a porcentagem de motion só alonga; o que dá
dinâmica é **quantos beats existem dentro do tempo que já se tem**.

---

## Checklist, antes de renderizar

- [ ] Desfoquei o frame: sobra **uma** mancha dominante?
- [ ] Alguma borda **quase** encosta em outra? (sobrepor de verdade ou afastar 40px)
- [ ] As sombras são diferentes por camada, ou copiei a mesma em tudo?
- [ ] Carimbo/rótulo está **sobre** o objeto que qualifica, dentro dele?
- [ ] Duas fotos de tamanho parecido lado a lado? → uma em tela cheia por vez
- [ ] Plano com mais de 4s: quantos beats tem? Um só? → decupe
- [ ] Cada corte cai em silêncio, e os beats seguem a ordem da fala?
