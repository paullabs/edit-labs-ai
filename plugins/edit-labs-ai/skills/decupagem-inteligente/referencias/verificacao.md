# Verificação — as checagens do Verificador

Todas gravam em `laudos/F<N>_V_verificador_t<k>.json` (`source: deterministic`), com `id`, `ok`, `severidade`, `medido`, `esperado`, `detalhe` e `video`. `VERIFICACAO.md` é gerado só do JSON.

| Severidade | Efeito |
| --- | --- |
| BLOCKER | a fase não fecha (`di portao fechar` recusa); em F2 o EDL nem sai |
| HIGH | não bloqueia sozinho; o Diretor tem que responder na rubrica; laudo com HIGH aberto é REPROVADO |
| MEDIUM / LOW | vai para o laudo e a mensagem de portão |
| aviso / info | contexto para o Editor e o Diretor |

## F1 LEITURA (`preparar`, `transcrever`, `retakes`)

| id | mede | severidade |
| --- | --- | --- |
| V07_cfr, V07b_sequencia, V08_faixas | fps constante, sequência de câmera, faixas de áudio | info |
| V09_transcricao | transcript com tempo e probabilidade por palavra | BLOCKER |
| V10_ambiguas | % de palavras com `p` < 0,6 (acima de 5 % = áudio ruim) | aviso |
| V10b_alucinacao | frases com alucinação suspeita | info |
| V12_grupo_sem_tomada_limpa | grupo sem tomada completa sem filler | aviso |

## F2 DECUPAGEM (`di edl`)

| id | mede | severidade |
| --- | --- | --- |
| V14_cobertura | toda palavra mantida tem motivo | BLOCKER |
| V14b_conteudo_sem_motivo | trecho de conteúdo ≥ 1 s tirado sem motivo em `remover[]` | HIGH |
| V15_retake_no_papel | duas tomadas inteiras do mesmo grupo no `manter` | BLOCKER |
| V16_ordem | o corte volta no tempo do bruto | aviso |
| V17_junta_em_silencio | toda junta num ponto que passa na régua | BLOCKER |
| V17_relaxada | junta sem silêncio medido, com energia OK (crossfade 20 ms) | HIGH |
| V18_folga_silencio | ponto ≥ 0,06 s da borda do silêncio depois de quantizar | BLOCKER |
| V18b_vazamento | o corte pega voz de palavra que ficou de fora (depois do fim da voz mantida) | HIGH |
| V19_residuo | silêncio sobrando por junta (respiro à parte) | HIGH fora de 0,20–0,60 |
| V20_pausas_preservadas | pausa > `pausa_max_s` mantida sem função (vão do Whisper ou silêncio medido, o maior) | HIGH |
| V20c_pausa_listada_fora | pausa em `pausas_preservar` que o ponto de corte já tirou | MEDIUM |
| V20b_palavra_no_silencio | palavra mantida ≥ 50 % dentro de silêncio medido (tempo do Whisper duvidoso) | aviso |
| V21_pausas_fillers | pausas + fillers tirados > 15 % do mantido | HIGH |
| V22_ambigua_na_borda | palavra em dúvida encostada numa junta | aviso |
| V22b_abre_em_conector | o vídeo abre em conector sem "gancho" no motivo | HIGH |
| V22c_repeticao | 5 palavras repetidas em 30 s, ou 3 a ±8 de uma junta | HIGH |
| V23_frames | timeline contígua em frames inteiros | BLOCKER |

## F3 CORTE BASE (`di render`, `di verificar-corte`, `di exportar`, `di pacote-leigo`)

| id | mede | severidade |
| --- | --- | --- |
| V24_frames_segmento, V25_duracao_concat, V26_duracao | frames por segmento; duração = EDL (±1 frame) | BLOCKER |
| V27_retranscricao | WER do render × roteiro montado, com linha de base (2× a base, mín. 3 %) | HIGH |
| V28_palavras_na_junta | ±3 palavras em volta de cada emenda (Levenshtein ≤ 2, 2 de 3 por lado) | HIGH |
| V29_frase_repetida, V29b_vazamento_na_junta | frase dita duas vezes; palavra vazada na junta | HIGH |
| V30_silencio | silêncio > `pausa_max_s` fora das pausas preservadas | HIGH |
| V31_estalo | pico nos ±20 ms da junta | MEDIUM |
| V31b_nivel_na_junta | ΔRMS de voz 200 ms antes × depois ≤ 3 dB | HIGH |
| V32_quadro_preto | blackdetect | BLOCKER |
| V33_pontas | 1ª voz entre 0,15 e 0,6 s; última termina entre dur−0,8 e dur−0,2 | HIGH |
| V34_quadro_da_fonte | PSNR do quadro do corte × fonte com o mesmo crop, ≥ 35 dB | HIGH |
| V35_loudness | loudness integrado e true peak | LOW |
| V36_formato | codec, resolução, fps, áudio | BLOCKER |
| V37_pulo_de_cabeca | deslocamento do rosto na emenda | aviso |
| V37b_rosto_no_recorte | margem lateral ≥ 5 %, topo no quadro e centro do rosto acima de 0,60 H em ≥ 99 % das amostras | HIGH |
| V39_ambiguas | palavras em dúvida confirmadas pela retranscrição | info |
| V40_remap | palavras remapeadas para o relógio do corte, nenhuma cruzando borda | BLOCKER |
| V41_xml | XML com a soma dos frames do EDL | — |
| V42_pacote_cego_F<N> | pacote do Leigo sem EDL, motivo, laudo nem digest | BLOCKER |

## O que a máquina não verifica

Escuta e movimento em tempo real. Nenhum papel ouve nem assiste. Toda mensagem de portão diz: "NÃO verificado: escuta e movimento em tempo real — fica com o usuário."
