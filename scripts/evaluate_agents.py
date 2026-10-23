#!/usr/bin/env python3
"""Measure every classifying agent: confusion matrix, precision, recall and F1.

    python scripts/evaluate_agents.py                     # every suite: dev, holdout and blind
    python scripts/evaluate_agents.py --suite intent --misses   # what the dev cases got wrong
    python scripts/evaluate_agents.py --json out.json --html report.html
    python scripts/evaluate_agents.py --check             # exit 1 when a suite falls below its floor

Tier 0 of docs/AGENT_TEAM.md: no model, no tokens. Each suite in `evals/`
holds labelled cases in up to three splits:

- `dev`: cases used to find and fix misses;
- `holdout`: cases written at the same time as dev and scored before and
  after a fix. It is not blind for every suite. ADR 0056 records that when
  the Arabic causal patterns were written, dev was already at 100%, the
  only failing cases were in the causal holdout (v4), and those cases
  were read before the patterns were written; it calls the resulting 100%
  contaminated and says it must not be read as generalisation, which is
  why that floor stayed at 0.68. The intent and causal blind_v6 sets were
  moved into dev once the rules were fixed against them (2026-10-20), and
  so were their blind_v7 sets (2026-10-23), and the standards holdout was written by the same session that wrote the
  patterns. For those suites a holdout score is a second dev score;
- `blind`: the split named by the suite's `blind` entry in SUITES
  (causal and intent blind_v8, jargon blind_v6, standards blind_v3);
  blind_v7 moved into the causal and intent dev splits on 2026-10-23.
  Written by an agent from the label definitions only and never looked at
  while fixing a rule, so it is the score to quote. Once a blind set is
  used to fix rules it moves into dev and a new one is written.

`--misses` shows dev cases only. The floors in `evals/floors.json` are the
recall each suite must keep on every split it has, blind included;
`tests/test_evals.py` enforces them (ADR 0027). Standard library only.
"""

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
EVALS = ROOT / "evals"
THEME = ROOT / ".claude" / "skills" / "rta-style" / "tokens.css"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def confusion(pairs, labels):
    """{truth: {predicted: count}} over the given labels, plus any label a
    predictor produced that the suite does not list."""
    labels = list(labels)
    for _, predicted, _ in pairs:
        if predicted not in labels:
            labels.append(predicted)
    matrix = {t: {p: 0 for p in labels} for t in labels}
    for truth, predicted, _ in pairs:
        matrix[truth][predicted] += 1
    return labels, matrix


def scores(labels, matrix, positive=None):
    """Per-class precision, recall, F1 and support; accuracy; macro recall
    over the classes that occur. For a detector, `positive` names the class
    whose recall is the headline: the share of real cases it catches."""
    per_class, total, right = {}, 0, 0
    for label in labels:
        tp = matrix[label][label]
        support = sum(matrix[label].values())
        predicted = sum(matrix[t][label] for t in labels)
        precision = tp / predicted if predicted else None
        recall = tp / support if support else None
        f1 = (2 * precision * recall / (precision + recall)
              if precision and recall else (0.0 if support else None))
        per_class[str(label)] = {"precision": precision, "recall": recall, "f1": f1,
                                 "support": support, "predicted": predicted}
        total += support
        right += tp
    recalls = [c["recall"] for c in per_class.values() if c["support"]]
    out = {"per_class": per_class, "accuracy": right / total if total else None,
           "macro_recall": sum(recalls) / len(recalls) if recalls else None, "cases": total}
    if positive is not None:
        out["positive"] = str(positive)
        out["recall"] = per_class[str(positive)]["recall"]
        out["precision"] = per_class[str(positive)]["precision"]
    return out


# ---------------------------------------------------------------------------
# Predictors: each returns [(truth, predicted, what)] for a split
# ---------------------------------------------------------------------------

def _intent(cases):
    import assistant
    return [(c["label"], assistant.understand(c["text"])["action"], c["text"]) for c in cases]


NOTES = {}   # per-suite remarks a predictor wants printed (the model suite's fallbacks)


