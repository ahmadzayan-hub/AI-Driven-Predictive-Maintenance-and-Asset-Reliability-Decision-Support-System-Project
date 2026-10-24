"""Hosted startup must validate, never silently migrate application data."""
import copy
import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from server.schema_contract import expected_contract, validate_postgres_schema, SchemaNotReady
from server.storage import PostgresStore, SCHEMA_VERSION, open_store
from server.rmd_schema import ensure_schema


class Catalog:
    def __init__(self):
        self.shape = copy.deepcopy(expected_contract())
        self.tables = [{'relname':t,'relrowsecurity':True} for t in self.shape]
        self.columns = [{'table_name':t,'column_name':n,'data_type':k,'is_nullable':'NO' if required else 'YES'}
                        for t,s in self.shape.items() for n,(k,required) in s['columns'].items()]
        self.keys = []
        self.indexes = []
        for t,s in self.shape.items():
            self.keys.append(dict(table_name=t,contype='p',condeferrable=False,columns=list(s['primary'])))
            for local,remote,columns in s['foreign']:
                self.keys.append(dict(table_name=t,contype='f',columns=list(local),referenced_table=remote,
                                      referenced_schema='public',referenced_columns=list(columns),confdeltype='a',confupdtype='a',condeferrable=False))
            self.indexes.extend(dict(table_name=t,columns=list(cols)) for cols in s['unique'])
        self.grants = []
        self.inherited = []
        self.column_grants = []
        self.effective_column_grants = []
        self.version = SCHEMA_VERSION
        self.statements = []

    def _exec(self, sql):
        self.statements.append(sql)
        assert sql.startswith('SELECT '), sql
        if sql == 'SELECT current_schema() AS name': return [{'name':'public'}]
        if 'information_schema.columns' in sql: return self.columns
        if 'pg_catalog.pg_constraint' in sql: return self.keys
        if 'pg_catalog.pg_index' in sql: return self.indexes
        if 'has_column_privilege' in sql: return self.effective_column_grants
        if 'aclexplode(a.attacl)' in sql: return self.column_grants
        if 'pg_has_role' in sql: return self.inherited
        if 'aclexplode' in sql: return self.grants
        return self.tables

    def _schema_version(self):
        self.statements.append('SELECT MAX(version) AS version FROM schema_migrations')
        return self.version


class HostedSchemaTest(unittest.TestCase):
    def test_matching_schema_is_read_only(self):
        store=Catalog(); validate_postgres_schema(store)
        self.assertTrue(all(sql.startswith('SELECT ') for sql in store.statements))

    def test_missing_table_and_column_fail_without_writes(self):
        store=Catalog(); store.tables=store.tables[:9]; store.columns=[]
        with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)
        self.assertTrue(all(sql.startswith('SELECT ') for sql in store.statements))

    def test_drift_and_security_each_fail_closed(self):
        cases=[lambda s:s.columns[0].update(data_type='uuid'),
               lambda s:s.columns[0].update(is_nullable='YES'),
               lambda s:s.tables[0].update(relrowsecurity=False),
               lambda s:s.keys.clear(),lambda s:s.indexes.clear(),
               lambda s:s.grants.append({'table_name':'runs'}),
               lambda s:s.inherited.append({'table_name':'runs'}),
               lambda s:setattr(s,'version',0),lambda s:setattr(s,'version',99)]
        for change in cases:
            with self.subTest(change=change):
                store=Catalog(); change(store)
                with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)

    def test_cross_schema_foreign_key_not_accepted(self):
        store=Catalog()
        for row in store.keys:
            if row['contype']=='f': row['referenced_schema']='untrusted'
        with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)

    def test_column_access_fails_closed_without_table_grants_or_writes(self):
        for attribute in ('column_grants', 'effective_column_grants'):
            with self.subTest(attribute=attribute):
                store = Catalog()
                getattr(store, attribute).append({'table_name': 'runs', 'column_name': 'goal'})
                with self.assertRaisesRegex(SchemaNotReady, 'runs.goal:public_api_column_grant'):
                    validate_postgres_schema(store)
                self.assertEqual(store.grants, [])
                self.assertEqual(store.inherited, [])
                self.assertTrue(all(sql.startswith('SELECT ') for sql in store.statements))

    def test_column_access_on_unrelated_tables_is_not_rejected(self):
        store = Catalog()
        for rows in (store.column_grants, store.effective_column_grants):
            rows.append({'table_name': 'unrelated_system', 'column_name': 'body'})
        validate_postgres_schema(store)

    def test_cascading_foreign_key_not_accepted(self):
        store=Catalog()
        for row in store.keys:
            if row['contype']=='f': row['confdeltype']='c'
        with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)

    def test_deferred_primary_key_not_accepted(self):
        store=Catalog()
        for row in store.keys:
            if row['contype']=='p': row['condeferrable']=True
        with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)

    def test_partial_index_does_not_meet_contract(self):
        store=Catalog(); store.indexes=[r for r in store.indexes if tuple(r['columns'])!=('owner','idempotency_key')]
        with self.assertRaises(SchemaNotReady): validate_postgres_schema(store)

    def test_verify_constructor_never_calls_schema_writer(self):
        with patch.object(PostgresStore,'_connect',return_value=Mock()), \
             patch.object(PostgresStore,'validate_schema') as check, \
             patch.object(PostgresStore,'_create_schema',side_effect=AssertionError('DDL')), \
             patch.object(PostgresStore,'_secure_backend_tables',side_effect=AssertionError('ACL')):
            store=PostgresStore('postgresql://synthetic.invalid/test',schema_mode='verify')
            check.assert_called_once(); store.close()

    def test_failed_preflight_closes_connection_pool(self):
        with patch.object(PostgresStore,'_connect',return_value=Mock()), \
             patch.object(PostgresStore,'validate_schema',side_effect=SchemaNotReady('required')), \
             patch.object(PostgresStore,'close') as close:
            with self.assertRaises(SchemaNotReady):
                PostgresStore('postgresql://synthetic.invalid/test',schema_mode='verify')
            close.assert_called_once()

    def test_rmd_consumer_never_reintroduces_ddl(self):
        store=Mock(schema_mode='verify'); ensure_schema(store)
        store.validate_schema.assert_called_once(); store.atomic.assert_not_called(); store._exec.assert_not_called()

    def test_local_sqlite_keeps_zero_setup(self):
        with tempfile.TemporaryDirectory() as root:
            store=open_store(sqlite_path=Path(root)/'data.db',schema_mode='verify')
            self.assertEqual(store._schema_version(),SCHEMA_VERSION); store.close()

    def test_runtime_entry_points_require_verify_mode(self):
        from server.app import create_app
        from server.worker import build_worker
        for fn in (create_app,build_worker):
            self.assertIn('schema_mode="verify"',inspect.getsource(fn))


