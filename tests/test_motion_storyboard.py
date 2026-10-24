"""Motion storyboard API contract: server-owned data and refused unvalidated runs."""
import unittest

from server.motion_storyboard import MotionStoryRefused, from_run


def run():
    return {
        "id": "RUN-TEST-001",
        "goal": "Review equipment performance",
        "dataset_name": "synthetic-fixture",
        "report_language": "ar",
        "tasks": [
            {"role": "planner", "state": "succeeded", "quality_checks": []},
            {"role": "validator", "state": "succeeded",
             "quality_checks": [{"passed": True, "name": "source grounded"}]},
            {"role": "publish", "state": "awaiting_approval", "quality_checks": []},
        ],
        "report": {"id": "REP-TEST-001", "version": 2, "content": "Synthetic report body"},
        "reports": [{"headline": "ارتفاع عدد الأعطال المسجلة في العينة"}],
    }


class StoryboardTests(unittest.TestCase):
    def test_validated_run_remains_draft(self):
        story = from_run(run())
        self.assertEqual(story["approval"], {"state": "DRAFT_VIDEO", "issued": False})
        self.assertEqual(story["scenes"][1]["text"], "ارتفاع عدد الأعطال المسجلة في العينة")
        self.assertEqual(story["scenes"][1]["evidence"][0]["locator"], "report:REP-TEST-001")

    def test_validator_failure_is_refused(self):
        data = run()
        data["tasks"][1]["quality_checks"][0]["passed"] = False
        with self.assertRaises(MotionStoryRefused):
            from_run(data)

    def test_any_analytical_stage_failure_blocks(self):
        data = run()
        data["tasks"][0]["state"] = "failed"
        with self.assertRaises(MotionStoryRefused):
            from_run(data)

    def test_missing_report_is_refused(self):
        data = run()
        data["report"] = None
        with self.assertRaises(MotionStoryRefused):
            from_run(data)

    def test_no_headline_is_refused(self):
        data = run()
        data["reports"] = []
        with self.assertRaises(MotionStoryRefused):
            from_run(data)


if __name__ == "__main__":
    unittest.main()
