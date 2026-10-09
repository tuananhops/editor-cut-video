#!/usr/bin/env bash
# Thin wrapper: render.sh <source.mp4> <segs.txt> [out.mp4] [extra render.py args...]
# Uses $ECV_VENV (default ~/.venv-ecv) python if present.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
PY=${ECV_VENV:-$HOME/.venv-ecv}/bin/python; [ -x "$PY" ] || PY=python3
src=${1:?usage: render.sh <source> <segs.txt> [out.mp4] [args]}; segs=${2:?segs.txt}; shift 2
if [ $# -gt 0 ] && [[ "$1" != -* ]]; then out=$1; shift; set -- -o "$out" "$@"; fi
exec nice -n 10 "$PY" "$here/render.py" "$src" "$segs" "$@"
