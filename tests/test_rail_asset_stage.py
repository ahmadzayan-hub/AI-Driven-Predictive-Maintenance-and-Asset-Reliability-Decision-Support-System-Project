"""Safety and governance tests for the opt-in maintenance role."""
import unittest

from server.maintenance.rail_stage import RailAssetManagerStage
from server.stages import validate_result, load_stages


def row(**changes):
    sample = {"Asset_Class": "Railway Signalling", "Industry_Context": "Rail",
              "Asset_ID": "A1", "Criticality": "High", "Condition_Score": "40",
              "Failure_Count": "2", "Downtime_Hours": "8",
              "Maintenance_Cost_USD": "200", "Production_Loss_USD": "900"}
    sample.update(changes)
    return sample


def context(rows):
    return {"cleaner": {"rows": rows}, "collector": {"columns": list(row())},
            "report_language": "en"}


class RailAssetStageTests(unittest.TestCase):
    def test_governed_calculations_exclude_invalid_and_other_classes(self):
        result = RailAssetManagerStage().run(context([
            row(), row(Failure_Count="-2"), row(Asset_Class="Industrial Pump")]))
        validate_result("rail_asset_manager", result)
        self.assertEqual(result["output"]["screened"], 1)
        self.assertEqual(result["output"]["excluded"], 1)
        self.assertEqual(result["output"]["engineering_review_count"], 1)
        self.assertEqual(result["output"]["observed_economic_exposure_usd"], 1100)
        self.assertFalse(result["output"]["predictive_model_evaluated"])
        self.assertTrue(result["output"]["human_approval_required"])

    def test_missing_schema_produces_no_claim(self):
        result = RailAssetManagerStage().run({"cleaner": {"rows": []},
                                              "collector": {"columns": []}})
        self.assertFalse(result["output"]["applicable"])
        self.assertEqual(result["calculations"], [])
        self.assertEqual(result["claims"], [])

    def test_arabic_claims_have_same_numbers(self):
        ctx = context([row()])
        ctx["report_language"] = "ar"
        result = RailAssetManagerStage().run(ctx)
        from server.analytics import figures
        self.assertEqual(figures(result["claims"][0]["text"]),
                         figures(result["claims"][0]["text_ar"]))
        validate_result("rail_asset_manager", result)

    def test_opt_in_profile_registry(self):
        import json
        from pathlib import Path
        cfg = json.loads((Path(__file__).parents[1] / "config.json").read_text())
        stages, issues = load_stages(env={}, config=cfg)
        self.assertEqual(issues, [])
        self.assertIn("rail_asset_manager", stages)
        self.assertIn("maintenance_risk", cfg["profiles"]["maintenance"])
        self.assertIn("rail_asset_manager", cfg["profiles"]["maintenance"])
        self.assertNotIn("rail_asset_manager", cfg["profiles"]["default"])

if __name__ == "__main__":
    unittest.main()
