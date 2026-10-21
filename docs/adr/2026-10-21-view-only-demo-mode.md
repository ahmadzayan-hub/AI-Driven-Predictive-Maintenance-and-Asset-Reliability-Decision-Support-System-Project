# View-only demo mode without sign-in

Date: 2026-10-21 · Status: Accepted. Server and interface complete; switching a
deployment to it needs the owner's approval (see "Turning it on").

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

## The interface (added the same day)

The app opened a chat session on load, which is a write. In demo mode
(`/api/auth/config` reports `mode: "demo"`) it now:

1. Shows no sign-in page and never asks the server for a session; a closed
   local session stands in, so no session-dependent write is attempted.
2. Opens on Overview. Workspace, Memory and Preferences, which live on a
   session, leave the sidebar and the phone bar (Analytics takes Workspace's
   place there), and a link to one of them lands on Overview.
3. Hides New session, End session, sign-out, the onboarding dialog and the
   buttons that start an analysis on Overview and Asset Intelligence.
4. Replaces the header status with "View-only demo" in English or Arabic,
   explained on hover, and names the visitor "Demo visitor".

## Serverless instances (added the same day)

The hosted site showed "Run not found." Production had no `DATABASE_URL`, so
each Vercel instance kept its own temporary SQLite file: a run created on one
instance was missing on the next. Reproduced locally with two app instances:
404 with separate SQLite files, 200 with one shared PostgreSQL. A demo seeded
per instance had the same flaw, because each copy got random ids.

The demo now seeds under ids from a generator seeded by the demo principal, so
every instance builds the same dataset, run, tasks, artifact and approval under
the same ids. Visitors cannot write, so the copies stay identical; the demo
therefore works on Vercel without a database. Outside seeding the engine's ids
stay random. A writable deployment still needs `DATABASE_URL`: nothing in code
can share state between instances that keep separate files.

## The default on an unconfigured Vercel deployment (added the same day)

Production carried neither `DATABASE_URL` nor a sign-in provider, and the
connected Vercel account could not add `AGENTIC_OS_DEMO=1`; three redeploys
stayed in single-owner `local` mode, writable by any visitor and losing runs
between instances. On Vercel (`VERCEL=1`, set by the platform) with no
`DATABASE_URL` and no sign-in provider, the server now starts the view-only
demo. A configured deployment keeps its mode: a sign-in provider gives `jwt`,
a database gives `local` as before, and `AGENTIC_OS_DEMO=0` opts out. Off
Vercel nothing changes.

## Write controls hidden (added 22 October)

Deeper views still offered controls the server refuses a demo visitor.
`ReadOnlyContext`, set by the app in demo mode, now hides them: adding a
dataset and starting an analysis from it, the new-analysis form, pause,
resume and cancel, approve and reject (a note says why instead), saving or
clearing a column mapping, and the dashboard's "Analyse maintenance data"
link. Operations leaves the demo navigation, as every action there is
administration. Reading controls stay: the executive brief (assembled in the
browser from data already read), refresh, export, drill-downs and evidence.
Outside demo mode the context is false and nothing changes. The server's
refusal remains the guarantee; hiding the controls only stops offering what
would be refused.

## Turning it on

On the hosted project, with the owner's approval: set `AGENTIC_OS_DEMO=1`;
remove `AGENTIC_OS_JWT_SECRET`, `SUPABASE_JWT_SECRET` and
`AGENTIC_OS_JWKS_URL` (the server refuses to start with both); redeploy. Without
`DATABASE_URL` the demo runs on SQLite in the function's temporary folder and
re-seeds its fictional run on each cold start, which is what a demo wants.

## Not done

- Deeper pages keep their write controls: the Analytics run form, adding a
  dataset, approving, saving a target, and the Operations administration.
  Using one shows the server's refusal ("Your role (viewer) cannot write
  here."); nothing is written.
- Two cold starts at once against one PostgreSQL database could both seed.

## Verification

Interface: a store test (demo mode opens with no sign-in, never calls
`createSession`, even when asked to start) and an Overview test (no start
buttons when it cannot start), each failing before the change. In a browser
against a demo server on a fresh database: no sign-in at 1440 px and 390 px,
English and Arabic; landing on Overview; `#/chat` redirected; no failed request
and no page error on load.

`tests/test_demo.py` (11 tests): one read-only principal; a token does not
upgrade a visitor; refusal next to any provider variable; production allowed;
the browser told there is no sign-in; one fictional analysis readable; ten
write endpoints refused with a forged token; no second seed on restart; a
deployment without the maintenance profile still seeds. A one-handle SQLite
`ResourceWarning` at interpreter exit is pre-existing: a plain local app
without demo mode shows it too.
