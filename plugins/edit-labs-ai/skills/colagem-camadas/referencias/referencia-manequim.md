# O manequim de 1890: anatomia da referência do estilo

Cena: `../exemplos/cena_manequim.py`. Peças: `../exemplos/manequim_pecas.py`. 22,5 s, 9:16, sem voz, trilha-leito calma.

## Como foi montado (a ordem importa)
1. **Fotografia por camada.** O boneco de papel real (American Manikin Co., 1890, Wellcome, domínio público) foi
   fotografado 12 vezes, na mesma posição, tirando uma peça por vez (de cima para baixo).
2. **Peça = diferença.** Entre a foto i e a i+1, a região que mudou (diferença em Lab desfocada, limpeza morfológica,
   buracos fechados) recortada da foto i vira a peça. Pular estados junta peças que saem juntas (cérebro e rosto).
3. **O estado de baixo entra no quadro exato em que a peça começa a levantar** (a troca não se vê); na volta, o estado
   de cima reaparece quando a peça pousa.
4. **Peças grandes saem da tela girando** (`levanta`); **peças pequenas** (estômago, coração, fragmentos) **se afastam
   e ficam paradas no ar** (`destaca`) até voltarem (`pousa`), em ordem inversa.
5. **Câmera:** já grande desde o início; aproxima da cabeça, desce ao tronco e à barriga, abre no joelho para as peças
   pequenas aparecerem, fecha no corpo inteiro. Curvas `io`, sem borrão.
6. **Som:** trilha-leito calma (−20 LUFS sem voz) e um efeito por pouso (`L.sons = [("pouso", q)]`).

## O que faz funcionar (a régua)
1. **Um objeto só, sempre na tela.** O mesmo boneco do começo ao fim. A figura muda por dentro; nada de "um cartão
   atrás do outro" (isso é slide).
2. **Camadas de verdade, registradas.** O que aparece embaixo é exatamente o que existia. Nada inventado, encaixe
   perfeito.
3. **Cada peça tem destino.** As grandes saem da tela; as pequenas ficam paradas no ar (vista explodida legível).
4. **Câmera lenta e com intenção.** Um mecanismo por vez; o olho já está onde a abertura começa.
5. **Fecha montando.** Tudo volta para o lugar em ordem inversa e cada peça pousa com som próprio.
6. **Perfeccionismo de borda:** borda branca de tesoura, sombra que cresce quando a peça descola, grão de papel, boil
   lento (3,5 trocas/s), vinheta leve. Nada serrilhado, nada de furo com borda branca.

## Como subir a régua
- **Sem legenda de fala embaixo.** Se precisar nomear, rótulo curto preso ao objeto (por isso a legenda dos exemplos
  vem desligada: `COLAGEM_LEGENDAS=1` liga).
- **Volume onde o objeto tem volume:** o estômago "por dentro", o crânio, o coração viram 3D renderizado (Z-Anatomy ou
  BodyParts3D) na mesma câmera, em vez de só foto chapada.
- **Mais riqueza por cena, sem acumular informação:** sombra de contato convincente, textura de papel por camada, um
  detalhe de vida por tela (respiração, pulso, líquido), transições planejadas.
