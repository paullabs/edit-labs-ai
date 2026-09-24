# B-roll e inserts em vídeo (Seedance, pelo Higgsfield)

Dois usos para vídeo gerado dentro de um clipe:

- **B-roll**: 3 a 5 s em tela cheia mostrando o que a pessoa está contando — a ação, o lugar, gente fazendo algo.
  É o uso comum.
- **Insert de motion**: uma ideia de motion que realmente ganha com movimento gerado (papel que vira, objeto que
  encaixa), no mundo visual do kit.

Nenhum dos dois é obrigatório em todo projeto. A composição por camadas continua preferível para interfaces reais,
logos, texto exato, gráficos e setas sincronizadas. Tudo aqui passa pelo Higgsfield: sem ele conectado, a skill
não começa (ver "Antes de começar" no `SKILL.md`).

## 1. Plano de B-roll

Escreva o plano por clipe em `00_brief/BROLL.md`, antes de gerar qualquer coisa:

| Coluna | O que vai |
| --- | --- |
| id | `NN-B1`, `NN-B2`… (clipe e ordem) |
| janela | início e fim no tempo do clipe, cortando no silêncio entre palavras |
| âncora | a palavra em que o B-roll entra |
| mostra | a ação ou o lugar, em uma frase |
| modelo e duração gerada | ver "Geração" |
| trecho usado | o pedaço do vídeo gerado que vai para o master |

**Onde colocar.**

1. Primeiro, troque cutaways paradas (foto ou recorte sem movimento) cuja fala descreve ação ou lugar. O B-roll
   entra no mesmo ponto da fala.
2. Depois, preencha os trechos longos de rosto: mais de ~4 s seguidos sem nada é o primeiro candidato.
3. Meça a cobertura de motion antes e depois (cutaway + overlay + B-roll, sem contar duas vezes o que se
   sobrepõe). A meta continua 65–75%.
4. Continua valendo **≥ 1 s de rosto entre cutaways**. Se o B-roll novo cobre o lugar de um overlay pequeno (seta,
   rótulo, foto pequena), o overlay sai.

**Quem aparece.**

- Só pessoas fictícias, sem rosto identificável: de costas, só as mãos, fora de foco, em silhueta ou ao longe.
- Nunca uma pessoa real, nem "parecida com" alguém real. Pessoa real e nomeada é foto real licenciada, como no
  resto do kit.
- Nada de texto, placa, logo ou tela legível gerados. Marca e texto entram desenhados por cima, em PIL.

## 2. Imagem primeiro, autorização de vídeo depois

1. **Imagem de partida** para cada B-roll: `gpt_image_2`, 9:16, 2k, qualidade alta. É o primeiro quadro do vídeo.
   Descreva o enquadramento, a luz e o mundo do clipe (noite, rua, escritório, bar), a ação que vai começar e
   onde fica o espaço da legenda. Gere em lote (`generate_image_batch` + `jobs_wait`), com o custo mostrado e
   aprovado antes.
2. **Folha de imagens** para o usuário, com o id, a janela e a frase de cada uma. Refaça só o que ele pedir, com
   nova autorização. Um esboço que já resolva a cena pode ser a própria imagem de partida.
3. **Proposta de vídeo**: imagens escolhidas, prompt de movimento de cada uma, modelo, duração, resolução,
   quantidade de jobs e **custo total informado pela ferramenta** (`get_cost: true` com os mesmos parâmetros).
   Não reutilize preço de uma proposta antiga.
4. **Autorização explícita** para gerar os vídeos apresentados. Silêncio, "está bom", aprovação das imagens ou
   autorização de um lote anterior não bastam. Se modelo, preço ou condições mudarem, atualize a proposta e peça
   de novo. A autorização precisa identificar qual proposta foi aceita; não exija palavra mágica se a resposta já
   for inequívoca. Pedido só de planejamento não autoriza gastar créditos.

Para um **insert de motion** o fluxo é o mesmo, mas a imagem segue o mundo do kit: papel marfim, materiais
foscos, paleta contida, acento com função. Textos, logos oficiais, prints e anotações que precisem de fidelidade
são compostos deterministicamente; fotografias e interfaces reais não viram imagens sintéticas apresentadas como
prova. Se início e fim diferirem muito, produza os dois estados para mostrar a transformação.

## 3. Direção do movimento

Escreva o prompt com: o que permanece fixo, **uma** ação principal, trajetória, velocidade, câmera, hold e saída.
Preserve objetos, materiais, proporções, luz e composição da imagem de partida. Movimento discreto funciona melhor:
câmera que se aproxima devagar, mão que pega ou entrega algo, gente que anda de costas, porta que fecha. Não
imponha estética fluida de 3D a um plano de colagem editorial.

Peça vídeo sem áudio (ou remova o áudio gerado antes da montagem): a fala original é preservada e os efeitos vêm
do fluxo `som-local.md`. Não prometa que a geração vai acertar o instante de cada palavra: gere uma ação com
margem e ajuste a janela na edição.

## 4. Geração

