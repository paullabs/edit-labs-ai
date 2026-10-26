---
name: colagem-camadas
description: >-
  Explicador vertical (9:16) em colagem de papel com CAMADAS REGISTRADAS que se levantam, mostram o que há embaixo e
  voltam ao lugar, no padrão de referência do "manequim de 1890" (boneco anatômico real que se desmonta peça por peça).
  Use quando o pedido for explicar algo POR DENTRO ou EM PARTES: corpo humano e medicina (pele, músculo, órgãos,
  ossos, mão, crânio, junta), objetos e máquinas por dentro, Terra e planetas, construção, usina, refinaria,
  geologia. Dispare também para "camadas", "descascar", "o que tem por dentro", "vista explodida", "3D no estilo
  colagem", "como o manequim", "como a luva de boxe", ou para continuar e melhorar um vídeo desses. Cobre o projeto
  inteiro: perguntas, roteiro, material (objeto real fotografado em camadas, modelo 3D próprio ou os dois), quadro-chave,
  peças registradas, conferência da figura, cena, vídeo, som e créditos. Não use para talking head com legenda
  (motion-vox), cortes de podcast (corte-viral), curiosidade histórica em colagem (colagem-historia) nem explicador Vox
  com voz sobre fotos soltas (explicador-vox).
---

# Colagem em camadas

Um objeto só fica na tela o vídeo inteiro e muda **por dentro**: a pele levanta e o músculo está lá; a luva sai e a
mão está lá; a tampa do crânio voa e o cérebro boia no líquor. Cada camada é registrada pixel a pixel com a de baixo,
então o que aparece é exatamente o que existia. No fim, tudo volta ao lugar em ordem inversa.

A referência do estilo é o **manequim de 1890** (`exemplos/cena_manequim.py`; anatomia dele em
`referencias/referencia-manequim.md`). Repita esse nível e suba.

**Antes de tudo, leia `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`** (perguntas, ordem da produção, texto na tela, margem do
Reels, material, movimento, som, crédito e "pode"). Aqui está só o que é específico deste estilo.

## Onde está cada coisa

| o quê | onde |
| --- | --- |
| motor (câmera, camadas, mecânicas, peças de papel, som) | `${CLAUDE_PLUGIN_ROOT}/motor/colagem/` (`LEIA.md`, `GUIA_OLHO.md`) |
| exemplos completos (manequim, luva, crânio, estalar, corpo humano, Terra, teste rápido) | `${CLAUDE_SKILL_DIR}/exemplos/` |
| preparo 3D dos exemplos (monta o .blend e renderiza as camadas) | `${CLAUDE_SKILL_DIR}/exemplos/preparar.py` + `exemplos/cfg/` |
| objetos 3D próprios (bloco do pré-sal, refinaria, moeda, maço, petroleiro em corte) | `${CLAUDE_SKILL_DIR}/modelos/` |
| técnica, quebras e como não repetir | `referencias/TECNICA.md` |
| portão de qualidade (responder antes de entregar) | `referencias/portao-de-qualidade.md` |
| receitas por assunto | `referencias/receitas-por-assunto.md` |
| fontes de modelos 3D e de pranchas | `referencias/FONTES_3D.md`, `referencias/FONTES_PRANCHAS.md` |
| créditos e licenças; o que baixar da release | `assets/CREDITOS.md`, `assets/RELEASE.md` |
| banco de referências de estilo (fichas, paletas) | `${CLAUDE_PLUGIN_ROOT}/referencias/` |

Ambiente: o Python do ambiente da colagem (`editlabs-setup --colagem`, ou `pip install -r
${CLAUDE_SKILL_DIR}/requirements.txt`), `ffmpeg` e, para os passos 3D, o Blender 4.x/5.x (`BLENDER=<executável>`).
Todo exemplo importa o motor assim:

```python
RAIZ = Path(__file__).resolve().parents[3]                        # a raiz do plugin
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
```

