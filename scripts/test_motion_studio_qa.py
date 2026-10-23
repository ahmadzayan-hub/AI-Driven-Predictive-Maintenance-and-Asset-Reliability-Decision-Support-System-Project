import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from motion_studio_qa import inspect_mp4

DATA = {"format": {"duration": "15.0"}, "streams": [
    {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
     "avg_frame_rate": "30/1", "width": 1920, "height": 1080},
    {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000"},
]}


class InspectionTests(unittest.TestCase):
    def test_missing_file_is_blocked(self):
        self.assertFalse(inspect_mp4(Path("/nonexistent/motion-qa-test.mp4"), expected_duration=15).passed)

    def test_valid_mp4_metadata_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "draft.mp4"
            file.write_bytes(b"x" * 2048)
            with patch("motion_studio_qa.subprocess.run", return_value=Mock(stdout=json.dumps(DATA))):
                check = inspect_mp4(file, expected_duration=15)
                self.assertTrue(check.passed)
                self.assertTrue(check.audio_present)

    def test_missing_audio_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "draft.mp4"
            file.write_bytes(b"x" * 2048)
            with patch("motion_studio_qa.subprocess.run", return_value=Mock(
                stdout=json.dumps({"format": DATA["format"], "streams": DATA["streams"][:1]})
            )):
                check = inspect_mp4(file, expected_duration=15)
                self.assertIn("missing_narration", check.failures)
