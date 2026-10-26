# Receitas por assunto

Cada receita: **o objeto único**, **as camadas na ordem em que saem** (e voltam ao contrário), **o que vira 3D**, **onde
achar material real** e **o que o rótulo nomeia** (1–2 palavras). Números, só com fonte conferida no dia. Nada de
texto de fala embaixo; rótulo preso ao objeto.

## Medicina e anatomia (a referência: o manequim de 1890)
- **Objeto único:** o corpo (ou a parte: garganta, ouvido, mão, crânio). Nunca troca de figura.
- **Camadas:** pele → músculo → ossos/órgãos → vasos e nervos; cada uma sai com `levanta`/`descasca`/`aba`/`janela`.
- **3D:** corte sagital e interior que o boneco não tem (via aérea, ouvido, junta, líquor) renderizados do Z-Anatomy ou
  BodyParts3D no mesmo enquadramento ortográfico; peça que o atlas não tem vira modelo próprio, declarado no crédito.
- **Material real:** Wellcome Collection (o manequim de 1890: 12 fotos do mesmo boneco), Witkowski, Albinus, Gray,
  pranchas com abas (`FONTES_PRANCHAS.md`). Pessoas reais só de arquivo; braço/mão gerado só a partir da própria foto, e
  declarado.
- **A ação mora na figura:** ar em bolinhas pelo canal, a bolha na junta, o líquido em volta do órgão; o corpo
  "responde" ao que a voz diz.
- **Rótulo:** só o nome da estrutura quando precisa. Série "só imagem e voz": nenhum texto.

## Geologia, petróleo e pré-sal
- **Objeto único:** o bloco geológico em corte (modelo próprio `modelos/presal_blender.py`) com a plataforma em cima.
  Exemplo pronto da descida: `exemplos/cena_subsolo.py` (`preparar.py subsolo`); lugares no mapa com alfinete e painel:
  `exemplos/cena_mapa.py`.
- **Camadas (descendo):** mar → pós-sal (areia, folhelho, marga) → sal → reservatório → óleo na crista → embasamento.
  A câmera DESCE junto com a sonda (um rótulo por vez); o óleo sobe pelo cano.
- **3D:** o bloco, o petroleiro em corte (casco, tanques, carga que enche; `modelos/objetos_blender.py`), a maquete da
  refinaria, moedas e maços.
- **Material real:** foto da plataforma (Wikimedia, com crédito), foto de refinaria, mapa Natural Earth.
- **Rótulos:** MAR, PÓS-SAL, SAL, PRÉ-SAL, PETRÓLEO. Espessuras do bloco são esquemáticas: declarar.

## Refinaria, usina e infraestrutura
- **Objeto único:** a maquete da instalação (refinaria, hidrelétrica, termelétrica, nuclear, estação de tratamento).
- **Camadas:** terreno e fundação → estrutura e equipamento principal → tubulação/linhas → controle; **o que está em obra
  vira andaime** (a mesma peça em estrutura) e **sobe aos poucos**.
- **3D:** a maquete inteira (`modelos/refinaria_blender.py`: `base`, `trem1`, `trem2`, `andaime` como camadas
  registradas); cortes que mostram o caminho do fluido ou da energia, com a gota/partícula andando por dentro.
- **Material real:** fotos aéreas (Wikimedia, órgãos públicos), plantas e cortes (Library of Congress HAER).
- **Rótulos:** nome do lugar ou do equipamento, 1 número em carimbo.

## Terra, planetas e geologia
- **Objeto único:** o globo (ou fatia). Camadas: crosta → manto → núcleo externo → núcleo interno; atmosfera por cima.
- **3D:** casca por casca (`exemplos/terra_blender.py`, sem licença de terceiros), a fatia que levanta e as cascas que
  se separam; para clima/atmosfera, camadas translúcidas empilhadas.
- **Material real:** NASA (domínio público), USGS (cortes), Natural Earth (contornos). Escala sempre explícita (km).

## Arquitetura, construção e planejamento
- **Objeto único:** a edificação (ou o quarteirão/cidade). Camadas na ordem da obra: terreno → fundação → estrutura →
  vedação/fachada → instalações → acabamento; para planejamento: lote → quadra → bairro → cidade.
- **3D:** o prédio em cortes (planta baixa que "levanta" em volume, andares que separam como explodida) e a cidade em
  blocos; foto real da obra/prédio como peça presa com fita.
- **Material real:** Library of Congress HAER/HABS (desenhos medidos), Wikimedia, plantas públicas, fotos históricas.

## Máquinas, motores e produtos
- **Objeto único:** a máquina. Camadas: carcaça → componentes → peças móveis → fluxo (ar, óleo, corrente).
- **3D:** vista explodida real (`explode`: peças que se afastam em eixo e voltam), `giro` a 7 qps quando a forma importa.
- **Material real:** patentes e manuais (Internet Archive, domínio público), fotos de oficina com licença.

## Comparações (preço, quantidade, dinheiro)
- **Objeto único:** a pilha (moedas, maços, barris) que se compara, no mesmo mundo.
- **Regras:** pilhas lado a lado na mesma escala; "o dobro" = pilha-fantasma em cima da menor; fluxo = objetos viajando
  por rotas; o painel sai quando o próximo entra. Unidade na tela = número + unidade em carimbo; fontes conferidas.
