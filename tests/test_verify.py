"""Tests for scripts/verify.py, the one command that runs every check."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import verify  # noqa: E402


class SummaryTests(unittest.TestCase):
    def test_unittest_counts_and_skips(self):
        output = "....s..\n----\nRan 705 tests in 51.2s\n\nOK (skipped=16)\n"
        self.assertEqual(verify.summarise_unittest(output), "705 tests, 16 skipped")
        self.assertEqual(verify.summarise_unittest("Ran 1 test in 0.1s\n\nOK\n"), "1 tests")
        self.assertEqual(verify.summarise_unittest("ImportError: no module"), "")

    def test_vitest_line_is_read_through_colour_codes(self):
        output = (" \x1b[2m Test Files \x1b[22m \x1b[1m\x1b[32m9 passed\x1b[39m\x1b[22m (9)\n"
                  "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m54 passed\x1b[39m\x1b[22m (54)\n")
        self.assertEqual(verify.summarise_vitest(output), "54 passed (54)")

    def test_playwright_totals(self):
        output = "  ✓ 1 [desktop] › overview.spec.ts\n\n  3 skipped\n  63 passed (1.6m)\n"
        self.assertEqual(verify.summarise_playwright(output), "3 skipped, 63 passed")

    def test_brain_line(self):
        output = "Brain: 23 notes · 0 broken links\nOK\n"
        self.assertEqual(verify.summarise_brain(output), "23 notes · 0 broken links")


class BudgetTests(unittest.TestCase):
    def build(self, js_bytes, font_bytes):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        dist = Path(temp.name)
        (dist / "assets").mkdir()
        # Random-looking text barely compresses, so its size is predictable.
        import random
        rng = random.Random(7)
        (dist / "assets" / "index-a1.js").write_text(
            "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(js_bytes)))
        (dist / "assets" / "index-a1.css").write_text("body{margin:0}" * 10)
        (dist / "assets" / "font-400.woff2").write_bytes(b"\0" * font_bytes)
        (dist / "assets" / "font-400.woff").write_bytes(b"\0" * 500_000)  # never counted
        return dist

    def test_a_build_inside_the_budget_passes(self):
        ok, summary = verify.check_budget(self.build(20_000, 50_000))
        self.assertTrue(ok, summary)
        self.assertIn("fonts 50.0 of 120 KB", summary)

    def test_a_build_over_the_budget_fails_and_names_what(self):
        ok, summary = verify.check_budget(self.build(200_000, 50_000))
        self.assertFalse(ok)
        self.assertIn("over: js", summary)

    def test_no_build_is_a_failure_not_a_pass(self):
        with tempfile.TemporaryDirectory() as empty:
            ok, summary = verify.check_budget(Path(empty))
        self.assertFalse(ok)
        self.assertIn("no build", summary)


class StepTests(unittest.TestCase):
    def names(self, group):
        return [s.name for s in verify.steps() if group in s.groups]

    def test_quick_skips_the_build_and_the_browser(self):
        quick = self.names("quick")
        self.assertIn("Python tests", quick)
        self.assertNotIn("Production build", quick)
        self.assertNotIn("End-to-end tests", quick)

    def test_the_default_runs_what_ci_runs_without_a_browser(self):
        full = self.names("full")
        for name in ("Python tests", "Brain check", "Type check", "Frontend unit tests",
                     "Production build", "Interface budget"):
            self.assertIn(name, full)
        self.assertNotIn("End-to-end tests", full)
        # The budget is measured after the build that produces it.
        self.assertLess(full.index("Production build"), full.index("Interface budget"))

    def test_list_runs_nothing(self):
        with mock.patch.object(verify.subprocess, "run", side_effect=AssertionError("ran")):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(verify.main(["--e2e", "--list"]), 0)
        self.assertIn("End-to-end tests", out.getvalue())

    def test_a_failing_step_fails_the_run(self):
        failing = verify.Step("Python tests", [sys.executable, "-c", "raise SystemExit(3)"],
                              groups={"quick"})
        with mock.patch.object(verify, "steps", return_value=[failing]):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(verify.main(["--quick"]), 1)
        self.assertIn("FAIL Python tests", out.getvalue())
        self.assertIn("1 of 1 steps failed", out.getvalue())


if __name__ == "__main__":
    unittest.main()
