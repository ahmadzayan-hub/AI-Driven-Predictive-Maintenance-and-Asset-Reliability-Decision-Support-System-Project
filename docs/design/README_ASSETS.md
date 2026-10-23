# GitHub presentation and image provenance

Date: 22 October 2026. Scope: the repository's README and documentation assets.

## Presentation decisions

The opening explains the maintenance decision, the data-to-review journey and
the relationship between Asset Reliability, Miyaar, Hermes and Agentic OS.
It uses the existing navy/blue industrial direction and ordinary GitHub Markdown.
There is no custom stylesheet, external badge service or JavaScript in the README.

The product tour uses actual committed interface captures. The maintenance
preview uses fictional equipment and costs; the Miyaar capture uses a synthetic
test session. Captions retain those distinctions. Product screenshots are never
replaced by generated interfaces.

Detailed capabilities and developer commands remain in expandable sections.
The existing Testing commands and dated verification history are retained in
README, which remains the one place for test counts. Historical verification
is not a claim that the current branch is green. Main was studied at
`f28518659a7574a3758fe052b53825aedd32a7e4`; its CI and UI Budget Fast workflows
were failing when inspected. This presentation change does not fix or certify
those application checks.

The repository stays at its current visibility. No deploy, repository rename,
model installation, application behavior or runtime dependency changes are
part of this delivery.

## Original generated artwork

Both images were generated on 22 October 2026 with the session's built-in
`image_gen` tool for this repository. The request referred to “image 2”; the tool
does not expose a model-version selector or return a model identifier, so an
exact model version cannot be independently asserted.

No repository data, source workbook, customer information, existing image or
private photograph was sent as a reference. Text-only prompts described generic
industrial objects. These images are conceptual editorial artwork and do not
show an operating installation, measured signal, product interface or result.

| Asset | Content | Dimensions | Encoding |
| --- | --- | --- | --- |
| `docs/media/reliability-hero.webp` | Cutaway industrial motor, bearing and sensor; the background signal is decorative | 2172 × 724 | WebP, quality 86 |
| `docs/media/evidence-review.webp` | Bearing and condition sensor beside a review notebook | 1672 × 941 | WebP, quality 86 |

Generated PNG masters remain in the execution workspace. The committed WebP
encodings preserve the complete compositions and original dimensions. No crop,
text overlay, generated figure or fabricated performance result was added.

## Existing screenshot derivatives

| README asset | Original capture | Treatment |
| --- | --- | --- |
| `docs/media/miyaar-workspace.webp` | `docs/screenshots/miyaar-en-desktop.png` | Lossless WebP; identical pixels and dimensions |
| `docs/media/maintenance-overview.webp` | `docs/screenshots/maintenance/desktop-en-light.png` | Lossless WebP; identical pixels and dimensions |
| Arabic phone image | `docs/screenshots/maintenance/phone-ar-dark.png` | Referenced directly; unchanged |

Source capture descriptions and limitations are in
[the Miyaar handoff](MIYAAR_UI_HANDOFF.md) and
[the maintenance UI specification](MAINTENANCE_UI_SPEC.md).

## Validation scope

Documentation checks cover local destinations against the studied GitHub tree,
heading anchors, image alternatives and decoding, lossless screenshot equality,
and preservation of the existing commands and dated Testing section.
The installed Markdown parser successfully renders the document's tables,
disclosures and RTL container. Generated images and the selected original
screenshots were visually inspected. The local Chromium preview could not
launch: the command sandbox rejected Crashpad's `setsockopt` operation. No
successful browser layout, keyboard or light/dark preview run is claimed for
this documentation change. GitHub supplies the README's native layout; this
delivery does not modify its interface or certify application accessibility.

Current application acceptance evidence and unresolved work remain in
[README Testing](../../README.md#testing),
[the project charter](../PROJECT_CHARTER.md) and
[known limitations](../KNOWN_LIMITATIONS.md).
