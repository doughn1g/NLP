# Cross-language idioms project

This file is the project brief and build guide for `nlpproj`. The current objective is a reproducible comparison of **four translation models** on idioms originally written in simplified Mandarin Chinese, Tamil, and Tagalog, translated into English. Start with 25 idioms per source language (75 total). English-to-other-language directions can be decided later. Bilingual reviewers will grade semantic accuracy and naturalness after the model outputs are collected.

## Research question and models

Which model best preserves the intended meaning of idioms when translating them into English?

| Model | Official checkpoint | Role |
| --- | --- | --- |
| NLLB-200 distilled 600M | [facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M) | Generate English translations |
| Qwen3-4B-Instruct-2507 | [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) | Generate English translations |
| MADLAD-400-3B-MT | [google/madlad400-3b-mt](https://huggingface.co/google/madlad400-3b-mt) | Generate English translations |
| M2M100-418M | [facebook/m2m100_418M](https://huggingface.co/facebook/m2m100_418M) | Generate English translations |

All four models translate the same source text independently. Join outputs by source example ID. Each model receives only the source text and language direction; never include draft meanings, reference translations, or another model's output in its prompt or input. The semantic matching experiment and its former embedding models, LaBSE and Qwen3-Embedding-0.6B, are outside the current four-model comparison.

## Data and evaluation

`data/idioms_to_en_draft.jsonl` has 25 idioms each for `zh`, `ta`, and `tl`, with `target_lang: en`. `build_idiom_draft.py` recreates it. Mandarin seeds come from `data/petci/filtered.json` ([PETCI](https://github.com/kenantang/petci)); Tamil seeds come from a [Tamil idiom list](https://thamizhkalanchiyam360.blogspot.com/2018/09/blog-post_18.html); Tagalog seeds come from a [Mapúa Filipino idiom handout](https://dunonglingkod.mapua.edu.ph/ALEAP/Assets/Mga%20Sawikain%20at%20Salawikain.pdf). Two items originated in `data/pilot.jsonl`. The English `intended_meaning` fields are draft reviewer aids. Bilingual reviewers must check the idioms and meanings before the data can count as a reviewed benchmark.

The first 75 items are isolated idiom phrases. They test phrase translation; they cannot establish how well a model handles an idiom **in context**. A later reviewed set should place idioms in natural sentences, include ordinary sentences for comparison, keep variants of the same idiom in one split, and reserve held-out examples for final evaluation.

The provisional [complexity audit](data/idiom_complexity_audit.md) rates all 75 draft items: 27 high, 30 medium, and 18 low on semantic opacity. Only 3 of 25 Tamil items received a high rating, and several Tamil items are single figurative words. These are analyst judgments pending bilingual review. Use the audit to balance or stratify the eventual benchmark before drawing difficulty-specific conclusions.

Use UTF-8 JSON Lines with unique nonempty IDs, nonempty source text, supported source and target languages, and distinct source and target languages. Preserve source metadata and review status in the data and results, but pass only the source text and direction to inference. Record the exact model revisions and package versions for every real run.

Review translations blind, with a randomized row ID and a separate private model mapping. Grade **meaning** from 0 to 2: 2 = intended meaning preserved, 1 = partial, 0 = wrong or missing. Grade **naturalness** from 0 to 2: 2 = fluent English, 1 = understandable but awkward, 0 = unclear or wrong language. An accurate English paraphrase can receive full meaning credit. Record a brief error note where useful. Report, for each model and direction, the rated count, share with full meaning credit, and mean naturalness. Keep draft and reviewed results separate. Do not call a model the semantic winner until human ratings are available.

## Implementation requirements

1. Check Python, disk space, RAM, GPU visibility, and PyTorch CUDA support before adding checkpoints. Use the local `.venv` and a configurable model cache directory. Check free storage before downloads; MADLAD adds a large checkpoint. Download only official publisher files, prefer publisher SafeTensors where available, and pin the exact revisions. Load one model at a time.
2. Extend the command-line runner with selectors for all four translation models. Retain input, output, model-directory, limit, dry-run, and resume options. A dry run validates data without importing model libraries. Real runs write one raw translation per source ID plus a manifest containing revision, device, runtime versions, input hash, and deterministic generation settings.
3. For NLLB, set the source tokenizer language and force the target language token. For Qwen Instruct, use its chat template and a fixed request for a natural meaning-preserving translation; decode only newly generated tokens. For MADLAD, prefix the source with its English target tag `<2en>`. For M2M100, set `tokenizer.src_lang` to `zh`, `ta`, or `tl` and force `tokenizer.get_lang_id("en")` during generation. Follow the official model cards and verify each language direction with a smoke run.
4. Run the four checkpoints on identical 75-item input, sequentially. Export four raw JSONL files, a 300-row blind grading CSV, a private mapping, and a 75-row side-by-side inspection table. The side-by-side table may contain draft meanings and model names; keep it away from blind graders.
5. After bilingual review, score by source language and model. Show example-level comparisons and sample counts. Reproduce all runs with documented commands and record any model, storage, or review work still pending. Fine-tuning and negation are later projects.

The official [MADLAD model card](https://huggingface.co/google/madlad400-3b-mt) describes the target-language prefix. The official [M2M100 model card](https://huggingface.co/facebook/m2m100_418M) lists Chinese, Tamil, Tagalog, and English, and shows how to force the target token. NLLB's pinned publisher checkpoint uses a PyTorch `.bin`, so use PyTorch 2.6 or later for that load path. Qwen3 needs a compatible recent Transformers version. Confirm these requirements again in the environment used for the new runs.

The runner pins NLLB revision `f8d333a098d19b4fd9a8b18f94170487ad3f821d`, Qwen Instruct revision `cdbee75f17c01a7cc42f958dc650907174af0554`, MADLAD revision `fa184c675da0b5c9e1c8694fccd4e12e2d422094`, and M2M100 revision `55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636`. The project `.venv` uses Python 3.10.12, PyTorch 2.6.0+cu124, Transformers 4.53.3, and sentence-transformers 5.1.0; each run manifest records its actual environment. Check available space again on any new machine.

## Current state and reproduction

`baseline.py` now supports selectors for all four translation models. On 2026-11-14, the new selectors passed data dry runs, code-only target-language tests, and real one-row smoke runs. A networked VS Code terminal downloaded the two official checkpoints. The local `.venv` needed `protobuf==4.21.12` for MADLAD's tokenizer; that version was supplied from an existing local environment and is pinned in `requirements.txt` for future setup. This Codex shell could then run both new checkpoints on CPU. All four translation files now contain 75 unique, nonempty outputs on the same source IDs, with 25 per language. `results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx` has 75 comparison rows, `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv` has 300 ungraded rows, and `FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl` has permissions `0600`. Their score columns remain blank. The earlier 12-row pilot exercised the former two-translation/two-embedding pipeline; those embedding outputs are historical pilot diagnostics, not results for this four-translation-model plan.

Existing two-model commands, run from this folder:

```bash
.venv/bin/python build_idiom_draft.py
.venv/bin/python baseline.py run --model nllb --input data/idioms_to_en_draft.jsonl --dry-run
.venv/bin/python baseline.py run --model qwen --input data/idioms_to_en_draft.jsonl --dry-run
.venv/bin/python baseline.py run --model nllb --input data/idioms_to_en_draft.jsonl --model-dir models --output results/idioms_to_en/nllb.jsonl --resume
.venv/bin/python baseline.py run --model qwen --input data/idioms_to_en_draft.jsonl --model-dir models --output results/idioms_to_en/qwen.jsonl --resume
```

The publisher checkpoints are pinned to `google/madlad400-3b-mt` revision `fa184c675da0b5c9e1c8694fccd4e12e2d422094` and `facebook/m2m100_418M` revision `55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636`. MADLAD uses publisher SafeTensors; M2M100 publishes a PyTorch `.bin`. This environment has PyTorch 2.6.0+cu124 and enough disk space. For a new setup, install the pinned `requirements.txt` and, in a terminal with internet access, run:

```bash
bash download_new_models.sh
```

After download, smoke test one row from each new model, then run the full four-model workflow. Select a GPU by setting `CUDA_VISIBLE_DEVICES=0` before `bash run_four_idioms.sh` in a terminal where PyTorch sees it. The script resumes the existing NLLB/Qwen files, runs MADLAD and M2M100 sequentially, then exports the comparison workbook, side-by-side CSV, and 300-row blind review file.

```bash
.venv/bin/python baseline.py run --model madlad --input data/idioms_to_en_draft.jsonl --model-dir models --limit 1 --output results/idioms_to_en/madlad_smoke.jsonl
.venv/bin/python baseline.py run --model m2m100 --input data/idioms_to_en_draft.jsonl --model-dir models --limit 1 --output results/idioms_to_en/m2m100_smoke.jsonl
bash run_four_idioms.sh
```

To place weights on another drive, pass its cache path as the first argument to both scripts. The completed workbook is `results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx`. Its `Comparison` sheet has one row per idiom, provisional complexity, a private draft meaning, four model translations, and blank grading columns; the `Run info` sheet lists provenance and completeness. It is an inspection file, not a blind grading sheet. Rebuild it with `export_excel.py` after any translation change. Keep `.venv`, `models/`, and `results/` out of version control.

All four 75-row runs in this workspace used CPU because PyTorch cannot see CUDA in the Codex shell. The two new `.run.json` manifests record their full resolved revisions and package versions. The completed workbook's ZIP and worksheet XML were verified, and the five workflow tests pass. Bilingual validation of idiom meanings and human translation grades are still needed before semantic-performance claims.
