# Roadmap do processo

- **Desenho editável**: `roadmap-processo.excalidraw` (excalidraw.com → Abrir).
- **Requisito**: Higgsfield conectado ao Claude (imagens, remoção de fundo, B-roll). Sem conta:
  https://higgsfield.ai/s/claude-opus-5-5-yt-canal-labs-RygxQf

## As sete etapas

| # | Etapa | O Claude faz | Com o quê | Você |
|---|---|---|---|---|
| 1 | Baixar | consulta, baixa vídeo H.264 + legenda automática com tempo por palavra + metadados | yt-dlp, Deno | |
| 2 | Achar | transcrição compacta → context-mapper + clip-hunter → lista com tempo e citação | corte-viral | escolhe |
| 3 | Cortar | clip-builder; borda conferida pelo ouvido (Whisper em 3 s); respiro por script; preview | ferramentas da corte-viral | aprova o preview |
| 4 | Vertical | edit-director; rosto de quem fala rastreado (YuNet) e conferido dentro do corte; um crop só, nunca tela dividida; QR da transmissão fora do quadro; render limpo | corte-viral | |
| 5 | Motion | ouvir o clipe e conferir emendas; plano frase a frase; fotos reais (Commons) e geração (Higgsfield); cenas em código ancoradas na palavra; travas por script; pranchas | motion-vox | autoriza créditos, aprova pranchas |
| 6 | B-roll | plano de B-rolls de 3–5 s; imagens de partida; vídeos Seedance; revisão de cada vídeo; beat de vídeo no motor; conferência dentro do master | motion-vox, Higgsfield | aprova imagens, autoriza vídeos |
| 7 | Fechar | legenda (correções + palavrão mascarado); render 12 fps (24 dentro do B-roll) em master do fps da fonte; verificação por conteúdo e áudio | motion-vox | publica |

## Princípios

1. A legenda automática do YouTube basta para achar e cortar: tempo por palavra, sem custo.
2. Risco não é critério do agente; a revisão é humana.
3. A borda do corte é do ouvido, não do agente: bordas propostas por agente costumam cortar fala.
4. O Whisper no arquivo inteiro inventa palavra na emenda → conferir em janela curta.
5. Nome ou palavra em dúvida vai para o usuário, com as hipóteses (ex.: a legenda automática não distingue
   "sessão" de "cessão", nem "Luís" de "Luiz").
6. A prancha esconde o tempo de leitura → trava de hold ≥ 8 quadros por script.
7. Gente da história é pessoa (fictícia gerada ou foto real); rosto real nunca gerado. No B-roll, ninguém tem o
   rosto identificável.
8. Toda fala com rosto na tela aparece na legenda; as janelas são recalculadas sempre que uma cena muda.
9. Verificar por conteúdo (mesmo quadro no mesmo instante) e áudio idêntico, não por contagem de quadros.
10. O vertical nunca divide a tela, e arte fixa da transmissão (QR, patrocínio) não entra no recorte.
11. Crédito só com autorização e com o custo informado antes; imagem aprovada não autoriza vídeo.

## Referências: de onde vêm

| Referência | Onde está |
|---|---|
| identidade (paleta, fontes, sombras, zonas seguras) | `motion-vox/IDENTIDADE.md`, `referencias/identidade.md` |
| Style Bible em números (massa escura 10–18%, acento 3–7%, vazio 25–40%) | `lib/medir.py` |
| registros visuais (que cena para que frase) | `referencias/registros.md` |
| quadros de referência por registro | `referencias/REFERENCIAS-VISUAIS.md` — **monte os seus** (seção "Monte as suas referências") |
| legenda medida (1,7 palavra por bloco, 0,33 s, 69% da altura) | `referencias/legenda.md`, `lib/captions.py` |
| transições e armadilhas | `referencias/transicoes.md`, `referencias/armadilhas.md` |
| B-roll em vídeo (plano, geração, revisão, encaixe) | `referencias/seedance-2.5.md` |
| kit (16 objetos, fundo, fontes livres) e biblioteca de assets | `assets/`, `fontes/`, `biblioteca/` |
| provas reais | Wikimedia Commons, com licença anotada por projeto |
| seleção de cortes (regras, 12 perfis, 3 plataformas) | `corte-viral/docs/05…`, `corte-viral/config/` |
