"""Model roles in a run: Hermes, the agents, and the consultants.

Hermes is the run engine (server/runs.py). It always sequences the
stages, enforces the state machine and holds the approval gate in code:
those are guarantees, and a model is not asked to keep them. What a model
adds here is judgement in words, at three points (ADR 2026-10-21 model
roles):

- **Hermes** (AGENTIC_OS_HERMES_MODEL): plans the run from the goal and
  the roster, and before the report closes the consultation into a brief
  for the approver: what to check first, and where the consultants
  disagree.
- **Agents** (AGENTIC_OS_AGENT_MODEL, normally "ollama"): after a stage
  succeeds, its own verified findings are phrased as that agent's note.
- **Consultants** (AGENTIC_OS_CONSULTANTS, e.g. "anthropic,openai"):
  before the report, each independently reviews the verified findings and
  names the risks and questions an approver should raise.

Each value names a provider the model gateway can reach, optionally with
a model of its own ("ollama:hermes3" for Hermes while the agents use
"ollama:qwen3"); an unreachable provider is reported in /api/health and
skipped. Every model sees verified
sentences only, never a dataset row, and writes words only: a note that
introduces a figure absent from its facts is dropped, so no number in a
report comes from a model. With nothing configured (the default, and in
every test) nothing here runs and runs are exactly as before.
"""

import re
from concurrent.futures import ThreadPoolExecutor

from server.model_gateway import split_spec

MAX_FACTS = 14
MAX_NOTE_CHARS = 900

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")

HERMES_PLAN_SYSTEM = (
    "You are Hermes, the orchestrator of a governed maintenance analytics "
    "pipeline. The stages, their order and the human approval gate are fixed. "
    "From the goal and the stage list, write at most three short sentences: "
    "which stages matter most for this goal and what the reviewer should "
    "watch. Never state a number. Plain business English."
)
HERMES_BRIEF_SYSTEM = (
    "You are Hermes, the orchestrator of a governed maintenance analytics "
    "pipeline. You are given verified findings and independent consultant "
    "notes. Write at most four short sentences for the human approver: what "
    "to check first before approving, and where the consultants agree or "
    "disagree. Use only numbers that appear in the findings. Do not add "
    "causes or predictions. Plain business English."
)
CONSULTANT_SYSTEM = (
    "You are an independent senior reliability and analytics consultant "
    "reviewing verified findings from a maintenance analysis. Name at most "
    "three risks, gaps or questions the approver should raise before acting. "
    "Use only numbers that appear in the findings; never invent figures, "
    "causes or predictions. Short, plain business English."
)
ARABIC = (" Write in formal Arabic, copying every number exactly as written "
          "in the facts with the same digits.")

TITLES = {
    "en": {"heading": "## Orchestrator and consultant notes",
           "caution": "*Written by language models from the verified findings "
                      "above. They add judgement, not figures; every number in "
                      "this report is calculated.*",
           "hermes": "**Hermes (orchestrator, {provider}):**",
           "consultant": "**Consultant ({provider}):**"},
    "ar": {"heading": "## ملاحظات المنسّق والمستشارين",
           "caution": "*كتبتها نماذج لغوية من النتائج المتحقق منها أعلاه. "
                      "تضيف رأياً لا أرقاماً؛ وكل رقم في هذا التقرير محسوب.*",
           "hermes": "**هيرميس (المنسّق، {provider}):**",
           "consultant": "**مستشار ({provider}):**"},
}


def _numbers(text):
    return {match.replace(",", "") for match in NUMBER.findall(text or "")}


def grounded(text, facts):
    """The note, trimmed, if every number in it appears in the facts;
    otherwise None. A model may phrase a figure, never produce one."""
    if not text:
        return None
    text = text.strip()[:MAX_NOTE_CHARS]
    allowed = set()
    for fact in facts:
        allowed |= _numbers(fact)
    return text if _numbers(text) <= allowed else None


def claim_texts(result):
    return [claim["text"] for claim in (result or {}).get("claims", [])
            if claim.get("text")]


