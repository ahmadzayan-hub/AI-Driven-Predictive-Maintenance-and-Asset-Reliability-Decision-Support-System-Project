# Keep documented confidential artifacts out of future Git trees

Date: 2026-10-21. Status: accepted and applied locally.

The full assessment identified a confidential Power BI package and its PDF
under `roles/02-rashed-bi-dashboard/`. Existing ignore rules cover both paths,
but cannot remove files that were previously tracked. The owner's instruction
to fix the assessment authorizes removing these known prohibited artifacts
from future source trees.

Use `git rm --cached` on the two documented paths, preserving both local files.
Do not inspect their contents, delete source files, rewrite history, change
collaborators or make the repository public. Verify local files still exist
and `git check-ignore` covers both. This removes the current-tree exposure;
historical and external copies remain covered by the earlier containment
decision. Public release still requires explicit owner approval after reviewed
historical-data remediation.

Reference: [temporary private containment](2026-10-20-temporary-private-containment.md).
