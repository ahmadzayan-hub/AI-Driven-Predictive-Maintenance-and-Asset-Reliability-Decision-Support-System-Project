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

import json
import re
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context

from server.model_gateway import split_spec
from server.model_privacy import blocks_model
from server import schema

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
    "reviewing verified analytics findings. Write exactly two short sentences "
    "in a single paragraph about the most important evidence gap or question "
    "the approver should raise before acting. This is a qualitative review: "
    "do not state numbers, enumerate points, use bullets or add headings. "
    "Never invent causes or predictions. Plain business English."
)
ARABIC = (" Write in formal Arabic, copying every number exactly as written "
          "in the facts with the same digits.")
# Structured consultant risks (assessment G5): each risk names the finding
# it is about by its number in the list, so agreement between consultants
# is a comparison of references, not a model's opinion (G6).
CONSULTANT_RISKS_SYSTEM = (
    "You are an independent senior reliability and analytics consultant "
    "reviewing verified analytics findings, numbered in the list you are given. "
    "Return ONLY one JSON object: {\"risks\": [{\"finding\": <number>, "
    "\"concern\": \"one short sentence\"}], \"note\": \"two short sentences\"}. "
    "Name at most three risks, each about one numbered finding: the evidence "
    "gap or question the approver should raise before acting on it. The note "
    "is your qualitative review in a single paragraph. Never state a number, "
    "never invent causes or predictions. Plain business English."
)
MAX_RISKS = 3
RISKS_SCHEMA = {
    "type": "object",
    "properties": {
        "risks": {"type": "array", "maxItems": MAX_RISKS, "items": {
            "type": "object",
            "properties": {"finding": {"type": "integer"},
                           "concern": {"type": "string", "minLength": 1}},
            "required": ["finding", "concern"], "additionalProperties": False}},
        "note": {"type": "string", "minLength": 1}},
    "required": ["risks", "note"], "additionalProperties": False,
}

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
           "consultant": "**Consultant ({provider}):**",
           "risk": "- Finding {finding}: {concern}",
           "agreement": ("**Agreement (compared by the finding each risk names):** named by "
                         "more than one consultant: {agreed}; by one only: {single}."),
           "none": "none"},
    "ar": {"heading": "## ملاحظات المنسّق والمستشارين",
           "caution": "*كتبتها نماذج لغوية من النتائج المتحقق منها أعلاه. "
                      "تضيف رأياً لا أرقاماً؛ وكل رقم في هذا التقرير محسوب.*",
           "caution_built_in": "*كتبتها قواعد المنصة المدمجة من النتائج المتحقق منها "
                               "أعلاه، دون أي نموذج لغوي. تضيف أسئلة لا أرقاماً؛ "
                               "وكل رقم في هذا التقرير محسوب.*",
           "hermes": "**هيرميس (المنسّق، {provider}):**",
           "consultant": "**مستشار ({provider}):**",
           "risk": "- النتيجة {finding}: {concern}",
           "agreement": ("**الاتفاق (بالمقارنة حسب رقم النتيجة):** سمّاها أكثر من مستشار: "
                         "{agreed}؛ وسمّاها مستشار واحد فقط: {single}."),
           "none": "لا شيء"},
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
        "brief_compared": ("Check first: {first}. The consultants' risks were compared "
                           "by the finding each names."),
        "agreed": "Named by more than one consultant, so confirmed: {findings}.",
        "single": ("Named by a single consultant, so it needs a reason before you act "
                   "on it: {findings}."),
        "joiner": ", ",
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
             "Operations: ask which assets and work orders carry these figures; a "
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
        "brief_compared": ("تحقّق أولاً من: {first}. قورنت مخاطر المستشارين حسب "
                           "البند الذي يسمّيه كل منهم."),
        "agreed": "سمّاها أكثر من مستشار فهي مؤكدة: {findings}.",
        "single": ("سمّاها مستشار واحد فتحتاج إلى سبب قبل التصرف بناءً عليها: "
                   "{findings}."),
        "joiner": "، ",
        "example": " البند المطلوب التحقق منه: {fact}",
        "rules": [
            (("مفقود", "فجوة", "فارغ", "ناقص", "غير متاح", "غير مدعوم",
              "missing", "gap", "blank", "null", "incomplete", "unavailable", "not supported"),
             "التغطية: تشير إحدى النتائج إلى بيانات مفقودة أو غير مدعومة؛ تأكد من الفجوة قبل "
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
    return built_in_consult_risks(facts, language)[0]


def built_in_consult_risks(facts, language="en"):
    """The built-in consultant's note and its structured risks: each rule
    hit names the finding (1-based) it quotes, so the agreement check
    (G6) can compare it with a model's risks by reference."""
    text = _text(language)
    notes, risks = [text["always"]], []
    for words, sentence in text["rules"]:
        hit = next((i for i, f in enumerate(facts) if any(w in f.lower() for w in words)), None)
        if hit is not None:
            notes.append(sentence + text["example"].format(fact=facts[hit]))
            risks.append({"finding": hit + 1, "concern": sentence})
        if len(notes) == 3:
            break
    return " ".join(notes), risks


def parse_risks(raw, facts):
    """A model's structured answer → (note, risks) or None (G5).

    The shape is validated against RISKS_SCHEMA; a finding number outside
    the list is dropped, and the note must be grounded like any other."""
    if not isinstance(raw, str):
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    if not schema.valid(RISKS_SCHEMA, data):
        return None
    risks = [{"finding": r["finding"], "concern": r["concern"].strip()[:300]}
             for r in data["risks"] if 1 <= r["finding"] <= len(facts)]
    return data["note"].strip(), risks


def agreement(notes, facts=()):
    """Which findings more than one consultant named, and which only one
    did, by reference (G6): a comparison the code makes, not a model.
    The quoted findings travel with the numbers so the brief and the
    report can name them without a digit of their own."""
    named = {}
    for note in notes:
        for risk in note.get("risks") or []:
            named.setdefault(risk["finding"], set()).add(note["provider"])
    agreed = sorted(f for f, who in named.items() if len(who) > 1)
    single = sorted(f for f, who in named.items() if len(who) == 1)
    quote = lambda f: facts[f - 1] if 0 < f <= len(facts) else f"#{f}"  # noqa: E731
    return {"agreed": agreed, "single": single,
            "agreed_findings": [quote(f) for f in agreed],
            "single_findings": [quote(f) for f in single],
            "by_finding": {str(f): sorted(who) for f, who in sorted(named.items())}}


def built_in_brief(facts, language="en", agreed=None):
    """The approver's brief. With the consultants' agreement (G6) it says
    which findings more than one consultant named and which only one did,
    by number, instead of telling the reader to compare the notes."""
    if not facts:
        return None
    text = _text(language)
    if not agreed or not (agreed.get("agreed") or agreed.get("single")):
        return text["brief"].format(first=facts[0])
    parts = []
    if agreed.get("agreed"):
        parts.append(text["agreed"].format(
            findings=text["joiner"].join(f"“{f}”" for f in agreed["agreed_findings"])))
    if agreed.get("single"):
        parts.append(text["single"].format(
            findings=text["joiner"].join(f"“{f}”" for f in agreed["single_findings"])))
    return text["brief_compared"].format(first=facts[0]) + " " + " ".join(parts)


# Quantity words a model can use to smuggle a figure past the digit check
# (assessment G13): each maps to the number it states. "one in five" and
# "two thirds" are read as the fraction they name.
# "one", "third" and "quarter" are left out on purpose: as a pronoun, an
# ordinal and a period they are prose, not figures ("one of them", "the
# third stage", "this quarter"); "one in five" is still read as a fraction.
QUANTITY_WORDS = {
    "zero": 0, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "dozen": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    "million": 1_000_000, "half": 0.5, "halved": 0.5,
    "double": 2, "doubled": 2, "twice": 2, "triple": 3, "tripled": 3, "threefold": 3,
    "fourfold": 4, "tenfold": 10,
    "ضعف": 2, "ضعفين": 2, "ثلاثة أضعاف": 3, "نصف": 0.5,
}
QUANTITY = re.compile(r"\b(" + "|".join(sorted(map(re.escape, QUANTITY_WORDS), key=len, reverse=True))
                      + r")\b", re.I)
FRACTION = re.compile(r"\b(one|two|three|four|five|six|seven|eight|nine)\s+in\s+"
                      r"(two|three|four|five|six|seven|eight|nine|ten|twenty|hundred)\b", re.I)


def _numbers(text):
    return {match.replace(",", "") for match in NUMBER.findall(text or "")}


def _quantities(text):
    """Every quantity a text states, as digits and as words, normalised to
    a number: "doubled" and "2" are the same claim."""
    found = set()
    for match in _numbers(text):
        try:
            found.add(float(match))
        except ValueError:
            pass
    for match in FRACTION.finditer(text or ""):
        words = {"one": 1, **QUANTITY_WORDS}
        found.add(round(words[match.group(1).lower()] / words[match.group(2).lower()], 6))
    for match in QUANTITY.finditer(text or ""):
        found.add(float(QUANTITY_WORDS[match.group(1).lower()]))
    return {round(value, 6) for value in found}


def _causal(text):
    """Causal wording the claims lint would refuse, when the lint is
    importable; the notes are written after the validator, so they get
    the same lint here (G13)."""
    try:
        from scripts.claims_lint import causal_phrases
    except Exception:
        return []
    return causal_phrases(text)


def grounded(text, facts):
    """The note, trimmed, if every quantity in it appears in the facts
    (as digits or as words) and it claims no cause; otherwise None. A
    model may phrase a figure, never produce one."""
    if not text:
        return None
    text = text.strip()[:MAX_NOTE_CHARS]
    allowed = set()
    for fact in facts:
        allowed |= _quantities(fact)
    if not _quantities(text) <= allowed:
        return None
    # The facts are verified already; the lint judges only what the
    # writer added around them.
    own = text
    for fact in sorted(facts, key=len, reverse=True):
        if fact:
            own = own.replace(fact, " ")
    if _causal(own):
        return None
    return text


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

        numbered = ("Goal: " + goal + "\nVerified findings, numbered:\n"
                    + "\n".join(f"{i + 1}. {f}" for i, f in enumerate(facts)))

        def consult_one(name):
            if name == BUILT_IN:
                text, risks = built_in_consult_risks(facts, language)
                return name, grounded(text, facts), risks
            structured = self._ask_risks(numbered, name, language, facts)
            if structured is not None:
                return (name,) + structured
            return name, self._ask(CONSULTANT_SYSTEM, user, name, language, facts), []

        if self.consultants:
            with ThreadPoolExecutor(max_workers=len(self.consultants)) as pool:
                # Each task gets its own Context, sharing the same locked
                # admission token and tenant identity. Threads do not inherit it.
                futures = [pool.submit(copy_context().run, consult_one, name)
                           for name in self.consultants]
                answers = [future.result() for future in futures]
            notes = [{"provider": name, "text": text, "risks": risks}
                     for name, text, risks in answers if text]
        brief = None
        if self.hermes == BUILT_IN:
            text = grounded(built_in_brief(facts, language, agreement(notes, facts)), facts)
            brief = {"provider": BUILT_IN, "text": text} if text else None
        elif self.hermes:
            consulted = "".join(f"\nConsultant ({n['provider']}): {n['text']}" for n in notes)
            text = self._ask(HERMES_BRIEF_SYSTEM, user + consulted, self.hermes,
                             language, facts)
            brief = {"provider": self.hermes, "text": text} if text else None
        if not notes and brief is None:
            return None
        return {"hermes": brief, "consultants": notes, "agreement": agreement(notes, facts)}

    def _ask_risks(self, user, provider, language, facts):
        """The structured consultant call (G5): (note, risks) when the
        provider answered in the schema and the note is grounded; None
        when it did not, so the free-text call can be tried."""
        ask = getattr(self.gateway, "ask_json", None)
        if not callable(ask) or blocks_model(texts=[user, *facts]):
            return None
        system = CONSULTANT_RISKS_SYSTEM + (ARABIC if language == "ar" else "")
        options = {}
        if (split_spec(provider)[0] == "ollama"
                and getattr(self.gateway, "ollama_think", None) is False):
            options["max_tokens"] = 240
            system += (" Use at most 45 words in the note, in one plain paragraph.")
        try:
            raw = ask(system, user, provider=provider, schema=RISKS_SCHEMA,
                      task="consult", **options)
        except TypeError:
            raw = ask(system, user, provider=provider, **options)
        parsed = parse_risks(raw, facts)
        if parsed is None:
            return None
        note, risks = parsed
        note = grounded(note, facts)
        return (note, risks) if note else None


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
        for risk in note.get("risks") or []:
            lines.append(text["risk"].format(finding=risk["finding"], concern=risk["concern"]))
    agreed = orchestration.get("agreement") or {}
    if agreed.get("agreed") or agreed.get("single"):
        lines += ["", text["agreement"].format(
            agreed="; ".join(f"“{f}”" for f in agreed.get("agreed_findings") or []) or text["none"],
            single="; ".join(f"“{f}”" for f in agreed.get("single_findings") or []) or text["none"])]
    return lines