- **Modelos.** Seedance 2.5 onde há gente ou mão fazendo algo (é onde o 2.0 mais deforma); Seedance 2.0 para
  lugar, objeto, bicho ou multidão ao longe. Os dois aceitam a imagem aprovada no papel `start_image`. Confira os
  modelos e parâmetros disponíveis com `models_explore`.
- **Duração.** O mínimo é 4 s. Gere 4 s para trechos de até 3,5 s e 5 s acima disso; o excesso sai na edição.
- **Resolução.** Num vertical recortado de fonte 1920×1080, o rosto tem cerca de 607 px de largura efetiva: um
  B-roll em 720p já é mais nítido que ele. Só vá para 1080p se a fonte for 4K.
- **Em lote.** `generate_video_batch` e depois `jobs_wait`. Acima de alguns vídeos simultâneos a API recusa com
  429 e não cobra: reenvie o mesmo job quando abrir vaga. Uma submissão recusada não gerou nada e não é uma nova
  geração.
- **Preset no lugar do job.** O servidor pode devolver a recomendação de um preset em vez de criar o job. Se o que
  foi autorizado é o job exato, reenvie com `declined_preset_id`: o preset não é o que o usuário aprovou.
- **Resposta incerta** (timeout, erro de rede): consulte o job existente antes de tentar de novo, para não criar
  cobrança duplicada. Não troque de modelo ou provedor por conta própria.

## 5. Revisão de cada vídeo

Baixe cada vídeo para `07_assets/broll/<id>.mp4` e revise-o **inteiro**: `mvpy broll_revisar.py` monta uma tira
de 8 quadros ou mais por vídeo. Quatro quadros não aprovam movimento. Procure:

- mão ou corpo deformado, objeto flutuando, troca de cor ou de forma no fim;
- texto, placa ou logo acidental;
- **rosto de passante que ficou visível**, mesmo por menos de um segundo;
- ação que não cabe na janela.

Anote o trecho útil de cada um (`uso_video_s`). Defeito num pedaço resolve-se na edição, sem gerar de novo:

- `va` = segundo do vídeo gerado em que o beat começa (pula o trecho ruim ou faz a ação cair na âncora);
- `vel` < 1 estica um trecho curto (0,85 quase não se nota).

Se não houver trecho útil do tamanho da janela, a cena volta a ser motion ou a janela encolhe. Uma saída
reprovada ou uma falha técnica não autoriza outra geração: prepare o ajuste, mostre a nova proposta e o custo, e
peça autorização para a regeneração.

## 6. Encaixe no master: o beat de vídeo

O B-roll aprovado entra como um beat de vídeo no motor por dados (`lib/cenas_plano.py`):

```python
"M2": [dict(video="03-B1", va=0.0, vel=1.0, items=[])],            # cena inteira em vídeo
"M5": [dict(pseed=10, items=[...]),                                   # beat de desenho
       dict(at=("porta", 12.4), video="03-B2", va=0.0, items=[])],    # e depois o vídeo, em corte com flash
"B3": [dict(video="03-B3", va=1.5, vel=0.9, items=[])],               # só o trecho útil, um pouco mais lento
```

- O arquivo fica em `07_assets/broll/<id>.mp4`. Uma cena nova entra no `J` do compose com a janela do plano.
- O render passa a 24 qps dentro do beat de vídeo, a cadência do próprio vídeo. O desenho por cima (etiqueta,
  marcador, logo, cartão) continua nos 12 qps do kit. O vídeo recebe o mesmo acabamento (grão, vinheta).
- Texto e marca sobre o vídeo continuam em PIL. Sobre fundo escuro, use marcador amarelo ou etiqueta: tinta preta
  some.
- O `montar` ordena as cenas pelo início, porque o mux concatena na ordem da lista e uma cena fora de ordem
  alonga o master.
- Sempre que uma cutaway mudar de lugar, recalcule as janelas de legenda (`mvpy janelas_legenda.py`). A legenda
  cala sob o B-roll como sob qualquer cutaway. Não adiante o início de uma cutaway para cima de uma palavra que
  ainda é dita no rosto: o `captions.check` para o render ("palavra perdida"). Na dúvida, mantenha o início
  original da cena que o B-roll substitui.

## 7. Render, conferência e entrega

- Renderize numa versão nova, sem sobrescrever a anterior: `MV_VERSAO=v02 mvpy render.py` grava
  `12_master/MASTER_V_v02.mp4`; `MV_VERSAO=v02 mvpy verificar_master.py` grava `11_qa/VERIFICACAO_v02.json`. Todas
  as travas precisam dar OK.
- Confira cada B-roll dentro do master: `MV_VERSAO=v02 mvpy broll_no_master.py` monta uma folha com a entrada, o
  meio, a saída e a volta para o rosto de cada um.
- No `CREDITOS.md` da entrega, liste os B-rolls como **conteúdo gerado por IA** (o que cada um mostra, e que
  ninguém real aparece) e peça o selo de conteúdo gerado por IA nas plataformas que pedem.

## 8. Registro

Guarde no projeto, para cada geração: imagem de partida e seu hash, prompt exato, modelo, parâmetros, custo
informado, a autorização do usuário, o ID do job e a revisão (trecho útil, defeitos). Nunca registre credenciais.
Esse registro é do projeto do usuário e não vai para dentro da skill.