def _intent_model(cases, gateway=None):
    """The chat assistant as deployed: a configured model decides first and the
    rules decide when it is absent or its answer is not a valid intent
    (ADR 0019). Returns None, so the suite reads "not available", when no
    provider is configured: this environment, CI and any install without a
    key or a local model. Sentences are synthetic; nothing here is data.

    Opt-in: `--suite intent_model`. It sends every case to the provider, so it
    is never part of the default run, the floors or the agent loop.
    """
    import tempfile
    from contextlib import closing
    from agent import Agent
    from server.assistant import Assistant
    from server.model_gateway import ModelGateway
    from server.runs import RunEngine
    from server.storage import open_store

    gateway = gateway or ModelGateway()
    if not gateway.status().get("configured"):
        return None

    class Session:
        id, owner, transcript = "eval", "eval", []
        agent = Agent({"agent_name": "eval", "version": "1",
                       "preferences": {"language": "English", "tone": "friendly"}})

    out, fell_back = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        store = open_store(None, Path(tmp) / "eval.db")
        with closing(store):
            assistant = Assistant(gateway, RunEngine(store, Path(tmp) / "vault", gateway))
            for case in cases:
                understood = assistant.understand(case["text"], Session)
                fell_back += understood["source"] != "model"
                out.append((case["label"], understood["action"], case["text"]))
    NOTES["intent_model"] = (f"{fell_back} of {len(cases)} sentences were decided by the rules "
                             "(model absent, answer invalid, or privacy guard)")
    return out


def _tables(cases):
    from server import mapping
    for case in cases:
        columns, rows = mapping.table(case["csv"])
        yield case, columns, rows


def _roles(cases):
    from server import mapping
    out = []
    for case, columns, rows in _tables(cases):
        roles = mapping.suggest(columns, rows)["roles"]
        out += [(case["roles"][c], roles.get(c), f"{case['name']} · {c}") for c in columns]
    return out


def _personal(cases):
    from server import analytics
    out = []
    for case, columns, rows in _tables(cases):
        flagged = {f["column"] for f in analytics.personal_data_findings(columns, rows)}
        out += [(case["personal"][c], c in flagged, f"{case['name']} · {c}") for c in columns]
    return out


def _router(cases):
    from server import routing
    every = [{"provider": p} for p in ("ollama", "anthropic", "openai", "groq", "deterministic")]
    return [(c["label"], routing.provider_for(c["text"], every) or "none", c["text"] or "(empty)")
            for c in cases]


def _raw(cases):
    import consult
    return [(c["label"], consult.looks_like_raw_rows(c["text"]), c["text"][:60].replace("\n", " ⏎ "))
            for c in cases]


def _jargon(cases):
    from server import analytics
    return [(c["label"], bool(analytics._jargon_in(c["text"])), c["text"]) for c in cases]


def _causal(cases):
    try:
        import claims_lint
    except ImportError:
        return None   # no zero-cost causal check existed before ADR 0027
    return [(c["label"], bool(claims_lint.causal_phrases(c["text"])), c["text"]) for c in cases]


def _standards(cases):
    try:
        import standards_lint
    except ImportError:
        return None   # the standards lint arrived with ADR 0060
    return [(c["label"], bool(standards_lint.refuses(c["text"])), c["text"]) for c in cases]


def _figures(cases):
    """Each figure in a document is one item: bad ones should be flagged."""
    import figures_check as fc
    out = []
    for i, case in enumerate(cases):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            doc, ref = Path(tmp) / "doc.md", Path(tmp) / "ref.md"
            doc.write_text(case["doc"], encoding="utf-8")
            ref.write_text(case["reference"], encoding="utf-8")
            register = [{"label": k, "value": v} for k, v in case["register"].items()]
            result = fc.check(register, [doc], [ref], sourcing_only=True)
            text = fc.read_text(doc)
            flagged = {u["number"] for u in result["unsourced"]}
            flagged |= {w["result"] for w in result.get("wrong_arithmetic", [])}
            normal = {fc.normalise(b) for b in case["bad"]}
            universe = set(fc.numbers_in(text)) | normal
            for token in sorted(universe):
                truth = token in normal
                out.append((truth, token in flagged, f"case {i + 1} · {token}"))
    return out


