"""The chat understands a sentence and acts on it — and knows its limits.

Three layers, tested separately because they fail separately:

- the rules (`assistant.understand`): a sentence in either language →
  one of a small set of typed actions, with no model;
- the executor: what each action does, which is the Agent's own
  behaviour — a reply never claims a save that did not happen;
- the server assistant: confirmations for anything destructive, the
  actions that need the run engine, and the model path — what a model
  may decide, what it may not, and what it is never shown.
"""

import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

import assistant
from agent import Agent
from server import analytics
from tests.support import closing, closing_store
from server.assistant import Assistant, INTENT_SCHEMA, MODEL_ACTION_ALIASES
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import open_store


def make_agent(language="English", tone="friendly"):
    return Agent({"agent_name": "Agentic OS", "version": "1.0.0",
                  "preferences": {"language": language, "tone": tone}})


class FakeSession:
    """The two things the assistant needs from a session."""

    def __init__(self, agent, owner="local-owner"):
        self.agent = agent
        self.owner = owner
        self.transcript = []

    def add_entry(self, role, text, **extra):
        entry = {"role": role, "text": text}
        entry.update({k: v for k, v in extra.items() if v is not None})
        self.transcript.append(entry)
        return entry


class FakeGateway:
    """A model that answers whatever the test says, and remembers what
    it was asked."""

    def __init__(self, answer, configured=True, provider="ollama"):
        self.answer = answer
        self.configured = configured
        self.provider = provider
        self.asked = []

    def status(self):
        return {"provider": self.provider if self.configured else "deterministic",
                "model": "fake", "configured": self.configured, "local_only": True}

    def ask(self, system, user, provider=None, max_tokens=None):
        self.asked.append((system, user))
        return self.answer


def engine_in(directory, case=None):
    """An engine over a throwaway store.

    Pass `case` to have the connection closed in that test's teardown:
    Windows will not delete the database file while a handle is open, so
    an unclosed store turns a passing test into a cleanup ERROR.
    """
    store = open_store(None, Path(directory) / "agentic.db")
    if case is not None:
        closing_store(case, store)
    return RunEngine(store, Path(directory) / "vault", ModelGateway(env={}))


def finish(engine, run_id):
    """Advance a run until it needs a person or ends."""
    for _ in range(40):
        run = engine.advance(run_id)
        if run["state"] not in ("queued", "running"):
            return run
    raise AssertionError("the run did not settle")


def action_of(text):
    return assistant.understand(text)["action"]


def args_of(text):
    return assistant.understand(text)["arguments"]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

class RulesEnglishTestCase(unittest.TestCase):
    def test_help(self):
        for text in ("help", "What can you do?", "what commands are there"):
            self.assertEqual(action_of(text), "help", text)

    def test_remember_keeps_the_information_and_drops_the_verb(self):
        self.assertEqual(args_of("Remember that the Q4 review is on Monday"),
                         {"information": "the Q4 review is on Monday", "category": None})
        self.assertEqual(args_of("Note: coffee at 8")["information"], "coffee at 8")
        self.assertEqual(action_of("remember"), "remember")
        self.assertEqual(args_of("remember")["information"], "")

    def test_a_note_about_deleting_is_a_note_not_a_deletion(self):
        self.assertEqual(action_of("Remember to delete all the old files"), "remember")

    def test_recall_with_and_without_a_topic(self):
        self.assertEqual(assistant.understand("What do you remember?"),
                         assistant.intent("recall", {"query": None}))
        self.assertEqual(args_of("what do you remember about coffee")["query"], "coffee")
        self.assertEqual(action_of("do you remember my name?"), "recall")

    def test_forget_everything_and_forget_one(self):
        for text in ("forget everything", "delete all memory", "wipe your memory"):
            self.assertEqual(args_of(text), {"key": "all"}, text)
        self.assertEqual(args_of("please forget memory_2"), {"key": "memory_2"})

    def test_clear_history(self):
        self.assertEqual(action_of("clear the conversation history"), "clear_history")

    def test_preferences_from_sentences(self):
        self.assertEqual(args_of("call me Ahmad"), {"key": "user_name", "value": "Ahmad"})
        self.assertEqual(args_of("My name is Sara Ali")["value"], "Sara Ali")
        self.assertEqual(args_of("be concise"), {"key": "tone", "value": "concise"})
        self.assertEqual(args_of("keep it short")["value"], "concise")
        self.assertEqual(args_of("please reply formally")["value"], "formal")
        self.assertEqual(args_of("reply in Arabic"), {"key": "language", "value": "Arabic"})
        self.assertEqual(args_of("arabic")["value"], "Arabic")
        self.assertEqual(args_of("switch to English")["value"], "English")

    def test_a_language_or_tone_word_inside_a_sentence_is_not_a_request(self):
        self.assertEqual(action_of("I like Arabic coffee in the morning"), "chat")
        self.assertEqual(action_of("the report was short"), "chat")

    def test_start_a_run(self):
        self.assertEqual(assistant.understand("Analyse the sample sales data"),
                         assistant.intent("start_run", {"goal": "Analyse the sample sales data",
                                                        "dataset": "sample"}))
        self.assertEqual(args_of("run an analysis of quarterly_sales")["dataset"], None)
        self.assertEqual(action_of("give me a report on revenue"), "start_run")

    def test_status_wins_over_the_noun_analysis(self):
        for text in ("what's the status of the analysis?", "is the analysis done?",
                     "is it finished?", "how far along is the run"):
            self.assertEqual(action_of(text), "run_status", text)

    def test_explain_picks_the_section_from_the_question(self):
        self.assertEqual(args_of("why did revenue move?")["section"], "diagnostic")
        self.assertEqual(args_of("what should we do?")["section"], "prescriptive")
        self.assertEqual(args_of("what will happen next quarter?")["section"], "predictive")
        self.assertEqual(args_of("can we claim a cause?")["section"], "experiment")
        self.assertEqual(args_of("explain the latest report")["section"], "all")
        self.assertEqual(action_of("what were the key findings"), "explain_report")

    def test_everything_else_is_chat(self):
        self.assertEqual(action_of("the weather is nice today"), "chat")
        self.assertEqual(action_of(""), "chat")


