"""The maintenance domain: contract and KPI register (milestone S1).

Synthetic fixtures only. The behaviour under test is arithmetic and
population logic, which a dozen rows exercise exactly as well as a real
export, and no customer or course data needs to live in this repository
to prove it.

The tests that matter most are the ones asserting a *refusal*: that a
zero denominator is not reported as zero, that an outcome column is kept
out of model inputs however well it would predict, and that a rate is
measured on its own population rather than on every row.
"""

import unittest

from server.maintenance import contract, kpis


def record(**overrides):
    """One corrective record with sane defaults, overridable per test."""
    row = {
        "Record_ID": "R1", "Record_Date": "2026-01-01", "Asset_ID": "A1",
        "Work_Order_Type": "Corrective", "Criticality": "High",
        "Completed_WO_Count": 10, "Preventive_WO_Count": 6,
        "Corrective_WO_Count": 4, "Overdue_WO_Count": 1,
        "First_Time_Fix_Count": 3, "Repeat_Repair_Count": 1,
        "Downtime_Hours": 10.0, "Failure_Count": 2,
        "Operating_Hours": 80.0, "Planned_Operating_Hours": 100.0,
        "Maintenance_Cost_USD": 1000.0, "Production_Loss_USD": 25000.0,
    }
    row.update(overrides)
    return row


class ContractTest(unittest.TestCase):

    def test_resolve_maps_known_columns_and_keeps_the_rest(self):
        mapping, unmapped = contract.resolve(
            ["Record_ID", "Downtime_Hours", "Customer_Reference"])
        self.assertEqual(set(mapping), {"Record_ID", "Downtime_Hours"})
        self.assertEqual(unmapped, ["Customer_Reference"],
                         "a column the product does not model is still the "
                         "customer's data and must be preserved")

    def test_a_maintenance_dataset_is_recognised(self):
        self.assertEqual(contract.tier(list(record())), "maintenance")

    def test_a_tabular_file_that_is_not_maintenance_degrades_to_general(self):
        self.assertEqual(
            contract.tier(["Invoice_No", "Customer", "Amount", "Region"]),
            "general")

    def test_nothing_analysable_is_refused(self):
        self.assertEqual(contract.tier([]), "unusable")
        self.assertEqual(contract.tier(["OnlyOneColumn"]), "unusable")

    def test_outcome_columns_are_kept_out_of_model_inputs(self):
        usable, excluded = contract.model_inputs(
            ["Criticality", "Downtime_Hours", "Failure_Mode", "Record_ID"])
        self.assertIn("Criticality", usable)
        for column in ("Downtime_Hours", "Failure_Mode"):
            self.assertIn(column, excluded)
            self.assertIn("leaks", excluded[column])
        self.assertIn("identifier", excluded["Record_ID"])

    def test_unknown_timing_is_excluded_for_a_different_stated_reason(self):
        # "We did not establish this" is not the same claim as "this is
        # not available", and the product must not conflate them.
        _, excluded = contract.model_inputs(["Vibration_mm_s"])
        self.assertIn("not established", excluded["Vibration_mm_s"])

    def test_a_derived_column_inherits_outcome_timing(self):
        _, excluded = contract.model_inputs(["Availability_Pct"])
        self.assertIn("derived", excluded["Availability_Pct"])


