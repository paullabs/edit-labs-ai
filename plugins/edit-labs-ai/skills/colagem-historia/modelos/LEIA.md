# Modelos de reel de história

Dois moldes prontos. Eles rodam no motor de colagem do plugin e leem as fotos da pasta `pecas/` do projeto.

| modelo | história | mundo | duração |
| --- | --- | --- | --- |
| `reel_napoleao.py` | **a medida desmente o mito:** régua em escala real, a pessoa com a sola no chão, a imagem do mito que vira, a medida errada riscada, a resposta que se monta | 7000×5000, 3 áreas, 10 px = 1 cm | 31 s |
| `reel_rota.py` | **a viagem que mudou a história:** a foto vira o documento, a rota no mapa antigo com o veículo na ponta e a câmera seguindo, o papel carvão, os objetos que se multiplicam, o fecho | 9000×3200, 4 áreas lado a lado | 22 s |

**Fotos não vêm no plugin.** Elas são de terceiros, com licenças diferentes (algumas pedem crédito, outras vêm de
acervos que cobram reuso comercial). Você baixa as suas, confere a licença e anota no `CREDITOS.md` do projeto. A
lista do exemplo do Napoleão está no fim deste arquivo.

## Começar

```bash
mkdir -p ferramentas pecas
cp "${CLAUDE_SKILL_DIR}/modelos/reel_rota.py" ferramentas/reel.py      # ou reel_napoleao.py
# ponha as fotos em pecas/ com os nomes de ARQ (ou troque os nomes em ARQ)
clpy ferramentas/reel.py --folha                    # todas as peças sobre azul: confira os recortes
clpy ferramentas/reel.py --quadros 10 --sem-texto   # o 1º quadro-chave
```

O modelo acha sozinho o motor (`EDITLABS_MOTOR`, que o `clpy` já define) e o projeto. O projeto é a pasta acima de
`ferramentas/`, ou `REEL_PROJETO=<pasta>`. Se faltar alguma peça, ele lista quais.

## O que trocar (só o bloco "1. O QUE TROCAR")

1. **`ARQ`:** o nome de cada arquivo em `pecas/`. PNG é recorte com alfa; JPG é a foto que vira cartão. O comentário
   de cada linha diz o papel da peça na história.
2. **Pontos dentro das imagens, sempre em fração (0–1)** da foto, e não em pixel. Assim, trocar a imagem por outra
   de outro tamanho não quebra nada:
   - `reel_rota.py`: `ROTA` (os pontos da viagem no mapa, do começo ao fim) e `ROSTO` (de onde a íris sai);
   - `reel_napoleao.py`: `MITO2_ALVO` (o que a caneta circula), `DOC_CAIXA` (o pedaço da página), `DOC_SUBLINHA`,
     `DOC_FOCO` e `REGUA_CERTA_CIRCULO`.
   - Para achar um ponto, abra a foto, ache o pixel e divida pela largura e pela altura.
3. **Escala real (Napoleão):** em `ALTURA_CM` vai a altura de cada pessoa. Em `TOPO_SOLA` vai o y do topo da cabeça
   e da sola no recorte **de entrada**. Use `None` para usar a caixa do alfa; ajuste quando há chapéu ou gorro (o
   topo da cabeça fica abaixo dele). `MEDIDAS` traz as três marcas da régua: a errada (que é riscada), a média e a
   resposta.
4. **Texto:** `LEGENDAS` (≤ 8 palavras cada, ≈ 40 no total, com `*palavra*` em vermelho), `TEMPOS_LEG`,
   `ETIQUETAS`, `CARIMBOS` e `RESPOSTA`. Deixe o texto para o fim: monte e confira com `--sem-texto`.
5. **Trilha:** `TRILHA` (arquivo em `pecas/` ou em `$EDITLABS_DATA/colagem/trilhas/`), `TRILHA_INI` (o segundo onde
   começa o trecho calmo) e `TRILHA_LICENCA`.

## Mexer na história (a função `montar`)

- **Tempos** em quadros de 24 por segundo (`FIM = 744` são 31 s). Para alongar uma batida, some N a todos os tempos
  dali para frente: as camadas, a câmera, as transições e `TEMPOS_LEG`.
- **Uma batida = um plano de câmera** (`C.quadro(caixa)` enquadra a caixa do mundo na região segura) com deriva lenta
  até o próximo. Toda transição precisa de um plano no `q0` e outro no `q1`.
- **Trocar uma peça de lugar:** mude o centro dela (`x, y` do mundo) e a caixa do plano que a enquadra.
- **Vocabulário** (todas as funções ficam em `motor/colagem/cena.py`):
  - entradas e movimentos: `cai`, `desliza`, `vira`, `multiplica`, `estilhaca`, `segue`;
  - traços e marcas: `Traco`, `circulo`, `carimbo`, `rajada`, `ondas`, `letras`, `contador`;
  - fundo: `papel_area`.
- Use **uma transição diferente** por passagem: `iris`, `mergulho`, `rasgo`, `empurra` ou `flash`.
- **Para outra mecânica:**
  - linha do tempo (como a Cleópatra): a régua do Napoleão em anos, em vez de cm;
  - contador de relógio (como o Santos-Dumont): `C.contador` andando junto com o `Traco`;
  - fio (como o Dom Pedro): um `Traco` com `suave=True` entre dois objetos.

