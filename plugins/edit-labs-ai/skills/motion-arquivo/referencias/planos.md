# Catálogo de planos

Cada plano do `plano.json` tem `tipo`, `inicio` e `fim` (quadros absolutos a 30 qps, na grade:
`inicio % 3 == 2`, exceto o primeiro, 0) e os parâmetros do tipo. Tempos de palavra vêm de
`ferramentas/batidas.py`: `quadro` = degrau em que a palavra aparece; `t` = instante exato da
fala em quadros (com fração), usado nos fades contínuos. Os padrões são os números medidos
no Hedy — mude só o que o conteúdo pede. Código em `motor/planos.py`.

Qual plano para qual batida: `gramatica.md` §9.

---

### `gancho_digitado` — a palavra que abre (Hedy 1)
Papel quadriculado escuro + grotesca digitada; só a letra nova se mexe; câmera fecha
0,764 → 1; sai escorregando com borrão no último degrau.
```json
{"tipo": "gancho_digitado", "inicio": 0, "fim": 20, "texto": "NINGUÉM"}
```
Opcionais: `primeira_letra` (padrão inicio+2), `fundo` ("grade" | "preto"), `centro`
[529, 958], `saida` (true). Palavra longa diminui sozinha até 80% da largura.

### `palavra_no_papel` — a fala, uma palavra por vez (Hedy 10, 16)
```json
{"tipo": "palavra_no_papel", "inicio": 566, "fim": 617,
 "palavras": [{"texto": "Virou", "quadro": 566}, {"texto": "a base", "quadro": 578}, {"texto": "de tudo", "quadro": 599}]}
```
Cada palavra fica até a próxima entrar (ou `ate`). Pausa na fala: ponha `ate` antes da
próxima para sobrar papel vazio. Opcionais por palavra: `corpo` (86), `centro`.

### `foto_pullout` — foto de arquivo com deriva (Hedy 8, 9, 11, 18, 19, 21)
```json
{"tipo": "foto_pullout", "inicio": 170, "fim": 209, "foto": "fabrica_1950.jpg",
 "zoom": [1.10, 1.0], "deriva": [[-72, 72], [59, -59]], "pb": true, "ganho": 0.8,
 "texto": {"texto": "Em 1952", "quadro": 173, "largura": 400, "esquerda": 320, "yc": 950}}
```
Opcionais: `ponto` (px da foto que vai ao centro), `curva` ("saida" | "entrada" | "linear" |
"s") e `potencia` (1,5), `ganho` (número ou [r,g,b]), `saturacao`, `desfoque_saida`
`{"de": q, "sigma": 14}` (casar foco com o plano seguinte), no texto `letras_por_degrau` (1)
e `letras_inicio`, `cor`.

### `cartao_rotulo` — como a coisa é vista (Hedy 2–3)
Foto em cartão no papel, objeto de base opcional, rótulo serifado pequeno com seta à mão.
```json
{"tipo": "cartao_rotulo", "inicio": 20, "fim": 32, "foto": "retrato.jpg", "rotulo": "o rosto da marca",
 "lado": "dir", "base": "corda_veludo.png", "camera": {"zoom": [1.0, 0.976], "dx": [0, -73]}}
```

### `figura_e_palavras` — "ninguém percebeu" (Hedy 4)
Recorte P&B com uma cor (`melhorar.py pb-cor`) no papel, pan em S; palavras pequenas em fila acima.
```json
{"tipo": "figura_e_palavras", "inicio": 47, "fim": 92, "figura": "plateia.png",
 "palavras": [{"texto": "quase", "quadro": 50, "x": 285}, {"texto": "ninguém", "quadro": 62, "x": 502},
              {"texto": "notou", "quadro": 74, "x": 735}]}
```
Opcionais: `altura` 760, `y` 760, `x` 60, `pan` −167, `y_palavras` 690, `corpo` 38.

### `documento_digitado` — a prova (Hedy 5)
Documento desbotado em bege; frase digitada com cursor; termo-chave com seleção azul; câmera
mergulha no cursor (1,85×) e abre rápido nos 3 últimos quadros.
```json
{"tipo": "documento_digitado", "inicio": 92, "fim": 140, "documento": "patente.jpg",
 "frase": "ELA AJUDOU A CRIAR A TECNOLOGIA", "destaque": "TECNOLOGIA",
 "quadro_digitar": 96, "quadro_selecao": 116, "quadro_zoom": 116}
```
Opcionais: `ponto_doc` [0,48, 0,48] (fração da página que vai ao centro), `escala_doc` 1,25,
`largura_inicio` 215 (largura das duas primeiras palavras), `letras_por_quadro` 1,
`esquerda` 330, `yc` 958, `alvo_cursor` [810, 910].

### `objeto_revela` — está aqui hoje (Hedy 6–7)
Preto; câmera abre 1,7 → 1 em torno de (540, 990) enquanto o objeto ainda sobe; domo teal
(a onda) sobe e cobre o quadro; legenda grotesca com fade por palavra na fase da fala.
```json
{"tipo": "objeto_revela", "inicio": 140, "fim": 170, "objeto": "celular.png", "ponto_objeto": [389, 533],
 "legenda": {"palavras": [{"texto": "NO", "t": 140.5}, {"texto": "SEU", "t": 145.6}, {"texto": "BOLSO.", "t": 148.7}]}}
```
Opcionais: `largura_objeto` 572 (largura da tinta), `centro_objeto` [541,5, 1230],
`ponto_objeto` (px do asset que cai no centro — o corpo, não as antenas), `onda` (true),
`cor_onda` [−0,06, 0,90, 0,97] por canal, na legenda `maiuscula` 55, `tracking`, `x`, `y`, `cor`.

