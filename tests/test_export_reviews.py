"""One review step for every executive output, and the executive video
(ADRs 2026-11-04-shared-review and 2026-11-04-executive-video)."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import wave

from fastapi.testclient import TestClient

from server.app import create_app
from server import executive_video, export_reviews
from tests import test_executive as fixtures
from tests.support import closing

FILTERS = json.dumps([{"column": "Site", "op": "in", "values": ["North"]}])


class ReviewStatusTests(unittest.TestCase):
    def test_a_decision_counts_only_for_the_exact_snapshot_and_bytes(self):
        review = {"format": "html", "language": "en", "snapshot_id": "s1", "artifact_sha256": "a" * 64,
                  "decision": "approved"}
        found = {"dashboard": "s1", "html": "a" * 64, "docx": "d" * 64, "slides": "c" * 64, "video": None}
        state = export_reviews.status([review], found, "s1", "en")
        self.assertEqual(state["html"]["state"], "approved")
        self.assertEqual(state["docx"]["state"], "draft")
        self.assertEqual(state["video"]["state"], "not_rendered")
        self.assertEqual(export_reviews.status([review], {**found, "html": "b" * 64}, "s1", "en")["html"]["state"],
                         "changed_since_review")
        self.assertEqual(export_reviews.status([review], found, "s2", "en")["html"]["state"], "changed_since_review")
        self.assertEqual(export_reviews.status([review], found, "s1", "ar")["html"]["state"], "draft")
        self.assertEqual(export_reviews.status([], {**found, "video": "failed"}, "s1", "en")["video"]["state"], "failed")

    def test_asking_for_changes_needs_a_comment(self):
        with self.assertRaises(export_reviews.ReviewError):
            export_reviews.record(None, run_id="r", snapshot_id="s", fmt="html", language="en", artifact_sha256="a",
                                  decision="changes_requested", comment=" ", reviewer="alice")


class ReviewApiTests(unittest.TestCase):
    auth = fixtures.ExecutiveApiTests.auth
    make_run = fixtures.ExecutiveApiTests.make_run

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Review tests", "database_file": str(root / "a.db"),
            "memory_file": str(root / "m.json"), "vault_dir": str(root / "vault"),
            "stages": ["server.maintenance.targets.MaintenanceRisk"],
            "profiles": {"default": [], "maintenance": ["maintenance_risk"]}}), encoding="utf-8")
        self.exports = root / "exports"
        self.app = create_app(config, env={"AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": fixtures.SECRET,
                                           "SUPABASE_URL": "https://test.supabase.invalid",
                                           "AGENTIC_OS_EXPORT_DIR": str(self.exports)})
        self.client = TestClient(closing(self, self.app), raise_server_exceptions=False)

    def status(self, run, language="en", who="alice", role="analyst"):
        return self.client.get(f"/api/runs/{run['id']}/executive/reviews", headers=self.auth(who, role),
                               params={"language": language, "filters": FILTERS})

    def review(self, run, state, fmt, decision="approved", comment="", role="analyst", language="en", **override):
        body = {"format": fmt, "language": language, "filters": FILTERS, "expected_snapshot_id": state["snapshot_id"],
                "artifact_sha256": state["formats"][fmt]["artifact_sha256"], "decision": decision, "comment": comment,
                **override}
        return self.client.post(f"/api/runs/{run['id']}/executive/reviews", headers=self.auth("alice", role), json=body)

    def test_reviews_are_recorded_per_output_and_any_change_needs_a_new_one(self):
        run = self.make_run()
        state = self.status(run).json()
        self.assertEqual({k: v["state"] for k, v in state["formats"].items()},
                         {"dashboard": "draft", "html": "draft", "docx": "draft", "slides": "draft", "video": "not_rendered"})
        exported = self.client.get(f"/api/runs/{run['id']}/executive/export", headers=self.auth(), params={
            "format": "slides", "expected_updated_at": run["updated_at"], "expected_snapshot_id": state["snapshot_id"],
            "filters": FILTERS})
        # The digest under review is the digest of the very bytes a reader downloads.
        self.assertEqual(export_reviews.digest(exported.content), state["formats"]["slides"]["artifact_sha256"])
        done = self.review(run, state, "slides", comment="Checked against the dashboard.")
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["formats"]["slides"]["state"], "approved")
        self.assertEqual(done.json()["review"]["reviewer"], "alice")
        asked = self.review(run, state, "html", decision="changes_requested", comment="Add the period.")
        self.assertEqual(asked.json()["formats"]["html"]["state"], "changes_requested")
        self.assertEqual(self.review(run, state, "docx", decision="changes_requested").status_code, 422)
        # Another file, another snapshot: refused, nothing recorded.
        self.assertEqual(self.review(run, state, "docx", artifact_sha256="0" * 64).status_code, 409)
        self.assertEqual(self.review(run, state, "docx", expected_snapshot_id="0" * 64).status_code, 409)
        self.assertEqual(self.review(run, state, "video", artifact_sha256="0" * 64).status_code, 409)
        # The Arabic outputs are other files and keep their own state.
        self.assertEqual(self.status(run, "ar").json()["formats"]["slides"]["state"], "draft")
        # The data changes after approval: the decision stays as history and the output needs a new review.
        self.app.state.store.update("runs", run["id"], {"updated_at": "2026-11-04T10:00:00+00:00"})
        later = self.status(run).json()
        self.assertNotEqual(later["snapshot_id"], state["snapshot_id"])
        self.assertEqual(later["formats"]["slides"]["state"], "changed_since_review")
        self.assertEqual([r["format"] for r in later["history"]], ["html", "slides"])

    def test_only_an_owner_with_approval_rights_records_a_decision(self):
        run = self.make_run()
        state = self.status(run).json()
        self.assertEqual(self.review(run, state, "dashboard", role="viewer").status_code, 403)
        self.assertEqual(self.status(run, who="mallory").status_code, 404)
        self.assertEqual(self.client.get(f"/api/runs/{run['id']}/executive/reviews").status_code, 401)
        self.assertEqual(self.review(run, state, "dashboard").status_code, 200)

    @unittest.skipIf(executive_video.missing_tools(), "needs ffmpeg, espeak-ng, libraqm and the verified font")
    def test_a_rendered_video_is_traceable_to_its_snapshot_and_reviewable(self):
        run = self.make_run()
        for language in ("en", "ar"):
            snapshot = self.status(run, language).json()["snapshot_id"]
            made = self.client.post(f"/api/runs/{run['id']}/executive/video", headers=self.auth(),
                                    params={"language": language, "filters": FILTERS, "expected_snapshot_id": snapshot})
            self.assertEqual(made.status_code, 200, made.text)
            video = made.json()["video"]
            manifest = video["manifest"]
            self.assertEqual((manifest["snapshot_id"], manifest["language"], manifest["status"]),
                             (snapshot, language, "DRAFT_REQUIRES_HUMAN_REVIEW"))
            # Every KPI on screen is the brief's own figure, or says it was not measured.
            brief = self.client.get(f"/api/runs/{run['id']}/executive", headers=self.auth(),
                                    params={"language": language, "filters": FILTERS}).json()
            cards = next(s for s in manifest["scenes"] if s["id"] == "kpis")["figures"]
            for card, measure in zip(cards, brief["kpis"]["measures"]):
                self.assertEqual(card["value"], measure["value"])
                self.assertTrue(card["source"].startswith(f"executive.kpi.{measure['key']}"))
            base = f"/api/runs/{run['id']}/executive/video/{video['id']}"
            mp4 = self.client.get(base + "/video.mp4", headers=self.auth(), params={"download": "true"})
            self.assertEqual(mp4.status_code, 200)
            self.assertEqual(mp4.headers["content-type"], "video/mp4")
            self.assertIn("attachment;", mp4.headers["content-disposition"])
            self.assertEqual(export_reviews.digest(mp4.content), manifest["files"]["video.mp4"]["sha256"])
            vtt = self.client.get(base + "/subtitles.vtt", headers=self.auth())
            self.assertTrue(vtt.text.startswith("WEBVTT"))
            self.assertIn("مسودة" if language == "ar" else "draft for review", vtt.text)
            self.assertEqual(self.client.get(base + "/video.mp4", headers=self.auth("mallory")).status_code, 404)
        current = self.status(run).json()
        self.assertEqual(current["formats"]["video"]["state"], "draft")
        self.assertEqual(self.review(run, current, "video").json()["formats"]["video"]["state"], "approved")
        # A changed file on disk is refused, never served as the reviewed one.
        video_id = current["video"]["id"]
        (self.exports / run["id"] / video_id / "video.mp4").write_bytes(b"tampered")
        self.assertEqual(self.client.get(f"/api/runs/{run['id']}/executive/video/{video_id}/video.mp4",
                                         headers=self.auth()).status_code, 410)

    def test_a_host_without_the_tools_says_so_and_renders_nothing(self):
        run = self.make_run()
        snapshot = self.status(run).json()["snapshot_id"]
        from unittest.mock import patch
        with patch.object(executive_video, "missing_tools", return_value=["espeak-ng"]):
            response = self.client.post(f"/api/runs/{run['id']}/executive/video", headers=self.auth(),
                                        params={"filters": FILTERS, "expected_snapshot_id": snapshot})
            self.assertEqual(response.status_code, 503)
            self.assertIn("espeak-ng", response.json()["detail"])
            self.assertFalse(self.status(run).json()["video_renderer"]["available"])

    def test_a_failed_render_is_recorded_and_labelled_failed(self):
        run = self.make_run()
        snapshot = self.status(run).json()["snapshot_id"]
        from unittest.mock import patch
        with patch.object(executive_video, "missing_tools", return_value=[]), \
                patch.object(executive_video, "render", side_effect=executive_video.VideoFailed("encoder failed")):
            response = self.client.post(f"/api/runs/{run['id']}/executive/video", headers=self.auth(),
                                        params={"filters": FILTERS, "expected_snapshot_id": snapshot})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.status(run).json()["formats"]["video"]["state"], "failed")


@unittest.skipIf(executive_video.missing_tools(), "needs ffmpeg, espeak-ng, libraqm and the verified font")
class VideoTimelineTests(unittest.TestCase):
    def test_voice_subtitles_and_pictures_share_one_timeline(self):
        from tests.test_executive_exports import ExecutiveDocumentTests
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        manifest = executive_video.render(ExecutiveDocumentTests().brief("ar"), folder)
        scenes = manifest["scenes"]
        self.assertEqual(scenes[0]["start"], 0)
        for a, b in zip(scenes, scenes[1:]):
            self.assertAlmostEqual(a["end"], b["start"], places=3)
        self.assertAlmostEqual(scenes[-1]["end"], manifest["duration"], places=2)
        cues = [line for line in (folder / "subtitles.vtt").read_text(encoding="utf-8").splitlines() if "-->" in line]
        self.assertLessEqual(cues[-1].split(" --> ")[1], executive_video._stamp(manifest["duration"]))
        self.assertTrue(all(s["narration"] for s in scenes))
        # The whole file decodes without a single error, video, audio and subtitles.
        import subprocess
        decoded = subprocess.run(["ffmpeg", "-v", "error", "-i", str(folder / "video.mp4"), "-map", "0:v", "-map", "0:a",
                                  "-f", "null", "-"], capture_output=True, timeout=300)
        self.assertEqual((decoded.returncode, decoded.stderr), (0, b""))


class SpokenFormTests(unittest.TestCase):
    def test_dates_are_said_as_words_and_figures_keep_their_digits(self):
        self.assertEqual(executive_video.spoken_date("2025-01-01", "en"), "1 January 2025")
        self.assertEqual(executive_video.spoken_date("2026-04", "ar"), "أبريل 2026")
        self.assertEqual(executive_video.spoken_date("Q1", "en"), "Q1")
        from tests.test_executive_exports import ExecutiveDocumentTests
        for language in ("en", "ar"):
            brief = ExecutiveDocumentTests().brief(language)
            brief["kpis"]["measures"][0].update(value=99.996, scale="percent")
            brief["kpis"]["measures"][1].update(value=None, undefined_reason="No downtime recorded.")
            scenes = executive_video.storyboard(brief)
            kpis = next(s for s in scenes if s["id"] == "kpis")
            self.assertEqual(kpis["figures"][0]["shown"], "99.996%")
            self.assertIn("99.996", kpis["narration"])
            self.assertNotIn("100 ", kpis["narration"])
            self.assertIsNone(kpis["figures"][1]["value"])
            self.assertIn("not measured" if language == "en" else "غير مقاس", kpis["narration"])
