# Exemplos de mecânica

Cada exemplo é um assunto ilustrativo, a mecânica que o conta e o cuidado de fato que ele pede. Use para escolher
o modelo e a mecânica de um reel novo. Todos são 9:16, sem voz, em colagem de papel antigo, com fotos reais de acervo.

| assunto ilustrativo | gancho (≤ 10 palavras) | mecânica principal (a caneta) | modelo mais próximo |
| --- | --- | --- | --- |
| Cleópatra, a Lua e as pirâmides | "Cleópatra viveu mais perto da *chegada à Lua* do que das *pirâmides*." | **régua do tempo:** linha vertical de anos em escala; a caneta mede um intervalo e depois o outro | `reel_regua_tempo.py` |
| a altura de Napoleão | "Napoleão *não* era baixinho." | **medida em escala real:** régua de 10 px = 1 cm; a medida errada riscada, a média, a resposta no topo da cabeça | `reel_napoleao.py` |
| o roubo da Mona Lisa | "A Mona Lisa ficou *mais famosa* quando *sumiu*." | **contorno + rota:** a caneta contorna o vão vazio; depois a rota de uma cidade a outra | `reel_rota.py` |
| Santos-Dumont e o relógio | "Um brasileiro ajudou a tirar o relógio do *bolso*." | **rota + contador:** o veículo na ponta da caneta e um relógio que corre junto | `reel_rota.py` |
| o cérebro de Einstein | "Einstein pediu para ser *cremado*." | **grade de corte + duas rotas:** a imagem estilhaça em blocos que voam para o destino | `reel_rota.py` |
| Dom Pedro II e o telefone | "Quase ninguém *ligava* pro telefone." | **rota + fio:** a viagem no mapa; depois um fio de caneta liga dois objetos | `reel_rota.py` |

## Como cada mecânica anda

**Régua do tempo (Cleópatra).**
- **Mecânica:** o gancho abre no personagem e a câmera dá um chicote até o marco mais antigo. A caneta desce a régua
  e mede até o personagem, com o contador de anos correndo junto da ponta; o carimbo com a resposta cai na batida da
  trilha. A câmera recua, volta ao personagem e a caneta mede até o marco recente (segundo carimbo, na batida). O fecho
  é o plano geral da linha inteira, com a caneta circulando o marco antigo.
- **Por que funciona:** a régua está em escala (0,8 px por ano), então o comprimento do traço já é a resposta. Uma
  mecânica só basta para um reel de 20 s.
- **Cuidado de fato:** não existe ano zero (de 30 a.C. a 1969 são 1.998 anos). O carimbo arredonda ("≈ 2.000 anos")
  e o contador mostra o número exato. Confira se a frase vale nas duas contas (do nascimento e da morte).

**Medida em escala real (Napoleão).**
- **Mecânica:** o objeto real abre o vídeo (o chapéu). Uma íris abre na régua, e a caneta sobe até a cabeça (carimbo
  "?"). O retrato vira a caricatura do mito e volta. Quem fazia a pessoa parecer menor entra marchando, e uma linha
  tracejada liga as duas cabeças. Uma íris vai ao lugar do momento dramático (papel carvão), com o navio, a máscara e o
  mergulho na linha da página que dá a medida. Depois vem um rasgo, e a régua mostra a medida errada riscada. As duas
  unidades aparecem (polegada inglesa × francesa), a caneta marca a média e a resposta, a resposta se monta no alto e
  o carimbo do fecho ocupa o lugar da legenda.
- **Cuidado de fato:** as fontes dão de 1,68 a 1,70 m. Use a medida do documento (5 pés, 2 polegadas e 4 linhas) e
  respeite a ordem dos fatos: as caricaturas (1803) vêm antes da medida (1821).

**Contorno + rota (Mona Lisa).**
- **Mecânica:** o quadro é arrancado e o fundo escurece (papel carvão: a noite do roubo). Um mergulho no vão vazio,
  depois a ficha do ladrão; as capas de jornal se multiplicam e a lupa passa sobre o suspeito errado. Cada passagem tem
  uma transição diferente (empurra, rasgo, flash, íris). A caneta faz a rota até a outra cidade, com a locomotiva na
  ponta. A capa vira a foto da volta, e a moldura vazia do começo recebe o quadro no fim.
- **Cuidado de fato:** ela já era célebre antes do roubo, por isso "*mais* famosa", e não "só ficou famosa". O
  ladrão já não trabalhava no museu: ele "ajudou a instalar o vidro".

**Rota + contador (Santos-Dumont).**
- **Mecânica:** um mergulho no mostrador leva ao mapa antigo. A rota vai do ponto de partida à torre, com o dirigível
  na ponta e o contador do relógio correndo junto (`C.contador` com o `Traco`). A foto vira a capa da revista, e um
  empurra leva à cena seguinte. O relógio de bolso voa até o pulso, e uma íris abre no pulso.
- **Cuidado de fato:** o tempo do voo depende da fonte (o do próprio aviador difere do oficial, e daí a polêmica). O
  relógio dele não foi o primeiro de pulso, por isso o fecho diz "ajudou a popularizar".

**Grade de corte + duas rotas (Einstein).**
- **Mecânica:** abre no papel carvão, com um mergulho na cabeça. A grade de corte aparece sobre a gravura do cérebro,
  que estilhaça em blocos que voam para os potes (`C.estilhaca`). Uma íris leva ao mapa antigo, com as duas viagens e a
  câmera seguindo o carro. Um rasgo leva ao fecho escuro.
- **Cuidado de fato:** o médico levou o cérebro "para casa", com o carimbo "sem autorização", e não "roubou"; a
  família aprovou o estudo depois. "≈ 240 pedaços" é o número mais citado.

**Rota + fio (Dom Pedro II).**
- **Mecânica:** a exposição e o invento (círculo de caneta). O personagem entra deslizando, e uma íris abre no rosto.
  No mapa antigo, o navio segue a rota. Um mergulho leva ao inventor e ao caderno com o desenho. Um empurra leva ao
  momento dramático (papel carvão, carimbo da data). Um rasgo volta ao invento: o fio vai até o ouvido do personagem
  (`Traco` com `suave=True`) e saem ondas de som (`C.ondas`). Um flash leva ao fecho: os aparelhos se multiplicam.
- **Cuidado de fato:** a frase famosa vem de um relato posterior, por isso entra como "a frase que ficou". Confira o
  lugar exato do primeiro aparelho no país antes de afirmar.

## O que as mecânicas têm em comum

- O gancho é uma negação ou uma surpresa concreta, em até 10 palavras.
- Há um traço vermelho com sentido em todas, e ele é o fio da história.
- De 3 a 7 transições, todas diferentes, saindo do foco (a régua do tempo, curta, troca a transição pelo chicote e
  pelo recuo de câmera).
- O papel carvão aparece uma vez, no momento dramático.
- A resposta é um número ou uma data, que se monta ou é carimbada no fecho; sem voz, o carimbo cai na batida da trilha.
- Cerca de 40 palavras de legenda, de 19 a 26 efeitos e o master a −20 LUFS.
