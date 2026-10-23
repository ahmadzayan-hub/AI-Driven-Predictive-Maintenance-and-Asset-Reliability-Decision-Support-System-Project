"""Configured display targets are explicit, scoped, audited and not approvals."""

import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch
from xml.etree import ElementTree as ET

from server.backup import create_backup, restore_backup
from server.erasure import erase, survey
from server.executive import ExecutiveDashboardAgent
from server.executive_export import render_html, render_docx, PERFORMANCE_COLORS
from server.maintenance import performance as p
from server.storage import SQLiteStore, PostgresStore
from tests.test_runs import PG_TEST_URL, _postgres_available
from tests import test_executive as fixtures
from tests.test_executive_exports import HtmlDocument, docx_document, docx_tables, property_table, NS, W


def rule(direction="higher", scale="percent", **limits):
    return {"direction": direction, "scale": scale,
            "source_ref": "Fictional QA display target, not a standard", **limits}


def ftf_rule(*args, **limits):
    """A first-time fix target reviewed for its current definition (2, since
    the 21 October alignment with the Power BI Method page)."""
    return {**rule(*args, **limits), "definition": 2}


def measure(value, records=2, missing=0):
    return {"key": "first_time_fix", "value": value,
            "records": records, "records_unmeasured": missing}


class AssessmentTests(unittest.TestCase):
    def test_a_target_set_for_an_earlier_definition_gives_no_verdict_until_reviewed(self):
        # Before 21 October "availability" meant operating over planned hours.
        # A stored 95% target for it now judges a different quantity, so it
        # must not colour the new figure; it asks for review instead.
        availability = {"key": "availability", "value": 99.0, "records": 2, "records_unmeasured": 0}
        legacy = {"availability": rule(good_at=95, okay_at=90)}
        out = p.assessment(availability, p.policy(legacy)["rules"])
        self.assertEqual((out["status"], out["reason_code"]), ("unassessed", "target_outdated"))
        self.assertIn("earlier definition", out["reason"])
        self.assertEqual(out["thresholds"], {"good_at": 95, "okay_at": 90})
        arabic = p.assessment(availability, p.policy(legacy)["rules"], "ar")
        self.assertRegex(arabic["reason"], "[\u0600-\u06FF]")
        # Reviewed against the current definition, it judges again.
        current = {"availability": {**rule(good_at=95, okay_at=90), "definition": 2}}
        self.assertEqual(p.assessment(availability, p.policy(current)["rules"])["status"], "good")
        # A measure whose meaning never changed is unaffected by a missing stamp.
        unchanged = {**measure(80), "key": "preventive_share"}
        self.assertEqual(p.assessment(unchanged, {"preventive_share": rule(good_at=75, okay_at=60)})["status"], "good")
        # First-time fix was redefined the same day: an unstamped target waits too.
        held = p.assessment(measure(80), {"first_time_fix": rule(good_at=75, okay_at=60)})
        self.assertEqual(held["reason_code"], "target_outdated")

    def test_a_definition_stamp_is_validated_and_a_legacy_policy_keeps_its_revision(self):
        for bad in (0, 3, "2", True, 2.5):
            with self.assertRaises(p.PolicyError, msg=repr(bad)):
                p.policy({"availability": {**rule(good_at=95, okay_at=90), "definition": bad}})
        legacy = {"availability": rule(good_at=95, okay_at=90)}
        # A stored policy without stamps must load with the revision it was saved under.
        self.assertNotIn("definition", p.policy(legacy)["rules"]["availability"])
        self.assertEqual(p.policy(legacy)["revision"], p.digest(p.validate_rules(legacy)))

    def test_json_depth_is_bounded_before_decoding_but_quoted_brackets_are_data(self):
        with patch.object(p.json, "loads") as decoder:
            with self.assertRaises(p.PolicyError):
                p.parse_json(b"[" * 1200 + b"0" + b"]" * 1200)
            decoder.assert_not_called()
        body = {"expected_revision": p.policy()["revision"], "rules": {
            "first_time_fix": ftf_rule(good_at=80, okay_at=60)}}
        body["rules"]["first_time_fix"]["source_ref"] = 'Fictional plan "[[[' + "[" * 80 + '"'
        self.assertEqual(p.parse_json(json.dumps(body).encode()), body)

    def assess(self, value, configured, **kwargs):
        return p.assessment(measure(value, **kwargs), {"first_time_fix": configured})

    def test_higher_lower_and_inclusive_range_boundaries_use_unrounded_values(self):
        higher = p.validate_rules({"first_time_fix": ftf_rule(good_at=80, okay_at=60)})["first_time_fix"]
        self.assertEqual([self.assess(v, higher)["status"] for v in (80, 79.9999999, 60, 59.9999999)],
                         ["good", "okay", "okay", "bad"])
        lower = p.validate_rules({"first_time_fix": ftf_rule("lower", good_at=10, okay_at=20)})["first_time_fix"]
        self.assertEqual([self.assess(v, lower)["status"] for v in (10, 10.0000001, 20, 20.0000001)],
                         ["good", "okay", "okay", "bad"])
        ranged = p.validate_rules({"first_time_fix": ftf_rule("range", good_min=40, good_max=60, okay_min=20, okay_max=80)})["first_time_fix"]
        self.assertEqual([self.assess(v, ranged)["status"] for v in (19.9, 20, 39.9, 40, 60, 60.1, 80, 80.1)],
                         ["bad", "okay", "okay", "good", "good", "okay", "okay", "bad"])

    def test_no_target_missing_and_partial_coverage_are_distinct(self):
        self.assertEqual(p.assessment(measure(99))["status"], "unassessed")
        configured = ftf_rule(good_at=80, okay_at=60)
        for value in (None, float("nan"), float("inf"), True):
            self.assertEqual(self.assess(value, configured)["status"], "unavailable")
        self.assertEqual(self.assess(0, configured, records=0)["status"], "unavailable")
        partial = self.assess(80, configured, missing=1)
        self.assertEqual(partial["status"], "good")
        self.assertIn("measured records only", partial["reason"])
        arabic = p.assessment(measure(80), {"first_time_fix": configured}, "ar")
        self.assertIn("الجيد", arabic["reason"])
        self.assertEqual(arabic["thresholds"], {"good_at": 80, "okay_at": 60})

    def test_policy_validation_has_no_defaults_or_universal_percent_clamp(self):
        self.assertEqual(p.policy()["rules"], {})
        self.assertEqual(p.policy()["revision"], p.policy({})["revision"])
        configured = {"first_time_fix": ftf_rule(good_at=150, okay_at=-1)}
        self.assertEqual(p.policy(configured)["rules"]["first_time_fix"]["good_at"], 150)
        snapshot = copy.deepcopy(configured)
        p.policy(configured)
        self.assertEqual(configured, snapshot)
        invalid = [
            {"unregistered": rule(good_at=80, okay_at=60)},
            {"first_time_fix": ftf_rule(good_at=True, okay_at=60)},
            {"first_time_fix": ftf_rule(good_at=float("nan"), okay_at=60)},
            {"first_time_fix": ftf_rule(good_at=float("inf"), okay_at=60)},
            {"first_time_fix": ftf_rule(good_at="80", okay_at=60)},
            {"first_time_fix": ftf_rule(scale="fraction", good_at=80, okay_at=60)},
            {"first_time_fix": ftf_rule(good_at=40, okay_at=60)},
            {"first_time_fix": ftf_rule("lower", good_at=60, okay_at=40)},
            {"first_time_fix": ftf_rule("range", good_min=10, good_max=60, okay_min=20, okay_max=80)},
            {"first_time_fix": {**ftf_rule(good_at=80, okay_at=60), "source_ref": ""}},
            {"first_time_fix": {**ftf_rule(good_at=80, okay_at=60), "source_ref": "x" * 241}},
            {"first_time_fix": {**ftf_rule(good_at=80, okay_at=60), "extra": 1}},
        ]
        for rules in invalid:
            with self.subTest(rules=str(rules)[:100]), self.assertRaises(p.PolicyError):
                p.policy(rules)

    def test_revision_and_rule_id_include_source_and_thresholds_even_when_status_does_not_change(self):
        a = {"first_time_fix": ftf_rule(good_at=80, okay_at=60)}
        b = copy.deepcopy(a)
        b["first_time_fix"]["source_ref"] = "Another explicit QA source"
        c = {"first_time_fix": ftf_rule(good_at=81, okay_at=60)}
        revisions = {p.policy(r)["revision"] for r in (a, b, c)}
        self.assertEqual(len(revisions), 3)
        assessments = [p.assessment(measure(90), r) for r in (a, b, c)]
        self.assertTrue(all(a["status"] == "good" for a in assessments))
        self.assertEqual(len({a["rule_id"] for a in assessments}), 3)

    def test_common_business_documents_show_status_reason_source_and_unavailable_policy(self):
        selected = p.policy({"first_time_fix": ftf_rule(good_at=75, okay_at=65),
            "loss_per_downtime_hour": rule("lower", scale="money", good_at=50, okay_at=100)})
        # Missing loss columns make the configured rule visible but uncomputable.
        table = fixtures.table()
        drop = table.columns.index("Production_Loss_USD")
        table.columns.pop(drop)
        table.numeric.remove("Production_Loss_USD")
        table.rows = [row[:drop] + row[drop + 1:] for row in table.rows]
        brief = ExecutiveDashboardAgent().brief(table, fixtures.run(), filters=[
            {"column": "Site", "op": "in", "values": ["North"]}], policy=selected)
        html = HtmlDocument(render_html(brief).decode())
        word = docx_document(render_docx(brief))
        for tables in (html.tables, docx_tables(word)):
            audit = property_table(tables, "Evidence ID", "executive.kpi.first_time_fix")
            self.assertEqual(audit["Performance status"], "Okay")
            self.assertEqual(audit["Target source"], selected["rules"]["first_time_fix"]["source_ref"])
            self.assertIn("okay target", audit["Assessment reason"])
            target = property_table(tables, "Metric key", "loss_per_downtime_hour")
            self.assertEqual(target["Good at"], "50")
            self.assertEqual(target["Okay at"], "100")
        self.assertTrue(any("performance--okay" in attrs.get("class", "") for _, attrs in html.tags))
        self.assertTrue(word.findall(f".//w:color[@w:val='{PERFORMANCE_COLORS['okay']}']", NS))


