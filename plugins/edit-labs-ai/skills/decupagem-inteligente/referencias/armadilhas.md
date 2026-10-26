# Armadilhas — corte, retake, transcrição, verificação, processo

Cada item custou uma rodada. Formato: sintoma · causa · correção · fase em que apareceu. O Diretor cita o número; achado que repete armadilha sobe uma severidade. Motion fica em `${CLAUDE_PLUGIN_ROOT}/skills/motion-vox/referencias/armadilhas.md`.

## Leitura (transcrição e retakes)

**1. Glossário só vale na primeira janela**
- Sintoma: "Cloud Code" o vídeo inteiro, mesmo com "Claude Code" no glossário.
- Causa: com `condition_on_previous_text=False`, o mlx-whisper descarta o `initial_prompt` depois da primeira janela de 30 s.
- Correção: `transcrever.py` injeta os tokens do glossário em toda janela (DecodingOptions); palavra perto de termo do glossário vira `sugerido` + `ambigua`, nunca troca sozinha.
- Fase: F1.

**2. "é" virou hesitação**
- Sintoma: frases perdiam o verbo "é" como se fosse "éé".
- Causa: comparação de hesitação sem acento.
- Correção: HESITACOES comparadas com acento; "é/né/tipo/assim" só contam isoladas.
- Fase: F1.

**3. Whisper estica palavra por cima de repetição**
- Sintoma: uma palavra de 1,5 s que engole um recomeço; o corte não acha o silêncio.
- Causa: o Whisper cola repetições e pausas numa palavra só.
- Correção: `di transcrever --realinhar` retranscreve janelas curtas (≤ 8 s) e costura palavra a palavra: nunca apaga palavra velha, só insere a nova se couber.
- Fase: F1.

**4. Silêncio longo vira "E aí E aí E aí"**
- Sintoma: dez frases "E aí" a −80 dB entre duas tentativas.
- Causa: alucinação do Whisper em silêncio.
- Correção: marca `~` (alucinação suspeita), fora do agrupamento; o mapa declara a faixa como alucinação.
- Fase: F1.

**5. Fala continuada lida como abandonada**
- Sintoma: a sugestão ✓ caía na metade curta ("Se você passa a hora") em vez da fala inteira.
- Causa: frase sem ponto e com vão < 0,5 s até a seguinte contava como incompleta.
- Correção: frase que emenda direto numa frase de outro grupo (sem recomeçar) conta como completa (`continuada`).
- Fase: F1.

**6. Metades num grupo de retake**
- Sintoma: "Alguém no GitHub…" e "Que fica entre…" agrupadas como alternativas.
- Causa: as duas somadas batem com a tomada inteira seguinte, e cada uma sozinha já passa do limiar.
- Correção: `retakes.py` marca `metade` (`½+F024` no digest); o Editor escolhe as duas metades ou a inteira.
- Fase: F1.

## Corte (EDL)

**7. Folga contada da borda do Whisper**
- Sintoma: nenhuma junta passava; ou o corte caía dentro da palavra.
- Causa: o Whisper erra a borda em até 0,15 s e às vezes põe a palavra dentro do silêncio.
- Correção: ponto de corte pela voz medida (envelope: `voz_inicio`/`voz_fim`), ~0,16 s de cada lado, dentro de silêncio medido, com teste de energia contra o pico da voz vizinha.
- Fase: F2.

**8. Respiração bloqueava o silêncio**
- Sintoma: "sem silêncio para cortar" onde havia pausa clara.
- Causa: a inspiração fica acima do limiar de silêncio.
- Correção: limiar de voz relativo à mediana da fala; busca aceita até 1,0 s de respiro entre a voz e o silêncio; respiro ≥ 0,15 s conta à parte do resíduo (V19).
- Fase: F2.

**9. Ordem cronológica desfazia a escolha de tomada**
- Sintoma: a tomada escolhida aparecia antes da frase que ela completa.
- Causa: EDL ordenado pelo tempo do bruto.
- Correção: a ordem é a do `manter` do Editor; voltar no tempo é aviso (V16).
- Fase: F2.

