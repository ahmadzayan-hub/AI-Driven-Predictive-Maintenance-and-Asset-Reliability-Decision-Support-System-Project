"""Deleting an analysis and keeping its audit (ADR 2026-11-06-delete-a-run-keep-its-audit).

The run's data copy and every output go; its approvals, reviews and policy history
stay, with the deletion itself recorded beside them. Checked on SQLite and, when a
test database is reachable, PostgreSQL. Synthetic rows only."""
import unittest

from tests import test_dataset_deletion as base
from tests.test_dataset_deletion import FASTAPI_AVAILABLE, PRODUCTS, SALES
from tests.test_runs import _postgres_available


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class RunDeletionMixin:
    # The dataset deletion tests' own setup and helpers, not their tests.
    setUp = base.DatasetDeletionMixin.setUp
    auth = base.DatasetDeletionMixin.auth
    upload = base.DatasetDeletionMixin.upload
    delete = base.DatasetDeletionMixin.delete
    ids = base.DatasetDeletionMixin.ids

    def analysis(self, subject="alice", joins=False):
        sales = self.upload(SALES, "sales.csv", subject)
        body = {"goal": "Monthly sales by product", "dataset_id": sales}
        products = None
        if joins:
            products = self.upload(PRODUCTS, "products.csv", subject)
            body["joins"] = [{"dataset_id": products, "keys": [{"left": "product", "right": "code"}]}]
        run = self.client.post("/api/runs", headers=self.auth(subject), json=body).json()
        for _ in range(80):
            run = self.client.post(f"/api/runs/{run['id']}/advance", headers=self.auth(subject)).json()
            if run["state"] not in ("queued", "running"):
                break
        self.assertEqual(run["state"], "awaiting_approval", run.get("error"))
        return run["id"], sales, products

    def remove(self, run_id, subject="alice", datasets=False, language="en"):
        return self.client.delete(f"/api/runs/{run_id}?datasets={str(datasets).lower()}&language={language}",
                                  headers=self.auth(subject))

    def test_the_data_and_outputs_go_and_the_audit_stays(self):
        run_id, sales, _ = self.analysis()
        response = self.remove(run_id)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deleted"], run_id)
        self.assertEqual(self.client.get(f"/api/runs/{run_id}", headers=self.auth("alice")).status_code, 404)
        listed = [r["id"] for r in self.client.get("/api/runs", headers=self.auth("alice")).json()["runs"]]
        self.assertNotIn(run_id, listed)
        row = self.store.get_run(run_id)
        self.assertEqual((row["state"], row["dataset_text"], row["dataset_id"]), ("deleted", "", None))
        self.assertEqual(self.store.get_tasks(run_id), [])
        audit = self.store.approvals_for_run(run_id)
        deletion = [a for a in audit if a["state"] == "recorded"]
        self.assertEqual((len(deletion), deletion[0]["decided_by"]), (1, "alice"))
        self.assertGreater(len(audit), 1)          # the publication request is still there
        # Without being asked, the dataset stays; and it is free to delete now.
        self.assertEqual(response.json()["datasets_kept"], [sales])
        self.assertEqual(self.delete(sales, "alice").status_code, 200)

    def test_datasets_only_it_read_can_go_with_it(self):
        run_id, sales, products = self.analysis(joins=True)
        other, _, _ = self.analysis()      # the same sales bytes: one stored dataset, read twice
        body = self.remove(run_id, datasets=True).json()
        self.assertEqual((body["datasets_deleted"], body["datasets_kept"]), ([products], [sales]))
        self.assertIn(sales, self.ids("alice"))
        self.assertNotIn(products, self.ids("alice"))
        self.assertEqual(self.remove(other).status_code, 200)

    def test_another_owner_a_viewer_and_a_second_delete_get_nothing(self):
        run_id, _, _ = self.analysis()
        self.assertEqual(self.remove(run_id, "mallory").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/runs/{run_id}", headers=self.auth("alice", "viewer")).status_code, 403)
        self.assertEqual(self.remove(run_id).status_code, 200)
        self.assertEqual(self.remove(run_id).status_code, 404)

    def test_a_running_analysis_is_refused_in_both_languages(self):
        sales = self.upload(SALES, "sales.csv", "alice")
        run = self.client.post("/api/runs", headers=self.auth("alice"),
                               json={"goal": "Monthly sales by product", "dataset_id": sales}).json()
        self.assertIn(run["state"], ("queued", "running"))
        for language, needle in (("en", "still running"), ("ar", "قيد التشغيل")):
            response = self.remove(run["id"], language=language)
            self.assertEqual(response.status_code, 409)
            self.assertIn(needle, response.json()["error"]["message"])


class SqliteRunDeletionTestCase(RunDeletionMixin, unittest.TestCase):
    build_client = base.SqliteDatasetDeletionTestCase.build_client


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class PostgresRunDeletionTestCase(RunDeletionMixin, unittest.TestCase):
    build_client = base.PostgresDatasetDeletionTestCase.build_client

if __name__ == "__main__":
    unittest.main()
