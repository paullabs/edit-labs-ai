# Som de um reel sem voz

Sem voz, a música não acompanha uma fala: ela é só o leito. Os efeitos marcam o que a imagem faz (o carimbo bate, o
papel pousa, a caneta risca) e precisam se ouvir sem serem altos.

## Os níveis

| o quê | valor | por quê |
| --- | --- | --- |
| master | **≈ −20 LUFS**, pico abaixo de −3 dBTP | −14 LUFS é o volume de um vídeo com voz; sem voz, nesse volume, a música e os efeitos soam altos e cansam |
| trilha antes da mixagem | −24 LUFS, com compressão leve e filtro nos graves e agudos extremos | fica um leito estável |
| efeito × música | pico do efeito no máximo +3 a +6 dB acima da música no instante: carimbo +6, transições +3 a +4, pousos +3 | o efeito se ouve sem pular do vídeo |
| ducking | a música cede de 2 a 3 dB quando um efeito toca | o efeito aparece sem precisar subir |

**Regra:** sem voz, mais baixo (−20 LUFS). Com voz, valem os níveis de voz do `${CLAUDE_PLUGIN_ROOT}/REGRAS.md` §7
(voz −16, master −14).

No motor: `som_auto.mixar_auto(..., alvo_lufs=-20, trilha_lufs=-24)` e as tabelas `PICO_MAX` e `PICO_REL` no
`som_auto.py`. Os modelos chamam isso no `--som`.

## A trilha

- **Calma, escolhida por medida:** poucos ataques por segundo (≲ 1 por segundo) e nível estável. As trilhas mais
  agitadas de uma biblioteca (1,4 a 1,9 ataques por segundo) brigam com os efeitos.
- Escolha o **trecho** da trilha, e não só a faixa: meça e comece no trecho calmo (`TRILHA_INI` no modelo).
- **Licença:** bancos como Mixkit e Artlist permitem usar no vídeo, mas **não redistribuir** o arquivo. A trilha
  fica na pasta do usuário (`pecas/` ou `$EDITLABS_DATA/colagem/trilhas`), nunca no plugin nem num projeto
  compartilhado. No `CREDITOS.md`, cite o nome da faixa, o autor, o link e a licença.

## Os efeitos

- **Nascem da cena** (`som_auto.eventos_da_cena`): o carimbo, o pouso do objeto, o cartão que vira, cada
  transição, o traço de caneta, o contador e o chicote de câmera são lidos das camadas e da câmera, então cada som cai
  no quadro do contato. Nunca escreva a lista de sons à mão: ela sai do compasso das imagens.
- **Direção:** o rasgo de papel vai para o mesmo lado da imagem; o objeto que entra deslizando traz o som do lado de
  onde chega.
- **Cada ocorrência soa diferente:** fatias novas dos áudios de papel, carimbo e caneta sintetizados com altura e
  nível sorteados e uma lista de amostras que gira.
- **Poucos:** de 19 a 26 efeitos em 30 s, de uns 10 tipos. Mais que isso cansa.
- **A caneta** faz um som contínuo do tamanho do traço, e não um clique de 0,3 s. **O relógio** faz tique-taque a
  2 Hz enquanto o contador corre, e não um tique por pedaço.
- **Sem biblioteca de efeitos**, o motor sintetiza os sons em código. Com biblioteca, ela fica em
  `$EDITLABS_DATA/colagem/sons` (uma subpasta por classe). Efeito de banco com licença que proíbe redistribuir nunca
  vai junto.

## Conferir

- `som/som.json`: a lista de efeitos (tempo, classe e material).
- `grafico_som.py`, do motor: o gráfico da música, dos efeitos e do master no tempo.
- **Quem gera o som mede, mas não escuta.** Declare a escuta humana como pendente na entrega.
