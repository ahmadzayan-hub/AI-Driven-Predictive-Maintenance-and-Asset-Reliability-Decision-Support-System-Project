"""Identity and authorization boundary.

Two providers behind one interface:

- LocalIdentity — the labelled local-first mode. Every request is the
  single local owner; no login, no credentials, unchanged offline UX.
  This is the default and what tests/CI exercise.
- JwtIdentity — production mode. Verifies a standards-based Bearer JWT
  from a managed provider (Supabase Auth, or any OIDC issuer) using a
  shared secret (HS256) or a JWKS endpoint (RS256/ES256). No password
  handling, no credential storage, no homemade auth.

- DemoIdentity — the public demo (AGENTIC_OS_DEMO=1). No sign-in; every
  visitor is one shared principal that can only read, and what it reads is
  fictional data the server generated (server/demo.py).

Fail-closed rule: when the deployment declares production
(AGENTIC_OS_ENV=production) or demands auth (AGENTIC_OS_REQUIRE_AUTH=1)
and no provider is configured, app startup raises instead of silently
serving everything as the local owner.
"""

import os
import time
from dataclasses import dataclass

# Role -> permission set. Checked server-side on every action; the UI is
# never the enforcement point.
#
# `admin` is *platform* administration: it crosses customer boundaries
# (see `owns` in app.py). Owning a workspace is not the same thing, so
# `owner` does not carry it. A customer owns their own data completely
# and can see nobody else's; reaching across owners is an operator
# action, granted deliberately, never inherited by being a customer.
PERMISSIONS = {
    "owner": {"read", "write", "approve"},
    "admin": {"read", "write", "approve", "admin"},
    "analyst": {"read", "write", "approve"},
    "viewer": {"read"},
    "auditor": {"read"},
}
ROLES = tuple(PERMISSIONS)
# Roles that cross customer boundaries. Kept as a name so the rule is
# searchable rather than implied by a permission string.
PLATFORM_ROLES = frozenset({"admin"})

# Least privilege: an authenticated user whose token carries no role
# claim gets read-only access until an operator grants more.
DEFAULT_ROLE = "viewer"

ROLE_CLAIMS = ("agentic_os_role", "role", "user_role")

# Where a role may come from, in order of trust.
#
# A signed token proves who the subject is. It does not make every field
# inside it administrator-controlled. Managed providers deliberately
# expose a bag the *end user* can rewrite - in Supabase that is
# `user_metadata`, writable by the signed-in user through `updateUser` -
# so a role read from there is a role the user granted themselves.
# https://supabase.com/docs/guides/auth/users
#
# Only these two token locations are trusted: top-level claims, which the
# issuer mints, and `app_metadata`, which a managed provider writes only
# with its service key. `user_metadata` is never consulted.
TRUSTED_CLAIM_SOURCES = ("", "app_metadata")
UNTRUSTED_CLAIM_SOURCES = ("user_metadata",)


class AuthNotConfigured(RuntimeError):
    """Raised at startup when production is declared without a provider."""


class AuthError(Exception):
    """Invalid or missing credentials (mapped to 401 by the API layer)."""


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str
    provider: str
    email: str = ""
    # Which source granted the role: "server_assignment", "claim:…",
    # "rejected_user_metadata" or "default". Diagnostic, never an input
    # to a permission decision.
    role_source: str = "default"

    @property
    def crosses_owners(self):
        return self.role in PLATFORM_ROLES

    def can(self, permission):
        return permission in PERMISSIONS.get(self.role, frozenset())

    def as_dict(self):
        return {
            "subject": self.subject,
            "role": self.role,
            "provider": self.provider,
            "email": self.email,
            "permissions": sorted(PERMISSIONS.get(self.role, frozenset())),
            "role_source": self.role_source,
        }


LOCAL_PRINCIPAL = Principal(subject="local-owner", role="owner", provider="local")


class LocalIdentity:
    mode = "local"
    requires_token = False

    def authenticate(self, authorization_header):
        return LOCAL_PRINCIPAL


# The demo's one principal. "viewer" carries read only, so every write
# endpoint answers 403 through the same permission check as any viewer.
DEMO_PRINCIPAL = Principal(subject="demo-showcase", role="viewer", provider="demo")


class DemoIdentity:
    mode = "demo"
    requires_token = False

    def authenticate(self, authorization_header):
        # A token sent to the demo grants nothing: there is no one to
        # sign in as, so it is ignored rather than verified.
        return DEMO_PRINCIPAL


