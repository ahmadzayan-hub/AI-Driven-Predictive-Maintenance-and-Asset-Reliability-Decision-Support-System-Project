"""Keep repository synchronization separate from production release approval."""

import json
import unittest
from pathlib import Path


class ReleasePolicyTests(unittest.TestCase):
    def test_main_push_requires_a_separate_production_release(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))
        self.assertIs(config["git"]["deploymentEnabled"]["main"], False)
