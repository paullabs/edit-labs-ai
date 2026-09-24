# Prompts de asset

Um objeto por prompt. Sempre isolado, sempre fotográfico, nunca ilustração genérica.

> Qual objeto gerar, quando reaproveitar e como não repetir: `assets-sob-medida.md` (famílias de prompt na §4,
> faixas medidas do kit na §3, biblioteca na §6). Este arquivo guarda os esqueletos e os casos especiais.

## Esqueleto — objeto isolado

```
Single isolated object centered on a completely flat plain neutral <COR DO FUNDO>
backdrop hex <HEX>. <OBJETO E ESTADO>, photographed straight from directly overhead,
perfect top-down view. <MATERIAL E DESGASTE>. Even soft diffuse light, no cast shadow
on the backdrop, object fully within frame with clear separation from background.
Muted desaturated color, matte finish, no glossy highlights. Documentary object
photograph. No text, no letters, no numbers, no symbols, no brand, no logo anywhere.
No glossy 3D render, no neon, no glow, no gradients, no HDR, no AI-polished look.
```

Fundo: `#8A8A8A` para objeto claro · `#D8D8D8` para objeto escuro.

## Esqueleto — fundo de mesa (1080×1920)

```
Background plate only, nothing on it. Flat straight-down photograph of warm ivory
dotted grid paper filling the entire vertical frame edge to edge. Fine regular light
warm-gray dot grid. Subtle paper fiber texture, matte uncoated surface, very slight
uneven aging. Even soft diffuse light, completely flat lighting. Absolutely empty:
no objects, no props, no writing, no text, no border, no frame, no shadow, no vignette.
Muted desaturated warm neutral palette around hex D9D8D1. Fine film grain.
```

## Esqueleto — fotografia noturna (fonte única de luz)

```
Documentary reportage photograph, dark room at night. <SUJEITO E POSTURA>. <A FONTE>
is the single light source in the entire frame: cool light falls on <O QUE RECEBE LUZ>,
and everything else drops into deep near-black shadow. No lamp, no window, no second
source. Coarse 35mm film grain, very high contrast, crushed matte blacks, heavily
desaturated. Natural photographic light only: no glow effect, no bloom, no halation,
no lens flare, no neon, no rim light, no volumetric light rays, no particles. <A TELA>
shows only an indistinct pale field with no readable interface, no text, no letters,
no numbers, no icons, no logo. Editorial reportage on pushed black and white film.
```

Depois trate com mapa de gradiente (`night_photo.py`) — ver armadilha 18.

## Regras que não podem faltar

| Sempre | Por quê |
| --- | --- |
| `no cast shadow on the backdrop` | sombra é camada |
| `no text, no letters, no numbers, no logo, no brand` | texto de IA é BLOCKER |
| `no glow, no bloom, no neon, no gradients, no HDR` | proibições da identidade |
| `matte finish, no glossy highlights` | material fosco |
| `muted desaturated` | 80% neutros |

## Casos especiais

**Mostrador (relógio, medidor):** peça `plain unmarked dial with only twelve small thin
tick marks, absolutely no numbers, no numerals, no digits`. Redesenhe os ponteiros em
PIL a partir de um total em minutos com fração — a hora vira dado controlado e animável.

**Teclado, teclas, botões:** peça `legends worn away to the point of being illegible
smudges`. Impede letra de IA sem impedir o objeto.

**Papel amassado com rabisco:** peça `a pure abstract tangle of looping lines only:
no letters, no words, no numbers, no diagram, no recognizable shape`.

**Embalagem, caixa:** `completely unbranded and blank: no printing, no label, no tape,
no barcode, no logo, no arrows, no symbols`.

## Variantes

Gere 2–3 variantes de qualquer asset que seja herói de cena. É barato, e a rejeitada
costuma ensinar algo: texto de IA num canto (um ano, um número solto) passa despercebido
quando só existe uma variante, e salta aos olhos na comparação.
