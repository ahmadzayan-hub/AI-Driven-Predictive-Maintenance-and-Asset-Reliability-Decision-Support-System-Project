"""The repository's operating system: the second brain and the session hooks.

These files run on every teammate's machine at the start and end of their
Claude Code sessions, so they are tested like product code. The hooks are
run as real processes against a throwaway git repository. The brain checker
is run against both the committed brain and a vault built to contain each
kind of fault.
"""

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS = ROOT / ".claude" / "hooks"
TODAY = dt.date(2026, 10, 16)


def load_brain_check():
    spec = importlib.util.spec_from_file_location(
        "brain_check", ROOT / "scripts" / "brain_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


brain_check = load_brain_check()


def note(path: Path, body: str, **meta):
    meta.setdefault("type", "concept")
    meta.setdefault("updated", TODAY.isoformat())
    lines = ["---"]
    for key, value in meta.items():
        if value is None:
            continue
        lines.append(f"{key}: [{', '.join(value)}]" if isinstance(value, list)
                     else f"{key}: {value}")
    lines.append("---")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n\n" + textwrap.dedent(body), encoding="utf-8")


class CommittedBrainTestCase(unittest.TestCase):
    """The brain in the repository is held to the rules it documents."""

    def setUp(self):
        self.report = brain_check.check(ROOT / "brain")

    def test_no_broken_links_fields_dates_or_sources(self):
        self.assertEqual(brain_check.structural_problems(self.report), 0,
                         brain_check.readable(self.report))

    def test_every_note_is_reachable(self):
        self.assertEqual(self.report["orphans"], [])

    def test_the_core_three_link_to_each_other_and_home_links_them(self):
        notes = {n.title: n for n in brain_check.load(ROOT / "brain")}
        core = ("User", "Identity", "Soul")
        for name in core:
            self.assertIn(name, notes)
            self.assertIn(name, notes["Home"].links)
            for other in core:
                if other != name:
                    self.assertIn(other, notes[name].links,
                                  f"{name} does not link to {other}")


class BrainCheckTestCase(unittest.TestCase):
    """Each kind of fault in a vault built to contain it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.brain = self.repo / "brain"
        (self.repo / "real.md").write_text("x", encoding="utf-8")
        note(self.brain / "Home.md", "[[Alpha]] [[Beta Note]] [[Beta Notes]] [[Old]] [[Untyped]] [[Sourced]]\n",
             type="index")
        note(self.brain / "Alpha.md",
             "Links to [[Missing note]] and [[Home]]. Mentions Beta Note without a link, "
             "and the user in passing.\n",
             aliases=["First"])
        note(self.brain / "Beta Note.md", "[[Home]] [[Alpha]]\n")
        note(self.brain / "Beta Notes.md", "[[Home]] [[Alpha]]\n")
        note(self.brain / "Old.md", "[[Home]] [[Alpha]]\n", updated="2026-01-01",
             review_every_days="30")
        note(self.brain / "Untyped.md", "[[Home]] [[Alpha]]\n", type=None)
        note(self.brain / "Sourced.md", "[[Home]] [[Alpha]]\n",
             sources=["real.md", "no/such/file.md", "https://example.com/page"])
        note(self.brain / "Lonely.md", "[[Home]] [[Alpha]]\n")
        note(self.brain / "User.md", "[[Home]] [[Alpha]]\n")
        note(self.brain / "_templates" / "Note.md", "[[Nowhere]]\n")
        self.report = brain_check.check(self.brain, TODAY)

    def tearDown(self):
        self.tmp.cleanup()

    def test_broken_links_are_found_and_templates_are_skipped(self):
        self.assertEqual(self.report["broken_links"],
                         [{"note": "Alpha", "link": "Missing note"}])

    def test_stale_notes_follow_their_own_review_period(self):
        self.assertEqual([s["note"] for s in self.report["stale"]], ["Old"])
        self.assertEqual(self.report["stale"][0]["days"], 288)

    def test_missing_fields_and_sources(self):
        self.assertEqual(self.report["missing_fields"],
                         [{"note": "Untyped", "fields": ["type"]}])
        self.assertEqual(self.report["missing_sources"],
                         [{"note": "Sourced", "source": "no/such/file.md"}])

    def test_near_identical_titles_are_duplicate_candidates(self):
        pairs = [d["notes"] for d in self.report["duplicates"]]
        self.assertIn(["Beta Note", "Beta Notes"], pairs)

    def test_an_alias_shared_with_a_title_is_a_duplicate(self):
        note(self.brain / "First.md", "[[Home]] [[Alpha]]\n")
        report = brain_check.check(self.brain, TODAY)
        self.assertTrue(any("same name or alias" in d["reason"]
                            and set(d["notes"]) == {"Alpha", "First"}
                            for d in report["duplicates"]))

    def test_unlinked_mentions_ignore_short_common_words(self):
        mentions = {(m["note"], m["mentions"]) for m in self.report["unlinked_mentions"]}
        self.assertIn(("Alpha", "Beta Note"), mentions)
        self.assertNotIn(("Alpha", "User"), mentions)

    def test_orphans_exclude_the_index(self):
        self.assertIn("Lonely", self.report["orphans"])
        self.assertNotIn("Home", self.report["orphans"])

    def test_links_resolve_by_alias_and_path(self):
        note(self.brain / "Gamma.md", "[[First]] [[Beta Note|beta]] [[Alpha#Section]]\n")
        report = brain_check.check(self.brain, TODAY)
        self.assertFalse([b for b in report["broken_links"] if b["note"] == "Gamma"])

    def test_links_inside_code_are_not_links(self):
        note(self.brain / "Code.md", "`[[Not a link]]`\n\n```\n[[Also not]]\n```\n[[Home]] [[Alpha]]\n")
        report = brain_check.check(self.brain, TODAY)
        self.assertFalse([b for b in report["broken_links"] if b["note"] == "Code"])

    def test_maintenance_is_due_until_today_is_logged(self):
        self.assertTrue(self.report["maintenance_due"])
        note(self.brain / "_meta" / "Maintenance log.md",
             "[[Home]] [[Alpha]]\n\n## 2026-10-15\n\n- x\n", type="log")
        self.assertTrue(brain_check.check(self.brain, TODAY)["maintenance_due"])
        note(self.brain / "_meta" / "Maintenance log.md",
             "[[Home]] [[Alpha]]\n\n## 2026-10-15\n\n## 2026-10-16\n", type="log")
        report = brain_check.check(self.brain, TODAY)
        self.assertFalse(report["maintenance_due"])
        self.assertEqual(report["last_maintained"], "2026-10-16")

    def test_strict_mode_fails_only_on_structural_faults(self):
        args = ["--brain", str(self.brain), "--today", TODAY.isoformat(), "--summary"]
        with open(os.devnull, "w") as sink:
            stdout, sys.stdout = sys.stdout, sink
            try:
                self.assertEqual(brain_check.main(args + ["--strict"]), 1)
                self.assertEqual(brain_check.main(args), 0)
            finally:
                sys.stdout = stdout

    def test_frontmatter_lists_in_both_styles(self):
        meta, body = brain_check.parse_frontmatter(
            "---\ntype: concept\naliases:\n  - One\n  - 'Two'\ntags: [a, b]\n---\n\nText")
        self.assertEqual(meta["aliases"], ["One", "Two"])
        self.assertEqual(meta["tags"], ["a", "b"])
        self.assertEqual(body, "Text")


class HookTestCase(unittest.TestCase):
    """The hooks as Claude Code runs them: a process, JSON on stdin."""

    SID = "abcd1234-0000-4000-8000-000000000000"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.repo),
                        GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.com",
                        GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.com")
        self.git("init", "-q")
        (self.repo / "project-progress.md").write_text(
            "# Progress\n\n## Now\n\n- Build the dataset API\n\n## Next\n\n- Later\n",
            encoding="utf-8")
        (self.repo / "session-logs.md").write_text(
            "# Session logs\n\n## 2026-10-15 · `00000000` · main\n\n- **Open / next:** ship it\n",
            encoding="utf-8")
        self.commit("start")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                              cwd=self.repo, env=self.env, capture_output=True,
                              text=True, check=True).stdout.strip()

    def commit(self, message):
        path = self.repo / f"{message.replace(' ', '_')}.txt"
        path.write_text(message, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_hook(self, script, payload):
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        done = subprocess.run([sys.executable, str(HOOKS / script)], input=stdin,
                              env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def start(self, source="startup"):
        return self.run_hook("session_start.py", {"session_id": self.SID, "source": source})

    def stop(self, **extra):
        out = self.run_hook("stop_gate.py", {"session_id": self.SID, **extra})
        return json.loads(out) if out.strip() else None

    def state(self):
        return json.loads((self.repo / ".claude" / "state" / "sessions"
                           / f"{self.SID}.json").read_text(encoding="utf-8"))

    def log(self):
        return (self.repo / "session-logs.md").read_text(encoding="utf-8")

    def test_session_start_records_the_start_and_briefs(self):
        out = self.start()
        self.assertIn("Session `abcd1234`", out)
        self.assertIn("Build the dataset API", out)
        self.assertIn("ship it", out)
        self.assertIn("session-start skill", out)
        self.assertEqual(self.state()["start_head"], self.git("rev-parse", "HEAD"))

    def test_resuming_keeps_the_original_starting_point(self):
        self.start()
        first = self.state()["start_head"]
        self.commit("work")
        self.start(source="resume")
        self.assertEqual(self.state()["start_head"], first)

    def test_a_compacted_session_gets_a_short_briefing(self):
        self.start()
        out = self.start(source="compact")
        self.assertNotIn("ship it", out)
        self.assertIn("compacted", out)

    def test_stop_is_allowed_when_nothing_was_committed(self):
        self.start()
        self.assertIsNone(self.stop())

    def test_stop_blocks_once_after_unlogged_commits(self):
        self.start()
        self.commit("feature")
        decision = self.stop()
        self.assertEqual(decision["decision"], "block")
        self.assertIn("1 commit(s)", decision["reason"])
        self.assertIn("session-end skill", decision["reason"])
        self.assertIsNone(self.stop(), "the gate must fire only once")

    def test_stop_never_blocks_while_a_stop_hook_is_active(self):
        self.start()
        self.commit("feature")
        self.assertIsNone(self.stop(stop_hook_active=True))

    def test_stop_is_allowed_once_the_session_is_logged(self):
        self.start()
        self.commit("feature")
        with (self.repo / "session-logs.md").open("a", encoding="utf-8") as handle:
            handle.write("\n## 2026-10-16 · `abcd1234` · main\n\n- **Done:** feature\n")
        self.assertIsNone(self.stop())

    def test_a_session_unknown_to_the_hooks_is_left_alone(self):
        self.commit("feature")
        self.assertIsNone(self.stop())
        before = self.log()
        self.run_hook("session_end.py", {"session_id": self.SID, "reason": "other"})
        self.assertEqual(self.log(), before)

    def test_session_end_appends_one_factual_entry(self):
        self.start()
        self.commit("feature one")
        sha = self.git("rev-parse", "--short", "HEAD")
        self.run_hook("session_end.py", {"session_id": self.SID, "reason": "prompt_input_exit"})
        log = self.log()
        self.assertIn("`abcd1234`", log)
        self.assertIn("(automatic)", log)
        self.assertIn(sha, log)
        self.assertIn("feature one", log)
        self.run_hook("session_end.py", {"session_id": self.SID, "reason": "other"})
        self.assertEqual(self.log().count("`abcd1234`"), 1)

    def test_session_end_leaves_a_logged_or_idle_session_alone(self):
        self.start()
        before = self.log()
        self.run_hook("session_end.py", {"session_id": self.SID, "reason": "other"})
        self.assertEqual(self.log(), before)

    def test_hooks_fail_open_on_bad_input(self):
        for script in ("session_start.py", "stop_gate.py", "session_end.py"):
            self.run_hook(script, "not json at all")

    def test_a_hostile_session_id_cannot_leave_the_state_folder(self):
        self.run_hook("session_start.py", {"session_id": "../../escape", "source": "startup"})
        self.assertFalse((self.repo / "escape.json").exists())
        self.assertFalse((self.repo / ".claude" / "escape.json").exists())
        self.assertTrue((self.repo / ".claude" / "state" / "sessions" / "escape.json").exists())


class SettingsTestCase(unittest.TestCase):
    def test_settings_wire_each_hook_to_a_script_that_exists(self):
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        for event, script in (("SessionStart", "session_start.py"),
                              ("Stop", "stop_gate.py"),
                              ("SessionEnd", "session_end.py")):
            commands = [h["command"] for entry in settings["hooks"][event]
                        for h in entry["hooks"]]
            self.assertTrue(any(script in c for c in commands), event)
            self.assertTrue((HOOKS / script).exists(), script)

    def test_session_end_has_a_budget_above_the_default(self):
        """SessionEnd hooks get 1.5 s unless a hook sets its own timeout."""
        settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        timeouts = [h.get("timeout", 0) for entry in settings["hooks"]["SessionEnd"]
                    for h in entry["hooks"]]
        self.assertTrue(all(t >= 5 for t in timeouts))

    def test_commands_and_agents_folders_hold_no_stray_markdown(self):
        """Every .md in commands/ becomes a slash command, so notes must not live there."""
        for folder in ("commands", "agents"):
            for path in (ROOT / ".claude" / folder).glob("*.md"):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith("---\n"), f"{path.name} has no frontmatter")


if __name__ == "__main__":
    unittest.main()
