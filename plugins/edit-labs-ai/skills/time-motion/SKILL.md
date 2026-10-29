---
name: time-motion
description: >-
  Time de Motion: quatro agentes em paralelo (Referências, Diretor de Motion, Caçador de Insets, Som) preparam a
  edição de um vídeo já cortado (talking head, live, anúncio, explicador com rosto); depois o Editor (você) monta
  no invideo e o Analista de Referências revisa uma vez contra a régua. Use quando o usuário mandar um vídeo ou
  projeto para "motion", "edição profissional", "manda o time", "time de motion", "agentes de edição", ou pedir
  insets reais (foto da pessoa citada, logo da marca citada) com motion por cima sem lotar a tela. Exige o conector
  do invideo para a montagem.
---

# Time de Motion

> **Caminhos e comandos (Claude Code e Codex).** CLAUDE_SKILL_DIR é a pasta desta skill (a do `SKILL.md`) e CLAUDE_PLUGIN_ROOT é a pasta do plugin. O Claude Code troca as duas variáveis pelo caminho antes de você ler este texto. Se os caminhos desta skill ainda mostram uma delas escrita com cifrão e chaves, ela não foi preenchida (Codex e outros agentes): a pasta da skill é onde está este `SKILL.md`, e a raiz do plugin é a pasta duas acima dela (a que tem `bin/` e `agents/`). Os comandos `vch`, `cvpy`, `mvpy`, `editlabs-*`, `cv-*` e `mv-*` ficam em `bin/` da raiz do plugin, e o Claude Code os põe no PATH. Se `command -v vch` não achar nada, chame cada um pelo caminho completo (`<raiz do plugin>/bin/vch`).

Quatro agentes trabalham ao mesmo tempo, cada um com uma tarefa definida, para uma edição mais profissional:
referências medidas, poucas batidas bem ilustradas, **nunca lotar a tela**, insets reais (a foto real da pessoa
citada, o logo da marca citada) e geração só do que não existe.

As regras comuns de produção (perguntas fáceis, ordem, margem, material real, som, "pode" antes de gastar crédito,
**legenda por último**) estão em `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`. Leia antes. Aqui fica o que é deste fluxo.

Você é o **Editor**: coordena, junta, monta e entrega. Nunca aprova o próprio trabalho. Os agentes não baixam nem
gastam crédito; quem pede o "pode" ao usuário é você, uma vez por vídeo.

| agente (chame assim) | entrega em `<projeto>/time/` |
| --- | --- |
| `edit-labs-ai:tm-referencias` | `REGUA_REFERENCIA.md` (passada 1) e `REVISAO_REFERENCIA.md` (passada 2) |
| `edit-labs-ai:tm-diretor-motion` | `PLANO_MOTION.md` (1ª e 2ª passada) + `ancoras.json` |
| `edit-labs-ai:tm-cacador-insets` | `INSETS.md` + `insets.json` |
| `edit-labs-ai:tm-som` | `MAPA_SOM.md` + `som.json` (+ banco de efeitos) |

Ferramentas da skill (rode com o Python do plugin): `${CLAUDE_SKILL_DIR}/ferramentas/` — `transcrever.py`,
`ilhas_fala.py`, `tempos.py`, `medir_niveis.py`, `montar.py`.

## 0. Preparação (você, antes do time)

Perguntas do começo (múltipla escolha, só o que faltar):

1. **Formato:** a) 9:16 Reels/TikTok/Shorts (recomendado) · b) 16:9 YouTube · c) os dois.
2. **Referências de edição:** a) as do plugin (`${CLAUDE_PLUGIN_ROOT}/referencias/`) · b) vídeos que eu mando ·
   c) as duas.
3. **Logo de marca na tela:** a) pode, quando a marca é citada (recomendado) · b) proibido neste projeto.
4. **Geração de imagem:** a) pode, com a lista e o custo antes (recomendado) · b) só material real.

Depois:

- Pasta `<projeto>/time/` e `00_brief.md`: o que o vídeo é, formato, quem fala, onde vai ser postado, as
  referências, a proibição de logo (se houver).
- **Se o vídeo é bruto, o corte vem antes:** skill `decupagem-inteligente`, entrega 1.
- Transcrição palavra a palavra, com a correção das palavras depois de pausa (ilhas de fala):

```bash
python3 ${CLAUDE_SKILL_DIR}/ferramentas/transcrever.py <corte.mp4> <projeto>/time/01_transcricao/palavras_whisper.json pt
python3 ${CLAUDE_SKILL_DIR}/ferramentas/ilhas_fala.py <corte.mp4> <projeto>/time/01_transcricao/palavras_whisper.json \
        <projeto>/time/01_transcricao/palavras.json
```

  Nome próprio ou número em dúvida volta para o usuário, com as hipóteses. Nunca corrija por conta própria.

## 1. Onda 1: os quatro em paralelo (uma mensagem, quatro chamadas Agent)

