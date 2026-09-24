# 12. Erros conhecidos e como evitá-los

Falhas típicas desta pipeline, com o sintoma e a regra que as evita. Ler antes de
fechar cortes.

## 12.1 Seleção e corte

| Erro | Sintoma | Regra |
| --- | --- | --- |
| Excluir bloco inteiro sem procurar janela apertada dentro | um insight curto se perde no meio de um bloco longo | procurar a janela curta dentro do bloco antes de descartá-lo |
| Deixar preâmbulo antes do número | o valor em dinheiro chega segundos depois do início | abrir **no** número |
| Tese antes do loop de curiosidade | a moral da história aparece antes da pergunta | pergunta primeiro; a moral vira payoff |
| Hook ocupando a maior parte do clipe | a frase de efeito vira o clipe inteiro | hook acima de 50% do clipe: fazer linear |
| Truncar a última palavra | a frase termina cortada no meio da palavra | verificar borda com `silencedetect` |
| Abrir em interjeição ("Uhum") | o corte começa na reação de quem ouve, não na frase forte | mover o in para a imagem forte |
| Publicar dois cortes, um contido no outro | dois cortes do mesmo trecho | checar contenção antes de cortar |

A checagem de borda de áudio é o que pega palavra truncada. Ela é barata e não é
opcional:

```bash
ffmpeg -i CLIPE -af "silencedetect=noise=-35dB:d=0.1" -f null -
```

## 12.2 Enquadramento vertical

### Movimento de boca sozinho escolhe a pessoa errada

Dois problemas, nesta ordem:

**ROI de tamanho variável.** `cv2` devolve a caixa do rosto com jitter de 1–2px
frame a frame. Comparar o ROI da boca por igualdade de shape antes do diff faz a
comparação falhar quase sempre, e o motion fica `0.00` justamente para o rosto que
mais aparece — o locutor principal. Sintoma: motion média exatamente 0.00 num track
com centenas de detecções. **Redimensione o ROI para um tamanho fixo antes de
comparar.**

**Motion engana mesmo com o ROI certo.** Num monólogo, o ouvinte passivo pode
mostrar motion médio **maior** que o de quem fala o tempo inteiro — ajeita a mão
perto do rosto, mastiga, reage. Motion puro centraliza o crop na pessoa errada.

O que `scripts/active_speaker.py` faz em vez disso: **correlação entre movimento de
boca e energia do áudio**, com histerese para não ficar pingando. Correlação separa
locutor real de ouvinte inquieto; motion sozinho não.

### Nunca escolher pelo maior rosto

Em plano aberto, quem está mais perto da câmera tem o maior rosto e frequentemente
não é quem fala. O critério é a correlação audiovisual, nunca a área.

### A câmera do bruto zooma dentro do próprio corte

Um punch-in contínuo da câmera faz o grupo crescer no quadro ao longo do corte.
Crop fixo, mesmo bem centrado, corta gente na borda na parte final.

**Antes de decidir se o crop pode ser estático, olhe o span por bucket de tempo.**
Se a largura necessária varia mais de ~25% entre buckets, faça o enquadramento em
subsegmentos — que é exatamente o que `autoframe` produz.

### Rosto pequeno não detecta em passe único

Num plano aberto 1920px com 2–3 pessoas, cada rosto vira ~12px depois do resize
interno de um detector SSD — confiança abaixo de 0.2, erra quase tudo. O YuNet do
pacote já trabalha em resolução própria, mas quando for necessário cair para um
detector SSD, fatie o frame em tiras verticais sobrepostas e amplie 2× antes de
detectar, somando as coordenadas de volta e removendo duplicata por proximidade de
centro.

### Amostrar, não processar frame a frame

2–5 fps já captura movimento de câmera e de pessoa num corte de 30–90s. Processar
todo frame é caro e não muda a decisão de crop.

### Tracks fragmentados competem consigo mesmos

O tracker por vizinho mais próximo cria um track novo toda vez que perde e
reencontra um rosto (oclusão, ângulo). Agrupe tracks cujo `cx` médio fique a menos
de ~220px um do outro **antes** de qualquer scoring, senão a mesma pessoa disputa
contra si mesma e o score se dilui.

