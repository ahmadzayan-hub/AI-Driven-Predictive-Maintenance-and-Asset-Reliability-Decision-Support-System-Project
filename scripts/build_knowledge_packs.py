#!/usr/bin/env python3
"""Build the RMD V2 knowledge packs from the two owner-supplied handover files.

    python scripts/build_knowledge_packs.py --mba PATH --analytics PATH [--check]

Each handover is split on its level-two headings into one Markdown file per
section, every section carrying a `<!-- kb: ... -->` directive (domain,
evidence status, synthetic flag, limits, superseded status) that the loader
in `server/knowledge.py` turns into retrieval metadata (ADR 2026-11-05).

Two outputs per handover:

* `knowledge/<id>/`, the public departmental copy. Owner-only sections are
  left out and a redaction guard fails the build if an identifier, a link to
  a private file library or a credential-shaped string survives.
* `private/knowledge/<id>-complete/` (git-ignored), the whole handover for
  the local owner. Retrieval filters cannot protect Git history, so anything
  the owner wants kept off a public repository lives only here.

Nothing is fabricated: the builder moves text, it never writes a fact. The
Arabic cards in `ARABIC_CARDS` restate figures that exist verbatim in the
source and are checked against it by `tests/test_rmd_knowledge_packs.py`.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT / "knowledge"
PRIVATE_DIR = ROOT / "private" / "knowledge"

SECTION = re.compile(r"^## (.*\S)\s*$")
H3 = re.compile(r"^### (.*\S)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")

# Nothing matching these may appear in a public pack.
FORBIDDEN = (
    (re.compile(r"24224008"), "registration number"),
    (re.compile(r"ABD\s+ELHAKAM", re.I), "full legal name"),
    (re.compile(r"chatgpt\.com/library"), "private file-library link"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "email address"),
    (re.compile(r"\b(?:sk|pk|ghp|xox[bp])[-_][A-Za-z0-9]{16,}"), "credential-shaped string"),
    (re.compile(r"(?i)\b(password|api[_ -]?key|secret)\s*[:=]\s*\S+"), "credential assignment"),
)
LIBRARY_LINK = re.compile(r"\[([^\]]+)\]\(https://chatgpt\.com/library[^)]*\)")

LIMITS_SYNTHETIC = "synthetic_educational_data|not_validated_prediction|not_operational_rmd"
LIMITS_ACADEMIC = "academic_case|not_rmd_operational_rule"
LIMITS_HISTORICAL = "historical_not_current_verification"

# Section number or key -> (file slug, directive). Longest key wins.
MBA_PLAN = {
    "00": ("start-here", "domain=meta.handover"),
    "01": ("evidence-model", "domain=meta.evidence"),
    "02": (None, None),  # owner profile: private copy only
    "03": ("course-control", f"domain=mba.9227.course; limits={LIMITS_ACADEMIC}"),
    "04": ("textbook-map", f"domain=mba.9227.theory; limits={LIMITS_ACADEMIC}"),
    "05": ("assessment-requirements", f"domain=mba.9227.course; limits={LIMITS_ACADEMIC}"),
    "06": ("g02-identity", f"domain=mba.9227.g02; limits={LIMITS_ACADEMIC}"),
    "07": ("g02-evidence", f"domain=mba.9227.g02; limits={LIMITS_ACADEMIC}"),
    "08": ("g02-final-requirements", f"domain=mba.9227.g02; limits={LIMITS_ACADEMIC}"),
    "09": ("g02-early-warning-p75", f"domain=mba.9227.g02.p75; limits={LIMITS_ACADEMIC}"),
    "10": ("g02-zapier-workflow", f"domain=mba.9227.g02.workflow; limits={LIMITS_ACADEMIC}|{LIMITS_HISTORICAL}"),
    "11": ("g02-solution-selection", f"domain=mba.9227.g02; limits={LIMITS_ACADEMIC}"),
    "12": ("g02-pilot-roadmap", f"domain=mba.9227.g02.pilot; limits={LIMITS_ACADEMIC}"),
    "13": ("financial-lessons", f"domain=mba.9227.g02.finance; limits={LIMITS_ACADEMIC}"),
    "14": ("correction-register", "domain=mba.9227.corrections"),
    "15": ("individual-assignment", f"domain=mba.9227.individual; evidence=DOCUMENT_REPORTED_RESULT; limits={LIMITS_ACADEMIC}"),
    "16": ("operating-model", f"domain=mba.9227.theory; limits={LIMITS_ACADEMIC}"),
    "17": ("decision-methods", f"domain=mba.9227.theory; limits={LIMITS_ACADEMIC}"),
    "18": ("rmd-destination", "domain=rmd.product; evidence=HISTORY_REPORTED; limits=requirements_not_current_functionality"),
    "19": ("rmd-proposed-applications", "domain=rmd.proposed; evidence=PROPOSED_APPLICATION; limits=proposal_not_approved_rule"),
    "20": ("knowledge-record-contract", "domain=rmd.product; evidence=PROPOSED_APPLICATION"),
    "21": ("claude-code-integration", "domain=rmd.product; evidence=PROPOSED_APPLICATION"),
    "22": ("implementation-stages", "domain=rmd.product; evidence=PROPOSED_APPLICATION"),
    "23": ("acceptance-questions", "domain=rmd.product.acceptance"),
    "24": ("implementation-prompt", "domain=rmd.product; evidence=PROPOSED_APPLICATION"),
    "25": ("missing-evidence", "domain=meta.gaps; status=unresolved"),
    "26": ("source-register", "domain=meta.sources"),
    "27": ("maintenance-status", "domain=meta.maintenance"),
}
MBA_SUBSECTIONS = (
    (re.compile(r"^09\.3\b"), "status=superseded; evidence=SUPERSEDED"),
)

ANALYTICS_PLAN = {
    "0": ("start-here", "domain=meta.handover"),
    "1": ("scope-and-evidence", "domain=meta.evidence"),
    "2": ("project-and-course-control", f"domain=analytics.9226.course; limits={LIMITS_ACADEMIC}"),
    "3": ("business-decision", f"domain=analytics.9226.decision; limits={LIMITS_ACADEMIC}"),
    "4": ("dataset-schema", f"domain=analytics.9226.dataset; synthetic=true; limits={LIMITS_SYNTHETIC}"),
    "5": ("verified-calculations", f"domain=analytics.9226.kpi; synthetic=true; evidence=CALCULATED; limits={LIMITS_SYNTHETIC}"),
    "6": ("data-quality", f"domain=analytics.9226.quality; synthetic=true; limits={LIMITS_SYNTHETIC}"),
    "7": ("modelling-prioritisation", f"domain=analytics.9226.model; synthetic=true; limits={LIMITS_SYNTHETIC}"),
    "8": ("rmd-proposed-capability", "domain=rmd.proposed; evidence=PROPOSED; limits=proposal_not_approved_rule"),
    "9": ("handover", "domain=rmd.product; evidence=PROPOSED"),
    "10": ("historical-context", f"domain=analytics.9226.history; evidence=HISTORICAL; limits={LIMITS_HISTORICAL}"),
    "11": ("open-decisions", "domain=meta.gaps; evidence=UNRESOLVED; status=unresolved"),
    "12": ("source-register", "domain=meta.sources"),
    "A": ("appendix-a-concepts", f"domain=analytics.9226.theory; limits={LIMITS_ACADEMIC}"),
    "B": ("appendix-b-lectures", f"domain=analytics.9226.course; limits={LIMITS_ACADEMIC}"),
    "C": ("appendix-c-books", f"domain=analytics.9226.theory; limits={LIMITS_ACADEMIC}"),
    "D": ("appendix-d-acceptance", "domain=rmd.product.acceptance"),
    "E": ("appendix-e-data-profile", f"domain=analytics.9226.dataset; synthetic=true; evidence=CALCULATED; limits={LIMITS_SYNTHETIC}"),
    "END": ("end", "domain=meta.handover"),
}
ANALYTICS_SUBSECTIONS = ()

# Restated figures, each present verbatim in the source (checked by the tests).
ARABIC_CARDS = {
    "mba": (
        "## بطاقة: قاعدة الإنذار المبكر وقيم P75 (حالة G02)\n"
        "<!-- kb: domain=mba.9227.g02.p75; lang=ar; limits=academic_case|not_rmd_operational_rule -->\n\n"
        "قيم P75 المعتمدة في حالة المجموعة G02 هي: RJ14 وBA20 وCE21 يوماً. "
        "القيم المؤقتة السابقة (8 و12 و10) حلّت محلها هذه القيم ولا تُستخدم كإجابة حالية. "
        "الشحنة تُعدّ مخالفة إذا تأخر التسليم أو كانت الأيام المتبقية أقل من P75 للولاية؛ "
        "التساوي ليس مخالفة. هذه حالة أكاديمية للتجارة الإلكترونية وليست قاعدة تشغيلية في RMD.\n"
    ),
    "analytics": (
        "## بطاقة: حدود البيانات الاصطناعية (المجموعة 9226)\n"
        "<!-- kb: domain=analytics.9226.dataset; synthetic=true; lang=ar; "
        "limits=synthetic_educational_data|not_validated_prediction|not_operational_rmd -->\n\n"
        "مجموعة البيانات اصطناعية وتعليمية (5000 سجل و60 عموداً). نتائجها ودرجات الأولوية فيها "
        "ليست تنبؤات مُتحقَّقاً منها بالأعطال المستقبلية ولا تمثل أداء تشغيلياً فعلياً في RMD. "
        "الحالة التاريخية للمشروع ليست تحققاً حالياً.\n"
    ),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def slug_key(heading, plan):
    """The plan key a level-two heading belongs to, or None."""
    match = re.match(r"^(\d+)\.", heading)
    if match:
        number = match.group(1)
        return number.zfill(2) if "00" in plan else number
    match = re.match(r"^Appendix ([A-E])\b", heading)
    if match:
        return match.group(1)
    if heading.lower().startswith("end of knowledge"):
        return "END"
    return None


def split_sections(text):
    """(preamble, [(heading, body_lines)]) split on level-two headings."""
    preamble, sections, current, fenced = [], [], None, False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        found = None if fenced else SECTION.match(line)
        if found:
            current = [found.group(1), []]
            sections.append(current)
        elif current is None:
            preamble.append(line)
        else:
            current[1].append(line)
    return preamble, [(h, b) for h, b in sections]


def with_subsection_directives(body, subsections):
    """Insert a directive under each matching level-three heading."""
    if not subsections:
        return body
    out, fenced = [], False
    for line in body:
        out.append(line)
        if FENCE.match(line):
            fenced = not fenced
            continue
        found = None if fenced else H3.match(line)
        if found:
            for pattern, directive in subsections:
                if pattern.match(found.group(1)):
                    out.append(f"<!-- kb: {directive} -->")
    return out


LEGAL_NAME = re.compile(r"Ahmed\s+Abd\s+Elhakam\s+Abd\s+Elfattah\s+Zaian", re.I)


def redact(text):
    """Public wording: working name only, no private library links."""
    text = LEGAL_NAME.sub("Ahmed Zaian", text)
    return LIBRARY_LINK.sub(r"\1 (private file; see the owner's library)", text)


def guard(files):
    """Fail the build if any public file holds something that must not ship."""
    problems = []
    for name, text in files.items():
        for pattern, what in FORBIDDEN:
            for hit in pattern.finditer(text):
                line = text.count("\n", 0, hit.start()) + 1
                problems.append(f"{name}:{line}: {what}")
    if problems:
        raise SystemExit("Redaction guard failed:\n  " + "\n  ".join(problems))


def build_collection(source, kind, plan, subsections, meta):
    text = Path(source).read_text(encoding="utf-8")
    preamble, sections = split_sections(text)
    public, private_lines, order = {}, list(preamble), []
    for heading, body in sections:
        key = slug_key(heading, plan)
        slug, directive = plan.get(key, (None, None)) if key else (None, None)
        if key is None:
            raise SystemExit(f"Unplanned section in {kind}: {heading!r}")
        block = with_subsection_directives(body, subsections)
        marker = f"<!-- kb: {directive} -->" if directive else ""
        private_lines += [f"## {heading}"] + ([marker] if marker else []) + block
        if slug is None:
            continue
        name = f"{len(order) + 1:02d}_{slug}.md"
        order.append(name)
        public[name] = redact("\n".join(
            [f"## {heading}", marker, ""] + block).rstrip() + "\n")
    cards = ARABIC_CARDS[kind]
    public["AR_CARDS.md"] = cards
    manifest = dict(meta, passages_source=Path(source).name,
                    source_sha256=sha256(source),
                    withheld_sections=[h for h, _ in sections
                                       if plan.get(slug_key(h, plan), (0,))[0] is None])
    return public, "\n".join(private_lines) + "\n", manifest


def write(folder, files):
    folder.mkdir(parents=True, exist_ok=True)
    for stale in folder.glob("*.md"):
        if stale.name not in files and stale.name != "README.md":
            stale.unlink()
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mba", required=True)
    parser.add_argument("--analytics", required=True)
    parser.add_argument("--check", action="store_true",
                        help="build in memory and run the guard; write nothing")
    args = parser.parse_args(argv)

    jobs = (
        ("mba", args.mba, MBA_PLAN, MBA_SUBSECTIONS, "rmd-v2-mba-9227", {
            "title": "RMD V2 MBA 9227 project knowledge / معرفة مقرر 9227",
            "description": ("Evidence-labelled course knowledge for AI for Business Strategy "
                            "and Decision Making (9227). Academic cases only; none of it is an "
                            "RMD operational rule. Owner-only sections are withheld."),
            "document_id": "RMD_V2_MBA_9227_Project_Knowledge", "version": "1.0"}),
        ("analytics", args.analytics, ANALYTICS_PLAN, ANALYTICS_SUBSECTIONS,
         "rmd-v2-analytics-9226", {
            "title": "RMD V2 data analytics project knowledge / معرفة مشروع تحليلات البيانات",
            "description": ("Group 9226 analytics knowledge: synthetic educational dataset, "
                            "calculation register, data-quality limits and the proposed RMD V2 "
                            "capability. Synthetic scores are not validated predictions."),
            "document_id": "RMD_V2_Data_Analytics_Project_Knowledge", "version": "1.0",
            "synthetic": True}),
    )
    built = []
    for kind, source, plan, subsections, cid, meta in jobs:
        meta = dict(meta, visibility="public", data_classification="public",
                    model_context_allowed=False, prepared_on="2026-11-04",
                    evidence_basis="owner-supplied handover; evidence labels preserved per passage",
                    operational_authority=False)
        public, private_text, manifest = build_collection(source, kind, plan, subsections, meta)
        guard(public)
        built.append((cid, public, private_text, manifest))
    if args.check:
        print("Guard passed for", ", ".join(c for c, *_ in built))
        return 0
    for cid, public, private_text, manifest in built:
        write(PUBLIC_DIR / cid, public)
        (PUBLIC_DIR / cid / "collection.json").write_text(
            json.dumps(dict(manifest, collection_id=cid), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        private_manifest = dict(manifest, collection_id=f"{cid}-complete",
                                visibility="private", data_classification="confidential",
                                model_context_allowed=False,
                                title=manifest["title"] + " (complete, owner only)",
                                withheld_sections=[])
        private_folder = PRIVATE_DIR / f"{cid}-complete"
        write(private_folder, {"complete.md": private_text})
        (private_folder / "collection.json").write_text(
            json.dumps(private_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{cid}: {len(public)} public files, private copy at {private_folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
