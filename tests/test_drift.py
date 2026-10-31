"""R5: drift between snapshots of a live source (31 October 2026).

Four stated rules: columns added or removed, the row count halved or
doubled, a numeric median moving by half its previous interquartile spread,
and the share of empty cells moving by 10 points. The alert is stated with
the snapshot in the connector's language; nothing is blocked.
"""
import unittest

from server import drift
from tests import test_connectors
from tests.test_connectors import source

URL = "https://data.example.com/sales.csv"


def table(rows, columns=("month", "region", "revenue")):
    return list(columns), [dict(zip(columns, r)) for r in rows]


BASE = [(f"2025-{m:02d}", "North" if m % 2 else "South", str(100 + m)) for m in range(1, 13)]


class CompareTests(unittest.TestCase):

    def test_a_stable_snapshot_raises_nothing(self):
        old = table(BASE)
        new = table(BASE + [("2026-01", "North", "113")])
        self.assertEqual(drift.compare(*old, *new), [])
        self.assertIsNone(drift.describe([]))

    def test_columns_added_and_removed(self):
        old = table(BASE)
        new = table([(m, r, v, "x") for m, r, v in BASE], ("month", "region", "sales", "site"))
        found = drift.compare(*old, *new)[0]
        self.assertEqual((found["added"], found["removed"]), (["sales", "site"], ["revenue"]))

    def test_rows_halved_or_doubled(self):
        self.assertEqual(drift.compare(*table(BASE), *table(BASE[:6]))[0],
                         {"kind": "rows", "old": 12, "new": 6})
        self.assertEqual(drift.compare(*table(BASE), *table(BASE[:7])), [])
        self.assertEqual(drift.compare(*table(BASE), *table(BASE * 2))[0]["kind"], "rows")

    def test_a_median_shift_of_half_the_spread(self):
        # Previous revenue 101..112: median 106.5, quartiles 103.75 and 109.25, spread 5.5.
        shifted = [(m, r, str(int(v) + 3)) for m, r, v in BASE]   # 3 >= 0.5 x 5.5
        small = [(m, r, str(int(v) + 2)) for m, r, v in BASE]     # 2 < 2.75
        found = drift.compare(*table(BASE), *table(shifted))
        self.assertEqual(found, [{"kind": "median", "column": "revenue",
                                  "old": 106.5, "new": 109.5, "spread": 5.5}])
        self.assertEqual(drift.compare(*table(BASE), *table(small)), [])

    def test_empty_cells_moving_ten_points(self):
        gaps = [(m, r, "" if i < 2 else v) for i, (m, r, v) in enumerate(BASE)]
        found = drift.compare(*table(BASE), *table(gaps))
        self.assertIn({"kind": "missing", "column": "revenue", "old": 0.0, "new": 0.1667}, found)
        one_gap = [(m, r, "" if i < 1 else v) for i, (m, r, v) in enumerate(BASE)]
        self.assertFalse(any(f["kind"] == "missing" for f in drift.compare(*table(BASE),
                                                                           *table(one_gap))))

    def test_the_note_reads_in_both_languages(self):
        findings = [{"kind": "rows", "old": 1200, "new": 400},
                    {"kind": "median", "column": "cost", "old": 50.0, "new": 80.0, "spread": 20.0}]
        english = drift.describe(findings)
        arabic = drift.describe(findings, "ar")
        self.assertIn("rows from 1,200 to 400; cost median from 50 to 80", english)
        self.assertIn("check the source before approving", english)
        self.assertIn("عدد الصفوف من 1,200 إلى 400", arabic)
        self.assertIn("راجع المصدر قبل اعتماد النتائج", arabic)


class ConnectorDriftTests(unittest.TestCase):
    # The connector helpers, borrowed without inheriting that file's tests.
    _base = test_connectors.ConnectorEngineTestCase
    make_store, setUp, fetch, make = _base.make_store, _base.setUp, _base.fetch, _base.make

    def test_the_first_snapshot_has_no_drift(self):
        result = self.connectors.refresh_now(self.make()["id"], "alice")
        self.assertEqual(result["drift"], [])
        self.assertIsNone(result["note"])

    def test_a_shrunken_snapshot_is_flagged_and_still_analysed(self):
        connector = self.make(language="ar")
        self.connectors.refresh_now(connector["id"], "alice")
        self.content[URL] = source(months=4)
        result = self.connectors.refresh_now(connector["id"], "alice")
        self.assertEqual(result["status"], "updated")
        self.assertIsNotNone(result["run"])
        self.assertIn({"kind": "rows", "old": 24, "new": 8}, result["drift"])
        self.assertIn("تغيّرت اللقطة الجديدة", result["note"])
        self.assertEqual(self.connectors.list("alice")[0]["last_error"], result["note"])

    def test_a_steady_refresh_raises_nothing(self):
        connector = self.make()
        self.connectors.refresh_now(connector["id"], "alice")
        self.content[URL] = source(months=13)
        result = self.connectors.refresh_now(connector["id"], "alice")
        self.assertEqual((result["drift"], result["note"]), ([], None))


if __name__ == "__main__":
    unittest.main()
