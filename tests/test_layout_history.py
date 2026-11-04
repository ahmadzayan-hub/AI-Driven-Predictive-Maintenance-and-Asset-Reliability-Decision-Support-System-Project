"""Designed-page layouts kept on the server (ADR 2026-11-04-layout-history)."""
import json
import unittest

from tests import test_export_reviews as reviews


class LayoutHistoryApiTests(reviews.ReviewApiTests):
    # Reuse the review tests' app and run fixture; none of their tests run here.
    test_reviews_are_recorded_per_output_and_any_change_needs_a_new_one = None
    test_only_an_owner_with_approval_rights_records_a_decision = None
    test_a_rendered_video_is_traceable_to_its_snapshot_and_reviewable = None
    test_a_host_without_the_tools_says_so_and_renders_nothing = None
    test_a_failed_render_is_recorded_and_labelled_failed = None

    def designed(self, run):
        response = self.client.post(f"/api/runs/{run['id']}/layout", headers=self.auth(), json={"objective": "", "use_model": False})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        return {"fingerprint": result["fingerprint"], "versions": [{"result": result, "at": "2026-11-04T09:00:00Z"}],
                "current": 0, "pinned": []}

    def put(self, run, history, expected, action="designed", who="alice", role="analyst"):
        return self.client.put(f"/api/runs/{run['id']}/layout/history", headers=self.auth(who, role),
                               json={"expected_version": expected, "action": action, "history": history})

    def test_versions_are_kept_audited_restored_and_conflicts_are_refused(self):
        run = self.make_run()
        base = f"/api/runs/{run['id']}/layout/history"
        self.assertEqual(self.client.get(base, headers=self.auth()).json(), {"head": None, "audit": []})
        history = self.designed(run)
        first = self.put(run, history, 0)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["head"]["version"], 1)
        pin = history["versions"][0]["result"]["plan"]["sections"][0]["id"]
        second = self.put(run, {**history, "pinned": [pin]}, 1, "pinned").json()
        self.assertEqual((second["head"]["version"], second["head"]["history"]["pinned"]), (2, [pin]))
        # A second tab still on version 1: refused, told, and given the latest.
        stale = self.put(run, history, 1, "designed")
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["head"]["version"], 2)
        self.assertIn("another tab", stale.json()["detail"])
        # Restore version 1: a new version, so nothing is lost from the trail.
        back = self.client.post(f"{base}/1/restore", headers=self.auth(), json={"expected_version": 2}).json()
        self.assertEqual((back["head"]["version"], back["head"]["action"], back["head"]["history"]["pinned"]),
                         (3, "restored_version", []))
        self.assertEqual([a["action"] for a in back["audit"]], ["restored_version", "pinned", "designed"])
        self.assertEqual(self.client.post(f"{base}/9/restore", headers=self.auth(), json={"expected_version": 3}).status_code, 404)

    def test_each_reader_has_their_own_history_and_access_is_checked(self):
        run = self.make_run()
        history = self.designed(run)
        self.assertEqual(self.put(run, history, 0).status_code, 200)
        base = f"/api/runs/{run['id']}/layout/history"
        self.assertEqual(self.client.get(base, headers=self.auth("mallory")).status_code, 404)
        self.assertEqual(self.put(run, history, 0, who="mallory").status_code, 404)
        self.assertEqual(self.put(run, history, 1, role="viewer").status_code, 403)
        self.assertEqual(self.client.get(base).status_code, 401)

    def test_a_layout_the_planner_would_refuse_is_never_stored(self):
        run = self.make_run()
        history = self.designed(run)
        bad = json.loads(json.dumps(history))
        bad["versions"][0]["result"]["plan"]["sections"][0]["binding"] = {"group_by": ["No_Such_Column"], "measures": [{"agg": "count"}]}
        for broken in (bad, {**history, "fingerprint": "other"}, {**history, "current": 3}, {**history, "extra": 1}):
            response = self.put(run, broken, 0)
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.client.get(f"/api/runs/{run['id']}/layout/history", headers=self.auth()).json()["head"], None)
        # Arabic refusal.
        refused = self.client.put(f"/api/runs/{run['id']}/layout/history?language=ar", headers=self.auth(),
                                  json={"expected_version": 0, "action": "designed", "history": {**history, "current": 3}})
        self.assertIn("غير صالح", refused.json()["detail"])


if __name__ == "__main__":
    unittest.main()
