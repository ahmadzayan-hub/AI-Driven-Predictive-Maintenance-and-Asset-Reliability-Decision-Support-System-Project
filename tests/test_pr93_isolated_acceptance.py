"""Additional isolated acceptance checks for PR #93.

Run on a disposable checkout of this branch:
  python -m unittest tests.test_pr93_isolated_acceptance -v
No network, hosted DB, production writes or video provider.
Failures here are release blockers, not proof of production support.
"""
import csv
import hashlib
import tempfile
import tracemalloc
import unittest
from pathlib import Path

from server.experimental_assets import identify, UnsupportedAsset
from server.experimental_ingest import spool, index_csv, page, LargeIntakeError
from server.experimental_jobs import submit, status
from server.experimental_stream import accept, health


class PR93IsolatedAcceptance(unittest.TestCase):
    def test_valid_png_must_be_recognized(self):
        # A real PNG header, no image decoding requested.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "synthetic.png"
            p.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"synthetic")
            self.assertEqual(identify(p)["kind"], "image")

    def test_valid_jpeg_must_be_recognized(self):
        with tempfile.TemporaryDirectory() as d:
            for extension in ("jpg", "jpeg"):
                with self.subTest(extension=extension):
                    p = Path(d) / ("synthetic." + extension)
                    p.write_bytes(bytes.fromhex("ffd8ffe000104a464946") + b"synthetic")
                    self.assertEqual(identify(p)["kind"], "image")

    def test_valid_tiff_must_be_recognized(self):
        with tempfile.TemporaryDirectory() as d:
            for extension in ("tif", "tiff"):
                for header in ("49492a00", "4d4d002a"):
                    with self.subTest(extension=extension, header=header):
                        p = Path(d) / ("synthetic." + extension)
                        p.write_bytes(bytes.fromhex(header) + b"synthetic")
                        self.assertEqual(identify(p)["kind"], "image")

    def test_literal_escape_text_is_not_an_image_signature(self):
        with tempfile.TemporaryDirectory() as d:
            for extension, text in (("png", br"\x89PNG\r\n\x1a\n"),
                                    ("jpg", br"\xff\xd8\xff"),
                                    ("tif", br"II*\x00")):
                with self.subTest(extension=extension):
                    p = Path(d) / ("synthetic." + extension)
                    p.write_bytes(text)
                    with self.assertRaises(UnsupportedAsset):
                        identify(p)

    def test_wrong_extension_image_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "synthetic.png"
            p.write_bytes(bytes.fromhex("ffd8ffe000104a464946"))
            with self.assertRaises(UnsupportedAsset):
                identify(p)

    def test_spool_to_index_to_page_and_ground_truth(self):
        # Cross-module integration, not the user-facing HTTP upload.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src, db = root / "input.csv", root / "index.sqlite"
            columns = ["asset_id", "downtime_hours", "maintenance_aed"] + [
                "extra_" + str(i) for i in range(498)
            ]
            with src.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(columns)
                for i in range(1201):
                    w.writerow(["SYN-" + str(i), str(i % 7), str((i % 11) * 25)] + [""] * 498)
            expected_bytes = src.read_bytes()
            target = root / "staged.csv"
            def chunks():
                with src.open("rb") as f:
                    while chunk := f.read(32 * 1024):
                        yield chunk
            result = spool(chunks(), target)
            self.assertEqual(result["sha256"], hashlib.sha256(expected_bytes).hexdigest())
            self.assertEqual(index_csv(target, db), {"rows": 1201, "columns": 501})
            total_downtime = total_cost = observed_rows = 0
            after = 0
            while True:
                batch = page(db, after=after, size=137)
                if not batch["rows"]:
                    break
                for record in batch["rows"]:
                    values = record["values"]
                    total_downtime += int(values[1])
                    total_cost += int(values[2])
                    observed_rows += 1
                after = batch["next"]
            self.assertEqual(observed_rows, 1201)
            self.assertEqual(total_downtime, sum(i % 7 for i in range(1201)))
            self.assertEqual(total_cost, sum((i % 11) * 25 for i in range(1201)))

    def test_spool_atomicity_rejects_limit_overrun(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "staged.csv"
            self.assertEqual(spool([b"abc"], target, max_bytes=3)["bytes"], 3)
            with self.assertRaises(LargeIntakeError):
                spool([b"abcd"], target, max_bytes=3)
            self.assertEqual(target.read_bytes(), b"abc")

    def test_owner_isolation_across_queue_and_stream(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            digest = hashlib.sha256(b"synthetic").hexdigest()
            job = submit(root / "jobs.db", owner="tenant-a", kind="ingest", request_sha256=digest)
            self.assertIsNone(status(root / "jobs.db", owner="tenant-b", job_id=job["id"]))
            event = {"id": "e1", "event_time": "2026-11-05T10:00:00+00:00", "payload": {"downtime": 2}}
            for owner in ("tenant-a", "tenant-b"):
                self.assertEqual(accept(root / "events.db", owner=owner, source="synthetic",
                    event=event, received_at=1793872800, max_future_skew_s=3600)["status"], "accepted")
            self.assertEqual(health(root / "events.db", owner="tenant-a", source="synthetic",
                now=1793872800)["accepted"], 1)
            self.assertEqual(health(root / "events.db", owner="tenant-b", source="synthetic",
                now=1793872800)["accepted"], 1)

    def test_bounded_peak_python_memory_for_streamed_csv(self):
        # A diagnostic budget only; excludes OS page cache and SQLite native allocations.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "large.csv"
            with src.open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["asset", "hours"])
                for i in range(50000):
                    w.writerow([i, i % 23])
            tracemalloc.start()
            try:
                indexed = index_csv(src, root / "index.db", batch_size=250)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(indexed, {"rows": 50000, "columns": 2})
            self.assertLess(peak, 64 * 1024 * 1024,
                "Python heap exceeded diagnostic 64 MiB threshold")

if __name__ == "__main__":
    unittest.main()