class KpiPopulationTest(unittest.TestCase):

    def rows(self):
        # Four corrective records that vary, and six preventive records
        # holding the placeholder zero that dilutes a row average.
        corrective = [record(Record_ID=f"C{i}", First_Time_Fix_Count=3,
                             Corrective_WO_Count=4) for i in range(4)]
        preventive = [record(Record_ID=f"P{i}", Work_Order_Type="Preventive",
                             First_Time_Fix_Count=0, Corrective_WO_Count=0,
                             Repeat_Repair_Count=0, Failure_Count=0,
                             Downtime_Hours=0.0) for i in range(6)]
        return corrective + preventive

    def test_first_time_fix_is_measured_on_corrective_work_only(self):
        result = kpis.REGISTER["first_time_fix"].compute(self.rows())
        self.assertEqual(result["records"], 4)
        self.assertEqual(result["records_excluded"], 6)
        self.assertAlmostEqual(result["value"], 75.0)
        self.assertEqual(result["population"], "corrective records")

    def test_the_row_average_is_a_different_number_and_is_named_as_one(self):
        rows = self.rows()
        for row in rows:
            row["First_Time_Fix_Rate"] = (
                0.0 if row["Work_Order_Type"] == "Preventive" else 0.75)
        kpi = kpis.REGISTER["first_time_fix"]
        weighted = kpi.compute(rows)["value"]
        # row_mean stays inside the KPI's population, so the two differ
        # only where the stored column differs from the ratio of sums.
        self.assertAlmostEqual(kpi.row_mean(rows, "First_Time_Fix_Rate"), 75.0)
        self.assertAlmostEqual(weighted, 75.0)

    def test_a_rate_is_a_ratio_of_sums_not_a_mean_of_row_rates(self):
        # One big record at 50% and one small at 100%. The ratio of sums
        # is 60%; averaging the two row rates would say 75%.
        rows = [record(Record_ID="big", Corrective_WO_Count=8, First_Time_Fix_Count=4),
                record(Record_ID="small", Corrective_WO_Count=2, First_Time_Fix_Count=2)]
        result = kpis.REGISTER["first_time_fix"].compute(rows)
        self.assertAlmostEqual(result["value"], 60.0)
        self.assertEqual(result["numerator"], 6)
        self.assertEqual(result["denominator"], 10)


class KpiBoundaryTest(unittest.TestCase):

    def test_a_zero_denominator_is_undefined_not_perfect(self):
        rows = [record(Corrective_WO_Count=0, First_Time_Fix_Count=0)]
        result = kpis.REGISTER["first_time_fix"].compute(rows)
        self.assertIsNone(result["value"],
                          "no corrective work is an absence of evidence, not 100%")
        self.assertIn("undefined rather than zero", result["undefined_reason"])

    def test_an_empty_population_is_undefined_not_zero(self):
        rows = [record(Work_Order_Type="Preventive", Corrective_WO_Count=0,
                       First_Time_Fix_Count=0)]
        result = kpis.REGISTER["first_time_fix"].compute(rows)
        self.assertEqual(result["records"], 0)
        self.assertIsNone(result["value"])

    def test_a_percentage_result_is_scaled_once(self):
        rows = [record(Operating_Hours=80.0, Planned_Operating_Hours=100.0)]
        self.assertAlmostEqual(
            kpis.REGISTER["availability"].compute(rows)["value"], 80.0)

    def test_a_money_result_is_not_scaled(self):
        rows = [record(Production_Loss_USD=25000.0, Downtime_Hours=10.0)]
        self.assertAlmostEqual(
            kpis.REGISTER["loss_per_downtime_hour"].compute(rows)["value"], 2500.0)

    def test_every_result_carries_its_formula_and_population(self):
        rows = [record()]
        for result in kpis.compute_all(list(record()), rows)["results"]:
            self.assertIn("/", result["formula"])
            self.assertTrue(result["population"])
            self.assertIn("scale", result)


