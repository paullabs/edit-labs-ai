# Créditos dos assets da colagem-camadas

Tudo o que a skill usa, com origem e licença. "No plugin" = vem no repositório; "release" = baixar da página de
releases (ver `RELEASE.md`); "você" = o usuário providencia.

## No plugin

| arquivo | o que é | autor / origem | licença | crédito no vídeo |
| --- | --- | --- | --- | --- |
| `3d/luva-boxe-polypizza-jtoastie/boxing-glove-jtoastie.glb` | luva de boxe low poly com punho longo (mão esquerda; os exemplos espelham) | J-Toastie, Poly Pizza — https://poly.pizza/m/35PCBHLrd4 | CC BY 3.0 | obrigatório: "Boxing Glove por J-Toastie (Poly Pizza), CC BY 3.0" |
| `3d/luva-boxe-polypizza-zsky/boxing-gloves-zsky.glb` | par de luvas low poly | Zsky, Poly Pizza — https://poly.pizza/m/l2S6HNEpey | CC BY 3.0 | obrigatório: "Boxing Gloves por Zsky (Poly Pizza), CC BY 3.0" |
| `3d/cranio-opengameart-cdmir/skull-obj.zip` | crânio com mandíbula, texturizado (OBJ + PNG de cor, normal, AO e rugosidade) | CDmir, OpenGameArt — https://opengameart.org/content/human-skull-0 | CC0 | opcional (cortesia): "Human skull por CDmir (OpenGameArt), CC0" |
| `../../motor/colagem/kit/papel_antigo.jpg` | textura de página de livro antigo | Flickr Commons, via Wikimedia Commons (`Blank_page,_brown_paper_texture_(14802136533).jpg`) | sem restrições de direitos conhecidas | opcional |
| `../exemplos/dados/estalar/palavras_bruto.json` | tempos das palavras da narração de exemplo | texto e transcrição próprios | do plugin | — |
| `../exemplos/dados/estalar/voz.mp3` | narração do exemplo do estalar (35 s), casada com as palavras acima | voz sintética gerada por IA pelo projeto (de biblioteca de vozes); sem metadados | do plugin, só para estudar o exemplo | declarar "narração gerada por IA" se publicar |
| `../exemplos/dados/mapa/ne_110m_admin_0_countries.geojson` | contornos dos países 1:110m (exemplo do mapa) | Natural Earth — https://www.naturalearthdata.com | domínio público | opcional (cortesia): "Made with Natural Earth" |
| modelos `../modelos/*_blender.py`, `../exemplos/terra_blender.py`, junta, bolha, terno e texturas do terno | objetos 3D feitos em código | próprios | do plugin | declarar "modelo próprio" |
| fontes (`skills/motion-vox/fontes`) | Archivo Black, IBM Plex Mono, Inter e outras | Google Fonts / autores | SIL OFL 1.1 (arquivos de licença ao lado) | — |

Fita crepe e todos os efeitos sonoros: gerados em código pelo motor (sem arquivo de terceiros).

## Na release (`RELEASE.md`)

