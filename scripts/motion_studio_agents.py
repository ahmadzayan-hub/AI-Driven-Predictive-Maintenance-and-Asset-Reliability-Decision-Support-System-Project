"""Local advisory agents for source-grounded motion drafts.

No provider calls. An external model may only be configured separately
after host authorization, confidentiality filtering and prompt-injection review.
Agent findings are advisory; never change approval or issue status.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from motion_studio_render import MotionInputError, validate


@dataclass(frozen=True)
class AdvisoryFinding:
    reviewer: str
    code: str
    scene: int
    message: str


def review_storyboard(manifest: Mapping) -> tuple[AdvisoryFinding, ...]:
    validate(dict(manifest))
    results: list[AdvisoryFinding] = []
    for n, scene in enumerate(manifest["scenes"], 1):
        text = scene["text"]
        if len(text) > 160:
            results.append(AdvisoryFinding(
                "readability", "DENSE_SCENE", n,
                "Consider dividing the content or extending this scene; do not silently truncate cited facts."
            ))
        if re.search(r"(?<!\w)\d+(?:\.\d+)?\s*%", text):
            results.append(AdvisoryFinding(
                "statistical_integrity", "VERIFY_PERCENT_DENOMINATOR", n,
                "Check the percentage numerator, denominator, reference period and source with a human reviewer."
            ))
        if re.search(r"(?i)\b(guaranteed|100% accuracy|proven cause|zero risk)\b", text):
            results.append(AdvisoryFinding(
                "claims", "UNSUPPORTED_CERTAINTY_LANGUAGE", n,
                "Verify unusually strong claims and display uncertainty, or remove unsupported language."
            ))
        if manifest["language"] == "ar" and not re.search(r"[\u0600-\u06ff]", text):
            results.append(AdvisoryFinding(
                "arabic", "ARABIC_COPY_REVIEW", n,
                "The Arabic-language project has a scene without Arabic text; request a professional language review."
            ))
    return tuple(results)


def review_report(manifest: Mapping) -> dict:
    findings = review_storyboard(manifest)
    return {
        "approval_state": "DRAFT_REQUIRES_HUMAN_REVIEW",
        "checked_scenes": 3,
        "reviewers": ["readability", "statistical_integrity", "claims", "arabic"],
        "advisories": [f.__dict__ for f in findings],
        "note": "Advisory rules cannot verify numerical truth, Arabic speech, rights or authorize release.",
    }
