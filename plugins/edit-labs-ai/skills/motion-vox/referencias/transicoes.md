# Saída dos cutaways

Corte seco de uma composição cheia direto para o rosto lê como tranco. E **repetir a
mesma saída** em todas as cenas vira tique. Quatro tipos:

| Tipo | O que acontece | Quando |
| --- | --- | --- |
| `flash` | desfoca + estoura em branco; o corte cai escondido no pico | **padrão atual** — troca de insert, nome citado, qualquer corte "rápido" |
| `push` | a câmera acelera para dentro e o corte cai na velocidade | fecho de ideia, última cena do clipe |
| `slide` | a mesa é puxada para fora do quadro e o vídeo aparece atrás | legado — evite; lê como "arrastar pro lado" |
| `wipe` | uma folha atravessa a lente; atrás dela o vídeo já está lá | legado — `flash` cobre o mesmo papel de "clarão" sem o gesto lateral |

13 frames a 29,97fps (~0,43s), com aceleração (`ease_in`, t^2.4) — em fonte de fps
diferente, escale por TEMPO, não por contagem de frames (ex.: 26 frames a 59,94fps).

## `flash` — o padrão atual

Nada de arrastar pro lado entre inserts: desfoca, estoura em branco, desfoca de novo e
já está na próxima cena. Implementação em duas metades simétricas:

```python
def exit_frame(img, kind, sl):        # sl: 0 (nitido) -> 1 (flash total)
    if kind == "flash":
        r = FLASH_BLUR * sl
        im = img.filter(ImageFilter.GaussianBlur(r)) if r > 0.4 else img
        return Image.blend(im.convert("RGBA"), WHITE, min(0.97, sl))
```

A entrada é o espelho (`sl` de 1 a 0) — só funciona **entre duas cutaways controladas
por PIL**. Saindo para o vídeo cru (talking head), só a saída desfoca: o plate nunca é
reprocessado, então a entrada da fala real é corte seco.

**Insert-burst (trocar de prova dentro da MESMA cena).** Quando uma janela cita várias
coisas em sequência — pessoa, depois objeto, depois lugar — não abra uma cutaway nova
pra cada uma: renderize cada insert como um desenho completo e troque entre eles com o
mesmo efeito, agora comparando DUAS imagens já prontas em vez de uma imagem e o branco:

```python
def _swap_flash(im_a, im_b, k, blur_max=22):
    if k <= 0: return im_a
    if k >= 1: return im_b
    base, t = (im_a, k/0.5) if k < 0.5 else (im_b, 1.0-(k-0.5)/0.5)
    im = base.filter(ImageFilter.GaussianBlur(blur_max*t)) if t > 0.02 else base
    return Image.blend(im.convert("RGBA"), WHITE, min(0.92, t))
```

`k` de 0 a 0,5 desfoca/estoura a imagem A; de 0,5 a 1 resolve pra imagem B. A cena
inteira (a `build_M#`) continua entrando e saindo uma vez só — o flash interno é ritmo
dentro dela, não uma transição de container. Exemplo: pessoa → documento → bandeira
(três provas, dois flashes internos, uma cutaway só).

## Por que o `flash` daqui não é o "flash branco" proibido

A identidade proíbe **flash instantâneo** (strobe de 1-2 frames, sem desfoque) e whip
pan, junto com glitch e "transições de template" — é o corte seco de câmera de rede
social, sem textura. O `flash` deste kit é outra coisa: um desfoque GRADUAL que estoura
em branco e resolve de novo, na mesma curva de aceleração (`ease_in`) que qualquer outra
saída daqui — tem textura de grão e boil como qualquer outro frame, não é um strobe puro.
`wipe` e `slide` leem como "arrastar pro lado", não como o corte rápido que o
insert-burst pede; por isso `flash` é o padrão — `wipe` e `slide` ficam como legado, não
proibidos, só fora do padrão corrente. `push` continua o "zoom na prova" pra fechar ideia.

## Implementação

Os cutaways renderizam em RGB opaco (o alfa que sobra da composição não importa pra
montagem — ver "concatenação" abaixo). Apesar do nome, o `push` também fica opaco a cena
inteira, como todos os cutaways: é a concatenação que esconde o corte, não uma revelação
de vídeo por trás.

