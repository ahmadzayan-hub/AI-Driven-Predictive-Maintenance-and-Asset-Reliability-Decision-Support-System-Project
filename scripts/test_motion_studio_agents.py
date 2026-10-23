import unittest
from motion_studio_agents import review_report

BASE = {
  "schema":"motion-evidence-v1","language":"ar","format":"wide",
  "classification":"INTERNAL","duration":6,
  "scenes":[
    {"kind":k,"text":t,"evidence":[{"source_id":"s","revision":"R1","locator":"p2","data_status":"VERIFIED"}]}
    for k,t in [("hook","ملخص هندسي"),("evidence","مؤشر 25%"),("action","مراجعة بشرية")]
  ]
}
class AdvisoryTest(unittest.TestCase):
    def test_no_automatic_approval(self):
        report = review_report(BASE)
        self.assertEqual(report["approval_state"], "DRAFT_REQUIRES_HUMAN_REVIEW")
    def test_percentage_demands_evidence_review(self):
        report = review_report(BASE)
        self.assertIn("VERIFY_PERCENT_DENOMINATOR", [x["code"] for x in report["advisories"]])

if __name__ == "__main__":
    unittest.main()
