"""Authorization: where a role may come from, and what it may reach.

Finding R1 of the 2026-10-17 assessment: `_principal_from` searched
top-level claims, then `app_metadata`, then `user_metadata` for a role.
Managed providers let the signed-in user write `user_metadata` directly
(Supabase: `updateUser`), so any authenticated user could mint themselves
`owner` or `admin` — and both carried the cross-owner `admin` permission.
The reproduction in the assessment showed a second user going from HTTP
404 to HTTP 200 on another user's run by setting one metadata field.

These tests are written from the attacker's side: a second authenticated
user, holding a perfectly valid token, trying to reach data that is not
theirs. They use ephemeral signing keys and isolated temporary
databases; nothing here touches a deployment.

The companion change splits the two ideas the old table conflated.
Owning a workspace is not administering the platform, so `owner` no
longer carries `admin`. Crossing customer boundaries is an operator
grant, made server-side, never inherited by being a customer.
"""

import json
import tempfile
import time
import unittest
from pathlib import Path

try:
    import jwt
    from fastapi.testclient import TestClient

    from server.app import create_app
    from server.auth import (
        DEFAULT_ROLE,
        PERMISSIONS,
        JwtIdentity,
        issue_local_test_token,
        parse_role_assignments,
    )
    from tests.support import closing
    DEPS_AVAILABLE = True
except ImportError:  # pragma: no cover - CLI-only environments
    DEPS_AVAILABLE = False

SECRET = "authorization-test-secret-not-a-real-credential"
AUDIENCE = "agentic-os-authorization-test"
ISSUER = "https://issuer.invalid/"


