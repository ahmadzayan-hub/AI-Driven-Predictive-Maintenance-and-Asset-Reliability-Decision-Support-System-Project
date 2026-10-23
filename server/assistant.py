"""The conversational assistant: understand, confirm, act.

`assistant.py` at the project root knows what a sentence means without
a model and runs the actions that need only the Agent. This module adds
the two things that need the server: a language model, when one is
configured, for sentences the rules do not catch; and the actions that
need the run engine — start an analysis, say how it is going, quote what
its report found.

What the model may decide, and what it may not (ADR 0019):

- It may decide **which action** a sentence asks for, and its arguments,
  from the same small catalogue the rules use. An action outside that
  catalogue is refused and the rules answer instead.
- It may **phrase a chat reply** — and that is the only text of its
  making a person ever sees. Every action's confirmation is the Agent's
  own deterministic sentence, so the assistant cannot say "saved" about
  a save that failed.
- It never sees a dataset row. It gets memory entries, preferences, the
  last few turns, and the *headlines* of the latest report — sentences
  the pipeline already verified. It never produces a number, because
  nothing it writes reaches a report.
- It never deletes anything. Destructive actions are confirmed in the
  next message, by rule, whoever understood the sentence.

With no provider configured — the default, and always in CI — the rules
do everything, and the reply says so (`source: "rules"`).
"""

import json
import re
from contextvars import ContextVar
from datetime import datetime, timezone

from assistant import (ACTIONS, DESTRUCTIVE, PREFERENCE_KEYS, RUN_STATES,
                       SECTION_QUESTIONS, arguments_valid, confirmation_prompt,
                       execute_local, fallback, intent, is_no, is_yes, reply,
                       understand)
from server import agent_learning, knowledge, model_privacy, quota, deadline, schema
from server.tools import ToolBox

# Enough passages that the answer is usually among them, few enough that a
# large collection costs a few hundred tokens rather than being injected
# whole. The retrieval layer is right first about eight times in ten and
# within its top three more often than that (ADR 0057), so the reader is
# given the shortlist, not a single guess.
KNOWLEDGE_HITS = 3
# A quoted passage is trimmed on a line boundary: a table cut mid-row is
# harder to read than one that stops early and says so.
KNOWLEDGE_EXCERPT_CHARS = 700

MAX_MEMORY_IN_CONTEXT = 20
MAX_TURNS_IN_CONTEXT = 6
MAX_REPLY_CHARS = 600
# Model tool names distinguish durable storage from ordinary conversation.
# Internal actions, user commands and response action names stay compatible.
MODEL_ACTION_ALIASES = {"search_saved_memory": "recall", "store_saved_memory": "remember"}
_MODEL_ACTION_NAMES = {internal: model for model, internal in MODEL_ACTION_ALIASES.items()}
_MODEL_ARGUMENT_HINTS = {
    ("remember", "category"): "category:general|profile|work|projects|preferences",
    ("recall", "query"): "query:string|null",
    ("forget", "key"): "key:memory_N|all",
    ("set_preference", "key"): "key:tone|language|user_name|save_history",
    ("start_run", "dataset"): "dataset:stored name|sample",
    ("explain_report", "section"): "section:descriptive|diagnostic|experiment|predictive|prescriptive|all",
}
MODEL_ACTION_CATALOG = "; ".join(
    _MODEL_ACTION_NAMES.get(action, action) + "{" +
    ",".join(_MODEL_ARGUMENT_HINTS.get((action, argument), argument) for argument in arguments) + "}"
    for action, arguments in ACTIONS.items()
)
INTENT_SCHEMA = {
    "oneOf": [
        {"type": "object", "properties": {
            "action": {"const": "chat"},
            "arguments": {"type": "object", "properties": {}, "additionalProperties": False},
            "reply": {"type": "string", "minLength": 1}},
         "required": ["action", "arguments", "reply"], "additionalProperties": False},
        {"type": "object", "properties": {
            "action": {"type": "string", "enum": sorted(
                _MODEL_ACTION_NAMES.get(action, action) for action in ACTIONS if action != "chat")},
            "arguments": {"type": "object"},
            "reply": {"const": ""}},
         "required": ["action", "arguments", "reply"], "additionalProperties": False},
    ]
}
# Local reasoning models think before they answer; the JSON must not be
# what gets cut off.
LOCAL_TOKENS = 900
NON_REASONING_LOCAL_TOKENS = 600
HOSTED_TOKENS = 400