from tests.test_runs import PG_TEST_URL, _postgres_available


@unittest.skipUnless(_postgres_available(), "test PostgreSQL is not reachable")
class HostedSchemaPostgresTest(unittest.TestCase):
    def test_column_grants_fail_closed_in_disposable_database(self):
        import psycopg2
        from psycopg2 import sql
        import uuid

        # Existing CI uses a disposable database. All grants, fixture roles and
        # extra tables below are rolled back; no hosted URL or commit is used.
        prepared = PostgresStore(PG_TEST_URL, schema_mode='migrate')
        prepared.close()
        connection = psycopg2.connect(PG_TEST_URL, connect_timeout=3)
        self.addCleanup(connection.close)
        self.addCleanup(connection.rollback)
        cursor = connection.cursor()
        self.addCleanup(cursor.close)

        class TransactionStore:
            def _exec(self, query):
                assert query.startswith('SELECT '), query
                cursor.execute(query)
                return [dict(zip([d[0] for d in cursor.description], row))
                        for row in cursor.fetchall()]

            def _schema_version(self):
                return self._exec('SELECT MAX(version) AS version FROM schema_migrations')[0]['version']

        store = TransactionStore()
        for role in ('anon', 'authenticated'):
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (role,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(role)))
        validate_postgres_schema(store)
        for role in ('PUBLIC', 'anon', 'authenticated'):
            for privilege in ('SELECT', 'INSERT', 'UPDATE', 'REFERENCES'):
                with self.subTest(role=role, privilege=privilege):
                    cursor.execute('SAVEPOINT column_grant')
                    target = sql.SQL('PUBLIC') if role == 'PUBLIC' else sql.Identifier(role)
                    cursor.execute(sql.SQL('GRANT {} (goal) ON public.runs TO {}').format(sql.SQL(privilege), target))
                    cursor.execute("SELECT has_table_privilege('authenticated','public.runs',%s)", (privilege,))
                    self.assertFalse(cursor.fetchone()[0])
                    with self.assertRaisesRegex(SchemaNotReady, 'runs.goal:public_api_column_grant'):
                        validate_postgres_schema(store)
                    cursor.execute('ROLLBACK TO SAVEPOINT column_grant')
                    validate_postgres_schema(store)

        backend = 'column_backend_' + uuid.uuid4().hex
        cursor.execute(sql.SQL('CREATE ROLE {} NOLOGIN NOSUPERUSER NOBYPASSRLS').format(sql.Identifier(backend)))
        cursor.execute(sql.SQL('GRANT SELECT(goal) ON public.runs TO {}').format(sql.Identifier(backend)))
        validate_postgres_schema(store)  # A standalone backend grant is not client access.
        cursor.execute(sql.SQL('GRANT {} TO authenticated').format(sql.Identifier(backend)))
        with self.assertRaisesRegex(SchemaNotReady, 'runs.goal:public_api_column_grant'):
            validate_postgres_schema(store)
        cursor.execute(sql.SQL('REVOKE {} FROM authenticated').format(sql.Identifier(backend)))
        unrelated = 'column_unrelated_' + uuid.uuid4().hex
        cursor.execute(sql.SQL('CREATE TABLE {} (body text)').format(sql.Identifier(unrelated)))
        cursor.execute(sql.SQL('GRANT SELECT(body) ON {} TO PUBLIC').format(sql.Identifier(unrelated)))
        validate_postgres_schema(store)

    def test_constructor_and_rmd_validate_in_read_only_session(self):
        # Disposable CI database only. Prepare through the explicit development
        # initializer, then enforce PostgreSQL read-only sessions on runtime.
        prepared = PostgresStore(PG_TEST_URL, schema_mode='migrate')
        prepared.close()

        class ReadOnlyStore(PostgresStore):
            def _connect(self):
                conn = super()._connect()
                conn.set_session(readonly=True, autocommit=True)
                return conn

        store = ReadOnlyStore(PG_TEST_URL, schema_mode='verify')
        self.addCleanup(store.close)
        self.assertEqual(store._exec('SHOW default_transaction_read_only')[0]['default_transaction_read_only'], 'on')
        ensure_schema(store)
        self.assertEqual(store._schema_version(), SCHEMA_VERSION)

