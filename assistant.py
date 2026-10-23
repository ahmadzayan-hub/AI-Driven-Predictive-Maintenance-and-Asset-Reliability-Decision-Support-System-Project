"""What a message means, and what to do about it — with no model at all.

The chat used to answer every sentence that was not a slash command with
a template: *"Happy to help! I received your request."* That is a
placeholder wearing a greeting. This module is the replacement's floor:
a rules-based understander that turns a sentence in English or Arabic
into one of a small, typed set of actions, and an executor for the
actions that need nothing but the Agent itself.

The contract is one dict, an **intent**:

    {"action": "remember", "arguments": {"information": "…"},
     "reply": None, "source": "rules"}

`server/assistant.py` produces the same dict from a language model when
one is configured, and runs the actions that need the run engine. Both
paths meet at the same executor, so what an action *does* never depends
on who understood the sentence.

Standard library only, because the command-line interface uses it too.
"""

import re

# The whole vocabulary. An action the model names that is not here is
# refused, not improvised; an argument it names that is not listed is
# dropped. Small on purpose: a person can read this and know exactly
# what a sentence can cause.
ACTIONS = {
    "chat": (),
    "help": (),
    "remember": ("information", "category"),
    "recall": ("query",),
    "forget": ("key", "about"),
    "clear_history": (),
    "set_preference": ("key", "value"),
    "start_run": ("goal", "dataset"),
    "run_status": ("run_id",),
    "explain_report": ("section", "run_id"),
    "search_knowledge": ("query", "collection"),
    "agent_scorecard": ("suite",),
}
# These delete something. Whoever understood the sentence — rules or
# model — the system asks first, and only a "yes" in the next message
# executes. The UI's own controls confirm too; the chat is not a way
# around that.
DESTRUCTIVE = {"forget", "clear_history"}
# These need the run engine, which the command-line interface does not have.
SERVER_ONLY = {"start_run", "run_status", "explain_report", "search_knowledge",
               "agent_scorecard"}
PREFERENCE_KEYS = ("tone", "language", "user_name", "save_history")
TONES = ("friendly", "concise", "formal")
SECTIONS = ("descriptive", "diagnostic", "experiment", "predictive", "prescriptive")

YES_WORDS = {
    "yes", "y", "yeah", "yep", "yup", "sure", "confirm", "confirmed", "do it",
    "go ahead", "ok", "okay", "please do", "proceed", "affirmative",
    "نعم", "أيوه", "ايوه", "أيوة", "ايوة", "اه", "آه", "أكيد", "اكيد", "تمام",
    "موافق", "موافقة", "نفذ", "نفّذ", "اعمل", "أكد", "أؤكد", "طبعا", "طبعًا",
}
NO_WORDS = {
    "no", "n", "nope", "cancel", "don't", "dont", "do not", "stop", "never mind",
    "nevermind", "leave it", "forget it", "negative",
    "لا", "لأ", "لاء", "إلغاء", "الغاء", "بلاش", "خلاص", "مش عايز", "لا تفعل",
    "توقف", "الغي", "ألغِ", "ألغي", "اتركه", "سيبه",
}

TONE_WORDS = {
    "concise": ("concise", "brief", "briefer", "short", "shorter", "terse",
                "مختصر", "مختصرة", "موجز", "موجزة", "باختصار", "قصير", "قصيرة"),
    "formal": ("formal", "formally", "professional",
               "رسمي", "رسمية", "رسميا", "رسميًا", "بشكل رسمي"),
    "friendly": ("friendly", "casual", "warm", "relaxed", "informal",
                 "ودود", "ودي", "ودية", "لطيف", "لطيفة", "بشكل ودي"),
}
LANGUAGE_WORDS = {
    "Arabic": ("arabic", "بالعربي", "بالعربية", "العربية", "عربي", "عربى"),
    "English": ("english", "بالإنجليزي", "بالانجليزي", "بالإنجليزية",
                "بالانجليزية", "الإنجليزية", "الانجليزية", "انجليزي", "إنجليزي"),
}