class ModelRoles:
    """Which reachable provider plays which role. Absent roles are None."""

    def __init__(self, gateway, env):
        reachable = {entry["provider"] for entry in gateway.providers()
                     if entry["provider"] != "deterministic"}
        self.gateway = gateway
        self.problems = []

        # A role's own variable wins; otherwise the task map
        # (AGENTIC_OS_TASK_MODELS) on the gateway names it.
        task_map = getattr(gateway, "task_map", {}) or {}

        def checked(spec, label):
            """The spec, normalised, if its provider is reachable."""
            name, model = split_spec(spec)
            if not name:
                return None
            if name not in reachable:
                self.problems.append(f"{label}{name} is not a configured provider; skipped.")
                return None
            return f"{name}:{model}" if model else name

        def pick(variable, task):
            if not (env.get(variable) or "").strip():
                return task_map[task][0] if task_map.get(task) else None
            return checked(env[variable], f"{variable}=")

        self.hermes = pick("AGENTIC_OS_HERMES_MODEL", "hermes")
        self.agents = pick("AGENTIC_OS_AGENT_MODEL", "agents")
        self.consultants = []
        consultants = env.get("AGENTIC_OS_CONSULTANTS")
        if not consultants and task_map.get("consultants"):
            consultants = ",".join(task_map["consultants"])
        for spec in (consultants or "").split(","):
            spec = checked(spec, "AGENTIC_OS_CONSULTANTS: ")
            if spec and spec not in self.consultants:
                self.consultants.append(spec)

    @property
    def active(self):
        return bool(self.hermes or self.agents or self.consultants)

    def status(self):
        return {"hermes": self.hermes or "rules", "agents": self.agents,
                "consultants": list(self.consultants), "problems": list(self.problems)}

    def model_map(self):
        """Every AI task and the provider that serves it now: the whole
        mapping in one place for /api/health. "built-in" means the
        deterministic template or rules answer, with no model."""
        gateway = self.gateway
        default = gateway.status()["provider"] if hasattr(gateway, "status") else "deterministic"
        task = getattr(gateway, "task_provider", lambda name: None)

        def name(provider):
            return "built-in" if provider in (None, "deterministic") else provider

        return {
            "narration": name(task("narration") or default),
            "chat": name(task("chat") or default),
            "hermes": self.hermes or "built-in",
            "agents": self.agents or "built-in",
            "consultants": list(self.consultants) or ["none"],
            "problems": list(getattr(gateway, "task_problems", [])) + list(self.problems),
        }

    def _ask(self, system, user, provider, language, facts):
        if language == "ar":
            system += ARABIC
        return grounded(self.gateway.ask(system, user, provider=provider), facts)

    def agent_note(self, goal, role, result, language="en"):
        """The agent's own findings, phrased by the agents' model."""
        facts = claim_texts(result)[:MAX_FACTS]
        if not self.agents or not facts:
            return None
        narration = self.gateway.narrate(goal, facts, provider=self.agents,
                                         language=language)
        if narration.get("source") != "model":
            return None
        text = grounded(narration["text"], facts)
        return {"text": text, "provider": self.agents, "role": role} if text else None

    def plan(self, goal, roster, language="en"):
        if not self.hermes:
            return None
        user = "Goal: " + goal + "\nStages, in their fixed order:\n- " + "\n- ".join(roster)
        text = self._ask(HERMES_PLAN_SYSTEM, user, self.hermes, language, [goal])
        return {"text": text, "provider": self.hermes} if text else None

    def consult(self, goal, facts, language="en"):
        """Consultants in parallel, then Hermes' brief. Returns None when
        neither role is configured or nobody answered."""
        facts = facts[:MAX_FACTS]
        if not facts or not (self.consultants or self.hermes):
            return None
        user = "Goal: " + goal + "\nVerified findings:\n- " + "\n- ".join(facts)
        notes = []
        if self.consultants:
            with ThreadPoolExecutor(max_workers=len(self.consultants)) as pool:
                answers = list(pool.map(
                    lambda name: (name, self._ask(CONSULTANT_SYSTEM, user, name,
                                                  language, facts)),
                    self.consultants))
            notes = [{"provider": name, "text": text} for name, text in answers if text]
        brief = None
        if self.hermes:
            consulted = "".join(f"\nConsultant ({n['provider']}): {n['text']}" for n in notes)
            text = self._ask(HERMES_BRIEF_SYSTEM, user + consulted, self.hermes,
                             language, facts)
            brief = {"provider": self.hermes, "text": text} if text else None
        if not notes and brief is None:
            return None
        return {"hermes": brief, "consultants": notes}


def report_section(orchestration, language="en"):
    """Markdown lines for the report, or [] when nothing was written."""
    if not orchestration:
        return []
    text = TITLES["ar" if language == "ar" else "en"]
    lines = ["", text["heading"], text["caution"]]
    if orchestration.get("hermes"):
        brief = orchestration["hermes"]
        lines += ["", text["hermes"].format(provider=brief["provider"]), brief["text"]]
    for note in orchestration.get("consultants") or []:
        lines += ["", text["consultant"].format(provider=note["provider"]), note["text"]]
    return lines
