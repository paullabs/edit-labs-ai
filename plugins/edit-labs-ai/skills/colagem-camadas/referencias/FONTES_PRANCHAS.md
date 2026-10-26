# Fontes das pranchas em camadas

Pacote `colagem-pranchas.zip` da release (`../assets/RELEASE.md`), em
`~/.local/share/edit-labs-ai/colagem/assets/pranchas/`. Cada pasta tem as fotos, a `folha.jpg` (camadas lado a lado +
sobreposição a 50%) e o `encaixe.json` com os números; `indice.json` tem o detalhe de cada conjunto.
Ordem das camadas: de fora para dentro. Os px se referem à imagem do pacote.
Método: ORB + RANSAC (similaridade) para achar o alinhamento e ECC afim para refinar. No fundo liso, mede-se a silhueta
(IoU e distância de contorno); no papel, o resíduo do ORB.

| id | obra | ano | camadas | px | encaixe medido | licença |
|---|---|---|---|---|---|---|
| `american-manikin-1890` | American Manikin Co., *Anatomical figures with detachable parts* (corpo inteiro) | c. 1890 | 12 | 3343×6000 | **bom**: desloc. ≤ 5 px, rot. ≤ 0,08°, IoU da silhueta 0,995–0,999 | Domínio público (PDM, Wellcome) |
| `witkowski-atlas-tronco-1880` | Witkowski, *A Movable Atlas of the Human Body (neck and trunk)* | c. 1880 | 13 (1 fechada + 12 abertas) | 4000×~3530 | **bom** na série aberta (resíduo 2,3–3,0 px); **médio-bom** entre a fechada e a interna | Domínio público (RCP London / Internet Archive) |
| `witkowski-visao-cabeca` | Witkowski, *A Pictorial Manikin: Mechanism of Vision* (cabeça lateral) | c. 1880 | 9 | 4000×2988 | **bom**: resíduo 2,3–3,2 px, IoU 0,967–0,988 | Domínio público (PDM, Wellcome) |
| `witkowski-visao-olho` | idem (globo ocular frontal) | c. 1880 | 17 | 3000×4004 | **bom**: resíduo 1,8–5,5 px, IoU 0,93–0,98 | Domínio público (PDM, Wellcome) |
| `fugitiva-tabula-foeminae-inteira` | *Tabula foeminae membra demonstrans*, folha avulsa com abas | 1573 | 4 | 4992×6666 / 3840×5128 | **bom**: desloc. ≤ 6 px, resíduo 1,5–3,7 px | **CC BY 4.0** (Wellcome, via Commons) |
| `fugitiva-tabula-foeminae-detalhe` | idem (close da figura) | 1573 | 4 + 4 | 2832×4256 | **bom** na série A, **médio** na série B | **CC BY 4.0** (Wellcome, via Commons) |
| `albinus-tabulae-1747` | Albinus & Wandelaar, *Tabulae sceleti et musculorum* (Músculos I–IV + Esqueleto I) | 1747 | 5 (+2 contornos) | ~4190×6000 | **médio**: mesma pose, gravuras separadas; pede escala 1–3 %, rot. ≤ 1,4°; correlação 0,54–0,78 | Domínio público (PDM, Wellcome) |

## Observações

- **american-manikin-1890** (a referência do estilo): o melhor conjunto de corpo inteiro. O boneco foi fotografado
  parado e cada foto tem uma peça a menos: cérebro e músculos do peito, costelas, estômago e fígado, rim, coluna e
  esqueleto. A metade esquerda é sempre pele com veias (o modelo é meio a meio). Fundo cinza liso, fácil de recortar.
- **Witkowski**: abas de verdade, em litografia colorida sobre fundo preto. Varetas de madeira seguram as abas e
  aparecem nas fotos: precisam de retoque. No tronco, a parede muscular rebatida fica à esquerda e as costelas à
  direita. Ideia pronta: o olho (17 camadas reais), a córnea sai, depois o cristalino, depois a retina.
- **Folha avulsa de 1573**: a única "folha" de verdade, com título, texto e figuras laterais. As abas levantadas ficam
  presas por uma espátula branca: precisa de máscara.
- **Albinus**: o encaixe é por desenho do autor, não físico. Serve para revelar o músculo e depois o esqueleto na mesma
  pose, depois de recortar a figura do fundo e registrar (`camadas.registrar`).

## Crédito pronto

- American Manikin Co., *Anatomical figures with detachable parts*, c. 1890. Wellcome Collection. Domínio público.
- G.-J. Witkowski, *A Movable Atlas of the Human Body (neck and trunk)*, c. 1880. Royal College of Physicians, London / Internet Archive. Domínio público.
- G.-J. Witkowski, *A Pictorial Manikin, or Movable Atlas: Mechanism of Vision*, c. 1880. Wellcome Collection. Domínio público.
- *Tabula foeminae membra demonstrans*, Wittenberg, 1573. Wellcome Collection, CC BY 4.0.
- B. S. Albinus e J. Wandelaar, *Tabulae sceleti et musculorum corporis humani*, Leiden, 1747. Wellcome Collection. Domínio público.

Versão curta para a tela: "Imagens: Wellcome Collection (CC BY 4.0 / domínio público); Royal College of Physicians /
Internet Archive."

## Origem (URLs)

- american-manikin-1890: https://wellcomecollection.org/works/kz8g5ggf (IIIF b21333749, canvases 10–21)
- witkowski-atlas-tronco-1880: https://archive.org/details/cn25039-2 (canvases 9–25)
- witkowski-visao-cabeca / -olho: https://wellcomecollection.org/works/zkgu8j3z (IIIF b33667937, canvases 10–18 e 24–40)
- fugitiva-*: https://commons.wikimedia.org/wiki/File:Anatomical_fugitive_sheet,female_Wellcome_L0049674.jpg (e L0049657–L0049677)
- albinus-tabulae-1747: https://wellcomecollection.org/works/a43g5vnz (IIIF b33543963, canvases 20, 23, 37, 41, 47, 53, 59)

## Outros candidatos (não testados ou sem licença aberta)

- *Anatomie iconoclastique* (original francês de Witkowski) no Internet Archive (cn25039-1a orelha, -1c encéfalo,
  -1d laringe): não testado.
- Phillips' Popular Manikin e Bilz "Der Mensch": sem digitalização com licença aberta encontrada.
- Schmidt, Vesalius *Epitome*, Bourgery & Jacob: não serviram ou não foram testados.
