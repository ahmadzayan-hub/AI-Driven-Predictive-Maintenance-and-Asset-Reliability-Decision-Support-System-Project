"""Source-contract regressions; synthetic fixtures are not a live CMMS test."""
import copy
import json
import unittest
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

from server.maintainx import MaintainXError, asset_import, synchronize
from scripts.maintainx_sync import sync_file, write_json


class MaintainXTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 21, tzinfo=timezone.utc)
        self.calls = []
        self.asset = {"id": 1, "name": "Pump", "locationId": 7, "updatedAt": "2026-10-20T12:00:00Z"}

    def fetcher(self, *pages):
        pages = iter(pages)
        def fetch(url, **kwargs):
            self.calls.append((url, kwargs))
            page = next(pages)
            if isinstance(page, Exception):
                raise page
            return json.dumps(page).encode()
        return fetch

    def page(self, rows=None, cursor=None, **extra):
        return {"assets": rows if rows is not None else [self.asset], "nextCursor": cursor, "nextPageUrl": None} | extra

    def sync(self, fetcher, previous=None):
        return synchronize("assets", "operator", "maintainx-test", previous, fetcher=fetcher, now=self.now)

    def test_cursor_pages_deduplicate_and_only_follow_fixed_host(self):
        result = self.sync(self.fetcher(self.page(cursor="next", nextPageUrl="https://evil.invalid/leak"),
                                      self.page([self.asset, self.asset | {"id": 2}])))
        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["watermark"], "2026-10-20T12:00:00+00:00")
        self.assertTrue(all(urlsplit(c[0]).hostname == "api.getmaintainx.com" for c in self.calls))
        self.assertEqual(parse_qs(urlsplit(self.calls[1][0]).query)["cursor"], ["next"])
        self.assertEqual(self.calls[0][1]["credential_id"], "maintainx-test")
        self.assertEqual(self.calls[0][1]["owner"], "operator")

    def test_incremental_overlap_keeps_filter_and_newest_version(self):
        previous = self.sync(self.fetcher(self.page()))
        changed = self.asset | {"name": "Renamed pump", "updatedAt": "2026-10-20T13:00:00Z"}
        self.calls.clear()
        result = self.sync(self.fetcher(self.page([changed], cursor="next"), self.page([self.asset])), previous)
        self.assertEqual(result["records"][0]["name"], "Renamed pump")
        query = [parse_qs(urlsplit(c[0]).query) for c in self.calls]
        self.assertEqual(query[0]["updatedAt[gte]"], ["2026-10-20T11:55:00+00:00"])
        self.assertEqual(query[0]["updatedAt[gte]"], query[1]["updatedAt[gte]"])

    def test_page_failure_never_mutates_prior_snapshot_or_advances_watermark(self):
        previous = self.sync(self.fetcher(self.page()))
        before = copy.deepcopy(previous)
        with self.assertRaises(MaintainXError):
            self.sync(self.fetcher(self.page(cursor="next"), MaintainXError("failed")), previous)
        self.assertEqual(previous, before)

    def test_schema_change_repeating_cursor_and_incomplete_paging_fail_closed(self):
        cases = [(self.page() | {"assets": "changed"},),
                 ({"assets": [self.asset]},),
                 (self.page(cursor="same"), self.page(cursor="same")),
                 (self.page(nextPageUrl="https://api.getmaintainx.com/v1/assets?offset=200"),)]
        for pages in cases:
            with self.subTest(pages=pages), self.assertRaises(MaintainXError):
                self.sync(self.fetcher(*pages))

    def test_source_mismatch_future_records_and_bad_identifiers_refused(self):
        previous = self.sync(self.fetcher(self.page()))
        for corrupt in ([], "corrupt", previous | {"owner": "other"}, previous | {"credential_id": "other"}):
            with self.assertRaises(MaintainXError):
                self.sync(self.fetcher(self.page()), corrupt)
        for row in (self.asset | {"id": True}, self.asset | {"updatedAt": "2027-01-01T00:00:00Z"}):
            with self.assertRaises(MaintainXError):
                self.sync(self.fetcher(self.page([row])))

    def test_import_requires_explicit_location_asset_selection_and_criticality(self):
        snapshot = self.sync(self.fetcher(self.page([self.asset, self.asset | {"id": 2, "locationId": 8}])))
        payload = asset_import(snapshot, "local-site", "initial", 7, ["1"], "high")
        self.assertEqual(payload["assets"][0]["external_id"], "1")
        self.assertEqual(payload["assets"][0]["criticality"], "high")
        with self.assertRaises(MaintainXError):
            asset_import(snapshot, "local-site", "initial", 7, ["1", "2"], "high")
        with self.assertRaises(MaintainXError):
            asset_import(snapshot, "local-site", "initial", 7, ["1"], None)

    def test_deleted_asset_not_imported_and_unmapped_work_order_remains_unmapped(self):
        snap = self.sync(self.fetcher(self.page([self.asset | {"deletedAt": "2026-10-20T14:00:00Z"}])))
        with self.assertRaises(MaintainXError):
            asset_import(snap, "local-site", "initial", 7, ["1"], "high")
        work = {"id": 10, "title": "Inspect pump", "status": "DONE", "updatedAt": "2026-10-20T14:00:00Z", "asset": None}
        snap = synchronize("workorders", "operator", "maintainx-test", now=self.now,
                           fetcher=self.fetcher({"workOrders": [work], "nextCursor": None}))
        self.assertIsNone(snap["records"][0]["asset_id"])
        self.assertIsNone(snap["records"][0]["completed_at"])

    def test_work_orders_request_and_preserve_expanded_asset_link(self):
        work = {"id": 10, "title": "Inspect pump", "status": "OPEN", "updatedAt": "2026-10-20T14:00:00Z", "asset": {"id": 42}}
        def sync(row):
            return synchronize("workorders", "operator", "maintainx-test", now=self.now,
                               fetcher=self.fetcher({"workOrders": [row], "nextCursor": None}))
        self.assertEqual(sync(work)["records"][0]["asset_id"], "42")
        self.assertEqual(parse_qs(urlsplit(self.calls[-1][0]).query)["expand"], ["asset"])
        for malformed in ({}, "42", {"id": True}):
            with self.assertRaises(MaintainXError):
                sync(work | {"asset": malformed})
        del work["asset"]
        with self.assertRaises(MaintainXError):
            sync(work | {"assetId": 42})

    def test_overlapping_file_sync_is_rejected_before_fetch_then_reads_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            args = SimpleNamespace(output=path, import_output=None, site_id=None,
                                   kind="assets", owner="operator", credential="alias")
            original = {"watermark": "original"}
            newest = {"watermark": "newest"}
            write_json(path, original)
            started, finish = threading.Event(), threading.Event()
            failures = []
            def fetch(*values, **kwargs):
                self.assertEqual(values[3], original)
                started.set()
                self.assertTrue(finish.wait(5))
                return newest
            def first():
                try:
                    sync_file(args, fetch)
                except BaseException as error:
                    failures.append(error)
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(started.wait(5))
                with self.assertRaises(MaintainXError):
                    sync_file(args, lambda *a, **kw: self.fail("Concurrent sync fetched source"))
                self.assertEqual(json.loads(path.read_text()), original)
            finally:
                finish.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(failures)
            seen = []
            sync_file(args, lambda *a, **kw: seen.append(a[3]) or newest)
            self.assertEqual(seen, [newest])
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_failed_atomic_replace_preserves_snapshot_and_cleans_unique_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            write_json(path, {"watermark": "old"})
            with patch.object(Path, "replace", side_effect=OSError("unavailable")), self.assertRaises(OSError):
                write_json(path, {"watermark": "new"})
            self.assertEqual(json.loads(path.read_text()), {"watermark": "old"})
            self.assertEqual(list(Path(directory).iterdir()), [path])
