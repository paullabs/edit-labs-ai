# O que baixar da release (e para onde)

Os arquivos grandes não vão no repositório. Eles ficam na página de releases do plugin:
https://github.com/paullabs/edit-labs-ai/releases

Baixe **só o pacote do exemplo que você vai usar**, e só com a permissão do usuário (mostre nome, tamanho e licença
antes: `REGRAS.md`, seção 8). Todos descompactam na mesma pasta de dados, fora do plugin:

```bash
DADOS="${EDITLABS_DATA:-$HOME/.local/share/edit-labs-ai}/colagem"
mkdir -p "$DADOS"
unzip -o colagem-zanatomy-camadas.zip -d "$DADOS"     # cria $DADOS/assets/3d/z-anatomy/...
```

| pacote | tamanho | licença | precisa para |
| --- | --- | --- | --- |
| `colagem-zanatomy-camadas.zip` | ~33 MB (46 MB aberto) | CC BY-SA 4.0 | luva, crânio, estalar, corpo humano |
| `colagem-bodyparts3d.zip` | ~68 MB (215 MB aberto) | CC BY-SA 2.1 JP | crânio (cérebro), corpo humano (terno) |
| `colagem-pranchas.zip` | ~207 MB | domínio público e CC BY 4.0 | manequim de 1890 (e as outras pranchas com abas) |

Depois de descompactar:

```
~/.local/share/edit-labs-ai/colagem/
  assets/
    3d/
      z-anatomy/            camadas/*.glb, LEIA.md, LICENSE-Z-Anatomy.txt
      bodyparts3d-partof-obj99/
                            partof_BP3D_4.0_obj_99/*.obj, download/*.txt, alinhamento.json,
                            pele_bodyparts3d_no_sistema_zanatomy.glb, LEIA.md
    pranchas/               american-manikin-1890/, witkowski-*/, albinus-tabulae-1747/, fugitiva-*/, indice.json, LEIA.md
  sons/                     (opcional) seus efeitos, uma subpasta por classe
  trilhas/                  (opcional) suas músicas
  kit/fita.png              (opcional) sua imagem de fita
```

Os assets pequenos e livres (luvas CC BY 3.0, crânio CC0) já vêm no plugin em `assets/3d/`. Cada pacote traz um
`LEIA.md` com a licença e o crédito pronto; os créditos de tudo estão em `CREDITOS.md`.

Para conferir: `python3 exemplos/preparar.py manequim` (pranchas) ou `python3 exemplos/preparar.py luva` (Z-Anatomy +
Blender) avisam com uma mensagem clara se faltar algum arquivo.
