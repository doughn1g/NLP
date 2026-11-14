"""Reproducible four-model idiom translation and semantic matching baseline."""

import argparse
from collections import defaultdict
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import shutil
import sys
import uuid


LANG = {"en": ("English", "eng_Latn"), "zh": ("Simplified Mandarin Chinese", "zho_Hans"),
        "ta": ("Tamil", "tam_Taml"), "tl": ("Tagalog", "tgl_Latn")}
MODELS = {
    "nllb": ("facebook/nllb-200-distilled-600M", "f8d333a098d19b4fd9a8b18f94170487ad3f821d", "translation", 2.5),
    "qwen": ("Qwen/Qwen3-4B-Instruct-2507", "cdbee75f17c01a7cc42f958dc650907174af0554", "translation", 8.1),
    "madlad": ("google/madlad400-3b-mt", "fa184c675da0b5c9e1c8694fccd4e12e2d422094", "translation", 11.8),
    "m2m100": ("facebook/m2m100_418M", "55c2e61bbf05dfb8d7abccdc3fae6fc8512fd636", "translation", 1.9),
    "labse": ("sentence-transformers/LaBSE", "836121a0533e5664b21c7aacc5d22951f2b8b25b", "matching", 1.9),
    "qwen_embed": ("Qwen/Qwen3-Embedding-0.6B", "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3", "matching", 1.2),
}
TRANSLATORS = ("nllb", "qwen", "madlad", "m2m100")
GENERATION = {"do_sample": False, "num_beams": 1, "max_new_tokens": 128}
PROMPT = "Translate this {source} sentence into {target}. Preserve its intended meaning in context. Return only a natural translation.\n\n{sentence}"
QUERY_INSTRUCTION = "Retrieve the target-language sentence that preserves the meaning of this source sentence in context."


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8-sig") as file:
        for line_no, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected an object")
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: empty JSONL")
    return rows


def examples(path):
    rows = read_jsonl(path)
    seen = set()
    for n, row in enumerate(rows, 1):
        ident, source, target = row.get("id"), row.get("source_lang"), row.get("target_lang")
        if not isinstance(ident, str) or not ident.strip() or ident in seen:
            raise ValueError(f"example row {n}: missing or duplicate ID")
        seen.add(ident)
        if not isinstance(row.get("source_text"), str) or not row["source_text"].strip():
            raise ValueError(f"example row {n}: empty source_text")
        if not isinstance(source, str) or not isinstance(target, str) or source not in LANG or target not in LANG or source == target:
            raise ValueError(f"example row {n}: invalid language direction")
    return rows


def candidates(path, example_rows):
    by_id = {row["id"]: row for row in example_rows}
    result = {}
    global_candidate_ids = set()
    for n, row in enumerate(read_jsonl(path), 1):
        ident = row.get("example_id")
        if not isinstance(ident, str) or ident not in by_id or ident in result:
            raise ValueError(f"candidate row {n}: unknown or duplicate example_id")
        if row.get("target_lang") != by_id[ident]["target_lang"]:
            raise ValueError(f"candidate row {n}: target language mismatch")
        items = row.get("candidates")
        if not isinstance(items, list) or len(items) < 2:
            raise ValueError(f"candidate row {n}: need at least two candidates")
        ids = set()
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip() or item["id"] in global_candidate_ids:
                raise ValueError(f"candidate row {n}: missing or duplicate candidate ID")
            if not isinstance(item.get("text"), str) or not item["text"].strip():
                raise ValueError(f"candidate row {n}: empty candidate text")
            ids.add(item["id"])
            global_candidate_ids.add(item["id"])
        correct = row.get("acceptable_candidate_ids")
        if not isinstance(correct, list) or not correct or any(not isinstance(x, str) for x in correct) or len(correct) != len(set(correct)) or not set(correct) <= ids:
            raise ValueError(f"candidate row {n}: invalid acceptable_candidate_ids")
        result[ident] = row
    missing = set(by_id) - set(result)
    if missing:
        raise ValueError(f"missing candidate sets for {len(missing)} examples: {sorted(missing)[:3]}")
    return result


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def versions():
    names = ("torch", "transformers", "sentence-transformers", "huggingface-hub", "safetensors", "accelerate", "sentencepiece", "protobuf")
    return {name: importlib.metadata.version(name) for name in names}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_model(selector, model_dir, download):
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from packaging.version import Version
    if Version(transformers.__version__) < Version("4.51.0"):
        raise RuntimeError("Transformers >=4.51.0 is required for Qwen3")
    if selector in ("nllb", "m2m100") and Version(torch.__version__.split("+")[0]) < Version("2.6.0"):
        raise RuntimeError("PyTorch >=2.6.0 is required for the official .bin checkpoints")
    model_id, revision, _, _ = MODELS[selector]
    model_dir = Path(model_dir).expanduser().resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    if download and shutil.disk_usage(model_dir).free < 25 * 10**9:
        raise RuntimeError(f"Need at least 25 GB free in {model_dir} before downloading model files")
    patterns = (["*.json", "*.txt", "*.model", "*.safetensors", "*.bin"] if selector in ("nllb", "m2m100")
                else ["*.json", "*.txt", "*.model", "*.safetensors"])
    local = snapshot_download(repo_id=model_id, revision=revision, cache_dir=str(model_dir),
                              local_files_only=not download, allow_patterns=patterns)
    return local, "cuda" if torch.cuda.is_available() else "cpu"