class JwtIdentity:
    mode = "jwt"
    requires_token = True

    def __init__(self, secret=None, jwks_url=None, audience=None, issuer=None,
                 default_role=DEFAULT_ROLE, role_assignments=None,
                 role_claims=ROLE_CLAIMS):
        if not secret and not jwks_url:
            raise AuthNotConfigured("JwtIdentity needs a secret or a JWKS URL.")
        self.secret = secret
        self.jwks_url = jwks_url
        self.audience = audience
        self.issuer = issuer
        self.default_role = default_role if default_role in PERMISSIONS else DEFAULT_ROLE
        # subject -> role, held by the operator. The only way to grant a
        # platform role, and unreachable from any token.
        self.role_assignments = {
            str(k): v for k, v in (role_assignments or {}).items() if v in PERMISSIONS}
        # An operator may pin a single claim name instead of accepting
        # any of the defaults.
        self.role_claims = tuple(role_claims) or ROLE_CLAIMS
        self._jwks_client = None

    def _decode(self, token):
        import jwt  # lazy: only hosted mode needs the dependency

        required = ["exp", "sub"]
        if self.issuer:
            required.append("iss")
        if self.audience:
            required.append("aud")
        # A token without the issuer and audience this deployment expects
        # may be a valid token for somewhere else entirely.
        options = {"require": required, "verify_aud": bool(self.audience),
                   "verify_iss": bool(self.issuer)}
        common = {
            "audience": self.audience,
            "issuer": self.issuer,
            "options": options,
            "leeway": 10,
        }
        if self.jwks_url:
            if self._jwks_client is None:
                self._jwks_client = jwt.PyJWKClient(self.jwks_url, cache_keys=True)
            key = self._jwks_client.get_signing_key_from_jwt(token).key
            # Asymmetric only: an attacker cannot downgrade to HS256 and
            # sign with the public key.
            return jwt.decode(token, key, algorithms=["RS256", "ES256"], **common)
        # Shared-secret mode pins HS256, so "alg": "none" and asymmetric
        # confusion attacks are rejected before signature checking.
        return jwt.decode(token, self.secret, algorithms=["HS256"], **common)

    def authenticate(self, authorization_header):
        import jwt

        if not authorization_header:
            raise AuthError("Authentication required.")
        scheme, _, token = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise AuthError("Expected an Authorization: Bearer <token> header.")
        try:
            claims = self._decode(token.strip())
        except jwt.ExpiredSignatureError:
            raise AuthError("The session token has expired. Sign in again.")
        except Exception:
            # Never echo library internals or token content back to a client.
            raise AuthError("The session token is not valid.")
        return self._principal_from(claims)

    def role_for(self, claims):
        """The role this token may hold, and where it came from.

        Precedence, highest first:

        1. A server-managed assignment for this subject. The operator
           holds this list; nothing in the token can override it, which
           is what makes it the place to grant platform administration.
        2. A trusted token claim - top level, or `app_metadata`.
        3. The least-privilege default.

        `user_metadata` is skipped at every step. A role found only there
        is reported as `rejected_user_metadata` so the attempt is visible
        in the identity response rather than silently downgraded.
        """
        subject = str(claims.get("sub") or "")
        assigned = self.role_assignments.get(subject)
        if assigned in PERMISSIONS:
            return assigned, "server_assignment"

        for name in TRUSTED_CLAIM_SOURCES:
            source = claims if not name else claims.get(name)
            if not isinstance(source, dict):
                continue
            for claim in self.role_claims:
                candidate = source.get(claim)
                if isinstance(candidate, str) and candidate in PERMISSIONS:
                    return candidate, f"claim:{name or 'top_level'}"

        for name in UNTRUSTED_CLAIM_SOURCES:
            source = claims.get(name)
            if isinstance(source, dict) and any(
                    isinstance(source.get(c), str) and source.get(c) in PERMISSIONS
                    for c in self.role_claims):
                return self.default_role, "rejected_user_metadata"

        return self.default_role, "default"

    def _principal_from(self, claims):
        role, source = self.role_for(claims)
        return Principal(
            subject=str(claims["sub"]),
            role=role,
            provider="jwt",
            email=str(claims.get("email") or ""),
            role_source=source,
        )


