#!/usr/bin/env bash
# Extract 16 kHz mono wav for analysis/transcription.
# usage: extract_audio.sh <video> [out.wav]   (default: src16k.wav in cwd)
set -euo pipefail
in=${1:?usage: extract_audio.sh <video> [out.wav]}
out=${2:-src16k.wav}
ffmpeg -v error -y -i "$in" -map 0:a:0 -vn -ac 1 -ar 16000 -c:a pcm_s16le "$out"
echo "$out"