def translation_model(selector, local, device):
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, AutoModelForCausalLM
    tokenizer = AutoTokenizer.from_pretrained(local, use_fast=selector not in ("madlad", "m2m100"))
    if selector in ("nllb", "m2m100"):
        model = AutoModelForSeq2SeqLM.from_pretrained(local, use_safetensors=False)
    elif selector == "madlad":
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForSeq2SeqLM.from_pretrained(local, use_safetensors=True, torch_dtype=dtype,
                                                       low_cpu_mem_usage=True)
    else:
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(local, use_safetensors=True, torch_dtype=dtype)
    return tokenizer, model.to(device).eval()


def translate(selector, tokenizer, model, device, row):
    import torch
    source, target = row["source_lang"], row["target_lang"]
    if selector == "nllb":
        tokenizer.src_lang = LANG[source][1]
        inputs = tokenizer(row["source_text"], return_tensors="pt").to(device)
        extra = {"forced_bos_token_id": tokenizer.convert_tokens_to_ids(LANG[target][1])}
    elif selector == "m2m100":
        tokenizer.src_lang = source
        inputs = tokenizer(row["source_text"], return_tensors="pt").to(device)
        extra = {"forced_bos_token_id": tokenizer.get_lang_id(target)}
    elif selector == "madlad":
        inputs = tokenizer(f"<2{target}> {row['source_text']}", return_tensors="pt").to(device)
        extra = {}
    else:
        prompt = PROMPT.format(source=LANG[source][0], target=LANG[target][0], sentence=row["source_text"])
        inputs = tokenizer.apply_chat_template([{"role": "user", "content": prompt}], tokenize=True,
                                               add_generation_prompt=True, return_dict=True, return_tensors="pt").to(device)
        extra = {}
    with torch.inference_mode():
        output = model.generate(**inputs, **GENERATION, **extra)[0]
    tokens = output if selector != "qwen" else output[inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(tokens, skip_special_tokens=True).strip()


def embedding_model(local, device):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(local, device=device, trust_remote_code=False)


def rank_candidates(selector, model, row, candidate_row):
    source = row["source_text"]
    prompt = f"Instruct: {QUERY_INSTRUCTION}\nQuery: " if selector == "qwen_embed" else ""
    query = model.encode([prompt + source], normalize_embeddings=True)[0]
    texts = [item["text"] for item in candidate_row["candidates"]]
    vectors = model.encode(texts, normalize_embeddings=True)
    ranked = [{"candidate_id": item["id"], "score": float(query @ vector)}
              for item, vector in zip(candidate_row["candidates"], vectors)]
    ranked.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    return ranked


def rank_translation_candidates(selector, tokenizer, model, device, row, candidate_row):
    """Rank target sentences by mean conditional token log probability."""
    import torch

    source, target = row["source_lang"], row["target_lang"]
    if selector == "nllb":
        tokenizer.src_lang = LANG[source][1]
        tokenizer.tgt_lang = LANG[target][1]
        source_inputs = tokenizer(row["source_text"], return_tensors="pt").to(device)
    else:
        prompt = PROMPT.format(source=LANG[source][0], target=LANG[target][0], sentence=row["source_text"])
        prompt_ids = tokenizer.apply_chat_template([{"role": "user", "content": prompt}],
                                                   tokenize=True, add_generation_prompt=True,
                                                   return_tensors="pt")[0].tolist()
    ranked = []
    for item in candidate_row["candidates"]:
        if selector == "nllb":
            labels = tokenizer(text_target=item["text"], return_tensors="pt")["input_ids"].to(device)
            with torch.inference_mode():
                logits = model(**source_inputs, labels=labels).logits
                log_probs = torch.nn.functional.log_softmax(logits.float(), dim=-1)
                token_scores = log_probs.gather(-1, labels.unsqueeze(-1)).squeeze(-1)
                # The first target token is the fixed target-language code.
                # Condition on it, then compare the candidate's own tokens and EOS.
                score = float(token_scores[:, 1:].mean().item())
        else:
            candidate_ids = tokenizer(item["text"], add_special_tokens=False)["input_ids"]
            sequence = prompt_ids + candidate_ids + [tokenizer.eos_token_id]
            input_ids = torch.tensor([sequence], device=device)
            labels = input_ids.clone()
            labels[:, :len(prompt_ids)] = -100
            with torch.inference_mode():
                loss = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids), labels=labels).loss
            score = -float(loss.item())
        ranked.append({"candidate_id": item["id"], "score": score})
    ranked.sort(key=lambda item: (-item["score"], item["candidate_id"]))
    return ranked


