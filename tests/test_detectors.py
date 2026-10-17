"""Governance detectors (server/detectors.py).

Every fixture here is synthetic and built in the test. The detectors are
structural, so a dozen rows exhibiting a pattern exercise them as well as
a real file does, and no dataset belonging to anyone needs to live in
this repository to prove they work.

Each detector gets two tests: one that it fires on the pattern, and one
that it stays quiet on data that merely looks similar. The second is the
important one. A detector that fires on sound data is worse than no
detector, because the whole value of a finding is that it means
something.
"""

import unittest

from server import detectors


def table(columns, *values):
    """Rows as dicts from a header and positional tuples."""
    return [dict(zip(columns, v)) for v in values]


class IdentityCollapseTest(unittest.TestCase):
    """A column named like an identifier that does not identify."""

    COLUMNS = ("Asset_ID", "Asset_Class", "Site", "Reading")

    # Twelve keys of four rows each: enough distinct keys to be an
    # entity rather than a dimension, and each repeating.
    KEYS, PER_KEY = 12, 4

    def bad_key(self):
        # Each key mixes classes and sites, so it labels no entity.
        rows = []
        for i in range(self.KEYS * self.PER_KEY):
            rows.append({"Asset_ID": f"AST-{i // self.PER_KEY:03d}",
                         "Asset_Class": f"Class-{i % 3}",
                         "Site": f"Site-{i % 4}", "Reading": i})
        return rows

    def good_key(self):
        # Each key keeps its class and site, as a real asset does.
        rows = []
        for i in range(self.KEYS * self.PER_KEY):
            key = i // self.PER_KEY
            rows.append({"Asset_ID": f"AST-{key:03d}", "Asset_Class": f"Class-{key}",
                         "Site": f"Site-{key}", "Reading": i})
        return rows

    def test_fires_when_attributes_are_unstable_inside_the_key(self):
        found = detectors.identity_collapse(self.COLUMNS, self.bad_key())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["detector"], "identity_collapse")
        self.assertIn("Asset_ID", found[0]["headline"])
        self.assertEqual(found[0]["numbers"]["distinct_keys"], self.KEYS)

    def test_silent_when_the_key_holds_its_attributes(self):
        self.assertEqual(detectors.identity_collapse(self.COLUMNS, self.good_key()), [])

    def test_silent_on_a_dimension_that_never_claimed_to_identify(self):
        # Region mixes everything, as a dimension does, and is not named
        # as an identifier, so it must not be reported.
        rows = [{"Region": f"R{i % 2}", "Asset_Class": f"C{i % 3}", "Site": f"S{i % 4}"}
                for i in range(40)]
        self.assertEqual(
            detectors.identity_collapse(("Region", "Asset_Class", "Site"), rows), [])

    def test_silent_on_a_row_id_that_identifies_only_the_row(self):
        rows = [{"Record_ID": f"R{i}", "Asset_Class": f"C{i % 3}", "Site": f"S{i % 4}"}
                for i in range(40)]
        self.assertEqual(
            detectors.identity_collapse(("Record_ID", "Asset_Class", "Site"), rows), [])


class TargetLeakageTest(unittest.TestCase):
    """Columns driven by one switch, reported once."""

    def split_rows(self):
        # Type decides every other column: one switch, many columns.
        rows = []
        for i in range(200):
            corrective = i % 4 != 0
            rows.append({"Type": "Corrective" if corrective else "Preventive",
                         "Downtime": 10.0 if corrective else 0.0,
                         "Failures": 2 if corrective else 0,
                         "Cost": 100.0 + i})
        return rows

    def test_reports_one_finding_for_one_split(self):
        found = detectors.target_leakage(
            ("Type", "Downtime", "Failures", "Cost"), self.split_rows())
        self.assertEqual(len(found), 1, "a single split must not be reported pair by pair")
        self.assertIn("Downtime", found[0]["columns"])
        self.assertIn("Failures", found[0]["columns"])
        self.assertEqual(found[0]["numbers"]["explained_by"], "Type")

    def test_silent_on_independent_columns(self):
        rows = [{"Team": f"T{i % 3}", "Downtime": float(i % 7), "Cost": float(i % 5)}
                for i in range(200)]
        self.assertEqual(detectors.target_leakage(("Team", "Downtime", "Cost"), rows), [])

    def test_silent_when_the_minority_side_is_too_thin_to_prove_anything(self):
        # Two positive rows in 200: almost any column looks pure.
        rows = [{"Team": f"T{i % 3}", "Incidents": 1.0 if i < 2 else 0.0,
                 "Flag": 1.0 if i < 2 else 0.0} for i in range(200)]
        self.assertEqual(detectors.target_leakage(("Team", "Incidents", "Flag"), rows), [])


