#!/usr/bin/env python3
"""Measure the agents, record it, and say what needs a person.

Decision: docs/adr/2026-10-20-agent-measurement-loop.md.

    python scripts/agent_loop.py                  # one bounded loop: measure, compare, report
    python scripts/agent_loop.py status           # the latest scorecard and the trend
    python scripts/agent_loop.py watch --every 300   # keep measuring until interrupted
    python scripts/agent_loop.py propose --suite intent --label help --text "..." --source "reviewer"
    python scripts/agent_loop.py proposals        # pending proposed cases
    python scripts/agent_loop.py accept ID --by "Name"   # into the dev split only
    python scripts/agent_loop.py reject ID --by "Name"

Tier 0 of docs/AGENT_TEAM.md: no model, no tokens. It never changes a rule,
a floor or a holdout case. Exit status: 0 done, 1 below a floor or a
regression, 2 needs a person (misses or proposals waiting).
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from server import agent_learning as learning  # noqa: E402


def _pct(value):
    return "-" if value is None else f"{value:.0%}"


def print_card(card):
    print(f"Measured {card['at'][:19]} at {card.get('rev') or 'unknown revision'}")
    for row in card["rows"]:
        print(f"  {row['suite']:14} holdout {_pct(row['holdout']):>4} "
              f"(floor {_pct(row['holdout_floor']):>4})  dev {_pct(row['dev']):>4}")
    for finding in card["findings"]:
        print(f"  ATTENTION {finding['kind']}: {finding['suite']} {finding['split']}")
    for gap in card["gaps"]:
        print(f"  gap {gap['suite']}: dev {_pct(gap['dev'])} vs holdout {_pct(gap['holdout'])}"
              " (write fresh cases; do not tune to the holdout)")


def trend(ledger):
    records = ledger.records(limit=10)
    print(f"{len(records)} recent measurement(s) in {ledger.path}")
    for record in records:
        parts = [f"{name} {_pct((suite.get('holdout') or {}).get('recall'))}"
                 for name, suite in record["suites"].items()]
        print(f"  {record['at'][:19]}  {record.get('rev') or '-':12}  " + "  ".join(parts))


def loop_once(args):
    ledger = learning.Ledger()
    proposals = learning.Proposals()
    result = learning.AgentLoop(ledger=ledger, proposals=proposals,
                                max_rounds=args.rounds).run()
    card = learning.scorecard(ledger=ledger)
    print_card(card)
    order = result["work_order"]
    print(f"\nLoop state: {result['state']} after {len(result['rounds'])} round(s).")
    for name, suite in order["suites"].items():
        for miss in suite["dev_misses"]:
            print(f"  dev miss [{name}] {miss['item']}: expected {miss['truth']}, got {miss['predicted']}")
    if order["pending_proposals"]:
        print(f"  {order['pending_proposals']} proposed case(s) wait for a person: "
              "scripts/agent_loop.py proposals")
    blocking = [f for f in order["findings"] if f["kind"] != "dev_miss"]
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    if blocking:
        return 1
    return 0 if result["state"] == learning.DONE else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    run = sub.add_parser("run", help="one bounded loop (the default)")
    run.add_argument("--rounds", type=int, default=learning.MAX_ROUNDS)
    run.add_argument("--json")
    sub.add_parser("status")
    watch = sub.add_parser("watch")
    watch.add_argument("--every", type=int, default=300, help="seconds between measurements")
    watch.add_argument("--times", type=int, default=0, help="stop after this many (0 = until interrupted)")
    propose = sub.add_parser("propose")
    propose.add_argument("--suite", required=True)
    propose.add_argument("--label", required=True)
    propose.add_argument("--text", required=True)
    propose.add_argument("--source", required=True)
    propose.add_argument("--note", default="")
    sub.add_parser("proposals")
    for name in ("accept", "reject"):
        decide = sub.add_parser(name)
        decide.add_argument("id")
        decide.add_argument("--by", required=True, help="the person who decides")
    args = parser.parse_args(argv)
    command = args.command or "run"
    if command == "run" and not hasattr(args, "rounds"):
        args.rounds, args.json = learning.MAX_ROUNDS, None

    proposals = learning.Proposals()
    try:
        if command == "run":
            return loop_once(args)
        if command == "status":
            ledger = learning.Ledger()
            card = learning.scorecard(ledger=ledger)
            if card is None:
                print("The evaluation harness is not available here.")
                return 2
            print_card(card)
            trend(ledger)
            return 0
        if command == "watch":
            steward = learning.Steward(max(args.every, 1))
            done = 0
            while not args.times or done < args.times:
                findings = steward.tick()
                if findings is not None:
                    done += 1
                    print(f"{time.strftime('%H:%M:%S')} measured; {len(findings)} finding(s)", flush=True)
                time.sleep(min(args.every, 5))
            return 0
        if command == "propose":
            item = proposals.propose(args.suite, args.text, args.label, args.source, args.note)
            print(f"Queued {item['id']} for review.")
        elif command == "proposals":
            pending = proposals.pending()
            for item in pending:
                print(f"{item['id']}  [{item['suite']}] {item['label']}: {item['text']}  ({item['source']})")
            print(f"{len(pending)} pending.")
        elif command == "accept":
            item = proposals.accept(args.id, args.by)
            print(f"Accepted {item['id']} into the {item['suite']} dev split.")
        elif command == "reject":
            item = proposals.reject(args.id, args.by)
            print(f"Rejected {item['id']}.")
    except learning.ProposalError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
