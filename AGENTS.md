# Agent handoff: cross-language idiom translation

Read this file first, then `AGENTS.override.md` for the full research brief. Work from the `nlpproj` directory. The current task is a **four-model translation comparison**, not an embedding-rank comparison.

## What this project does

Translate the same 75 draft idioms into English with four independent models: 25 source idioms each in simplified Mandarin Chinese (`zh`), Tamil (`ta`), and Tagalog (`tl`). The four checkpoints are NLLB-200 distilled 600M, Qwen3-4B-Instruct-2507, MADLAD-400-3B-MT, and M2M100-418M. The current input contains isolated idiom phrases, not contextual sentences. Do not claim a winner until bilingual reviewers verify the data and grade the outputs.

| Selector | Official Hugging Face repo | Pinned revision |
| --- | --- | --- |
| `nllb` | `facebook/nllb-200-distilled-600M` | `f8d333a098d19b4fd9a8b18f94170487ad3f821d` |
| `qwen` | `Qwen/Qwen3-4B-Instruct-2507` | `cdbee75f17c01a7cc42f958dc650907174af0554` |
| `madlad` | `google/madlad400-3b-mt` | `fa184c675da0b5c9e1c8694fccd4e12e2d422094` |
| `m2m100` | `facebook/m2m100_418M` | `55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636` |

`baseline.py` contains the exact model selectors, generation logic, validation, blind review, and scoring. The earlier LaBSE/Qwen Embedding candidate-ranking code and `legacy/run_gpu_pilot.sh` are historical pilot work. They are not part of the current four-model comparison.

## Repository map

- `data/idioms_to_en_draft.jsonl`: 75 source idioms, unique IDs, draft English meanings, provenance, and `review_status: draft`.
- `build_idiom_draft.py`: recreates the 75-row input. Do not regenerate it after inference if you have edited the source list; `--resume` checks row IDs but does not detect changed source text.
- `data/idiom_complexity_audit.md`: provisional 27 high, 30 medium, 18 low complexity labels. These need bilingual confirmation.
- `data/pilot.jsonl` and `data/pilot_candidates.jsonl`: historical 12-row pipeline fixtures.
- `data/petci/`: Chinese source material with its own license and README.
- `requirements.txt`: pinned Python dependencies other than PyTorch.
- `prepare_models.sh`: downloads all four pinned translation checkpoints. `download_new_models.sh` downloads only MADLAD and M2M100 if the first two are already cached.
- `run_four_idioms.sh`: runs one model at a time, resumes complete outputs, then exports the workbook, CSV, and blind review.
- `publish_to_github.sh`: clones `https://github.com/doughn1g/NLP`, checks for conflicting existing files, and commits and pushes only the source tree from a temporary working copy. It requires Git and GitHub authentication in the terminal.
- `install_portable_git.sh`: if system Git is missing, downloads the Ubuntu Git package into ignored `.local-tools/` without `sudo`. Run it in a networked terminal before publishing.
- `export_excel.py`: builds the `.xlsx` workbook using the Python standard library. It rejects missing model translations unless `--allow-missing` is specified.
- `tests/`: code-only workflow and export tests. No model weights are needed for these tests.
- `models/`, `.venv/`, `results/`: local-only files ignored by Git. Preserve them when working on this machine; recreate them on a fresh clone.
- `results/idioms_to_en/`: current four-model outputs. The `FINAL_75_IDIOMS_4_MODELS_*` files are the current comparison and review exports. `results/archive_prior_runs/` holds older pilot, smoke, and superseded two-model files.

## Fresh setup

1. Check Python, storage, RAM, and GPU. Python 3.10 worked here. Allow roughly 45 GB for the four checkpoints, Python packages, and cache. `prepare_models.sh` requires at least 35 GB free in the model-cache directory before it downloads. A CUDA-capable terminal is optional; CPU runs are supported but slower.
2. Create a local environment. This host's system Python lacks `ensurepip`, so `virtualenv .venv` worked here. On a host with a working `venv`, `python3 -m venv .venv` is also fine.
3. Install a compatible PyTorch 2.6 build, then the pinned requirements. Choose the official PyTorch index for the actual device; the examples below are for Linux CPU or CUDA 12.4. Verify `torch.cuda.is_available()` in the same terminal that will run inference.

```bash
virtualenv .venv
# Choose one of these PyTorch commands:
.venv/bin/pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
# .venv/bin/pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c 'import torch; print(torch.__version__, torch.cuda.is_available())'
```

4. In a terminal with access to Hugging Face, download the official pinned checkpoints. Use another drive by passing its cache path as the first argument. Keep that same path for the run script.

