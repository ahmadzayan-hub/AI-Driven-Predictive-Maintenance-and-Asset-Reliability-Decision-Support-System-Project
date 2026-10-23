"""Synthetic regression evidence for record reconciliation and honest measures."""

from copy import deepcopy
import json
import unittest

from server.rmd_analytics import analyse_records, MAX_PROPOSED_LINKS


NOW = "2026-02-15T12:00:00+00:00"


def row(identifier, grain="mms_work_order", source_id="source-a", **fields):
    return {"id": identifier, "source_id": source_id, "source_sha": "synthetic-version",
            "sheet": "Synthetic records", "source_row": int(identifier[1:]) + 2 if identifier[1:].isdigit() else 2,
            "grain": grain, "fields": fields, "raw_fields": {"private": "never-copy-the-raw-row"}}


def analyse(records, **kwargs):
    return analyse_records(records, calculated_at=NOW, **kwargs)


def completeness(result, grain, field):
    return next(x for x in result["completeness"] if x["grain"] == grain and x["field"] == field)


class GrainAndReconciliationTests(unittest.TestCase):
    def test_source_populations_and_summary_are_separate_from_incidents(self):
        result = analyse([row("r1"), row("r2", "occ_event"),
                          row("r3", "sr_reconciliation"), row("r4", "summary", total=20)])
        self.assertEqual(result["counts_by_grain"], {
            "mms_work_order": 1, "occ_event": 1, "sr_reconciliation": 1, "summary": 1, "other": 0})
        self.assertEqual(result["coverage"]["selected_detail_records"], 3)
        self.assertIsNone(result["relationships"]["canonical_incident_count"])
        self.assertEqual([x["value"] for x in result["kpis"]], [1, 1, 1, 1, 0])

    def test_original_not_found_label_does_not_override_computed_mms_match(self):
        records = [row("r1", sr_id="SR-A", wo_id="WO-A"),
                   row("r2", "sr_reconciliation", source_id="source-b", sr_id="SR-A",
                       source_reconciliation_label="SR not found")]
        result = analyse(records)
        rec = result["reconciliation"]["records"][0]
        self.assertEqual(rec["source_label"], "SR not found")
        self.assertEqual(rec["calculated_match"], "matched_in_uploaded_mms")
        self.assertIsNone(rec["source_label_comparison_source"])
        self.assertEqual(rec["matched_record_ids"], ["r1"])
        self.assertEqual(result["reconciliation"]["source_labels"][0]["count"], 1)

    def test_repeated_sr_retains_multiple_work_orders_and_source_rows(self):
        result = analyse([row("r1", sr_id="SR-A", wo_id="WO-1"),
                          row("r2", sr_id="SR-A", wo_id="WO-2"),
                          row("r3", "sr_reconciliation", sr_id="SR-A")])
        self.assertEqual(result["reconciliation"]["records"][0]["matched_record_ids"], ["r1", "r2"])
        self.assertEqual(result["relationships"]["sr_to_work_orders"], [{"sr_id": "SR-A", "wo_ids": ["WO-1", "WO-2"]}])
        self.assertEqual(len(result["relationships"]["sr_nodes"]), 1)
        self.assertEqual(len(result["relationships"]["wo_nodes"]), 2)
        self.assertEqual(result["counts_by_grain"]["mms_work_order"], 2)

    def test_exact_identifiers_keep_leading_zero_and_namespace(self):
        result = analyse([row("r1", sr_id="001", wo_id="001"),
                          row("r2", "sr_reconciliation", sr_id=1)])
        self.assertEqual(result["reconciliation"]["records"][0]["calculated_match"], "not_in_uploaded_mms")
        self.assertNotEqual(result["relationships"]["sr_nodes"][0]["id"], result["relationships"]["wo_nodes"][0]["id"])

    def test_absent_comparison_is_unavailable_not_a_not_found_match(self):
        result = analyse([row("r1", "sr_reconciliation", sr_id="SR-A")])
        self.assertEqual(result["reconciliation"]["records"][0]["calculated_match"], "comparison_unavailable")
        self.assertEqual(result["reconciliation"]["comparison_scope"]["records"], 0)

    def test_date_and_display_filters_do_not_hide_reference_work_orders(self):
        result = analyse([
            row("r1", sr_id="SR-A", event_date="2024-01-01", location="Other site"),
            row("r2", "sr_reconciliation", sr_id="SR-A", event_date="2026-01-01", location="Selected site")],
            filters={"date_from": "2026-01-01", "date_to": "2026-01-31", "location": "Selected site"})
        self.assertEqual(result["coverage"]["selected_records"], 1)
        self.assertEqual(result["reconciliation"]["records"][0]["calculated_match"], "matched_in_uploaded_mms")
        self.assertFalse(result["reconciliation"]["comparison_scope"]["date_filter_applied"])
        self.assertEqual(result["proposed_links"][0]["right_record_id"], "r1")

    def test_explicit_comparison_source_bounds_matching(self):
        result = analyse([
            row("r1", source_id="reference-a", sr_id="SR-A", event_date="2026-01-01", location="Site"),
            row("r2", source_id="reference-b", sr_id="SR-B", event_date="2026-01-01", location="Site"),
            row("r3", "sr_reconciliation", sr_id="SR-A", event_date="2026-01-01", location="Site")],
            filters={"comparison_source_ids": ["reference-b"]})
        self.assertEqual(result["reconciliation"]["records"][0]["calculated_match"], "not_in_uploaded_mms")
        self.assertEqual(result["reconciliation"]["comparison_scope"]["source_ids"], ["reference-b"])
        self.assertEqual(result["proposed_links"], [])


