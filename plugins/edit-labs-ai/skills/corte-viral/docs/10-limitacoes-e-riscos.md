# 10. Limitações, riscos e controles

## 10.1 Não existe detector universal de viralidade

O harness estima qualidade e adequação. O algoritmo de distribuição, audiência e contexto cultural variam. Um score alto não garante alcance.

## 10.2 “Dopamina” pode virar pseudociência

Controle: usar métricas comportamentais e linguagem de hipótese. Não afirmar que uma edição “libera dopamina”.

## 10.3 Montagem pode distorcer

Risco maior quando:

- segmentos são reordenados;
- negações são removidas;
- qualificações desaparecem;
- reação é deslocada;
- pergunta e resposta pertencem a contextos diferentes.

Controle: `truthfulness` como gate, transcript reconstruído e auditoria de causalidade.

## 10.4 Transcrição automática erra

Nomes, números e negações são críticos.

Controle:

- baixa confiança ASR gera flag;
- números-chave devem ser confirmados no áudio;
- transcript correction log;
- não aprovar hook baseado em trecho duvidoso.

## 10.5 Revisão visual é amostrada

Frames periódicos podem perder gesto rápido ou card curto.

Controle: extrair frames extras nos intervalos candidatos e revisar início, payoff e transições em maior densidade.

## 10.6 Crop automático pode cortar pessoas

O `autoframe` segue o locutor ativo e resolve a maior parte dos casos, mas continua
sendo heurístico. Limites conhecidos:

- **fala sobreposta**: com duas pessoas falando juntas a correlação fica ambígua;
- **plano aberto**: o rosto ocupa uma fração pequena do quadro; mesmo com o
  punch-in máximo (`max_zoom`, 1,45x) sobra cenário. Zoom maior degrada numa
  fonte 1080p;
- **telas no cenário**: vídeo exibido numa tela do cenário tem movimento de boca
  real e pode competir na correlação. Use `autoframe.exclude_zones` para mascarar
  a região;
- **enquadramento vertical**: o renderer centraliza no eixo Y; não há controle de
  altura do rosto;
- **quem não fala**: reação de ouvinte é conteúdo às vezes, e o autoframe vai
  ignorá-la por definição.

Controle: `--exclude-zones`, anchors manuais no edit plan, e preview antes de publicar.

## 10.7 Legenda pode aumentar carga

Texto excessivo compete com o rosto e o objeto.

Controle: chunks sintáticos, duas linhas, safe zone, palavra por palavra apenas opcional.

## 10.8 Pausas não são sempre desperdício

Controle: silêncios são candidatos à remoção, não cortes automáticos definitivos.

## 10.9 Conteúdo legal, médico ou financeiro

O clipe pode remover contexto que continha ressalvas.

Controle: classificação de risco e exigência de preservar disclaimers materialmente relevantes.

## 10.10 Direitos autorais e privacidade

O usuário é responsável por ter direito de editar e publicar vídeo, música, imagem e fala. O sistema não remove watermarks, não falsifica autorização e não busca B-roll protegido automaticamente.

## 10.11 Custo computacional

Vídeos longos geram transcript e frames extensos.

Controles:

- processamento em blocos contínuos;
- mapas hierárquicos;
- frames adaptativos;
- subagentes com contexto isolado;
- cache por checksum;
- retomada por manifest.

## 10.12 Dependências

FFmpeg e backend de transcrição não vêm no pacote. O pacote inclui scripts e instruções, não binários de terceiros.
