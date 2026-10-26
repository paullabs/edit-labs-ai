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
| modelos `../modelos/*_blender.py`, `../exemplos/terra_blender.py`, junta, bolha, terno e texturas do terno | objetos 3D feitos em código | próprios | do plugin | declarar "modelo próprio" |
| fontes (`skills/motion-vox/fontes`) | Archivo Black, IBM Plex Mono, Inter e outras | Google Fonts / autores | SIL OFL 1.1 (arquivos de licença ao lado) | — |

Fita crepe e todos os efeitos sonoros: gerados em código pelo motor (sem arquivo de terceiros).

## Na release (`RELEASE.md`)

| pacote | conteúdo | autor / origem | licença | crédito no vídeo |
| --- | --- | --- | --- | --- |
| `colagem-zanatomy-camadas.zip` | 8 camadas GLB do corpo (pele, músculos, órgãos, esqueleto, mão direita pele e ossos, crânio, coração), **sem** as partes NC do atlas | Z-Anatomy (Gauthier Kervyn & Marcin Zielinski), sobre BodyParts3D — https://github.com/Z-Anatomy/Models-of-human-anatomy | CC BY-SA 4.0 | obrigatório; o vídeo derivado sai sob CC BY-SA 4.0 |
| `colagem-bodyparts3d.zip` | 1.258 OBJ (PART-OF, 99%), tabelas originais, `alinhamento.json` e a pele inteira no sistema do Z-Anatomy | BodyParts3D © DBCLS — https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html | CC BY-SA 2.1 JP | obrigatório; derivado sob a mesma licença |
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
| foto do homem de terno do exemplo do corpo humano: "Photographic postcard of an unidentified man in a suit", 1926–1940s, Smithsonian NMAAHC 2013.46.29.86 — https://nmaahc.si.edu/object/nmaahc_2013.46.29.86 | `exemplos/homem3_*.py` | CC0 segundo o Smithsonian Open Access; confira na página antes de baixar e de publicar. Crédito: "Collection of the Smithsonian National Museum of African American History and Culture" |
| poses do braço geradas por IA a partir da própria foto | `exemplos/homem3_poses_ia.py` | declarar no crédito que o braço foi gerado por IA; o rosto é sempre o da foto |
| narração | `exemplos/cena_estalar.py` | voz gerada só com "pode" do usuário (gasta crédito) |
| música | todos (`COLAGEM_TRILHA`) | só trilha com licença que permita o uso; sem trilha, o motor gera uma cama |

## Ficou de fora (e por quê)

- O `Z-Anatomy_Startup.blend` completo não é redistribuído: tem partes CC BY-NC e NC-SA (rim, orelha interna,
  ossículos) e um cérebro sem licença declarada.
- O coração do NIH 3D (`3DPX-022787`, CC0) não entra: foi gerado por IA e a anatomia não é confiável.
- Nenhuma música nem efeito de bancos que proíbem redistribuir (Mixkit, Artlist e afins).
