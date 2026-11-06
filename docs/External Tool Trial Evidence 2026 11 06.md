# Isolated tool evaluation: execution evidence

Date: 6 November 2026. Owner: Ahmed Zaian.

## Independent source and licence checks

| Candidate | Canonical source | Source licence | Status |
| --- | --- | --- | --- |
| Open Notebook | https://github.com/lfnovo/open-notebook | MIT, checked from repository LICENSE | Unapproved for execution |
| Book to Skill | https://github.com/virgiliojr94/book-to-skill | MIT, checked from LICENSE.md | Unapproved for execution |
| No AI Slop | https://github.com/petergyang/no-ai-slop | MIT, checked from LICENSE | Unapproved for execution |

A code licence does not establish dependency licence compatibility, supply-chain integrity, or suitability for RTA data.

**Critical warning:** The upstream Book to Skill project published SECURITY-NOTICE.md on 17 August 2026 about a malicious, unaffiliated re-upload at `Leutenegger/book-to-skill`, including alleged exfiltration. NEVER install that fork. Authenticate canonical origin and immutable revision, then inspect all install scripts and dependencies before installing anything.

## Actual tests performed in isolated model execution container

- Python 3.13.5; four unittest cases PASSED, including subtests covering absent fields, restricted data, external network egress, write permissions, and invalid repository.
- Existing local assessment candidate catalogue executed; tool exited with **2** (expected rejection). All three sample candidates remain **BLOCKED**.
- Attempted GitHub network checkout via `git ls-remote`; failed DNS resolution (`Could not resolve host: github.com`). Docker runtime not available.
- Therefore third-party executable code has **NOT** been fetched, installed, started or integration-tested; no app-wide CI, dependency audit or realistic acceptance benchmark has run.
- No real RTA records, keys, operational endpoints or production environments accessed.

## Acceptance decision: NOT APPROVED FOR MERGE

Safety-gate unit behaviour: PASS (local copy); upstream dependency audit: NOT RUN; immutable executable source pinning: NOT DONE; sandbox installation: BLOCKED BY ENVIRONMENT; actual integration runtime tests: NOT RUN; data-egress verification: NOT RUN; independent human review: NOT DONE. Keep draft PR unmerged.

## Required follow-up in a capable controlled runner

1. Provision an ephemeral VM/container with approved network allowlisting, denied outbound runtime egress, synthetic-only files and nonproduction credentials.
2. Clone from the verified canonical URL by immutable commit; capture full commit IDs and archive checksums.
3. Independently inspect dependency manifests, transitive licences, known CVEs, installation scripts and outbound endpoints.
4. Run full unit, end-to-end and negative safety tests, record command, timestamp, logs, inputs, expected and observed outputs.
5. Benchmark gain against existing MIYAAR / RMD V2 capability; reject duplication and memory-intensive additions without measurable benefit.
6. Obtain security and engineering human sign-off; only then mark the relevant integration PR reviewable and consider merging. Never equate merge with production deployment.

Source URLs above are identification only; no code installed.
