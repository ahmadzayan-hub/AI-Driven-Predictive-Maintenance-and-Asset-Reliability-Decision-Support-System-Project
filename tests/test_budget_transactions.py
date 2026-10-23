"""Synthetic admission scopes: rollback, concurrency, recovery and ownership."""
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from server import tenant
from server.model_gateway import ModelGateway
from server.orchestration import ModelRoles
from server.quota import ModelBudget
from server.runs import RunEngine
from server.storage import open_store
from tests.support import closing_store


class BudgetTransactionTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = closing_store(self, open_store(None, self.root / 'test.db'))
        self.owner = 'synthetic-tenant-a'
        self.day = datetime(2026, 10, 23, tzinfo=timezone.utc)
        token = tenant.current_owner.set(self.owner)
        self.addCleanup(tenant.current_owner.reset, token)
        self.budget = ModelBudget(self.store, {'model_calls_per_day': 10}, now=lambda: self.day)

    def used(self, owner=None, day='2026-10-23', store=None):
        return (store or self.store).model_calls_today(owner or self.owner, day)

    def test_rollback_cannot_erase_attempt_and_restart_keeps_it(self):
        with self.assertRaisesRegex(RuntimeError, 'stage failed'):
            with self.budget.reservation(4):
                with self.store.atomic('run:synthetic'):
                    self.assertTrue(self.budget.allow('synthetic'))
                    raise RuntimeError('stage failed')
        self.assertEqual(self.used(), 1)
        reopened = closing_store(self, open_store(None, self.root / 'test.db'))
        self.assertEqual(self.used(store=reopened), 1)

    def test_nested_scope_does_not_top_up_or_close_outer_token(self):
        with self.budget.reservation(2) as outer:
            with self.store.atomic('run:synthetic'):
                with self.budget.reservation(9) as inner:
                    self.assertIs(inner, outer)
                    self.assertTrue(self.budget.allow('synthetic'))
                self.assertTrue(self.budget.allow('synthetic'))
                self.assertFalse(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 2)
        self.assertFalse(outer.consume(self.owner, '2026-10-23'))

    def test_unsafe_nested_database_reservation_fails_closed(self):
        with self.store.atomic('run:synthetic'):
            with self.assertLogs('agentic.quota', level='WARNING'):
                self.assertFalse(self.budget.allow('synthetic'))
            with self.assertLogs('agentic.quota', level='WARNING'):
                with self.budget.reservation(3):
                    self.assertFalse(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 0)

    def test_parallel_contexts_share_credits_without_touching_database(self):
        with self.budget.reservation(3):
            with self.store.atomic('run:synthetic'):
                with patch.object(self.store, 'reserve_model_call', side_effect=AssertionError('nested DB call')):
                    with ThreadPoolExecutor(max_workers=8) as pool:
                        tasks = [pool.submit(copy_context().run, self.budget.allow, 'synthetic')
                                 for _ in range(20)]
                        self.assertEqual(sum(t.result() for t in tasks), 3)
        self.assertEqual(self.used(), 3)

    def test_other_scope_cannot_overspend_and_other_owner_is_independent(self):
        other_store = closing_store(self, open_store(None, self.root / 'test.db'))
        other_budget = ModelBudget(other_store, {'model_calls_per_day': 10}, now=lambda: self.day)
        with self.budget.reservation(10):
            self.assertFalse(other_budget.allow('synthetic'))
            token = tenant.current_owner.set('synthetic-tenant-b')
            try:
                self.assertTrue(other_budget.allow('synthetic'))
                self.assertFalse(self.budget.allow('synthetic'))
            finally:
                tenant.current_owner.reset(token)
            self.assertTrue(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 1)
        self.assertEqual(self.used('synthetic-tenant-b'), 1)

    def test_midnight_expires_old_token_and_refunds_only_old_day(self):
        with self.budget.reservation(3):
            self.assertTrue(self.budget.allow('synthetic'))
            self.day = datetime(2026, 10, 24, tzinfo=timezone.utc)
            self.assertFalse(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 1)
        self.assertEqual(self.used(day='2026-10-24'), 0)
        self.assertTrue(self.budget.allow('synthetic'))
        self.assertEqual(self.used(day='2026-10-24'), 1)

    def test_failed_reservation_scope_never_falls_back_to_database(self):
        with patch.object(self.store, 'reserve_model_calls', side_effect=RuntimeError('private')):
            with self.assertLogs('agentic.quota', level='WARNING'):
                with self.budget.reservation(3):
                    with patch.object(self.store, 'reserve_model_call') as single:
                        self.assertFalse(self.budget.allow('synthetic'))
                        single.assert_not_called()
        self.assertEqual(self.used(), 0)

    def test_unknown_refund_commit_is_not_retried(self):
        real_release = self.store.release_model_credits
        def committed_but_ack_lost(*args):
            real_release(*args)
            raise RuntimeError('private connection details')
        with patch.object(self.store, 'release_model_credits', side_effect=committed_but_ack_lost) as release:
            with self.assertLogs('agentic.quota', level='WARNING') as logs:
                with self.budget.reservation(4):
                    self.assertTrue(self.budget.allow('synthetic'))
            self.assertEqual(release.call_count, 1)
        self.assertEqual(self.used(), 1)
        self.assertNotIn('private', '\n'.join(logs.output))

    def test_failed_refund_and_abandoned_reservation_remain_conservative(self):
        with patch.object(self.store, 'release_model_credits', side_effect=RuntimeError('down')):
            with self.assertLogs('agentic.quota', level='WARNING'):
                with self.budget.reservation(4):
                    self.assertTrue(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 4)
        self.assertEqual(self.store.reserve_model_calls(self.owner, '2026-10-23', 10, 4), 4)
        reopened = closing_store(self, open_store(None, self.root / 'test.db'))
        self.assertEqual(self.used(store=reopened), 8)

    def test_base_exception_settles_and_closes_scope(self):
        with self.assertRaises(KeyboardInterrupt):
            with self.budget.reservation(4) as credits:
                self.assertTrue(self.budget.allow('synthetic'))
                raise KeyboardInterrupt()
        self.assertEqual(self.used(), 1)
        self.assertTrue(credits.closed)

    def test_engine_failure_after_provider_keeps_credit_and_restores_context(self):
        gateway = ModelGateway(env={'OLLAMA_MODEL': 'synthetic'})
        gateway.budget = self.budget
        engine = RunEngine(self.store, self.root / 'vault', gateway)
        run = engine.create_run('Synthetic fixture', owner=self.owner)
        def failing_stage(*args):
            self.assertEqual(self.store._transaction_depth, 1)
            gateway.ask('verified synthetic fixture', 'synthetic')
            raise RuntimeError('late state failure')
        with patch.object(gateway, '_post', return_value={'message': {'content': 'synthetic'}}) as post:
            with patch.object(engine, '_advance_atomic', side_effect=failing_stage):
                with self.assertRaisesRegex(RuntimeError, 'late state failure'):
                    engine.advance(run['id'])
            self.assertEqual(post.call_count, 1)
        self.assertEqual(self.used(), 1)
        self.assertEqual(engine.get_run(run['id'])['state'], 'queued')
        self.assertEqual(tenant.owner_or_local(), self.owner)

    def test_parallel_consultants_keep_owner_budget_and_never_deadlock(self):
        env = {'OPENAI_API_KEY': 'synthetic', 'OPENAI_MODEL': 'synthetic',
               'GROQ_API_KEY': 'synthetic', 'AGENTIC_OS_CONSULTANTS': 'openai,groq',
               'AGENTIC_OS_HERMES_MODEL': 'openai', 'AGENTIC_OS_BUILT_IN_ROLES': '0'}
        gateway = ModelGateway(env=env)
        gateway.budget = self.budget
        roles = ModelRoles(gateway, env)
        seen = []
        def provider(*args, **kwargs):
            seen.append(tenant.owner_or_local())
            return None
        with patch.object(gateway, '_post', side_effect=provider):
            with self.budget.reservation(3):
                with self.store.atomic('run:synthetic'):
                    roles.consult('Synthetic audit', ['Verified availability is 80 percent.'])
        self.assertEqual(len(seen), 3)
        self.assertEqual(set(seen), {self.owner})
        self.assertEqual(self.used(), 3)

    def test_uncertain_reservation_commit_denies_provider_but_retains_credits(self):
        real_finish = self.store._finish_transaction
        def uncertain(statement):
            real_finish(statement)
            if statement == 'COMMIT':
                raise RuntimeError('lost acknowledgement')
        with patch.object(self.store, '_finish_transaction', side_effect=uncertain):
            with self.assertLogs('agentic.quota', level='WARNING'):
                with self.budget.reservation(4):
                    self.assertFalse(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 4)

    def test_paused_advance_returns_all_unused_credits(self):
        gateway = ModelGateway(env={'OLLAMA_MODEL': 'synthetic'})
        gateway.budget = self.budget
        engine = RunEngine(self.store, self.root / 'vault', gateway)
        run = engine.create_run('Synthetic fixture', owner=self.owner)
        self.store.update('runs', run['id'], {'paused': 1})
        with patch.object(gateway, '_post') as post:
            with self.assertRaisesRegex(ValueError, 'paused'):
                engine.advance(run['id'])
            post.assert_not_called()
        self.assertEqual(self.used(), 0)

    def test_bounded_reservation_does_not_block_all_other_owner_calls(self):
        with self.budget.reservation(2):
            independent = ModelBudget(self.store, {'model_calls_per_day': 10}, now=lambda: self.day)
            self.assertTrue(independent.allow('synthetic'))
            self.assertEqual(self.used(), 3)
            self.assertTrue(self.budget.allow('synthetic'))
        self.assertEqual(self.used(), 2)

    def test_legacy_counter_handles_a_fully_refunded_zero_row(self):
        with self.budget.reservation(3):
            pass
        self.assertEqual(self.used(), 0)
        self.assertEqual(self.store.count_model_call(self.owner, '2026-10-23'), 1)
        self.assertEqual(self.used(), 1)

    def test_two_store_scopes_share_limit_and_settle_without_lost_updates(self):
        from threading import Barrier
        stores = [closing_store(self, open_store(None, self.root / 'test.db')) for _ in range(2)]
        ready = Barrier(2)
        def run(store):
            token = tenant.current_owner.set(self.owner)
            try:
                budget = ModelBudget(store, {'model_calls_per_day': 5}, now=lambda: self.day)
                with budget.reservation(3) as credits:
                    ready.wait()
                    self.assertTrue(budget.allow('synthetic'))
                    return credits.reserved
            finally:
                tenant.current_owner.reset(token)
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(run, stores)), 5)
        self.assertEqual(self.used(), 2)

    def test_sufficient_budget_preserves_full_multirole_graph_and_model_variants(self):
        import json
        from collections import Counter
        env = {'OLLAMA_MODEL': 'synthetic-narrator',
               'AGENTIC_OS_HERMES_MODEL': 'ollama:synthetic-hermes',
               'AGENTIC_OS_AGENT_MODEL': 'ollama:synthetic-agent',
               'AGENTIC_OS_CONSULTANTS': 'ollama:consult-one,ollama:consult-two,ollama:consult-three',
               'AGENTIC_OS_BUILT_IN_ROLES': '0'}
        observations = []
        for enabled in (False, True):
            store = closing_store(self, open_store(None, self.root / f'roles-{enabled}.db'))
            gateway = ModelGateway(env=env)
            if enabled:
                gateway.budget = ModelBudget(store, {'model_calls_per_day': 500}, now=lambda: self.day)
            engine = RunEngine(store, self.root / f'vault-{enabled}', gateway,
                               roles=ModelRoles(gateway, env))
            self.assertEqual(engine._model_attempt_bound(), 24)
            run = engine.create_run('Review the fictional sample', owner=self.owner)
            models = []
            def answer(instance, url, headers, payload):
                models.append(payload['model'])
                self.assertEqual(tenant.owner_or_local(), self.owner)
                # Invalid structured response deliberately exercises text fallback.
                return {'message': {'content': 'Check data coverage before approval.'}}
            with patch.object(ModelGateway, '_post', autospec=True, side_effect=answer):
                for _ in range(100):
                    if run['state'] not in ('queued', 'running'):
                        break
                    run = engine.advance(run['id'])
            self.assertEqual(run['state'], 'awaiting_approval')
            self.assertEqual(run['approvals'][0]['state'], 'pending')
            results = {t['role']: json.loads(t['result_json'] or '{}') for t in store.get_tasks(run['id'])}
            self.assertEqual(len(results['reporter']['orchestration']['consultants']), 3)
            self.assertTrue(any(x.get('agent_note') for x in results.values()))
            self.assertIn('hermes_plan', results['planner'])
            self.assertTrue(all(models.count(name) >= 2 for name in ('consult-one', 'consult-two', 'consult-three')))
            if enabled:
                self.assertEqual(store.model_calls_today(self.owner, '2026-10-23'), len(models))
            observations.append(Counter(models))
        self.assertEqual(observations[0], observations[1])
