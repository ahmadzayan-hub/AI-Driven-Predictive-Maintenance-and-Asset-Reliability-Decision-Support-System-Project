# Trend decorations must not intercept the chart controls

Date: 2026-10-29. Status: Accepted corrective review of PR #72.

## Evidence

The trend line paints a small visible circle and its connecting polyline
after the larger interactive circle. SVG hit testing therefore sends a click
at the visible point's centre to a decorative element without a handler.
The original cross-filter tests covered bars and histogram bins, but not
direct pointer clicks on trend points.

The hosted browser review on commit `eddb57d` reproduced the interception
in English and Arabic on desktop and mobile:
https://github.com/ahmadzayan-hub/AI-Driven-Predictive-Maintenance-and-Asset-Reliability-Decision-Support-System-Project/actions/runs/40944443034

## Decision

The decorative polylines and small circles ignore pointer events. The existing
larger circle remains the pointer and keyboard control, with its accessible
name and pressed state. Visual review also found compact Arabic axis values
clipped inside the trend and scatter SVGs on phones. Reserve a wider label
gutter and move the plot's left edge with it; keep all numeric values and
relative positions unchanged. Data, filters and calculations do not change.
No new dependency, hosted migration or deployment is involved.

The regression uses a normal centre click, never a forced click, checks the
filter and record coverage, and releases the filter using Enter. The same
browser suite captures each Arabic dashboard page and checks RTL, horizontal
overflow, SVG label bounds and accessibility on desktop and phone. Screenshots are synthetic
test evidence; they make no claim about production data or hosted readiness.

The parallel push run on `5dc60af` also exposed a test-fixture flake:
the journey's random UUID ended in a ten-digit sequence, which correctly
triggered the conservative model privacy boundary when stored as memory.
That failure prevented cleanup and affected two later conversation tests.
Encode the fixture UUID's digits as letters, preserving uniqueness without
manufacturing phone-like test data. Production privacy checks and all test
assertions stay unchanged. Evidence: Actions run `40945474927`.
