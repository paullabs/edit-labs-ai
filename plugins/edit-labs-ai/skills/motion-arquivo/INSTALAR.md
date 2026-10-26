# Instalar

A skill vem com o plugin `edit-labs-ai`. O `editlabs-setup` prepara o ambiente Python; esta página é para quem
instala à mão ou precisa conferir.

1. Python 3.10–3.12 com as dependências de `requirements.txt`:
   `pip install -r requirements.txt` (dentro do ambiente do plugin, em `$EDITLABS_DATA`).
2. `ffmpeg` no PATH (com libx264). Texto nunca entra por filtro do ffmpeg — vem do motor.
3. macOS: Xcode Command Line Tools (`xcode-select --install`) para o `swift` que renderiza o cursor do sistema e
   recorta o sujeito (`recorte.swift`). Sem ele, o resto funciona; o cursor vem de print.
4. Fontes: Instrument Serif e Inter já estão em `motor/fontes/`, com as licenças OFL ao lado. A grotesca do gancho
   é a Arial Bold do sistema (macOS/Windows); no Linux, Liberation Sans Bold (mesma métrica). Sem nenhuma das duas,
   o gancho usa a Inter 800. Nenhuma fonte de sistema vai no pacote.
5. Som (opcional): `export EDITLABS_SONS="<sua pasta de efeitos>"` e `python3 ferramentas/som_biblioteca.py`. Sem
   isso, o mixador usa os efeitos sintetizados de `motor/kit/sfx/` (refaça com `python3 motor/som.py`).
6. `python3 verificar.py` — confere tudo e renderiza um quadro de cada tipo de plano.

A transcrição usa o modelo `mobiuslabsgmbh/faster-whisper-large-v3-turbo` (baixa ~1,6 GB na primeira vez, para o
cache do Hugging Face). Modelo menor erra o início da palavra em até 0,15 s — meio degrau da grade.