SUITES = {
    "intent_model": {"file": "intent.json", "predict": _intent_model, "opt_in": True,
                     "agent": "Assistant with a model behind the rules: what a chat sentence asks for",
                     "module": "server/assistant.Assistant.understand"},
    # intent and causal are judged on blind_v8 (2026-10-23): blind_v7 moved into
    # dev that day when the rules were fixed against it, and blind_v8 was
    # written independently and scored once against the fixed rules.
    "intent": {"file": "intent.json", "predict": _intent, "blind": "blind_v8",
               "agent": "Assistant: what a chat sentence asks for", "module": "assistant.understand"},
    "column_roles": {"file": "datasets.json", "predict": _roles, "agent": "Column mapping: each column's role",
                     "module": "server/mapping.suggest"},
    "personal_data": {"file": "datasets.json", "predict": _personal, "positive": True,
                      "labels": [True, False], "agent": "Privacy Agent: columns holding personal data",
                      "module": "server/analytics.personal_data_findings"},
    "router": {"file": "router.json", "predict": _router, "agent": "Model router: which provider a model name means",
               "module": "server/routing.provider_for"},
    "raw_guard": {"file": "raw_guard.json", "predict": _raw, "positive": True,
                  "agent": "Raw-data guard: rows that must not reach a model", "module": "scripts/consult.looks_like_raw_rows"},
    "jargon": {"file": "jargon.json", "predict": _jargon, "positive": True, "blind": "blind_v6",
               "agent": "Validator: statistical jargon in claims", "module": "server/analytics._jargon_in"},
    "causal": {"file": "causal.json", "predict": _causal, "positive": True, "blind": "blind_v8",
               "agent": "Claims lint: causal wording in deliverables", "module": "scripts/claims_lint.causal_phrases"},
    "figures": {"file": "figures.json", "predict": _figures, "positive": True, "labels": [True, False],
                "agent": "Figures check: unsourced or wrong figures", "module": "scripts/figures_check.check"},
    "standards": {"file": "standards.json", "predict": _standards, "positive": True, "blind": "blind_v3",
                  "agent": "Standards lint: what a reporting standard would refuse",
                  "module": "scripts/standards_lint.refuses"},
}


def default_suites():
    """The suites a plain run, the floors and the agent loop cover."""
    return [name for name, spec in SUITES.items() if not spec.get("opt_in")]


SPLITS = ("dev", "holdout", "blind")


def run_suite(name, extra_splits=()):
    """Score a suite on dev, holdout and, when the suite declares one, its
    blind split (stored under "blind", with the set's name in "split" and in
    the result's "blind_split"). Extra splits are stored under their own
    names."""
    spec = SUITES[name]
    data = json.loads((EVALS / spec["file"]).read_text(encoding="utf-8"))
    labels = spec.get("labels") or data["labels"]
    blind = spec.get("blind")
    result = {"suite": name, "agent": spec["agent"], "module": spec["module"], "about": data.get("about", ""),
              "blind_split": blind}
    splits = ["dev", "holdout"] + (["blind"] if blind else [])
    splits += [x for x in extra_splits if x in data and x not in splits and x != blind]
    for split in splits:
        pairs = spec["predict"](data[blind if split == "blind" else split])
        if pairs is None:
            result[split] = None
            continue
        all_labels, matrix = confusion(pairs, labels)
        result[split] = {"split": blind if split == "blind" else split,
                         "labels": [str(l) for l in all_labels],
                         "matrix": {str(t): {str(p): n for p, n in row.items()} for t, row in matrix.items()},
                         **scores(all_labels, matrix, spec.get("positive")),
                         "misses": [{"item": what, "truth": str(t), "predicted": str(p)}
                                    for t, p, what in pairs if t != p]}
    if name in NOTES:
        result["notes"] = NOTES[name]
    return result


def headline(split):
    """The recall a suite is judged by: positive-class recall for a
    detector, macro recall for a multi-class agent."""
    if not split:
        return None
    return split.get("recall") if "positive" in split else split.get("macro_recall")


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def pct(value):
    return "–" if value is None else f"{value:.0%}"


def split_label(result, split):
    """How a split is named in print: the blind split carries its set's name."""
    return f"blind ({result['blind_split']})" if split == "blind" else split


def print_results(results, misses):
    for r in results:
        print(f"\n{r['suite']} · {r['agent']} ({r['module']})")
        for split in [k for k in r if k != "blind_split" and (k in SPLITS or k.startswith("blind_"))]:
            s, label = r[split], split_label(r, split)
            if s is None:
                print(f"  {label:8} not available (no model provider is configured)"
                      if r["suite"] == "intent_model" else f"  {label:8} not available")
                continue
            kind = f"recall {pct(s['recall'])}, precision {pct(s['precision'])}" if "positive" in s \
                else f"macro recall {pct(s['macro_recall'])}"
            print(f"  {label:8} {s['cases']:3} cases · accuracy {pct(s['accuracy'])} · {kind}")
        if r.get("notes"):
            print(f"  note: {r['notes']}")
        if misses and r["dev"]:
            for m in r["dev"]["misses"]:
                print(f"    MISS  {m['item']}: expected {m['truth']}, got {m['predicted']}")


BENCHES = {"A": "A · dev", "B": "B · held out", "C": "C · blind"}


