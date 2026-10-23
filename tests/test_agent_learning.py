"""Agents that are measured again and again, and say when a person is needed.

Decision: docs/adr/2026-10-20-agent-measurement-loop.md.

The rules under test:

- the ledger is append-only and survives a damaged line;
- a record never carries a held-out sentence;
- a floor breach, a regression and a dev miss are each found;
- the loop always stops, and `done` is reported only when nothing is left;
- a proposed case is accepted by a named person, into dev only;
- the worker measures on a schedule and a failing measurement never stops it;
- the scorecard is a tool, in both languages, and it never writes.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from assistant import ACTIONS, DESTRUCTIVE, SERVER_ONLY, reply
from server import agent_learning as learning
from server.tools import NAMES, ToolBox
from tests.support import temp_workspace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def suite(dev, holdout, dev_misses=(), holdout_misses=0):
    def split(recall, cases, misses, items=()):
        out = {"cases": cases, "recall": recall, "accuracy": recall,
               "misses": misses, "confusions": [], "matrix": {}}
        if items:
            out["missed_items"] = [{"item": i, "truth": "a", "predicted": "b"} for i in items]
        return out
    return {"agent": "Test agent", "module": "test.module",
            "dev": split(dev, 10, len(dev_misses), dev_misses),
            "holdout": split(holdout, 10, holdout_misses)}


def record(**suites):
    return {"at": "2026-10-20T10:00:00+00:00", "rev": "abc123", "suites": suites}


FLOORS = {"alpha": {"dev": 1.0, "holdout": 0.7}}


class LedgerTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(temp_workspace(self, tempfile).name)
        self.ledger = learning.Ledger(self.dir / "ledger.jsonl")

    def test_records_are_appended_and_read_back_in_order(self):
        for n in range(3):
            self.ledger.append(dict(record(alpha=suite(1.0, 0.7)), at=f"t{n}"))
        self.assertEqual([r["at"] for r in self.ledger.records()], ["t0", "t1", "t2"])
        self.assertEqual(self.ledger.latest()["at"], "t2")

    def test_a_missing_ledger_is_empty_not_an_error(self):
        self.assertEqual(self.ledger.records(), [])
        self.assertIsNone(self.ledger.latest())

    def test_a_damaged_line_is_skipped_and_the_rest_still_read(self):
        self.ledger.append(record(alpha=suite(1.0, 0.7)))
        with open(self.ledger.path, "a", encoding="utf-8") as handle:
            handle.write("{not json\n[1, 2]\n")
        self.ledger.append(dict(record(alpha=suite(1.0, 0.8)), at="later"))
        self.assertEqual([r["at"] for r in self.ledger.records()][-1], "later")
        self.assertEqual(len(self.ledger.records()), 2)

    def test_the_ledger_is_trimmed_to_its_bound(self):
        original = learning.MAX_LEDGER_LINES
        learning.MAX_LEDGER_LINES = 5
        self.addCleanup(setattr, learning, "MAX_LEDGER_LINES", original)
        for n in range(8):
            self.ledger.append(dict(record(alpha=suite(1.0, 0.7)), at=f"t{n}"))
        self.assertEqual([r["at"] for r in self.ledger.records()],
                         ["t3", "t4", "t5", "t6", "t7"])


class MeasureTestCase(unittest.TestCase):
    def test_a_real_measurement_keeps_dev_misses_by_item_and_holdout_by_count(self):
        # intent has holdout misses today; the record must hold none of their text.
        measured = learning.measure(["intent"])["suites"]["intent"]
        holdout = measured["holdout"]
        self.assertGreater(holdout["misses"], 0)
        self.assertNotIn("missed_items", holdout)
        data = json.loads((ROOT / "evals" / "intent.json").read_text(encoding="utf-8"))
        wire = json.dumps(measured, ensure_ascii=False)
        for case in data["holdout"]:
            self.assertNotIn(case["text"], wire)
        self.assertIn("missed_items", measured["dev"])
        self.assertTrue(0 <= measured["holdout"]["recall"] <= 1)

    def test_every_suite_can_be_measured(self):
        measured = learning.measure()
        import evaluate_agents
        self.assertEqual(set(measured["suites"]), set(evaluate_agents.default_suites()))


class CompareTestCase(unittest.TestCase):
    def test_a_healthy_record_has_no_findings(self):
        self.assertEqual(learning.compare(record(alpha=suite(1.0, 0.8)), None, FLOORS), [])

    def test_a_floor_breach_is_found(self):
        found = learning.compare(record(alpha=suite(1.0, 0.6)), None, FLOORS)
        self.assertEqual([(f["kind"], f["split"]) for f in found], [("below_floor", "holdout")])

    def test_a_regression_is_found_even_above_the_floor(self):
        previous = record(alpha=suite(1.0, 0.95))
        found = learning.compare(record(alpha=suite(1.0, 0.8)), previous, FLOORS)
        self.assertEqual([f["kind"] for f in found], ["regression"])
        self.assertEqual(found[0]["was"], 0.95)

    def test_rounding_noise_is_not_a_regression(self):
        previous = record(alpha=suite(1.0, 0.8))
        self.assertEqual(learning.compare(record(alpha=suite(1.0, 0.7999)), previous, FLOORS), [])

    def test_a_dev_miss_is_found(self):
        found = learning.compare(record(alpha=suite(0.9, 0.8, dev_misses=["x"])), None, {})
        self.assertEqual([f["kind"] for f in found], ["dev_miss"])

    def test_a_gap_between_dev_and_holdout_is_information_and_never_a_finding(self):
        current = record(alpha=suite(1.0, 0.7))
        self.assertEqual(learning.compare(current, None, FLOORS), [])
        self.assertEqual(learning.generalisation_gaps(current)[0]["suite"], "alpha")

    def test_the_work_order_hands_over_dev_text_and_holdout_counts_only(self):
        current = record(alpha=suite(0.9, 0.7, dev_misses=["fix me"], holdout_misses=3))
        order = learning.work_order(current, learning.compare(current, None, FLOORS))
        alpha = order["suites"]["alpha"]
        self.assertEqual([m["item"] for m in alpha["dev_misses"]], ["fix me"])
        self.assertEqual(alpha["holdout"]["misses"], 3)
        self.assertNotIn("missed_items", alpha["holdout"])
        self.assertIn("Never read or copy a held-out sentence", " ".join(order["rules"]))


class LoopTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(temp_workspace(self, tempfile).name)
        self.ledger = learning.Ledger(self.dir / "ledger.jsonl")
        self.proposals = learning.Proposals(self.dir / "p.jsonl", self.dir)
        floors = learning.floors
        learning.floors = lambda: FLOORS
        self.addCleanup(setattr, learning, "floors", floors)

    def loop(self, sequence, **kwargs):
        feed = iter(sequence)
        last = {}

        def measure():
            last["record"] = next(feed, last.get("record"))
            return last["record"]
        return learning.AgentLoop(ledger=self.ledger, proposals=self.proposals,
                                  measure_fn=measure, **kwargs)

    def test_a_healthy_world_is_done_after_one_measurement(self):
        result = self.loop([record(alpha=suite(1.0, 0.8))]).run()
        self.assertEqual(result["state"], learning.DONE)
        self.assertEqual(len(result["rounds"]), 1)
        self.assertEqual(len(self.ledger.records()), 1)

    def test_without_an_improver_a_problem_goes_to_a_person_after_one_round(self):
        result = self.loop([record(alpha=suite(0.9, 0.8, dev_misses=["x"]))]).run()
        self.assertEqual(result["state"], learning.NEEDS_PERSON)
        self.assertEqual(len(result["rounds"]), 1)

    def test_an_improver_that_fixes_the_miss_ends_the_loop_done(self):
        sequence = [record(alpha=suite(0.9, 0.8, dev_misses=["x"])),
                    record(alpha=suite(1.0, 0.8))]
        orders = []
        result = self.loop(sequence, improvers=[lambda o: orders.append(o) or 1]).run()
        self.assertEqual(result["state"], learning.DONE)
        self.assertEqual(len(result["rounds"]), 2)
        self.assertEqual(orders[0]["suites"]["alpha"]["dev_misses"][0]["item"], "x")

    def test_an_improver_that_changes_nothing_hands_over_instead_of_spinning(self):
        result = self.loop([record(alpha=suite(0.9, 0.8, dev_misses=["x"]))],
                           improvers=[lambda o: 0]).run()
        self.assertEqual(result["state"], learning.NEEDS_PERSON)
        self.assertEqual(len(result["rounds"]), 1)

    def test_changes_without_gain_stall_after_the_patience_is_spent(self):
        stuck = record(alpha=suite(0.9, 0.8, dev_misses=["x"]))
        result = self.loop([stuck], improvers=[lambda o: 1], patience=2, max_rounds=9).run()
        self.assertEqual(result["state"], learning.STALLED)
        self.assertEqual(len(result["rounds"]), 3)

    def test_gain_keeps_the_loop_going_until_the_round_bound(self):
        sequence = [record(alpha=suite(0.5 + n / 20, 0.8, dev_misses=["x"])) for n in range(9)]
        result = self.loop(sequence, improvers=[lambda o: 1], max_rounds=4).run()
        self.assertEqual(result["state"], learning.BUDGET)
        self.assertEqual(len(result["rounds"]), 4)

    def test_the_time_budget_ends_the_loop(self):
        ticks = iter(range(0, 1000, 100))
        sequence = [record(alpha=suite(0.5 + n / 20, 0.8, dev_misses=["x"])) for n in range(9)]
        result = self.loop(sequence, improvers=[lambda o: 1], max_rounds=9,
                           budget_seconds=150, clock=lambda: next(ticks)).run()
        self.assertEqual(result["state"], learning.BUDGET)
        self.assertLess(len(result["rounds"]), 9)

    def test_a_failing_improver_does_not_end_the_loop(self):
        def broken(order):
            raise RuntimeError("boom")
        result = self.loop([record(alpha=suite(0.9, 0.8, dev_misses=["x"]))],
                           improvers=[broken]).run()
        self.assertEqual(result["state"], learning.NEEDS_PERSON)

    def test_a_pending_proposal_keeps_it_from_saying_done(self):
        (self.dir / "intent.json").write_text(json.dumps(
            {"labels": ["help", "chat"], "dev": [], "holdout": []}), encoding="utf-8")
        self.proposals.propose("intent", "Show me what you can do", "help", "reviewer")
        result = self.loop([record(alpha=suite(1.0, 0.8))]).run()
        self.assertEqual(result["state"], learning.NEEDS_PERSON)
        self.assertEqual(result["work_order"]["pending_proposals"], 1)

    def test_a_regression_against_the_previous_measurement_is_reported(self):
        self.ledger.append(record(alpha=suite(1.0, 0.95)))
        result = self.loop([record(alpha=suite(1.0, 0.8))]).run()
        self.assertEqual(result["state"], learning.NEEDS_PERSON)
        self.assertEqual([f["kind"] for f in result["work_order"]["findings"]], ["regression"])


class ProposalTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(temp_workspace(self, tempfile).name)
        shutil.copy(ROOT / "evals" / "intent.json", self.dir / "intent.json")
        self.proposals = learning.Proposals(self.dir / "p.jsonl", self.dir)

    def intent_data(self):
        return json.loads((self.dir / "intent.json").read_text(encoding="utf-8"))

    def test_a_proposal_waits_and_changes_no_suite(self):
        before = (self.dir / "intent.json").read_text(encoding="utf-8")
        item = self.proposals.propose("intent", "Could you list what you are able to do?",
                                      "help", "reviewer")
        self.assertEqual(item["status"], "pending")
        self.assertEqual((self.dir / "intent.json").read_text(encoding="utf-8"), before)
        self.assertEqual([p["id"] for p in self.proposals.pending()], [item["id"]])

    def test_acceptance_adds_to_dev_only_and_names_the_person(self):
        item = self.proposals.propose("intent", "Could you list what you are able to do?",
                                      "help", "reviewer")
        holdout_before = self.intent_data()["holdout"]
        dev_before = len(self.intent_data()["dev"])
        done = self.proposals.accept(item["id"], "Ahmed")
        data = self.intent_data()
        self.assertEqual(len(data["dev"]), dev_before + 1)
        self.assertEqual(data["dev"][-1], {"text": "Could you list what you are able to do?",
                                           "label": "help"})
        self.assertEqual(data["holdout"], holdout_before)
        self.assertEqual((done["status"], done["decided_by"]), ("accepted", "Ahmed"))
        self.assertEqual(self.proposals.pending(), [])

    def test_an_anonymous_decision_is_refused(self):
        item = self.proposals.propose("intent", "Could you list what you are able to do?",
                                      "help", "reviewer")
        for decide in (self.proposals.accept, self.proposals.reject):
            with self.assertRaises(learning.ProposalError):
                decide(item["id"], "  ")
        self.assertEqual(len(self.proposals.pending()), 1)

    def test_a_decided_proposal_cannot_be_decided_again(self):
        item = self.proposals.propose("intent", "Could you list what you are able to do?",
                                      "help", "reviewer")
        self.proposals.reject(item["id"], "Ahmed")
        with self.assertRaises(learning.ProposalError):
            self.proposals.accept(item["id"], "Ahmed")

    def test_accepting_into_any_proposable_suite_changes_one_entry_and_nothing_around_it(self):
        for name, filename in learning.TEXT_SUITES.items():
            text = (ROOT / "evals" / filename).read_text(encoding="utf-8")
            again = json.dumps(json.loads(text), ensure_ascii=False, indent=1) + "\n"
            self.assertEqual(again, text, f"{filename} would be reformatted on acceptance")

    def test_only_one_sentence_suites_take_proposals(self):
        with self.assertRaises(learning.ProposalError):
            self.proposals.propose("column_roles", "x", "measure", "reviewer")
        with self.assertRaises(learning.ProposalError):
            self.proposals.propose("intent", "a\nb", "help", "reviewer")

    def test_an_unknown_label_a_blank_source_and_an_oversize_text_are_refused(self):
        for args in (("intent", "hello there", "nonsense", "reviewer"),
                     ("intent", "hello there", "help", " "),
                     ("intent", "x" * (learning.MAX_TEXT + 1), "help", "reviewer"),
                     ("intent", "", "help", "reviewer")):
            with self.assertRaises(learning.ProposalError, msg=str(args)[:60]):
                self.proposals.propose(*args)

    def test_a_sentence_already_in_any_split_or_already_queued_is_refused(self):
        data = self.intent_data()
        with self.assertRaises(learning.ProposalError):
            self.proposals.propose("intent", data["holdout"][0]["text"],
                                   data["holdout"][0]["label"], "reviewer")
        self.proposals.propose("intent", "Could you list what you are able to do?",
                               "help", "reviewer")
        with self.assertRaises(learning.ProposalError):
            self.proposals.propose("intent", "Could you list what you are able to do?",
                                   "help", "reviewer")

    def test_the_queue_is_bounded(self):
        original = learning.MAX_PENDING
        learning.MAX_PENDING = 2
        self.addCleanup(setattr, learning, "MAX_PENDING", original)
        self.proposals.propose("intent", "Sentence number one here", "help", "reviewer")
        self.proposals.propose("intent", "Sentence number two here", "help", "reviewer")
        with self.assertRaises(learning.ProposalError):
            self.proposals.propose("intent", "Sentence number three here", "help", "reviewer")


class StewardTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(temp_workspace(self, tempfile).name)
        self.ledger = learning.Ledger(self.dir / "ledger.jsonl")
        self.now = [0.0]
        self.logged = []

    def steward(self, measure_fn, interval=60):
        return learning.Steward(interval, ledger=self.ledger, measure_fn=measure_fn,
                                clock=lambda: self.now[0], log=self.logged.append)

    def test_the_interval_is_off_by_default_and_never_below_a_minute(self):
        self.assertEqual(learning.interval_from({}), 0)
        self.assertEqual(learning.interval_from({"AGENTIC_OS_EVAL_INTERVAL_SECONDS": "5"}), 60)
        self.assertEqual(learning.interval_from({"AGENTIC_OS_EVAL_INTERVAL_SECONDS": "300"}), 300)
        self.assertEqual(learning.interval_from({"AGENTIC_OS_EVAL_INTERVAL_SECONDS": "soon"}), 0)
        self.assertEqual(learning.interval_from({"AGENTIC_OS_EVAL_INTERVAL_SECONDS": "-3"}), 0)

    def test_it_measures_when_due_records_and_waits_for_the_interval(self):
        steward = self.steward(lambda: record(alpha=suite(1.0, 0.8)))
        self.assertEqual(steward.tick(), [])
        self.assertEqual(len(self.ledger.records()), 1)
        self.now[0] = 30
        self.assertIsNone(steward.tick())
        self.now[0] = 61
        self.assertEqual(steward.tick(), [])
        self.assertEqual(len(self.ledger.records()), 2)

    def test_a_regression_is_logged_for_the_operator(self):
        values = iter([record(alpha=suite(1.0, 0.95)), record(alpha=suite(1.0, 0.8))])
        steward = self.steward(lambda: next(values))
        steward.tick()
        self.now[0] = 100
        findings = steward.tick()
        self.assertEqual([f["kind"] for f in findings], ["regression"])
        self.assertTrue(any("regression in alpha" in line for line in self.logged))

    def test_an_interval_of_zero_never_measures(self):
        steward = self.steward(lambda: self.fail("measured while off"), interval=0)
        self.assertIsNone(steward.tick())

    def test_the_worker_loop_measures_and_survives_a_failing_measurement(self):
        from server.worker import RunWorker
        calls = []

        def measure_fn():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("suite crashed")
            return record(alpha=suite(1.0, 0.8))
        steward = self.steward(measure_fn)

        class IdleStore:
            def __init__(self):
                self.heartbeats = []

            def claim_run(self, *args):
                return None

            def upsert_worker_heartbeat(self, worker_id, seen_at, state):
                self.heartbeats.append({"id": worker_id, "seen_at": seen_at, "state": state})

        store = IdleStore()
        worker = RunWorker(engine=None, store=store, steward=steward)
        stop = type("Stop", (), {"naps": 0, "is_set": lambda s: s.naps >= 3})()

        def nap(seconds):
            stop.naps += 1
            self.now[0] += 100

        worker.run_forever(poll_seconds=0.01, stop=stop, sleep=nap)
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(len(self.ledger.records()), len(calls) - 1)
        states = [row["state"] for row in store.heartbeats]
        self.assertEqual(states[0], "idle")
        self.assertEqual(states.count("evaluating"), stop.naps)
        self.assertEqual(states[-1], "stopped")
        self.assertEqual({row["id"] for row in store.heartbeats}, {worker.worker_id})
        self.assertTrue(all(row["seen_at"] for row in store.heartbeats))


class ScorecardToolTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(temp_workspace(self, tempfile).name)
        self.ledger = learning.Ledger(self.dir / "ledger.jsonl")

    def test_it_reads_the_ledger_and_does_not_write(self):
        self.ledger.append(record(intent=suite(1.0, 0.72), jargon=suite(1.0, 0.9)))
        before = self.ledger.path.read_text(encoding="utf-8")
        card = learning.scorecard(ledger=self.ledger)
        self.assertEqual([r["suite"] for r in card["rows"]], ["intent", "jargon"])
        self.assertFalse(card["measured_now"])
        self.assertEqual(self.ledger.path.read_text(encoding="utf-8"), before)

    def test_one_suite_can_be_asked_for(self):
        self.ledger.append(record(intent=suite(1.0, 0.72), jargon=suite(1.0, 0.9)))
        card = learning.scorecard("jargon", ledger=self.ledger)
        self.assertEqual([r["suite"] for r in card["rows"]], ["jargon"])

    def test_without_a_ledger_it_measures_but_records_nothing(self):
        card = learning.scorecard("raw_guard", ledger=self.ledger)
        self.assertTrue(card["measured_now"])
        self.assertFalse(self.ledger.path.exists())

    def test_it_is_a_read_only_tool_the_driver_may_call(self):
        self.assertIn("agent_scorecard", NAMES)
        self.assertIn("agent_scorecard", SERVER_ONLY)
        self.assertNotIn("agent_scorecard", DESTRUCTIVE)
        self.assertEqual(set(ACTIONS["agent_scorecard"]), {"suite"})

    def test_a_tool_call_answers_in_both_languages(self):
        from server.assistant import Assistant
        import os
        previous = os.environ.get("AGENTIC_OS_EVAL_LEDGER")
        os.environ["AGENTIC_OS_EVAL_LEDGER"] = str(self.ledger.path)

        def restore():
            if previous is None:
                os.environ.pop("AGENTIC_OS_EVAL_LEDGER", None)
            else:
                os.environ["AGENTIC_OS_EVAL_LEDGER"] = previous
        self.addCleanup(restore)
        # The default Ledger() reads the environment at construction.
        self.ledger.append(record(intent=suite(1.0, 0.72)))
        for language in ("en", "ar"):
            outcome = Assistant._agent_scorecard(None, {"suite": "intent"}, language)
            self.assertIn("intent", outcome["text"])
            self.assertIn("72%", outcome["text"])
        arabic = Assistant._agent_scorecard(None, {}, "ar")["text"]
        self.assertTrue(any("؀" <= ch <= "ۿ" for ch in arabic))
        self.assertIn("scorecard_none", __import__("assistant").REPLIES["en"])
        self.assertTrue(reply("ar", "scorecard_none"))

    def test_what_the_tool_returns_is_never_mistaken_for_personal_data(self):
        """A 16-digit float or an ISO timestamp reads as a phone number to the
        privacy guard, which would withhold the scorecard from the model that
        asked for it. Measured with real recall values, as the suites give them."""
        import os
        from server import model_privacy
        from server.assistant import Assistant
        self.ledger.append(record(intent=suite(1.0, 43 / 60), jargon=suite(1.0, 22 / 24)))
        previous = os.environ.get("AGENTIC_OS_EVAL_LEDGER")
        os.environ["AGENTIC_OS_EVAL_LEDGER"] = str(self.ledger.path)
        self.addCleanup(lambda: os.environ.__setitem__("AGENTIC_OS_EVAL_LEDGER", previous)
                        if previous is not None else os.environ.pop("AGENTIC_OS_EVAL_LEDGER", None))
        for language in ("en", "ar"):
            outcome = Assistant._agent_scorecard(None, {}, language)
            self.assertFalse(model_privacy.blocks_model(
                texts=[outcome["text"], json.dumps(outcome["result"])]), language)

    def test_the_toolbox_runs_it_and_records_the_call(self):
        from server.assistant import Assistant

        class Session:
            class agent:
                @staticmethod
                def language():
                    return "en"

        class Fake:
            _agent_scorecard = Assistant._agent_scorecard
            _model_privacy_reason = staticmethod(lambda session, text: None)

            def _execute(self, name, arguments, session, text, source="runtime"):
                outcome = self._agent_scorecard(arguments, "en")
                return {"text": outcome["text"], "result": outcome["result"]}

        self.ledger.append(record(intent=suite(1.0, 0.72)))
        import os
        os.environ["AGENTIC_OS_EVAL_LEDGER"] = str(self.ledger.path)
        self.addCleanup(os.environ.pop, "AGENTIC_OS_EVAL_LEDGER", None)
        box = ToolBox(Fake(), Session())
        outcome = box.call("agent_scorecard", {"suite": "intent"})
        self.assertTrue(outcome["ok"])
        self.assertEqual(box.steps[0]["tool"], "agent_scorecard")
        self.assertIn("holdout 72%", box.steps[0]["text"])


if __name__ == "__main__":
    unittest.main()