def run(args):
    rows = examples(args.input)
    selector = args.model
    model_id, revision, model_task, _ = MODELS[selector]
    if args.task == "rank" and model_task != "translation":
        raise ValueError("--task rank is for translation models; embedding models already rank candidates")
    task = "matching" if args.task == "rank" else model_task
    candidate_rows = candidates(args.candidates, rows) if task == "matching" else None
    selected = rows[:args.limit] if args.limit else rows
    if args.dry_run:
        print(f"Validated {len(rows)} examples" + (f" and {len(candidate_rows)} candidate sets" if candidate_rows else "") +
              f"; selected {len(selected)} for {model_id}. No model libraries imported.")
        return
    if not args.output:
        raise ValueError("--output is required for a real run")
    completed = []
    output_path = Path(args.output)
    if args.resume and task == "translation" and output_path.exists():
        completed = read_jsonl(output_path)
        if len(completed) > len(selected):
            raise ValueError("existing output has more rows than selected input")
        for previous, source_row in zip(completed, selected):
            if (previous.get("id"), previous.get("model_id"), previous.get("revision"),
                previous.get("source_lang"), previous.get("target_lang")) != (
                    source_row["id"], model_id, revision, source_row["source_lang"], source_row["target_lang"]
                ) or not isinstance(previous.get("translation"), str) or not previous["translation"].strip():
                raise ValueError("existing output does not match selected input and model")
        if len(completed) == len(selected) and Path(str(output_path) + ".run.json").exists():
            print(f"Already completed {len(completed)} translation rows in {args.output}")
            return
    local, device = local_model(selector, args.model_dir, args.download)
    if task == "translation":
        tokenizer, model = translation_model(selector, local, device)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Path(str(output_path) + ".run.json").unlink(missing_ok=True)
        outputs = list(completed)
        with output_path.open("a" if args.resume and completed else "w", encoding="utf-8", newline="\n") as file:
            for index, row in enumerate(selected[len(completed):], len(completed) + 1):
                result = {"id": row["id"], "model_id": model_id, "revision": revision,
                          "source_lang": row["source_lang"], "target_lang": row["target_lang"],
                          "translation": translate(selector, tokenizer, model, device, row)}
                if not result["translation"]:
                    raise RuntimeError(f"empty translation for {row['id']}")
                file.write(json.dumps(result, ensure_ascii=False) + "\n")
                file.flush()
                outputs.append(result)
                print(f"{selector}: {index}/{len(selected)} {row['id']}", flush=True)
        settings = {"generation": GENERATION, "prompt_template": PROMPT if selector == "qwen" else None,
                    "nllb_language_codes": {code: value[1] for code, value in LANG.items()} if selector == "nllb" else None,
                    "madlad_target_prefix": "<2{target_lang}>" if selector == "madlad" else None,
                    "m2m100_language_codes": "project ISO codes" if selector == "m2m100" else None}
    else:
        if model_task == "translation":
            tokenizer, model = translation_model(selector, local, device)
        else:
            model = embedding_model(local, device)
        outputs = []
        for row in selected:
            ranked = (rank_translation_candidates(selector, tokenizer, model, device, row, candidate_rows[row["id"]])
                      if model_task == "translation" else rank_candidates(selector, model, row, candidate_rows[row["id"]]))
            outputs.append({"id": row["id"], "model_id": model_id, "revision": revision,
                            "source_lang": row["source_lang"], "target_lang": row["target_lang"],
                            "score_type": "mean_token_log_probability" if model_task == "translation" else "cosine",
                            "ranked_candidates": ranked})
        settings = ({"score_type": "mean_token_log_probability", "length_normalization": "per target token including EOS",
                     "tie_break": "candidate_id ascending", "prompt_template": PROMPT if selector == "qwen" else None,
                     "nllb_language_codes": {code: value[1] for code, value in LANG.items()} if selector == "nllb" else None,
                     "nllb_score_excludes_target_language_token": selector == "nllb"}
                    if model_task == "translation" else
                    {"score_type": "cosine", "normalization": "L2", "tie_break": "candidate_id ascending",
                     "query_instruction": QUERY_INSTRUCTION if selector == "qwen_embed" else None,
                     "pooling": "model's sentence-transformers modules"})
    if task != "translation":
        write_jsonl(args.output, outputs)
    manifest = {"model_id": model_id, "revision": revision, "resolved_revision": Path(local).name,
                "task": task, "device": device,
                "settings": settings, "python": sys.version, "packages": versions(),
                "input": str(Path(args.input).resolve()), "input_sha256": sha256(args.input),
                "candidate_file": str(Path(args.candidates).resolve()) if candidate_rows else None,
                "candidate_sha256": sha256(args.candidates) if candidate_rows else None,
                "n": len(outputs)}
    Path(str(args.output) + ".run.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(outputs)} {task} rows to {args.output}")


