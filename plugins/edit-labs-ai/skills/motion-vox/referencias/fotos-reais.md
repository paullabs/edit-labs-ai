# Fotos e logos reais — pessoa, marca ou lugar citado

> Quando o falante nomeia alguém ou algo verificável, ficar no símbolo genérico não faz
> sentido. Ver `SKILL.md` §2.

## Quando usar

Nome próprio identificável dito no áudio — pessoa, marca, bandeira/país — e a cena
correspondente **não** tem outro motivo pra ficar simbólica (ver exceções abaixo).
"Um carro-brinquedo genérico" ilustra "carro"; não ilustra "Tesla, especificamente".

## Fonte: Wikimedia Commons, nunca gerador de imagem

**Nunca peça pro gerador de IA desenhar uma pessoa real.** A rota é buscar uma
fotografia ou logo **que já existe**, com licença clara:

1. `WebSearch` com `site:commons.wikimedia.org "<nome>"` (foto de pessoa/lugar) ou
   `site:commons.wikimedia.org "<marca> logo" svg` (logo de empresa).
2. Abra o `File:` da Commons e confirme a licença antes de baixar — domínio público,
   CC BY, CC BY-SA. Registre autor e licença em `07_assets/ATRIBUICOES.md` do projeto.
3. Baixe o arquivo real via `Special:FilePath`:
   `https://commons.wikimedia.org/wiki/Special:FilePath/<nome-do-arquivo>`

**Logo/marca: uso identificador é aceito** mesmo sendo marca registrada — é o mesmo
uso que qualquer canal de notícia ou review faz ao mostrar o logo da empresa que está
comentando. Não redesenhe o logo, não o distorça, não o combine com outra marca.

## Exceção: quando NÃO usar o rosto

Só fica simbólico quando:

- **A identidade não está confirmada** — nome ambíguo, sinalizado como possível erro
  de ASR no `06-candidates.json` da fase de corte. Não dá pra ilustrar com segurança
  quem não se sabe ao certo quem é.
- **A pessoa é menor de idade**, ou a situação é sensível o bastante pra que mostrar o
  rosto real seja o problema, não a solução — julgamento editorial, não uma lista
  fechada.

Registre a decisão (usar ou não) no `PLANO_MOTION.md`, com o motivo — igual a
qualquer outra escolha de frase.

## Tratamento — cai no registro "foto em cartão"

Fotos reais entram como **fotografia impressa**, não como cutout flutuante: rosto tem
fundo de estúdio ou de rua, não o cinza neutro que o `cutout.py` espera, e tentar
recortar por flood-fill come cabelo e borda. A prova é a moldura, não o contorno.

```python
def photo_card_asset(src_path, out_path, box=(4,5), sepia=False, focus_y=0.42):
    """Recorta em retrato, aplica margem de impressao (bw=24, bb=66, cor #F1ECE0),
    grada leve (sepia=True pra foto de epoca, senao so dessatura 0.86/contraste 1.03).
    box = proporcao largura:altura do recorte final."""
```

- **Foto de época** (pessoa histórica, decreto, evento datado): `sepia=True` — duotone
  preto-quente/creme, não é enfeite, é o que faz a foto ler como "daquela época" em vez
  de parecer uma reprodução moderna colada sem tratamento.
- **Foto contemporânea** (marca/pessoa atual): dessature levemente (`Color 0.86`), sem
  duotone — ela é real e atual, não precisa fingir ser antiga.
- Depois de gerar o PNG com moldura, ele entra no `07_assets/cutout/` e se comporta como
  qualquer outro asset: `asset("PH_NOME", width, rotation=...)`, com fita ou clipe
  prendendo na mesa, igual a qualquer prop do kit.

**Logo:** SVG da Commons não tem `rsvg-convert`/`cairosvg` garantido na máquina — use
`qlmanage -t -s 800 -o . arquivo.svg` (Quick Look, built-in no macOS) e depois
chroma-key o fundo branco que ele desenha por baixo (a Commons não devolve alfa
verdadeiro no thumbnail):

```python
dist = 255 - rgb.min(axis=2)                      # 0 = branco puro
alpha = np.clip((dist - 2) * 8, 0, 255)            # rampa curta = borda anti-aliased limpa
```

Depois `getbbox()` pra cortar a folga e salvar só o conteúdo. **Cuidado com bandeiras e
qualquer imagem que já seja um retângulo cheio**: o `qlmanage` letterboxa em vez de
esticar, e o `getbbox()` não separa "letterbox branco" de "conteúdo real"se a imagem
inteira já for opaca — meça linhas/colunas quase-brancas nas bordas e corte à mão.

## Transição entre inserts reais

Quando a janela cita mais de uma coisa em sequência, use o `flash` interno
(`_swap_flash`, ver `referencias/transicoes.md`) pra alternar entre as fotos/logos
dentro da mesma cutaway — não abra uma cena nova pra cada nome.
