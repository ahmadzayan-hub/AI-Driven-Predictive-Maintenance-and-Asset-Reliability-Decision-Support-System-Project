"""The period a brief and a chat answer cover, read only from the date role."""

import unittest

from server import query
from server.period import period_of
from tests.test_executive import COLUMNS, ROWS


def table(roles):
    return query.Table(COLUMNS, set(COLUMNS[4:]), [list(r) for r in ROWS], roles)


class PeriodTests(unittest.TestCase):
    def test_reads_the_date_role_over_the_given_rows(self):
        t = table({"Record_Date": "date", "Site": "breakdown"})
        self.assertEqual(period_of(t, t.rows), {"column": "Record_Date", "from": "2026-01", "to": "2026-03", "dated": 3})
        north = [r for r in t.rows if r[2] == "North"]
        self.assertEqual(period_of(t, north)["to"], "2026-02")  # the filter narrows the period too

    def test_no_date_role_or_no_readable_date_means_no_period(self):
        self.assertIsNone(period_of(table({"Site": "breakdown"}), ROWS))  # never guessed from a column name
        t = table({"Record_Date": "date"})
        self.assertIsNone(period_of(t, [["x", "soon"] + list(ROWS[0][2:])]))
        self.assertIsNone(period_of(t, []))

    def test_unreadable_values_are_skipped_not_counted(self):
        t = table({"Record_Date": "date"})
        rows = [list(ROWS[0]), ["y", "n/a"] + list(ROWS[0][2:]), ["z", "2026-05-17"] + list(ROWS[0][2:])]
        self.assertEqual(period_of(t, rows), {"column": "Record_Date", "from": "2026-01", "to": "2026-05-17", "dated": 2})


if __name__ == "__main__":
    unittest.main()
