"""Loopback-only synthetic hackathon workspace; never opens the owner's database.

Uses existing installed dependencies. No model, worker, download or cloud call.
The generated database is kept under the supplied NEW directory for inspection.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8017)
    args = parser.parse_args()
    directory = args.data_dir.resolve()
    if directory.exists():
        raise SystemExit('Use a new empty synthetic directory; existing data is never opened.')
    if not (ROOT / 'frontend/dist/index.html').is_file():
        raise SystemExit('Build the frontend using installed dependencies first.')
    directory.mkdir(parents=True)
    config = directory / 'config.json'
    config.write_text(json.dumps({'agent_name': 'Miyaar Jarvis synthetic demo',
        'database_file': str(directory / 'synthetic.db'), 'memory_file': str(directory / 'memory.json'),
        'vault_dir': str(directory / 'vault')}), encoding='utf-8')
    # Isolate only this child process from ambient hosted/model settings.
    for name in list(os.environ):
        if name.startswith(('AGENTIC_OS_', 'OLLAMA_', 'SUPABASE_', 'OPENAI_', 'ANTHROPIC_', 'GROQ_', 'PG_')) or name == 'DATABASE_URL':
            del os.environ[name]
    os.environ['AGENTIC_OS_CONFIG'] = str(config)
    from server.app import app
    engine = app.state.engine
    fixture = 'Record_ID,Asset_ID,Period,Maintenance_Cost_USD,Operating_Hours,Planned_Operating_Hours,Downtime_Hours,Failure_Count\nSYN-01,SYN-A,2026-01,120,90,100,10,1\nSYN-02,SYN-B,2026-02,300,280,300,20,2\nSYN-03,SYN-C,2026-03,80,100,100,0,0\n'
    sparse = 'Record_ID,Asset_ID,Maintenance_Cost_USD\nSYN-04,SYN-D,40\n'
    for name, csv in [('SYNTHETIC_maintenance_review.csv', fixture), ('SYNTHETIC_missing_hours.csv', sparse)]:
        run = engine.create_run('Synthetic hackathon maintenance review; no operational claim',
                                dataset_text=csv, dataset_name=name)
        for _ in range(30):
            if run['state'] in {'awaiting_approval', 'completed', 'failed', 'blocked'}:
                break
            run = engine.advance(run['id'])
        if run['state'] not in {'awaiting_approval', 'completed'}:
            raise SystemExit('Synthetic analysis did not complete: ' + run['state'])
    @app.get('/api/jarvis-demo')
    def marker():
        return {'synthetic': True, 'llm': False}
    app.router.routes.insert(0, app.router.routes.pop())  # before the SPA static mount
    print(f'Synthetic Jarvis: http://127.0.0.1:{args.port}/?workspace=jarvis', flush=True)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