def matrix_table(labels, matrix, caption):
    peak = max([max(row.values()) for row in matrix.values()] + [1])
    head = "".join(f"<th scope='col'>{html.escape(str(p))}</th>" for p in labels)
    body = ""
    for t in labels:
        if t not in matrix or not sum(matrix[t].values()):
            continue
        cells = "".join(f"<td class='{'hit' if t == p else ('miss' if n else '')}' style='--w:{n / peak:.2f}'>{n}</td>"
                        for p, n in matrix[t].items())
        body += f"<tr><th scope='row'>{html.escape(str(t))}</th>{cells}</tr>"
    return (f"<div class='scroll'><table class='cm'><caption>{html.escape(caption)}</caption>"
            f"<thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table></div>")


def render_reviewers(rows):
    """The reviewer benchmark (evals/reviewers): every saved run, and the
    category confusion of each controlled run."""
    if not rows:
        return ""
    table = "".join(
        f"<tr><td>{html.escape(r['agent'])}</td><td>{BENCHES.get(r['bench'], r['bench'])}</td>"
        f"<td>{html.escape(r['tag'])}</td><td class='num'>{pct(r['recall'])}</td>"
        f"<td class='num'>{pct(r['detection']['recall'])}</td><td class='num'>{pct(r['detection']['precision'])}</td>"
        f"<td class='num'>{len(r['false_alarms'])}</td></tr>" for r in rows)
    cards = "".join(
        f"<div class='card'><h3>{html.escape(r['agent'])} · {BENCHES.get(r['bench'], r['bench'])} · {r['tag']}</h3>"
        f"<p class='kpi'>Lane recall <b>{pct(r['recall'])}</b> · false alarms {len(r['false_alarms'])}</p>"
        + matrix_table(r["category_confusion"]["labels"], r["category_confusion"]["matrix"],
                       "Rows: the planted defect. Columns: what the reviewer called it.") + "</div>"
        for r in rows if r["tag"].startswith("ctl-") or r["agent"] == "figures-tool")
    return f"""<section><h2>Reviewers on seeded memos</h2>
<p class="muted">Three synthetic memos with planted defects (<code>evals/reviewers/</code>): A was used to choose fixes, B is held out
(same author), C was written blind by an independent agent. <b>ctl</b> runs give a model of the reviewer's tier the v1 or v2
instructions, with nothing else changed; <b>named</b> runs are the project subagents as loaded. Scored by <code>scripts/score_review.py</code>.</p>
<div class="scroll"><table class="cm runs"><thead><tr><th>Reviewer</th><th>Memo</th><th>Run</th><th>Lane recall</th>
<th>Detection recall</th><th>Detection precision</th><th>False alarms</th></tr></thead><tbody>{table}</tbody></table></div>
<div class="grid">{cards}</div></section>"""


def _pill(value):
    """A recall as a status pill: 90% and over good, 75% and over fair, else weak."""
    if value is None:
        return "–"
    kind, word = (("good", "good") if value >= 0.9 else ("warn", "fair") if value >= 0.75 else ("bad", "weak"))
    return f"<span class='pill pill--{kind}'>{pct(value)} · {word}</span>"


