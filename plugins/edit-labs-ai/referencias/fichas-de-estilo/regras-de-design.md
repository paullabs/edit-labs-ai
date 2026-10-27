# Regras de design: margem, texto, fonte, densidade e camadas

Valem para todos os estilos de colagem em 1080×1920. Nasceram da medição de peças **profissionais** (o piloto
"Epigenetics" da Vox e o "Josephine Baker Tribute" da NBC Sports, ambos animados por Lucas Mariano, e o explicador
Vox Creative × JP Morgan). Números, método e limites: `../analises/vox-profissionais-2026.md`. As regras de produção
gerais (margem do Reels, uma coisa por vez, legenda por último) estão em `REGRAS.md` na raiz do plugin; aqui ficam as
de **design de quadro**.

Cada regra diz de onde vem: **[M]** medido nos profissionais, **[V]** visto neles, **[N]** decisão do plugin para o
vertical (calibrar com um quadro-chave antes de fixar).

## O erro que estas regras evitam

"Poluído" quase nunca é "coisa demais na tela". É **tudo com o mesmo peso**: dois sujeitos nítidos, três cores vivas,
texto sem suporte, nada em primeiro plano nem no fundo. Os profissionais enchem a tela (metade do quadro tem
detalhe) e **mesmo assim leem limpo**, porque o que é secundário fica cinza, desfocado ou cortado pela borda, e só
um objeto tem contraste e cor.

---

## 1. Margem

1. **Zona segura:** x 80–960, y 260–1420. Texto, número, rosto e o sujeito ficam aqui. **[N]** (é mais rígida que o
   mínimo medido: nos profissionais o texto que importa nunca chega a menos de ~6% da borda, ou 65 px num lado de
   1080 **[V]**).
2. **Respiro do texto:** a etiqueta ou o papel que carrega o texto fica a 40 px ou mais da borda da zona segura. **[N]**
3. **O que pode sangrar:** papel, fita, clipe, moldura, objeto de primeiro plano e círculo de dados passam da borda
   do quadro e da zona segura. A **palavra que importa nunca** sai. **[V]**
4. **Periferia preenchida:** a faixa de borda (~8% de cada lado) tem camada de baixo contraste (objeto cortado,
   desfocado ou cinza), e não só papel liso. Profissionais: 28–34% das células da borda com detalhe **[M]**. Alvo
   inicial do plugin: 20% ou mais **[N]**; veja o limite do medidor no fim.

## 2. Texto

5. **Quantidade:** no máximo **2 textos por plano** no vertical (1 rótulo + 1 número, ou 1 palavra-camada). Os
   profissionais usam 1 a 3 em 16:9 **[V]**; em 9:16 a largura é um terço, então cortamos. **[N]**
6. **Tamanho do trecho:** até **3 palavras** por texto. Documento real aparece como objeto e só 3 palavras recebem
   marca-texto. **[V]**
7. **Todo texto tem suporte:** etiqueta amarela, fita, placa de rua, cartaz, neon, folha de papel. Sem suporte só a
   **palavra-camada** (regra 11). **[V]**
8. **Tamanho (maiúscula, em 1080 de largura):**
   - rótulo: **36–48 px** de altura de maiúscula (fonte 56–72 px); mínimo 32 px de maiúscula (fonte 56 px).
     Profissionais: 2,8–4,5% do lado curto, mediana ~3,5% = 38 px **[V]**.
   - título: 50–65 px de maiúscula (fonte 80–100 px). Profissionais: 4,4–6% **[V]**.
   - palavra-camada: ocupa **70–90% da largura**. Profissionais: 30–45% da altura do quadro **[V]**.
   - nada abaixo de 32 px de maiúscula. Texto de documento fotografado não conta: não é para ser lido, só a parte
     marcada.
9. **Três papéis de fonte, nada mais:** (a) **serifa pesada** para título e etiqueta; (b) **grotesca pesada
   condensada** para a palavra-chave ou a pergunta; (c) **manuscrito em caixa alta** para anotação em fita ou
   etiqueta escura. Uma família por papel e no máximo **3 famílias** no vídeo. **[V]** A palavra-camada herda a serifa
   (a) e leva a cor de acento da cena em retícula.
10. **Entra depois da imagem**, e a imagem não espera o texto. Em vez de mais texto, um gesto de caneta: círculo,
    seta, "X", interrogação. **[V]**
11. **Palavra-camada:** uma palavra gigante (lugar, ano, tema) fica **entre** o fundo e o sujeito, e o sujeito cobre
    10 a 25% das letras. É a única palavra do plano. Confira que a parte coberta não esconde um dígito ou letra
    que muda o sentido (um "9" coberto lê "1800"). **[V]** ("Paris", "1963", "Family")

## 3. Densidade (como não poluir)

12. **Ocupação** (onde há detalhe no quadro, método na análise): média **35–50%**; nunca acima de **75% por mais de
    1 s**; pelo menos **1 plano em cada 5** com 30% ou menos (respiro e plano de herói). Profissionais: média
    43–45%, 10% dos quadros abaixo de 12–29%, 10% acima de 55–74% **[M]**.