class RulesArabicTestCase(unittest.TestCase):
    def test_help(self):
        self.assertEqual(action_of("ماذا تستطيع أن تفعل؟"), "help")
        self.assertEqual(action_of("مساعدة"), "help")

    def test_remember(self):
        self.assertEqual(args_of("تذكّر أن الاجتماع الساعة الثامنة")["information"],
                         "الاجتماع الساعة الثامنة")
        self.assertEqual(args_of("احفظ: مراجعة الربع الرابع يوم الاثنين")["information"],
                         "مراجعة الربع الرابع يوم الاثنين")

    def test_recall(self):
        self.assertEqual(action_of("ماذا تتذكر؟"), "recall")
        self.assertEqual(args_of("إيه اللي فاكره عن القهوة")["query"], "القهوة")

    def test_forget_and_clear(self):
        self.assertEqual(args_of("انسَ كل شيء"), {"key": "all"})
        self.assertEqual(args_of("احذف memory_1"), {"key": "memory_1"})
        self.assertEqual(action_of("امسح سجل المحادثة"), "clear_history")

    def test_preferences(self):
        self.assertEqual(args_of("ناديني أحمد"), {"key": "user_name", "value": "أحمد"})
        self.assertEqual(args_of("خليك مختصر"), {"key": "tone", "value": "concise"})
        self.assertEqual(args_of("رد بشكل رسمي")["value"], "formal")
        self.assertEqual(args_of("رد بالإنجليزي"), {"key": "language", "value": "English"})

    def test_runs(self):
        self.assertEqual(args_of("حلّل بيانات المبيعات النموذجية")["dataset"], "sample")
        self.assertEqual(action_of("وصل فين التحليل؟"), "run_status")
        self.assertEqual(action_of("خلص التحليل؟"), "run_status")

    def test_explain(self):
        self.assertEqual(args_of("لماذا تغيّرت الإيرادات؟")["section"], "diagnostic")
        self.assertEqual(args_of("ماذا ينبغي أن نفعل؟")["section"], "prescriptive")
        self.assertEqual(args_of("اشرح آخر تقرير")["section"], "all")

    def test_chat(self):
        self.assertEqual(action_of("الجو جميل النهاردة"), "chat")


# ---------------------------------------------------------------------------
# The executor, through the Agent alone (this is also the CLI's path)
# ---------------------------------------------------------------------------

