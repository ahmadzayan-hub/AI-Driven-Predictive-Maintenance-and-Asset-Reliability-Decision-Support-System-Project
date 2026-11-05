"""Held-out paraphrase benchmark for the RMD V2 packs (ADR 2026-11-04, measurement 2).

The 18 questions in `evals/knowledge_paraphrase/cases.json` were written before
any retrieval change and avoid the source's own key terms. The floors are the
measured baseline of the current lexical scorer. A change to scoring must keep
them: a light stemmer was tried on 2026-11-05 and lowered MRR from 0.516 to
0.398, so it was reverted. Using this set to tune would make it dev data; a
change that is tuned on it needs a new held-out set.
"""
import json
import unittest
from pathlib import Path

from tests.test_rmd_knowledge_packs import evidence, public_store

CASES = json.loads((Path(__file__).resolve().parents[1] / "evals" / "knowledge_paraphrase"
                    / "cases.json").read_text(encoding="utf-8"))["cases"]
FLOOR_TOP5, FLOOR_TOP3, FLOOR_MRR = 15, 11, 0.51


def ranks(store):
    out = {}
    for case in CASES:
        hits = evidence(store, case["collection"], case["q"], limit=5)
        out[case["id"]] = next(
            (i + 1 for i, h in enumerate(hits)
             if any(s in f"{h.passage.document} {h.passage.section}".lower() for s in case["sections"])),
            None)
    return out


class ParaphraseBenchmark(unittest.TestCase):
    def test_floors_hold(self):
        found = ranks(public_store())
        top5 = sum(1 for r in found.values() if r)
        top3 = sum(1 for r in found.values() if r and r <= 3)
        mrr = sum(1 / r for r in found.values() if r) / len(found)
        self.assertEqual(len(found), 18)
        self.assertGreaterEqual(top5, FLOOR_TOP5, found)
        self.assertGreaterEqual(top3, FLOOR_TOP3, found)
        self.assertGreaterEqual(mrr, FLOOR_MRR, found)


if __name__ == "__main__":
    unittest.main()