# The assistant's own sentences. The Agent's catalogue (agent.py) covers
# the slash commands; these cover understanding, confirmation and the
# actions only the assistant can take. Same rule as everywhere: the
# reply is in the language the person chose, and English is the fallback.
REPLIES = {
    "en": {
        "fallback_friendly":
            "Happy to help! I'm not sure what you'd like me to do with "
            "“{request}”. I can analyse a dataset, remember something, show "
            "what I remember, change how I reply, or explain the latest "
            "report — for example: “analyse the sample sales data” or "
            "“remember that the Q4 review is on Monday”.",
        "fallback_concise":
            "Not sure what to do with “{request}”. Try: analyse the sample "
            "sales data · remember that … · what do you remember? · explain "
            "the latest report.",
        "fallback_formal":
            "Your request “{request}” was not understood. The following are "
            "supported: analysing a dataset, saving and recalling "
            "information, changing reply preferences, and explaining the "
            "latest report.",
        "capabilities":
            "Here is what I can do:\n"
            "• Analyse a dataset — “analyse the sample sales data”, or name "
            "a dataset you have uploaded\n"
            "• Remember things — “remember that the Q4 review is on Monday”\n"
            "• Show what I remember — “what do you remember?”\n"
            "• Explain the latest report — “why did revenue move?”, “what "
            "should we do?”\n"
            "• Change how I reply — “be concise”, “reply in Arabic”, “call "
            "me Ahmad”\n"
            "Slash commands still work; /help lists them.",
        "confirm_forget_all":
            "This will permanently delete everything I remember. Reply "
            "“yes” to confirm or “no” to keep it.",
        "confirm_forget_key":
            "This will permanently delete {key}: “{text}”. Reply “yes” to "
            "confirm or “no” to keep it.",
        "forget_none_match":
            "Nothing I remember matches “{about}”. Say “show my notes” to "
            "see what I have.",
        "forget_which":
            "These notes match “{about}”:\n{entries}\nSay which one to delete, "
            "for example “forget {first}”.",
        "confirm_clear_history":
            "This will clear this session's conversation history (saved "
            "memory is not affected). Reply “yes” to confirm or “no” to "
            "keep it.",
        "cancelled": "Nothing was changed.",
        "recall_none_match": "Nothing I remember mentions “{query}”.",
        "bad_tone":
            "I can reply in a friendly, concise, or formal tone — which "
            "would you like?",
        "unknown_preference":
            "I can change the tone, the language, your name, or whether "
            "history is recorded.",
        "cli_needs_web":
            "Analytics runs need the web interface: start it with "
            "`python scripts/serve.py` and ask there.",
        "knowledge_found":
            "From {collection}:\n\n{passages}\n\nQuoted from the knowledge "
            "base, not paraphrased. Follow a citation to read the section in "
            "full.",
        "knowledge_none":
            "Nothing in the knowledge base matches “{query}”. I would rather "
            "say so than answer from memory.",
        "knowledge_empty":
            "No knowledge collection is loaded. Point "
            "AGENTIC_OS_KNOWLEDGE_DIR at a folder of Markdown, or add one to "
            "private/knowledge/.",
        "scorecard":
            "Agent scorecard ({when}). Recall is the share of real cases an "
            "agent gets right; the holdout is the number to trust.\n{rows}"
            "{notes}",
        "scorecard_none":
            "No agent evaluation is available in this deployment. Run "
            "`python scripts/agent_loop.py` where the repository's evals/ "
            "folder is present.",
        "run_started":
            "Started analysis {run_id} on {dataset}: “{goal}”. It is open in "
            "Runs — the pipeline advances while that view is open, and "
            "publishing waits for your approval.",
        "run_status":
            "Analysis {run_id} (“{goal}”) is {state}: {done} of {total} "
            "steps done{approval}.",
        "run_status_approval": " — waiting for your approval to publish",
        "no_runs":
            "There is no analysis yet. Say “analyse the sample sales data” "
            "to start one.",
        "no_report_yet":
            "Analysis {run_id} has not produced a report yet — it is "
            "{state}.",
        "report_intro": "From analysis {run_id} (“{goal}”):",
        "report_outro": "The full report, with every calculation, is in Runs.",
        "dataset_sample": "the sample sales dataset",
        # What an outside driver — an agent runtime or an MCP client — is
        # told when it asks for something the catalogue does not offer.
        "tool_unknown": "There is no tool called “{name}”. Available: {available}.",
        "tool_not_offered":
            "Deleting is not offered to an automated driver. Ask me directly "
            "— “forget memory_3” — and confirm.",
        "tool_limit":
            "The step limit ({limit}) for one message was reached; nothing "
            "further was run.",
        "tool_bad_arguments":
            "The arguments for “{name}” were not valid, so it was not run.",
    },
    "ar": {
        "fallback_friendly":
            "يسعدني المساعدة! لم أفهم ما تريده من «{request}». أستطيع تحليل "
            "مجموعة بيانات، أو حفظ معلومة، أو عرض ما أتذكره، أو تغيير طريقة "
            "ردي، أو شرح آخر تقرير — مثلًا: «حلّل بيانات المبيعات النموذجية» "
            "أو «تذكّر أن مراجعة الربع الرابع يوم الاثنين».",
        "fallback_concise":
            "لم أفهم «{request}». جرّب: حلّل بيانات المبيعات النموذجية · "
            "تذكّر أن … · ماذا تتذكر؟ · اشرح آخر تقرير.",
        "fallback_formal":
            "لم يُفهم طلبك «{request}». المدعوم: تحليل مجموعة بيانات، وحفظ "
            "المعلومات واستدعاؤها، وتغيير تفضيلات الرد، وشرح آخر تقرير.",
        "capabilities":
            "هذا ما أستطيع فعله:\n"
            "• تحليل مجموعة بيانات — «حلّل بيانات المبيعات النموذجية»، أو "
            "اذكر اسم مجموعة رفعتها\n"
            "• حفظ المعلومات — «تذكّر أن مراجعة الربع الرابع يوم الاثنين»\n"
            "• عرض ما أتذكره — «ماذا تتذكر؟»\n"
            "• شرح آخر تقرير — «لماذا تغيّرت الإيرادات؟»، «ماذا ينبغي أن "
            "نفعل؟»\n"
            "• تغيير طريقة ردي — «خليك مختصر»، «رد بالإنجليزي»، «ناديني أحمد»\n"
            "أوامر الشرطة المائلة ما زالت تعمل؛ ‎/help يعرضها.",
        "confirm_forget_all":
            "سيُحذف كل ما أتذكره نهائيًا. أجب بـ«نعم» للتأكيد أو «لا» للإبقاء "
            "عليه.",
        "confirm_forget_key":
            "سيُحذف {key} نهائيًا: «{text}». أجب بـ«نعم» للتأكيد أو «لا» "
            "للإبقاء عليه.",
        "forget_none_match":
            "لا شيء مما أتذكره يطابق «{about}». قل «اعرض ملاحظاتي» لترى ما "
            "لدي.",
        "forget_which":
            "هذه الملاحظات تطابق «{about}»:\n{entries}\nقل أيها أحذف، مثلًا "
            "«انس {first}».",
        "confirm_clear_history":
            "سيُمسح سجل محادثة هذه الجلسة (لن تتأثر الذاكرة المحفوظة). أجب "
            "بـ«نعم» للتأكيد أو «لا» للإبقاء عليه.",
        "cancelled": "لم يتغيّر شيء.",
        "recall_none_match": "لا شيء مما أتذكره يذكر «{query}».",
        "bad_tone": "أستطيع الرد بأسلوب ودود أو موجز أو رسمي — أيها تفضّل؟",
        "unknown_preference":
            "أستطيع تغيير الأسلوب، أو اللغة، أو اسمك، أو تسجيل السجل.",
        "cli_needs_web":
            "عمليات التحليل تحتاج واجهة الويب: شغّلها بـ "
            "`python scripts/serve.py` واطلب منها هناك.",
        "knowledge_found":
            "من {collection}:\n\n{passages}\n\nمقتبس من قاعدة المعرفة دون "
            "إعادة صياغة. اتبع المرجع لقراءة القسم كاملاً.",
        "knowledge_none":
            "لا يوجد في قاعدة المعرفة ما يطابق «{query}». أقول ذلك بدل أن "
            "أجيب من الذاكرة.",
        "knowledge_empty":
            "لم تُحمَّل أي مجموعة معرفة. وجّه "
            "AGENTIC_OS_KNOWLEDGE_DIR إلى مجلد ماركداون، أو أضف واحداً إلى "
            "private/knowledge/.",
        "scorecard":
            "بطاقة أداء الوكلاء ({when}). الاستدعاء هو نسبة الحالات الحقيقية "
            "التي يصيبها الوكيل؛ والرقم الذي يُعتمد عليه هو رقم المجموعة "
            "المحجوزة.\n{rows}{notes}",
        "scorecard_none":
            "لا يتوفر تقييم للوكلاء في هذا النشر. شغّل "
            "`python scripts/agent_loop.py` حيث يوجد مجلد evals/ الخاص "
            "بالمستودع.",
        "run_started":
            "بدأت التحليل {run_id} على {dataset}: «{goal}». مفتوح في "
            "التحليلات — يتقدّم خط المعالجة أثناء فتح تلك الشاشة، والنشر "
            "ينتظر موافقتك.",
        "run_status":
            "التحليل {run_id} («{goal}») {state}: اكتملت {done} من {total} "
            "خطوات{approval}.",
        "run_status_approval": " — بانتظار موافقتك على النشر",
        "no_runs":
            "لا يوجد تحليل بعد. قل «حلّل بيانات المبيعات النموذجية» لبدء "
            "واحد.",
        "no_report_yet": "التحليل {run_id} لم يُنتج تقريرًا بعد — حالته {state}.",
        "report_intro": "من التحليل {run_id} («{goal}»):",
        "report_outro": "التقرير الكامل، بكل حساباته، في التحليلات.",
        "dataset_sample": "مجموعة بيانات المبيعات النموذجية",
        "tool_unknown": "لا توجد أداة باسم «{name}». المتاح: {available}.",
        "tool_not_offered":
            "الحذف غير متاح لمشغّل آلي. اطلبه مني مباشرة — «انسَ memory_3» — "
            "وأكّد.",
        "tool_limit":
            "بلغنا حد الخطوات ({limit}) للرسالة الواحدة؛ لم يُنفَّذ شيء آخر.",
        "tool_bad_arguments": "وسائط «{name}» غير صالحة، فلم تُنفَّذ.",
    },
}

