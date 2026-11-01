"""Storage-only skill package checks; no Hermes execution or network calls."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "docs/hermes-reviewed-skills"


class ReviewedHermesSkillsTests(unittest.TestCase):
    def test_manifest_exact_and_hashes_match(self):
        manifest = json.loads((ROOT / "CHECKSUMS.json").read_text())
        files = {str(p.relative_to(ROOT)): p for p in ROOT.rglob("*") if p.is_file() and p.name != "CHECKSUMS.json"}
        self.assertEqual(set(files), set(manifest))
        for name, path in files.items():
            self.assertFalse(path.is_symlink())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), manifest[name])

    def test_portable_text_only_metadata_and_licenses(self):
        skills = sorted((ROOT / "skills").iterdir())
        self.assertEqual([p.name for p in skills], ["zaian-editorial-qa", "zaian-private-reference-pack"])
        for folder in skills:
            text = (folder / "SKILL.md").read_text(encoding="utf-8")
            front = text.split("---", 2)[1]
            fields = dict(line.split(":", 1) for line in front.strip().splitlines())
            self.assertEqual(set(fields), {"name", "description", "version", "license"})
            self.assertEqual(fields["name"].strip(), folder.name)
            self.assertIn("explicit request", fields["description"])
            self.assertEqual(fields["license"].strip(), "MIT")
            self.assertNotIn("!`", text)
            for path in folder.iterdir():
                self.assertTrue(path.is_file())
                self.assertIn(path.suffix, {".md", ".txt"})
            licenses = list(folder.glob("LICENSE*.txt"))
            self.assertTrue(licenses)
            for path in licenses:
                self.assertIn("MIT License", path.read_text())
                self.assertIn("Copyright (c)", path.read_text())

    def test_relative_readme_links_resolve(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" not in target:
                self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()