class ExecutorTestCase(unittest.TestCase):
    def test_a_sentence_saves_a_memory_with_the_agents_own_confirmation(self):
        agent = make_agent()
        self.assertEqual(agent.process_input("Remember that the review is on Monday"),
                         "Information saved.")
        self.assertIn("the review is on Monday", agent.memory.values())

    def test_recall_lists_or_says_nothing_matched(self):
        agent = make_agent()
        agent.process_input("remember coffee at 8")
        self.assertIn("coffee at 8", agent.process_input("what do you remember?"))
        self.assertEqual(agent.process_input("what do you remember about tea"),
                         "Nothing I remember mentions “tea”.")

    def test_preferences_are_validated_before_they_are_set(self):
        agent = make_agent()
        self.assertIn("concise", agent.process_input("be concise"))
        self.assertEqual(agent.preferences["tone"], "concise")
        self.assertIn("Ahmad", agent.process_input("call me Ahmad"))
        self.assertEqual(agent.preferences["user_name"], "Ahmad")
        # An action with a bad argument is refused, not stored.
        agent.preferences["tone"] = "concise"
        self.assertIn("friendly, concise, or formal",
                      assistant.execute_local("set_preference",
                                              {"key": "tone", "value": "shouty"}, agent, ""))
        self.assertEqual(agent.preferences["tone"], "concise")
        self.assertIn("I can change",
                      assistant.execute_local("set_preference",
                                              {"key": "api_key", "value": "x"}, agent, ""))

    def test_the_fallback_is_honest_and_in_the_chosen_tone(self):
        self.assertIn("Happy to help", make_agent().process_input("the weather is nice"))
        self.assertIn("Not sure what to do with “the weather is nice”",
                      make_agent(tone="concise").process_input("the weather is nice"))
        self.assertIn("was not understood",
                      make_agent(tone="formal").process_input("the weather is nice"))
        self.assertIn("يسعدني المساعدة", make_agent("Arabic").process_input("الجو جميل"))
        self.assertIn("لم أفهم", make_agent("Arabic", "concise").process_input("الجو جميل"))

    def test_the_command_line_says_runs_need_the_web_interface(self):
        self.assertIn("web interface", make_agent().process_input("analyse the sales data"))
        self.assertIn("واجهة الويب", make_agent("Arabic").process_input("حلّل المبيعات"))

    def test_help_lists_what_can_be_asked_in_the_chosen_language(self):
        self.assertIn("Analyse a dataset", make_agent().process_input("what can you do?"))
        self.assertIn("تحليل مجموعة بيانات", make_agent("Arabic").process_input("ماذا تستطيع؟"))

    def test_the_tone_templates_survive_for_the_documentation(self):
        self.assertEqual(make_agent(tone="concise").acknowledge("Ping"),
                         'Received: "Ping". See /help for commands.')


# ---------------------------------------------------------------------------
# The server assistant: confirmations, runs, reports
# ---------------------------------------------------------------------------

class ServerAssistantTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = engine_in(self.tmp.name, case=self)
        self.assistant = Assistant(ModelGateway(env={}), self.engine)
        self.session = FakeSession(make_agent())

    def say(self, text):
        self.session.add_entry("user", text)
        outcome = self.assistant.handle(text, self.session)
        self.session.add_entry("agent", outcome["text"], source=outcome.get("source"),
                               action=outcome.get("action"), result=outcome.get("result"),
                               pending=outcome.get("pending"))
        return outcome

    def test_a_sentence_starts_a_run_and_says_which(self):
        outcome = self.say("Analyse the sample sales data")
        self.assertEqual(outcome["action"], "start_run")
        run_id = outcome["result"]["run_id"]
        self.assertIn(run_id, outcome["text"])
        self.assertIn("sample sales dataset", outcome["text"])
        self.assertEqual(outcome["source"], "rules")
        runs = self.engine.list_runs(owner="local-owner")
        self.assertEqual([r["id"] for r in runs], [run_id])
        self.assertEqual(runs[0]["goal"], "Analyse the sample sales data")

    def test_a_stored_dataset_named_in_the_sentence_is_used(self):
        self.engine.store_dataset("team,quarter,sales\nA,Q1,100\nB,Q1,90\n",
                                  "quarterly_sales.csv", "local-owner")
        outcome = self.say("analyse quarterly_sales by team")
        run = self.engine.get_run(outcome["result"]["run_id"])
        self.assertEqual(run["dataset_name"], "quarterly_sales.csv")
        self.assertIn("quarterly_sales.csv", outcome["text"])

    def test_status_before_and_after_a_run(self):
        self.assertIn("no analysis yet", self.say("what's the status?")["text"])
        run_id = self.say("Analyse the sample sales data")["result"]["run_id"]
        finish(self.engine, run_id)
        outcome = self.say("is it done?")
        self.assertEqual(outcome["action"], "run_status")
        self.assertIn(run_id, outcome["text"])
        self.assertIn("waiting for approval", outcome["text"])
        self.assertIn("waiting for your approval to publish", outcome["text"])

    def test_explain_quotes_the_reports_own_headlines_verbatim(self):
        self.assertIn("no analysis yet", self.say("why did revenue move?")["text"])
        run_id = self.say("Analyse the sample sales data")["result"]["run_id"]
        self.assertIn("has not produced a report yet",
                      self.say("explain the latest report")["text"])
        finish(self.engine, run_id)
        run = self.engine.get_run(run_id)
        headlines = {s["type"]: s["headline"] for s in run["reports"] if s["headline"]}
        self.assertTrue(headlines, "the finished run has headlines to quote")

        outcome = self.say("explain the latest report")
        for headline in headlines.values():
            self.assertIn(headline, outcome["text"])
        self.assertIn("What should I do?", outcome["text"])

        only = self.say("why did revenue move?")["text"]
        self.assertIn(headlines["diagnostic"], only)
        self.assertNotIn(headlines["descriptive"], only)

    def test_deleting_needs_a_yes_in_the_next_message(self):
        agent = self.session.agent
        agent.process_input("remember coffee at 8")
        outcome = self.say("forget everything")
        self.assertEqual(outcome["action"], "confirm")
        self.assertIn("Reply “yes” to confirm", outcome["text"])
        self.assertEqual(agent.memory, {"memory_1": "coffee at 8"}, "nothing deleted yet")

        self.assertEqual(self.say("no")["text"], "Nothing was changed.")
        self.assertEqual(agent.memory, {"memory_1": "coffee at 8"})

        self.say("forget everything")
        self.assertEqual(self.say("yes")["text"], "All saved information has been removed.")
        self.assertEqual(agent.memory, {})

    def test_an_unrelated_sentence_drops_the_pending_deletion(self):
        agent = self.session.agent
        agent.process_input("remember coffee at 8")
        self.say("forget everything")
        outcome = self.say("Analyse the sample sales data")
        self.assertEqual(outcome["action"], "start_run")
        self.assertEqual(agent.memory, {"memory_1": "coffee at 8"})
        # And "yes" now means nothing: the pending request is gone.
        self.assertEqual(self.say("yes")["action"], "chat")
        self.assertEqual(agent.memory, {"memory_1": "coffee at 8"})

    def test_the_confirmation_names_the_entry_it_would_delete(self):
        self.session.agent.process_input("remember coffee at 8")
        outcome = self.say("forget memory_1")
        self.assertIn("“coffee at 8”", outcome["text"])
        self.assertEqual(outcome["action"], "confirm")

    def test_forgetting_an_unknown_key_needs_no_confirmation(self):
        outcome = self.say("forget memory_9")
        self.assertIn("No saved information found for memory_9", outcome["text"])
        self.assertNotEqual(outcome["action"], "confirm")

    def test_a_note_named_by_what_it_says_is_confirmed_then_deleted(self):
        """ADR 0027: "delete the note about X" finds the one note about X and
        asks first; it never deletes on a description alone."""
        agent = self.session.agent
        agent.process_input("remember the warehouse stocktake is on 3 March")
        agent.process_input("remember the board meets on Thursday")
        outcome = self.say("Delete the note about the warehouse stocktake, it's no longer valid")
        self.assertEqual(outcome["action"], "confirm")
        self.assertIn("“the warehouse stocktake is on 3 March”", outcome["text"])
        self.assertEqual(len(agent.memory), 2, "nothing deleted yet")
        self.say("yes")
        self.assertEqual(agent.memory, {"memory_2": "the board meets on Thursday"})

    def test_a_description_that_fits_several_notes_lists_them_and_deletes_nothing(self):
        agent = self.session.agent
        agent.process_input("remember the board meets on Thursday")
        agent.process_input("remember the board pack is due Monday")
        outcome = self.say("delete the note about the board")
        self.assertNotEqual(outcome["action"], "confirm")
        self.assertIn("memory_1: the board meets on Thursday", outcome["text"])
        self.assertIn("memory_2: the board pack is due Monday", outcome["text"])
        self.assertEqual(len(agent.memory), 2)
        self.assertIn("Nothing I remember matches “the canteen menu”",
                      self.say("forget the note about the canteen menu")["text"])

    def test_an_arabic_note_is_found_by_its_words(self):
        self.session = FakeSession(make_agent("Arabic"))
        self.session.agent.process_input("تذكر أن عدد الموظفين 42")
        outcome = self.say("امسح الملاحظة المتعلقة بعدد الموظفين، تغيرت الأرقام")
        self.assertEqual(outcome["action"], "confirm")
        self.say("نعم")
        self.assertEqual(self.session.agent.memory, {})

    def test_the_confirmation_is_in_arabic_for_an_arabic_session(self):
        self.session = FakeSession(make_agent("Arabic"))
        self.session.agent.process_input("تذكّر القهوة الساعة 8")
        self.assertIn("أجب بـ«نعم»", self.say("انسَ كل شيء")["text"])
        self.assertEqual(self.say("نعم")["text"], "تمت إزالة كل المعلومات المحفوظة.")


