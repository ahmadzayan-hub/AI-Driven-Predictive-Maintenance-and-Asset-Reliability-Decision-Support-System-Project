"""Run the repository verifier, retaining each step's full output for review."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import verify

original = verify.run


def logged_run(step):
    result = original(step)
    (Path(__file__).parent / (step.name.lower().replace(' ', '-') + '.txt')).write_text(
        result[2], encoding='utf-8')
    return result


verify.run = logged_run
raise SystemExit(verify.main())
