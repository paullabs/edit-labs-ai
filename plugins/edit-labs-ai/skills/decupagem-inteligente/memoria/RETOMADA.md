# RETOMADA — faça isto antes de qualquer outra ação

Este arquivo é o **procedimento** de retomada; não guarda projeto nenhum. A lista de projetos do usuário mora fora
do plugin, em `$EDITLABS_DATA/decupagem-inteligente/projetos.json` (padrão `~/.local/share/edit-labs-ai/…`),
escrita por `di preparar` e `di portao` (caminho, bruto, fase, data, estado). O `memoria/projetos.json` do
plugin é só o modelo vazio desse arquivo.

1. **Ache o projeto.** Caminho dado pelo usuário → use. Sem caminho → pasta atual (ou acima) com
   `run-manifest.json`; senão a lista de projetos do usuário. Um projeto ativo → use. Vários → mostre os 3 mais
   recentes com a fase e pergunte SÓ "qual? (a) … (b) … (c) …". Nenhum → projeto novo: `fases/0-brief.md`.
2. **Rode `di portao status --projeto <pasta>`.** Leia `ESTADO.md` inteiro. Se o comando falhar (ambiente
   quebrado: rode `editlabs-setup`), leia `ESTADO.md` direto e diga que o estado pode estar defasado. Não leia
   mais nada ainda: nem DIARIO, nem laudos, nem transcript.
3. **Responda ao usuário com a linha de estado** antes de qualquer trabalho, e o próximo passo na linha seguinte:
   `F4 PLANO · tentativa 2 de 3 · aprovado até: F3 (usuário, 10/03 21:14) · modo: portoes`
   `Próximo: reescrever o plano (DIARIO #4).`
4. **Carregue só `fases/<N>-*.md` da fase atual.** Nada de outra fase.
5. **Não refaça nada marcado ✓.** Aprovado é congelado. Se o usuário pedir para mexer em algo aprovado:
   primeiro uma entrada DECISÃO no DIARIO (`di diario --tipo DECISAO --texto "…"`), depois a mudança vira versão
   nova (`corte_v02`, plano t3) e o portão daquela fase reabre. Nunca edite a versão aprovada.
6. **Antes de perguntar qualquer coisa, procure em `respostas[]`** (o ESTADO mostra) **e na régua** (modelo
   `memoria/regua.yaml` + respostas do usuário em `$EDITLABS_DATA/decupagem-inteligente/regua.yaml`).
   Está lá → use. Não pergunte de novo, nem "só para confirmar".
7. **Mensagem de portão sem resposta** (`laudos/PORTAO_F<N>_t<k>.md`) → repita a pergunta tal qual e espere.
   A resposta chegou → `di portao responder` / `fechar` ANTES de qualquer trabalho.
   Tentativa `em_curso` → continue ELA; não abra outra. Se não sabe onde parou, leia a última entrada
   TENTATIVA do DIARIO e os laudos dessa tentativa (só eles).
8. **Job `rodando` em `jobs{}`** → espere com `run_in_background` + `di portao status`; nunca relance.
   `erro` → leia o log apontado (`00_fonte/_log/<job>.log`) e refaça só aquele comando.
   Cena de motion sem `.done` → re-renderize só ela.
9. **Pendência aberta em `pendencias[]` continua valendo:** palavra ambígua não vira legenda nem foto real
   até o usuário confirmar.
10. **Onde parar** é a tabela do `SKILL.md` conforme `modo`; não interprete o modo.
11. **Nunca edite `ESTADO.md` à mão.** Nunca use a memória do host para saber a fase, o que foi aprovado
    ou o que o usuário respondeu: o manifest do projeto é a única verdade.