class ModelPathTestCase(unittest.TestCase):
    def test_exact_workspace_commands_do_not_wait_for_a_model(self):
        gateway = FakeGateway(None)
        gateway.ask = Mock(side_effect=AssertionError("exact command called a model"))
        result = Assistant(gateway, self.engine).handle("is the analysis done?", self.session)
        self.assertEqual(result["source"], "rules")
        self.assertNotEqual(result["action"], "chat")
        gateway.ask.assert_not_called()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine = engine_in(self.tmp.name, case=self)
        self.session = FakeSession(make_agent())
        memory = patch("server.assistant_availability.free_memory_bytes", return_value=8 * 1024 ** 3)
        memory.start()
        self.addCleanup(memory.stop)

    def handle(self, answer, text):
        gateway = FakeGateway(answer)
        outcome = Assistant(gateway, self.engine).handle(text, self.session)
        return outcome, gateway

    def test_the_model_decides_the_action_but_the_agent_writes_the_confirmation(self):
        outcome, gateway = self.handle(
            json.dumps({"action": "remember",
                        "arguments": {"information": "Meeting at 9"},
                        "reply": "Saved! You're all set."}),
            "can you keep in mind that we meet at 9")
        self.assertIn("Meeting at 9", self.session.agent.memory.values())
        # The model said "Saved!" — the person sees the Agent's sentence,
        # which is true by construction.
        self.assertEqual(outcome["text"], "Information saved.")
        self.assertEqual(outcome["source"], "model")
        self.assertEqual(outcome["provider"], "ollama")
        self.assertEqual(len(gateway.asked), 1)

    def test_only_a_chat_reply_shows_the_models_words(self):
        outcome, _ = self.handle(
            json.dumps({"action": "chat", "arguments": {},
                        "reply": "Ask me to analyse the sales data and I will."}),
            "hi there")
        self.assertEqual(outcome["text"], "Ask me to analyse the sales data and I will.")
        self.assertEqual(outcome["source"], "model")

    def test_structured_intent_is_optional_and_nonreasoning_budget_is_bounded(self):
        answer = json.dumps({"action": "chat", "arguments": {}, "reply": "A general inspection needs approved procedures."})
        gateway = FakeGateway(answer)
        gateway.ollama_think = False
        gateway.ask_json = Mock(return_value=answer)
        gateway.ask = Mock(side_effect=AssertionError("ordinary ask must not handle structured intent"))
        outcome = Assistant(gateway, self.engine).handle("Explain a general inspection", self.session)
        self.assertEqual(outcome["source"], "model")
        self.assertEqual(outcome["action"], "chat")
        self.assertEqual(gateway.ask_json.call_args.kwargs["max_tokens"], 600)
        self.assertEqual(gateway.ask_json.call_args.kwargs["schema"], INTENT_SCHEMA)
        gateway.ask.assert_not_called()

    def test_legacy_gateway_duck_keeps_ordinary_ask_and_reasoning_budget(self):
        gateway = FakeGateway("")
        gateway.ask = Mock(return_value=json.dumps({"action": "chat", "reply": "A useful answer."}))
        outcome = Assistant(gateway, self.engine).handle("A conceptual question", self.session)
        self.assertEqual(outcome["text"], "A useful answer.")
        self.assertEqual(gateway.ask.call_args.kwargs["max_tokens"], 900)
        self.assertNotIn("schema", gateway.ask.call_args.kwargs)

    def test_current_turn_is_sent_once_while_followup_history_is_preserved(self):
        self.session.add_entry("user", "We are discussing a centrifugal pump.")
        self.session.add_entry("agent", "Its inspection follows approved procedures.")
        question = "Which equipment did I mention?"
        self.session.add_entry("user", question)
        _, gateway = self.handle(json.dumps({"action": "chat", "reply": "A centrifugal pump."}), question)
        context = gateway.asked[0][1]
        self.assertEqual(context.count(question), 1)
        self.assertIn("user: We are discussing a centrifugal pump.", context)
        self.assertIn("agent: Its inspection follows approved procedures.", context)
        self.assertIn("Message: " + question, context)

    def test_context_separates_saved_entries_from_conversation_without_saving_turns(self):
        self.session.add_entry("user", "Discuss the exhaust fan.")
        self.session.add_entry("agent", "We can discuss its maintenance.")
        question = "Continue with this topic."
        self.session.add_entry("user", question)
        for saved in (False, True):
            with self.subTest(saved=saved):
                if saved:
                    self.session.agent.process_input("remember the inspection review is Friday")
                memories = dict(self.session.agent.memory)
                transcript = [dict(entry) for entry in self.session.transcript]
                _, gateway = self.handle(json.dumps({"action": "chat", "reply": "Useful guidance."}), question)
                context = gateway.asked[0][1]
                saved_section, recent = context.split("Recent conversation:", 1)
                self.assertIn("Saved memory:", saved_section)
                self.assertIn("memory_1: the inspection review is Friday" if saved else "Saved memory:\nnone", saved_section)
                self.assertNotIn("Discuss the exhaust fan.", saved_section)
                self.assertNotIn("memory_1:", recent)
                self.assertIn("user: Discuss the exhaust fan.", recent)
                self.assertIn("agent: We can discuss its maintenance.", recent)
                self.assertEqual(context.count(question), 1)
                self.assertEqual(self.session.agent.memory, memories)
                self.assertEqual(self.session.transcript, transcript)

    def test_model_catalog_and_schema_expose_only_the_mapped_action_names(self):
        _, gateway = self.handle(None, "Explain a general inspection")
        system = gateway.asked[0][0]
        aliases = {internal: model for model, internal in MODEL_ACTION_ALIASES.items()}
        expected = {aliases.get(action, action) for action in assistant.ACTIONS}
        for action in expected:
            self.assertIn(action + "{", system)
        for internal in MODEL_ACTION_ALIASES.values():
            self.assertNotIn(internal + "{", system)
        chat, other = INTENT_SCHEMA["oneOf"]
        exposed = {chat["properties"]["action"]["const"]} | set(other["properties"]["action"]["enum"])
        self.assertEqual(exposed, expected)

    def test_saved_memory_aliases_and_legacy_names_keep_internal_action_contracts(self):
        for store_name, search_name in (("store_saved_memory", "search_saved_memory"), ("remember", "recall")):
            with self.subTest(store=store_name, search=search_name):
                self.session = FakeSession(make_agent())
                saved, _ = self.handle(json.dumps({"action": store_name,
                    "arguments": {"information": "The shift log is reviewed on Friday"}, "reply": ""}),
                    "Save the shift review schedule")
                self.assertEqual(saved["action"], "remember")
                self.assertEqual(saved["text"], "Information saved.")
                self.assertEqual(len(self.session.agent.memory), 1)
                found, _ = self.handle(json.dumps({"action": search_name,
                    "arguments": {"query": "shift log"}, "reply": ""}), "Search saved notes about the shift log")
                self.assertEqual(found["action"], "recall")
                self.assertIn("The shift log is reviewed on Friday", found["text"])
                self.assertEqual(len(self.session.agent.memory), 1)

    def test_aliases_pass_through_existing_argument_validation(self):
        for action, arguments in (("store_saved_memory", {"information": "  "}),
                                  ("store_saved_memory", {}),
                                  ("delete_saved_memory", {"key": "all"})):
            with self.subTest(action=action):
                parsed = Assistant(FakeGateway(None), self.engine)._parse(
                    json.dumps({"action": action, "arguments": arguments, "reply": ""}), self.session)
                self.assertIsNone(parsed)
        self.assertEqual(self.session.agent.memory, {})

    def test_an_older_matching_turn_is_not_removed_from_history(self):
        question = "Which equipment did I mention?"
        self.session.add_entry("user", question)
        self.session.add_entry("agent", "You mentioned a pump.")
        _, gateway = self.handle(json.dumps({"action": "chat", "reply": "A pump."}), question)
        self.assertEqual(gateway.asked[0][1].count(question), 2)

    def test_missing_blank_or_nested_chat_reply_is_an_honest_rules_fallback(self):
        for fields in ({}, {"reply": None}, {"reply": ""}, {"reply": "  "},
                       {"reply": 5}, {"arguments": {"reply": "Not a top-level answer"}}):
            with self.subTest(fields=fields):
                outcome, _ = self.handle(json.dumps({"action": "chat", **fields}),
                                         "Suggest a pump reliability checklist")
                self.assertEqual(outcome["source"], "rules")
                self.assertNotIn("provider", outcome)
                self.assertEqual("invalid_model_output", outcome["why"])
                self.assertNotIn("Not a top-level answer", outcome["text"])

    def test_nonchat_actions_still_accept_an_empty_reply_and_use_the_agents_text(self):
        outcome, _ = self.handle(json.dumps({"action": "remember",
            "arguments": {"information": "Inspect the pump at the approved interval"}, "reply": ""}),
            "Remember the approved inspection interval")
        self.assertEqual(outcome["source"], "model")
        self.assertEqual(outcome["text"], "Information saved.")
        self.assertIn("Inspect the pump at the approved interval", self.session.agent.memory.values())

    def test_general_domain_chat_keeps_both_languages_and_no_automated_action(self):
        for language, question, answer in (
            ("English", "Suggest a pump checklist", "Use the approved inspection procedure; review leaks and maintenance history."),
            ("Arabic", "اقترح قائمة فحص للمضخة", "راجع سجل الصيانة وفق إجراءات الفحص المعتمدة؛ هذه إرشادات عامة وليست قياسات للأصل."),
        ):
            with self.subTest(language=language):
                self.session = FakeSession(make_agent(language))
                outcome, gateway = self.handle(json.dumps({"action": "chat", "arguments": {}, "reply": answer}), question)
                self.assertEqual(outcome["action"], "chat")
                self.assertEqual(outcome["text"], answer)
                self.assertEqual(self.engine.list_runs(owner="local-owner"), [])
                self.assertEqual(self.session.agent.memory, {})
                self.assertIn("Miyaar", gateway.asked[0][0])
                self.assertIn("at the TOP LEVEL", gateway.asked[0][0])

    def test_an_invalid_model_intent_reports_failure_without_executing_a_guessed_action(self):
        outcome, _ = self.handle("I think you want me to remember something.",
                                 "remember that the review is on Monday")
        self.assertEqual(outcome["source"], "rules")
        self.assertEqual(outcome["action"], "chat")
        self.assertEqual(outcome["why"], "invalid_model_output")
        self.assertEqual(self.session.agent.memory, {})

    def test_an_action_outside_the_catalogue_is_refused(self):
        outcome, _ = self.handle(
            json.dumps({"action": "drop_database", "arguments": {}, "reply": "Done."}),
            "the weather is nice")
        self.assertEqual(outcome["source"], "rules")
        self.assertEqual(outcome["action"], "chat")
        self.assertNotIn("Done.", outcome["text"])

    def test_a_bad_argument_is_refused_with_the_whole_intent(self):
        outcome, _ = self.handle(
            json.dumps({"action": "set_preference",
                        "arguments": {"key": "tone", "value": "shouty"}}),
            "the weather is nice")
        self.assertEqual(outcome["source"], "rules")
        self.assertEqual(self.session.agent.preferences["tone"], "friendly")

    def test_the_model_cannot_delete_without_the_persons_yes(self):
        self.session.agent.process_input("remember coffee at 8")
        outcome, _ = self.handle(
            json.dumps({"action": "forget", "arguments": {"key": "all"},
                        "reply": "Deleted everything."}),
            "hmm")
        self.assertEqual(outcome["action"], "confirm")
        self.assertEqual(self.session.agent.memory, {"memory_1": "coffee at 8"})
        self.assertNotIn("Deleted everything", outcome["text"])

    def test_the_model_is_shown_facts_and_settings_but_never_a_row(self):
        self.session.agent.process_input("remember the Q4 review is on Monday")
        run_id = Assistant(ModelGateway(env={}), self.engine).handle(
            "analyse the sample sales data", self.session)["result"]["run_id"]
        finish(self.engine, run_id)
        _, gateway = self.handle(json.dumps({"action": "chat", "reply": "ok"}), "hello")
        system, user = gateway.asked[0]
        self.assertIn("the Q4 review is on Monday", user)
        self.assertIn("Latest analysis", user)
        self.assertIn("descriptive:", user)
        for line in analytics.sample_dataset().splitlines()[:5]:
            self.assertNotIn(line, user, "a dataset row reached the model")
        self.assertIn("never see data rows", system)

    def test_a_model_that_returns_nothing_is_the_rules(self):
        outcome, _ = self.handle(None, "what can you do?")
        self.assertEqual(outcome["source"], "rules")
        self.assertIn("Analyse a dataset", outcome["text"])

    def test_an_unconfigured_gateway_never_gets_asked(self):
        gateway = FakeGateway("{}", configured=False)
        Assistant(gateway, self.engine).handle("hello", self.session)
        self.assertEqual(gateway.asked, [])


