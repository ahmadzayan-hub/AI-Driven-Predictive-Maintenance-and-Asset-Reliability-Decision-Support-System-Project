# ADR 0036 — Maintenance product identity over the Agentic OS engine

**Status:** Accepted
**Date:** 2026-10-17

## Context

The owner named the product AI-Driven Predictive Maintenance and Asset Reliability
Decision-Support System SaaS Project. The repository already contains a reusable
analytics engine called Agentic OS. Replacing every occurrence would confuse the
product with engine identifiers and could break existing installations.

## Decision

1. Use the owner's full title for the project documentation, browser title,
   onboarding and web manifest. Normalize the service acronym to `SaaS`.
2. Use `Asset Reliability` and `موثوقية الأصول` as compact interface names. The
   full localized title remains readable in onboarding and in the browser title,
   and is available from the shell label's title attribute.
3. Product labels belong to the bilingual dictionaries. Changing language updates
   the browser title and Apple web-app title. The static manifest uses English;
   the installed application's name follows platform manifest handling.
4. Keep Agentic OS as the engine name, including its configurable assistant
   greeting. Keep existing package, storage, API, export and repository identifiers.
   This change does not rename the remote repository, local folder or deployment.
5. Record the domain delivery roadmap in `docs/PROJECT_CHARTER.md`; keep course
   deliverable requirements and personal information in ignored private files.

## Consequences and verification

The shell's product identity is independent of the configured assistant name.
Existing API clients, saved browser state and exported backups retain their
identifiers. The project name does not certify a production service or a validated
maintenance model.

Locale tests exercise browser-title switching. Existing onboarding, sign-in and
Arabic browser checks use the new product labels. The static identity test checks
the README, HTML and install manifest for agreement. Verification results belong
in the session log; historical screenshots and ADRs are not relabelled as new evidence.
