# Regras de produção do Edit Labs AI

Valem para **todos os estilos** do plugin. Cada skill traz só o que é específico dela e aponta para cá.
Uma skill pode declarar **exceções explícitas** do próprio estilo (com o motivo); fora delas, vale este arquivo.

## 1. Conversa com o usuário: pouco e fácil

1. **No máximo 4 perguntas no começo**, todas de múltipla escolha, com a opção recomendada em primeiro e um
   "outro" livre. Nunca peça para o usuário escrever especificação técnica.
2. **O que já foi respondido não se pergunta de novo.** Guarde as respostas na régua do projeto
   (`memoria/regua.yaml` da `decupagem-inteligente` serve de modelo) e reaproveite.
3. **Portões curtos.** Em cada portão, mostre o resultado (quadro, prancha, preview) e faça **uma** pergunta:
   aprovar, ajustar ou trocar. Sem relatório longo.
4. **Decida o que é técnico.** Fps, codec, nível de som e margem são decisão sua; pergunte só o que é gosto ou
   custo.
5. **Valide o estilo antes do vídeo inteiro.** Mostre 1 quadro-chave (ou um plano de 3 s) no estilo final e só
   então monte o resto. Corrigir no começo custa um quadro; no fim, o vídeo todo.

## 2. Gancho e roteiro

- **Ofereça 5 ganchos de uma linha** para o usuário escolher antes de pesquisar.
- O gancho é um **caso real e absurdo na 1ª frase**, em até ~14 palavras. Gancho de voz e gancho de imagem
  juntos nos primeiros 3 s. Teste: os 3 primeiros segundos sem som ainda prendem?
- Depois do gancho, **uma pergunta que fica martelando** ("Como é que…?"), e só então o contexto, curto e direto.
- Formatos que funcionam: "E se…?" e "Níveis" (abre pelo caso mais absurdo; 3–4 níveis).
- Todo número tem fonte (2 fontes ou a primária) e vem com uma referência do dia a dia.
- Escreva como se fala: frases curtas, sem enfeite, sem cara de texto gerado.

## 3. Ordem da produção

1. Pergunta e gancho → 2. roteiro com fontes → 3. estilo (um principal e no máximo um de apoio) → 4. quadro-chave
aprovado → 5. peças e assets → 6. cena/motion/B-roll → 7. quadros de conferência → 8. voz e decupagem (se houver)
→ 9. som → 10. **legenda e créditos por último** → 11. render e verificação.

**A legenda entra sempre por último.** Ela depende do corte final da fala, das cutaways e do motion; qualquer
mudança anterior obriga a recalcular as janelas. Nunca queime legenda antes de motion, B-roll e som estarem
fechados.

## 4. Texto na tela

- Legenda de fala depende do estilo: os de colagem narrada (camadas, história, arquivo) vão **sem legenda**, só
  imagem e voz; cortes de podcast e o explicador Vox usam legenda. Créditos de 2,3 s no fim, em todos.
- Onde houver texto: no máximo **1 rótulo curto** (1–2 palavras, preso ao objeto) e **1 número** por plano.
- Corpo mínimo na tela: 50–58 px num quadro 1080×1920. Nada pequeno.
- Texto sobre fundo ocupado vai numa tira de papel. Texto entra **depois** da imagem que ele explica.
- Ao tirar um texto, dê ao olho um gesto no lugar (uma seta, um círculo de caneta, um objeto que acende).
- Série "só imagem e voz": nem rótulo nem número; a exceção precisa estar declarada na skill do estilo.

## 5. Composição (vertical 1080×1920)

- **Margem segura do Reels/TikTok/Shorts:** x 80–960, y 260–1420. Confira com o verificador antes do render.
- **Uma coisa por vez:** um objeto grande (≥ 600 px) e um mecanismo por plano. Objeto minúsculo é erro.
- O olho já está onde a próxima ação começa. A camada de baixo tem que ser mais interessante que a de cima.
- O vertical nunca divide a tela: um crop só, em quem fala.
- **Mapa e comparação:** um mundo só, com a câmera viajando por ele; alfinete numerado e o painel brota dele;
  "o dobro" vira uma pilha-fantasma sobre a menor; o rótulo vale por frase.

## 6. Material

- **Foto real recortada ou 3D próprio "papelizado".** Clip-art vetorial desenhado em código fica amador.
- **Não misture fontes visuais sem um objeto central em camadas** (silhueta + fotos geradas + desenhos soltos =
  colagem sem identidade). Escolha o material do vídeo e mantenha.
