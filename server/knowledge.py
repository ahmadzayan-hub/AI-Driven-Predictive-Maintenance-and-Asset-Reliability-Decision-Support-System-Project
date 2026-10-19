"""Searchable Markdown knowledge collections, cited back to their headings.

    from server import knowledge
    store = knowledge.load()
    for hit in store.search("what is MTBF", limit=3):
        print(hit.citation, hit.score)

A collection is a folder of Markdown files. Each file is split on its
heading hierarchy, so a passage carries the path that leads to it and can
be cited as `Source: <file>, <section>`. Tables, fenced blocks and formula
lines stay whole inside their passage: a KPI definition cut in half is
worse than one that is slightly too long.

Retrieval is deterministic keyword scoring - no embeddings, no model, no
tokens. `docs/OBSIDIAN_INTEGRATION.md` records that embeddings and vector
retrieval are deliberately absent, and a corpus of this size does not need
them: the index is built in memory in milliseconds and every score can be
explained from the words that produced it. ADR 0057.

Where the content lives is configuration, never a committed path. This
repository is public and course material, client documents and personal
records must stay out of it, so the default root is the git-ignored
`private/knowledge/`. `AGENTIC_OS_KNOWLEDGE_DIR` overrides it, the same way
`AGENTIC_OS_VAULT_DIR` overrides the vault (ADR 0044).

A passage is data, never an instruction. Text retrieved here is quoted to a
reader or handed to a model as reference material; it never decides what
the system does.
"""

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = PROJECT_ROOT / "private" / "knowledge"

# A passage must hold a whole idea. Long enough for a table, short enough
# that a citation points somewhere a reader can actually look.
MAX_PASSAGE_CHARS = 4000
MIN_PASSAGE_CHARS = 40

HEADING = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
WORD = re.compile(r"[a-z0-9_]+|[؀-ۿ]+")

# Words too common to tell two passages apart, in both languages the
# product ships in.
STOPWORDS = frozenset("""
a an and are as at be been by for from has have how in is it its of on or
that the this to was what when where which who why with
في من على عن إلى الى هذا هذه ذلك التي الذي ما هل كان هي هو مع بين او أو و
""".split())


def _words(text):
    return [w for w in WORD.findall(text.lower()) if w not in STOPWORDS]


@dataclass(frozen=True)
class Passage:
    """One citable piece of a document."""

    collection: str
    document: str
    section: str
    text: str
    anchor: str
    counts: dict = field(compare=False, default_factory=dict)

    @property
    def citation(self):
        """The one line a reader needs to find this passage themselves."""
        return f"Source: {self.document}, {self.section}" if self.section \
            else f"Source: {self.document}"

    def as_dict(self, score=None):
        out = {"collection": self.collection, "document": self.document,
               "section": self.section, "anchor": self.anchor,
               "citation": self.citation, "text": self.text}
        if score is not None:
            out["score"] = round(score, 4)
        return out


@dataclass(frozen=True)
class Hit:
    passage: Passage
    score: float
    matched: tuple

    @property
    def citation(self):
        return self.passage.citation


def split_markdown(text, collection, document):
    """Markdown into passages, one per heading, deepest heading wins.

    The heading path is kept whole - "4. Team 3 case > 4.2 Reliability
    measures" says more than the leaf alone, and a reader can find it.
    Content before the first heading belongs to the document itself.
    """
    passages = []
    trail = {}
    heading_path = []
    body = []
    fenced = False

    def flush():
        content = "\n".join(body).strip()
        if len(content) < MIN_PASSAGE_CHARS and not heading_path:
            return
        if not content:
            return
        # The document title repeats in every citation and says nothing that
        # the file name has not already said, so it is dropped from the path
        # once there is a deeper heading to name.
        named = heading_path[1:] if len(heading_path) > 1 else heading_path
        section = " > ".join(named)
        head = "\n".join(f"{'#' * (i + 1)} {h}" for i, h in enumerate(heading_path))
        whole = f"{head}\n\n{content}".strip() if head else content
        for piece in _fit(whole):
            anchor = hashlib.sha256(
                f"{document}\x00{section}\x00{piece[:120]}".encode()).hexdigest()[:16]
            passages.append(Passage(collection=collection, document=document,
                                    section=section, text=piece, anchor=anchor,
                                    counts=_count(f"{section} {piece}")))

    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        match = None if fenced else HEADING.match(line)
        if match:
            flush()
            body = []
            level = len(match.group(1))
            trail[level] = match.group(2)
            for deeper in [k for k in trail if k > level]:
                del trail[deeper]
            heading_path = [trail[k] for k in sorted(trail)]
            continue
        body.append(line)
    flush()
    return passages