@unittest.skipUnless(fixtures.FASTAPI_AVAILABLE, "fastapi is not installed")
class KpiPolicyApiTests(unittest.TestCase):
    setUp = fixtures.ExecutiveApiTests.setUp
    auth = fixtures.ExecutiveApiTests.auth
    make_run = fixtures.ExecutiveApiTests.make_run

    def get_policy(self, run, **params):
        return self.client.get(f"/api/runs/{run['id']}/kpi-policy",
                               headers=self.auth(), params=params)

    def put_policy(self, run, current, rules, headers=None, **params):
        return self.client.put(f"/api/runs/{run['id']}/kpi-policy",
            headers=headers or self.auth(), params=params,
            json={"expected_revision": current["revision"], "rules": rules})

    def test_policy_edit_is_audited_persistent_and_does_not_mutate_governed_run(self):
        run = self.make_run()
        store = self.app.state.store
        before = (store.get_run(run["id"]), store.get_tasks(run["id"]),
                  store.approvals_for_run(run["id"]), store.latest_artifact(run["id"]), store.list_notes())
        initial = self.get_policy(run).json()
        self.assertEqual(initial["rules"], {})
        rules = {"first_time_fix": ftf_rule(good_at=75, okay_at=65)}
        saved = self.put_policy(run, initial, rules)
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.get_policy(run).json(), saved.json())
        self.assertEqual(before, (store.get_run(run["id"]), store.get_tasks(run["id"]),
                  store.approvals_for_run(run["id"]), store.latest_artifact(run["id"]), store.list_notes()))
        history = store._exec("SELECT * FROM kpi_policies WHERE run_id = ? ORDER BY version", (run["id"],))
        self.assertEqual(len(history), 1)
        self.assertEqual((history[0]["version"], history[0]["actor"]), (1, "alice"))
        # No-op saves do not invent new policy history.
        self.assertEqual(self.put_policy(run, saved.json(), rules).status_code, 200)
        self.assertEqual(len(store._exec("SELECT * FROM kpi_policies")), 1)
        removed = self.put_policy(run, saved.json(), {})
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(store.latest_kpi_policy(run["id"])["version"], 2)

    def test_an_unstamped_availability_target_is_held_until_saved_for_the_current_definition(self):
        run = self.make_run()
        def availability():
            body = self.client.get(f"/api/runs/{run['id']}/kpis", headers=self.auth()).json()
            return next(m for m in body["measures"] if m["key"] == "availability")
        self.assertEqual(availability()["definition"], 2)
        initial = self.get_policy(run).json()
        # What a policy saved before stamps existed looks like.
        legacy = self.put_policy(run, initial, {"availability": rule(good_at=95, okay_at=90)})
        self.assertEqual(legacy.status_code, 200, legacy.text)
        self.assertEqual(availability()["assessment"]["reason_code"], "target_outdated")
        self.assertEqual(self.put_policy(run, legacy.json(),
            {"availability": {**rule(good_at=95, okay_at=90), "definition": 3}}).status_code, 422)
        reviewed = self.put_policy(run, legacy.json(),
            {"availability": {**rule(good_at=95, okay_at=90), "definition": 2}})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["rules"]["availability"]["definition"], 2)
        self.assertIn(availability()["assessment"]["status"], {"good", "okay", "bad"})

    def test_ownership_permissions_readiness_validation_and_lost_update(self):
        queued = self.make_run(finish=False)
        path = f"/api/runs/{queued['id']}/kpi-policy"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.auth("mallory")).status_code, 404)
        self.assertEqual(self.client.get(path, headers=self.auth()).status_code, 409)
        self.assertEqual(self.client.put(path, headers=self.auth(role="viewer"), json={}).status_code, 403)
        run = self.make_run()
        initial = self.get_policy(run).json()
        rules = {"first_time_fix": ftf_rule(good_at=75, okay_at=65)}
        self.assertEqual(self.put_policy(run, initial, rules).status_code, 200)
        conflict = self.put_policy(run, initial, {}, language="ar")
        self.assertEqual(conflict.status_code, 409)
        self.assertIn("تغيرت", conflict.json()["detail"])
        self.assertEqual(self.put_policy(run, initial, rules, headers=self.auth("mallory")).status_code, 404)
        invalid = self.put_policy(run, self.get_policy(run).json(),
            {"first_time_fix": ftf_rule(scale="fraction", good_at=80, okay_at=60)}, language="ar")
        self.assertEqual(invalid.status_code, 422)
        self.assertIn("مقياس", invalid.json()["detail"])
        oversized = self.client.put(f"/api/runs/{run['id']}/kpi-policy", headers=self.auth(),
            content=b"x" * (p.MAX_POLICY_BYTES + 1))
        self.assertEqual(oversized.status_code, 422)
        nested = self.client.put(f"/api/runs/{run['id']}/kpi-policy", headers=self.auth(),
            content=b"[" * 1200 + b"0" + b"]" * 1200)
        self.assertEqual(nested.status_code, 422)

    def test_filtered_assessments_match_kpis_and_policy_change_invalidates_export_without_timestamp_change(self):
        run = self.make_run()
        initial = self.get_policy(run).json()
        rules = {"first_time_fix": ftf_rule(good_at=75, okay_at=65)}
        saved = self.put_policy(run, initial, rules).json()
        base = f"/api/runs/{run['id']}"
        brief = self.client.get(base + "/executive", headers=self.auth()).json()
        kpis = self.client.get(base + "/kpis", headers=self.auth()).json()
        first = next(m for m in brief["kpis"]["measures"] if m["key"] == "first_time_fix")
        whole = next(m for m in kpis["measures"] if m["key"] == "first_time_fix")
        self.assertEqual(first["assessment"], whole["assessment"])
        self.assertEqual(brief["kpi_policy"], saved)
        filtered = self.client.get(base + "/executive", headers=self.auth(),
            params={"filters": json.dumps([{"column": "Site", "op": "in", "values": ["South"]}])}).json()
        unavailable = next(m for m in filtered["kpis"]["measures"] if m["key"] == "first_time_fix")
        self.assertEqual(unavailable["assessment"]["status"], "unavailable")
        changed_rules = copy.deepcopy(rules)
        changed_rules["loss_per_downtime_hour"] = rule("lower", scale="money", good_at=100, okay_at=200)
        self.assertEqual(self.put_policy(run, saved, changed_rules).status_code, 200)
        self.assertEqual(self.app.state.store.get_run(run["id"])["updated_at"], brief["run"]["updated_at"])
        stale = self.client.get(base + "/executive/export", headers=self.auth(), params={
            "expected_updated_at": brief["run"]["updated_at"], "expected_snapshot_id": brief["snapshot_id"]})
        self.assertEqual(stale.status_code, 409)

    def test_history_is_in_backup_restore_and_erasure(self):
        run = self.make_run()
        initial = self.get_policy(run).json()
        self.put_policy(run, initial, {"first_time_fix": ftf_rule(good_at=75, okay_at=65)})
        store = self.app.state.store
        backup = create_backup(store)
        self.assertEqual(len(backup["tables"]["kpi_policies"]), 1)
        with tempfile.TemporaryDirectory() as directory:
            restored = SQLiteStore(Path(directory) / "restored.db")
            self.addCleanup(restored.close)
            try:
                restore_backup(restored, backup)
                self.assertEqual(p.load_policy(restored, run["id"]), self.get_policy(run).json())
                self.assertEqual(survey(restored, "alice")["rows"]["kpi_policies"], 1)
                erased = erase(restored, "alice")
                self.assertEqual(erased["deleted"]["kpi_policies"], 1)
                self.assertIsNone(restored.latest_kpi_policy(run["id"]))
            finally:
                restored.close()

    def test_two_independent_store_connections_cannot_both_win_same_revision(self):
        run = self.make_run()
        primary = self.app.state.store
        expected = p.policy()["revision"]
        gate = threading.Barrier(2)

        def write(which):
            connection = SQLiteStore(primary.path)
            try:
                chosen = p.policy({"first_time_fix": ftf_rule(good_at=80 + which, okay_at=60)})
                gate.wait(timeout=10)
                return connection.save_kpi_policy(uuid.uuid4().hex, run["id"], expected,
                    chosen["revision"], p.canonical(chosen["rules"]), "synthetic-writer",
                    "2026-10-20T00:00:00+00:00", expected)
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(write, index) for index in (0, 1)]
            outcomes = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(primary.latest_kpi_policy(run["id"])["version"], 1)
        self.assertEqual(len(primary._exec("SELECT * FROM kpi_policies")), 1)