RUN_STATES = {
    "en": {"queued": "queued", "running": "running",
           "awaiting_approval": "waiting for approval", "completed": "completed",
           "partially_completed": "partially completed", "failed": "failed",
           "cancelled": "cancelled"},
    "ar": {"queued": "في الانتظار", "running": "قيد التنفيذ",
           "awaiting_approval": "بانتظار الموافقة", "completed": "مكتمل",
           "partially_completed": "مكتمل جزئيًا", "failed": "فشل",
           "cancelled": "أُلغي"},
}

SECTION_QUESTIONS = {
    "en": {"descriptive": "What happened?", "diagnostic": "Why did it happen?",
           "experiment": "Can we claim a cause?", "predictive": "What will happen?",
           "prescriptive": "What should I do?"},
    "ar": {"descriptive": "ماذا حدث؟", "diagnostic": "لماذا حدث؟",
           "experiment": "هل يمكننا ادعاء سبب؟", "predictive": "ماذا سيحدث؟",
           "prescriptive": "ماذا ينبغي أن أفعل؟"},
}


def reply(language, message, /, **values):
    """A sentence of the assistant's own, in the person's language.

    `message` is positional-only because one of the placeholders a
    caller fills is named `key`."""
    catalogue = REPLIES.get(language) or REPLIES["en"]
    template = catalogue.get(message) or REPLIES["en"][message]
    return template.format(**values)


def intent(action, arguments=None, text=None, source="rules", why=None):
    return {"action": action, "arguments": dict(arguments or {}),
            "reply": text, "source": source, "why": why}


_PUNCTUATION = " \t\r\n!.,;:؟?،؛\"'«»“”"


def is_yes(text):
    return str(text).strip(_PUNCTUATION).lower() in YES_WORDS


def is_no(text):
    return str(text).strip(_PUNCTUATION).lower() in NO_WORDS


# ---------------------------------------------------------------------------
# Rules. Order is the priority: a sentence matching two rules gets the
# first. Anchored patterns (^) are for verbs that open a request;
# unanchored ones are for questions that can be phrased many ways.
# ---------------------------------------------------------------------------

_HELP = re.compile(
    r"^\W*(help|commands|capabilities)\W*$|^\W*how (do|can|should) i\b"
    r"|\b(what can you do|what do you do|what are you able to do|"
    r"what can i (ask|do)|what commands|which commands|(list|show)( me)? (the |your )?commands|"
    r"what can you (actually |really |even )?do|not sure (where|how) to start|"
    r"how (does|do) (this|it|you) work|how do i use (this|it|you)|what are my options|"
    r"help me (get started|start|begin)|get(ting)? started|guide me|how to use (this|it|you)|"
    r"walk me through how|show me how (to|i)|how (do|can|should) i (upload|use|get)|how to upload|"
    r"how (does|do) (this|the|your) (tool|app|thing|system|assistant|chat|bot) work|"
    r"what('s| is) in your (bag of tricks|toolbox|toolkit|repertoire|arsenal)|"
    r"(what|which) (commands|requests|questions|things) (do|can) you (understand|handle|take|accept|know)|"
    r"no idea (where|how) to (begin|start)(\s+(here|with (this|it|you)))?\s*([,.!?;]|$)|(first time|just opened|just started) (using |with )?(this|you|the (app|tool)))\b"
    r"|\bwhat (kinds? of )?(things|tasks|requests) (can|could) i (ask|request|get)\b"
    r"|(أقدر|اقدر|أستطيع|استطيع|يمكنني|ممكن)\s+(أن\s+)?(أطلب|اطلب|أسأل|اسأل)(ها|ه)?\s+(منك|عنك)"
    r"|^\W*(مساعدة|ساعدني|ماذا تستطيع|ماذا يمكنك|إيه اللي تقدر|ايه اللي تقدر|"
    r"تقدر تعمل|ما الذي تستطيع|ما الذي يمكنك|الأوامر|كيف أستخدم|كيف استخدم|كيف يعمل)"
    r"|(الأوامر المتاحة|ما الأوامر|كيف أبدأ|كيف ابدأ|كيف أستخدم|كيف استخدم|أستخدمك|استخدمك|تفهمني|"
    r"إزاي أستخدم|ازاي استخدم|ازاي أستخدم|إزاي استخدم|أول مرة أستخدم|اول مرة استخدم)"
    # "ايش اللي تقدر تساعدني فيه": what the assistant can do, in Gulf and Levantine words.
    r"|(ايش|إيش|شو|وش|ايه|إيه|ماذا|ما)\s+(اللي\s+|الذي\s+)?(تقدر|بتقدر|تقدري|تستطيع|يمكنك|تعرف)\s+"
    r"(تساعدني|تساعد|تسوي|تسويه|تعمل|تعمله|تفعل|تفعله|تقدمه|تقدم)", re.I)
