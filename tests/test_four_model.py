"""Critical four-model export and language-control checks without weights."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import baseline
import export_excel


class FakeInputs(dict):
    def to(self, device):
        return self


class FakeTokenizer:
    def __init__(self):
        self.text = None
        self.src_lang = None

    def __call__(self, text, return_tensors):
        self.text = text
        return FakeInputs(input_ids=[[1, 2]])

    def get_lang_id(self, language):
        return {"en": 99}[language]

    def decode(self, tokens, skip_special_tokens):
        return "English output"


class FakeModel:
    def __init__(self):
        self.options = None

    def generate(self, **options):
        self.options = options
        return [[4, 5]]


class FourModelTests(unittest.TestCase):
    def test_madlad_and_m2m100_target_control(self):
        row = {"source_lang": "ta", "target_lang": "en", "source_text": "தமிழ் சொல்"}
        tokenizer, model = FakeTokenizer(), FakeModel()
        self.assertEqual(baseline.translate("madlad", tokenizer, model, "cpu", row), "English output")
        self.assertEqual(tokenizer.text, "<2en> தமிழ் சொல்")
        self.assertNotIn("forced_bos_token_id", model.options)
        self.assertEqual(baseline.translate("m2m100", tokenizer, model, "cpu", row), "English output")
        self.assertEqual(tokenizer.src_lang, "ta")
        self.assertEqual(tokenizer.text, "தமிழ் சொல்")
        self.assertEqual(model.options["forced_bos_token_id"], 99)

    def test_complete_excel_requires_all_four_models(self):
        source = baseline.examples("data/idioms_to_en_draft.jsonl")
        with TemporaryDirectory() as directory:
            paths = []
            for selector in baseline.TRANSLATORS:
                model_id, revision, _, _ = baseline.MODELS[selector]
                path = Path(directory) / f"{selector}.jsonl"
                baseline.write_jsonl(path, [{"id": row["id"], "model_id": model_id, "revision": revision,
                                            "source_lang": row["source_lang"], "target_lang": "en",
                                            "translation": f"{selector} output"} for row in source])
                paths.append(path)
            output = Path(directory) / "comparison.xlsx"
            args = SimpleNamespace(input="data/idioms_to_en_draft.jsonl",
                                   complexity="data/idiom_complexity_audit.md", predictions=paths[:2],
                                   output=output, allow_missing=False)
            with self.assertRaisesRegex(ValueError, "missing 150"):
                export_excel.export(args)
            args.predictions = paths
            export_excel.export(args)
            with ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
                ns = {"s": export_excel.NS}
                self.assertEqual(len(root.findall("./s:sheetData/s:row", ns)), 76)
                self.assertIn(b"madlad output", archive.read("xl/worksheets/sheet1.xml"))


if __name__ == "__main__":
    unittest.main()
