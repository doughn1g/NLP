#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_CACHE="${1:-$PROJECT_ROOT/models}"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "Project .venv is missing." >&2
  exit 1
fi

mkdir -p results/idioms_to_en
for model in nllb qwen madlad m2m100; do
  .venv/bin/python baseline.py run --model "$model" \
    --input data/idioms_to_en_draft.jsonl --model-dir "$MODEL_CACHE" \
    --output "results/idioms_to_en/$model.jsonl" --resume
done

predictions=(results/idioms_to_en/nllb.jsonl results/idioms_to_en/qwen.jsonl \
             results/idioms_to_en/madlad.jsonl results/idioms_to_en/m2m100.jsonl)

.venv/bin/python baseline.py blind-review --input data/idioms_to_en_draft.jsonl \
  --predictions "${predictions[@]}" --output results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv \
  --mapping results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl
.venv/bin/python baseline.py translation-table --input data/idioms_to_en_draft.jsonl \
  --predictions "${predictions[@]}" --output results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_SIDE_BY_SIDE.csv
.venv/bin/python export_excel.py --input data/idioms_to_en_draft.jsonl \
  --predictions "${predictions[@]}" --output results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx

echo "Four-model comparison is ready in results/idioms_to_en/"
