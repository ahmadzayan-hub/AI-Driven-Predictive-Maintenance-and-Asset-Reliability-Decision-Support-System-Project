"""Public callback configuration is opt-in; it never activates an identity provider."""
import unittest
from types import SimpleNamespace
from server.auth import public_auth_config

class CallbackConfigurationTests(unittest.TestCase):
    def config(self, redirect, mode='jwt'):
        return public_auth_config(SimpleNamespace(mode=mode), {
            'SUPABASE_URL': 'https://example.supabase.co',
            'SUPABASE_PUBLISHABLE_KEY': 'public-only',
            'AGENTIC_OS_AUTH_REDIRECT_URL': redirect,
            'DATABASE_URL': 'never-publish-database',
            'SUPABASE_SERVICE_ROLE_KEY': 'never-publish-service-key',
            'AGENTIC_OS_JWT_SECRET': 'never-publish-secret',
        })

    def test_exact_https_callback_enables_pkce_not_specific_provider(self):
        config = self.config('https://app.example.invalid/auth/callback')
        self.assertEqual(config['flows'], ['password', 'pkce'])
        self.assertEqual(config['redirect_url'], 'https://app.example.invalid/auth/callback')
        self.assertNotIn('google', config['flows'])
        self.assertNotIn('never-publish', str(config))

    def test_invalid_callbacks_leave_password_only(self):
        for callback in ['', 'http://app.invalid/auth/callback', '//app.invalid/auth/callback',
                         'https://user:password@app.invalid/auth/callback',
                         'https://app.invalid/other', 'https://app.invalid/auth/callback?next=evil',
                         'https://app.invalid/auth/callback#access_token=x',
                         'https://app.invalid/auth/callback\n', 'https://[broken/auth/callback']:
            with self.subTest(callback=callback):
                config = self.config(callback)
                self.assertEqual(config['flows'], ['password'])
                self.assertEqual(config['redirect_url'], '')

    def test_local_and_demo_never_advertise_hosted_auth(self):
        for mode in ['local', 'demo']:
            config = self.config('https://app.invalid/auth/callback', mode)
            self.assertEqual(config, {'mode': mode, 'flows': []})
