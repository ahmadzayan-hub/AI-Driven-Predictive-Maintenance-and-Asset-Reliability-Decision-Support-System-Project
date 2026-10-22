"""Model roles: Hermes plans and briefs, agents phrase their findings,
consultants review. Words only, grounded in verified facts; nothing
configured changes nothing. No test touches the network."""

import tempfile
import unittest
from pathlib import Path

from server.model_gateway import ModelGateway
from server.orchestration import (ModelRoles, built_in_consult, built_in_plan,
                                  grounded, report_section)
from server.runs import RunEngine
from server.storage import open_store

ROLES = {"AGENTIC_OS_HERMES_MODEL": "anthropic", "AGENTIC_OS_AGENT_MODEL": "ollama",
         "AGENTIC_OS_CONSULTANTS": "anthropic,openai"}
NO_BUILT_IN = {"AGENTIC_OS_BUILT_IN_ROLES": "0"}


class FakeGateway:
    """Answers like a model would, and records who was asked what."""

    def __init__(self, invent=None):
        self.calls = []
        self.invent = invent  # provider that slips in a figure of its own

    def providers(self):
        return [{"provider": p, "model": "m", "local_only": p == "ollama"}
                for p in ("ollama", "anthropic", "openai")] + [
            {"provider": "deterministic", "model": None, "local_only": True}]

    def narrate(self, goal, facts, provider=None, language="en"):
        self.calls.append(("narrate", provider, facts))
        return {"text": "In short: " + facts[0], "source": "model"}

    def ask(self, system, user, provider=None, max_tokens=None):
        self.calls.append(("ask", provider, system + user))
        if provider == self.invent:
            return "Savings of 98765 dollars are certain."
        if "Consultant (" in user:
            return "Check data coverage first; the consultants agree."
        if system.startswith("You are Hermes"):
            return "Quality and diagnostic stages matter most for this goal."
        return f"{provider}: confirm the data coverage before acting."


class RoleSelectionTestCase(unittest.TestCase):
    def test_nothing_configured_means_the_built_in_writer_plays_every_role(self):
        roles = ModelRoles(FakeGateway(), {})
        self.assertTrue(roles.active)
        self.assertTrue(roles.all_built_in)
        self.assertEqual(roles.status(), {"hermes": "built-in", "agents": "built-in",
                                          "consultants": ["built-in"], "problems": []})

    def test_the_built_in_writer_can_be_switched_off(self):
        roles = ModelRoles(FakeGateway(), NO_BUILT_IN)
        self.assertFalse(roles.active)
        self.assertEqual(roles.status(), {"hermes": "rules", "agents": None,
                                          "consultants": [], "problems": []})

    def test_each_role_takes_a_reachable_provider(self):
        roles = ModelRoles(FakeGateway(), ROLES)
        self.assertEqual((roles.hermes, roles.agents, roles.consultants),
                         ("anthropic", "ollama", ["anthropic", "openai"]))

    def test_an_unreachable_provider_is_reported_not_used(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "qwen3:4b"})
        roles = ModelRoles(gateway, {**ROLES, **NO_BUILT_IN})
        self.assertEqual((roles.hermes, roles.agents, roles.consultants),
                         (None, "ollama", []))
        self.assertEqual(len(roles.status()["problems"]), 3)
        # With the built-in writer on, the unreachable roles fall to it.
        roles = ModelRoles(gateway, ROLES)
        self.assertEqual((roles.hermes, roles.agents, roles.consultants),
                         ("built-in", "ollama", ["built-in"]))
        self.assertFalse(roles.all_built_in)


class GroundingTestCase(unittest.TestCase):
    def test_a_note_may_repeat_a_figure_but_never_add_one(self):
        facts = ["Availability is 95.8% across 1,200 records."]
        self.assertTrue(grounded("Availability stands at 95.8% on 1,200 records.", facts))
        self.assertIsNone(grounded("Availability is 97% on 1,200 records.", facts))
        self.assertIsNone(grounded("", facts))

    def test_an_invented_figure_drops_that_consultant_only(self):
        roles = ModelRoles(FakeGateway(invent="openai"), ROLES)
        notes = roles.consult("goal", ["Overdue work is 21.6% of completed work."])
        self.assertEqual([n["provider"] for n in notes["consultants"]], ["anthropic"])
        self.assertIsNotNone(notes["hermes"])

    def test_the_report_section_labels_every_author_in_both_languages(self):
        notes = {"hermes": {"provider": "anthropic", "text": "Check X."},
                 "consultants": [{"provider": "openai", "text": "Ask Y."}]}
        english = "\n".join(report_section(notes))
        self.assertIn("Hermes (orchestrator, anthropic)", english)
        self.assertIn("Consultant (openai)", english)
        self.assertIn("every number in this report is calculated", english)
        self.assertIn("هيرميس", "\n".join(report_section(notes, "ar")))
        self.assertEqual(report_section(None), [])


