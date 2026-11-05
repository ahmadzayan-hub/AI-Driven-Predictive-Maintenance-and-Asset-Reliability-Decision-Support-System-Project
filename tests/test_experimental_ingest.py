"""Isolated unit tests; these do not assert production MIYAAR supports 300MB."""
import csv
import tempfile
import unittest
from pathlib import Path
from server.experimental_ingest import LargeIntakeError, spool, index_csv, page

class LargeIntakeTests(unittest.TestCase):
    def test_atomic_limit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"file.csv"
            self.assertEqual(spool([b"ab",b"cd"],p,max_bytes=4)["bytes"],4)
            with self.assertRaises(LargeIntakeError):
                spool([b"abcde"],p,max_bytes=4)
            self.assertEqual(p.read_bytes(),b"abcd")

    def test_wide_and_paged(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"wide.csv"
            with p.open("w",newline="") as f:
                w=csv.writer(f)
                w.writerow([f"c{i}" for i in range(501)])
                for n in range(1201):
                    w.writerow([str(n)]*501)
            db=Path(d)/"index.db"
            self.assertEqual(index_csv(p,db),{"rows":1201,"columns":501})
            self.assertEqual(len(page(db,after=1198,size=20)["rows"]),3)

if __name__=="__main__":
    unittest.main()
