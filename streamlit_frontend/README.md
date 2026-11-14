# Idiom Lab — portable Streamlit frontend

Pull the latest `doughn1g/NLP` repository to get `streamlit_frontend/` next to
`baseline.py`. No existing research files need editing. The folder can also live
elsewhere: select the repository path in the sidebar or set `NLP_REPO_ROOT` before
launch.

## What is included

- **Compare / Saved experiment:** choose an idiom and see the four existing
  English translations in a two-column layout. Draft intended meanings are
  explicitly marked as provisional reviewer aids.
- **Compare / Live models:** type an idiom or select a dataset example, choose
  models, and run real inference on the machine hosting Streamlit. Progress,
  per-model errors, elapsed time, device, and process logs are shown. Download
  successful and failed results as CSV or JSON.
- **Browse results:** filter by language, search source text/IDs/draft meanings,
  and download a comparison CSV. Missing files are handled as missing results,
  never replaced with made-up translations.
- **Setup & handoff:** short in-app setup guidance.

This is a research inspection tool. Model names and draft meanings are visible;
it is **not a blind grading tool** and does not calculate semantic accuracy.
Use the original repository's blind-review exports for formal evaluation.

## Quick start for the teammate with the cluster

Expected layout:

```text
NLP/
├── baseline.py
├── requirements.txt
├── data/idioms_to_en_draft.jsonl
├── models/                         # existing Hugging Face cache
├── results/idioms_to_en/            # optional existing outputs
└── streamlit_frontend/
    ├── app.py
    ├── backend.py
    ├── style.html
    ├── requirements.txt
    ├── README.md
    ├── .env.example
    └── tests/
```

From the repository root, use the **same Python environment** that already runs
the model experiment. The repo's Python 3.10 environment is suitable; use Python
3.12 for a new local preview. The UI dependency is pinned to Streamlit 1.50.0.
This folder does not reinstall PyTorch or the research packages. Do not assume
newer Python releases are compatible with this pinned dependency stack.

```bash
cd /path/to/NLP
source .venv/bin/activate
python -m pip install -r streamlit_frontend/requirements.txt
python -m streamlit run streamlit_frontend/app.py \
  --server.address 127.0.0.1 --server.port 8501 \
  --server.headless true --browser.gatherUsageStats false
```

If the model environment is Conda, activate that environment instead of `.venv`.
Install the UI requirement on a networked machine or via your cluster's normal
package mirror/wheelhouse. No install is triggered by opening the app.

### Local Windows preview without model dependencies

In Command Prompt, from the repository root, explicitly select Python 3.12:

```bat
py install 3.12
py -3.12 -m venv streamlit_frontend\.venv312
streamlit_frontend\.venv312\Scripts\python.exe -m pip install --upgrade pip
streamlit_frontend\.venv312\Scripts\python.exe -m pip install --only-binary=:all: -r streamlit_frontend\requirements.txt
streamlit_frontend\.venv312\Scripts\python.exe -m streamlit run streamlit_frontend\app.py
```

`py install` requires the current Windows Python install manager. With the older
launcher, install Python 3.12 separately first, then start at `py -3.12 -m venv`.
The new `.venv312` folder avoids overwriting an existing environment. Activation
and a `(.venv)` prompt are unnecessary because the commands use its Python
directly. Open http://localhost:8501. Saved mode works without model dependencies;
missing result files show empty states.

If pip tries to compile pandas and reports missing `vswhere.exe`, check the
environment's Python version. An environment created with Python 3.15 can trigger
this failure with the pinned Streamlit/pandas dependencies. Create the Python
3.12 environment above; upgrading pip alone does not change an environment's
Python version. `--only-binary=:all:` avoids attempting native source builds.

For a different model cache, set its path **before launch**:

```bash
export NLP_MODEL_DIR=/scratch/your-user/model-cache
# Optional when this frontend folder is outside the repo:
export NLP_REPO_ROOT=/path/to/NLP
```

Or edit **Connection settings** in the sidebar. Relative cache, dataset, and
results paths resolve against the selected repository, not the shell's current
directory. `.env.example` documents variables; it is not automatically loaded.

## Cluster access from your laptop

Start Streamlit **inside an allocated compute job** with the desired GPU/CPU
resources, following your cluster's scheduling rules. Keep that job alive while
using the app. The app inherits `CUDA_VISIBLE_DEVICES`; `baseline.py` selects CUDA
if PyTorch can see it and otherwise uses CPU. It does not submit scheduler jobs
or connect to another machine's GPU.

For a single remotely accessible host, run this in a terminal on your laptop:

```bash
ssh -N -L 8501:127.0.0.1:8501 your-user@cluster-host
```

When Streamlit runs on a compute node reached through a login node, use an SSH
jump host **if supported by your cluster**:

```bash
ssh -N -J your-user@login-host \
  -L 8501:127.0.0.1:8501 your-user@compute-node
```

Then open **http://localhost:8501** on your laptop. Replace hostnames and username
with your own. Clusters that disallow SSH to compute nodes need their documented
port-forwarding mechanism; a tunnel to the login node alone does not reach an
app bound to the compute node's loopback interface.

Keep the app bound to loopback and use SSH forwarding. This handoff assumes a
trusted user, local repository paths, and an existing allocated environment; it
does not add accounts or public hosting.