O trabalho do projeto vai para `./colagem-trabalho/` na pasta do usuário (ou `COLAGEM_TRABALHO`); os assets grandes,
para `~/.local/share/edit-labs-ai/colagem/` (`EDITLABS_DATA`). Teste a instalação com
`python3 ${CLAUDE_SKILL_DIR}/exemplos/teste_rapido.py` (não precisa de nenhum asset).

## 1. Perguntas (no máximo 4, múltipla escolha, recomendada em primeiro)

Pule o que o pedido já respondeu. Depois disso, nada técnico: fps, nível de som, margem e codec são decisão sua.

1. **O que vamos abrir por dentro?** — uma parte do corpo (mão, crânio, peito, junta) · o corpo inteiro · um objeto
   ou máquina · um lugar (Terra, usina, prédio) · outro (diga qual).
2. **De que é feito o objeto?** — os dois: 3D próprio para o volume + foto real presa na cena (recomendado) · foto real
   de um objeto em camadas (pranchas antigas, como o manequim) · só 3D próprio, renderizado em papel.
3. **Duração?** — 20–35 s (recomendado) · 35–60 s · até 20 s.
4. **Com voz?** — sim, voz grave gerada (eu mostro 3 amostras; gasta crédito, só com "pode") · sem voz, só imagem e
   trilha · já tenho a narração.

## 2. Fluxo (cada portão mostra uma coisa e faz uma pergunta)

1. **Pergunta e objeto único.** Uma frase de promessa e o objeto que a responde. Liste as camadas na ordem em que
   saem e na ordem inversa em que voltam (`referencias/receitas-por-assunto.md`).
2. **Roteiro** com fonte para cada número (nada inventado). Com voz: frases curtas, falado.
3. **Material.** Escolha o caminho (tabela abaixo) e anote no `CREDITOS.md` do projeto: fonte, licença, tamanho.
   Download só com "pode" (mostre nome, tamanho e licença). Pacotes da release: `assets/RELEASE.md`.
4. **Estilo aprovado com 1 quadro-chave antes de montar.** Renderize UM quadro no estilo final (a figura central, o
   papel, a luz, a borda) e pergunte: aprovar, ajustar ou trocar. Só depois monte o resto.
5. **Peças registradas.** 3D: `.blend` com prefixo por camada + `blender_giro.py` (mesma câmera, `px_por_m`) +
   `papelizar(registrado=True)`. Foto: peça = diferença entre fotos (`manequim_pecas.py`) ou `registrar()` (ECC).
6. **Conferir a figura** antes de qualquer vídeo: `python3 -I ${CLAUDE_PLUGIN_ROOT}/motor/colagem/conferir_figura.py
   lascas|buracos|cortados|composto ...`. Zero problemas, ou cada achado explicado.
7. **Cena.** Uma figura central; camadas na ordem de empilhar; mecânicas por palavra (com voz: `q(t) = 10 + 24·t`);
   câmera por planos lentos com `C.quadro(caixa, regiao=M.REGIAO_REELS)`; um mecanismo por vez.
8. **Quadros de conferência** (`M.render(..., quadros=[...])` + `folha_quadros.py`), `M.checar_margens` e
   `M.ajustar_texto`. Responda `referencias/portao-de-qualidade.md` como espectador.
9. **Vídeo** (`M.render`), e o `qa.py` no vídeo pronto (borrão fora das transições).
10. **Som.** `som_auto.mixar_auto(camadas, cam, trans, trilha, fim, pasta)`: um efeito por ação, sintetizado e medido
    contra a música; sem trilha do usuário, entra uma cama gerada em código. Com voz, a voz entra por cima
    (`cena_estalar.py --som` mostra o mix com sidechain). Declare a escuta humana como pendente.
11. **Rótulos, legenda (se houver) e créditos por último.** Neste estilo não há legenda de fala; no máximo 1 rótulo
    curto preso ao objeto e 1 número em carimbo. Créditos de 2,3 s no fim, com cada licença.

### Escolher o material

