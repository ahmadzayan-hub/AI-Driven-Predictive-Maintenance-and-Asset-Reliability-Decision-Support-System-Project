"""The seventh slice: the P3 findings (assessment A16, A17, A19, B17, B18,
B19, B20, G12, G13, G14, G15, U17): signed shares with n, a robust anomaly
rule, a noise baseline and two held seasons, one CSP source and preflight
PATCH, public liveness with authenticated detail, relative published
paths and an escaped frontmatter, one handler per service error, recorded
orchestration failures, quantity words and causal wording in grounding,
known reviewers, tool arguments held to their schema, and the voice label."""

import json
import random
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from server import analytics, modelling, orchestration, tools
from server.app import create_app
from server.connectors import ConnectorError
from server.model_gateway import ModelGateway
from server.orchestration import grounded
from server.runs import RunEngine
from server.storage import open_store
from tests.support import closing, closing_store
from tests.test_analytics import run_pipeline
from tests.test_modelling import checked, context

ROOT = Path(__file__).resolve().parent.parent


def _app(case, env=None):
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    root = Path(tmp.name)
    config = root / "config.json"
    config.write_text(json.dumps({"agent_name": "Slice Seven", "database_file": str(root / "agentic.db"),
                                  "memory_file": str(root / "memory.json"),
                                  "vault_dir": str(root / "vault")}), encoding="utf-8")
    app = create_app(config, env=env)
    return app, TestClient(closing(case, app), raise_server_exceptions=False)


class SignedSharesTest(unittest.TestCase):
    """A16: a share above the whole is said as such, and n travels with r."""

    def test_a_group_that_moved_further_than_the_total_is_named_as_such(self):
        rows = ["month,team,sales"]
        for month, (alpha, beta) in enumerate([(100, 100), (120, 90), (140, 80), (160, 70), (180, 60), (200, 50)], 1):
            rows += [f"2025-{month:02d},alpha,{alpha}", f"2025-{month:02d},beta,{beta}"]
        ctx, results = run_pipeline("\n".join(rows))
        diag = ctx["diagnostic"]
        self.assertGreater(diag["contributions"][0]["share_of_change"], 1)
        texts = " ".join(c["text"] for c in results["diagnostic"]["claims"])
        self.assertIn("more than the whole", texts)
        self.assertIn("moved further than the total", diag["headline"])

    def test_an_association_states_its_sign_and_its_n(self):
        rows = ["month,x,sales"] + [f"2025-{i + 1:02d},{10 - i},{100 + 10 * i}" for i in range(8)]
        _, results = run_pipeline("\n".join(rows))
        claim = next(c for c in results["diagnostic"]["claims"] if c["id"].endswith("cl_assoc_0"))
        self.assertIn("correlation -1.00 over 8 rows", claim["text"])


class RobustAnomalyTest(unittest.TestCase):
    """A17: an obvious outlier stands out at four periods; a straight
    series and a noisy one do not."""

    def test_an_obvious_outlier_at_four_periods_is_found(self):
        data = "month,team,sales\n2025-01,A,100\n2025-02,A,110\n2025-03,A,900\n2025-04,A,130\n"
        ctx, _ = run_pipeline(data)
        self.assertEqual([a["period"] for a in ctx["anomaly"]["anomalies"]], ["2025-03"])

    def test_three_periods_say_the_minimum(self):
        data = "month,team,sales\n2025-01,A,100\n2025-02,A,110\n2025-03,A,900\n"
        _, results = run_pipeline(data)
        claim = next(c for c in results["anomaly"]["claims"] if c["id"].endswith("cl_anom_none"))
        self.assertIn("at least 4", claim["text"])

    def test_ordinary_variation_is_not_unusual(self):
        rng = random.Random(3)
        data = "month,team,sales\n" + "".join(f"2025-{i + 1:02d},A,{100 + 10 * i + rng.uniform(-3, 3):.1f}\n"
                                              for i in range(10))
        ctx, _ = run_pipeline(data)
        self.assertEqual(ctx["anomaly"]["anomalies"], [])
        rule = next(c for c in ctx["anomaly_result"]["calculations"] if c["id"].endswith("c_anom_rule"))
        self.assertEqual(rule["value"], analytics.ANOMALY_Z)