SYSTEM_PROMPT = (
    "You are Miyaar (معيار), Asset Reliability's governed assistant. Return ONLY "
    "one JSON object: {\"action\":\"name\",\"arguments\":{},\"reply\":\"text\"}.\n"
    "Actions (only these arguments): " + MODEL_ACTION_CATALOG + ".\n"
    "search_saved_memory searches Saved memory entries. "
    "Answer conversation follow-ups from Recent conversation using chat. "
    "Conceptual maintenance/checklists use chat: answer the specified question "
    "directly and briefly; do not ask whether to give the checklist already requested. "
    "Give useful general guidance with a NONEMPTY reply at the TOP LEVEL, never "
    "inside arguments. Keep the named equipment type. Use help ONLY for an "
    "explicit question about app capabilities; start_run ONLY to analyse data.\n"
    "You never see data rows. Never invent measurements, findings, diagnoses, "
    "operating limits, predictions or savings. General guidance is not a measured "
    "asset assessment. Inspections follow approved site/manufacturer procedures "
    "and safe isolation by qualified personnel.\n"
    "The system executes actions, confirms deletions, and quotes reports for "
    "run_status/explain_report. Leave reply empty for non-chat actions; never "
    "claim an action already happened. Answer in {language}, at most two short "
    "sentences and 600 characters; escape newlines inside JSON strings."
)


def _excerpt(text, limit=KNOWLEDGE_EXCERPT_CHARS):
    """The head of a passage, cut on a line boundary, marked when shortened."""
    body = text.strip()
    if len(body) <= limit:
        return body
    cut = body[:limit]
    edge = cut.rfind(chr(10))
    if edge > limit // 2:
        cut = cut[:edge]
    return cut.rstrip() + chr(10) + "…"


def _measured_at(stamp):
    """"20 Oct 2026 19:52 UTC". An ISO timestamp in a reply reads as a phone
    number to the privacy guard, so the month is written out."""
    try:
        moment = datetime.fromisoformat(stamp).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return "unknown time"
    return moment.strftime("%d %b %Y %H:%M UTC")


def reference_turn(entry):
    """Older runtimes embedded reference replies inside a composite turn.

    They carry no durable authorization grant. Keep them out of model context
    and ordinary transcript exports; current references are retrieved live.
    """
    if not isinstance(entry, dict):
        return False
    if entry.get("action") in ("search_knowledge", "rmd_evidence") or entry.get("tool") in ("search_knowledge", "rmd_evidence"):
        return True
    return any(reference_turn(step) for step in entry.get("steps", []) if isinstance(step, dict))


def redact_reference_turns(entries, language="en"):
    notice = ("افتح عرض المعرفة المصرح به للاطلاع على المرجع الحالي."
              if language == "ar" else
              "Open the authorized knowledge view to retrieve this reference again.")
    return [({key: value for key, value in entry.items()
              if key in ("id", "role", "time", "action")} | {"text": notice, "reference_redacted": True})
            if reference_turn(entry) else entry for entry in entries]


