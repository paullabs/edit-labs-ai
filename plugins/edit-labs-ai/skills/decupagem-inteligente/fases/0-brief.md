# F0 BRIEF

**Entrada obrigatória:** o caminho do bruto (ou a pasta com a sequência da câmera, ex. CLIP0001 + CLIP0002).
**Saída:** pasta do projeto `<bruto>-decupagem/`, criada **na pasta onde o Claude Code foi aberto**, com `run-manifest.json`, `ESTADO.md`, `config.yaml`, `DIARIO.md`, `00_fonte/`; linha na lista de projetos do usuário (`$EDITLABS_DATA/decupagem-inteligente/projetos.json`); leitura (F1) lançada em segundo plano.
**Quem revisa:** ninguém. É a única fase sem laudo. Portão do usuário, uma vez.

## Passos

1. **Instalação.** `di verificar`. Se faltar ambiente ("ainda não foi preparado"): rode `editlabs-setup` ("preparando; o modelo do Whisper tem 1,5 GB, leva uns minutos"). Erro vira mensagem em português com o comando pronto para colar.
2. **Host e gerador.** Você descobre o host pela ferramenta que tem, não por variável de ambiente:
   - Claude Code com MCP de imagem (Higgsfield) → `--host claude --gerador higgsfield`;
   - sem gerador na sessão → `--gerador nenhum` (o corte roda igual; na F5 o usuário conecta o Higgsfield ou manda as imagens).
3. **Preparar.** Rode e volte na hora (a leitura segue em segundo plano):
   ```
   di preparar "<BRUTO>" --host claude --gerador higgsfield
   ```
   Ele sonda com ffprobe, junta sequência de câmera, extrai o áudio a 16 kHz, cria o projeto e lança a leitura. A transcrição espera até 90 s pelo glossário.
4. **Mensagem única ao usuário**, literal, no formato abaixo: no máximo 2 perguntas, de múltipla escolha, com o padrão marcado. Antes de montar, confira a régua (`di portao status` mostra `respostas[]`; `di preparar` já herda a saída da régua do usuário): **o que já foi respondido não entra na mensagem.** Nada de trabalho pesado antes dela.
5. **Resposta chegou → grave ANTES de qualquer outra coisa:**
   ```
   di portao responder --pergunta "Saída: vertical, horizontal ou as duas?" --resposta "<literal>" --chave saida
   di portao responder --pergunta "Nomes próprios que aparecem na fala?" --resposta "<literal>" --chave glossario
   ```
   "vai" sozinho = padrões assumidos; grave o padrão por extenso (`--resposta "as duas (padrão)"`, `--resposta "nenhum (padrão)"`).
   A saída respondida vai também para a régua do usuário: o próximo projeto não pergunta de novo (use `--so-projeto` se ele disser que é só desta vez).
   "vai até o fim" / "só o corte" → `--chave modo --resposta ate_o_fim|so_corte`.
6. `di portao status` e siga para `fases/1-leitura.md`.

## Mensagem de F0 (formato fixo)

```
F0 BRIEF · tentativa 1 de 3 · aprovado até: nada · modo: portoes
Feito: recebi <arquivo> · <duração> · <resolução> · <fps> quadros por segundo · <n> faixa(s) de áudio · pronto para cortar. Kit de motion encontrado. Gerador de imagem: <Higgsfield | nenhum nesta sessão>. Tempo estimado até o corte: ~<N> min.
Onde: <pasta do projeto>
Vou: ler → marcar → cortar (paro: você vê o corte) → plano de motion (paro: você aprova) → motion → legenda por último → vídeo completo (paro).
Com "vai até o fim" paro 2 vezes: corte e entrega. "Só o corte": corte e entrega, sem motion.
Responda com as letras (ou só "vai" e assumo os padrões):
  1. Saída? (a) as duas — padrão · (b) só vertical 9:16 · (c) só horizontal 16:9
  2. Nomes próprios na fala (marcas, pessoas, ferramentas)? (a) nenhum — padrão · (b) escreva-os separados por vírgula
Já extraí o áudio. A transcrição começa quando você responder ou em 90 s.
```

Variantes:
- Fonte já 9:16, ou saída já respondida na régua do usuário: sem o item 1 (diga na linha "Feito": "saída: <V|H|as duas>, como nos outros projetos").
- Podcast com um áudio só: item a mais, "tem uma faixa de áudio por pessoa?". Duas ou mais faixas no ffprobe: caminho multitrack, sem pergunta.
- F0 **não** pergunta solo × podcast. O que a leitura achar é declarado no portão F3 ("achei 1 voz, tratei como solo").

## Não faça

- Não olhe frame nenhum. F0 é texto e áudio.
- Não pergunte régua de motion aqui. Ela é perguntada uma vez, no portão do corte (F3), e só o que ainda não estiver na régua do usuário nem em `respostas[]`.
- Não espere a transcrição terminar para mandar a mensagem.

## Auto-rejeição de F0

- Mandei mais de uma mensagem com perguntas?
- Perguntei algo que já estava em `respostas[]` ou na régua do usuário?
- Alguma pergunta não era de múltipla escolha, ou veio sem o padrão marcado?
- Trabalhei antes de gravar a resposta do usuário?

## Checklist de saída

```
[ ] projeto criado na pasta do usuário e na lista de projetos ($EDITLABS_DATA/decupagem-inteligente/projetos.json)
[ ] respostas gravadas (padrão por extenso quando foi "vai") com di portao responder
[ ] leitura rodando ou pronta (di portao status)
[ ] DIARIO #1 com as respostas
```
