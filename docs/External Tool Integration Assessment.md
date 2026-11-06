# External AI Tool Integration Assessment

Owner: Ahmed Zaian. Review: 6 November 2026.
Status: **assessment scaffolding only**, not installation, security approval, deployment, or production acceptance.

## Scope

The Instagram references are discovery signals rather than validated vendor claims.

| External capability | Best project | Isolated acceptance test |
| --- | --- | --- |
| Open Notebook | MIYAAR knowledge workspace | Citation fidelity, Arabic retrieval, data isolation |
| Book to Skill | MIYAAR and Hermes | Source traceability and retrieval precision against baseline |
| Strix | RMD V2 / MIYAAR | Authorized security testing of disposable synthetic environments only |
| OmniRoute | Hermes | Provider failover, latency, cost, local resource impact, no external disclosure |
| No AI Slop | AI with Zaian editorial review | Blind human review and Arabic/English style fidelity |
| OpenSEO | MIYAAR public research pages | Technical SEO without fabricated findings |

**No third-party repo is installed by this change.** No RTA data may be sent outside approved infrastructure.

## Test gate

Run `python scripts/ExternalToolAssessment.py "docs/External Tool Candidates.json"` from the repository root. Exit 2 means blocked; that is expected until security, licence, pinned revision and egress controls are verified. A passing gate only permits an isolated trial, not production integration.

Require an accountable human owner, a recorded licence, pinned revision SHA, dependency audit, supply-chain and prompt-injection review, documented data flows, a synthetic-only trial, rollback instructions and test logs. Never grant production write privileges. AI cannot authorize safety, procurement, contractual or maintenance decisions.

## Content pipeline

For AI with Zaian: source research → manually select idea → draft Arabic-first Instagram carousel → verify every number → linguistic/RTL and 360px review → human approval → publish. Reuse the process, not unverified audience growth claims.

## Instagram references

- https://www.instagram.com/p/DepqxTjk9mQ/
- https://www.instagram.com/p/DfXT9u4jPG9/
- https://www.instagram.com/p/DfYLHvxiN8F/
- https://www.instagram.com/p/DfXF3fEiL0u/

## Next engineering action

After independent security review, run a synthetic benchmark comparing candidate tools to existing application capabilities, log measurable value and operational overhead, and request a separate human approval for each integration.
