# Fase 5 — Render e entrega

Ordem fixa: **som → legenda (se houver) → render final → verificação**. A legenda entra por último
(`${CLAUDE_PLUGIN_ROOT}/REGRAS.md` §2): só escreva a `legenda` global do `plano.json` depois de planos, desenhos e som
fechados; qualquer mudança antes dela obriga a recalcular as janelas. Antes do render final, rode
`python3 ferramentas/zona_segura.py <projeto>` (texto fora da margem é erro).

```bash
python3 ferramentas/render.py <projeto>                         # saida/render_1080.mp4
python3 ferramentas/render.py <projeto> saida/teste.mp4 --de 140 --ate 170   # trecho, só para conferir
```

- Áudio de mp4/m4a é **copiado** bit a bit na peça inteira; wav vira AAC 192k.
- Sem `-shortest`: o vídeo manda no comprimento.
- **Com referência** (reproduzir um vídeo): passe o render pela entrega da referência e meça
  com a mesma régua:
  ```bash
  ffmpeg -i saida/render_1080.mp4 -vf scale=720:1280:flags=bicubic -c:v libx264 -b:v 1265k \
    -maxrate 1600k -bufsize 2500k -pix_fmt yuv420p -an saida/render_720sim.mp4
  python3 ferramentas/comparar.py <quadros_ref> <quadros_nosso> <projeto>
  python3 ferramentas/montar_entrega.py <quadros_ref> <quadros_nosso> <projeto>
  ```
- **Som** (`referencias/som.md`): trilha por baixo, efeitos presos aos quadros do plano e master
  a −14 LUFS. A escuta é do usuário: entregue 2 a 4 trilhas na mesma peça para ele escolher. Efeitos da pasta do
  usuário (`EDITLABS_SONS`, mapa de `som_biblioteca.py`) ou, sem ela, os sintetizados do plugin.
  ```bash
  python3 ferramentas/mixar.py <projeto> saida/render_1080.mp4 saida/final.mp4 --trilha "<música>"
  python3 ferramentas/mixar.py <projeto> saida/render_1080.mp4 saida/final.mp4 --trilha pad_documental   # sem música
  ```
- **Nenhuma cena igual** entre os vídeos da série (o mesmo gráfico, a mesma folha, o mesmo fim): confira todos os
  vídeos da entrega juntos. Sem render (rápido, para mexer nos planos) e depois nos mp4 finais:
  ```bash
  python3 ferramentas/cenas_iguais.py <saida> ep01=<projeto1> ep02=<projeto2> ...
  python3 ferramentas/cenas_iguais.py <saida> ep01=<video1.mp4>:<plano1.json> ...
  ```
  Par "igual" (distância ≤ 0,15) muda de enquadramento, fundo ou tamanho, não só de palavra. Uma versão por vídeo:
  cinco ganchos com o mesmo corpo são cinco vídeos iguais.
- **Laudo final** do Diretor (D4 em tempo real) em `saida/LAUDO_final.md`.

Entrega: o mp4, os trípticos (ou o lado a lado e as pranchas), o laudo e `assets/FONTES.md`.
