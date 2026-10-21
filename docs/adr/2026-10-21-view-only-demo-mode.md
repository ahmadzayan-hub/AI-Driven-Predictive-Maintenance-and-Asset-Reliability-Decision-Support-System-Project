# View-only demo mode without sign-in (server half)

Date: 2026-10-21 · Status: Accepted for the server; the interface is not built,
so **do not set `AGENTIC_OS_DEMO` on any deployment yet**.

## Context

The owner asked to remove "Sign in to Asset Reliability" for now. The sign-in
screen appears only where an identity provider is configured, so removing it
means removing authentication from the hosted site, where anyone with the link
would act as the owner. Offered three routes, the owner chose a view-only demo:
no sign-in, fictional data, nothing writable.

## Decision

1. `AGENTIC_OS_DEMO=1` selects `DemoIdentity`: every request is one principal,
   `demo-showcase`, with the read-only `viewer` role. Every write endpoint
   already checks its permission server-side, so each answers 403. A bearer
   token sent to the demo is ignored, not verified: there is no one to be.
2. Demo mode next to a configured sign-in provider refuses to start. Either
   way round it is a mistake, so the server does not guess.
3. Demo mode is allowed with `AGENTIC_OS_ENV=production`, because it cannot
   write.
4. At startup the server seeds one fictional 240-record fleet dataset and its
   analysis, owned by the demo principal, if that principal has none. The
   file is generated from a fixed seed (`server/demo.py`), so no real data can
   reach the demo and every cold start shows the same figures. It uses the
   maintenance profile where configured and the default profile otherwise.

## Not done

- **The interface.** The app opens a chat session on load, which is a write,
  so with demo mode on today the browser shows a start-up error. The plan:
  in demo mode, open on Overview with a client-side session, hide Workspace,
  Memory, Preferences and the session buttons, and show a bilingual
  "view only, fictional data" note.
- Two cold starts at once against one PostgreSQL database could both seed.

## Verification

`tests/test_demo.py` (11 tests): one read-only principal; a token does not
upgrade a visitor; refusal next to any provider variable; production allowed;
the browser told there is no sign-in; one fictional analysis readable; ten
write endpoints refused with a forged token; no second seed on restart; a
deployment without the maintenance profile still seeds. A one-handle SQLite
`ResourceWarning` at interpreter exit is pre-existing: a plain local app
without demo mode shows it too.
