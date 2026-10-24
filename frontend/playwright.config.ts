import { defineConfig } from '@playwright/test'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// A local virtual environment is available on Windows even without python3
// on PATH. CI can still use its interpreter or set PYTHON_EXECUTABLE.
const localPython = fileURLToPath(new URL(process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python', import.meta.url))
const python = process.env.PYTHON_EXECUTABLE ?? (existsSync(localPython) ? localPython : 'python3')
if (/["\r\n]/.test(python)) throw new Error('Invalid PYTHON_EXECUTABLE path')
const PYTHON = `"${python}"`

// The web server runs the real FastAPI adapter against a disposable
// configuration in e2e/.tmp/, so end-to-end runs never touch the
// repository's real data/memory.json.
const PREPARE_CONFIG =
  `${PYTHON} -c "import json,os,shutil; os.makedirs('frontend/e2e/.tmp',exist_ok=True); ` +
  'shutil.rmtree(\'frontend/e2e/.tmp/vault\', ignore_errors=True); ' +
  'shutil.rmtree(\'frontend/e2e/.tmp/sources\', ignore_errors=True); os.makedirs(\'frontend/e2e/.tmp/sources\'); ' +
  '[os.remove(p) for p in [\'frontend/e2e/.tmp/agentic.db\'] if os.path.exists(p)]; ' +
  'json.dump({\'agent_name\':\'Agentic OS\',\'version\':\'1.0.0\',' +
  '\'preferences\':{\'tone\':\'friendly\',\'language\':\'English\',\'save_history\':True},' +
  '\'memory_file\':\'frontend/e2e/.tmp/memory.json\',' +
  '\'database_file\':\'frontend/e2e/.tmp/agentic.db\',' +
  '\'vault_dir\':\'frontend/e2e/.tmp/vault\',\'maximum_history_items\':50,' +
  '\'stages\':[{\'path\':\'examples.stages.target_attainment.TargetAttainment\',' +
  '\'options\':{\'target\':3000000}},' +
  '\'server.modelling.RegressionModel\',\'server.modelling.ClassificationModel\',' +
  '\'server.modelling.ClusteringModel\',\'server.modelling.SeasonalForecast\'],' +
  '\'profiles\':{\'default\':[],\'with-target\':[\'target_attainment\'],' +
  '\'models\':[\'regression_model\',\'classification_model\',\'clustering_model\',\'seasonal_model\']},' +
  '\'agent_runtime\':{\'path\':\'tests.test_agent_runtime.ScriptedRuntime\',' +
  '\'options\':{\'calls\':[[\'help\',{}]],\'closing\':\'Over to you.\',\'trigger\':\'sort out\'}}},' +
  'open(\'frontend/e2e/.tmp/config.json\',\'w\')); ' +
  'json.dump({},open(\'frontend/e2e/.tmp/memory.json\',\'w\'))"'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:8123',
    trace: 'retain-on-failure',
    // Use the environment's pre-installed Chromium when present instead of
    // downloading a browser (see PLAYWRIGHT_EXECUTABLE_PATH to override).
    launchOptions: process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : undefined,
  },
  projects: [
    {
      name: 'desktop',
      use: { viewport: { width: 1440, height: 900 } },
    },
    {
      name: 'mobile',
      use: { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true },
    },
  ],
  webServer: [
    {
      command: `${PREPARE_CONFIG} && ${PYTHON} -m uvicorn server.app:app --host 127.0.0.1 --port 8123`,
      cwd: '..',
      url: 'http://127.0.0.1:8123/api/health',
      // Live sources (ADR 0034) read files from this folder at the
      // reserved https://fixtures.invalid/ host; never set outside tests.
      env: {
        AGENTIC_OS_CONFIG: 'frontend/e2e/.tmp/config.json',
        AGENTIC_OS_CONNECTOR_FIXTURES: 'frontend/e2e/.tmp/sources',
        // Tests refresh one source twice in a row; the cooldown is for people.
        AGENTIC_OS_CONNECTOR_COOLDOWN: '0',
      },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Second instance with managed auth enabled, for e2e/auth.spec.ts.
      // The secret is test-only and the provider is never contacted.
      command:
        `${PYTHON} -c "import json,os; os.makedirs('frontend/e2e/.tmp/auth',exist_ok=True); ` +
        'json.dump({\'agent_name\':\'Agentic OS\',\'version\':\'1.0.0\',' +
        "'memory_file':'frontend/e2e/.tmp/auth/memory.json'," +
        "'database_file':'frontend/e2e/.tmp/auth/agentic.db'," +
        "'vault_dir':'frontend/e2e/.tmp/auth/vault'}, " +
        'open(\'frontend/e2e/.tmp/auth/config.json\',\'w\'))" ' +
        `&& ${PYTHON} -m uvicorn server.app:app --host 127.0.0.1 --port 8124`,
      cwd: '..',
      url: 'http://127.0.0.1:8124/api/health',
      env: {
        AGENTIC_OS_CONFIG: 'frontend/e2e/.tmp/auth/config.json',
        AGENTIC_OS_JWT_SECRET: 'e2e-test-signing-secret',
        SUPABASE_URL: 'https://example.supabase.co',
        SUPABASE_ANON_KEY: 'e2e-publishable-key',
      },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Third instance in view-only demo mode (ADR 2026-10-21), for
      // e2e/demo.spec.ts. A fresh database each start, so the server seeds
      // its one fictional analysis; the maintenance profile is configured
      // the way test_demo.py does, so Asset Intelligence has evidence.
      command:
        `${PYTHON} -c "import json,os,shutil; os.makedirs('frontend/e2e/.tmp/demo',exist_ok=True); ` +
        'shutil.rmtree(\'frontend/e2e/.tmp/demo/vault\', ignore_errors=True); ' +
        '[os.remove(p) for p in [\'frontend/e2e/.tmp/demo/agentic.db\'] if os.path.exists(p)]; ' +
        'json.dump({\'agent_name\':\'Agentic OS\',\'version\':\'1.0.0\',' +
        "'memory_file':'frontend/e2e/.tmp/demo/memory.json'," +
        "'database_file':'frontend/e2e/.tmp/demo/agentic.db'," +
        "'vault_dir':'frontend/e2e/.tmp/demo/vault'," +
        "'stages':['server.maintenance.governance.MaintenanceGovernance'," +
        "'server.maintenance.targets.MaintenanceRisk'," +
        "'server.maintenance.rail_stage.RailAssetManagerStage']," +
        "'profiles':{'default':[],'maintenance':['maintenance_governance','maintenance_risk','rail_asset_manager']}}, " +
        'open(\'frontend/e2e/.tmp/demo/config.json\',\'w\'))" ' +
        `&& ${PYTHON} -m uvicorn server.app:app --host 127.0.0.1 --port 8125`,
      cwd: '..',
      url: 'http://127.0.0.1:8125/api/health',
      env: {
        AGENTIC_OS_CONFIG: 'frontend/e2e/.tmp/demo/config.json',
        AGENTIC_OS_DEMO: '1',
      },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Explicit isolated local-owner profile, no account/key/model is created.
      command: `${PYTHON} -c "import shutil; shutil.rmtree('frontend/e2e/.tmp/local-workspace', ignore_errors=True)" && ` +
        `${PYTHON} scripts/local_workspace.py start --port 8127 --workspace frontend/e2e/.tmp/local-workspace`,
      cwd: '..',
      url: 'http://127.0.0.1:8127/api/health',
      // A user's optional local-model settings must not enable generation in tests.
      env: { OLLAMA_MODEL: '', OLLAMA_HOST: '', AGENTIC_OS_TASK_MODELS: '',
        AGENTIC_OS_HERMES_MODEL: '', AGENTIC_OS_AGENT_MODEL: '', AGENTIC_OS_CONSULTANTS: '' },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // Real API + worker + durable checkpoints; scripted model transport only.
      // This disposable fixture is never imported by the production factory.
      command: `${PYTHON} -m uvicorn tests.specialist_browser_app:app --host 127.0.0.1 --port 8126`,
      cwd: '..',
      url: 'http://127.0.0.1:8126/api/health',
      env: { MIYAAR_SYNTHETIC_SPECIALIST_BROWSER: '1' },
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})
