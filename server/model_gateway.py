"""Provider-neutral model gateway.

LLMs may phrase and summarize; they never calculate. Every number in a
report comes from deterministic code, and the gateway is only offered the
already-computed facts — never the dataset. With no provider configured
(the default, and always in tests/CI) a deterministic template is used, so
the application is fully functional offline and no test needs credentials.

Five providers, chosen by environment variable, in priority order:

- **ollama** — an open-source model through Ollama's chat API. On the
  operator's own machine (the default host) nothing leaves it. A hosted
  Ollama endpoint (OLLAMA_HOST pointing elsewhere, with OLLAMA_API_KEY) is
  treated like any hosted provider: it ranks after Claude and OpenAI and
  can fail over. Hosted open-source models also come through Groq.
  (OLLAMA_MODEL, optional OLLAMA_HOST). No key, no account, and the facts
  never leave the host. Preferred when set, because it is the only option
  that sends nothing anywhere.
- **anthropic** — Claude via ANTHROPIC_API_KEY (+ ANTHROPIC_MODEL).
- **openai** — OPENAI_API_KEY with an explicit OPENAI_MODEL; no OpenAI
  model is selected implicitly.
- **groq** — GROQ_API_KEY (+ GROQ_MODEL).
- **vercel** — an explicit AI_GATEWAY_MODEL and deployment OIDC token
  or AI_GATEWAY_API_KEY. No hosted model is selected implicitly.

When the chosen hosted provider fails, the next configured hosted one is
tried once before the deterministic narrator (failover), so one provider's
outage does not silence the model.

Keys are read server-side only. They are never logged, stored, or sent to
the browser, and any provider failure degrades to the deterministic
narrator, which is reported honestly as the source in the report itself.
"""

import os
import re
import math
import threading
import time
from collections import deque

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
# Hosted open-source models behind the same chat-completions contract
# (ADR 2026-10-22 free open models and the task map). Each needs its key
# and an explicit model id: free model ids rotate, so none is chosen here.
COMPAT_PROVIDERS = {
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions",
                   "OPENROUTER_API_KEY", "OPENROUTER_MODEL"),
    "nvidia": ("https://integrate.api.nvidia.com/v1/chat/completions",
               "NVIDIA_API_KEY", "NVIDIA_MODEL"),
    "mistral": ("https://api.mistral.ai/v1/chat/completions",
                "MISTRAL_API_KEY", "MISTRAL_MODEL"),
    "cerebras": ("https://api.cerebras.ai/v1/chat/completions",
                 "CEREBRAS_API_KEY", "CEREBRAS_MODEL"),
}
# The tasks a model can be mapped to. narration and chat are the gateway's
# own; hermes, agents and consultants are the model roles.
TASKS = ("narration", "chat", "hermes", "agents", "consultants")
AI_GATEWAY_URL = "https://ai-gateway.vercel.sh/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1"
TIMEOUT_SECONDS = 12
MAX_OUTPUT_TOKENS = 220
# Local models get a larger budget than the metered ones: reasoning models
# (qwen3, deepseek-r1, …) spend tokens thinking before they answer, and a
# 220-token cap would be exhausted by the scratchpad, leaving no summary.
LOCAL_OUTPUT_TOKENS = 600

# The in-process model call ledger keeps this many recent attempts.
LEDGER_ENTRIES = 500

# Reasoning models wrap their scratchpad in <think> tags. That is working
# out loud, not an executive summary: it never belongs in a report.
THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# The house style the narrator must follow. A finding that cannot be
# communicated cannot drive action, so plain language is part of the
# contract with the model — and it is checked afterwards regardless
# (analytics.validator.claims_avoid_statistical_jargon).
SYSTEM_PROMPT = (
    "You write two-sentence executive summaries for business readers — a "
    "board, an executive, an investor. Use ONLY the verified facts provided. "
    "Never add numbers, causes, predictions, or claims of your own. Write in "
    "plain business language: say “costs are rising”, never “the mean "
    "increased by 2.3 standard deviations”; say “the data strongly suggests "
    "maintenance is the main cost driver”, never “p < 0.05”. No statistical "
    "vocabulary, no hedging about methodology."
)

