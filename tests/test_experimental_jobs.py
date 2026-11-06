import hashlib
import tempfile
import unittest
from pathlib import Path
from server.experimental_jobs import submit,claim,finish,status,heartbeat,retry_failed

class IsolatedJobTests(unittest.TestCase):
    def test_owner_and_idempotence_and_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"queue.db"
            digest=hashlib.sha256(b"synthetic brief").hexdigest()
            first=submit(db,owner="alice",kind="video",request_sha256=digest)
            self.assertEqual(first,submit(db,owner="alice",kind="video",request_sha256=digest))
            self.assertIsNone(status(db,owner="bob",job_id=first["id"]))
            task=claim(db,worker="test-worker",kind="video")
            self.assertEqual(task["id"],first["id"])
            self.assertIsNone(claim(db,worker="test-worker-2",kind="video"))
            self.assertFalse(heartbeat(db,owner="bob",job_id=task["id"],worker="test-worker"))
            self.assertTrue(heartbeat(db,owner="alice",job_id=task["id"],worker="test-worker"))
            self.assertFalse(finish(db,owner="bob",job_id=task["id"],worker="test-worker",success=True,artifact_sha256=digest))
            self.assertTrue(finish(db,owner="alice",job_id=task["id"],worker="test-worker",success=True,artifact_sha256=digest))
            self.assertEqual(status(db,owner="alice",job_id=task["id"])["state"],"awaiting_review")
            self.assertIsNone(claim(db,worker="test-worker",kind="video"))
    def test_explicit_owner_scoped_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"queue.db"
            digest=hashlib.sha256(b"retry synthetic").hexdigest()
            task=submit(db,owner="alice",kind="ingest",request_sha256=digest)
            claim(db,worker="runner",kind="ingest")
            self.assertTrue(finish(db,owner="alice",job_id=task["id"],worker="runner",success=False,error="synthetic error"))
            self.assertIsNone(claim(db,worker="runner",kind="ingest"))
            self.assertFalse(retry_failed(db,owner="bob",job_id=task["id"]))
            self.assertTrue(retry_failed(db,owner="alice",job_id=task["id"]))
            self.assertEqual(claim(db,worker="runner",kind="ingest")["attempt"],2)
            self.assertTrue(finish(db,owner="alice",job_id=task["id"],worker="runner",success=False,error="synthetic error"))
            self.assertTrue(retry_failed(db,owner="alice",job_id=task["id"]))
            self.assertEqual(claim(db,worker="runner",kind="ingest")["attempt"],3)
            self.assertTrue(finish(db,owner="alice",job_id=task["id"],worker="runner",success=False,error="synthetic error"))
            self.assertFalse(retry_failed(db,owner="alice",job_id=task["id"]))
    def test_reject_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                submit(Path(tmp)/"db",owner="alice",kind="video",request_sha256="bad")

if __name__=="__main__":
    unittest.main()