### `lista_ui` — o legado (Hedy 17)
Radar pulsando; caixas azuis entram pela direita em escada; chicote de saída opcional.
```json
{"tipo": "lista_ui", "inicio": 617, "fim": 698, "saida_desde": 650,
 "itens": [{"texto": "Pix", "quadro": 620}, {"texto": "Cartão", "quadro": 647}, {"texto": "Boleto", "quadro": 668}]}
```
Ponha o `quadro` do item 2–7 quadros ANTES da fala. Opcionais por item: `x`, `y`.

### `odometro` — o tempo passa (Hedy 14)
```json
{"tipo": "odometro", "inicio": 503, "fim": 536, "de": 1974, "ate": 2024, "passo": 5}
```
Opcionais: `duracao` 30 (quadros da rolagem), `corpo` 90.

### `moldura_legenda` — a conclusão (Hedy 20)
Foto na moldura dourada do kit; câmera abre 1,75 → 1 saindo de foco puxado; legenda 1–2
linhas palavra a palavra.
```json
{"tipo": "moldura_legenda", "inicio": 758, "fim": 824, "foto": "retrato_cor.jpg", "ganho": 0.62, "saturacao": 0.55,
 "legenda": [[{"texto": "a história", "quadro": 770}, {"texto": "lembra", "quadro": 773}],
             [{"texto": "pela", "quadro": 776}, {"texto": "cabeça.", "quadro": 788}]]}
```
Opcionais: `moldura` (do kit), `ponto`, `zoom_foto`, `largura_legenda` 484,5, `y_linhas`.

### `icone_cursor` — a ação (Hedy 22)
Ícone REAL (`assets_locais.py icone`) e cursor REAL (`assets_locais.py cursor pointinghand`);
câmera abre 2,43 → 1; o dedo chega, agarra e arrasta nos 4 últimos degraus.
```json
{"tipo": "icone_cursor", "inicio": 845, "fim": 905, "icone": "icone_adobe_after_effects_2026_aep.png",
 "cursor": "cursor_pointinghand.png"}
```
Opcionais: `cor_icone` (mapa por canal de `melhorar.py casar-cor`), `largura_icone` 120,
`largura_cursor` 57, `centro`, `fundo` ("dobras" | "liso"), `arrasto` (true).

### `site_url` — o destino (Hedy 23)
Print REAL do site (`tela`) com a URL digitada; sem `tela`, página genérica.
```json
{"tipo": "site_url", "inicio": 905, "fim": 960, "tela": "site_print.png", "url": "seusite.com", "barra": [210, 180, 34]}
```
Opcionais: `quadro_digitar` (inicio+7), `desfoque`, `ganho`.

### `queda_objeto` — uso ou alerta (Hedy 12)
Céu; o objeto sobe, etiqueta rasgada com letras sorteadas, vira vermelho e cai girando.
```json
{"tipo": "queda_objeto", "inicio": 407, "fim": 449, "objeto": "foguete.png", "rotulo": "falha no lançamento"}
```
Opcionais: `altura` 660, `vira_cor` 24, `cai` 27 (quadros desde o início), `cor_alerta`.

### `palavras_e_figura` — o mecanismo (Hedy 10)
Palavras soltas e depois uma figura entra deslizando da direita com rótulo e título.
```json
{"tipo": "palavras_e_figura", "inicio": 248, "fim": 359, "quadro_figura": 296, "figura": "diagrama.png",
 "palavras": [{"texto": "não", "quadro": 251}, {"texto": "era só", "quadro": 260}],
 "rotulo_pequeno": {"texto": "ela criou um", "quadro": 302},
 "titulo": {"texto": "Sistema de Comunicação", "largura": 675, "partes": [{"texto": "Sistema", "quadro": 320},
            {"texto": "Sistema de Comunicação", "quadro": 335}]}}
```
Opcionais: `altura_figura` 1100, `pos_figura`.

### `objeto_na_parede` — ambiente (Hedy 15)
```json
{"tipo": "objeto_na_parede", "inicio": 536, "fim": 566, "objeto": "quadro_negro.png"}
```
Opcionais: `largura` [1000, 1390], `y` 900.

### `amassar_lixeira` — recusa (Hedy 13)
A folha (`folha`, imagem do papel do plano anterior) amassa larga e cai na lixeira.
```json
{"tipo": "amassar_lixeira", "inicio": 449, "fim": 503, "lixeira": "lixeira.png", "folha": "folha_plano10.png"}
```
Opcionais: `boca_tela` [576, 585], `bola` (do kit), `ganho`.


---

## Camada comum a todos os planos (rótulo, rodapé, legenda)

Qualquer plano aceita, ao lado dos próprios parâmetros:

```json
{"rotulo": "02 / O MERCADO NOVO", "rodape": "Fonte: IBGE · 260 de 513 cidades", "sem_legenda": false}
```
`rotulo` e `rodape` (fonte do dado, crédito da foto) ficam no alto à esquerda, dentro da zona segura (v12.7: o crédito
saiu do pé da tela, que fica embaixo da legenda do Instagram; `rodape_pos`/`rotulo_pos` mudam o lugar; sobre papel claro o
crédito sai em tinta escura) e a `legenda` global do `plano.json` mostra a frase falada com a palavra já dita acesa:
```json
"legenda": [{"inicio": 330, "fim": 410, "palavras": [{"w": "Pouco", "quadro": 332}, {"w": "mais", "quadro": 338}]}]
```
Tudo é desenhado antes do acabamento: leva a mesma scanline e o mesmo RGB split da cena.
`sem_legenda: true` desliga a legenda no plano (nos ganchos de palavra no papel, a própria
palavra grande já é a legenda).