| pacote | conteúdo | autor / origem | licença | crédito no vídeo |
| --- | --- | --- | --- | --- |
| `colagem-zanatomy-camadas.zip` | 8 camadas GLB do corpo (pele, músculos, órgãos, esqueleto, mão direita pele e ossos, crânio, coração), **sem** as partes NC do atlas | Z-Anatomy (Gauthier Kervyn & Marcin Zielinski), sobre BodyParts3D — https://github.com/Z-Anatomy/Models-of-human-anatomy | CC BY-SA 4.0 | obrigatório; o vídeo derivado sai sob CC BY-SA 4.0 |
| `colagem-bodyparts3d.zip` | 1.258 OBJ (PART-OF, 99%), tabelas originais, `alinhamento.json` e a pele inteira no sistema do Z-Anatomy | BodyParts3D © DBCLS — https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html | CC BY-SA 2.1 JP | obrigatório; derivado sob a mesma licença |
| `colagem-zanatomy-garganta.zip` | a garganta (cabeça, pescoço e peito de cima) cortada em camadas num GLB, para o exemplo do espirro; sem as partes NC; o seio piriforme é modelo próprio | Z-Anatomy, sobre BodyParts3D (corte e cores pelo projeto, `garganta_blender.py`) | CC BY-SA 4.0 | obrigatório; o vídeo derivado sai sob CC BY-SA 4.0 |
| `colagem-homem3.zip` | o homem de terno recortado da foto e as poses do tchau (braço levantado gerado por IA a partir da própria foto), com as entradas e saídas da IA | foto: NMAAHC 2013.46.29.86, Smithsonian Open Access; recorte e poses pelo projeto | CC0 1.0 (foto); recorte e poses liberados em CC0 | "Foto: NMAAHC, Smithsonian (CC0). Pose do braço editada com IA." |
| `colagem-pranchas.zip` | manequim de 1890, Witkowski (tronco, cabeça, olho), Albinus 1747 | Wellcome Collection; Royal College of Physicians / Internet Archive | domínio público | cortesia (ver o `LEIA.md` do pacote) |
| `colagem-pranchas.zip` | *Tabula foeminae membra demonstrans*, 1573 | Wellcome Collection, via Wikimedia Commons | CC BY 4.0 | obrigatório: "Wellcome Collection, CC BY 4.0" |

Crédito pronto (tire o que não entrar no vídeo):

```
Modelos 3D: Z-Anatomy, the libre 3D atlas of anatomy (Gauthier Kervyn & Marcin Zielinski), CC BY-SA 4.0, baseado em BodyParts3D © The Database Center for Life Science, CC BY-SA 2.1 Japan. Luva de boxe: "Boxing Glove" por J-Toastie (Poly Pizza), CC BY 3.0. Os quadros anatômicos deste vídeo estão sob CC BY-SA 4.0.
Imagens: American Manikin Co., Anatomical figures with detachable parts, c. 1890. Wellcome Collection. Domínio público.
```

## O usuário providencia (não vem no plugin)

| o quê | onde usar | cuidado |
| --- | --- | --- |
| outra foto de pessoa para o homem de foto (o exemplo já vem com a foto CC0 no pacote `colagem-homem3`) | `exemplos/homem3_*.py` | só foto licenciada (CC0/domínio público); poses novas pelo prompt do `LEIA.md` do pacote, com "pode" (gasta crédito); o rosto é sempre o da foto |
| narração | `exemplos/cena_estalar.py` (a de exemplo já vem), `exemplos/cena_espirro.py` (`COLAGEM_VOZ`) | voz gerada só com "pode" do usuário (gasta crédito) |
| o ouvido do exemplo do espirro | `exemplos/ouvido_blender.py` | a orelha interna e os ossículos do atlas são CC BY-NC-SA 4.0 (University of Dundee): uso NÃO comercial, crédito obrigatório |
| música | todos (`COLAGEM_TRILHA`) | só trilha com licença que permita o uso; sem trilha, o motor gera uma cama |

## Ficou de fora (e por quê)

- O `Z-Anatomy_Startup.blend` completo não é redistribuído: tem partes CC BY-NC e NC-SA (rim, orelha interna,
  ossículos) e um cérebro sem licença declarada.
- O ouvido do exemplo do espirro (orelha interna, ossículos) não vem em pacote nenhum: é CC BY-NC-SA 4.0.
- A narração do exemplo do espirro não vem: o exemplo roda sem voz, no relógio da narração original.
- O coração do NIH 3D (`3DPX-022787`, CC0) não entra: foi gerado por IA e a anatomia não é confiável.
- Nenhuma música nem efeito de bancos que proíbem redistribuir (Mixkit, Artlist e afins).
