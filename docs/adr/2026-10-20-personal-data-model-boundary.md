# ADR 2026-10-20 — Detected personal data stops model handoffs

**Status:** Accepted
**Date:** 2026-10-20

## Context

A computed fact can contain an unmodified dataset label. A synthetic dataset
with email addresses as groups was flagged by the privacy stage, yet its leading
email appeared in the narrator's provider request before any approval existed.
The assistant also reused report headlines as model context, and runtime/MCP
report tools returned those headlines to their caller.

The existing privacy warning only governed publication. Publication approval is
not permission to send identifying labels to a model, and aggregate arithmetic
does not anonymize its category labels.

## Decision

`server/model_privacy.py` is the shared gate for these handoffs:

- Main-dataset privacy findings and joined-dataset findings stop narration before
  any provider or router is called. The summary remains deterministic, with an
  English or Arabic explanation in the report.
- The exact outgoing goal and fact text is screened too. This catches a sensitive
  leading group beyond the dataset detector's bounded first 2,000-row scan.
- Assistant model/runtime handoffs use the same persisted run findings and text
  screening. A private report referenced in conversation history remains private
  after another run becomes the latest. The rules still execute authorized user
  actions and quote the original report directly to the reader.
- Report/status tools withhold detected private context from runtimes and MCP
  clients. Other tool outputs are screened before text or structured results
  are returned to a model-facing caller. Completed actions remain recorded.
- Original datasets and human reports remain intact. No silent redaction or new
  model-egress permission is inferred from a publication approval.

## Limits

This is a conservative use of the existing measured pattern detector, not a
claim of exhaustive personal-data discovery or anonymization. Undetected
identifiers remain possible, and sensitive installations should use the
fully deterministic path. Detection can also suppress a model unnecessarily.
The knowledge collection remains operator-managed shared reference material.

## Validation

`tests/test_model_privacy_boundary.py` exercises main and joined personal data,
a sensitive label beyond the bounded scan, unchanged safe narration, both report
languages, private conversation history, direct human quotation, and provider,
runtime and tool boundaries. All providers are spies; no real model receives
these fixtures. The existing assistant, model gateway, runtime, MCP and report
language tests provide compatibility coverage.