**10. Pausa curta sem função**
- Sintoma: V20 HIGH com pausas de 0,40–0,50 s.
- Causa: vão acima de `pausa_max_s` (0,35) e abaixo do mínimo para colapsar (0,6).
- Correção: o Editor lista em `pausas_preservar` com a função (respiro antes de número, antes do pedido). Abaixo de 0,6 s não compensa emenda.
- Fase: F2.

**50. Pausa declarada procurada no fim da palavra que o Whisper esticou**
- Sintoma: V30 HIGH numa pausa que está em `pausas_preservar` e aparece certinha no MARCAS ("00:23.3 0.57s").
- Causa: `verificar_corte` ancorava a pausa preservada no fim da palavra (`pal[a].e`). Quando o Whisper estica a palavra (o mesmo caso que o V20b acusa — "criou" com 2,72 s), a pausa real cai **dentro** do span da palavra e o verificador a procurava segundos depois.
- Correção: o V30 procura a pausa declarada na faixa `pal[a].t → pal[a+1].e` e compara com o centro do silêncio medido, não com o ponto do fim da palavra.
- Fase: F3.
- **Revisto (armadilhas 60):** esta correção tratou o sintoma. A "pausa" que o V30 procurava era o silêncio ENTRE um falso começo e o recomeço, os dois engolidos no "criou" — e ensinar o verificador a achar a pausa declarada fez ele aceitar o defeito. Palavra esticada com voz dentro não se valida: se corta (`cortar_trecho`, V20d).

## Render e verificação

**11. `-ss` + `-t` na saída cortava o áudio**
- Sintoma: 2 s de silêncio digital em cada junta (V30 pegou).
- Causa: com pre-seek de 2 s, `-t` na saída contava a partir do seek.
- Correção: trim/atrim por filtro, exatos; `-frames:v` exato.
- Fase: F3.

**12. Decode por hardware falha em 4K**
- Sintoma: "hardware accelerator failed".
- Causa: `-hwaccel videotoolbox` no decode.
- Correção: decode em software; `h264_videotoolbox` só no encode.
- Fase: F3.

## Revisão

**13. Leigo julga erro de transcrição como corte**
- Sintoma: BLOCKER em "comenta aqui, Facebook eu te mando" ("frase cortada").
- Causa: o pacote mostrava a palavra do Whisper.
- Correção: o pacote troca a palavra sugerida pelo glossário e mostra `[palavra incerta]` na pendência; achado sobre `[palavra incerta]` vira `tipo: pendencia` LOW, por código.
- Fase: F2.

**14. Leigo aprova com HIGH aberto**
- Sintoma: veredito APROVADO_COM_CORRECAO com HIGH de corte não corrigido; laudo recusado.
- Causa: o modelo mistura "eu entendi" com "está certo".
- Correção: `laudo gravar --de leigo` aplica a regra por código (BLOCKER/HIGH aberto → REPROVADO; `veredito_do_leigo` guardado).
- Fase: F2.

**51. O pacote cego conta ao Leigo onde o corte cai dentro do bruto**
- Sintoma: o Leigo reprova o fim por corte três vezes seguidas, citando a folha do pacote ("o papel diz que ainda tinha fala gravada depois disso"), e o Editor remonta o fim sem que exista remontagem possível.
- Causa: `sobre.txt` trazia "começo:" e "fim:" comparando o corte com o bruto. "O corte termina antes da última fala gravada" é verdade em quase todo solo (sempre sobra bastidor depois da última tomada) e planta a ideia de que faltou um pedaço — o Leigo passa a reprovar por `corte` o que é buraco de conteúdo do próprio bruto.
- Correção: `pacote_leigo.sobre_pontas` não fala mais do bruto; diz só duração, trechos e "este é o vídeo inteiro, do começo ao fim — não é um trecho de algo maior". O que o Leigo não pode ver, ele não julga.
- Fase: F2.

**15. Leigo escreve "ouvi"**
- Sintoma: laudo recusado por verbo de escuta.
- Causa: o Leigo lê texto, mas fala como espectador.
- Correção: regra 10 do papel ("escreva li"); o validador recusa verbo de escuta sem `escuta: humana`.
- Fase: F2.

