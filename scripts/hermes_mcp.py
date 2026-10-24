"""Miyaar's existing MCP transport, with an explicit local-workspace scope.

No arguments: help-only preview, no storage or model provider. --config names
an operator-reviewed local configuration; no website config is auto-discovered.
This is a stdio process, not an HTTP server or a replacement for the website.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
PATH_FIELDS = ("database_file", "memory_file", "vault_dir", "knowledge_dir")
WORKSPACE_TOOLS = frozenset({"help", "run_status", "explain_report"})
PREVIEW = (
    "Miyaar preview: only help is enabled. No workspace is connected. "
    "Review docs/HERMES_DESKTOP.md before granting storage or tool access. "
    "معاينة معيار: المساعدة فقط متاحة، ولا توجد مساحة عمل متصلة. "
    "راجع دليل Hermes قبل منح صلاحيات البيانات أو الأدوات."
)


def check_tools(enabled):
    """This first package accepts only the reviewed report-reading subset."""
    if (not isinstance(enabled, list) or not enabled
            or not all(isinstance(name, str) for name in enabled)):
        raise ValueError("enabled_tools must be a nonempty explicit list")
    if not set(enabled) <= WORKSPACE_TOOLS:
        raise ValueError("this package permits only help, run_status and explain_report")
    return enabled


def read_scope(path):
    """Validate the whole opt-in before importing application code/opening data."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    permitted = {*PATH_FIELDS, "enabled_tools", "scope", "language"}
    if not isinstance(config, dict) or set(config) - permitted:
        raise ValueError("unsupported configuration fields")
    if config.get("scope") != "miyaar-local-workspace-v1":
        raise ValueError("an explicit local workspace scope is required")
    for field in PATH_FIELDS:
        value = config.get(field)
        if (not isinstance(value, str) or not value.strip()
                or value.startswith(("\\\\", "//")) or not Path(value).is_absolute()
                or "${" in value or "<" in value or ">" in value):
            raise ValueError(f"{field} must be an approved absolute local path")
        config[field] = str(Path(value).resolve())
    if config.get("language", "en") not in ("en", "ar"):
        raise ValueError("language must be en or ar")
    check_tools(config.get("enabled_tools"))
    return config


@contextmanager
def build(scope=None):
    enabled = check_tools(["help"] if scope is None else scope.get("enabled_tools"))
    # Deliberately do not import server.app: it creates its default app/store
    # at import time. Reuse the same core Assistant, ToolBox and MCP transport.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from agent import Agent
    from server.assistant import Assistant
    from server.mcp import McpServer
    from server.model_gateway import ModelGateway
    config = {"agent_name": "Miyaar", "version": "0.1.0",
              "preferences": {"language": "Arabic" if scope and scope.get("language") == "ar" else "English"}}
    store = None
    engine = None
    gateway = ModelGateway(env={})
    env = {}
    try:
        if scope is not None:
            from server.storage import open_store
            from server.runs import RunEngine
            # Agent loads this file even though recall is not exposed. Approval
            # must cover that startup read, not just the selected MCP tools.
            config["memory_file"] = scope["memory_file"]
            env["AGENTIC_OS_KNOWLEDGE_DIR"] = scope["knowledge_dir"]
            # Opening the existing store initializes/migrates schema and WAL;
            # a read-tools allowlist does not make this a read-only DB connection.
            store = open_store(None, scope["database_file"], allow_temporary_fallback=False)
            engine = RunEngine(store, scope["vault_dir"], gateway,
                               glossary={"metrics": [], "problems": []},
                               publish_target="vault", stage_timeout=120)
        session = SimpleNamespace(agent=Agent(config), owner="local-owner",
                                  id="miyaar-mcp", transcript=[])
        instructions = PREVIEW if scope is None else (
            "Miyaar local workspace. Only the listed tools are approved. "
            "Report publication requires separate human approval in the web app. "
            "مساحة معيار المحلية: الأدوات المدرجة فقط معتمدة. "
            "نشر التقرير يحتاج موافقة بشرية منفصلة في تطبيق الويب."
        )
        yield McpServer(Assistant(gateway, engine, env=env), session,
                        name="miyaar", version="0.1.0", allowed_tools=enabled,
                        instructions=instructions)
    finally:
        if store is not None:
            store.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--config", help="explicit reviewed local scope JSON")
    args = parser.parse_args(argv)
    # Child-process-only isolation. No Hermes/profile/environment file is edited.
    # Do not inherit provider credentials, database URLs, runtime plugins or
    # application paths. Python -I also prevents ambient Python path injection.
    retained = {key: value for key, value in os.environ.items()
                if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}}
    os.environ.clear()
    os.environ.update(retained)
    try:
        scope = read_scope(args.config) if args.config else None
        with build(scope) as server:
            server.serve()
    except (OSError, ValueError):
        # Do not echo configuration contents, paths or underlying DB errors.
        print("Miyaar configuration refused; review the local scope file. / "
              "رُفض إعداد معيار؛ راجع ملف النطاق المحلي.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
