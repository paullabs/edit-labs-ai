# Banco de referências: guia completo

Memória de **estilo** do plugin: o que já vimos de bonito, o que cada obra ensina, e **as receitas** para usar isso num vídeo novo. Começou na pesquisa de um vídeo do corpo humano, mas vale para **qualquer assunto**. Resumo curto em `LEIA.md`.

O banco guarda **só texto**: título, autor, link, licença declarada e a nossa análise. Quadros, vídeos e áudios de terceiros não entram; para ver uma obra, **abra o link**.

## Como está organizado
| o quê | onde | para quê |
|---|---|---|
| **Catálogo** (fonte única) | `catalogo.json` | cada referência com autor, link, licença declarada, tema, estilo, mecânicas, **profundidade** e análise |
| Catálogo legível | `CATALOGO.md` | gerado do JSON, por estilo, por mecânica e por tema |
| **Fichas de estilo** | `fichas-de-estilo/*.md` | a receita de cada estilo: papel, cor, tipografia, composição, textura, movimento, **como fazer no motor e no invideo**, riscos |
| Paletas | `paletas/paletas.json` | cores **medidas** (Vox e outras) e as do motor de colagem, lado a lado |
| Análises a fundo | `analises/` | estudos de uma obra (R03, R23, guia Vox, Style Bible) |
| Modelo de brief | `modelo/BRIEF_DE_ESTILO_modelo.md` | o que preencher **antes** de cada vídeo novo |
| Ferramenta | `ferramentas/refs.py` | `listar`, `ver`, `estilo`, `mecanica`, `adicionar`, `validar`, `gerar` |

Referências **internas** (texto nosso, não cópia de ninguém): `I01` manequim de 1890 (o vídeo de exemplo não vem no repositório; a técnica está na skill `colagem-camadas`), `I02` guia de estilo Vox (`analises/vox-guia-de-estilo.md`), `I03` Style Bible do estilo Vox explainer e referências da skill `motion-vox` (`analises/vox-style-bible.md` e `../skills/motion-vox/referencias/`).

## Os 8 estilos
| estilo | usar para | ref principal | profundidade |
|---|---|---|---|
| `vox-clean` | dados, comparações, pessoas sem rosto; tom editorial | R03 Two Parties, R25 Porsche | **a fundo** |
| `gravura-bw-acento` | anatomia e ciência "livro antigo vivo", uma cor de acento | R11 Longevity Hackers | vista |
| `papel-cortado-camadas` | corpo como pilha de recortes com sombra | R13 Gildersleeve, I01 | citada / nosso |
| `flap-book-abas` | revelar camadas abrindo abas, como nos livros do século XVI | R06 Duke | vista |
| `colagem-barroca` | abertura, capa, interlúdio: anatomia como arte | R01 T. Dorje | vista |
| `colagem-documental` | contar uma história com documentos de época | R04 Naeem, R12 Fromsquare | vista |
| `recorte-ritmo-textura` | abertura e transições com ritmo de recorte | R09 Fakeplastictree | vista |
| `documentario-dramatico` | drama em documento: medo, perda, espera; foto P&B granulada em moldura de negativo, um vermelho só | R23 MiraRuido | a fundo |

## Escolher o estilo de um vídeo (guia rápido)
| o vídeo é... | estilo principal | apoio |
|---|---|---|
| "como é por dentro" (corpo, máquina) | `flap-book-abas` ou `papel-cortado-camadas` | `gravura-bw-acento` nas peças |
| "quanto / quantos / compare" (números, grupos) | `vox-clean` | `gravura-bw-acento` para o órgão |
| "a história de..." (descoberta, doença) | `colagem-documental` | `flap-book-abas` |
| drama em documento: medo, perda, espera (pessoas, história de doença) | `documentario-dramatico` | `flap-book-abas` para o corpo |
| abertura ou capa, 3 a 5 s | `recorte-ritmo-textura` ou `colagem-barroca` | — |

**Regra:** um estilo principal, **no máximo um** de apoio. `colagem-barroca` e `vox-clean` brigam (um enfeita, o outro esvazia): não juntar.

## Como usar num vídeo novo (4 passos)
1. **Consultar:** `python3 -I ${CLAUDE_PLUGIN_ROOT}/referencias/ferramentas/refs.py estilo <nome>` e ler a ficha.
2. **Brief:** copiar `modelo/BRIEF_DE_ESTILO_modelo.md` para a pasta do vídeo e preencher (estilo, paleta, regras de clean, refs usadas). O usuário aprova **antes** do roteiro.
3. **Construir** com o motor, seguindo "No nosso motor" da ficha.
4. **Depois de pronto**, se o vídeo ensinou algo, **atualizar a ficha** e a profundidade das referências.

## Como acrescentar uma referência
```
python3 -I ferramentas/refs.py adicionar --id R26-autor-obra --titulo "..." --autor "..." --url https://... \
  --tipo video --prof vista --tema anatomia --estilo vox-clean --mecanica marca-texto \
  --licenca "todos os direitos reservados" --nota "o que ensina"
```
O comando valida e regera o `CATALOGO.md`. Link (`--url`) e licença declarada (`--licenca`) são obrigatórios; se a fonte não diz a licença, escreva `desconhecida; tratar como todos os direitos reservados`. **Não baixe nem salve mídia de terceiros** no banco. Para virar `a-fundo` é obrigatório ter um arquivo em `analises/` (o validador cobra).

## Regras do banco
- **Profundidade honesta.** `a-fundo` = quadros do vídeo, texto e medidas; `vista` = abri e olhei; `citada` = só apareceu numa busca ou artigo (**não confiar nos detalhes**).
- **Direitos.** Tudo é referência de estudo; nunca copiar imagem ou animação. Se precisar de material, usar domínio público (Wellcome, Gray, Duke) com crédito do acervo.
- **Autoria só quando confirmada** (o pin da MSF não confirma estúdio: não creditar).
- Cada afirmação de ficha diz de qual referência vem; **hipótese** é marcada como hipótese.

## Fila de aprofundamento (o que mais vale estudar)
| prioridade | referência | o que falta |
|---|---|---|
| 1 | R11 Longevity Hackers | **assistir o vídeo inteiro** (Vimeo) e transformar a ficha `gravura-bw-acento` de hipótese em receita medida |
| 2 | R13 Gildersleeve | **ver as imagens do livro** e medir camadas, cores e sombras |
| 3 | R02 Epigenetics | estudar como o corpo e o DNA são animados (mesmo autor do R03) |
| 4 | R06 Duke | assistir os 10 minutos e anotar como cada aba abre, pesa e revela (alimenta `K.aba`) |
| 5 | R12 Fromsquare educativas | ver os 6 vídeos (Vimeo) e anotar texturas e acentos |
| 6 | R01 T. Dorje | ver as obras em movimento (GIFs no Behance) |
| 7 | R23 MiraRuido | **feito em movimento** (99 s medidos); falta só **ouvir o áudio** (narração e trilha) |