try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    FASTAPI_AVAILABLE = True
except ImportError:  # pragma: no cover
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "fastapi is not installed")
class AssistantApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Agentic OS", "version": "1.0.0",
            "memory_file": str(root / "memory.json"),
            "database_file": str(root / "agentic.db"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        self.client = TestClient(closing(self, create_app(config)), raise_server_exceptions=False)
        self.sid = self.client.post("/api/sessions").json()["session_id"]

    def send(self, text):
        response = self.client.post(f"/api/sessions/{self.sid}/messages",
                                    json={"text": text})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_a_sentence_starts_a_run_the_runs_list_shows(self):
        body = self.send("Analyse the sample sales data")
        reply = body["reply"]
        self.assertEqual(reply["action"], "start_run")
        self.assertEqual(reply["source"], "rules")
        run_id = reply["result"]["run_id"]
        listed = self.client.get("/api/runs").json()["runs"]
        self.assertEqual([r["id"] for r in listed], [run_id])

    def test_a_slash_command_is_marked_as_one(self):
        self.assertEqual(self.send("/help")["reply"]["source"], "command")

    def test_a_pending_confirmation_survives_between_requests(self):
        self.send("remember coffee at 8")
        self.assertEqual(self.send("forget everything")["reply"]["action"], "confirm")
        body = self.send("yes")
        self.assertEqual(body["reply"]["text"], "All saved information has been removed.")
        self.assertEqual(body["state"]["memory"], {})
        # The consumed confirmation is not lying in wait for a later "yes".
        transcript = body["state"]["transcript"]
        self.assertFalse(any("pending" in entry for entry in transcript))

    def test_the_request_is_in_the_history_whichever_path_answered(self):
        self.send("remember coffee at 8")
        self.assertIn("remember coffee at 8", self.send("/history")["reply"]["text"])

class IndirectPhrasingTestCase(unittest.TestCase):
    """Indirect and Arabic phrasings found by an independent blind set (2026-10-20)."""

    def action(self, text):
        return assistant.understand(text)["action"]

    def test_each_phrasing_family_reaches_its_action(self):
        cases = {
            "help": ["What kinds of things can I ask you?", "ما هي الأشياء اللي أقدر أطلبها منك"],
            "remember": ["could you maybe save this for later, the target is 4500 hours",
                         "خلّ في بالك إن الورشة تسكر يوم الجمعة"],
            "recall": ["show me everything you've saved", "did I tell you anything about the thresholds",
                       "شو اللي حافظه عن المشروع؟", "وش الملاحظات اللي سجلتها سابقا"],
            "forget": ["please remove that saved item about line 2", "انسَ موضوع هدف التوقف"],
            "run_status": ["any update on the analysis you started", "وين وصل التحليل؟"],
            "explain_report": ["what did the diagnostic part say about the cause",
                               "quote the descriptive summary from the latest report",
                               "وش قالت التوصيات في قسم prescriptive"],
        }
        for expected, texts in cases.items():
            for text in texts:
                with self.subTest(text=text):
                    self.assertEqual(self.action(text), expected)

    def test_stopping_the_history_is_a_setting_and_deletes_nothing(self):
        off = assistant.understand("stop recording our conversation history")
        self.assertEqual((off["action"], off["arguments"]),
                         ("set_preference", {"key": "save_history", "value": "false"}))
        on = assistant.understand("start recording our conversation history again")
        self.assertEqual(on["arguments"], {"key": "save_history", "value": "true"})
        self.assertEqual(self.action("clear the conversation history"), "clear_history")

    def test_the_new_rules_do_not_widen_into_other_actions(self):
        self.assertEqual(self.action("Remember to delete all the old files"), "remember")
        self.assertEqual(self.action("I like Arabic coffee"), "chat")
        self.assertEqual(self.action("thanks, that was useful"), "chat")
        self.assertEqual(self.action("the report was behind schedule"), "chat")


if __name__ == "__main__":
    unittest.main()
