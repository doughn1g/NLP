"""Recipient-run Streamlit smoke checks. Never submit model inference."""

import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONTEND))
from backend import LABELS


class AppSmokeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name)
        definitions = {name: (f"test/{name}", "test-revision", "translation", 1) for name in LABELS}
        (root / "baseline.py").write_text(f"MODELS = {definitions!r}\nTRANSLATORS = {tuple(LABELS)!r}\n", encoding="utf-8")
        source = root / "data.jsonl"
        source.write_text(json.dumps({"id": "one", "source_lang": "zh", "target_lang": "en",
                                      "source_text": "画蛇添足", "intended_meaning": "Draft meaning"}) + "\n", encoding="utf-8")
        environment = patch.dict(os.environ, {"NLP_REPO_ROOT": str(root), "NLP_DATA_PATH": str(source),
                                               "NLP_RESULTS_DIR": "missing-results", "NLP_MODEL_DIR": "missing-cache"})
        environment.start()
        self.addCleanup(environment.stop)
        self.app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=15)

    def test_saved_empty_state_and_library(self):
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("no saved translations" in item.value.lower() for item in self.app.info))
        self.app.radio(key="workspace").set_value("Browse results").run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.dataframe), 1)

    def test_live_form_renders_without_models(self):
        self.app.run()
        self.app.radio(key="translation_mode").set_value("Live models").run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.text_area), 1)
        self.assertEqual(len(self.app.multiselect[0].value), 4)
        self.app.radio(key="workspace").set_value("Setup & handoff").run()
        self.assertEqual(len(self.app.exception), 0)


if __name__ == "__main__":
    unittest.main()
