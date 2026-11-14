#!/usr/bin/env bash
set -euo pipefail

# Download the four pinned translation checkpoints after installing .venv.
# Usage: bash prepare_models.sh [model-cache-directory]

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CACHE="${1:-$PROJECT_ROOT/models}"
mkdir -p "$MODEL_CACHE"

FREE_BYTES="$(df -PB1 "$MODEL_CACHE" | awk 'NR==2 {print $4}')"
if (( FREE_BYTES < 35000000000 )); then
  echo "Need at least 35 GB free in $MODEL_CACHE before downloading all four checkpoints." >&2
  exit 1
fi

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  echo "Create .venv and install PyTorch and requirements.txt first." >&2
  exit 1
fi

HF_CLI="$(command -v hf || true)"
if [[ -z "$HF_CLI" ]]; then
  HF_CLI="$PROJECT_ROOT/.venv/bin/hf"
fi
if [[ ! -x "$HF_CLI" ]]; then
  echo "The hf CLI is missing; install huggingface_hub in .venv." >&2
  exit 1
fi

"$HF_CLI" download facebook/nllb-200-distilled-600M \
  --revision f8d333a098d19b4fd9a8b18f94170487ad3f821d --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.bin'
"$HF_CLI" download Qwen/Qwen3-4B-Instruct-2507 \
  --revision cdbee75f17c01a7cc42f958dc650907174af0554 --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.safetensors'
"$HF_CLI" download google/madlad400-3b-mt \
  --revision fa184c675da0b5c9e1c8694fccd4e12e2d422094 --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.safetensors'
"$HF_CLI" download facebook/m2m100_418M \
  --revision 55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636 --cache-dir "$MODEL_CACHE" \
  --include '*.json' '*.txt' '*.model' '*.bin'

echo "All four pinned translation checkpoints are ready in $MODEL_CACHE"