class MissingnessAndStatusTests(unittest.TestCase):
    def test_placeholders_blank_unknown_and_measured_zero_are_distinct(self):
        records = [row("r1", sr_id=None), row("r2", sr_id=""), row("r3", sr_id="NA"),
                   row("r4", sr_id="EMPTY"), row("r5", sr_id="TBD"), row("r6", sr_id=0)]
        result = analyse(records)
        item = completeness(result, "mms_work_order", "sr_id")
        self.assertEqual(item["states"], {"blank": 1, "measured_zero": 1, "unknown": 1, "unresolved_placeholder": 3})
        self.assertEqual(item["recorded"], 1)
        self.assertEqual(item["record_ids_missing"], ["r1", "r2", "r3", "r4", "r5"])
        self.assertEqual(result["relationships"]["sr_nodes"][0]["identifier"], "0")

    def test_reviewed_placeholder_meaning_is_specific_to_a_field(self):
        a = row("r1", sr_id="NA", location="NA")
        a["field_states"] = {"sr_id": "not_applicable", "location": "recorded"}
        result = analyse([a])
        self.assertEqual(completeness(result, "mms_work_order", "sr_id")["not_applicable"], 1)
        self.assertEqual(completeness(result, "mms_work_order", "sr_id")["applicable_records"], 0)
        self.assertEqual(result["charts"][0]["table"][0]["label"], "NA")

    def test_close_comp_and_blank_are_only_recorded_statuses(self):
        result = analyse([row("r1", wo_status="CLOSE"), row("r2", wo_status="COMP"), row("r3", wo_status="")])
        self.assertEqual({x["label"]: x["count"] for x in result["status_distributions"]["mms_work_order"]}, {"": 1, "CLOSE": 1, "COMP": 1})
        self.assertEqual(completeness(result, "mms_work_order", "rca_evidence")["recorded"], 0)
        self.assertTrue(any("neither proves" in x["en"] for x in result["limitations"]))

    def test_complex_field_value_and_nonfinite_value_do_not_become_identifiers(self):
        result = analyse([row("r1", sr_id={"unexpected": 5}), row("r2", sr_id=float("nan"))])
        self.assertEqual(result["relationships"]["sr_nodes"], [])


