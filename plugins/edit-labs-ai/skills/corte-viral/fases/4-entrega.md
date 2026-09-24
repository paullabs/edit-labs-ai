# Fase 4 — ENTREGA

> Verificar, empacotar e entregar num caminho que o usuário ache. Nenhum
> documento novo a carregar.

---

## 1. Verificação automática

```bash
vch verify-output --run <run-dir>
vch validate-artifact --run <run-dir> --file 16-output-verification.json
```

Se `16-output-verification.json` voltar `valid: false`, **não declare sucesso.**

## 2. Verificação que o script não faz

`verify-output` checa resolução, duração, frame preto, silêncio e tamanho. O que
ele **não** vê, e você precisa olhar:

```bash
# borda de áudio: tem que haver silêncio nas pontas
ffmpeg -i CLIPE -af "silencedetect=noise=-35dB:d=0.1" -f null -

# primeiro e último frame, de verdade
ffmpeg -ss 0.05 -i CLIPE -frames:v 1 ini.jpg
ffmpeg -ss $(DUR-0.2) -i CLIPE -frames:v 1 fim.jpg
```

É esta checagem que pega a última palavra truncada. **Olhe os frames.** Não
presuma.

## 3. O que sai, por clipe

| Arquivo | O que é |
| --- | --- |
| `clip-vertical.mp4` | **o entregável** — 1080×1920, sem legenda queimada |
| `clip-clean.mp4` | idêntico ao anterior enquanto a queima estiver desligada |
| `captions.srt` / `.ass` | decupagem do clipe, timing por palavra |
| `transcript.txt` | fala reconstruída do clipe |
| `edit-plan.json` | layout, anchor, zoom e ordem dos segmentos |
| `metadata.json` | scores, eventos, segmentos, sha256 |
| `editor-notes.md` | o que o editor precisa saber |

Organizado por `primary_context`, em `<workspace>/<run-id>/output/`.

## 4. Entregue num caminho que ele ache

A pasta da run tem nome de run e numeração de artefato: serve ao pipeline, não
a quem vai publicar. **Copie os verticais aprovados para uma pasta de entrega
com nome descritivo** e abra no Finder:

```bash
mkdir -p <PROJETO>/clipes-verticais
cp <run-dir>/output/final-clips/*/*/clip-vertical.mp4 <PROJETO>/clipes-verticais/
# renomeie cada um pelo slug do clipe, não deixe todos "clip-vertical.mp4"
open <PROJETO>/clipes-verticais
```

Dê ao usuário **esse** caminho, não o interno da run. Um entregável que ele não
acha é um entregável que não foi entregue.

## 5. Condição de conclusão

Só declare sucesso quando:

- schemas válidos;
- nenhum clipe aprovado com hard fail;
- todos os arquivos exigidos pelo modo existirem;
- durações renderizadas dentro da tolerância;
- Quality Gate pós-render válido;
- o relatório separar aprovado, rebuild, duplicate, long clip e rejeitado;
- cada clipe aprovado tiver promessa clara e payoff verificável.

## 6. Auto-rejeição — reportar sempre

Termine listando o que **você mesmo** reprovaria. Lista vazia = não olhou.

- [ ] Algum corte abre em conector?
- [ ] Algum trunca palavra?
- [ ] Algum passa de 90s sem tentativa de versão curta?
- [ ] Dois cortes com >30% em comum, ou um contido no outro?
- [ ] Hook >50% do clipe (devia ser linear)?
- [ ] Payoff cortado antes da reação?
- [ ] Corte imediatamente antes de recurso visual do bruto?
- [ ] Alguma tela dividida, ou rosto cortado na borda?
- [ ] Reposicionamento de crop no meio de uma palavra?
- [ ] `method` declarado diferente do que foi realmente usado?

## 7. Passagem para a motion-vox

```text
output/final-clips/<contexto>/<slug>/
├── clip-vertical.mp4   →  o clipe que a motion-vox recebe
└── captions.srt/.ass   →  o timing por palavra que ancora cada motion
```

Ela queima a legenda e insere o motion no mesmo passe, sem tocar no áudio.

Para publicar um clipe **sem** motion, ligue `make_captioned_version: true` em
`config/default.yaml` e rode `render` de novo: aí sim esta skill queima a
legenda padrão do pacote.
