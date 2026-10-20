# New labelled cases from real use: consent, redaction and tenancy

- Status: **Accepted 2026-10-20 by the owner: option D now, option C conditional.** Option D is done (see below). Option C is not built and stays closed until both of its conditions are met.
- Date: 2026-10-20
- Follows [the agent measurement loop](2026-10-20-agent-measurement-loop.md),
  which gave new cases a safe way in (a review queue) but no source of them.

## The question

The agents improve only if they meet cases they were not fitted to. Three
places could supply them from real use:

1. **Chat sentences.** Sessions store the transcript per owner. A sentence
   and the action it should have caused is a label for the intent suite.
2. **Column mapping corrections.** When a person changes a column's role,
   the dataset's saved mapping records the corrected role. That is a label
   for the column-role suite.
3. **Reviewer edits and rejections.** A person rewriting a claim the causal
   or jargon check passed is a label for those checks.

All three are tenant data. Sentences can contain names, asset identifiers,
contract values, or an email. Column names can themselves be personal
("emirates_id", a person's name used as a header). Using any of them to
improve a shared product is a new purpose, separate from the one the
person gave it for.

## What the system does today (verified in the code)

- Memory, sessions, datasets, runs and connectors carry an `owner` and are
  deleted per owner by `scripts/erase.py` (ADR 0015). That command removes
  rows and published notes. It cannot reach backups, and says so in every
  report.
- `save_history` is a preference. Turning it off stops the transcript being
  recorded; it is not a consent to anything else.
- The personal-data detector finds emails, phone numbers, long identifiers,
  person-like names in varied columns, and personal-sounding column names.
  It is measured, not complete: its recall on the project's own suite is
  100% on cases written for it, and nothing says it is that good on free
  text. A date, a timestamp or a 16-digit float already read as a phone
  number during the last change, so it also over-fires.
- Raw data never goes to a model. Detected personal data stops model
  handoffs (2026-10-20 personal-data boundary).
- The `owner` role reads runs across owners by design. There is no
  purpose-limited reviewer role and no audit entry for an operator reading
  a tenant's text.

## Options

**A. Do nothing.** New cases come only from people and from blind sets
written by an independent agent from the label definitions, as the project
does today. No tenant data is touched. Limit: those cases may not look like
real use, so measured recall may not predict recall in production.

**B. Passive harvesting with automatic redaction.** Log every sentence and
correction, mask what the detector finds, queue the rest. **Rejected.**
Consent would have to be blanket. The detector's recall on free text is
unmeasured. Masking changes what a sentence means, so the label can become
wrong. The queue would hold tenant text that nobody asked to share.

**C. Explicit, per-item contribution, then a person rewrites it.**
Described below.

**D. Synthetic cases from label definitions, written blind.** An agent that
has not seen the rules writes new cases from the definitions alone, which is
how the current blind sets were made. No tenant data, no consent needed.
The weakness is the same as A: distribution.

## Recommendation

Do **D now**, and treat **C as a conditional second step**, built only when
two things are true: a measured mismatch between synthetic and real cases
(for example, recall on a real pilot sample far below holdout recall), and a
pilot customer who has agreed in writing. Without both, C adds legal and
operational exposure for a gain nobody has measured. There is no production
user base today, so the mismatch cannot yet be measured, and building C now
would be effort spent on a hypothetical.

If the owner chooses C, these are the rules.

### 1. Consent

- **Off by default and separate** from `save_history` and from any
  terms of use. Turning it on is a deliberate act by the owner of the
  workspace.
- **Per item, not blanket.** Even with the switch on, nothing is taken
  passively. A person marks a specific sentence ("use as a training
  example") or a specific mapping correction. Unmarked content is never
  read for this purpose.
- **A consent record**: who, when, the wording version they saw, and the
  scope (sentences, corrections). Withdrawing turns the switch off and
  deletes everything still waiting.
- **The wording says plainly** what cannot be undone: once a case has been
  rewritten and accepted, it no longer belongs to the contributor and
  cannot be traced to them, so it cannot be withdrawn.

### 2. What may be contributed

- **Sentences:** one sentence, at most 200 characters.
- **Mapping corrections:** the column name and the chosen role only. No
  values. The column-role suite scores real tables, so a correction becomes
  a case only when a person rebuilds it with invented values of the right
  type. Real values are never copied.
- **Never:** rows, files, report text, run results, or anything from a run
  flagged as holding personal data.

### 3. Redaction, in this order, failing closed

1. **Reject, do not mask.** If the detector flags the text, or the
   run it came from was flagged, the contribution is refused with a reason.
   Masked text is not used.
2. **Reject** text containing an email, a number of six or more digits, a
   URL, or a capitalised name sequence. These are blunt checks on purpose.
   Over-rejecting costs a few cases. Under-rejecting leaks a person.
3. **Human rewrite.** A named reviewer writes a new, synthetic sentence
   with the same intent. **The rewritten sentence is what enters the review
   queue. The original is deleted when the reviewer decides, and in any case
   after 30 days.** The suites therefore never hold a tenant's words.
4. The rewritten case carries no owner, no session and no timestamp finer
   than the month. Its source is recorded as "contribution", nothing more.

### 4. Tenancy and access

- Contributions wait in a per-owner table that is added to the erasure
  command's table list, so erasing an owner removes them.
- A reviewer reads a contribution under a purpose-limited role created for
  this, and every read is written to an audit entry. The `owner` role's
  cross-tenant read is not reused for this.
- Quarantined text never goes to a model, the improver included. A model
  sees only the accepted, rewritten cases.
- Backups taken during the 30 days hold quarantined text. The existing
  backup caveat applies and is stated in the consent wording.

### 5. What it must not do to the measurement

- Accepted cases go to the **dev** split only, as already enforced. They
  never enter a holdout. A holdout is written blind by someone who did not
  write the rules.
- A person accepts. No agent accepts its own or another agent's case.

## Legal position: not verified

I have not verified any article of the UAE personal data law. A web search
returned commentary only, not the statute. The commentary describes
Federal Decree-Law No. 45 of 2021 (in force 2 January 2022) as limiting
retention to the purpose, giving a right to erasure, and requiring
informed consent, and says implementing regulations were still developing.
Treat all of that as unconfirmed until read in the Official Gazette or the
UAE legislation portal. Sources consulted:
[Hunton](https://hunton.com/insights/legal/data-protection-in-the-uae-game-changing-federal-uae-data-law),
[CookieYes](https://www.cookieyes.com/blog/uae-data-protection-law-pdpl/).

Questions for counsel before any build:

1. Does a rewritten, unlinkable sentence still count as personal data, and
   does the 30-day quarantine of the original need a separate lawful basis?
2. Where the customer is a government entity, is the customer permitted to
   let a supplier use its staff's messages for product improvement at all,
   whatever the staff member ticks? This may end option C for that customer.
3. Does storing quarantined text where the database is hosted raise a
   cross-border question?
4. Free zones (DIFC, ADGM) have their own regimes. Does any target customer
   sit in one?

## What would be built if C is accepted

A consent record and switch; a contribution button on a chat sentence and on
a mapping change, in English and Arabic; the quarantine table, its 30-day
deletion job and its place in the erasure order; the reviewer role and audit
entry; the redaction checks; tests for each rule above, each watched failing
first, including that a held-out sentence, a flagged run and an unconsented
item can never reach the queue. Nothing in this record changes code.

## Decision taken

The owner chose D now, C conditional. Concretely:

- **D, done the same day.** Three independent agents, given only the label
  definitions and told not to read the repository, wrote fresh sentences:
  48 for intent, 40 for jargon, 40 for causal wording. Each set was scored
  once against the unchanged rules, then stored as `blind_v6` in its suite
  file. It is not a `holdout` key, so no floor and no existing score changed.
  Two intent sentences ("help", "is the analysis done yet?") already sat in
  earlier splits, so they were removed and the set rescored at 48. A test
  now fails if any blind_v6 sentence also appears in another split.
- **C stays closed** until both conditions hold: a measured gap between
  synthetic and real cases, and a pilot customer's written agreement. Then
  the rules in this record apply, after counsel has answered the questions
  above.

### What the first blind_v6 run measured

| Suite | Cases | Blind_v6 | Existing holdout | Reading |
| --- | --- | --- | --- | --- |
| Intent | 48 | 68.5% macro recall | 72% | Consistent with the holdout |
| Jargon | 40 | 85% recall, 100% precision | 92% | A little lower, as expected |
| Causal wording | 40 | 45% recall, 69% precision | 100% | The holdout figure is not evidence |

The causal row is the finding. The existing causal holdout reads 100% only
because it was read and fitted to. On sentences nobody fitted to, the lint
misses 11 of 20 real causal claims (for example "is responsible for",
"stems from", "gave rise to", "نتج عن", "ناجماً عن") and flags 4 of 20
non-causal sentences ("Due to the timetable change", a driver driving a
train, "نتيجة اختبار"). The floor of 68% looks generous against 45%, but it
guards a different, fitted set, so it was left alone. The rules were not
changed in this step: fixing them against blind_v6 would turn it into dev
data. Whoever fixes them should move blind_v6 into dev first, say so in the
record, and ask for a new blind set to judge the fix.

Intent misses are mostly sentences that mean recall, forget, run status or
explain-report in indirect or Arabic phrasing. Jargon misses are a Weibull
distribution, overdispersion, and an Arabic "null hypothesis rejected".

Limits of this measurement: one author per suite, one pass, 40 to 48 cases
each. The recalls carry wide uncertainty (for 40 cases a single figure can
move by about 15 points either way), and an agent writing from definitions
may differ from how real users write. Both suites' labels were assigned by
the writing agent and not independently reviewed.

## Decision requested (answered above)

Choose A, D, C, or D now with C conditional (recommended). If C, the owner
also names the person who may review contributions and who answers the
legal questions.

## Limits of this draft

- It rests on the code as of this date and on secondary legal commentary.
- "Reject, do not mask" will throw away many usable sentences. The yield has
  not been measured.
- A rewrite by a person removes the tenant's words, but it can still carry
  the tenant's situation (an unusual asset type or a rare workflow). That
  residual risk is small and not zero.
