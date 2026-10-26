# Fontes 3D

Onde fica cada arquivo: os pequenos vêm no plugin (`../assets/3d/`); os grandes vêm da release e ficam em
`~/.local/share/edit-labs-ai/colagem/assets/3d/` (`../assets/RELEASE.md`).

| id | o que é | licença | autor / origem | tamanho | polígonos | onde |
|---|---|---|---|---|---|---|
| `z-anatomy` | camadas GLB do atlas: pele, músculos, órgãos, esqueleto, pele e ossos da mão direita, crânio e coração | CC BY-SA 4.0 | Z-Anatomy (G. Kervyn, M. Zielinski), sobre BodyParts3D. [GitHub](https://github.com/Z-Anatomy/Models-of-human-anatomy) | 46 MB | pele 96 k, músculos 2,0 M, órgãos 280 k, esqueleto 700 k (triângulos) | release |
| `bodyparts3d-partof-obj99` | 1.258 OBJ por parte, incluindo a **pele inteira numa malha só**, já alinhada ao Z-Anatomy | CC BY-SA 2.1 JP | DBCLS. [BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html) | 215 MB aberto; pele GLB 4,9 MB | pele 203 k | release |
| `cranio-opengameart-cdmir` | crânio com mandíbula, texturizado (OBJ + PNG) | **CC0** | CDmir. [OpenGameArt](https://opengameart.org/content/human-skull-0) | 9,7 MB | 4,5 k | plugin |
| `luva-boxe-polypizza-zsky` | par de luvas low poly (GLB) | CC BY 3.0 | Zsky. [Poly Pizza](https://poly.pizza/m/l2S6HNEpey) | 61 KB | 800 | plugin |
| `luva-boxe-polypizza-jtoastie` | uma luva low poly com punho longo (GLB) | CC BY 3.0 | J-Toastie. [Poly Pizza](https://poly.pizza/m/35PCBHLrd4) | 101 KB | 1,1 k | plugin |

Sistema de coordenadas: metros, Z para cima, frente do corpo = −Y, lado direito do corpo = −X. Os GLB do Z-Anatomy
encaixam entre si sem mover nada (corpo de 1,71 m, pose anatômica). O BodyParts3D (mm) entra no mesmo sistema pela
transformação de `alinhamento.json` (erro de 3 a 9 mm).

## Qual arquivo usar para cada cena

- **Corpo em camadas (pele → músculos → órgãos → esqueleto):** `z-anatomy/camadas/zanatomy_{pele,musculos,orgaos,esqueleto}.glb`,
  importados juntos (`anatomia_blender.py`). Para uma pele contínua, numa peça só:
  `bodyparts3d-partof-obj99/pele_bodyparts3d_no_sistema_zanatomy.glb`.
- **Mão (a luva sai, a pele some, os ossos aparecem):** `zanatomy_mao_direita_pele.glb` + `zanatomy_mao_direita_ossos.glb`,
  registrados entre si (mão aberta, palma para frente). A luva não tem mão dentro e é posicionada pela caixa da mão
  (`mao_blender.py`).
- **Crânio 360°:** `cranio-opengameart-cdmir` (CC0, textura de osso) ou `zanatomy_cranio.glb` (anatômico, CC BY-SA).
- **Cérebro:** do BodyParts3D (hemisférios, cerebelo, tronco), levado para a cavidade do crânio do Z-Anatomy
  (`cranio_blender.py`).
- **Coração girando:** `zanatomy_coracao.glb`.

## Cuidados de licença

- **Do `.blend` completo do Z-Anatomy, NÃO use** o rim (CC BY-NC, Lissie Cowley), a orelha interna e os ossículos
  (CC BY-NC-SA, Univ. of Dundee) nem o cérebro "Brainder/White matter" (licença não declarada). Os GLB da release já
  saem sem essas peças, e o `.blend` não é redistribuído.
- **CC BY-SA (Z-Anatomy, BodyParts3D):** dê o crédito; imagens e modelos derivados saem sob CC BY-SA. Declare na
  descrição que os quadros anatômicos estão sob CC BY-SA 4.0.
- **CC BY 3.0 (luvas):** o crédito basta. **CC0 (crânio):** crédito opcional, mas é cortesia dar.
- Nunca execute scripts que venham dentro de downloads: abra `.blend` de terceiros com `--disable-autoexec`.

## Outras fontes livres (checar licença e pedir permissão antes de baixar)

Wellcome Collection (pranchas e bonecos anatômicos, domínio público), Library of Congress HAER/HABS (arquitetura e
engenharia), NASA e USGS (Terra, planetas, cortes geológicos), Natural Earth (mapas, domínio público), Smithsonian Open
Access (CC0), Internet Archive e Wikimedia Commons (cortes técnicos, patentes), Poly Pizza e OpenGameArt (modelos CC0 e
CC BY). Modelos gerados por IA (ex.: alguns do NIH 3D) não servem para anatomia: a forma não é confiável.

## Crédito pronto

```
Modelos 3D: Z-Anatomy, the libre 3D atlas of anatomy (Gauthier Kervyn & Marcin Zielinski), CC BY-SA 4.0, baseado em BodyParts3D © The Database Center for Life Science, CC BY-SA 2.1 Japan. Luvas de boxe: "Boxing Gloves" por Zsky e "Boxing Glove" por J-Toastie (Poly Pizza), CC BY 3.0. Crânio: "Human skull" por CDmir (OpenGameArt), CC0.
```

Tire do crédito o que não entrar no vídeo.