class PlaceholderRateTest(unittest.TestCase):
    """A rate that is filler for a subgroup."""

    COLUMNS = ("Type", "Fix_Rate")

    def test_fires_and_reports_both_means(self):
        rows = ([{"Type": "Preventive", "Fix_Rate": 0.0} for _ in range(40)]
                + [{"Type": "Corrective", "Fix_Rate": r}
                   for _ in range(20) for r in (0.7, 0.8, 0.9)])
        found = detectors.placeholder_rates(self.COLUMNS, rows)
        self.assertEqual(len(found), 1)
        numbers = found[0]["numbers"]
        self.assertEqual(numbers["placeholder_rows"], 40)
        self.assertAlmostEqual(numbers["mean_all_pct"], 48.0, places=1)
        self.assertAlmostEqual(numbers["mean_measured_pct"], 80.0, places=1)

    def test_silent_when_every_group_varies(self):
        rows = [{"Type": f"T{i % 2}", "Fix_Rate": (i % 10) / 10} for i in range(100)]
        self.assertEqual(detectors.placeholder_rates(self.COLUMNS, rows), [])

    def test_silent_when_the_constant_group_is_a_rounding_share(self):
        rows = ([{"Type": "Preventive", "Fix_Rate": 0.0} for _ in range(2)]
                + [{"Type": "Corrective", "Fix_Rate": r}
                   for _ in range(33) for r in (0.7, 0.8, 0.9)])
        self.assertEqual(detectors.placeholder_rates(self.COLUMNS, rows), [])


class ScaleMislabelledTest(unittest.TestCase):

    def test_fires_on_a_pct_column_holding_a_fraction(self):
        rows = [{"Availability_Pct": 0.9} for _ in range(5)]
        found = detectors.scale_mislabelled(("Availability_Pct",), rows)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], "medium")

    def test_silent_on_a_pct_column_holding_a_percentage(self):
        rows = [{"Availability_Pct": 90.0} for _ in range(5)]
        self.assertEqual(detectors.scale_mislabelled(("Availability_Pct",), rows), [])

    def test_silent_on_a_column_that_promises_no_scale(self):
        rows = [{"Condition": 0.9} for _ in range(5)]
        self.assertEqual(detectors.scale_mislabelled(("Condition",), rows), [])


class BrokenIdentityTest(unittest.TestCase):

    COLUMNS = ("Maintenance_Cost_USD", "Parts_Cost_USD", "Labor_Cost_USD")

    def test_fires_when_a_total_never_equals_its_parts(self):
        rows = [{"Maintenance_Cost_USD": 130.0, "Parts_Cost_USD": 60.0,
                 "Labor_Cost_USD": 40.0} for _ in range(10)]
        found = detectors.broken_identity(self.COLUMNS, rows)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["numbers"]["share_of_total"], 0.2308, places=3)

    def test_silent_when_the_identity_holds(self):
        rows = [{"Maintenance_Cost_USD": 100.0, "Parts_Cost_USD": 60.0,
                 "Labor_Cost_USD": 40.0} for _ in range(10)]
        self.assertEqual(detectors.broken_identity(self.COLUMNS, rows), [])

    def test_silent_when_names_share_only_a_unit(self):
        # Nobody claimed operating hours were MTBF plus MTTR.
        rows = [{"Operating_Hours": 500.0, "MTBF_Hours": 300.0, "MTTR_Hours": 10.0}
                for _ in range(10)]
        self.assertEqual(
            detectors.broken_identity(("Operating_Hours", "MTBF_Hours", "MTTR_Hours"),
                                      rows), [])

    def test_silent_when_the_parts_exceed_the_total(self):
        # Related by something other than addition, so saying it is not
        # a sum tells the reader nothing.
        rows = [{"Net_Cost_USD": 40.0, "Gross_Cost_USD": 100.0, "Rebate_Cost_USD": 60.0}
                for _ in range(10)]
        self.assertEqual(
            detectors.broken_identity(("Net_Cost_USD", "Gross_Cost_USD", "Rebate_Cost_USD"),
                                      rows), [])


