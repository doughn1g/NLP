# Idiom translation comparison

<!-- BEGIN PUBLIC RESULTS -->
## Current results: 75 isolated idioms

The [published results snapshot](published_results/idioms_to_en_75/README.md) contains all four raw translation files, run manifests, a side-by-side workbook, and 300 preliminary semantic decisions. On the 0–2 meaning rubric, full-credit counts out of 25 idioms per language were:

| Source language | NLLB-200 | Qwen3-4B-Instruct | MADLAD-400-3B-MT | M2M100-418M |
| --- | ---: | ---: | ---: | ---: |
| Mandarin → English | 0 | 12 | 3 | 0 |
| Tamil → English | 0 | 0 | 0 | 0 |
| Tagalog → English | 0 | 2 | 0 | 0 |
| **Total / 75** | **0** | **14** | **3** | **0** |

These are **preliminary AI judgments**, not validated bilingual scores. Naturalness has not been graded. The inputs are isolated idioms rather than full sentences, so this table does not measure in-context translation. The [semantic summary CSV](published_results/idioms_to_en_75/GRADED_75_IDIOMS_4_MODELS_SEMANTIC_SUMMARY.csv) includes partial-credit and zero-credit counts; the [graded workbook](published_results/idioms_to_en_75/GRADED_75_IDIOMS_4_MODELS_SEMANTIC_DRAFT.xlsx) shows each case.
<!-- END PUBLIC RESULTS -->

This project compares four translation models on 75 draft idioms translated into English: 25 each from simplified Mandarin Chinese, Tamil, and Tagalog. The models are NLLB-200 distilled 600M, Qwen3-4B-Instruct-2507, MADLAD-400-3B-MT, and M2M100-418M. All four translate the same source IDs independently. The current inputs are isolated phrases, and bilingual grading has not yet been done.

**For a coding agent:** start with [AGENTS.md](AGENTS.md), then read [AGENTS.override.md](AGENTS.override.md) for the research brief. The [complexity audit](data/idiom_complexity_audit.md) explains why these are not all high-complexity idioms.

**For project users:** [USAGE_GUIDE.md](USAGE_GUIDE.md) explains setup, commands, result files, and blind grading.

## Quick start

Use Python 3.10 and a project-local `.venv`. Install an official PyTorch 2.6 build suitable for your CPU or GPU, then install `requirements.txt`. Allow about 45 GB for packages and the four checkpoints. `prepare_models.sh` checks model-cache space before downloading pinned files from the official publishers.

```bash
virtualenv .venv
.venv/bin/pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r requirements.txt
bash prepare_models.sh
.venv/bin/python -m unittest discover -s tests -q
bash run_four_idioms.sh
```

For CUDA 12.4, install PyTorch from `https://download.pytorch.org/whl/cu124` instead of the CPU index and verify `torch.cuda.is_available()` in the inference terminal. Pass a model cache path as the first argument to both shell scripts to store weights on another drive.

The run creates `results/idioms_to_en/FINAL_75_IDIOMS_4_MODELS_UNGRADED.xlsx` with one row per idiom and all four model translations, plus a 300-row blind grading CSV and private mapping. The workbook contains draft meanings and model names for inspection; give reviewers only the blind CSV. The source idioms, meanings, and provisional complexity labels require bilingual review before benchmark claims.

Model weights, Python environments, and generated results stay local and are ignored by Git. See [AGENTS.md](AGENTS.md) for exact model revisions, output files, grading rubric, and reproduction details.

To publish the source to `doughn1g/NLP` from a networked terminal, run `bash publish_to_github.sh`. If Git is unavailable, first run `bash install_portable_git.sh` to unpack a local Git binary without `sudo`. The publish script stops if an existing remote file differs; it never stages the local model cache or results.
