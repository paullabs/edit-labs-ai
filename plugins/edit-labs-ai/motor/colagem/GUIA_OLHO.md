# Guia do olho: regras de leitura das colagens

O estilo funciona como um guia: o olho vai sempre ao lugar mais óbvio, e a próxima coisa aparece ali ou é levada até
lá pela caneta ou pela câmera. Muita gente enxerga mal no celular, então nada pode ser pequeno nem abstrato.

> Explicador narrado em camadas: **sem legenda de fala embaixo**. Se precisar nomear, rótulo curto preso ao objeto
> (1–2 palavras) e no máximo 1 número em carimbo, dentro da margem x 80–960 / y 260–1420. As regras gerais estão em
> `REGRAS.md` na raiz do plugin.

## Tamanho mínimo na tela (1080×1920)

| elemento | mínimo | como é garantido |
| --- | --- | --- |
| legenda (só nos estilos que usam) | corpo 64 px, Inter 800, faixa até 880 px | `pecas.legenda` (quebra sozinha; número + unidade não se separam) |
| etiqueta / rótulo | 1ª linha ≥ 50–54 px na tela | `motor.ajustar_texto`, que aumenta a escala da etiqueta se a câmera a deixar pequena |
| carimbo | ≥ 58 px na tela | idem |
| objeto principal | ≥ 600 px; a maior parte da largura útil | `cena.quadro(caixa)` enquadra pela região segura |

## O caminho do olho

1. **Um foco por vez.** Em cada batida, um objeto principal e no máximo dois de apoio. O que entra novo aparece perto do
   foco atual ou é trazido até lá: pela ponta da caneta, por um objeto que viaja no traço, ou por um deslizamento que
   parte da borda mais próxima.
2. **A imagem vem antes do texto.** Primeiro o olho chega no objeto; depois o rótulo confirma.
3. **Transição a partir do foco.** O mergulho e a íris saem do ponto onde o olho está (o vão da moldura, a cabeça, o
   mostrador) e chegam no foco da cena seguinte.
4. **Nada abstrato:**
   - **Objetos:** sempre reais e reconhecíveis (foto recortada ou 3D papelizado).
   - **Explosão de traços:** só no carimbo, para marcar a batida.
   - **Grade em losango:** clara, só como fundo.
   - **Borrão:** só nos movimentos rápidos de câmera, e leve. Nunca através de um corte: o 1º desenho depois de uma
     transição é sempre nítido.
5. **Margens:** conteúdo dentro de x 80–960 e y 260–1420 (interface do Reels, TikTok e Shorts).

## Conferências automáticas (antes de entregar)

- `motor.checar_margens(camadas, cam, quadros)`: objetos cortados ou fora da margem.
- `motor.ajustar_texto(...)`: texto pequeno; corrige sozinho e lista o que mudou.
- `python3 -I conferir.py <pasta do projeto> <video>`: no vídeo pronto, aponta desenhos borrados fora das transições e
  textos que ainda ficaram pequenos.
