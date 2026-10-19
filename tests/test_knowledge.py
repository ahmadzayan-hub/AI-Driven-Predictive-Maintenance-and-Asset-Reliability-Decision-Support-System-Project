"""Markdown knowledge collections: chunking, citation and retrieval (ADR 0057).

The fixtures here are synthetic. The repository is public, so the real
collection - course material with an institution, a group and an
instructor in it - lives in the git-ignored private/knowledge/ and is
exercised by the one test that skips when it is absent, the same shape as
the PostgreSQL tests.
"""

import json
import tempfile
import unittest
from pathlib import Path

from server import knowledge
from tests.support import temp_workspace

SAMPLE = """# Reliability Handbook

Everything below is invented for this test.

## 1. Measures

### 1.1 Mean time between failures

MTBF is the operating time divided by the number of failures.

| Measure | Formula | Unit |
| --- | --- | --- |
| MTBF | operating_hours / failures | hours |
| MTTR | repair_hours / repairs | hours |

### 1.2 Availability

Availability = MTBF / (MTBF + MTTR), expressed as a share of the period.

## 2. Prioritisation

Rank assets by expected consequence, not by failure count alone.
"""

ARABIC = """# دليل الموثوقية

## 1. المؤشرات

متوسط الزمن بين الأعطال هو زمن التشغيل مقسوماً على عدد الأعطال.
"""


