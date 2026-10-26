---
name: colagem-historia
description: Reel curto de curiosidade histórica em colagem de papel antigo (9:16, 20–32 s, sem voz por padrão). Usa fotos reais de época recortadas, um mundo de papel em escala real e um traço de caneta vermelha que mede, contorna ou traça a rota, com a câmera seguindo a ponta. Tem cartões que viram, objetos que se multiplicam, transições variadas e pouquíssimo texto. Use para "reel de história", "curiosidade histórica", "mito × fato", "fulano não era…", "a viagem que…", "a altura de Napoleão", "Cleópatra e a Lua", "linha do tempo em escala", "régua do tempo", "colagem de papel antigo", "estilo Vox sem voz", e para continuar ou ajustar um desses reels. Não use para explicar algo por dentro em camadas (colagem-camadas), explicador narrado longo (explicador-vox), documentário de arquivo narrado (motion-arquivo) nem corte de podcast (corte-viral).
---

# Colagem de história: um fato, uma caneta, fotos de verdade

Um reel conta **uma pequena história com começo, virada e fim**, e não só um fato solto. O olho segue uma caneta
vermelha num mundo de papel antigo, onde cada coisa é uma foto real recortada ou impressa num cartão com fita.

As regras comuns valem sempre: `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`. Aqui está só o que é deste estilo. As lições
detalhadas ficam em `${CLAUDE_SKILL_DIR}/referencias/`:

| arquivo | quando ler |
| --- | --- |
| `referencias/estilo.md` | antes de montar a cena: as regras do estilo e o porquê de cada uma |
| `referencias/guia-do-olho.md` | ao planejar a câmera e o texto |
| `referencias/som-sem-voz.md` | na fase de som |
| `referencias/pesquisa-e-licencas.md` | na pesquisa e na busca de fotos |
| `referencias/exemplos.md` | para escolher a mecânica (exemplos: assunto → mecânica → cuidado de fato) |
| `modelos/LEIA.md` | ao copiar e adaptar um modelo |

## Antes de começar

- O motor de colagem é do plugin: `${CLAUDE_PLUGIN_ROOT}/motor/colagem/`. Rode tudo com `clpy` (nunca `python3`);
  se ele disser que falta, rode `editlabs-setup --colagem`.
- **Fotos de exemplo** (opcional, para ver o estilo antes de pesquisar): `editlabs-assets colagem-historia-fotos`
  (~31 MB, domínio público, CC0, CC BY e CC BY-SA; mostre nome, tamanho e licença e espere o "pode"). Com elas, os
  moldes `reel_napoleao.py` e `reel_regua_tempo.py` rodam num projeto sem `pecas/`. Créditos no `LEIA.md` do pacote.
- Projeto numa pasta do usuário (onde ele abriu o Claude Code):

```text
PROJETO/
├── roteiro.md          fatos com 2 fontes, gancho, batidas e legendas
├── CREDITOS.md         cada imagem: arquivo, o que é, página de origem, autor, licença, crédito
├── baixados/<id>/      originais (cada download numa pasta nova e vazia)
├── pecas/              o que o reel lê: recortes PNG, fotos JPG e a trilha
├── ferramentas/reel.py cópia do modelo, adaptada
└── previa/  som/  entrega/
```

## Perguntas (no máximo 4, todas de múltipla escolha)

1. **Assunto:** (a) eu sugiro 3 personagens ou fatos com boa virada *(recomendado se não houver um)*;
   (b) um que você já tem em mente; (c) outro.
2. **A curiosidade em uma frase:** (a) eu proponho 3 ganchos de até 10 palavras e você escolhe *(recomendado)*;
   (b) você escreve a sua.
3. **Voz:** (a) sem voz, com legenda curta *(recomendado: é o estilo)*; (b) com voz narrada (gasta crédito, só com
   "pode"; as regras de voz e som com voz estão no REGRAS.md).
4. **Duração:** (a) 30 s *(recomendado)*; (b) 20 s, com uma mecânica só (ex.: a régua do tempo); (c) 45 s.

A mecânica (medir, traçar rota, contornar, estender um fio, linha do tempo) é decisão sua: proponha no roteiro.

## Fluxo

Cada fase termina num resultado conferível. As fases com 👤 param e esperam o usuário (uma pergunta só).

1. **Pesquisa com fontes** → `roteiro.md`. Cada afirmação tem 2 fontes confiáveis. O que for disputado ou mito ganha
   uma frase que continua verdadeira (veja os "cuidados de fato" em `referencias/exemplos.md`). O gancho tem até
   10 palavras; são 6 a 9 batidas, cada uma com o que aparece, a ação da caneta e uma legenda de no máximo
   8 palavras (ou nenhuma). São **≈ 40 palavras no vídeo todo**; marque o fecho. 👤 aprovar o roteiro.
2. **Brief de objetos e fotos** → lista de 6 a 10 imagens (pessoas, documentos, mapas antigos, lugares) e de 4 a
   7 **objetos reais** (o chapéu, a régua, o navio, o baú). Cada item leva origem, autor, licença, crédito e
   tamanho. Licença e onde buscar: `referencias/pesquisa-e-licencas.md`. 👤 "pode" para baixar. Depois, baixe, faça
   o recorte local, confira cada recorte sobre fundo azul e preencha o `CREDITOS.md`.
