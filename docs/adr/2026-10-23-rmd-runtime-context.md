# Preserve requester context across runtime deadlines

Date: 2026-10-23  
Status: Accepted for integration.

Main's P2 update moves custom stages and agent runtimes onto bounded worker
threads. RMD's knowledge isolation uses a ContextVar containing the actual
requester, distinct from the conversation creator. ThreadPoolExecutor does not
inherit context variables by default. Combining the changes without adaptation
causes authorised runtime knowledge lookups to fail closed.

Copy the caller's context for each deadline invocation and execute the callable
inside that copy. Retain the deadline, timeout reporting and original exception
semantics. Context changes made by the worker do not change the caller's context;
each later request gets its own copy. Do not infer a requester from the session
creator or grant an administrator access to another owner's collection.

A regression first reproduced failed permitted lookups for two principals.
After the correction, each principal sees only its own explicitly permitted
reference collection; the administrator receives no substituted creator grant.
The caller's requester ContextVar is reset after each operation. Existing
runtime, timeout, RMD service and report-publication regressions cover the
combined implementation. Hosted verification uses the normal HTTP server;
local legacy TestClient requests are blocked by this environment's AnyIO portal.

This preserves main through 986b168c, including idempotent run creation and
analytics safeguards. It changes no source applicability, model-use grant,
approval rule or maintenance authority. See the original
[RMD decision](2026-10-22-rmd-evidence-and-insights.md).
