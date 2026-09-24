# 7. Legendas e áudio

## 7.1 Por que legenda é parte do conteúdo

Legenda não serve apenas a pessoas sem som. Evidência acumulada mostra benefícios de compreensão, atenção e memória; ao mesmo tempo, legenda mal segmentada ou excessiva aumenta carga cognitiva. Ver S15–S19.

O objetivo é sincronizar texto, voz e imagem, não ocupar a tela.

## 7.2 Regras de segmentação

Default para português:

- 2–6 palavras por chunk;
- máximo de 2 linhas;
- preferir uma unidade sintática por chunk;
- não separar artigo do substantivo;
- não separar preposição do complemento;
- não quebrar nome próprio;
- não deixar pontuação sozinha;
- duração mínima 0,55s;
- duração alvo 0,8–2,2s;
- evitar um único termo, salvo ênfase intencional.

A recomendação oficial do TikTok para overlays é 5–10 palavras por segundo; o harness usa esse intervalo como limite amplo e prioriza legibilidade e sintaxe. Ver S3.

## 7.3 Hierarquia

### Legenda base

Transcrição fiel.

### Ênfase

No máximo 1–3 palavras por beat, quando representam:

- número;
- contraste;
- verbo de mudança;
- conclusão;
- nome essencial.

### Card

Informação editorial separada da fala. Deve estar identificada no edit plan como `editorial_text`, nunca misturada como se fosse citação.

## 7.4 Safe zone

TikTok e Meta recomendam manter elementos-chave dentro das safe zones, pois interface, descrição, perfil e CTA podem cobrir bordas. Ver S4–S6.

Default conservador para 1080x1920:

- margem esquerda: 90 px;
- margem direita: 170 px;
- topo: 160 px;
- base: 310 px;
- baseline da legenda: aproximadamente 1380–1500 px.

Esses valores são editáveis e devem ser validados no preview real da plataforma.

## 7.5 Estilo default

- fonte do sistema, sem arquivos de fonte incluídos;
- branco com contorno escuro;
- sem caixa colorida permanente;
- tamanho adaptado à largura;
- alinhamento central;
- sem animações por caractere por padrão;
- destaque opcional com peso, não carnaval de cores.

## 7.6 Palavra por palavra

Legenda word-by-word pode funcionar para vídeos muito rápidos, mas também cria movimento visual constante e divide atenção.

Use apenas quando:

- há timestamps por palavra confiáveis;
- fala é curta;
- imagem é simples;
- o estilo foi solicitado.

Default do harness: chunks por frase curta.

## 7.7 Correção do transcript

Pode corrigir:

- pontuação;
- capitalização;
- grafia de nome confirmada;
- erro inequívoco de ASR confirmado no áudio.

Não pode:

- reescrever fala para parecer mais elegante;
- remover negação;
- alterar número;
- substituir dúvida por certeza;
- apresentar paráfrase como legenda literal.

Toda correção deve aparecer em `transcript_corrections`.

## 7.8 Mix de áudio

Default técnico:

- voz como prioridade;
- loudness alvo configurável, default aproximado de -14 LUFS;
- true peak máximo -1 dB;
- música opcional abaixo da fala;
- redução de ruído apenas quando disponível e necessária;
- sem compressor agressivo automático.

O alvo de loudness é convenção de produção, não garantia de plataforma.

## 7.9 Som ligado e som desligado

O vídeo deve funcionar com legenda sem áudio, mas não deve ser projetado como se áudio fosse irrelevante. Estudos de vídeo legendado mostram que remover som pode elevar carga e reduzir imersão, mesmo quando a compreensão permanece razoável. Ver S16.

Por isso:

- voz precisa estar clara;
- legenda precisa ser suficiente;
- música não deve carregar informação essencial;
- efeitos não devem substituir contexto.

## 7.10 Arquivos

Por clipe:

- `captions.srt` para compatibilidade;
- `captions.ass` para render com estilo;
- `caption-map.json` para auditoria;
- `clip-clean.mp4` para edição posterior;
- `clip-vertical.mp4` com burn-in.
