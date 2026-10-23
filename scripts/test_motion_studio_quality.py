import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from motion_studio_quality import MediaQualityError, inspect_mp4


class QualityContract(unittest.TestCase):
    def test_refuses_missing_media(self):
        with TemporaryDirectory() as td:
            with self.assertRaises(MediaQualityError):
                inspect_mp4(Path(td) / "missing.mp4", expect_audio=True, expected_duration=10)

    def test_refuses_non_mp4(self):
        with TemporaryDirectory() as td:
            file = Path(td) / "fake.mp4"
            file.write_bytes(b"not a movie")
            with self.assertRaises(MediaQualityError):
                inspect_mp4(file, expect_audio=False, expected_duration=10)


if __name__ == "__main__":
    unittest.main()
