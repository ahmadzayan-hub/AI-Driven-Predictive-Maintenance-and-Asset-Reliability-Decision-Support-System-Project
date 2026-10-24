# Miyaar in Hermes Desktop / معيار في Hermes Desktop

Miyaar remains a web application. This package adds its existing analytics
tool interface to Hermes Desktop through **stdio MCP**. It does not start,
embed, rebuild or replace the website. The web address on port 8017 is not an
MCP endpoint.

**Preparation status:** branch publication and a draft PR are owner-approved;
installation, activation, merge and deployment remain unapproved.
The default package is a **help-only preview**.
Connecting actual workspace data remains a separate approval step.
The revised package and MCP dispatch tests passed in isolated synthetic storage
after memory recovered, with network-denial guards. This bounded result does
not establish live Hermes activation or production acceptance; see README.

## Verified compatibility

Read-only inspection on 24 October 2026 identified Nous Research Hermes:

- Packaged Desktop `app.asar/package.json`: **0.17.6**.
- Installed Agent `hermes_cli/__init__.py`: **0.21.3**.
- Desktop install stamp and installed source ref:
  `c1488ac947c9bc33fd65ec464548dc9d8edd6122`.
- The local gateway PID record matched a running process using the installed
  Hermes Python runtime. Local listening sockets and a running Desktop-owned
  backend were present. No remote authentication or chat was inspected.
- The installed portable parser accepted this package, its skill and its MCP
  entry without diagnostics in an isolated scratch profile. This does not
  constitute installation or Desktop UI acceptance.

The installed Desktop detector accepts a root `plugin.json`, or native
`plugin.yaml` plus `__init__.py`; a renderer extension uses `desktop/plugin.js`.
The original repository supplied none of these, explaining **“No agent or
desktop plugin artifacts found in this repository.”** A portable Agent plugin
is sufficient; a new Desktop renderer is unnecessary.

Current official [plugin documentation](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
describes portable `plugin.json`, `mcp.json` and `skills/` packages. Its newer
portable trust extension is **not implemented by the inspected installed
parser**. This package therefore enforces its tool allowlist in the Miyaar
server. The installed native MCP configuration supports `trust: untrusted`
and [tool filters](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference).
Filters use server-native names; `include` takes precedence over `exclude`.
Neither filters nor trust settings form an operating-system sandbox.

## Package contents

| File | Purpose |
| --- | --- |
| `plugin.json` | Portable Agent Plugins v1 manifest at the repository root |
| `mcp.json` | Launch `python -I -B -X utf8 ${PLUGIN_ROOT}/scripts/hermes_mcp.py` |
| `skills/miyaar/SKILL.md` | English/Arabic workflow and scope guidance |
| `scripts/hermes_mcp.py` | Preview or explicitly configured local workspace |
| `server/mcp.py` | Existing JSON-RPC transport, with optional enforced allowlist |
| `examples/hermes/` | Inactive examples for later review |

No dependency installer, setup hook, model download or hosted service is
included. Existing callers of `McpServer` retain their original catalogue
unless they supply an allowlist. `scripts/mcp_server.py` and the web app remain
unchanged. The new launcher avoids `server.app`, whose import creates the web
application and can initialize default storage before CLI configuration.

## Prerequisites and installation boundary

Review this candidate before merging; main lacks the package until it is merged.
Python 3.11+ must resolve as `python` in the Hermes backend; a Store alias is
insufficient. Only the standard library is required, not the MCP SDK or frontend.
Installation/activation needs approval of the revision, profile, executable and
local code execution. Plugins run as the user; this guard is not an OS sandbox.
The documented CLI supports `hermes plugins install <reviewed-source> --no-enable`;
Desktop installation may activate immediately. Neither was run. After approved
activation, verify that only `help` appears; help text grants no extra access.

## Optional workspace access, only after approval

Preview connects no storage or provider. Review a copy of the workspace example
outside the installation; use explicit absolute local paths. Placeholders are
invalid. Missing/malformed configuration fails without default-storage fallback.
Only a nonempty subset of `help`, `run_status`, `explain_report` is accepted;
all other opt-ins fail before storage opens. Direct calls enforce the same list.
The disabled native example replaces the same-name portable server. Match
`tools.include` to `enabled_tools`; filters cannot widen access. Keep resources
and prompts disabled and approval mode enabled.

Approve exact paths and startup effects: `Agent` reads `memory_file` even without
`recall`; SQLite can create directories/database, initialize or migrate schema,
and enable WAL/create files. This is not a read-only connection. Start with a
separate synthetic database and empty/synthetic memory. Read-tools approval alone
does not authorize these writes or connection to live storage.

`recall`, `remember`, `set_preference`, `start_run`, `search_knowledge` and
`agent_scorecard` are rejected. Knowledge loading follows symlinks beyond its
root; scorecards use plugin-root/bundled evaluation rather than workspace data.
Those facilities were not repaired. Vault/knowledge paths remain explicit fields;
`knowledge_dir` grants no search access or containment guarantee. Do not bypass
exclusions through legacy MCP. Website/default MCP behavior is unchanged.

No inherited credentials, hosted database URLs, custom stages, model roles,
application config or glossaries are used. The gateway has no provider; there is
no worker. Starting runs and approving/publishing stay in the web app. This is
local-owner only, without identity tokens or hosted/tenant authentication parity.
Separately approve sharing selected run metadata/summaries with Hermes, its model
recipient and cost policy. A local gateway does not establish local inference.
Never forward raw rows or secrets. No model call or external message was made.

## Verification and remaining acceptance

**Revised package/MCP dispatch tests passed in isolated synthetic storage.**
The supervisor and stdio children denied network audit events and observed no
attempts. Current commands/counts and earlier checks are in README. Parser checks
used a scratch profile, not activation. An SDK probe was interrupted without a
result, not passed. A concrete local Python executable/version was verified;
command resolution inside Hermes, Desktop handshake/activation, full web/CI,
real-data access, hosted identity and production parity remain untested.
No install, activation, merge, deployment or live-web changes were performed.

## ملخص التشغيل بالعربية

الوضع الافتراضي للمساعدة فقط. ربط البيانات يحتاج موافقة على قراءة الذاكرة
وكتابات SQLite وملفات WAL ومشاركة الملخصات مع النموذج. ابدأ ببيانات اصطناعية.
نجحت الاختبارات المحدودة ببيانات اصطناعية مع منع الشبكة؛ ولم تُثبّت الحزمة
أو تُفعّل. وافق المالك على نشر الفرع وفتح طلب دمج للمراجعة فقط؛ ويبقى
اختبار التشغيل داخل Hermes واعتماد البيانات والتثبيت والتفعيل منفصلًا.
