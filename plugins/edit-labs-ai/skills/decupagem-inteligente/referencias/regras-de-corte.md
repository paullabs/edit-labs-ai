# Regras de corte — os números e de onde vêm

A régua do projeto mora em `<projeto>/config.yaml` (copiada de `memoria/templates/config.yaml`). Este arquivo explica cada número. Mudança de régua é na global, com entrada em `armadilhas.md`.

## Onde o corte pode cair

Um ponto de corte vale quando as quatro coisas são verdade:

1. **Fora da voz medida.** A borda da palavra vem do envelope de energia do wav, não do Whisper. O limiar de voz é o maior entre `limiar de silêncio + 8 dB` e `mediana da fala − 20 dB`, então respiração fica abaixo dele.
2. **Dentro de um silêncio medido**, a pelo menos `folga_silencio_s` (0,06 s) de cada borda do silêncio.
3. **Longe da voz.** O alvo é ~0,16 s depois do fim da voz (saída) e ~0,16 s antes do início dela (entrada). A busca aceita até 1,0 s de respiro entre a voz e o silêncio.
4. **Teste de energia.** O RMS nos 40 ms de cada lado do ponto fica pelo menos `energia_db` (15 dB) abaixo do pico da voz vizinha.

Por que a voz e não o Whisper: o Whisper erra a borda em até 0,15 s, cola palavras vizinhas e às vezes põe a palavra dentro do silêncio (armadilha 7). A folga de 0,15 s do plano virou "folga à voz medida", que é o que ela queria proteger.

**Sem silêncio medido** mas com trecho quieto: o ponto vai para o quadro mais perto do alvo entre os que ficam a até 6 dB do mais quieto, e ainda passa no teste de energia. A junta sai **relaxada** (V17_relaxada, HIGH) com crossfade de 20 ms. O Diretor julga em C2.

**Sem ponto nenhum:** BLOCKER, o EDL não sai. Troque a tomada ou a costura. Nunca baixe a régua.

## Juntas

| Tipo | Quando | Regra |
| --- | --- | --- |
| A (salto) | a próxima palavra mantida não é a vizinha no bruto: retake, bastidor, frase removida | ponto nos dois silêncios; resíduo 0,30–0,35 s |
| B (pausa colapsada) | palavras vizinhas, vão ≥ 0,6 s, entre frases (ou dentro da frase com `pausas_colapsar_intra`) | tira o meio do silêncio; se não achar ponto limpo, a pausa fica (não bloqueia) |
| pausa mantida | vão entre `pausa_max_s` (0,35) e 0,6 s | precisa estar em `pausas_preservar` com a função (V20) |

**Resíduo** = silêncio que fica na timeline em cada junta. Alvo 0,30–0,35 s, nunca zero. Respiro ≥ 0,15 s entre a voz e o silêncio fica inteiro e conta à parte: V19 é HIGH se o silêncio sobrando for < 0,20 ou > 0,60 s, ou se silêncio + respiro passar de 0,95 s. Os números são hipótese de engenheiro, a calibrar com o usuário ouvindo as juntas do piloto.

## Dinamismo das emendas

- `emendas: punch_in` (padrão): a escala alterna 1,00 / 1,035 entre segmentos vizinhos, trocando só na junta (no silêncio).
- Duas trocas a menos de `min_entre_trocas_s` (1,2 s): só uma leva punch-in.
- `emendas_seco[]` no `decisoes.json` veta o punch-in de uma junta, com motivo.
- Ganho por segmento: iguala o RMS da fala à mediana do bloco (±6 dB); ΔRMS na junta ≤ 3 dB (V31b).

## Conectores que não abrem bloco

"mas", "então", "aí", "e", "porque", "uhum", "olha só", "agora", "cara". Emenda que abre nisso é HIGH em F2 (frase pela metade?) e item da auto-rejeição de F3. Exceção com motivo: o gancho que começa assim de propósito ("Agora você pode…").

## Quanto sai

- Solo: 60–85 % do bruto sai (quase tudo é retake). Normal.
- O aviso dos 15 % (V21) vale só para pausas + fillers dentro das tomadas mantidas.
