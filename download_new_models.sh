#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CACHE="${1:-$PROJECT_ROOT/models}"
mkdir -p "$MODEL_CACHE"

FREE_BYTES="$(df -PB1 "$MODEL_CACHE" | awk 'NR==2 {print $4}')"
if (( FREE_BYTES < 30000000000 )); then
  echo "Need at least 30 GB free in $MODEL_CACHE before these downloads." >&2
  exit 1
fi

HF_CLI="$(command -v hf || true)"
if [[ -z "$HF_CLI" ]]; then
  HF_CLI="$PROJECT_ROOT/.venv/bin/hf"
fi
if [[ ! -x "$HF_CLI" ]]; then
  echo "The hf CLI is unavailable in this terminal." >&2
  exit 1
fi

"$HF_CLI" download google/madlad400-3b-mt \
  --revision fa184c675da0b5c9e1c8694fccd4e12e2d422094 --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.safetensors'
"$HF_CLI" download facebook/m2m100_418M \
  --revision 55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636 --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.bin'

echo "MADLAD and M2M100 checkpoints are ready in $MODEL_CACHE"
