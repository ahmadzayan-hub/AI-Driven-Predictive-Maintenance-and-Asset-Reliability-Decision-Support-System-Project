"""Detected personal dataset labels never enter model or runtime handoffs."""

import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from server import analytics, model_privacy
from server.assistant import Assistant
from server.runs import RunEngine
from server.storage import open_store
from server.tools import ToolBox
from tests.support import closing_store
from tests.test_agent_runtime import FakeSession, ScriptedRuntime, make_agent, finish
from tests.test_assistant import FakeGateway
from tests.test_analytics import explicit_grouping, linear_dataset

EMAIL = "synthetic.person@example.invalid"
PRIVATE_CSV = linear_dataset().replace("Alpha", EMAIL)


class RecordingNarrator:
    def __init__(self):
        self.calls = []

    def narrate(self, goal, facts, language="en"):
        self.calls.append((goal, facts, language))
        return {"text": " ".join(facts), "source": "model"}


def pipeline(text, gateway, language="en", mapping=None):
    ctx = {"goal": "Analyze sales", "dataset_text": text,
           "dataset_name": "synthetic.csv", "report_language": language,
           "run_id": "synthetic-run", "mapping": mapping}
    for role, stage in analytics.PIPELINE:
        result = (stage(ctx, gateway=gateway)
                  if role in analytics.NARRATED_STAGES else stage(ctx))
        ctx[role], ctx[role + "_result"] = result["output"], result
        if result["status"] == "failed" and role != "validator":
            raise AssertionError((role, result["summary"]))
    return ctx


class NarrationPrivacyTests(unittest.TestCase):
    def test_personal_data_uses_an_explained_deterministic_summary_in_both_languages(self):
        for language in ("en", "ar"):
            with self.subTest(language=language):
                gateway = RecordingNarrator()
                ctx = pipeline(PRIVATE_CSV, gateway, language, mapping=explicit_grouping())
                self.assertTrue(ctx["privacy"]["personal_data"])
                self.assertEqual(gateway.calls, [])
                self.assertEqual(ctx["prescriptive"]["exec_summary_source"], "deterministic")
                self.assertEqual(ctx["prescriptive"]["exec_summary_privacy_reason"],
                                 model_privacy.notice(language))
                self.assertIn(model_privacy.notice(language), ctx["reporter"]["report_markdown"])
                # The authorized human keeps the real evidence; no silent redaction.
                self.assertIn(EMAIL, ctx["reporter"]["report_markdown"])

    def test_a_sensitive_group_beyond_the_dataset_scan_is_checked_before_sending(self):
        data = "month,team,sales\n" + "".join(
            f"2026-01,North,{i}\n" for i in range(1, 2001))
        data += f"2026-02,{EMAIL},9999999\n"
        gateway = RecordingNarrator()
        ctx = pipeline(data, gateway, mapping=explicit_grouping())
        self.assertFalse(ctx["privacy"]["personal_data"])
        self.assertEqual(gateway.calls, [])
        self.assertTrue(ctx["prescriptive"]["exec_summary_privacy_reason"])

    def test_automatic_grouping_omits_the_personal_label_and_still_blocks_the_model(self):
        gateway = RecordingNarrator()
        ctx = pipeline(PRIVATE_CSV, gateway)
        self.assertTrue(ctx["privacy"]["personal_data"])
        self.assertIsNone(ctx["preparer"]["group_col"])
        self.assertNotIn(EMAIL, ctx["reporter"]["report_markdown"])
        self.assertEqual(gateway.calls, [])

    def test_unflagged_aggregate_facts_still_reach_the_narrator(self):
        gateway = RecordingNarrator()
        ctx = pipeline(linear_dataset(), gateway)
        self.assertEqual(len(gateway.calls), 1)
        self.assertEqual(ctx["prescriptive"]["exec_summary_source"], "model")
        self.assertIsNone(ctx["prescriptive"]["exec_summary_privacy_reason"])


