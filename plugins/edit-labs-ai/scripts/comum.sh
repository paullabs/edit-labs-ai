# Peças comuns dos lançadores em bin/ (não é comando: fica fora do PATH de propósito).
# ROOT vem de quem chama: a pasta do plugin, deduzida do próprio caminho do lançador.
# Funciona no macOS, no Linux e no Windows (Git Bash, que é o shell do Claude Code no Windows).

# ---- sistema: mac | linux | windows (EDITLABS_OS força, só para teste)
case "$(uname -s 2>/dev/null || echo desconhecido)" in
  Darwin) EDITLABS_OS="${EDITLABS_OS:-mac}" ;;
  MINGW*|MSYS*|CYGWIN*) EDITLABS_OS="${EDITLABS_OS:-windows}" ;;
  *) EDITLABS_OS="${EDITLABS_OS:-linux}" ;;
esac
export EDITLABS_OS

# Python nativo do Windows não entende /c/Users/...: passe sempre o caminho no formato C:/Users/... (cygpath -m).
caminho_nativo() {
  if [ "$EDITLABS_OS" = windows ] && command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else printf '%s' "$1"; fi
}
ROOT="$(caminho_nativo "$ROOT")"

# Python imprime ✓ e acentos: no Windows o padrão seria cp1252 e quebraria com UnicodeEncodeError.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

# Separador de PYTHONPATH: ";" no Windows, ":" no resto.
if [ "$EDITLABS_OS" = windows ]; then SEP_PY=";"; VENV_BIN="Scripts"; PY_EXE="python.exe"; else SEP_PY=":"; VENV_BIN="bin"; PY_EXE="python"; fi
# acrescenta pastas ao PYTHONPATH sem perder o que o usuário já tinha
pythonpath_somar() { local novo="$1"; PYTHONPATH="$novo${PYTHONPATH:+$SEP_PY$PYTHONPATH}"; export PYTHONPATH; }

if [ -n "${EDITLABS_DATA:-}" ]; then EDITLABS_DATA="$(caminho_nativo "$EDITLABS_DATA")"
else EDITLABS_DATA="$(caminho_nativo "$HOME")/.local/share/edit-labs-ai"; fi   # fora do plugin: sobrevive a atualização
CV_SKILL="$ROOT/skills/corte-viral"
MV_SKILL="$ROOT/skills/motion-vox"
CV_PY="$EDITLABS_DATA/venv-corte/$VENV_BIN/$PY_EXE"
MV_PY="$EDITLABS_DATA/venv-motion/$VENV_BIN/$PY_EXE"
CL_PY="$EDITLABS_DATA/venv-colagem/$VENV_BIN/$PY_EXE"   # motor de colagem (colagem-camadas, colagem-historia, explicador-vox)
export EDITLABS_MOTOR="${EDITLABS_MOTOR:-$ROOT/motor/colagem}"
export EDITLABS_ASSETS="$EDITLABS_DATA/colagem/assets"  # pacotes grandes baixados da release (3D, pranchas)
export CV_YUNET="$CV_SKILL/models/face_detection_yunet_2023mar.onnx"   # rosto (YuNet) para cenas_plano e desdividir
export EDITLABS_AGENTS="$ROOT/agents"                  # a verificação da corte-viral procura os agentes aqui
export MOTION_VOX="$EDITLABS_DATA/motion-vox"          # a biblioteca de assets mora aqui (persistente)

# um Python qualquer (do plugin, ou o do sistema) para tarefas pequenas: unzip, ler JSON…
py_qualquer() {
  local c
  for c in "$CL_PY" "$CV_PY" "$MV_PY"; do [ -x "$c" ] && { printf '%s' "$c"; return 0; }; done
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then command -v "$c"; return 0; fi
  done
  if [ "$EDITLABS_OS" = windows ] && command -v py >/dev/null 2>&1; then printf 'py'; return 0; fi
  return 1
}

# Como instalar os programas que faltam, no sistema da pessoa. Entrada: nomes (ffmpeg yt-dlp deno python).
dica_instalar() {
  local n pacotes=""
  case "$EDITLABS_OS" in
    mac)
      for n in "$@"; do case "$n" in python) pacotes="$pacotes python@3.12";; ffprobe) ;; *) pacotes="$pacotes $n";; esac; done
      echo "brew install$pacotes   (sem Homebrew: https://brew.sh)" ;;
    windows)
      for n in "$@"; do case "$n" in
        ffmpeg) echo "winget install --id Gyan.FFmpeg -e" ;;
        ffprobe) ;;
        yt-dlp) echo "winget install --id yt-dlp.yt-dlp -e" ;;
        deno) echo "winget install --id DenoLand.Deno -e" ;;
        python) echo "winget install --id Python.Python.3.12 -e" ;;
        git) echo "winget install --id Git.Git -e" ;;
      esac; done
      echo "(depois feche e abra o Claude Code de novo, para o PATH novo valer)" ;;
    *)
      echo "Debian/Ubuntu: sudo apt install ffmpeg python3.12 python3.12-venv  (yt-dlp: pipx install yt-dlp; deno: https://deno.com)" ;;
  esac
}

precisa_setup() {
  echo "O ambiente do Edit Labs AI ainda não foi preparado neste computador." >&2
  echo "Rode:  editlabs-setup     (cria os ambientes Python em $EDITLABS_DATA)" >&2
  exit 3
}
