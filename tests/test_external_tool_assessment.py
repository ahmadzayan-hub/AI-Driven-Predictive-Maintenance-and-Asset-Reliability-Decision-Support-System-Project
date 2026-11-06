"""Deterministic offline safety-gate regression tests.

Written as unittest cases (6 November 2026): CI runs `python -m unittest
discover`, which ran none of the earlier pytest-style functions."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("external_tool_assessment", ROOT / "scripts" / "ExternalToolAssessment.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def evidenced():
    return {"name": "Fixture", "repository": "https://github.com/example/fixture",
            "license_verified": True, "revision_pinned": True, "revision": "a" * 40,
            "isolation_evidence": "b" * 64,
            "security_review": "passed", "security_review_record": {"reviewer": "Named reviewer", "date": "2026-11-06"},
            "data_classification": "synthetic", "external_egress": False,
            "human_owner": "Named reviewer", "operational_write_access": False, "runtime": "isolated"}


class GateTests(unittest.TestCase):

    def test_only_evidenced_synthetic_candidates_are_eligible(self):
        self.assertEqual(tool.assess(evidenced())["status"], "ELIGIBLE_FOR_ISOLATED_TRIAL")

    def test_missing_required_fields_fail_closed(self):
        for field in tool.REQUIRED:
            candidate = evidenced()
            del candidate[field]
            self.assertEqual(tool.assess(candidate)["status"], "BLOCKED", field)

    def test_production_access_and_egress_blocked(self):
        for field, value in (("operational_write_access", True), ("external_egress", True),
                             ("data_classification", "restricted"), ("security_review", "pending")):
            candidate = evidenced()
            candidate[field] = value
            self.assertEqual(tool.assess(candidate)["status"], "BLOCKED", field)

    def test_a_declaration_is_not_evidence(self):
        for field, value in (("revision", None), ("revision", "main"), ("isolation_evidence", None),
                             ("isolation_evidence", "network blocked"), ("security_review_record", None),
                             ("security_review_record", {"reviewer": "", "date": "2026-11-06"})):
            candidate = evidenced()
            candidate[field] = value
            self.assertEqual(tool.assess(candidate)["status"], "BLOCKED", (field, value))

    def test_every_listed_candidate_stays_blocked(self):
        catalog = json.loads((ROOT / "docs" / "External Tool Candidates.json").read_text(encoding="utf-8"))
        self.assertTrue(catalog)
        for candidate in catalog:
            self.assertEqual(tool.assess(candidate)["status"], "BLOCKED", candidate["name"])


if __name__ == "__main__":
    unittest.main()
