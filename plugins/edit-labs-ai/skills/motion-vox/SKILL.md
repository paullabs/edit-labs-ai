---
name: motion-vox
description: >-
  Insere motion graphics no estilo editorial da Vox e legenda queimada dentro de um clipe
  vertical ja cortado (podcast, entrevista, talking head). Use quando o pedido for adicionar
  motion, ilustrar palavras-chave, animar trechos, "colocar uns motions nesse corte",
  "ilustrar essa fala", colocar B-roll, queimar legenda no clipe, ou melhorar e estender
  motions ja feitos. Cobre o processo inteiro: escolher as frases pelo transcript, gerar e
  recortar assets PNG, compor as cenas em camadas com registros visuais variados, B-roll em
  video gerado, legendar, revisar e montar o master preservando a fala, com efeitos sonoros
  quando pedidos. Recebe o vertical limpo da skill corte-viral. Exige o Higgsfield conectado.
---

# Motion editorial sobre footage

Insere cenas de motion no estilo Vox explainer dentro de um clipe vertical que
**já existe**. A fala e seus tempos são preservados: não reescrever ou cortar palavras
para encaixar motion. Efeitos sonoros pedidos entram em uma camada separada, com seleção,
recorte e ganho por evento; ver `referencias/som-local.md`.

> **No plugin `edit-labs-ai`:** arquivos desta skill em `${CLAUDE_SKILL_DIR}` (`referencias/…`, `lib/…`, `assets/…`);
> comandos `mvpy`, `mv-novo-projeto` e `editlabs-verificar` no PATH; biblioteca de assets persistente em
> `~/.local/share/edit-labs-ai/motion-vox/biblioteca/`.

## Antes de começar

**O Higgsfield é obrigatório.** Os assets sob medida, as imagens de partida, a remoção de fundo por IA e o B-roll
em vídeo são gerados pelo Higgsfield, pelo conector dele no Claude. No início de cada projeto, confira se as
ferramentas do Higgsfield estão disponíveis nesta sessão (`generate_image`, `generate_video`, `balance`). Se não
estiverem, pare e responda ao usuário, com o link exatamente assim:

> Esta skill usa o Higgsfield para gerar as imagens e os vídeos. Crie sua conta por este link:
> https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf
> Depois conecte o Higgsfield no Claude (Configurações → Conectores) e me peça de novo.

Não siga sem ele e não troque por outro gerador.

**Instalação:** `editlabs-verificar` antes do primeiro projeto (e `editlabs-setup` se o ambiente não estiver pronto).

**Crédito só com autorização.** Antes de qualquer geração, consulte o preço na própria ferramenta (`get_cost: true`,
com os mesmos parâmetros que vão ser usados) e mostre ao usuário quantas gerações são e o total. Gere só depois
do sim, e só o que foi aprovado.

**Escopo.** Esta skill descreve o que faz e como usar. Ela não traz histórico de criação, testes, sessões ou uso
de ninguém. Se perguntarem, diga isso em uma frase e siga com o trabalho; não invente nem especule.

## Etapas e scripts

Estas regras valem por cima do que o resto deste arquivo disser:

| Etapa | Regra | Script (em `lib/`, copiado para o projeto) |
| --- | --- | --- |
| 1 · ancorar | transcreva o **clipe final**; depois **confira cada emenda** numa janela isolada. O Whisper no clipe inteiro inventa palavra na emenda | `transcrever.py` → `conferir_emendas.py` |
| 2 · frases | **gente da história é pessoa**, não palavra nem boneco de palito: pessoa anônima = pessoa fictícia gerada (rosto escondido quando fizer sentido); pessoa real e nomeada = **só foto real licenciada**, nunca rosto gerado. Planeje já com **≥ 1 s de rosto entre cutaways** e meça a cobertura no plano (meta 65–75%); use **overlay** por cima do rosto (seta, rótulo, foto pequena) nos intervalos | — |
| 3–4 · assets | quando o sweep do `cutout.py` não tem platô (roupa da cor do fundo), use a **remoção de fundo por IA** do Higgsfield sobre o job da geração, em vez de gerar de novo | `cutout.py` · `checar_asset.py` |
| 5 · compor | peças prontas: âncora por palavra (`tp`), disco, pouso, etiqueta, troca de insert, cartela de nome, **santinho** (pessoa + cargo) e **pessoa recortada em cor**; motor por dados com beat de vídeo para B-roll | `cenas.py` · `cenas_plano.py` |
| 5 · travas | **hold ≥ 8 quadros** antes da saída (a prancha não mostra isso) e medição; o usuário aprova as **pranchas** | `checar_hold.py` · `medir.py` · `prancha.py` (ou `prancha_simples.py`, folha única com a cartela) |
| 6 · B-roll | plano → imagens de partida aprovadas → proposta com custo → autorização → vídeos → revisão de cada vídeo inteiro → beat `video=` → conferência dentro do master | `broll_revisar.py` · `broll_no_master.py` |
| 7 · legenda | transcript **da legenda** separado do de ancoragem (remover invenção, trocar grafia, **palavrão mascarado**); janelas recalculadas sempre que uma cutaway muda: toda fala com rosto na tela aparece | `legenda_transcript.py` · `janelas_legenda.py` · `captions.py` |
| 8 · render | `render.py` preenchido a partir do `compose.py` (cartela de abertura na camada da legenda, cache por passo de 12 fps, 24 fps dentro dos B-rolls, saída de 0,17 s, início do vídeo igual ao da fonte); `MV_VERSAO` grava versões lado a lado | `preencher_render.py` |
| 8 · verificar | sincronia **por conteúdo** (mesmo quadro no mesmo instante), áudio idêntico (MD5), início e duração; contagem de quadros é só informativa | `verificar_master.py` |

