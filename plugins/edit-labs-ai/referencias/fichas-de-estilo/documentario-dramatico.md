# Ficha de estilo: documentario-dramatico

**Quando usar:** narrativa dramática em documento: medo, perda, espera, investigação. O peso vem de **foto de arquivo em preto e branco, granulada, dentro de moldura de negativo**, sobre **papel de jornal ou de documento**, com **palavras que entram uma por vez** e **um único vermelho** para anotação. Serve para drama de pessoas reais e também para histórias de corpo e mente.

**Evidência:** R23 MiraRuido, *The New Promised Land, Chapter 3* (**a fundo** em movimento: 99 s medidos a cada 0,25 s, mais tremor a cada 0,04 s; **áudio não ouvido**). Paleta: `paletas/paletas.json` → `documentario-new-promised-land`.

**Diferença da `colagem-documental`:** aquela é uma história com documentos coloridos e acento verde/salmão; esta é **dramática, quase toda em P&B**, com sombras frias e um só vermelho. Não misturar as duas no mesmo vídeo.

## O sistema
| item | regra | confiança |
|---|---|---|
| foto | **P&B granulada com meio-tom**, contraste alto nas sombras | a fundo (R23) |
| moldura | **tarja de negativo preta** com cantos levemente arredondados | a fundo (R23) |
| fundo | **papel de jornal ou de documento amarelado**, com texto ilegível em miniatura | a fundo (R23) |
| acento | **um vermelho** (`#C35853` medido), só em anotação manuscrita, carimbo ou marcação | a fundo (R23) |
| tipografia | **manuscrito vermelho** para anotação e **serifada em caixa alta** para carimbo e fala | a fundo (R23) |
| luz | vinheta leve; **sombras frias** (preto azulado) contra papel quente | a fundo (R23) |
| **ritmo** | **corte a cada ~2,75 s** (mediana; 30 cortes em 99 s); entrada da foto em **~1 s**; **trecho estável de 2 a 3 s** | medido (R23) |
| **deriva de câmera** | **conteúdo inteiro desliza ~1 px a cada 0,25 s para a esquerda** (câmera vai para a direita), ~40 a 50 px/s em 1080p; varia de ~5 a ~50 px/s por trecho | medido (R23) |
| **tremor** | a imagem **treme a cada quadro** (diferença entre quadros vizinhos alterna ~10 e ~5 níveis), sobre a deriva | medido (R23) |
| palavra | **palavra que entra por frase** (letras ou linha inteira), sobre fundo parado | a fundo (R23) |
| fim | congela ~2 s no último texto | medido (R23) |
| **tarja horizontal fixa** | **não existe**: as linhas de documento aparecem em alturas variáveis, sem varredura | medido (R23): descartada |

## No nosso motor
- Deriva de câmera: `Camera.chaves` com `cx` variando ~40 px/s na tela (1080p), com chaves lineares. Ritmo de corte: cortes secos, sem `Transicao`.
- Tremor por quadro: `boil` na classe `obj` (já existe), amplitude um pouco maior que a da Vox.
- Foto P&B: `papelizar(estilo="gravura", cor=0)` com grão; a moldura de negativo é um retângulo preto com cantos `borda_papel`.
- Papel de jornal: `PC.papel_mundo` com tom quente e textura de texto (imagem de documento em miniatura).
- Palavra que entra: `C.letras` (já existe) em serifada caixa alta; uma frase por vez.
- Anotação vermelha: `Traco` com cor `#C35853`, desenhado com `trim`.
- Movimento de entrada: `C.cai` ou `K.desliza` com escala de 0,8 para 1,0 em 1 s.

## No invideo
Fotos como imagens com alfa; moldura como forma preta; palavras como textos com `set_text` por frase; anotação como forma de caminho com `trim_shape_path`; sombra fria como efeito `drop_shadow` com cor azulada. Escrever um efeito GLSL só se for preciso para o grão da foto.

## Riscos
- **Pessoas reais:** nunca reutilizar foto de pessoas reais de projetos de terceiros. Usar arquivo de domínio público e crédito do acervo.
- **Peso:** o estilo é pesado; em assunto leve parece exagero.
- **Documento falso:** jornal e carimbo podem passar por fato. Em anatomia, as fontes e o texto precisam estar claros.
- **Sem confirmação:** o áudio (narração, trilha). A tarja horizontal foi descartada; a deriva de câmera e o ritmo estão medidos.
