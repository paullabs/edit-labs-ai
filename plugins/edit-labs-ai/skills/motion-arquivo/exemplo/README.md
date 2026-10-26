# Exemplos

- [`hedy/`](hedy/README.md): estudo de medida de uma referência de terceiros (o reel sobre Hedy Lamarr), com o
  plano em tipos genéricos e a medida plano a plano. Crédito ao autor original; não é para republicar.
- `plano_teste_pipeline.json`: teste ponta a ponta de 13,7 s (410 quadros) que mostra o formato mínimo de um
  projeto: transcrição → batidas → plano → ícone e cursor reais da máquina → trípticos → render.

## Rodar o teste do pipeline

A narração (`audio/narracao.wav`) é **sua**: grave a sua ou use qualquer wav com pelo menos 13,7 s. Para testar só
a imagem, um wav mudo gerado na hora serve. O ícone entra com o nome genérico `icone_app.png` (qualquer app seu).

```bash
mkdir -p teste/audio
cp ${CLAUDE_SKILL_DIR}/exemplo/plano_teste_pipeline.json teste/plano.json
ffmpeg -v error -y -f lavfi -i anullsrc=r=48000:cl=mono -t 13.7 teste/audio/narracao.wav   # wav mudo, só para tempo
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/assets_locais.py icone "Calculator" teste             # macOS; ou copie um PNG seu
cp teste/assets/reais/icone_calculator.png teste/assets/reais/icone_app.png
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/assets_locais.py cursor pointinghand teste            # macOS (precisa do swift)
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/triptico.py teste                                     # saida/tripticos/
mvpy ${CLAUDE_SKILL_DIR}/ferramentas/render.py teste                                       # saida/render_1080.mp4
```

Fora do macOS, ponha um PNG de ícone em `teste/assets/reais/icone_app.png` e um cursor de mão em
`teste/assets/reais/cursor_pointinghand.png`. Sem o wav, o `render.py` para e diz o caminho que falta.