A ordem completa, do link ao vídeo publicado, está na skill **`edit-labs-ai`**.

## A identidade viaja junto

Esta skill é um **kit fechado**, não só um método. Ver `IDENTIDADE.md`.

| | |
| --- | --- |
| `fontes/` | as fontes da identidade, licenças livres, com os arquivos de licença |
| `assets/` | os 16 objetos e fotografias recortados, mais o manifesto |
| `sfx/` | alternativa sintetizada; priorizar a biblioteca local fornecida e preparar trechos por evento (`referencias/som-local.md`) |
| `lib/` | o motor, o recorte, o CRT, a legenda, a transcrição, o **medidor** (`medir.py`), o **aferidor de legibilidade** (`legibilidade.py`), o **conversor da corte-viral** (`words_from_corte_viral.py`), as ferramentas de B-roll, os dois templates |
| `exemplo/` | um bloco de configuração de clipe preenchido, com o motivo de cada escolha |
| `verificar.py` | checagem de instalação — rode antes do primeiro projeto |
| `referencias/` | identidade, registros, transições, legenda, armadilhas, rubricas, prompts, fotos reais, B-roll (`seedance-2.5.md`), **hierarquia e profundidade**, **índice de referências visuais** |
| `referencias/estudos/` | peças de fora dissecadas, com o que confirmam e o que propõem — insumo de revisão, não regra |

Quem instalar reproduz **este** visual, não um parecido.

## Requisitos de máquina

| | | Se faltar |
| --- | --- | --- |
| `python3` + `Pillow`, `numpy`, `opencv-python` | composição e recorte | nada roda |
| `ffmpeg` | montagem do master | os frames saem, o vídeo não |
| `faster-whisper` | transcript palavra a palavra | sem ancoragem e sem legenda |
| Higgsfield conectado ao Claude | assets sob medida, remoção de fundo, B-roll | a skill não começa (ver "Antes de começar") |

**Transcript.** Insumo sem substituto — motion ancorado e legenda em corte seco dependem
de saber em que frame cada palavra foi dita. Gere com:

```bash
mvpy transcrever.py 00_brief/fonte.mp4 00_brief/transcript_palavras.json
```

Formato: `[{"w": "palavra", "t": 12.28, "e": 12.54}, ...]`, em segundos **do clipe**.
Já tem transcript em outro formato? Converta para este — não reescreva o motor.

**Clipe vindo da corte-viral: não rode Whisper de novo.** A pasta do clipe já traz
`caption-map.json` com timing por palavra (`source_words`). Converta:

```bash
mvpy words_from_corte_viral.py <pasta-do-clipe>/caption-map.json 00_brief/transcript_palavras.json
```

**`night_photo.py` e `crt.py` trazem constantes calibradas** para as fotos do kit
(recorte, curva de cor, quadrilátero da tela). Ao gerar fotografia nova, recalibre — os
dois scripts dizem onde.

## Duas formas de projeto

A skill trabalha de duas formas. Na principal, **motion sobre footage**, o áudio é congelado e tudo se ancora no
que já foi dito. Na segunda, o **documentário narrado**, não há talking head: a peça é cutaway do primeiro ao
último frame e a narração é escrita antes. Identidade, registros, kit e rubricas valem iguais; muda a ordem das
duas primeiras etapas e o critério das transições.

