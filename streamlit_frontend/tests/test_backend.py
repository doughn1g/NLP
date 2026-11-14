"""Recipient-run checks; fake subprocesses only, no model imports or weights."""

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import (LABELS, csv_bytes, inference_lock, load_examples, load_saved,
                     model_specs, resolve_path, run_live, stop_process)


FAKE_WORKER = '''
if __name__ == "__main__":
    import json
    from pathlib import Path
    import sys
    args = sys.argv[1:]
    def flag(name):
        return args[args.index(name) + 1]
    selector = flag("--model")
    row = json.loads(Path(flag("--input")).read_text(encoding="utf-8"))
    assert set(row) == {"id", "source_text", "source_lang", "target_lang"}
    assert "--download" not in args
    import os
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    if row["source_text"] == "__sleep__":
        import time
        time.sleep(60)
    if selector == "qwen":
        print("Intentional fake-worker failure", flush=True)
        raise SystemExit(2)
    spec = MODELS[selector]
    output = Path(flag("--output"))
    row.update(model_id=spec[0], revision=spec[1], translation="Test output: " + row["source_text"])
    output.write_text(json.dumps(row, ensure_ascii=False) + "\\n", encoding="utf-8")
    Path(str(output) + ".run.json").write_text(json.dumps({"device": "cpu"}), encoding="utf-8")
    print("Fake worker complete", flush=True)
'''


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="idiom frontend test ")
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.cache = self.repo / "model cache"
        self.cache.mkdir()
        definitions = {name: (f"test/{name}", "test-revision", "translation", 1) for name in LABELS}
        (self.repo / "baseline.py").write_text(
            f"MODELS = {definitions!r}\nTRANSLATORS = {tuple(LABELS)!r}\n" + FAKE_WORKER, encoding="utf-8")
        self.source = self.repo / "source.jsonl"
        self.example = {"id": "one", "source_lang": "zh", "target_lang": "en",
                        "source_text": "画蛇添足", "intended_meaning": "PRIVATE DRAFT"}
        self.source.write_text(json.dumps(self.example, ensure_ascii=False) + "\n", encoding="utf-8")
        self.specs = model_specs(self.repo)

    def write_prediction(self, **changes):
        spec = self.specs[0]
        row = {"id": "one", "source_lang": "zh", "target_lang": "en", "translation": "An English paraphrase",
               "model_id": spec.model_id, "revision": spec.revision}
        row.update(changes)
        path = self.repo / "nllb.jsonl"
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        return path

    def test_config_is_read_without_execution(self):
        path = self.repo / "baseline.py"
        path.write_text(path.read_text(encoding="utf-8") + '\nraise RuntimeError("must never execute")\n', encoding="utf-8")
        self.assertEqual(len(model_specs(self.repo)), 4)
        self.assertEqual(resolve_path("model cache", self.repo), self.cache)

    def test_duplicate_source_ids_are_rejected(self):
        self.source.write_text((json.dumps(self.example) + "\n") * 2, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_examples(self.source)

    def test_saved_revision_and_source_hash_are_checked(self):
        self.write_prediction(revision="old")
        predictions, warnings = load_saved(self.repo, self.source, [self.example], self.specs)
        self.assertFalse(predictions)
        self.assertTrue(any("revision" in warning for warning in warnings))
        path = self.write_prediction()
        manifest = Path(str(path) + ".run.json")
        manifest.write_text(json.dumps({"input_sha256": "wrong"}), encoding="utf-8")
        self.assertFalse(load_saved(self.repo, self.source, [self.example], self.specs)[0])
        manifest.write_text(json.dumps({"input_sha256": hashlib.sha256(self.source.read_bytes()).hexdigest()}), encoding="utf-8")
        predictions, warnings = load_saved(self.repo, self.source, [self.example], self.specs)
        self.assertEqual(predictions[("one", "nllb")]["translation"], "An English paraphrase")
        self.assertEqual(warnings, [])

    def test_duplicate_predictions_are_not_silently_overwritten(self):
        path = self.write_prediction()
        path.write_text(path.read_text() * 2, encoding="utf-8")
        predictions, warnings = load_saved(self.repo, self.source, [self.example], self.specs)
        self.assertFalse(predictions)
        self.assertTrue(any("duplicate" in warning for warning in warnings))

    def test_fake_cli_preserves_unicode_and_continues_after_model_failure(self):
        text = '画蛇添足; echo "literal text"'
        events = list(run_live(self.repo, self.cache, "zh", text, ["nllb", "qwen", "madlad"], timeout=20))
        results = [event for event in events if event["type"] == "result"]
        self.assertEqual([event["selector"] for event in results], ["nllb", "madlad"])
        self.assertEqual(results[0]["translation"], "Test output: " + text)
        errors = [event for event in events if event["type"] == "error"]
        self.assertEqual([event["selector"] for event in errors], ["qwen"])
        self.assertFalse((self.repo / "results").exists())

    def test_second_session_cannot_start_inference(self):
        with inference_lock(self.repo):
            with self.assertRaisesRegex(RuntimeError, "Another frontend request"):
                list(run_live(self.repo, self.cache, "zh", "画蛇添足", ["nllb"]))

    def test_timeout_terminates_child_process(self):
        with patch("backend.stop_process", wraps=stop_process) as stopped:
            events = list(run_live(self.repo, self.cache, "zh", "__sleep__", ["nllb"], timeout=1))
        self.assertTrue(any(event["type"] == "error" and "Exceeded" in event["message"] for event in events))
        process = stopped.call_args.args[0]
        self.assertIsNotNone(process.poll())

    def test_closing_request_terminates_child_process(self):
        with patch("backend.stop_process", wraps=stop_process) as stopped:
            events = run_live(self.repo, self.cache, "zh", "__sleep__", ["nllb"], timeout=10)
            try:
                while next(events)["type"] != "heartbeat":
                    pass
            finally:
                events.close()
        process = stopped.call_args.args[0]
        self.assertIsNotNone(process.poll())

    def test_missing_cache_and_invalid_requests_fail_before_launch(self):
        with self.assertRaises(ValueError):
            list(run_live(self.repo, self.repo / "absent", "zh", "text", ["nllb"]))
        with self.assertRaises(ValueError):
            list(run_live(self.repo, self.cache, "en", "text", ["nllb"]))
        with self.assertRaises(ValueError):
            list(run_live(self.repo, self.cache, "zh", "text", []))

    def test_csv_supports_unicode_and_escapes_formula_cells(self):
        output = csv_bytes([{"source": "画蛇添足", "translation": "=1+1"}]).decode("utf-8-sig")
        self.assertIn("画蛇添足", output)
        self.assertIn("'=1+1", output)


if __name__ == "__main__":
    unittest.main()
