"""Launch with: python -m streamlit run streamlit_frontend/app.py"""

from contextlib import closing
import json
import os
from pathlib import Path

import streamlit as st

from backend import (LANGUAGES, comparison_rows, csv_bytes, load_examples, load_saved,
                     model_specs, resolve_path, run_live)


st.set_page_config(page_title="Idiom Lab | Translation comparison", page_icon="🌐", layout="wide")
st.markdown((Path(__file__).parent / "style.html").read_text(encoding="utf-8"), unsafe_allow_html=True)


def render_cards(specs, outputs, live=False):
    for start in range(0, len(specs), 2):
        columns = st.columns(2)
        for column, spec in zip(columns, specs[start:start + 2]):
            with column, st.container(border=True):
                st.subheader(spec.label)
                item = outputs.get(spec.selector)
                if item and item.get("translation"):
                    st.text(item["translation"])
                    if live:
                        st.caption(f"{item.get('device', 'unknown')} · {item['seconds']:.1f}s including model loading")
                    else:
                        st.caption("Saved model output")
                elif item and item.get("error"):
                    st.error(item["error"])
                else:
                    st.caption("No saved translation yet." if not live else "No result for this model.")


def download_live(job, specs):
    rows = [{"source_language": LANGUAGES[job["language"]], "source_text": job["text"],
             "model": spec.selector, "model_id": spec.model_id, "revision": spec.revision,
             "translation": job["outputs"].get(spec.selector, {}).get("translation", ""),
             "device": job["outputs"].get(spec.selector, {}).get("device", ""),
             "elapsed_seconds": job["outputs"].get(spec.selector, {}).get("seconds", ""),
             "error": job["outputs"].get(spec.selector, {}).get("error", "")}
            for spec in specs if spec.selector in job["selected"]]
    csv_col, json_col = st.columns(2)
    csv_col.download_button("Download translations · CSV", csv_bytes(rows), "live_translations.csv", "text/csv")
    json_col.download_button("Download translations · JSON", json.dumps(rows, ensure_ascii=False, indent=2),
                             "live_translations.json", "application/json")