_CLEAR_HISTORY = re.compile(
    r"\b(clear|delete|erase|wipe|reset)\b.*\b(history|conversation|chat|messages|(our|this|my) thread)\b"
    r"|(امسح|احذف|امح|صفّر|صفر|فضي|فضّي|حذف|مسح|نظف|نظّف|نضف|نضّف)\b.*(السجل|سجل المحادثة|المحادثة|التاريخ|الشات|الرسائل)", re.I)
_HISTORY_OFF = re.compile(
    r"\b(stop|quit|no longer|don'?t|do not|turn off|disable|pause|without)\b.{0,25}"
    r"\b(record(ing)?|sav(e|ing)|keep(ing)?|stor(e|ing)|log(ging)?|track(ing)?)\b.{0,30}"
    r"\b(history|conversation|chat|messages)\b"
    r"|(وقف|أوقف|اوقف|ايقاف|إيقاف|بلاش|لا)\s+(تسجيل|حفظ|تخزين)\s+(السجل|المحادثة|المحادثات|الرسائل|التاريخ|الشات)", re.I)
_HISTORY_ON = re.compile(
    r"\b(start|resume|turn on|enable|begin)\b.{0,25}"
    r"\b(record(ing)?|sav(e|ing)|keep(ing)?|stor(e|ing)|log(ging)?)\b.{0,30}"
    r"\b(history|conversation|chat|messages)\b"
    r"|(ابدأ|ابدا|شغل|شغّل|فعّل|فعل)\s+(تسجيل|حفظ|تخزين)\s+(السجل|المحادثة|المحادثات|الرسائل|التاريخ|الشات)", re.I)
_FORGET_ALL = re.compile(
    r"\b(forget|delete|clear|erase|wipe|remove)\b.*"
    r"\b(everything|all memory|all memories|all of it|the memory|my memory|"
    r"your memory|all)\b"
    r"|(انس|انسى|انسَ|امسح|احذف|امح|شيل|شيلي|أزل|ازل)\b.*(كل|الكل|كل الذاكرة|الذاكرة كلها|"
    r"كل حاجة|كل شيء|الذاكرة)", re.I)
_FORGET_KEY = re.compile(
    r"\b(forget|delete|remove|erase)\b.*\b(?P<key>memory_\d+)\b"
    r"|\b(forget|delete|remove|erase)\b.*\b(?:memory|note)\s+(?:number\s+|no\.?\s*|#)?(?P<num>\d+)\b"
    r"|(انس|انسى|انسَ|احذف|امسح|امح)\b.*(?P<key_ar>memory_\d+)"
    r"|(انس|انسى|انسَ|احذف|امسح|امح)\b.*(?:الذاكرة|الملاحظة)\s*(?:رقم\s*)?(?P<num_ar>\d+)", re.I)
_FORGET_ABOUT = re.compile(
    r"\b(forget|delete|remove|erase|drop|scrap|discard|ditch|bin|get rid of|throw out|throw away)\s+(?:the |my |that |this )?(?:saved |stored |old )?"
    r"(?:note|memory|reminder|entry|item|thing|bit|info|information|preference|fact)\s+"
    r"(?:about|on|regarding|concerning|for)\s+(?P<about>[^,.;!?]+)"
    r"|(?:انس|انسَ|انسى|احذف|امسح|امح|شيل|شيلي|أزل|ازل)\s+(?:ال)?(?:ملاحظة|ذاكرة|معلومة)\s*(?:المتعلقة|الخاصة|التي عن|عن|اللي\s+(?:\S+\s+){0,3}?عن)\s*"
    r"(?P<about_ar>[^،,.؟!]+)"
    r"|(?:انس|انسَ|انسى|احذف|امسح|امح|شيل|شيلي|أزل|ازل)\s+(?:موضوع|مسألة|مسالة|موضوعي)\s+(?P<about_ar2>[^،,.؟!]+)", re.I)
_REMEMBER = re.compile(
    r"^\W*(?:(?:could|can|would|will) you\s+(?:maybe\s+|just\s+|please\s+|kindly\s+)*|please\s+)?"
    r"(?:remember|note|save|keep in mind|don'?t forget|make a note|take a note|jot down|"
    r"dont forget|don'?t let me forget|do not let me forget|make sure (?:i|we) (?:don'?t|do not) forget)(?:\s+(?:this|that|it))?(?:\s+for later)?(?:\s+that)?\s*[:,\-–—]?\s*(?P<info>.+?)\s*$"
    r"|^\W*(?:من فضلك\s+|لو سمحت\s+|أرجو\s+|ارجو\s+|ممكن\s+|رجاءً?\s+)?"
    # "ابغاك تحفظ", "عايزك تفتكر", "أريدك أن تتذكر": I want you to remember.
    r"(?:(?:ابغاك|أبغاك|ابيك|أبيك|ابغيك|أبغيك|عايزك|عاوزك|أريدك|اريدك|بدي ياك|بدّي ياك)\s+(?:أن\s+|ان\s+)?"
    r"(?:تتذكر|تتذكّر|تفتكر)|(?:(?:ابغاك|أبغاك|ابيك|أبيك|ابغيك|أبغيك|عايزك|عاوزك|أريدك|اريدك|بدي ياك|بدّي ياك)\s+(?:أن\s+|ان\s+)?)?(?:تذكر|تذكّر|افتكر|إفتكر|"
    r"احفظ|إحفظ|سجل|سجّل|تسجل|تسجّل|تحفظ|خزن|خزّن|تخزن|لا تنس|لا تنسى|ما تنساش|متنساش|خلي بالك|خلّ في بالك|خل في بالك|خلي في بالك|خلّي في بالك|"
    r"خلك حافظ|خليك حافظ|خلّيك حافظ|خلك فاكر|خليك فاكر))"
    r"(?:\s+(?:لي|عندك|في الذاكرة|بالذاكرة))?"
    r"(?:\s+(?:هالملاحظة|هالمعلومة|هذه الملاحظة|هذي الملاحظة|هذه المعلومة|هذي المعلومة))?"
    r"(?:\s+(?:أن|ان|إن|انه|أنه|إنه|ان\s))?\s*[:،,\-–—]?\s*(?P<info_ar>.+?)\s*$",
    re.I | re.S)
_REMEMBER_BARE = re.compile(
    r"^\W*(remember|note|save|تذكر|تذكّر|افتكر|احفظ|سجل|سجّل)\W*$", re.I)
