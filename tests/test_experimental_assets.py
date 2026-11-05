import tempfile
import unittest
import zipfile
from pathlib import Path
from server.experimental_assets import identify,UnsupportedAsset

class AssetSafetyTests(unittest.TestCase):
    def test_pdf_signature(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"synthetic.pdf";p.write_bytes(b"%PDF-1.4\\nsynthetic fixture")
            self.assertEqual(identify(p)["kind"],"pdf")
    def test_reject_fake_image(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fake.png";p.write_bytes(b"not a png")
            with self.assertRaises(UnsupportedAsset):identify(p)
    def test_pbix_metadata_not_model(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"synthetic.pbix"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("Report/Layout","{}")
                z.writestr("DataModel",b"synthetic")
            r=identify(p)
            self.assertTrue(r["has_report_layout"])
            self.assertIn("metadata_only",r["status"])
    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.pbix"
            with zipfile.ZipFile(p,"w") as z:z.writestr("../outside","x")
            with self.assertRaises(UnsupportedAsset):identify(p)

if __name__=="__main__":
    unittest.main()