**52. Leigo reprova por corte o pulo de cabeça da emenda**
- Sintoma: Leigo HIGH `tipo: corte` — "de um quadro para o outro o rosto fica maior e escorrega para o lado" — em emendas que o Verificador já mediu (V37: junta 3, 5,2 %; junta 6, 7,2 %).
- Causa: ele vê os quadros das juntas no pacote da F3. O pulo é próprio do corte entre tomadas do mesmo plano: nenhuma remontagem o tira, e a skill já dá o dono — a cutaway do plano de motion (o próprio V37 diz "vira tarefa do plano (F4)").
- Correção: regra 17 por código em `laudo.ajustar_leigo`: achado de `corte` sobre rosto/cabeça pulando na emenda, num vídeo com `pulo_de_cabeca` em `avisos.json`, vira `conteudo` LOW e entra na F4 como tarefa. O texto do Leigo não muda.
- Fase: F3.

**53. A correção do portão troca a palavra também onde havia decisão de não trocar**
- Sintoma: o usuário confirma "Markdown → MarkItDown" e o transcript do motion sai "em arquivos MarkItDown, aquele .md" — ali a palavra é o FORMATO, e o MARCAS já dizia que fica.
- Causa: `aplicar_correcoes` casava por forma, sem olhar a decisão escrita por ocorrência.
- Correção: `exportar` monta o conjunto de intocáveis a partir de `decisoes.ambiguas` (status `confirmada` apontando para a própria palavra) e passa a `aplicar_correcoes`, que pula esses índices.
- Fase: F4.

**54. O glossário do usuário não chegava à legenda**
- Sintoma: o MARCAS diz "'Cloud' → 'Claude' (glossário)" e o `palavras_corte.json` (legenda, SRT e motion) sai com "Cloud" nas quatro ocorrências.
- Causa: `remapear` copiava a palavra do Whisper; a sugestão do glossário ia junto como campo, sem entrar no texto.
- Correção: `remapear` aplica a sugestão do glossário (própria ou pela forma, como o MARCAS já fazia), só com 4+ letras — palavra curta vira outra coisa ("a" → "horas", armadilha 39).
- Fase: F4.

**55. O pacote cego cala a palavra que o usuário já confirmou**
- Sintoma: depois de `di portao confirmar 3 --valor "Markdown → MarkItDown"`, o Leigo da F4 continua lendo "em arquivos [palavra incerta] aquele .md" e abre LOW de pendência a cada tentativa.
- Causa: a máscara vinha de `decisoes.ambiguas`, que segue com `status: a confirmar` (o Editor não reescreve o arquivo a cada resposta); a resposta do usuário mora em `correcoes[]` no manifest e já estava no texto exportado.
- Correção: `pacote_leigo` tira da máscara toda palavra coberta por uma correção confirmada no manifest.
- Fase: F4.

**56. Pacote de imagens sem índice: o Leigo volta dizendo "a pasta está vazia para mim"**
- Sintoma: o Revisor Leigo da F5 devolve "o `LEIA-ME.md` não existe" e não emite laudo. A pasta tinha as 16 imagens.
- Causa: o pacote de F5/F6/F7 só copia quadros; o texto de instrução era dado a mão no pedido. O Leigo roda com a ferramenta de LER arquivo e mais nada — sem listar pasta, sem buscar —, então arquivo que ele não sabe nomear não existe para ele.
- Correção: `pacote_leigo._leia_me` escreve o `LEIA-ME.md` em todo pacote, de toda fase, com o passo, a ordem das letras, o que `_deitado` quer dizer e a lista dos arquivos.
- Fase: F5 t3.

**57. Texto a marcador ilegível no preview, medido em 17 px**
- Sintoma: os nomes "WORD", "EXCEL" e "POWERPOINT" na aba das pastas de M5 somem a 300 px — e é o nome que faz a cena, porque o ícone do aplicativo não pode entrar como marca.
- Causa: `escrito(..., corpo=0.075)` é fração da ALTURA do asset; pasta larga e baixa devolve corpo minúsculo. E ninguém mede o que se escreve dentro de um asset: `legibilidade.py` compara dois renders do quadro e não enxerga tinta que já veio embutida no PNG.
- Correção: medir a altura da tinta de cada palavra escrita no QUADRO final (piso de 36 px em 1920), não no asset.
- Fase: F5 t3.

