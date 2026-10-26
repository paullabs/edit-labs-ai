# Estudo de medida: o reel sobre Hedy Lamarr (32 s, 23 planos)

Um **estudo de medida** de uma referência de terceiros: o reel curto sobre Hedy Lamarr, a atriz que ajudou a
inventar o salto de frequência. O crédito e os direitos do vídeo são do autor original; ele foi medido quadro a
quadro só para tirar a régua da Família A (tempos, posições, movimentos, cadência). Isto **não** é uma réplica para
publicar: serve para aprender a medir e a tabelar um plano.

Só código e texto próprios: nenhum quadro, áudio ou trecho do vídeo original vem junto, e a referência é citada só
pelo assunto.

- **`plano.json`**: os 32 s escritos só com os tipos genéricos da skill (22 planos; o 6 e o 7 do original viram
  um só). É o modelo de como um projeto novo se escreve. Os textos na tela foram reescritos em português; os
  tempos, as posições e os movimentos são os medidos (21/21 cortes caem no mesmo quadro da referência).
- **`cena_sob_medida.py`** (+ `teste_hedy.py`): a medida plano a plano, com as tabelas tiradas da referência
  (`EVERY_`, `P7_`, `P13_`, `P20_`, `P22_`). Mostra como se mede e se tabela um plano
  (`referencias/medir-referencia.md`). Os poucos rótulos curtos em inglês ficaram porque a largura e o tempo por
  letra foram medidos neles; num projeto seu, o texto é o da sua narração.

Para usar o estilo num vídeo seu, parta do `plano.json` e troque assunto, textos e assets; não republique a
sequência da referência.

Assets (não vêm no plugin; o projeto baixa ou gera):

- fotos da Hedy em domínio público/CC0 (Wikimedia Commons): `mvpy ${CLAUDE_SKILL_DIR}/ferramentas/buscar_assets.py
  commons "Hedy Lamarr 1940"`, depois `baixar_asset.py`, que registra a origem em `assets/FONTES.md`;
- objetos sem pessoa real gerados no Higgsfield (roteador, torpedo, lixeira, lousa...); a moldura dourada e o papel
  amassado já estão em `motor/kit/`;
- ícone do app e cursor de mão reais tirados da máquina (`ferramentas/assets_locais.py`).
- a narração não vem: o `plano.json` espera `audio/narracao.mp4` na pasta do projeto.
