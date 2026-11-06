"""Synthetic isolated query checks, not production/300 MB or full-RSS evidence."""
import csv
from fractions import Fraction
import gc
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from server.experimental_ingest import LargeIntakeError, index_csv
from server import experimental_query as query


class ExperimentalQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "index.sqlite"

    def index(self, columns, rows, *, path=None, batch_size=37):
        path = path or self.db
        source = path.with_suffix(".csv")
        with source.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)
        index_csv(source, path, batch_size=batch_size)
        return path

    def modify(self, sql, params=()):
        db = sqlite3.connect(self.db)
        try:
            db.execute(sql, params)
            db.commit()
        finally:
            db.close()

    def check_both_reject(self, **kwargs):
        for operation in (query.page, query.summarize):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(LargeIntakeError) as caught:
                    operation(self.db, columns=["a"], **kwargs)
                self.assertNotIn("PRIVATE_CELL", str(caught.exception))

    def test_wide_projection_order_and_keyset_paging(self):
        columns = [f"c{i}" for i in range(607)]
        rows = [[f"{n}:{c}" for c in range(607)] for n in range(111)]
        self.index(columns, rows)
        selected = ["c606", "c2", "c500", "c0"]
        after = 0
        actual = []
        while True:
            result = query.page(self.db, columns=selected, after=after, size=17)
            self.assertEqual(result["columns"], selected)
            if not result["rows"]:
                self.assertIsNone(result["next"])
                break
            actual.extend(result["rows"])
            after = result["next"]
        self.assertEqual(actual, [{"ordinal": n + 1,
                                  "values": [row[i] for i in (606, 2, 500, 0)]}
                                 for n, row in enumerate(rows)])
        self.assertEqual(query.page(self.db, columns=selected, after=110)["next"], 111)

    def test_original_ordinals_with_gaps_and_maximum_cursor(self):
        self.index(["a"], [["1"], ["2"], ["3"]])
        self.modify("DELETE FROM wide_records WHERE ordinal=2")
        self.modify("UPDATE wide_records SET ordinal=? WHERE ordinal=3", (query.MAX_CURSOR,))
        self.assertEqual([r["ordinal"] for r in query.page(self.db, columns=["a"])["rows"]],
                         [1, query.MAX_CURSOR])
        self.assertEqual(query.page(self.db, columns=["a"], after=query.MAX_CURSOR)["rows"], [])
        self.assertEqual(query.summarize(self.db, columns=["a"])["rows_scanned"], 2)

    @staticmethod
    def fraction_string(value):
        # Independent oracle: rational arithmetic and long division, not the
        # implementation's integer coefficient/scale machinery or Decimal.
        sign = "-" if value < 0 else ""
        numerator, denominator = abs(value.numerator), value.denominator
        whole, remainder = divmod(numerator, denominator)
        digits = []
        while remainder:
            digit, remainder = divmod(remainder * 10, denominator)
            digits.append(str(digit))
        return sign + str(whole) + (("." + "".join(digits)) if digits else "")

    def test_exact_summaries_across_ingest_batches_and_long_cancellation(self):
        huge = "9" * 70 + ".012345678901234567890123456789"
        choices = [huge, "-" + huge, "0.000000000000000000000000000001",
                   "-0.000000000000000000000000000002",
                   "1000000000000000000000000000000.1",
                   "-1000000000000000000000000000000", " +.50 ", "1.", "-000.000"]
        values = [choices[n % len(choices)] for n in range(1307)]
        random.Random(93).shuffle(values)
        self.index(["amount", "other", "invalid"],
                   [[v, str(n % 7 - 3), "not a number"] for n, v in enumerate(values)],
                   batch_size=19)
        result = query.summarize(self.db, columns=["other", "amount", "invalid"])
        self.assertEqual(list(result["columns"]), ["other", "amount", "invalid"])
        self.assertEqual(result["rows_scanned"], len(values))
        for name, source in (("amount", values), ("other", [str(n % 7 - 3) for n in range(1307)])):
            rational = [Fraction(v.strip()) for v in source]
            self.assertEqual(result["columns"][name], {
                "numeric": 1307, "blank": 0, "invalid": 0,
                "sum": self.fraction_string(sum(rational)),
                "min": self.fraction_string(min(rational)),
                "max": self.fraction_string(max(rational)),
            })
        self.assertEqual(result["columns"]["invalid"], {
            "numeric": 0, "blank": 0, "invalid": 1307, "sum": None, "min": None, "max": None})

    def test_numeric_boundaries_and_extreme_scale_alignment_are_exact(self):
        huge = "9" * query.MAX_NUMERIC_DIGITS
        tiny = "0." + "0" * (query.MAX_NUMERIC_SCALE - 1) + "1"
        self.index(["a"], [[huge], [tiny], ["-" + huge]])
        result = query.summarize(self.db, columns=["a"])["columns"]["a"]
        self.assertEqual(result["sum"], tiny)
        self.assertEqual(result["max"], huge)
        self.assertEqual(result["min"], "-" + huge)

    def test_blank_invalid_and_numeric_are_distinct(self):
        invalid = ["$12", "1,200", "1e3", "1E-4", "NaN", "nan", "inf", "Infinity",
                   "-Infinity", "+", ".", "--2", "1 2", "١٢", "１２", "0x12", "1_000",
                   "false", "text" * 1000]
        blank = ["", " \t\r\n", "\u2003"]
        numeric = ["0", "-0.000", "+000.000", " .5 ", "1.", "-.25", "-2"]
        self.index(["a"], [[v] for v in invalid + blank + numeric])
        result = query.summarize(self.db, columns=["a"])["columns"]["a"]
        self.assertEqual(result, {"numeric": len(numeric), "blank": len(blank),
                                 "invalid": len(invalid), "sum": "-0.75", "min": "-2", "max": "1"})

    def test_canonical_zero_and_no_numeric_values(self):
        self.index(["zero", "blank", "bad"], [["0.2", "", "x"], ["-.2", " ", "NaN"]])
        result = query.summarize(self.db, columns=["zero", "blank", "bad"])["columns"]
        self.assertEqual(result["zero"]["sum"], "0")
        self.assertEqual(result["blank"], {"numeric": 0, "blank": 2, "invalid": 0,
                                           "sum": None, "min": None, "max": None})
        self.assertEqual(result["bad"]["sum"], None)
        self.assertEqual(result["bad"]["invalid"], 2)

    def test_header_only_index(self):
        self.index(["a", "b"], [])
        self.assertEqual(query.page(self.db, columns=["b"]), {"columns": ["b"], "rows": [], "next": None})
        self.assertEqual(query.summarize(self.db, columns=["a"]), {
            "rows_scanned": 0, "columns": {"a": {"numeric": 0, "blank": 0, "invalid": 0,
                                                  "sum": None, "min": None, "max": None}}})

    def test_missing_database_is_not_created(self):
        for operation in (query.page, query.summarize):
            with self.assertRaises(LargeIntakeError):
                operation(self.db, columns=["a"])
            self.assertFalse(self.db.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_empty_database_is_invalid_and_unchanged(self):
        self.db.touch()
        self.check_both_reject()
        self.assertEqual(self.db.stat().st_size, 0)

    def test_uri_special_characters_are_literal_path_characters(self):
        path = self.root / "query?mode=rw#data.sqlite"
        self.index(["a"], [["2"]], path=path)
        self.assertEqual(query.summarize(path, columns=["a"])["columns"]["a"]["sum"], "2")
        self.assertEqual(query.page(path, columns=["a"])["rows"][0]["values"], ["2"])

    def test_source_bytes_and_mtime_are_unchanged(self):
        self.index(["a"], [["3.14"], ["2"]])
        before = hashlib.sha256(self.db.read_bytes()).hexdigest(), self.db.stat().st_mtime_ns
        query.page(self.db, columns=["a"])
        query.summarize(self.db, columns=["a"])
        after = hashlib.sha256(self.db.read_bytes()).hexdigest(), self.db.stat().st_mtime_ns
        self.assertEqual(before, after)

    def test_invalid_selections(self):
        self.index(["a"], [["1"]])
        cases = [None, "a", {"a"}, (x for x in ["a"]), [], ["a", "a"], [True], [1],
                 [""], ["PRIVATE_CELL"], ["a"] * 33, ["\ud800"]]
        for selected in cases:
            for operation in (query.page, query.summarize):
                with self.subTest(selected=repr(selected), operation=operation.__name__):
                    with self.assertRaises(LargeIntakeError) as caught:
                        operation(self.db, columns=selected)
                    self.assertNotIn("PRIVATE_CELL", str(caught.exception))

    def test_32_columns_and_selection_byte_budget(self):
        names = [str(i) for i in range(32)]
        self.index(names, [["1"] * 32])
        self.assertEqual(len(query.page(self.db, columns=tuple(names))["columns"]), 32)
        self.assertEqual(len(query.summarize(self.db, columns=names)["columns"]), 32)
        self.index(["é"], [["1"]])
        for operation in (query.page, query.summarize):
            self.assertTrue(operation(self.db, columns=["é"], max_selection_bytes=2))
            with self.assertRaises(LargeIntakeError):
                operation(self.db, columns=["é"], max_selection_bytes=1)

    def test_invalid_integer_arguments_and_hard_budget_caps(self):
        common = {"max_metadata_bytes": query.HARD_METADATA_BYTES,
                  "max_record_bytes": query.HARD_RECORD_BYTES,
                  "max_selection_bytes": query.HARD_SELECTION_BYTES}
        for operation, specific in (
                (query.page, {"size": query.MAX_PAGE_SIZE, "max_output_bytes": query.HARD_OUTPUT_BYTES,
                              "max_scan_bytes": query.HARD_PAGE_SCAN_BYTES}),
                (query.summarize, {"max_scan_rows": query.HARD_SCAN_ROWS,
                                   "max_scan_bytes": query.HARD_SCAN_BYTES})):
            for name, maximum in {**common, **specific}.items():
                for value in (True, False, 1.0, "1", None, 0, -1, maximum + 1):
                    with self.subTest(operation=operation.__name__, name=name, value=value):
                        with patch.object(query.sqlite3, "connect") as connect:
                            with self.assertRaises(LargeIntakeError):
                                operation(self.db, columns=["a"], **{name: value})
                            connect.assert_not_called()
        for value in (True, False, 1.0, "0", None, -1, query.MAX_CURSOR + 1):
            with self.subTest(cursor=value), self.assertRaises(LargeIntakeError):
                query.page(self.db, columns=["a"], after=value)

    def test_metadata_missing_or_corrupt(self):
        self.index(["a"], [["1"]])
        for raw in ("PRIVATE_CELL", "null", "{}", "[]", '["a","a"]', '[""]', '[1]',
                    '["a",{}]', "[" * 1500 + "]" * 1500):
            with self.subTest(raw=raw[:40]):
                self.modify("UPDATE wide_meta SET value=? WHERE name='columns'", (raw,))
                self.check_both_reject()
        self.modify("DELETE FROM wide_meta")
        self.check_both_reject()

    def test_record_corruption_including_unselected_cells_is_rejected(self):
        self.index(["a", "b"], [["1", "2"]])
        for raw in ("PRIVATE_CELL", "null", "{}", "[]", '["1"]', '["1","2","3"]',
                    '["1",true]', '["1",1]', '["1",null]', '["1",{}]', '["1",NaN]',
                    "[" * 1500 + "]" * 1500):
            with self.subTest(raw=raw[:40]):
                self.modify("UPDATE wide_records SET payload=?", (raw,))
                self.check_both_reject()

    def test_blob_storage_and_bad_utf8_are_rejected(self):
        self.index(["a"], [["1"]])
        self.modify("UPDATE wide_records SET payload=?", (b'["1"]',))
        self.check_both_reject()
        self.modify("UPDATE wide_records SET payload=CAST(x'80' AS TEXT)")
        self.check_both_reject()
        self.modify("UPDATE wide_records SET payload=?", ('["1"]',))
        self.modify("UPDATE wide_meta SET value=?", (b'["a"]',))
        self.check_both_reject()

    def test_bad_schema_and_nonpositive_ordinals_are_rejected(self):
        self.index(["a"], [["1"]])
        for ordinal in (0, -1):
            self.modify("UPDATE wide_records SET ordinal=?", (ordinal,))
            self.check_both_reject()
        self.modify("DROP TABLE wide_records")
        self.modify("CREATE VIEW wide_records AS SELECT 1 AS ordinal, '[\"1\"]' AS payload")
        self.check_both_reject()
        self.modify("DROP VIEW wide_records")
        self.modify("CREATE TABLE wide_records (ordinal TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.check_both_reject()

    def test_metadata_limit_is_checked_before_loading_json(self):
        self.index(["a"], [["1"]])
        self.modify("UPDATE wide_meta SET value=?", ('["a","' + "PRIVATE_CELL" * 1000 + '"]',))
        with patch.object(query.json, "loads", side_effect=AssertionError("Must not decode oversized metadata")):
            self.check_both_reject(max_metadata_bytes=20)

    def test_oversized_record_does_not_cross_sqlite_boundary(self):
        self.index(["a"], [["PRIVATE_CELL" * 10000]])
        original_connect = sqlite3.connect
        observed, fetched_payloads = [], []

        class InspectCursor:
            def __init__(self, inner):
                self.inner = inner

            def fetchone(self):
                row = self.inner.fetchone()
                if row:
                    observed.append(row)
                return row

            def close(self):
                self.inner.close()

        class InspectConnection(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql.startswith("SELECT payload FROM"):
                    fetched_payloads.append(parameters)
                cursor = super().execute(sql, parameters)
                return InspectCursor(cursor) if sql.startswith("SELECT ordinal,typeof(payload)") else cursor

        def connect(*args, **kwargs):
            return original_connect(*args, factory=InspectConnection, **kwargs)

        with patch.object(query.sqlite3, "connect", side_effect=connect):
            self.check_both_reject(max_record_bytes=20)
        self.assertEqual(len(observed), 2)
        self.assertTrue(all(row[2] > 20 and len(row) == 3 for row in observed))
        self.assertEqual(fetched_payloads, [])

    def test_scan_budgets_prevent_payload_fetch_and_sentinel_decode(self):
        self.index(["a"], [["1"], ["PRIVATE_CELL" * 1000]])
        original_connect = sqlite3.connect
        fetched_payloads = []

        class InspectConnection(sqlite3.Connection):
            def execute(self, sql, parameters=()):
                if sql.startswith("SELECT payload FROM"):
                    fetched_payloads.append(parameters[0])
                return super().execute(sql, parameters)

        def connect(*args, **kwargs):
            return original_connect(*args, factory=InspectConnection, **kwargs)

        with patch.object(query.sqlite3, "connect", side_effect=connect):
            for operation in (query.page, query.summarize):
                fetched_payloads.clear()
                with self.assertRaises(LargeIntakeError):
                    operation(self.db, columns=["a"], max_scan_bytes=1)
                self.assertEqual(fetched_payloads, [])
                with self.assertRaises(LargeIntakeError):
                    operation(self.db, columns=["a"], max_scan_bytes=6)
                self.assertEqual(fetched_payloads, [1])
            fetched_payloads.clear()
            with patch.object(query, "_decode_row", wraps=query._decode_row) as decode:
                with self.assertRaises(LargeIntakeError):
                    query.summarize(self.db, columns=["a"], max_scan_rows=1)
                self.assertEqual(decode.call_count, 1)
            self.assertEqual(fetched_payloads, [1])

    def test_record_and_metadata_limits_count_utf8_not_characters(self):
        self.index(["a"], [["😀"]])
        raw = '["😀"]'
        self.assertEqual(query.page(self.db, columns=["a"], max_record_bytes=len(raw.encode()))["rows"][0]["values"], ["😀"])
        self.check_both_reject(max_record_bytes=len(raw))
        self.index(["é"], [["1"]])
        metadata_bytes = len(json.dumps(["é"], ensure_ascii=False).encode())
        self.assertTrue(query.page(self.db, columns=["é"], max_metadata_bytes=metadata_bytes))
        with self.assertRaises(LargeIntakeError):
            query.page(self.db, columns=["é"], max_metadata_bytes=metadata_bytes - 1)

    def test_page_output_budget_matches_exact_compact_ascii_json(self):
        self.index(["a", "b"], [["é\n\"\\😀", str(i)] for i in range(12)])
        result = query.page(self.db, columns=["b", "a"])
        size = len(json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
        self.assertEqual(query.page(self.db, columns=["b", "a"], max_output_bytes=size), result)
        with self.assertRaises(LargeIntakeError):
            query.page(self.db, columns=["b", "a"], max_output_bytes=size - 1)
        with self.assertRaises(LargeIntakeError):
            query.page(self.db, columns=["a"], after=100, max_output_bytes=1)

    def test_scan_limits_fail_instead_of_returning_partial_results(self):
        self.index(["a"], [["1"], ["2"]])
        bytes_per_row = len('["1"]'.encode())
        for operation in (query.page, query.summarize):
            with self.subTest(operation=operation.__name__):
                self.assertTrue(operation(self.db, columns=["a"], max_scan_bytes=2 * bytes_per_row))
                with self.assertRaises(LargeIntakeError):
                    operation(self.db, columns=["a"], max_scan_bytes=2 * bytes_per_row - 1)
        self.assertEqual(query.summarize(self.db, columns=["a"], max_scan_rows=2)["rows_scanned"], 2)
        with self.assertRaises(LargeIntakeError):
            query.summarize(self.db, columns=["a"], max_scan_rows=1)

    def test_oversized_numeric_tokens_fail_closed(self):
        for token in ("1" * (query.MAX_NUMERIC_TOKEN_CHARS + 1),
                      "1" * (query.MAX_NUMERIC_DIGITS + 1),
                      "0." + "1" * (query.MAX_NUMERIC_SCALE + 1)):
            with self.subTest(length=len(token)):
                self.index(["a"], [["2"], [token]])
                with self.assertRaises(LargeIntakeError) as caught:
                    query.summarize(self.db, columns=["a"])
                self.assertNotIn(token, str(caught.exception))
        # Paging is not numeric interpretation; do not reject plain text there.
        self.assertEqual(query.page(self.db, columns=["a"])["rows"][1]["values"], [token])

    def test_readonly_connections_close_on_success_and_all_failure_paths(self):
        self.index(["a"], [["1"], ["2"]])
        connections, calls = [], []
        original_connect = sqlite3.connect

        def connect(*args, **kwargs):
            db = original_connect(*args, **kwargs)
            connections.append(db)
            calls.append((args, kwargs))
            return db

        with patch.object(query.sqlite3, "connect", side_effect=connect):
            query.page(self.db, columns=["a"])
            query.summarize(self.db, columns=["a"])
            with self.assertRaises(LargeIntakeError):
                query.page(self.db, columns=["a"], max_record_bytes=1)
            with self.assertRaises(LargeIntakeError):
                query.summarize(self.db, columns=["a"], max_scan_rows=1)
            with self.assertRaises(LargeIntakeError):
                query.page(self.db, columns=["missing"])
            with self.assertRaises(RuntimeError):
                with patch.object(query, "_decode_row", side_effect=RuntimeError("synthetic failure")):
                    query.summarize(self.db, columns=["a"])
        self.assertEqual(len(connections), 6)
        for db, (args, kwargs) in zip(connections, calls):
            self.assertTrue(args[0].endswith("?mode=ro"))
            self.assertTrue(kwargs["uri"])
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")

    def test_snapshot_stays_consistent_during_concurrent_wal_update(self):
        for operation in (query.page, query.summarize):
            with self.subTest(operation=operation.__name__):
                self.index(["a", "b"], [["1", "10"], ["2", "20"], ["3", "30"]])
                writer = sqlite3.connect(self.db)
                try:
                    writer.execute("PRAGMA journal_mode=WAL")
                    original_decode = query._decode_row
                    changed = False

                    def decode(payload, width):
                        nonlocal changed
                        if not changed:
                            writer.execute("UPDATE wide_records SET payload=? WHERE ordinal=3", ('["900","9000"]',))
                            writer.execute("INSERT INTO wide_records VALUES (4,?)", ('["400","4000"]',))
                            writer.execute("UPDATE wide_meta SET value=? WHERE name='columns'", ('["b","a"]',))
                            writer.commit()
                            changed = True
                        return original_decode(payload, width)

                    with patch.object(query, "_decode_row", side_effect=decode):
                        result = operation(self.db, columns=["b", "a"])
                    self.assertTrue(changed)
                    if operation is query.page:
                        self.assertEqual(result["rows"], [{"ordinal": i, "values": [str(i * 10), str(i)]}
                                                          for i in range(1, 4)])
                    else:
                        self.assertEqual(result["rows_scanned"], 3)
                        self.assertEqual(result["columns"]["a"]["sum"], "6")
                        self.assertEqual(result["columns"]["b"]["sum"], "60")
                    new = query.summarize(self.db, columns=["a"])
                    self.assertEqual(new["rows_scanned"], 4)
                    self.assertEqual(new["columns"]["a"]["sum"], "13030")
                finally:
                    writer.close()

    def test_fixed_width_python_heap_does_not_scale_with_row_count(self):
        # Diagnostic only: SQLite native memory, process RSS and a 300 MB
        # end-to-end run are deliberately not claimed by this test.
        names = [f"c{i}" for i in range(64)]
        small, large = self.root / "small.sqlite", self.root / "large.sqlite"
        for path, count in ((small, 500), (large, 10000)):
            self.index(names, ([str(i % 7)] * 64 for i in range(count)), path=path)
        peaks = []
        for path, count in ((small, 500), (large, 10000)):
            gc.collect()
            tracemalloc.start()
            try:
                result = query.summarize(path, columns=["c63", "c0", "c17"])
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(result["rows_scanned"], count)
            peaks.append(peak)
        self.assertLess(peaks[1], peaks[0] + 512 * 1024)
        self.assertLess(max(peaks), 4 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
