"""The fourth P2 slice (assessment A11, A14, B11, G5, G6, G8): screened
inputs for the generic models, probabilities with a Brier score and
calibration bins, a bounded PostgreSQL connection pool, structured model
answers validated on the server with JSON mode per provider, consultant
agreement compared by finding reference, and eval cases for the knowledge
search and the agent scorecard."""

import json
import random
import threading
import unittest

import assistant as rules
from server import modelling, orchestration, schema
from server.assistant import INTENT_SCHEMA
from server.orchestration import ModelRoles, agreement, built_in_brief, parse_risks, report_section
from server.storage import PostgresStore, open_store
from tests.support import closing_store
from tests.test_modelling import context, linear_rows
from tests.test_runs import PG_TEST_URL, _postgres_available


class SchemaCheckerTest(unittest.TestCase):
    """G5: the server checks the shape it asked for."""

    def test_the_intent_schema_accepts_its_two_shapes_and_nothing_else(self):
        chat = {"action": "chat", "arguments": {}, "reply": "Hello"}
        act = {"action": "store_saved_memory", "arguments": {"information": "x"}, "reply": ""}
        self.assertTrue(schema.valid(INTENT_SCHEMA, chat))
        self.assertTrue(schema.valid(INTENT_SCHEMA, act))
        self.assertFalse(schema.valid(INTENT_SCHEMA, {"action": "chat", "arguments": {}, "reply": ""}))
        self.assertFalse(schema.valid(INTENT_SCHEMA, {"action": "delete_everything", "arguments": {}, "reply": ""}))
        self.assertFalse(schema.valid(INTENT_SCHEMA, {"action": "chat", "arguments": [], "reply": "x"}))
        self.assertFalse(schema.valid(INTENT_SCHEMA, {"action": "chat", "reply": "x"}))

    def test_problems_name_the_path_and_the_rule(self):
        spec = {"type": "object", "properties": {"n": {"type": "integer"},
                                                 "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 1}},
                "required": ["n"], "additionalProperties": False}
        found = schema.problems(spec, {"tags": [1, "a"], "extra": 1})
        self.assertIn("$.n: required", found)
        self.assertIn("$.tags[0]: must be string", found)
        self.assertIn("$.tags: at most 1 item(s)", found)
        self.assertIn("$.extra: not allowed", found)
        self.assertEqual(schema.problems({"type": "integer"}, True), ["$: must be integer"])


class StructuredRisksTest(unittest.TestCase):
    """G5 and G6: consultant risks in a schema, agreement by reference."""

    FACTS = ["Overdue work is 21.6% of completed work.",
             "Forecast error is 12% against a 15% baseline.",
             "Coverage is complete."]

    def test_a_valid_answer_is_parsed_and_out_of_range_findings_are_dropped(self):
        raw = json.dumps({"risks": [{"finding": 1, "concern": "Confirm the denominator."},
                                    {"finding": 9, "concern": "Nothing."}],
                          "note": "Two sentences. Of review."})
        note, risks = parse_risks("Here you go: " + raw, self.FACTS)
        self.assertEqual(note, "Two sentences. Of review.")
        self.assertEqual(risks, [{"finding": 1, "concern": "Confirm the denominator."}])

    def test_an_answer_outside_the_schema_is_refused(self):
        self.assertIsNone(parse_risks(json.dumps({"risks": "none", "note": "x"}), self.FACTS))
        self.assertIsNone(parse_risks(json.dumps({"risks": [{"finding": "1", "concern": "x"}], "note": "x"}), self.FACTS))
        self.assertIsNone(parse_risks("plain prose", self.FACTS))
        self.assertIsNone(parse_risks(None, self.FACTS))

    def test_agreement_is_a_comparison_of_references(self):
        notes = [{"provider": "a", "risks": [{"finding": 1, "concern": "x"}, {"finding": 2, "concern": "y"}]},
                 {"provider": "b", "risks": [{"finding": 2, "concern": "z"}]},
                 {"provider": "c", "risks": []}]
        agreed = agreement(notes, self.FACTS)
        self.assertEqual(agreed["agreed"], [2])
        self.assertEqual(agreed["single"], [1])
        self.assertEqual(agreed["agreed_findings"], [self.FACTS[1]])
        self.assertEqual(agreed["by_finding"], {"1": ["a"], "2": ["a", "b"]})

    def test_the_built_in_brief_names_the_agreement_without_a_digit_of_its_own(self):
        agreed = agreement([{"provider": "a", "risks": [{"finding": 2, "concern": "x"}]},
                            {"provider": "b", "risks": [{"finding": 2, "concern": "y"},
                                                        {"finding": 3, "concern": "z"}]}], self.FACTS)
        for language in ("en", "ar"):
            text = built_in_brief(self.FACTS, language, agreed)
            self.assertIn(self.FACTS[1], text)
            self.assertIn(self.FACTS[2], text)
            self.assertEqual(orchestration.grounded(text, self.FACTS), text, language)
        plain = built_in_brief(self.FACTS, "en", {"agreed": [], "single": []})
        self.assertNotIn("compared", plain)

    def test_two_structured_consultants_are_compared_in_the_report(self):
        class Gateway:
            def providers(self):
                return [{"provider": p, "model": "m", "local_only": False}
                        for p in ("anthropic", "openai")]

            def ask_json(self, system, user, provider=None, schema=None, task=None, **_):
                risks = [{"finding": 2, "concern": f"{provider} asks for the baseline's period."}]
                if provider == "anthropic":
                    risks.append({"finding": 1, "concern": "Confirm the denominator."})
                return json.dumps({"risks": risks, "note": "Check the baseline. Then the denominator."})

            def ask(self, *args, **kwargs):
                raise AssertionError("the free-text call is not needed when the schema is met")

        roles = ModelRoles(Gateway(), {"AGENTIC_OS_CONSULTANTS": "anthropic,openai"})
        result = roles.consult("Review", self.FACTS)
        self.assertEqual([n["provider"] for n in result["consultants"]], ["anthropic", "openai"])
        self.assertEqual(result["agreement"]["agreed"], [2])
        self.assertEqual(result["agreement"]["single"], [1])
        lines = "\n".join(report_section(result, "en"))
        self.assertIn("- Finding 2: anthropic asks for the baseline's period.", lines)
        self.assertIn("**Agreement (compared by the finding each risk names):**", lines)
        self.assertIn(self.FACTS[1], lines)
        arabic = "\n".join(report_section(result, "ar"))
        self.assertIn("**الاتفاق", arabic)

    def test_a_consultant_outside_the_schema_falls_back_to_free_text(self):
        class Gateway:
            def providers(self):
                return [{"provider": "anthropic", "model": "m", "local_only": False}]

            def ask_json(self, *args, **kwargs):
                return "I would rather write prose."

            def ask(self, system, user, provider=None, **kwargs):
                return "Confirm the coverage before acting."

        roles = ModelRoles(Gateway(), {"AGENTIC_OS_CONSULTANTS": "anthropic"})
        result = roles.consult("Review", self.FACTS)
        self.assertEqual(result["consultants"][0]["text"], "Confirm the coverage before acting.")
        self.assertEqual(result["consultants"][0]["risks"], [])
        self.assertEqual(result["agreement"]["agreed"], [])


class IntentRulesTest(unittest.TestCase):
    """G8: the two server actions the rules now reach, with their arguments."""

    def test_knowledge_searches_carry_the_query(self):
        found = rules.understand("What does the maintenance manual say about brake pad wear limits?")
        self.assertEqual(found["action"], "search_knowledge")
        self.assertEqual(found["arguments"]["query"], "brake pad wear limits")
        arabic = rules.understand("ابحث في قاعدة المعرفة عن فترات تشحيم المحامل")
        self.assertEqual(arabic["action"], "search_knowledge")
        self.assertEqual(arabic["arguments"]["query"], "فترات تشحيم المحامل")

    def test_scorecard_requests_carry_the_suite_when_named(self):
        self.assertEqual(rules.understand("Show me the agent scorecard")["arguments"]["suite"], None)
        found = rules.understand("What is the recall of the jargon detector?")
        self.assertEqual(found["action"], "agent_scorecard")
        self.assertEqual(found["arguments"]["suite"], "jargon")
        self.assertEqual(rules.understand("أرني بطاقة الأداء للوكلاء")["action"], "agent_scorecard")

    def test_the_eval_file_labels_both_actions_in_dev_and_holdout(self):
        data = json.loads(open("evals/intent.json", encoding="utf-8").read())
        for label in ("search_knowledge", "agent_scorecard"):
            self.assertIn(label, data["labels"])
            for split in ("dev", "holdout"):
                self.assertTrue([c for c in data[split] if c["label"] == label], f"{label} {split}")


def _rows_with_shadow(n=300):
    rows = linear_rows(n)
    for i, row in enumerate(rows):
        row["sales_copy"] = row["sales"]
        row["sales_x2"] = 2 * row["sales"] + 1
        row["email"] = f"person{i}@example.com"
        row["noise"] = random.Random(i).uniform(0, 1)
    return rows


class InputScreenTest(unittest.TestCase):
    """A11: the generic models refuse what can be known without a contract."""

    COLUMNS = ["channel", "price", "ads", "sales", "sales_copy", "sales_x2", "email", "noise"]
    NUMERIC = ["price", "ads", "sales", "sales_copy", "sales_x2", "noise"]

    def test_identical_derived_personal_and_ignored_columns_are_refused_with_reasons(self):
        rows = _rows_with_shadow()
        ctx = context(rows, self.COLUMNS, self.NUMERIC, "sales")
        ctx["mapping"] = {"roles": {"noise": "ignore"}}
        screened = modelling._screen(ctx, rows, self.COLUMNS, set(self.NUMERIC), "sales")
        self.assertEqual(screened["sales_copy"], "identical to the target")
        self.assertIn("linear function of the target", screened["sales_x2"])
        self.assertEqual(screened["email"], "detected personal data is not a model input")
        self.assertEqual(screened["noise"], "explicitly ignored by the saved column mapping")
        self.assertNotIn("price", screened)

    def test_the_regression_card_lists_the_refused_inputs(self):
        rows = _rows_with_shadow()
        ctx = context(rows, self.COLUMNS, self.NUMERIC, "sales")
        card = modelling.RegressionModel().run(ctx)["output"]["model_card"]
        self.assertNotIn("sales_copy", card["inputs"])
        self.assertNotIn("sales_x2", card["inputs"])
        self.assertEqual(set(card["excluded_inputs"]), {"sales_copy", "sales_x2", "email"})
        claim = next(c for c in modelling.RegressionModel().run(ctx)["claims"]
                     if c["id"].endswith("cl_inputs"))
        self.assertIn("refusing 3 column(s)", claim["text"])


class CalibrationTest(unittest.TestCase):
    """A14: probabilities, a Brier score against the base rate, and bins."""

    def test_calibration_arithmetic_on_known_values(self):
        result = modelling.calibration([0.9, 0.1, 0.8, 0.2], [1, 0, 1, 1], base_rate=0.75)
        self.assertAlmostEqual(result["brier"], (0.01 + 0.01 + 0.04 + 0.64) / 4, places=4)
        self.assertAlmostEqual(result["baseline_brier"], (0.0625 * 3 + 0.5625) / 4, places=4)
        self.assertTrue(result["better_than_base_rate"])
        self.assertEqual([b["records"] for b in result["bins"]], [1, 1, 2])
        self.assertEqual(result["bins"][0]["observed"], 0.0)
        self.assertEqual(result["bins"][2]["observed"], 1.0)

    def test_posteriors_sum_to_one_and_follow_the_prediction(self):
        model = modelling.fit_naive_bayes([[0.0], [0.1], [1.0], [1.1]], ["a", "a", "b", "b"])
        probabilities = modelling.naive_bayes_probabilities(model, [1.05])
        self.assertAlmostEqual(sum(probabilities.values()), 1.0)
        self.assertEqual(max(probabilities, key=probabilities.get),
                         modelling.predict_naive_bayes(model, [1.05]))

    def test_the_classification_card_carries_probabilities_and_their_score(self):
        rows = linear_rows(400)
        ctx = context(rows, ["channel", "price", "ads", "sales"], ["price", "ads", "sales"], "sales")
        result = modelling.ClassificationModel().run(ctx)
        probabilities = result["output"]["model_card"]["details"]["probabilities"]
        self.assertIn("brier", probabilities)
        self.assertIn("baseline_brier", probabilities)
        self.assertTrue(probabilities["bins"])
        self.assertIn(probabilities["positive_class"], result["output"]["model_card"]["details"]["classes"])
        ids = {c["id"].rsplit(".", 1)[-1] for c in result["calculations"]}
        self.assertTrue({"c_brier", "c_base_brier"} <= ids)
        if not probabilities["better_than_base_rate"]:
            self.assertTrue([c for c in result["claims"] if c["id"] == "cl_calibration"])


@unittest.skipUnless(_postgres_available(), "PostgreSQL test database not reachable")
class BoundedPoolTest(unittest.TestCase):
    """B11: connections per process stay within the bound and are reused."""

    def test_more_threads_than_the_bound_share_connections(self):
        store = closing_store(self, open_store(database_url=PG_TEST_URL))
        self.assertIsInstance(store, PostgresStore)
        store.MAX_CONNECTIONS = 2
        results, errors = [], []

        def reader():
            try:
                for _ in range(3):
                    results.append(len(store.list_runs(limit=1)))
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
        threads = [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(20)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 24)
        self.assertLessEqual(store.open_connections(), 2)
        # A transaction keeps its connection for its whole duration.
        with store.atomic("slice-four-pool"):
            first = store._conn
            store.list_runs(limit=1)
            self.assertIs(store._conn, first)


if __name__ == "__main__":
    unittest.main()