| | sobre footage | documentário narrado |
| --- | --- | --- |
| etapa 1 | transcrever o clipe | **escrever o roteiro** |
| etapa 2 | escolher frases do que foi dito | gerar a locução, transcrever, **reancorar** |
| densidade | 65–75% do clipe | 100% — não há rosto para voltar |
| transição | como sair sem tranco para o rosto | **o que a passagem diz** entre duas cenas |
| verificação | fala isolada preservada; MD5 só na cópia sem mix/reencode | duração do master contra a locução, mais revisão da mixagem |

**Ao escrever roteiro, conte palavras FALADAS.** "1929" é uma palavra escrita e seis
faladas; "250 GTO" são quatro. Um roteiro que parece caber no papel pode ocupar a duração
inteira sem nenhum respiro. Tire anos e nomes de modelo da narração e deixe-os só na
imagem, o que a identidade já pede por outro caminho (texto não repete a narração).

## Regra-mãe

> **Mostrar uma prova, apontar o detalhe, concluir — nesta ordem.**
> Movimento acompanha raciocínio. Nada se mexe só para "dar dinâmica".

## Régua de gosto do kit — vale em toda cena

A régua é conferida pelas travas por script (hold, DNA, medição) e pelo usuário, nas pranchas. Troque pela sua
régua quando montar o seu estilo:

1. **12 fps, um relógio só** (desenho, boil e grão), grão por cima, RGB mínimo, assets texturizados e bonitos.
2. **Turbulent Displace leve em tudo** (boil, `BOIL_SCALE` ≤ 0,6): a edição parece viva, nunca tremida.
3. O elemento representa **o que de fato é** o que foi dito.
4. **Marca citada → logo oficial** daquela marca.
5. **Nada abstrato**: nenhum círculo vazio, forma sem referente, ícone de "ideia" genérico.
6. **Gente aparece de fato**: situação com pessoas mostra corpo, mãos, figura ou foto — negociação são duas mãos apertando — nunca só a palavra.
7. Palavra escrita só para coisa específica (título, nome, número), e **título vem com um elemento que faz parte dele**.
8. **Toda cena com bastante motion**: nada parado, nada clichê.
9. **Assets sob medida, sem repetir**: cada cena ganha o objeto da própria fala, no mesmo mundo do kit;
   o kit não vira elenco fixo (`referencias/assets-sob-medida.md`).

Horizontal (1920×1080) tem motion também: `MV_CANVAS=H` escolhe o quadro, e a cena escreve posição em fração
(`X()`, `Y()`, `U`) com layout próprio por `ORIENT` — nunca o vertical esticado.

## Escolher o meio antes de produzir

Composição por camadas continua sendo o padrão para logos, prints, texto, setas e
diagramas que exigem controle exato. IA de imagem cria objetos físicos genéricos,
texturas e esboços, preservando o registro visual da cena. **B-roll em vídeo** (Seedance,
pelo Higgsfield) entra onde a fala descreve ação, lugar ou gente fazendo algo — ver a seção
"B-roll em vídeo" abaixo e `referencias/seedance-2.5.md`.

Vídeo gerado tem trava própria: plano → imagem de partida → revisão → mostrar imagem
e proposta concreta ao usuário → autorização explícita específica → geração.
“Está ficando bom”, aprovação do plano ou da imagem não autorizam gerar vídeo.
Não submeter uma geração, variação ou regeneração sem a autorização correspondente.

**Nunca gere por IA o rosto de uma pessoa real e identificável.** Isso não muda com este
kit permitir foto real de gente citada — é o oposto: quando a cena precisa do rosto de
alguém nomeado, a resposta é **buscar uma fotografia real e licenciada** (Wikimedia
Commons ou equivalente, ver `referencias/fotos-reais.md`), nunca pedir pro gerador
desenhar essa pessoa. Gerar um rosto sintético de gente real é o problema que a
restrição existe pra evitar; trazer uma foto verdadeira não é.

## Ordem de execução

Cada etapa tem uma trava. Não avance sem ela. Sempre escrever o plano e produzir
imagens para verificar a composição antes de animar. O usuário aprova as imagens:
imagens aprovadas liberam a composição por camadas, mas não autorizam vídeo gerado.
Quando a ideia precisar de vídeo, seguir a aprovação adicional de `seedance-2.5.md`.
Quando houver SFX, preparar e revisar o mapa de eventos de `som-local.md` antes da mixagem.

