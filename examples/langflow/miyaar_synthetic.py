"""Opt-in, temporary synthetic Miyaar MCP example for Langflow. / مثال معياري مؤقت."""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ["help", "run_status", "explain_report"]
REFUSED = "Synthetic example refused. / رُفض تشغيل المثال الاصطناعي."


def deny_external_effects(event, args):
    """Process-only Python audit guard, not an OS sandbox or hostile-code boundary."""
    if (event.startswith("socket.") or event.startswith("subprocess.")
            or event in {"os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty"}):
        raise PermissionError(REFUSED)


def configuration(language):
    return {"mcpServers": {f"miyaar-synthetic-{language}": {
        "command": str(Path(sys.executable).absolute()),
        "args": ["-I", "-B", "-X", "utf8", str(Path(__file__).resolve()),
                 "--serve-synthetic", "--language", language], "env": {}}}}


@contextmanager
def synthetic_server(language):
    """Own and close all temporary state; never approve or publish the sample."""
    from scripts.hermes_mcp import build
    from server.analytics import sample_dataset
    from server.mcp import RpcError

    with tempfile.TemporaryDirectory(prefix="miyaar-synthetic-") as directory:
        root = Path(directory)
        scope = {"scope": "miyaar-local-workspace-v1", "language": language,
                 "enabled_tools": TOOLS,
                 "database_file": str(root / "sample.db"),
                 "memory_file": str(root / "memory.json"),
                 "vault_dir": str(root / "vault"),
                 "knowledge_dir": str(root / "knowledge")}
        with build(scope) as server:
            engine = server.assistant.engine
            run = engine.create_run(
                "Fictional sample analysis" if language == "en" else "تحليل عينة اصطناعية",
                dataset_text=sample_dataset(language), language=language,
                owner=server.session.owner)
            # One advance per built-in task, plus one fail-closed state check.
            for _ in range(len(run["tasks"]) + 1):
                if run["state"] == "awaiting_approval":
                    break
                run = engine.advance(run["id"])
            if run["state"] != "awaiting_approval":
                raise RuntimeError(REFUSED)
            server.name = f"miyaar-synthetic-{language}"
            server.instructions = (
                "Synthetic English example: fictional sample only; no real workspace is connected. "
                "Only help, run_status and explain_report are available. The report is unapproved; "
                "this example cannot approve or publish it. State is deleted on normal exit."
                if language == "en" else
                "مثال اصطناعي بالعربية: عينة خيالية فقط، ولا توجد مساحة عمل حقيقية متصلة. "
                "المتاح فقط هو help وrun_status وexplain_report. التقرير غير معتمد؛ "
                "لا يمكن لهذا المثال اعتماده أو نشره. تُحذف البيانات عند الخروج الطبيعي."
            )
            dispatch = server._dispatch

            def safe_dispatch(method, params):
                try:
                    return dispatch(method, params)
                except RpcError:
                    raise
                except Exception:
                    # Avoid the core transport's exception-detail logging/echo.
                    raise RpcError(-32603, REFUSED) from None

            server._dispatch = safe_dispatch
            yield server


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, REFUSED + "\n")


def main(argv=None):
    parser = SafeParser(description=__doc__, allow_abbrev=False)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--print-config", action="store_true", help="Print config only / عرض الإعداد فقط")
    action.add_argument("--serve-synthetic", action="store_true", help="Serve fictional sample / تشغيل عينة خيالية")
    parser.add_argument("--language", choices=("en", "ar"), default="en")
    args = parser.parse_args(argv)
    if args.print_config:
        print(json.dumps(configuration(args.language), ensure_ascii=False))
        return 0
    if not args.serve_synthetic:
        parser.print_help()
        return 0
    retained = {key: value for key, value in os.environ.items()
                if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP"}}
    os.environ.clear()
    os.environ.update(retained)
    try:
        sys.addaudithook(deny_external_effects)
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(ROOT))
        with synthetic_server(args.language) as server:
            server.serve()
    except Exception:
        print(REFUSED, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
