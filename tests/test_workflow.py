"""Code-only workflow checks; synthetic predictions are not model results."""

import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

import baseline


class WorkflowTests(unittest.TestCase):
    def test_pilot_validation_and_duplicate_rejection(self):
        rows = baseline.examples("data/pilot.jsonl")
        sets = baseline.candidates("data/pilot_candidates.jsonl", rows)
        self.assertEqual((len(rows), len(sets)), (12, 12))
        duplicate = [dict(row) for row in rows]
        duplicate[1]["id"] = duplicate[0]["id"]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            baseline.write_jsonl(path, duplicate)
            with self.assertRaisesRegex(ValueError, "duplicate ID"):
                baseline.examples(path)

    def test_stable_tie_break(self):
        class FakeEncoder:
            def encode(self, texts, normalize_embeddings):
                return [FakeVector() for _ in texts]

        class FakeVector:
            def __matmul__(self, other):
                return 0.5

        ranked = baseline.rank_candidates("labse", FakeEncoder(), {"source_text": "example"},
                                          {"candidates": [{"id": "z", "text": "x"}, {"id": "a", "text": "y"}]})
        self.assertEqual([item["candidate_id"] for item in ranked], ["a", "z"])

    def test_pilot_exports_and_scores_with_synthetic_predictions(self):
        examples = baseline.examples("data/pilot.jsonl")
        sets = baseline.candidates("data/pilot_candidates.jsonl", examples)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {}
            for selector, (model_id, revision, task, _) in baseline.MODELS.items():
                path = root / f"{selector}.jsonl"
                rows = []
                for example in examples:
                    row = {"id": example["id"], "model_id": model_id, "revision": revision,
                           "source_lang": example["source_lang"], "target_lang": example["target_lang"]}
                    if task == "translation":
                        row["translation"] = "SYNTHETIC WORKFLOW CHECK"
                    else:
                        items = sets[example["id"]]["candidates"]
                        row["ranked_candidates"] = [{"candidate_id": item["id"], "score": 1.0 - i * 0.1}
                                                    for i, item in enumerate(items)]
                    rows.append(row)
                baseline.write_jsonl(path, rows)
                paths[selector] = path
            blind = root / "blind.csv"
            mapping = root / "private.jsonl"
            baseline.blind(SimpleNamespace(input="data/pilot.jsonl", predictions=[paths["nllb"], paths["qwen"]],
                                           output=blind, mapping=mapping, seed=7))
            with blind.open(encoding="utf-8", newline="") as file:
                reviewed = list(csv.DictReader(file))
            self.assertEqual(len(reviewed), 24)
            self.assertEqual(len({r["row_id"] for r in reviewed}), 24)
            self.assertTrue(all("model_id" not in r and "intended_meaning" not in r for r in reviewed))
            for row in reviewed:
                row["meaning_0_2"] = "2"
                row["naturalness_0_2"] = "1"
            baseline.write_csv(blind, reviewed)
            translation_scores = root / "translation_scores.csv"
            baseline.translation_scores(SimpleNamespace(review=blind, mapping=mapping, output=translation_scores))
            with translation_scores.open(encoding="utf-8", newline="") as file:
                scored = list(csv.DictReader(file))
            self.assertEqual(len(scored), 24)
            self.assertTrue(all(float(row["full_meaning_share"]) == 1 for row in scored))
            matching_scores = root / "matching_scores.csv"
            baseline.matching_scores(SimpleNamespace(input="data/pilot.jsonl", candidates="data/pilot_candidates.jsonl",
                                                     predictions=[paths["labse"], paths["qwen_embed"]], output=matching_scores))
            with matching_scores.open(encoding="utf-8", newline="") as file:
                scored = list(csv.DictReader(file))
            self.assertEqual(len(scored), 24)
            self.assertTrue(all(float(row["top1_accuracy"]) == 1 for row in scored))
            joined = root / "comparison.jsonl"
            baseline.compare(SimpleNamespace(input="data/pilot.jsonl", candidates="data/pilot_candidates.jsonl",
                                             translation=[paths["nllb"], paths["qwen"]],
                                             matching=[paths["labse"], paths["qwen_embed"]], output=joined))
            comparison = baseline.read_jsonl(joined)
            self.assertEqual(len(comparison), 12)
            self.assertTrue(all(row["labse_ranking"][0]["candidate_text"] for row in comparison))


if __name__ == "__main__":
    unittest.main()