_RECALL = re.compile(
    r"\b(what do you (remember|know)|what have (i|you) (saved|remembered|told)|"
    r"show (me )?(my |the )?(memory|memories|notes)|list (my |the )?(memory|"
    r"memories|notes)|what did i (tell|say|ask)( you)?|what('s| is) in "
    r"(your|my) memory|what do you remember about|^\W*recall\b|"
    r"^\W*(do|can) you remember|(list|show)( me)? (everything|all( that)?) you('ve| have)? (remember|know|saved|stored|kept|noted)|did i (tell|say|mention|ask) you (anything|something)|"
    r"what (notes|memories) do you have|remind me (what|of what)|what (have|did) i ask(ed)? you to remember|"
    r"do you (still )?have (the |my |a |any |that |this |those )?(note|notes|memory|memories|bit|thing|info|information|entry)\b|"
    r"what (have you|you have|you've) (got )?(saved|stored|kept)|what('s| is) (saved|stored) about me)"
    r"|(إيه اللي فاكره|ايه اللي فاكره|إيه اللي حفظته|ايه اللي حفظته|ماذا تتذكر|"
    r"ما الذي تتذكره|ماذا حفظت|ما الذي حفظته|اعرض الذاكرة|أعرض الذاكرة|"
    r"اعرض ما حفظت|ماذا تعرف عني|ما هي ذاكرتك|فاكر إيه|فاكر ايه|فاكر حاجة|"
    r"هل تتذكر|تفتكر|بتفتكر|اعرض ملاحظاتي|ملاحظاتي|ذكرني|ذكّرني|خزنته|خزنت لي|حفظته لي|وش حفظت|"
    r"وش اللي حفظت|اللي حفظتها|اللي حفظته|اللي خزنتها|المعلومات اللي حفظت|اللي حافظه|اللي حافظ|"
    r"(الملاحظات|المعلومات|الأشياء|الاشياء)\s+(اللي|التي|التى)\s+(سجلت|حفظت|خزنت|دونت)|"
    # "شو المحفوظ عندك عني", "إيش كنت قلت لك عن": what is saved, what I told you.
    r"(المحفوظ|المحفوظة|المخزن|المخزّن|المسجل|المسجّل)\s+(عندك|لديك)|عندك عني|"
    r"(ايش|إيش|شو|وش|ايه|إيه|ماذا|ما الذي)\s+(كنت\s+)?(قلت لك|قلتلك|قلت|قتلك|خبرتك|أخبرتك|اخبرتك|قلته لك))", re.I)
_RECALL_QUERY = re.compile(r"\babout\s+(?P<q>.+?)\s*[?؟.]*\s*$|\bعن\s+(?P<q_ar>.+?)\s*[?؟.]*\s*$", re.I)
_NAME = re.compile(
    r"\b(?:call me|my name is|my name's|i am called|i'm called|you can call me)"
    r"\s+(?P<name>[^\s.,!?؟،]{1,40}(?:\s+[^\s.,!?؟،]{1,40})?)"
    r"|(?:اسمي|إسمي|ناديني|نادني|سمّني|سميني|أنا اسمي|انا اسمي)"
    r"\s+(?P<name_ar>[^\s.,!?؟،]{1,40}(?:\s+[^\s.,!?؟،]{1,40})?)", re.I)
_TONE_VERB = re.compile(
    r"\b(be|reply|answer|respond|keep|make|switch|use|talk|speak|go|stay|"
    r"sound|please)\b"
    r"|(خليك|خلّيك|كن|كوني|رد|ردّ|ردودك|اجعل|اجعلي|خلي|خلّي|تكلم|اتكلم|استخدم|استعمل|"
    r"كلمني|لو سمحت|من فضلك)", re.I)
_LANGUAGE_VERB = re.compile(
    r"\b(reply|answer|speak|talk|switch|change|respond|write|use)\b"
    r"|\b(in|to|into)\s+(arabic|english)\b"
    r"|(رد|ردّ|تكلم|اتكلم|كلمني|غير|غيّر|حوّل|حول|اللغة|بال)", re.I)
_SEARCH_KNOWLEDGE = re.compile(
    r"(?:search|look\s+up|find|check|consult|query|what\s+do(?:es)?)\b.{0,40}?\b"
    r"(?:knowledge(?:\s+base)?|handbook|manual|standard|procedure|guide(?:line)?s?|"
    r"documentation|docs|collection)\b"
    r"|\b(?:knowledge\s+base|handbook|manual|standards?|procedures?|guidelines?)\b.{0,30}?"
    r"\b(?:say|says|state|states|require|requires|on|about|for)\b"
    r"|(?:ابحث|ابحثي|فتّش|راجع|ماذا\s+(?:تقول|يقول))\b.{0,40}?"
    r"(?:قاعدة\s+المعرفة|المعرفة|الدليل|المواصفة|المعيار|الإجراء|الإجراءات|الوثائق)"
    r"|(?:قاعدة\s+المعرفة|الدليل|المواصفة|المعيار|الإجراء)\b.{0,30}?(?:عن|حول|بشأن|تقول|يقول)",
    re.I | re.S)
_SEARCH_KNOWLEDGE_QUERY = re.compile(
    r"(?:about|on|for|regarding|say(?:s)?\s+about|require(?:s)?\s+for)\s+(?P<q>[^?.!]+)"
    r"|(?:عن|حول|بشأن)\s+(?P<q_ar>[^؟?.!]+)", re.I | re.S)
_SCORECARD = re.compile(
    r"\b(?:agent|agents'?|eval(?:uation)?|reviewer|classifier|detector)s?\b.{0,30}?"
    r"\b(?:scorecard|score\s*card|recall|precision|confusion\s+matrix|floors?)\b"
    r"|\b(?:scorecard|score\s*card)\b"
    r"|\b(?:recall|precision|accuracy|floors?)\b.{0,30}?\b(?:agents?|classifiers?|detectors?|lints?|suites?)\b"
    r"|\bhow\s+(?:accurate|good|well)\b.{0,40}?\b(?:agents?|classifiers?|detectors?|assistant)\b"
    r"|(?:بطاقة\s+(?:الأداء|النتائج|التقييم)|سجل\s+الأداء)"
    r"|(?:ما\s+(?:مدى\s+)?دقة|كم\s+دقة)\b.{0,30}?(?:الوكلاء|الوكيل|المصنّف|المصنفات|المساعد)",
    re.I | re.S)
