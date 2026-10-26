# Ficha de estilo: flap-book-abas

**Quando usar:** revelar o corpo **abrindo abas** como nos livros anatômicos do século XVI: a pele é uma aba que levanta e mostra o músculo, que levanta e mostra o osso. É a **origem histórica** das nossas camadas, e dá "autoridade" ao vídeo.

**Evidência:** R06 Duke (**vista**: 2 quadros do vídeo de 10 min), R07 e R08 (citadas), I01 (nosso manequim). Fonte histórica verificada: Vogtherr (Estrasburgo, 1538), Vesalius (*Epitome*, 1543), Remmelin (1613).

## O sistema
| item | regra |
|---|---|
| mecânica | cada camada é **uma aba presa por uma dobradiça** (esquerda, direita, topo); ao abrir, **gira na dobradiça**, escurece de lado, mostra o **verso de papel** |
| camadas | de cima para baixo: pele → músculo → vísceras → osso; o **desenho de baixo já existe inteiro** (registrado) |
| câmera | **mostrar a dobradiça**: sem ela a aba parece deslizar (lição da técnica de camadas, skill `colagem-camadas`) |
| som | **papel pesado** (folhear, aba), um efeito por ação |
| fonte de arte | **gravuras de domínio público** (Gray, Vesalius, Wellcome); não precisam de crédito legal, mas dar crédito do acervo |

## No nosso motor
- Já existe: `K.aba` (dobradiça, perspectiva `kx`, verso), `K.metades` (duas portas), `K.descasca`.
- Falta: **verso com texto de época** (página de livro) e **sombra da dobradiça**; dobradiça visível sempre.
- Regra do estilo: sem legenda embaixo; rótulo curto preso à aba.

## Riscos
- Aba demais vira "livro infantil"; usar **no máximo 3 abas** por vídeo, cada uma com um porquê.
- Gravuras antigas têm erros anatômicos; checar fatos no texto.
