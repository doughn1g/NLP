#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GPU_INDEX="${1:-0}"
MODEL_CACHE="${2:-$PROJECT_ROOT/models}"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "Project .venv is missing. Run prepare_models.sh first." >&2
  exit 1
fi

if ! .venv/bin/python - <<'PY'
import torch
raise SystemExit(0 if torch.version.cuda is not None else 1)
PY
then
  .venv/bin/python -m pip install --no-cache-dir --force-reinstall torch==2.6.0 \
    --index-url https://download.pytorch.org/whl/cu124
fi

CUDA_VISIBLE_DEVICES="$GPU_INDEX" .venv/bin/python - <<'PY'
import torch
print(f"PyTorch {torch.__version__}; CUDA build {torch.version.cuda}; available {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable in this terminal; no model run was started.")
print(f"Selected device: {torch.cuda.get_device_name(0)}")
PY

mkdir -p results/gpu
for model in nllb qwen labse qwen_embed; do
  CUDA_VISIBLE_DEVICES="$GPU_INDEX" .venv/bin/python baseline.py run \
    --model "$model" --model-dir "$MODEL_CACHE" \
    --output "results/gpu/$model.jsonl"
done

.venv/bin/python baseline.py blind-review \
  --predictions results/gpu/nllb.jsonl results/gpu/qwen.jsonl \
  --output results/gpu/blind.csv --mapping results/gpu/private_mapping.jsonl
.venv/bin/python baseline.py score-matching \
  --predictions results/gpu/labse.jsonl results/gpu/qwen_embed.jsonl \
  --output results/gpu/matching_scores.csv
.venv/bin/python baseline.py compare \
  --translation results/gpu/nllb.jsonl results/gpu/qwen.jsonl \
  --matching results/gpu/labse.jsonl results/gpu/qwen_embed.jsonl \
  --output results/gpu/comparison.jsonl

echo "GPU pilot complete. Outputs: $PROJECT_ROOT/results/gpu"