def token(subject="user-a", claims=None, secret=SECRET, audience=AUDIENCE,
          issuer=ISSUER, expires_in=3600, algorithm="HS256"):
    payload = {"sub": subject, "exp": int(time.time()) + expires_in}
    if audience:
        payload["aud"] = audience
    if issuer:
        payload["iss"] = issuer
    payload.update(claims or {})
    return jwt.encode(payload, secret, algorithm=algorithm)


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi/pyjwt are not installed")
class RoleSourceTest(unittest.TestCase):
    """Which parts of a token may decide a role."""

    def identity(self, **kwargs):
        kwargs.setdefault("secret", SECRET)
        kwargs.setdefault("audience", AUDIENCE)
        kwargs.setdefault("issuer", ISSUER)
        return JwtIdentity(**kwargs)

    def role_of(self, claims, **kwargs):
        principal = self.identity(**kwargs).authenticate(
            "Bearer " + token(claims=claims))
        return principal.role, principal.role_source

    # -- the reproduction ------------------------------------------------
    def test_user_metadata_cannot_grant_owner(self):
        role, source = self.role_of({"user_metadata": {"agentic_os_role": "owner"}})
        self.assertEqual(role, DEFAULT_ROLE)
        self.assertEqual(source, "rejected_user_metadata")

    def test_user_metadata_cannot_grant_admin(self):
        role, _ = self.role_of({"user_metadata": {"role": "admin"}})
        self.assertEqual(role, DEFAULT_ROLE)
        self.assertNotIn("admin", PERMISSIONS[role])

    def test_user_metadata_cannot_override_a_trusted_claim(self):
        role, source = self.role_of({
            "app_metadata": {"agentic_os_role": "viewer"},
            "user_metadata": {"agentic_os_role": "admin"}})
        self.assertEqual(role, "viewer")
        self.assertEqual(source, "claim:app_metadata")

    def test_the_rejection_is_visible_rather_than_silent(self):
        # An operator looking at /api/identity should be able to see that
        # a self-grant was attempted and refused.
        principal = self.identity().authenticate(
            "Bearer " + token(claims={"user_metadata": {"role": "owner"}}))
        self.assertEqual(principal.as_dict()["role_source"],
                         "rejected_user_metadata")

    # -- trusted sources -------------------------------------------------
    def test_a_top_level_claim_is_trusted(self):
        role, source = self.role_of({"agentic_os_role": "analyst"})
        self.assertEqual(role, "analyst")
        self.assertEqual(source, "claim:top_level")

    def test_app_metadata_is_trusted(self):
        role, source = self.role_of({"app_metadata": {"role": "analyst"}})
        self.assertEqual(role, "analyst")
        self.assertEqual(source, "claim:app_metadata")

    def test_an_unknown_role_falls_back_to_least_privilege(self):
        role, source = self.role_of({"agentic_os_role": "superuser"})
        self.assertEqual(role, DEFAULT_ROLE)
        self.assertEqual(source, "default")

    def test_a_pinned_claim_name_ignores_the_others(self):
        role, _ = self.role_of({"role": "admin"}, role_claims=("agentic_os_role",))
        self.assertEqual(role, DEFAULT_ROLE)

    # -- server-managed assignment --------------------------------------
    def test_a_server_assignment_outranks_every_token_claim(self):
        role, source = self.role_of(
            {"agentic_os_role": "admin", "user_metadata": {"role": "admin"}},
            role_assignments={"user-a": "viewer"})
        self.assertEqual(role, "viewer")
        self.assertEqual(source, "server_assignment")

    def test_a_server_assignment_can_grant_platform_administration(self):
        role, source = self.role_of({}, role_assignments={"user-a": "admin"})
        self.assertEqual(role, "admin")
        self.assertEqual(source, "server_assignment")

    def test_assignments_parse_and_drop_what_they_cannot_understand(self):
        parsed = parse_role_assignments("a:admin, b:nonsense ,:viewer, c:analyst, junk")
        self.assertEqual(parsed, {"a": "admin", "c": "analyst"})


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi/pyjwt are not installed")
class TokenValidationTest(unittest.TestCase):

    def setUp(self):
        self.identity = JwtIdentity(secret=SECRET, audience=AUDIENCE, issuer=ISSUER)

    def assert_rejected(self, raw):
        from server.auth import AuthError
        with self.assertRaises(AuthError):
            self.identity.authenticate("Bearer " + raw)

    def test_an_expired_token_is_rejected(self):
        self.assert_rejected(token(expires_in=-60))

    def test_a_token_for_another_audience_is_rejected(self):
        self.assert_rejected(token(audience="someone-else"))

    def test_a_token_from_another_issuer_is_rejected(self):
        self.assert_rejected(token(issuer="https://evil.invalid/"))

    def test_a_token_missing_the_issuer_is_rejected_when_one_is_configured(self):
        self.assert_rejected(token(issuer=None))

    def test_a_token_missing_the_audience_is_rejected_when_one_is_configured(self):
        self.assert_rejected(token(audience=None))

    def test_a_token_signed_with_another_key_is_rejected(self):
        self.assert_rejected(token(secret="a-different-secret-entirely"))

    def test_an_unsigned_token_is_rejected(self):
        self.assert_rejected(jwt.encode(
            {"sub": "user-a", "exp": int(time.time()) + 60, "aud": AUDIENCE,
             "iss": ISSUER}, None, algorithm="none"))


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi/pyjwt are not installed")
class CrossOwnerAccessTest(unittest.TestCase):
    """A second user, with a valid token, reaching for another's run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({
            "agent_name": "Authorization Test Agent",
            "memory_file": str(root / "memory.json"),
            "database_file": str(root / "agentic.db"),
            "vault_dir": str(root / "vault"),
        }), encoding="utf-8")
        self.client = TestClient(
            closing(self, create_app(config, env={
                "AGENTIC_OS_JWT_SECRET": SECRET,
                "AGENTIC_OS_JWT_AUDIENCE": AUDIENCE,
                "AGENTIC_OS_JWT_ISSUER": ISSUER,
                "AGENTIC_OS_ROLE_ASSIGNMENTS": "platform-admin:admin",
            })), raise_server_exceptions=False)

    def headers(self, subject, claims=None):
        return {"Authorization": "Bearer " + token(subject=subject, claims=claims)}

    def owner_headers(self, subject):
        return self.headers(subject, {"agentic_os_role": "owner"})

    def make_run(self, subject):
        response = self.client.post(
            "/api/runs",
            json={"goal": "find the largest downtime",
                  "dataset_text": "month,downtime\n2026-01,10\n2026-02,20\n",
                  "dataset_name": "downtime.csv"},
            headers=self.owner_headers(subject))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["id"]

    # -- the headline guarantee ------------------------------------------
    def test_a_self_granted_metadata_role_reaches_nothing(self):
        run = self.make_run("user-a")
        attacker = self.headers("user-b", {
            "user_metadata": {"agentic_os_role": "owner"}})
        response = self.client.get(f"/api/runs/{run}", headers=attacker)
        self.assertEqual(response.status_code, 404, response.text)

    def test_an_owner_cannot_read_another_owners_run(self):
        run = self.make_run("user-a")
        response = self.client.get(f"/api/runs/{run}",
                                   headers=self.owner_headers("user-b"))
        self.assertEqual(response.status_code, 404)

    def test_an_owner_cannot_advance_another_owners_run(self):
        run = self.make_run("user-a")
        response = self.client.post(f"/api/runs/{run}/advance",
                                    headers=self.owner_headers("user-b"))
        self.assertEqual(response.status_code, 404)

    def test_an_owner_cannot_export_another_owners_run(self):
        run = self.make_run("user-a")
        for path in (f"/api/runs/{run}/data.csv", f"/api/runs/{run}/fields"):
            response = self.client.get(path, headers=self.owner_headers("user-b"))
            self.assertIn(response.status_code, (403, 404), path)

    def test_the_owner_still_reaches_their_own_run(self):
        run = self.make_run("user-a")
        response = self.client.get(f"/api/runs/{run}",
                                   headers=self.owner_headers("user-a"))
        self.assertEqual(response.status_code, 200)

    def test_a_viewer_cannot_create_a_run(self):
        response = self.client.post(
            "/api/runs",
            json={"goal": "g", "dataset_text": "a,b\n1,2\n", "dataset_name": "d.csv"},
            headers=self.headers("user-c"))
        self.assertEqual(response.status_code, 403)

    # -- the deliberate grant --------------------------------------------
    def test_an_assigned_platform_administrator_may_cross_owners(self):
        run = self.make_run("user-a")
        response = self.client.get(f"/api/runs/{run}",
                                   headers=self.headers("platform-admin"))
        self.assertEqual(response.status_code, 200, response.text)

    def test_an_unauthenticated_request_is_refused(self):
        run = self.make_run("user-a")
        self.assertEqual(self.client.get(f"/api/runs/{run}").status_code, 401)


@unittest.skipUnless(DEPS_AVAILABLE, "fastapi/pyjwt are not installed")
class PermissionTableTest(unittest.TestCase):

    def test_owning_a_workspace_is_not_administering_the_platform(self):
        self.assertNotIn("admin", PERMISSIONS["owner"],
                         "owner is a customer role; crossing customer "
                         "boundaries must be granted deliberately")

    def test_the_default_role_can_only_read(self):
        self.assertEqual(PERMISSIONS[DEFAULT_ROLE], {"read"})


if __name__ == "__main__":
    unittest.main()
