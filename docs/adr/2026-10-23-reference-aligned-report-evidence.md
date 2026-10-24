# Reference-aligned, bounded report evidence contract

Date: 2026-10-23

## Source and decision

The owner's reference is `docs/roles/Group_9226_Team_3_Report_Final.pdf`, blob
`f92d2672e8f84898e428eeb5193950d68e3b2813`, inspected at commit
`f05ac4bd7a53f7e4e68b135c7233c0ab9933d2ee`. Its actual PDF has 31 pages.
Business-question mapping (p6), quality/method discipline (pp8–10), model
baselines/uncertainty/leakage (pp16–20), and structured decisions/assumptions
(pp21–26) inform the contract. They are structural requirements, NOT evidence
for another dataset. No academic team details, case-specific figures, model
scores or financial assumptions are copied into generated reports.

Add a versioned `report_contract` to the prepared executive brief before its
snapshot digest. It is explicitly an **unapproved evidence projection**, not
an independently reviewed expert report. Existing ordered priorities supply
problem and review rationale; resolved registry values supply demonstrated
findings with scope; only referenced controlled KPIs are linked. Owners remain
proposed/unassigned. No date, operational constraint, intervention approval,
financial benefit or forecast is inferred. Existing read gates and exact
snapshot refresh checks remain mandatory; no stored artifact is rewritten.

A concise coverage table distinguishes available evidence from missing
business context, grain/period/fingerprint, detailed quality-stage projection,
financial scenarios, implementation schedule and demonstrated expert review.
Missing means unavailable in this view, not proof that the whole run contains
no such output. The deterministic descriptive/diagnostic/anomaly specialist
path does not establish all reference-required analytical capabilities.

Repair loss of existing model-card audit evidence at the export boundary:
version, fitting time, training snapshot/window, excluded-input reasons,
mean of per-class one-sided 95% Wilson lower bounds (not an overall confidence
interval), held-out/unmeasured counts, calibration event/positive class, scores and
known bounded calibration/class aggregate fields. These remain whole-run
recorded evaluations, never refitted for display filters. Preserve weak and
unsupported verdicts. Use strict known keys/types/count/length bounds; reject
arbitrary nested dictionaries, nonfinite numbers and numeric booleans. Signal
bounded omissions rather than quietly presenting partial evidence as complete.

## Deliberately not completed

No new training, provider call, recommendation model or independent specialist
review is introduced. Rich saved prescriptive decisions need a separate typed,
source-bound projection; illustrative effects must never become achieved
savings. Detailed quality/cleaning/lineage inputs need their own bounded
projection, not copying stage output that can contain rows. New substantive
model-authored analysis must become a version-bound draft with human approval,
not an export-time rewrite of an approved report. PDF API remains unsupported.

## Acceptance

Synthetic tests cover both languages/formats, lossless known audit values,
retained weak-model warnings, strict malformed/nested/oversized metadata
handling, registry-resolved recommendation evidence, unknown financial and
implementation fields, unchanged source inputs, deterministic contract and
snapshot hashing. Existing export ACL/stale-snapshot and compact-layout tests
remain in force. Real rendered fixture review is presentation evidence only;
it is not business-expert sign-off or proof that all analysis agents ran.
