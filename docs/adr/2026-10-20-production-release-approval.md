# Production release approval

Date: 2026-10-20

Status: Accepted

## Context

AGENTS.md authorizes synchronization to `main` while requiring explicit owner
permission for production deployment. Hosting metadata shows a production
deployment sourced from Git on `main`; the checked-in configuration previously
left automatic Git deployment enabled by default. A normal code push could
therefore publish a release before that approval.

## Decision

Set `git.deploymentEnabled.main` to `false` in `vercel.json`. GitHub Actions
continues to validate every push. Preview branches retain their existing
behavior. An owner-approved production release must be an explicit deployment
of the reviewed commit, after the hosted authentication, persistence, worker
and provider acceptance checks.

This does not change the running deployment, remove a domain, or approve a
release. A repository configuration regression test preserves the main-branch
guard. Hosted integrations outside this Vercel configuration need their own
release controls.

## Source

[Vercel Git configuration](https://vercel.com/docs/project-configuration/git-configuration),
accessed 2026-10-20: named branches can disable deployments triggered by commits;
unspecified branches remain enabled.
