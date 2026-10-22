# Release gate, slice one: honest gains, no substituted models, an uncapped approval queue, announced loading, read-only CI token

Date: 2026-10-22 · Status: Accepted (assessment findings A3, G7, U1, U9, B15
in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the P1 list in
`docs/implementation/DELIVERY_ROADMAP.md`)

## Decisions

1. **The prescriptive gain is labelled an assumption (A3).** The recommendation
   claim and the prescriptive headline say the figure is illustrative at an
   assumed 10% change, in English and Arabic. The ranking itself is unchanged;
   taking the uplift and a cost as inputs is the next step
   (`docs/analytics/PRESCRIPTIVE_DECISION_FRAMEWORK.md`).
2. **No GPT name is routed to Groq (G7).** The aliases `gpt`, `gpt-4` and
   `gpt-4o` to Groq are removed; `gpt-oss` stays Groq's. A `gpt-*` name goes to
   OpenAI when it is reachable and is otherwise refused, as
   `docs/KNOWN_LIMITATIONS.md` promised. The router evaluation now lists OpenAI
   among the reachable providers and labels the two GPT cases `openai`. The
   router's holdout floor moves from 0.90 to 0.88 macro recall: accuracy is
   unchanged at 10 of 12, but the two cases that used to count as correct
   Groq routings were mislabelled, and without them the Groq class carries
   only its two long-standing misses (`llama-3.1-8b-instant`, `gemma2-9b-it`).
   Those misses are not fixed here, because changing the router to pass the
   holdout would be tuning against it (ADR 0056).
3. **The approval queue is never capped (U1).** `GET /api/runs?state=…` lists
   every run in that state up to 1,000, and the Approvals inbox asks for
   `awaiting_approval`. The plain listing keeps its page of 50.
4. **Every loading placeholder announces itself (U9).** Each `role="status"`
   container carries its label as visually hidden text, so screen readers
   read it; the visible skeletons are unchanged.
5. **CI runs with a read-only token (B15).** Both workflows declare
   `permissions: contents: read`.

## Verification

`tests/test_tenancy.py::ApprovalQueueNotCappedTestCase`;
`tests/test_routing.py` (a GPT name with no OpenAI is `None`);
`scripts/evaluate_agents.py --check` with the relabelled router cases;
the prescriptive tests in `tests/test_analytics.py`; frontend typecheck,
unit tests and the accessibility spec.
