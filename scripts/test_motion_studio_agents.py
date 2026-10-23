"""Agentic media review refuses to authorize publication or invent evaluation."""
from __future__ import annotations
import unittest

from motion_studio_agents import AgentReviewError, check_transcript, digest, review

MANIFEST = {
    "schema": "motion-evidence-v1", "language": "ar", "format": "wide",
    "classification": "INTERNAL", "duration": 3,
    "scenes": [
        {"kind": "hook", "text": "إدارة الأصول", "evidence": [{
            "source_id": "src", "revision": "rev2", "locator": "p1",
            "data_status": "VERIFIED"}]},
        {"kind": "evidence", "text": "تحليل الأداء", "evidence": [{
            "source_id": "src", "revision": "rev2", "locator": "p2",
            "data_status": "VERIFIED"}]},
        {"kind": "action", "text": "المراجعة البشرية", "evidence": [{
            "source_id": "src", "revision": "rev2", "locator": "p3",
            "data_status": "VERIFIED"}]},
    ]
}


class ReviewAgentTests(unittest.TestCase):
    def test_requires_human_even_when_every_reference_looks_valid(self):
        result = review(MANIFEST)
        self.assertFalse(result["publication_allowed"])
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["source_truth_verified"])
        self.assertEqual(len(result["manifest_sha256"]), 64)

    def test_voice_similarity_never_claims_automatic_approval(self):
        transcript = " ".join(scene["text"] for scene in MANIFEST["scenes"])
        result = check_transcript(MANIFEST, transcript)
        self.assertEqual(result["word_error_rate"], 0.0)
        self.assertEqual(result["status"], "REQUIRES_HUMAN_REVIEW")

    def test_no_transcript_is_not_falsely_passed(self):
        self.assertEqual(review(MANIFEST)["checks"][2]["status"], "NOT_TESTED")

    def test_editorial_ai_cannot_issue_or_approve(self):
        def editorial(_prompt):
            return {"suggestions": ["Shorten the first headline"]}
        result = review(MANIFEST, editor_assistant=editorial)
        self.assertEqual(result["editorial_assistant"]["status"], "ADVISORY_ONLY")
        self.assertFalse(result["publication_allowed"])

    def test_malformed_model_response_fails(self):
        with self.assertRaises(AgentReviewError):
            review(MANIFEST, editor_assistant=lambda _: {"approved": True})

    def test_digest_is_stable_across_dictionary_key_order(self):
        self.assertEqual(digest(MANIFEST), digest(dict(reversed(list(MANIFEST.items())))))


if __name__ == "__main__":
    unittest.main()
