#!/usr/bin/env python3
"""Find sentences a reporting standard would refuse, in a deliverable.

    python scripts/standards_lint.py --doc report.pdf --doc deck.pptx
    python scripts/standards_lint.py --doc report.md --json findings.json

Tier 0 of docs/AGENT_TEAM.md: no model, no tokens. The companion to
`claims_lint.py`, which finds claims of a cause; this one finds claims a
standard the project answers to would not accept. Five classes, each
from a published rule and each already named in the team's own
pre-submission gate:

- **Optimisation.** A ranking is not an optimum. ISO 55001 Clause 6 asks
  for asset management objectives and how decisions meet them; calling a
  priority order "optimal" or "optimised" asserts a solved allocation
  problem that no ranking solves.
- **Realised benefit.** A saving that has not happened is a proposal.
  "Saved", "reduced costs by" and "delivered savings" assert an outcome;
  "would save" and "is expected to save" do not.
- **Capitalisation.** IAS 16 sends day-to-day servicing and repairs to
  profit or loss (para 12) and treats a major inspection or overhaul as a
  component of its own. A total that mixes them, presented as one cost,
  is two different things added together.
- **Grain.** An observation is not an asset. A panel with repeated
  observations of the same asset makes "289 high-risk assets" false when
  the 289 counts rows.
- **Line of sight.** ISO 55001 Clause 6.2.1 expects a visible line from
  organisational objectives to the asset decision. A recommendation that
  names no objective, owner or measure is an instruction without a reason.

It finds **wording, not truth**: a flagged sentence may be correct and
accepted in the plan with a reason, exactly as the review gate accepts a
flagged figure. It is bilingual, English and Arabic. Exits 0 when nothing
is found, 1 otherwise.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SENTENCE = re.compile(r"[^.!?؟\n]+[.!?؟]?")

# The patterns are linguistic families, not the phrasings of the cases
# they were fixed on (blind sets v1 and v2, moved into dev on 23 October):
# each class names the idea and lets the words vary.

# English number words, for counts written out ("fifty-seven assets").
NUMBER_WORDS = (r"(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|"
                r"fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|"
                r"sixty|seventy|eighty|ninety|hundred|thousand)(?:[- ](?:one|two|three|four|five|"
                r"six|seven|eight|nine|hundred|thousand))*)")
COUNT = rf"(?:\d[\d,]*|{NUMBER_WORDS})"

# A ranking presented as a solved allocation.
OPTIMISATION = re.compile(
    r"\b(optimal|optimally|optimum|optimis(e|es|ed|ing)|optimiz(e|es|ed|ing)|"
    r"best possible|best achievable|"
    r"the best (allocation|schedule|plan|use|mix|order|arrangement|sequence|sequencing|roster|rota|split|ordering|combination)|"
    r"the best \w+ (the |a |any )?\w+ (can|could) (achieve|reach|manage|get|do)|"
    r"ideal (allocation|schedule|plan|mix|order|use|arrangement|sequence|roster)|"
    r"solved (allocation|schedule|plan|roster|rota|problem|assignment)|"
    r"(most|as) (efficient|effective|economical)( (spend|allocation|use|plan|schedule|order|arrangement))?( possible| as possible| achievable)|"
    r"perfect(ly)? (allocat|schedul|balanc|sequenc)\w*|"
    r"no (other|alternative) (order|ordering|schedule|arrangement|allocation|sequence|plan|roster) (could|would|can|will)|"
    r"(cannot|can't|could not|couldn't) be (improved|bettered|beaten)|as good as it gets|"
    r"maximis(e|es|ed|ing)|maximiz(e|es|ed|ing)|minimis(e|es|ed|ing)|minimiz(e|es|ed|ing))\b"
    r"|الأمثل|المثلى|أمثلية|الحل الأمثل|المثالي|المثالية|أكفأ|"
    r"أفضل (توزيع|جدول|خطة|استخدام|ترتيب|تسلسل|تخصيص|مزيج)|"
    r"(التوزيع|الجدول|الترتيب|التخصيص) المحلول|لا يوجد (ترتيب|جدول|توزيع|تخصيص) آخر|"
    r"لا يمكن تحسين|لا (يمكن|يُمكن) (تجاوزه|تجاوزها|التفوق عليه)", re.I)

# A benefit asserted as already obtained.
REALISED = re.compile(
    r"\b(saved|savings? of|delivered savings|achieved savings|realis(ed|ing) savings|"
    r"realiz(ed|ing) savings|(has|have|had) (already )?(paid for (it|them)sel(f|ves)|"
    r"saved|recovered|avoided)|paid for (it|them)sel(f|ves)|"
    r"(cut|reduced|lowered|trimmed|slashed|brought down) (the |its |our |their |a )?"
    r"(\w+ ){0,3}(costs?|bill|bills|invoices?|spend|spending|expenditure|outlay) by|"
    r"(knocked|took|taken|shaved|wiped|lopped|trimmed) (\S+ ){0,4}off (the |this |its |our |their |last )?"
    r"(\S+ ){0,3}(costs?|bill|bills|invoices?|spend|spending|expenditure|outlay|budget)|"
    r"(earned|made|won|got|clawed) back (its|the|their) (purchase price|price|cost|outlay|investment)|"
    r"recouped|(has|have|had) paid (it|them)sel(f|ves) back|"
    r"payback (was|has been|is) (reached|achieved|complete)|"
    r"cut costs? by|reduced costs? by|returned|recovered)\b"
    r"|وفّر(نا|ت)?|تم توفير|حقق(ت|نا)? (وفورات|توفيراً)|وفورات (فعلية|محققة)|"
    r"(خفّض|خفض|قلّص|قلص|خفّضت|قلّصت)(ت|نا)? [^.؟]{0,60}(التكاليف|تكاليف|فاتورة|الفاتورة|فواتير|الفواتير|الإنفاق|المصروفات|النفقات|نفقات)|"
    r"دفع تكلفته|استرد(ت|ّت)? |استعاد(ت)? (ثمنه|ثمنها|تكلفته|تكلفتها|سعره|سعرها)|"
    r"(غطّت|غطت|سدّدت|سددت) (ثمنه|ثمنها|تكلفته|تكلفتها)", re.I)

# A cost total that does not say how overhaul is treated: a maintenance
# cost word, a spend word and a money figure in one sentence.
COST_ACTIVITY = (r"(upkeep|maintenance|servicing|repair|repairs|overhaul|overhauls|refurbishment|renewal|"
                 r"refits?|rebuilds?|inspections?|restoration|keeping (the |its |our |their )?\w+ (fleet |assets |plant )?running|"
                 r"keep(ing)? (them|it) (going|running))")
SPEND_WORD = r"(spend|spending|spent|expenditure|costs?|outlay|outlays|bill|bills|budget|cash out|came to|totalled|totaled)"
MONEY = r"(aed|usd|sar|eur|gbp|qar|kwd|\$|€|£|million|billion|\d[\d,]*(\.\d+)?\s*(m|bn|k))\b"
CAPITALISATION = re.compile(
    r"\b(total (maintenance|repair|overhaul) (cost|costs|spend|expenditure)|"
    r"maintenance (cost|costs|spend|expenditure) of|"
    r"capitalis(e|ed)|capitaliz(e|ed)|capex|opex)\b"
    rf"|(?=.*\b{COST_ACTIVITY}\b)(?=.*\b{SPEND_WORD}\b)(?=.*{MONEY}).+"
    r"|إجمالي (تكاليف|تكلفة) (الصيانة|الإصلاح)|رسملة"
    r"|(?=.*(الصيانة|الإصلاح|الإصلاحات|العمرة|العمرات|الخدمة الدورية|الصيانة الدورية|الفحوص|الفحوصات|الترميم|الترميمات|التشغيل|تشغيل|الإبقاء على))"
    r"(?=.*(إنفاق|الإنفاق|تكاليف|تكلفة|مصروفات|نفقات|النفقات|ما أُنفق|أُنفق|أنفق|بلغ|بلغت|وصل|مجموع|إجمالي))(?=.*(درهم|ريال|دولار|مليون|ألف|يورو)).+", re.I)

# Saying how the cost is treated is what the standard asks for, so a
# sentence that says it is the compliant case rather than the breach.
TREATMENT = re.compile(
    r"\b(profit or loss|expensed|charged to|day[- ]to[- ]day|component|"
    r"depreciat(e|es|ed|ing)|derecognis(e|ed)|derecogniz(e|ed)|ias ?16|para(graph)? ?12|"
    r"split between|separately|of which .*(overhaul|capitalis|capitaliz)|"
    r"(overhaul|inspection) (is|was|being) (treated|capitalis|capitaliz|expensed))\b"
    r"|الأرباح والخسائر|مكوّن|إهلاك|تُرسمل|ترسمل|تُحمَّل|مفصولة|بشكل منفصل", re.I)

# A count of rows described as a count of things: a count, an asset noun
# within a few words, and a state or threshold anywhere in the sentence.
ASSET_NOUN = r"(assets?|equipments?|machines?|units?|vehicles?|trains?|escalators?|pumps?|motors?|cars?|lifts?)"
STATE = (r"(high[- ]risk|critical|overdue|failing|at[- ]risk|exceed\w*|above|over the|threshold|"
         r"band|alarm\w*|flagged|late|past due|due for|out of tolerance|breach\w*|"
         r"ceiling|limit|limits|cross\w*|beyond|outside|tripped|warning|fault\w*|defect\w*|"
         r"in the (red|amber)|red|amber|worst|need\w* (attention|repair|replacement|action|work)|"
         r"risk (class|category|group|band|tier)|(class|category|tier|group) [a-d1-5]\b)")
GRAIN = re.compile(
    rf"\b{COUNT}\s+(?:\w+\s+){{0,2}}?{ASSET_NOUN}\b(?=.*\b{STATE}\b)"
    rf"|\b{COUNT}\s+{STATE}\s+{ASSET_NOUN}\b"
    r"|(\d[\d,]*|[^ ]+ )\s*(أصول|أصلاً|أصل|معدات|معدة|وحدات|وحدة|مركبات|مركبة|قطارات|قطاراً|سلالم)"
    r"(?=.*(عالية المخاطر|عالية الخطورة|شديدة الخطورة|الخطورة|الخطرة|حرجة|الحرج|الحرجة|متأخرة|متأخر|"
    r"تجاوز|تجاوزت|تخطت|تخطى|الحد|السقف|إنذار|تحذير|خارج الحدود|خارج النطاق|معيبة|متعثرة|الفئة|فئة))", re.I)

# A recommendation with no objective, owner or measure attached.
RECOMMENDATION = re.compile(
    r"\b(we recommend|it is recommended|recommendation:|we (suggest|propose|advise)|"
    r"(is|are) (advised|suggested|proposed)|"
    r"(should|ought to|needs? to|must|has to|have to) (be )?"
    r"(prioritis|prioritiz|replac|overhaul|defer|bring|move|schedul|inspect|repair|renew|retir|go to|focus|start|stop|increase|reduce|accelerat|postpon|look|revisit|review|consider|re-?examin|shorten|lengthen|extend|tighten|relax)\w*|"
    r"it (would|might|may|could) be (sensible|wise|prudent|advisable|worthwhile|worth|reasonable|a good idea)|"
    r"(would|might|may) (do well|be well advised) to|"
    r"(is|are) worth (considering|looking at|revisiting|a look)|"
    r"we (urge|encourage|ask|call on|invite|would like)|"
    r"priority (should|ought to|must|needs to) (go|be given))"
    r"|نوصي|يوصى|يُقترح|نقترح|يقترح|ينبغي|يجب|يلزم|من الأفضل|من المستحسن|يُستحسن|يستحسن|من الحكمة|"
    r"حبذا|يحسن|من المفيد|ندعو|نحث|يجدر|من المناسب|يجب (إعطاء|تحديد) الأولوية", re.I)
LINE_OF_SIGHT = re.compile(
    r"\b(objective|objectives|goal|target|availability|reliability|downtime|cost|risk|safety|"
    r"owner|owns|accountable|responsible|manager|kpi|measure|measured|budget|deadline|by \d{4}|"
    r"within \d+|\d+ ?%|hours?)\b"
    r"|هدف|أهداف|مؤشر|المالك|المسؤول|الميزانية|يتولى|مدير|الجاهزية|السلامة|يقاس|%|ساعة|ساعات", re.I)

# Sentences about a rule are not breaches of it.
META = re.compile(
    r"\b(not|never|cannot|can ?not|must not|do(es)? not|without)\s+\w*\s*"
    r"(claim|assert|describ|present|call|report|mean|imply)"
    r"|\bis not an?\b|\bare not\b|\brather than\b|\binstead of\b|\bnot (individual|distinct|separate)\b"
    r"|\bnot (yet )?(realis|realiz|achiev|demonstrat|validat)|\b(projected|expected|estimated), not\b"
    r"|لا (يعني|يجوز|يمكن|تدّعي|تدعي|يدّعي)|ليس|وليست|وليس|بدلاً من|لم تتحقق|غير محققة", re.I)

CHECKS = (
    ("optimisation", OPTIMISATION,
     "a ranking presented as an optimum (ISO 55001 Cl. 6: objectives and how decisions meet them)"),
    ("realised_benefit", REALISED,
     "a benefit asserted as obtained rather than proposed"),
    ("capitalisation", CAPITALISATION,
     "a cost total that does not say how overhaul is treated (IAS 16 para 12)"),
    ("grain", GRAIN,
     "a count of observations described as a count of assets"),
)


# A decimal point does not end a sentence. Without this, "saved USD 4.2
# million" is quoted back as "saved USD 4." and the evidence for a
# finding is a fragment its author cannot recognise.
DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")
_DOT = chr(1)


def _sentences(text):
    guarded = DECIMAL.sub(_DOT, text)
    for match in SENTENCE.finditer(guarded):
        sentence = match.group(0).replace(_DOT, ".").strip()
        if sentence:
            yield sentence


def findings_in(text):
    """[(check, phrase, sentence)] for each sentence a standard would refuse."""
    found = []
    for sentence in _sentences(text):
        if META.search(sentence):
            continue
        for name, pattern, _ in CHECKS:
            hit = pattern.search(sentence)
            if hit and name == "capitalisation" and TREATMENT.search(sentence):
                continue
            if hit:
                found.append((name, hit.group(0), sentence))
                break
        else:
            # A recommendation is judged by what it carries, not by a phrase.
            if RECOMMENDATION.search(sentence) and not LINE_OF_SIGHT.search(sentence):
                found.append(("line_of_sight", RECOMMENDATION.search(sentence).group(0), sentence))
    return found


def refuses(text):
    """True when a standard would refuse something in `text`. The eval's hook."""
    return bool(findings_in(text))


def main(argv=None):
    import figures_check
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--doc", action="append", required=True, help="a document to read (repeatable)")
    parser.add_argument("--json", help="also write the findings here")
    args = parser.parse_args(argv)
    reasons = {name: why for name, _, why in CHECKS}
    reasons["line_of_sight"] = ("a recommendation with no objective, owner or measure "
                                "(ISO 55001 Cl. 6.2.1: line of sight)")
    findings = []
    for doc in args.doc:
        try:
            text = figures_check.read_text(doc)
        except (OSError, RuntimeError) as error:
            print(f"standards_lint: {error}", file=sys.stderr)
            return 2
        findings += [{"doc": Path(doc).name, "check": c, "phrase": p, "sentence": s}
                     for c, p, s in findings_in(text)]
    for f in findings:
        print(f"  {f['check'].upper():17} {f['doc']}: “{f['phrase']}” in: {f['sentence'][:140]}")
        print(f"  {'':17} why: {reasons[f['check']]}")
    print(f"{len(findings)} sentence(s) a standard would refuse")
    if args.json:
        Path(args.json).write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
