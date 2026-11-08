# Edit Labs AI no Windows

O plugin roda no Windows 10/11 sem assinatura de nenhum gerador. Os comandos dele (`editlabs-setup`, `clpy`, `cvpy`,
`mvpy`, `vch`, `di`…) são scripts bash: no Windows eles rodam no **Git Bash**, que o Claude Code já usa como shell
(vem com o Git for Windows). Também existem atalhos `.cmd` (`bin/*.cmd`) para quem chamar de um terminal comum.

## 1. Programas (uma vez)

No PowerShell:

```powershell
winget install Git.Git Python.Python.3.12 Gyan.FFmpeg yt-dlp.yt-dlp DenoLand.Deno
```

- **Python 3.10 a 3.12** (o kit fixa `numpy 2.0.2`, sem pacote para 3.13+). Se o `python` abrir a Microsoft Store, só
  existe o atalho da Store: instale pelo comando acima e, se precisar, desligue o atalho em *Configurações →
  Aplicativos → Configurações avançadas → Aliases de execução de aplicativo*.
- **ffmpeg** inclui o `ffprobe`. **Deno** é o que o `yt-dlp` usa para o YouTube.
- Depois de instalar, **feche e abra o Claude Code de novo** (o PATH novo só vale em terminais novos).

## 2. Plugin e setup

```
/plugin marketplace add paullabs/edit-labs-ai
/plugin install edit-labs-ai@edit-labs-ai
```

Reinicie o Claude Code e peça *"roda o editlabs-setup --colagem --recorte"*. Ele:

1. confere `ffmpeg`, `ffprobe`, `yt-dlp`, `deno` e o Python (também procura pelo `py -3.12`);
2. cria os ambientes em `C:\Users\<você>\.local\share\edit-labs-ai\` (`venv-corte`, `venv-motion`, `venv-colagem`);
3. com `--recorte`, instala o `rembg` (recorte de fundo local, grátis; o modelo, ~170 MB, baixa na primeira vez).

## 3. O que é diferente do Mac

| Assunto | No Mac | No Windows |
| --- | --- | --- |
| Recorte de fundo | Vision da Apple (`recorte.swift`, já pronto) | `rembg` (`clpy recorte.py`, depois de `editlabs-setup --recorte`) |
| Ícones de app e cursores do sistema (`assets_locais.py`, motion-arquivo) | lê os `.icns` e os cursores do macOS | **não existe**: baixe o ícone do site da marca (uso nominativo) |
| Transcrição rápida (`requirements-mlx.txt`) | mlx-whisper (Apple Silicon) | só o `faster-whisper`, que já vem no ambiente |
| Blender (3D próprio, opcional) | `/Applications/Blender.app` | `C:\Program Files\Blender Foundation\Blender *\blender.exe` (o setup reconhece) |
| Programas | `brew install …` | `winget install …` |
| Mostrar a entrega | Finder | Explorer |

Todo o resto (motor de colagem, motion-vox, corte-viral, decupagem, som sintetizado) roda igual.

## 4. Como o plugin lida com o Windows por dentro

- `scripts/comum.sh` detecta o sistema (`EDITLABS_OS` = `mac`, `linux` ou `windows`), usa `venv/Scripts/python.exe`
  em vez de `venv/bin/python`, passa os caminhos no formato `C:/Users/...` (o Python nativo não entende
  `/c/Users/...`) e usa `;` no `PYTHONPATH`.
- Define `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`: sem isso o Python do Windows usa `cp1252` e quebra ao imprimir
  acentos e `✓`.
- `.gitattributes` força **LF** nos scripts. Sem isso o Git for Windows converte para CRLF e o bash falha com
  `bash\r: No such file or directory`.
- A trava do manifest da decupagem usa `msvcrt.locking` (no lugar de `fcntl`), e a checagem "o processo ainda
  vive?" usa a API do Windows. **Nunca** use `os.kill(pid, 0)` para isso no Windows: ele encerra o processo.

## 5. Problemas comuns

| Sintoma | Saída |
| --- | --- |
| `bash\r: No such file or directory` | atualize o plugin; se persistir, `git config --global core.autocrlf input` e reinstale |
| `'bash' não é reconhecido` ao usar um `.cmd` | instale o Git for Windows (`winget install Git.Git`) e reabra o terminal |
| setup diz "Python ausente" mas o `python --version` funciona | a versão é 3.13+ ou é o atalho da Store: `winget install Python.Python.3.12` |
| `clpy`, `vch`… não encontrados | reinicie o Claude Code; `/plugin` → `edit-labs-ai` precisa estar ativo |
| `pip` falha ao compilar algo | confirme Python 3.10–3.12 de 64 bits; `editlabs-setup --refazer` |
| caminhos muito longos | habilite caminhos longos do Windows (`LongPathsEnabled`) ou use uma pasta de projeto curta (`C:\v\projeto`) |
| antivírus apaga ou trava o `ffmpeg`/`deno` | adicione a pasta `.local\share\edit-labs-ai` às exceções |

## Status

Adaptação feita em 07/11/2026. Testada no macOS, incluindo os ramos do Windows simulados nos scripts (caminhos,
separadores, venv, trava de arquivo entre processos). **Ainda não passou por uma máquina Windows de verdade**: se algo
falhar, rode `editlabs-verificar` e mande a saída.