```bash
bash prepare_models.sh
# or: bash prepare_models.sh /path/to/large/model-cache
```

MADLAD uses publisher SafeTensors. NLLB and M2M100 use publisher PyTorch `.bin` files, which need PyTorch 2.6 or later for this loading path. `protobuf==4.21.12` is required by MADLAD's tokenizer and is pinned in `requirements.txt`.

## Verify and run

Run code-only checks and validate all 75 input rows before inference:

```bash
.venv/bin/python -m unittest discover -s tests -q
for model in nllb qwen madlad m2m100; do
  .venv/bin/python baseline.py run --model "$model" --input data/idioms_to_en_draft.jsonl --dry-run
done
```

For a fresh cache, smoke test one row per model with `--limit 1` and separate `*_smoke.jsonl` outputs, then run the full workflow. Run one checkpoint at a time to limit memory use. On this machine, the Codex shell could not see CUDA; all four 75-row runs completed on CPU. A VS Code terminal may expose the GPUs.

```bash
mkdir -p results/idioms_to_en
for model in nllb qwen madlad m2m100; do
  .venv/bin/python baseline.py run --model "$model" \
    --input data/idioms_to_en_draft.jsonl --model-dir models --limit 1 \
    --output "results/idioms_to_en/${model}_smoke.jsonl"
done
bash run_four_idioms.sh
# or: CUDA_VISIBLE_DEVICES=0 bash run_four_idioms.sh /path/to/large/model-cache
```

The script produces `results/idioms_to_en/{nllb,qwen,madlad,m2m100}.jsonl`, adjacent `.run.json` manifests, `FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx`, `FINAL_75_IDIOMS_4_MODELS_SIDE_BY_SIDE.csv`, `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv`, and `FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl`. The workbook has one row per idiom with all four English translations and blank grading columns. `FINAL` identifies the completed translation run; `UNGRADED` makes clear that human evaluation is pending. It includes draft meanings and model names, so it is **not** blind. Give graders only `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv`; keep the private mapping separate.

Each `.run.json` manifest records the model revision, resolved snapshot commit, device, package versions, input SHA-256, and generation settings. The four current output files each have 75 unique nonempty predictions. The blind file has 300 unscored rows. The current results live only in the ignored `results/` directory; a GitHub clone must run the workflow to recreate them.

## Review and reporting

The source list and English glosses are drafts. The complexity audit is an analyst judgment, not a native-speaker rating. Before reporting benchmark accuracy, bilingual reviewers must validate each idiom, gloss, and source-language usage. A known priority is the isolated Tagalog `naglalaro ng apoy`, whose handout meaning is narrower than the draft gloss. The Tamil set includes several single figurative words and only 3 provisionally high-complexity items.

Blind graders fill `meaning_0_2`, `naturalness_0_2`, and `reviewer_notes` in `FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv`. Meaning: 2 = intended sense preserved, 1 = partial, 0 = wrong or missing. Naturalness: 2 = fluent English, 1 = awkward but understandable, 0 = unclear or wrong language. An accurate paraphrase can receive full meaning credit. Score only after review:

```bash
.venv/bin/python baseline.py score-translation \
  --review results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_BLIND_REVIEW.csv \
  --mapping results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_PRIVATE_MAPPING.jsonl \
  --output results/idioms_to_en/four_model_scores.csv
```

Report rated counts, full-meaning share, and mean naturalness by model and language direction. Keep draft scores distinct from a later reviewed held-out benchmark. English-source directions, contextual sentence examples, ordinary-sentence controls, fine-tuning, and negation are later work.

## GitHub readiness

Commit source code, tests, documentation, the small draft data, and the PETCI license/provenance. The `.gitignore` excludes `.venv/`, `.local-tools/`, `models/`, `results/`, caches, local agent directories, and credentials. Do not add model weights, private review mapping, local environments, or generated results to Git. The parent `FYP` directory contains unrelated OpenVLA work and large files. This Codex shell has no system `git` executable and shows an empty local `.git` directory. The authorized push to `doughn1g/NLP` uses `bash publish_to_github.sh` from a networked VS Code terminal; the script clones the remote into `/tmp`, refuses to overwrite different existing files, and stages only the listed source paths. If system Git is missing, first run `bash install_portable_git.sh`. To use a chosen commit identity without sending the email to an agent, run `PUBLISH_AUTHOR_NAME="Your Name" PUBLISH_AUTHOR_EMAIL="you@example.com" bash publish_to_github.sh`. GitHub authentication must also be available in that terminal; commit identity and push authentication are separate.