**58. O Leigo é descartado por falar português: "marcas" casou com o arquivo MARCAS**
- Sintoma: `laudo gravar --de leigo` devolve "CONTAMINADO: vocabulário de Diretor/arquivo (\bMARCAS\b)". O laudo dizia "umas marcas pequenininhas que eu não consigo ler".
- Causa: a lista `CONTAMINA` inteira era casada com `re.I`, e nela havia nome de ARQUIVO em caixa alta. "MARCAS" é o arquivo da F2; "marcas" é palavra de todo dia.
- Correção: `CONTAMINA_CS` (MARCAS, EDL, TOMADAS.jpg) casada SEM `re.I`; o resto segue insensível. Mesma classe no V81 (escuta): `\bassust` casava "servidor assusta quem não é da área" — agora só `assustou/assustei/assustava/assustaram`.
- Fase: F5 t4.

**59. Página gerada sem margem lê como retângulo listrado, não como página**
- Sintoma: o Leigo reprovou o mesmo quadro duas tentativas seguidas — "retângulos cinza vazios", "não é nada que eu reconheça" — sobre o herói PAGINA_DENSA, que é o documento que a fala descreve.
- Causa: o prompt pedia "the whole sheet filled with about forty dense rows ... from the top edge to the bottom edge". Texto corrido de borda a borda, sem margem e sem parágrafo. A 300 px de preview ninguém lê a letra: o que faz reconhecer uma página é a MARGEM e o ritmo do parágrafo, e o asset não tinha nem um nem outro.
- Correção: no prompt, sempre "clear white margins on all four sides" + "separated paragraph blocks" para qualquer herói de papel impresso (`motion-vox/referencias/assets-sob-medida.md`). Quando o asset já existe, `pagina_documento()` remonta a página sobre a folha do kit — margem, título curto, parágrafos com respiro, última linha mais curta — usando recortes reais da tinta do asset, sem gastar crédito.
- Fase: F5 t3.

**60. Falso começo escondido numa palavra esticada — e declarado como "suspense"**
- Sintoma: o usuário ouviu no piloto da F6 "A Microsoft criou uma ferramenta — A Microsoft criou uma ferramenta gratuita". Passou por F1, F2, F3 (aprovada), F4, F5 e todos os revisores.
- Causa, em três camadas: (1) o Whisper pôs "criou" de 111,22 a 113,94 s (2,72 s) e engoliu dentro dela a primeira passada inteira — nenhuma palavra repetida no transcript, então V22c/V29 não tinham o que achar; (2) o V30 acusou o vão e o Editor o calou declarando `pausas_preservar` "suspense antes do nome da ferramenta" sem medir o que havia dentro — 77 % do vão tinha voz; (3) F1 e F2 eram portões internos, e ninguém dentro da skill ouve.
- Correção: o corte só vai ao usuário com a auditoria frase a frase (`di auditar`, ver 61); palavra mantida com duração > 1,2 s e voz medida em mais da metade dela é BLOCKER no `di edl` (V20d); pausa com voz dentro não entra em `pausas_preservar`; e o corte dentro de uma palavra esticada se faz com `cortar_trecho` (onde a fala abandonada termina e onde a tomada boa recomeça), sem mexer no transcript. A retranscrição isolada do trecho (faster-whisper, sem prompt) é o que revela as palavras engolidas.

**61. Um vídeo levava horas: rodada de revisor em cascata antes de cada parada**
- Sintoma: um vídeo passou dois dias entre F2 e F6 — cinco tentativas abertas só para Diretor e Leigo conferirem papel — e mesmo assim um falso começo passou; quem pegou foi o usuário, no piloto.
- Causa: cada fase exigia Diretor e Leigo por tentativa, com teto de 3 e escalada; F1, F2, F5 e F6 ainda paravam. O custo ia para conferir relatório, não para achar o erro no áudio.
- Correção: três entregas ao usuário — corte + prévia (F3), plano (F4), vídeo completo (F7). F1/F2/F5/F6 correm sem parar e sem revisor; por dentro fica o Verificador e, no corte, `di auditar` (frase por frase, com tempo no corte e no bruto, voz medida nos vãos, o que o render diz). A única rodada de Diretor é a análise C4 do plano já aprovado, uma vez. Reprovação do usuário no corte volta pela auditoria, frase por frase.