### `foto_pullout` — caixas sobre a foto
```json
"caixas": [{"texto": "frete grátis acima de R$ 99", "quadro": 1380, "x": 110, "y": 1230}]
```
Caixa azul de interface que entra pela direita (largura acompanha o texto).

### `barras_placar` — resultado em barras (pesquisa, ranking, comparação)
Barras cor de papel crescem do chão (ease-out) com o número contando; selo carimbado em pop.
```json
{"tipo": "barras_placar", "inicio": 302, "fim": 545, "rotulo": "01 / O CENÁRIO",
 "barras": [{"nome": "Modelo A", "valor": 47.03}, {"nome": "Modelo B", "valor": 45.16}],
 "selo": {"titulo": "FINAL", "sub": "25 DE OUTUBRO"}, "quadro_selo": 410}
```
Opcionais: `escala` (14 px por ponto), `base_y` (1130), `y_selo` (245).

### `dezena` — proporção que se enxerga (público iniciante)
Fileiras de 10 pessoas que acendem uma a uma; a última com a fração. Linhas de marca e anel
no que falta. Troca "260 de 513" por "pouco mais de 5 em cada 10".
```json
{"tipo": "dezena", "inicio": 668, "fim": 1028, "rotulo": "02 / QUEM JÁ TEM",
 "linhas": [{"rotulo": "ESCOLAS", "valor": 5.07, "inicio": 0, "passo": 5, "numero": "260 de 513 · com internet", "y": 700},
            {"rotulo": "HOSPITAIS", "valor": 5.93, "inicio": 130, "passo": 5, "numero": "48 de 81 · com internet", "y": 1120}],
 "marcas": [{"valor": 6, "texto": "seis em cada dez · a meta", "quadro": 900}],
 "falta": [{"linha": 1, "icone": 5, "texto": "falta 1", "quadro": 960}]}
```
`inicio` negativo (-999) = já acesa. `passo` = quadros por pessoa (3 = uma por degrau).


---

## v8 — figura no lugar de texto (números, comparação, dois lados)

- **`palavras_grandes`** (em qualquer plano): `[{"texto": "A FAVOR", "quadro": 330, "ate": 400, "y": 1400}]` —
  1 a 3 palavras em serifa grande, com pop de entrada. É a única camada de texto recomendada.
- **`barras_placar`**: a barra pode levar `foto`, `ponto` e `lado` (retrato redondo sob ela); `selo`
  é uma string curta ("25/10"). Sem nome escrito.
- **`dupla_retratos`**: tela dividida com duas fotos P&B escurecidas, sem texto
  (`fotos`, `pontos`, `ganho`).
- **`dezena`**: cada linha pode levar `predio` (o desenho do prédio no lugar do rótulo: "camara" = cuia, "senado" = cúpula);
  `marcas` com `texto` curto ("1/2", "6/10"); `falta` com "+1".
- `rotulo`, `rodape` e `legenda` continuam disponíveis, mas **não use** sem pedido explícito.


---

## v9 — papel e tinta (explicativo: número, comparação, "o que acontece se")

Sobre o **papel** da Família A (nunca sobre preto), foto **colorida** de arquivo e figura desenhada a **tinta**,
com azul de interface como único acento (vermelho só para recusa/veto). Cada tipo é a figura que uma frase
nomeia — nunca um rótulo. Margens: texto e figura em x 90–990 / y 250–1500.

### `calendario` — a data
Folha de calendário de parede; na fala do dia a folha anterior levanta, gira na dobradiça e some em 3 degraus.
```json
{"tipo": "calendario", "inicio": 0, "fim": 62, "mes": "outubro", "dia": 25, "dia_antes": 24, "quadro_troca": 29}
```

### `hemiciclo` — o plenário (quem tem a maioria)
Cada cadeira é um ponto; a bancada acende da DIREITA para o centro; cruzar a linha do meio é "mais da metade".
Uma ou mais câmaras (`figuras`), câmera que viaja entre elas, limiares radiais (1/2, 3/5), `falta` (as próximas
cadeiras em azul pulsando), `apaga` (esmaece quando a câmera sai) e `numerais`/`setas`.
```json
{"tipo": "hemiciclo", "inicio": 230, "fim": 392,
 "figuras": [{"total": 513, "centro": [540, 930], "raio": 390, "acende": {"de": 232, "ate": 295, "k": 260},
              "metade": {"quadro": 256}, "apaga": {"de": 320, "alfa": 0.22},
              "numerais": [{"texto": "1/2", "quadro": 256, "ate": 295, "pos": [540, 395], "corpo": 170}]},
             {"total": 81, "centro": [540, 1400], "raio": 300, "entra": 320, "acende": {"de": 326, "ate": 372, "k": 48}}],
 "camera": [{"quadro": 230, "ancora": [540, 880], "z": 1.12}, {"quadro": 314, "ancora": [540, 880], "z": 1.12},
            {"quadro": 332, "ancora": [540, 1240], "z": 1.12}]}
```
Voto que falta: `"falta": {"quadro": 140, "n": 1}` + `"limiares": [{"quadro": 122, "fracao": 0.6}]`.

### `pizza` — "mais da metade"
Círculo que se enche no sentido horário; metade em tinta, o que passa em azul; linha tracejada no meio.
`{"tipo": "pizza", "inicio": ., "fim": ., "valor": 0.53, "acende": {"de": ., "ate": .}, "metade": {"quadro": .}}`