class StructureBaselinesTest(unittest.TestCase):
    """A19: clustering against shapeless data; two held-out seasons."""

    def test_the_clustering_card_carries_the_noise_floor(self):
        rng = random.Random(4)
        rows = [{"a": rng.gauss(cx, 0.3), "b": rng.gauss(cy, 0.3), "sales": cx + cy}
                for cx, cy in ((0, 0), (6, 0), (3, 6)) for _ in range(80)]
        card = checked(modelling.ClusteringModel(), context(rows, ["a", "b", "sales"],
                                                            ["a", "b", "sales"], "sales"))["output"]["model_card"]
        self.assertTrue(card["beats_baseline"])
        self.assertLess(card["details"]["separation_in_noise"] + modelling.NOISE_MARGIN, card["metric"]["model"])

    def test_the_seasonal_model_holds_out_two_seasons_when_four_exist(self):
        pattern = [100, 90, 80, 70, 60, 70, 80, 90, 100, 110, 120, 110]
        labels = [f"{2022 + i // 12}-{i % 12 + 1:02d}" for i in range(48)]
        trend = {label: pattern[i % 12] + i for i, label in enumerate(labels)}
        card = checked(modelling.SeasonalForecast(), context([], [], [], "sales", trend=trend))["output"]["model_card"]
        self.assertEqual(card["split"], {"kind": "last_two_seasons", "seasons_held": 2})
        self.assertEqual(card["test_records"], 24)
        short = {label: trend[label] for label in labels[:36]}
        card = checked(modelling.SeasonalForecast(), context([], [], [], "sales", trend=short))["output"]["model_card"]
        self.assertEqual(card["split"]["seasons_held"], 1)


