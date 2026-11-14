# How to use this project

This project compares four translation models on the **same 75 draft idioms**: 25 each from simplified Mandarin Chinese (`zh`), Tamil (`ta`), and Tagalog (`tl`), all translated into English. The models are NLLB-200 distilled 600M, Qwen3-4B-Instruct-2507, MADLAD-400-3B-MT, and M2M100-418M. The aim is to find which translations best preserve the idioms' meanings. **No model has been declared the winner:** bilingual review and translation grading are still pending.

Run commands below from the `nlpproj` folder. Read [AGENTS.md](AGENTS.md) for the current project state and exact model revisions, and [AGENTS.override.md](AGENTS.override.md) for the research brief.

## Where things are

| Path | Purpose |
| --- | --- |
| `data/idioms_to_en_draft.jsonl` | The 75 source idioms, IDs, language codes, and draft meanings. The meanings are reviewer aids and are never passed to models. |
| `data/idiom_complexity_audit.md` | Provisional low/medium/high complexity judgments. |
| `data/pilot.jsonl`, `data/pilot_candidates.jsonl` | Earlier 12-example pilot fixtures. They are separate from the current 75-idiom comparison. |
| `data/petci/` | Mandarin sourcing reference and its license; the reference file is not a reviewed benchmark. |
| `baseline.py` | Input validation, model inference, raw predictions, blind review export, and scoring. |
| `export_excel.py` | Creates the Excel comparison workbook from the four raw prediction files. |
| `run_four_idioms.sh` | Runs/resumes all four translation models, then builds the comparison and review files. |
| `prepare_models.sh` | Downloads all four pinned checkpoints into a chosen cache directory. |
| `download_new_models.sh` | Downloads only MADLAD and M2M100 if NLLB and Qwen are already cached. |
| `tests/` | Pipeline checks that do not download model weights. |
| `models/`, `.venv/`, `results/` | Local model cache, Python environment, and generated output. Git ignores these directories. |

## Set up on a new machine

Use Python 3.10 and allow roughly 45 GB for the environment and checkpoints. Check free disk space, memory, and GPU visibility before downloading. Install a PyTorch 2.6 build appropriate for the machine; the command below is for CPU. For a compatible NVIDIA GPU, use the appropriate wheel index from [PyTorch](https://pytorch.org/get-started/previous-versions/) and confirm that `torch.cuda.is_available()` is `True` in the same terminal used for inference.

```bash
cd /path/to/nlpproj
python3.10 -m venv .venv
.venv/bin/python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -q
bash prepare_models.sh
```

`prepare_models.sh` checks for at least 35 GB free in the cache location before downloading. To keep weights on another drive, pass its directory as the first argument, for example `bash prepare_models.sh /path/to/model-cache`. Use the same path when running the models. The scripts download pinned revisions from official Hugging Face publishers. Keep the environment and weights out of Git.

## Validate and run the 75 idioms

First validate the input without loading any model library:

```bash
.venv/bin/python baseline.py run --model nllb --input data/idioms_to_en_draft.jsonl --dry-run
```

Run all four models sequentially. The script uses `--resume`, so a completed prediction file is reused after an interruption. It then **recreates the review exports**; save a copy of any graded review CSV before rerunning it.

```bash
bash run_four_idioms.sh
```

For weights on another drive, use `bash run_four_idioms.sh /path/to/model-cache`. To select one visible NVIDIA GPU, run `CUDA_VISIBLE_DEVICES=0 bash run_four_idioms.sh` after confirming PyTorch can see CUDA. The script can run on CPU, but the larger models will be slower. To test one row for a single model, see the `baseline.py run` examples in [AGENTS.override.md](AGENTS.override.md).

## Read the results

The current completed files are under `results/idioms_to_en/`:

| File | Use |
| --- | --- |
| `FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx` | Main inspection workbook: one row per source idiom, four translations, draft meaning, complexity, and blank grading columns. Open the `Comparison` and `Run info` sheets. |
| `FINAL_75_IDIOMS_4_MODELS_SIDE_BY_SIDE.csv` | Plain CSV version of the source text, draft meaning, and four model translations. |
| `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv` | 300 randomized rows for reviewers. Model identities are hidden. |
| `FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl` | Links blind row IDs to source IDs and model identities. Keep private from blind reviewers. |
| `nllb.jsonl`, `qwen.jsonl`, `madlad.jsonl`, `m2m100.jsonl` | Raw translations keyed by source ID. Each has a matching `.run.json` manifest with model revision, device, package versions, and generation settings. |

`results/archive_prior_runs/` holds older pilot, smoke, and two-model outputs. They are **not** the current four-model comparison. Generated results are ignored by Git, so a fresh GitHub clone must run the workflow to recreate them or receive them through a separate authorized transfer.

## Grade the translations

Give bilingual reviewers a **copy** of `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv`; keep the mapping and the side-by-side files private until grading is complete. Preserve `row_id` and fill `meaning_0_2`, `naturalness_0_2`, and optional `reviewer_notes`:

- Meaning: `2` = intended meaning preserved, `1` = partly preserved, `0` = wrong or missing. An accurate paraphrase can earn `2`.
- Naturalness: `2` = fluent English, `1` = understandable but awkward, `0` = unclear or wrong language.

After saving the completed CSV as a separate file, calculate scores:

```bash
.venv/bin/python baseline.py score-translation \
  --review results/idioms_to_en/graded_review.csv \
  --mapping results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl \
  --output results/idioms_to_en/graded_scores.csv
```

The score table reports each model and language direction with a rated count, the share receiving full meaning credit, and mean naturalness. It labels the current examples as **draft**. Review the idiom forms, meanings, and translations with bilingual speakers before presenting scores as benchmark findings. The current items are isolated phrases, so they do not yet measure translation of idioms in full sentence context.

## Commit source changes

Source code, documentation, tests, and draft data belong in Git. The local `models/`, `.venv/`, and `results/` directories do not. If a normal Git checkout is available, use `git status`, stage the intended source files, and commit. On this machine, `publish_to_github.sh` creates a temporary checkout and publishes listed source files to `doughn1g/NLP`; see [README.md](README.md) for the portable Git setup. GitHub HTTPS authentication may request a personal access token. Never put the token in a command, file, or chat message.
