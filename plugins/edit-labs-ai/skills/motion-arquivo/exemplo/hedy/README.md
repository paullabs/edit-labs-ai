# Exemplo — Hedy Lamarr (32 s, 23 planos)

A referência que originou a Família A, reproduzida duas vezes. Só código e texto próprios: nenhum quadro, áudio
ou trecho do vídeo de referência vem junto, e a referência é citada só pelo assunto (o reel sobre Hedy Lamarr,
a atriz que ajudou a inventar o salto de frequência).

- **`plano.json`** — os 32 s só com os tipos genéricos da skill (22 planos; o 6 e o 7 do original são um só). É o
  modelo de como um projeto novo se escreve. Os textos na tela foram reescritos em português; os tempos, as
  posições e os movimentos são os medidos. Contra o original, na mesma régua: 21/21 cortes no mesmo quadro.
- **`cena_sob_medida.py`** (+ `teste_hedy.py`) — a versão medida plano a plano, com as tabelas do original
  (`EVERY_`, `P7_`, `P13_`, `P20_`, `P22_`). Serve de referência de como se mede e se tabela um plano quando o
  objetivo é ficar IGUAL a um vídeo existente (`referencias/medir-referencia.md`).

Assets (não vêm no plugin; o projeto baixa ou gera):

- fotos da Hedy em domínio público/CC0 (Wikimedia Commons) — `ferramentas/buscar_assets.py commons "Hedy Lamarr 1940"`,
  depois `baixar_asset.py`, que registra a origem em `assets/FONTES.md`;
- objetos sem pessoa real gerados no Higgsfield (roteador, torpedo, lixeira, lousa...); a moldura dourada e o papel
  amassado já estão em `motor/kit/`;
- ícone do app e cursor de mão REAIS tirados da máquina (`ferramentas/assets_locais.py`).
