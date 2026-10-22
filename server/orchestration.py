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
report comes from a model.

A role with no model is played by the **built-in** writer (ADR 2026-10-22
built-in roles): rules that phrase the same verified findings and raise
the standard questions, so every report carries the section whether or
not a model is reachable. AGENTIC_OS_BUILT_IN_ROLES=0 switches that off,
and then with nothing configured (as in most tests) nothing here runs.
"""

import re
from concurrent.futures import ThreadPoolExecutor

from server.model_gateway import split_spec
from server.model_privacy import blocks_model

MAX_FACTS = 14
MAX_NOTE_CHARS = 900
BUILT_IN = "built-in"

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
           "caution_built_in": "*Written by the platform's built-in rules from the "
                               "verified findings above, with no language model. "
                               "They add questions, not figures; every number in "
                               "this report is calculated.*",
           "hermes": "**Hermes (orchestrator, {provider}):**",
           "consultant": "**Consultant ({provider}):**"},
    "ar": {"heading": "## ملاحظات المنسّق والمستشارين",
           "caution": "*كتبتها نماذج لغوية من النتائج المتحقق منها أعلاه. "
                      "تضيف رأياً لا أرقاماً؛ وكل رقم في هذا التقرير محسوب.*",
           "caution_built_in": "*كتبتها قواعد المنصة المدمجة من النتائج المتحقق منها "
                               "أعلاه، دون أي نموذج لغوي. تضيف أسئلة لا أرقاماً؛ "
                               "وكل رقم في هذا التقرير محسوب.*",
           "hermes": "**هيرميس (المنسّق، {provider}):**",
           "consultant": "**مستشار ({provider}):**"},
}

# The built-in writers. Each sentence is fixed text in both languages and
# carries no digit of its own, so grounded() can only ever pass it; the
# only figures are the quoted findings, which are verified already.
WATCH_WORDS = ("quality", "privacy", "clean", "valid", "predict", "risk",
               "الجودة", "الخصوصية", "تنظيف", "تحقق", "تنبؤ", "مخاطر")

BUILT_IN_TEXT = {
    "en": {
        "plan": ("The stages run in their fixed order, from {first} to {last}. For this "
                 "goal, read {watch} first. Nothing is published before the validator "
                 "passes and a person approves."),
        "note": "{role} verified: {facts}",
        "always": ("Before approving, open each figure's linked calculation and confirm "
                   "the dataset snapshot it was computed from is the one you mean."),
        "brief": ("Check first: {first}. Then read the consultant notes below: a risk "
                  "named by more than one of them is confirmed; one named by a single "
                  "consultant needs a reason before you act on it."),
        "example": " Finding to check: {fact}",
        "rules": [
            (("missing", "gap", "blank", "null", "incomplete", "unavailable", "not supported"),
             "Coverage: a finding reports missing or unsupported data; confirm the gap "
             "before relying on any rate built over it."),
            (("forecast", "predict", "baseline", "error"),
             "Prediction: treat any forecast as indicative, and confirm it beat its "
             "stated baseline before planning on it."),
            (("cost", "loss", "spend", "aed", "usd", "price"),
             "Finance: confirm the cost basis and the period before quoting a money "
             "figure outside this report."),
            (("overdue", "downtime", "failure", "repeat", "backlog"),
             "Operations: ask which assets and work orders drive these figures; a "
             "fleet-wide rate can hide one bad site."),
            (("cause", "causal", "driver", "associated", "correlat"),
             "Causation: an association is not a cause; ask what controlled "
             "comparison would confirm it before changing a maintenance plan."),
            (("anomal", "outlier", "unusual"),
             "Anomalies: confirm each flagged record with the people who logged it "
             "before treating it as a fault."),
        ],
    },
    "ar": {
        "plan": ("تُنفَّذ المراحل بترتيبها الثابت، من {first} إلى {last}. لهذا الهدف، "
                 "اقرأ {watch} أولاً. لا يُنشر شيء قبل اجتياز مرحلة التحقق وموافقة شخص."),
        "note": "تحقّقت مرحلة {role} من: {facts}",
        "always": ("قبل الموافقة، افتح الحساب المرتبط بكل رقم وتأكد أن لقطة البيانات التي "
                   "حُسب منها هي التي تقصدها."),
        "brief": ("تحقّق أولاً من: {first}. ثم اقرأ ملاحظات المستشارين أدناه: الخطر الذي "
                  "يذكره أكثر من مستشار مؤكد؛ وما يذكره مستشار واحد يحتاج إلى سبب قبل "
                  "التصرف بناءً عليه."),
        "example": " نتيجة للتحقق: {fact}",
        "rules": [
            (("مفقود", "فجوة", "فارغ", "ناقص", "غير متاح", "غير مدعوم",
              "missing", "gap", "blank", "null", "incomplete", "unavailable", "not supported"),
             "التغطية: تشير نتيجة إلى بيانات مفقودة أو غير مدعومة؛ تأكد من الفجوة قبل "
             "الاعتماد على أي معدل مبني عليها."),
            (("توقع", "تنبؤ", "خط الأساس", "خطأ", "forecast", "predict", "baseline", "error"),
             "التنبؤ: اعتبر أي توقع إرشادياً، وتأكد أنه تفوّق على خط الأساس المذكور قبل "
             "التخطيط عليه."),
            (("تكلفة", "خسارة", "إنفاق", "درهم", "cost", "loss", "spend", "aed", "usd", "price"),
             "المالية: تأكد من أساس التكلفة والفترة قبل الاستشهاد بأي رقم مالي خارج "
             "هذا التقرير."),
            (("متأخر", "توقف", "عطل", "متكرر", "تراكم",
              "overdue", "downtime", "failure", "repeat", "backlog"),
             "التشغيل: اسأل عن الأصول وأوامر العمل التي تقف وراء هذه الأرقام؛ قد يخفي "
             "معدل الأسطول موقعاً واحداً متعثراً."),
            (("سبب", "سببي", "محرك", "مرتبط", "ارتباط",
              "cause", "causal", "driver", "associated", "correlat"),
             "السببية: الارتباط ليس سبباً؛ اسأل عن المقارنة المضبوطة التي تؤكده قبل "
             "تغيير خطة الصيانة."),
            (("شاذ", "متطرف", "غير معتاد", "anomal", "outlier", "unusual"),
             "الشواذ: تأكد من كل سجل مُعلَّم مع من سجّله قبل اعتباره عطلاً."),
        ],
    },
}


def _text(language):
    return BUILT_IN_TEXT["ar" if language == "ar" else "en"]


def built_in_plan(goal, roster, language="en"):
    """Hermes' plan with no model: the fixed order, and the stages whose
    titles say they guard quality, privacy, validity or risk."""
    if not roster:
        return None
    watch = [title for title in roster if any(w in title.lower() for w in WATCH_WORDS)]
    watch = watch[:3] or roster[:2]
    joiner = "، " if language == "ar" else ", "
    return _text(language)["plan"].format(first=roster[0], last=roster[-1],
                                          watch=joiner.join(watch))


def built_in_agent_note(role, facts, language="en"):
    """The stage's own verified findings, read back as its note."""
    facts = [f for f in facts if f][:3]
    if not facts:
        return None
    return _text(language)["note"].format(role=role, facts=" ".join(facts))


