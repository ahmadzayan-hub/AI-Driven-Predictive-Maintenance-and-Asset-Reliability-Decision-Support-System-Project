"""Disposable PG17 single-user tests. No network, credentials or production URL."""
import json,re,subprocess,tempfile,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parents[1]
if len(sys.argv)<4: raise SystemExit('Usage: test_migration.py REPOSITORY POSTGRES_BIN OUTPUT_DIRECTORY')
BIN=Path(sys.argv[2]).resolve()
OUTPUT=Path(sys.argv[3]).resolve()
if OUTPUT==REPO.resolve() or REPO.resolve() in OUTPUT.parents: raise SystemExit('Choose an output directory outside the tracked repository.')
OUTPUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(REPO))
from server.storage import SCHEMA_STATEMENTS,TABLES
M=json.loads((ROOT/'manifest.json').read_text())
SQL=(REPO/'database/migrations/20261023165959_hosted_schema_catchup.sql').read_text()
legacy_names=['runs','tasks','approvals','artifacts','sessions','memory_kv','vault_notes','datasets','connectors']
missing={'runs':['assumptions_json','idempotency_key','request_hash'],'approvals':['decided_by'],'connectors':['credential_id']}
legacy=[]
for s in SCHEMA_STATEMENTS:
 name=re.search('CREATE TABLE IF NOT EXISTS ([a-z_]+)',s)[1]
 if name not in legacy_names:continue
 for c in missing.get(name,[]): s=re.sub(r',?\s*'+c+r' TEXT,?', lambda m: ',' if m.group().startswith(',') and m.group().endswith(',') else '', s)
 # ensure neighboring words remain delimited after removal
 s=s.replace('connector_id TEXT\n      paused','connector_id TEXT,\n      paused')
 legacy.append(s+';')
legacy_sql='\n'.join(legacy)+'\n'+'\n'.join(f'ALTER TABLE public.{t} ENABLE ROW LEVEL SECURITY; REVOKE ALL ON public.{t} FROM PUBLIC,anon,authenticated;' for t in legacy_names)
(OUTPUT/'legacy_fixture.sql').write_text(legacy_sql)
# Manually meaningful sentinel rows in every historical table, never production data.
fixtures=[]
for t in legacy_names:
 cols=[c for c in M[t]['columns'] if c not in missing.get(t,[])]
 vals=[]
 for c in cols:
  if M[t]['columns'][c]['type']=='integer':v='1'
  elif c=='owner':v="'synthetic-owner-a'"
  elif c=='run_id':v="'sentinel-runs'"
  elif c=='id':v="'sentinel-"+t+"'"
  else:v="'synthetic-"+c+"'"
  vals.append(v)
 fixtures.append(f"INSERT INTO public.{t}({','.join(cols)}) VALUES ({','.join(vals)});")
fixture_sql='\n'.join(fixtures)
reserve="do $$ declare n oid; begin loop create sequence public.test_oid_reservation; select oid into n from pg_class where relname='test_oid_reservation'; drop sequence public.test_oid_reservation; exit when n >= 16384; end loop; end $$;"
roles="CREATE ROLE anon NOLOGIN NOSUPERUSER NOBYPASSRLS; CREATE ROLE authenticated NOLOGIN NOSUPERUSER NOBYPASSRLS; CREATE ROLE service_role NOLOGIN NOSUPERUSER BYPASSRLS; ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon,authenticated,service_role;"
table_sql=','.join("'"+t+"'" for t in TABLES)
checks=f"""
DO $$ BEGIN
 IF (SELECT count(*) FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN ({table_sql}))<>{len(TABLES)} THEN RAISE EXCEPTION 'Wrong table count'; END IF;
 IF (SELECT max(version) FROM public.schema_migrations)<>1 THEN RAISE EXCEPTION 'Wrong marker'; END IF;
 IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN ({table_sql}) AND NOT c.relrowsecurity) THEN RAISE EXCEPTION 'RLS absent'; END IF;
 IF EXISTS (SELECT 1 FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r' AND c.relname IN ({table_sql}) AND (has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER') OR has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'))) THEN RAISE EXCEPTION 'Client grant remains'; END IF;
 IF NOT has_table_privilege('service_role','public.runs','SELECT') THEN RAISE EXCEPTION 'Existing service grant lost'; END IF;
END $$;
SET ROLE authenticated;
DO $$ BEGIN
 IF (SELECT rolsuper OR rolbypassrls OR oid<16384 FROM pg_roles WHERE rolname=current_user) THEN RAISE EXCEPTION 'Invalid test role'; END IF;
 BEGIN PERFORM * FROM public.runs; RAISE EXCEPTION 'UNAUTHORIZED_READ'; EXCEPTION WHEN insufficient_privilege THEN NULL; END;
END $$;
RESET ROLE;
"""
legacy_checks='\n'.join(f"DO $$ BEGIN IF (SELECT count(*) FROM public.{t})<>1 THEN RAISE EXCEPTION 'Sentinel lost in {t}'; END IF; END $$;" for t in legacy_names)
legacy_checks+="\nDO $$ BEGIN IF (SELECT owner FROM public.runs)<>'synthetic-owner-a' OR (SELECT dataset_text FROM public.runs)<>'synthetic-dataset_text' THEN RAISE EXCEPTION 'Sentinel changed'; END IF; END $$;"
results=[]
(OUTPUT/'test_databases').mkdir(exist_ok=True)
def run(name,setup,body,expected_errors=None,tail=''):
 if os.environ.get('ONLY_CASES') and name not in os.environ['ONLY_CASES'].split(','):return
 data=Path(tempfile.mkdtemp(prefix=name+'-',dir=OUTPUT/'test_databases'))/'data'
 subprocess.run([str(BIN/'initdb'),'-D',str(data),'--no-locale','--encoding=UTF8','--auth=trust'],capture_output=True,check=True)
 outputs=[]
 for phase,part in [('setup',reserve+'\n'+roles+'\n'+setup),('migration',body),('verification',tail+"\nSELECT 'MIGRATION_TEST_END';")]:
  sql='\n'.join(l for l in part.splitlines() if l.strip())+'\n\n'
  r=subprocess.run([str(BIN/'postgres'),'--single','-D',str(data),'-j','postgres'],input=sql,text=True,capture_output=True)
  outputs.append('PHASE '+phase+'\n'+r.stdout+r.stderr)
 out='\n'.join(outputs)
 (OUTPUT/(name+'.log')).write_text(out)
 errors=re.findall(r'.*(?:ERROR|FATAL):.*',out)
 expected_errors=expected_errors or []
 ok= all(any(e in x for x in errors) for e in expected_errors) and ('MIGRATION_TEST_END' in out)
 if expected_errors:ok=ok and all(any(e in x for e in expected_errors) or 'current transaction is aborted' in x for x in errors)
 else:ok=ok and not errors
 results.append({'case':name,'passed':ok,'errors':errors,'data':str(data)})