def public_auth_config(identity, env=None):
    """Non-secret configuration the browser needs to start a sign-in.

    The publishable ("anon") key is designed to be public; the JWT
    secret, service-role key and database URL are never included."""
    env = os.environ if env is None else env
    if identity.mode in ("local", "demo"):
        return {"mode": identity.mode, "flows": []}
    provider_url = (env.get("SUPABASE_URL") or "").rstrip("/")
    publishable_key = (
        env.get("SUPABASE_PUBLISHABLE_KEY") or env.get("SUPABASE_ANON_KEY") or ""
    )
    flows = []
    if provider_url and publishable_key:
        # Password sign-in is implemented. Magic-link callback token
        # verification/redirect handling is not yet implemented, so it
        # must not be advertised as a working sign-in option.
        flows = ["password"]
    return {
        "mode": "jwt",
        "provider": "supabase" if provider_url else "custom",
        "provider_url": provider_url,
        "publishable_key": publishable_key,
        "flows": flows,
    }


def parse_role_assignments(raw):
    """`subject:role,subject:role` from the operator, as a mapping.

    Deliberately not read from the database the application itself
    writes: a role list a request could reach is a role list a request
    could change. Unparseable entries and unknown roles are dropped
    rather than guessed at, because a half-understood grant is worse
    than none.
    """
    assignments = {}
    for entry in (raw or "").split(","):
        subject, _, role = entry.partition(":")
        subject, role = subject.strip(), role.strip()
        if subject and role in PERMISSIONS:
            assignments[subject] = role
    return assignments


def build_identity(env=None):
    """Select the provider from the environment, failing closed."""
    env = os.environ if env is None else env
    secret = env.get("AGENTIC_OS_JWT_SECRET") or env.get("SUPABASE_JWT_SECRET")
    jwks_url = env.get("AGENTIC_OS_JWKS_URL")
    if env.get("AGENTIC_OS_DEMO") == "1":
        # Both at once is a mistake either way round: a demo would hide the
        # sign-in a real deployment needs, or real accounts would sit
        # behind a public demo. Refuse rather than guess.
        if secret or jwks_url:
            raise AuthNotConfigured(
                "AGENTIC_OS_DEMO=1 and a sign-in provider are both set. A demo "
                "has no accounts; remove one of them.")
        return DemoIdentity()
    if secret or jwks_url:
        return JwtIdentity(
            secret=secret,
            jwks_url=jwks_url,
            audience=env.get("AGENTIC_OS_JWT_AUDIENCE"),
            issuer=env.get("AGENTIC_OS_JWT_ISSUER"),
            default_role=env.get("AGENTIC_OS_DEFAULT_ROLE", DEFAULT_ROLE),
            role_assignments=parse_role_assignments(
                env.get("AGENTIC_OS_ROLE_ASSIGNMENTS")),
            role_claims=tuple(
                c.strip() for c in env["AGENTIC_OS_ROLE_CLAIM"].split(",") if c.strip())
            if env.get("AGENTIC_OS_ROLE_CLAIM") else ROLE_CLAIMS,
        )
    # On Vercel with no shared database each instance keeps its own SQLite
    # file, so a writable single-owner site loses runs between requests
    # ("Run not found"). The view-only demo is the one mode that works
    # there unconfigured. AGENTIC_OS_DEMO=0 opts out.
    if (env.get("VERCEL") == "1" and not env.get("DATABASE_URL")
            and env.get("AGENTIC_OS_DEMO") != "0"):
        return DemoIdentity()
    production = env.get("AGENTIC_OS_ENV", "").lower() == "production"
    if production or env.get("AGENTIC_OS_REQUIRE_AUTH") == "1":
        raise AuthNotConfigured(
            "Production mode requires a managed identity provider. Set "
            "AGENTIC_OS_JWT_SECRET (or SUPABASE_JWT_SECRET) for shared-secret "
            "tokens, or AGENTIC_OS_JWKS_URL for OIDC/JWKS verification."
        )
    return LocalIdentity()


def issue_local_test_token(secret, subject, role=None, audience=None,
                           issuer=None, expires_in=3600, algorithm="HS256"):
    """Helper used by the test suite only — never called by the server."""
    import jwt

    claims = {"sub": subject, "exp": int(time.time()) + expires_in}
    if role:
        claims["agentic_os_role"] = role
    if audience:
        claims["aud"] = audience
    if issuer:
        claims["iss"] = issuer
    return jwt.encode(claims, secret, algorithm=algorithm)
