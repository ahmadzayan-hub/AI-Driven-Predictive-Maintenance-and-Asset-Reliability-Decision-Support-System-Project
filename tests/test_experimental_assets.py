import tempfile
import stat
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
    def test_wrong_valid_signature_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"renamed.png"
            p.write_bytes(bytes.fromhex("ffd8ffe000104a464946"))
            with self.assertRaises(UnsupportedAsset):
                identify(p)

    def test_pbix_metadata_not_model(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"synthetic.pbix"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("Report/Layout","{}")
                z.writestr("DataModel",b"synthetic")
            r=identify(p)
            self.assertTrue(r["has_report_layout"])
            self.assertIn("metadata_only",r["status"])
    def test_reject_pbix_expansion_bomb(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bomb.pbix"
            with zipfile.ZipFile(p,"w",compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("DataModel", b"0" * (2 * 1024 * 1024))
            with self.assertRaisesRegex(UnsupportedAsset, "compression ratio"):
                identify(p)

    def test_reject_pbix_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"linked.pbix"
            with zipfile.ZipFile(p,"w") as z:
                info=zipfile.ZipInfo("Report/Layout")
                info.create_system=3
                info.external_attr=(stat.S_IFLNK | 0o777) << 16
                z.writestr(info,"../../outside")
            with self.assertRaisesRegex(UnsupportedAsset, "symbolic links"):
                identify(p)

    def test_reject_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bad.pbix"
            with zipfile.ZipFile(p,"w") as z:z.writestr("../outside","x")
            with self.assertRaises(UnsupportedAsset):identify(p)

if __name__=="__main__":
    unittest.main()
