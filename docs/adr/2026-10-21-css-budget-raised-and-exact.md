# CSS budget raised, and checked in exact bytes

Date: 2026-10-21 · Status: Accepted (owner request, 21 October: "raising the style budget")

## Context

After four rounds of interface work the stylesheets sat at 23,499 of 23,500
bytes in total and 9,984 of 10,000 bytes on first load, gzipped. Every
further change had to remove something first, which had already cost one
useful element (the Assets capability chips) and several compressions of
new rules. The size audit
([decision](2026-10-21-simplified-navigation-runs-and-assets.md)) found no
dead CSS left to remove.

The check itself had a flaw: it rounded each size to 0.1 KB before
comparing, so 10,046 bytes printed as "10.0 of 10 KB" and passed.

## Decision

1. **CSS total: 23.5 → 25 KB.** About 1.5 KB of room, roughly one view's
   worth of styling.
2. **CSS first load: 10 → 10.5 KB.** The smaller rise, because every
   visitor pays it on every first visit.
3. **JavaScript limits unchanged** (100, 185 and 30 KB): they have 1.8 KB of
   room, and the larger cost to a phone is script, not style.
4. **The check compares exact bytes.** Only the printed summary is rounded.

## Consequences

The next visual change no longer needs a removal first, but the room is
finite: when it is gone the choice returns. Raising a limit again needs a new
record. A test now fails a build that is a few bytes over even when it rounds
to the limit.

## Verification

`tests/test_verify.py`: a 120,040-byte font fails the 120 KB limit (it
passed before the fix); 120,000 bytes passes.