| # | Etapa | Saída | Trava |
| --- | --- | --- | --- |
| 1 | **Ancorar** | tabela palavra → frame | transcript palavra-a-palavra existe |
| 2 | **Escolher frases** | tabela entra/não-entra com motivo | cada corte tem justificativa escrita |
| 3 | **Gerar assets** | PNG cru por objeto | zero texto de IA, zero sombra embutida |
| 4 | **Recortar** | PNG com alfa | rubrica D1 aprovada |
| 5 | **Compor** | 4 estados por cena | rubricas D2/D3 aprovadas |
| 6 | **Blueprint + transições** | um .md por cena + mapa | entrada e saída definidas |
| 7 | **Legenda** | sequência RGBA de duração total | nenhuma palavra dita fica de fora |
| 8 | **Render + mux** | master + mapa de áudio | duração e cadência verificadas; fala preservada, mix revisada e MD5 aplicado só quando válido |

Leia `referencias/rubricas-diretor.md` antes da etapa 4 e aplique em 4, 5 e 7.
Escolha o registro de cada cena em `referencias/registros.md` **antes** de compor.
Legenda queimada: `referencias/legenda.md`. Saídas e transições: `referencias/transicoes.md`.
Boil (o objeto redesenhado a cada passo): `referencias/boil.md`.

**Hierarquia, profundidade e decupagem em beats: `referencias/hierarquia-e-profundidade.md`
— leitura obrigatória antes da etapa 5, e de novo depois de compor.**

**Antes de compor cada cena, abra os frames de referência do registro dela**
(`referencias/REFERENCIAS-VISUAIS.md`). A skill compõe **olhando** a referência, não
lembrando dela — descrição em texto não substitui o frame na tela.

---

## 1. Ancorar no transcript

Converta cada palavra para frame local do plano:

```
frame24 = (t_palavra − t_início_do_plano) × 24
```

**Todo evento visual se trava numa palavra**, com tolerância de ±3 frames. Um elemento
que entra fora da palavra vira enfeite: o espectador não liga uma coisa à outra.

Sem transcript com timestamp por palavra, pare e produza um antes (Whisper com
`word_timestamps`, ou legendas do YouTube).

## 2. Escolher as frases

Entra a frase que tem **objeto, narrativa (gente fazendo algo) ou mecanismo explicado**.
Narrativa (alguém contando uma história, mesmo sem nome) e explicação (um mecanismo, um
"por quê", um conceito técnico) são o material mais fácil de desenhar: entram via
`storyboard/persona` e `diagrama explicativo` (`referencias/registros.md`). Objeto é o
caso mais fácil, não o único. Só fica de fora o que é opinião solta, aparte, ou já foi mostrado.

| Critério | Entra | Não entra |
| --- | --- | --- |
| tem substantivo concreto ou unidade de medida | ✓ mesa de pesquisa/processo/etc. | |
| é narrativa — alguém faz algo, mesmo sem nome ("um cliente que...", "ela jogou...") | ✓ storyboard/persona | |
| explica um mecanismo, estrutura ou "por quê" técnico/científico | ✓ diagrama explicativo | |
| é a instrução ou o payoff do clipe | ✓ | |
| nome de pessoa, marca ou lugar identificável | ✓ (foto/logo real, ver abaixo) | |
| descreve uma ação, um lugar ou gente fazendo algo que dura alguns segundos | ✓ B-roll em vídeo | |
| número que o falante **se autocorrige** ou estima ("sei lá") | | ✗ em tipografia de dado |
| piada lateral, aparte, sem ação nem mecanismo | | ✗ |
| já ilustrado por outra cena (mesmo objeto/mecanismo repetido) | | ✗ |
| grandiloquência sem objeto nem mecanismo ("primeira vez na história") | | ✗ |

**Teste rápido:** se a frase tem um substantivo, uma pessoa fazendo algo, ou explica
como/por que algo funciona, ela é candidata. O que sobra de fora é opinião pura,
aparte cômico sem ação, ou repetição do que a cena anterior já mostrou.

**Registro de fato vs. opinião.** Número dito pelo entrevistado só vira gráfico limpo se
for verificável. Estimativa vira **marcador manual** ou não entra.

**Nome citado pede prova real, não símbolo.** Pessoa, marca ou lugar identificável que o
falante nomeia — "Elon Musk", "Tesla", "Getúlio Vargas" — vira **foto ou logo real**,
não um objeto genérico inventado pra representar a ideia por tabela. Um carro-brinquedo
sem marca ilustra "carro"; não ilustra "Tesla". A regra-mãe pede a prova de verdade
quando ela existe e é obtível — símbolo genérico só entra quando a identidade **não
está confirmada com segurança** (nome ambíguo, possível erro de ASR) ou quando mostrar
o rosto seria o problema em si (menor, situação sensível). Ver
`referencias/fotos-reais.md` para como buscar, licenciar e tratar essas fotos/logos
sem sair do estilo do kit. Vale em **toda** cena do clipe.