run('fresh','',SQL+checks+SQL+checks)
run('legacy',legacy_sql+fixture_sql,SQL+checks+legacy_checks+SQL+checks+legacy_checks)
# Failing preflight must leave the baseline and existing data, with no schema marker/new tables.
rollback_check="DO $$ BEGIN IF to_regclass('public.schema_migrations') IS NOT NULL OR to_regclass('public.organizations') IS NOT NULL THEN RAISE EXCEPTION 'PARTIAL_MIGRATION'; END IF; END $$;"
run('wrong_type',legacy_sql+"ALTER TABLE public.connectors ALTER COLUMN goal TYPE integer USING 1;",SQL,['Unexpected column type/nullability: connectors.goal'],rollback_check)
run('ownerless',legacy_sql+fixture_sql+"UPDATE public.runs SET owner=NULL;",SQL,['Ownerless historical runs require owner review'],rollback_check)
run('missing_owner_column',legacy_sql+"ALTER TABLE public.memory_kv DROP CONSTRAINT memory_kv_pkey; ALTER TABLE public.memory_kv DROP COLUMN owner; ALTER TABLE public.memory_kv ADD PRIMARY KEY(key);",SQL,['Required legacy column absent: memory_kv.owner'],rollback_check)
run('wrong_index',legacy_sql+"CREATE INDEX runs_idempotency ON public.runs(goal);",SQL,['Unexpected index: runs_idempotency'],rollback_check)
run('wrong_fk',legacy_sql+"ALTER TABLE public.tasks DROP CONSTRAINT tasks_run_id_fkey; ALTER TABLE public.tasks ADD FOREIGN KEY(run_id) REFERENCES public.runs(id) ON DELETE CASCADE;",SQL,['Unexpected foreign key: tasks'],rollback_check)
run('atomic_failure',legacy_sql+fixture_sql,SQL.replace('COMMIT;',"DO $$ BEGIN RAISE EXCEPTION 'SYNTHETIC_POST_DDL_FAILURE'; END $$; COMMIT;"),['SYNTHETIC_POST_DDL_FAILURE'],rollback_check+legacy_checks)
extra="CREATE TABLE public.unrelated_system(id text PRIMARY KEY,body text); INSERT INTO public.unrelated_system VALUES ('keep','untouched');"
extra_check="DO $$ BEGIN IF (SELECT body FROM public.unrelated_system WHERE id='keep')<>'untouched' OR (SELECT relrowsecurity FROM pg_class WHERE oid='public.unrelated_system'::regclass) OR NOT has_table_privilege('anon','public.unrelated_system','SELECT') THEN RAISE EXCEPTION 'UNRELATED_OBJECT_CHANGED'; END IF; END $$;"
run('unrelated_preserved',legacy_sql+fixture_sql+extra,SQL+checks+legacy_checks+extra_check)
run('existing_client_grant',legacy_sql+"GRANT SELECT ON public.runs TO authenticated;",SQL,['Existing client access requires review: runs'],rollback_check+"DO $$ BEGIN IF NOT has_table_privilege('authenticated','public.runs','SELECT') THEN RAISE EXCEPTION 'EXISTING_ACCESS_CHANGED'; END IF; END $$;")
run('deferred_key',legacy_sql+"ALTER TABLE public.memory_kv DROP CONSTRAINT memory_kv_pkey; ALTER TABLE public.memory_kv ADD PRIMARY KEY(owner,key) DEFERRABLE INITIALLY DEFERRED;",SQL,['Unexpected primary key: memory_kv'],rollback_check)
run('inherited_client_grant',legacy_sql+"CREATE ROLE app_reader NOLOGIN; GRANT SELECT ON public.runs TO app_reader; GRANT app_reader TO authenticated;",SQL,['Existing client access requires review: runs'],rollback_check)
(OUTPUT/'test_results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(x['passed'] for x in results) else 1)
