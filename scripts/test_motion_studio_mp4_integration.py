"""Synthetic integration proof: real FFmpeg mux and ffprobe inspection.

No RTA/customer source media or uploaded private records are used.
This test proves codec/timing only, not Arabic voice quality or visual approval.
"""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from motion_studio_quality import inspect_mp4


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Requires approved FFmpeg and ffprobe installation")
class Mp4SyntheticIntegration(unittest.TestCase):
    def test_real_three_second_h264_aac_file(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "synthetic-probe.mp4"
            command = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                "-f", "lavfi", "-i", "color=c=0x112b48:s=640x360:r=30:d=3",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=3:sample_rate=48000",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                "-c:a", "aac", "-ar", "48000", "-t", "3",
                "-movflags", "+faststart", str(output),
            ]
            subprocess.run(command, check=True, timeout=45, capture_output=True)
            info = inspect_mp4(output, expect_audio=True, expected_duration=3)
            self.assertEqual(info["codec"], "h264")
            self.assertTrue(info["audio"])
            self.assertEqual(info["fps"], 30)
            self.assertEqual(info["status"], "TECHNICAL_CHECKS_PASSED_NOT_PUBLISHED")


if __name__ == "__main__":
    unittest.main()