**Varie o REGISTRO, nao so o objeto.** Tres cenas seguidas de "mesa + objeto + fita"
leem como a mesma cena, por mais que os objetos mudem. Nunca repita registro em cenas
vizinhas — a tabela esta em `referencias/registros.md`.

**Densidade.** Mire em **65–75% do clipe coberto por motion**, contando overlay e B-roll.
Vídeo sem motion suficiente não prende; abaixo de 50% já lê como pouco. Isso só é
possível com a régua de seleção larga (objeto, narrativa OU mecanismo — ver acima):
sem ela não sobra frase suficiente pra cobrir 70% honestamente.

**Gatilho rápido.** Assim que a fala começa a descrever algo desenhável, o motion tem
que aparecer em **menos de 1s** — não espere a frase terminar para decidir. Um clipe
em insert-burst — vários flashes curtos (foto, logo, foto, logo…) alternando com o
rosto — lê como RITMO, não como "sumiu o rosto", e é o jeito mais fácil de bater 70%
sem cansar: o que importa não é só o percentual bruto, é nunca ficar mais de 1-2s sem
cortar pra alguma coisa (rosto real OU insert). Mesmo em 70%+, ainda vale nunca repetir
registro em cenas vizinhas (acima) e segurar pelo menos ~1s de rosto real entre blocos
de insert, pra não virar ruído — dentro de um insert-burst, os cortes internos
(`_swap_flash`) podem ser bem mais rápidos, 0,7–1,5s por insert.

**Ritmo agradável, não frenético.** Motion cedo e denso não é motion curto: um elemento
que aparece em <1s ainda segura o hold de 8–18 frames de sempre (`identidade.md`) antes
de sair. A densidade sobe por ter MAIS cenas e cenas mais próximas umas das outras, não
por encurtar o tempo que cada uma tem pra ser lida — senão vira estroboscópio, o oposto
do "desenhar pra alguém entender" que é o objetivo aqui.

**Escreva a tabela dos que ficaram de fora, com o motivo.** A decisão descartada é tão
útil quanto a adotada, e evita refazer a discussão depois.

## 3. Gerar os assets

**Antes de tudo: `referencias/assets-sob-medida.md`.** O kit é a identidade, não o elenco: o herói de cada
cena é o objeto da própria fala, gerado no mesmo mundo (DNA medido na §3 de lá), procurado antes na
`biblioteca/` (`lib/biblioteca.py buscar …`) e registrado nela depois da rubrica D1. Herói do kit no máximo 1
cena por vídeo, cartão A05 no máximo 2 (E9/E10 do verificador).

Geração no Higgsfield: `gpt_image_2`, quadrado, 2k, qualidade alta, várias em lote (`generate_image_batch` e
`jobs_wait`), sempre com o custo aprovado antes. Um prompt por objeto. Templates completos em
`referencias/prompts-asset.md` e, por família, em `referencias/assets-sob-medida.md` §4.

**Fundo: escolha pelo maior afastamento de LUMINÂNCIA do objeto.**

| Objeto | Fundo |
| --- | --- |
| papel, cartão, objeto claro | cinza médio `#8A8A8A` |
| objeto escuro (teclado, metal escuro) | cinza claro `#D8D8D8` |
| objeto de luminância média E neutro | último recurso: chroma |

**Pedir "fundo transparente" não funciona**: o modelo devolve RGB sem canal alfa, e o
pedido produz um fundo cinza sólido. **Fundo chroma** torna o recorte trivial, mas
contamina boa parte dos pixels de borda com a cor, o que estraga justamente a
borda — que neste estilo é a matéria (fibra de papel rasgado, metal fosco).

Sempre no prompt, sem exceção:

- `no cast shadow on the backdrop` — sombra é camada, não pixel do asset
- `no text, no letters, no numbers, no logo, no brand`
- `no glow, no bloom, no neon, no gradients, no HDR, no AI-polished look`
- objeto isolado, top-down, luz difusa uniforme

**Relógio e qualquer mostrador:** peça **sem números, só tracinhos**, e redesenhe os
ponteiros em PIL. Assim a hora vira dado controlado e animável, e não sobra texto de IA.

## 4. Recortar

Use `lib/cutout.py`. Três passes, e a ordem importa:

1. **Flood** `FIXED_RANGE` semeado nas bordas. A tolerância sai de uma **varredura**
   (`mvpy cutout.py --sweep NOME`): escolha o **platô**, o ponto a partir do qual
   aumentar a tolerância não remove mais nada.
2. **Sombra.** O fundo cresce, restrito à faixa onde a sombra mora: pixel neutro, liso,
   e do lado certo em luminância. `dark_floor` inverte a regra para objeto escuro.