## Processo

**16. Render adiantado mudava a fase**
- Sintoma: `ESTADO.md` dizia F3 com F1 aberta.
- Causa: `render_corte.py` gravava `fase_atual = F3` mesmo rodado com `--agora` em teste.
- Correção: só muda a fase se F2 estiver fechada; `abrir-tentativa` recusa fase com a anterior aberta.
- Fase: construção da skill.

**17. Pausa escondida dentro da palavra do Whisper**
- Sintoma: V30 no render (0,66 s de silêncio dentro de um segmento) que F2 não viu.
- Causa: o Whisper esticou "Se" por cima de um silêncio medido; o vão entre palavras era zero.
- Correção: F2 usa o maior silêncio medido entre as palavras (não só o vão do Whisper); V20 lista cada pausa sem função; V20b avisa palavra mantida ≥ 50 % dentro de silêncio.
- Fase: F3.

**18. Fim do vídeo leva o começo da palavra seguinte**
- Sintoma: V33 no render (voz até o último quadro); o fim pegava "Se-" de "Segue o perfil".
- Causa: a última palavra mantida emenda direto na seguinte, sem silêncio; o ponto de saída ficou sem régua.
- Correção: V18b em F2 (voz medida depois do fim da voz mantida, dentro do corte). O Editor mantém a palavra seguinte ou troca o fim.
- Fase: F3.

**19. Rosto "fora do recorte" com o rosto no lugar**
- Sintoma: V37b HIGH em 96–98 % com os piores quadros bem enquadrados.
- Causa: o critério pedia a caixa inteira (queixo) acima de 0,60 H; ao se inclinar, o queixo passa.
- Correção: centro do rosto acima de 0,60 H, topo dentro do quadro, margem lateral de 5 %.
- Fase: F3.

**20. Diretor reprova três vezes pelo mesmo defeito**
- Sintoma: F1 escalada ao usuário; cada tentativa achava um grupo novo com o mesmo problema.
- Causa: o Diretor citava um caso e o Editor corrigia só o citado.
- Correção: papel do Diretor manda varrer por tipo e, na t2+, conferir os achados anteriores primeiro; fases 1 e 2 mandam o Editor corrigir todas as ocorrências do tipo.
- Fase: F1 t1–t3.

**21. Laudo com dois-pontos no texto livre não grava**
- Sintoma: "mapping values are not allowed here"; o laudo C1 t4 ficou só no `.bruto.md`.
- Causa: texto livre sem aspas com ": " no meio (a mesma lição da motion-vox).
- Correção: `laudo.py` repara valor simples de várias linhas como bloco `>-`; os papéis mandam pôr texto livre entre aspas.
- Fase: F1 t4.

**22. O Whisper adianta a próxima palavra e o fim fica sem régua**
- Sintoma: o fim do vídeo 1 saiu "sem silêncio" (corte às cegas), levando o "S-" de "Segue".
- Causa: a busca do ponto de saída parava no início do Whisper da palavra seguinte (286,28 s), antes do fim medido da voz; a volta real da voz era 286,54 s.
- Correção: o limite da busca é a volta MEDIDA da voz; o ponto caiu no vão de 0,12 s a −47 dB (286,48 s).
- Fase: F2 t2.

**23. Estalo antes da fala abre o segmento cedo demais**
- Sintoma: 0,76 s de silêncio dentro do segmento, depois de um som curto de 0,12 s.
- Causa: o início de voz pegou o estalo (ou um "S-" solto) como começo da frase.
- Correção: `entrada: voz_sustentada` no item de `manter` (o Editor pede, com motivo); a retranscrição do render confere se a palavra ficou.

**24. "sou" lido como verbo de escuta**
- Sintoma: laudo do Leigo recusado sem verbo de escuta nenhum.
- Causa: o padrão de "soou" (`soo?u`) casava "sou" ("Sou gente que chegou pelo feed").
- Correção: padrão só `soou`.
- Fase: F2 t2.

