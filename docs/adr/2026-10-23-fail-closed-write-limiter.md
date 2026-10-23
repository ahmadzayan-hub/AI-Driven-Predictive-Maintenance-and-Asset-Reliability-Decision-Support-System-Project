# Fail closed when shared write admission is unavailable

Date: 2026-10-23 · Status: Proposed for review

## Context and decision

The shared rate limiter admitted writes if its counter store failed. Some
handlers can perform work independently of that store, so a counter outage
cannot safely be treated as unlimited admission.

Raise a dedicated unavailable exception and stop API writes with a sanitized
English/Arabic 503 and Retry-After. Do not claim 429 or exhausted quota when the
counter is unknown. Read-only routes stay available. No schema, environment,
provider or dependency change is required. Tests cover the store exception,
bilingual API envelope, read availability and absence of a newly created run.

## Release and rollback

This is code-ready only after review and checks, not hosted acceptance. Main
merge and deployment require owner approval. Roll back by a new revert commit
and reviewed application release, without deleting data; a rollback restores
the old fail-open behavior and is not a safety fix. There is no database
migration in this patch. Before any broader hosted release, separately review
the existing database's schema gap and backup/restore plan.

## Separate unresolved work

The model budget's read/charge race and missing worker hookup need a separate
transaction-boundary repair: run advancement holds a transaction across model
work, so a naive nested reservation would roll back after external work and
would not acquire the intended per-owner lock. This patch does not claim to
solve that problem and does not disable existing model roles.

## Preservation and authority

The owner instructed preservation of intentionally public MBA files on
23 October. Stale blanket confidentiality/removal instructions are corrected,
without deleting course materials or rewriting history. Secrets and genuinely
non-public personal data remain protected. Earlier standing merge instructions
are superseded by the current approval requirement.