3. **Fundo encapsulado.** Miolo de clipe de papel tem cor de fundo mas o flood não chega.

Tolerância relativa ao vizinho não serve: escorre por gradiente liso e come o interior
de objetos chapados.

## 5. Compor

**Divisão de trabalho — não negociável:**

| Camada | Origem | Motivo |
| --- | --- | --- |
| fundo, objetos físicos, fotografias | IA de imagem | materialidade |
| **todo texto** | PIL, fonte local | grafia garantida |
| **toda anotação** (círculo, seta, sublinhado, linha) | PIL procedural | precisa ser desenhável em progresso |
| sombra de contato, grão, vinheta | PIL | intensidade por camada |

Anotação procedural não é economia: é o que permite renderizar "seta 40% desenhada"
sem regerar imagem.

**Uma timeline por cena, quatro estados amostrados dela:** `START` (frame 0),
`MID` (beat DIRECT), `END` (último evento concluído), `EXIT` (fim do plano). Os estados
são coerentes por construção — nenhum pode contradizer outro sem que o código esteja
errado.

Confira que `END` cai **depois** do último evento, senão o estado mostra texto pela metade.

**Um plano longo é uma SEQUÊNCIA DE BEATS, não uma composição que se acumula.** Oito
segundos comportam quatro ideias; empilhar as quatro no mesmo quadro entope a composição
e mata a hierarquia. Decupe em beats com corte seco, na ordem da fala, cortando no
silêncio entre palavras. Ver `referencias/hierarquia-e-profundidade.md` §4.

**Todo texto sobre imagem passa pelo aferidor.** Renderize a cena duas vezes — com o
texto e sem — e rode `mvpy legibilidade.py com.png sem.png`. Ele separa o que a
olho se confunde: se a TINTA some no fundo dela (interno) ou se o BLOCO some na imagem
(externo). Legenda sobre footage sem `kit.scrim_inferior()` não passa no aferidor.

**Meça antes de aprovar, não estime.** `mvpy medir.py 08_images/frames/M*_END.png`
devolve massa escura, acento e vazio de cada frame contra a faixa da Style Bible. A olho,
vazio e massa escura são fáceis de errar por muito: rubrica sem medição não aprova.

Detalhes de paleta, tipografia, safe zones e sombras: `referencias/identidade.md`.
Armadilhas conhecidas: `referencias/armadilhas.md` — **leia antes de compor**.

## 6. Entrada, saída e transição

| Tipo | Entrada | Saída |
| --- | --- | --- |
| **cutaway** (cobre o vídeo) | corte seco, herói **já em voo no frame 0** — o corte é a revelação | `flash` é o padrão (desfoca + estoura em branco, corte escondido no pico) — nunca **arrasta pro lado** (`slide`/`wipe`). `push` (zoom) continua pra fechar ideia. Repetir a mesma saída em cenas vizinhas vira tique. Ver `referencias/transicoes.md` |
| **overlay** (sobre o vídeo) | animada, com trajetória | volta por onde entrou, com fitas e anotação **presas ao objeto** |
| **B-roll** (vídeo gerado em tela cheia) | corte seco na palavra-âncora, a ação já andando | como a cutaway; volta para o rosto no silêncio |

Hold de 8–18 frames antes de qualquer saída. Melhor ponto de corte é o **silêncio** entre
palavras.

**Insert-burst: trocar de prova sem sair da cutaway.** Quando uma janela cita várias
coisas em sequência (pessoa → objeto → lugar), não abra uma cena por citação — isso
estoura a densidade e pisca demais. Renderize cada insert como um sub-desenho completo
dentro da MESMA função `build_M#`, e troque entre eles com o mesmo efeito de `flash`
(desfoca + branco + resolve), aplicado internamente por uma função tipo `_swap_flash(
im_a, im_b, k)`. A cena inteira ainda entra e sai uma vez só — o flash interno é só
ritmo dentro dela. Código e exemplo em `referencias/transicoes.md`.

Continuidade honesta: dois elementos separados por dezenas de segundos não formam match
cut. Registre como **motivo recorrente**. O que amarra de verdade é **objeto herdado** —
o mesmo prop voltando com outro estado.

## 7. B-roll em vídeo

B-roll é vídeo gerado (Seedance, pelo Higgsfield) em tela cheia, de 3 a 5 s, mostrando o que a pessoa está
contando: a ação, o lugar, gente fazendo algo. Guia completo, com a geração e o encaixe: `referencias/seedance-2.5.md`.

