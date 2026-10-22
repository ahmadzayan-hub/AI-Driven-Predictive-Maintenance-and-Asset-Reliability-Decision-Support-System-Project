"""Contract tests for railway asset role screening and fail-closed authorization."""
import unittest

from server.rail_asset_decisions import ROLE_TAG, assess_observation, authorize


def sample():
    return {
        "Industry_Context": "Rail", "Asset_Class": "Railway Signalling",
        "Asset_ID": "A001", "Criticality": "Critical",
        "Condition_Score": 42, "Failure_Count": 2,
        "Downtime_Hours": 12, "Maintenance_Cost_USD": 500,
        "Production_Loss_USD": 2500,
    }


class RailAssetDecisionsTest(unittest.TestCase):
    def test_critical_asset_requires_review_without_predictive_claim(self):
        result = assess_observation(sample())
        self.assertEqual(result["analytic_key"], "Rail|Railway Signalling|A001")
        self.assertEqual(result["identity_status"], "UNVERIFIED_PHYSICAL_IDENTITY")
        self.assertEqual(result["screening"], "engineering_review")
        self.assertEqual(result["observed_economic_exposure_usd"], 3000)
        self.assertEqual(result["prediction_status"], "NOT_EVALUATED")
        self.assertEqual(result["approval_status"], "HUMAN_REVIEW_REQUIRED")

    def test_lower_criticality_is_not_an_automatic_intervention(self):
        row = sample()
        row.update(Criticality="Low", Condition_Score=80, Failure_Count=0)
        self.assertEqual(assess_observation(row)["screening"], "routine_review")

    def test_a_failure_on_a_signalling_asset_escalates_whatever_its_criticality(self):
        # A failure on a safety function is never routine (assessment A8).
        row = sample()
        row.update(Criticality="Low", Condition_Score=95, Failure_Count=1)
        result = assess_observation(row)
        self.assertEqual(result["screening"], "engineering_review")
        self.assertEqual(result["screening_reason"], "failure_on_safety_function")
        self.assertTrue(result["safety_function"])
        # The same failure on a non-safety class of low criticality stays routine.
        row.update(Asset_Class="Escalator")
        result = assess_observation(row)
        self.assertEqual(result["screening"], "routine_review")
        self.assertFalse(result["safety_function"])

    def test_the_condition_threshold_is_stated_with_every_screening(self):
        row = sample()
        row.update(Criticality="High", Condition_Score=59, Failure_Count=0)
        result = assess_observation(row)
        self.assertEqual(result["screening_reason"], "condition_below_threshold")
        self.assertEqual(result["condition_review_threshold"], 60.0)

    def test_missing_or_invalid_data_is_rejected(self):
        for field, value in (("Condition_Score", 101),
                             ("Failure_Count", -1),
                             ("Downtime_Hours", float("nan")),
                             ("Criticality", "Unknown"),
                             ("Asset_ID", "")):
            with self.subTest(field=field):
                row = sample()
                row[field] = value
                with self.assertRaises(ValueError):
                    assess_observation(row)

    def test_authorization_fails_closed(self):
        self.assertFalse(authorize([], "read_screening"))
        self.assertTrue(authorize([ROLE_TAG], "read_screening"))
        self.assertFalse(authorize([ROLE_TAG], "release_recommendation"))
        self.assertTrue(authorize([ROLE_TAG], "release_recommendation", approved=True))
        self.assertFalse(authorize([ROLE_TAG], "execute_safety_work", approved=True))


if __name__ == "__main__":
    unittest.main()
