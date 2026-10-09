#!/usr/bin/env bash
# One-time setup on a new bot/box.
#   bash scripts/setup.sh                 # venv ~/.venv-ecv + deps + download 'medium'
#   ECV_VENV=/path MODELS="medium large-v3" bash scripts/setup.sh
#   SKIP_MODEL=1 bash scripts/setup.sh
set -euo pipefail
VENV=${ECV_VENV:-$HOME/.venv-ecv}
MODELS=${MODELS:-medium}
command -v ffmpeg >/dev/null || { echo "ffmpeg missing -> sudo apt-get install -y ffmpeg"; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe missing (comes with ffmpeg)"; exit 1; }
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q faster-whisper numpy soundfile gdown
if [ -z "${SKIP_MODEL:-}" ]; then
  for m in $MODELS; do
    echo "downloading faster-whisper model: $m"
    "$VENV/bin/python" -c "from faster_whisper.utils import download_model as d; print(d('$m'))"
  done
fi
"$VENV/bin/python" -c "import faster_whisper, numpy, soundfile, gdown; print('faster-whisper', faster_whisper.__version__, 'OK')"
echo "Done. Use: $VENV/bin/python scripts/transcribe.py ...  (or: source $VENV/bin/activate)"