class UnevenPeriodsTest(unittest.TestCase):

    def test_fires_when_one_period_is_half_the_others(self):
        rows = ([{"Record_Date": "2024-01-01"} for _ in range(100)]
                + [{"Record_Date": "2025-01-01"} for _ in range(50)])
        found = detectors.uneven_periods(("Record_Date",), rows)
        self.assertEqual(len(found), 1)
        self.assertAlmostEqual(found[0]["numbers"]["imbalance"], 0.5, places=2)

    def test_silent_when_periods_are_balanced(self):
        rows = ([{"Record_Date": "2024-01-01"} for _ in range(100)]
                + [{"Record_Date": "2025-01-01"} for _ in range(98)])
        self.assertEqual(detectors.uneven_periods(("Record_Date",), rows), [])


class DetectorNamingTest(unittest.TestCase):

    def test_each_finding_is_keyed_by_the_function_that_produced_it(self):
        # Anything that consumes findings matches them to detectors by
        # this name. A plural function emitting a singular key makes a
        # quality check fail while reporting that it found nothing.
        rows = ([{"Type": "Preventive", "Fix_Rate": 0.0, "Availability_Pct": 0.9,
                  "Record_Date": "2024-01-01"} for _ in range(40)]
                + [{"Type": "Corrective", "Fix_Rate": r, "Availability_Pct": 0.9,
                    "Record_Date": "2025-01-01"}
                   for _ in range(20) for r in (0.7, 0.8, 0.9)])
        columns = ("Type", "Fix_Rate", "Availability_Pct", "Record_Date")
        produced = {f["detector"] for f in detectors.run_all(columns, rows)}
        known = {d.__name__ for d in detectors.DETECTORS}
        self.assertTrue(produced, "the fixture should trigger something")
        self.assertTrue(produced <= known,
                        f"findings keyed by an unknown name: {produced - known}")


class RunAllTest(unittest.TestCase):

    def test_orders_findings_with_the_most_severe_first(self):
        rows = ([{"Type": "Preventive", "Fix_Rate": 0.0, "Availability_Pct": 0.9}
                 for _ in range(40)]
                + [{"Type": "Corrective", "Fix_Rate": r, "Availability_Pct": 0.9}
                   for _ in range(20) for r in (0.7, 0.8, 0.9)])
        found = detectors.run_all(("Type", "Fix_Rate", "Availability_Pct"), rows)
        severities = [f["severity"] for f in found]
        self.assertEqual(severities, sorted(severities,
                                            key=lambda s: detectors.SEVERITY_ORDER[s]))
        self.assertIn("high", severities)

    def test_empty_data_produces_no_findings_and_no_error(self):
        self.assertEqual(detectors.run_all(("A", "B"), []), [])

    def test_every_finding_carries_its_numbers_and_columns(self):
        rows = ([{"Type": "Preventive", "Fix_Rate": 0.0} for _ in range(40)]
                + [{"Type": "Corrective", "Fix_Rate": r}
                   for _ in range(20) for r in (0.7, 0.8, 0.9)])
        for finding in detectors.run_all(("Type", "Fix_Rate"), rows):
            self.assertTrue(finding["numbers"], "a finding must show what it fired on")
            self.assertTrue(finding["columns"])
            self.assertIn(finding["severity"], detectors.SEVERITY_ORDER)


if __name__ == "__main__":
    unittest.main()
