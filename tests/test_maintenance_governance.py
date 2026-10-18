"""The governed diagnostics stage (milestone S2).

The load-bearing test here is `test_the_result_passes_the_stage_contract`:
the point of the stage is not that it finds things - `test_detectors.py`
covers that - but that what it produces is admissible as evidence. A
finding the validator cannot audit is a finding that can be quietly
dropped between the detector and the reader, which is exactly what
wiring it into the pipeline is meant to prevent.

Synthetic fixtures only.
"""

import unittest

from server import stages
from server.maintenance.governance import MaintenanceGovernance


def maintenance_rows(n=160):
    """Rows carrying two planted problems: an identifier that identifies
    nothing, and one split encoded by several columns.

    160 rows is not arbitrary. The leakage detector declines a split
    whose minority side is under 30 rows, because with a handful on one
    side almost any column looks pure by accident; a quarter of 160
    clears that floor, and 60 would not.
    """
    rows = []
    for i in range(n):
        corrective = i % 4 != 0
        rows.append({
            # Each key mixes classes, so it labels no entity.
            "Asset_ID": f"AST-{i // 4:03d}",
            "Record_ID": f"R{i}",
            "Record_Date": f"202{4 + i % 2}-01-01",
            "Asset_Class": f"Class-{i % 3}",
            "Site": f"Site-{i % 5}",
            "Work_Order_Type": "Corrective" if corrective else "Preventive",
            "Criticality": "High" if i % 2 else "Low",
            "Downtime_Hours": 10.0 + i if corrective else 0.0,
            "Failure_Count": 2 if corrective else 0,
            "Corrective_WO_Count": 4 if corrective else 0,
            "Completed_WO_Count": 10,
            "Planned_Operating_Hours": 100.0,
            "Operating_Hours": 80.0,
            "First_Time_Fix_Count": 3 if corrective else 0,
            "Maintenance_Cost_USD": 1000.0,
        })
    return rows


def context(rows=None, columns=None, date_col="Record_Date"):
    rows = maintenance_rows() if rows is None else rows
    columns = list(rows[0]) if (columns is None and rows) else (columns or [])
    return {"cleaner": {"rows": rows, "date_col": date_col},
            "collector": {"columns": columns},
            "dataset_name": "fixture", "goal": "diagnose"}


class ContractComplianceTest(unittest.TestCase):

    def test_the_descriptor_is_a_valid_stage(self):
        self.assertIsNone(stages.check_descriptor(MaintenanceGovernance(), {}))

    def test_the_result_passes_the_stage_contract(self):
        result = MaintenanceGovernance().run(context())
        # Raises ContractViolation if the shape is not auditable.
        clean = stages.validate_result(MaintenanceGovernance.role, result)
        self.assertEqual(clean["status"], "succeeded")
        self.assertTrue(clean["claims"])
        self.assertTrue(clean["calculations"])

    def test_every_claim_cites_calculations_that_exist(self):
        result = MaintenanceGovernance().run(context())
        ids = {c["id"] for c in result["calculations"]}
        for claim in result["claims"]:
            for reference in claim["evidence"]:
                self.assertIn(reference, ids,
                              f"{claim['id']} cites {reference}, which no "
                              f"calculation produces")

    def test_ids_carry_the_role_so_they_cannot_collide(self):
        result = MaintenanceGovernance().run(context())
        for item in result["calculations"] + result["claims"]:
            self.assertTrue(item["id"].startswith("maintenance_governance."),
                            item["id"])

    def test_every_claim_ships_in_english_and_arabic(self):
        result = MaintenanceGovernance().run(context())
        for claim in result["claims"]:
            self.assertTrue(claim["text"], claim["id"])
            self.assertTrue(claim.get("text_ar"), f"{claim['id']} has no Arabic")
            self.assertNotEqual(claim["text"], claim["text_ar"])

    def test_the_arabic_names_one_subject_not_a_list_of_columns(self):
        # The subject slot of a sentence takes the column the finding is
        # about. The others are context and belong in the detail, or the
        # Arabic reads as a comma-spliced fragment.
        result = MaintenanceGovernance().run(context())
        identity = next(c for c in result["claims"]
                        if c["text"].startswith("Asset_ID does not identify"))
        self.assertIn("Asset_ID", identity["text_ar"])
        self.assertNotIn("Asset_Class", identity["text_ar"])

    def test_text_stays_inside_the_contract_limits(self):
        result = MaintenanceGovernance().run(context())
        self.assertLessEqual(len(result["summary"]), stages.MAX_SUMMARY)
        for claim in result["claims"]:
            self.assertLessEqual(len(claim["text"]), stages.MAX_TEXT)
            self.assertLessEqual(len(claim["text_ar"]), stages.MAX_TEXT)


