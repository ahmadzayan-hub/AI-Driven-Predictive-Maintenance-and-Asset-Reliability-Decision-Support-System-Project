#!/usr/bin/env python3
"""Check the Moodle package before upload.

    python -I tools/check_package.py

Checks what can be checked from the files themselves: exactly three files,
the exact names the brief requires, the report's page count, the deck's
slide count, and that no highlighted placeholder is left in either source.
It also prints the four headline totals recomputed from the master, so the
person uploading can tick them against the report, deck and dashboard.

It cannot open the .pbix model; that check stays manual, against the 30
rows of Expected_Values.csv.
"""

import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset import WORKSPACE, load, total

REQUIRED = ["Group_9226_Team_3_Dashboard.pbix",
            "Group_9226_Team_3_Presentation.pptx",
            "Group_9226_Team_3_Report.pdf"]
HEADLINE = ["Failure_Count", "Downtime_Hours", "Maintenance_Cost_USD", "Production_Loss_USD"]
PLACEHOLDER = re.compile(r"\[Add:[^\]]*\]|\bTBD\b|\bXX\b|<<[^>]+>>")

results = []


def check(name, passed, detail=""):
    results.append(passed)
    print(f"{'PASS' if passed else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))


def pdf_pages(path):
    """Page count from the PDF's own page objects."""
    data = path.read_bytes()
    counts = [int(m) for m in re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", data)]
    return max(counts) if counts else len(re.findall(rb"/Type\s*/Page\b", data))


def main():
    folder = WORKSPACE / "deliverables"
    present = sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix != ".md")

    for name in REQUIRED:
        check(f"{name} present", (folder / name).is_file())
    extra = [n for n in present if n not in REQUIRED]
    check("no fourth file in deliverables/", not extra, f"extra: {extra}" if extra else "")

    report = folder / REQUIRED[2]
    if report.is_file():
        pages = pdf_pages(report)
        check("report is 20-25 pages", 20 <= pages <= 25, f"{pages} pages")

    deck = folder / REQUIRED[1]
    if deck.is_file():
        with zipfile.ZipFile(deck) as z:
            slides = [n for n in z.namelist()
                      if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        check("deck is 12-15 slides", 12 <= len(slides) <= 15, f"{len(slides)} slides")

    draft = WORKSPACE / "report" / "report_draft.md"
    if draft.is_file():
        hits = PLACEHOLDER.findall(draft.read_text(encoding="utf-8", errors="replace"))
        check("no placeholder left in report_draft.md", not hits,
              f"{len(hits)} found: {sorted(set(hits))[:4]}" if hits else "")

    slides_dir = WORKSPACE / "presentation" / "source" / "slides"
    if slides_dir.is_dir():
        hits = []
        for f in sorted(slides_dir.glob("*.html")):
            hits += [(f.name, h) for h in PLACEHOLDER.findall(f.read_text(encoding="utf-8", errors="replace"))]
        check("no placeholder left in the slide sources", not hits,
              f"{len(hits)} found: {hits[:3]}" if hits else "")

    print("\nThe four headline totals, recomputed from the master.")
    print("Tick each against the report, the deck and the dashboard:")
    rows = load()
    for c in HEADLINE:
        print(f"  [ ] {c:24s} {total(rows, c):>16,.0f}")
    print("\nStill manual: the .pbix opens on a second machine with its data,")
    print("and all 30 rows of powerbi-kit/Expected_Values.csv agree.")

    print(f"\n{sum(results)} of {len(results)} automatic checks pass.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
