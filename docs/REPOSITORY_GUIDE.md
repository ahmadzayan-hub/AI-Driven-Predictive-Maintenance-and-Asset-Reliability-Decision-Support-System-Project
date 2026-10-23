# Repository guide

## Product and audience

Asset Reliability helps maintenance analysts, reliability engineers and
reviewers take data through calculation, evidence inspection and a human
publication decision. Miyaar is the conversational workspace, Hermes coordinates
the analysis, and Agentic OS is the underlying engine.

A model output, score or polished dashboard does not establish prediction
quality, a maintenance saving or authority to act. Read the
[project charter](PROJECT_CHARTER.md), [known limitations](KNOWN_LIMITATIONS.md)
and [pilot runbook](PILOT_RUNBOOK.md) for acceptance boundaries.

## Three runtime modes

| Mode | Identity and state | Appropriate use |
| --- | --- | --- |
| Local owner | One local owner, no sign-in; local persistent storage | Personal evaluation with authorized inputs on a trusted computer |
| Public demo | Shared read-only demo identity, generated fictional data | Interface exploration, not customer work |
| Managed identity | Verified provider tokens, server-side roles and owner scoping; durable shared storage must be configured | Hosted acceptance after the intended environment is verified |

The local launcher binds to loopback by default. `--lan` deliberately opens
network access; do not enable it on an untrusted network or confuse local-owner
mode with authenticated multi-user isolation.

A Vercel frontend/serverless build is not a continuous worker. The API and worker
need compatible shared configuration and storage. Production configuration must
fail closed if managed identity is missing; do not weaken that check to publish
a working-looking page.

## Setup and authentication

1. Use the README's local installation on a fresh checkout. Python 3.12 matches
   the repository's hosted interpreter pin. The deterministic path does not
   require paid model credentials.
2. Inspect `.env.example` for the supported configuration names. Keep secrets
   in private runtime configuration, never in Git or browser bundles.
3. For managed sign-in, review the provider verification and browser settings
   in [VERCEL_DEPLOYMENT.md](VERCEL_DEPLOYMENT.md). Provider URL/key presence is
   not evidence of successful sign-in, registration or recovery.
4. Verify the actual provider callback, allowed origins, token issuer/audience,
   role assignment, expiry and sign-out for the intended deployment. Do not
   advertise Google, Apple or recovery as enabled until that exact path works.
5. Review the current full database schema before pointing startup at a shared
   database: initialization can apply DDL. An existing initial migration does
   not establish compatibility with the present source.
6. Validate cross-owner denial with two authorized test users, durable state
   after restart and restoration from an isolated backup.

The original [managed-identity decision](adr/0002-authentication.md) records the
design at its date; later source and decisions refine it. Current
`server/auth.py` is the executable role/identity boundary. Never derive a role
from user-editable profile metadata.

## Data and review flow

**Upload → Validate and map → Analyze → Inspect calculations and evidence →
Review the exact report → Approve publication → Retain the result**

- The React interface calls the FastAPI API; it is not the authorization layer.
- Server-side dataset, mapping and analytics services perform calculations.
- Runs and sessions use the configured storage adapter. Optional workers
  continue execution, still respecting approval gates.
- Raw dataset rows stay out of model prompts. Optional narration receives
  checked findings, not blanket permission to transmit source documents.
- Publication approval applies to the reviewed report. It is not approval of
  another edited artifact or permission for an autonomous maintenance action.

See [dataset analytics](DATASET_ANALYTICS.md),
[architecture](ARCHITECTURE.md) and [agent catalog](AGENT_CATALOG.md).

## Verify the exact release

Run `python scripts/verify.py` on the candidate source. Add `--e2e` for the
browser suites; `--quick` is an iteration aid, not complete release evidence.
PostgreSQL coverage needs an isolated test database configured as documented in
`CLAUDE.md`; tests skipped without it must remain marked skipped.

The dated test results remain in README as the repository's single test-count
reference. They describe their exact source and environment, not all later
commits. Hosted identity, durable-worker behavior, recovery and independent
maintenance evaluation require separate acceptance.

## Contributions, security and license

Follow [CONTRIBUTING.md](../CONTRIBUTING.md) and preserve intentionally published
MBA/course materials, existing screenshots, examples and source attribution.
Do not include secrets or genuinely non-public personal information in changes,
issues or captures. Read [the threat model](SECURITY_THREAT_MODEL.md) before
reporting a vulnerability and use a maintainer-approved private route for
sensitive details; no new contact or response-time promise is implied here.

No repository-wide license file is present in the reviewed source. This page
does not create or change licensing terms. Existing third-party notices and
licenses continue to apply.

## Visual assets

The earlier hero, evidence artwork, logos and actual UI captures remain in the
repository. Existing screenshots retain their original synthetic/preview
captions and are not substituted with generated UI. Historical visual
provenance remains in [README_ASSETS.md](design/README_ASSETS.md).

## Managed account activation

The sign-in UI supports existing-account email links, email onboarding and
conditional Google/Apple login using PKCE, but only after secure provider and
exact callback configuration. An eligible email request is not successful login.
New verified accounts remain read-only until an operator assigns workspace
permissions. See [the managed-auth decision](adr/2026-10-23-managed-auth-onboarding.md)
for delivery limitations, callback rules and production acceptance requirements.
