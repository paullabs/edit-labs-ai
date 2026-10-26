# Portão de qualidade (responder por escrito antes de entregar; se um "não" aparecer, corrigir)

Montar a folha de quadros no tamanho da tela (um quadro a cada ~1,5 s; `ffmpeg -vf fps=1/1.5` ou
`motor/colagem/folha_quadros.py`) e responder como ESPECTADOR distraído, não como autor.

## Composição
1. Em qualquer quadro, dá para dizer em 1 s qual é o objeto principal? (herói ≥ 600 px na tela)
2. Há no máximo 1 rótulo e 1 número ao mesmo tempo? Algum texto menor que ~50 px?
3. Algum objeto tão pequeno que "nem dá para notar"? (cresce ou sai)
4. Tudo importante está dentro de x 80–960 e y 260–1420? (`motor.checar_margens`; só entradas e saídas podem passar)
5. A cena tem uma coisa por vez, ou está acumulando painéis e ícones?
6. O objeto central é o MESMO do começo ao fim (sem trocar de figura)?

## Explicação
7. A camada de baixo é mais interessante que a de cima? Cada revelação mostra o que o rótulo/voz diz?
8. Há algo fisicamente impossível (peça flutuando sem motivo, líquido em pé, corpo sem cabeça, enquadramento cortando
   o rosto)?
9. A ação principal se vê SEM som? O último quadro explica a ideia?
10. O que devia ser volume (3D) está em imagem chapada? (se sim, é slide)
11. Comparações estão na mesma escala, lado a lado? (nunca "o dobro" com alturas que mentem)

## Movimento
12. Câmera lenta, sem borrão fora de chicote deliberado, sem corte seco? Transição curta demais (< 1 s entre lugares)?
13. O destino de cada transição já tem o objeto quando ela termina (sem papel vazio, sem fantasma)?
14. Tudo volta ao lugar em ordem inversa no final (quando o vídeo desmonta algo)?
15. Entradas e saídas de peça têm sombra que cresce/some e pouso suave (nada "estoura" no canto)?
16. Algum plano fica parado por mais de ~2 s sem nada acontecendo?

## Som e entrega
17. Um efeito por ação visível, nível medido contra a trilha? Com voz: voz −16 LUFS, master −14 LUFS, pico ≤ −1,2
    dBTP. Sem voz: master ≈ −20 LUFS.
18. Quem gera o som mede, mas não escuta: declarar "escuta pendente".
19. Versão cheia + leve (crf ~23), `CREDITOS.md` do projeto com autor, licença e link de cada foto/modelo; modelos
    próprios declarados; créditos na tela por último (2,3 s).
20. Fatos conferidos no dia (números, datas, valores) e divergências de fonte sinalizadas na entrega.
