# Peças comuns dos lançadores em bin/ (não é comando: fica fora do PATH de propósito).
# ROOT vem de quem chama: a pasta do plugin, deduzida do próprio caminho do lançador.
EDITLABS_DATA="${EDITLABS_DATA:-$HOME/.local/share/edit-labs-ai}"   # fica fora do plugin: sobrevive a atualização
CV_SKILL="$ROOT/skills/corte-viral"
MV_SKILL="$ROOT/skills/motion-vox"
CV_PY="$EDITLABS_DATA/venv-corte/bin/python"
MV_PY="$EDITLABS_DATA/venv-motion/bin/python"
CL_PY="$EDITLABS_DATA/venv-colagem/bin/python"         # motor de colagem (colagem-camadas, colagem-historia, explicador-vox)
export EDITLABS_MOTOR="${EDITLABS_MOTOR:-$ROOT/motor/colagem}"
export EDITLABS_ASSETS="$EDITLABS_DATA/colagem/assets"  # pacotes grandes baixados da release (3D, pranchas)
export CV_YUNET="$CV_SKILL/models/face_detection_yunet_2023mar.onnx"   # rosto (YuNet) para cenas_plano e desdividir
export EDITLABS_AGENTS="$ROOT/agents"                  # a verificação da corte-viral procura os agentes aqui
export MOTION_VOX="$EDITLABS_DATA/motion-vox"          # a biblioteca de assets mora aqui (persistente)

precisa_setup() {
  echo "O ambiente do Edit Labs AI ainda não foi preparado neste computador." >&2
  echo "Rode:  editlabs-setup     (cria os ambientes Python em $EDITLABS_DATA)" >&2
  exit 3
}
