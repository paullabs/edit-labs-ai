# PLANO_MOTION — <id> · <título>

> Formato obrigatório (PLANO.md §6.3). `di verificar-plano <id>` lê este arquivo; coluna fora do formato é BLOCKER.
> Tempos em segundos do CORTE, com vírgula ou ponto. Frame = tempo × 24 (unidade do `compose.py`).

## A. Régua do projeto

(de `memoria/regua.yaml` — o Editor não escolhe nenhum destes)

- motion_fps: 12
- densidade_alvo: 0.65–0.75
- fim_de_cena: <flash | push | decidir_vendo>
- min_rosto_s: 1.0
- logos_oficiais: sim
- saida: <V | H | ambas>
- estilo: E1–E9 (`memoria/regua.yaml`)

## B. Cenas

Uma linha por cena. Nada se anima sem linha aqui.

| M# | Âncora | Registro | Referência | O que aparece | Referente | Entra | Se mexe | Fim de cena | SFX | Legenda | Cobre emenda? | Layout H | Motivo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | "Fable" · 0,24 s · f6 | Insert real | Porsche bf06 | logo oficial do Claude grande, "FABLE 5" em etiqueta amarela | marca: Claude (logo oficial) | t0 0,20 s · corte seco, herói já em voo | **prova** logo pousa f5 · **detalhe** etiqueta "FABLE 5" f14 · **conclusão** círculo à mão no "5" f30 | push · t1 1,60 s | — | cala | não | logo à esquerda, etiqueta à direita | "Fable 5" é o assunto do vídeo; logo real da marca citada |

Regras das colunas:
- **Âncora**: `"palavra" · t s · f<t×24>`.
- **Registro**: um nome de `motion-vox/referencias/registros.md`; nunca igual ao da cena vizinha.
- **Referência**: o frame aberto antes de compor (`REFERENCIAS-VISUAIS.md`: "Porsche bf06", "Bible p.8").
- **O que aparece**: a coisa de verdade, nunca abstrata (E3, E5). Marca = logo oficial (E4). Gente = a pessoa, o corpo ou as mãos (E6). Título sempre com um elemento que faz parte dele (E7).
- **Referente**: `tipo: o quê`, com tipo ∈ `marca`, `pessoa`, `objeto`, `mecanismo`, `numero`, `titulo`.
- **Entra**: `t0 <s> · <corte seco | trajetória> · …`.
- **Se mexe**: os três beats, cada um com frame: `**prova** … f<n> · **detalhe** … f<n> · **conclusão** … f<n>` (E8: nada parado).
- **Fim de cena**: `<flash | push | slide | wipe | volta> · t1 <s>`; t1 dentro de um silêncio do corte.
- **Legenda**: `corre` ou `cala`. **Cobre emenda?**: `sim — <s>` ou `não`.
- **Layout H**: como a cena se arruma no 16:9 (obrigatório quando a saída é `ambas` ou `H`).
- **Motivo**: uma frase; "dá dinâmica" não é motivo.

## C. Ficou de fora, com motivo

| momento / palavra | t | motivo |
| --- | --- | --- |

## D. Emendas cobertas por cutaway

| emenda (s) | cena |
| --- | --- |

## E. Janelas de legenda

(gerado por `janelas_legenda.py` — não escrever à mão)

## F. Provas reais e atribuições

| cena | o quê | origem (URL) | licença | arquivo em 07_assets/raw/ |
| --- | --- | --- | --- | --- |

## G. Lista de geração (= 00_brief/PROMPTS.md)

| asset | cena | host | ferramenta | chamadas | custo |
| --- | --- | --- | --- | --- | --- |