_SCORECARD_SUITE = re.compile(
    r"\b(?P<suite>intent|column_roles|personal_data|router|raw_guard|jargon|causal|figures|standards)\b",
    re.I)

_RUN_STATUS = re.compile(
    r"\b(status|progress)\b|\bhow('s| is| far)( along)?( is)? (the |my |that )?"
    r"(run|analysis|report)|\bis (the |my |it |that )?(run |analysis |report )?"
    r"(done|finished|ready|complete)|\bwhere (are we|is it|did (we|it) get)"
    r"|\bhas (the |my |it |that )?(run |analysis |report )?(finished|completed|ended)"
    r"|\b(is it|is the (run|analysis)) still running|\bstill running\b"
    r"|\bwhere (is|are) (the |my )?(run|analysis|report)\b"
    r"|\b(any|what('s| is) the|got an?) (update|news|progress)s? (on|about|with|regarding) (the |my |that )?(run|analysis|report)\b"
    r"|\bis (the |my |that )?(run|analysis|report)\b.{0,60}?\b(done|finished|ready|complete)\b"
    r"|\b(did|has|is) (the |my |that |this )?(run|analysis|pipeline)\b.{0,40}?\b(finish(ed)?|complete[d]?|done|stuck|fail(ed)?|end(ed)?)\b"
    # "did that job I started earlier finish": a job is a run only when someone started it.
    r"|\b(run|job|analysis|task|pipeline) (that )?(i|we|you) (started|ran|kicked off|launched|began|set off)\b.{0,40}?"
    r"\b(finish(ed)?|complete[d]?|done|stuck|fail(ed)?|end(ed)?|ready)\b"
    r"|\bwhat happened (to|with) (the |my |that |this )?(run|analysis|pipeline)\b"
    # "شو صار بالتشغيل", "ايش صار في التحليل": what became of the run.
    # The run is one the person started or the last one; "التشغيل التجريبي للخط" is a
    # line's trial operation, not a run.
    r"|(صار|صاير|حصل|جرى)\s+(ب|في|مع|بـ)?\s*(ال)?(تشغيل|تحليل)"
    r"(?=\s+(اللي|الذي|حقي|حقنا|تبعي|تبعنا|الأخير|الاخير)\b|\s*[؟?.!]?\s*$)"
    r"|(الحالة|حالة التحليل|حالة التشغيل|اكتمل|اكتملت|وصل فين|وصلنا فين|وين وصل|وين وصلت|وين وصلنا|خلص|خلصت|خلّص|انتهى|انتهت|"
    r"جاهز|جاهزة|فين التحليل|أين التحليل|ايه وضع|إيه وضع|ما وضع|وضع التحليل)",
    re.I)
_EXPLAIN = re.compile(
    r"\b(explain|summari[sz]e|walk me through|what did (it|the analysis|the "
    r"report|you) find|what (does|did) the report (say|show)|tell me about "
    r"the (report|results|findings|analysis)|(key|main) (findings|results|"
    r"takeaways)|what happened|why did .*(move|change|rise|fall|drop|grow|"
    r"increase|decrease|go (up|down))|what will happen|what('s| is) the "
    r"forecast|what (does|did) the (forecast|analysis|model) (say|show)|what should (i|we) do|what do you recommend|can we claim a "
    r"cause|is (it|this) causal|what caused)\b"
    r"|(اشرح|إشرح|اشرحلي|اشرح لي|لخص|لخّص|لخصلي|ايه النتائج|إيه النتائج|"
    r"ما النتائج|ما هي النتائج|ماذا وجد|ماذا وجدت|النتائج الرئيسية|أهم النتائج|"
    r"ماذا حدث|ايه اللي حصل|إيه اللي حصل|لماذا تغير|لماذا تغيّر|ليه اتغير|"
    r"ليه زاد|ليه نقص|لماذا زاد|لماذا انخفض|ماذا سيحدث|ايه اللي هيحصل|"
    r"إيه اللي هيحصل|التوقع|التوقعات|ماذا ينبغي|ايه اللي المفروض|"
    r"إيه اللي المفروض|ماذا تنصح|بماذا توصي|ما توصيتك|هل السبب|"
    r"هل يمكننا ادعاء سبب|ما سبب|ماذا يقول|التنبؤ|توقعات|حسب التقرير|وفق التقرير|في التقرير)", re.I)
_SECTION_HINTS = (
    ("diagnostic", re.compile(r"\b(why|cause of the change|diagnostic)\b|لماذا|ليه|ليش|التشخيص", re.I)),
    ("predictive", re.compile(r"\b(forecast|will happen|predict|predictive|next (month|quarter|"
                              r"period|year)|outlook)\b|سيحدث|هيحصل|التوقع|توقع|"
                              r"الشهر القادم|الربع القادم", re.I)),
    ("prescriptive", re.compile(r"\b(should|recommend|recommendation|advice|prescriptive|"
                                r"what to do)\b|ينبغي|المفروض|تنصح|توصي|توصية|"
                                r"نعمل ايه|نعمل إيه", re.I)),
    ("experiment", re.compile(r"\b(causal|cause|caused|experiment)\b|سبب|سببي|"
                              r"تجربة", re.I)),
    ("descriptive", re.compile(r"\b(what happened|overview|summary|summari[sz]e)\b"
                               r"|ماذا حدث|اللي حصل|لخص|لخّص|ملخص", re.I)),
)
_START_RUN = re.compile(
    r"\b(analy[sz]e|analysis|run (an? |the )?(analysis|report|pipeline)|"
    r"(generate|produce|create|make|build|prepare|write|give me|start|begin|kick off|run|launch|fire off) (a |an |the |new )?"
    r"(report|analysis|study|run)|"
    # "take the track geometry file and work out ...": an action on a named file.
    r"(take|use|grab|load|open|pull up) (the |my |this |that |our )?(\w+ ){0,4}(file|data|dataset|sheet|spreadsheet|csv|export|log)s? and|examine|study|explore|dig into|look into|crunch|"
    r"put(ting)? together (a |an |the )?(\w+ )?(report|analysis)|go(ing)? through (the |my |this )?(\w+ ){0,3}(sheet|file|data|dataset|spreadsheet))\b"
    r"|(حلل|حلّل|حلّلي|حللي|تحليل|اعمل تحليل|إعمل تحليل|اعمل تقرير|اعملي تقرير|"
    r"أعد تقرير|أعدّ تقرير|جهز تقرير|جهّز تقرير|ابدأ تحليل|ابدأ التحليل|"
    r"إبدأ تحليل|شغل تحليل|شغّل تحليل|شغل التحليل|ادرس|إدرس|افحص|إفحص|"
    # "شغّل لي دراسة", "سوّ لي تقرير": run me a study, make me a report.
    r"(شغل|شغّل|ابدأ|إبدأ|اعمل|سو|سوّ|سوي|سوّي|جهز|جهّز)\s+(لي|لنا)\s+(تحليل|دراسة|تقرير))", re.I)
