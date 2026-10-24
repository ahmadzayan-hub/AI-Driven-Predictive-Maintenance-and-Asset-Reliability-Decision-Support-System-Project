"""Read-only hosted schema preflight. No connection details enter diagnostics."""
from functools import lru_cache
import sqlite3


class SchemaNotReady(RuntimeError):
    """A reviewed database migration is required before hosted startup."""


@lru_cache(maxsize=1)
def expected_contract():
    # Derive the portable shape from storage, not a second manual list.
    from server.storage import SCHEMA_STATEMENTS, TABLES
    connection = sqlite3.connect(":memory:")
    try:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute("CREATE UNIQUE INDEX runs_idempotency ON runs(owner,idempotency_key)")
        contract = {}
        for table in TABLES:
            info = list(connection.execute(f'PRAGMA table_info({table})'))
            columns = {r[1]: (r[2].lower(), bool(r[3] or r[5])) for r in info}
            primary = tuple(r[1] for r in sorted(info, key=lambda r: r[5]) if r[5])
            unique = set()
            for index in connection.execute(f'PRAGMA index_list({table})'):
                if index[2]:
                    unique.add(tuple(r[2] for r in connection.execute(f'PRAGMA index_info({index[1]})')))
            foreign = {}
            for r in connection.execute(f'PRAGMA foreign_key_list({table})'):
                foreign.setdefault(r[0], []).append(r)
            keys = set()
            for rows in foreign.values():
                rows.sort(key=lambda r: r[1])
                keys.add((tuple(r[3] for r in rows), rows[0][2], tuple(r[4] for r in rows)))
            contract[table] = {'columns': columns, 'primary': primary,
                               'unique': unique, 'foreign': keys}
        return contract
    finally:
        connection.close()


def column_privilege_problems(store, expected):
    """Inspect column ACLs and effective client access without changing grants.

    Table REVOKE does not remove column grants. PUBLIC has no pg_roles row,
    so check its explicit ACL separately from named roles' effective access.
    Custom backend roles are allowed unless a client inherits their access.
    """
    public = store._exec("SELECT c.relname AS table_name, a.attname AS column_name "
        "FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "CROSS JOIN LATERAL aclexplode(a.attacl) acl "
        "WHERE n.nspname=current_schema() AND c.relkind='r' "
        "AND a.attnum>0 AND NOT a.attisdropped AND acl.grantee=0")
    effective = store._exec("SELECT c.relname AS table_name, a.attname AS column_name "
        "FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_class c ON c.oid=a.attrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "CROSS JOIN pg_catalog.pg_roles r "
        "WHERE n.nspname=current_schema() AND c.relkind='r' "
        "AND a.attnum>0 AND NOT a.attisdropped "
        "AND r.rolname IN ('anon','authenticated') "
        "AND has_column_privilege(r.oid,c.oid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES')")
    return [f"{row['table_name']}.{row['column_name']}:public_api_column_grant"
            for row in public + effective if row['table_name'] in expected]


