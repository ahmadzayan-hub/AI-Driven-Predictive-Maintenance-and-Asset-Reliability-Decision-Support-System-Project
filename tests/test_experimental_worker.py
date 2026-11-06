import hashlib
import tempfile
import unittest
from pathlib import Path
from server.experimental_jobs import submit,status
from server.experimental_worker import process_one

class SyntheticWorkerTests(unittest.TestCase):
    def test_synthetic_artifact_requires_review(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            request=hashlib.sha256(b"synthetic brief").hexdigest()
            job=submit(root/"jobs.db",owner="alice",kind="video",request_sha256=request)
            result=process_one(root/"jobs.db",root/"private",worker_id="w1",
                               kind="video",render=lambda kind,j:b"synthetic-film-bytes")
            self.assertEqual(result["id"],job["id"])
            self.assertEqual(status(root/"jobs.db",owner="alice",job_id=job["id"])["state"],"awaiting_review")
            self.assertIsNone(process_one(root/"jobs.db",root/"private",worker_id="w1",
                                          kind="video",render=lambda k,j:b"another"))
            self.assertIsNone(status(root/"jobs.db",owner="bob",job_id=job["id"]))
    def test_invalid_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            job=submit(root/"jobs.db",owner="alice",kind="video",
                       request_sha256=hashlib.sha256(b"bad").hexdigest())
            with self.assertRaises(ValueError):
                process_one(root/"jobs.db",root/"private",worker_id="w1",
                            kind="video",render=lambda kind,j:b"")
            self.assertEqual(status(root/"jobs.db",owner="alice",job_id=job["id"])["state"],"failed")
            self.assertEqual(list((root/"private").glob("*.mp4")),[])

if __name__=="__main__":
    unittest.main()
