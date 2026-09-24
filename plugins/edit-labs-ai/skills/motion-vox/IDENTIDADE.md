# MOTION-VOX v1

Identidade visual fechada. Quem instalar esta skill reproduz **este** visual, não um
parecido: as fontes e os assets viajam junto.

```yaml
identidade: MOTION-VOX
versao: 1
canvas: 1080x1920
base: Vox Explainer LABS (gramática editorial dos explicativos da Vox)
```

## O que faz esta identidade ser esta identidade

Não é a paleta sozinha, nem as fontes sozinhas. São seis coisas, e trocar qualquer uma
produz outra identidade — o que é legítimo, mas aí é outra versão, com outro nome.

1. **Papel marfim pontilhado** como chão de toda cena de mesa.
2. **Três props recorrentes** — fita crepe, clipe, retalhos — presentes em todas as cenas.
3. **Cinco funções tipográficas** com fontes fixas (abaixo).
4. **Um acento por cena**, com função: amarelo `#DBD653` ou azul `#2E82F7`.
5. **Anotação procedural** — círculo, seta, sublinhado desenhados com jitter de mão,
   nunca vetor perfeito.
6. **Acabamento** — grão "on twos" com campo borrado, vinheta discreta, aberração
   cromática radial nula no centro, push de câmera de 3–4%.
7. **Boil a 9fps** — cada elemento redesenhado a cada passo, com intensidade por classe.
   É o que separa "colado" de "feito à mão". Ver `referencias/boil.md`.

## Tipografia — as fontes vão junto

| Função | Fonte | Peso | Licença |
| --- | --- | --- | --- |
| manchete condensada | Archivo Narrow | 700 (eixo) | OFL |
| etiqueta manual | Permanent Marker | regular | Apache 2.0 |
| legenda técnica | IBM Plex Mono | Medium | OFL |
| número editorial | Fraunces | 800 (eixo) | OFL |
| legenda falada | Inter | 700 (eixo) | OFL |

São as alternativas canônicas do estilo para cada função, todas de licença livre.

**Por que não as do macOS.** DIN Condensed Bold, Bradley Hand e Helvetica Neue são da
Apple e **não podem ser redistribuídas** — a identidade ficaria presa a uma máquina.
Archivo Narrow é 1,35× mais larga que a DIN, por isso os corpos do kit são calibrados
para ela; Permanent Marker fica a 1,04× da Bradley Hand e lê até melhor em corpo pequeno.

## Como evoluir a identidade

Ela muda por **laudo**, não por gosto. O ciclo:

1. Uma decisão é tomada numa produção (asset novo, registro novo, parâmetro novo).
2. O Diretor aprova ou reprova, por escrito, contra a rubrica.
3. **Aprovado** → vira regra em `referencias/` e, se for asset, entra em `assets/`
   depois de passar D1.
4. **Reprovado** → vira item em `referencias/armadilhas.md`, com o porquê.

A parte que mais vale é a das reprovações. Cada armadilha é um retrabalho que não
precisa se repetir.

**Mudança que altera o visual** (fonte, paleta, acabamento) sobe a versão: `MOTION-VOX v2`.
Mudança de método, regra ou asset novo não sobe. Os laudos devem dizer em qual versão
foram feitos.

## Decisões fixas

Não se perdem numa refatoração:

- **push de câmera lento**, 3–4% ao longo da cena — nunca impacto
- **grão "on twos"** com campo borrado (σ 0,9): grão de filme tem tamanho, e ruído de
  1px por frame é incompressível
- **aberração cromática radial** leve, nula no centro — a uniforme franja a tipografia
- **boil a 9fps** com semente por elemento, e campo compartilhado entre elementos que
  são fisicamente um só

## O que fica fora da identidade

- gravura de caverna → metáfora não vence referente
- pilha de cartões como "produto" → some sob o rótulo
- fundo chroma nos assets → 65% dos pixels de borda contaminados
- flash branco instantâneo (strobe) e whip pan → fora; o `flash` do kit é desfoque
  gradual, outra coisa (`referencias/transicoes.md`)
- revelar texto caractere a caractere → é máquina de escrever
- número estimado em tipografia de dado → vai em marcador
