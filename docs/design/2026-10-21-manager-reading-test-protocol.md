# Does the redesign help managers decide? A reading test

Protocol, 2026-10-21. Nothing here has been run yet, and no result is claimed.

## Why

The redesign moved figures up the screen and cut visible words by 32 to 57%
([dashboard study](2026-10-21-colourful-minimal-dashboard-study.md),
[navigation and views decision](../adr/2026-10-21-simplified-navigation-runs-and-assets.md)).
That shows what moved, not whether a manager answers faster or more
accurately. This protocol tests that.

## Who and what

- **Participants:** three or four maintenance managers or engineers who make
  maintenance decisions, from at least two sites if possible. A sample this
  small can surface the main usability problems; it cannot establish a speed
  difference with statistical confidence. Say so in the write-up.
- **Data:** each participant's own export, analysed on their own machine or on
  the pilot tenant. No participant data, name or recording enters this
  repository; notes go in the git-ignored `private/` folder.
- **Builds:** the version before the redesign (`efb6eb1`) and the current one,
  in a counterbalanced order (half see the old build first).
- **Consent:** written consent to take part and to note timings; recording only
  with separate consent.

## Tasks (same for both builds, different datasets per build)

1. "What is availability for the last period, and is it on target?"
2. "Which group of measures looks worst, and what figure tells you?"
3. "How many records is the first-time-fix rate computed on?"
4. "Start a new analysis on this file." (Runs)
5. "Which asset measures have no target set?" (Assets)
6. On a phone: "Open the dashboard and read the downtime per record."

## Measures

- Time from the question to a spoken answer, with a stopwatch.
- Correct, partly correct, or wrong, against the figure the register computed.
- Number of clicks, and any moment of "where is…".
- One question after each build: "How confident are you in your answer?"
  (1 to 5).
- Comments, written down as said.

## What would count as success

- No task is answered wrongly more often on the new build.
- Tasks 1, 2 and 6 are answered faster on the new build by most participants.
- Nobody misreads a family colour as a verdict. If even one person does,
  that is a design defect to fix before release, whatever the timings say.

## Reporting

A short note with the per-task table (anonymised as P1 to P4), what was
changed as a result, and the limits: small sample, the moderator knows the
design, and the managers' own data differ.

## Native apps: what it would take

The product stays an installable web app (PWA) on phone and desktop. A native
package is possible but is a separate decision:

- **Android:** a wrapper (for example Capacitor or a Trusted Web Activity)
  around the same build. It needs the Android SDK, a signing key held outside
  Git, a Play Console account, and store review. This environment has Java and
  Gradle but no Android SDK, so no package was built.
- **iOS:** needs Xcode on macOS and an Apple Developer account. It cannot be
  built in this Linux environment.
- **What it adds:** a store listing and access to device features a web app
  does not get; which features a pilot needs has not been established. What
  it costs: two more release pipelines, and store review on every interface
  change.

The recommendation is to run the reading test first and decide on native
packages only if pilot customers ask for a store install.
