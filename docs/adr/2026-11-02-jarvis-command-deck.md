# Jarvis command deck: celestial core, speaking waveform, live agent map

Date: 2026-11-02 · Status: Proposed. The owner approved the design from the
clickable mockup on 2 November 2026 and asked for a head while speaking. The
budget raise below waits for the owner's approval before merge.

## Context

The owner reviewed Codex's Jarvis and asked for a premium command deck:
celestial particles, gold accents, a map of the agents with real run states,
and the orb turning into a human head while Jarvis speaks. Codex had stopped
work on Jarvis (owner confirmation, 2 November), so its files could change.

## Decision

1. **Celestial core.** The voice core (`JarvisCore`) sits on a night-sky
   gradient with a field of particles drawn in CSS, and has a gold outer ring.
   The particles drift slowly and stop under *Reduce motion* or the system's
   reduced-motion setting.
2. **Speaking waveform.** While the state is `speaking`, the microphone fades
   into a gold abstract waveform. It is a state cue, not an audio level. A
   human-head outline was tried first. The owner's 2 November brief rules out
   human likeness in the default design, so it was replaced. Every other state
   keeps the microphone.
3. **Live agent map** (`AgentMap`, beside Jarvis on the dashboard). It reads
   the run's real tasks from `GET /api/runs/{id}` and groups them in the
   existing bands: data, analytics, assurance, publish.
   - Each agent shows its server state with a mark and a label.
   - Built-in agents are named in the interface language from the existing
     `cockpit.role.*` strings; a custom stage keeps the server's title, which
     is already in the run's language.
   - The map refreshes every 4 seconds only while the run is queued or
     running. If the states cannot be read, it says so and shows none.
4. **What is kept.** All of Codex's Jarvis behaviour is unchanged: the
   session binding, the evidence, the review, the voice controls and the
   reduced motion.

## Budget

Measured in exact bytes after the build, against the current main:

- **Script total:** 272,477 bytes, up from 271,114. That is +1,363 bytes,
  over the 272,000 limit.
- **Style total:** 36,688 bytes, up from 36,071. That is +617 bytes, over the
  36,500 limit.
- **First load:** unchanged. Script is 96.1 of 100 KB, style 10.4 of 10.5 KB.

The limits rise to **273 KB of script** and **37 KB of style**, totals only,
for a chunk that loads only when Jarvis opens.

## Verification

- `AgentMap.test.tsx`, 4 tests:
  - the server states are shown, grouped by band, with interface-language names;
  - the map refreshes while the run is live and stops once it settles;
  - a read failure shows no invented state;
  - the waveform is tied to the `speaking` state.
- The 10 Jarvis browser tests (`playwright.jarvis.config.ts`) pass.
- Screenshots were checked in Arabic and English.
