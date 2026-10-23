import unittest
from motion_studio_review import REQUIRED_CHECKS, assess_release, manifest_digest

MANIFEST = {"schema": "motion-evidence-v1", "approval": {"state": "DRAFT", "issued": False}}
CHECKS = {key: True for key in REQUIRED_CHECKS}


class MotionReleaseGateTests(unittest.TestCase):
    def evaluate(self, **kwargs):
        options = dict(reviewer_id="engineer-1", reviewer_is_human=True,
                       authorized_by_host=True, approved_manifest_sha256=manifest_digest(MANIFEST))
        options.update(kwargs)
        return assess_release(MANIFEST, CHECKS, **options)

    def test_full_review_only_eligible_not_issued(self):
        self.assertEqual(self.evaluate().state, "RELEASE_ELIGIBLE_FOR_HOST_DECISION")

    def test_ai_cannot_approve(self):
        self.assertEqual(self.evaluate(reviewer_is_human=False).state, "DRAFT_BLOCKED")

    def test_authority_is_required(self):
        self.assertEqual(self.evaluate(authorized_by_host=False).state, "DRAFT_BLOCKED")

    def test_modified_manifest_invalidates_approval(self):
        self.assertEqual(self.evaluate(approved_manifest_sha256="wrong").state, "DRAFT_BLOCKED")

    def test_missing_checks_fail_closed(self):
        result = assess_release(MANIFEST, {}, reviewer_id="engineer-1",
                                reviewer_is_human=True, authorized_by_host=True,
                                approved_manifest_sha256=manifest_digest(MANIFEST))
        self.assertEqual(result.state, "DRAFT_BLOCKED")


if __name__ == "__main__":
    unittest.main()
