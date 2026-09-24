# Fase 3 — VERTICAL

> **A entrega é o 9:16 com o locutor rastreado.** Só para os clipes que o
> usuário aprovou assistindo os previews da fase 2.

**Carregue:** `config/default.yaml` e `config/platforms/<platform>.yaml`. Os
perfis em `config/profiles/` só do perfil de cada candidato — não a pasta toda.

**Subagente desta fase:** `edit-director`.

---

## 1. Direção de edição

Subagente `edit-director`, **só para os aprovados**. Produz `11-edit-plans.json`
com ordem real dos segmentos, layout e crop anchor, punch-ins motivados, cortes
e pausas removíveis, cards, chunks de legenda, mix de áudio, categoria e nome de
saída.

### Um layout só: `cover`

O vertical **nunca divide a tela**. Todo segmento é um crop 9:16 único em quem sustenta a fala, com punch-in
opcional. Em plano aberto com duas ou três pessoas, feche no locutor (zoom 1,3–1,6) em vez de mostrar a mesa
inteira. Se mesmo assim o rosto fica pequeno demais para ler expressão, marque o trecho como candidato a cutaway
(motion ou B-roll) nas notas do editor. Um plano antigo com `split` é renderizado como `cover`.

Vertical já entregue com tela dividida (layout antigo)? `cv-desdividir ENTRADA.mp4 SAIDA.mp4` põe a metade de
baixo em tela cheia, centrada no rosto, sem mexer em tempo nem áudio, com o QR code da gravação fora do
recorte quando o rosto ainda tem folga. Confira o resultado com `cv-desdividir SAIDA.mp4 --medir`: 0 trechos divididos.

Ordem de preferência do enquadramento:

1. locutor ativo rastreado (`autoframe`);
2. `crop_anchor_x` definido à mão por segmento;
3. centro, como último recurso.

## 2. Enquadramento automático por locutor ativo

```bash
vch autoframe --run <run-dir>
```

Reescreve `timeline` de cada plano com `crop_anchor_x` e `zoom` por subsegmento.
Detecta rostos com YuNet e decide **quem está falando** por correlação entre
movimento de boca e energia do áudio.

> **Em plano aberto nunca escolha o maior rosto.** Quem está mais perto da
> câmera tem o maior rosto e frequentemente não é quem fala. O critério é a
> correlação audiovisual, não a área. Movimento de boca sozinho também não
> basta: o ouvinte pode mexer mais a boca que o locutor.

Requer `opencv-contrib-python` e `numpy` (opcionais — ver `INSTALAR.md`). Sem
eles, caia para anchor por segmento e **declare** no plano que o enquadramento é
manual. Não declare `autoframe` num plano que foi ancorado à mão.

Valide antes de renderizar:

```bash
vch validate-artifact --run <run-dir> --file 11-edit-plans.json
```

Não peça B-roll externo como se já existisse. Asset ausente é `optional`.

## 3. Decupagem do respiro

A `timeline` de cada clipe é uma **lista de segmentos que o render concatena**
(`_concat_segments`). É assim que o ar morto sai: o Edit Director emite dois
segmentos que pulam a pausa, em vez de um só que a contém.

**Respiro sai por padrão; `preserve_pause` é a exceção.** Corta hesitação, "é…",
ar entre frases, gagueira e retomada. Preserva a pausa antes do payoff, a espera
da reação depois da punchline, o riso do outro, e a respiração curta dentro da
frase — cortar essa vira locução de robô.

Ponto de partida a calibrar: silêncio sem função acima de ~0,4s colapsa para
~0,15–0,2s. **Não zere.**

Cada segmento obedece à mesma regra de borda do Clip Builder: 0,2–0,3s antes da
primeira palavra, 0,3–0,5s depois da última sílaba. Vale por segmento, não só
nas pontas do clipe.

Se a soma do que saiu passar de ~15% da duração, o problema provavelmente é o
in/out — devolva ao Clip Builder em vez de costurar aqui.

> **A legenda acompanha sozinha.** `map_transcript_to_timeline` remapeia o
> timing por palavra com offset acumulado por segmento, então o `.srt` sai
> correto contra o clipe renderizado e a `motion-vox` continua ancorando motion
> no frame exato da palavra.

## 4. Finalize

Sem revisor de LLM pré-render: o usuário já aprovou assistindo o preview, e o
que é mecânico é conferido por script.

```bash
vch finalize --run <run-dir>
```

Gera `13-final-clips.json`, `14-rejected-clips.json`, `15-run-report.md` e
`output/context-index.md`.

## 5. Render

```bash
vch subtitles --run <run-dir>
vch render --run <run-dir>
```

`subtitles` roda **mesmo sem queimar legenda**: os `.srt`/`.ass` são a decupagem
por clipe, com timing por palavra, e é o que a `motion-vox` usa depois para
ancorar cada evento de motion no frame exato da palavra dita. Não pule.

## 6. Arte da transmissão fora do quadro

Transmissão de podcast costuma ter arte fixa no canto de uma das câmeras: QR code de patrocínio, Pix da live,
lettering. O recorte 9:16 do plano dessa câmera pode carregar essa arte sem ninguém perceber. Em cada vertical
renderizado:

```bash
cv-conferir-qr <vertical.mp4>
```

A ferramenta lê o vídeo em meia resolução e só confirma um trecho quando decodifica o QR em resolução cheia ou
quando ele persiste por um segundo ou mais (o detector sozinho dá falso positivo de um quadro em textura). Sai
com código 1 se achar. Trecho acusado: mude o `crop_anchor_x` daquele segmento para deixar a arte fora, com o
rosto ainda com folga, e renderize de novo. Se não houver recorte que tire a arte sem cortar o rosto, anote o
trecho como candidato a cutaway para a motion-vox.

Passe para a fase 4 para verificar e empacotar. Não declare sucesso aqui — o
render existir não é o mesmo que o render estar certo.