## Conferir e entregar

```bash
clpy ferramentas/reel.py --margens --sem-texto                    # cortados / fora da margem
clpy ferramentas/reel.py --quadros 0,36,72,108,144,180,216,252,288,324,360,396,432,468,504 --sem-texto
clpy "${CLAUDE_PLUGIN_ROOT}/motor/colagem/folha_quadros.py" previa/quadros previa/folha_quadros.jpg 6
clpy ferramentas/reel.py --video --sem-texto && clpy ferramentas/reel.py --som --sem-texto   # som aprovado
# por último: o texto, e de novo vídeo e som (os efeitos dos carimbos nascem da cena)
clpy ferramentas/reel.py --video && clpy ferramentas/reel.py --som
clpy "${CLAUDE_PLUGIN_ROOT}/motor/colagem/conferir.py" . previa/sem_som.mp4
```

Uma etiqueta passando pela borda durante um movimento é normal no `--margens`; parada fora da margem, não.
`conferir.py` só aceita borrão nos chicotes de câmera e no cartão que vira.

## As fotos do exemplo do Napoleão (onde achar e licença)

Para reproduzir o exemplo, baixe estas imagens (confira a licença na página antes) e ponha em `pecas/` com os nomes
de `ARQ`. Os recortes (pessoas e objetos) saem com o `recorte.swift` do motor.

| peça | o que é | onde | licença e crédito |
| --- | --- | --- | --- |
| `pessoa_em_pe.png` | *The Emperor Napoleon in His Study at the Tuileries*, J.-L. David, 1812 (recorte) | Commons: `Jacques-Louis_David_-_The_Emperor_Napoleon_in_His_Study_at_the_Tuileries_-_Google_Art_Project.jpg` | domínio público; cortesia: National Gallery of Art, Washington |
| `contraste_em_pe.png` | granadeiro da Guarda Imperial, estampa da série *Troupes Françaises* (recorte) | Commons: `Garde_Impériale_Grenadiers_(à_pied)_-_estampe_-_btv1b6941036w.jpg` | domínio público, **mas é digitalização da BnF/Gallica (reuso comercial cobrado)**: para post comercial, troque por uma estampa equivalente de acervo com Open Access |
| `mito.jpg` | *Maniac-raving's – or – Little Boney in a strong fit*, J. Gillray, 1803 | Library of Congress, item 94509079 | domínio público |
| `mito2.jpg` | *The King of Brobdingnag and Gulliver*, J. Gillray, 1803 | The Met, Open Access, 17.3.888-313 | CC0 |
| `lugar.jpg` | *Geological plan and elevation of the Island of St Helena* (1816) | Wellcome Collection, L0069644 | Public Domain Mark |
| `documento.jpg` | p. 158, t. II das *Mémoires du docteur F. Antommarchi* (1825), com a medida | Wellcome Collection, b29331882 | Public Domain Mark |
| `obj_abertura.png` | bicorne de Napoleão, Musée de l'Armée | Commons: `Paris_-_Musée_de_l'Armée_-_Chapeau_ayant_appartenu_à_Napoléon_Bonaparte.jpg` | **CC BY-SA 3.0**, foto de Thesupermat (crédito obrigatório) |
| `obj_chegada.png` | maquete do HMS Northumberland (1798) | Commons: `HMS_Northumberland_(1798).PNG` | **CC BY 3.0**, foto de Maciej Szczepańczyk (crédito obrigatório) |
| `obj_drama.png` | máscara mortuária de Napoleão I, Musée Carnavalet | Paris Musées / Commons: `Masque_mortuaire_de_Napoléon_1er_(1769-1821),_S578.jpg` | CC0 |
| `regua_errada.png` | régua dobrável de dois pés, em polegadas inglesas | Commons: `Folding_rule_(AM_1994.25-1).jpg` | **CC BY 4.0**, Auckland War Memorial Museum (crédito obrigatório) |
| `regua_certa.png` | régua *Demy Pied de Roy*, séc. XVIII, Musée d'histoire des sciences de Genève | Commons: `Half_french_kings_foot-MHS_1840-P5200158-white.jpg` | **CC BY-SA 3.0 FR**, foto de Rama (crédito obrigatório) |

Linha de crédito pronta para a descrição do post desse exemplo: *Imagens: National Gallery of Art; Library of
Congress; The Met; Wellcome Collection; Paris Musées; chapéu: foto de Thesupermat, CC BY-SA 3.0; maquete do
Northumberland: foto de Maciej Szczepańczyk, CC BY 3.0; régua inglesa: Auckland War Memorial Museum, CC BY 4.0; régua
do rei: foto de Rama, CC BY-SA 3.0 FR.*

No `reel_rota.py`, os nomes de `ARQ` são genéricos (pessoa, retrato, documento, mapa, veículo, lugar, objeto,
fecho), e os textos de exemplo seguem a história do telefone de 1876. Busque as fotos como em
`../referencias/pesquisa-e-licencas.md`.
