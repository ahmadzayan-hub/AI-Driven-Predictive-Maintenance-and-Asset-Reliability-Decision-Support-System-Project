# Project knowledge graph

Updated 20 October 2026, following the owner's uploaded Obsidian graph and request to increase its points.

## Review and changes

The screenshot shows a connected foundation around Agentic OS, the user, identity, principles and delivery practices. Most subjects share a dense central cluster. The similar node styling makes categories hard to distinguish, several labels overlap, and the generic `Note` template is visible as a node.

The curated vault has been expanded from **27 to 45 notes**, with **18 focused additions**. Each new note describes an implemented capability or an explicit acceptance boundary, names its repository sources and connects to Home and related concepts. These are knowledge topics, not additional software agents or proof of newly implemented capabilities.

| Area | Added notes |
| --- | --- |
| Agents and evidence | Agent collaboration; Run lifecycle; Evidence and claims; Knowledge retrieval |
| Data and maintenance | Data quality contracts; Dataset joins; Live data; Model validation; Maintenance decision support |
| Security | Managed identity; Tenant isolation; Model privacy |
| Interface | Accessible motion; Scoped dashboards; Business report exports |
| Operations | Release acceptance; Backup and restore; Verification and budgets |

[Home](../../brain/Home.md) indexes every curated note by purpose. Existing pipeline and mapping notes now reflect multi-format inputs, declared joins, automatic breakdown provenance and separate domain-model inputs. The [maintenance log](../../brain/_meta/Maintenance%20log.md) records the change.

## Reading it in Obsidian

Open the repository's `brain` folder as a vault. Use the global graph for orientation and a local graph around a selected concept for detailed relationships.

- Apply `-path:_templates` in the graph search filter to hide the generic template. Optionally add `-path:_meta` when reviewing product concepts rather than maintenance notes.
- Add graph groups using `tag:#agents`, `tag:#data`, `tag:#security`, `tag:#interface` and `tag:#operations`. Choose distinct, restrained colors; the note names and categories remain meaningful without color.
- Start a local graph at Agent collaboration, Evidence and claims or Maintenance decision support. Use depth 1 for direct relationships, increasing it when broader context is needed.
- Adjust link distance and repulsion to separate labels. Keep attachments off unless their relationships are part of the review.

These are optional display settings. This update does not overwrite the owner's Obsidian preferences. Graph visibility also depends on active filters, so the number of visible circles can differ from the curated-note count. See the official [graph controls](https://obsidian.md/help/plugins/graph) and [search syntax](https://obsidian.md/help/plugins/search).

## Knowledge links and live activity

Obsidian links describe relationships between reviewed notes. They do not represent live agent messages. The SaaS Runs workspace separately displays observed stage handoffs, statuses, expandable details and current evidence, as described in the [collaboration study](AGENT_COLLABORATION_MOTION.md).

The chosen motion is professional and restrained: a brief highlight when an observed handoff changes, a pause-view control and respect for reduced-motion preferences. A real message transcript would need a durable, tenant-scoped event contract; it is not inferred from graph edges or polling snapshots.

## Validation

Run `python scripts/brain_check.py --strict` for frontmatter, sources, broken links, orphans and related maintenance checks. Home coverage and related incoming links were also checked explicitly for this expansion. These checks establish graph structure; note accuracy still depends on reviewing the named sources. Application test results remain in [README Testing](../../README.md#testing).