**25. Pausa listada que o corte já tirou**
- Sintoma: o Diretor achou uma pausa preservada "depois de 'E'" 0,1 s antes do início do segmento.
- Causa: o Whisper adiantou o "E"; o silêncio que parecia depois dele estava antes da voz real, e a entrada pela voz já o tinha tirado.
- Correção: V20 e V20c medem a pausa DENTRO do corte; pausa listada fora do corte é MEDIUM e sai da lista.
- Fase: F2 t2.

**26. Nome de duas palavras virou "NotebookLM LM" no pacote**
- Sintoma: BLOCKER do Leigo, "sobrou um pedaço do nome".
- Causa: a sugestão do glossário trocava só a primeira das duas palavras do Whisper ("Notebook" + "LM").
- Correção: sugestão que já contém a palavra seguinte engole essa palavra no pacote.
- Fase: F2 t2.

**27. Conteúdo tirado sem motivo escrito**
- Sintoma: o Diretor achou trechos de conteúdo marcados "removido" ou "bastidor" sem justificativa.
- Causa: `padrao: remover` tira tudo o que não está em `manter`, e a tabela "Sai" não tinha motivo.
- Correção: V14b (HIGH) exige `remover[]` com motivo para todo trecho de conteúdo ≥ 1 s; MARCAS mostra o motivo.
- Fase: F2 t2.

**28. Frase colada que não dá para tirar**
- Sintoma: tirar "E ela faz tudo automaticamente" deu BLOCKER (V17).
- Causa: "…todo o resto e ela faz…" é um fôlego só; o único vão tem 40–60 ms e não passa no teste de energia.
- Correção: a frase fica, com motivo, e vira oferta ao usuário no portão F3 (emenda colada com crossfade só com a palavra dele). Nunca afrouxar o teste de energia.
- Fase: F2 t3.

**29. "ouvir" e "ouvindo" recusados como escuta inventada**
- Sintoma: laudo do Diretor recusado por escrever "só se julga ouvindo" e "quais juntas ouvir primeiro".
- Causa: o padrão pegava infinitivo e gerúndio, que falam da escuta do usuário, não de ter ouvido.
- Correção: só a afirmação conta ("ouvi", "escutei", "soou", "estala"); "não ouvi" e "nem ouvi" são negação.
- Fase: F2 t3.

**30. Laudo recusado por incoerência custa uma revisão inteira**
- Sintoma: o Diretor escreveu "corrigido" no texto e `corrigido: false` no campo; refazer a C2 levou 5 min.
- Causa: o gravador só recusava.
- Correção: `revisor.py` devolve o laudo e o erro ao mesmo papel uma vez, para corrigir só formato ou coerência, sem mudar achado; contaminação e laudo existente continuam recusados direto.
- Fase: F2 t3.

**31. Salto de nível na emenda com ganho pela mediana**
- Sintoma: V31b −4,0 e −3,8 dB em duas juntas do vídeo 1, acima da variação natural do falante (p90 ≤ 3 dB nas trocas de frase sem corte).
- Causa: o ganho iguala a mediana do segmento; o fim de frase cai de nível e a frase seguinte abre alta.
- Correção: V31b compara com a linha de base do próprio vídeo; `edl.py` nivela a junta (alvo 2,5 dB, no máximo ±1,5 dB por segmento, `ganho_ajuste_junta` no EDL). O resto fica para a escuta do usuário.
- Fase: F3 t1.

**32. Palavra adiantada pelo Whisper "cruza a borda" no remapeamento**
- Sintoma: V40 BLOCKER com "E" e "Se" fora do segmento, e as duas estavam no render.
- Causa: o Whisper do bruto adiantou as palavras 0,4–0,6 s; o corte entra pela voz medida.
- Correção: o remapeamento alinha as palavras mantidas com a retranscrição do render e usa o tempo dela para palavra fora da borda ou encostada (±0,1 s), na ordem do bruto.
- Fase: F3 t1.

**33. O Leigo não sabe onde estão as emendas**
- Sintoma: BLOCKER "falta um pedaço no meio" numa frase contínua do autor, sem emenda nenhuma ali.
- Causa: o texto do corte não mostra onde houve corte, e a pontuação do Whisper ("provedores, Você conecta") parece frase quebrada.
- Correção: `‖` no texto do pacote F3 em cada emenda (fato do produto, não motivo); regra 17 do Leigo: longe de `‖` é conteúdo.
- Fase: F3 t1.

