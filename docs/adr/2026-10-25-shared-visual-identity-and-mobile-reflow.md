# Shared visual identity and mobile reflow

Status: implemented; runtime verification recorded separately.

The owner requested a visible change in the interface, beyond the preceding
alignment repair. Use navy navigation, cyan navigation accents, blue primary
actions and an off-white light canvas through shared semantic tokens. Retain
explicit dark and system themes, Arabic direction, existing capabilities and
honest model status. Larger body text and headings improve hierarchy. Do not
invent metrics or remove provenance and approval controls for visual simplicity.

The observed phone layout had a small outer vertical scrollbar in addition to
the content scroll area. Size the shell to the dynamic viewport and reserve bottom-navigation padding.
Actual browser inspection identified an absolutely positioned screen-reader
announcement at its static off-screen position as the remaining root overflow.
Anchor visually hidden elements at the containing origin; retain their accessible
content. Do not hide shell overflow as a substitute for fixing the cause. Content areas remain
scrollable; bottom navigation and keyboard focus must remain visible.

Keep long filenames on one ellipsized line with their full bidirectional text
and title available. Action accessible names continue to contain the full name;
analysis still receives the original dataset object. This changes presentation,
not file identity, user data or storage.

Remove redundant style overrides and decorative glows to retain unchanged
bundle budgets. Component assertions cover the full filename and analysis
binding. Browser layout assertions cover root overflow and bottom navigation;
actual bilingual phone and desktop inspection is a separate release gate.

RTL follow-up: a negative margin on an origin-anchored visually hidden element
places its left edge at -1px. In RTL this creates an outer horizontal scrollbar,
which reduces the client height and induces a second vertical scrollbar. Use a
zero margin while preserving clipping and accessible content. Compare scroll
dimensions with document client dimensions in browser tests; innerWidth and
innerHeight include scrollbar space and can conceal this regression. Retain an
explicit identity-control focus rule with the existing navigation contrast token.
The source-color regression reads the last equal-specificity rule, matching the
CSS cascade; its existing 3:1 focus and 4.5:1 text thresholds are unchanged.