### `termometro` — "seis em cada dez"
Dez blocos que acendem de baixo para cima; linha do limite com o numeral.
`{"tipo": "termometro", "valor": 6, "de": 0, "limite": {"valor": 6, "quadro": ., "texto": "6/10"}}`

### `dezena` (tema papel, grade 2×5) — proporção com gente
`{"tipo": "dezena", "tema": "papel", "colunas": 5, "linhas": [{"valor": 5.0, "inicio": -999, "y": 700}],
 "falta": [{"linha": 0, "icone": 5, "texto": ""}], "marcas": [{"valor": 6, "texto": "+1/10", "quadro": ., "pos": [540, 1290]}]}`

### `carimbo` — a decisão
Folha (a lei) e a palavra carimbada em vermelho: chega grande, bate em 2 degraus, a folha afunda, câmera treme.
Tinta multiplicativa com falhas. `{"tipo": "carimbo", "texto": "APROVADA", "quadro_carimbo": 1058}`
Quando a folha volta em outro vídeo da série, ela não pode ser a mesma cena: varie `fundo` (papel, canvas, parede),
`tamanho_folha` [larg, alt] (deitada: [820, 620]), `semente` (o desenho das linhas), `rot`, `centro`, `rot_carimbo`,
`dx`/`dy`, `cor` (azul para "a fazer") e o enquadramento: `zoom` [z0, z1] com `foco` [x, y] (de perto: [1.62, 1.75]
em torno do título; abrindo: [1.22, 1.08]).

### `selecao_digitada` — a sigla
Hedy "THE |TECHNOLOGY|": letras aparecem cada uma no instante em que são ditas, cursor, caixa de seleção azul,
câmera mergulha. `{"tipo": "selecao_digitada", "texto": "NASA", "letras": [q1, q2, q3, q4], "quadro_selecao": q5}`

### `duas_molduras` — o "contra"
Dois retratos em moldura dourada, cada um entra na palavra do nome, legenda em serifa. `x`, `ys`,
`tamanho_ouro`; por item `foto`, `ponto`, `quadro`, `legenda`, `legenda_pos`.

### `dois_lados` — "negociar"
Pessoa e a silhueta de uma instituição (o desenho de um parlamento) com setas de ida e volta que se desenham uma depois da outra.

### `encontro` — duas fotos que se encontram (negociar, comparar)
`{"tipo": "encontro", "fotos": ["a.jpg", "b.jpg"], "pontos": [[x, y], [x, y]]}`

### `objeto_no_papel` — o objeto real
Recorte de foto de produto/objeto (`melhorar.py recorte`) no papel com sombra mole, sobe e assenta. É o
"objeto 3D" do Priming feito com foto de verdade.

### `baloes` — "todo mundo falando"
Balões de fala que estouram um por degrau da fala. `cada` = quadros entre balões.

### Extensões de tipos antigos
- `palavra_no_papel`: `seta` `{"lado": "dir|esq|baixo|cima", "quadro": q, "y": 1120}` (seta a mão que se
  desenha) e, por palavra, `cor` e `queda` (a palavra cai girando, como o torpedo do Hedy).
- `foto_pullout`: a janela nunca passa da borda da foto (sem faixa preta); `palavras_grandes` sobre foto leva
  sombra; `hud_dezena` desenha dez pessoas sobre a foto (nunca sobre foto de pessoa identificável).
- `lista_ui`: caixa de largura automática para texto longo.

**Regra de montagem que o script confere:** nenhum asset duas vezes no mesmo vídeo; nenhum plano > 2,65 s
(exceto figura que viaja a câmera); palavra grande nunca sobre rosto.


---

## v10 — looks por conteúdo (as 4 referências, cada uma onde faz melhor)

Não é "um estilo": cada tipo de conteúdo ganha o look da referência que o faz bem. Qualquer plano de
diagrama/calendário aceita `"fundo": "papel" | "canvas" | "parede"`.

| conteúdo | look | referência | tipos |
| --- | --- | --- | --- |
| palavra, carimbo, folha | papel cinza, grão | Hedy | `palavra_no_papel`, `carimbo` |
| retrato, data | parede cinza com luz de janela, moldura dourada com sombra | galeria documental | `galeria`, `calendario` (`fundo: parede`) |
| diagrama, número, objeto 3D | canvas claro quadriculado + piso em perspectiva | Priming | `hemiciclo`, `pizza`, `termometro`, `dezena`, `dois_lados` (`fundo: canvas`), `canvas_objeto`, `pictograma` |
| frase de gancho | preto, régua nas bordas, curva fina, texto creme que acende desfocado | Outreach | `hud_texto` |
| interface | radar + caixas azuis | Hedy | `lista_ui` |
| prova | foto cheia colorida com palavra serifada | galeria documental | `foto_pullout` |

### `galeria` — a abertura (retratos + o povo)
Molduras douradas penduradas na parede (sombra, legenda em serifa italica) e o **povo de costas** embaixo,
cada grupo sob a sua moldura (47 e 45: a proporção como gente, sem número). `povo.destaque` pinta o
grupo de azul quando a fala fala dele; `povo.voce` põe UMA pessoa azul ("você escolhe"); `baloes`
("todo mundo falando"); `palavras` sobre a parede, com `queda` (a palavra cai).
```json
{"tipo": "galeria", "inicio": 0, "fim": 56,
 "itens": [{"foto": "inventora.jpg", "ponto": [760, 1100], "quadro": 2, "legenda": "Ana"},
           {"foto": "inventor.jpg", "ponto": [760, 1000], "quadro": 8, "legenda": "Bruno"}],
 "camera": {"z": [1.16, 1.0], "foco": [540, 800]},
 "povo": {"quadro": [14, 18], "n": [47, 45], "destaque": [{"grupo": 1, "quadro": 60, "ate": 120}]},
 "baloes": [{"inicio": 30, "cada": 3}]}
```