class InvestigationTests(unittest.TestCase):
    def test_date_location_conflicts_remain_unresolved_without_overwriting(self):
        records = [row("r1", sr_id="SR-A", event_date="2026-01-01", location="Site A"),
                   row("r2", sr_id="SR-A", event_date="2026-01-02", location="Site B")]
        original = deepcopy(records)
        result = analyse(records)
        self.assertEqual({x["kind"] for x in result["conflicts"]}, {"date", "location"})
        self.assertTrue(all(x["status"] == "unresolved" for x in result["conflicts"]))
        self.assertEqual(records, original)
        self.assertIsNone(result["relationships"]["canonical_incident_count"])

    def test_same_date_and_location_only_proposes_a_link(self):
        result = analyse([row("r1", event_date="2026-01-01", location="Junction A"),
                          row("r2", "occ_event", event_date="2026-01-01", location="junction a")])
        self.assertEqual(len(result["proposed_links"]), 1)
        self.assertEqual(result["proposed_links"][0]["method"], "date_location")
        self.assertEqual(result["proposed_links"][0]["state"], "proposed")
        self.assertIsNone(result["relationships"]["canonical_incident_count"])

    def test_heuristic_cannot_overrule_conflicting_populated_sr_ids(self):
        result = analyse([row("r1", sr_id="SR-A", event_date="2026-01-01", location="Site"),
                          row("r2", "occ_event", sr_id="SR-B", event_date="2026-01-01", location="Site")])
        self.assertEqual(result["proposed_links"], [])

    def test_different_date_needs_multiple_shared_symptom_terms(self):
        records = [row("r1", event_date="2026-01-01", location="Site", symptom="Door circuit interrupted"),
                   row("r2", "occ_event", event_date="2026-01-02", location="Site", symptom="Door circuit reset"),
                   row("r3", "occ_event", event_date="2026-01-02", location="Site", symptom="Door inspected")]
        result = analyse(records)
        self.assertEqual([(x["left_record_id"], x["right_record_id"]) for x in result["proposed_links"]], [("r2", "r1")])

    def test_bounded_candidate_search_reports_incomplete_coverage(self):
        records = [row("m" + str(i), event_date="2026-01-01", location="Site") for i in range(MAX_PROPOSED_LINKS + 2)]
        records.append(row("o1", "occ_event", event_date="2026-01-01", location="Site"))
        result = analyse(records)
        self.assertEqual(len(result["proposed_links"]), MAX_PROPOSED_LINKS)
        self.assertTrue(result["proposed_links_truncated"])

    def test_unselected_events_do_not_consume_candidate_limit(self):
        records = [row("m1", event_date="2026-01-01", location="Site")]
        records += [row("o" + str(i), "occ_event", source_id="hidden", event_date="2026-01-01", location="Site") for i in range(MAX_PROPOSED_LINKS + 2)]
        records.append(row("z1", "occ_event", source_id="visible", event_date="2026-01-01", location="Site"))
        result = analyse(records, filters={"source_ids": ["visible"]})
        self.assertEqual(len(result["proposed_links"]), 1)
        self.assertEqual(result["proposed_links"][0]["left_record_id"], "z1")


