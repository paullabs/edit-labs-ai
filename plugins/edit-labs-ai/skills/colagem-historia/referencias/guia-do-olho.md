# Guia do olho: como a colagem é lida no celular

O estilo funciona como um guia: o olho vai sempre ao lugar mais óbvio, e a próxima coisa aparece ali ou é levada até
lá pela caneta ou pela câmera. Muita gente enxerga mal no celular, então nada pode ser pequeno nem abstrato.

## Tamanho mínimo na tela (1080×1920)

| elemento | mínimo | como é garantido |
| --- | --- | --- |
| legenda | corpo 64 px, faixa de até 880 px | `PC.legenda` (quebra sozinha; número e unidade não se separam) |
| etiqueta (nome, data) | 1ª linha ≥ 50–54 px na tela | `M.ajustar_texto` aumenta a escala se a câmera a deixar pequena |
| carimbo | ≥ 58 px na tela | idem |
| objeto principal | a maior parte da largura útil | `C.quadro(caixa, regiao)` enquadra pela região segura |

## O caminho do olho

1. **Um foco por vez.** Em cada batida há um objeto principal e no máximo dois de apoio. O que entra novo aparece
   perto do foco atual ou é trazido até lá: pela ponta da caneta, por um objeto que viaja no traço ou por um
   deslizamento que parte da borda mais próxima.
2. **A câmera vai antes do texto.** Primeiro o olho chega no objeto, depois a legenda confirma. Como a legenda fica
   sempre no mesmo lugar (y 1320), o olho aprende onde ler.
3. **Transição a partir do foco.** O mergulho e a íris saem do ponto onde o olho está (o vão da moldura, a cabeça, o
   mostrador) e chegam no foco da cena seguinte.
4. **Nada abstrato:**
   - **objetos:** sempre reais e reconhecíveis (moldura, baú, trem, chapéu, régua);
   - **explosão de traços:** só no carimbo, para marcar a batida;
   - **grade em losango:** clara, só como fundo;
   - **borrão:** só nos movimentos rápidos de câmera, e leve. Nunca através de um corte.
5. **Margens** (as do `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`):
   - laterais: x 80–960;
   - nada importante acima de y 260 nem abaixo de y 1420 (interface do Reels, TikTok e Shorts);
   - o assunto fica entre y 260 e 1190, e a legenda entra em 1320. Os modelos usam `REGIAO = (80, 260, 960, 1190)`.

## Conferências automáticas (antes de entregar)

- `M.checar_margens(camadas, cam, quadros, regiao)` (nos modelos: `--margens`): objetos cortados ou fora da margem.
  Uma etiqueta passando na borda durante um movimento é aceitável; parada fora da margem, não.
- `M.ajustar_texto(...)`: texto pequeno. Corrige sozinho e lista o que mudou.
- `conferir.py <projeto> <vídeo>`: no vídeo pronto, aponta desenhos borrados fora das transições e textos que ainda
  ficaram pequenos.
