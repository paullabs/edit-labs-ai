# Armadilhas — as que custaram tempo de verdade

Cada uma aconteceu no Hedy. A correção já está no motor; a lista existe para não voltar.

**Medição**
- **Calibrar antes da compressão engana.** A entrega 720p (~1,26 Mbps, croma subamostrado)
  come metade do RGB split, apaga a cor da scanline e o ruído do escuro. Meça sempre o nosso
  passado pela mesma entrega.
- **"Preto" que esconde textura.** O fundo do gancho parecia chapado (média 11) e era papel
  quadriculado. Estique o contraste ×5–7 antes de declarar fundo liso. O domo teal do
  roteador só apareceu assim.
- **Grão medido por passa-alta** soma a scanline. Tire o perfil por linha antes.
- **Nitidez pela variância do Laplaciano** no quadro entregue mede scanline e grão, não foco.
  Meça desfoque numa borda conhecida (ou compare a olho).
- **Fonte escolhida de olho.** Ranqueie candidatas pelo perfil de colunas na mesma altura e
  largura (Arial 0,90 × Inter 0,70 no gancho).
- **Medir objeto pela caixa da tinta** quando ele tem partes finas: as antenas puxaram o centro
  do roteador 138 px para cima. Ancore pelo corpo (`ponto_objeto`).
- **Fade de palavra "45% no 1º degrau"** não é regra: o fade é contínuo a partir da fala e a
  grade só amostra (8% a 41% no 1º degrau, conforme a fase).

**Assets**
- **Desenhar o que existe.** Ícone de software, cursor, site: pegue o real (app instalado,
  sistema, print). O desenhado ficou genérico e o real bateu sozinho.
- **Recorte de fundo em degradê** vaza nos casacos: inunde só do topo numa cópia alisada
  (tolerância 3) e apague o chão abaixo da linha dos pés.
- **Fundo cercado** (entre os pedestais da corda) não sai com inundação pela borda: `--tudo`.
- **Rosto de pessoa real gerado**: nunca. Foto licenciada ou outro enquadramento.

**Código**
- **Alfa 0–255 × 0–1** na composição: normalize ao colar (`compor.sobre` já faz).
- **`corrigir` (ganho/saturação) aplicado no alfa** deixa a foto translúcida: só no RGB.
- **Default `px=CONSTANTE`** congela no import: leia a constante dentro da função.
- **`getbbox` do Pillow** ignora o recuo esquerdo positivo do glifo (Arial E: 7 px): a caixa da
  tinta vem dos pixels desenhados (`c2_letras._tinta_glifo`).
- **`str.replace` em lote falha em silêncio**: confira com `assert` ou grep depois.
- **Áudio**: `-shortest` corta o último quadro e recodificar AAC muda o áudio. Peça inteira
  copia o áudio (MD5 dos pacotes igual ao da origem).
- **Grão por pixel e por quadro** é incompressível: explode o bitrate do master. O grão
  congela com o quadro da grade (3 quadros iguais).
- **Texto por filtro do ffmpeg**: o ffmpeg desta máquina não tem libass — todo texto entra
  pelo motor (PIL), nunca por `drawtext`/`subtitles`.