class ApiHardeningTest(unittest.TestCase):
    """B17, B18, B19, B20 and G12 at the API."""

    def test_a_preflight_for_patch_is_allowed(self):
        _, client = _app(self)
        response = client.options("/api/operations/assets/x", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "PATCH"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("PATCH", response.headers.get("access-control-allow-methods", ""))

    def test_health_is_liveness_for_everyone_and_detail_for_a_reader(self):
        _, local = _app(self)
        body = local.get("/api/health").json()
        self.assertIn("model_map", body)  # local mode signs everyone in
        self.assertIn("orchestration_problems", body)
        _, hosted = _app(self, env={"SUPABASE_JWT_SECRET": "s" * 32,
                                    "SUPABASE_URL": "https://test.supabase.invalid"})
        public = hosted.get("/api/health").json()
        self.assertEqual(public["status"], "ok")
        self.assertNotIn("model_map", public)
        self.assertNotIn("model_provider", public)
        self.assertNotIn("stage_problems", public)

    def test_a_connector_error_is_answered_by_the_one_handler_in_the_envelope(self):
        # Production without an allowlist refuses a live source with a
        # ConnectorError; the app-level handler turns it into the envelope.
        from tests.support import scoped_token
        secret = "test-signing-secret-not-a-real-credential"
        _, client = _app(self, env={"AGENTIC_OS_ENV": "production", "AGENTIC_OS_JWT_SECRET": secret,
                                    "SUPABASE_URL": "https://test.supabase.invalid"})
        headers = {"Authorization": "Bearer " + scoped_token(secret, "owner-a", role="owner")}
        response = client.post("/api/connectors?language=ar", json={
            "name": "feed", "url": "https://data.example.org/feed.csv", "goal": "Analyze the feed"},
            headers=headers)
        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertIn("AGENTIC_OS_CONNECTOR_HOSTS", body["detail"])
        self.assertEqual(body["error"]["code"], "http_422")
        self.assertTrue(response.headers.get("X-Request-ID"))

    def test_runtime_dependencies_carry_no_unused_extras(self):
        text = (ROOT / "requirements.in").read_text(encoding="utf-8")
        self.assertNotIn("uvicorn[standard]", text)
        lock = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for extra in ("uvloop", "httptools", "websockets", "watchfiles"):
            self.assertNotIn(f"\n{extra}==", lock)
        self.assertIn("\nhttpx==", lock)


class PublishedPathTest(unittest.TestCase):
    """B19: the path a reader sees is relative to the vault, and the
    frontmatter cannot be forged through the dataset name."""

    def engine(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = closing_store(self, open_store(None, Path(tmp.name) / "agentic.db"))
        return RunEngine(store, Path(tmp.name) / "vault", ModelGateway(env={})), store

    def test_the_path_is_relative_and_the_name_is_escaped(self):
        engine, store = self.engine()
        name = 'quote" and\nstatus: forged.csv'
        run = engine.create_run("Analyze the sample sales dataset", dataset_name=name,
                                dataset_text="team,sales\nA,1\nB,2\nC,3\nD,4\n")
        for _ in range(40):
            run = engine.advance(run["id"])
            if run["state"] == "awaiting_approval":
                break
        approval = next(a for a in run["approvals"] if a["state"] == "pending")
        run = engine.decide_approval(run["id"], approval["id"], "approve", approver="owner")
        path = run["report"]["published_path"]
        self.assertFalse(Path(path).is_absolute())
        self.assertTrue(path.startswith("Reports/"))
        note = (engine.vault_dir / path).read_text(encoding="utf-8")
        head = note.split("---", 2)[1]
        self.assertIn('dataset: "quote\\" and\\nstatus: forged.csv"', head)
        self.assertNotIn("\nstatus: forged", head)
        publish = next(t for t in run["tasks"] if t["role"] == "publish")
        self.assertNotIn(str(engine.vault_dir), publish["summary"])


class OrchestrationProblemsTest(unittest.TestCase):
    """G12: a failing model is recorded on the task and the engine."""

    def test_a_raising_role_leaves_a_reason_not_silence(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store = closing_store(self, open_store(None, Path(tmp.name) / "agentic.db"))

        class Broken:
            hermes = agents = "anthropic"
            consultants = ["anthropic"]
            active = True

            def plan(self, *a, **k):
                raise RuntimeError("provider down")

            def agent_note(self, *a, **k):
                raise RuntimeError("provider down")

            def consult(self, *a, **k):
                raise RuntimeError("provider down")

        engine = RunEngine(store, Path(tmp.name) / "vault", ModelGateway(env={}))
        engine.roles = Broken()
        engine._roles_for = lambda run, ctx, facts: engine.roles
        run = engine.create_run("Analyze the sample sales dataset")
        for _ in range(40):
            run = engine.advance(run["id"])
            if run["state"] != "running":
                break
        self.assertEqual(run["state"], "awaiting_approval")
        tasks = {t["role"]: json.loads(t["result_json"] or "{}") for t in store.get_tasks(run["id"])}
        self.assertIn("provider down", tasks["planner"]["orchestration_problem"])
        self.assertIn("consult: RuntimeError: provider down", tasks["reporter"]["orchestration_problem"])
        self.assertTrue(engine.orchestration_problems)


class GroundingWordsTest(unittest.TestCase):
    """G13: quantity words and causal wording in a note."""

    FACTS = ["Overdue work is 21.6% of completed work.", "Failures fell from 10 to 5."]

    def test_quantity_words_count_as_figures(self):
        self.assertIsNone(grounded("Overdue work doubled this year.", self.FACTS))
        self.assertIsNone(grounded("One in five work orders is overdue.", self.FACTS))
        self.assertIsNone(grounded("Failures fell by a dozen.", self.FACTS))
        self.assertIsNone(grounded("Failures halved.", self.FACTS))
        self.assertEqual(grounded("Failures fell from ten to five.", self.FACTS),
                         "Failures fell from ten to five.")

    def test_causal_wording_is_refused_and_prose_passes(self):
        self.assertIsNone(grounded("Overdue work caused the failures.", self.FACTS))
        self.assertEqual(grounded("Confirm the denominator of overdue work first.", self.FACTS),
                         "Confirm the denominator of overdue work first.")

    def test_every_built_in_sentence_passes_its_own_checks(self):
        for language in ("en", "ar"):
            text = orchestration._text(language)
            sentences = [text["always"], text["brief"].format(first="x")] + [s for _, s in text["rules"]]
            for sentence in sentences:
                with self.subTest(language=language, sentence=sentence[:40]):
                    self.assertEqual(grounded(sentence, ["x"]), sentence)


class KnownReviewersTest(unittest.TestCase):
    """G14: an acceptance names a known reviewer."""

    def test_the_plans_reviewers_or_the_repositorys_committers_decide(self):
        import review_gate
        plan = {"name": "p", "gates": [{"id": "g", "type": "exists", "files": ["x"]}],
                "accepted": [{"gate": "g", "by": "Nobody Known", "reason": "r"}]}
        self.assertTrue(any("known reviewer" in p for p in review_gate.validate_plan({**plan, "reviewers": ["Owner"]})))
        self.assertEqual(review_gate.validate_plan({**plan, "reviewers": ["Nobody Known"]}), [])
        self.assertEqual(review_gate.known_reviewers({"reviewers": ["A"]}), {"A"})
        committers = review_gate.known_reviewers({})
        self.assertTrue(committers is None or isinstance(committers, set))


class ToolSchemaTest(unittest.TestCase):
    """G15: the catalogue's schema is the executor's contract."""

    def test_the_schemas_name_every_executor_argument(self):
        for tool in tools.TOOLS:
            with self.subTest(tool=tool["name"]):
                self.assertEqual(set(tool["inputSchema"]["properties"]), set(tools.ACTIONS[tool["name"]]))

    def test_an_argument_outside_the_schema_is_refused(self):
        from server.assistant import Assistant
        from tests.test_agent_runtime import FakeSession, engine_in, make_agent
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        engine = engine_in(tmp.name, case=self)
        box = tools.ToolBox(Assistant(ModelGateway(env={}), engine), FakeSession(make_agent()))
        # An unknown argument is dropped, as before; a value outside the
        # schema's enum is refused rather than passed to the executor.
        dropped = box.call("help", {"verbose": True})
        self.assertTrue(dropped["ok"])
        self.assertEqual(box.steps[-1]["arguments"], {})
        refused = box.call("remember", {"information": "a note", "category": "nonsense"})
        self.assertFalse(refused["ok"])
        self.assertEqual(box.steps[-1]["arguments"], {"information": "a note", "category": "nonsense"})
        missing = box.call("start_run", {"dataset": "sample"})
        self.assertFalse(missing["ok"])


class VoiceLabelTest(unittest.TestCase):
    """U17: the toggle keeps one accessible name; the state is aria-pressed."""

    def test_the_toggle_has_a_fixed_name_in_both_languages(self):
        for name in ("en.ts", "ar.ts"):
            with self.subTest(file=name):
                self.assertIn("'voice.toggle'", (ROOT / "frontend" / "src" / "i18n" / name).read_text(encoding="utf-8"))
        component = (ROOT / "frontend" / "src" / "features" / "chat" / "VoiceDictation.tsx").read_text(encoding="utf-8")
        self.assertIn("aria-label={t('voice.toggle')}", component)
        self.assertIn("aria-pressed={active}", component)


if __name__ == "__main__":
    unittest.main()