13. **Um sujeito nítido por plano.** Ele tem o maior contraste e a única cor viva. O resto muda de valor: cinza,
    desaturado ou desfocado. **[V]**
14. **Cor, dois modos (escolha um por vídeo):**
    - **funcional:** até 3 cores vivas, cada uma com função fixa (ex.: amarelo = etiqueta e marca-texto;
      vermelho e verde = marcadores de dados). Saturação média 0,056 **[M]**.
    - **uma por cena:** uma cor, desaturada e com retícula (menta, coral, mostarda); o resto em preto e branco.
      Saturação média 0,12 **[M]**.
    Nunca mais de 3 cores vivas na mesma cena. **[V]**
15. **Ritmo:** cena nova a cada **4–9 s** (6–15 trocas por minuto); **~4–5 cortes secos por minuto**; o resto é
    troca no lugar. Ritmo em rajada é permitido (cinco imagens em 2 s), depois respiro de 3–12 s. **[M]**
16. **~15–18 desenhos distintos por segundo** com movimento contínuo e lento (mediana de diferença entre quadros
    de 0,004–0,006), e não um quadro parado trocando de vez em quando. **[M]**

## 4. Camadas (sempre valorizar)

17. **Três camadas legíveis em todo plano:** **fundo** (papel, textura ou cenário em cinza, baixo contraste),
    **plano do sujeito** (nítido, contraste e cor máximos) e **primeiro plano** (desfocado e cortado pela borda).
    Profissionais mostram 5 a 7 camadas físicas por quadro (mesa, cartão, fita, etiqueta, caneta, lupa; fundo,
    palavra, cenário, figura, bicho, banco desfocado). **[V]**
18. **Sombra em tudo que está sobre outra coisa:** curta e para baixo, **sempre da mesma direção** no vídeo todo;
    figura em pé leva uma elipse achatada no chão. **[V]**
19. **Algo por cima do objeto principal:** clipe, fita, caneta, lupa. É o que cria ordem de profundidade e dá a
    sensação de mesa. **[V]**
20. **Profundidade por foco:** primeiro plano com desfoque forte (começar com sigma de 6 a 10 px a 1080 e
    calibrar) e cortado pela borda; fundo mais claro e cinza. **[V]; valor [N]**
21. **Câmera com paralaxe:** as camadas andam em velocidades diferentes quando a câmera deriva (o primeiro plano
    mais rápido, o fundo mais devagar). Valores que funcionaram num teste: fundo 0,94 e primeiro plano 1,22–1,28
    **[N]**. O motor de camadas registradas faz isso com o parâmetro `prof` da camada.
22. **Troca por camada, não por corte:** a camada sai e outra entra (descascar, arrastar, máscara em forma de
    objeto como binóculo, túnel radial, desfoque de movimento circular). Corte seco só nos ~4–5 por minuto. **[V]**
23. **Divisão de canais RGB e granulado** só em transição e em material de arquivo, nunca como acabamento do
    vídeo todo. **[V]**

## 5. Conferência antes de entregar

1. Folha de quadros a cada 1,5 s e responder **por plano**: quantos textos? tem suporte? quantos sujeitos nítidos?
   quantas cores vivas? há as 3 camadas? a borda tem algo?
2. Opcional: medir a ocupação com o método da análise (bordas em grade de 8 px). O script de medição não vem
   no plugin.
3. Todo "não" vira linha na tabela "causa → regra → como conferir" do projeto.

| sintoma | causa | regra |
| --- | --- | --- |
| "poluído" | peso igual em tudo: 2 sujeitos nítidos, 4 cores | 13, 14 |
| "informação demais" | 3 ou mais textos, ou texto longo | 5, 6 |
| "parece slide" | tudo no centro, nada na borda, sem primeiro plano | 4, 17, 20 |
| "texto flutuando" | sem suporte | 7 |
| "letra pequena" | maiúscula abaixo de 32 px | 8 |
| "sem profundidade" | sem sombra, sem desfoque, sem paralaxe | 18, 20, 21 |

## Limites desta versão

- Tamanhos de texto e posição foram **estimados em quadros reduzidos** de 3 peças; valem como ordem de grandeza.
- A ocupação conta **bordas fortes** (grão e grade de papel entram). Um fundo cinza de baixo contraste, que é
  exatamente o que a regra 17 pede, **quase não aumenta** esse número. Num teste com um explicador de anatomia, a
  ocupação da borda subiu pouco depois de acrescentar fundo cinza, folhas e primeiro plano desfocado, embora a
  mudança fosse clara a olho e a meta de 20% não fosse atingida. Por isso a regra 4 não deve ser aprovada só pelo
  medidor: confira por quadro, a olho, "tem fundo, sujeito e primeiro plano?".
- Os profissionais são 16:9 e os vídeos do plugin são verticais; a comparação da faixa de borda é indicativa.
- Faltam: medir desfoque de primeiro plano, a distância real de sombra e a velocidade da paralaxe. Itens **[N]**
  devem ser calibrados em um quadro-chave antes de virar regra fixa.
