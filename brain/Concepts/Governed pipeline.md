---
type: concept
aliases: [Specialist pipeline, Analytics pipeline]
tags: [architecture, agents]
status: active
updated: 2026-10-23
review_every_days: 30
sources: [server/analytics.py, server/datasets.py, server/joins.py, docs/AGENT_CATALOG.md, docs/PROJECT_CHARTER.md, docs/adr/0009-hermes-and-the-specialist-roster.md, docs/adr/2026-10-22-release-gate-slice-two.md, docs/adr/2026-10-22-release-gate-slice-three.md, docs/adr/2026-10-23-p2-slice-one.md]
---

# Governed pipeline

How [[Agentic OS]] analyses a dataset: specialist stages in a defined order, each contributing a distinct result. The [[Hermes orchestrator]] sequences them, and the [[Approval gate]] closes the run.

## The stages, in order

1. **Preparing the data:** planner, data source, data contract, profiling, quality, privacy, cleaning, metric governance, preparation, and segment concentration.
2. **The four analytics types:** descriptive (what happened?), diagnostic (why?), predictive (what will happen?) and prescriptive (what should I do?). They run as a maturity ladder, with experiment and causal inference, anomaly detection and sensitivity testing between them.
3. **Making it trustworthy:** visualisation, provenance, independent validation and reporting.
4. **Publishing:** an approval-gated task that writes to the vault.

## Rules that make it governed

- A claim without evidence, or written in statistical jargon, fails validation.
- Association is never reported as cause; causal claims need a control and a treatment group.
- Every figure names its measure and its owner through the metric glossary, and follows [[Weighted KPIs]].
- Runs are durable: they can be paused, cancelled and resumed after a crash.
- A rate is never summed, trended or ranked; every forecast is backtested against repeating the last period and called weak when it does not beat it; every figure in a claim must appear in the evidence it cites (release-gate slice two, 22 October 2026).
- Uplift and cost are inputs, not assumptions: a run may state them per target, every option says whether its improvement was stated or assumed, and the sensitivity stage reports the flip point when the ranking is a close call. The Analytics form collects them and the run view shows the decision record (22 October).
- A last period holding fewer records than three quarters of the busiest earlier period is left out of the forecast and the anomaly check and declared as incomplete (23 October).

## Limits

Runs accept the supported upload formats and can combine datasets through declared [[Dataset joins]]. The selected measure, breakdown and dates govern the report view; domain models have their own input contracts. A completed run does not establish future-failure prediction or independent maintenance-domain acceptance. The [[Analytics OS roadmap]] separates implemented features from those remaining acceptance gates.

## Related

- [[Custom stages]]: how a domain stage joins the same audit.
- [[Decision log]]: decisions 0007, 0009, 0010 and 0011 shaped the pipeline.
- [[Data quality contracts]]: defines the input assumptions each stage must check.
- [[Evidence and claims]]: connects computed results to statements a reviewer can inspect.
