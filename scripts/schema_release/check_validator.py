"""Exercise the actual Python SELECT-only verifier on disposable PG17 catalogs."""
import json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parents[1]
if len(sys.argv)<4: raise SystemExit('Usage: check_validator.py REPOSITORY POSTGRES_BIN OUTPUT_DIRECTORY')
BIN=Path(sys.argv[2]).resolve()
OUTPUT=Path(sys.argv[3]).resolve()
if OUTPUT==REPO.resolve() or REPO.resolve() in OUTPUT.parents: raise SystemExit('Choose an output directory outside the tracked repository.')
sys.path.insert(0,str(REPO))
from server.schema_contract import validate_postgres_schema,SchemaNotReady
class SingleUserStore:
 def __init__(self,data):self.data=data;self.statements=[]
 def _exec(self,sql,params=()):
  assert sql.lstrip().upper().startswith('SELECT') and not params
  self.statements.append(sql)
  batch="BEGIN READ ONLY; SELECT COALESCE(json_agg(row_to_json(t)), '[]'::json)::text AS payload FROM ("+sql+") t; COMMIT;\n\n"
  p=subprocess.run([str(BIN/'postgres'),'--single','-D',self.data,'-j','postgres'],input=batch,text=True,capture_output=True)
  if re.search('(?:ERROR|FATAL):',p.stderr):raise AssertionError(p.stderr)
  m=re.search(r'payload = "(.*)"\s+\(typeid',p.stdout)
  if not m:raise AssertionError(p.stdout)
  return json.loads(m[1])
 def _schema_version(self):return int(self._exec('SELECT MAX(version) AS version FROM public.schema_migrations')[0]['version'] or 0)
results=[]
for c in json.loads((OUTPUT/'test_results.json').read_text()):
 store=SingleUserStore(c['data'])
 try:
  validate_postgres_schema(store); ready=True;reason=None
 except SchemaNotReady as e:ready=False;reason=str(e)
 expected=c['case'] in ('fresh','legacy','unrelated_preserved','column_backend_only','column_unrelated')
 # Column fixtures have the full matching schema and no client table grants.
 # Require the specific refusal, not merely a failure for unrelated drift.
 column_case=c['case'].startswith('column_') and not expected
 column_reason=not column_case or (reason is not None and 'runs.goal:public_api_column_grant' in reason)
 results.append({'case':c['case'],'passed':ready==expected and column_reason,'ready':ready,'select_count':len(store.statements),'reason':reason})
print(json.dumps(results,indent=2));(OUTPUT/'validator_results.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(0 if all(r['passed'] for r in results) else 1)