def render_glance(results):
    rows = "".join(
        f"<tr><th scope='row'>{html.escape(r['agent'])}</th><td><code>{html.escape(r['module'])}</code></td>"
        f"<td>{_pill(headline(r['dev']))}</td><td>{_pill(headline(r['holdout']))}</td>"
        f"<td class='num'>{r['holdout']['cases'] if r['holdout'] else '–'}</td>"
        f"<td>{_pill(headline(r.get('blind')))}</td>"
        f"<td class='num'>{r['blind']['cases'] if r.get('blind') else '–'}</td>"
        f"<td>{html.escape(r.get('blind_split') or '–')}</td></tr>" for r in results)
    return f"""<section><h2>At a glance</h2>
<p class="muted">Headline recall: the share of real cases each agent gets right (macro recall for agents with several labels).
Dev cases were used to find fixes. Holdout cases were written with dev and are not blind for every suite: the causal
holdout was read while its fixes were chosen (ADR 0056) and the standards holdout was written by the session that wrote
the patterns. The blind set was written from the label definitions only and never looked at while fixing; it is the score to quote.</p>
<div class="scroll"><table class="cm runs"><thead><tr><th>Agent</th><th>Module</th><th>Dev</th><th>Holdout</th>
<th>Holdout cases</th><th>Blind</th><th>Blind cases</th><th>Blind set</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""


def render_html(results, reviewers=None):
    """The report as one page, in the house style (.claude/skills/rta-style)."""
    css = THEME.read_text(encoding="utf-8") if THEME.exists() else ""
    parts = [render_glance(results)]
    for r in results:
        cards = []
        for split in SPLITS:
            if split == "blind" and not r.get("blind_split"):
                continue
            s, label = r[split], split_label(r, split)
            if s is None:
                cards.append(f'<div class="card"><h3>{label}</h3><p class="muted">Not available before ADR 0027.</p></div>')
                continue
            labels = s["labels"]
            peak = max(max(row.values()) for row in s["matrix"].values()) or 1
            head = "".join(f"<th scope='col'>{html.escape(p)}</th>" for p in labels)
            body = ""
            for t in labels:
                if not sum(s["matrix"][t].values()) and not any(s["matrix"][x][t] for x in labels):
                    continue
                cells = "".join(
                    f"<td class='{'hit' if t == p else ('miss' if n else '')}' style='--w:{n / peak:.2f}'>{n}</td>"
                    for p, n in s["matrix"][t].items())
                rec = s["per_class"][t]["recall"]
                body += f"<tr><th scope='row'>{html.escape(t)}</th>{cells}<td class='num'>{pct(rec)}</td></tr>"
            kind = (f"Recall <b>{pct(s['recall'])}</b> · precision {pct(s['precision'])}" if "positive" in s
                    else f"Macro recall <b>{pct(s['macro_recall'])}</b>")
            cards.append(f"""<div class="card"><h3>{label} · {s['cases']} cases</h3>
<p class="kpi">{kind} · accuracy {pct(s['accuracy'])}</p>
<div class="scroll"><table class="cm"><caption>Rows: true label. Columns: predicted. Last column: recall.</caption>
<thead><tr><th></th>{head}<th scope='col'>Recall</th></tr></thead><tbody>{body}</tbody></table></div></div>""")
        parts.append(f"""<section><h2>{html.escape(r['agent'])}</h2>
<p class="muted"><code>{html.escape(r['module'])}</code> · {html.escape(r['about'])}</p>
<div class="grid">{''.join(cards)}</div></section>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Agentic OS evaluation</title>
<style>{css}
.cm{{border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:.85rem}}
.cm th,.cm td{{border:1px solid var(--border);padding:.3rem .5rem;text-align:center}}
.cm caption{{caption-side:bottom;font-size:.75rem;color:var(--muted);text-align:start;padding-top:.3rem}}
.cm td.hit{{background:color-mix(in srgb,var(--status-good) calc(var(--w)*45%),transparent)}}
.cm td.miss{{background:color-mix(in srgb,var(--brand) calc(20% + var(--w)*40%),transparent);color:var(--text)}}
.scroll{{overflow-x:auto}} .kpi b{{font-size:1.2rem}}
.cm.runs td{{text-align:start}} .cm.runs td.num{{text-align:end}}
</style></head><body><header class="brandbar"><div class="page"><p class="org">Agentic OS · agent evaluation</p>
<h1>Confusion matrices and recall</h1><p class="period">Every classifying agent, on labelled dev, holdout and blind cases. Synthetic data only.</p></div></header>
<main class="page">{''.join(parts)}{render_reviewers(reviewers)}</main></body></html>"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--suite", action="append", choices=sorted(SUITES), help="one suite (repeatable)")
    parser.add_argument("--split", action="append", default=[],
                        help="also score a named extra split, such as holdout_v3 (repeatable)")
    parser.add_argument("--misses", action="store_true", help="list the dev cases each suite got wrong")
    parser.add_argument("--json", help="write the full results here")
    parser.add_argument("--html", help="write the report page here")
    parser.add_argument("--check", action="store_true", help="exit 1 when a suite is below its floor")
    args = parser.parse_args(argv)
    results = [run_suite(name, args.split) for name in (args.suite or default_suites())]
    print_results(results, args.misses)
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    if args.html:
        import score_review
        Path(args.html).write_text(render_html(results, score_review.summary()), encoding="utf-8")
    if args.check:
        floors = json.loads((EVALS / "floors.json").read_text(encoding="utf-8"))
        broken = [f"{r['suite']} {split_label(r, split)}: {pct(headline(r.get(split)))} < {pct(floors[r['suite']][split])}"
                  for r in results for split in SPLITS
                  if r["suite"] in floors and split in floors[r["suite"]]
                  and (headline(r.get(split)) or 0) + 1e-9 < floors[r["suite"]][split]]
        for line in broken:
            print(f"BELOW FLOOR  {line}", file=sys.stderr)
        return 1 if broken else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
