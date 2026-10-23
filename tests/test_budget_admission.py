"""Provider-free regressions for durable admission and shared-write outages."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from fastapi.testclient import TestClient
from server import tenant
from server.app import create_app
from server.model_gateway import ModelGateway
from server.quota import ModelBudget
from server.storage import open_store
from server.worker import build_worker
from tests.support import closing, closing_store


class BudgetAdmissionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.db = self.root / 'test.db'
        self.store = closing_store(self, open_store(None, self.db))
        self.config = self.root / 'config.json'
        self.config.write_text(json.dumps({'database_file': str(self.db),
                                          'vault_dir': str(self.root / 'vault')}))

    def budget(self, store=None, limit=1, day=23):
        return ModelBudget(store or self.store, {'model_calls_per_day': limit},
                           now=lambda: datetime(2026, 10, day, tzinfo=timezone.utc))

    def test_concurrent_instances_admit_only_the_remaining_budget(self):
        stores = [closing_store(self, open_store(None, self.db)) for _ in range(8)]
        ready = Barrier(len(stores))
        def attempt(store):
            token = tenant.current_owner.set('synthetic-owner')
            try:
                ready.wait()
                return self.budget(store).allow('ollama')
            finally:
                tenant.current_owner.reset(token)
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(attempt, stores)), 1)
        self.assertEqual(self.store.model_calls_today('synthetic-owner', '2026-10-23'), 1)

    def test_reservation_survives_restart_and_resets_by_owner_and_day(self):
        token = tenant.current_owner.set('synthetic-owner')
        self.addCleanup(tenant.current_owner.reset, token)
        self.assertTrue(self.budget().allow('ollama'))
        reopened = closing_store(self, open_store(None, self.db))
        self.assertFalse(self.budget(reopened).allow('ollama'))
        self.assertTrue(self.budget(reopened, day=24).allow('ollama'))
        other = tenant.current_owner.set('other-owner')
        try:
            self.assertTrue(self.budget(reopened).allow('ollama'))
        finally:
            tenant.current_owner.reset(other)

    def test_failed_provider_counts_once_and_blocks_failover(self):
        gateway = ModelGateway(env={'OPENAI_API_KEY': 'synthetic-test', 'OPENAI_MODEL': 'synthetic-model', 'GROQ_API_KEY': 'synthetic-test'})
        gateway.budget = self.budget()
        token = tenant.current_owner.set('synthetic-owner')
        self.addCleanup(tenant.current_owner.reset, token)
        with patch.object(gateway, '_post', return_value=None) as post:
            self.assertIsNone(gateway.ask('verified fixture', 'synthetic', provider='openai'))
            self.assertEqual(post.call_count, 1)
        self.assertEqual(self.store.model_calls_today('synthetic-owner', '2026-10-23'), 1)

    def test_storage_failure_never_contacts_a_provider(self):
        gateway = ModelGateway(env={'OLLAMA_MODEL': 'synthetic-model'})
        gateway.budget = self.budget()
        with self.assertLogs('agentic.quota', level='WARNING') as logs, patch.object(
                self.store, 'reserve_model_call', side_effect=RuntimeError('private detail')):
            with patch.object(gateway, '_post') as post:
                self.assertIsNone(gateway.ask('fixture', 'fixture'))
                self.assertIsNone(gateway.ask_json('fixture', 'fixture'))
                self.assertEqual(gateway.narrate('fixture', ['verified fact'])['source'], 'deterministic')
                post.assert_not_called()
        self.assertNotIn('private detail', '\n'.join(logs.output))
        self.assertTrue(all('unavailable' in line for line in logs.output))

    def test_worker_budget_is_shared_by_model_variants(self):
        worker = build_worker(env={'OLLAMA_MODEL': 'synthetic-model',
                                   'AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY': '0'},
                              config_path=self.config)
        self.addCleanup(worker.store.close)
        gateway = worker.engine.gateway
        self.assertIsInstance(gateway.budget, ModelBudget)
        self.assertIs(gateway.budget.store, worker.store)
        variant = gateway.with_model('ollama', 'other-synthetic-model')
        self.assertIs(variant.budget, gateway.budget)
        with patch.object(ModelGateway, '_post') as post:
            self.assertIsNone(variant.ask('fixture', 'fixture'))
            post.assert_not_called()

    def test_shared_limiter_outage_returns_bilingual_503_without_mutation(self):
        app = closing(self, create_app(self.config, env={'AGENTIC_OS_RATE_LIMIT_STORE': '1'}))
        client = TestClient(app, raise_server_exceptions=False)
        with patch.object(app.state.store, 'rate_hit', side_effect=RuntimeError('private detail')):
            for language in ('en', 'ar'):
                response = client.post('/api/runs', json={'goal': 'Synthetic audit'},
                                       headers={'Accept-Language': language})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.headers['Retry-After'], '5')
                self.assertNotIn('private detail', response.text)
            self.assertEqual(client.get('/api/runs').status_code, 200)
        self.assertEqual(app.state.store.list_runs(), [])


# The CI service is disposable PostgreSQL, never the production DATABASE_URL.
from tests.test_runs import PG_TEST_URL, _postgres_available


@unittest.skipUnless(_postgres_available(), 'isolated test PostgreSQL unavailable')
class PostgresBudgetAdmissionTest(unittest.TestCase):
    def test_parallel_connections_reserve_once_and_reconnect_preserves_count(self):
        import uuid
        owner = 'synthetic-budget-' + str(uuid.uuid4())
        day = '2026-10-23'
        stores = [closing_store(self, open_store(PG_TEST_URL)) for _ in range(8)]
        self.addCleanup(stores[0]._exec,
                        'DELETE FROM model_calls_daily WHERE owner = ?', (owner,))
        ready = Barrier(8)
        def reserve(store):
            ready.wait()
            return store.reserve_model_call(owner, day, 1)
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(reserve, stores)), 1)
        reopened = closing_store(self, open_store(PG_TEST_URL))
        self.assertEqual(reopened.model_calls_today(owner, day), 1)
        self.assertFalse(reopened.reserve_model_call(owner, day, 1))

    def test_postgres_run_rollback_cannot_erase_reserved_attempt(self):
        import uuid
        owner = 'synthetic-budget-' + str(uuid.uuid4())
        store = closing_store(self, open_store(PG_TEST_URL))
        self.addCleanup(store._exec, 'DELETE FROM model_calls_daily WHERE owner = ?', (owner,))
        context = tenant.current_owner.set(owner)
        self.addCleanup(tenant.current_owner.reset, context)
        budget = ModelBudget(store, {'model_calls_per_day': 5},
                             now=lambda: datetime(2026, 10, 23, tzinfo=timezone.utc))
        with self.assertRaisesRegex(RuntimeError, 'state rollback'):
            with budget.reservation(3):
                with store.atomic('run:' + owner):
                    self.assertTrue(budget.allow('synthetic'))
                    raise RuntimeError('state rollback')
        other = closing_store(self, open_store(PG_TEST_URL))
        self.assertEqual(other.model_calls_today(owner, '2026-10-23'), 1)

    def test_postgres_parallel_scopes_settle_without_lost_updates(self):
        import uuid
        owner = 'synthetic-budget-' + str(uuid.uuid4())
        stores = [closing_store(self, open_store(PG_TEST_URL)) for _ in range(2)]
        self.addCleanup(stores[0]._exec, 'DELETE FROM model_calls_daily WHERE owner = ?', (owner,))
        ready = Barrier(2)
        def run(store):
            token = tenant.current_owner.set(owner)
            try:
                budget = ModelBudget(store, {'model_calls_per_day': 5},
                                     now=lambda: datetime(2026, 10, 23, tzinfo=timezone.utc))
                with budget.reservation(3) as credits:
                    ready.wait()
                    self.assertTrue(budget.allow('synthetic'))
                    return credits.reserved
            finally:
                tenant.current_owner.reset(token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(run, stores)), 5)
        self.assertEqual(stores[0].model_calls_today(owner, '2026-10-23'), 2)
        # A fully-refunded row must remain compatible with legacy counter use.
        self.assertEqual(stores[0].reserve_model_calls(owner, '2026-10-24', 5, 3), 3)
        stores[0].release_model_credits(owner, '2026-10-24', 3)
        self.assertEqual(stores[0].count_model_call(owner, '2026-10-24'), 1)