### `hud_texto` — a frase do gancho
```json
{"tipo": "hud_texto", "inicio": 107, "fim": 164, "linhas": [{"texto": "VAI MUDAR", "quadro": 110, "corpo": 130},
 {"texto": "TUDO", "quadro": 122, "corpo": 250, "caixa": true}]}
```
Texto creme entra desfocado (σ 10 → 0 em 2 degraus), `caixa` fecha a seleção azul; `curva: false` tira a curva.

### `canvas_objeto` — objeto 3D (look Priming)
Canvas claro quadriculado com piso, UM objeto em cinza (contraste puxado) com sombra mole, 1–3 palavras
(a pequena clara, a grande escura) que entram desfocadas, círculo fino e caixa tracejada; câmera viaja ~1 s e para.
```json
{"tipo": "canvas_objeto", "inicio": 560, "fim": 596, "objeto": "obj3d_dinheiro.png", "largura": 800,
 "palavras": [{"texto": "zero", "quadro": 566, "x": 500, "y": 560, "corpo": 170, "peso": 700}],
 "circulo": {"quadro": 576, "raio": 450}}
```
`cinza: false` mantém a cor; `piso: false` tira o piso.

### `pictograma` — "sozinha"
Uma pessoa grande, em tinta, sozinha no canvas; `quadro_fantasmas` faz chegar, tracejados, os votos que faltam.


---

## v11 — a notícia explicada (`motor/planos_noticia.py`)

Para a notícia explicada: IA contra IA, notícia de tecnologia, "viralizou, é verdade?". Os tipos desenham o que a
notícia NOMEIA — sem logotipo: nome de empresa só em tipografia; celular, app e chat são desenhos genéricos.
Câmera comum a todos: `"camera": [{"quadro", "ancora": [x, y], "z"}]` (a âncora vai para o centro; viagem em S
entre as chaves) ou, sem chaves, revelação de entrada + empurrão lento. Fundos: `canvas` (padrão), `papel`, `parede`.

| tipo | a fala | o que faz |
| --- | --- | --- |
| `ranking` | "bateu o Opus", "ficou em 1º" | lista de posições (look radar do Hedy ou canvas); a linha entra pela direita e **ultrapassa** a outra (`trocas`); marcas ▲▼ e círculo a mão |
| `terminal` | "no teste de programação" | janela escura, texto monoespaçado digitado, seleção azul na linha que importa, cursor em bloco |
| `podio` | "em primeiro... em terceiro" | três blocos no piso do canvas; a etiqueta CAI no bloco na palavra; `circulos` no número |
| `barras` | "15 dólares contra 32" | 2–3 barras com o número contando; `muda` (a barra sobe/desce depois: "custa o mesmo"), `linha` tracejada com "=" |
| `centena` | "15% das vezes", "99 anulam e 1 vota" | 10×10 (pessoas ou quadrados); `grupos` mudam de cor na batida; `um` com anel pulsando; `titulo` |
| `pizzas` | "50% contra 66%", "só conta quem respondeu" | uma ou mais pizzas; valor único ou `fatias` (as opções, com `destaque` que salta); `fora` (quem ficou de fora) |
| `celular` | "no seu celular, em modo avião" | telefone desenhado: barra de status (`aviao`), `cabecalho`, `conversa` (bolhas, "digitando", imagem, ✓/✗), `download`, `canal` (contador, derrubado, volta), `nuvem` com seta e X, `carimbo` sobre a tela, `etiqueta` (entra pela direita; `"entra": "pop"` cresce no lugar, para câmera fechada sem cruzar os botões do Reels) |
| `icones` | "dinheiro por fora", "sem sinal", "48 horas" | ícones a tinta: nota, wifi, sinal, nuvem, cadeado, relógio (gira), engrenagem, avião, jornal, terminal, imagem, celular, pessoa, tecla de urna, cuia e cúpula (prédios de parlamento); `rotulo`, `certo`, `xis`, `risco`, `setas` (com X), `ligacoes` (rede), `textos`, `divisor` (dois painéis) |
| `semana` | "em uma semana" | tira de calendário na parede; os dias acendem em sequência. Não usar como "quinta, dia 8 / sexta, dia 9" a cada fato: data solta entra seco e o ouvinte perde o fio (`referencias/texto.md`) |
| `linha_no_papel` | "promessa não é entrega" | uma linha montada palavra a palavra, cada uma com sua cor e `risco`; ≠ ← → ✓ × saem na Inter (a serifa não tem) |
| `botao_cta` | "Segue o perfil" | botão "Seguir" com o **cursor real do macOS** (`assets/reais/cursor_pointinghand.png` + json do hotspot) que chega, clica e vira "Seguindo"; palavras acima/abaixo |

