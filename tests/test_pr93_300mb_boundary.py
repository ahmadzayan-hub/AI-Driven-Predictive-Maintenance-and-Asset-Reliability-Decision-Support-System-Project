"""Opt-in 300,000,000 byte disk spool boundary check; no hosted application.

Run: MIYAAR_LARGE_STRESS=1 python -m unittest tests.test_pr93_300mb_boundary -v
Requires ~600 MB transient disk writes; uses only synthetic bytes and a temp directory.
The regular CI suite skips these stress probes unless explicitly enabled.
"""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from server.experimental_ingest import spool, LargeIntakeError, MAX_UPLOAD_BYTES


def chunks(n):
    block = b"0123456789ABCDEF" * (1024 * 64)
    full, remainder = divmod(n, len(block))
    for _ in range(full):
        yield block
    if remainder:
        yield block[:remainder]


@unittest.skipUnless(os.environ.get("MIYAAR_LARGE_STRESS") == "1",
                     "opt-in only: synthetic 300 MB disk stress")
class LargeSpoolBoundary(unittest.TestCase):
    def test_exact_limit_and_one_byte_over_are_atomic(self):
        with tempfile.TemporaryDirectory(prefix="miyaar-large-") as d:
            dst = Path(d) / "synthetic.bin"
            result = spool(chunks(MAX_UPLOAD_BYTES), dst)
            self.assertEqual(result["bytes"], 300_000_000)
            self.assertEqual(dst.stat().st_size, MAX_UPLOAD_BYTES)
            old_hash = result["sha256"]
            with self.assertRaises(LargeIntakeError):
                spool(chunks(MAX_UPLOAD_BYTES + 1), dst)
            self.assertEqual(dst.stat().st_size, MAX_UPLOAD_BYTES)
            with dst.open("rb") as f:
                self.assertEqual(hashlib.file_digest(f, "sha256").hexdigest(), old_hash)
            self.assertEqual(list(Path(d).glob(".incoming-*")), [])

    def test_bad_chunks_and_empty_upload_cleanup(self):
        with tempfile.TemporaryDirectory(prefix="miyaar-bad-") as d:
            dst = Path(d) / "synthetic.bin"
            for bad in ([], [b"x", "non-bytes"]):
                with self.subTest(bad=bad):
                    with self.assertRaises(LargeIntakeError):
                        spool(bad, dst)
                    self.assertFalse(dst.exists())
                    self.assertEqual(list(Path(d).glob(".incoming-*")), [])