def prediction_map(paths, allowed, example_rows):
    known = {row["id"]: row for row in example_rows}
    result = {}
    for path in paths:
        for row in read_jsonl(path):
            ident, model_id = row.get("id"), row.get("model_id")
            if ident not in known or model_id not in allowed or (ident, model_id) in result:
                raise ValueError(f"unknown or duplicate prediction: {ident!r}, {model_id!r}")
            model = next(item for item in MODELS.values() if item[0] == model_id)
            if row.get("revision") != model[1] or (row.get("source_lang"), row.get("target_lang")) != (known[ident]["source_lang"], known[ident]["target_lang"]):
                raise ValueError(f"revision or direction mismatch: {ident!r}, {model_id!r}")
            result[ident, model_id] = row
    return result


def write_csv(path, rows):
    if not rows:
        raise ValueError("no rows to write")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def blind(args):
    source = examples(args.input)
    predictions = prediction_map(args.predictions, {MODELS[x][0] for x in TRANSLATORS}, source)
    if any(not isinstance(pred.get("translation"), str) or not pred["translation"].strip() for pred in predictions.values()):
        raise ValueError("translation predictions must contain nonempty text")
    rng = random.Random(args.seed) if args.seed is not None else random.SystemRandom()
    pairs = [(row, pred) for row in source for (ident, _), pred in predictions.items() if ident == row["id"]]
    rng.shuffle(pairs)
    blind_rows, mapping = [], []
    for example, pred in pairs:
        row_id = uuid.UUID(int=rng.getrandbits(128)).hex
        blind_rows.append({"row_id": row_id, "source_lang": example["source_lang"], "target_lang": example["target_lang"],
                           "kind": example.get("kind", ""), "source_text": example["source_text"],
                           "translation": pred["translation"], "meaning_0_2": "", "naturalness_0_2": "", "reviewer_notes": ""})
        mapping.append({"row_id": row_id, "example": example, "model_id": pred["model_id"], "revision": pred["revision"]})
    write_csv(args.output, blind_rows)
    previous = os.umask(0o077)
    try:
        write_jsonl(args.mapping, mapping)
        Path(args.mapping).chmod(0o600)
    finally:
        os.umask(previous)
    print(f"Wrote {len(blind_rows)} blind rows and private mapping")


