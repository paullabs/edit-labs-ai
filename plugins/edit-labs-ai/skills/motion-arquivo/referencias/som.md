# Som: trilha, efeitos e master

As referências medidas do estilo (o arquivo em papel do Hedy, a galeria documental, o explicador claro, o preto com
régua, o explicador de dados) têm trilha por baixo, efeito no evento e master a −14 LUFS. Vídeo só com voz soa vazio
ao lado delas. As regras gerais de som estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`; aqui fica o que é deste estilo.

```bash
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/mixar.py <projeto> saida/render_1080.mp4 saida/final.mp4 --trilha "<música>"
```

## De onde vem o som (o plugin não traz biblioteca de terceiros)

| fonte | o que é | como ligar |
| --- | --- | --- |
| **a sua pasta de efeitos** | qualquer pasta com .wav/.mp3/.aif/.flac de que você tem licença | `export EDITLABS_SONS="<pasta>"` (ou `--biblioteca <pasta>`), depois `mvpy ${CLAUDE_SKILL_DIR}/ferramentas/som_biblioteca.py` uma vez |
| **reserva sintetizada** | 13 efeitos feitos em código (`motor/som.py`, gravados em `motor/kit/sfx/`) | automático: sem pasta, sem mapa ou sem arquivo para um papel |
| **trilha** | a sua pasta de músicas, ou as camas compostas em código (`compor_trilha.py`) e os pads (`--trilha pad_documental`) | `--trilha <arquivo>` ou o nome do pad |

O mapa de recortes (`som_biblioteca.json`) e o catálogo medido (`som_catalogo.json`) ficam fora do plugin, em
`$EDITLABS_DATA/motion-arquivo/` (padrão `~/.local/share/edit-labs-ai/motion-arquivo/`). Os arquivos
`motor/kit/som_*.modelo.json` mostram o formato. Nada da sua biblioteca é copiado: o mapa guarda só o caminho relativo,
o recorte e a âncora.

## Trilha
- **Origem, nesta ordem:** a pasta de músicas do usuário, depois a cama composta (`compor_trilha.py`) ou o pad
  sintetizado de `motor/som.py` (`pad_documental`, `pad_dados`, `pad_explicador`, `grave_808`). O pad é igualado em
  quatro bandas de frequência à trilha de cada referência (`som.ALVOS`).
- **Escolha por medida, aprovação de ouvido.** Para escolher entre as músicas do usuário, meça bandas, força da
  batida e variação de nível. Em documentário, procure a música estável e sem batida. Depois gere a mesma peça com 2 a
  4 trilhas e deixe o usuário escolher ouvindo.
- **Trecho:** o mixador pega a janela mais estável da música (`--trilha-inicio` força outra), com 1 s de entrada e
  2,5 s de saída.
- **Nível:** `--abaixo 15.5` (padrão) põe a trilha 15,5 dB abaixo da voz, e ela baixa mais 3 dB enquanto a voz fala.
  Na régua da referência (mediana do RMS de 10 ms, fala contra o miolo das pausas), isso dá 20 dB, o mesmo da galeria
  documental (19,8). Os outros pontos medidos: arquivo em papel e explicador claro, 13 a 14 dB; preto com régua, 8 dB,
  com uma trilha só de grave, que soa mais baixa do que mede.

## Efeitos
- **Origem:** a pasta do usuário, pelo mapa de `ferramentas/som_biblioteca.py` (cada papel acha o arquivo pelo nome e
  fica com o mais limpo; `--escolha escolha.json` fixa o que você preferir). Papel sem arquivo, ou nenhuma pasta: a
  reserva sintetizada. O `mix.json` diz qual das duas entrou (`efeitos_origem`).
- **Só onde a tela mostra a ação.** O mixador lê os quadros do próprio `plano.json`:

| tela | papel | tela | papel |
| --- | --- | --- | --- |
| carimbo, canal derrubado | baque | clique no Seguir | clique |
| foto que entra na galeria | obturador | dia que acende, linha de corte | tique |
| balão no celular, seleção | balao | contador, barra, pizza ou cadeira enchendo | contador (laço na duração) |
| etiqueta, fatia, o que falta | ponto | círculo, X ou marca feitos à mão | giz |
| letra digitada (seleção, terminal) | tecla | folha do calendário | folhear |
| folha amassada | amassar | câmera que viaja grande (zoom ≥ 28% ou ≥ 300 px) | whoosh / whoosh_suave |

- **Um som por instante:** se dois papéis caem no mesmo quadro, fica o mais importante (`PRIORIDADE` em `mixar.py`).
- **Pedido explícito no plano:** `"som": [{"quadro": 812, "papel": "grave", "nivel": -10}]`. Com `"som": false`, o
  plano fica mudo.
- **Nível** em dB relativos à voz (`NIVEL` em `mixar.py`): clique −8, baque −7, obturador −12, ponto −18, tecla −19,
  contador −23, impacto −8, riser −15, pop −17, palavra −22, bloco −16, hud/seleção −18, ambiente −25. Medido: a soma
  dos efeitos fica 18–19 dB abaixo da voz e o ambiente 25–30 dB abaixo.
- **Ritmo:** o mesmo papel não volta antes de `INTERVALO` quadros (palavra 21, pop 6); `VARIA_TOM` muda o tom do pop e
  do bloco para não virar metralhadora. Sinal de tipo sem mapa: menos de 1 efeito a cada 2 s em `som/mix.json`.

### Os papéis (o que procurar na sua pasta)

| papel | som | quando |
| --- | --- | --- |
| impacto | golpe metálico com grave que segura | a palavra que fecha o gancho (automático) e a quebra (pedido no plano) |
| riser | ar ao contrário que sobe | até o "Só que..." (pedido no plano; o pico cai na palavra) |
| pop | plink curto e quente (o tom varia) | ícone, figura, legenda que aparece |
| palavra | ar curto e baixo | palavra que entra (no máximo uma a cada 0,7 s) |
| bloco | clique mecânico | bloco da semana que vira |
| hud / selecao | janela de interface / botão com glitch | linha do HUD / caixa azul |
| negativo / positivo | acorde menor / acorde que confirma | o que não vale / virou "Seguindo" |
| dinheiro / relogio | contador de cédulas / tique-taque | nota na tela / relógio girando |
| corte_ar1..4 | quatro ares curtos diferentes | toda troca de cena desenhada ou de b-roll |
| amb_vento, amb_cidade, amb_agua, amb_caverna, amb_industria | ambiente estável de 8 s | por baixo de cada b-roll em vídeo, escolhido pelo nome do clipe (o plano força com `"ambiente"`) |

Os padrões de busca de cada papel estão em `ESCOLHA` (`ferramentas/som_biblioteca.py`). Ambiente sem arquivo fica em
silêncio (não há ambiente sintetizado).

### Gancho, quebra e corte
- **Estrutura gancho → curiosidade → quebra → desenvolvimento:** no plano da quebra,
  `"som": [{"quadro": F(só), "papel": "riser"}, {"quadro": F(palavra), "papel": "impacto", "nivel": -11}]`.
- **Toda troca de cena tem som:** o mixador põe um som no `inicio` de cada plano pelo tipo que ENTRA — ar curto que
  roda entre 4 (`corte_ar1..4`) nas cenas desenhadas e no b-roll, obturador nas fotos, papel nas cenas de papel, glitch
  no HUD. Se um golpe/riser/baque/clique cai a 2 quadros do corte, ele faz o papel do corte. O plano pode forçar
  (`"corte_som": "papel"`) ou calar (`false`). Conferir: "trocas com som N/N".

## Master
Ganho até −14 LUFS e limitador a 4× a taxa de amostragem, com pico de −1,5 dBTP antes do AAC e cerca de −1,1 depois.
A 48 kHz, o clique seco passava de −1 dBTP. Uma voz com cerca de 14 dB entre pico e volume médio faz o loudnorm
sozinho parar em −15,5. O limitador corta só os picos, cerca de 1,5 dB.

## Conferir
- `<projeto>/som/mix.json`: nível da voz, ganho da trilha, efeitos por papel, LUFS e pico.
- `<projeto>/som/SFX_MAP.json`: cada efeito com fonte, recorte, âncora, tempo, ganho e motivo.
- **Sincronia:** a correlação entre a voz original e a mix deve dar atraso 0.
- **A escuta é do usuário.** O mixador mede; nada é dado como aprovado de ouvido.

## Medir, provar e criar som sem custo
- **Catalogar a sua pasta:** `ferramentas/catalogar_efeitos.py [<pasta>] [<saida.json>] [<saida.md>]` mede cada arquivo
  (ataque, cauda, golpes, onde está o pico, centróide, grave, planura, tonalidade) e junta as etiquetas do nome. Para
  escolher entre candidatos, desenhe onda + espectrograma ("ouvir com os olhos"): o riser sobe até o fim, o whoosh incha
  no meio, o plink tem uma linha de tom só.
- **Provar efeitos:** `ferramentas/prova_efeitos.py <saida> [<pasta>]` exporta, por papel, o som escolhido e 3
  alternativas que casam com o mesmo padrão, recortados como o mixador usa e com o mesmo pico. Ouça e fixe o preferido
  num `escolha.json` (modelo em `motor/kit/som_escolha.modelo.json`).
- **Medir músicas:** `ferramentas/catalogar_trilhas.py <saida> <pasta de músicas>...` mede estabilidade (desvio do nível
  em janelas de 0,5 s), pulso, centróide, grave e agudo, escolhe a janela mais estável e grava clipes de 25 s no mesmo
  nível (`--reusar` refaz só os clipes). Em geral, poucas faixas de uma biblioteca servem de fundo de voz.
- **"Ouvir" antes de usar:** `ferramentas/ouvir_trilha.py <saida.json> <músicas...>` mede andamento, pulso, golpes por
  segundo (acima de ~4/s é frenético sob a voz), tom e modo (menor = dramático), centróide, a fração na faixa da voz
  (300 Hz–3,4 kHz: quanto menor, mais espaço) e **se tem canto** (faster-whisper no trecho mais cheio). Faixa vendida
  como "instrumental" pode ter canto: sem essa checagem, a música briga com a narração.
- **Compor:** `ferramentas/compor_trilha.py <saida> [curioso|dados|tensao|claro]` gera camas de 96 s (pad, baixo,
  pluck, prato e bumbo suaves). Lições: (1) acordes vizinhos precisam de cruzamento linear de 1 s, senão o nível
  "respira" a cada compasso (desvio 3 dB, contra 0,45 dB depois); (2) reverb de cauda de ruído dá ganho aleatório por
  frequência e uma nota grave pura caía 8 dB: o envio do reverb é passa-alta (200 Hz).
- **Trilha por partes:** `"trilha_partes": [{"quadro", "musica" (arquivo | "silencio"), "ss", "cruza", "entra",
  "ganho"}]` no `plano.json` e `mixar.py ... --trilha partes`. Cada parte é nivelada à mesma referência. Padrão: gancho
  com uma música → a quebra ("Só que...") em silêncio com o riser e o golpe → desenvolvimento com outra → o fim no
  trecho ralo. Varie as músicas entre vídeos.

## Licença do som
- **Fontes grátis para o usuário baixar (checar a licença do arquivo e guardar a página):** Freesound só CC0, YouTube
  Audio Library, Pixabay Music (sem crédito; risco de Content ID), Mixkit (https://mixkit.co/license/ — não vale para
  TV, jogo nem CD). Baixar exige o "pode" do usuário.
- **Biblioteca por assinatura** (Artlist, Epidemic e afins): vale enquanto a licença do usuário cobrir o projeto;
  anote a origem no `FONTES.md`. Nenhum desses arquivos entra no plugin nem no repositório.
- **Música de artista do YouTube não entra** (direito autoral; o Instagram muta ou derruba). Para usar uma faixa
  famosa, entregue a versão `--trilha nenhuma` e o usuário põe a música pelo próprio app na hora de postar.