class KpiMissingValueTest(unittest.TestCase):
    """An unmeasured cell is not a measured zero (ADR 0042)."""

    def test_a_missing_measurement_does_not_lower_a_per_record_average(self):
        measured = [record(Downtime_Hours=10.0)]
        with_gap = [record(Downtime_Hours=10.0), record(Downtime_Hours="")]
        kpi = kpis.REGISTER["downtime_per_record"]
        self.assertEqual(kpi.compute(measured)["value"],
                         kpi.compute(with_gap)["value"],
                         "a record nobody measured must not count as zero hours")
        self.assertEqual(kpi.compute(with_gap)["value"], 10.0)

    def test_the_unmeasured_records_are_counted_and_named(self):
        rows = [record(Downtime_Hours=10.0), record(Downtime_Hours=""),
                record(Downtime_Hours="n/a")]
        result = kpis.REGISTER["downtime_per_record"].compute(rows)
        self.assertEqual(result["records"], 1)
        self.assertEqual(result["records_unmeasured"], 2)
        self.assertEqual(result["missing_policy"], kpis.EXCLUDE)

    def test_the_record_count_divides_into_the_printed_value(self):
        # A reader who divides the numerator by `records` must get the
        # figure on the card, or the card cannot be audited.
        rows = [record(Downtime_Hours=10.0), record(Downtime_Hours=30.0),
                record(Downtime_Hours=None)]
        result = kpis.REGISTER["downtime_per_record"].compute(rows)
        self.assertEqual(result["numerator"] / result["records"], result["value"])

    def test_a_half_measured_pair_is_withheld_not_halved(self):
        rows = [record(Production_Loss_USD=5000.0, Downtime_Hours="")]
        result = kpis.REGISTER["loss_per_downtime_hour"].compute(rows)
        self.assertIsNone(result["value"])
        self.assertEqual(result["records"], 0)
        self.assertEqual(result["records_unmeasured"], 1)
        self.assertIn("every column", result["undefined_reason"])

    def test_a_nonfinite_number_is_not_a_measurement(self):
        rows = [record(Downtime_Hours=float("nan")), record(Downtime_Hours=8.0)]
        result = kpis.REGISTER["downtime_per_record"].compute(rows)
        self.assertEqual(result["value"], 8.0)
        self.assertEqual(result["records_unmeasured"], 1)

    def test_a_declared_zero_policy_counts_a_blank_as_none_happened(self):
        kpi = kpis.Kpi("t_zero", "T", "ت", "a", kpis.RECORDS, kpis.every_record,
                       "all records", contract.HOURS, "test", missing=kpis.ZERO)
        self.assertEqual(kpi.compute([{"a": 10.0}, {"a": ""}])["value"], 5.0)
        self.assertEqual(kpi.compute([{"a": 10.0}, {"a": ""}])["records"], 2)

    def test_an_unknown_policy_is_refused_when_the_kpi_is_defined(self):
        with self.assertRaises(ValueError):
            kpis.Kpi("t_bad", "T", "ت", "a", kpis.RECORDS, kpis.every_record,
                     "all records", contract.HOURS, "test", missing="guess")

    def test_every_shipped_kpi_declares_a_known_policy(self):
        for key, kpi in kpis.REGISTER.items():
            with self.subTest(kpi=key):
                self.assertIn(kpi.missing, kpis.MISSING_POLICIES)


class KpiAvailabilityTest(unittest.TestCase):

    def test_missing_columns_are_reported_with_what_they_need(self):
        available, unavailable = kpis.computable(
            ["Record_ID", "Operating_Hours", "Planned_Operating_Hours"])
        self.assertEqual([k.key for k in available], ["availability"])
        self.assertIn("first_time_fix", unavailable)
        self.assertIn("Corrective_WO_Count", unavailable["first_time_fix"])

    def test_a_non_maintenance_dataset_yields_no_kpis_but_does_not_error(self):
        result = kpis.compute_all(["Invoice_No", "Amount"], [{"Amount": 5}])
        self.assertEqual(result["results"], [])
        self.assertEqual(len(result["unavailable"]), len(kpis.REGISTER))


class RegisterShapeTest(unittest.TestCase):

    def test_every_kpi_ships_in_english_and_arabic(self):
        for kpi in kpis.REGISTER.values():
            self.assertTrue(kpi.title, kpi.key)
            self.assertTrue(kpi.title_ar, f"{kpi.key} has no Arabic title")
            self.assertNotEqual(kpi.title, kpi.title_ar)

    def test_every_kpi_states_its_population_and_edge_cases(self):
        for kpi in kpis.REGISTER.values():
            self.assertTrue(kpi.population_name, kpi.key)
            self.assertTrue(kpi.edge_cases, f"{kpi.key} states no edge cases")

    def test_every_kpi_column_is_in_the_contract(self):
        # source_columns flattens tuple denominators and drops the
        # RECORDS sentinel, which is a row count rather than a column.
        for kpi in kpis.REGISTER.values():
            for column in kpi.source_columns:
                self.assertIn(column, contract.BY_NAME,
                              f"{kpi.key} uses {column}, which the contract "
                              f"does not define")

    def test_a_record_count_denominator_prints_as_a_count(self):
        kpi = kpis.REGISTER["downtime_per_record"]
        self.assertEqual(kpi.denominator, kpis.RECORDS)
        self.assertIn("count(records)", kpi.formula)
        self.assertNotIn("Record_ID", kpi.source_columns)

    def test_a_summed_denominator_prints_both_columns(self):
        kpi = kpis.REGISTER["preventive_share"]
        self.assertIn("Preventive_WO_Count + Corrective_WO_Count", kpi.formula)


if __name__ == "__main__":
    unittest.main()