def collection(case, files, manifest=None):
    """A knowledge root holding one collection, cleaned up with the case."""
    workspace = temp_workspace(case, tempfile)
    root = Path(workspace.name)
    folder = root / "handbook"
    folder.mkdir()
    for name, text in files.items():
        (folder / name).write_text(text, encoding="utf-8")
    if manifest is not None:
        (folder / "collection.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


class ChunkingTestCase(unittest.TestCase):
    def test_a_passage_is_named_by_the_headings_above_it(self):
        passages = knowledge.split_markdown(SAMPLE, "c", "handbook.md")
        sections = [p.section for p in passages]
        self.assertIn("1. Measures > 1.1 Mean time between failures", sections)
        self.assertIn("2. Prioritisation", sections)

    def test_the_document_title_is_not_repeated_in_every_citation(self):
        """It is already in the file name, and it crowds out the section."""
        passages = knowledge.split_markdown(SAMPLE, "c", "handbook.md")
        deep = [p for p in passages if ">" in p.section]
        self.assertTrue(deep)
        for passage in deep:
            self.assertNotIn("Reliability Handbook", passage.section)

    def test_a_table_is_not_cut_in_half(self):
        """A KPI definition split from its formula is worse than a long passage."""
        passages = knowledge.split_markdown(SAMPLE, "c", "handbook.md")
        table = [p for p in passages if "| MTBF |" in p.text]
        self.assertEqual(len(table), 1)
        self.assertIn("| MTTR | repair_hours / repairs | hours |", table[0].text)

    def test_the_citation_names_the_document_and_the_section(self):
        passage = [p for p in knowledge.split_markdown(SAMPLE, "c", "handbook.md")
                   if p.section.endswith("1.2 Availability")][0]
        self.assertEqual(passage.citation,
                         "Source: handbook.md, 1. Measures > 1.2 Availability")


class LoadingTestCase(unittest.TestCase):
    def test_a_folder_becomes_a_collection_named_by_its_manifest(self):
        root = collection(self, {"handbook.md": SAMPLE},
                          manifest={"collection_id": "reliability-handbook",
                                    "data_classification": "educational"})
        described = knowledge.load(root).describe()
        self.assertEqual(len(described), 1)
        self.assertEqual(described[0]["collection_id"], "reliability-handbook")
        self.assertEqual(described[0]["data_classification"], "educational")

    def test_a_missing_root_is_empty_rather_than_an_error(self):
        """A deployment without a knowledge folder still starts."""
        workspace = temp_workspace(self, tempfile)
        store = knowledge.load(Path(workspace.name) / "nothing-here")
        self.assertEqual(store.describe(), [])
        self.assertFalse(store)

    def test_importing_the_same_bytes_twice_changes_nothing(self):
        """Re-import must not double the corpus (acceptance criterion)."""
        root = collection(self, {"handbook.md": SAMPLE})
        first = knowledge.load(root)
        before = first.describe()[0]
        (root / "handbook" / "handbook.md").write_text(SAMPLE, encoding="utf-8")
        after = knowledge.load(root).describe()[0]
        self.assertEqual(before["passages"], after["passages"])
        self.assertEqual(before["documents"][0]["sha256"],
                         after["documents"][0]["sha256"])

    def test_changed_content_is_a_changed_digest(self):
        """Re-indexing follows the bytes, not a timestamp."""
        root = collection(self, {"handbook.md": SAMPLE})
        before = knowledge.load(root).describe()[0]["documents"][0]["sha256"]
        (root / "handbook" / "handbook.md").write_text(
            SAMPLE + "\n### 1.3 Backlog\n\nOpen work orders per asset.\n",
            encoding="utf-8")
        after = knowledge.load(root).describe()[0]
        self.assertNotEqual(before, after["documents"][0]["sha256"])
        # The new heading was appended after "## 2. Prioritisation", so it
        # nests under that section: the path follows the document, not the
        # numbering someone wrote in the heading text.
        self.assertIn("2. Prioritisation > 1.3 Backlog",
                      [h.passage.section for h in
                       knowledge.load(root).search("backlog open work orders")])


class RetrievalTestCase(unittest.TestCase):
    def setUp(self):
        self.store = knowledge.load(collection(
            self, {"handbook.md": SAMPLE, "arabic.md": ARABIC}))

    def test_a_question_finds_the_section_that_answers_it(self):
        hit = self.store.search("how is availability calculated")[0]
        self.assertIn("1.2 Availability", hit.passage.section)

    def test_the_heading_counts_for_more_than_the_body(self):
        """Two passages may share a word; the one titled with it wins."""
        hit = self.store.search("prioritisation")[0]
        self.assertEqual(hit.passage.section, "2. Prioritisation")

    def test_arabic_is_searchable_in_arabic(self):
        hits = self.store.search("متوسط الزمن بين الأعطال")
        self.assertTrue(hits)
        self.assertEqual(hits[0].passage.document, "arabic.md")

    def test_a_query_of_only_common_words_returns_nothing(self):
        """Better no answer than the longest passage in the corpus."""
        self.assertEqual(self.store.search("what is the and of"), [])

    def test_an_unknown_collection_is_empty_not_everything(self):
        """A filter that matches nothing must not silently widen the search."""
        self.assertEqual(self.store.search("availability", collection="absent"), [])

    def test_every_hit_can_be_cited(self):
        for hit in self.store.search("MTBF failures operating time", limit=5):
            self.assertTrue(hit.citation.startswith("Source: "))
            self.assertIn(hit.passage.document, hit.citation)


class AgentToolTestCase(unittest.TestCase):
    """The tool the model is offered, and what it hands back (ADR 0057)."""

    def setUp(self):
        from assistant import ACTIONS, SERVER_ONLY
        from server import tools
        self.ACTIONS, self.SERVER_ONLY, self.tools = ACTIONS, SERVER_ONLY, tools

    def test_the_tool_is_offered_and_takes_a_question(self):
        self.assertIn("search_knowledge", self.tools.NAMES)
        self.assertIn("search_knowledge", self.ACTIONS)
        declared = [t for t in self.tools.TOOLS
                    if t["name"] == "search_knowledge"][0]
        self.assertEqual(declared["inputSchema"]["required"], ["query"])
        self.assertIn("collection", declared["inputSchema"]["properties"])

    def test_it_needs_the_server(self):
        """The command-line interface has no collections to search."""
        self.assertIn("search_knowledge", self.SERVER_ONLY)

    def test_it_is_not_destructive(self):
        from assistant import DESTRUCTIVE
        self.assertNotIn("search_knowledge", DESTRUCTIVE)


class ExecutorTestCase(unittest.TestCase):
    """What the assistant says when it searches, in both languages."""

    def search(self, root, query, language="en"):
        import os
        from server.assistant import Assistant
        previous = os.environ.get("AGENTIC_OS_KNOWLEDGE_DIR")
        os.environ["AGENTIC_OS_KNOWLEDGE_DIR"] = str(root)
        self.addCleanup(lambda: os.environ.__setitem__(
            "AGENTIC_OS_KNOWLEDGE_DIR", previous) if previous is not None
            else os.environ.pop("AGENTIC_OS_KNOWLEDGE_DIR", None))
        return Assistant._search_knowledge(
            None, {"query": query}, query, language)

    def test_the_answer_quotes_passages_and_their_citations(self):
        root = collection(self, {"handbook.md": SAMPLE})
        outcome = self.search(root, "how is availability calculated")
        self.assertIn("Source: handbook.md", outcome["text"])
        self.assertIn("1.2 Availability", outcome["text"])
        self.assertTrue(outcome["result"]["results"])

    def test_no_match_says_so_rather_than_answering_from_memory(self):
        root = collection(self, {"handbook.md": SAMPLE})
        outcome = self.search(root, "zygomorphic penguin husbandry")
        self.assertIsNone(outcome["result"])
        self.assertIn("Nothing in the knowledge base", outcome["text"])

    def test_an_empty_root_says_how_to_load_one(self):
        workspace = temp_workspace(self, tempfile)
        outcome = self.search(Path(workspace.name) / "absent", "availability")
        self.assertIsNone(outcome["result"])
        self.assertIn("AGENTIC_OS_KNOWLEDGE_DIR", outcome["text"])

    def test_every_message_ships_in_arabic_too(self):
        root = collection(self, {"handbook.md": SAMPLE})
        for query, language in (("how is availability calculated", "ar"),
                                ("zygomorphic penguin husbandry", "ar")):
            text = self.search(root, query, language)["text"]
            self.assertTrue(any("؀" <= ch <= "ۿ" for ch in text),
                            f"no Arabic in the reply for {query!r}")

    def test_only_a_few_passages_are_quoted(self):
        """A 100 KB collection must not be injected whole."""
        from server.assistant import KNOWLEDGE_HITS
        root = collection(self, {"handbook.md": SAMPLE})
        outcome = self.search(root, "MTBF MTTR availability failures assets")
        self.assertLessEqual(len(outcome["result"]["results"]), KNOWLEDGE_HITS)


class RealCollectionTestCase(unittest.TestCase):
    """The private collection, when the machine running this has it.

    It is deliberately not committed: the repository is public and this is
    course material. Absent, the test skips and says so.
    """

    def setUp(self):
        self.store = knowledge.load()
        if not self.store:
            self.skipTest("no private/knowledge collection on this machine")

    def test_what_is_indexed_is_reported_with_its_version(self):
        for described in self.store.describe():
            self.assertTrue(described["documents"])
            for document in described["documents"]:
                self.assertEqual(len(document["sha256"]), 64)
                self.assertGreater(document["passages"], 0)

    def test_the_acceptance_questions_retrieve_something_citable(self):
        questions = (
            "What is the difference between Business Analytics and Data Science?",
            "Explain the four types of analytics with business examples.",
            "Explain MTBF, MTTR and availability.",
            "How should Team 3 prioritize maintenance interventions?",
            "What causes data leakage in predictive maintenance?",
            "What are the mandatory Group 9226 capstone deliverables?",
            "How do we validate a predictive model against a baseline?",
            "What is a star schema in Power BI?",
            "What is the difference between an AI Agent and Agentic AI?",
        )
        for question in questions:
            hits = self.store.search(question, limit=3)
            self.assertTrue(hits, question)
            self.assertTrue(hits[0].citation.startswith("Source: "), question)


if __name__ == "__main__":
    unittest.main()
