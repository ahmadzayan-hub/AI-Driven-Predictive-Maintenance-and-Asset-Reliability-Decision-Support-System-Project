"""Real local Arabic glyph shaping + FFmpeg audio/video media regression.

Synthetic assets only. Confirms codecs, duration, frame rate and RTL support.
Does not assert that a synthesized tone is intelligible Arabic speech.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motion_studio_frames import render_frames
from motion_studio_quality import inspect_mp4
from motion_studio_render import mux_frames

STORYBOARD = {
    "schema": "motion-evidence-v1", "language": "ar", "format": "wide",
    "classification": "SYNTHETIC", "duration": 3,
    "scenes": [
        {"kind": kind, "text": text, "evidence": [{
            "source_id": "SYNTHETIC-TEST", "revision": "1", "locator": "fixture",
            "data_status": "SYNTHETIC"}]}
        for kind, text in (
            ("hook", "الهندسة والموثوقية"),
            ("evidence", "تحليل البيانات بصورة توضيحية"),
            ("action", "المراجعة البشرية مطلوبة"),
        )
    ],
}


class ArabicMotionEndToEnd(unittest.TestCase):
    def test_real_mp4_with_arabic_frames_and_synced_audio(self):
        try:
            from PIL import features
        except ImportError:
            self.skipTest("Pillow not installed on worker")
        if not features.check("raqm"):
            self.skipTest("Arabic shaping engine (libraqm) is unavailable")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg and ffprobe are required")
        font = next((p for p in [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
        ] if p.exists()), None)
        if font is None:
            self.skipTest("An Arabic-capable test font is required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            frames = root / "frames"
            count = render_frames(STORYBOARD, frames, font, duration=3)
            self.assertEqual(count, 90)
            audio = root / "test-tone.wav"
            subprocess.run([
                "ffmpeg", "-v", "error", "-nostdin", "-y",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=3",
                "-c:a", "pcm_s16le", str(audio),
            ], capture_output=True, timeout=30, check=True)
            output = root / "motion.mp4"
            info = mux_frames(frames, output, audio, duration=3)
            qa = inspect_mp4(output, expect_audio=True, expected_duration=3)
            self.assertEqual(info["status"], "DRAFT_REQUIRES_HUMAN_REVIEW")
            self.assertEqual(qa["status"], "TECHNICAL_CHECKS_PASSED_NOT_PUBLISHED")
            self.assertEqual(qa["fps"], 30)
            self.assertTrue(qa["audio"])


if __name__ == "__main__":
    unittest.main()
