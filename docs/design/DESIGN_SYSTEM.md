# Design system

Date: 22 October 2026 · The system is the one in the code. This page names
where it lives, what the brief asked for, and where they differ.

**Stitch screen-generation brief:** [root `DESIGN.md`](../../DESIGN.md) is the semantic visual contract for the three Miyaar screens. It does not supersede the runtime tokens or grant approval for new features, claims, or deployment.

## 1. Where it lives

| Part | File |
| --- | --- |
| Tokens (colour, type scale, spacing, radius, motion), light and dark | `frontend/src/shared/styles/tokens.css` |
| Base, layout, components (cards, buttons, controls, KPI tiles, performance badges) | `frontend/src/shared/styles/*.css`, `shared/components/*` |
| Brand mark and principles | `docs/design/ASSET_RELIABILITY_BRAND_SYSTEM.md`, `frontend/public/artwork/*` |
| Charts | `frontend/src/features/dashboard/charts.tsx` (role img, numbers table) |
| Dashboard style study | `docs/design/2026-10-21-colourful-minimal-dashboard-study.md` (owner-accepted palette) |

## 2. Tokens in use

Light canvas `#f8fafc` on white surfaces; text `#0f172a`; teal accent
`#006b73` (6.3:1 on white); amber highlight `#b45309` for attention; violet
`#6d28d9` and magenta `#be185d` as category tones (owner-accepted); navy
`#111a2e` defined for navigation. Dark theme: surface `#0d182a`, text
`#edf4fc`, accent `#55dfd2`. All text tones pass AA; strong borders pass 3:1.

Type: system stack with Arabic support; scale `--text-xs` to `--text-xl`.
Spacing `--space-1` to `--space-5`. Motion honours reduced motion and a user
toggle.

## 3. The brief against the code

| Brief | Code | Decision needed |
| --- | --- | --- |
| Dark navy navigation | navy tokens exist; the shipped rail is light; navy appears in the design preview only | Owner: adopt the navy rail in the app shell (one CSS change, contrast re-checked) |
| Light analytics canvas | matches | — |
| Restrained teal and gold accents | teal matches; amber marks attention and negative bars, which is wider than "accent" | Owner: reserve amber for attention only, or keep |
| Strong hierarchy, professional type, consistent icons | present | — |
| Minimal decoration | present; the Command Centre adds none | — |
| Accessible contrast, responsive, RTL | present and tested | — |

## 4. Rules for new screens

1. Use the existing cards, buttons and performance badges; no new primitives
   without a decision record.
2. Colour names a category or a verdict the server gave; never a verdict the
   screen inferred.
3. Every chart has a title, unit, period and a numbers table.
4. Every string ships in English and Arabic, in a pack under the parity test.
5. Every allocation of the interface budget is recorded in a decision.
