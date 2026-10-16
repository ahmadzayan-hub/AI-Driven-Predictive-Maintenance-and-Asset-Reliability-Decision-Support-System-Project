#!/usr/bin/env python3
"""Run every check this repository has, and say plainly what passed.

    python scripts/verify.py            # Python suite, brain, typecheck, unit tests, build, budget
    python scripts/verify.py --e2e      # ... and the Playwright end-to-end suite
    python scripts/verify.py --quick    # Python suite, brain, typecheck and unit tests only
    python scripts/verify.py --list     # print the steps; run nothing

It runs the same commands as CI (.github/workflows/ci.yml), plus the brain
check and the interface budget from docs/UI_PLAN.md, and prints one line per
step with the counts the tools reported. A failed step prints the end of its
output, and the script exits 1. Standard library only.

Set PG_TEST_URL (and REQUIRE_PG=1) to run the PostgreSQL tests too; without
it they skip, and the summary shows how many did.
"""

import argparse
import gzip
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
DIST = FRONTEND / "dist"

# The interface budget from docs/UI_PLAN.md §7, in kilobytes (1,000 bytes).
# Scripts and styles are measured gzipped, as they are sent; fonts as woff2,
# which is already compressed.
BUDGET_KB = {"js": 100, "css": 10, "fonts": 120}

ANSI = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class Step:
    name: str
    command: list
    cwd: Path = ROOT
    summarise: object = None
    groups: set = field(default_factory=lambda: {"full"})


def summarise_unittest(output):
    ran = re.search(r"Ran (\d+) tests?", output)
    skipped = re.search(r"skipped=(\d+)", output)
    if not ran:
        return ""
    text = f"{ran.group(1)} tests"
    return text + (f", {skipped.group(1)} skipped" if skipped else "")


def summarise_vitest(output):
    tests = re.search(r"^\s*Tests\s+(.+?)\s*$", ANSI.sub("", output), re.M)
    return tests.group(1) if tests else ""


def summarise_playwright(output):
    plain = ANSI.sub("", output)
    parts = [f"{m.group(1)} {m.group(2)}" for m in
             re.finditer(r"^\s*(\d+) (passed|failed|skipped|flaky)\b", plain, re.M)]
    return ", ".join(parts)


def summarise_brain(output):
    line = next((l for l in output.splitlines() if l.startswith("Brain:")), "")
    return line.removeprefix("Brain:").strip()


def measure_budget(dist):
    """Return {kind: kilobytes} for the built interface."""
    sizes = {"js": 0, "css": 0, "fonts": 0}
    for path in (dist / "assets").iterdir():
        if path.suffix == ".js":
            sizes["js"] += len(gzip.compress(path.read_bytes(), 9))
        elif path.suffix == ".css":
            sizes["css"] += len(gzip.compress(path.read_bytes(), 9))
        elif path.suffix == ".woff2":
            sizes["fonts"] += path.stat().st_size
    return {kind: round(total / 1000, 1) for kind, total in sizes.items()}


def check_budget(dist=DIST, budget=BUDGET_KB):
    """Return (ok, summary) for the built interface against the budget."""
    if not (dist / "assets").is_dir():
        return False, f"no build at {dist}; run the build step first"
    sizes = measure_budget(dist)
    over = [kind for kind, size in sizes.items() if size > budget[kind]]
    summary = ", ".join(f"{kind} {size} of {budget[kind]} KB" for kind, size in sizes.items())
    return not over, summary + (f"; over: {', '.join(over)}" if over else "")


def steps():
    npm = "npm.cmd" if os.name == "nt" else "npm"
    python = sys.executable
    return [
        Step("Python tests", [python, "-m", "unittest", "discover", "tests"],
             summarise=summarise_unittest, groups={"quick", "full", "e2e"}),
        Step("Brain check", [python, "scripts/brain_check.py", "--strict"],
             summarise=summarise_brain, groups={"quick", "full", "e2e"}),
        Step("Type check", [npm, "run", "typecheck"], cwd=FRONTEND,
             groups={"quick", "full", "e2e"}),
        Step("Frontend unit tests", [npm, "test"], cwd=FRONTEND,
             summarise=summarise_vitest, groups={"quick", "full", "e2e"}),
        Step("Production build", [npm, "run", "build"], cwd=FRONTEND, groups={"full", "e2e"}),
        Step("Interface budget", ["budget"], groups={"full", "e2e"}),
        Step("End-to-end tests", [npm, "run", "e2e"], cwd=FRONTEND,
             summarise=summarise_playwright, groups={"e2e"}),
    ]


def run(step):
    """Run one step; return (ok, detail, output, seconds)."""
    started = time.monotonic()
    if step.command == ["budget"]:
        ok, detail = check_budget()
        return ok, detail, detail, time.monotonic() - started
    env = dict(os.environ)
    if step.name == "End-to-end tests" and Path("/opt/pw-browsers/chromium").exists():
        env.setdefault("PLAYWRIGHT_EXECUTABLE_PATH", "/opt/pw-browsers/chromium")
    try:
        done = subprocess.run(step.command, cwd=step.cwd, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as error:
        return False, f"cannot run: {error}", str(error), time.monotonic() - started
    output = done.stdout + done.stderr
    detail = step.summarise(output) if step.summarise else ""
    return done.returncode == 0, detail, output, time.monotonic() - started


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--quick", action="store_true", help="skip the build, budget and end-to-end tests")
    mode.add_argument("--e2e", action="store_true", help="also run the Playwright suite")
    parser.add_argument("--list", action="store_true", help="print the steps and exit")
    args = parser.parse_args(argv)
    group = "quick" if args.quick else "e2e" if args.e2e else "full"
    chosen = [s for s in steps() if group in s.groups]

    if args.list:
        for s in chosen:
            if s.command == ["budget"]:
                print(f"{s.name:20} gzipped sizes of frontend/dist/assets against docs/UI_PLAN.md §7")
                continue
            where = "" if s.cwd == ROOT else f"  (in {s.cwd.relative_to(ROOT)})"
            print(f"{s.name:20} {' '.join(Path(c).name if i == 0 else c for i, c in enumerate(s.command))}{where}")
        return 0

    failed = []
    for s in chosen:
        print(f"… {s.name}", flush=True)
        ok, detail, output, seconds = run(s)
        mark = "PASS" if ok else "FAIL"
        print(f"{mark} {s.name:20} {seconds:6.1f}s  {detail}", flush=True)
        if not ok:
            failed.append(s.name)
            tail = "\n".join(output.rstrip().splitlines()[-40:])
            print("    " + tail.replace("\n", "\n    "))
    print()
    if failed:
        print(f"{len(failed)} of {len(chosen)} steps failed: {', '.join(failed)}")
        return 1
    print(f"All {len(chosen)} steps passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
