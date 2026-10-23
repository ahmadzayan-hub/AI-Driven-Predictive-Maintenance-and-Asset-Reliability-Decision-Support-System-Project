# Model failures and explicit recipient boundaries

Status: accepted for code; no provider activation or hosted acceptance implied.

## Decision

Having another API credential is not permission to send it the current request.
Default hosted failover is disabled. An operator may separately authorize and
configure a directional edge such as `AGENTIC_OS_MODEL_FAILOVER=anthropic>openai`.
Only one additional already-configured recipient can be attempted, only after a
network error, timeout or server failure. Local Ollama never transfers to a
hosted recipient. Quota, rate limits, missing/invalid credentials, model retirement,
unknown model/resource and payment errors never trigger another provider, even
when an edge exists. There is no model-name substitution, payment, upgrade or
automatic retry loop. Structured-output requests retain their single-provider
contract.

The gateway retains only fixed error categories, not upstream messages, bodies,
URLs, prompts, credentials or replies. A generic 404 is `not_found`, not proof
that a model retired. Explicit machine error codes distinguish `model_retired`
from `model_unavailable`; 429 distinguishes provider quota from ordinary rate
limiting when the provider supplies a recognized code/type. Successful subsequent
calls clear the last error while aggregate historical counts remain visible.
Per-thread transport state prevents concurrent calls mixing failure reasons.

Configuration health separately reports missing credentials and missing explicit
model IDs. Configured means configured, not available, tested, funded or free.
Live catalog availability and pricing remain unverified. No catalog/model calls
are made as a side effect of startup or health requests.

The 23 October primary-document review identifies the legacy Sonnet 4.5 default
as deprecated, with the dated model's retirement scheduled for 30 November 2026.
Health reports this dated review and source, not a live guarantee. The configured
model is not silently changed. Groq currently lists GPT-OSS 120B with metered
pricing; availability in a public list is not proof of free account quota.

Database admission remains fail-closed and bounded. A denied admission counts no
provider call or billed usage; diagnostics count it separately. The existing
reservation, tenant isolation, atomic quota and token-accounting tests remain.
Built-in fallback reports its actual deterministic source, never simulated model
success. Unsupported model-only work must remain unavailable.

## Evidence and limits

Mocked contract tests exercise status codes, machine codes, malformed responses,
network/timeout errors, thread isolation, quota gates and recipient boundaries.
No live provider, email, paid call or credential configuration is used. Provider
error contracts differ: unrecognized codes stay generic rather than inferred
from free-text messages. This does not certify the availability of any model ID.

Primary references checked 23 October 2026:
[OpenAI errors](https://developers.openai.com/api/docs/guides/error-codes),
[Claude errors](https://platform.claude.com/docs/en/api/errors),
[Groq deprecations](https://console.groq.com/docs/deprecations).
Lifecycle/pricing review:
[Claude lifecycle](https://platform.claude.com/docs/en/about-claude/model-deprecations),
[Groq model listing](https://console.groq.com/docs/models).
The [capability manifest](../implementation/model-resilience-manifest.json)
separates code support from production acceptance.
