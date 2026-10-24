# Motion script approval and bounded repair

Status: additive local API proposal, not production activation or complete creative generation.

## Explicit post-report branch

Only an explicit user request starts `POST /api/motion/runs/{run_id}/draft` after current source validation. The deterministic evidence template is a baseline, not an LLM creative specialist. The new assistant integration must use this draft path, never the compatibility `.../render` endpoint. No chat phrase, model verdict or worker result constitutes approval.

The draft accepts audience `internal`, `leadership` or `maintenance`, format `wide` or `vertical`, and optional intentionally uploaded narration bytes. Arabic requires an attached human-approved narration asset. These are retained local video assets, not conversational microphone capture. No voice cloning, microphone auto-capture, paid provider or new credential is introduced.

1. Draft creation records immutable storyboard, full report hash, source revision context, narration hash, audience and format. It does not enqueue rendering.
2. An already-authorized independent reviewer fetches `GET /api/motion/jobs/{id}/script` and `/narration`. Existing private-pack ACL still denies a reviewer without source access. No role is granted.
3. `POST .../script-approval` requires the exact binding and four affirmative human checks: reviewed_script, checked_evidence, checked_audience_format, checked_narration_rights. Author self-approval is denied.
4. The author explicitly calls `POST .../render-approved`. Live source ACL and source freshness are rechecked, as are approved content/narration hashes. The transition is transactional and duplicate render requests are refused.
5. The existing isolated local encoder produces a draft and technical MP4 checks. Those checks do not establish professional aesthetics, factual validity, intelligible Arabic or correct semantic audio synchronization.
6. Existing independent human review checks all facts, Arabic, full playback, audio alignment and brand/rights. Internal approval never publishes: publication_allowed remains false.

## Bounded repair and immutable artifacts

A failed or human-returned job may become a parent_id for a new draft with an explicit repair_note. The new draft has its own ID, storyboard/audio hashes and fresh required script approval. Two repair children at most are reserved per root lineage, transactionally; a parent cannot spawn duplicate children. A third repair is refused with human escalation. Old media is not overwritten or deleted. This wave does not have automatic creative model mutation or automatic retry: specialist suggestions must enter as new reviewed proposals, not silent edits.

Authorized job status can return only id, SOURCE_STALE, needs_update, next_action and publication_allowed when the source changes. Preview, script, narration, approval and render remain blocked until regeneration. Revoked access, deleted sources and wrong tenants return 404 without stale metadata. Permission is checked when a request is authorized; already downloaded bytes cannot be recalled.

## Specialist adapter seam and remaining work

The input to LocalMotion.create is a server-validated storyboard plus workflow metadata. A future evidence-bound script/story/design/QA specialist adapter should use the main bounded kernel and model gateway, with cancellation, provenance, budget and failure envelopes. It must retain source references and approval-bound hashes and must not treat synthetic test drivers as production fallback. That adapter is not activated by this PR; the emitted creative_generation marker explicitly says deterministic_evidence_template_not_llm_specialists.

The creative generation goal remains open: specialist-backed alternative scripts/storyboards, designed visual variation, real Arabic narration, real-device playback and visual/audio acceptance still need implementation and evaluation. No full-duplex voice or latency claim follows from these synthetic HTTP tests.

## Deployment boundary

This reuses the existing opt-in persistent local SQLite/filesystem service and existing JSON columns, with no schema migration. It is not the PostgreSQL daemon kernel and cannot run on an ephemeral serverless filesystem. Production renderer availability, persistent storage, fonts/codec readiness and operating cost remain separately gated. The existing direct-render endpoint remains legacy compatibility, not an approved new-assistant tool.

English may deliberately use silent video; Arabic requires uploaded narration. Approval binds the presence or absence and SHA-256 of that exact audio. Audio must be listened to by the reviewer; technical duration/container checks do not transcribe or validate its meaning.

The existing local limits are 24 MB per narration, 60 seconds per encode and one encoding thread. This wave bounds each repair lineage to two children and guards duplicate queue submission, but does not introduce global disk quotas or a durable distributed admission queue. Those capacity controls and process/CPU/memory isolation remain prerequisites for production enablement. Submission failure records FAILED with a safe error instead of promising execution; no automatic retry follows. A failed draft transaction removes only the narration file exclusively created by that request.