def translation_table(args):
    source = examples(args.input)
    predictions = prediction_map(args.predictions, {MODELS[x][0] for x in TRANSLATORS}, source)
    output = []
    for example in source:
        row = {"id": example["id"], "source_lang": example["source_lang"],
               "target_lang": example["target_lang"], "source_text": example["source_text"],
               "draft_meaning": example.get("intended_meaning", ""),
               "review_status": example.get("review_status", "")}
        for selector in TRANSLATORS:
            pred = predictions.get((example["id"], MODELS[selector][0]))
            row[selector + "_translation"] = pred["translation"] if pred else ""
        output.append(row)
    write_csv(args.output, output)
    print(f"Wrote {len(output)} side-by-side translation rows")


def translation_scores(args):
    mapping_rows = read_jsonl(args.mapping)
    mapping = {row["row_id"]: row for row in mapping_rows}
    if len(mapping) != len(mapping_rows):
        raise ValueError("duplicate row_id in mapping")
    groups = defaultdict(list)
    seen = set()
    with Path(args.review).open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            ident = row.get("row_id")
            if ident not in mapping or ident in seen:
                raise ValueError(f"unknown or duplicate review row: {ident!r}")
            seen.add(ident)
            m, n = row.get("meaning_0_2", "").strip(), row.get("naturalness_0_2", "").strip()
            if not m and not n:
                continue
            if m not in ("0", "1", "2") or n not in ("0", "1", "2"):
                raise ValueError(f"invalid score for row {ident}")
            item = mapping[ident]
            example = item["example"]
            status = "reviewed" if example.get("review_status") == "reviewed" else "draft"
            groups[(item["model_id"], example["source_lang"], example["target_lang"], example.get("kind", ""), status)].append((int(m), int(n)))
    output = [{"model_id": key[0], "source_lang": key[1], "target_lang": key[2], "kind": key[3],
               "evaluation_status": key[4],
               "rated_n": len(values), "full_meaning_share": sum(m == 2 for m, _ in values) / len(values),
               "mean_naturalness": sum(n for _, n in values) / len(values)} for key, values in sorted(groups.items())]
    write_csv(args.output, output)
    print(f"Wrote {len(output)} translation score groups")


def matching_scores(args):
    source = examples(args.input)
    candidate_rows = candidates(args.candidates, source)
    predictions = prediction_map(args.predictions, {model[0] for model in MODELS.values()}, source)
    groups = defaultdict(list)
    for example in source:
        for selector in MODELS:
            key = (example["id"], MODELS[selector][0])
            if key not in predictions:
                continue
            ranked = predictions[key].get("ranked_candidates")
            expected = {c["id"] for c in candidate_rows[example["id"]]["candidates"]}
            if not isinstance(ranked, list) or {x.get("candidate_id") for x in ranked} != expected or len(ranked) != len(expected):
                raise ValueError(f"invalid ranked candidate IDs for {key}")
            if not all(isinstance(x.get("score"), (float, int)) and math.isfinite(x["score"]) for x in ranked):
                raise ValueError(f"invalid similarity score for {key}")
            if ranked != sorted(ranked, key=lambda x: (-x["score"], x["candidate_id"])):
                raise ValueError(f"rank order mismatch for {key}")
            correct = ranked[0]["candidate_id"] in candidate_rows[example["id"]]["acceptable_candidate_ids"]
            status = ("reviewed" if example.get("review_status") == "reviewed" and
                      candidate_rows[example["id"]].get("review_status") == "reviewed" else "draft")
            score_type = "mean_token_log_probability" if MODELS[selector][2] == "translation" else "cosine"
            if predictions[key].get("score_type", score_type) != score_type:
                raise ValueError(f"score type mismatch for {key}")
            groups[(MODELS[selector][0], example["source_lang"], example["target_lang"], example.get("kind", ""), status, score_type)].append(correct)
    output = [{"model_id": key[0], "source_lang": key[1], "target_lang": key[2], "kind": key[3],
               "evaluation_status": key[4], "score_type": key[5],
               "n": len(values), "top1_accuracy": sum(values) / len(values)} for key, values in sorted(groups.items())]
    write_csv(args.output, output)
    print(f"Wrote {len(output)} matching score groups")


