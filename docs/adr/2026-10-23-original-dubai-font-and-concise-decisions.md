# Original Dubai font and concise decision presentation

The owner explicitly requested Dubai typography and removal of redundant copy on
23 October 2026. This supersedes the older blanket no-redistribution note in
Memory.md only for Miyaar application/report embedding under the official TEC
statement and Monotype creator confirmation. See the adjacent font rights notice
at server/assets/fonts/DUBAI-FONT-NOTICE.md. This is not an unrestricted font
redistribution grant or government affiliation.

Bundle one original, unmodified official Dubai Regular TTF (139928 bytes), shared
by UI and report exports. No conversion, subsetting or outline changes. Preserve
embedded copyright. The existing code license does not cover this font. No other
Dubai weights are loaded; browser synthesis supplies heavier UI text. Previous
Fira source assets may remain historical but are not imported into the build.

## Transparent performance allocation

Increase only the original-font byte cap from100KB to145KB. Count TTF, OTF, WOFF
and WOFF2 by original bytes, preventing a new format from evading the check.
139928 original bytes gzip to70798 bytes in the local measurement; actual network
compression depends on serving configuration and is verified separately. The
original TTF remains unchanged. JS/CSS limits are untouched. One face is loaded
on use with font-display:swap and cached offline; no extra preloads or third-party
font requests. System fonts remain readable if the resource fails.

## Copy and evidence

Remove generic overview description and duplicated read-only prose, retaining the
single mode notice and explicit fictional-data warning. Put workflow instructions
in a keyboard-native disclosure. Preserve source identity, as-of, review status,
owner uncertainty and all recommendation caveats. A long recommendation shows only a complete literal first sentence when short enough, otherwise a neutral recommendation label; its full unchanged source text and caveats remain in a native disclosure. No new model summary or invented
operational information is introduced. Test actual Dubai font loading, failure
fallback, Arabic/English, reflow, keyboard and color contrast on the changed build.
