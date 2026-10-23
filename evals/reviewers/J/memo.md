# Interface change packet: asset table and filters (synthetic benchmark J)

Nothing here is a real product screen. Each paragraph is one hunk of a proposed interface change, with the relevant test or build evidence where it exists. Review it for WCAG 2.2 AA and English–Arabic parity.

[P01] `AssetTable.tsx` adds a status icon per row: `<img src={icon} alt="" />` with the status also written in the adjacent cell as text.

[P02] `AssetTable.tsx` adds a trend sparkline per row: `<img src={sparkline} />` with no `alt` attribute and no text alternative.

[P03] `en.ts` adds `assets.filter.overdue: "Overdue only"` and `ar.ts` adds `assets.filter.overdue: "المتأخرة فقط"`; the translation parity test passes.

[P04] `en.ts` adds `assets.export.pdf: "Export PDF"`; `ar.ts` has no `assets.export.pdf` key, and the parity test was marked `.skip` "until the Arabic is confirmed".

[P05] `FilterDrawer.tsx` traps focus inside the drawer while open and returns it to the opening button on close; Escape closes it.

[P06] `FilterDrawer.tsx` adds `onKeyDown={(e) => { if (e.key === "Tab") e.preventDefault(); }}` on the drawer root so focus "stays on the filters", with no other way to leave than the mouse.

[P07] `AssetTable.css` sets the row action buttons to `height: 28px; min-width: 28px`.

[P08] `AssetTable.css` sets the column sort toggles to `height: 18px; width: 18px` with no padding.

[P09] `AssetTable.tsx` renders the Arabic view with `dir="rtl"` on the table and formats currency with `formatCurrencyIn("ar", value)`, which the unit test shows as `3,583,440 د.إ`.

[P10] `KpiTile.tsx` renders the Arabic percentage as `<span dir="ltr">{value}%</span>` inside the right-to-left tile, which the screenshot shows reading as `%45` with the sign on the wrong side.

[P11] `AssetTable.css` sets the table wrapper to `width: 100%; overflow-x: auto`, and the end-to-end run at 320 px shows no page-level sideways scroll.

[P12] `FilterDrawer.css` sets the drawer to `width: 400px` with no maximum, and the end-to-end run at 320 px shows the page scrolling sideways by 80 px.

[P13] The axe run on the changed pages reports no violations; the result is attached in the scorecard.

[P14] `AssetTable.tsx` adds a "Reset filters" button whose label is the untranslated English string `"Reset filters"` in both languages.

[P15] `AssetTable.css` sets the focus ring on the row action buttons to `outline: 2px solid var(--focus)` with a contrast of 4.6:1 against the row background, measured in the scorecard.

[P16] `AssetTable.css` sets the muted status text to `#9a9a9a` on white, a contrast of 2.7:1, for the "last seen" column.
