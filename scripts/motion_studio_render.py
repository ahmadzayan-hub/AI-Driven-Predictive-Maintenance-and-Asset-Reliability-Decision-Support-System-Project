"""Local motion rendering from evidence-linked, human-reviewed storyboards.

No external network calls. Requires ffmpeg/ffprobe installed on the worker.
Video output is a DRAFT until a reviewer supplies a separate approval record.
No PDF/content extraction is performed here; only upstream-authorized evidence
references in a validated manifest may be cited.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

SUPPORTED = {"VERIFIED", "RECORDED_IN_REGISTER"}
SCENES = 3
MAX_DURATION = 180
MAX_TEXT = 480
SAFE_REF = re.compile(r"^[A-Za-z0-9_.:/#@-]{1,150}$")


class MotionInputError(ValueError):
    pass


def validate(payload: dict, *, require_approval: bool = False) -> dict:
    if payload.get("schema") != "motion-evidence-v1":
        raise MotionInputError("Unsupported manifest schema")
    if payload.get("format") not in ("wide", "vertical"):
        raise MotionInputError("Invalid format")
    if payload.get("language") not in ("ar", "en"):
        raise MotionInputError("Invalid language")
    if payload.get("classification") not in ("SYNTHETIC", "INTERNAL"):
        raise MotionInputError("Select explicit source classification")
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != SCENES:
        raise MotionInputError("Exactly three scenes required")
    duration = payload.get("duration")
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 3 <= duration <= MAX_DURATION:
        raise MotionInputError("Duration must be 3–180 seconds")
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise MotionInputError("Scene must be an object")
        title = scene.get("text")
        if not isinstance(title, str) or not title.strip() or len(title) > MAX_TEXT:
            raise MotionInputError(f"Scene {index + 1} requires a bounded text")
        refs = scene.get("evidence")
        if not isinstance(refs, list) or not refs:
            raise MotionInputError(f"Scene {index + 1} requires source evidence or an explicit synthetic marker")
        for ref in refs:
            if not isinstance(ref, dict):
                raise MotionInputError("Evidence must be an object")
            fields = ("source_id", "revision", "locator", "data_status")
            if any(not isinstance(ref.get(k), str) or not ref[k] for k in fields):
                raise MotionInputError("Evidence must identify source, revision, locator and status")
            if not all(SAFE_REF.fullmatch(ref[k]) for k in ("source_id", "revision", "locator")):
                raise MotionInputError("Unsafe evidence reference format")
            if ref["data_status"] not in SUPPORTED | {"SYNTHETIC"}:
                raise MotionInputError("Unsupported evidence must remain blocked")
            if payload["classification"] == "INTERNAL" and ref["data_status"] not in SUPPORTED:
                raise MotionInputError("Operational video cannot use synthetic or missing evidence")
        if scene.get("kind") not in ("hook", "evidence", "action"):
            raise MotionInputError("Invalid scene role")
    if [x["kind"] for x in scenes] != ["hook", "evidence", "action"]:
        raise MotionInputError("Scene order must be hook, evidence, action")
    if require_approval:
        raise MotionInputError("Issuance is not supported by the rendering CLI; use the existing authorized human decision workflow")
    return payload


def checked_run(args: list[str]) -> None:
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=240, check=False)
    if result.returncode:
        raise MotionInputError((result.stderr or b"Encoder failed")[-1500:].decode("utf-8", "replace"))


def probe_audio(path: Path) -> float:
    if not shutil.which("ffprobe"):
        raise MotionInputError("ffprobe unavailable")
    if not path.is_file() or path.stat().st_size > 80_000_000:
        raise MotionInputError("Invalid local audio file")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
    )
    if result.returncode:
        raise MotionInputError("Audio could not be probed")
    duration = float(result.stdout.decode().strip())
    if not math.isfinite(duration) or not 3 <= duration <= MAX_DURATION:
        raise MotionInputError("Audio duration outside permitted range")
    return duration


def render(payload: dict, output: Path, audio: Path | None = None, *, fps: int = 30) -> dict:
    validate(payload)
    if not shutil.which("ffmpeg"):
        raise MotionInputError("ffmpeg unavailable")
    if fps != 30:
        raise MotionInputError("Use constant 30 fps")
    seconds = probe_audio(audio) if audio else float(payload["duration"])
    size = (1280, 720) if payload["format"] == "wide" else (720, 1280)
    # Rendering from SVG rasterized through ffmpeg's input is not guaranteed
    # across OS builds. Use text-free, precomposed PPM frames and render text
    # separately through the existing browser composition for RTL correctness.
    # This CLI intentionally refuses unsupported high-fidelity text rendering.
    # It produces a background-only proof frame if requested with title metadata,
    # but MUST NOT claim the storyboard text was rendered.
    raise MotionInputError(
        "MP4 text rendering requires an approved browser-frame capture adapter "
        "that provides verified PNG frames at 30 fps; refusing misleading blank video."
    )


def mux_frames(frames_dir: Path, output: Path, audio: Path | None = None, *,
               duration: float | None = None) -> dict:
    """Encode pre-rendered trusted PNG frames with the *full* narration.

    This is production-useful once approved browser renders supply one
    sequential image per frame. Caller must verify source provenance.
    """
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise MotionInputError("ffmpeg and ffprobe are required")
    frames = sorted(frames_dir.glob("frame-*.png"))
    if not frames or len(frames) > MAX_DURATION * 30:
        raise MotionInputError("Missing frames or exceeds 180-second budget")
    for i, f in enumerate(frames):
        if f.name != f"frame-{i:06d}.png" or f.stat().st_size > 5_000_000:
            raise MotionInputError("Non-contiguous or oversized frame")
    frames_duration = len(frames) / 30
    target = probe_audio(audio) if audio else float(duration or frames_duration)
    if abs(frames_duration - target) > 1 / 30 + 0.001:
        raise MotionInputError("Frame and audio lengths differ by more than one frame")
    if output.suffix.lower() != ".mp4":
        raise MotionInputError("Output must be .mp4")
    if output.exists():
        raise MotionInputError("Refusing to overwrite an existing file")
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
           "-framerate", "30", "-i", str(frames_dir / "frame-%06d.png")]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30", "-fps_mode", "cfr"]
    if audio:
        cmd += ["-c:a", "aac", "-ar", "48000", "-b:a", "192k"]
    cmd += ["-t", f"{target:.6f}", "-movflags", "+faststart", str(output)]
    checked_run(cmd)
    return {"output": str(output), "fps": 30, "duration": target,
            "frames": len(frames), "audio": bool(audio), "status": "DRAFT_REQUIRES_HUMAN_REVIEW"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--frames", type=Path,
                        help="Directory containing approved frame-000000.png etc")
    parser.add_argument("--font", type=Path,
                        help="Approved local TTF/OTF for automatic evidence-scene composition")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = validate(json.loads(args.manifest.read_text(encoding="utf-8")))
        duration = probe_audio(args.audio) if args.audio else manifest["duration"]
        if args.frames:
            if args.font:
                raise MotionInputError("Choose either pre-rendered frames or a font")
            result = mux_frames(args.frames, args.output, args.audio, duration=duration)
        elif args.font:
            from motion_studio_frames import render_frames
            with tempfile.TemporaryDirectory(prefix="motion-studio-") as tmp:
                folder = Path(tmp)
                render_frames(manifest, folder, args.font, duration=duration)
                result = mux_frames(folder, args.output, args.audio, duration=duration)
        else:
            raise MotionInputError("Provide --font for local scene rendering or --frames for trusted frames")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Refused: {exc}\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