with st.sidebar:
    st.markdown("### 🌐 Idiom Lab")
    st.caption("Four perspectives. One intended meaning.")
    page = st.radio("Workspace", ["Compare translations", "Browse results", "Setup & handoff"], label_visibility="collapsed", key="workspace")
    st.divider()
    with st.expander("Connection settings", expanded=False):
        repo_text = st.text_input("NLP repository", os.environ.get("NLP_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))
        st.caption("Folder containing baseline.py. Relative data/cache paths start here.")
        source_text = st.text_input("Source dataset", os.environ.get("NLP_DATA_PATH", "data/idioms_to_en_draft.jsonl"))
        result_text = st.text_input("Saved results folder", os.environ.get("NLP_RESULTS_DIR", "results/idioms_to_en"))
        cache_text = st.text_input("Model cache folder", os.environ.get("NLP_MODEL_DIR", "models"))
        timeout_minutes = st.number_input("Time limit per model (minutes)", min_value=1, max_value=240, value=30)
    st.button("Refresh saved files", use_container_width=True)
    st.caption("Mandarin Chinese / Tamil / Tagalog → English")
    st.caption("Research comparison · Human grading pending")

st.caption("CROSS-LANGUAGE IDIOMS")
st.title("Meaning, across languages.")
st.write("Compare how four translation models express the same idiom in English.")

if page == "Setup & handoff":
    st.subheader("Connect to the existing research code")
    st.write("Copy this entire folder into the NLP repository, beside baseline.py. Use the same Python environment and model cache as the existing experiment.")
    st.code("python -m pip install -r streamlit_frontend/requirements.txt\n"
            "python -m streamlit run streamlit_frontend/app.py --server.address 127.0.0.1 --server.port 8501", language="bash")
    st.write("For a cluster, start Streamlit inside your allocated CPU/GPU job. Inherit CUDA_VISIBLE_DEVICES from the allocation; the app uses baseline.py's existing device selection.")
    st.write("Forward port 8501 over SSH, then open http://localhost:8501 in your own browser. See README.md for commands and troubleshooting.")
    st.info("Live requests use cached checkpoints only. Models run sequentially in separate processes. First results include model-loading time; CPU runs can take much longer.")
    st.write("Saved mode reads existing JSONL outputs. It needs no model weights or PyTorch. Live outputs stay in this browser session until downloaded; benchmark files are never overwritten.")
    st.caption("This is an inspection interface, not a blind grading interface: model identities and draft meanings are visible.")
    st.stop()

try:
    repo = Path(repo_text).expanduser().resolve()
    source_path = resolve_path(source_text, repo)
    results_dir = resolve_path(result_text, repo)
    model_dir = resolve_path(cache_text, repo)
    specs = model_specs(repo)
except (OSError, ValueError, SyntaxError) as exc:
    st.error(str(exc))
    st.info("Open Connection settings and select the folder containing the research repo's baseline.py, or see Setup & handoff.")
    st.stop()

examples, source_error = [], None
try:
    examples = load_examples(source_path)
except (OSError, ValueError) as exc:
    source_error = str(exc)

predictions, warnings = {}, []
if examples:
    predictions, warnings = load_saved(results_dir, source_path, examples, specs)

if page == "Browse results":
    st.subheader("The comparison library")
    if source_error:
        st.error(source_error)
        st.stop()
    language_filter = st.selectbox("Source language", ["all", *LANGUAGES], format_func=lambda x: "All languages" if x == "all" else LANGUAGES[x])
    search = st.text_input("Search idioms or draft meanings", placeholder="Type an idiom, ID, or meaning…")
    filtered = [row for row in examples if (language_filter == "all" or row["source_lang"] == language_filter)
                and search.casefold() in " ".join([row["id"], row["source_text"], row.get("intended_meaning", "")]).casefold()]
    a, b, c = st.columns(3)
    a.metric("Idioms in view", len(filtered))
    available = sum((row["id"], spec.selector) in predictions for row in filtered for spec in specs)
    b.metric("Translations available", f"{available} / {len(filtered) * len(specs)}")
    c.metric("Translation models", len(specs))
    if not predictions:
        st.info("No saved translations found. Ask your teammate for the four JSONL result files, or run the existing experiment on the cluster. The source idioms are listed below.")
    for warning in warnings:
        st.warning(warning)
    table = comparison_rows(filtered, predictions, specs)
    if table:
        st.dataframe(table, hide_index=True, use_container_width=True)
        st.download_button("Download filtered comparison", csv_bytes(table), "idiom_comparison.csv", "text/csv")
    else:
        st.info("No idioms match these filters.")
    st.caption("Blank translations mean no saved output is available. Draft meanings are provisional reviewer aids, not validated reference translations.")
    st.stop()

mode = st.radio("Translation source", ["Saved experiment", "Live models"], horizontal=True, key="translation_mode")
if mode == "Saved experiment":
    if source_error:
        st.error(source_error)
        st.stop()
    language = st.selectbox("Source language", list(LANGUAGES), format_func=LANGUAGES.get)
    choices = [row for row in examples if row["source_lang"] == language]
    if not choices:
        st.info("No idioms for this language in the selected dataset.")
        st.stop()
    example = st.selectbox("Choose an idiom", choices, format_func=lambda row: f"{row['source_text']} · {row['id']}")
    st.caption("Target language: English · Saved outputs are read without loading any models.")
    for warning in warnings:
        st.warning(warning)
    outputs = {spec.selector: predictions[(example["id"], spec.selector)] for spec in specs if (example["id"], spec.selector) in predictions}
    if not outputs:
        st.info("There are no saved translations for this idiom. Select Live models to translate on the cluster, or point Connection settings at existing results.")
    render_cards(specs, outputs)
    with st.expander("Draft intended meaning · reviewer aid"):
        st.text(example.get("intended_meaning") or "No draft meaning supplied.")
        st.caption("Provisional, pending bilingual validation. Never included in a live model request.")
    st.download_button("Download this comparison", csv_bytes(comparison_rows([example], predictions, specs)), "idiom_comparison.csv", "text/csv")
else:
    st.info("Runs on the machine hosting Streamlit. Select one or more models; each loads and finishes before the next starts.")
    languages = list(LANGUAGES)
    language = st.selectbox("Source language", languages, format_func=LANGUAGES.get, key="live_language")
    choices = [row for row in examples if row["source_lang"] == language]
    seed = st.selectbox("Start from an existing idiom (optional)", [None, *choices],
                        format_func=lambda row: "Enter my own idiom" if row is None else row["source_text"])
    # Separate widget keys prevent edits in one language/example leaking into another.
    text_key = f"text_{language}_{seed['id'] if seed else 'custom'}"
    with st.form("live_translation"):
        text = st.text_area("Source idiom", value=seed["source_text"] if seed else "", max_chars=3000,
                            height=120, key=text_key, placeholder="Enter an idiom in the selected source language…")
        selected = st.multiselect("Models to compare", [spec.selector for spec in specs],
                                  default=[spec.selector for spec in specs],
                                  format_func=lambda selector: next(spec.label for spec in specs if spec.selector == selector))
        st.caption("Target: English. Only the source text and language direction are sent to the model runner.")
        submitted = st.form_submit_button("Translate & compare", type="primary", use_container_width=True)
    if submitted:
        if not text.strip() or not selected:
            st.warning("Enter an idiom and select at least one model.")
        else:
            job = {"repo": str(repo), "language": language, "text": text.strip(), "selected": selected, "specs": specs,
                   "outputs": {}, "logs": {}}
            st.session_state["live_job"] = job
            count = 0
            progress = st.progress(0.0, text="Preparing model request…")
            with st.status("Translating…", expanded=True) as status:
                try:
                    with closing(run_live(repo, model_dir, language, text, selected, timeout_minutes * 60)) as events:
                        for event in events:
                            selector = event["selector"]
                            label = next(spec.label for spec in specs if spec.selector == selector)
                            if event["type"] == "started":
                                st.write(f"Loading and translating with {label}…")
                            elif event["type"] == "heartbeat":
                                progress.progress(count / len(selected), text=f"{label} · {event['seconds']:.0f}s elapsed")
                            elif event["type"] == "log":
                                job["logs"][selector] = (job["logs"].get(selector, "") + event["text"])[-16000:]
                            elif event["type"] in ("result", "error"):
                                count += 1
                                job["outputs"][selector] = event if event["type"] == "result" else {"error": event["message"]}
                                if event["type"] == "result":
                                    st.success(f"{label} finished on {event['device']}.")
                                    st.text(event["translation"])
                                else:
                                    st.error(f"{label}: {event['message']}")
                                progress.progress(count / len(selected), text=f"{count} of {len(selected)} models finished")
                    failed = any(item.get("error") for item in job["outputs"].values())
                    status.update(label="Finished with model errors" if failed else "Translations ready", state="error" if failed else "complete")
                except (OSError, ValueError, RuntimeError, SyntaxError) as exc:
                    job["request_error"] = str(exc)
                    status.update(label="Request could not finish", state="error")
    job = st.session_state.get("live_job")
    if job:
        st.divider()
        st.subheader("Latest live comparison")
        st.caption(f"{LANGUAGES[job['language']]} → English · Results for the submitted text below")
        st.text(job["text"])
        if job["repo"] != str(repo):
            st.warning("These results came from a different repository path than the current settings.")
        if job.get("request_error"):
            st.error(job["request_error"])
        job_specs = job["specs"]
        render_cards([spec for spec in job_specs if spec.selector in job["selected"]], job["outputs"], live=True)
        if job["outputs"]:
            download_live(job, job_specs)
        with st.expander("Model process logs & troubleshooting"):
            st.caption("A missing checkpoint requires prepare_models.sh in a networked terminal. CUDA errors may mean insufficient GPU memory; try fewer models or check the job allocation. See README.md.")
            for selector, log in job["logs"].items():
                st.markdown(f"**{selector}** · last 16,000 characters")
                st.code(log, language="text")
    st.caption("Ad hoc inspection only. This page shows model identities and does not compute semantic accuracy or replace blind bilingual grading.")
