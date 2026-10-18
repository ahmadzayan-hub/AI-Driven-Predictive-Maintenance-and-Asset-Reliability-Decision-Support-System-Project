"""Isolated review probes. Synthetic data and ephemeral signing keys only."""
import csv
import io
import json
import secrets
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import jwt
from fastapi.testclient import TestClient
from server.app import create_app
from server.auth import issue_local_test_token
from server.maintenance import contract, kpis
from server.maintenance.governance import MaintenanceGovernance
from server.model_gateway import ModelGateway
from server.modelling import _inputs
from server.runs import RunEngine
from server.storage import open_store
from tests.test_maintenance_governance import maintenance_rows

results = {}

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    config = root / 'config.json'
    config.write_text(json.dumps({
        'database_file': str(root / 'api.db'),
        'memory_file': str(root / 'memory.json'), 'vault_dir': str(root / 'vault'),
    }), encoding='utf-8')
    secret = secrets.token_hex(32)
    app = create_app(config, env={'AGENTIC_OS_JWT_SECRET': secret, 'AGENTIC_OS_ENV': 'production'})
    try:
        with TestClient(app) as client:
            victim = {'Authorization': 'Bearer ' + issue_local_test_token(secret, 'review-a', 'analyst')}
            run = client.post('/api/runs', headers=victim, json={'goal': 'Synthetic review run'}).json()
            def token(metadata):
                return {'Authorization': 'Bearer ' + jwt.encode({
                    'sub': 'review-b', 'exp': int(time.time()) + 600,
                    'role': 'authenticated', 'user_metadata': metadata,
                }, secret, algorithm='HS256')}
            normal = token({})
            elevated = token({'agentic_os_role': 'owner'})
            results['authorization'] = {
                'ordinary_role': client.get('/api/identity', headers=normal).json()['principal']['role'],
                'ordinary_other_owner_run_status': client.get('/api/runs/' + run['id'], headers=normal).status_code,
                'metadata_role': client.get('/api/identity', headers=elevated).json()['principal']['role'],
                'metadata_other_owner_run_status': client.get('/api/runs/' + run['id'], headers=elevated).status_code,
            }
    finally:
        app.state.store._conn.close()

    rows = maintenance_rows()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    store = open_store(None, root / 'stage.db')
    try:
        stage = MaintenanceGovernance(fail_on_high=True)
        engine = RunEngine(store, root / 'stage-vault', ModelGateway(env={}), stages={stage.role: stage})
        run = engine.create_run('Analyze synthetic maintenance records', dataset_text=buf.getvalue(), dataset_name='review-fixture.csv')
        for _ in range(40):
            if run['state'] not in ('queued', 'running'):
                break
            run = engine.advance(run['id'])
        task = next(t for t in run['tasks'] if t['role'] == stage.role)
        results['fail_on_high'] = {
            'configured': stage.fail_on_high, 'can_fail_run': stage.can_fail_run,
            'task_state': task['state'], 'run_state': run['state'],
            'report_created': bool(run['report']),
        }
    finally:
        store._conn.close()

columns = list(rows[0])
numeric = [c for c in columns if isinstance(rows[0][c], (int, float))]
chosen_numbers, chosen_text = _inputs(rows, columns, numeric, {'Downtime_Hours', 'Record_Date'})
_, excluded = contract.model_inputs(columns)
selected = chosen_numbers + [c for c, _ in chosen_text]
results['model_inputs'] = {'selected_despite_contract_exclusion': [c for c in selected if c in excluded]}

results['kpi_missing_value'] = kpis.REGISTER['downtime_per_record'].compute([
    {'Downtime_Hours': '10'}, {'Downtime_Hours': ''}])
results['kpi_population_column_missing'] = kpis.computable(['First_Time_Fix_Count', 'Corrective_WO_Count'])[1].get('first_time_fix', 'reported computable')
output = json.dumps(results, indent=2)
Path(__file__).with_name('probes.json').write_text(output, encoding='utf-8')
print(output)
