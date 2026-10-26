# Portfolio remediation briefing, 23 October 2026

> Historical briefing as recorded on 23 October. It is not current project status.
> The 26 October integration preserves current main behavior; consult the latest
> session log and GitHub checks for the present Miyaar status.

Prepared for Ahmed Zaian. Status is separated into four levels: code-ready (tests pass on the changed commit), demo-ready, deployment-verified, and operationally accepted. Nothing in this briefing is operationally accepted. Deployment-verified is marked only where I checked a live URL, and I did not check any today.

## 1. Executive summary

- 12 pull requests are merged. Fixes for masaar and RailMind-Agent-OS are ready but unmerged, and the Miyaar release is not merged.
- The Miyaar (Team3) release, PR #30, is not merged. CI was green on its head, then `main` moved when another session merged PR #24, which put #30 in conflict. I rebuilt the merge on a local scratch branch (commit 4580db3, not pushed).
- Nothing is deployed. Vercel's daily deployment limit blocked deployments earlier, and every merged change is code-ready only.
- Four items need you: Supabase project IDs for the migrations, the Replit redeploy, the login-code provider credentials, and the three repository deletions.
- The most serious find: the live v6 site ran Next.js 16.3.0, which has five unauthenticated remote-code-execution advisories. The fix is merged but not deployed, so the site stays exposed until you deploy it.

## 2. What was done

| Repository | Change | State |
| --- | --- | --- |
| RMD-V2 | Sign-in throttling from the audit trail (5 failures in 15 min gives 429), refused sign-ins now kept (they were rolled back before), agent-run close ordering fix, motion-studio fixes, IDOR coverage, ruff fixes. PRs #30, #24, #31 merged into develop. | Code-ready (local tests). Its CI never starts any step, so no CI evidence exists. |
| Beyond-Style Generator | Production login-code delivery through WhatsApp Cloud API or SMTP adapters, fail-closed in production, with tests. PR #1 merged. | Code-ready. Not deployed. |
| beyond-style-uae-v6 | PR #2 merged: returned-scrap double credit pinned by tests and a decision note. PR #3 merged: Next.js 16.4.3 security upgrade and the pricing fix (net consumption, formula v2.1.0, zero-total warning). | Code-ready (80 tests, typecheck, lint, local). CI failed in about 2 seconds with no log. Not deployed. |
| PromptOps, Pitchora-studio, pitchorastudio, prompt-orchestrator- | Closed a tenancy hole: any signed-in user could add themselves to any organisation. Organisation creation now goes through a security-definer RPC. PRs merged. | Code merged. The SQL migrations are NOT applied to any database. |
| Hader-lecture-ai | ASR request contract fix with a test. PR #5 merged. | Code-ready. |
| mutabasir | Citation anchoring: missing citations downgrade confidence to LOW. PR #6 merged. | Code-ready. |
| Miyaar / Team3 | Release PR #30 prepared, two CI failures fixed (a dashboard row cap I wrongly kept in a merge; a browser test for a renamed button). | Not merged. See section 3. |
| RailMind-Agent-OS | PR #2 verified: 159 of 159 tests with PostgreSQL, on 20 September. | Not merged. |

## 3. What was not done, and why

| Item | Blocker | Who acts |
| --- | --- | --- |
| Merge Miyaar PR #30 | `main` moved to 2455cc5 after my CI run. The PR conflicts in 12 files. My scratch merge (4580db3) is local only. On 4580db3 the Python suite passes (1,989 tests, 21 skipped, PostgreSQL 16), frontend unit tests 388, typecheck and brain check pass. Browser and platform jobs have not run on it. After any push, CI must pass again. | Me, once you allow the push and the merge. |
| Production deploy of Miyaar | Needs the merge first, then an explicit Vercel deploy. Vercel was refusing deployments (rate limit). Rollback target: `dpl_4Gv6P2vB6d36DSQcDT6dWFVEQEET`. Risk: if `DATABASE_URL` is set in production without a sign-in provider, the new code refuses to start. I could not read the variable names (403). | You and me. |
| Deploy v6 | Merged only. After deploy: test sign-in, a silver quote, a gold quote and an order. | You. |
| masaar PR #6 | Held on purpose. After merge its webhooks reject every call unless `WEBHOOK_SECRET` and `WHATSAPP_APP_SECRET` are set in Vercel. If they are not, live order intake stops. The Apps Script must also send `x-webhook-secret`. Migration 0007 needs a backup first. | You, then me. |
| RailMind-Agent-OS PR #2 | Branch protection: needs an approval from someone other than the last pusher. I did not bypass it. | You or a second reviewer. |
| Five tenancy migrations, backup, membership audit | The Supabase account I can reach has four projects, and none is for PromptOps, Pitchora or prompt-orchestrator. I did not guess a target. | You: send project IDs. |
| Replit backend redeploy | No Replit access from this session. The production monitor was returning 404 from the wrong app. | You. |
| Generator login-code provider | Needs your account and credentials. My recommendation: SMTP email first. Set `APP_ENV=production` and `CONTACT_HASH_PEPPER`. | You. |
| Delete AI-Agents-Virsual-Code, pitchora, pitchora2 | I have no deletion tool. Needs your login and confirmation at the moment of deletion, and a recheck that each is still empty. | You. |
| RMD-V2 CI | Jobs end in 1 to 4 seconds with no steps run. I could not see the cause through the API and did not assume billing. Check Actions settings and the account's billing page. | You. |
| Vercel projects | RMD-V2 has 6 projects; rmd-v2 and rmd-v2-duef are in ERROR. Needs a consolidation decision. | You. |