3. **Mundo de papel em escala real.** Copie o modelo que mais se parece (`modelos/LEIA.md`) para
   `ferramentas/reel.py` e troque só o bloco "1. O QUE TROCAR". Medida = régua de verdade (ex.: 10 px = 1 cm, com a
   sola no chão); rota = mapa antigo. As áreas do mundo ficam separadas na horizontal. 👤 1 quadro-chave no estilo
   final (`clpy ferramentas/reel.py --quadros N`).
4. **Cena.**
   - **A caneta vermelha** (o único acento de cor) mede, contorna ou traça a rota. Na rota, a câmera segue a ponta
     (`Camera.seguir`) e o veículo viaja nela (`C.segue`).
   - **Peças que mudam:** cartão que vira (`C.vira`), objetos que se multiplicam (`C.multiplica`), estilhaço
     (`C.estilhaca`), entrada deslizando (`C.desliza`).
   - **Transições:** cada passagem tem uma diferente (íris, mergulho, rasgo, empurra, flash) e sai do ponto onde o
     olho está.
   - **Papel carvão** (`C.papel_area`) só nos momentos dramáticos, preso à área dele.
   - **Carimbo cai na batida da trilha (reel sem voz):** meça a batida com `--batidas` (no `reel_regua_tempo.py`) e
     puxe os carimbos e os pousos principais para ela (`na_batida`).
   - Monte com `--sem-texto`: o texto entra no fim.
5. **Quadros de conferência.** Rode `--margens` e depois `--quadros` a cada 1,5 s (de 36 em 36 quadros) e
   `clpy "${CLAUDE_PLUGIN_ROOT}/motor/colagem/folha_quadros.py" previa/quadros previa/folha_quadros.jpg 6`.
   Responda as perguntas do REGRAS.md §10. 👤 aprovar a folha.
6. **Vídeo:** `--video --sem-texto`.
7. **Som:** trilha calma escolhida por medida (veja `referencias/som-sem-voz.md`), efeitos lidos da própria cena e
   `--som`. A escuta humana fica pendente: diga isso.
8. **Legenda e carimbos por último:** feche as frases (≤ 8 palavras, `*palavra*` em vermelho), os carimbos e a
   resposta que se monta. Rode `--video` e `--som` de novo (os efeitos dos carimbos nascem da cena e não custam
   nada) e depois `clpy "${CLAUDE_PLUGIN_ROOT}/motor/colagem/conferir.py" . previa/sem_som.mp4`, que aponta desenho
   borrado fora das transições e texto pequeno. 👤 assistir e aprovar.
9. **Entrega:** `entrega/<nome>.mp4` + `CREDITOS.md` com a linha pronta para a descrição do post (CC BY e CC BY-SA
   exigem crédito).

## Regras deste estilo

- **Pouco texto.** Nomes e datas viram etiqueta de papel presa ao objeto ou carimbo vermelho. A legenda fica sempre
  numa tira de papel em y 1320, com corpo 64 px. A resposta final pode se montar letra a letra no alto.
- **Carimbo** só na batida, com uma explosão de traços curta. Etiquetas e carimbos ficam com ≥ 50–58 px na tela
  (`M.ajustar_texto` corrige sozinho e lista o que mudou).
- **Fotos reais.** Pessoa real é foto real de época, nunca gerada. Um objeto histórico específico (o chapéu dele, a
  régua do rei) também é foto real. Só um objeto genérico sem foto livre pode ser gerado no Higgsfield com fundo
  transparente, com "pode", e marcado como gerado no `CREDITOS.md`.
- **Mundo em escala real:** o tamanho na tela conta a história (a régua, a sola no chão, o mapa de verdade).
- **Câmera:** um foco por batida. A câmera chega antes da legenda, com deriva lenta (×1,02–1,04 por plano). Borrão só
  nos chicotes rápidos, e nunca no 1º desenho depois de um corte.
- **Ritmo de desenho:** 14 desenhos/s (saída 28 qps). O boil tem ~1 px na tela e troca 3,5 vezes por segundo. O filme
  Fuji é leve. Tudo isso já é o padrão do motor: não aumente.
- **Margens:** a região segura do REGRAS.md (x 80–960, y 260–1420). O assunto fica entre y 260 e 1190, acima da
  legenda.
- **Som sem voz:** master ≈ −20 LUFS. O motivo: −14 LUFS é o volume de um vídeo com voz. Sem voz, a música é só um
  leito e, nesse volume, ela e os efeitos soam altos e cansam. Regra: **sem voz, mais baixo**. Os detalhes estão em
  `referencias/som-sem-voz.md`.

## Erros que já aconteceram (e a regra que ficou)

| sintoma | causa | regra |
| --- | --- | --- |
| "parece slide" | todas as batidas iguais: a câmera ia até um cartão parado | cada passagem com uma transição diferente; as peças viram, multiplicam, deslizam |
| personagem esticado e borrado | o rastro de câmera atravessava o corte | o 1º desenho depois de um corte é sempre nítido |
| tremor nervoso | o boil aplicado antes do zoom e trocando a cada desenho | o boil é medido na tela (~1 px) e troca 3,5 vezes/s |
| texto ilegível no celular | etiqueta de ~20 px na tela | `ajustar_texto` + conferir.py antes de entregar |
| efeitos repetidos e fora do quadro | lista de sons escrita à mão, as mesmas amostras | os efeitos nascem da cena e cada um soa diferente |
| música alta | mix a −14 LUFS sem voz | master −20 LUFS, trilha calma medida |
| a área escura vazava na vizinha | o papel carvão era fundo global | `papel_area` por área, com distância das vizinhas |
