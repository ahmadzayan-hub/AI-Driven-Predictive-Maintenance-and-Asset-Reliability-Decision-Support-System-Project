"""Generate the reviewed catch-up from the pinned application DDL; never connects."""
import json, re, sqlite3, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parents[1]
sys.path.insert(0,str(REPO))
from server.storage import SCHEMA_STATEMENTS,TABLES,SCHEMA_VERSION
conn=sqlite3.connect(':memory:')
for s in SCHEMA_STATEMENTS: conn.execute(s)
optional={'runs':['assumptions_json','idempotency_key','request_hash'],'approvals':['decided_by'],'connectors':['credential_id']}
manifest={}
for t in TABLES:
 rows=conn.execute(f'PRAGMA table_info({t})').fetchall()
 unique=[]
 for idx in conn.execute(f'PRAGMA index_list({t})').fetchall():
  if idx[2] and idx[3]!='pk': unique.append([r[2] for r in conn.execute(f'PRAGMA index_info({idx[1]})')])
 fks=[]
 for r in conn.execute(f'PRAGMA foreign_key_list({t})'): fks.append({'columns':[r[3]],'target':r[2],'target_columns':[r[4]]})
 manifest[t]={'columns':{r[1]:{'type':r[2].lower(),'not_null':bool(r[3] or r[5]),'optional':r[1] in optional.get(t,[])} for r in rows},'pk':[r[1] for r in sorted(rows,key=lambda r:r[5]) if r[5]],'unique':unique,'foreign':fks}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
manifest_sql=json.dumps(manifest).replace("'","''")
preflight=f"""-- No schema/data rewrite precedes this drift check. Unexpected legacy ownership
-- or shapes need an explicit migration review, never automatic attribution.
DO $preflight$
DECLARE expected jsonb := '{manifest_sql}'::jsonb;
  tab text; spec jsonb; col text; c jsonb; rel oid; actual record;
  keys text[]; wanted text[]; fk jsonb; target_cols text[];
BEGIN
  FOR tab,spec IN SELECT * FROM jsonb_each(expected) LOOP
    SELECT pc.oid, pc.relkind INTO actual FROM pg_catalog.pg_class pc
      JOIN pg_catalog.pg_namespace ns ON ns.oid=pc.relnamespace
      WHERE ns.nspname='public' AND pc.relname=tab;
    IF NOT FOUND THEN CONTINUE; END IF;
    rel := actual.oid;
    IF EXISTS (SELECT 1 FROM pg_catalog.aclexplode(COALESCE((SELECT pc.relacl FROM pg_catalog.pg_class pc WHERE pc.oid=rel),pg_catalog.acldefault('r',(SELECT pc.relowner FROM pg_catalog.pg_class pc WHERE pc.oid=rel)))) acl WHERE acl.grantee=0 OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles role WHERE role.rolname IN ('anon','authenticated') AND CASE WHEN acl.grantee<>0 THEN pg_catalog.pg_has_role(role.oid,acl.grantee,'USAGE') ELSE false END))
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles role WHERE role.rolname IN ('anon','authenticated') AND pg_catalog.has_table_privilege(role.oid,rel,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')) THEN
      RAISE EXCEPTION 'Existing client access requires review: %',tab;
    END IF;
    IF actual.relkind <> 'r' THEN RAISE EXCEPTION 'Unexpected relation kind for %',tab; END IF;
    FOR col,c IN SELECT * FROM jsonb_each(spec->'columns') LOOP
      SELECT at.attname, pg_catalog.format_type(at.atttypid,at.atttypmod) AS kind, at.attnotnull
      INTO actual FROM pg_catalog.pg_attribute at WHERE at.attrelid=rel
        AND at.attname=col AND at.attnum>0 AND NOT at.attisdropped;
      IF NOT FOUND THEN
        IF NOT (c->>'optional')::boolean THEN RAISE EXCEPTION 'Required legacy column absent: %.%',tab,col; END IF;
      ELSIF actual.kind <> c->>'type' OR actual.attnotnull <> (c->>'not_null')::boolean THEN
        RAISE EXCEPTION 'Unexpected column type/nullability: %.%',tab,col;
      END IF;
    END LOOP;
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_attribute at WHERE at.attrelid=rel AND at.attnum>0 AND NOT at.attisdropped AND NOT (spec->'columns' ? at.attname)) THEN
      RAISE EXCEPTION 'Unreviewed additional column in %',tab;
    END IF;
    SELECT array_agg(at.attname::text ORDER BY k.ord) INTO keys
      FROM pg_catalog.pg_constraint co CROSS JOIN LATERAL unnest(co.conkey) WITH ORDINALITY k(attnum,ord)
      JOIN pg_catalog.pg_attribute at ON at.attrelid=co.conrelid AND at.attnum=k.attnum
      WHERE co.conrelid=rel AND co.contype='p' AND NOT co.condeferrable;
    SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(spec->'pk');
    IF keys IS DISTINCT FROM wanted THEN RAISE EXCEPTION 'Unexpected primary key: %',tab; END IF;
    FOR c IN SELECT * FROM jsonb_array_elements(spec->'unique') LOOP
      SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(c);
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint co WHERE co.conrelid=rel AND co.contype='u' AND NOT co.condeferrable
        AND ARRAY(SELECT at.attname::text FROM unnest(co.conkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=rel AND at.attnum=k.attnum ORDER BY k.ord)=wanted) THEN
        RAISE EXCEPTION 'Missing unique key: %',tab;
      END IF;
    END LOOP;
    FOR fk IN SELECT * FROM jsonb_array_elements(spec->'foreign') LOOP
      SELECT array_agg(value) INTO wanted FROM jsonb_array_elements_text(fk->'columns');
      SELECT array_agg(value) INTO target_cols FROM jsonb_array_elements_text(fk->'target_columns');
      IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_constraint co JOIN pg_catalog.pg_class rt ON rt.oid=co.confrelid JOIN pg_catalog.pg_namespace rn ON rn.oid=rt.relnamespace
        WHERE co.conrelid=rel AND co.contype='f' AND co.convalidated AND NOT co.condeferrable AND co.confdeltype='a' AND co.confupdtype='a'
        AND rn.nspname='public' AND rt.relname=fk->>'target'
        AND ARRAY(SELECT at.attname::text FROM unnest(co.conkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=rel AND at.attnum=k.attnum ORDER BY k.ord)=wanted
        AND ARRAY(SELECT at.attname::text FROM unnest(co.confkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute at ON at.attrelid=co.confrelid AND at.attnum=k.attnum ORDER BY k.ord)=target_cols) THEN
        RAISE EXCEPTION 'Unexpected foreign key: %',tab;
      END IF;
    END LOOP;
  END LOOP;
  IF pg_catalog.to_regclass('public.runs') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.runs WHERE owner IS NULL OR btrim(owner)='') THEN RAISE EXCEPTION 'Ownerless historical runs require owner review'; END IF;
  END IF;
  IF pg_catalog.to_regclass('public.sessions') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.sessions WHERE owner IS NULL OR btrim(owner)='') THEN RAISE EXCEPTION 'Ownerless historical sessions require owner review'; END IF;
  END IF;
  IF pg_catalog.to_regclass('public.schema_migrations') IS NOT NULL THEN
    IF EXISTS (SELECT 1 FROM public.schema_migrations WHERE version > {SCHEMA_VERSION}) THEN RAISE EXCEPTION 'Database is newer than this release'; END IF;
  END IF;
END $preflight$;
"""
# Essential indexed invariants must never be silently skipped by IF NOT EXISTS.
indexes=[('runs_idempotency','runs',['owner','idempotency_key'],True),('tasks_role_state_run','tasks',['role','state','run_id'],False)]
indexcheck='DO $indexes$ BEGIN\n'
for name,t,cols,uniq in indexes:
 cs=','.join("'"+c+"'" for c in cols)
 indexcheck+=f"""IF pg_catalog.to_regclass('public.{name}') IS NOT NULL AND NOT EXISTS (
 SELECT 1 FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class ix ON ix.oid=i.indexrelid JOIN pg_catalog.pg_namespace ns ON ns.oid=ix.relnamespace JOIN pg_catalog.pg_class tb ON tb.oid=i.indrelid JOIN pg_catalog.pg_namespace tn ON tn.oid=tb.relnamespace
 WHERE ns.nspname='public' AND ix.relname='{name}' AND tn.nspname='public' AND tb.relname='{t}' AND i.indisvalid AND i.indisready AND i.indimmediate AND i.indisunique={str(uniq).lower()} AND i.indpred IS NULL AND i.indexprs IS NULL
 AND ARRAY(SELECT a.attname::text FROM unnest(i.indkey) WITH ORDINALITY k(attnum,ord) JOIN pg_catalog.pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum ORDER BY k.ord)=ARRAY[{cs}]) THEN RAISE EXCEPTION 'Unexpected index: {name}'; END IF;
"""
indexcheck+='END $indexes$;\n'
ddl=[]
for s in SCHEMA_STATEMENTS:
 s=re.sub(r'(CREATE TABLE IF NOT EXISTS |REFERENCES )([a-z_]+)',r'\1public.\2',s)
 ddl.append(s+';')