class ChartsAndReadinessTests(unittest.TestCase):
    def test_pareto_uses_one_record_grain_and_pooled_record_denominator(self):
        result = analyse([row("r1", "occ_event", location="A"), row("r2", "occ_event", location="A"),
                          row("r3", "occ_event", location="B"), row("r4", "occ_event", location=""),
                          row("r5", "summary", location="A")])
        chart = result["charts"][0]
        self.assertEqual(chart["grain"], "occ_event")
        self.assertEqual(chart["denominator"], 3)
        self.assertEqual(chart["missing_records"], 1)
        self.assertEqual([x["value"] for x in chart["table"]], [2, 1])
        self.assertAlmostEqual(chart["table"][0]["share"], 2 / 3)
        self.assertEqual(chart["table"][-1]["cumulative_share"], 1)

    def test_monthly_history_does_not_guess_dates_or_fill_gaps_with_zero(self):
        result = analyse([row("r1", "occ_event", event_date="2026-01-03"),
                          row("r2", "occ_event", event_date="2026-03-03T08:00:00Z"),
                          row("r3", "occ_event", event_date="03/04/2026"),
                          row("r4", "occ_event", event_date="2026-02-30")])
        chart = result["charts"][2]
        self.assertEqual([x["label"] for x in chart["table"]], ["2026-01", "2026-03"])
        self.assertEqual(chart["missing_records"], 2)
        self.assertEqual(result["coverage"]["records_without_validated_dates"], 2)

    def test_recurrence_is_candidate_wording_not_verified_failure_or_cause(self):
        result = analyse([row("r1", "occ_event", symptom="Observed noise", location="A"),
                          row("r2", "occ_event", symptom="Observed noise", location="A")])
        self.assertEqual(result["recurrence"][0]["count"], 2)
        self.assertEqual(result["recurrence"][0]["state"], "candidate")
        self.assertIn("not a verified", result["recurrence"][0]["interpretation"]["en"])

    def test_event_age_does_not_create_an_overdue_status(self):
        result = analyse([row("r1", event_date="2020-01-01", wo_status="OPEN"),
                          row("r2", due_date="2026-02-01", outstanding_status=True),
                          row("r3", due_date="2026-02-01", outstanding_status=False),
                          row("r4", due_date="2026-02-15", outstanding_status=True),
                          row("r5", due_date="2026-02-01", wo_status="CLOSE")])
        review = result["age_and_due_date_review"]
        self.assertEqual((review["overdue"], review["not_overdue"], review["unassessable"]), (1, 2, 2))
        self.assertGreater(review["records"][0]["age_since_event_days"], 2000)
        self.assertIsNone(review["records"][0]["overdue"])
        self.assertIsNone(review["records"][-1]["overdue"])

    def test_future_event_does_not_have_a_negative_age(self):
        result = analyse([row("r1", event_date="2027-01-01")])
        self.assertIsNone(result["age_and_due_date_review"]["records"][0]["age_since_event_days"])

    def test_reviewed_missing_status_never_becomes_overdue_from_its_raw_text(self):
        for state in ("unknown", "not_applicable", "not_measured", "blank", "unresolved_placeholder"):
            for raw_value in ("outstanding", "true", True, False):
                with self.subTest(state=state, raw_value=raw_value):
                    item = row("r1", due_date="2026-02-01", outstanding_status=raw_value)
                    item["field_states"] = {"outstanding_status": {"state": state}}
                    result = analyse([item])["age_and_due_date_review"]
                    self.assertEqual(result["overdue"], 0)
                    self.assertEqual(result["unassessable"], 1)
                    self.assertIsNone(result["records"][0]["overdue"])
                    self.assertIsNone(result["records"][0]["outstanding_status"])

    def test_reviewed_recorded_status_and_value_state_alias_are_respected(self):
        recorded = row("r1", due_date="2026-02-01", outstanding_status=True)
        recorded["field_states"] = {"outstanding_status": "recorded"}
        excluded = row("r2", due_date="2026-02-01", outstanding_status="outstanding")
        excluded["value_states"] = {"outstanding_status": "not_applicable"}
        result = analyse([recorded, excluded])["age_and_due_date_review"]
        self.assertEqual(result["overdue"], 1)
        self.assertEqual(result["unassessable"], 1)

    def test_all_unavailable_measures_name_required_inputs_not_scores(self):
        result = analyse([row("r1", wo_status="CLOSE", duration="30 minutes", aed_loss="TBD")])
        self.assertEqual({x["id"] for x in result["readiness"]}, {"mtbf", "mttr", "availability", "failure_probability", "remaining_useful_life", "aed_loss"})
        for gate in result["readiness"]:
            self.assertFalse(gate["available"])
            self.assertEqual(gate["state"], "unavailable")
            self.assertGreater(len(gate["missing_inputs"]), 0)
            self.assertGreater(len(gate["needed_validation"]), 0)
            self.assertNotIn("value", gate)

    def test_priorities_are_supported_advisory_and_no_deadline_is_invented(self):
        result = analyse([row("r1", sr_id="SR-A", wo_id="WO-A", event_date="2026-01-01", location="A"),
                          row("r2", sr_id="SR-A", event_date="2026-01-02", location="B"),
                          row("r3", "sr_reconciliation", sr_id="SR-A", source_reconciliation_label="Not found")])
        self.assertEqual(len(result["priorities"]), 3)
        for priority in result["priorities"]:
            self.assertTrue(priority["owner_is_suggested"])
            self.assertIsNone(priority["due_date"])
            self.assertEqual(priority["status"], "proposed")
            self.assertTrue(priority["evidence"]["record_ids"])
            self.assertTrue(priority["evidence"]["calculation_ids"])
            self.assertTrue(priority["closure_evidence"]["ar"])