## 12.3 Ambiente

| Erro | Sintoma | Regra |
| --- | --- | --- |
| `pip install opencv-contrib-python` sem versão | pode instalar o 5.0.0, que vem sem `readNetFromCaffe` e sem haarcascades | pinar `==4.10.0.84` |
| Usar `mediapipe` no macOS | `Check failed: service_ Service is unavailable` no `DrishtiMetalHelper`, mesmo com `delegate=CPU` | usar o detector do OpenCV |
| Testar substring `"ass"` nos filtros do ffmpeg | casa com `lowpass`, `highpass`, `bass`, `allpass`, `bandpass` — falso positivo | casar por palavra inteira (é o que `preflight.py` faz) |
| `-c copy` para cortar | corta no keyframe errado, in/out não bate com o transcript | sempre recodificar |
| Rodar `init` sem `--workspace` | a run vai parar dentro da pasta do plugin e some da vista | apontar para a pasta do projeto |

## 12.4 Regras do motor que não podem regredir

| Regra | Se quebrar |
| --- | --- |
| `autoframe` lê o vídeo de `video_path` no manifest e exige `11-edit-plans.json`; sem o plano, sai com erro explícito mandando rodar o Edit Director antes | traceback cru, ou "Run sem vídeo" com vídeo presente |
| `autoframe` reescreve só `crop_anchor_x` e `zoom` por subsegmento e herda todo campo editorial do segmento de origem | `layout` e `framing_reason` do Edit Director somem |
| `framing.py` importa `active_speaker` como pacote, com fallback | quebra conforme o diretório de execução |
| VTT do YouTube tem parser próprio: palavra por palavra, dedupe da cue rolante por sufixo, `>>` como troca de locutor | pelo parser genérico de SRT, o **timing por palavra se perde** e o texto sai triplicado |
| Não sobrepor cues tem prioridade sobre a duração mínima da cue; cue curta é aceitável | `verify-output` reprova com `srt_entries_overlap_or_out_of_order` |
| Texto no início da cue sem timestamp próprio é distribuído no intervalo até a primeira palavra cronometrada | várias palavras no mesmo instante e legenda sobreposta adiante |

`tests/test_vtt_e_legenda.py` e `tests/test_layout_cover.py` cobrem o parser de
VTT, as regras de cue e o layout único.

## 12.5 Ambientes comuns no macOS

| Fato | Consequência |
| --- | --- |
| em muitos Macs, o `python3` do PATH é o 3.9 do sistema; o pacote exige 3.10+ | por isso existe o lanchador `vch` e a venv própria da skill |
| o `ffmpeg` do Homebrew pode vir **sem libass** | aí queimar legenda com o filtro `ass` é impossível; `make_captioned_version` fica desligado, e a motion-vox queima por conta própria via Pillow + `overlay` |

## 12.6 Nada decodifica o vídeo inteiro antes da seleção

Gerar o índice visual do vídeo inteiro decodifica o arquivo **duas vezes** (frames
periódicos a cada 5s + detecção de cena). Num vídeo longo isso trava a run antes
mesmo do Context Mapper ou do Clip Hunter rodarem — e nada disso é necessário para
a seleção, que roda inteira em cima do transcript. Vale também quando o usuário só
quer os momentos e já trouxe o transcript com timestamps.

Por isso:

- `prepare` não gera índice visual: grava `03-visual-index.json` como placeholder
  adiado, com aviso explícito;
- `vch visual-index --run <dir> --windows "start-end,..."` gera o índice **só nas
  janelas dos candidatos já escolhidos**, depois da seleção.
  `extract_visual_index()` aceita `start_seconds`/`duration_seconds` e faz seek
  com `-ss` antes do `-i`, sem decodificar o resto do arquivo;
- `vch prepare --visual-index` indexa o vídeo inteiro, para quem precisar disso
  de propósito.

Regra geral: **nenhum script do pacote decodifica o vídeo inteiro antes da fase de
seleção.** Um passo novo antes do Clip Hunter que toque no arquivo de vídeo (não só
no transcript) está na ordem errada.