A folha do `wipe` usa um papel **diferente** do fundo da mesa (cartão de algodão frio
contra marfim), senão a passagem não lê — vale só se você reativar esse tipo legado.

## Encadeamento por concatenação, não por overlay

Encadear cada cutaway como `overlay=...:enable='between(t,{t0},{t1})'` sobre a fonte,
com `eof_action=pass` revelando o vídeo cru fora da janela, vaza 1 frame de vídeo cru no
corte entre duas cutaways quando há 5+ shots encadeados (comum em insert-burst) — mesmo
com o `t1` frame-exato (`t1x = t0 + round((t1-t0)*FPS)/FPS`) e a janela matematicamente
correta. Com 2 shots isolados o vazamento não aparece, e a causa exata dentro do filtro
`overlay` do ffmpeg não está isolada.

**A solução: concatenação.** Monta a base de vídeo como uma sequência de blocos
discretos — trechos da fonte (`trim`) alternados com as cutaways — e concatena. Sem
overlay, sem `enable`, sem `eof_action`: não existe "o que tem por baixo" pra vazar,
porque não há baixo nenhum, só uma sequência.

```python
segs, prev_end = [], 0.0
for k, (name, _, t0, t1, _, _) in enumerate(SHOTS, start=1):
    n = int(round((t1 - t0) * FPS)); t1x = t0 + n / FPS
    if t0 > prev_end + 1e-6:
        segs.append(("gap", prev_end, t0))       # trecho de fonte antes deste shot
    segs.append(("shot", k))
    prev_end = max(prev_end, t1x)
segs.append(("gap", prev_end, DUR))              # trecho de fonte depois do ultimo shot

# por segmento:
#   gap:  [0:v]trim=start=A:end=B,setpts=PTS-STARTPTS,format=yuv420p[gN]
#   shot: [k:v]setpts=PTS-STARTPTS,format=yuv420p[sN]
# concat=n=len(segs):v=1:a=0[vbase] — a legenda (overlay RGBA, sempre ativa) entra por
# cima do [vbase], essa parte continua igual.
```

Gaps com duração menor que 1 frame (sobreposição residual entre shots encadeados, do
mesmo arredondamento) são pulados — não geram segmento.

**Efeito colateral aceito: ±poucos frames na contagem total**, quando a fonte não é
perfeitamente CFR (a maioria não é — uma fonte pode ter 10 frames a menos do que
duração×fps sugere). Os gaps vêm de `trim` puro na fonte (frames reais, não um
recálculo por FPS nominal), então herdam essa variação; não é o defeito de corte
acima. Duração do container continua batendo exato — é só a contagem interna de
frames que pode variar em 1-2 por corte quando a fonte tem essa característica.

## Som — biblioteca local e corte por evento

Ler [som-local.md](som-local.md) antes de preparar os sons. A biblioteca local fornecida
pelo usuário tem prioridade; cliques suaves de câmera são candidatos iniciais. Sons de
giz só fazem sentido quando a imagem mostra escrita. Não alternar tipos de som apenas
para completar um pool nem colocar som em todo corte.

`SFX_EVENTS` define arquivo, entrada/saída do trecho, transiente-âncora, instante na
timeline, redução de ganho e fades. `lib/sfx.py` monta essa camada sem mudar o ganho da
fala. `SFX_TIMES`/`SFX_OFFSET` continuam disponíveis para projetos legados com arquivos
sintetizados já preparados. Não usar ambos no mesmo projeto.

Flashes e desfoques devem acompanhar a mudança de informação. Quando o usuário pedir
flashes muito rápidos, ajustar a duração ao pedido e testar com voz e movimento, sem
substituí-los por outro efeito sem avisar. O efeito sonoro marca o instante percebido
(captura, encaixe ou revelação); não precisa começar no primeiro frame da transição.

Sem SFX, o template copia o áudio. Com SFX, documentar a mixagem e verificar duração,
sincronia, picos e inteligibilidade; não exigir que o MD5 do áudio mixado seja igual ao
original. A verificação completa está em `som-local.md`.