def built_in_consult(facts, language="en"):
    """At most three questions for the approver: the standard one, then
    one per risk rule that a finding triggers, quoting that finding."""
    text = _text(language)
    notes = [text["always"]]
    for words, sentence in text["rules"]:
        hit = next((f for f in facts if any(w in f.lower() for w in words)), None)
        if hit:
            notes.append(sentence + text["example"].format(fact=hit))
        if len(notes) == 3:
            break
    return " ".join(notes)


def built_in_brief(facts, language="en"):
    return _text(language)["brief"].format(first=facts[0]) if facts else None


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

        # A role nobody plays is played by the built-in writer, unless the
        # operator switched that off.
        self.built_in = (env.get("AGENTIC_OS_BUILT_IN_ROLES") or "1").strip() != "0"
        if self.built_in:
            self.hermes = self.hermes or BUILT_IN
            self.agents = self.agents or BUILT_IN
            self.consultants = self.consultants or [BUILT_IN]

    @property
    def active(self):
        return bool(self.hermes or self.agents or self.consultants)

    def status(self):
        return {"hermes": self.hermes or "rules", "agents": self.agents,
                "consultants": list(self.consultants), "problems": list(self.problems)}

    def restricted(self):
        """These roles with every model replaced by the built-in writer:
        what a run that carries personal data gets, so that no verified
        sentence with a person in it reaches a provider."""
        import copy
        clone = copy.copy(self)
        clone.hermes = BUILT_IN if self.hermes and self.built_in else None
        clone.agents = BUILT_IN if self.agents and self.built_in else None
        clone.consultants = [BUILT_IN] if self.consultants and self.built_in else []
        return clone

    @property
    def all_built_in(self):
        return (self.hermes in (None, BUILT_IN) and self.agents in (None, BUILT_IN)
                and all(c == BUILT_IN for c in self.consultants))

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
            "built_in_fallback": self.built_in,
            "problems": list(getattr(gateway, "task_problems", [])) + list(self.problems),
        }

    def _ask(self, system, user, provider, language, facts):
        if blocks_model(texts=[user, *facts]):
            return None
        options = {}
        if (split_spec(provider)[0] == "ollama"
                and getattr(self.gateway, "ollama_think", None) is False):
            # A short CPU briefing should not spend the reasoning budget
            # reserved for models that think before writing their answer.
            options["max_tokens"] = 240
            system += (
                " Use at most 45 words in one plain paragraph, without numbered lists"
                " or item labels. Prioritize the essential checks without an introduction."
            )
        if language == "ar":
            system += ARABIC
        return grounded(self.gateway.ask(system, user, provider=provider, **options), facts)

    def agent_note(self, goal, role, result, language="en"):
        """The agent's own findings, phrased by the agents' model."""
        facts = claim_texts(result)[:MAX_FACTS]
        if not self.agents or not facts:
            return None
        if self.agents == BUILT_IN:
            text = grounded(built_in_agent_note(role, facts, language), facts)
            return {"text": text, "provider": BUILT_IN, "role": role} if text else None
        if blocks_model(texts=[goal, *facts]):
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
        if self.hermes == BUILT_IN:
            text = grounded(built_in_plan(goal, roster, language), [goal] + list(roster))
        else:
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

        def consult_one(name):
            if name == BUILT_IN:
                return name, grounded(built_in_consult(facts, language), facts)
            return name, self._ask(CONSULTANT_SYSTEM, user, name, language, facts)

        if self.consultants:
            with ThreadPoolExecutor(max_workers=len(self.consultants)) as pool:
                answers = list(pool.map(consult_one, self.consultants))
            notes = [{"provider": name, "text": text} for name, text in answers if text]
        brief = None
        if self.hermes == BUILT_IN:
            text = grounded(built_in_brief(facts, language), facts)
            brief = {"provider": BUILT_IN, "text": text} if text else None
        elif self.hermes:
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
    authors = [n["provider"] for n in orchestration.get("consultants") or []]
    if orchestration.get("hermes"):
        authors.append(orchestration["hermes"]["provider"])
    only_rules = bool(authors) and all(a == BUILT_IN for a in authors)
    lines = ["", text["heading"],
             text["caution_built_in"] if only_rules else text["caution"]]
    if orchestration.get("hermes"):
        brief = orchestration["hermes"]
        lines += ["", text["hermes"].format(provider=brief["provider"]), brief["text"]]
    for note in orchestration.get("consultants") or []:
        lines += ["", text["consultant"].format(provider=note["provider"]), note["text"]]
    return lines
