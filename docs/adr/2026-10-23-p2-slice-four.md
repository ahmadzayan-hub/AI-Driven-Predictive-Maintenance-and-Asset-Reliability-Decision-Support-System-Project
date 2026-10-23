# P2 slice four: screened inputs, probabilities with a Brier score, a bounded connection pool, structured model answers checked on the server, agreement by finding, eval cases for two actions

Date: 2026-10-23 · Status: Accepted (assessment findings A11, A14, B11, G5,
G6 and G8 in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the fourth slice of
section 3 of `docs/implementation/DELIVERY_ROADMAP.md`, taken under the
owner's standing instruction to continue slice by slice).

## Decisions

1. **The generic models screen their inputs (A11, closed).** Regression and
   classification have no timing contract, so they refuse what can be known
   without one: columns the saved mapping marks `ignore`, columns the
   personal-data detector flags, and numeric columns that are the target
   under another name (identical values, or a Pearson correlation of at
   least 0.999 in absolute value, which is a copy, a scaled total or an
   offset). The card's `excluded_inputs` names each with its reason and the
   leakage claim says how many were refused. A measure recorded after the
   outcome that is none of those is still declared, not detected: the
   claim keeps saying so.
2. **Classification carries probabilities and their score (A14, closed).**
   The naive Bayes posteriors for the least common training class are
   scored on the held-out records: the Brier score, the Brier score of
   always saying the training base rate, five reliability bins (mean
   predicted against observed share) and whether the model beats the base
   rate. Both scores are calculations the card cites. When the model's
   probabilities are no closer to what happened than the base rate, a
   limitation claim says no probability from it should be quoted, in both
   languages. The registered-window protocol keeps its own Brier and bins
   for the reliability trials; this is the pipeline's.
3. **One bounded pool per process (B11, closed).** `PostgresStore` holds
   at most `MAX_CONNECTIONS` (20) connections. Every statement outside a
   transaction returns its connection to the pool, so an idle request
   thread holds none; a transaction pins its connection from `BEGIN` to
   `COMMIT` or `ROLLBACK`. At the bound a thread waits on a condition for
   a released connection and fails after `POOL_WAIT_SECONDS` (30) with a
   database error, which the API answers as 503, rather than hanging. A
   pooler in front of the database remains the hosted recommendation; the
   bound is what one instance will ask of it.
4. **Structured answers are checked on the server and asked for in each
   provider's JSON mode (G5).** `server/schema.py` is a small JSON Schema
   checker (type, properties, required, additionalProperties, const, enum,
   minLength, items, maxItems, oneOf, anyOf). The assistant validates the
   model's intent against `INTENT_SCHEMA` after normalising it (an
   internal action name, a missing `arguments` and a reply beside a
   non-chat action keep working, as older models were told), and the
   rules decide when the shape is wrong. `ask_json` sends `response_format
   json_object` to OpenAI, Groq, the AI Gateway and the compatible
   providers, the schema itself to Ollama, and plain text to Anthropic,
   which has no such switch; the check applies to all of them. Consultants
   are asked for structured risks (`RISKS_SCHEMA`: at most three, each
   naming a finding by its number, plus a two-sentence note); an answer
   outside the schema falls back to the free-text question, so a provider
   that will not comply loses nothing. The built-in consultant's rule hits
   name their finding the same way.
5. **Agreement is a comparison of references (G6).** `agreement()` groups
   the consultants' risks by the finding they name: named by more than one
   consultant is agreed, by one is single. The built-in brief and the
   report's agreement line quote those findings rather than number them,
   so the built-in text still carries no digit of its own and `grounded()`
   can only pass it. Hermes' model brief keeps the consultant notes it is
   given; the comparison is the code's either way.
6. **Two actions are measured (G8).** The rules now reach
   `search_knowledge` (with the query taken from "about", "on", "for" or
   the Arabic "عن", "حول", "بشأن") and `agent_scorecard` (with the suite
   when one is named). `evals/intent.json` gains 28 dev and 12 holdout
   cases for them in both languages, written before the rules were run;
   dev stays at 100% and holdout at 81% against its 76% floor. The
   `intent_model` suite stays opt-in because it needs a provider; its
   schedule is the standing one in `docs/AGENT_TEAM.md`.

## Consequences

- `tests/test_p2_slice_four.py` (17 tests, one PostgreSQL-only) covers the
  schema checker, the structured risks and their fallback, the agreement
  and the grounded brief, the two actions' rules and cases, the screen with
  its reasons, the calibration arithmetic and the card, and eight threads
  sharing two connections with a transaction keeping its own.
- A classification card's `details.probabilities` is new; the generic
  cards gain `excluded_inputs`; a consultant note gains `risks` and the
  orchestration gains `agreement`. The provider contract test for hosted
  JSON mode changed with the behaviour.
- Open after this slice: the three unbenchmarked reviewers (G9), the
  interface items (U10, U11, U14, U15, U16, U18, U19), the standards lint
  blind score.
