## 21. Claude Code integration approach
<!-- kb: domain=rmd.product; evidence=PROPOSED_APPLICATION -->


### 21.1 Inspect first

Before changing code, Claude Code should inspect:

1. The actual RMD V2 repository, branch, commit and working-tree changes.
2. Existing AGENTS.md, CLAUDE.md and repository-specific instructions.
3. Existing knowledge import, retrieval, citation and assistant interfaces.
4. Authentication, roles, source access, audit mechanisms and current tests.
5. Existing Arabic/English and voice pathways where relevant to the requested change.

This file supplies no verified build command, database schema, framework version or target service URL. Derive those from the actual repository.

Also inspect repository visibility and collaborator access before committing this handover. Owner-only academic identifiers and restricted source material must remain outside shared or public repository content. If the repository audience is broader than this document's permitted audience, create a departmental copy with the private sections removed and retain the private reference separately. Retrieval filters do not protect information already disclosed through source files or Git history.

### 21.2 Suggested placement

Suggested reference path:

~~~text
docs/knowledge/RMD_V2_MBA_9227_Project_Knowledge.md
~~~

This is a proposed path, not a claim about the current repository. Reuse the existing knowledge location if there is one. Only place the version suitable for that repository's audience there; the complete owner copy does not need to be committed.

Keep the detailed knowledge in that reference file. Add a short pointer to the existing project instructions only when appropriate; preserve unrelated instructions and reconcile any conflict explicitly.

Example pointer:

~~~markdown
## MBA 9227 reference knowledge

When working on course-derived decision support or knowledge ingestion, read
docs/knowledge/RMD_V2_MBA_9227_Project_Knowledge.md.

Treat it as a dated reference source. Keep its source IDs, evidence status,
domain boundaries and correction history. Keep owner-only academic details
outside general RMD retrieval. Follow the repository's actual permissions.
~~~

Official Claude Code documentation explains that CLAUDE.md provides context, can import files with @path syntax, and should remain concise. Imported content also consumes context. For this long reference, a short pointer and task-specific reading is preferable to automatically loading the whole pack into every session. Markdown instructions are not an enforced permission layer. [S11]

### 21.3 Coding-assistant context versus application knowledge

Giving the file to Claude Code helps the coding assistant understand the project. RMD V2's end-user assistant benefits only after the application actually loads or retrieves the permitted content.

Therefore, a complete integration requires evidence that a user's question reaches the knowledge source, returns the correct scoped passage, and displays a meaningful citation. Merely placing the file in the repository is not proof of that behaviour.