class ModelContextPrivacyTests(unittest.TestCase):
    def setUp(self):
        # Reach the privacy boundary with a fake available provider on any host.
        memory = patch("server.assistant_availability.free_memory_bytes", return_value=8 * 1024 ** 3)
        memory.start()
        self.addCleanup(memory.stop)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.gateway = RecordingNarrator()
        self.store = closing_store(self, open_store(None, root / "test.db"))
        self.engine = RunEngine(self.store, root / "vault", self.gateway)
        self.session = FakeSession(make_agent())

    def private_run(self):
        dataset = self.engine.store_dataset(PRIVATE_CSV, "synthetic.csv", "local-owner")
        self.engine.save_mapping(dataset["id"], "local-owner", explicit_grouping())
        run = self.engine.create_run("Analyze sales", dataset_id=dataset["id"])
        return finish(self.engine, run["id"])

    def test_joined_personal_data_also_stops_narration(self):
        main = self.engine.store_dataset(linear_dataset(), "sales.csv", "local-owner")
        lookup = self.engine.store_dataset(
            f"team,email\nAlpha,{EMAIL}\nBeta,other.person@example.invalid\n",
            "contacts.csv", "local-owner")
        run = self.engine.create_run("Analyze sales", dataset_id=main["id"],
            joins=[{"dataset_id": lookup["id"], "keys": [{"left": "team", "right": "team"}]}],
            breakdown="email")
        run = finish(self.engine, run["id"])
        tasks = {task["role"]: json.loads(task["result_json"])["output"]
                 for task in self.store.get_tasks(run["id"]) if task["result_json"]}
        self.assertFalse(tasks["privacy"]["personal_data"])
        self.assertTrue(tasks["merge"]["personal_data"])
        self.assertEqual(self.gateway.calls, [])
        self.assertTrue(model_privacy.run_blocks_model(self.store, run["id"]))

    def test_assistant_uses_rules_while_human_report_quotes_remain_intact(self):
        self.private_run()
        gateway = FakeGateway('{"action":"chat","reply":"model text"}')
        assistant = Assistant(gateway, self.engine)
        response = assistant.handle("Explain the report", self.session)
        self.assertEqual(gateway.asked, [])
        self.assertEqual(response["source"], "rules")
        self.assertIn(EMAIL, response["text"])
        self.assertEqual(response["why"], model_privacy.notice("en"))

    def test_runtime_never_receives_the_private_context(self):
        self.private_run()
        runtime = ScriptedRuntime()
        gateway = FakeGateway('{"action":"chat","reply":"model text"}')
        assistant = Assistant(gateway, self.engine, runtime=runtime)
        response = assistant.handle("Tell me something useful", self.session)
        self.assertIsNone(runtime.seen)
        self.assertEqual(gateway.asked, [])
        self.assertEqual(response["source"], "rules")
        self.assertEqual(response["why"], model_privacy.notice("en"))

    def test_model_facing_tools_withhold_private_reports_and_status(self):
        self.private_run()
        assistant = Assistant(FakeGateway("{}"), self.engine)
        for name in ("explain_report", "run_status"):
            tool = ToolBox(assistant, self.session)
            response = tool.call(name, {})
            self.assertFalse(response["ok"])
            self.assertIsNone(response["result"])
            self.assertNotIn(EMAIL, json.dumps(response))
            self.assertEqual(response["text"], model_privacy.notice("en"))

    def test_previous_private_report_in_history_remains_blocked_after_a_new_run(self):
        private = self.private_run()
        self.session.add_entry("agent", "Quoted private report", action="explain_report",
                               result={"run_id": private["id"]})
        safe = self.engine.create_run("Analyze sample sales")
        finish(self.engine, safe["id"])
        gateway = FakeGateway('{"action":"chat","reply":"model text"}')
        assistant = Assistant(gateway, self.engine)
        response = assistant.handle("Continue the conversation", self.session)
        self.assertEqual(gateway.asked, [])
        self.assertEqual(response["why"], model_privacy.notice("en"))


if __name__ == "__main__":
    unittest.main()