class RegistrationTest(unittest.TestCase):
    """ADR 0038 documents two ways to register this stage. Both are
    tested, so the documented path cannot rot into a wrong instruction."""

    PATH = "server.maintenance.governance.MaintenanceGovernance"

    def test_it_registers_through_the_environment_variable(self):
        loaded, problems = stages.load_stages(env={"AGENTIC_OS_STAGES": self.PATH})
        self.assertEqual(problems, [])
        self.assertIn("maintenance_governance", loaded)

    def test_it_registers_through_config_with_options(self):
        loaded, problems = stages.load_stages(env={}, config={"stages": [
            {"path": self.PATH, "options": {"fail_on_high": True}}]})
        self.assertEqual(problems, [])
        self.assertTrue(loaded["maintenance_governance"].fail_on_high)

    def test_it_runs_after_governance_and_before_the_audited_tail(self):
        after = stages.describe(MaintenanceGovernance())["after"]
        self.assertIn(after, stages.PLACEMENTS)
        self.assertNotIn(after, stages.GUARDED_TAIL)


class FindingsTest(unittest.TestCase):

    def test_planted_problems_become_claims(self):
        result = MaintenanceGovernance().run(context())
        found = {f["detector"] for f in result["output"]["findings"]}
        self.assertIn("identity_collapse", found)
        self.assertIn("target_leakage", found)
        self.assertTrue(
            any(c["type"] == "warning" for c in result["claims"]),
            "a high-severity structural finding must be a warning, not a note")

    def test_outcome_columns_are_reported_as_unusable_for_prediction(self):
        result = MaintenanceGovernance().run(context())
        excluded = result["output"]["model_inputs_excluded"]
        self.assertIn("Downtime_Hours", excluded)
        self.assertIn("Criticality", result["output"]["model_inputs_usable"])

    def test_a_clean_table_says_so_rather_than_inventing_a_finding(self):
        rows = [{"Record_ID": f"R{i}", "Record_Date": "2026-01-01",
                 "Site": f"S{i % 4}", "Reading": float(i % 7)} for i in range(40)]
        result = MaintenanceGovernance().run(context(rows))
        self.assertEqual(result["output"]["findings"], [])
        self.assertIn("No structural problem", result["summary"])


class TierTest(unittest.TestCase):

    def test_a_non_maintenance_table_stands_the_domain_agents_down_by_name(self):
        rows = [{"Invoice_No": f"I{i}", "Customer": f"C{i % 5}",
                 "Amount": float(i), "Region": f"R{i % 3}"} for i in range(30)]
        result = MaintenanceGovernance().run(context(rows, date_col=None))
        self.assertEqual(result["output"]["tier"], "general")
        tier_claim = next(c for c in result["claims"] if c["id"].endswith("cl_tier"))
        self.assertIn("stand down", tier_claim["text"])

    def test_an_empty_table_is_reported_not_crashed_on(self):
        result = MaintenanceGovernance().run(context([], columns=[]))
        stages.validate_result(MaintenanceGovernance.role, result)
        self.assertEqual(result["output"]["tier"], "unusable")


class PolicyTest(unittest.TestCase):

    def test_by_default_a_high_finding_restricts_but_does_not_fail_the_run(self):
        result = MaintenanceGovernance().run(context())
        self.assertEqual(result["status"], "succeeded")

    def test_fail_on_high_stops_the_run_instead(self):
        result = MaintenanceGovernance(fail_on_high=True).run(context())
        self.assertEqual(result["status"], "failed")

    def test_a_table_over_the_cell_budget_reports_what_it_skipped(self):
        result = MaintenanceGovernance(max_cells=1).run(context())
        skipped = result["output"]["skipped_detectors"]
        self.assertIn("identity_collapse", skipped)
        self.assertIn("target_leakage", skipped)
        checks = {c["name"]: c["detail"] for c in result["quality_checks"]}
        self.assertIn("skipped", checks["identity_collapse"],
                      "a skipped detector must say so, not pass silently")
        stages.validate_result(MaintenanceGovernance.role, result)

    def test_findings_are_capped_so_the_report_stays_readable(self):
        result = MaintenanceGovernance(max_findings=2).run(context())
        self.assertLessEqual(len(result["output"]["findings"]), 2)
        self.assertLessEqual(len(result["claims"]), stages.MAX_CLAIMS)


class QualityCheckTest(unittest.TestCase):

    def test_a_check_never_contradicts_itself(self):
        # A failing check that says "no finding" means the check and the
        # finding are keyed differently and neither can be trusted.
        result = MaintenanceGovernance().run(context())
        for check in result["quality_checks"]:
            if not check["passed"]:
                self.assertNotIn("no finding", check["detail"],
                                 f"{check['name']} fails but reports no finding")
            elif "skipped" not in check["detail"]:
                self.assertNotIn("finding(s)", check["detail"],
                                 f"{check['name']} passes but reports findings")

    def test_every_detector_has_a_check(self):
        from server import detectors
        names = {c["name"] for c in MaintenanceGovernance().run(context())["quality_checks"]}
        for detector in detectors.DETECTORS:
            self.assertIn(detector.__name__, names)


