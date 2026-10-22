"""Synthetic collection isolation and reference-to-model boundary regressions."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from server import knowledge
from server.assistant import Assistant, redact_reference_turns
from server.auth import LOCAL_PRINCIPAL, Principal
from server.operations import Operations
from server.storage import open_store


class KnowledgeAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "references"
        self.root.mkdir()
        self.store = open_store(None, Path(self.tmp.name) / "scope.db")
        self.addCleanup(self.store.close)
        self.alice = Principal("alice", "owner", "test")
        self.bob = Principal("bob", "owner", "test")
        self.admin = Principal("operator", "admin", "test")

    def source(self, name, **metadata):
        folder = self.root / name
        folder.mkdir(exist_ok=True)
        (folder / "handbook.md").write_text(
            "# Synthetic maintenance reference\n\n## Evidence\n\n"
            f"The synthetic canary PRIVATE_{name} describes reference evidence only.\n",
            encoding="utf-8")
        (folder / "collection.json").write_text(json.dumps(metadata), encoding="utf-8")
        return folder

    def scoped(self, principal, **options):
        return knowledge.load(self.root).for_principal(principal, self.store, **options)

    def names(self, principal, **options):
        return [row["collection_id"] for row in self.scoped(principal, **options).describe()]

    def test_private_scope_precedes_metadata_counts_and_search(self):
        self.source("alice-ref", owner="alice", data_classification="private")
        self.source("bob-ref", owner="bob", data_classification="private")
        self.assertEqual(self.names(self.alice), ["alice-ref"])
        self.assertEqual(self.names(self.bob), ["bob-ref"])
        self.assertEqual(self.names(self.admin), [])
        scoped = self.scoped(self.bob)
        self.assertEqual(scoped.search("evidence", collection="alice-ref"), [])
        self.assertNotIn("PRIVATE_alice-ref", json.dumps(scoped.describe()))
        self.assertEqual({h.passage.collection for h in scoped.search("evidence")}, {"bob-ref"})

    def test_organization_membership_revocation_affects_warm_content(self):
        org = Operations(self.store).create_organization(
            self.alice, {"name": "Synthetic depot", "idempotency_key": "depot"})
        self.source("org-ref", organization_id=org["id"], data_classification="private")
        loaded = knowledge.load(self.root)
        self.assertTrue(loaded.for_principal(self.alice, self.store))
        self.assertFalse(loaded.for_principal(self.admin, self.store))
        self.assertFalse(loaded.for_principal(self.bob, self.store))
        self.store._exec("DELETE FROM organization_members WHERE org_id = ? AND subject = ?",
                         (org["id"], "alice"))
        self.assertFalse(loaded.for_principal(self.alice, self.store))

    def test_manifest_only_scope_change_is_seen_without_a_text_edit(self):
        folder = self.source("changing", owner="alice", data_classification="private")
        self.assertEqual(self.names(self.alice), ["changing"])
        (folder / "collection.json").write_text(json.dumps({"owner": "bob"}))
        self.assertEqual(self.names(self.alice), [])
        self.assertEqual(self.names(self.bob), ["changing"])

    def test_unscoped_legacy_references_are_only_for_the_local_owner(self):
        self.source("legacy")
        self.assertEqual(self.names(LOCAL_PRINCIPAL, local=True), ["legacy"])
        self.assertEqual(self.names(LOCAL_PRINCIPAL), [])
        self.assertEqual(self.names(self.admin, local=True), [])
        self.assertEqual(self.names(self.alice, local=True), [])

    def test_model_scope_requires_explicit_public_and_model_grant(self):
        self.source("private", owner="alice", model_context_allowed=True)
        self.source("public-no-model", visibility="public", data_classification="public")
        self.source("allowed", visibility="public", data_classification="public", model_context_allowed=True)
        self.source("ambiguous", visibility="public", data_classification="internal", model_context_allowed=True)
        self.assertEqual(self.names(self.alice, for_model=True), ["allowed"])

    def test_manifest_response_allowlist_does_not_serialize_access_configuration(self):
        self.source("allowed", owner="alice", title="Reference", token="DO_NOT_SERIALIZE",
                    path="/private/internal", documents=["FORGED"], passages=900)
        result = self.scoped(self.alice).describe()[0]
        self.assertEqual(result["title"], "Reference")
        self.assertEqual(result["passages"], 1)
        self.assertIsInstance(result["documents"][0], dict)
        self.assertFalse({"owner", "token", "path"}.intersection(result))

    def test_citation_identity_includes_collection_and_full_text(self):
        prefix = "Repeated synthetic paragraph " * 12
        first = knowledge.split_markdown(prefix + "FIRST", "one", "same.md")[0]
        second = knowledge.split_markdown(prefix + "SECOND", "one", "same.md")[0]
        other = knowledge.split_markdown(prefix + "FIRST", "two", "same.md")[0]
        self.assertNotEqual(first.anchor, second.anchor)
        self.assertNotEqual(first.anchor, other.anchor)

    def assistant(self):
        engine = SimpleNamespace(store=self.store, list_runs=lambda **_: [])
        return Assistant(Mock(), engine, identity_mode="jwt",
                         env={"AGENTIC_OS_KNOWLEDGE_DIR": str(self.root)})

    def test_session_creator_never_substitutes_for_actual_requester(self):
        self.source("secret", owner="alice", data_classification="private")
        assistant = self.assistant()
        session = SimpleNamespace(owner="alice")
        token = assistant._requester.set(self.admin)
        try:
            result = assistant._search_knowledge({"query": "evidence"}, "evidence", "en", session)
        finally:
            assistant._requester.reset(token)
        self.assertNotIn("PRIVATE_secret", json.dumps(result))
        self.assertIsNone(result["result"])

    def test_private_reference_text_cannot_enter_tool_results_or_persistent_chat(self):
        self.source("secret", owner="alice", data_classification="private")
        assistant = self.assistant()
        token = assistant._requester.set(self.alice)
        try:
            for runtime in (False, True):
                result = assistant._search_knowledge({"query": "evidence"}, "evidence", "en", for_model=runtime)
                self.assertNotIn("PRIVATE_secret", json.dumps(result))
                self.assertIsNone(result["result"])
        finally:
            assistant._requester.reset(token)

    def test_former_reference_transcript_entries_are_excluded_from_model_context(self):
        assistant = self.assistant()
        agent = SimpleNamespace(memory_entries=lambda: [], preferences={})
        session = SimpleNamespace(owner="alice", agent=agent, transcript=[
            {"role": "agent", "action": "search_knowledge", "text": "PRIVATE_OLD_REFERENCE"},
            {"role": "agent", "action": "rmd_evidence", "text": "PRIVATE_OLD_RMD"},
            {"role": "user", "text": "ordinary question"}])
        with patch.object(assistant, "_latest_run", return_value=None):
            context = assistant._context(session)
        self.assertNotIn("PRIVATE_", context)
        self.assertIn("ordinary question", context)

    def test_requester_context_is_reset_when_execution_fails(self):
        assistant = self.assistant()
        with patch.object(assistant, "_handle", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                assistant.handle("question", object(), principal=self.alice)
        self.assertIsNone(assistant._requester.get())

    def test_legacy_runtime_references_are_redacted_in_snapshot_and_export(self):
        entry = {"id": 3, "role": "agent", "action": "runtime", "text": "PRIVATE_OLD",
                 "steps": [{"tool": "search_knowledge", "text": "PRIVATE_STEP", "result": {"text": "PRIVATE_RESULT"}}]}
        clean = redact_reference_turns([entry])
        self.assertNotIn("PRIVATE_", json.dumps(clean))
        self.assertTrue(clean[0]["reference_redacted"])
        self.assertEqual(clean[0]["id"], 3)
        assistant = self.assistant()
        session = SimpleNamespace(owner="alice", agent=SimpleNamespace(memory_entries=lambda: [], preferences={}),
                                  transcript=[entry])
        with patch.object(assistant, "_latest_run", return_value=None):
            self.assertNotIn("PRIVATE_", assistant._context(session))


if __name__ == "__main__":
    unittest.main()
