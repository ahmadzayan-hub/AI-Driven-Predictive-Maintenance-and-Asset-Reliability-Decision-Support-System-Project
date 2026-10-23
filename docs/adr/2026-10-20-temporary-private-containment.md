# Temporarily make the repository private to contain historical exposure

Date: 2026-10-20
Status: accepted by the repository owner; conversion executed and verified.

## Context

The current main tree excludes private course material, but metadata review
identified protected paths on historical branch tips. Deleting current files
does not remove those historical copies. Branch deletion and history rewriting
remain prohibited. The owner replied "perform next" to the explicit proposal
to make the repository private while retaining existing collaborators.

## Decision

Change only repository visibility to private. Preserve collaborator permissions,
all branches and their existing tips. Do not change production, invitations,
branch protection or history as part of this action. Personal/course data must
still stay out of new commits.

On 20 October, authenticated GitHub metadata confirmed private visibility.
Before/after comparisons preserved all four access entries (the owner and three
other collaborators) and all 17 branch tips. Anonymous web and API requests
returned 404. There were no forks, Pages site, stars or watchers at conversion.
Detailed access snapshots remain outside the repository.

## Consequences and follow-up

Existing authorized collaborators retain access. Instructors or team members
without access need an owner-approved invitation. Repository, CI and old-name
redirect links now require authentication.

This closes immediate access containment, not historical-data remediation.
Existing local clones or other external copies cannot be recalled by changing
visibility. GitHub reported no forks, but that does not establish that no other
copies exist. Agree remediation with affected owners and GitHub before any
future public release; making the repository public again requires explicit
owner approval.

The hosted-release and independent maintenance-domain acceptance gates remain
open. No production deployment was performed.

Reference: [GitHub's visibility-change consequences](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility).
