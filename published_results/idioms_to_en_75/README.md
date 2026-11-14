# Published 75-idiom translation snapshot

This folder contains the four-model outputs for 25 isolated idioms each from Mandarin, Tamil, and Tagalog, translated into English. The original source is [`data/idioms_to_en_draft.jsonl`](../../data/idioms_to_en_draft.jsonl). The run manifests record pinned model revisions, runtime versions, device, and generation settings.

`GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DRAFT.xlsx` is the main side-by-side workbook with **preliminary AI meaning judgments**. These judgments were made against cited source-language meaning notes; they are not blind bilingual ratings. Naturalness was not scored. The 75 source idioms and meanings also remain draft material. Do not report the score table as validated benchmark performance.

| File | Purpose |
| --- | --- |
| `GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DRAFT.xlsx` | Side-by-side translations and provisional meaning scores. |
| `GRADED_75_IDIOMS_4_MODELS_SEMANTIC_SUMMARY.csv` | Counts of 0, 1, and 2 meaning scores by language and model. |
| `GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DECISIONS.csv` | All 300 preliminary decisions, source meaning notes, and citations. |
| `FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx` | Original comparison workbook before semantic grading. |
| `FINAL_75_IDIOMS_4_MODELS_SIDE_BY_SIDE.csv` | Plain-text comparison table. |
| `nllb.jsonl`, `qwen.jsonl`, `madlad.jsonl`, `m2m100.jsonl` | Raw translation outputs keyed by idiom ID. |
| `*.jsonl.run.json` | Per-model run manifests. |
| `grade_semantic_draft.py` | Recreates the preliminary grading files from the ungraded workbook and CSV. |

The blind review file and private model mapping are intentionally absent so a later bilingual review can remain blind. For a new run, see the [project usage guide](../../USAGE_GUIDE.md). Runtime output files remain in the ignored local `results/` folder.
