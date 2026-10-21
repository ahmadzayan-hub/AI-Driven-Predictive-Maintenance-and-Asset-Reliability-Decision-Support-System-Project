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

    def test_first_time_fix_is_unaffected_by_placeholder_zeros(self):
        # Summed over every record, as the Power BI Method page defines it.
        # Preventive placeholders add 0 to both sums, so they do not dilute
        # the rate the way they dilute a row average.
        result = kpis.REGISTER["first_time_fix"].compute(self.rows())
        self.assertEqual(result["records"], 10)
        self.assertEqual(result["records_excluded"], 0)
        self.assertAlmostEqual(result["value"], 75.0)
        self.assertEqual(result["population"], "all records")
        self.assertEqual(result["definition"], 2)

    def test_corrective_counts_on_a_record_typed_preventive_are_counted(self):
        # The case where the old and new definitions part: a record typed
        # preventive that carries corrective work orders.
        rows = self.rows() + [record(Record_ID="M1", Work_Order_Type="Preventive",
                                     First_Time_Fix_Count=0, Corrective_WO_Count=4)]
        self.assertAlmostEqual(kpis.REGISTER["first_time_fix"].compute(rows)["value"], 60.0)  # 12 / 20

    def test_the_row_average_is_a_different_number_and_is_named_as_one(self):
        rows = self.rows()
        for row in rows:
            row["First_Time_Fix_Rate"] = (
                0.0 if row["Work_Order_Type"] == "Preventive" else 0.75)
        kpi = kpis.REGISTER["first_time_fix"]
        weighted = kpi.compute(rows)["value"]
        # The row mean averages the preventive placeholders in; the ratio
        # of sums does not. Two numbers, two names.
        self.assertAlmostEqual(kpi.row_mean(rows, "First_Time_Fix_Rate"), 30.0)
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
        population = kpis.Kpi("x", "X", "س", "First_Time_Fix_Count", "Corrective_WO_Count",
                              kpis.corrective_only, "corrective records", contract.PERCENT, "test")
        rows = [record(Work_Order_Type="Preventive", Corrective_WO_Count=0,
                       First_Time_Fix_Count=0)]
        result = population.compute(rows)
        self.assertEqual(result["records"], 0)
        self.assertIsNone(result["value"])

    def test_a_percentage_result_is_scaled_once(self):
        rows = [record(Downtime_Hours=20.0, Planned_Operating_Hours=100.0)]
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
        self.assertEqual([k.key for k in available], ["utilisation"])
        self.assertIn("availability", unavailable)
        self.assertIn("Downtime_Hours", unavailable["availability"])
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