class PipelineWithRolesTestCase(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.store = open_store(None, root / "runs.db")
        self.addCleanup(self.store.close)
        self.gateway = FakeGateway()
        self.engine = RunEngine(self.store, root / "vault", ModelGateway(env={}),
                                roles=ModelRoles(self.gateway, ROLES))

    def drive(self, goal="Review maintenance cost"):
        run = self.engine.create_run(goal)
        for _ in range(100):
            if run["state"] not in ("queued", "running"):
                break
            run = self.engine.advance(run["id"])
        return run

    def test_every_role_contributes_and_the_figures_stay_calculated(self):
        run = self.drive()
        self.assertEqual(run["state"], "awaiting_approval")
        import json
        tasks = {t["role"]: json.loads(t["result_json"] or "{}")
                 for t in self.store.get_tasks(run["id"])}
        self.assertEqual(tasks["planner"]["hermes_plan"]["provider"], "anthropic")
        noted = [role for role, result in tasks.items() if result.get("agent_note")]
        self.assertIn("descriptive", noted)
        self.assertTrue(all(tasks[r]["agent_note"]["provider"] == "ollama" for r in noted))
        orchestration = tasks["reporter"]["orchestration"]
        self.assertEqual([n["provider"] for n in orchestration["consultants"]],
                         ["anthropic", "openai"])
        report = self.store.latest_artifact(run["id"])["content"]
        self.assertIn("## Orchestrator and consultant notes", report)
        self.assertIn("Check data coverage first", report)
        # Only verified sentences reached a model: never a dataset row.
        dataset = self.engine._dataset_text(self.store.get_run(run["id"]))
        first_row = dataset.splitlines()[1]
        self.assertFalse(any(first_row in str(call) for call in self.gateway.calls))

    def test_a_failing_model_never_fails_the_run(self):
        def broken(*args, **kwargs):
            raise RuntimeError("provider down")
        self.gateway.ask = broken
        self.gateway.narrate = broken
        run = self.drive()
        self.assertEqual(run["state"], "awaiting_approval")
        report = self.store.latest_artifact(run["id"])["content"]
        self.assertNotIn("Orchestrator and consultant notes", report)

    def test_without_roles_the_report_is_unchanged(self):
        self.engine.roles = None
        run = self.drive()
        report = self.store.latest_artifact(run["id"])["content"]
        self.assertNotIn("Orchestrator and consultant notes", report)


class BuiltInRolesTestCase(unittest.TestCase):
    """No model anywhere: the built-in writer plans, notes and consults
    from the verified findings, in both languages, without a figure of
    its own."""

    FACTS = ["Overdue work is 21.6% of completed work.",
             "Downtime per 1,000 planned hours is 12.4.",
             "Three columns are missing values in 8% of records."]

    def test_the_plan_names_the_order_and_the_guarding_stages(self):
        roster = ["Data contract", "Data quality", "Privacy", "Descriptive", "Validator", "Publish"]
        plan = built_in_plan("Review cost", roster)
        self.assertIn("from Data contract to Publish", plan)
        self.assertIn("Data quality, Privacy, Validator", plan)
        self.assertIn("a person approves", plan)
        self.assertIn("من Data contract إلى Publish", built_in_plan("x", roster, "ar"))
        self.assertIsNone(built_in_plan("x", []))

    def test_the_consultant_raises_the_standard_question_then_the_triggered_rules(self):
        note = built_in_consult(self.FACTS)
        self.assertTrue(note.startswith("Before approving"))
        self.assertIn("Coverage:", note)
        self.assertIn("Operations:", note)
        self.assertNotIn("Finance:", note)
        self.assertIn("Finding to check: Overdue work is 21.6%", note)
        self.assertEqual(note.count("Finding to check"), 2)
        # Only quoted findings carry digits, so the note is always grounded.
        self.assertEqual(grounded(note, self.FACTS), note)
        arabic = built_in_consult(self.FACTS, "ar")
        self.assertIn("التغطية", arabic)
        self.assertEqual(grounded(arabic, self.FACTS), arabic)

    def test_a_run_with_no_model_still_carries_the_section_in_both_languages(self):
        import json
        for language in ("en", "ar"):
            root = Path(tempfile.mkdtemp())
            store = open_store(None, root / "runs.db")
            self.addCleanup(store.close)
            engine = RunEngine(store, root / "vault", ModelGateway(env={}),
                               roles=ModelRoles(ModelGateway(env={}), {}))
            run = engine.create_run("Review maintenance cost", language=language)
            for _ in range(100):
                if run["state"] not in ("queued", "running"):
                    break
                run = engine.advance(run["id"])
            self.assertEqual(run["state"], "awaiting_approval", language)
            tasks = {t["role"]: json.loads(t["result_json"] or "{}")
                     for t in store.get_tasks(run["id"])}
            self.assertEqual(tasks["planner"]["hermes_plan"]["provider"], "built-in")
            notes = [r["agent_note"] for r in tasks.values() if r.get("agent_note")]
            self.assertTrue(notes)
            self.assertTrue(all(n["provider"] == "built-in" for n in notes))
            orchestration = tasks["reporter"]["orchestration"]
            self.assertEqual([n["provider"] for n in orchestration["consultants"]], ["built-in"])
            self.assertEqual(orchestration["hermes"]["provider"], "built-in")
            report = store.latest_artifact(run["id"])["content"]
            if language == "en":
                self.assertIn("Hermes (orchestrator, built-in)", report)
                self.assertIn("Consultant (built-in)", report)
                self.assertIn("built-in rules", report)
                self.assertNotIn("Written by language models", report)
            else:
                self.assertIn("قواعد المنصة المدمجة", report)

    def test_a_model_beside_the_built_in_writer_keeps_the_model_caution(self):
        notes = {"hermes": {"provider": "built-in", "text": "Check X."},
                 "consultants": [{"provider": "openai", "text": "Ask Y."}]}
        self.assertIn("Written by language models", "\n".join(report_section(notes)))


class LocalHermesAndAgentsTestCase(unittest.TestCase):
    """One local Ollama, two models: Hermes on hermes3, agents on qwen3."""

    def test_a_run_uses_each_roles_own_model(self):
        import json
        from unittest.mock import patch
        env = {"OLLAMA_MODEL": "qwen3",
               "AGENTIC_OS_TASK_MODELS": "hermes=ollama:hermes3,agents=ollama:qwen3"}
        root = Path(tempfile.mkdtemp())
        store = open_store(None, root / "runs.db")
        self.addCleanup(store.close)
        gateway = ModelGateway(env=env)
        engine = RunEngine(store, root / "vault", ModelGateway(env={}),
                           roles=ModelRoles(gateway, env))
        models = []

        def answer(self, url, headers, payload):
            models.append(payload["model"])
            # No digits: a note may not add a figure (grounded()).
            return {"message": {"content": "Check data coverage first."}}

        with patch.object(ModelGateway, "_post", autospec=True, side_effect=answer):
            run = engine.create_run("Review maintenance cost")
            for _ in range(100):
                if run["state"] not in ("queued", "running"):
                    break
                run = engine.advance(run["id"])
        self.assertEqual(run["state"], "awaiting_approval")
        tasks = {t["role"]: json.loads(t["result_json"] or "{}")
                 for t in store.get_tasks(run["id"])}
        self.assertEqual(tasks["planner"]["hermes_plan"],
                         {"text": "Check data coverage first.", "provider": "ollama:hermes3"})
        notes = [r["agent_note"] for r in tasks.values() if r.get("agent_note")]
        self.assertTrue(notes)
        self.assertTrue(all(n["provider"] == "ollama:qwen3" for n in notes))
        self.assertEqual(set(models), {"hermes3", "qwen3"})
        report = store.latest_artifact(run["id"])["content"]
        self.assertIn("Hermes (orchestrator, ollama:hermes3)", report)


if __name__ == "__main__":
    unittest.main()
