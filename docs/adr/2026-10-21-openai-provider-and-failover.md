# OpenAI provider and one failover between hosted models

Date: 2026-10-21 · Status: Accepted (owner request, 21 October: "connect the
platform to my Claude and OpenAI APIs … to ensure … continuous operation")

## Context

The gateway reached Ollama, Claude, Groq and the Vercel AI Gateway, one at a
time: if the chosen provider failed, the report fell straight to the
deterministic narrator. The owner holds Claude and OpenAI accounts and asked
for both, with continuous operation. Production had no provider configured.

## Decision

1. **OpenAI is a fifth provider**, after Claude in priority. It needs
   `OPENAI_API_KEY` and an explicit `OPENAI_MODEL`: no OpenAI model id is
   chosen in code, because model names change and a guessed one fails
   silently. The request is the same chat-completions contract as Groq,
   with `max_completion_tokens`.
2. **One failover.** When the chosen hosted provider returns nothing, the
   next configured hosted provider is tried once, then the deterministic
   narrator. Two attempts at most keep a request inside Vercel's 30-second
   function limit (each call times out at 12 seconds). A local Ollama model
   never fails over to a hosted one: choosing it means nothing leaves the
   machine.
3. **Router names.** "openai", "chatgpt" and names starting "gpt-" go to
   OpenAI when it is reachable; "gpt-oss" stays with Groq, which hosts it.
4. The rules that already bound a model are unchanged: it sees verified
   facts only, never the dataset, and never calculates.

## Consequences

- With Claude and OpenAI both set, one provider's outage or exhausted
  credit no longer silences the model; the report says `model` when either
  answered and `deterministic` when neither did.
- Both are metered services billed to the owner's accounts; neither is free.
- Keys live only in the hosting environment, never in Git or chat.

## Verification

`tests/test_model_gateway.py`: OpenAI needs key and model; Claude keeps
priority; the OpenAI request carries the bearer key and its reply is read;
a failed Claude call fails over to OpenAI for narration and for `ask`; at
most two attempts, then `deterministic`; a local model is never swapped.
`tests/test_routing.py`: OpenAI names route to OpenAI and `gpt-oss` to Groq.
No live call was made: no key is available in the development container.
