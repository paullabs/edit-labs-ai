# Ficha de estilo: gravura-bw-acento

**Quando usar:** anatomia e ciência com cara de **livro antigo vivo**: o corpo é uma gravura em preto e branco com grão, e **uma cor** carrega a ideia (o órgão, o fluxo, o problema). É o tom mais "arte" que achamos para o corpo humano.

**Evidência:** R11 Longevity Hackers (**vista**: 1 quadro e texto; falta estudar o vídeo inteiro), R03 (o degradê de cor sobre o cinza), R01 (gravura de anatomia animada, em versão colorida). Esta ficha é uma **hipótese a confirmar** com o vídeo do R11.

## O sistema (o que sei e o que suponho)
| item | regra | confiança |
|---|---|---|
| imagem | gravura anatômica real (domínio público: Gray, Vesalius, atlas antigos) em **preto e branco**, com **grão de papel e meio-tom** | vista (R11) |
| fundo | papel claro quase sem cor, com **diagramas técnicos finos** (hexágonos moleculares, régua, setas) | vista (R11) |
| acento | **uma cor** por ideia, só no que importa; o resto cinza | R03 (a fundo) + hipótese |
| tipografia | serifada fina de alto contraste (títulos), sans pequena nas legendas técnicas | vista (R11) |
| composição | um objeto gravado grande + **2 ou 3 elementos técnicos pequenos** ao redor (seringa, tubo, número); muito branco | vista (R11) |
| movimento | **desenhar o objeto sendo "revelado"** (máscara, traço que preenche), leve parallax, troca no lugar | não estudado |

## No nosso motor
- As gravuras já entram como `papelizar(estilo="gravura")`; falta o **preto e branco puro com acento** (`cor=0` + máscara de cor por órgão).
- Camadas de órgão com `levanta` e `destaca/pousa` valem como estão; o diferencial é **tirar a cor** de tudo menos o órgão em foco.
- Diagrama técnico: `Traco` fino cinza com setas e círculos; números em serifada fina.

## Riscos
- Preto e branco com uma cor pode ficar **frio e sem vida**; precisa de **vida sutil** (pulsa, respira) e de som forte.
- Gravuras antigas têm anatomia desatualizada: conferir o fato no texto, não na imagem.