def _fit(text):
    """Split only when a passage is too long, and only between blocks.

    A table or a fenced block is never cut: the split points are blank
    lines outside them, so a KPI formula and its variables stay together.
    """
    if len(text) <= MAX_PASSAGE_CHARS:
        return [text]
    pieces, current, fenced = [], [], False
    for block in text.split("\n\n"):
        if block.count("```") % 2 or block.count("~~~") % 2:
            fenced = not fenced
        candidate = "\n\n".join(current + [block])
        if current and len(candidate) > MAX_PASSAGE_CHARS and not fenced:
            pieces.append("\n\n".join(current))
            current = [block]
        else:
            current.append(block)
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def _count(text):
    counts = {}
    for word in _words(text):
        counts[word] = counts.get(word, 0) + 1
    return counts


@dataclass
class Collection:
    """A folder of Markdown, with whatever its manifest declares about it."""

    name: str
    root: Path
    metadata: dict
    passages: list
    documents: dict

    def as_dict(self):
        return {"collection_id": self.name, "passages": len(self.passages),
                "documents": [{"document": name, "sha256": info["sha256"],
                               "bytes": info["bytes"], "passages": info["passages"]}
                              for name, info in sorted(self.documents.items())],
                **self.metadata}


class KnowledgeStore:
    """Every collection under one root, searchable by keyword."""

    def __init__(self, collections):
        self.collections = {c.name: c for c in collections}

    def __bool__(self):
        return any(c.passages for c in self.collections.values())

    def describe(self):
        return [c.as_dict() for c in sorted(self.collections.values(),
                                            key=lambda c: c.name)]

    def search(self, query, collection=None, limit=5):
        """The best passages for a question, most relevant first.

        Score is the rarity of each query word the passage holds, doubled
        when the word is in the heading path, scaled by how much of the
        question the passage covers. Deterministic and explainable from
        `matched` alone.

        Okapi BM25 was tried here and measured worse: 6 of the 10
        acceptance questions answered exactly against 8, because its
        length normalisation pushes down the long glossary passage that
        actually holds the formula reference. A corpus of 73 passages of
        very uneven length is not what BM25's averages assume. The
        measurement is in ADR 0057; the simpler rule stays until a larger
        corpus makes it fail.
        """
        wanted = _words(query or "")
        if not wanted:
            return []
        chosen = ([self.collections[collection]] if collection in self.collections
                  else list(self.collections.values()) if collection is None else [])
        passages = [p for c in chosen for p in c.passages]
        if not passages:
            return []
        rarity = self._rarity(passages)
        hits = []
        for passage in passages:
            matched = tuple(w for w in dict.fromkeys(wanted) if w in passage.counts)
            if not matched:
                continue
            section = passage.section.lower()
            score = sum(rarity.get(w, 1.0) * (2.0 if w in section else 1.0)
                        for w in matched)
            score *= len(matched) / len(set(wanted))
            hits.append(Hit(passage=passage, score=score, matched=matched))
        hits.sort(key=lambda h: (-h.score, h.passage.document, h.passage.section))
        return hits[:max(1, int(limit))]

    @staticmethod
    def _rarity(passages):
        """How much each word distinguishes a passage from the rest."""
        total = len(passages)
        seen = {}
        for passage in passages:
            for word in passage.counts:
                seen[word] = seen.get(word, 0) + 1
        return {w: math.log(1 + total / n) for w, n in seen.items()}


def _manifest(folder):
    path = folder / "collection.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load(root=None, env=None):
    """Read every collection under the root. Missing root is not an error.

    A folder of Markdown is a collection named after the folder; Markdown
    sitting directly in the root forms a collection named after the root.
    Each document is content-addressed, so importing the same file twice
    produces the same passages and re-indexing follows the bytes rather
    than a timestamp.
    """
    env = os.environ if env is None else env
    base = Path(root or env.get("AGENTIC_OS_KNOWLEDGE_DIR") or DEFAULT_ROOT).expanduser()
    if not base.is_dir():
        return KnowledgeStore([])
    folders = [f for f in sorted(base.iterdir()) if f.is_dir()]
    if any(base.glob("*.md")):
        folders.insert(0, base)
    collections = []
    for folder in folders:
        files = sorted(folder.glob("*.md"))
        if not files:
            continue
        name = folder.name if folder != base else base.name
        metadata = _manifest(folder)
        name = str(metadata.get("collection_id") or name)
        passages, documents = [], {}
        for file in files:
            try:
                text = file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found = split_markdown(text, name, file.name)
            passages += found
            documents[file.name] = {
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "bytes": len(text.encode("utf-8")), "passages": len(found)}
        collections.append(Collection(name=name, root=folder, metadata=metadata,
                                      passages=passages, documents=documents))
    return KnowledgeStore(collections)