_REPORT_QUESTION = re.compile(
    r"\bwhat (does|did) the (report|analysis|model|forecast|results?) (say|show|recommend|suggest|"
    r"conclude|find|predict)\b|"
    r"\bwhat (does|did) the (\w+ )?(part|section|chapter|summary|page) (say|show|recommend|suggest|conclude|find)\b|"
    r"\b(quote|read( me| out)?|recite|repeat)\b.{0,40}\b(report|summary|section|findings|headlines?|"
    r"(descriptive|diagnostic|experiment|predictive|prescriptive) (bit|part|piece|section|chapter))\b|"
    r"(ماذا|وش|ايش|إيش|شو)\s+(قال|قالت|يقول|تقول|يقترح|تقترح)\s+(التوصيات|التشخيص|التنبؤ|الوصف|الملخص)|"
    r"(قسم|جزء)\s+(descriptive|diagnostic|experiment|predictive|prescriptive|الوصف|التشخيص|التنبؤ|التوصيات)|(بماذا|ماذا) (يوصي|توصي|يقول|يقترح) (التحليل|التقرير)|"
    r"(حسب|وفق|في) التقرير|أظهرها التقرير|أظهره التقرير|أظهر التقرير|يظهر التقرير|يُظهر التقرير|"
    r"التقرير بيقول|التقرير يقول|التقرير قال", re.I)
_SAMPLE_DATASET = re.compile(r"\bsample\b|النموذجي|النموذجية|التجريبي|التجريبية|العينة", re.I)


def _language_named(text):
    lowered = text.lower()
    for language, words in LANGUAGE_WORDS.items():
        if any(word in lowered for word in words):
            return language
    return None


def _tone_named(text):
    lowered = text.lower()
    for tone, words in TONE_WORDS.items():
        if any(re.search(r"(?<!\w)" + re.escape(word) + r"(?:اً|ا)?(?!\w)", lowered)
               for word in words):
            return tone
    return None


def section_for(text):
    """Which report section a question is about; "all" when it is general."""
    for section, pattern in _SECTION_HINTS:
        if pattern.search(text):
            return section
    return "all"


# Chat shorthand read as the words it stands for, before any rule: "wat
# commands do u understand", "pls forget". Only whole tokens change, so
# "u-bolt" and "urgent" stay as they are.
_SHORTHAND = [(re.compile(r"(?<![\w'-])" + short + r"(?![\w'-])", re.I), full) for short, full in (
    ("u", "you"), ("ur", "your"), ("r", "are"), ("pls", "please"), ("plz", "please"),
    ("wat", "what"), ("wut", "what"), ("whats", "what's"), ("thx", "thanks"), ("abt", "about"),
    ("cud", "could"), ("dont", "don't"), ("im", "I'm"),
)]


def _expand_shorthand(text):
    for pattern, full in _SHORTHAND:
        text = pattern.sub(full, text)
    return text


def understand(text):
    """A sentence → an intent, by rules.

    Returns the `chat` intent when nothing matches; the executor then
    answers honestly that it did not understand, and says what it can do.
    """
    # Rules read the expanded text; what is kept (a note, a goal, a name, a
    # search term) is taken from the person's own words when they match.
    original = str(text or "").strip()
    text = _expand_shorthand(original)
    if not text:
        return intent("chat")
    words = len(text.split())

    if _HELP.search(text):
        return intent("help")
    # "Remember to delete all the old files" is a note, not a deletion:
    # the anchored remember rule decides before any forget rule can.
    if _REMEMBER_BARE.match(text):
        return intent("remember", {"information": ""})
    match = _REMEMBER.match(original) or _REMEMBER.match(text)
    if match:
        info = match.group("info") or match.group("info_ar") or ""
        return intent("remember", {"information": info.strip(), "category": None})
    if _CLEAR_HISTORY.search(text):
        return intent("clear_history")
    # "Stop recording our conversation history" changes a setting; it deletes
    # nothing, so it is not clear_history, and it is not a request to forget.
    if _HISTORY_OFF.search(text):
        return intent("set_preference", {"key": "save_history", "value": "false"})
    if _HISTORY_ON.search(text):
        return intent("set_preference", {"key": "save_history", "value": "true"})
    match = _FORGET_KEY.search(text)
    if match:
        number = match.group("num") or match.group("num_ar")
        key = match.group("key") or match.group("key_ar") or f"memory_{number}"
        return intent("forget", {"key": key})
    match = _FORGET_ABOUT.search(original) or _FORGET_ABOUT.search(text)
    if match:
        about = (match.group("about") or match.group("about_ar")
                 or match.group("about_ar2") or "").strip()
        # "... عن خالد من الذاكرة", "... about pumps from your memory": the place is not the topic.
        about = re.sub(r"\s+(?:من|في)\s+(?:الذاكرة|ذاكرتك)$|\s+from (?:your |the )?memory$", "", about, flags=re.I)
        return intent("forget", {"key": None, "about": about})
    if _FORGET_ALL.search(text):
        return intent("forget", {"key": "all"})
    if _RECALL.search(text):
        query = None
        found = _RECALL_QUERY.search(original)
        if found:
            query = (found.group("q") or found.group("q_ar") or "").strip() or None
        return intent("recall", {"query": query})
    match = _NAME.search(original) or _NAME.search(text)
    if match:
        name = match.group("name") or match.group("name_ar")
        return intent("set_preference", {"key": "user_name", "value": name.strip()})
    # A language or tone word on its own ("arabic", "concise please") is a
    # request; inside a longer sentence it needs a verb of address, or "I
    # like Arabic coffee" would switch the interface.
    language = _language_named(text)
    if language and (words <= 2 or _LANGUAGE_VERB.search(text)):
        return intent("set_preference", {"key": "language", "value": language})
    tone = _tone_named(text)
    if tone and (words <= 2 or _TONE_VERB.search(text)):
        return intent("set_preference", {"key": "tone", "value": tone})
    # "Is the analysis done?" names the analysis and asks about it; the
    # question wins over the noun.
    if _RUN_STATUS.search(text):
        return intent("run_status")
    # Two server actions the rules did not reach before (assessment G8):
    # the knowledge base and the agents' scorecard.
    if _SCORECARD.search(text):
        suite = _SCORECARD_SUITE.search(text)
        return intent("agent_scorecard", {"suite": suite.group("suite").lower() if suite else None})
    if _SEARCH_KNOWLEDGE.search(text):
        found = _SEARCH_KNOWLEDGE_QUERY.search(text)
        query = (found.group("q") or found.group("q_ar") or "").strip() if found else ""
        return intent("search_knowledge", {"query": query or text, "collection": None})
    if _REPORT_QUESTION.search(text):
        return intent("explain_report", {"section": section_for(text)})
    if _START_RUN.search(text):
        dataset = "sample" if _SAMPLE_DATASET.search(text) else None
        return intent("start_run", {"goal": original, "dataset": dataset})
    if _EXPLAIN.search(text):
        return intent("explain_report", {"section": section_for(text)})
    return intent("chat")


