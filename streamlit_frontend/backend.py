"""Standard-library adapter; importing this module never imports ML libraries."""

from __future__ import annotations

import ast
from contextlib import contextmanager
import csv
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


LANGUAGES = {"zh": "Mandarin Chinese", "ta": "Tamil", "tl": "Tagalog"}
LABELS = {
    "nllb": "NLLB-200 · 600M",
    "qwen": "Qwen3 Instruct · 4B",
    "madlad": "MADLAD-400 · 3B",
    "m2m100": "M2M100 · 418M",
}


@dataclass(frozen=True)
class ModelSpec:
    selector: str
    label: str
    model_id: str
    revision: str


def resolve_path(value, root):
    path = Path(value).expanduser()
    return (path if path.is_absolute() else Path(root) / path).resolve()


def model_specs(repo):
    """Read the repo's pinned configuration without executing baseline.py."""
    path = Path(repo) / "baseline.py"
    if not path.is_file():
        raise ValueError(f"baseline.py was not found in {repo}. Select the NLP repository folder.")
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    config = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("MODELS", "TRANSLATORS"):
                    config[target.id] = ast.literal_eval(node.value)
    translators = config.get("TRANSLATORS", ())
    if set(translators) != set(LABELS) or len(translators) != 4:
        raise ValueError("This frontend expects the repo's four-model TRANSLATORS configuration.")
    result = []
    for selector in translators:
        entry = config.get("MODELS", {}).get(selector, ())
        if len(entry) < 3 or entry[2] != "translation" or not all(isinstance(x, str) and x for x in entry[:2]):
            raise ValueError(f"Unsupported model configuration for {selector}.")
        result.append(ModelSpec(selector, LABELS[selector], entry[0], entry[1]))
    return result


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{Path(path).name}, line {number}: invalid JSON. The file may still be writing.") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{Path(path).name}, line {number}: expected a JSON object.")
            rows.append(row)
    if not rows:
        raise ValueError(f"{Path(path).name} is empty.")
    return rows


def load_examples(path):
    rows = read_jsonl(path)
    seen = set()
    for row in rows:
        ident = row.get("id")
        if not isinstance(ident, str) or not ident.strip() or ident in seen:
            raise ValueError("Source data contains a missing or duplicate example ID.")
        if row.get("source_lang") not in LANGUAGES or row.get("target_lang") != "en":
            raise ValueError(f"{ident}: expected a supported source language and English target.")
        if not isinstance(row.get("source_text"), str) or not row["source_text"].strip():
            raise ValueError(f"{ident}: source text is empty.")
        seen.add(ident)
    return rows


def load_saved(directory, source_path, examples, specs):
    """Return only validated, current-revision predictions plus visible warnings."""
    by_id = {row["id"]: row for row in examples}
    predictions, warnings = {}, []
    source_hash = hashlib.sha256(Path(source_path).read_bytes()).hexdigest()
    for spec in specs:
        path = Path(directory) / f"{spec.selector}.jsonl"
        if not path.is_file():
            continue
        try:
            manifest_path = Path(str(path) + ".run.json")
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
                if not isinstance(manifest, dict) or manifest.get("input_sha256") != source_hash:
                    raise ValueError("run manifest does not match the selected source file; outputs were not loaded")
            else:
                warnings.append(f"{path.name}: no run manifest; the original source text cannot be verified.")
            pending = {}
            for row in read_jsonl(path):
                ident = row.get("id")
                if not isinstance(ident, str) or ident not in by_id:
                    raise ValueError("contains an unknown example ID")
                if ident in pending:
                    raise ValueError("contains duplicate example IDs")
                source = by_id[ident]
                if row.get("model_id") != spec.model_id or row.get("revision") != spec.revision:
                    raise ValueError("model identity or revision differs from baseline.py")
                if (row.get("source_lang"), row.get("target_lang")) != (source["source_lang"], "en"):
                    raise ValueError("language direction differs from the source data")
                if not isinstance(row.get("translation"), str) or not row["translation"].strip():
                    raise ValueError("contains an empty translation")
                pending[ident] = row
            predictions.update({(ident, spec.selector): row for ident, row in pending.items()})
        except (OSError, ValueError) as exc:
            warnings.append(f"{path.name}: {exc}. Refresh after the file is complete, or select the correct results folder.")
    return predictions, warnings


def comparison_rows(examples, predictions, specs):
    return [
        {"id": row["id"], "source_language": LANGUAGES[row["source_lang"]],
         "source_text": row["source_text"], "draft_meaning": row.get("intended_meaning", ""),
         **{spec.selector: predictions.get((row["id"], spec.selector), {}).get("translation", "") for spec in specs}}
        for row in examples
    ]


def csv_bytes(rows):
    if not rows:
        return b""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    # CSVs are opened in spreadsheet apps. Keep user/model text as text cells.
    for row in rows:
        safe = {key: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value
                for key, value in row.items()}
        writer.writerow(safe)
    return output.getvalue().encode("utf-8-sig")