# Added for a report written in Arabic (ADR 0022). The facts arrive in
# Arabic already; the instruction is about register and about figures,
# because a model rewriting 1,234.56 as ١٬٢٣٤٫٥٦ or rounding it would break
# the report's promise that its figures are the calculated ones.
ARABIC_INSTRUCTION = (
    " Write the summary in Arabic, in the formal register of a Gulf business "
    "report. Copy every number exactly as it appears in the facts, with the "
    "same digits (0-9), separators and percent signs."
)


def split_spec(spec):
    """"ollama:hermes3" -> ("ollama", "hermes3"); "groq" -> ("groq", None).

    The provider is everything before the first colon, so a model id that
    itself contains colons ("qwen3:4b", "some/model:free") survives whole.
    The provider is case-insensitive; the model id is kept as written."""
    name, _, model = (spec or "").strip().partition(":")
    return name.strip().lower(), (model.strip() or None)


def _is_loopback(url):
    """True when the Ollama host is this machine, the only case in which
    a call sends nothing anywhere."""
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    return host in ("localhost", "::1") or host.startswith("127.")


class ModelGateway:
    def __init__(self, env=None):
        env = os.environ if env is None else env
        # Keep the mapping live: deployment OIDC credentials can rotate.
        self._env = env
        self.ai_gateway_model = env.get("AI_GATEWAY_MODEL") or None
        self.ollama_model = env.get("OLLAMA_MODEL") or None
        self.ollama_host = env.get("OLLAMA_HOST") or DEFAULT_OLLAMA_HOST
        # A hosted Ollama endpoint takes a bearer key; a local one needs none.
        self.ollama_key = env.get("OLLAMA_API_KEY") or None
        self.ollama_local = _is_loopback(self.ollama_host)
        self.anthropic_key = env.get("ANTHROPIC_API_KEY") or None
        self.anthropic_model = env.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        self.openai_key = env.get("OPENAI_API_KEY") or None
        self.openai_model = env.get("OPENAI_MODEL") or None
        self.groq_key = env.get("GROQ_API_KEY") or None
        self.compat = {name: (url, env.get(key_var), env.get(model_var))
                       for name, (url, key_var, model_var) in COMPAT_PROVIDERS.items()
                       if env.get(key_var) and env.get(model_var)}
        self.groq_model = env.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
        # CPU-hosted models need a bounded cold-start window. Hosted defaults
        # remain unchanged; callers can explicitly allow up to one minute.
        try:
            timeout = float(env.get("AGENTIC_OS_MODEL_TIMEOUT_SECONDS", TIMEOUT_SECONDS))
            self.timeout = min(60, max(1, timeout)) if math.isfinite(timeout) else TIMEOUT_SECONDS
        except (TypeError, ValueError):
            self.timeout = TIMEOUT_SECONDS
        # On Vercel the function itself has 30 s (vercel.json), and a call
        # may time out twice; a longer configured timeout would cut the
        # request off mid-answer instead (assessment B13).
        if env.get("VERCEL"):
            self.timeout = min(self.timeout, TIMEOUT_SECONDS)
        thinking = str(env.get("OLLAMA_THINK", "")).lower()
        self.ollama_think = (False if thinking in ("0", "false")
                             else True if thinking in ("1", "true") else None)
        self.ollama_options = {}
        for variable, option, low, high, default in (
                ("OLLAMA_CONTEXT_LENGTH", "num_ctx", 512, 8192, 4096),
                ("OLLAMA_NUM_THREAD", "num_thread", 1, 16, 6)):
            if variable in env:
                try:
                    value = int(env[variable])
                except (TypeError, ValueError):
                    value = default
                self.ollama_options[option] = min(high, max(low, value))
        if "OLLAMA_TEMPERATURE" in env:
            try:
                temperature = float(env["OLLAMA_TEMPERATURE"])
            except (TypeError, ValueError):
                temperature = 0.2
            if not math.isfinite(temperature):
                temperature = 0.2
            self.ollama_options["temperature"] = min(2, max(0, temperature))

        # Local first: it is the only provider that sends nothing off the
        # machine, so it wins when the operator has configured one. A hosted
        # Ollama endpoint has no such claim and ranks with the hosted ones.
        if self.ollama_model and self.ollama_local:
            self.provider, self.model = "ollama", self.ollama_model
        elif self.anthropic_key:
            self.provider, self.model = "anthropic", self.anthropic_model
        elif self.openai_key and self.openai_model:
            self.provider, self.model = "openai", self.openai_model
        elif self.ollama_model:
            self.provider, self.model = "ollama", self.ollama_model
        elif self.groq_key:
            self.provider, self.model = "groq", self.groq_model
        elif self.compat:
            name = next(iter(self.compat))
            self.provider, self.model = name, self.compat[name][2]
        elif self.ai_gateway_model and self._ai_gateway_token():
            self.provider, self.model = "vercel", self.ai_gateway_model
        else:
            self.provider, self.model = "deterministic", None

        self.task_map, self.task_problems = self._read_task_map(
            env.get("AGENTIC_OS_TASK_MODELS") or "")
        # The call ledger (assessment finding G4): one entry per provider
        # attempt and running totals per provider. Shared by the copies
        # `with_model` makes, so every role's calls land in one record.
        self._ledger_lock = threading.Lock()
        self._ledger_entries = deque(maxlen=LEDGER_ENTRIES)
        self._ledger_totals = {}
        # The task a call serves, per thread, so the completers (which
        # tests and roles may replace) keep their signatures.
        self._ledger_task = threading.local()

    def _read_task_map(self, raw):
        """AGENTIC_OS_TASK_MODELS, e.g. "narration=groq,chat=openrouter,
        consultants=anthropic+openai": which configured provider serves
        each task. An unknown task or a provider that is not configured is
        reported and skipped, never guessed."""
        reachable = {entry["provider"] for entry in self.providers()}
        mapping, problems = {}, []
        for item in raw.split(","):
            if not item.strip():
                continue
            task, _, names = item.partition("=")
            task = task.strip().lower()
            if task not in TASKS:
                problems.append(f"AGENTIC_OS_TASK_MODELS: unknown task {task!r}; skipped.")
                continue
            chosen = []
            for spec in names.split("+"):
                name, model = split_spec(spec)
                if not name:
                    continue
                if name not in reachable or name == "deterministic":
                    problems.append(f"AGENTIC_OS_TASK_MODELS: {task}={name} is not a "
                                    "configured provider; skipped.")
                    continue
                spec = f"{name}:{model}" if model else name
                if spec not in chosen:
                    chosen.append(spec)
            if chosen:
                mapping[task] = chosen
        return mapping, problems

    def with_model(self, provider, model):
        """A copy of this gateway whose `provider` answers with `model`
        instead of its configured one: how one Ollama serves Hermes with
        hermes3 and the agents with qwen3. The original is untouched, so
        parallel callers never see each other's choice."""
        import copy
        clone = copy.copy(self)
        if provider == "ollama":
            clone.ollama_model = model
        elif provider == "anthropic":
            clone.anthropic_model = model
        elif provider == "openai":
            clone.openai_model = model
        elif provider == "groq":
            clone.groq_model = model
        elif provider == "vercel":
            clone.ai_gateway_model = model
        elif provider in self.compat:
            url, key, _ = self.compat[provider]
            clone.compat = {**self.compat, provider: (url, key, model)}
        return clone

    def _resolve(self, spec):
        """(gateway, provider) for a "provider" or "provider:model" spec."""
        name, model = split_spec(spec)
        if not name:
            return self, None
        return (self.with_model(name, model) if model else self), name

    def task_provider(self, task):
        """The provider mapped to a task, or None for the default."""
        chosen = getattr(self, "task_map", {}).get(task)
        return chosen[0] if chosen else None

    def status(self):
        return {
            "provider": self.provider,
            "model": self.model,
            "configured": self.provider != "deterministic",
            # Stated plainly because it is the question that matters: does
            # anything leave this machine?
            "local_only": (self.provider == "deterministic"
                           or (self.provider == "ollama" and self.ollama_local)),
        }

    def providers(self):
        """Every provider this gateway could actually reach, in the order
        it would pick them.

        The constructor collapses these to one by priority, which is the
        right default and the wrong amount of information for anything
        that wants to choose per report (see server/routing.py).
        """
        found = []
        if self.ollama_model and self.ollama_local:
            found.append({"provider": "ollama", "model": self.ollama_model,
                          "local_only": True})
        if self.anthropic_key:
            found.append({"provider": "anthropic", "model": self.anthropic_model,
                          "local_only": False})
        if self.openai_key and self.openai_model:
            found.append({"provider": "openai", "model": self.openai_model,
                          "local_only": False})
        if self.ollama_model and not self.ollama_local:
            found.append({"provider": "ollama", "model": self.ollama_model,
                          "local_only": False})
        if self.groq_key:
            found.append({"provider": "groq", "model": self.groq_model,
                          "local_only": False})
        for name, (_, _, model) in self.compat.items():
            found.append({"provider": name, "model": model, "local_only": False})
        if self.ai_gateway_model and self._ai_gateway_token():
            found.append({"provider": "vercel", "model": self.ai_gateway_model,
                          "local_only": False})
        # Always reachable, always last: it needs nothing and never fails.
        found.append({"provider": "deterministic", "model": None,
                      "local_only": True})
        return found

    def narrate(self, goal, facts, provider=None, language="en", task=None):
        """Return {'text', 'source'}. Facts are short verified statements;
        the model is asked only to phrase them.

        `provider` overrides the priority order for this call. The gateway
        could always reach all three; until now nothing could ask it for
        a particular one.

        `language` is the report's language; the facts are already in it.
        A "provider:model" spec (or task map entry) picks that model.
        `task` names the role the call serves in the ledger; narration
        when the call site says nothing.
        """
        task = task or "narration"
        gateway, provider = self._resolve(provider or self.task_provider("narration"))
        if gateway is not self:
            return gateway.narrate(goal, facts, provider=provider, language=language,
                                   task=task)
        self._ledger_task.name = task
        callers = {"ollama": self._call_ollama,
                   "vercel": self._call_vercel,
                   "anthropic": self._call_anthropic,
                   "openai": self._call_openai,
                   "groq": self._call_groq,
                   **{name: self._compat_caller(name) for name in self.compat}}
        for name in self._attempts(provider):
            caller = callers.get(name)
            if caller is None:
                continue
            text = (caller(goal, facts, language=language) if language != "en"
                    else caller(goal, facts))
            if text:
                return {"text": text, "source": "model"}
        summary = " ".join(facts[:4])
        if language == "ar":
            return {"text": f"تحليل الهدف «{goal}»: {summary}",
                    "source": "deterministic"}
        return {
            "text": f"Analysis of the goal “{goal}”: {summary}",
            "source": "deterministic",
        }

    def ask(self, system, user, provider=None, max_tokens=None, task=None):
        """A free-form completion: the assistant's understanding step.

        Returns the model's text, or None when no provider is configured
        or the call fails — the caller decides what "no answer" means,
        which for the assistant is "the rules decide". The same
        no-dataset rule applies: `user` is built from verified sentences
        and settings, never rows. `task` names the role in the ledger;
        chat when the call site says nothing.
        """
        task = task or "chat"
        gateway, provider = self._resolve(provider or self.task_provider("chat"))
        if gateway is not self:
            return gateway.ask(system, user, provider=provider, max_tokens=max_tokens,
                               task=task)
        self._ledger_task.name = task
        callers = {"ollama": self._complete_ollama,
                   "vercel": self._complete_vercel,
                   "anthropic": self._complete_anthropic,
                   "openai": self._complete_openai,
                   "groq": self._complete_groq,
                   **{name: self._compat_completer(name) for name in self.compat}}
        for name in self._attempts(provider):
            caller = callers.get(name)
            text = caller(system, user, max_tokens) if caller else None
            if text:
                return text
        return None

    def _attempts(self, provider=None):
        """The chosen provider, then at most one other configured hosted
        provider as failover. Two attempts at most keep a request inside a
        serverless time limit (two timeouts of TIMEOUT_SECONDS each). A
        local model is never swapped for a hosted one: choosing Ollama is
        a choice that nothing leaves the machine."""
        first = provider or self.provider
        if first == "deterministic":
            return []
        if first == "ollama" and self.ollama_local:
            return ["ollama"]
        hosted = [entry["provider"] for entry in self.providers()
                  if not entry["local_only"] and entry["provider"] != first]
        return [first] + hosted[:1]

    def _prompt(self, goal, facts):
        return "Goal: " + goal + "\nVerified facts:\n- " + "\n- ".join(facts)

    def ask_json(self, system, user, provider=None, max_tokens=None, schema=None,
                 task=None):
        """Intent-only structured output; report narration keeps plain text.

        Hosted providers retain their existing request contracts. A caller
        without this optional method can continue exposing ordinary ask.
        """
        task = task or "chat"
        gateway, provider = self._resolve(provider or self.task_provider("chat"))
        if gateway is not self:
            return gateway.ask_json(system, user, provider=provider,
                                    max_tokens=max_tokens, schema=schema, task=task)
        self._ledger_task.name = task
        if (provider or self.provider) == "ollama":
            return self._complete_ollama(system, user, max_tokens, json_output=True,
                                         schema=schema)
        if (provider or self.provider) == "vercel":
            return self._complete_vercel(system, user, max_tokens, json_output=True)
        return self.ask(system, user, provider=provider, max_tokens=max_tokens, task=task)

    def _post(self, url, headers, payload):
        try:
            import httpx

            options = {"timeout": self.timeout}
            if self.ollama_local and url == self.ollama_host.rstrip("/") + "/api/chat":
                # A loopback provider must not send verified context through
                # an ambient HTTP_PROXY. Cloud provider behavior is unchanged.
                options["trust_env"] = False
            response = httpx.post(url, headers=headers, json=payload, **options)
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            # Timeouts, network, schema drift: degrade to deterministic.
            return None

    # -- the call ledger (assessment finding G4) --------------------------
    @staticmethod
    def _count(value):
        """A token count the provider reported, or None. Never estimated."""
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    @classmethod
    def _usage(cls, provider, body):
        """(input, output, total) token counts as the response reports them.

        OpenAI-compatible replies (openai, groq, vercel and the compat
        providers) carry `usage.prompt_tokens` / `completion_tokens` /
        `total_tokens`; Anthropic carries `usage.input_tokens` /
        `output_tokens`; Ollama carries `prompt_eval_count` / `eval_count`
        at the top level. Anything missing is None.
        """
        if not isinstance(body, dict):
            return None, None, None
        if provider == "ollama":
            prompt, done = cls._count(body.get("prompt_eval_count")), cls._count(body.get("eval_count"))
            total = None
        else:
            usage = body.get("usage")
            usage = usage if isinstance(usage, dict) else {}
            if provider == "anthropic":
                prompt, done = cls._count(usage.get("input_tokens")), cls._count(usage.get("output_tokens"))
                total = None
            else:
                prompt, done = cls._count(usage.get("prompt_tokens")), cls._count(usage.get("completion_tokens"))
                total = cls._count(usage.get("total_tokens"))
        if total is None and prompt is not None and done is not None:
            total = prompt + done
        return prompt, done, total

    def _record(self, provider, model, body, text, started):
        """One ledger entry per provider attempt. `body` is the parsed
        response (None when the call failed) and `text` the cleaned reply
        (None when the reply held nothing usable). The task is the one
        narrate, ask or ask_json noted for this thread."""
        task = getattr(self._ledger_task, "name", None)
        latency_ms = round((time.monotonic() - started) * 1000, 1)
        outcome = "error" if body is None else ("ok" if text else "empty")
        prompt, done, total = self._usage(provider, body)
        entry = {"provider": provider, "model": model, "task": task,
                 "outcome": outcome, "latency_ms": latency_ms,
                 "input_tokens": prompt, "output_tokens": done, "total_tokens": total}
        with self._ledger_lock:
            self._ledger_entries.append(entry)
            totals = self._ledger_totals.setdefault(provider, {
                "calls": 0, "failures": 0, "latency_ms": 0.0,
                "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
                "calls_with_tokens": 0})
            totals["calls"] += 1
            if outcome != "ok":
                totals["failures"] += 1
            totals["latency_ms"] = round(totals["latency_ms"] + latency_ms, 1)
            if total is not None:
                totals["calls_with_tokens"] += 1
                totals["total_tokens"] += total
                totals["input_tokens"] += prompt or 0
                totals["output_tokens"] += done or 0
        return text

    def ledger(self):
        """Running totals per provider for this process: calls, failures,
        summed latency and the token counts providers reported. Token
        totals cover only `calls_with_tokens`; no count is estimated."""
        with self._ledger_lock:
            return {"entries_kept": len(self._ledger_entries),
                    "entries_limit": LEDGER_ENTRIES,
                    "providers": {name: dict(t) for name, t in self._ledger_totals.items()}}

    def ledger_entries(self):
        """The most recent attempts, oldest first. Prompts and replies are
        never kept: an entry is provider, model, task, outcome and counts."""
        with self._ledger_lock:
            return [dict(entry) for entry in self._ledger_entries]

    @staticmethod
    def _clean(text):
        if not isinstance(text, str):
            return None
        text = THINK_BLOCK.sub("", text)
        if "<think>" in text.lower():
            # An unclosed block means the reply was cut off mid-thought, so
            # everything present is scratchpad. Degrade to the deterministic
            # narrator rather than printing a model's reasoning as a summary.
            return None
        return text.strip() or None

    # The narrator's calls: the house-style system prompt over goal + facts.
    @staticmethod
    def _system(language):
        return SYSTEM_PROMPT + (ARABIC_INSTRUCTION if language == "ar" else "")

    def _call_ollama(self, goal, facts, language="en"):
        return self._complete_ollama(self._system(language), self._prompt(goal, facts),
                                     LOCAL_OUTPUT_TOKENS)

    def _call_anthropic(self, goal, facts, language="en"):
        return self._complete_anthropic(self._system(language),
                                        self._prompt(goal, facts), MAX_OUTPUT_TOKENS)

    def _call_openai(self, goal, facts, language="en"):
        return self._complete_openai(self._system(language), self._prompt(goal, facts),
                                     MAX_OUTPUT_TOKENS)

    def _call_groq(self, goal, facts, language="en"):
        return self._complete_groq(self._system(language), self._prompt(goal, facts),
                                   MAX_OUTPUT_TOKENS)

    def _ai_gateway_token(self):
        return self._env.get("AI_GATEWAY_API_KEY") or self._env.get("VERCEL_OIDC_TOKEN")

    def _call_vercel(self, goal, facts, language="en"):
        return self._complete_vercel(self._system(language), self._prompt(goal, facts),
                                     MAX_OUTPUT_TOKENS)

    def _complete_vercel(self, system, user, max_tokens=None, json_output=False):
        token = self._ai_gateway_token()
        if not token or not self.ai_gateway_model:
            return None
        payload = {"model": self.ai_gateway_model,
                   "max_tokens": max_tokens or MAX_OUTPUT_TOKENS,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        started = time.monotonic()
        body = self._post(AI_GATEWAY_URL,
                          {"Authorization": f"Bearer {token}"}, payload)
        return self._record("vercel", self.ai_gateway_model, body,
                            self._choice_text(body), started)

    @classmethod
    def _choice_text(cls, body):
        """The reply of an OpenAI-compatible response, cleaned, or None."""
        try:
            return cls._clean(body["choices"][0]["message"]["content"])
        except (TypeError, KeyError, IndexError):
            return None

    # The wire calls, one per provider, over an arbitrary system + user pair.
    def _complete_ollama(self, system, user, max_tokens=None, json_output=False, schema=None):
        payload = {"model": self.ollama_model, "stream": False,
                   "options": {"num_predict": max_tokens or LOCAL_OUTPUT_TOKENS,
                               **self.ollama_options},
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        if self.ollama_think is not None:
            payload["think"] = self.ollama_think
        if json_output:
            payload["format"] = schema if schema is not None else "json"
        started = time.monotonic()
        body = self._post(
            self.ollama_host.rstrip("/") + "/api/chat",
            {"Authorization": f"Bearer {self.ollama_key}"} if self.ollama_key else {},
            payload)
        try:
            text = self._clean(body["message"]["content"])
        except (TypeError, KeyError, IndexError):
            text = None
        return self._record("ollama", self.ollama_model, body, text, started)

    def _complete_anthropic(self, system, user, max_tokens=None):
        started = time.monotonic()
        body = self._post(
            ANTHROPIC_URL,
            {"x-api-key": self.anthropic_key,
             "anthropic-version": ANTHROPIC_VERSION,
             "content-type": "application/json"},
            {"model": self.anthropic_model,
             "max_tokens": max_tokens or MAX_OUTPUT_TOKENS,
             "system": system,
             "messages": [{"role": "user", "content": user}]})
        try:
            text = self._clean(body["content"][0]["text"])
        except (TypeError, KeyError, IndexError):
            text = None
        return self._record("anthropic", self.anthropic_model, body, text, started)

    def _complete_openai(self, system, user, max_tokens=None):
        if not (self.openai_key and self.openai_model):
            return None
        started = time.monotonic()
        body = self._post(
            OPENAI_URL, {"Authorization": f"Bearer {self.openai_key}"},
            {"model": self.openai_model,
             "max_completion_tokens": max_tokens or MAX_OUTPUT_TOKENS,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]})
        return self._record("openai", self.openai_model, body,
                            self._choice_text(body), started)

    def _compat_caller(self, name):
        def call(goal, facts, language="en"):
            return self._complete_compat(name, self._system(language),
                                         self._prompt(goal, facts), MAX_OUTPUT_TOKENS)
        return call

    def _compat_completer(self, name):
        return lambda system, user, max_tokens=None: self._complete_compat(
            name, system, user, max_tokens)

    def _complete_compat(self, name, system, user, max_tokens=None):
        if name not in self.compat:
            return None
        url, key, model = self.compat[name]
        started = time.monotonic()
        body = self._post(
            url, {"Authorization": f"Bearer {key}"},
            {"model": model, "max_tokens": max_tokens or MAX_OUTPUT_TOKENS,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]})
        return self._record(name, model, body, self._choice_text(body), started)

    def _complete_groq(self, system, user, max_tokens=None):
        started = time.monotonic()
        body = self._post(
            GROQ_URL, {"Authorization": f"Bearer {self.groq_key}"},
            {"model": self.groq_model, "max_tokens": max_tokens or MAX_OUTPUT_TOKENS,
             "messages": [{"role": "system", "content": system},
                          {"role": "user", "content": user}]})
        return self._record("groq", self.groq_model, body,
                            self._choice_text(body), started)
