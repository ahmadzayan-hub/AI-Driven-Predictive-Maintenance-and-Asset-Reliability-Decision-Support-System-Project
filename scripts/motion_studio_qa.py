"""Independent, offline MP4 quality inspector for Motion Studio.

Only inspects files through ffprobe; never equates a passing technical
inspection with permission to issue or publish material.
"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoInspection:
    passed: bool
    failures: tuple[str, ...]
    duration_seconds: float | None
    video_fps: float | None
    audio_present: bool
    metadata: dict


def _fps(raw: str) -> float:
    try:
        numerator, denominator = raw.split("/")
        value = float(numerator) / float(denominator)
        return value if math.isfinite(value) else 0.0
    except (ValueError, ZeroDivisionError, AttributeError):
        return 0.0


def inspect_mp4(path: Path, *, expected_duration: float, require_audio: bool = True,
                ffprobe: str = "ffprobe") -> VideoInspection:
    issues: list[str] = []
    if path.suffix.lower() != ".mp4" or not path.is_file() or path.stat().st_size < 1024:
        return VideoInspection(False, ("missing_or_invalid_mp4",), None, None, False, {})
    try:
        output = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            timeout=25, check=True, capture_output=True, text=True,
        )
        data = json.loads(output.stdout)
    except (OSError, ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return VideoInspection(False, ("unreadable_media_or_ffprobe_missing",), None, None, False, {})
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    try:
        duration = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        duration = None
    fps = _fps(video.get("avg_frame_rate", "")) if video else None
    if not video:
        issues.append("missing_video")
    else:
        if video.get("codec_name") != "h264":
            issues.append("video_not_h264")
        if video.get("pix_fmt") != "yuv420p":
            issues.append("video_not_yuv420p")
        if fps is None or abs(fps - 30) > 0.05:
            issues.append("fps_not_30")
        if int(video.get("width") or 0) <= 0 or int(video.get("height") or 0) <= 0:
            issues.append("invalid_geometry")
    if require_audio and not audio:
        issues.append("missing_narration")
    if audio:
        if audio.get("codec_name") != "aac":
            issues.append("audio_not_aac")
        if str(audio.get("sample_rate")) != "48000":
            issues.append("audio_not_48khz")
    if duration is None or not math.isfinite(duration) or abs(duration - expected_duration) > 0.1:
        issues.append("duration_mismatch")
    # No raw filename or private metadata in the user-facing QA report.
    sanitized = {
        "video_codec": video.get("codec_name") if video else None,
        "resolution": [video.get("width"), video.get("height")] if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_sample_rate": audio.get("sample_rate") if audio else None,
    }
    return VideoInspection(not issues, tuple(issues), duration, fps, bool(audio), sanitized)