```json
{"tipo": "ranking", "inicio": 0, "fim": 98, "fundo": "radar", "vagas": 2,
 "itens": [{"pos": 1, "texto": "Opus 5.5", "quadro": 2, "cor": "cinza", "marcas": [{"tipo": "cai", "quadro": 56}]},
           {"pos": 2, "texto": "Gemini 4 Argon", "quadro": 26, "cor": "azul"}],
 "trocas": [{"quadro": 41, "ordem": ["Gemini 4 Argon", "Opus 5.5"]}]}
```
```json
{"tipo": "celular", "inicio": 0, "fim": 116, "aviao": 104, "etiqueta": {"texto": "GRÁTIS", "quadro": 23},
 "cabecalho": {"titulo": "IA do Google", "sub": "no aparelho"},
 "conversa": [{"lado": "eu", "texto": "Traduz essa frase?", "quadro": 41}, {"lado": "ia", "texto": "Claro.", "quadro": 77, "pensa": 47}],
 "camera": [{"quadro": 0, "ancora": [540, 960], "z": 1.0}, {"quadro": 107, "ancora": [640, 430], "z": 2.1}]}
```

**Lições:**
- O texto do celular é de interface (34–38 px): a câmera ENTRA na fala que importa (z 1,3–1,7), senão não se lê.
- Papel vazio antes da palavra (0,8–1,4 s) é o defeito mais comum: começar pela palavra anterior da frase, pôr o
  balão com reticências, ou repetir a figura do capítulo (a semana) — nunca deixar o papel parado.
- A mesma figura com outro estado vale mais que um plano novo sem relação: dois painéis (✓ / ✗ → "a regra"), a
  barra que sobe até a outra ("custa o mesmo"), a mesma pergunta respondida de dois jeitos, os cem do começo no fim.
- Cena reenquadrada (corte para perto) é marcada `"continua": true` no montador: não conta como asset repetido.
- Voz do ElevenLabs sai a ~−21,5 LUFS: a entrega leva `loudnorm` (alvo −14, pico −1,5; o linear para em ~−15,5).

## v12 — a galeria documental (`motor/planos_galeria.py`)

Medida quadro a quadro na abertura de uma referência de terceiros (0–11,8 s; crédito no `SKILL.md`, nenhuma mídia no
plugin) e reconstruída com a mesma régua. A galeria é a Família A com outro relógio e outra pele:

| no projeto (`plano.json`) | o que faz | medido |
| --- | --- | --- |
| `"cadencia": 15` | o quadro muda a cada 2 quadros | padrão `=x=x`; a 30 só em trechos rápidos |
| `"fase_por_plano": true` | cada plano conta os degraus do próprio corte | os cortes da referência caem em 154, 221 e 259 |
| `"acabamento": "galeria"` | linhas de CRT **verticais**, split e grão leves | período 7,97 px em 1080, 5% de contraste |
| `"pouso": {"sigma", "quadros"}` (no plano) | o corte entra desfocado e foca | nitidez 0,61 → 1,0 em 9 quadros (jornais: 0,14) |
| `"trechos_30qps": [[a, b]]` (no plano) | trecho a 30 qps | o empurrão rápido na moldura e o pouso dos jornais |

| tipo | quando | o que faz |
| --- | --- | --- |
| `moldura_entra` | abertura, "em 2022" | parede com luz de janela e moldura dourada fina; a câmera entra (ouro de 297 a 716 px em 720 até 1,7 s, lento até 1,2 s e rápido depois, com borrão de zoom); a abertura estica até virar a tela (largura em 7 quadros, altura até q69); foto P&B → cor no empurrão; `frases` trocam sobre o peito, presas à foto |
| `foto_recorte` | a pessoa, o objeto que importa | foto P&B com o sujeito em cor (máscara do `ferramentas/recorte.swift`, Vision, local e de graça); empurra 1,0 → 1,19 em 25 quadros; `bloco` monta palavra a palavra **atrás do sujeito**; `virada`: desfoca, escurece a 45% em 14 quadros, a frase nova entra à direita e o **sublinhado amarelo cresce do meio para as pontas** em 15 quadros |
| `etiqueta_rasgada` | "três anos depois" | foto P&B que afasta 5%; etiqueta amarela (212,164,28) que nasce dobrada em Z e abre da esquerda para a direita em 3 degraus de 2 quadros (60/69/87/100% da largura); texto pequeno na etiqueta e palavra grande por cima |
| `jornais_mesa` | o número que saiu no jornal | mesa de madeira vista de cima e jornais desenhados pelo motor (nomes inventados, sem logo); chegam a 1,7× com borrão e pousam em 8 quadros; a câmera afasta até 0,91; `laco` branco feito à mão na manchete; `foco` que respira; título no alto e linha pequena palavra a palavra |

Frases da galeria: serifa itálica branca que entra **desfocada e transparente** e assenta em 6–8 quadros
(`planos_galeria.frase`); a seguinte **substitui** a anterior, exceto no bloco que monta à esquerda.

```json
{"tipo": "foto_recorte", "inicio": 154, "fim": 221, "foto": "pessoa.jpg", "mascara": "pessoa_mascara.png",
 "pouso": {"sigma": 3.0, "quadros": 9, "curva": 1.0}, "empurra": {"de": 6, "ate": 31, "z": 1.19},
 "bloco": {"x": 280, "y0": 495, "passo": 96, "corpo": 100,
           "linhas": [[{"texto": "Todo", "quadro": 160}], [{"texto": "mundo", "quadro": 166}]]},
 "virada": {"quadro": 194, "escurece": 0.45, "frase": {"texto": "achou que era o fim.", "centro": [792, 662], "corpo": 128},
            "sublinhado": {"x0": 560, "x1": 1030, "y": 740}}}
```

Máscara do sujeito: `swift ferramentas/recorte.swift <foto> assets/prontos/<foto>_mascara.png [objeto|pessoa]`.

