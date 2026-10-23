# P2 slice six: the interface items, with the font subsets paying for them

Date: 2026-10-23 · Status: Accepted (assessment findings U10, U11, U14, U15,
U16, U18 and U19 in `docs/audits/SAAS_PLATFORM_ASSESSMENT.md`; the sixth
slice of section 3 of `docs/implementation/DELIVERY_ROADMAP.md`).

## Decisions

1. **The fonts are subsets the repository keeps (U19).** The five
   @fontsource Latin faces (Fira Sans 400, 500, 600; Fira Code 400, 500)
   are subset by `scripts/subset_fonts.py` to printable ASCII, Latin-1,
   the general punctuation the reports use, the euro, the arrows and the
   comparison signs, and committed under `frontend/src/shared/fonts/` with
   one stylesheet of `@font-face` rules, woff2 only. The build no longer
   imports @fontsource (the package stays as the source to regenerate
   from). Fonts fell from 119.4 KB to 86.5 KB; the budget is 100 KB. The
   script, not the subsets, is the thing to edit after a font upgrade.
2. **One answer for the asset evidence (U10).** `GET /api/assets/evidence`
   returns the newest run carrying a succeeded railway asset screen, in
   full, with `scanned` (how many recent runs were inspected) and
   `capped` (whether the owner has more runs than the scan reads). The
   Asset Intelligence view reads that one answer instead of the run list
   and up to fifty run payloads; its error state with a retry stays.
3. **The relationship table says how many rows it shows (U11).** Under the
   scatter's numeric alternative, when the chart draws more than the 100
   rows the table lists, a line says so in both languages.
4. **One noun per destination (U14).** The run list is "Analyses"
   (Arabic unchanged); the administration view is "Administration"
   (الإدارة). The end-to-end specs follow the labels.
5. **Every upload call to action reaches the Datasets flow (U15).** The
   Command Centre, Asset Intelligence, the dashboard picker and the
   maintenance preview all go to Datasets, where the preview and the
   mapping live; a stored dataset is then analysed from there. The Analyses
   form keeps its own file control as a source choice inside the form,
   which the intake tests still cover; the entry points no longer bypass
   the preview.
6. **Figures say when (U16).** The asset evidence shows the run's last
   update as a `<time>` beside the dataset and state; the empty dashboard
   picker offers the action it was missing.
7. **Every message pack is held to parity, and the Command Centre is
   smaller (U18).** The parity test covers all 21 packs (eight were
   untested); the export job moved to `useExecutiveExport`, the view has no
   line over 200 characters, and `hasVerdict()` in `PerformanceValue` is
   the one place that says which tones carry a reason.

## Consequences

- Budgets after the slice: JS first load 99.0 of 100 KB, total 245.2 of
  248 KB, CSS 10.0 of 10.5 and 32.7 of 33.5 KB, fonts 86.5 of 100 KB. The
  interface change cost 0.2 KB of script; the font subsets freed 33 KB.
- `tests/test_p2_slice_six.py` covers the endpoint, the subsets, the
  labels and the call-to-action routing; the frontend unit tests cover the
  one-call loader, the as-of time, the dashboard link and the parity of
  every pack; the intake, overview, datasets, dashboard, accessibility,
  keyboard, runs, decision, joins, responsive, workspace, plugins and
  collaboration specs cover the rest.
- Open: the standards lint blind score; the model half of G8; P3 items.