for t,cols in optional.items():
 for c in cols: ddl.append(f'ALTER TABLE public.{t} ADD COLUMN IF NOT EXISTS {c} TEXT;')
for name,t,cols,uniq in indexes: ddl.append(f"CREATE {'UNIQUE ' if uniq else ''}INDEX IF NOT EXISTS {name} ON public.{t} ({', '.join(cols)});")
security="DO $security$ DECLARE tab text; grantee text; BEGIN\n FOR tab IN SELECT unnest(ARRAY["+','.join("'"+t+"'" for t in TABLES)+"]) LOOP\n EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',tab);\n EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC',tab);\n FOR grantee IN SELECT rolname FROM pg_catalog.pg_roles WHERE rolname IN ('anon','authenticated') LOOP\n EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I',tab,grantee);\n END LOOP; END LOOP; END $security$;"
text="""-- Miyaar hosted catch-up, pinned application base 1e9ccd039292796400f34ccada1c927762af6b6d.
-- REVIEW ONLY: does not authorize any hosted write. Back up and rehearse first.
-- No existing owner/data is rewritten. Non-matching legacy schema aborts.
BEGIN;
SET LOCAL search_path = pg_catalog, public;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
SELECT pg_catalog.pg_advisory_xact_lock(727001);
"""+preflight+indexcheck+'\n'.join(ddl)+'\n'+security+f"\nINSERT INTO public.schema_migrations(version,applied_at) VALUES ({SCHEMA_VERSION},to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')) ON CONFLICT(version) DO NOTHING;\nCOMMIT;\n"
path=REPO/'database/migrations/20261023165959_hosted_schema_catchup.sql'
if not path.is_file(): raise SystemExit('The CLI-created migration file is missing; do not invent a replacement filename.')
path.write_text(text)
print(path, len(TABLES),'tables')