@contextmanager
def inference_lock(repo):
    """OS lock auto-releases on exit; serialize this repo's local app sessions."""
    digest = hashlib.sha256(str(Path(repo).resolve()).encode()).hexdigest()[:24]
    path = Path(tempfile.gettempdir()) / f"nlp-streamlit-{digest}.lock"
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        acquired = False
        try:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as exc:
                raise RuntimeError("Another frontend request is using this repository. Try again when it finishes.") from exc
            yield
        finally:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def stop_process(process):
    if process.poll() is None:
        if os.name == "nt":
            # A Windows venv's python.exe may launch another interpreter. Stop
            # its entire owned tree so model memory and log handles are freed.
            taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
            stopped = subprocess.run([str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            if stopped.returncode and process.poll() is None:
                raise RuntimeError("Could not stop the model process tree. Stop its Python processes before retrying.")
        else:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def run_live(repo, model_dir, language, text, selected, timeout=1800):
    """Yield progress/results. Close this generator to stop its active subprocess.

    Every model gets a fresh process and only source text + language direction.
    No model downloads, reference meanings, shell execution, or benchmark writes.
    """
    repo, model_dir = Path(repo).resolve(), Path(model_dir).resolve()
    specs = {spec.selector: spec for spec in model_specs(repo)}
    if language not in LANGUAGES or not isinstance(text, str) or not text.strip() or len(text) > 3000:
        raise ValueError("Choose a supported language and enter 1–3,000 characters.")
    if not selected or len(set(selected)) != len(selected) or any(item not in specs for item in selected):
        raise ValueError("Select at least one of the four translation models.")
    if timeout <= 0:
        raise ValueError("The per-model timeout must be positive.")
    if not model_dir.is_dir():
        raise ValueError(f"Model cache does not exist: {model_dir}. Use the cache prepared by prepare_models.sh.")
    with inference_lock(repo), tempfile.TemporaryDirectory(prefix="nlp-streamlit-job-") as work:
        work = Path(work)
        input_path = work / "input.jsonl"
        request = {"id": "frontend-request", "source_lang": language, "target_lang": "en", "source_text": text.strip()}
        input_path.write_text(json.dumps(request, ensure_ascii=False) + "\n", encoding="utf-8")
        for selector in selected:
            spec = specs[selector]
            output_path, log_path = work / f"{selector}.jsonl", work / f"{selector}.log"
            command = [sys.executable, "-u", str(repo / "baseline.py"), "run", "--model", selector,
                       "--input", str(input_path), "--model-dir", str(model_dir), "--output", str(output_path)]
            environment = os.environ.copy()
            environment.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
            started = time.monotonic()
            yield {"type": "started", "selector": selector}
            process = None
            try:
                with log_path.open("wb") as destination:
                    process = subprocess.Popen(command, cwd=str(repo), env=environment, stdin=subprocess.DEVNULL,
                                               stdout=destination, stderr=subprocess.STDOUT, shell=False)
                    with log_path.open(encoding="utf-8", errors="replace") as log:
                        while True:
                            chunk = log.read()
                            if chunk:
                                yield {"type": "log", "selector": selector, "text": chunk}
                            elapsed = time.monotonic() - started
                            if process.poll() is not None:
                                chunk = log.read()
                                if chunk:
                                    yield {"type": "log", "selector": selector, "text": chunk}
                                break
                            if elapsed > timeout:
                                raise TimeoutError(f"Exceeded the {timeout:g}-second per-model limit. Increase it in Connection settings.")
                            yield {"type": "heartbeat", "selector": selector, "seconds": elapsed}
                            time.sleep(0.5)
                if process.returncode != 0:
                    raise RuntimeError(f"Model process exited with code {process.returncode}. See the process log below.")
                rows = read_jsonl(output_path)
                if len(rows) != 1:
                    raise ValueError("Expected exactly one model prediction.")
                result = rows[0]
                if any(result.get(key) != request[key] for key in ("id", "source_lang", "target_lang")):
                    raise ValueError("The model returned an unexpected example or language direction.")
                if result.get("model_id") != spec.model_id or result.get("revision") != spec.revision:
                    raise ValueError("The model returned an unexpected model identity or revision.")
                if not isinstance(result.get("translation"), str) or not result["translation"].strip():
                    raise ValueError("The model returned an empty translation.")
                manifest = json.loads(Path(str(output_path) + ".run.json").read_text(encoding="utf-8"))
                if not isinstance(manifest, dict):
                    raise ValueError("The model run manifest must be a JSON object.")
                yield {"type": "result", "selector": selector, "translation": result["translation"],
                       "model_id": spec.model_id, "revision": spec.revision, "device": manifest.get("device", "unknown"),
                       "seconds": round(time.monotonic() - started, 1)}
            except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
                yield {"type": "error", "selector": selector, "message": str(exc)}
            finally:
                if process is not None:
                    stop_process(process)
