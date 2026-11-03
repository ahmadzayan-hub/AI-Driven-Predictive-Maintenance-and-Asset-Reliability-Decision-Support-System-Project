"""The synthetic dataset generator, and the database round trip it exists to test.

The generator invents every value from a seed. The API tests upload its file and
run the whole pipeline on SQLite and, when a database is available, PostgreSQL.
"""

import csv
import io
import unittest

from scripts.generate_synthetic_dataset import COLUMNS, MAX_ROWS, generate, main, to_csv
from tests.test_datasets import (FASTAPI_AVAILABLE, PG_TEST_URL, DatasetApiPostgresTestCase,
                                 DatasetApiTestCase, _postgres_available)


def parse(text):
    return list(csv.reader(io.StringIO(text)))


class GeneratorTests(unittest.TestCase):
    def test_same_seed_same_file_different_seed_different_file(self):
        self.assertEqual(to_csv(generate(800, seed=7)), to_csv(generate(800, seed=7)))
        self.assertNotEqual(to_csv(generate(800, seed=7)), to_csv(generate(800, seed=8)))

    def test_shape_and_values_are_plausible(self):
        rows = parse(to_csv(generate(3_000)))
        self.assertEqual(rows[0], COLUMNS)
        body = rows[1:]
        self.assertEqual(len(body), 3_000)
        self.assertEqual(len({r[0] for r in body}), 3_000)  # record ids are unique
        self.assertTrue(all(r[0].startswith("SYN-") for r in body))
        for record in body:
            cost, operating, planned, downtime, failures = (float(record[i]) for i in (4, 5, 6, 7, 8))
            self.assertGreaterEqual(cost, 0)
            self.assertLessEqual(operating, planned)
            self.assertGreaterEqual(downtime, 0)
            self.assertEqual(failures, int(failures))
            self.assertEqual(downtime > 0, failures > 0)  # downtime only comes from a failure

    def test_failures_cost_money(self):
        body = parse(to_csv(generate(4_000)))[1:]
        failed = [float(r[4]) for r in body if int(r[8]) > 0]
        calm = [float(r[4]) for r in body if int(r[8]) == 0]
        self.assertTrue(failed and calm)
        self.assertGreater(sum(failed) / len(failed), 3 * sum(calm) / len(calm))

    def test_defects_are_planted_and_the_row_limit_holds(self):
        body = parse(to_csv(generate(2_000, defects=True)))[1:]
        self.assertEqual(len(body), 2_000)
        self.assertTrue(any(r[4] == "" for r in body))
        self.assertTrue(any(r[5] == "n/a" for r in body))
        self.assertTrue(any(r[8] == "-1" for r in body))
        self.assertEqual(len(generate(MAX_ROWS, defects=True)), MAX_ROWS)

    def test_row_count_is_bounded(self):
        for bad in (0, MAX_ROWS + 1):
            with self.assertRaises(ValueError):
                generate(bad)
        self.assertEqual(main(["--rows", "0"]), 2)


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class SyntheticDatabaseRoundTrip(DatasetApiTestCase):
    """Upload, store, read back and analyse a generated file, on SQLite."""

    ROWS = 1_500

    def test_upload_store_and_full_run(self):
        text = to_csv(generate(self.ROWS))
        response = self.upload(text.encode(), "SYNTHETIC_fleet.csv", **{})
        self.assertEqual(response.status_code, 201, response.text)
        dataset = response.json()["dataset"]
        self.assertEqual((dataset["row_count"], dataset["column_count"]), (self.ROWS, len(COLUMNS)))
        self.assertEqual(response.json()["columns"], COLUMNS)

        again = self.upload(text.encode(), "SYNTHETIC_fleet.csv")  # the same bytes are the same dataset
        self.assertEqual(again.json()["dataset"]["id"], dataset["id"])
        self.assertFalse(again.json()["created"])

        run = self.client.post("/api/runs", json={"goal": "Synthetic fleet review",
                                                  "dataset_id": dataset["id"]}).json()
        for _ in range(40):
            if run["state"] not in ("queued", "running"):
                break
            run = self.client.post(f"/api/runs/{run['id']}/advance").json()
        self.assertEqual(run["state"], "awaiting_approval", run)

    def test_planted_defects_are_caught_by_validation(self):
        text = to_csv(generate(self.ROWS, defects=True))
        response = self.upload(text.encode(), "SYNTHETIC_messy.csv")
        self.assertEqual(response.status_code, 201, response.text)
        run = self.client.post("/api/runs", json={"goal": "Synthetic messy review",
                                                  "dataset_id": response.json()["dataset"]["id"]}).json()
        for _ in range(40):
            if run["state"] not in ("queued", "running"):
                break
            run = self.client.post(f"/api/runs/{run['id']}/advance").json()
        # The file is stored and analysed, but the validation stage refuses to call it clean.
        self.assertEqual(run["state"], "partially_completed", run)
        self.assertEqual(run["error"], "Validation checks failed.")


@unittest.skipUnless(FASTAPI_AVAILABLE and _postgres_available(), "PostgreSQL is not available")
class SyntheticDatabaseRoundTripPostgres(SyntheticDatabaseRoundTrip, DatasetApiPostgresTestCase):
    """The same round trip against the hosted-mode PostgresStore."""


# The inherited dataset tests would run again under these classes; keep only this file's own.
for _case in (SyntheticDatabaseRoundTrip, SyntheticDatabaseRoundTripPostgres):
    for _name in [n for n in dir(_case) if n.startswith("test_") and n not in
                  ("test_upload_store_and_full_run", "test_planted_defects_are_caught_by_validation")]:
        setattr(_case, _name, None)

if __name__ == "__main__":
    unittest.main()