class SnapshotContractTests(unittest.TestCase):
    def test_empty_extract_has_no_fabricated_priority_or_canonical_incidents(self):
        result = analyse([])
        self.assertEqual(result["priorities"], [])
        self.assertEqual(result["coverage"]["selected_records"], 0)
        self.assertIsNone(result["relationships"]["canonical_incident_count"])
        self.assertTrue(all(x["table"] == [] for x in result["charts"]))

    def test_calculation_is_stable_under_input_order_and_does_not_copy_raw_rows(self):
        records = [row("r2", sr_id="SR-B"), row("r1", sr_id="SR-A")]
        a, b = analyse(records), analyse(list(reversed(records)))
        self.assertEqual(a, b)
        self.assertNotIn("never-copy-the-raw-row", json.dumps(a))
        self.assertNotIn("raw_fields", a)

    def test_kpi_metadata_has_denominator_population_and_source_version(self):
        result = analyse([row("r1")], source_versions=[{"id": "v1", "sha256": "synthetic", "raw_bytes": "private"}])
        for item in result["kpis"]:
            for key in ["formula", "unit", "population", "period", "coverage", "numerator", "denominator", "missing_policy", "exclusions", "calculation_version", "source_versions", "evidence_record_ids"]:
                self.assertIn(key, item)
            self.assertIsNone(item["denominator"])
        self.assertEqual(result["source_versions"], [{"id": "v1", "sha256": "synthetic"}])

    def test_calculation_references_are_unique_and_resolve_priority_values(self):
        result = analyse([row("r1", sr_id="SR-A", event_date="2026-01-01", location="A"),
                          row("r2", sr_id="SR-A", event_date="2026-01-02", location="B"),
                          row("r3", "sr_reconciliation", sr_id="SR-A")])
        calculations = {x["calculation_id"]: x for x in result["calculations"]}
        self.assertEqual(len(calculations), len(result["calculations"]))
        for priority in result["priorities"]:
            for identifier in priority["evidence"]["calculation_ids"]:
                self.assertIn(identifier, calculations)
        conflict = next(x for x in result["priorities"] if x["id"] == "priority-conflicts")
        self.assertEqual(calculations[conflict["evidence"]["calculation_ids"][0]]["value"], 2)
        for chart in result["charts"]:
            for key in ["formula", "population", "period", "coverage", "exclusions", "missing_policy", "source_versions", "calculation_version"]:
                self.assertIn(key, chart)
        self.assertIn("year_month", result["charts"][2]["formula"])

    def test_changed_mapping_values_or_reference_change_the_calculation_version_id(self):
        a = [row("r1", sr_id="SR-A", wo_status="CLOSE"),
             row("r2", "sr_reconciliation", sr_id="SR-A")]
        b = deepcopy(a)
        b[0]["fields"]["wo_status"] = "COMP"
        self.assertNotEqual(analyse(a)["calculation_id"], analyse(b)["calculation_id"])
        b = deepcopy(a)
        b[0]["fields"]["sr_id"] = "SR-B"
        filters = {"grains": ["sr_reconciliation"]}
        self.assertNotEqual(analyse(a, filters=filters)["calculation_id"], analyse(b, filters=filters)["calculation_id"])

    def test_recorded_state_cannot_make_an_empty_field_complete(self):
        item = row("r1", sr_id=None)
        item["field_states"] = {"sr_id": "recorded"}
        result = analyse([item])
        self.assertEqual(completeness(result, "mms_work_order", "sr_id")["recorded"], 0)

    def test_source_versions_retain_mapping_and_safe_extraction_provenance(self):
        provenance = {
            "tool": "stdlib OOXML parser", "version": "synthetic-extractor/1",
            "python_version": "3.11", "xml_parser_version": "synthetic-parser",
            "original_preserved_by": "authorized_persistence_caller",
            "conversion": {"tool": "Synthetic converter", "version": "1",
                           "isolated_profile": True, "macros_disabled": True,
                           "docx_sha256": "synthetic-docx", "pdf_sha256": "synthetic-pdf",
                           "raw_text": "private-document-text"},
            "records": [{"raw_cell": "private-workbook-value"}],
        }
        result = analyse([row("r1")], source_versions=[{
            "id": "version-a", "mapping_revision": 2, "extraction_version": "extractor/1",
            "extraction": provenance, "raw_bytes": "private-original"}])
        version = result["source_versions"][0]
        self.assertEqual(version["mapping_revision"], 2)
        self.assertEqual(version["extraction_version"], "extractor/1")
        self.assertEqual(version["extraction"]["tool"], "stdlib OOXML parser")
        self.assertEqual(version["extraction"]["conversion"]["pdf_sha256"], "synthetic-pdf")
        self.assertNotIn("records", version["extraction"])
        self.assertNotIn("raw_text", version["extraction"]["conversion"])
        self.assertNotIn("private-", json.dumps(version))
        changed = deepcopy(version)
        changed["mapping_revision"] = 3
        self.assertNotEqual(result["calculation_id"], analyse([row("r1")], source_versions=[changed])["calculation_id"])

    def test_explicit_unknown_mapping_revision_stays_unknown(self):
        result = analyse([], source_versions=[{"id": "version-a", "mapping_revision": None}])
        self.assertIsNone(result["source_versions"][0]["mapping_revision"])

    def test_duplicate_ids_and_ambiguous_filter_dates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyse([row("r1"), row("r1")])
        with self.assertRaisesRegex(ValueError, "ISO"):
            analyse([], filters={"date_from": "03/04/2026"})
        with self.assertRaisesRegex(ValueError, "after"):
            analyse([], filters={"date_from": "2026-04-01", "date_to": "2026-03-01"})


if __name__ == "__main__":
    unittest.main()
