#!/usr/bin/env python3
"""Read MaintainX into a private, atomic snapshot. No remote mutations."""
import argparse
import json
import os
import sys
import tempfile
from contextlib import contextmanager, ExitStack
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server.connectors import ConnectorError
from server.maintainx import MaintainXError, asset_import, synchronize


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".new", delete=False) as output:
            temporary = Path(output.name)
            json.dump(value, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def snapshot_lock(path):
    """Exclusive local admission across read, network sync and replacement.

    Never steal a stale lock: after a crash an operator must verify that its
    PID is no longer running before removing it. Atomic-create works on Windows.
    """
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise MaintainXError("A snapshot sync is already running or its lock needs operator review.") from None
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def sync_file(args, synchronizer=synchronize):
    # Lock both outputs in stable order; different snapshots may share an import
    # destination. Do not let either overwrite a concurrent operator's result.
    paths = {args.output.resolve()}
    if args.import_output:
        paths.add(args.import_output.resolve())
    with ExitStack() as stack:
        for path in sorted(paths):
            stack.enter_context(snapshot_lock(path))
        previous = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else None
        snapshot = synchronizer(args.kind, args.owner, args.credential, previous, env=os.environ)
        payload = asset_import(snapshot, args.site_id, "maintainx:" + snapshot["checked_at"], args.location_id,
                               [x.strip() for x in args.asset_ids.split(",")], args.criticality) if args.site_id else None
        write_json(args.output, snapshot)
        if payload:
            write_json(args.import_output, payload)
        return snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("assets", "workorders"))
    parser.add_argument("--owner", required=True, help="Managed identity subject authorized by the credential registry")
    parser.add_argument("--credential", required=True, help="Operator-held credential alias, never a token")
    parser.add_argument("--output", required=True, type=Path, help="Private snapshot file outside tracked data")
    parser.add_argument("--site-id", help="Explicit reviewed site for a separate initial asset-import payload")
    parser.add_argument("--import-output", type=Path)
    parser.add_argument("--location-id", type=int, help="Reviewed MaintainX location ID")
    parser.add_argument("--asset-ids", help="Comma-separated reviewed MaintainX asset IDs")
    parser.add_argument("--criticality", choices=("low", "medium", "high", "critical"))
    args = parser.parse_args(argv)
    if bool(args.site_id) != bool(args.import_output) or (args.site_id and args.kind != "assets"):
        parser.error("--site-id and --import-output must be supplied together for an asset snapshot")
    if args.import_output and args.output.resolve() == args.import_output.resolve():
        parser.error("The snapshot and import payload must use different paths")
    if args.import_output and not (args.location_id and args.asset_ids and args.criticality):
        parser.error("An import requires --location-id, --asset-ids and an explicitly reviewed --criticality")
    try:
        snapshot = sync_file(args)
        print(json.dumps({"status": "snapshot_saved", "records": len(snapshot["records"]),
                          "pages": snapshot["pages"], "watermark": snapshot["watermark"]}))
        return 0
    except ConnectorError as error:
        print(error.message("en"), file=sys.stderr)
    except (MaintainXError, OSError, ValueError) as error:
        # OS paths, response bodies and secrets never enter the printed error.
        print(str(error) if isinstance(error, MaintainXError) else "The private snapshot could not be read or saved.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
