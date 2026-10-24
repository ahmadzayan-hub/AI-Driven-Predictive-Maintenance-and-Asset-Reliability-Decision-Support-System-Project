"""The development DOM runtime must not regress to the affected undici range."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UndiciAuditFloorTests(unittest.TestCase):
    def test_locked_dom_dependency_is_above_the_reviewed_security_floor(self):
        lock = json.loads((ROOT / "frontend/package-lock.json").read_text())
        dep = lock["packages"]["node_modules/undici"]
        version = tuple(int(part) for part in dep["version"].split("."))
        self.assertGreaterEqual(version, (8, 12, 2))
        self.assertEqual(dep["resolved"], f"https://registry.npmjs.org/undici/-/undici-{dep['version']}.tgz")
        self.assertTrue(dep["integrity"].startswith("sha512-"))

    def test_http_client_remains_a_development_dependency(self):
        manifest = json.loads((ROOT / "frontend/package.json").read_text())
        lock = json.loads((ROOT / "frontend/package-lock.json").read_text())
        self.assertNotIn("undici", manifest["dependencies"])
        self.assertIs(lock["packages"]["node_modules/undici"]["dev"], True)


if __name__ == "__main__":
    unittest.main()
