# Boil — o objeto redesenhado a cada passo

Equivale ao **Turbulent Displace + Posterize Time** do After Effects. É o que faz cada
elemento parecer redesenhado à mão a cada quadro, em vez de colado.

Está na mesma família do "on twos" que a identidade já usa (sensação de stop motion) —
só que aplicado à **forma**, não à posição.

## Como funciona

Campo de ruído fractal em duas componentes, aplicado como `cv2.remap` sobre a camada.
O campo **não evolui suavemente**: ele **troca de semente** a cada passo de 9fps. É o
salto que dá a sensação de desenho refeito — evolução contínua daria ondulação de
gelatina, que é outra coisa e fica pior.

A camada ganha margem de `amount` antes do remap, senão o deslocamento empurraria pixel
para fora e cortaria a borda (o "Pin All" do AE).

## Intensidade por classe — medida, não estimada

```yaml
obj:    amount 3.0  size 110   # objeto fotografado
paper:  amount 4.0  size  95   # papel, cartão, fita
type:   amount 2.0  size 130   # tipografia editorial dentro da cena
ink:    amount 6.0  size  75   # marcador e anotação
print:  amount 3.0  size  22   # tipografia de impacto — erode a BORDA, não a forma
```

**Tinta desenhada aguenta o dobro de um objeto fotografado.** Acima disso o objeto
**derrete**, e a identidade proíbe. Numa tira comparativa, o relógio já perde a
circunferência em 3,5; a tipografia editorial começa a ondular em 4; o marcador e o
círculo aguentam 7 sem estranhar.

## Duas armadilhas

**Semente por elemento, estável entre frames.** Sem isso o quadro inteiro balança junto e
parece tremor de câmera, não desenho. A semente vem da **linha que chamou** — cada ponto
de desenho ganha um campo próprio, e ele não muda quando um objeto condicional aparece
ou some. (Semear por ordem de desenho quebra exatamente nesse caso.)

**Elemento fisicamente único precisa de campo único.** Fita e a palavra escrita sobre ela
são um objeto só: com campos separados a etiqueta parece descolar do papel. Use
`boil_seed=` igual nos dois. No AE isso seria uma pré-composição.

## Uso

`V.boil_ctx(frame)` no topo de cada `build_M#` liga tudo. Depois disso, todo
`text_layer`, `hand_circle`, `hand_arrow`, `hand_underline`, `blue_line`, `hand_pie` e
`place` já saem com boil na classe certa.

É estado implícito de propósito: sem ele, cada uma das ~50 chamadas de desenho
carregaria o frame, e uma cena nova nasceria sem boil por esquecimento.

**A tipografia leva boil, mas com outro preset.** `print` (amount 3.0, size 22) erode a
BORDA da letra como tinta em papel áspero; `ink` (size 75) deformaria a forma. E `print`
não escala com `BOIL_SCALE`, porque é textura, não intensidade.

**A legenda também leva `print`**, aplicado dentro da própria passada de legenda
(`captions.draw`), com semente própria: erode a borda sem deformar a letra, e a
legibilidade fica. Como o frame corrente é estado de módulo, essa passada precisa chamar
`boil_ctx(None)` antes de desenhar: senão a legenda herda o campo congelado do último
frame da última cena e sai torta **sem nem animar**, que é o pior dos dois mundos.

**O fundo NÃO leva boil.** Aplicado ao quadro inteiro, o papel pontilhado ondularia e o
efeito viraria distorção de lente. No AE o efeito vai em cada layer, não no comp.
