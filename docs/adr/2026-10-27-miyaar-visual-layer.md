# Miyaar visual layer: the brief, the AI core and a bounded glow

Date: 2026-10-27 · Status: Accepted (owner's request of 27 October 2026 to
study current AI-dashboard interface work and develop the Miyaar interface;
amends ADR 0054 and the budget line of `2026-10-27-stacked-datasets.md`).

## Context

The owner shared nine reference interfaces (an AI call-centre cockpit, a
personal-finance bento dashboard in three themes, an AI-assistant phone
home, an AI-agent SaaS overview, and HR, security, fintech, smart-home and
wind-turbine dashboards) and asked that Miyaar learn from them. What they
share, and what current practice confirms (dark surfaces and bento grids
remain the dominant dashboard idiom in 2026; executives want the key figure
in seconds, with secondary data behind a deliberate disclosure; WCAG 2.2 is
the floor): a greeting that states the situation in one sentence with one
action; large figures with a small trend beside them; a glowing "core" that
stands for the intelligence layer; soft depth from gradients and halos,
never from colour alone.

Miyaar already had the midnight surfaces, cyan actions, restrained glass
and the honest-voice rules of ADR 0054. What it lacked was the brief, a
trend beside the figures, and a hero that looked like an intelligence layer
rather than a gear.

## Decision

1. **The brief opens the Command Centre.** A greeting by the hour and the
   signed-in name, one sentence from counted runs ("Miyaar has N analyses
   closed and M waiting for your approval"), and one primary action: Review, which
   opens the analysis that has waited longest, when something waits; Start
   an analysis otherwise. Beside it, analyses
   started in the last 14 days as a figure, a sparkline and the change
   against the 14 days before, all counted client-side from the runs'
   own `created_at` (`dailyStarts` in `summary.ts`, tested). Nothing is
   fabricated: no health score, uptime, response time or satisfaction
   figure appears, because none is measured.
2. **The AI core replaces the industrial gear** in the Miyaar hero: rings,
   a slow dashed orbit (still under reduced motion) and streams around the
   mark, with a halo. It is labelled an illustration and encodes nothing.
   The three workflow steps become chips; the action grid goes to three
   columns from 1280px.
3. **A glow token, decorative only.** `--glow` (cyan in dark, blue in light)
   and `--glow-edge` back the core, the listening microphone, the sparkline
   and hovered actions; the workspace background gains two faint radial
   hazes in dark and the hero a gradient. Text colours and control borders
   are unchanged, so every AA pair of ADR 0054 holds; axe runs on the
   Miyaar workspace in both languages and four viewports and on the
   Command Centre.
4. **Strings** ship in English and Arabic in the Overview's lazy pack, not
   the shell dictionaries, so first load stays under 100 KB.
5. **Budget.** Measured after the change: first-load script 99.6 of 100 KB,
   first-load style 10.46 of 10.5 KB, total script 254.3 KB, total style
   33.97 KB. The strings were moved off the first load first; the rest is
   the brief, the sparkline, the core and the glow rules. The total ceilings
   move to 255 KB script and 35 KB style (`scripts/verify.py`,
   `tests/test_verify.py`), as ADR 0054 did for the first visual layer.
   The first-load ceilings do not move.

## Consequences

- `summary.test.ts` (daily starts by UTC day, the period before, unreadable
  dates left out, the greeting by hour) and an `OverviewStates` case: the
  greeting names the reader, the sentence carries the counts, Review opens
  the approval queue. The Miyaar workspace suite and the overview journey
  pass with axe; the Miyaar screenshots in `docs/screenshots/` are refreshed.
- Not done, and candidates for the next slices: a per-agent card row
  (success rate per pipeline stage, from the runs' task states), a live
  timeline in the Overview's right rail, a lavender light variant, and
  imagery-led asset cards for the maintenance views. Each needs its own
  measured figures and its own budget line.