1. **Onde.** Primeiro troque cutaways paradas (foto ou recorte sem movimento) cuja fala descreve ação ou lugar.
   Depois preencha os trechos longos de rosto: mais de ~4 s seguidos sem nada é o primeiro candidato. Continua
   valendo **≥ 1 s de rosto entre cutaways**; se o B-roll novo cobre o lugar de um overlay pequeno, o overlay sai.
2. **Quem aparece.** Só pessoas fictícias, sem rosto identificável: de costas, só as mãos, fora de foco ou ao
   longe. Nunca uma pessoa real; nunca texto, placa ou logo gerado (marca vem desenhada por cima, em PIL).
3. **Plano escrito** por clipe (`00_brief/BROLL.md`): janela no tempo do clipe, palavra-âncora, o que mostra,
   modelo, duração gerada e trecho que vai ser usado, e a cobertura de motion antes e depois.
4. **Imagem de partida** para cada B-roll (`gpt_image_2`, 9:16, 2k, alta), no mesmo mundo do clipe. Mostre as
   imagens numa folha, com o custo das imagens já aprovado. **A aprovação das imagens não autoriza os vídeos.**
5. **Proposta de vídeo** com o custo que a ferramenta informa (`get_cost: true`) → autorização explícita →
   geração em lote (`generate_video_batch` e `jobs_wait`), com a imagem aprovada como `start_image`.
6. **Revise cada vídeo inteiro** (`mvpy broll_revisar.py`, 8 quadros ou mais por vídeo): mão deformada, objeto
   flutuando, texto acidental, **rosto de passante que ficou visível**. Anote o trecho útil de cada um. Defeito
   num pedaço se resolve na edição, com `va` (segundo de início) e `vel` (velocidade), sem gerar de novo; se não
   der, a cena volta a ser motion. Gerar de novo pede nova autorização.
7. **Encaixe** como beat `video=` no motor por dados (`cenas_plano.py`), recalcule as janelas de legenda, e renderize
   numa versão nova: `MV_VERSAO=v02 mvpy render.py`, depois `MV_VERSAO=v02 mvpy verificar_master.py`.
8. **Confira no master** (`MV_VERSAO=v02 mvpy broll_no_master.py`): entrada, meio, saída e a volta para o rosto de
   cada B-roll. No `CREDITOS.md` da entrega, liste os B-rolls como conteúdo gerado por IA e peça o selo da
   plataforma.

## 8. Render e montagem

Use o `render.py` do projeto (o `mv-novo-projeto` o copia de `lib/render_template.py`; rode com
`mvpy render.py`). **Base de vídeo por CONCATENAÇÃO** (fonte + cutaways, blocos
discretos, um atrás do outro) — **não** overlay condicional encadeado. A legenda
continua overlay (RGBA, sempre ativa, por cima de tudo).

> **Por que concatenação, e não `overlay=...:enable='between(t,t0,t1)'` por shot.** Com
> muitos shots encadeados (comum em insert-burst), o overlay condicional deixa vazar 1
> frame do vídeo cru bem no corte entre duas cutaways, mesmo com `t1` calculado
> frame-exato. Na concatenação, cada trecho (vídeo cru OU cutaway) é um bloco discreto
> ligado por `concat`, sem janela de tempo condicional: não existe "por baixo" para vazar.

```python
# monta [gap_fonte][shot1][gap_fonte][shot2]...[gap_fonte] e concatena
segs, prev_end = [], 0.0
for k, (name, _, t0, t1, _, _) in enumerate(SHOTS, start=1):
    n = int(round((t1 - t0) * FPS)); t1x = t0 + n / FPS
    if t0 > prev_end + 1e-6:
        segs.append(("gap", prev_end, t0))
    segs.append(("shot", k))
    prev_end = max(prev_end, t1x)
segs.append(("gap", prev_end, DUR))
# cada segmento: [0:v]trim=start=A:end=B,setpts=PTS-STARTPTS,format=yuv420p[gN]
#            ou: [k:v]setpts=PTS-STARTPTS,format=yuv420p[sN]
# concat=n=len(segs):v=1:a=0[vbase] — so entao a legenda entra por cima
```

- cutaway = frames opacos (a concatenação já garante que só um bloco é visível por vez)
- as cenas são concatenadas na ordem da lista: o `montar` do motor ordena as cenas pelo início, e uma cena fora
  de ordem alongaria o master.
- a timeline pode ser 24fps mesmo com o clipe em 29,97: avalie cada frame de saída no
  tempo real (`frame24 = t × 24`, com fração). Converter cadência depois gera judder.
- grão: campo **borrado** (σ≈0,9) e **"on twos"**. Ruído branco por pixel e por frame é
  incompressível e leva o bitrate às alturas.
