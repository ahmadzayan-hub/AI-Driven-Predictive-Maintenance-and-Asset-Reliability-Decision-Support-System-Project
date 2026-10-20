"""Agents that are measured again and again, and say when a person is needed.

Decision: docs/adr/2026-10-20-agent-measurement-loop.md.

`scripts/evaluate_agents.py` measures every classifying agent once. That
is a photograph. This module makes it a record and a loop:

- a **ledger**: every measurement appended as one line, so a regression
  is a comparison with the line before it rather than a feeling;
- a **comparison** against the recall floors and the previous line;
- a **work order**: what a person or a model-backed improver may act on;
- a **loop** that measures, compares and, when improvers are registered,
  lets them act and measures again. It stops at `done`, `needs_person`,
  `stalled` or `budget`, the same bounds as the review loop in
  docs/AGENT_TEAM.md (five rounds, two without gain);
- a **proposal queue** for new labelled cases that only a named person
  accepts, and only into the dev split.

What it deliberately does not do:

- It never writes or fits to a holdout case. The work order carries dev
  misses by text and holdout results as counts and label pairs only, so
  an improver cannot read the held-out sentences. Fitting rules to the
  holdout would turn the one honest number into another dev number
  (docs/KNOWN_LIMITATIONS.md item 6 records this already happening to
  causal wording).
- It never edits a rule, a floor or a suite by itself. Raising a floor
  and accepting a case are human acts.
- It never loops without a bound.

Standard library only, and no model is called here.
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
DEFAULT_LEDGER = ROOT / "data" / "eval-ledger.jsonl"
DEFAULT_PROPOSALS = ROOT / "data" / "eval-proposals.jsonl"

MAX_ROUNDS = 5
PATIENCE = 2
MAX_LEDGER_LINES = 2000
MAX_PENDING = 200
MAX_TEXT = 600
# A drop smaller than this between two measurements is rounding, not news.
REGRESSION_EPSILON = 0.005

# The suites whose cases are one sentence and one label, which a person can
# review at a glance, and whose file is exactly what `json.dumps(indent=1)`
# writes, so accepting a case changes one entry and nothing around it.
# `standards.json` is hand-formatted and is left out until it is normalised.
TEXT_SUITES = {
    "intent": "intent.json",
    "jargon": "jargon.json",
    "causal": "causal.json",
}

# The loop's states. Only `done` means nothing is left to do.
DONE, NEEDS_PERSON, STALLED, BUDGET = "done", "needs_person", "stalled", "budget"


def _now():
    return datetime.now(timezone.utc).isoformat()


def ledger_path(env=None):
    env = os.environ if env is None else env
    value = (env.get("AGENTIC_OS_EVAL_LEDGER") or "").strip()
    return Path(value).expanduser() if value else DEFAULT_LEDGER


def proposals_path(env=None):
    env = os.environ if env is None else env
    value = (env.get("AGENTIC_OS_EVAL_PROPOSALS") or "").strip()
    return Path(value).expanduser() if value else DEFAULT_PROPOSALS


def _harness():
    """The evaluation harness. It lives in scripts/, which a packaged
    deployment may not carry, so a missing one is a sentence, not a crash."""
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import evaluate_agents
    return evaluate_agents


def floors():
    path = EVALS / "floors.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# Measuring
# ---------------------------------------------------------------------------

def _split_record(harness, split, include_items):
    if not split:
        return None
    off_diagonal = [{"truth": t, "predicted": p, "count": n}
                    for t, row in split["matrix"].items()
                    for p, n in row.items() if n and t != p]
    off_diagonal.sort(key=lambda c: (-c["count"], c["truth"], c["predicted"]))
    record = {"cases": split["cases"], "recall": harness.headline(split),
              "accuracy": split["accuracy"], "misses": len(split["misses"]),
              "confusions": off_diagonal[:12], "matrix": split["matrix"]}
    if "positive" in split:
        record["precision"] = split.get("precision")
    if include_items:
        record["missed_items"] = list(split["misses"])
    return record


def measure(suites=None, harness=None, rev=None):
    """Run the suites and return one ledger record.

    A record keeps dev misses by item and holdout misses by count only: the
    ledger is read by improvers, and a held-out sentence in it would stop
    being held out.
    """
    harness = harness or _harness()
    names = list(suites or (harness.default_suites() if hasattr(harness, "default_suites") else harness.SUITES))
    record = {"at": _now(), "rev": rev or _git_rev(), "suites": {}}
    for name in names:
        result = harness.run_suite(name)
        record["suites"][name] = {
            "agent": result["agent"], "module": result["module"],
            "dev": _split_record(harness, result["dev"], include_items=True),
            "holdout": _split_record(harness, result["holdout"], include_items=False),
        }
    return record


def _git_rev():
    head = ROOT / ".git" / "HEAD"
    try:
        text = head.read_text(encoding="utf-8").strip()
        if text.startswith("ref: "):
            ref = ROOT / ".git" / text[5:]
            text = ref.read_text(encoding="utf-8").strip()
        return text[:12] or None
    except OSError:
        return None


# ---------------------------------------------------------------------------
# The ledger
# ---------------------------------------------------------------------------

class Ledger:
    """Append-only, one JSON object per line. A torn or hand-damaged line is
    skipped when reading rather than hiding every line after it."""

    def __init__(self, path=None):
        self.path = Path(path) if path else ledger_path()

    def append(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        self._trim()
        return record

    def _trim(self):
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        if len(lines) > MAX_LEDGER_LINES:
            keep = "\n".join(lines[-MAX_LEDGER_LINES:]) + "\n"
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(keep, encoding="utf-8")
            os.replace(tmp, self.path)

    def records(self, limit=None):
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and isinstance(value.get("suites"), dict):
                out.append(value)
        return out[-limit:] if limit else out

    def latest(self):
        records = self.records(limit=1)
        return records[0] if records else None


# ---------------------------------------------------------------------------
# Comparing
# ---------------------------------------------------------------------------

def compare(current, previous=None, floor_table=None):
    """What needs attention in `current`, as plain findings.

    kinds: `below_floor` (the contract in evals/floors.json is broken),
    `regression` (a headline fell since the previous record), `dev_miss`
    (a dev case is wrong, so a fix is possible and checkable). The gap
    between dev and holdout recall is reported as information elsewhere
    and never gates: a gap is the holdout doing its job.
    """
    floor_table = floors() if floor_table is None else floor_table
    findings = []
    for name, suite in current["suites"].items():
        for split in ("dev", "holdout"):
            now = suite.get(split)
            if not now or now.get("recall") is None:
                continue
            floor = (floor_table.get(name) or {}).get(split)
            if floor is not None and now["recall"] + 1e-9 < floor:
                findings.append({"kind": "below_floor", "suite": name, "split": split,
                                 "recall": now["recall"], "floor": floor})
            before = ((previous or {}).get("suites", {}).get(name) or {}).get(split)
            if before and before.get("recall") is not None \
                    and now["recall"] < before["recall"] - REGRESSION_EPSILON:
                findings.append({"kind": "regression", "suite": name, "split": split,
                                 "recall": now["recall"], "was": before["recall"]})
        dev = suite.get("dev") or {}
        if dev.get("misses"):
            findings.append({"kind": "dev_miss", "suite": name, "split": "dev",
                             "count": dev["misses"]})
    return findings


def generalisation_gaps(record):
    """Suites where dev recall is well above holdout recall, widest first.
    Information for a person writing fresh cases, not a failure."""
    gaps = []
    for name, suite in record["suites"].items():
        dev, holdout = suite.get("dev"), suite.get("holdout")
        if dev and holdout and dev.get("recall") is not None \
                and holdout.get("recall") is not None:
            gap = dev["recall"] - holdout["recall"]
            if gap > 0.05:
                gaps.append({"suite": name, "dev": dev["recall"],
                             "holdout": holdout["recall"], "gap": round(gap, 4)})
    return sorted(gaps, key=lambda g: -g["gap"])


def work_order(record, findings, proposals=None):
    """What an improver is allowed to see and act on."""
    suites = {}
    for name, suite in record["suites"].items():
        dev = suite.get("dev") or {}
        holdout = suite.get("holdout") or {}
        suites[name] = {
            "agent": suite["agent"], "module": suite["module"],
            "dev_misses": [{"item": m["item"], "truth": m["truth"],
                            "predicted": m["predicted"]}
                           for m in dev.get("missed_items", [])],
            "holdout": {"recall": holdout.get("recall"), "cases": holdout.get("cases"),
                        "misses": holdout.get("misses"),
                        "confusions": holdout.get("confusions", [])},
        }
    return {"at": record["at"], "rev": record.get("rev"), "findings": findings,
            "gaps": generalisation_gaps(record), "suites": suites,
            "pending_proposals": len(proposals.pending()) if proposals else 0,
            "rules": ["Fix a dev miss, then measure again.",
                      "Never read or copy a held-out sentence; fresh cases go through the proposal queue.",
                      "Raising a floor and accepting a case are a person's decision."]}


# ---------------------------------------------------------------------------
# The loop
# ---------------------------------------------------------------------------

def _score(record, findings):
    """Higher is better. Dev recall is the only part an improver can move on
    purpose, so it is the only part that counts as gain."""
    total = 0.0
    for suite in record["suites"].values():
        dev = suite.get("dev") or {}
        total += dev.get("recall") or 0.0
    penalty = len([f for f in findings if f["kind"] in ("below_floor", "regression")])
    return round(total - penalty, 6)


class AgentLoop:
    """Measure, compare, let improvers act, measure again, within bounds.

    `improvers` are callables taking the work order and returning how many
    changes they made (an int). A person, a script or a model-backed
    runtime can be one; with none registered the loop measures once and
    hands over, because nothing here can change a rule on its own.
    """

    def __init__(self, ledger=None, proposals=None, improvers=(), measure_fn=None,
                 max_rounds=MAX_ROUNDS, patience=PATIENCE, budget_seconds=None,
                 clock=time.monotonic):
        self.ledger = ledger if ledger is not None else Ledger()
        self.proposals = proposals
        self.improvers = list(improvers)
        self.measure = measure_fn or measure
        self.max_rounds = max(1, int(max_rounds))
        self.patience = max(1, int(patience))
        self.budget_seconds = budget_seconds
        self.clock = clock

    def run(self):
        started = self.clock()
        rounds, best, flat = [], None, 0
        state, order = BUDGET, None
        for number in range(1, self.max_rounds + 1):
            previous = self.ledger.latest()
            record = self.measure()
            self.ledger.append(record)
            findings = compare(record, previous)
            order = work_order(record, findings, self.proposals)
            score = _score(record, findings)
            rounds.append({"round": number, "score": score, "findings": len(findings)})
            if not findings and not order["pending_proposals"]:
                state = DONE
                break
            if not self.improvers:
                state = NEEDS_PERSON
                break
            flat = flat + 1 if best is not None and score <= best else 0
            best = score if best is None else max(best, score)
            if flat >= self.patience:
                state = STALLED
                break
            if self.budget_seconds is not None and self.clock() - started >= self.budget_seconds:
                state = BUDGET
                break
            changed = 0
            for improver in self.improvers:
                try:
                    changed += int(improver(order) or 0)
                except Exception as error:  # one failing improver must not end the loop
                    print(f"agent loop: improver failed: {error!r}", file=sys.stderr)
            if not changed:
                state = NEEDS_PERSON
                break
        return {"state": state, "rounds": rounds, "work_order": order}


# ---------------------------------------------------------------------------
# Proposals: fresh labelled cases, accepted only by a named person
# ---------------------------------------------------------------------------

class ProposalError(ValueError):
    pass


class Proposals:
    def __init__(self, path=None, evals_dir=None):
        self.path = Path(path) if path else proposals_path()
        self.evals_dir = Path(evals_dir) if evals_dir else EVALS

    def _all(self):
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict) and value.get("id"):
                out.append(value)
        return out

    def _write(self, items):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items),
                       encoding="utf-8")
        os.replace(tmp, self.path)

    def pending(self):
        return [p for p in self._all() if p["status"] == "pending"]

    def propose(self, suite, text, label, source, note=""):
        if suite not in TEXT_SUITES:
            raise ProposalError(f"Proposals are for one-sentence suites: {', '.join(TEXT_SUITES)}.")
        text = str(text or "").strip()
        if not text or len(text) > MAX_TEXT:
            raise ProposalError(f"A case is one sentence of 1 to {MAX_TEXT} characters.")
        if "\n" in text:
            raise ProposalError("A case is one sentence; rows and documents are not proposed.")
        if label not in self._labels(suite):
            raise ProposalError(f"{label!r} is not a label of {suite}.")
        if not str(source or "").strip():
            raise ProposalError("A proposal names its source.")
        items = self._all()
        if any(i["suite"] == suite and i["text"] == text and i["status"] == "pending"
               for i in items) or self._already_in_suite(suite, text):
            raise ProposalError("That sentence is already a case or already proposed.")
        if len([i for i in items if i["status"] == "pending"]) >= MAX_PENDING:
            raise ProposalError("The queue is full; review it first.")
        item = {"id": uuid.uuid4().hex[:10], "suite": suite, "text": text, "label": label,
                "source": str(source).strip()[:80], "note": str(note or "")[:200],
                "status": "pending", "at": _now()}
        items.append(item)
        self._write(items)
        return item

    def reject(self, proposal_id, by):
        return self._decide(proposal_id, by, "rejected")

    def accept(self, proposal_id, by):
        """Add the case to the suite's dev split. Never the holdout: a case
        written to be added is not independent of the people adding it."""
        item = self._find(proposal_id)
        if item["status"] != "pending":
            raise ProposalError(f"Proposal {proposal_id} is already {item['status']}.")
        if not str(by or "").strip():
            raise ProposalError("Accepting a case names the person who accepts it.")
        path = self.evals_dir / TEXT_SUITES[item["suite"]]
        data = json.loads(path.read_text(encoding="utf-8"))
        data["dev"].append({"text": item["text"], "label": item["label"]})
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return self._decide(proposal_id, by, "accepted")

    def _find(self, proposal_id):
        for item in self._all():
            if item["id"] == proposal_id:
                return item
        raise ProposalError(f"No proposal {proposal_id}.")

    def _decide(self, proposal_id, by, status):
        if not str(by or "").strip():
            raise ProposalError("A decision names the person who made it.")
        items = self._all()
        found = None
        for item in items:
            if item["id"] == proposal_id:
                if item["status"] != "pending":
                    raise ProposalError(f"Proposal {proposal_id} is already {item['status']}.")
                item.update(status=status, decided_by=str(by).strip()[:80], decided_at=_now())
                found = item
        if found is None:
            raise ProposalError(f"No proposal {proposal_id}.")
        self._write(items)
        return found

    def _labels(self, suite):
        data = json.loads((self.evals_dir / TEXT_SUITES[suite]).read_text(encoding="utf-8"))
        return data["labels"]

    def _already_in_suite(self, suite, text):
        data = json.loads((self.evals_dir / TEXT_SUITES[suite]).read_text(encoding="utf-8"))
        return any(case["text"] == text for key, cases in data.items()
                   if isinstance(cases, list) for case in cases
                   if isinstance(case, dict) and "text" in case)


# ---------------------------------------------------------------------------
# The steward: the worker's periodic measurement
# ---------------------------------------------------------------------------

MIN_INTERVAL = 60


def interval_from(env=None):
    """Seconds between measurements, or 0 for off (the default). A value
    below a minute is raised to a minute: the suites cost nothing but a
    measurement is not a heartbeat."""
    env = os.environ if env is None else env
    try:
        seconds = int(float(env.get("AGENTIC_OS_EVAL_INTERVAL_SECONDS") or 0))
    except ValueError:
        return 0
    return 0 if seconds <= 0 else max(seconds, MIN_INTERVAL)


class Steward:
    """Measures the agents every `interval` seconds inside the worker loop,
    records the result and reports what needs attention on stderr. It never
    changes anything, and one failing measurement never stops the worker."""

    def __init__(self, interval, ledger=None, measure_fn=None, clock=time.monotonic,
                 log=None):
        self.interval = interval
        self.ledger = ledger if ledger is not None else Ledger()
        self.measure = measure_fn or measure
        self.clock = clock
        self.log = log or (lambda text: print(text, file=sys.stderr, flush=True))
        self.last = None

    def due(self):
        return self.interval > 0 and (
            self.last is None or self.clock() - self.last >= self.interval)

    def tick(self):
        """Measure if due. Returns the findings, or None when not due."""
        if not self.due():
            return None
        self.last = self.clock()
        previous = self.ledger.latest()
        record = self.measure()
        self.ledger.append(record)
        findings = compare(record, previous)
        for finding in findings:
            if finding["kind"] != "dev_miss":
                self.log(f"agent evaluation: {finding['kind']} in {finding['suite']} "
                         f"({finding['split']})")
        return findings


# ---------------------------------------------------------------------------
# The scorecard the assistant and MCP clients read
# ---------------------------------------------------------------------------

def _round(value):
    """Four decimals. A 16-digit float in a tool reply reads as a phone number
    to the privacy guard (model_privacy), which would then withhold the whole
    scorecard from the model that asked for it."""
    return None if value is None else round(value, 4)


def scorecard(suite=None, ledger=None):
    """The latest measurement, compact enough to read aloud.

    Reads the ledger; with none, measures without recording, because a
    chat question must not write to the disk of a hosted deployment.
    Returns None when the harness is not part of this deployment.
    """
    ledger = ledger if ledger is not None else Ledger()
    record = ledger.latest()
    measured_now = False
    if record is None:
        try:
            record = measure()
        except ImportError:
            return None
        measured_now = True
    names = [suite] if suite and suite in record["suites"] else list(record["suites"])
    table = floors()
    rows = []
    for name in names:
        entry = record["suites"][name]
        rows.append({"suite": name, "agent": entry["agent"],
                     "dev": _round((entry.get("dev") or {}).get("recall")),
                     "holdout": _round((entry.get("holdout") or {}).get("recall")),
                     "holdout_floor": _round((table.get(name) or {}).get("holdout")),
                     "holdout_cases": (entry.get("holdout") or {}).get("cases"),
                     "confusions": (entry.get("holdout") or {}).get("confusions", [])[:3]})
    findings = [{k: _round(v) if isinstance(v, float) else v for k, v in f.items()}
                for f in compare(record, None, table) if f["kind"] != "dev_miss"]
    gaps = [{k: _round(v) if isinstance(v, float) else v for k, v in g.items()}
            for g in generalisation_gaps(record)]
    return {"at": record["at"], "rev": record.get("rev"), "measured_now": measured_now,
            "rows": rows, "findings": findings, "gaps": gaps}