O pedido de cada um leva: o caminho do projeto, o caminho do corte, o `palavras.json` e as referências (do brief).
Ao Som, diga também onde está a pasta de sons do usuário (`EDITLABS_SONS`), se houver.

## 2. Onda 2: o plano final

`edit-labs-ai:tm-diretor-motion` de novo, com os quatro arquivos. Ele ajusta à régua, troca desenho por inset
real, corta o que ficou sem objeto bom e escreve o `ancoras.json` (evento → palavra). Então:

```bash
python3 ${CLAUDE_SKILL_DIR}/ferramentas/tempos.py <projeto>/time/01_transcricao/palavras.json \
        <projeto>/time/ancoras.json <projeto>/trabalho/tempos.json --fps 24
```

## 3. Portão do usuário (uma vez)

Mostre, nesta ordem, e faça **uma** pergunta ("pode?"):

1. o plano (a ideia em uma frase e as batidas);
2. a lista de download dos insets (arquivo, origem, licença, tamanho);
3. as gerações, com o custo total em créditos (o valor que a ferramenta informa);
4. as 2 trilhas a ouvir.

Nada é baixado ou gerado antes do "pode".

## 4. Montagem (você)

Ordem fixa: **insets e peças → motion → som → legenda por último → export.**

- **Downloads:** cada arquivo numa pasta nova; Python com `-I` ao ler; crédito e licença em `FONTES.md` (ou
  `CREDITOS.md` do projeto).
- **Montagem nativa no invideo** (conector do invideo ligado; sem ele, pare aqui e entregue plano, insets e mapa
  de som). Leia antes as regras medidas do invideo em
  `${CLAUDE_PLUGIN_ROOT}/skills/explicador-vox/referencias/invideo.md` (zoom relativo ao encaixe, luz linear,
  clipe curto, ids criados, faixas).
  - Escreva o `elementos.py` do projeto (modelo na ajuda de `montar.py`) e rode por etapas:
    ```bash
    python3 ${CLAUDE_SKILL_DIR}/ferramentas/montar.py <projeto>/trabalho/elementos.py lotes <tl> A
    python3 ${CLAUDE_SKILL_DIR}/ferramentas/montar.py <projeto>/trabalho/elementos.py ops <tl> A 0   # -> edit_timeline
    python3 ${CLAUDE_SKILL_DIR}/ferramentas/montar.py <projeto>/trabalho/elementos.py reg <tl> A 0 '<created>'
    ```
    Etapa A cria os clipes, B ajusta estáticos e cria as faixas, C põe as chaves. Registre os ids depois de cada lote.
  - Composições aninhadas (uma por "mundo" do motion); degraus de 2 quadros por pares de chaves; o rosto fica liso
    (câmera lisa no clipe de quem fala, degrau só nos gráficos).
- **Som:** os níveis do `MAPA_SOM.md` (já medidos com `medir_niveis.py`), master a −14 LUFS e ≤ −1 dBTP.
- **Legenda por último:** só depois de motion e som fechados, a partir das janelas de `tempos.json`; qualquer
  mudança anterior obriga a recalcular as janelas.

## 5. Revisão (uma passada, sem cascata)

- `edit-labs-ai:tm-referencias`, passada 2, recebe: capturas início/meio/fim de cada batida; as medidas do export
  (`media_probe`: duração, LUFS, pico); a sincronia da voz.
- Você corrige os achados BLOCKER e HIGH e exporta.
- Entrega ao usuário: o link do export, os trípticos, o laudo curto e "escuta pendente" no som.

## Regras do time (valem para os quatro)

- **Régua permanente:** `${CLAUDE_PLUGIN_ROOT}/skills/decupagem-inteligente/memoria/regua.yaml` (regras E1–E9). Se o
  usuário tiver uma régua própria no projeto, ela vale por cima.
- **Nunca lotar a tela:** ≤ 2 elementos gráficos + legenda por quadro; respiro de rosto ou filmagem limpa a cada
  ~6 s; só as batidas que carregam a mensagem ganham elemento.
- **Sem piada visual que precise de explicação.** Exemplo de reprovação: um ícone de pausa desenhado sobre a luz do
  estúdio, sem relação com a fala.
- **Real primeiro:** pessoa citada = foto real licenciada, com crédito; marca citada = logo oficial (salvo
  proibição do brief); fato = vídeo ou print da fonte. Gerar só o que não existe, nunca rosto de pessoa real, sem
  texto na imagem (gerador do plugin: Higgsfield; se o projeto já vive no invideo, a IA dele serve).
- **Som:** efeitos 15–19 dB abaixo da voz (LUFS medido), poucos, só onde a imagem mostra a ação. Master a −14 LUFS
  e ≤ −1 dBTP.
- **Rapidez:** os quatro em paralelo; **uma** revisão só. Rodadas de revisão em cascata atrasam a entrega e não
  melhoram o resultado.
