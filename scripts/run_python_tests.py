#!/usr/bin/env python3
"""Run the Python suite in parallel, safely, and report it as unittest does.

    python scripts/run_python_tests.py            # one worker per CPU
    python scripts/run_python_tests.py --jobs 1   # everything in one process

The suite takes minutes in one process and most of it waits on nothing but
the CPU. Test files go on a queue, largest first, and each worker takes the
next batch and runs it as an ordinary `python -m unittest` process, so a
test sees exactly what it sees under `discover`.

PostgreSQL. The PostgreSQL tests drop and recreate the tables of the test
database, so two workers must never share one. With PG_TEST_URL set, worker
1 uses that database and every other worker its own copy, named after it
(`agentic_test_w2`, ...), created when missing. The files that create roles,
which belong to the whole server rather than to one database, run together
in one batch so they never overlap. When a copy cannot be created, the
PostgreSQL files fall back to one batch run by one worker, as safe as the
serial run.

The output ends with one combined "Ran N tests" line and "OK" or
"FAILED (...)", which is what scripts/verify.py reads; a failed batch's own
output is printed in full above it. The exit code is 1 when any batch fails.
Standard library, plus psycopg2 only to create the database copies.
"""

import argparse
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
POSTGRES = re.compile(r"PG_TEST_URL|psycopg2")
# Files that create or drop roles: server-wide objects, so never concurrent.
ROLES = re.compile(r"CREATE ROLE|DROP ROLE", re.I)
RAN = re.compile(r"^Ran (\d+) tests? in", re.M)
# unittest's result line; a warning printed after it must not hide it.
STATUS = re.compile(r"^(?:OK|FAILED)(?: \((.*)\))?$", re.M)
COUNTS = re.compile(r"(failures|errors|skipped|expected failures|unexpected successes)=(\d+)")
# A PostgreSQL file waits on the database more than on the CPU; weigh it so
# the queue starts the slow files first.
POSTGRES_WEIGHT = 4
BATCH = 3


def database_copies(url, workers):
    """One database URL per worker: the given one, then copies made from
    its name. None when a copy cannot be made."""
    if not url or workers < 2:
        return [url] * workers
    parts = urlsplit(url)
    name = parts.path.lstrip("/")
    names = [name] + [f"{name}_w{i}" for i in range(2, workers + 1)]
    try:
        import psycopg2
        conn = psycopg2.connect(url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            for copy in names[1:]:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (copy,))
                if cursor.fetchone() is None:
                    cursor.execute(f'CREATE DATABASE "{copy}"')
        conn.close()
        urls = [urlunsplit(parts._replace(path="/" + n)) for n in names]
        # A copy can exist and still refuse this user (a server that trusts
        # only the original database): check each before relying on it.
        for copy in urls[1:]:
            psycopg2.connect(copy, connect_timeout=3).close()
    except Exception as error:  # no driver, no right, no access: run safely
        print(f"note: PostgreSQL copies not available ({error.__class__.__name__}); "
              "its tests run in one batch")
        return None
    return urls


def plan(files, isolated):
    """Batches, heaviest first. Role files are always one batch; without
    isolated databases every PostgreSQL file is."""
    texts = {f: f.read_text(encoding="utf-8") for f in files}
    pinned = [f for f in files if ROLES.search(texts[f])]
    if not isolated:
        pinned = [f for f in files if POSTGRES.search(texts[f])]
    weight = {f: f.stat().st_size * (POSTGRES_WEIGHT if POSTGRES.search(texts[f]) else 1)
              for f in files}
    rest = sorted((f for f in files if f not in pinned), key=weight.get, reverse=True)
    batches = [rest[i:i + BATCH] for i in range(0, len(rest), BATCH)]
    if pinned:
        batches.append(pinned)
    return sorted(batches, key=lambda b: sum(weight[f] for f in b), reverse=True)


def run(batch, env):
    modules = [f"tests.{f.stem}" for f in batch]
    started = time.monotonic()
    done = subprocess.run([sys.executable, "-m", "unittest", *modules], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return done.returncode, done.stdout + done.stderr, time.monotonic() - started


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                        help="how many workers run at once (default: one per CPU)")
    args = parser.parse_args(argv)
    started = time.monotonic()
    files = sorted(TESTS.glob("test_*.py"))
    workers = max(1, args.jobs)
    urls = database_copies(os.environ.get("PG_TEST_URL"), workers)
    isolated = urls is not None
    urls = urls or [os.environ.get("PG_TEST_URL")] * workers
    work = queue.Queue()
    for batch in plan(files, isolated):
        work.put(batch)
    results, lock = [], threading.Lock()

    def worker(url):
        env = dict(os.environ)
        if url:
            env["PG_TEST_URL"] = url
        while True:
            try:
                batch = work.get_nowait()
            except queue.Empty:
                return
            outcome = run(batch, env)
            with lock:
                results.append((batch, *outcome))

    threads = [threading.Thread(target=worker, args=(url,)) for url in urls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    total, counts, failed = 0, {}, False
    for batch, code, output, took in results:
        ran = RAN.findall(output)
        total += int(ran[-1]) if ran else 0
        status = STATUS.findall(output)
        for name, n in COUNTS.findall(status[-1] if status else ""):
            counts[name] = counts.get(name, 0) + int(n)
        if code != 0 or not ran:
            failed = True
            print(f"--- batch failed ({', '.join(f.stem for f in batch)}) ---")
            print(output)
    seconds = time.monotonic() - started
    slowest = max(results, key=lambda r: r[3]) if results else None
    print("-" * 70)
    print(f"Ran {total} tests in {seconds:.3f}s "
          f"({len(results)} batches on {workers} workers"
          f"{', a database each' if isolated and urls[0] else ''}"
          + (f"; slowest {slowest[3]:.0f}s: {', '.join(f.stem for f in slowest[0])}" if slowest else "")
          + ")")
    print()
    detail = ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    if failed:
        print(f"FAILED ({detail})" if detail else "FAILED")
        return 1
    print(f"OK ({detail})" if detail else "OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
