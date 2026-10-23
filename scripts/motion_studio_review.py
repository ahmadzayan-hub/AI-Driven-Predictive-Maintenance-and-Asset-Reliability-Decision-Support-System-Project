"""Fail-closed Motion Studio production review policy.

This module never grants publication rights. Final approval must be
validated by the host application's authenticated authority service.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

REQUIRED_CHECKS = (
    "source_evidence",
    "technical_accuracy",
    "arabic_typography",
    "audio_sync",
    "media_rights",
    "security_classification",
    "render_integrity",
)


@dataclass(frozen=True)
class ReviewDecision:
    state: str
    reasons: tuple[str, ...]
    manifest_sha256: str


def manifest_digest(manifest: Mapping) -> str:
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def assess_release(
    manifest: Mapping,
    checks: Mapping[str, bool],
    *,
    reviewer_id: str | None,
    reviewer_is_human: bool,
    authorized_by_host: bool,
    approved_manifest_sha256: str | None,
) -> ReviewDecision:
    digest = manifest_digest(manifest)
    failures = [name for name in REQUIRED_CHECKS if checks.get(name) is not True]
    if manifest.get("approval", {}).get("issued") is True:
        failures.append("unexpected_issued_manifest")
    if not reviewer_id or not reviewer_is_human:
        failures.append("human_reviewer_required")
    if not authorized_by_host:
        failures.append("host_authority_required")
    if approved_manifest_sha256 != digest:
        failures.append("reviewed_revision_mismatch")
    return ReviewDecision(
        state="RELEASE_ELIGIBLE_FOR_HOST_DECISION" if not failures else "DRAFT_BLOCKED",
        reasons=tuple(failures),
        manifest_sha256=digest,
    )
