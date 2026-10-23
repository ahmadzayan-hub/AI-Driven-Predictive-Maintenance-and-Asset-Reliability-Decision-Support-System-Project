# Verified Dubai typography for derived executive exports

Date: 2026-10-23

## Decision

Use the single original `server/assets/fonts/Dubai-Regular.ttf` resource, with
its adjacent copyright/provenance notice, for newly generated HTML and DOCX
exports. Resource publication is owned by the UI/font change, not duplicated
here. Verify the exact original byte count and SHA-256 before use; a missing,
unreadable or mismatched optional resource keeps the existing Arial fallback.
`report_fonts.font_readiness()` reports that condition honestly and lists only
HTML and DOCX. The public PDF export remains unsupported (422).

Standalone HTML embeds the verified original via a data font URL. CSP permits
only data font loads, not arbitrary network fonts. DOCX packages the entire
original using reversible OOXML font obfuscation with an internal relationship;
no font subsetting, outline conversion, copyright removal or relicensing is
performed. A deterministic key preserves reproducible output; obfuscation is
packaging, not a security or DRM guarantee. One regular face means bold may be
synthesized by the document viewer. Client font engines may differ.

Only presentation changes. Existing authorized brief preparation, exact
snapshot checks, evidence, arithmetic, source ACL and approval state remain
unchanged. Previously stored approved reports/media are not rewritten. This
is not government certification and does not finish the executive copy/layout
redesign: the full technical evidence appendix is still retained.

## Verification

Synthetic package tests verify complete reversible byte preservation,
deterministic exports, internal-only relationships, both language directions,
resource hash/size rejection, fallback and unmodified brief data. Existing
export API tests retain ownership, stale snapshot, PDF rejection and approval
immutability coverage. Local QA additionally renders original-font Arabic and
English DOCX in LibreOffice and inspects page images and the PDF font list.
Those PDFs are local rendering probes, not a public server capability; their
normal renderer-generated font subsets are not modified repository resources.
Browser HTML font-engine acceptance and real Word/mobile behavior remain
separate from LibreOffice proof.

## References

- [Microsoft OOXML font part and embedding](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/1663dabc-5d98-463f-889e-bcd9b77c3d34)
- Font provenance and permitted distribution are recorded with the canonical
  original resource in `server/assets/fonts/DUBAI-FONT-NOTICE.md`.