## How live inference connects

1. Reads `MODELS` and `TRANSLATORS` from `baseline.py` using Python's AST parser.
   Merely opening the UI does not import or execute the model code. Exact model
   IDs and pinned revisions come from the teammate's repository.
2. Writes **one temporary input row**, containing only an ID, source text,
   source language, and English target. No draft meaning or other model output
   is provided to inference.
3. Calls the existing CLI with an argument list and `shell=False`, using the
   same Python executable as Streamlit:

   ```text
   python -u /path/to/NLP/baseline.py run --model <selector>
     --input <temporary-input> --model-dir <cache> --output <temporary-output>
   ```

4. Runs selected models **one at a time in fresh processes**. This frees model
   memory on process exit, but reloads weights for every request. Model loading
   is included in elapsed time. The app deliberately does not keep four models
   resident in GPU memory.
5. Uses existing checkpoints only: there is no `--download`, and the child
   process has `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`. If checkpoints are
   missing, the cluster owner should prepare them separately with the repo's
   `prepare_models.sh`, then select that same cache directory.
6. Validates the returned example, language, model ID, revision, and translation.
   A model failure is displayed without discarding successful models. Remaining
   selected models are still attempted.
7. Deletes temporary input/output/log files when the request finishes. Results
   remain in browser-session memory until replaced or the session expires;
   download them to keep them. Benchmark JSONL files and review files are never
   overwritten by live requests.

An OS file lock permits one live request per repository across app sessions on
the same host using the same temp directory. It does not coordinate with other
hosts or with independently launched benchmark jobs. Avoid running this app and
another GPU experiment in the same allocation at the same time.

The per-model timeout defaults to 30 minutes and is adjustable up to four hours.
An expired subprocess is terminated before the next model starts. A Streamlit
rerun that closes the request also terminates its current subprocess. Closing a
browser tab does not guarantee immediate cancellation; the server-side request
may continue until Streamlit closes it, it finishes, or its timeout expires.

## Saved results and local development without models

Saved mode needs only Streamlit, `baseline.py` for its literal configuration,
and the source dataset. It does **not** require PyTorch or model checkpoints.
Without result files, the app shows the source idioms and clear empty states.
There are no simulated translations.

To see actual saved results without a cluster, obtain these files from the
experiment owner and place them in the configured results folder:

```text
nllb.jsonl             nllb.jsonl.run.json
qwen.jsonl             qwen.jsonl.run.json
madlad.jsonl           madlad.jsonl.run.json
m2m100.jsonl           m2m100.jsonl.run.json
```

Partial sets are supported. Every loaded output must have valid IDs, matching
languages, the current model revision, and nonempty translations. If a run
manifest exists, its input SHA-256 must match the selected dataset. Files with
invalid/mismatched data are skipped with a warning. Without a manifest, an
explicit warning explains that the original source text cannot be verified.
Use **Refresh saved files** after a benchmark run finishes. The app does not
import the private blind-review mapping or display invented accuracy scores.

CSV downloads include a UTF-8 BOM for multilingual Excel compatibility and
escape formula-like text as literal cells. Raw JSON downloads preserve live
output text unchanged.

## Checks for the recipient (no model weights required)

All 12 model-free checks passed locally on Windows with Python 3.12. They verify
the adapter and Streamlit interface without loading checkpoints. Actual model
inference still requires validation on the cluster using its existing model
environment and cache.

Backend checks use temporary fake CLI workers, never actual models:

```bash
python -m unittest discover -s streamlit_frontend/tests -p 'test_backend.py' -v
```

Streamlit smoke checks use its in-process testing API and never submit a live
translation:

```bash
python -m unittest discover -s streamlit_frontend/tests -p 'test_app.py' -v
```

Before using real models, verify in your environment:

1. Saved mode opens, language/idiom selections work, and missing files are clear.
2. Saved JSONL outputs appear and filtered CSV downloads contain the expected rows.
3. Start a live request with **one model and one idiom**. Confirm the language,
   device, and output agree with a direct `baseline.py` run on that node.
4. Try all four models sequentially, then check that the existing benchmark
   results and review exports were not altered.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| `baseline.py` not found | Set the repository path in Connection settings. |
| Missing source dataset | Select the correct JSONL path. Custom live text still works without the source dataset. |
| No saved translations | Select the directory containing the four raw JSONL files, not an XLSX/CSV export. |
| Missing cached snapshot | Run `prepare_models.sh` separately in a networked terminal; use the same cache path. |
| `ModuleNotFoundError` in model log | Start Streamlit with the model environment's Python; install the repo's pinned requirements there. |
| NLLB/M2M100 loading errors | The repo requires a compatible PyTorch 2.6+ build for its official `.bin` loading path. |
| CUDA unavailable / CPU shown | Check the compute allocation and PyTorch CUDA visibility in the launch environment. |
| GPU out of memory | Stop conflicting experiments or request more GPU memory. Selecting one model does not reduce that model's own memory requirements. |
| Timeout | Increase the limit in Connection settings or use an appropriately provisioned node. |
| Another request is running | Wait for that session to finish; requests are serialized rather than queued. |
| File still writing / invalid JSON | Let the existing run complete and refresh. |

All added files live in this folder. To remove the UI, remove the folder; the
research backend requires no rollback.
