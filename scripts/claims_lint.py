#!/usr/bin/env python3
"""Find sentences that claim a cause, in a deliverable that only has associations.

    python scripts/claims_lint.py --doc report.pdf --doc deck.pptx
    python scripts/claims_lint.py --doc report.md --json findings.json

Tier 0 of docs/AGENT_TEAM.md: no model, no tokens. Observational data
supports "goes with", "is higher where" and "accounts for", not "drives",
"causes" or "leads to". The capstone review's two blockers were both of
this kind, so the review loop runs this check before a reviewer reads a
word (ADR 0027). It finds wording, not truth: a sentence it flags may be
backed by a controlled comparison, and then it is accepted in the plan.
English and Arabic. Exits 0 when nothing is found, 1 otherwise.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CAUSAL = [
    # "Drive the train to the shed" operates a vehicle; it claims nothing.
    re.compile(r"\b(drives?|drove|driven|driving)\b(?!\s+(?:the |a |an |this |that |each |our |their )?(?:\w+\s+)?"
               r"(?:train|tram|car|vehicle|bus|truck|locomotive|metro|shuttle|loco|engine|trolley|unit|set)s?\b)"
               r"(?!\s+(?:to|into|along|past|through|down|over|on|off|out|back|home)\b)", re.I),
    re.compile(r"\b(caus(e|es|ed|ing))\b", re.I),
    re.compile(r"\b(lead|leads|led|leading) to\b", re.I),
    re.compile(r"\b(result|results|resulted|resulting) in\b", re.I),
    re.compile(r"\b(because of|due to|owing to)\b", re.I),
    re.compile(r"\b(prolongs?|prolonged)\b", re.I),
    # "Stockouts double outages" claims an effect; "double the downtime" compares.
    re.compile(r"\b(doubles?|doubled|triples?|tripled)\b(?!\s+the\b)", re.I),
    # Arabic puts the subject between the verb and its "إلى": "أدى نقص المخزون إلى".
    re.compile(r"(أدى|أدت|يؤدي|تؤدي|أدّى|أدّت)\s+(?:\S+\s+){0,7}(إلى|الى)|بسبب|تسبب|تسبّب|يسبب|يسبّب"),
    re.compile(r"\b(contribut(es|ed|ing)|produc(es|ed)|trigger(s|ed)|spark(s|ed)|set(s)? off)\b", re.I),
    # Attribution: "was responsible for", "is to blame for", "the reason for". A bare
    # "behind" is left out: "the record was behind the tree" reports a lag.
    re.compile(r"\b(is|are|was|were|been|being)\s+(?:\w+ly\s+)?(responsible for|to blame for|"
               r"the (?:reason|source|root cause|origin|driver|culprit) (?:for|of|behind))\b", re.I),
    # Phrasal and nominal forms: "brought about", "gave rise to", "as a result of", "stems from".
    re.compile(r"\b(brought|bring|brings|bringing) about\b|\b(give|gives|gave|given|giving) rise to\b|"
               r"\bas a (result|consequence) of\b|\bin consequence of\b|\b(consequence|upshot) of\b|"
               r"\bstem(s|med|ming)? from\b|\bthanks to\b|\battributable to\b|\battributed to\b", re.I),
    re.compile(r"(ساهم|ساهمت|يساهم|تساهم|أسهم|أسهمت)\s+(?:\S+\s+){0,4}في|ينتج عن|نتج عن|نتيجة ل"),
    # "نتج عطل الإشارة عن تسرب", "ناتج عن", "ناجماً عن": the origin may follow other words.
    re.compile(r"(نتج|نتجت|ينتج|تنتج|ناتج|ناتجة|ناتجا|ناتجاً|ناجم|ناجمة|ناجما|ناجماً|نجم|نجمت|ينجم|تنجم)\s+(?:\S+\s+){0,6}?عن\b"),
    # Attribution of blame or origin: "هو المسؤول عن", "السبب في", "السبب وراء".
    re.compile(r"(المسؤول|المسؤولة|المسئول|المسئولة|المتسبب|المتسببة)\s+(?:\S+\s+){0,2}?(عن|في)\b|السبب\s+(في|وراء|الرئيسي|الأساسي)"),
    # A transitive effect verb: "the discount increased orders" claims an
    # effect; "orders increased 15%" or "increased by 15%" only reports a change.
    re.compile(r"\b(increase[sd]?|reduce[sd]?|decrease[sd]?|boost(s|ed)?|raise[sd]?|lower(s|ed)?|"
               r"improve[sd]?|worsen(s|ed)?|cut(s)?|lift(s|ed)?)\s+(?!(by|to|from|in|on|at|over|during|after|"
               r"before|across|between|with|than|for|of|and|or|but)\b(?!-))(?!\w+ly\b)(?![\d$%(])\w+", re.I),
    # "Lead times are pushing stockouts up": a force on a measure.
    re.compile(r"\b(push(es|ed|ing)?|drag(s|ged|ging)?|pull(s|ed|ing)?)\s+(?:\w+\s+){1,3}(up|down)\b", re.I),
    # Arabic subject-verb-object: "خفض الساعات يقلل التكاليف". A verb that opens
    # the sentence, or is followed by a preposition, only reports a change.
    # A prefix joins the verb in writing: "و" (and), "ف" (so), and the colloquial "ب" of
    # "بيقلل". "يسوي" and "يخلي" (makes) are the Gulf and Egyptian causatives.
    re.compile(r"\S+\s+(?:\S+\s+){0,6}[وف]?ب?(يقلل|تقلل|يقلّل|تقلّل|يزيد|تزيد|يزود|تزود|يرفع|ترفع|يخفض|تخفض|يخفّض|تخفّض|"
               r"يحسن|تحسن|يحسّن|تحسّن|يسوي|تسوي|يخلي|تخلي|يخلّي|تخلّي)\s+(?!(في|خلال|بنسبة|عن|على|إلى|الى|حتى)\s)(?:من\s+)?\S+"),
    # Arabic attributes a cause by returning to it: "يعود التراجع إلى نقص البيانات".
    re.compile(r"(يعود|تعود|يرجع|ترجع|يُعزى|تُعزى|يعزى|تعزى)\s+(?:\S+\s+){0,7}(إلى|الى)"),
    # "جاء نتيجة تحديث النظام": a result attributed to a thing. The older rule
    # had only "نتيجة ل"; the noun may follow directly or after "عن".
    re.compile(r"نتيجة\s+(?!(لذلك|لهذا|ذلك|هذا)\b)(?!(الاختبار|اختبار|الفحص|فحص|التحليل|القياس|قياس|الاستطلاع|الاقتراع|الامتحان|المباراة|"
               r"الفحوصات|الاختبارات|المعايرة|القراءة|الحساب|التدقيق)\b)(?:ل|عن\s+)?\S+"),
    # The Arabic counterpart of the English "pushes X up".
    re.compile(r"(يدفع|تدفع|دفع|دفعت)\s+(?:\S+\s+){0,5}(إلى|الى)\s+"
               r"(الأعلى|الاعلى|الأسفل|الاسفل|الارتفاع|الانخفاض|التراجع|الصعود|الهبوط)"),
    # English nominalised cause: "the impact of the new rule was a 15-minute cut"
    # asserts the effect the intervention produced.
    # "The impact of the outage is still being assessed" reports a status, so the
    # complement must assert an effect rather than defer one.
    re.compile(r"\bthe\s+(impact|effect|consequence|upshot)\s+of\b(?:\s+\S+){0,8}?\s+"
               r"(was|is|has been|were|are)\s+"
               r"(?!(still|not|yet|unclear|unknown|under|being|hard|difficult|impossible)\b)", re.I),
    # Arabic verb-subject-object, the language's default order: "خفّض التدريب
    # الجديد زمن التوقف" claims an effect. The subject-verb-object rule above
    # requires a word before the verb, which is an English assumption - there a
    # sentence-opening verb is an imperative or a report. Here the verb opens,
    # the subject follows, and a further noun phrase is the thing acted on.
    # "زاد الإنتاج بنسبة 12%" and "زاد الإنتاج في الربع الأخير" stay out: what
    # follows the subject is a measure or a circumstance, so a change is being
    # reported. A second noun phrase instead means something was acted on.
    # Only the position right after the subject is tested - prepositions inside
    # the phrases themselves are ordinary Arabic ("التدريب الجديد على التشغيل").
    re.compile(r"^[وف]?(خفّض|خفض|قلّل|قلل|رفع|زاد|ضاعف|حسّن|حسن|أبطأ|ابطأ|سرّع|سرع|"
               r"عطّل|عطل|أطال|اطال|قصّر|قصر)\s+"
               r"(?!(في|خلال|بنسبة|بمقدار|عن|على|إلى|الى|حتى|من|بين)\s)\S+\s+"
               r"(?!(في|خلال|بنسبة|بمقدار|عن|على|إلى|الى|حتى|من|بين)\s)\S+"),
]
# Sentences about causation itself are not claims of it.
META = re.compile(
    r"\b(can ?not|can't|no finding|not)\s+(claim|prove|show|be stated as|establish|confirm)|"
    r"\bnot (what|a) caus|\bnot proof\b|\bassociation,? not\b|"
    r"\b(doesn't|does not|don't|do not|can't|cannot)\s+(tell|show|say|prove)\s+(us\s+)?(which|whether|if|what)\b|"
    r"لا يمكن (ادعاء|إثبات)|ليس سبباً|لم (يثبت|تثبت|يُثبت|تُثبت|يتضح)|لا (يثبت|تثبت|يدل على أن)|"
    # A hypothesis, or a question not yet tested, is not a claim (round 5 of ADR 0027).
    r"\bhypothes[ie]s\b|\bhypothesi[sz]e|\buntested\b|\bunproven\b|"
    r"\bnot (yet )?(checked|tested|verified|established|proven|confirmed)\b|"
    r"\b(check|checked|test|tested|know|knew|see|establish|determine|confirm)(ed)?\s+whether\b|"
    r"فرضية|لم (نختبر|يختبر|يُختبر|نتحقق)|نحتاج (لاختبار|إلى اختبار|الى اختبار)|قبل أن نستنتج", re.I)
SENTENCE = re.compile(r"[^.!?؟\n]+[.!?؟]?")


def causal_phrases(text):
    """[(phrase, sentence)] for each sentence that claims a cause."""
    found = []
    for match in SENTENCE.finditer(text):
        sentence = match.group(0).strip()
        # A question asks about a cause; it does not claim one.
        if not sentence or META.search(sentence) or sentence.endswith(("?", "؟")):
            continue
        for pattern in CAUSAL:
            hit = pattern.search(sentence)
            if hit:
                found.append((hit.group(0), sentence))
                break
    return found


def main(argv=None):
    import figures_check
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--doc", action="append", required=True, help="a document to read (repeatable)")
    parser.add_argument("--json", help="also write the findings here")
    args = parser.parse_args(argv)
    findings = []
    for doc in args.doc:
        try:
            text = figures_check.read_text(doc)
        except (OSError, RuntimeError) as error:
            print(f"claims_lint: {error}", file=sys.stderr)
            return 2
        findings += [{"doc": Path(doc).name, "phrase": p, "sentence": s} for p, s in causal_phrases(text)]
    for f in findings:
        print(f"  CAUSAL  {f['doc']}: “{f['phrase']}” in: {f['sentence'][:160]}")
    print(f"{len(findings)} sentence(s) claim a cause")
    if args.json:
        Path(args.json).write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
