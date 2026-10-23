"""Post-render MP4 integrity checks. No publication side-effects.

Independent ffprobe inspection ensures a real H.264/AAC output and duration
agreement; a successful encoder exit is not sufficient evidence on its own.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


class MediaQualityError(ValueError):
    pass


def inspect_mp4(path: Path, *, expect_audio: bool, expected_duration: float,
                fps: int = 30, tolerance: float = 0.12) -> dict:
    if path.suffix.lower() != ".mp4" or not path.is_file() or path.stat().st_size < 1024:
        raise MediaQualityError("Missing or implausibly small MP4")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(path)],
        capture_output=True, timeout=25, check=False,
    )
    if probe.returncode:
        raise MediaQualityError("Unable to inspect MP4")
    try:
        data = json.loads(probe.stdout)
        streams = data["streams"]
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        if len(videos) != 1 or videos[0].get("codec_name") != "h264":
            raise MediaQualityError("Expected one H.264 video stream")
        video = videos[0]
        if video.get("pix_fmt") != "yuv420p":
            raise MediaQualityError("Video must be yuv420p")
        numerator, denominator = (int(x) for x in video["avg_frame_rate"].split("/"))
        if denominator == 0 or numerator / denominator != fps:
            raise MediaQualityError("Video average frame rate is not 30fps")
        if bool(audios) != expect_audio:
            raise MediaQualityError("Audio stream presence does not match request")
        if expect_audio:
            if len(audios) != 1 or audios[0].get("codec_name") != "aac":
                raise MediaQualityError("Expected one AAC audio stream")
            if int(audios[0].get("sample_rate", 0)) != 48000:
                raise MediaQualityError("Audio must be 48 kHz")
        duration = float(data["format"]["duration"])
        if not math.isfinite(duration) or abs(duration - expected_duration) > tolerance:
            raise MediaQualityError("Container duration disagrees with narration/timeline")
        if expect_audio:
            stream_duration = float(audios[0].get("duration", duration))
            if abs(stream_duration - expected_duration) > tolerance:
                raise MediaQualityError("Audio stream duration differs from timeline")
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as exc:
        if isinstance(exc, MediaQualityError):
            raise
        raise MediaQualityError("Invalid codec, timestamp or media metadata") from exc
    return {
        "status": "TECHNICAL_CHECKS_PASSED_NOT_PUBLISHED",
        "codec": "h264",
        "pix_fmt": "yuv420p",
        "fps": fps,
        "duration": duration,
        "audio": expect_audio,
        "size_bytes": path.stat().st_size,
    }
