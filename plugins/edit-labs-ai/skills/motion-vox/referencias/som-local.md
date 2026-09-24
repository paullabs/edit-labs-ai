# Som editorial — biblioteca local, recorte e mixagem

## Biblioteca e seleção

Biblioteca: a biblioteca local de efeitos do usuário — pergunte o caminho.

Usar essa biblioteca como primeira opção. Antes de procurar, confirmar que a pasta existe
(e, se estiver num disco externo, que ele está montado); nunca criar uma pasta vazia nesse
caminho para fingir que a biblioteca existe. Não empacotar nem redistribuir a biblioteca
com a skill. Copiar para o projeto apenas os sons escolhidos, preservando os originais.

Categorias que costumam servir; nenhum arquivo é aprovado só pelo nome:

| Grupo | O que procurar | Possível função |
|---|---|---|
| câmeras | cliques de obturador e de disparo, de câmera digital ou antiga | Captura de print, foto que entra, pequeno encaixe. Priorizar o clique mais suave após ouvir. |
| toques | toque curto, seleção | Toque ou seleção, se o timbre combinar. |
| whoosh curto | passagem de ar curta e leve | Deslize curto ou desfoque, sem ocupar a frase seguinte. |
| whoosh suave | transição de ar macia, sem impacto | Passagem leve de imagem. |
| giz / escrita | giz ou lápis riscando papel ou quadro | Só se houver uma anotação sendo desenhada. |

Ouvir candidatos e comparar no contexto da fala. Não deduzir suavidade pelo nome, pelo
pico ou pela waveform. Se não houver capacidade de escuta, preparar a seleção e indicar
que a escuta está pendente; nunca inventar uma aprovação sonora.

## Recorte útil e sincronização

Um arquivo pode ter preparação, vários cliques ou uma cauda longa. Selecionar o evento
útil, em vez de usar o arquivo inteiro por padrão. Inspecionar waveform/espectrograma e
ouvir para localizar o ataque, o pico percebido e a cauda necessária.

- Clique: conservar o ataque reconhecível e uma cauda curta natural; retirar espera e
  cliques adicionais. Não cortar o próprio ataque tentando reduzir a duração.
- Whoosh: pode começar antes do corte; alinhar o pico da passagem com a mudança visual.
- Aplicar fades curtos nas extremidades quando evitarem estalo. Ponto de partida:
  1–3 ms na entrada de um clique, 5–20 ms na saída, mais tempo em caudas suaves. Adaptar
  ao material; não dissolver o transiente que torna o som reconhecível.
- A âncora do som é um instante dentro do arquivo, não necessariamente seu início:
  `inicio_timeline = timeline_at - (anchor_at - source_in)`.
- Se o pré-ataque cair antes do vídeo, rever trecho/âncora conscientemente; não deslocar
  o clique com um clamp silencioso. O efeito não deve estender a duração do vídeo.

## Ganho e mixagem

Abaixar o SFX em relação à voz. O ganho deve ser escolhido por arquivo e por evento:
`volume=-18dB` significa reduzir o arquivo em 18 dB, não atingir pico de −18 dBFS.
Começar com redução conservadora e ouvir a soma. Não normalizar todos os arquivos para
o mesmo pico nem supor que um valor fixo torna qualquer efeito suave.

Preservar a voz; baixar primeiro o efeito que mascara uma palavra. Usar
`amix:normalize=0` para evitar a queda automática do ganho da fala. Medir os picos e o
true peak da mix final, pois sons sobrepostos podem estourar mesmo quando cada arquivo
isolado parece baixo. Se houver excesso, reduzir os SFX antes de recorrer a limitador.
Um limitador não é licença para tornar a mix agressiva nem para elevar todo o volume.

Som deve pontuar informação. Não colocar efeito em todo corte, não adicionar som de
câmera a qualquer ação e não alternar clique/giz mecanicamente. Variar quando houver
função e usar silêncio quando ele preservar a clareza.

## Mapa por evento e integração

No bloco de configuração do projeto, usar `SFX_EVENTS`, uma lista de dicionários. Cada
entrada exige os campos abaixo; tempos em segundos, `source_in`, `source_out` e
`anchor_at` referidos ao arquivo sonoro original. `timeline_at` é local ao vídeo cortado.

| Campo | Significado |
|---|---|
| `source` | Arquivo existente, absoluto ou relativo à raiz do projeto. Preferir a cópia local selecionada. |
| `source_in`, `source_out` | Início e fim exclusivos do trecho útil. |
| `anchor_at` | Transiente/pico escolhido, dentro desse trecho. |
| `timeline_at` | Instante visual que o transiente deve acompanhar. |
| `gain_db` | Atenuação individual, zero ou negativa. |
| `fade_in`, `fade_out` | Fades em segundos, compatíveis com o trecho. |
| `reason` | Ação ilustrada e motivo da seleção. |

Copiar `lib/sfx.py` para junto de `render.py`. O template consulta `SFX_EVENTS` e monta
trim, fades, ganho e atraso em amostras a 48 kHz. Valida caminhos, tempos, pré-ataque,
limites de duração e ganho antes de renderizar. Não gera som, não escolhe timbre e não
substitui a escuta. Campos não podem ser preenchidos automaticamente só pelo nome.

`SFX_EVENTS=[]` significa sem SFX. Não combinar com `SFX_TIMES`: o pool legado só é
aceito quando o novo mapa não foi definido. Arquivo faltante gera erro, sem fallback
silencioso para outro som.

Guardar o mapa efetivamente usado em `06_transitions/SFX_MAP.json`, junto do nome da
fonte e do motivo de cada recorte, para permitir revisão e reajuste. O template publica esse mapa apenas após sucesso:
`[]` quando não há SFX; registros com `mode=legacy_prepared` quando o projeto usa o
pool legado, sem confundi-los com eventos recortados do fluxo novo.

## Revisão do som

O revisor deve reproduzir o trecho já mixado: ataque no evento certo, nenhum clique
extra, cauda limpa, voz dominante e sem efeito cobrindo a consoante seguinte. Conferir
em volume normal e baixo e documentar o que realmente foi ouvido/medido.

Guardar a fala isolada. Sem mix ou reencode, comparar o áudio decodificado com a fonte
usando o mesmo formato de amostras. Com SFX, o MD5 do master muda legitimamente:
comparar a fala isolada, duração, sincronismo e trechos fora dos eventos; registrar
picos da soma e escuta. A retranscrição não prova que a mix é agradável.