# ---------------------------------------------------------------------------
# Execution of the actions that need only the Agent. The server adds the
# three that need the run engine.
# ---------------------------------------------------------------------------

def fallback(agent, text):
    """The honest "I did not understand", in the agent's tone and language."""
    tone = agent.preferences.get("tone", "friendly")
    if tone not in TONES:
        tone = "friendly"
    return reply(agent.language(), f"fallback_{tone}", request=text)


def execute_local(action, arguments, agent, text, model_reply=None):
    """Run one non-server action against the Agent and return the reply.

    Every confirmation here is the Agent's own sentence — the same one the
    slash command would produce — so a reply can never claim a save that
    did not happen. Only `chat` shows text a model wrote.
    """
    language = agent.language()
    arguments = arguments or {}
    if action == "help":
        return reply(language, "capabilities")
    if action == "remember":
        return agent.add_memory(str(arguments.get("information") or ""),
                                arguments.get("category"))
    if action == "recall":
        query = str(arguments.get("query") or "").strip().lower()
        entries = agent.memory_entries()
        if query:
            entries = [e for e in entries if query in e["text"].lower()]
            if not entries:
                return reply(language, "recall_none_match", query=query)
        if not entries:
            return agent.text("nothing_saved")
        return agent.text("saved_heading") + "\n" + "\n".join(
            f"{e['key']}: {e['text']}" for e in entries)
    if action == "forget":
        key = str(arguments.get("key") or "").strip()
        if not key and arguments.get("about"):
            # A description never deletes on its own: one match is confirmed
            # first (confirmation_prompt), so here the person picks.
            about = str(arguments["about"])
            matches = memories_about(agent, about)
            if not matches:
                return reply(language, "forget_none_match", about=about)
            return reply(language, "forget_which", about=about, first=matches[0],
                         entries="\n".join(f"{k}: {agent.memory[k]}" for k in matches))
        if key.lower() == "all":
            return agent.clear_all_memory()
        return agent.remove_memory(key)
    if action == "clear_history":
        agent.history.clear()
        return agent.text("history_cleared")
    if action == "set_preference":
        key = str(arguments.get("key") or "").strip().lower()
        value = arguments.get("value")
        if key not in PREFERENCE_KEYS:
            return reply(language, "unknown_preference")
        if key == "tone" and str(value).lower() not in TONES:
            return reply(language, "bad_tone")
        if key == "save_history" and isinstance(value, bool):
            value = "true" if value else "false"
        return agent.set_preference(key, str(value).strip())
    if action in SERVER_ONLY:
        return reply(language, "cli_needs_web")
    # chat: a model's phrasing if one answered, else the honest fallback.
    return (model_reply or "").strip() or fallback(agent, text)


def arguments_valid(action, arguments):
    """Whether arguments someone other than the rules produced — a model,
    an agent runtime, an MCP client — are ones the executor can act on.
    Normalises in place where a loose value has an obvious reading."""
    if action == "set_preference":
        key = str(arguments.get("key") or "").lower()
        if key not in PREFERENCE_KEYS:
            return False
        if key == "tone" and str(arguments.get("value") or "").lower() not in TONES:
            return False
    if action == "forget":
        key = str(arguments.get("key") or "")
        if key.lower() != "all" and not re.fullmatch(r"memory_\d+", key) \
                and not str(arguments.get("about") or "").strip():
            return False
    if action == "explain_report":
        section = arguments.get("section")
        if section is not None and section not in SECTIONS + ("all",):
            arguments["section"] = "all"
    if action == "remember" and not str(arguments.get("information") or "").strip():
        return False
    if action == "start_run" and not str(arguments.get("goal") or "").strip():
        return False
    return True


_STOP_WORDS = {"the", "about", "note", "notes", "memory", "that", "this", "with", "for", "and",
               "ملاحظة", "الملاحظة", "ذاكرة", "الذاكرة", "المتعلقة", "الخاصة", "التي"}


def _content_words(text):
    words = set()
    for word in re.findall(r"\w+", str(text).lower()):
        for prefix in ("وال", "بال", "لل", "ال", "و", "ب", "ل", "ف"):
            if re.match(r"[\u0621-\u064A]", word) and word.startswith(prefix) and len(word) - len(prefix) >= 3:
                word = word[len(prefix):]
                break
        if len(word) >= 3 and word not in _STOP_WORDS:
            words.add(word)
    return words


def memories_about(agent, about):
    """Keys of the memories a description points to: those holding at least
    half of its words (ADR 0027). Several matches are listed, never guessed."""
    wanted = _content_words(about)
    if not wanted:
        return []
    return [key for key, text in agent.memory.items()
            if len(wanted & _content_words(text)) * 2 >= len(wanted)]


def confirmation_prompt(action, arguments, agent):
    """The question asked before a destructive action runs."""
    language = agent.language()
    if action == "clear_history":
        return reply(language, "confirm_clear_history")
    if action == "forget" and not (arguments or {}).get("key") and (arguments or {}).get("about"):
        matches = memories_about(agent, arguments["about"])
        if len(matches) != 1:
            return None     # nothing to delete: the executor lists the matches
        arguments["key"] = matches[0]
    key = str((arguments or {}).get("key") or "").strip()
    if key.lower() == "all":
        return reply(language, "confirm_forget_all")
    text = agent.memory.get(key)
    if text is None:
        # Nothing to confirm: the executor will say the key does not exist.
        return None
    return reply(language, "confirm_forget_key", key=key, text=text)
