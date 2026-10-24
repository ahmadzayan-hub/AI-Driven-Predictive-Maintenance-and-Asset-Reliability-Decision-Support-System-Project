#!/usr/bin/env python3
"""Start or back up the explicit, credential-free single-person Miyaar workspace.

No packages/models are installed, no accounts are created and no cloud settings
are changed. The app uses its existing LocalIdentity and SQLite backend.
"""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from server.local_workspace import FLAG, validate, verify_local_model
from server.backup import create_backup, restore_backup
from server.storage import open_store
from utils import load_config

DEFAULT_WORKSPACE = Path.home() / ".miyaar" / "workspace"


def workspace_config(directory):
    """One isolated directory, reused on restart; never reuse hosted settings."""
    directory = directory.expanduser().resolve()
    path = directory / "config.json"
    if path.exists():
        config = load_config(path)
        expected = {"database_file": str(directory / "agentic.db"),
                    "memory_file": str(directory / "memory.json"),
                    "vault_dir": str(directory / "vault")}
        if config.get("local_workspace_version") != 1 or any(config.get(k) != v for k, v in expected.items()):
            raise RuntimeError("Workspace configuration is not an isolated local profile; no files were changed.")
        validate({FLAG: "1"}, config)
        return path, config
    # Missing config beside a database is not a new installation.
    if directory.exists() and any(directory.iterdir()):
        raise RuntimeError("Choose an empty workspace directory; existing data was not changed.")
    config = load_config(ROOT / "config.json")
    config.update({"local_workspace_version": 1,
                   "database_file": str(directory / "agentic.db"),
                   "memory_file": str(directory / "memory.json"),
                   "vault_dir": str(directory / "vault")})
    validate({FLAG: "1"}, config)
    directory.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(config, output, indent=2)
    return path, config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("start", "backup", "restore"))
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE,
                        help="isolated durable directory; reuse this path on restart")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--out", type=Path, help="new backup JSON file (never overwritten)")
    parser.add_argument("--from-backup", type=Path, help="restore into a new empty workspace only")
    args = parser.parse_args(argv)
    # Opt-in is process-local. Refuse, rather than disable, REQUIRE_AUTH or
    # any existing managed provider/cloud configuration.
    environment = dict(os.environ, **{FLAG: "1"})
    validate(environment)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    if args.command == "start" and not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Build the interface first: npm --prefix frontend ci && npm --prefix frontend run build")
    if args.command == "backup" and (not args.out or not (args.workspace.expanduser() / "config.json").is_file()):
        parser.error("backup requires an existing workspace and --out pointing to a new file")
    if args.command == "restore":
        if not args.from_backup:
            parser.error("restore requires --from-backup")
        if args.workspace.expanduser().exists() and any(args.workspace.expanduser().iterdir()):
            raise RuntimeError("Restore requires a new empty workspace; the existing workspace was not changed.")
        payload = json.loads(args.from_backup.read_text(encoding="utf-8"))
    if args.command == "start":
        verify_local_model(environment)
    path, config = workspace_config(args.workspace)
    if args.command == "backup" and not Path(config["database_file"]).is_file():
        raise RuntimeError("Workspace database is missing; no empty replacement or backup was created.")
    if args.command in ("backup", "restore"):
        with closing(open_store(sqlite_path=config["database_file"], allow_temporary_fallback=False)) as store:
            if args.command == "backup":
                with store.atomic("local-workspace-backup"):
                    snapshot = create_backup(store)
                with args.out.expanduser().open("x", encoding="utf-8") as output:
                    json.dump(snapshot, output, ensure_ascii=False)
                print("Backup saved. Keep it private; it contains your workspace data.")
            else:
                restore_backup(store, payload)
                print("Restored into the new workspace. Start it with the same --workspace path.")
        return 0
    environment["AGENTIC_OS_CONFIG"] = str(path)
    environment["AGENTIC_OS_RUN_EXECUTION"] = "client"
    environment["AGENTIC_OS_RATE_LIMIT_STORE"] = "1"
    os.environ.update(environment)
    os.chdir(ROOT)
    print(f"Miyaar: http://127.0.0.1:{args.port} | معيار: على هذا الجهاز فقط", flush=True)
    print("Local owner, no password. Other users/processes on this computer are trusted.\n"
          "مالك محلي بلا كلمة مرور. يُفترض أن مستخدمي هذا الجهاز وبرامجه موثوقون.", flush=True)
    print("No model is installed or started. Select an installed local Ollama model explicitly for AI.\n"
          "لا يُثبَّت أو يُشغَّل أي نموذج. اختر نموذج Ollama محليًا مثبتًا لتفعيل الذكاء الاصطناعي.", flush=True)
    import uvicorn
    uvicorn.run("server.app:app", host="127.0.0.1", port=args.port,
                proxy_headers=False, forwarded_allow_ips="", log_level="warning")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError):
        # Do not echo configuration values, paths from archives or environment
        # secrets in command logs. Actionable setup is in the local guide.
        print("Local workspace refused to start or change data. Check the local-workspace guide and use a clean shell.\n"
              "تعذر تشغيل مساحة العمل المحلية أو تعديلها. راجع الدليل واستخدم جلسة أوامر نظيفة.", file=sys.stderr)
        raise SystemExit(2)
