import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from server.experimental_stream import accept,health,EventRejected

def event(eid,sec,payload=None):
    return {"id":eid,"event_time":datetime.fromtimestamp(sec,timezone.utc).isoformat(),
            "payload":payload if payload is not None else {"temperature_c":42.5}}

class SyntheticStreamingTests(unittest.TestCase):
    def test_dedupe_late_stale_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"stream.db"
            self.assertEqual(accept(p,owner="A",source="S",event=event("1",900),received_at=1000)["status"],"accepted")
            self.assertEqual(accept(p,owner="A",source="S",event=event("1",900),received_at=1001)["status"],"duplicate")
            self.assertTrue(accept(p,owner="A",source="S",event=event("2",600),received_at=1002)["late"])
            h=health(p,owner="A",source="S",now=1003)
            self.assertEqual((h["accepted"],h["late"],h["duplicates"]),(2,1,1))
            self.assertEqual(health(p,owner="A",source="S",now=1500)["state"],"stale")
            self.assertEqual(health(p,owner="B",source="S")["state"],"no_data")
    def test_future_and_naive_timestamp_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"s.db"
            with self.assertRaises(EventRejected):
                accept(p,owner="A",source="S",event=event("future",2000),received_at=1000)
            with self.assertRaises(EventRejected):
                accept(p,owner="A",source="S",event={"id":"bad","event_time":"2026-01-01T00:00:00","payload":{}},received_at=1000)
    def test_bad_payload_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(EventRejected):
                accept(Path(d)/"s.db",owner="A",source="S",event=event("x",900,{"bad":float("nan")}),received_at=1000)

if __name__=="__main__":
    unittest.main()
