"""Explicit single-person SQLite profile, never a hosted authentication bypass.

Reuses LocalIdentity and the existing durable store. The operating-system user
is the trust boundary: other processes/users on this computer are not isolated.
"""

from ipaddress import ip_address
from urllib.parse import urlsplit

FLAG = "AGENTIC_OS_LOCAL_WORKSPACE"


def enabled(env):
    return env.get(FLAG) == "1"


def loopback(host):
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def local_url(value):
    try:
        url = urlsplit(value)
        return (url.scheme == "http" and loopback(url.hostname or "") and "%" not in (url.hostname or "")
                and url.port != 0 and not url.username and not url.password
                and not url.query and not url.fragment and url.path in ("", "/"))
    except ValueError:
        return False


def validate(env, config=None):
    """Refuse conflicts, never silently remove managed/hosted configuration."""
    if not enabled(env):
        return
    forbidden = (
        "VERCEL", "VERCEL_URL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME",
        "AWS_EXECUTION_ENV", "K_SERVICE", "WEBSITE_SITE_NAME", "RENDER",
        "FLY_APP_NAME", "RAILWAY_ENVIRONMENT", "DYNO", "NETLIFY", "CF_PAGES",
        "GAE_ENV", "RENDER_SERVICE_ID", "WEBSITE_INSTANCE_ID", "DATABASE_URL",
        "AGENTIC_OS_JWT_SECRET", "AGENTIC_OS_JWKS_URL", "AGENTIC_OS_JWT_ISSUER",
        "AGENTIC_OS_JWT_AUDIENCE", "AGENTIC_OS_ROLE_ASSIGNMENTS",
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "OLLAMA_API_KEY",
        "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "MISTRAL_API_KEY", "CEREBRAS_API_KEY",
        "AI_GATEWAY_API_KEY", "AI_GATEWAY_MODEL", "VERCEL_OIDC_TOKEN",
        "AGENTIC_OS_MODEL_FAILOVER", "AGENTIC_OS_AGENT_RUNTIME", "AGENTIC_OS_ROUTER",
        "AGENTIC_OS_VAULT_DIR", "AGENTIC_OS_PUBLISH_TARGET", "VITE_API_BASE",
    )
    if (any(env.get(name) for name in forbidden)
            or any(value for name, value in env.items() if name.startswith("SUPABASE_"))
            or env.get("AGENTIC_OS_ENV", "").lower() not in ("", "local", "development", "test")
            or env.get("AGENTIC_OS_REQUIRE_AUTH", "0") != "0"
            or env.get("AGENTIC_OS_DEMO", "0") != "0"):
        raise RuntimeError("Local workspace conflicts with hosted, managed-auth or cloud-model settings. Use a separate clean shell; existing settings were not changed.")
    if env.get("OLLAMA_HOST") and not local_url(env["OLLAMA_HOST"]):
        raise RuntimeError("Local workspace requires a loopback HTTP Ollama endpoint.")
    if (env.get("OLLAMA_MODEL", "").endswith((":cloud", "-cloud"))
            or any(value.strip() not in ("", "ollama") for value in
                   (part.partition("=")[2] for part in env.get("AGENTIC_OS_TASK_MODELS", "").split(",")))):
        raise RuntimeError("Local workspace permits only an explicitly selected local model.")
    for key in ("AGENTIC_OS_HERMES_MODEL", "AGENTIC_OS_AGENT_MODEL", "AGENTIC_OS_CONSULTANTS"):
        if any(spec.strip() not in ("", "ollama") for spec in env.get(key, "").split(",")):
            raise RuntimeError("Local workspace roles must use the selected local Ollama model without overrides.")
    if config is not None and (config.get("database_url") or config.get("agent_runtime")
                               or config.get("router")):
        raise RuntimeError("Local workspace requires SQLite without an external runtime/router.")

def verify_local_model(environment):
    """Read-only inventory check; refuse cloud aliases before any model call."""
    model = environment.get("OLLAMA_MODEL")
    if not model:
        if environment.get("OLLAMA_HOST"):
            raise RuntimeError("Choose an installed local model explicitly with OLLAMA_MODEL.")
        return
    import json
    import urllib.request
    from scripts.local_runtime import installed_local
    endpoint = (environment.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise RuntimeError("Local model inventory must not redirect.")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(endpoint + "/api/tags", timeout=3) as response:
        models = json.loads(response.read(1_000_001))
    entries = models.get("models", []) if isinstance(models, dict) else None
    if (not isinstance(entries, list) or not all(isinstance(entry, dict)
            and isinstance(entry.get("size", 0), (int, float)) for entry in entries)
            or not installed_local(entries, model)):
        raise RuntimeError("Selected Ollama model is not an installed local model; no generation was attempted.")



class LoopbackOnly:
    """Reject public bindings, DNS rebinding, cross-site and proxy requests.

    The launcher also disables uvicorn's proxy-header interpretation. This
    guard stays active if an operator imports the app through another launcher.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        raw_headers = scope.get("headers", [])
        headers = {key.lower(): value.decode("latin1") for key, value in raw_headers}
        host = headers.get(b"host", "")
        origin = headers.get(b"origin")
        peer = scope.get("client")
        server = scope.get("server")
        allowed = (sum(key.lower() == b"host" for key, _ in raw_headers) == 1
                   and sum(key.lower() == b"origin" for key, _ in raw_headers) <= 1
                   and bool(peer) and loopback(peer[0]) and bool(server) and loopback(server[0])
                   and scope.get("scheme") == "http" and local_url("http://" + host)
                   and (origin is None or origin == "http://" + host)
                   and headers.get(b"sec-fetch-site") not in ("cross-site", "same-site")
                   and not any(key == b"forwarded" or key == b"x-real-ip" or key.startswith(b"x-forwarded-")
                               for key in headers))
        if not allowed:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
                return
            from starlette.responses import JSONResponse
            arabic = headers.get(b"accept-language", "").startswith("ar")
            response = JSONResponse({"detail": (
                "مساحة العمل المحلية متاحة مباشرة على هذا الجهاز فقط." if arabic else
                "Local workspace is available directly on this computer only.")}, status_code=403,
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)