def validate_postgres_schema(store):
    """SELECT-only validation; never repair, grant, or infer ownership."""
    from server.storage import SCHEMA_VERSION
    expected = expected_contract()
    schema_name = store._exec("SELECT current_schema() AS name")[0]["name"]
    tables = store._exec("SELECT c.relname, c.relrowsecurity FROM pg_catalog.pg_class c "
                         "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
                         "WHERE n.nspname=current_schema() AND c.relkind='r'")
    present = {r['relname']: r for r in tables}
    problems = []
    for name in expected:
        if name not in present:
            problems.append(f'{name}:missing_table')
        elif not present[name]['relrowsecurity']:
            problems.append(f'{name}:rls_disabled')
    rows = store._exec("SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns "
                       "WHERE table_schema=current_schema()")
    columns = {}
    for row in rows:
        columns.setdefault(row['table_name'], {})[row['column_name']] = row
    for table, spec in expected.items():
        for name, (kind, required) in spec['columns'].items():
            actual = columns.get(table, {}).get(name)
            if actual is None:
                problems.append(f'{table}.{name}:missing_column')
            elif actual['data_type'] != kind or (actual['is_nullable'] != ('NO' if required else 'YES')):
                problems.append(f'{table}.{name}:incompatible_column')
    constraints = store._exec("SELECT c.relname AS table_name,k.contype,k.confdeltype,k.confupdtype,k.condeferrable, "
        "ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY AS u(attnum,ord) "
        "JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum=u.attnum ORDER BY u.ord) AS columns, "
        "rc.relname AS referenced_table, rn.nspname AS referenced_schema, "
        "ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY AS u(attnum,ord) "
        "JOIN pg_catalog.pg_attribute a ON a.attrelid=rc.oid AND a.attnum=u.attnum ORDER BY u.ord) AS referenced_columns "
        "FROM pg_catalog.pg_constraint k JOIN pg_catalog.pg_class c ON c.oid=k.conrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "LEFT JOIN pg_catalog.pg_class rc ON rc.oid=k.confrelid "
        "LEFT JOIN pg_catalog.pg_namespace rn ON rn.oid=rc.relnamespace "
        "WHERE n.nspname=current_schema() AND k.contype IN ('p','f') AND k.convalidated")
    indexes = store._exec("SELECT c.relname AS table_name, "
        "ARRAY(SELECT a.attname FROM unnest(i.indkey) WITH ORDINALITY AS u(attnum,ord) "
        "JOIN pg_catalog.pg_attribute a ON a.attrelid=c.oid AND a.attnum=u.attnum "
        "WHERE u.ord<=i.indnkeyatts ORDER BY u.ord) AS columns "
        "FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class c ON c.oid=i.indrelid "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname=current_schema() AND i.indisunique AND i.indisvalid AND i.indisready AND i.indimmediate "
        "AND i.indpred IS NULL AND i.indexprs IS NULL")
    for table, spec in expected.items():
        actual = [r for r in constraints if r['table_name'] == table]
        if not any(r['contype']=='p' and not r['condeferrable'] and tuple(r['columns'])==spec['primary'] for r in actual):
            problems.append(f'{table}:primary_key')
        uniques = {tuple(r['columns']) for r in indexes if r['table_name']==table}
        if not spec['unique'].issubset(uniques):
            problems.append(f'{table}:unique_key')
        foreign = {(tuple(r['columns']),r['referenced_table'],tuple(r['referenced_columns']))
                   for r in actual if r['contype']=='f' and r['referenced_schema']==schema_name
                   and r['confdeltype']=='a' and r['confupdtype']=='a' and not r['condeferrable']}
        if not spec['foreign'].issubset(foreign):
            problems.append(f'{table}:foreign_key')
    # Backend-only architecture: RLS plus no grants to public API roles.
    grants = store._exec("SELECT c.relname AS table_name, a.grantee, r.rolname "
        "FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) a "
        "LEFT JOIN pg_catalog.pg_roles r ON r.oid=a.grantee "
        "WHERE n.nspname=current_schema() AND c.relkind='r' "
        "AND (a.grantee=0 OR r.rolname IN ('anon','authenticated'))")
    for row in grants:
        if row['table_name'] in expected:
            problems.append(f"{row['table_name']}:public_api_grant")
    inherited = store._exec("SELECT c.relname AS table_name FROM pg_catalog.pg_class c "
        "JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace "
        "CROSS JOIN LATERAL aclexplode(COALESCE(c.relacl,acldefault('r',c.relowner))) a "
        "CROSS JOIN pg_catalog.pg_roles r WHERE n.nspname=current_schema() AND c.relkind='r' "
        "AND r.rolname IN ('anon','authenticated') "
        "AND CASE WHEN a.grantee=0 THEN true ELSE pg_has_role(r.oid,a.grantee,'USAGE') END")
    for row in inherited:
        if row['table_name'] in expected:
            problems.append(f"{row['table_name']}:public_api_grant")
    problems.extend(column_privilege_problems(store, expected))
    if 'schema_migrations' in present and 'version' in columns.get('schema_migrations', {}):
        if store._schema_version() != SCHEMA_VERSION:
            problems.append('schema_migrations:version')
    if problems:
        raise SchemaNotReady('Hosted database schema is not ready; reviewed migration required. '
                             + ', '.join(sorted(set(problems))))

