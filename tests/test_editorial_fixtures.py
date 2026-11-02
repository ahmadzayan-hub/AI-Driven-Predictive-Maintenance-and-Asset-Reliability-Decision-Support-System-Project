"""Bounded teaching examples only; not a general editorial safety validator."""
import unittest
from pathlib import Path
from scripts.check_editorial_fixtures import EXAMPLES, preserves


class EditorialFixtures(unittest.TestCase):
    def test_documented_pairs_preserve_selected_tokens(self):
        doc = (Path(__file__).resolve().parents[1] /
               "docs/editorial/EDITORIAL_QA_AR_EN.md").read_text(encoding="utf-8")
        for before, after, protected in EXAMPLES:
            with self.subTest(before=before):
                self.assertIn(before, doc)
                self.assertIn(after, doc)
                self.assertTrue(preserves(before, after, protected))

    def test_each_protected_token_removal_is_rejected(self):
        for before, after, protected in EXAMPLES:
            for token in protected:
                with self.subTest(token=token):
                    self.assertFalse(preserves(before, after.replace(token, ""), protected))

    def test_changed_units_numbers_sources_and_negation_are_rejected(self):
        for index, old, new in [(0, "4.5 h", "5 h"), (0, "12 units", "12 h"),
                                (0, "[S1]", "[S3]"),
                                (0, "has not been approved", "has been approved"),
                                (1, "قراءة أولية", "قراءة مؤكدة"),
                                (1, "ولا تثبت", "وتثبت")]:
            before, after, protected = EXAMPLES[index]
            with self.subTest(old=old):
                self.assertFalse(preserves(before, after.replace(old, new), protected))

    def test_added_number_is_rejected(self):
        before, after, protected = EXAMPLES[0]
        self.assertFalse(preserves(before, after + " 99", protected))


if __name__ == "__main__":
    unittest.main()