- **o desenho segura em degraus de `MOTION_FPS`** — **12**, um relógio só com o boil e o grão (estudo Porsche §8 #1; `RELOGIO_UNICO` no `render.py`), não os ~60fps reais da fonte —
  é a vibe de stop-motion da Vox, nunca smooth de CG. Só o conteúdo (`fn(f24)`) prende;
  o flash de entrada/saída e o grão continuam fluidos na cadência real, senão a própria
  transição vira o defeito que essa regra existe pra evitar. `t_step =
  floor(t*MOTION_FPS)/MOTION_FPS` antes de converter pra `f24` — ver `render_template.py`.
  Dentro de um beat de vídeo (B-roll) o passo é de 24 fps, a cadência do próprio vídeo; o desenho por cima
  continua nos 12.
- **versões lado a lado:** `MV_VERSAO=v02` grava `12_master/MASTER_V_v02.mp4` e `11_qa/VERIFICACAO_v02.json` sem
  sobrescrever a versão anterior.

**Som de transição — quando pedido.** Priorizar a biblioteca local fornecida pelo usuário,
principalmente cliques suaves de câmera. Selecionar o trecho útil, alinhar o transiente
à ação e reduzir o efeito em relação à voz; não usar automaticamente o arquivo inteiro
nem sonorizar todo corte. Ler `referencias/som-local.md` e usar `lib/sfx.py` com
`SFX_EVENTS`. `SFX_TIMES`/pool sintetizado ficam apenas como compatibilidade legada.

**Verificação obrigatória do master**, contra a fonte: duração sempre tem que bater
exatamente. **Contagem de frames de vídeo**: bate exatamente quando a fonte é CFR
estrito; uma variação de 1 frame a cada poucos cortes é aceitável e **não** é o defeito
de corte descrito acima — fonte de podcast raramente é CFR perfeito, e `-count_frames`
pode diferir da conta duração × fps já na própria fonte. Os trechos de
vídeo cru vêm de `trim` direto na fonte (frames reais, não recalculados), então essa
variação é herdada, não introduzida pelo render. **MD5 do áudio decodificado** (`ffmpeg -i x.mp4
-map 0:a -f md5 -`) bate **só quando não há mixagem, reencode ou alteração de formato/amostras** — é o padrão, e é o que
garante que a fala não foi tocada. Com som de transição ligado, documente no lugar do
MD5: duração do áudio idêntica + os trechos fora dos intervalos efetivamente ocupados pelos SFX continuam com
o mesmo conteúdo perceptual (início = `timeline_at - (anchor_at - source_in)`;
fim = início + `source_out - source_in`, conforme o mapa) (a mixagem some sobre o original, nunca substitui —
`normalize=0` no `amix`, sem abaixar a fala pra caber o efeito).

---

## Começar um projeto

```bash
mv-novo-projeto PROJETO        # motor (lib/*.py), fontes, kit em 07_assets/, compose.py e render.py de template, pastas
```

**Rode todo script do projeto com `mvpy`** (o Python do ambiente da motion-vox, com as versões fixadas do kit),
da pasta do projeto: `mvpy compose.py M1`. Onde este arquivo diz `python3`, use `mvpy`.

`fontes/` tem que ficar ao lado de `voxlab.py` — a identidade depende dela e o motor
falha com mensagem clara se não achar.

```
PROJETO/
  00_brief/PLANO_MOTION.md      frases escolhidas e recusadas, com motivo
  00_brief/BROLL.md             plano de B-roll (quando houver)
  05_motion/M#_motion.md        blueprint por cena
  06_transitions/TRANSITION_MAP.md
  07_assets/{raw,cutout,broll}/
  08_images/frames/             os 4 estados por cena
  09_plates/                    frames do vídeo para as cenas de overlay
  10_sequences/                 PNG por frame, por cena
  11_qa/                        verificação, pranchas, folhas de B-roll
  12_master/
  voxlab.py cutout.py compose.py render.py    (copiar de lib/)
```

O `bg_paper()` do template lê `07_assets/raw/BG_PAPER.png`; os demais assets saem de
`07_assets/cutout/`; os vídeos de B-roll, de `07_assets/broll/<id>.mp4`. Escreva as cenas a partir de
`compose_template.py`.

## Ao editar em lote

`str.replace()` devolve a string **intacta** quando o padrão não casa — patch silencioso.
Depois de qualquer rodada de patches, confirme por `grep -cF` que cada padrão crítico
entrou. Para edição que depende do contexto ao redor, use a ferramenta Edit, que **erra**
se não casar.