| caminho | quando | como | exemplo |
| --- | --- | --- | --- |
| **A. Objeto real em camadas** | existe um objeto/ilustração em camadas fotografado (boneco anatômico, prancha com abas, corte técnico) | baixar (com "pode"), registrar, extrair cada peça por diferença entre fotos | manequim de 1890, Witkowski, Albinus |
| **B. 3D próprio em camadas** | o objeto não existe em camadas, ou o volume importa | Blender ortográfico, mesma câmera e mesmos px/m em todas as camadas; `papelizar(luz=...)` vira gravura de papel | crânio, mão, Terra, bloco geológico, refinaria |
| **C. Híbrido (o melhor, quase sempre)** | volume e mecânica em 3D, com uma foto real dentro da cena | 3D para o corpo; foto real recortada como peça (presa com fita, recorte que viaja) | o homem de terno de foto com a anatomia encaixada |

Pessoa real: só foto real licenciada; o rosto nunca é gerado (`REGRAS.md`). Imagem que falta: gere no Higgsfield com
fundo transparente.

## 3. Mecânicas do motor (`camadas.py`, importado como `K`)

Todas andam em degraus de 7 qps (stop-motion); a câmera anda a 14. Cada uma já marca o som dela (`L.som`).

| mecânica | o que faz | exemplo |
| --- | --- | --- |
| `K.levanta(camada, q0, q1, para=(dx, dy), giro=12)` | a peça descola (cresce, a sombra se afasta), sobe e sai girando; a camada de baixo aparece no lugar | a luva sai da mão (`cena_luva.py`); as peças grandes do manequim saem da tela |
| `K.janela(img, centro, q0, q1, raio, fecha=(q2, q3))` / `K.janela_forma(img, mascara, ...)` | buraco de papel rasgado que cresce de um ponto (ou com a forma do tronco), com borda branca e sombra; pode fechar | a pele da mão abre sobre os ossos; o peito abre na forma do tronco (`cena_homem3.py`) |
| `K.descasca(img, q0, q1, direcao, volta=(q2, q3))` | uma borda rasgada atravessa a camada e leva o papel; pode voltar | o músculo some e mostra as costelas |
| `K.aba(nome, frente, x, y, q0, q1, dobradica="esquerda", fecha=...)` | a camada abre como aba de livro de anatomia (perspectiva, verso de papel, escurece de lado) | a capa, a tampa, a pele que abre como porta |
| `K.metades(img)` + 2× `K.aba` | corta a camada ao meio e abre como duas portas | o peito que abre ao meio |
| `K.destaca(camada, q0, q1, para, esc)` / `K.pousa(camada, q0, q1, para, esc)` | a peça descola e viaja crescendo até o meio; depois volta e assenta com o pouso | o coração sai do peito, gira e volta; as peças pequenas do manequim ficam paradas no ar |
| `K.explode(camadas, q0, q1, passo=(0, 260), volta=q2, desloc=[...])` | vista explodida (ou grade) e volta | as cascas da Terra se separam (`cena_terra.py`) |
| `K.pulsa(camada, q0, q1, padrao, periodo)` | vida: a escala pulsa sem mexer nas chaves de movimento | coração a 70 bpm `[1.07, 1.03, 1, 1, 1, 1]`; pulmão em senoide lenta |
| `K.giro(nome, vistas, x, y, chaves_ang)` (vistas do `blender_giro.py`) | objeto 3D girando a **7 qps**, como recorte girado à mão; a vista 0 é igual à peça parada | o crânio e o cérebro girando (`cena_cranio.py`) |
| `K.pilha`, `K.cortar_alfa`, `K.registrar`, `K.papelizar`, `K.apara_lascas`, `K.fecha_vazados` | encaixe, recorte sem perder o lugar, alinhamento ECC, render 3D → gravura, limpeza do alfa | todos os exemplos |

Peças e cena: `PC.recorte` (borda de tesoura), `PC.cartao` (foto com fita), `PC.etiqueta`, `PC.carimbo`,
`C.cai`, `C.Traco` (caneta que se desenha), `C.circulo`, `C.rajada`, `C.Camera().plano(...)`, transições
`M.Transicao` (`mergulho`, `recua`, `iris`, `rasgo`, `empurra`, `flash`). Detalhes em `motor/colagem/LEIA.md`.