## v12.1 — margem nas barras, semana e galeria
- **`barras`**: `margem` (no plano ou no item) desenha a faixa de ±margem em cada barra (`quadro_margem` diz quando
  aparece); `sobreposicao: {quadro, de, ate, texto?}` pinta de amarelo a zona onde as faixas se cruzam. É a forma de
  mostrar **empate técnico** sem fala técnica. `linha.dy` afasta o texto da linha do rótulo do valor.
- **`semana`**: `sem_numero` mostra só o dia da semana (sem data) e `sequencia: {de, passo, marca}` marca os sete dias
  um a um (X por padrão; `"certo"` para ✓). Usado em "em uma semana, olha o que aconteceu" e em "todo dia".
- **`galeria`**: cada palavra aceita `x`, para um número embaixo de cada retrato ("51%" e "49%").
- **`icones`**: novos `robo` (atendimento por IA), `balao` (chat), `lampada`, `saude` e `banco`.
- **Pesquisa na tela**: todo plano que mostra número de pesquisa leva `rodape` com instituto e contratante, período,
  entrevistas, margem e confiança (no Brasil, pesquisa eleitoral exige ainda o registro: Res. TSE 23.600, art. 10). É a
  única exceção à regra de não pôr texto pequeno.

## v12.2 — escala de trabalho e ícones novos
- **`escala_semana`** (`planos_noticia.py`): a escala de trabalho em blocos, um por dia (escuro = trabalho `T`, azul = folga `F`).
  `semanas: ["TTTTTTF"]` (6x1); `muda: {quadro, semanas, rotulo}` vira os blocos que mudam, um por degrau, com um pulo
  (6x1 → 5x2); `nome_escala: {texto, quadro, dy, corpo}` é o nome grande embaixo (não use a chave `rotulo`, que a camada
  comum desenha); `destaque: {quadro, dia, semana, texto}` circula um dia (o domingo); `legenda: {quadro, y}` explica as
  cores (trabalho/folga). Uma ou várias linhas em `semanas`.
- **`hemiciclo`**: `contra: {quadro, n}` pinta de vermelho as cadeiras logo depois das acesas (75 a favor e 1 contra).
- **`icones`**: novo `loja` (fachada com toldo, vitrine e porta).
- **Regra de roteiro:** todo número e atribuição ("o setor diz", "o instituto calculou") se confere na fonte antes de
  gravar. Por quê: um número atribuído à entidade errada já gravado obriga a cortar a frase do áudio (`ffmpeg atrim`
  com fade de 12 ms) e refazer os tempos.

## v12.3 — b-roll em vídeo (`motor/planos_video.py`)
- **`video_clip`**: toca um trecho de um `.mp4` preenchendo a tela vertical **na grade da série** (um degrau a cada 3 quadros, sem
  interpolar), com `sat` 0,82, vinheta 0,28 e empurrão de câmera `zoom: [1.0, 1.06]`. Parâmetros: `clip`, `ss` (segundo inicial),
  `vel`, `zoom`, `ponto`, `sat`, `ganho`, `vinheta`. Congela no último quadro se o plano passar do clipe. Aceita `palavras_grandes`
  (com sombra) e `rodape`. No montador da série: `clipe(inicio, fim, "nome", ss=0, palavras=[(texto, quadro, y, corpo)])`.
- **Gerar o clipe:** no Higgsfield (o gerador do plugin), 9:16, 4–5 s, sem áudio; mostre o custo antes e espere o "pode"
  (`${CLAUDE_PLUGIN_ROOT}/REGRAS.md`). Prompt: "Vertical documentary landscape. <cena>. Muted desaturated film colors, fine film grain. No people in close-up, no text, no logos."
- **Cuidado:** a IA coloca placas quase legíveis; conferir. Conteúdo de IA se avisa na legenda.
- **Filmagem real 16:9 no vertical (v12.6):** quando a notícia é um evento filmado (o salto do Roadster), o gancho é o
  vídeo do evento, não uma animação dele. `foco` (0–1 na largura da fonte, ou `[[t, x], ...]` para acompanhar a ação, t em
  segundos do plano), `aproxima` (zoom na fonte; 4K aguenta ~1,8) e `foco_y` recortam o 9:16 onde a ação está; `gama` clareia
  noturna. O mesmo arquivo pode entrar em trechos diferentes (a trava compara arquivo + `ss`). Testar o recorte antes com uma
  folha de quadros; palavra de cima sai com `ate` quando a seguinte entra; sobre céu claro, tinta escura sem sombra; crédito
  no `rodape` ("Vídeo: Tesla"). Vídeo sem licença aberta entra em trecho curto, com crédito, para comentar (citação).

## v12.5 — objeto real em ação (`motor/planos_objeto.py`) e um gancho diferente por vídeo
O recorte de uma foto real (`swift ferramentas/recorte.swift <foto> <mascara.png> objeto` → RGBA na caixa do sujeito)
faz o que a fala diz, no canvas claro com piso:
- **`salto`**: `saltador` {imagem, largura, x_inicio, x_decola, x_pousa, x_fim, decola, apice, pousa, altura, giro, giro_de,
  giro_ate} pula o `obstaculo` {imagem, largura, x}; sombra que encolhe, linhas de velocidade, poeira e tranco no pouso.
  Câmera: abra perto dos dois (z 1,45, âncora longe da borda: |x−540| ≤ 540 − 540/z) e recue no ápice.
