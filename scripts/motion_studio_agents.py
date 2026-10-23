"""Evidence, narration and AI-assisted editorial checks for Motion Studio.

No model is invoked without an explicitly supplied and already-authorized
callback. Source documents are data, never instructions. This module does
not approve, sign, publish, email or upload media.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable, Any

from motion_studio_render import validate, MotionInputError


class AgentReviewError(ValueError):
    pass


def digest(manifest: dict) -> str:
    return hashlib.sha256(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _words(text: str) -> list[str]:
    return re.findall(r"[\w]+", text.casefold(), re.UNICODE)


def _distance(a: list[str], b: list[str]) -> int:
    previous = list(range(len(b) + 1))
    for i, word in enumerate(a, 1):
        next_row = [i]
        for j, candidate in enumerate(b, 1):
            next_row.append(min(next_row[-1] + 1, previous[j] + 1,
                                previous[j-1] + (word != candidate)))
        previous = next_row
    return previous[-1]


def check_transcript(manifest: dict, transcript: str | None) -> dict:
    """Compare an independently obtained transcript with the approved script.

    This is a reading-aid measure only; intelligibility, dialect, translation,
    clipping and exact audio-to-scene timing still require listening.
    """
    if not transcript or not transcript.strip():
        return {"status": "NOT_TESTED", "word_error_rate": None,
                "reason": "No reviewed speech transcript supplied"}
    expected = _words(" ".join(s["text"] for s in manifest["scenes"]))
    observed = _words(transcript)
    if not expected or len(expected) > 500:
        raise AgentReviewError("Narration script is empty or too long")
    error = _distance(expected, observed) / len(expected)
    return {"status": "REQUIRES_HUMAN_REVIEW", "word_error_rate": round(error, 4),
            "reason": "Text similarity is not a measurement of pronunciation or timing"}


def review(manifest: dict, *, transcript: str | None = None,
           editor_assistant: Callable[[dict], dict] | None = None) -> dict:
    """Run only safe, deterministic audits and optional advisory AI feedback."""
    validate(manifest)
    checks = []
    evidence = [ref for s in manifest["scenes"] for ref in s["evidence"]]
    checks.append({
        "agent": "provenance-checker",
        "status": "PASS" if evidence and all(
            ref["data_status"] in ("VERIFIED", "RECORDED_IN_REGISTER") for ref in evidence
        ) else "REVIEW_REQUIRED",
        "message": "Source IDs and recorded revisions are present; exact claim-text agreement is not independently confirmed.",
    })
    direction = "rtl" if manifest["language"] == "ar" else "ltr"
    checks.append({"agent": "arabic-rtl-inspector", "status": "REVIEW_REQUIRED",
                   "message": f"Visual shaping and reading order ({direction}) require rendered playback inspection."})
    transcript_result = check_transcript(manifest, transcript)
    checks.append({"agent": "narration-checker", **transcript_result})
    model_output = None
    if editor_assistant is not None:
        # The caller must enforce confidentiality and model/provider eligibility.
        # Never send private data outside the platform just because an
        # optional editorial callback exists.
        response = editor_assistant({
            "language": manifest["language"],
            "scenes": [{"kind": s["kind"], "text": s["text"]} for s in manifest["scenes"]],
            "instructions": ("Return concise editorial clarity suggestions only. "
                             "Do not invent facts, timestamps, KPIs or citations."),
        })
        if not isinstance(response, dict) or "suggestions" not in response or not isinstance(response["suggestions"], list):
            raise AgentReviewError("Editorial assistant returned an invalid result")
        model_output = {
            "status": "ADVISORY_ONLY",
            "suggestions": [str(x)[:300] for x in response["suggestions"][:8]],
        }
    return {
        "manifest_sha256": digest(manifest),
        "checks": checks,
        "editorial_assistant": model_output,
        "publication_allowed": False,
        "requires_human_review": True,
        "source_truth_verified": False,
    }
