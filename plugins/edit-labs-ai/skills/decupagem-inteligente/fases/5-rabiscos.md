# F5 RABISCOS

**Entrada obrigatória:** F4 fechada e a autorização de imagens (`motion/<id>/07_assets/.autorizado.json`); sem ela, `cutout.py`, `prancha.py` e `render.py --frames` recusam PNG gerado (V53b).
**Saída, por vídeo:** assets em `07_assets/raw/` e `cutout/`, `07_assets/qa/`, `compose.py` com uma `build_M#` por cena, os 4 estados por cena em V e em H (`08_images/frames/M#{,_H}_{START,MID,END,EXIT}.png`), `08_images/PRANCHA_VH.jpg` + `REVISAR.html`, `05_motion/ANCORAGEM.md`, blueprints gerados.
**Quem revisa:** primeiro a **análise** — Diretor C4 sobre o plano que o usuário aprovou, uma vez: faz sentido, cabe no tempo, cada marca tem logo, cada evento tem palavra, o crédito basta? Corrige o que ela achar e segue. Depois o Verificador (ancoragem, medir, legibilidade). **Não para no usuário.**

## Passos

1. **Assets.** Antes, `biblioteca.py buscar` (o que já existe e é o objeto dito entra com `biblioteca.py usar NOME`). Gere só o que a lista G autorizou (Higgsfield conectado ao Claude), destino `07_assets/raw/<NOME>_v1..3.png`. Logos e fotos reais baixados com a permissão do usuário vão para `07_assets/raw/` e para `07_assets/reais.json` (`{"arquivos": [...]}`), com origem e licença em `07_assets/ATRIBUICOES.md`.
2. **Recorte:** `di mv <id> cutout.py --sweep NOME` → platô → `di mv <id> cutout.py NOME …` (receita da motion-vox §4). Logo: `qlmanage` + chroma do branco, proporção intocada.
3. **D1** sobre `07_assets/qa/` (tiles, bordas, alfa): asset liso, vetorial, 3D ou com glow reprova (E1: texturizado e bonito). Regenerar = uma alteração no prompt, até 3 vezes.
4. **Compor** `compose.py`, abrindo antes o frame de referência de cada cena (coluna Referência). Regras:
   - posição em fração do quadro (`X()`, `Y()`, `U`) e layout por `ORIENT`: a mesma `build_M#` desenha V e H, com arrumação própria;
   - todo evento de `M#_EVENTS` nasce de um beat da coluna "Se mexe", no frame da palavra;
   - herói já em voo no frame 0 (evento com início negativo); hold de 8–18 frames antes da saída;
   - `boil_ctx(frame)` no topo de cada cena (Turbulent Displace leve, E2).
5. `di mv <id> --agora ancorar.py --blueprints` — qualquer FORA bloqueia (evento a > 3 frames24 da palavra, saída na sílaba, END antes do último evento).
6. Estados: `di mv <id> --saida V --agora compose.py` e `di mv <id> --saida H --agora compose.py`; prancha: `di mv <id> --agora prancha.py --ambos`.
7. Medir: `di mv <id> --agora medir.py 08_images/frames/M#_END.png` e `legibilidade.py` para texto sobre imagem.
8. Sem rodada de D2/D3/Leigo: a análise C4 já foi feita no começo da fase. Olhe a prancha você mesma contra as E-regras e corrija o que achar.
9. Sem portão: com ancoragem sem FORA e medições feitas, segue para a F6.

## Refazer (taxonomia, PLANO §6.5)

| Sintoma | Refazer = | Nunca |
| --- | --- | --- |
| D1 (asset ruim) | regenerar o asset com uma alteração | redesenhar a cena |
| não entendi em 1 s / sem dominante | trocar hierarquia | mexer em registro |
| E3/E5 (abstrato, não é o que foi dito) | trocar o objeto pela coisa de verdade | "melhorar" o abstrato |
| E6 (gente só em palavra) | pôr a pessoa: mãos, figura, foto | escrever mais |
| colisão, vazio, acento | correção localizada, medida de novo | redesenho geral |

## Auto-rejeição de F5

- Algum elemento se sobrepõe a outro sem sombra de contato (tangente)?
- O layout H é só o vertical encolhido?
- Algum texto sem o elemento que faz parte dele?

## Checklist de saída

```
[ ] ANCORAGEM sem FORA
[ ] 4 estados por cena em V e H; PRANCHA_VH.jpg; REVISAR.html
[ ] análise C4 gravada e o que ela achou corrigido
[ ] D1 sobre os assets; prancha conferida contra as E-regras
```