def compare(args):
    source = examples(args.input)
    candidate_rows = candidates(args.candidates, source)
    translation = prediction_map(args.translation, {MODELS[x][0] for x in ("nllb", "qwen")}, source)
    matching = prediction_map(args.matching, {model[0] for model in MODELS.values()}, source)
    output = []
    for example in source:
        row = {"id": example["id"], "source_lang": example["source_lang"], "target_lang": example["target_lang"],
               "kind": example.get("kind", ""), "review_status": example.get("review_status", ""),
               "candidate_review_status": candidate_rows[example["id"]].get("review_status", ""),
               "source_text": example["source_text"]}
        for selector in ("nllb", "qwen"):
            pred = translation.get((example["id"], MODELS[selector][0]))
            row[selector + "_translation"] = pred["translation"] if pred else None
        for selector in MODELS:
            pred = matching.get((example["id"], MODELS[selector][0]))
            texts = {item["id"]: item["text"] for item in candidate_rows[example["id"]]["candidates"]}
            row[selector + "_ranking"] = [{**item, "candidate_text": texts[item["candidate_id"]]}
                                           for item in pred["ranked_candidates"]] if pred else None
        output.append(row)
    write_jsonl(args.output, output)
    print(f"Wrote {len(output)} joined examples")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--model", choices=MODELS, required=True)
    run_parser.add_argument("--task", choices=("auto", "rank"), default="auto",
                            help="rank target candidates with NLLB or Qwen; embedding models rank by default")
    run_parser.add_argument("--input", default="data/pilot.jsonl")
    run_parser.add_argument("--candidates", default="data/pilot_candidates.jsonl")
    run_parser.add_argument("--output")
    run_parser.add_argument("--model-dir", default="models")
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--download", action="store_true")
    run_parser.add_argument("--resume", action="store_true", help="continue an interrupted translation output")
    run_parser.set_defaults(func=run)
    review_parser = sub.add_parser("blind-review")
    review_parser.add_argument("--input", default="data/pilot.jsonl")
    review_parser.add_argument("--predictions", nargs="+", required=True)
    review_parser.add_argument("--output", required=True)
    review_parser.add_argument("--mapping", required=True)
    review_parser.add_argument("--seed", type=int)
    review_parser.set_defaults(func=blind)
    table_parser = sub.add_parser("translation-table", help="export translations side by side for dataset inspection")
    table_parser.add_argument("--input", default="data/pilot.jsonl")
    table_parser.add_argument("--predictions", nargs="+", required=True)
    table_parser.add_argument("--output", required=True)
    table_parser.set_defaults(func=translation_table)
    tscore = sub.add_parser("score-translation")
    tscore.add_argument("--review", required=True)
    tscore.add_argument("--mapping", required=True)
    tscore.add_argument("--output", required=True)
    tscore.set_defaults(func=translation_scores)
    mscore = sub.add_parser("score-matching")
    mscore.add_argument("--input", default="data/pilot.jsonl")
    mscore.add_argument("--candidates", default="data/pilot_candidates.jsonl")
    mscore.add_argument("--predictions", nargs="+", required=True)
    mscore.add_argument("--output", required=True)
    mscore.set_defaults(func=matching_scores)
    comparison = sub.add_parser("compare")
    comparison.add_argument("--input", default="data/pilot.jsonl")
    comparison.add_argument("--candidates", default="data/pilot_candidates.jsonl")
    comparison.add_argument("--translation", nargs="+", required=True)
    comparison.add_argument("--matching", nargs="+", required=True,
                            help="candidate rankings from any or all four models")
    comparison.add_argument("--output", required=True)
    comparison.set_defaults(func=compare)
    args = parser.parse_args()
    if args.command == "run" and args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.command == "blind-review" and Path(args.output).resolve() == Path(args.mapping).resolve():
        parser.error("blind file and private mapping must differ")
    try:
        args.func(args)
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