## 4. Os exemplos

| exemplo | material | antes de rodar | cena |
| --- | --- | --- | --- |
| manequim de 1890 (a referência) | fotos reais em camadas | pacote de pranchas; `preparar.py manequim` | `cena_manequim.py` |
| luva de boxe | Z-Anatomy + luva CC BY 3.0 | pacote Z-Anatomy; `preparar.py luva` | `cena_luva.py` |
| crânio e cérebro boiando | Z-Anatomy + BodyParts3D | Z-Anatomy + BodyParts3D; `preparar.py cranio` | `cena_cranio.py` |
| estalar os dedos (com voz) | Z-Anatomy + junta própria | `preparar.py luva` e `preparar.py estalar`; sua narração em `estalar/voz.mp3` | `cena_estalar.py` |
| corpo humano (homem de terno) | foto CC0 + Z-Anatomy + BodyParts3D | `preparar.py homem`, a foto recortada, `homem3_pecas.py`, `homem3_poses_ia.py` | `cena_homem3.py` |
| Terra | 3D próprio | `preparar.py terra` | `cena_terra.py` |
| teste rápido | nada | — | `teste_rapido.py` |

Cada cena roda assim: sem argumento = quadros de conferência em `colagem-trabalho/previa/<nome>/`; `--video` = vídeo
sem som; `--som` = mix e vídeo final. A legenda de fala vem desligada (`COLAGEM_LEGENDAS=1` liga, só para estudo);
a trilha é sua (`COLAGEM_TRILHA=<arquivo>`, `COLAGEM_TRILHA_LICENCA="..."`) ou a cama gerada pelo motor.

## 5. Lições do que não funcionou (regras)

- **Colagem que mistura fontes visuais sem objeto real em camadas fica amadora.** Silhueta + fotos geradas + desenhos
  soltos + ícones = sem identidade. Escolha UM objeto central em camadas e faça o resto morar nele.
- **Imagens avulsas em sequência são slide.** Cartão atrás de cartão, raio X, pictograma: reprovado. O que tem volume
  vira 3D em camadas registradas.
- **Vídeo parado demais cansa.** Plano sem ação por mais de ~2 s, só o osso mexendo dentro de uma mão parada, uma
  revelação por vídeo: tudo isso fica simples demais. Dê vida (pulso, respiração, dedos que dobram, câmera que deriva)
  e 2 a 4 eventos por frase.
- **Validar 1 quadro no estilo final antes de montar o vídeo todo.** Corrigir no quadro-chave custa um quadro; no fim,
  custa o vídeo.
- **Clip-art vetorial desenhado em código fica amador.** Objetos são foto real recortada ou 3D renderizado e
  papelizado.
- **Legenda de fala embaixo atrapalha.** Rótulo curto preso ao objeto, e só quando precisa.
- **Coisa pequena e coisa demais.** Herói ≥ 600 px; uma coisa grande por vez; dentro de x 80–960, y 260–1420.
- **Movimento agressivo.** Zoom de 0,3 s, câmera que vai e volta, mergulho que não termina: troque por aproximação
  contínua e lenta e transição de zoom entre lugares.
- **Figura "limpa" ainda pode estar estranha** (olho esbugalhado, tronco sem cabeça, líquido em pé): a revisão de
  espectador é obrigatória (`referencias/TECNICA.md`, "Como não repetir as quebras").

## 6. Antes de dizer "pronto"

Mesmo objeto o vídeo todo · camadas registradas · volume em 3D · uma coisa grande por vez · no máximo 1 rótulo + 1
número · sem legenda de fala · nada fora da margem · câmera lenta e sem borrão · volta em ordem inversa · um efeito
por ação · voz grave (se houver) · `CREDITOS.md` e créditos na tela · escuta humana declarada como pendente.