class ReportTest(unittest.TestCase):

    def test_the_stage_contributes_a_report_section(self):
        result = MaintenanceGovernance().run(context())
        report = result["output"]["report_markdown"]
        self.assertIn("# Maintenance Governance Agent", report)
        self.assertIn("What may be used to predict", report)

    def test_the_report_frames_findings_as_restrictions_not_errors(self):
        report = MaintenanceGovernance().run(context())["output"]["report_markdown"]
        self.assertIn("restrict what may be concluded", report)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# Under the engine (assessment finding R2)
# ---------------------------------------------------------------------------

try:
    from tests.test_stages import engine_in, registry, settle, task
    ENGINE_AVAILABLE = True
except Exception:  # pragma: no cover - CLI-only environments
    ENGINE_AVAILABLE = False


@unittest.skipUnless(ENGINE_AVAILABLE, "the run engine's test helpers are unavailable")
class FatalPolicyUnderTheEngineTest(unittest.TestCase):
    """The configured policy has to be the policy the engine applies.

    The earlier test for this asserted the *stage's returned status* and
    passed while the run carried on to a report and an approval request,
    because the engine reads `can_fail_run` off the descriptor and the
    descriptor still said False. A stage-level assertion cannot see that;
    only driving the engine can. The assessment reproduced exactly this:
    task_state=failed, run_state=awaiting_approval, report produced.
    """

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    # A dataset that provably triggers a high-severity finding: one
    # switch drives the type, the downtime and the failure count, so the
    # leakage detector fires. Relying on the built-in sample made these
    # tests skip, which is indistinguishable from passing.
    @staticmethod
    def leaky_csv(rows=240):
        """One switch drives type, downtime and failures, so leakage fires.

        Every row is unique. The cleaner drops duplicates, and an earlier
        version of this fixture repeated rows until the minority side of
        the split fell under the detector's floor - so the stage found
        nothing and the tests below proved nothing.
        """
        lines = ["record_id,month,work_order_type,downtime_hours,failure_count"]
        for i in range(rows):
            corrective = i % 4 != 0
            lines.append(
                f"R{i:04d},2026-{(i % 12) + 1:02d},"
                f"{'Corrective' if corrective else 'Preventive'},"
                f"{(10 + i * 0.25) if corrective else 0},"
                f"{2 if corrective else 0}")
        return chr(10).join(lines) + chr(10)

    def run_with(self, stage):
        engine = engine_in(self.tmp.name, registry(stage))
        self.addCleanup(engine.store.close)
        run = engine.create_run("Find the largest downtime concentration",
                                self.leaky_csv(), "leaky.csv")
        return engine, settle(engine, run["id"])

    def assert_fired(self, run):
        """The fixture must actually produce the finding under test."""
        governance = task(run, "maintenance_governance")
        self.assertEqual(
            governance["state"], "failed",
            "the fixture must trigger a high-severity finding, or this test "
            f"proves nothing (state={governance['state']}, "
            f"summary={governance.get('summary')!r})")
        return governance

    def test_the_descriptor_policy_follows_the_configured_option(self):
        self.assertTrue(MaintenanceGovernance(fail_on_high=True).can_fail_run)
        self.assertFalse(MaintenanceGovernance().can_fail_run)
        self.assertTrue(
            stages.describe(MaintenanceGovernance(fail_on_high=True))["can_fail_run"])

    def test_the_fatal_option_stops_the_run(self):
        engine, run = self.run_with(MaintenanceGovernance(fail_on_high=True))
        self.assert_fired(run)
        self.assertEqual(run["state"], "failed",
                         "a fatal governance finding must stop the run")

    def test_nothing_downstream_runs_after_a_fatal_finding(self):
        engine, run = self.run_with(MaintenanceGovernance(fail_on_high=True))
        self.assert_fired(run)
        roles = [t["role"] for t in run["tasks"]]
        index = roles.index("maintenance_governance")
        for later in run["tasks"][index + 1:]:
            self.assertNotEqual(
                later["state"], "succeeded",
                f"{later['role']} ran after a fatal governance failure")

    def test_no_report_or_publishing_approval_follows_a_fatal_finding(self):
        engine, run = self.run_with(MaintenanceGovernance(fail_on_high=True))
        self.assert_fired(run)
        self.assertIsNone(engine.store.latest_artifact(run["id"]),
                          "a stopped run must not publish a report")
        approvals = [t for t in run["tasks"]
                     if t["role"] == "publish" and t["state"] == "awaiting_approval"]
        self.assertEqual(approvals, [],
                         "a stopped run must not request publishing approval")

    def test_the_nonfatal_configuration_still_continues_with_its_findings(self):
        engine, run = self.run_with(MaintenanceGovernance())
        governance = task(run, "maintenance_governance")
        self.assertEqual(governance["state"], "succeeded")
        self.assertNotEqual(run["state"], "failed",
                            "the deliberate nonfatal case must carry on")
