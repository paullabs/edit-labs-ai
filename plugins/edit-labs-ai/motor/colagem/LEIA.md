# Motor de colagem

Motor em Python que monta vídeos verticais (1080×1920) de colagem de papel: camadas com chaves, câmera sobre um
mundo de papel, boil de desenho, sombras, transições, mecânicas de camadas registradas e som. É compartilhado pelas
skills de colagem do plugin (`colagem-camadas`, `colagem-historia`, `explicador-vox`).

## Como importar

```python
import os, sys
from pathlib import Path
RAIZ = Path(__file__).resolve().parents[N]          # a raiz do plugin, contada a partir do seu arquivo
sys.path.insert(0, os.environ.get("EDITLABS_MOTOR", str(RAIZ / "motor" / "colagem")))
import motor as M, pecas as PC, cena as C, camadas as K
import som_auto as SA, som as S
```

Dependências: `pip install -r requirements.txt` (numpy, opencv-python, Pillow) e `ffmpeg` no PATH. Os passos 3D
pedem o Blender 4.x/5.x (`blender_giro.py` roda dentro dele).

## Módulos

| arquivo | o que faz |
| --- | --- |
| `motor.py` | núcleo: `Camada` (imagem ou função que desenha), `Camera`, curvas, boil, sombra por material, `Transicao` (`iris`, `rasgo`, `empurra`, `mergulho`, `recua`, `flash`), acabamento de filme, `render` (vídeo ou quadros PNG), `checar_margens`, `ajustar_texto` |
| `cena.py` | blocos de cena: `cai`, `desliza`, `fixo`, `Traco` (caneta que se desenha), `circulo`, `carimbo`, `contador`, `Camera` por planos (`plano`, `seguir`), `quadro(caixa)` para enquadrar na região segura, `rajada`, `ondas`, `letras`, `vira`, `flutua`, `papel_area` |
| `camadas.py` | mecânicas de camadas registradas: `aba`, `metades`, `janela`/`janela_forma`, `descasca`, `levanta`, `destaca`, `pousa`, `explode`, `pulsa`, `giro` (3D a 7 qps), `pilha`, `registrar` (ECC), `cortar_alfa`, `papelizar` (render 3D → gravura de papel), `apara_lascas`, `fecha_vazados` |
| `pecas.py` | peças de papel: `cartao` (foto impressa com fita), `recorte` (borda de tesoura), `etiqueta`, `carimbo`, `legenda`, `fita` (procedural), `papel_mundo`, `textura_papel`, `grade`, `folha` |
| `som_auto.py` | som que nasce da cena: lê o `L.som` de cada mecânica e da câmera, sintetiza um efeito por ação, nivela contra a música, sidechain, master −20 LUFS. `mixar_auto(camadas, cam, trans, trilha, fim, pasta)`; `trilha=None` usa a cama sintetizada |
| `som.py` | utilidades de áudio (`ler`, `gravar`, `medir` LUFS/dBTP, `juntar` vídeo + mix, `acentos` da trilha) e `mixar` com lista de eventos manual |
| `sons_sint.py` | banco de sons gerado em código (papel, amassar, folhear, ar, reverso, grave, brilho, relógio, toque, baque, giz, obturador) e `cama` (trilha-leito calma). Aceita uma pasta do usuário por classe |
| `recursos.py` | onde ficam fontes, kit, sons e dados (`EDITLABS_DATA`, `EDITLABS_FONTES`, `EDITLABS_SONS`, `EDITLABS_TRILHAS`) |
| `blender_giro.py` | roda dentro do Blender: renderiza vistas e camadas de um modelo pela MESMA câmera (passes `cor` e `luz`, `vistas.json` com `px_por_m` e marcos) |
| `conferir_figura.py` | checagens antes do vídeo: `lascas`, `buracos`, `cortados`, `composto`, `faltando` |
| `conferir.py`, `qa.py` | conferência do vídeo pronto: desenhos borrados fora das transições e texto pequeno |
| `folha_quadros.py` | folha de conferência com os quadros PNG lado a lado |
| `grafico_som.py` | gráfico do nível da música, dos efeitos e do master |
| `recorte.swift` | recorte local do sujeito com alfa (Vision, só macOS 14+) |
| `GUIA_OLHO.md` | regras de leitura: tamanhos mínimos, caminho do olho, margens |
| `kit/` | textura de papel antigo (ver `kit/CREDITOS.md`) |

## Convenções

- Tela 1080×1920; relógio de autoria de 24 qps (as chaves estão em quadros de 24); o vídeo sai a 28 qps com 14
  desenhos por segundo. Mecânicas de camadas andam a 7 qps (stop-motion).
- Coordenadas do mundo em px, origem no canto de cima à esquerda; rotação em graus, horária.
- Chaves: `[(quadro, valor, curva)]`, curvas `lin`, `in`, `out`, `io`, `back`, `segura`.
- Margem segura do Reels: `motor.REGIAO_REELS = (80, 260, 960, 1420)`.

## Som sem biblioteca de terceiros

Nenhum som ou música vem no plugin. Os efeitos são sintetizados em `sons_sint.py`. Para usar sons seus (com licença
que permita), crie `~/.local/share/edit-labs-ai/colagem/sons/<classe>/` (classes: `papel`, `amassar`, `folhear`,
`ar`, `ar_suave`, `reverso`, `grave`, `brilho`, `relogio`, `toque`, `baque`, `giz`, `obturador`) e ponha os
arquivos lá. Trilhas: passe o caminho do arquivo para `mixar_auto`; sem trilha, entra uma cama sintetizada.

## Teste rápido

```bash
clpy - <<'EOF'
import sys; sys.path.insert(0, "motor/colagem")
import motor as M, pecas as PC, cena as C
fundo = PC.papel_mundo(M.W, M.H)
et = PC.etiqueta(["TESTE"])
cam = M.Camera()
M.render([C.cai("ET", et, 0, 540, 900)], cam, fundo, 24, "teste_quadros", quadros=[12])
EOF
```
