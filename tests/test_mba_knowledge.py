"""Reviewed reference lookup and publication-boundary regression checks.

No project rows, provider calls or model execution. Lookup examples are not a
general retrieval benchmark. API checks use temporary local storage only.
"""
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from server import knowledge

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "knowledge" / "mba-analytics"
COLLECTION = "mba-analytics-reference"


class ReviewedKnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.private = Path(self.tmp.name) / "private"
        self.principal = SimpleNamespace(subject="reader", provider="test", can=lambda _: True)

    def fixture(self, root, name, collection_id=None):
        folder = root / name
        folder.mkdir(parents=True)
        (folder / "note.md").write_text("# Synthetic\n\nPrivate canary evidence.\n", encoding="utf-8")
        (folder / "collection.json").write_text(json.dumps({
            "collection_id": collection_id or name, "owner": "other",
            "data_classification": "private"}), encoding="utf-8")

    def default_store(self):
        with patch.object(knowledge, "DEFAULT_ROOT", self.private):
            return knowledge.load(env={})

    def test_default_load_keeps_public_and_private_access_separate(self):
        self.fixture(self.private, "private-example")
        loaded = self.default_store()
        self.assertIn("private-example", loaded.collections)
        scoped = loaded.for_principal(self.principal)
        self.assertEqual(set(scoped.collections), {COLLECTION})
        self.assertNotIn("canary", json.dumps(scoped.describe()))
        self.assertFalse(scoped.for_principal(None))

    def test_explicit_missing_or_empty_root_does_not_add_bundled_content(self):
        for root in (self.private, Path(self.tmp.name)):
            self.assertFalse(knowledge.load(root))
            self.assertFalse(knowledge.load(env={"AGENTIC_OS_KNOWLEDGE_DIR": str(root)}))

    def test_explicit_path_takes_precedence_over_environment(self):
        self.fixture(self.private, "selected")
        loaded = knowledge.load(self.private, env={"AGENTIC_OS_KNOWLEDGE_DIR": str(ROOT / "knowledge")})
        self.assertEqual(set(loaded.collections), {"selected"})

    def test_private_collision_cannot_replace_reviewed_bundled_identity(self):
        self.fixture(self.private, "shadow", COLLECTION)
        loaded = self.default_store()
        self.assertEqual(loaded.collections[COLLECTION].root, CORPUS)
        self.assertNotIn("canary", " ".join(p.text for p in loaded.collections[COLLECTION].passages))

    def test_reference_is_readable_but_never_model_context(self):
        loaded = self.default_store()
        self.assertTrue(loaded.for_principal(self.principal))
        self.assertFalse(loaded.for_principal(self.principal, for_model=True))

    def test_english_and_arabic_lookup_cite_reviewed_sources(self):
        loaded = self.default_store()
        examples = (("leakage controls", "04_VALIDATION_UNCERTAINTY.md"),
                    ("أنواع التحليلات", "01_ANALYTICS_TYPES.md"),
                    ("independent comparison", "08_INDEPENDENT_COMPARISON.md"))
        for query, document in examples:
            with self.subTest(query=query):
                hits = loaded.search(query, collection=COLLECTION, limit=3)
                self.assertIn(document, [h.passage.document for h in hits])
                self.assertTrue(all(h.citation.startswith("Source: ") for h in hits))
        self.assertEqual(loaded.search("analytics", collection="unknown"), [])

    def test_published_reference_has_no_source_payloads_or_local_paths(self):
        for p in CORPUS.rglob("*"):
            if not p.is_file():
                continue
            self.assertIn(p.suffix, {".md", ".json"})
            text = p.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)(?:[a-z]:[\\/](?:Users|Documents)|file://|/home/|OneDrive[\\/])")
            self.assertNotRegex(text, r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
        coverage = (CORPUS / "COVERAGE.md").read_text(encoding="utf-8")
        self.assertIn("semantic review is partial", coverage)
        self.assertIn("private reports", coverage)

    def test_local_reference_links_and_source_ids_resolve(self):
        index = (CORPUS / "SOURCE_INDEX.md").read_text(encoding="utf-8")
        ids = set(re.findall(r"^## (S\d{3})$", index, re.M))
        for p in CORPUS.glob("*.md"):
            text = p.read_text(encoding="utf-8")
            self.assertFalse(set(re.findall(r"\bS\d{3}\b", text)) - ids, p.name)
            for table in re.findall(r"(?m)(?:^\|.*\n)+", text):
                widths = {line.count("|") for line in table.splitlines()}
                self.assertEqual(len(widths), 1, (p.name, "inconsistent table columns"))
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                path = target.split("#", 1)[0]
                if path and not re.match(r"https?://", path):
                    self.assertTrue((p.parent / path).is_file(), (p.name, target))


try:
    from fastapi.testclient import TestClient
    from server.app import create_app
    from tests.support import closing
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


@unittest.skipUnless(API_AVAILABLE, "server dependencies unavailable")
class ReviewedKnowledgeApiTests(unittest.TestCase):
    def test_default_api_source_lookup_and_explicit_override(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        config = root / "config.json"
        config.write_text(json.dumps({"agent_name": "Reference test", "version": "test",
            "memory_file": str(root / "memory.json"), "database_file": str(root / "test.db"),
            "vault_dir": str(root / "vault"), "preferences": {}}), encoding="utf-8")
        with patch.object(knowledge, "DEFAULT_ROOT", root / "absent"):
            app = closing(self, create_app(config, env={}))
            with TestClient(app) as client:
                listed = client.get("/api/knowledge")
                self.assertEqual(listed.status_code, 200)
                self.assertIn(COLLECTION, listed.text)
                found = client.get("/api/knowledge/search", params={"q": "leakage controls", "collection": COLLECTION})
                self.assertEqual(found.status_code, 200)
                self.assertIn("04_VALIDATION_UNCERTAINTY.md", found.text)
                self.assertNotIn(str(ROOT), found.text)
        app = closing(self, create_app(config, env={"AGENTIC_OS_KNOWLEDGE_DIR": str(root / "empty")}))
        with TestClient(app) as client:
            self.assertNotIn(COLLECTION, client.get("/api/knowledge").text)


if __name__ == "__main__":
    unittest.main()