**34. Início da voz achado na cauda da palavra anterior**
- Sintoma: BLOCKER "a voz de 'Você' sai direto da fala anterior", com 0,16 s de silêncio medido logo depois.
- Causa: a janela de busca começava no meio de "provedores" (o Whisper a encurtou), e a voz em curso foi lida como início.
- Correção: se a janela começa com voz soando, a busca pula até o primeiro vale e procura o início real depois.
- Fase: F3 t2.

**35. Fim sem silêncio: melhor terminar na repetição do autor**
- Sintoma: o fim cortava 0,10 s depois da voz, com o gesto pela metade (V33, Leigo e Diretor).
- Causa: a frase final emendava em "Segue o perfil" sem pausa; estender o corte pegaria o "S".
- Correção: terminar onde o autor terminou a tomada ("… Segue o perfil."), com `repeticao_intencional` e motivo; V15 vira aviso V15b para o Diretor julgar.
- Fase: F3 t2.

**36. Tentativa de um vídeo herdando checagem do próprio vídeo**
- Sintoma: o Diretor achou V40 e V41 do vídeo 1 "herdados da t1" (1055 quadros) num vídeo recortado para 1007 quadros; a verificação parecia limpa.
- Causa: a tentativa nova herdava todas as checagens da anterior, inclusive as do vídeo que mudou.
- Correção: tentativa com `video` não herda nada desse vídeo; só os intocados herdam, marcados `herdado_de`.
- Fase: F3 t2.

**37. Fala rápida quase não tem silêncio medido**
- Sintoma: só 6 pontos em 37 s onde uma cena podia terminar "no silêncio".
- Causa: a fala é contínua; o limiar de silêncio (−47 dB) quase nunca é atingido entre palavras.
- Correção: t1 da cutaway vale no silêncio medido (ideal), na fronteira entre palavras ou numa emenda; no meio da palavra é HIGH (V50, ancorar.py).
- Fase: F4.

**38. Maiúscula não é dúvida**
- Sintoma: "KIMI K2 → Kimi K2" calava a legenda e travava a cena do Kimi.
- Causa: o par entrava como pendência igual a "Antropic → Anthropic".
- Correção: só o par em que a palavra MUDA é pendente (`pares_pendentes`).
- Fase: F4, F6.

**39. Retranscrição do piloto contra o transcript dá diferença falsa**
- Sintoma: V61 com 8,6 % e nenhuma palavra perdida.
- Causa: o piloto começa e termina no meio de palavras; o transcript não.
- Correção: V61 compara com a linha de base — o mesmo trecho do corte sem motion, recortado igual (0,0 %).
- Fase: piloto.