class CorrectedMeasuresTest(unittest.TestCase):
    """The pooled reliability definitions (2026-10-21 decision).

    Three synthetic records, small enough to check by hand:

        record  planned  operating  downtime  failures  preventive  corrective  overdue  SLA target/actual
        R1        100       80         10        2          6           4          1        8 / 6   (met)
        R2        100       70          0        0          5           0          0        8 / 8   (met, equal)
        R3        100       90         20        3          5           5          2        8 / 12  (missed)

    Totals: planned 300, operating 240, downtime 30, failures 5,
    preventive 16, corrective 9, overdue 3. R2 had no failure, so its
    operating hours are exposure with nothing to divide by: it is censored.
    """

    def rows(self):
        base = dict(Work_Order_Type="Corrective", Planned_Operating_Hours=100.0, SLA_Target_Hours=8.0)
        return [
            record(Record_ID="R1", Operating_Hours=80.0, Downtime_Hours=10.0, Failure_Count=2,
                   Preventive_WO_Count=6, Corrective_WO_Count=4, Overdue_WO_Count=1,
                   Completed_WO_Count=9, SLA_Actual_Hours=6.0, **base),
            record(Record_ID="R2", Operating_Hours=70.0, Downtime_Hours=0.0, Failure_Count=0,
                   Preventive_WO_Count=5, Corrective_WO_Count=0, Overdue_WO_Count=0,
                   Completed_WO_Count=5, SLA_Actual_Hours=8.0, **base),
            record(Record_ID="R3", Operating_Hours=90.0, Downtime_Hours=20.0, Failure_Count=3,
                   Preventive_WO_Count=5, Corrective_WO_Count=5, Overdue_WO_Count=2,
                   Completed_WO_Count=8, SLA_Actual_Hours=12.0, **base),
        ]

    def value(self, key, rows=None):
        return kpis.REGISTER[key].compute(self.rows() if rows is None else rows)

    def test_availability_is_uptime_on_planned_time_not_utilisation(self):
        result = self.value("availability")
        self.assertAlmostEqual(result["value"], 90.0)             # 1 - 30 / 300
        self.assertEqual(result["formula"], "1 - sum(Downtime_Hours) / sum(Planned_Operating_Hours)")
        self.assertAlmostEqual(self.value("utilisation")["value"], 80.0)   # 240 / 300
        self.assertNotEqual(kpis.REGISTER["availability"].formula,
                            kpis.REGISTER["utilisation"].formula,
                            "operating / planned is utilisation; the register must not call it availability")

    def test_the_old_definition_is_not_what_availability_returns(self):
        """ADR 0049 shipped operating / planned under this name and reported 79.39%
        beside a team dashboard showing 97.0%. A hand-built case pins the fix."""
        rows = [record(Operating_Hours=60.0, Downtime_Hours=1.0, Planned_Operating_Hours=100.0)]
        self.assertAlmostEqual(self.value("availability", rows)["value"], 99.0)
        self.assertAlmostEqual(self.value("utilisation", rows)["value"], 60.0)

    def test_inherent_availability_is_mtbf_over_mtbf_plus_mttr(self):
        mtbf, mttr = self.value("mtbf")["value"], self.value("mttr")["value"]
        inherent = self.value("availability_inherent")
        self.assertAlmostEqual(inherent["value"], 100 * mtbf / (mtbf + mttr))
        self.assertAlmostEqual(inherent["value"], 100 * 240 / 270)
        self.assertNotAlmostEqual(inherent["value"], self.value("availability")["value"],
                                  msg="the two variants use different time bases and must not be confused")

    def test_mtbf_is_pooled_and_a_record_with_no_failure_adds_exposure_only(self):
        result = self.value("mtbf")
        self.assertAlmostEqual(result["value"], 48.0)             # 240 / 5
        self.assertEqual((result["numerator"], result["denominator"]), (240.0, 5.0))
        # The wrong way: the stored per-record MTBF (operating / failures, with a
        # no-failure record carrying its operating hours) averaged over records.
        row_values = [80 / 2, 70.0, 90 / 3]
        self.assertAlmostEqual(sum(row_values) / 3, 46.666666, places=5)
        self.assertNotAlmostEqual(result["value"], sum(row_values) / 3, places=2)
        # More censored exposure raises MTBF by exactly its hours / failures.
        more = self.rows() + [record(Record_ID="R4", Operating_Hours=100.0, Downtime_Hours=0.0,
                                     Failure_Count=0, Planned_Operating_Hours=100.0)]
        self.assertAlmostEqual(self.value("mtbf", more)["value"], 68.0)   # 340 / 5
        self.assertEqual(self.value("mtbf", more)["records"], 4)

    def test_mtbf_with_no_failure_anywhere_is_undefined_not_zero_or_infinite(self):
        rows = [record(Failure_Count=0, Downtime_Hours=0.0, Operating_Hours=80.0)]
        result = self.value("mtbf", rows)
        self.assertIsNone(result["value"])
        self.assertIn("undefined", result["undefined_reason"])

    def test_mttr_is_all_downtime_over_all_failures(self):
        # The Power BI Method page: MTTR = sum(Downtime h) / sum(Failures).
        result = self.value("mttr")
        self.assertAlmostEqual(result["value"], 6.0)              # 30 / 5
        self.assertEqual((result["records"], result["records_excluded"]), (3, 0))
        self.assertEqual(result["population"], "all records")
        self.assertEqual(result["definition"], 2)
        # Downtime on a record with no failure now counts, as stated on the card.
        rows = self.rows()
        rows[1]["Downtime_Hours"] = 5.0
        self.assertAlmostEqual(self.value("mttr", rows)["value"], 7.0)   # 35 / 5
        self.assertIn("overstates", kpis.REGISTER["mttr"].edge_cases)

    def test_overdue_rate_and_overdue_share_are_two_named_measures(self):
        rate, share = self.value("overdue_rate"), self.value("overdue_share")
        self.assertAlmostEqual(rate["value"], 100 * 3 / 25)       # overdue / (preventive + corrective)
        self.assertAlmostEqual(share["value"], 100 * 3 / 22)      # overdue / completed
        self.assertNotEqual(rate["formula"], share["formula"])
        self.assertNotEqual(kpis.REGISTER["overdue_rate"].title, kpis.REGISTER["overdue_share"].title)

    def test_sla_attainment_counts_equality_as_met(self):
        result = self.value("sla_attainment")
        self.assertAlmostEqual(result["value"], 100 * 2 / 3)      # R1 met, R2 met on equality, R3 missed
        self.assertEqual(result["formula"],
                         "count(records where SLA_Actual_Hours <= SLA_Target_Hours) / count(records)")

    def test_a_record_with_no_sla_reading_is_unmeasured_not_a_miss(self):
        rows = self.rows()
        rows[2]["SLA_Actual_Hours"] = None
        result = self.value("sla_attainment", rows)
        self.assertEqual((result["records"], result["records_unmeasured"]), (2, 1))
        self.assertAlmostEqual(result["value"], 100.0)

    def test_the_sla_score_is_not_attainment(self):
        """The mean of MIN(1, target / actual) is a performance score. It must not
        be offered under the compliance name, so it is not in the register."""
        self.assertNotIn("sla_compliance", kpis.REGISTER)
        self.assertNotIn("sla_score", kpis.REGISTER)
        score = sum(min(1, 8 / a) for a in (6.0, 8.0, 12.0)) / 3
        self.assertAlmostEqual(score, 0.8889, places=4)
        self.assertGreater(100 * score, self.value("sla_attainment")["value"])

    def test_first_time_fix_and_repeat_repair_use_corrective_work_and_sum_to_one(self):
        rows = [record(Record_ID="C1", First_Time_Fix_Count=3, Repeat_Repair_Count=1, Corrective_WO_Count=4),
                record(Record_ID="C2", First_Time_Fix_Count=4, Repeat_Repair_Count=2, Corrective_WO_Count=6),
                record(Record_ID="P1", Work_Order_Type="Preventive", First_Time_Fix_Count=0,
                       Repeat_Repair_Count=0, Corrective_WO_Count=0)]
        first, repeat = self.value("first_time_fix", rows), self.value("repeat_repair", rows)
        self.assertAlmostEqual(first["value"], 70.0)               # 7 / 10, not (75 + 66.7 + 0) / 3
        self.assertAlmostEqual(first["value"] + repeat["value"], 100.0)
        self.assertEqual(first["records_excluded"], 0)

    def test_every_new_or_changed_measure_prints_its_formula_and_has_both_titles(self):
        for key in ("availability", "utilisation", "availability_inherent", "mtbf", "mttr",
                    "overdue_rate", "overdue_share", "sla_attainment"):
            with self.subTest(kpi=key):
                kpi = kpis.REGISTER[key]
                self.assertIn("/", kpi.formula)
                self.assertTrue(kpi.title.strip())
                self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in kpi.title_ar), key)
                self.assertTrue(kpi.meaning.strip() and kpi.edge_cases.strip(), key)
                self.assertIn(kpi.missing, kpis.MISSING_POLICIES)

    def test_hours_based_and_replacement_value_measures_are_not_offered(self):
        """These need fields no export here carries. Offering a stand-in would be
        a guess presented as a measurement; they are named gaps instead."""
        for key in ("planned_maintenance_hours", "wrench_time", "pm_compliance",
                    "schedule_compliance", "backlog_weeks", "maintenance_cost_pct_rav"):
            self.assertNotIn(key, kpis.REGISTER)

    def test_availability_needs_downtime_and_planned_hours_and_says_so(self):
        _, unavailable = kpis.computable(["Record_ID", "Operating_Hours", "Planned_Operating_Hours"])
        self.assertIn("Downtime_Hours", unavailable["availability"])
        available, unavailable = kpis.computable(["Downtime_Hours", "Planned_Operating_Hours"])
        keys = [k.key for k in available]
        self.assertIn("availability", keys)
        self.assertNotIn("utilisation", keys)
        self.assertIn("Operating_Hours", unavailable["utilisation"])

    def test_every_population_has_an_arabic_name_and_keeps_its_english_code(self):
        # An Arabic page showed "all records": the register named populations
        # in English only. The code stays English, because exports and
        # policies match on it; the Arabic name travels beside it.
        for kpi in kpis.REGISTER.values() if isinstance(kpis.REGISTER, dict) else kpis.REGISTER:
            self.assertIn(kpi.population_name, kpis.POPULATION_AR, kpi.key)
            self.assertRegex(kpis.POPULATION_AR[kpi.population_name], "[\u0600-\u06FF]")
        with self.assertRaises(ValueError):
            kpis.Kpi("x", "X", "س", "Downtime_Hours", kpis.RECORDS, lambda row: True,
                     "untranslated records", contract.HOURS, "test")

    def test_every_measure_names_a_dashboard_family_and_it_is_not_a_verdict(self):
        """The family groups a card on the dashboard. It must be declared, known,
        and returned with the figure, and it must not depend on the value."""
        for key, kpi in kpis.REGISTER.items():
            with self.subTest(kpi=key):
                self.assertIn(kpi.family, kpis.FAMILIES)
                self.assertNotEqual(kpi.family, "other", "every shipped measure has a real family")
        rows = self.rows()
        self.assertEqual(self.value("availability", rows)["family"], "reliability")
        self.assertEqual(self.value("sla_attainment", rows)["family"], "execution")
        worse = [dict(row, Downtime_Hours=90.0) for row in rows]
        self.assertEqual(self.value("availability", worse)["family"], "reliability")
        with self.assertRaises(ValueError):
            kpis.Kpi("x", "X", "س", "Downtime_Hours", kpis.RECORDS, kpis.every_record,
                     "all records", contract.HOURS, "test", edge_cases="e", family="good")

    def test_the_register_holds_eighteen_measures(self):
        """Fourteen after the first 21 October decision, plus the four the
        Power BI report shows that the register lacked."""
        self.assertEqual(len(kpis.REGISTER), 18)

    def test_the_power_bi_measures_the_register_lacked(self):
        rows = self.rows()
        for row, loss, cost in zip(rows, (900.0, 0.0, 300.0), (100.0, 100.0, 100.0)):
            row["Production_Loss_USD"], row["Maintenance_Cost_USD"] = loss, cost
        per_1000 = self.value("downtime_per_1000_planned", rows)
        self.assertAlmostEqual(per_1000["value"], 100.0)          # 1,000 x 30 / 300
        self.assertEqual(per_1000["formula"],
                         "1,000 × sum(Downtime_Hours) / sum(Planned_Operating_Hours)")
        availability = self.value("availability", rows)["value"]
        self.assertAlmostEqual(per_1000["value"], 10 * (100 - availability))
        self.assertAlmostEqual(self.value("failures_per_record", rows)["value"], 5 / 3)
        self.assertAlmostEqual(self.value("loss_per_record", rows)["value"], 400.0)        # 1,200 / 3
        self.assertAlmostEqual(self.value("loss_to_maintenance_ratio", rows)["value"], 4.0)  # 1,200 / 300
        self.assertEqual(kpis.REGISTER["loss_to_maintenance_ratio"].scale, contract.RATIO)
