"""Motion Studio exported-container validation: strict codec, FPS, duration and audio gates."""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from motion_studio_qc import VideoQAError, inspect_mp4


def fake_probe(*, audio=True, rate="30/1", video="h264", duration="3.000", pix="yuv420p"):
    rows = [
        {"codec_type": "video", "codec_name": video, "pix_fmt": pix,
         "avg_frame_rate": rate, "width": 1280, "height": 720},
    ]
    if audio:
        rows.append({"codec_type": "audio", "codec_name": "aac",
                     "sample_rate": "48000", "duration": duration})
    return {"streams": rows, "format": {"duration": duration}}


class MotionVideoQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.video = Path(self.temp.name) / "test.mp4"
        self.video.write_bytes(b"MP4-test-fixture" * 400)

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, data, **kwargs):
        with patch("motion_studio_qc._probe", return_value=data):
            return inspect_mp4(self.video, **kwargs)

    def test_valid_mp4_requires_human_review(self):
        result = self.inspect(fake_probe(), expected_seconds=3.0)
        self.assertEqual(result["qa"], "PASS_TECHNICAL_CONTRACT_ONLY")
        self.assertEqual(result["human_review"], "PENDING")
        self.assertFalse(result["issued"])
        self.assertEqual(result["audio_sample_rate"], 48000)
        self.assertEqual(len(result["sha256"]), 64)

    def test_silent_video_fails_when_narration_expected(self):
        with self.assertRaises(VideoQAError):
            self.inspect(fake_probe(audio=False))

    def test_silent_video_passes_only_with_explicit_flag(self):
        result = self.inspect(fake_probe(audio=False), narration_expected=False)
        self.assertIsNone(result["audio_codec"])

    def test_wrong_frame_rate_is_refused(self):
        with self.assertRaises(VideoQAError):
            self.inspect(fake_probe(rate="25/1"))

    def test_wrong_codec_is_refused(self):
        with self.assertRaises(VideoQAError):
            self.inspect(fake_probe(video="vp9"))

    def test_audio_drifts_more_than_two_frames(self):
        with self.assertRaises(VideoQAError):
            self.inspect(fake_probe(duration="3.6"), expected_seconds=3.0)

    def test_bad_frame_dimensions_are_refused(self):
        with self.assertRaises(VideoQAError):
            self.inspect(fake_probe(), expected_format="vertical")


if __name__ == "__main__":
    unittest.main()
