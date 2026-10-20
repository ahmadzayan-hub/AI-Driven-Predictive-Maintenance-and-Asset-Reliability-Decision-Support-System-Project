# Keep interface evidence within its stated scope

Date: 2026-10-20
Status: Accepted

## Context

The full project review found that Asset Intelligence searched only eight
recent analyses before declaring that railway evidence was absent. Its KPI
state could also retain a previous run's measurements while a new run was
loading. Dashboard trend queries are bounded, but did not disclose that later
periods were omitted. Arabic planning text ignored the supplied Arabic stage
titles, and asset state labels exposed raw identifiers.

Authenticated API failures outside chat did not return an expired session to
sign-in, including approval, mapping and export requests.

## Decision

Search the complete run list returned by the existing endpoint in batches of
eight, preserving the endpoint's bounded workload. Explicitly disclose its
50-analysis scope when the list is full. Failed candidate reads remain visible
as an incomplete search, and cannot silently prove that no railway evidence exists.

Bind asset measurements to the run identifier, update timestamp and interface
language. Hide mismatched responses immediately and ignore late responses from
an earlier scope. Display translated run states and use supplied Arabic stage
titles in plan previews and profile help.
The KPI audit note describes numerator divided by denominator, with the
percentage scale factor, rather than claiming every measure divides by records.

Both dashboard trend surfaces disclose truncation, including the number of
periods displayed and the Records page for inspecting the complete matching data.
This changes disclosure rather than inventing aggregated or sampled points.

All authenticated JSON, CSV and executive-export requests signal expired
credentials to the session store. The signal applies only when the credential
sent still matches the current credential, preventing an old request from
logging out a newly signed-in identity. The UI returns to the existing managed
sign-in screen; this does not add token refresh or a custom authentication flow.

## Validation

Regression tests cover railway evidence behind ten newer unrelated analyses,
pending and late KPI responses during run/language changes, Arabic planning
and state labels, both truncated trend surfaces in English and Arabic, all
three request transports, stale-credential refusal and non-chat sign-in
recovery. These component and transport checks do not constitute a production
identity-provider round trip or manual assistive-technology validation.
