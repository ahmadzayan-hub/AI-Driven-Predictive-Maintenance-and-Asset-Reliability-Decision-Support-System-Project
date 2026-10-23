"""No provider or production database calls: shared write-limiter outage."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from server.app import create_app
from tests.support import closing

class LimiterOutageTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.config = root / 'config.json'
        self.config.write_text(json.dumps({'database_file': str(root / 'test.db'),
                                          'vault_dir': str(root / 'vault')}))

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