## 4. Assessment by project

Facts are from this session's checks. Judgements are mine.

**RMD-V2 (priority 1).** Strongest engineering of the portfolio: governance rules enforced by tests, audit chain, IDOR test over 79 routes. Sign-in had no brute-force limit and lost its own failure records; both fixed. Gap: no CI evidence at all, so every green claim rests on my local runs. Treat it as code-ready, not release-ready, until Actions runs again. It also depends on the owner-supplied `kpi_definitions.csv`, which is absent, so contractual KPIs correctly show Missing evidence.

**Miyaar / Team3 (priority 2).** The most advanced product, and the one with the most integration risk right now. Two sessions built the same error contract and asset-evidence features in parallel, which is why #30 conflicts. Lesson: one session owns `main` for a release. CI before the move covered Windows, macOS and Android-size browsers and was green. The merged result needs the same proof again.

**Beyond Style: Generator, v6, ops (priority 3).** v6 is a live pricing engine with a real defect: returned scrap counted twice, which priced an 18K gold piece at AED 0 and made dearer metal lower silver quotes. Fixed under Reading A. The scrap valuation basis (refining loss, buy-back rate) is still your input. Until v6 is redeployed it runs an RCE-vulnerable Next.js. Generator's production sign-in is fail-closed but has no provider yet, so customers cannot log in until you choose one.

**PromptOps and the Pitchora variants.** Same tenancy hole in four copies. Fixed in code, not in the databases. Until you apply the migrations, the hole is open in production. Audit existing memberships afterwards; anyone could have added themselves.

**masaar.** Fix is ready and tested, held for a real reason (section 3). Risk is operational, not technical.

**RailMind-Agent-OS.** Verified and waiting on a reviewer. Per its own notes it is a P0 synthetic demo, not connected to live data, and must not be presented as operational.

**Hader-lecture-ai, mutabasir.** Small, correct fixes merged. Low risk.

**Not assessed (deferred, no work done):** Maktab, Maktab-, exeflow, vertex, wisal, lahza, lahza-, draftly-Private, agentic-os-enterprise, ALKAHTANI-Agentic-OS, AI-Knowledge-Assistant, annual-operation-plan-2026, RailMind, mutabasir-director-lens-, data-value-studio, beyond-style-ops and other Phase 3 repositories. I have no findings on them. Do not read their absence from this briefing as a clean bill of health.

## 5. Preserved assets

No repository was deleted or archived. All intentionally public MBA files and distinct products were left alone. The three deletions you approved remain open.

## 6. Short approval and action list

1. Allow me to push the scratch merge (4580db3) to the Miyaar branch and merge #30 after CI.
2. Supabase project IDs for the four tenancy repositories.
3. Choose and credential the Generator login-code provider; redeploy the Replit backend.
4. Deploy v6 and run the sign-in, quote and order checks.
5. Confirm the masaar webhook secrets are set (or that the site is not live).
6. Approve RailMind-Agent-OS #2 as a second reviewer.
7. Check RMD-V2 Actions and billing.
8. Delete the three empty repositories yourself.
9. Confirm the v6 scrap valuation basis.

## 7. Migration and rollback

- Miyaar: rollback is promoting `dpl_4Gv6P2vB6d36DSQcDT6dWFVEQEET`.
- v6: rollback is reverting merge bb1e18e. Quotes already issued keep the formula version they were priced under.
- Tenancy migrations: take a database backup first, apply, audit memberships. Not yet applied.
- masaar 0007: backup first, apply, then merge.