- **`de_cabeca`**: `movel` (o recorte, virado na vertical) anda sob uma pista hachurada; `quadro_ar` mostra o ar.
- **`ventilador`**: `movel` na pista, ventilador que gira embaixo, setas do ar (`quadro_ar`), setas que apertam
  (`quadro_gruda`) e `vira` (a cena inteira gira 180° e o carro não cai).
- **`jatos`**: carro visto de cima e `n` jatos que disparam a cada `passo` quadros; `sobe` dispara todos e o carro cresce.
- Novos ícones: `envelope` (convite). A chave do objeto é `movel` (não `objeto`, que o `gravar()` confere como asset).
- **Fotos de paisagem num quadro vertical:** `cartao_rotulo` mostra a foto inteira num cartão (não corta o carro);
  `foto_pullout`/`etiqueta_rasgada` cortam no `ponto`. A camada comum não desenha o `rotulo` do cartão no canto.
- **Regra:** o gancho visual muda em todo vídeo da série. Mantenha no projeto uma tabela "Ganchos visuais já usados"
  (por exemplo, num `SERIE.md`).

## v12.7 — texto no meio, zona segura e o desenho que explica
Regras: texto no meio da tela e dentro da margem do Instagram; explicação vira motion desenhado por cima da imagem;
pessoa citada entra pela foto real.
- **Zona segura do Reels** (`familia_a.ZONA`): nada de texto em y < 270 (cabeçalho), y > 1520 (perfil, legenda, áudio),
  x > 930 com y > 880 (coluna de curtir/comentar/enviar) nem a menos de 90 px das bordas. Texto mora no **meio** (`MEIO`, y
  560–1360). `ferramentas/zona_segura.py <projeto>` monta cada degrau com e sem texto e acha toda tinta fora (de qualquer
  plano, já depois da câmera); `ferramentas/folha_quadros.py <projeto> q1,q2 saida.png --zona` mostra. Rode antes de entregar.
  Palavra grande: `y` padrão 960 (era 1450), largura máxima 800, `x` para tirar do caminho de um objeto.
  O sujeito (rosto, carro) também fica fora da coluna de botões: enquadre com `foco`/`aproxima`.
- **Telestração** (`motor/desenho.py`): qualquer plano aceita `desenhos` (no `video_clip`, antes do empurrão da câmera:
  anda com a filmagem). Tipos: `escurece` (com `desfoca`: o modo explicação), `traco` (escreve; `tracejado`, `ponta`,
  `linhas`), `seta`, `fluxo` (tracejado que corre: o ar), `circulo`, `ventilador`, `carrinho` (carro de perfil a giz que
  gira/vira), `rotulo` (etiqueta com fio), `balao` (fala que estoura), `recorte` (foto recortada com borda de adesivo que
  sobe e assenta), `proibido`, `cronometro`, `numero`. `segue: [[quadro, dx, dy]]` prende o desenho a um objeto que anda
  (posição medida). Traço com tremor e boil a cada 2 degraus. Cada desenho tem som no `mixar.py`.
- **`video_clip` com `congela`** (segundo do plano em que a imagem para; o som original para junto): "congela e explica".
- **Palavra atrás do objeto:** `palavras_grandes[].atras = {limiar, regiao}` (o claro da filmagem fica na frente da
  palavra: o carro cruza o PULOU); `atras_ate` devolve a palavra para a frente (a fumaça não a engole).
- **`tela_dividida`** (`planos_video.py`): `lados` [{clip, ss, vel, foco, aproxima, congela}] em `modo` "lado_a_lado"
  (o carro nos jatos x o foguete), "empilhada" ou "janela" (o segundo numa janela de cantos redondos). `audios` dá o som
  de cada lado.
- **`linha_do_tempo`** (`motor/planos_desenho.py`): eixo dos anos que se desenha, cursor que anda de "hoje" até o ano
  com o ano rolando, o ano grande que pousa no meio e desce para o eixo, polaroide alfinetada da promessa, seta tracejada
  da promessa, círculo e X no prazo perdido e a chave do atraso ("+8 anos").
- **Pessoa citada pelo nome:** foto real licenciada (Commons; contexto neutro, nunca rosto gerado), recortada
  (`recorte.swift ... pessoa`) e entrando como `recorte` com `balao` e `rotulo` com o nome; crédito no `rodape`.

## v12.8 — a resposta que vira app
- **`celular`**, item da conversa com `"tipo": "interface"`: a resposta da IA montada como app, num cartão branco que
  reserva o espaço e recebe cada componente na palavra dita: `titulo`, `texto`, `botoes` (`itens`, `ativo`, `clique` com o
  anel do toque), `grafico` (`valores`, `rotulos`, `altura`), `calculadora` (`visor` dá o formato, `conta` [de, até] conta
  no `quadro_conta`, `altura`), `campos` (`itens` [[rótulo, valor]]), `resultado` (`conta`, `prefixo`, `sufixo`), `opcoes`
  (rádio; `bloqueados` apagam e ganham cadeado no `quadro_bloqueio`) e `barra` (o limite que esvazia: `de`, `até`).
  Cartão alto não cabe: use `altura` compacta e câmera ≤ 1,1 (o relógio do celular sobe para baixo do cabeçalho do Reels).
- Ícones novos: `sol`, `lua`.
- Print de página oficial como prova: captura do navegador, recortada só no que se cita (sem o logotipo da barra), entra
  como `recorte` (borda de adesivo) sobre papel, com `circulo` no que a fala aponta. Mede-se o ponto no quadro renderizado
  (a borda do adesivo desloca tudo ~54 px). Cuidado com a coluna da direita: a célula que é a prova não pode cair em x > 930.

