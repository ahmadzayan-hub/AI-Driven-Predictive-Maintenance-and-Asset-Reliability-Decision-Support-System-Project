"""Deterministic Motion Studio media QA, independent of an LLM.

Checks the *actual encoded MP4*, not an export command exit status.
This is one gate in a larger human/governance release workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

MAX_SECONDS = 180.0
FRAME_RATE = 30.0


class VideoQAError(ValueError):
    pass


def _probe(video: Path) -> dict:
    if not shutil.which("ffprobe"):
        raise VideoQAError("ffprobe is required on the isolated renderer")
    if not video.is_file() or video.suffix.lower() != ".mp4":
        raise VideoQAError("A real .mp4 file is required")
    if video.stat().st_size <= 1024:
        raise VideoQAError("Video file is empty or truncated")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(video)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
    )
    if result.returncode:
        raise VideoQAError("Unable to inspect the MP4 container")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise VideoQAError("Malformed ffprobe output") from exc


def _ratio(text: str) -> float:
    a, sep, b = str(text).partition("/")
    if not sep:
        return float(a)
    divisor = float(b)
    return float(a) / divisor if divisor else 0.0


def inspect_mp4(video: Path, *, expected_seconds: float | None = None,
                narration_expected: bool = True,
                expected_format: str | None = None) -> dict:
    """Return release QA evidence, fail closed on unsupported, missing or drifted media."""
    data = _probe(video)
    streams = data.get("streams") or []
    vids = [s for s in streams if s.get("codec_type") == "video"]
    auds = [s for s in streams if s.get("codec_type") == "audio"]
    if len(vids) != 1:
        raise VideoQAError("Exactly one video stream is required")
    v = vids[0]
    if v.get("codec_name") != "h264" or v.get("pix_fmt") != "yuv420p":
        raise VideoQAError("H.264/yuv420p encoding is required")
    if not math.isclose(_ratio(v.get("avg_frame_rate", "0")), FRAME_RATE, abs_tol=.01):
        raise VideoQAError("Video must be constant 30fps")
    if v.get("width") is None or v.get("height") is None:
        raise VideoQAError("No video dimensions recorded")
    size = (v["width"], v["height"])
    accepted = {"wide": (1280, 720), "vertical": (720, 1280)}
    if expected_format and size != accepted.get(expected_format):
        raise VideoQAError("Video dimensions do not match requested format")
    if size not in accepted.values():
        raise VideoQAError("Unexpected frame dimensions")
    if narration_expected and len(auds) != 1:
        raise VideoQAError("Expected narration soundtrack is missing")
    if auds and (len(auds) != 1 or auds[0].get("codec_name") != "aac"
                 or int(auds[0].get("sample_rate") or 0) != 48000):
        raise VideoQAError("Require a single AAC audio stream at 48kHz")
    duration = float(data.get("format", {}).get("duration") or 0)
    if not 3 <= duration <= MAX_SECONDS + .1:
        raise VideoQAError("Video duration outside the 3–180 second contract")
    # Codec priming and MP4 container rounding can add up to 2 frames;
    # a larger deviation indicates narration/frame drift.
    if expected_seconds is not None and abs(duration - expected_seconds) > 2/FRAME_RATE + .012:
        raise VideoQAError("MP4 length does not match the approved narration / frame contract")
    if narration_expected and auds:
        a_duration = float(auds[0].get("duration") or duration)
        if abs(a_duration - duration) > 2/FRAME_RATE + .012:
            raise VideoQAError("Audio stream duration does not match video duration")
    digest = hashlib.sha256()
    with video.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return {
        "qa": "PASS_TECHNICAL_CONTRACT_ONLY",
        "sha256": digest.hexdigest(),
        "format": "wide" if size == accepted["wide"] else "vertical",
        "duration_seconds": round(duration, 3),
        "video_codec": v["codec_name"],
        "pixel_format": v["pix_fmt"],
        "fps": round(_ratio(v.get("avg_frame_rate", "0")), 3),
        "audio_codec": auds[0].get("codec_name") if auds else None,
        "audio_sample_rate": int(auds[0].get("sample_rate") or 0) if auds else None,
        "human_review": "PENDING",
        "issued": False,
        "limitations": [
            "Does not verify Arabic pronunciation or speech-to-scene semantics",
            "Does not authorize publication or official RTA branding",
            "Does not validate edited claims against original source content",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a rendered MP4 before human review")
    parser.add_argument("video", type=Path)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--format", choices=("wide", "vertical"))
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_mp4(
            args.video, expected_seconds=args.duration,
            narration_expected=not args.silent, expected_format=args.format,
        )
    except (VideoQAError, OSError, ValueError) as exc:
        parser.exit(2, f"Motion QA refused: {exc}\n")
    raw = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        if args.output.exists():
            parser.exit(2, "Refusing to overwrite an existing QA record\n")
        args.output.write_text(raw + "\n", encoding="utf-8")
    print(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
