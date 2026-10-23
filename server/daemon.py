"""Opt-in, built-in-only daemon candidate; never a migration entrypoint."""

import os
import sys
from urllib.parse import urlsplit

from server.auth import build_identity
from server.model_gateway import ModelGateway
from server.worker import main as worker_main, read_config


def validate_environment(env):
    """Reject accidental activation and unsupported ephemeral-state settings.

    This switch is an operational guard, not evidence of owner authorization.
    Credential setup, backups, migration and hosted acceptance remain separate.
    No connection or provider request is made by this validation.
    """
    if env.get("AGENTIC_OS_DAEMON_ACTIVATION") != "reviewed":
        raise ValueError("Daemon activation has not been explicitly configured.")
    try:
        target = urlsplit(env.get("DATABASE_URL", ""))
        postgres = target.scheme in {"postgres", "postgresql"} and bool(target.hostname)
    except ValueError:
        postgres = False
    if not postgres:
        raise ValueError("The daemon requires an explicit PostgreSQL DATABASE_URL.")
    if env.get("AGENTIC_OS_PUBLISH_TARGET") != "database":
        raise ValueError("Ephemeral daemons require database publication.")
    if env.get("AGENTIC_OS_RUN_EXECUTION") != "worker":
        raise ValueError("The API and daemon must explicitly use worker execution.")
    if env.get("AGENTIC_OS_REQUIRE_AUTH") != "1" or build_identity(env).mode != "jwt":
        raise ValueError("The shared deployment must require managed JWT identity.")
    if env.get("AGENTIC_OS_EVAL_INTERVAL_SECONDS", "0") not in {"", "0"}:
        raise ValueError("The filesystem evaluation ledger is not durable here.")
    if env.get("AGENTIC_OS_KNOWLEDGE_DIR"):
        raise ValueError("Filesystem knowledge is not durable; use database-backed RMD sources.")
    config = read_config(env.get("AGENTIC_OS_CONFIG"))
    if (any(p["provider"] != "deterministic" for p in ModelGateway(env).providers())
            or env.get("AI_GATEWAY_MODEL") or env.get("AGENTIC_OS_TASK_MODELS")
            or env.get("AGENTIC_OS_ROUTER") or config.get("router")):
        raise ValueError("This candidate supports built-in analytics only, not external model providers.")


def main():
    try:
        validate_environment(os.environ)
    except Exception:
        # Do not print exception contents: malformed DSNs may contain credentials.
        print("Daemon configuration rejected; check the release runbook.", file=sys.stderr)
        return 2
    return worker_main(["--poll", "15"])


if __name__ == "__main__":
    raise SystemExit(main())