**40. Autorização de imagens lida pelo número errado**
- Sintoma: a trava de crédito comparava as imagens geradas com o número da autorização (#1), não com a quantidade.
- Causa: `.autorizado.json` guarda `n` (ordem) e `n_imagens` (quantidade).
- Correção: a trava lê `n_imagens`.
- Fase: F5, construção da skill.

**41. Dois jobs gravando o manifest ao mesmo tempo corrompem o JSON**
- Sintoma: `JSONDecodeError: Extra data` no `run-manifest.json`; Diretor e Leigo lançados juntos morrem.
- Causa: `gravar_json` usava um `.tmp` de nome fixo; os dois processos escreviam no mesmo arquivo.
- Correção: temporário com nome próprio (`mkstemp`) e `trava_manifest` (flock) em volta de ler→mudar→gravar nos jobs.
- Fase: F2 t4.

**42. Palavra confirmada pelo usuário não mudava a legenda**
- Sintoma: "palavras ok" gravado, mas `palavras_corte.json`, SRT e motion seguiam com "Cloud Code", "Antropic".
- Causa: `confirmar` só marcava a pendência.
- Correção: `di portao confirmar N --valor "ouvido → certo; …"` grava `correcoes` no manifest; `exportar` aplica (caixa e pontuação) — refaça `di exportar` e `di iniciar-motion`.
- Fase: portão F3 t3.

**43. Tirar a pedido do usuário uma frase colada na seguinte**
- Sintoma: `V17_junta_em_silencio` BLOCKER: a voz de "resto" emenda direto em "E ela faz…" (F048).
- Causa: não há silêncio medido; o corte exige silêncio.
- Correção: `"saida_no_vale": [{"apos_palavra": N, "motivo": "pedido do usuário: …"}]` em `decisoes.json` — o corte vai para o vale de energia (crossfade 20 ms, V17_relaxada HIGH) e a entrada seguinte leva o resíduo inteiro (0,30–0,35 s), senão V19 cai para 0,14 s.
- Fase: F2 t4–t5.

**44. Leigo muda de ideia entre tentativas sobre a mesma fala**
- Sintoma: "segue o perfil… segue o perfil" LOW na t4 e BLOCKER de corte na t5, com o trecho intocado.
- Causa: a regra 16 do papel (repetição não colada é jeito de falar) era só texto.
- Correção: `laudo.py` aplica a regra 16 por código (repetição de 3+ palavras não colada, na mesma linha do pacote, sem ‖ → conteúdo LOW). Regra nova sobre laudo já gravado: `di laudo reaplicar <laudo>` (o texto do Leigo fica; muda tipo, severidade e veredito, com o original em `*_do_leigo`). Nunca rode o Leigo de novo só para mudar o veredito.
- Fase: F2 t5.

**45. Pedido do usuário esgotava o teto de tentativas**
- Sintoma: "F2 já teve 3 tentativas" logo depois de abrir a tentativa pedida pelo usuário.
- Causa: as tentativas de antes do pedido contavam para o teto de 3.
- Correção: pedido de mudança do usuário abre ciclo novo; só contam as tentativas depois dele.
- Fase: F2 t5.

**46. Aviso visual escrito à mão atravessa um render novo com o tempo velho**
- Sintoma: descontinuidades das juntas 5 e 6 apontando 1,5 s fora das emendas do corte novo (Diretor C3 t4, HIGH).
- Causa: `exportar` carregava os avisos de `fonte` (laudo do Diretor) como estavam.
- Correção: o tempo sai da junta em `cortes.json`; aviso com `edl_assinatura` diferente volta com `revalidar` até o Editor reconferir o quadro na `juntas.jpg`.
- Fase: F3 t4.

**47. O pacote do Leigo trocava toda palavra "a" por "horas"**
- Sintoma: Leigo F4 do vídeo 2 lê "Em poucos segundos horas ferramenta" e reprova por palavra sobrando.
- Causa: `_troca_corte` mapeava por forma escrita a confirmação "a hora → horas" (palavra 540, "a") e aplicava em todo "a".
- Correção: F4–F7 usam o transcript do motion, que já sai corrigido; o pacote só mascara dúvida em aberto, e nunca palavra com menos de 4 letras.
- Fase: F4 t1.

**48. Laudo C4 de três vídeos com o mesmo nome**
- Sintoma: "F4_C4_diretor_t1.md já existe" — só o laudo do último vídeo entrou; o bruto dos outros foi sobrescrito.
- Causa: rubrica de um vídeo gravava sem o id no nome (nem no bruto).
- Correção: C4/D* gravam `…_t<k>_<id>.md`; o portão exige o laudo de cada vídeo (a última tentativa que valeu para ele).
- Fase: F4 t1.

**49. O kit virou elenco fixo: o mesmo cartão em toda cena**
- Sintoma: num vídeo, o cartão de algodão (A05_CARD) apoiava o objeto das 7 cenas (logo, páginas, cartões, manual, fichas, bilhete); o usuário sentiu a repetição e o Leigo leu "cartão" onde a fala dizia manual, prompt ou bilhete.
- Causa: gerar pede crédito e autorização, então o plano puxava o kit para tudo.
- Correção: `motion-vox/referencias/assets-sob-medida.md` (o herói é o objeto da fala, gerado no mesmo mundo; famílias de prompt; faixas medidas do kit), `lib/biblioteca.py` (acervo entre projetos) e os checks `E9_heroi_repetido` / `E10_sob_medida` no `di verificar-plano`, que contam também o que o `compose.py` usa.

