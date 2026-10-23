"""Authenticated source credentials are scoped at each pinned HTTPS fetch."""

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from server import connectors as c
from server.model_gateway import ModelGateway
from server.runs import RunEngine
from server.storage import open_store
from tests.test_connectors import FakeResponse, resolver, source


URL = "https://data.example.com/sales.csv"
ALIAS = "maintenance-export"
TOKEN = "fixture-only-credential-never-real"


def environment(**changes):
    config = {"owner": "alice", "host": "data.example.com", "token_env": "TEST_SOURCE_TOKEN"}
    config.update(changes)
    return {"AGENTIC_OS_CONNECTOR_HOSTS": "data.example.com,other.example.com",
            "AGENTIC_OS_CONNECTOR_CREDENTIALS": json.dumps({ALIAS: config}),
            "TEST_SOURCE_TOKEN": TOKEN}


def transport(response, seen):
    class Connection:
        def __init__(self, host, address, port, timeout):
            seen.append({"host": host, "address": address, "port": port})

        def request(self, method, path, headers=None):
            seen.append({"method": method, "path": path, "headers": headers})

        def getresponse(self):
            return response

        def close(self):
            pass
    return Connection


class CredentialFenceTests(unittest.TestCase):
    def test_owner_origin_and_explicit_host_allowlist_are_all_required(self):
        cases = [(URL, "bob", environment()),
                 ("https://other.example.com/sales.csv", "alice", environment()),
                 ("https://data.example.com:8443/sales.csv", "alice", environment()),
                 (URL, "alice", {**environment(), "AGENTIC_OS_CONNECTOR_HOSTS": ""})]
        for url, owner, env in cases:
            with self.subTest(url=url, owner=owner):
                with self.assertRaises(c.ConnectorError):
                    c.credential_headers(url, ALIAS, owner, env)

    def test_valid_authentication_uses_pinned_transport_and_rotation_is_immediate(self):
        env, seen = environment(), []
        for token in (TOKEN, "rotated-fixture-value"):
            env["TEST_SOURCE_TOKEN"] = token
            c.fetch(URL, env, resolver("93.184.216.34"), credential_id=ALIAS,
                    owner="alice", connection_class=transport(FakeResponse(body=source()), seen))
            self.assertEqual(seen[-2], {"host": "data.example.com", "address": "93.184.216.34", "port": 443})
            self.assertEqual(seen[-1]["headers"]["Authorization"], "Bearer " + token)
        self.assertEqual(c.credential_headers(URL, ALIAS, "alice", environment(header="X-API-Key")),
                         {"X-API-Key": TOKEN})

    def test_authentication_does_not_weaken_private_address_refusal(self):
        seen = []
        with self.assertRaises(c.ConnectorError):
            c.fetch(URL, environment(), resolver("127.0.0.1"), credential_id=ALIAS,
                    owner="alice", connection_class=transport(FakeResponse(), seen))
        self.assertEqual(seen, [])

    def test_redirect_does_not_forward_or_echo_credentials(self):
        seen = []
        response = FakeResponse(302, headers={"Location": "https://other.example.com/?token=" + TOKEN})
        with self.assertRaises(c.ConnectorError) as caught:
            c.fetch(URL, environment(), resolver("93.184.216.34"), credential_id=ALIAS,
                    owner="alice", connection_class=transport(response, seen))
        self.assertEqual(len(seen), 2)
        self.assertNotIn(TOKEN, caught.exception.message())
        self.assertNotIn("other.example", caught.exception.message())
        self.assertTrue(caught.exception.message("ar"))

    def test_missing_revoked_or_malformed_configuration_is_generic(self):
        cases = [environment(header="Host"), environment(owner="*"), environment(port=True),
                 {**environment(), "TEST_SOURCE_TOKEN": ""},
                 {**environment(), "TEST_SOURCE_TOKEN": TOKEN + "\r\nX-Other: injected"},
                 {**environment(), "AGENTIC_OS_CONNECTOR_CREDENTIALS": "not-json"},
                 {**environment(), "AGENTIC_OS_CONNECTOR_CREDENTIALS": "{}"},
                 {**environment(), "AGENTIC_OS_CONNECTOR_CREDENTIALS": "[]"}]
        for env in cases:
            with self.subTest(config=cases.index(env)):
                with self.assertRaises(c.ConnectorError) as caught:
                    c.credential_headers(URL, ALIAS, "alice", env)
                self.assertNotIn(TOKEN, str(caught.exception))
                self.assertNotIn("TEST_SOURCE_TOKEN", str(caught.exception))
        with self.assertRaises(c.ConnectorError):
            c.credential_headers(URL, "alias\n", "alice", environment())

    def test_public_sources_need_no_registry_and_send_no_authentication(self):
        seen = []
        c.fetch(URL, {}, resolver("93.184.216.34"),
                connection_class=transport(FakeResponse(body=source()), seen))
        self.assertNotIn("Authorization", seen[-1]["headers"])
        self.assertNotIn("X-API-Key", seen[-1]["headers"])

    def test_authenticated_fixture_bypass_is_refused(self):
        env = environment(host="fixtures.invalid")
        env["AGENTIC_OS_CONNECTOR_HOSTS"] = "fixtures.invalid"
        with self.assertRaises(c.ConnectorError):
            c.credential_headers("https://fixtures.invalid/file.csv", ALIAS, "alice", env)


class CredentialPersistenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.root = root
        self.store = open_store(None, root / "runs.db")
        self.addCleanup(self.store.close)
        engine = RunEngine(self.store, root / "vault", ModelGateway({}))
        self.env = environment()
        self.connectors = c.Connectors(engine, env=self.env, cooldown=0)

    def test_only_alias_is_persisted_and_refresh_rechecks_revocation(self):
        connector = self.connectors.create("alice", "Maintenance export", URL,
                                           "Review maintenance", credential_id=ALIAS)
        row = self.store.get_connector(connector["id"])
        self.assertEqual(row["credential_id"], ALIAS)
        self.assertNotIn(TOKEN, json.dumps(row))
        self.assertNotIn("TEST_SOURCE_TOKEN", json.dumps(row))
        self.assertNotIn(TOKEN, json.dumps(connector))

        original_fetch = c.fetch
        seen = []

        def fetch_fixture(url, env, **kwargs):
            return original_fetch(url, env, resolver("93.184.216.34"),
                                  connection_class=transport(FakeResponse(body=source()), seen),
                                  **kwargs)

        with patch.object(c, "fetch", side_effect=fetch_fixture):
            result = self.connectors.refresh_now(connector["id"], "alice")
            self.assertEqual(result["status"], "updated")
            self.assertEqual(seen[-1]["headers"]["Authorization"], "Bearer " + TOKEN)
            self.env["AGENTIC_OS_CONNECTOR_CREDENTIALS"] = "{}"
            result = self.connectors.refresh_now(connector["id"], "alice")
        self.assertEqual(result["status"], "failed")
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertNotIn(TOKEN, json.dumps(self.store.get_connector(connector["id"])))

    def test_another_owner_cannot_save_or_refresh_the_alias(self):
        with self.assertRaises(c.ConnectorError):
            self.connectors.create("bob", "Export", URL, "Review", credential_id=ALIAS)
        connector = self.connectors.create("alice", "Export", URL, "Review", credential_id=ALIAS)
        with self.assertRaises(KeyError):
            self.connectors.refresh_now(connector["id"], "bob")

    def test_separate_api_connections_cannot_both_take_the_final_connector_slot(self):
        other_store = open_store(None, self.root / "runs.db")
        self.addCleanup(other_store.close)
        other_engine = RunEngine(other_store, self.root / "vault", ModelGateway({}))
        other = c.Connectors(other_engine, env=self.env, cooldown=0)
        start, both_counted = threading.Barrier(2), threading.Event()
        counts, results, errors = [], [], []
        counting = threading.Lock()

        def widen_race(store):
            original = store.count_connectors

            def count(owner):
                result = original(owner)
                with counting:
                    counts.append(result)
                    if len(counts) == 2:
                        both_counted.set()
                # Without admission atomicity both requests read the free
                # slot before either inserts. With it the second read waits.
                if result == 0:
                    both_counted.wait(.25)
                return result
            return count

        def create(service):
            try:
                start.wait(5)
                results.append(service.create("alice", "Export", URL, "Review", credential_id=ALIAS))
            except Exception as error:
                errors.append(error)

        with patch.object(c, "MAX_PER_OWNER", 1), \
                patch.object(self.store, "count_connectors", side_effect=widen_race(self.store)), \
                patch.object(other_store, "count_connectors", side_effect=widen_race(other_store)):
            threads = [threading.Thread(target=create, args=(service,)) for service in (self.connectors, other)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(10)
                self.assertFalse(thread.is_alive())
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], c.ConnectorError)
        self.assertEqual(errors[0].status, 429)
        self.assertEqual(self.store.count_connectors("alice"), 1)


if __name__ == "__main__":
    unittest.main()