@unittest.skipUnless(fixtures.FASTAPI_AVAILABLE, "fastapi is not installed")
@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class KpiPolicyPostgresTests(unittest.TestCase):
    """CI exercises the actual PG dialect; only a unique synthetic owner is erased."""

    make_run = fixtures.ExecutiveApiTests.make_run
    get_policy = KpiPolicyApiTests.get_policy
    put_policy = KpiPolicyApiTests.put_policy

    def setUp(self):
        from fastapi.testclient import TestClient
        from server.app import create_app
        from tests.support import closing

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.owner = "policy-pg-test-" + uuid.uuid4().hex
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Synthetic PostgreSQL policy tests",
            "database_url": PG_TEST_URL, "memory_file": str(root / "m.json"),
            "vault_dir": str(root / "vault"), "stages": ["server.maintenance.targets.MaintenanceRisk"],
            "profiles": {"default": [], "maintenance": ["maintenance_risk"]}}), encoding="utf-8")
        from tests.support import prepare_postgres_schema
        prepare_postgres_schema(PG_TEST_URL)
        self.app = create_app(config, env={"AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": fixtures.SECRET, "SUPABASE_URL": "https://test.supabase.invalid"})
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)
        # LIFO: erase our rows before the registered store close and temp cleanup.
        self.addCleanup(lambda: erase(self.app.state.store, self.owner))

    def auth(self, owner=None, role="analyst"):
        return fixtures.ExecutiveApiTests.auth(self, self.owner if owner is None else owner, role)

    def test_real_postgres_api_noop_lost_update_history_and_backup_roundtrip(self):
        run = self.make_run()
        initial = self.get_policy(run).json()
        rules = {"first_time_fix": ftf_rule(good_at=75, okay_at=65)}
        response = self.put_policy(run, initial, rules)
        self.assertEqual(response.status_code, 200, response.text)
        saved = response.json()
        self.assertEqual(self.put_policy(run, saved, rules).status_code, 200)
        store = self.app.state.store
        self.assertEqual(store.latest_kpi_policy(run["id"])["version"], 1)
        self.assertEqual(self.put_policy(run, initial, {}).status_code, 409)
        changed = copy.deepcopy(rules)
        changed["first_time_fix"]["source_ref"] = "Revised fictional PostgreSQL target source"
        response = self.put_policy(run, saved, changed)
        self.assertEqual(response.status_code, 200, response.text)
        history = store._exec("SELECT * FROM kpi_policies WHERE run_id = ? ORDER BY version", (run["id"],))
        self.assertEqual([item["version"] for item in history], [1, 2])
        self.assertTrue(all(item["actor"] == self.owner for item in history))
        backup = create_backup(store)
        restored = SQLiteStore(Path(self.tmp.name) / "roundtrip.db")
        try:
            restore_backup(restored, backup)
            self.assertEqual(p.load_policy(restored, run["id"]), response.json())
            self.assertEqual(len(restored._exec("SELECT * FROM kpi_policies WHERE run_id = ?", (run["id"],))), 2)
        finally:
            restored.close()

    def test_real_postgres_independent_connections_cas_race_and_lost_acknowledgement(self):
        run = self.make_run()
        expected = p.policy()["revision"]
        gate = threading.Barrier(2)

        def write(which):
            connection = PostgresStore(PG_TEST_URL)
            try:
                chosen = p.policy({"first_time_fix": ftf_rule(good_at=80 + which, okay_at=60)})
                gate.wait(timeout=15)
                return connection.save_kpi_policy(uuid.uuid4().hex, run["id"], expected,
                    chosen["revision"], p.canonical(chosen["rules"]), self.owner,
                    "2026-10-20T00:00:00+00:00", expected)
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = [future.result(timeout=30) for future in
                        [pool.submit(write, index) for index in (0, 1)]]
        self.assertEqual(sorted(outcomes), [False, True])
        store = self.app.state.store
        current = store.latest_kpi_policy(run["id"])
        self.assertEqual(current["version"], 1)
        self.assertFalse(store.save_kpi_policy(uuid.uuid4().hex, run["id"], expected,
            current["revision"], current["rules_json"], self.owner, "2026-10-20T00:00:01+00:00", expected))
        chosen = p.policy({"first_time_fix": ftf_rule(good_at=90, okay_at=70)})
        execute = store._exec_rowcount

        def acknowledgement_lost(sql, params):
            execute(sql, params)  # The actual PostgreSQL insert commits.
            return 0             # Simulate losing its row-count acknowledgement.

        with patch.object(store, "_exec_rowcount", side_effect=acknowledgement_lost):
            self.assertTrue(store.save_kpi_policy(uuid.uuid4().hex, run["id"], current["revision"],
                chosen["revision"], p.canonical(chosen["rules"]), self.owner,
                "2026-10-20T00:00:02+00:00", expected))
        self.assertEqual(store.latest_kpi_policy(run["id"])["version"], 2)
        self.assertEqual(p.load_policy(store, run["id"]), chosen)


if __name__ == "__main__":
    unittest.main()
