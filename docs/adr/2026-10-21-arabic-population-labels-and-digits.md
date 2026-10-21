# Arabic population labels and Western digits on Assets

Date: 2026-10-21 · Status: Accepted

## Context

Two faults were seen on the Arabic Assets page:

- **Untranslated population.** The KPI register named each population in
  English only ("all records", "corrective records", "records with a
  failure"). The KPI and executive endpoints translated the title but passed
  the population through, so Assets and the dashboard's evidence fold showed
  English on an Arabic page. The Arabic export translated two of the three
  names; "records with a failure" was missing from its own list.
- **Arabic-Indic digits.** Assets formatted values with `ar-EG` (٧٧٫٠٪),
  against [ADR 0018](0018-the-interface-in-the-readers-language.md), which
  keeps digits Western in Arabic (`ar-u-nu-latn`) so a figure on screen
  matches the same figure in the English report.

## Decision

1. **The register owns the Arabic names.** `POPULATION_AR` maps every
   population code to its Arabic name, and a `Kpi` whose population has no
   entry is refused at definition, so a new population cannot ship
   untranslated.
2. **`population` stays the code; `population_label` is what a reader
   sees.** Both the `/kpis` and executive endpoints return
   `population_label` in the request language. The code is kept because the
   export and stored policies match on it, and the Arabic export continues to
   print "Arabic name (code)".
3. **The export reads the same map**, so "records with a failure" is now
   translated there too.
4. **Assets formats numbers with `ar-u-nu-latn`**, as the rest of the
   interface does.

## Verification

Python: every population has an Arabic name and an unnamed one is refused;
the `/kpis` endpoint returns the Arabic label with the English code; the
Arabic executive brief carries the label and keeps the code. Frontend: the
formatter keeps Western digits in Arabic; Assets shows the label with the
code as fallback. Each test failed before the change. On the fictional
maintenance run, the Arabic Assets tiles contain no Arabic-Indic digit and no
English population name. Counts are in README.md under Testing.

No CSS changed.