- Objeto com volume vira modelo 3D renderizado em **camadas registradas** (mesma câmera, mesmos px/m). Imagem
  chapada atrás de imagem chapada é slide.
- **Pessoa real e nomeada: só foto real licenciada.** Nunca gere nem "recrie" rosto de alguém real. Pessoa
  anônima pode ser gerada, de preferência sem rosto.
- Imagem que falta (textura, objeto, paisagem): gere no Higgsfield com fundo transparente em vez de recortar foto
  à mão. Textura natural (gelo, água, pedra) se pede como **fotografia real**, não como ilustração.
- **Toda imagem tem origem e licença anotadas** (`CREDITOS.md` do projeto) e entra nos créditos quando a licença
  pede.

## 7. Movimento

- Câmera com intenção: deriva lenta, ou parada de propósito enquanto a ação acontece no quadro; giro de zoom de
  8–12 quadros entre planos; tremor só em impacto. Nada de zoom de 0,3 s nem câmera que vai e volta.
- 2 a 4 eventos por frase da narração. Plano parado por mais de ~2 s sem nada acontecendo cansa.
- Boil lento (3,5 trocas/s, ≤ 1 px na tela). Desenho a 12–14 qps; objetos 3D girando a 7 qps.
- Fecha montando: o que saiu volta ao lugar, em ordem inversa.

## 8. Voz, decupagem e som

- Voz: ofereça **3 amostras** e deixe escolher. Gerar voz gasta crédito: só com "pode" explícito.
- Assunto pesado (guerra, economia, polêmica) pede **voz grave de estúdio**, tom de documentário; assunto leve, voz
  natural de conversa.
- Transcrição palavra a palavra (faster-whisper). Cada evento cai na palavra que o dispara.
- **Com voz:** voz −16 LUFS; trilha ~18 dB abaixo com ducking; efeitos 15–19 dB abaixo da voz; master −14 LUFS,
  pico ≤ −1,2 dBTP.
- **Sem voz:** master ≈ −20 LUFS; efeito no máximo +3 a +6 dB acima da música; o carimbo cai na batida da trilha.
- Um efeito por ação, cada ocorrência diferente. Traço de caneta = som contínuo, não clique.
- Música e efeitos de bancos com licença que proíbe redistribuir (Mixkit, Artlist e afins) nunca vão junto com o
  plugin nem com o projeto compartilhado: cite o link.
- Quem gera o som mede, mas não escuta: declare a escuta humana como pendente.

## 9. Crédito, custo e dados

- **Gastar crédito ou baixar arquivo só com "pode" explícito**, mostrando custo, tamanho e origem antes.
  "Continue", "segue" ou "cria" **não** autorizam gasto: pergunte com o valor.
- Imagem aprovada não autoriza vídeo: cada geração tem proposta e autorização próprias.
- Nunca apague: o que sai vai para `_removidos/`.
- O projeto do usuário fica na pasta dele. Nada de dados pessoais em arquivos que possam ser compartilhados.

## 10. Qualidade antes de entregar

- Conferir a figura (lascas, buracos, cortes) antes de gerar o vídeo.
- Folha de quadros a cada 1,5 s respondendo: o espectador entende o que vê? há algo estranho? algo pequeno demais?
  algo cortado na margem? o plano tem ação? a ordem conta a história?
- Erro encontrado vira linha na tabela "causa → regra → como conferir" do projeto.

## 11. Design de quadro

O detalhe, com números, fonte de cada regra e limites, está em
`${CLAUDE_PLUGIN_ROOT}/referencias/fichas-de-estilo/regras-de-design.md`. O resumo:

- **"Poluído" é peso igual em tudo**, não "coisa demais". Um sujeito nítido e colorido por plano; o resto cinza,
  desaturado ou desfocado; no máximo 3 cores vivas.
- **Texto:** até 2 por plano, até 3 palavras, sempre preso a um objeto (etiqueta, fita, placa, papel). Maiúscula de
  36–48 px em 1080 de largura (mínimo 32). Três papéis de fonte: serifa pesada, grotesca pesada, manuscrito em caixa
  alta. Palavra gigante só como camada entre o fundo e o sujeito.
- **Margem:** texto, número e rosto dentro da zona segura; papel, fita e objetos de primeiro plano podem sangrar.
- **Camadas:** fundo em cinza de baixo contraste, sujeito nítido, primeiro plano desfocado e cortado pela borda;
  sombra curta sempre da mesma direção; paralaxe; troca por camada, não por corte seco.
- **Conferir por quadro, a olho:** "tem fundo, sujeito e primeiro plano? quantos textos? quantas cores vivas?"
