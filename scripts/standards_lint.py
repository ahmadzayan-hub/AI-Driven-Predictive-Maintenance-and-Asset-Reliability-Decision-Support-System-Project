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

# A ranking presented as a solved allocation.
OPTIMISATION = re.compile(
    r"\b(optimal|optimally|optimis(e|es|ed|ing)|optimiz(e|es|ed|ing)|"
    r"best possible|maximis(e|es|ed)|maximiz(e|es|ed)|minimis(e|es|ed)|minimiz(e|es|ed))\b"
    r"|الأمثل|المثلى|أمثلية|الحل الأمثل", re.I)

# A benefit asserted as already obtained.
REALISED = re.compile(
    r"\b(saved|savings? of|delivered savings|achieved savings|realis(ed|ing) savings|"
    r"realiz(ed|ing) savings|cut costs? by|reduced costs? by|"
    r"returned|recovered)\b"
    r"|وفّر(نا|ت)?|تم توفير|حقق(ت|نا)? وفورات|خفّض(ت|نا)? التكاليف", re.I)

# A cost total that does not say how overhaul is treated.
CAPITALISATION = re.compile(
    r"\b(total (maintenance|repair|overhaul) (cost|costs|spend|expenditure)|"
    r"maintenance (cost|costs|spend|expenditure) of|"
    r"capitalis(e|ed)|capitaliz(e|ed)|capex|opex)\b"
    r"|إجمالي (تكاليف|تكلفة) (الصيانة|الإصلاح)|رسملة", re.I)

# Saying how the cost is treated is what the standard asks for, so a
# sentence that says it is the compliant case rather than the breach.
TREATMENT = re.compile(
    r"\b(profit or loss|expensed|charged to|day[- ]to[- ]day|component|"
    r"depreciat(e|es|ed|ing)|derecognis(e|ed)|derecogniz(e|ed)|ias ?16|para(graph)? ?12)\b"
    r"|الأرباح والخسائر|مكوّن|إهلاك", re.I)

# A count of rows described as a count of things.
GRAIN = re.compile(
    r"\b\d[\d,]*\s+(high[- ]risk|critical|overdue|failing|at[- ]risk)\s+"
    r"(assets?|equipments?|machines?|units?)\b"
    r"|\d[\d,]*\s+(أصول|أصل|معدات|وحدات)\s+(عالية المخاطر|حرجة|متأخرة)", re.I)

# A recommendation with no objective, owner or measure attached.
RECOMMENDATION = re.compile(
    r"\b(we recommend|it is recommended|recommendation:|should (be )?(prioritis|prioritiz|replac|overhaul|defer)"
    r"|must (be )?(prioritis|prioritiz|replac|overhaul|defer))"
    r"|نوصي|يوصى|يجب (إعطاء|تحديد) الأولوية", re.I)
LINE_OF_SIGHT = re.compile(
    r"\b(objective|objectives|target|availability|downtime|cost|risk|safety|"
    r"owner|accountable|responsible|kpi|measure|budget|deadline|by \d{4})\b"
    r"|هدف|أهداف|مؤشر|المالك|المسؤول|الميزانية", re.I)

# Sentences about a rule are not breaches of it.
META = re.compile(
    r"\b(not|never|cannot|can ?not|must not|do(es)? not|without)\s+\w*\s*"
    r"(claim|assert|describ|present|call|report|mean|imply)"
    r"|\bis not an?\b|\bare not\b|\brather than\b|\binstead of\b"
    r"|\bnot (yet )?(realis|realiz|achiev|demonstrat|validat)"
    r"|لا (يعني|يجوز|يمكن)|ليس|بدلاً من", re.I)

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
