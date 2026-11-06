"""Synthetic contract probes for the actual MIYAAR dataset reader on this branch.

These are deliberately small integration probes, NOT hosted-browser or 300 MB tests.
"""
import io
import json
import unittest

from server import datasets

class CurrentDatasetContract(unittest.TestCase):
    def test_small_csv_is_accepted(self):
        p=datasets.read(b"asset_id,downtime_hours\nSYN-001,2.5\n", "synthetic.csv")
        self.assertEqual(len(p.rows),1)
        self.assertEqual(len(p.columns),2)

    def test_tabular_json_is_accepted(self):
        source=json.dumps([{"asset_id":"SYN-01","cost_aed":100},
                           {"asset_id":"SYN-02","cost_aed":150}]).encode()
        parsed=datasets.read(source,"synthetic.json")
        self.assertEqual(len(parsed.rows),2)

    def test_501_columns_are_explicitly_rejected(self):
        data=(",".join("c"+str(i) for i in range(501))+"\n"+",".join("1" for _ in range(501))+"\n").encode()
        with self.assertRaises(datasets.DatasetError):
            datasets.read(data,"wide.csv")

    def test_oversize_is_explicitly_rejected(self):
        data=b"a,b\n"+b"x"*(datasets.MAX_UPLOAD_BYTES+1)
        with self.assertRaises(datasets.DatasetError) as context:
            datasets.read(data,"oversize.csv")
        self.assertEqual(context.exception.status,413)

    def test_empty_is_explicitly_rejected(self):
        with self.assertRaises(datasets.DatasetError):
            datasets.read(b"","empty.csv")

    def test_document_is_not_silently_a_table(self):
        with self.assertRaises(datasets.DatasetError):
            datasets.read(b"%PDF-1.4\nsynthetic","synthetic.pdf")

    def test_renamed_pdf_is_not_silently_csv(self):
        with self.assertRaises(datasets.DatasetError) as error:
            datasets.read(b"%PDF-1.7\\nsynthetic", "renamed.csv")
        self.assertEqual(error.exception.status, 415)

    def test_renamed_png_is_not_silently_csv(self):
        with self.assertRaises(datasets.DatasetError):
            datasets.read(bytes.fromhex("89504e470d0a1a0a") + b"synthetic", "renamed.csv")

    def test_parquet_is_not_silently_csv(self):
        with self.assertRaises(datasets.DatasetError):
            datasets.read(b"PAR1synthetic", "renamed.csv")

    def test_pbix_is_not_silently_a_table(self):
        with self.assertRaises(datasets.DatasetError):
            datasets.read(b"PK\x03\x04not-a-valid-pbix","synthetic.pbix")


    def test_explicit_csv_override_cannot_bypass_pdf_guard(self):
        with self.assertRaises(datasets.DatasetError) as error:
            datasets.read(b"%PDF-1.7\\nsynthetic", "renamed.csv", fmt="csv")
        self.assertEqual(error.exception.status, 415)

    def test_explicit_tsv_override_cannot_bypass_image_guard(self):
        with self.assertRaises(datasets.DatasetError) as error:
            datasets.read(bytes.fromhex("89504e470d0a1a0a") + b"synthetic",
                          "renamed.tsv", fmt="tsv")
        self.assertEqual(error.exception.status, 415)

if __name__=="__main__":
    unittest.main()
