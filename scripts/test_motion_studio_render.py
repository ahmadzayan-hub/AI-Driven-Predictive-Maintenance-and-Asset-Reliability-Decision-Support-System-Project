"""Offline trust and synchronization checks for the MP4 worker contract."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from motion_studio_render import MotionInputError, mux_frames, validate

SAMPLE = {
    "schema": "motion-evidence-v1", "language": "ar", "format": "wide",
    "classification": "INTERNAL", "duration": 12,
    "scenes": [
        {"kind": kind, "text": text, "evidence": [{
            "source_id": "src1", "revision": "rev1",
            "locator": "p2", "data_status": "VERIFIED"}]}
        for kind, text in [
            ("hook", "Engineering summary"),
            ("evidence", "Source-backed finding"),
            ("action", "Human review required")]
    ],
}

class MotionContractTests(unittest.TestCase):
    def test_valid_manifest(self):
        self.assertEqual(validate(SAMPLE)["duration"], 12)

    def test_operational_evidence_cannot_be_synthetic(self):
        import copy
        x = copy.deepcopy(SAMPLE)
        x["scenes"][0]["evidence"][0]["data_status"] = "SYNTHETIC"
        with self.assertRaises(MotionInputError):
            validate(x)

    def test_missing_source_ref_is_refused(self):
        import copy
        x = copy.deepcopy(SAMPLE)
        x["scenes"][1]["evidence"] = []
        with self.assertRaises(MotionInputError):
            validate(x)

    def test_no_automated_approval(self):
        with self.assertRaises(MotionInputError):
            validate(SAMPLE, require_approval=True)

    def test_missing_frames_are_refused(self):
        with TemporaryDirectory() as temp:
            with self.assertRaises(MotionInputError):
                mux_frames(Path(temp), Path(temp) / "video.mp4", duration=12)

if __name__ == "__main__":
    unittest.main()