class Assistant:
    def __init__(self, gateway, engine, runtime=None, runtime_name=None, identity_mode="local", env=None):
        self.gateway = gateway
        self.engine = engine
        # Optional (ADR 0021): a loop that may call several tools for one
        # sentence. It gets the sentences the rules cannot place, and
        # nothing the rules can — one exact action stays one exact action.
        self.runtime = runtime
        self.runtime_name = runtime_name
        self.identity_mode = identity_mode
        self.env = env
        self._requester = ContextVar("assistant_requester", default=None)
        # The runtime's wall-clock limit (G10): AGENTIC_OS_RUNTIME_TIMEOUT,
        # seconds, default 60.
        self.runtime_timeout = deadline.seconds_from_env("AGENTIC_OS_RUNTIME_TIMEOUT",
                                                         deadline.DEFAULT_RUNTIME_SECONDS)


    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def handle(self, text, session, principal=None):
        # The real requester is distinct from a session's creator: an admin
        # viewing another conversation must not inherit its collection grants.
        token = self._requester.set(principal)
        try:
            return self._handle(text, session)
        finally:
            self._requester.reset(token)

    def _handle(self, text, session):
        """Answer one message. Returns a dict for the transcript entry:
        text, source, provider, action, result, pending."""
        agent = session.agent
        language = agent.language()

        pending = self._take_pending(session)
        if pending is not None:
            if is_yes(text):
                return self._execute(pending["action"], pending["arguments"],
                                     session, text, source="rules")
            if is_no(text):
                return {"text": reply(language, "cancelled"), "source": "rules",
                        "action": "cancel"}
            # Anything else is a new request; the earlier one is dropped
            # rather than executed on the strength of an unrelated sentence.

        if self.runtime is not None and understand(text)["action"] == "chat":
            outcome = self._via_runtime(text, session)
            if outcome is not None:
                return outcome
            # The runtime declined: the model-or-rules path answers, as
            # if no runtime were configured.

        understood = self.understand(text, session)
        action, arguments = understood["action"], understood["arguments"]
        if action in DESTRUCTIVE:
            prompt = confirmation_prompt(action, arguments, agent)
            if prompt is not None:
                return {"text": prompt, "source": understood["source"],
                        "provider": understood.get("provider"),
                        "action": "confirm",
                        "pending": {"action": action, "arguments": arguments}}
        outcome = self._execute(action, arguments, session, text,
                                source=understood["source"],
                                provider=understood.get("provider"),
                                model_reply=understood.get("reply"))
        if understood.get("why"):
            outcome["why"] = understood["why"]
        return outcome

    # ------------------------------------------------------------------
    # Understanding
    # ------------------------------------------------------------------
    def understand(self, text, session):
        """Model first when one is configured, rules otherwise — and rules
        whenever the model's answer is not a valid intent."""
        # Only unambiguous read-only shortcuts skip the model. Broad rules
        # such as "explain" still need understanding for open conversation.
        shortcuts = {"help", "what can you do", "what can you do?",
                     "is the analysis done?", "analysis status",
                     "مساعدة", "ما الذي يمكنك فعله؟", "ما حالة التحليل؟"}
        if text.strip().casefold() in shortcuts:
            known = understand(text)
            if known["action"] in ("help", "run_status"):
                return known
        status = self.gateway.status()
        if not status.get("configured"):
            return understand(text)
        privacy_reason = self._model_privacy_reason(session, text)
        if privacy_reason:
            outcome = understand(text)
            outcome["why"] = privacy_reason
            return outcome
        ask = getattr(self.gateway, "ask_json", None)
        structured = callable(ask)
        if not structured:
            ask = self.gateway.ask
        local_tokens = (NON_REASONING_LOCAL_TOKENS
                        if getattr(self.gateway, "ollama_think", None) is False
                        else LOCAL_TOKENS)
        options = {"max_tokens": local_tokens if status.get("provider") == "ollama"
                   else HOSTED_TOKENS}
        if structured:
            options["schema"] = INTENT_SCHEMA
        raw = ask(
            SYSTEM_PROMPT.replace("{language}",
                                  "Arabic" if session.agent.language() == "ar"
                                  else "English"),
            self._context(session, current_message=text) + "\nMessage: " + text,
            **options,
        )
        parsed = self._parse(raw, session)
        if parsed is None:
            fallback = understand(text)
            fallback["why"] = ("the model's answer was not a valid intent; "
                               "the rules decided instead")
            return fallback
        parsed["provider"] = status.get("provider")
        return parsed

    def _model_privacy_reason(self, session, text=""):
        """Keep detected personal report labels out of every model handoff.

        A quoted report in conversation history remains private even after
        a different run becomes the latest one. The rules still quote the
        original report directly to its authorized reader.
        """
        latest = self._latest_run(session.owner)
        run_ids = {latest["id"]} if latest else set()
        for entry in session.transcript:
            result = entry.get("result")
            if isinstance(result, dict) and result.get("run_id"):
                run_ids.add(result["run_id"])
        if any(model_privacy.run_blocks_model(self.engine.store, run_id)
               for run_id in run_ids):
            return model_privacy.notice(session.agent.language())
        if model_privacy.blocks_model(
                texts=[self._context(session, current_message=text), text]):
            return model_privacy.notice(session.agent.language())
        return None

    def _context(self, session, current_message=None):
        """What the model is told. Verified sentences and settings only —
        the dataset is not here, and nothing here is a row of it."""
        agent = session.agent
        lines = ["Context:"]
        memory = agent.memory_entries()[:MAX_MEMORY_IN_CONTEXT]
        lines.append("Saved memory:")
        if memory:
            lines.extend(f"- {e['key']}: {e['text'][:200]}" for e in memory)
        else:
            lines.append("none")
        prefs = {k: agent.preferences.get(k) for k in PREFERENCE_KEYS
                 if agent.preferences.get(k) is not None}
        lines.append("Preferences: " + json.dumps(prefs, ensure_ascii=False))
        datasets = self.engine.store.list_datasets(session.owner)[:10]
        if datasets:
            lines.append("Stored datasets: " + ", ".join(d["name"] for d in datasets))
        latest = self._latest_run(session.owner)
        if latest:
            lines.append(f"Latest analysis {latest['id']} ({latest['state']}): "
                         f"{latest['goal']} — dataset {latest['dataset_name']}")
            for section in latest.get("reports", []):
                if section.get("headline"):
                    lines.append(f"  {section['type']}: {section['headline']}")
        turns = [e for e in session.transcript if e.get("role") in ("user", "agent")
                 and not reference_turn(e)]
        if (current_message is not None and turns and turns[-1].get("role") == "user"
                and turns[-1].get("text") == current_message):
            # The API appends the current turn before asking. It is sent
            # below as Message, so retain history without duplicating it.
            turns = turns[:-1]
        lines.append("Recent conversation:")
        for entry in turns[-MAX_TURNS_IN_CONTEXT:]:
            lines.append(f"{entry['role']}: {str(entry.get('text', ''))[:300]}")
        return "\n".join(lines)

    def _parse(self, raw, session):
        """A model's text → a validated intent, or None."""
        if not isinstance(raw, str):
            return None
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except ValueError:
            return None
        if not isinstance(data, dict):
            return None
        # The shape the model was told to answer in is checked here, not
        # trusted (assessment G5): a hosted JSON mode only promises an
        # object, and a local model can still drift from `format`. The
        # check runs on the normalised answer so the contracts older
        # models were given still hold: an internal action name, a
        # missing `arguments`, and a reply beside a non-chat action (which
        # is discarded, never shown as if the action had happened).
        if not schema.valid(INTENT_SCHEMA, self._normalised(data)):
            return None
        action = str(data.get("action") or "").strip()
        action = MODEL_ACTION_ALIASES.get(action, action)
        if action not in ACTIONS:
            return None
        allowed = ACTIONS[action]
        given = data.get("arguments") if isinstance(data.get("arguments"), dict) else {}
        arguments = {k: given[k] for k in allowed if k in given}
        text = data.get("reply")
        text = text.strip()[:MAX_REPLY_CHARS] if isinstance(text, str) else None
        # A parsed chat intent without its own answer would execute the
        # deterministic fallback while falsely labelling that text a model
        # response. Reject the entire intent and disclose the rules fallback.
        if action == "chat" and not text:
            return None
        if not self._arguments_valid(action, arguments, session):
            return None
        return intent(action, arguments, text, source="model")

    @staticmethod
    def _normalised(data):
        action = str(data.get("action") or "").strip()
        internal = MODEL_ACTION_ALIASES.get(action, action)
        shaped = {"action": _MODEL_ACTION_NAMES.get(internal, internal),
                  "arguments": data.get("arguments") if "arguments" in data else {},
                  "reply": data.get("reply", "")}
        if shaped["action"] != "chat":
            shaped["reply"] = ""
        elif "arguments" not in data or shaped["arguments"] == {}:
            shaped["arguments"] = {}
        return shaped

    @staticmethod
    def _arguments_valid(action, arguments, session):
        return arguments_valid(action, arguments)

    # ------------------------------------------------------------------
    # An agent runtime (ADR 0021): several tools for one sentence
    # ------------------------------------------------------------------
    def _via_runtime(self, text, session):
        """Hand the sentence to the configured runtime with the tool box.

        What comes back on screen is every tool's own text, verbatim and
        in order — the same sentences the rules path would have produced
        — and then the runtime's closing line, which is the one piece of
        text of its making, labelled as such. If the runtime raises, the
        rules answer, the transcript says why, and whatever tools it did
        call before failing are still on the record: those happened.
        A runtime that returns None having called nothing has declined,
        and the caller answers the sentence the ordinary way.
        """
        agent = session.agent
        privacy_reason = self._model_privacy_reason(session, text)
        if privacy_reason:
            outcome = self._execute("chat", {}, session, text, source="rules")
            outcome["why"] = privacy_reason
            return outcome
        tools = ToolBox(self, session)
        context = {"language": agent.language(), "notes": self._context(session),
                   "thread_id": getattr(session, "id", None),
                   "ask": self.gateway.ask,
                   "ask_json": getattr(self.gateway, "ask_json", None)}
        try:
            # A wall-clock limit (assessment G10): a runtime that hangs is
            # abandoned on its thread and the rules answer instead.
            closing = deadline.call_with_deadline(
                self.runtime.run, self.runtime_timeout, text, tools, context)
        except deadline.Timeout:
            outcome = self._execute("chat", {}, session, text, source="rules")
            outcome["why"] = (f"the agent runtime “{self.runtime_name}” did not answer "
                              f"within {self.runtime_timeout:g} s and was abandoned; "
                              "the rules answered instead")
            if tools.steps:
                outcome["steps"] = tools.steps
            return outcome
        except Exception as error:
            outcome = self._execute("chat", {}, session, text, source="rules")
            outcome["why"] = (f"the agent runtime “{self.runtime_name}” failed "
                              f"({type(error).__name__}: {error}); the rules "
                              "answered instead")
            if tools.steps:
                outcome["steps"] = tools.steps
            return outcome
        if closing is None and not tools.steps:
            return None
        closing = str(closing or "").strip()[:MAX_REPLY_CHARS]
        parts = [step["text"] for step in tools.steps if step["text"]]
        if closing:
            parts.append(closing)
        return {"source": "runtime", "provider": self.runtime_name,
                "action": "runtime", "steps": tools.steps,
                "result": tools.last_result,
                "text": "\n\n".join(parts) or fallback(agent, text)}

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def _execute(self, action, arguments, session, text, source="rules",
                 provider=None, model_reply=None):
        agent = session.agent
        language = agent.language()
        outcome = {"source": source, "provider": provider, "action": action,
                   "result": None}
        if action == "start_run":
            outcome.update(self._start_run(arguments, session, text))
        elif action == "run_status":
            outcome.update(self._run_status(session, arguments))
        elif action == "explain_report":
            outcome.update(self._explain(arguments, session))
        elif action == "search_knowledge":
            outcome.update(self._search_knowledge(arguments, text, language, session,
                                                 for_model=source == "runtime"))
        elif action == "agent_scorecard":
            outcome.update(self._agent_scorecard(arguments, language))
        else:
            outcome["text"] = execute_local(action, arguments, agent, text,
                                            model_reply=model_reply)
        if outcome.get("provider") is None:
            outcome.pop("provider", None)
        return outcome

    def _agent_scorecard(self, arguments, language):
        """Read the agents' latest measurement: recall per suite, with the
        holdout first. It reads; it never measures into the ledger, and the
        held-out sentences are not in what it returns
        (docs/adr/2026-10-20-agent-measurement-loop.md)."""
        card = agent_learning.scorecard(str(arguments.get("suite") or "").strip() or None)
        if card is None:
            return {"text": reply(language, "scorecard_none"), "result": None}

        def pct(value):
            return "-" if value is None else f"{value:.0%}"

        rows = "\n".join(
            f"{row['suite']}: holdout {pct(row['holdout'])} "
            f"(floor {pct(row['holdout_floor'])}), dev {pct(row['dev'])}"
            for row in card["rows"])
        notes = ""
        if card["findings"]:
            notes = "\n" + ", ".join(
                f"{f['kind'].replace('_', ' ')}: {f['suite']} {f['split']}"
                for f in card["findings"])
        return {"text": reply(language, "scorecard", when=_measured_at(card["at"]),
                              rows=rows, notes=notes),
                "result": card}

    def _search_knowledge(self, arguments, text, language, session=None, *, for_model=False):
        """Quote the passages that answer a question, with their citations.

        The assistant quotes; it does not paraphrase, and it does not
        answer from memory when the question is about indexed material.
        Only the best few passages are returned, so a 100 KB collection
        costs a few hundred tokens rather than being injected whole.

        What comes back is reference text. It is quoted to the reader and
        it never decides what the system does - the same rule this
        repository applies to dataset contents and to fetched web pages.
        """
        query = str(arguments.get("query") or "").strip() or text.strip()
        collection = str(arguments.get("collection") or "").strip() or None
        from server.auth import LOCAL_PRINCIPAL
        local = self is None or getattr(self, "identity_mode", "local") == "local"
        principal = self._requester.get() if self is not None else None
        if principal is None and local:
            principal = LOCAL_PRINCIPAL
        database = getattr(getattr(self, "engine", None), "store", None)
        store = knowledge.load(env=getattr(self, "env", None)).for_principal(principal, database, local=local,
                                               for_model=for_model)
        if not store:
            return {"text": reply(language, "knowledge_empty"), "result": None}
        hits = store.search(query, collection=collection, limit=KNOWLEDGE_HITS)
        if not hits:
            return {"text": reply(language, "knowledge_none", query=query),
                    "result": None}
        if self is not None and any(
                not (store.collections[hit.passage.collection].metadata.get("data_classification") == "public"
                     and store.collections[hit.passage.collection].metadata.get("visibility") == "public")
                for hit in hits):
            # Do not persist private excerpts in a general transcript that can
            # outlive membership. The scoped evidence view retrieves them live.
            notice = ("تتوفر مراجع مصرح بها. افتح عرض المعرفة للاطلاع على النص والمصدر الحاليين."
                      if language == "ar" else
                      "Authorized references are available. Open the knowledge view to inspect their current text and sources.")
            return {"text": notice, "result": None}
        blank, newline = chr(10) * 2, chr(10)
        passages = blank.join(
            hit.citation + newline + _excerpt(hit.passage.text)
            for hit in hits)
        names = sorted({hit.passage.collection for hit in hits})
        return {"text": reply(language, "knowledge_found",
                              collection=", ".join(names), passages=passages),
                "result": {"query": query,
                           "results": [dict(hit.passage.as_dict(score=hit.score),
                                            matched=list(hit.matched))
                                       for hit in hits]}}

    def _start_run(self, arguments, session, text):
        agent = session.agent
        language = agent.language()
        goal = str(arguments.get("goal") or "").strip() or text.strip()
        dataset_id, dataset_name = self._resolve_dataset(
            arguments.get("dataset"), text, session.owner)
        try:
            # The report is written in the language the person is using.
            run = self.engine.create_run(goal, owner=session.owner,
                                         dataset_id=dataset_id,
                                         language="ar" if language == "ar" else "en")
        except quota.QuotaExceeded as error:
            return {"text": error.message, "result": None}
        shown = dataset_name or reply(language, "dataset_sample")
        return {"text": reply(language, "run_started", run_id=run["id"],
                              dataset=shown, goal=goal),
                "result": {"run_id": run["id"]}}

    def _resolve_dataset(self, named, text, owner):
        """A stored dataset the person named, else the sample data."""
        candidates = self.engine.store.list_datasets(owner)
        wanted = str(named or "").strip().lower()
        haystack = text.lower()
        if wanted == "sample":
            return None, None
        for dataset in candidates:
            name = str(dataset["name"]).lower()
            stem = name.rsplit(".", 1)[0]
            if wanted and (wanted == name or wanted == stem):
                return dataset["id"], dataset["name"]
            if stem and len(stem) >= 3 and stem in haystack:
                return dataset["id"], dataset["name"]
        return None, None

    def _latest_run(self, owner):
        runs = self.engine.list_runs(owner=owner)
        # Private RMD reports use live authorized context in the evidence panel,
        # never the ordinary model/runtime conversation or its retained history.
        runs = [run for run in runs if not self.engine.store._exec(
            "SELECT id FROM rmd_runs WHERE id = ?", (run["id"],))]
        if not runs:
            return None
        return self.engine.get_run(runs[0]["id"])

    def _selected_run(self, session, arguments):
        """Honor an explicit report, never fall back to another owner's/latest.

        Private RMD evidence belongs to the ephemeral ACL-aware panel, not a
        saved ordinary transcript, even for an otherwise authorized reader.
        """
        run_id = arguments.get("run_id")
        principal = self._requester.get()
        if principal is None and self.identity_mode != "local":
            return None
        if principal is not None and not principal.can("read"):
            return None
        if not run_id:
            # An inspected session is not an authorization grant.
            if principal is not None and principal.subject != session.owner and not principal.can("admin"):
                return None
            return self._latest_run(session.owner)
        if self.engine.store._exec("SELECT id FROM rmd_runs WHERE id = ?", (run_id,)):
            return None
        try:
            owner = self.engine.owner_of(run_id)
            requester = principal.subject if principal is not None else session.owner
            if owner != requester and not (principal is not None and principal.can("admin")):
                return None
            return self.engine.get_run(run_id)
        except KeyError:
            return None

    def _run_status(self, session, arguments=None):
        language = session.agent.language()
        run = self._selected_run(session, arguments or {})
        if run is None:
            return {"text": reply(language, "no_runs"), "result": None}
        done = sum(1 for t in run["tasks"] if t["state"] == "succeeded")
        pending = any(a["state"] == "pending" for a in run["approvals"])
        state = RUN_STATES.get(language, RUN_STATES["en"]).get(
            run["state"], run["state"].replace("_", " "))
        return {"text": reply(language, "run_status", run_id=run["id"],
                              goal=run["goal"], state=state, done=done,
                              total=len(run["tasks"]),
                              approval=reply(language, "run_status_approval")
                              if pending else ""),
                "result": {"run_id": run["id"]}}

    def _explain(self, arguments, session):
        """Quote the report's own headlines. The model is not asked to
        rephrase them: a paraphrase of a verified sentence is no longer a
        verified sentence."""
        language = session.agent.language()
        run = self._selected_run(session, arguments or {})
        if run is None:
            return {"text": reply(language, "no_runs"), "result": None}
        sections = [s for s in run.get("reports", []) if s.get("headline")]
        if not sections:
            state = RUN_STATES.get(language, RUN_STATES["en"]).get(
                run["state"], run["state"].replace("_", " "))
            return {"text": reply(language, "no_report_yet", run_id=run["id"],
                                  state=state),
                    "result": {"run_id": run["id"]}}
        wanted = arguments.get("section") or "all"
        questions = SECTION_QUESTIONS.get(language, SECTION_QUESTIONS["en"])
        chosen = [s for s in sections if wanted == "all" or s["type"] == wanted]
        if not chosen:
            chosen = sections
        lines = [reply(language, "report_intro", run_id=run["id"], goal=run["goal"])]
        for section in chosen:
            question = questions.get(section["type"], section.get("question", ""))
            lines.append(f"• {question} {section['headline']}")
        lines.append(reply(language, "report_outro"))
        return {"text": "\n".join(lines), "result": {"run_id": run["id"]}}

    # ------------------------------------------------------------------
    # Confirmations live on the transcript, so they survive a restart and
    # a change of server instance.
    # ------------------------------------------------------------------
    @staticmethod
    def _take_pending(session):
        for entry in reversed(session.transcript):
            if entry.get("role") != "agent":
                continue
            pending = entry.pop("pending", None)
            return pending if isinstance(pending, dict) else None
        return None
