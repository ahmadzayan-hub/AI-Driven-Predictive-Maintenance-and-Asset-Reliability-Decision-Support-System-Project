"""The model gateway: provider selection, and the limits on what a model
is allowed to do.

No test here touches the network. Provider calls are exercised by
substituting the one HTTP method, which is also the only place a
credential is ever used.
"""

import unittest
from unittest.mock import patch, Mock

from server.model_gateway import ModelGateway
from server.assistant import INTENT_SCHEMA


class ProviderSelectionTestCase(unittest.TestCase):
    def test_gateway_requires_explicit_model_and_credential(self):
        for env in ({}, {"VERCEL_OIDC_TOKEN": "private-token"},
                    {"AI_GATEWAY_MODEL": "provider/model"}):
            self.assertFalse(ModelGateway(env=env).status()["configured"])
        gateway = ModelGateway(env={"AI_GATEWAY_MODEL": "provider/model",
                                    "VERCEL_OIDC_TOKEN": "private-token"})
        self.assertEqual(gateway.provider, "vercel")
        self.assertFalse(gateway.status()["local_only"])
        self.assertNotIn("private-token", repr(gateway.status()))
        self.assertEqual(gateway.providers()[0]["provider"], "vercel")

    def test_gateway_does_not_replace_existing_provider(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "local-model",
                                    "AI_GATEWAY_MODEL": "provider/model",
                                    "VERCEL_OIDC_TOKEN": "private-token"})
        self.assertEqual(gateway.provider, "ollama")

    def test_no_configuration_means_deterministic_and_offline(self):
        gateway = ModelGateway(env={})
        self.assertEqual(gateway.status(),
                         {"provider": "deterministic", "model": None,
                          "configured": False, "local_only": True})
        result = gateway.narrate("the goal", ["Revenue is up 45%."])
        self.assertEqual(result["source"], "deterministic")
        self.assertIn("Revenue is up 45%.", result["text"])

    def test_ollama_wins_because_nothing_leaves_the_machine(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "llama3.1",
                                    "ANTHROPIC_API_KEY": "k", "GROQ_API_KEY": "k"})
        self.assertEqual(gateway.provider, "ollama")
        self.assertTrue(gateway.status()["local_only"])

    def test_anthropic_is_used_when_no_local_model_is_configured(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "k", "GROQ_API_KEY": "k"})
        self.assertEqual(gateway.provider, "anthropic")
        self.assertEqual(gateway.model, "claude-sonnet-4-5")
        self.assertFalse(gateway.status()["local_only"])

    def test_groq_remains_available(self):
        gateway = ModelGateway(env={"GROQ_API_KEY": "k", "GROQ_MODEL": "m"})
        self.assertEqual((gateway.provider, gateway.model), ("groq", "m"))

    def test_the_status_never_exposes_a_credential(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "secret-key-value"})
        self.assertNotIn("secret-key-value", repr(gateway.status()))


class ProviderCallTestCase(unittest.TestCase):
    """Each provider's request shape and response parsing, without a network."""

    def gateway_with(self, env, response):
        gateway = ModelGateway(env=env)
        self.sent = {}

        def fake_post(url, headers, payload):
            self.sent = {"url": url, "headers": headers, "payload": payload}
            return response

        gateway._post = fake_post
        return gateway

    def test_gateway_rotated_oidc_is_read_for_each_request(self):
        env = {"AI_GATEWAY_MODEL": "provider/model", "VERCEL_OIDC_TOKEN": "old"}
        gateway = self.gateway_with(env, {"choices": [{"message": {"content": "Ready."}}]})
        env["VERCEL_OIDC_TOKEN"] = "new"
        self.assertEqual(gateway.ask("system", "hello"), "Ready.")
        self.assertEqual(self.sent["url"], "https://ai-gateway.vercel.sh/v1/chat/completions")
        self.assertEqual(self.sent["headers"]["Authorization"], "Bearer new")
        self.assertNotIn("response_format", self.sent["payload"])
        gateway.ask_json("Return JSON.", "hello", max_tokens=80)
        self.assertEqual(self.sent["payload"]["response_format"], {"type": "json_object"})
        self.assertEqual(self.sent["payload"]["max_tokens"], 80)

    def test_gateway_api_key_precedes_oidc_and_narration_stays_plain(self):
        gateway = self.gateway_with(
            {"AI_GATEWAY_MODEL": "provider/model", "VERCEL_OIDC_TOKEN": "oidc",
             "AI_GATEWAY_API_KEY": "explicit-key"},
            {"choices": [{"message": {"content": "Costs rose."}}]})
        self.assertEqual(gateway.narrate("goal", ["Costs rose."])["source"], "model")
        self.assertEqual(self.sent["headers"]["Authorization"], "Bearer explicit-key")
        self.assertNotIn("response_format", self.sent["payload"])

    def test_gateway_failure_keeps_truthful_fallback(self):
        gateway = self.gateway_with(
            {"AI_GATEWAY_MODEL": "provider/model", "VERCEL_OIDC_TOKEN": "oidc"}, None)
        self.assertIsNone(gateway.ask("system", "hello"))
        self.assertEqual(gateway.narrate("goal", ["Verified fact."])["source"], "deterministic")

    def test_ollama_posts_to_the_local_host_and_reads_its_reply(self):
        gateway = self.gateway_with(
            {"OLLAMA_MODEL": "llama3.1", "OLLAMA_HOST": "http://127.0.0.1:11434"},
            {"message": {"content": "  Costs are rising.  "}})
        result = gateway.narrate("goal", ["Costs rose 12%."])
        self.assertEqual(result, {"text": "Costs are rising.", "source": "model"})
        self.assertEqual(self.sent["url"], "http://127.0.0.1:11434/api/chat")
        self.assertEqual(self.sent["headers"], {})  # no credential, none needed
        self.assertFalse(self.sent["payload"]["stream"])

    def test_json_mode_is_used_only_for_intents_not_narration_or_ordinary_ask(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "m"},
                                    {"message": {"content": '{"action":"chat","reply":"Useful."}'}})
        gateway.ask_json("system", "conceptual question", max_tokens=600)
        self.assertEqual(self.sent["payload"]["format"], "json")
        self.assertEqual(self.sent["payload"]["options"]["num_predict"], 600)
        gateway.narrate("goal", ["A verified fact."])
        self.assertNotIn("format", self.sent["payload"])

    def test_intent_schema_is_sent_to_ollama_without_changing_plain_text_calls(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "m"},
                                    {"message": {"content": '{"action":"chat","arguments":{},"reply":"Useful."}'}})
        self.assertTrue(gateway.ask_json("system", "question", max_tokens=600, schema=INTENT_SCHEMA))
        self.assertEqual(self.sent["payload"]["format"], INTENT_SCHEMA)
        gateway.narrate("goal", ["A verified fact."])
        self.assertNotIn("format", self.sent["payload"])
        gateway.ask("system", "ordinary runtime question")
        self.assertNotIn("format", self.sent["payload"])

    def test_hosted_json_intent_uses_each_providers_own_json_mode(self):
        # Assessment G5: the OpenAI-compatible providers take
        # response_format; Anthropic has no JSON switch and is asked in text.
        gateway = self.gateway_with({"ANTHROPIC_API_KEY": "test"}, {"content": [{"text": "{}"}]})
        gateway.ask("system", "user", max_tokens=400)
        ordinary = self.sent
        gateway.ask_json("system", "user", max_tokens=400, schema=INTENT_SCHEMA)
        self.assertEqual(self.sent, ordinary)
        for environment, response in (({"GROQ_API_KEY": "test"}, {"choices": [{"message": {"content": "{}"}}]}),
                                       ({"OPENAI_API_KEY": "test", "OPENAI_MODEL": "m"},
                                        {"choices": [{"message": {"content": "{}"}}]})):
            with self.subTest(provider=environment):
                gateway = self.gateway_with(environment, response)
                gateway.ask("system", "user", max_tokens=400)
                self.assertNotIn("response_format", self.sent["payload"])
                gateway.ask_json("system", "user", max_tokens=400, schema=INTENT_SCHEMA)
                self.assertEqual(self.sent["payload"]["response_format"], {"type": "json_object"})
                self.assertNotIn("format", self.sent["payload"])

    def test_anthropic_sends_the_versioned_header_and_reads_its_reply(self):
        gateway = self.gateway_with({"ANTHROPIC_API_KEY": "k"},
                                    {"content": [{"text": "Costs are rising."}]})
        result = gateway.narrate("goal", ["Costs rose 12%."])
        self.assertEqual(result["source"], "model")
        self.assertEqual(self.sent["headers"]["x-api-key"], "k")
        self.assertIn("anthropic-version", self.sent["headers"])

    def test_the_narrator_is_told_to_write_in_business_language(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "m"},
                                    {"message": {"content": "ok"}})
        gateway.narrate("goal", ["A fact."])
        system = self.sent["payload"]["messages"][0]["content"]
        self.assertIn("plain business language", system)
        self.assertIn("standard deviations", system)  # named as what NOT to write

    def test_only_verified_facts_are_sent__never_the_dataset(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "m"},
                                    {"message": {"content": "ok"}})
        gateway.narrate("Analyze sales", ["Total revenue is 3,583,440."])
        payload = repr(self.sent["payload"])
        self.assertIn("Total revenue is 3,583,440.", payload)
        # The prompt is the goal plus the fact list, and nothing else.
        user = self.sent["payload"]["messages"][1]["content"]
        self.assertEqual(user, "Goal: Analyze sales\nVerified facts:\n"
                               "- Total revenue is 3,583,440.")

    def test_a_reasoning_model_s_scratchpad_never_reaches_the_report(self):
        """qwen3, deepseek-r1 and friends think out loud in <think> tags.
        That is not an executive summary."""
        gateway = self.gateway_with(
            {"OLLAMA_MODEL": "qwen3:4b"},
            {"message": {"content":
                         "<think>The user wants a summary. Revenue rose 45%, so I "
                         "should lead with that. Let me check the numbers again…"
                         "</think>\n\nRevenue is up sharply, led by the North region."}})
        result = gateway.narrate("goal", ["Revenue rose 45%."])
        self.assertEqual(result["text"], "Revenue is up sharply, led by the North region.")
        self.assertNotIn("<think>", result["text"])
        self.assertNotIn("check the numbers again", result["text"])

    def test_a_reply_cut_off_mid_thought_falls_back_rather_than_leaking(self):
        gateway = self.gateway_with(
            {"OLLAMA_MODEL": "qwen3:4b"},
            {"message": {"content": "<think>Let me work through this. First the total"}})
        result = gateway.narrate("goal", ["Revenue rose 45%."])
        self.assertEqual(result["source"], "deterministic")
        self.assertNotIn("<think>", result["text"])

    def test_local_models_get_a_bigger_token_budget_to_think_with(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "qwen3:4b"},
                                    {"message": {"content": "ok"}})
        gateway.narrate("goal", ["A fact."])
        self.assertEqual(self.sent["payload"]["options"]["num_predict"], 600)

    def test_cpu_install_can_disable_reasoning_without_changing_provider_defaults(self):
        gateway = self.gateway_with({"OLLAMA_MODEL": "qwen3:4b", "OLLAMA_THINK": "0"},
                                    {"message": {"content": "Ready."}})
        self.assertEqual(gateway.ask("system", "user"), "Ready.")
        self.assertIs(self.sent["payload"]["think"], False)
        gateway = self.gateway_with({"OLLAMA_MODEL": "m"},
                                    {"message": {"content": "Ready."}})
        gateway.ask("system", "user")
        self.assertNotIn("think", self.sent["payload"])

    def test_timeout_is_bounded_and_invalid_configuration_keeps_default(self):
        for value, expected in (("45", 45), ("999", 60), ("0", 1),
                                ("bad", 12), ("nan", 12), ("inf", 12)):
            with self.subTest(value=value):
                self.assertEqual(ModelGateway(env={"AGENTIC_OS_MODEL_TIMEOUT_SECONDS": value}).timeout,
                                 expected)

    def test_local_context_bypasses_ambient_proxies(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "m"})
        response = Mock(status_code=200)
        response.json.return_value = {"message": {"content": "Ready."}}
        with patch("httpx.post", return_value=response) as post:
            self.assertEqual(gateway.ask("system", "private verified facts"), "Ready.")
            self.assertIs(post.call_args.kwargs["trust_env"], False)

    def test_explicit_local_resource_settings_are_bounded(self):
        for context, threads, expected in (("99999", "999", (8192, 16)),
                                           ("invalid", "invalid", (4096, 6))):
            with self.subTest(context=context):
                gateway = self.gateway_with({"OLLAMA_MODEL": "m", "OLLAMA_CONTEXT_LENGTH": context,
                                             "OLLAMA_NUM_THREAD": threads,
                                             "OLLAMA_TEMPERATURE": "nan"},
                                            {"message": {"content": "Ready."}})
                gateway.ask("system", "user")
                options = self.sent["payload"]["options"]
                self.assertEqual((options["num_ctx"], options["num_thread"]), expected)
                self.assertEqual(options["temperature"], 0.2)

    def test_a_provider_failure_degrades_to_deterministic_and_says_so(self):
        for response in (None, {}, {"content": []}, {"message": {"content": "   "}}):
            with self.subTest(response=response):
                gateway = self.gateway_with({"OLLAMA_MODEL": "m"}, response)
                result = gateway.narrate("goal", ["A verified fact."])
                self.assertEqual(result["source"], "deterministic")
                self.assertIn("A verified fact.", result["text"])


if __name__ == "__main__":
    unittest.main()


class OpenAiAndFailoverTestCase(unittest.TestCase):
    """OpenAI next to Claude, and one failover so a provider outage does
    not silence the model."""

    def reply(self, text):
        return {"choices": [{"message": {"content": text}}]}

    def test_openai_needs_a_key_and_an_explicit_model(self):
        self.assertEqual(ModelGateway(env={"OPENAI_API_KEY": "k"}).provider, "deterministic")
        gateway = ModelGateway(env={"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"})
        self.assertEqual((gateway.provider, gateway.model), ("openai", "m"))
        self.assertNotIn("k\"", repr(gateway.status()))

    def test_claude_keeps_priority_over_openai(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o",
                                    "OPENAI_MODEL": "m"})
        self.assertEqual(gateway.provider, "anthropic")
        self.assertEqual([p["provider"] for p in gateway.providers()],
                         ["anthropic", "openai", "deterministic"])

    def test_openai_request_carries_the_bearer_key_and_reads_its_reply(self):
        gateway = ModelGateway(env={"OPENAI_API_KEY": "secret", "OPENAI_MODEL": "m"})
        with patch.object(gateway, "_post", return_value=self.reply("Costs are rising.")) as post:
            result = gateway.narrate("goal", ["Costs rose 4%."])
        url, headers, payload = post.call_args.args
        self.assertEqual(url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(headers, {"Authorization": "Bearer secret"})
        self.assertEqual(payload["model"], "m")
        self.assertEqual(result, {"text": "Costs are rising.", "source": "model"})

    def test_explicit_edge_allows_one_claude_to_openai_attempt(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o",
                                    "OPENAI_MODEL": "m", "AGENTIC_OS_MODEL_FAILOVER": "anthropic>openai"})
        replies = [None, self.reply("Costs are rising.")]
        with patch.object(gateway, "_post", side_effect=replies) as post:
            result = gateway.narrate("goal", ["Costs rose 4%."])
        self.assertEqual(post.call_count, 2)
        self.assertIn("anthropic.com", post.call_args_list[0].args[0])
        self.assertIn("openai.com", post.call_args_list[1].args[0])
        self.assertEqual(result["source"], "model")
        with patch.object(gateway, "_post", side_effect=replies[:1] + [self.reply("ok")]):
            self.assertEqual(gateway.ask("s", "u"), "ok")

    def test_failover_stops_after_two_attempts_then_says_deterministic(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o",
                                    "OPENAI_MODEL": "m", "GROQ_API_KEY": "g", "AGENTIC_OS_MODEL_FAILOVER": "anthropic>openai,openai>groq"})
        with patch.object(gateway, "_post", return_value=None) as post:
            result = gateway.narrate("goal", ["Costs rose 4%."])
        self.assertEqual(post.call_count, 2)
        self.assertEqual(result["source"], "deterministic")

    def test_a_local_model_is_never_swapped_for_a_hosted_one(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "llama3.1", "OPENAI_API_KEY": "o",
                                    "OPENAI_MODEL": "m"})
        with patch.object(gateway, "_post", return_value=None) as post:
            gateway.narrate("goal", ["Costs rose 4%."])
        self.assertEqual(post.call_count, 1)
        self.assertIn("11434", post.call_args.args[0])


class HostedOllamaTestCase(unittest.TestCase):
    """Open-source models on a hosted Ollama endpoint: reachable from a
    serverless deployment, and never described as staying on the machine."""

    HOSTED = {"OLLAMA_MODEL": "an-open-model", "OLLAMA_HOST": "https://ollama.example.com",
              "OLLAMA_API_KEY": "secret"}

    def test_a_hosted_endpoint_sends_the_key_and_uses_the_proxy(self):
        gateway = ModelGateway(env=self.HOSTED)
        reply = Mock(status_code=200, json=lambda: {"message": {"content": "Costs are rising."}})
        with patch("httpx.post", return_value=reply) as post:
            result = gateway.narrate("goal", ["Costs rose 4%."])
        url, = post.call_args.args
        self.assertEqual(url, "https://ollama.example.com/api/chat")
        self.assertEqual(post.call_args.kwargs["headers"], {"Authorization": "Bearer secret"})
        self.assertNotIn("trust_env", post.call_args.kwargs)
        self.assertEqual(result["source"], "model")

    def test_a_hosted_endpoint_is_not_local_and_ranks_after_claude(self):
        gateway = ModelGateway(env=self.HOSTED)
        self.assertEqual(gateway.provider, "ollama")
        self.assertFalse(gateway.status()["local_only"])
        both = ModelGateway(env={**self.HOSTED, "ANTHROPIC_API_KEY": "a"})
        self.assertEqual(both.provider, "anthropic")
        self.assertEqual([p["provider"] for p in both.providers()],
                         ["anthropic", "ollama", "deterministic"])

    def test_a_hosted_endpoint_may_fail_over_and_a_local_one_may_not(self):
        hosted = ModelGateway(env={**self.HOSTED, "ANTHROPIC_API_KEY": "a", "AGENTIC_OS_MODEL_FAILOVER": "ollama>anthropic"})
        self.assertEqual(hosted._attempts("ollama"), ["ollama", "anthropic"])
        local = ModelGateway(env={"OLLAMA_MODEL": "m", "ANTHROPIC_API_KEY": "a"})
        self.assertEqual(local._attempts("ollama"), ["ollama"])
        self.assertTrue(local.status()["local_only"])

    def test_the_status_never_shows_the_key(self):
        self.assertNotIn("secret", repr(ModelGateway(env=self.HOSTED).status()))


class FreeOpenModelsAndTaskMapTestCase(unittest.TestCase):
    """Hosted open-source providers on the chat-completions contract, and
    one map from each AI task to the provider that serves it."""

    def reply(self, text):
        return {"choices": [{"message": {"content": text}}]}

    def test_each_open_provider_needs_a_key_and_an_explicit_model(self):
        self.assertEqual(ModelGateway(env={"OPENROUTER_API_KEY": "k"}).provider, "deterministic")
        gateway = ModelGateway(env={"OPENROUTER_API_KEY": "k", "OPENROUTER_MODEL": "some/model:free"})
        self.assertEqual((gateway.provider, gateway.model), ("openrouter", "some/model:free"))
        self.assertNotIn("k'", repr(gateway.status()))

    def test_the_request_goes_to_that_provider_with_its_key(self):
        from server.model_gateway import COMPAT_PROVIDERS
        for name, (url, key_var, model_var) in COMPAT_PROVIDERS.items():
            gateway = ModelGateway(env={key_var: "secret", model_var: "m"})
            with patch.object(gateway, "_post", return_value=self.reply("Costs are rising.")) as post:
                result = gateway.narrate("goal", ["Costs rose 4%."])
            self.assertEqual(post.call_args.args[0], url, name)
            self.assertEqual(post.call_args.args[1], {"Authorization": "Bearer secret"}, name)
            self.assertEqual(result["source"], "model", name)

    def test_the_task_map_sends_each_task_to_its_provider(self):
        env = {"GROQ_API_KEY": "g", "OPENROUTER_API_KEY": "o", "OPENROUTER_MODEL": "m",
               "AGENTIC_OS_TASK_MODELS": "narration=openrouter, chat=groq"}
        gateway = ModelGateway(env=env)
        with patch.object(gateway, "_post", return_value=self.reply("ok")) as post:
            gateway.narrate("goal", ["Costs rose 4%."])
            self.assertIn("openrouter.ai", post.call_args.args[0])
            gateway.ask("system", "user")
            self.assertIn("groq.com", post.call_args.args[0])
            gateway.ask_json("system", "user")
            self.assertIn("groq.com", post.call_args.args[0])
        self.assertEqual(gateway.task_problems, [])

    def test_a_wrong_task_or_provider_is_reported_not_guessed(self):
        gateway = ModelGateway(env={"GROQ_API_KEY": "g",
                                    "AGENTIC_OS_TASK_MODELS": "narration=nvidia,poetry=groq,chat=groq"})
        self.assertEqual(gateway.task_map, {"chat": ["groq"]})
        self.assertEqual(len(gateway.task_problems), 2)

    def test_the_roles_and_the_health_map_follow_the_task_map(self):
        from server.orchestration import ModelRoles
        env = {"GROQ_API_KEY": "g", "OPENROUTER_API_KEY": "o", "OPENROUTER_MODEL": "m",
               "AGENTIC_OS_TASK_MODELS": "hermes=groq,agents=openrouter,consultants=groq+openrouter"}
        gateway = ModelGateway(env=env)
        roles = ModelRoles(gateway, env)
        self.assertEqual((roles.hermes, roles.agents, roles.consultants),
                         ("groq", "openrouter", ["groq", "openrouter"]))
        mapping = roles.model_map()
        self.assertEqual(mapping["narration"], "groq")
        self.assertEqual(mapping["consultants"], ["groq", "openrouter"])
        empty = ModelRoles(ModelGateway(env={}), {}).model_map()
        self.assertEqual((empty["narration"], empty["hermes"], empty["consultants"]),
                         ("built-in", "built-in", ["built-in"]))
        self.assertTrue(empty["built_in_fallback"])
        off = {"AGENTIC_OS_BUILT_IN_ROLES": "0"}
        self.assertEqual(ModelRoles(ModelGateway(env=off), off).model_map()["consultants"],
                         ["none"])


class PerRoleModelTestCase(unittest.TestCase):
    """"provider:model" gives one provider a different model per role:
    Hermes on a local hermes3 while the agents use a local qwen3."""

    LOCAL = {"OLLAMA_MODEL": "qwen3:4b",
             "AGENTIC_OS_TASK_MODELS": "hermes=ollama:hermes3,agents=ollama:qwen3:4b,"
                                       "consultants=ollama:hermes3+ollama:qwen3:4b"}

    @staticmethod
    def answer(gateway, url, headers, payload):
        return {"message": {"content": f"Answered by {payload['model']}."}}

    def test_a_spec_splits_at_the_first_colon_only(self):
        from server.model_gateway import split_spec
        self.assertEqual(split_spec("ollama:qwen3:4b"), ("ollama", "qwen3:4b"))
        self.assertEqual(split_spec(" OpenRouter:Some/Model:free "),
                         ("openrouter", "Some/Model:free"))
        self.assertEqual(split_spec("groq"), ("groq", None))
        self.assertEqual(split_spec(""), ("", None))

    def test_each_role_reaches_the_same_ollama_with_its_own_model(self):
        from server.orchestration import ModelRoles
        gateway = ModelGateway(env=self.LOCAL)
        roles = ModelRoles(gateway, self.LOCAL)
        self.assertEqual((roles.hermes, roles.agents, roles.consultants),
                         ("ollama:hermes3", "ollama:qwen3:4b",
                          ["ollama:hermes3", "ollama:qwen3:4b"]))
        with patch.object(ModelGateway, "_post", autospec=True,
                          side_effect=self.answer) as post:
            self.assertEqual(gateway.ask("s", "u", provider=roles.hermes), "Answered by hermes3.")
            narration = gateway.narrate("goal", ["Costs rose."], provider=roles.agents)
        self.assertEqual(narration, {"text": "Answered by qwen3:4b.", "source": "model"})
        self.assertTrue(all("127.0.0.1" in call.args[1] for call in post.call_args_list))
        # The shared gateway keeps its own model; only the copy changed.
        self.assertEqual(gateway.ollama_model, "qwen3:4b")
        self.assertEqual(roles.model_map()["hermes"], "ollama:hermes3")

    def test_a_role_variable_may_name_a_model_and_keeps_its_case(self):
        from server.orchestration import ModelRoles
        env = {"OLLAMA_MODEL": "qwen3", "AGENTIC_OS_HERMES_MODEL": "Ollama:Hermes3",
               "AGENTIC_OS_CONSULTANTS": "anthropic:claude-x, ollama:qwen3"}
        roles = ModelRoles(ModelGateway(env=env), env)
        self.assertEqual(roles.hermes, "ollama:Hermes3")
        self.assertEqual(roles.consultants, ["ollama:qwen3"])
        self.assertEqual(len(roles.problems), 1)

    def test_a_hosted_provider_takes_a_model_override_too(self):
        env = {"OPENROUTER_API_KEY": "o", "OPENROUTER_MODEL": "default/model:free",
               "AGENTIC_OS_TASK_MODELS": "chat=openrouter:other/model:free"}
        gateway = ModelGateway(env=env)
        reply = {"choices": [{"message": {"content": "ok"}}]}
        with patch.object(ModelGateway, "_post", autospec=True, return_value=reply) as post:
            gateway.ask("system", "user")
            gateway.narrate("goal", ["Costs rose."])
        self.assertEqual(post.call_args_list[0].args[3]["model"], "other/model:free")
        self.assertEqual(post.call_args_list[1].args[3]["model"], "default/model:free")
        self.assertEqual(gateway.task_problems, [])


class CallLedgerTestCase(unittest.TestCase):
    """Assessment finding G4: every provider attempt is on the record,
    with the token counts the provider reported and nothing estimated."""

    def test_an_openai_compatible_reply_records_its_usage_block(self):
        gateway = ModelGateway(env={"GROQ_API_KEY": "k", "GROQ_MODEL": "m"})
        reply = {"choices": [{"message": {"content": "Costs are rising."}}],
                 "usage": {"prompt_tokens": 40, "completion_tokens": 12, "total_tokens": 52}}
        with patch.object(gateway, "_post", return_value=reply):
            self.assertEqual(gateway.ask("sys", "user"), "Costs are rising.")
            gateway.narrate("goal", ["Revenue is up."])
        entries = gateway.ledger_entries()
        self.assertEqual([e["task"] for e in entries], ["chat", "narration"])
        first = entries[0]
        self.assertEqual((first["provider"], first["model"], first["outcome"]),
                         ("groq", "m", "ok"))
        self.assertEqual((first["input_tokens"], first["output_tokens"], first["total_tokens"]),
                         (40, 12, 52))
        self.assertGreaterEqual(first["latency_ms"], 0)
        totals = gateway.ledger()["providers"]["groq"]
        self.assertEqual(totals["calls"], 2)
        self.assertEqual(totals["failures"], 0)
        self.assertEqual(totals["total_tokens"], 104)
        self.assertEqual(totals["calls_with_tokens"], 2)
        self.assertNotIn("entries", gateway.ledger())

    def test_anthropic_and_ollama_usage_fields_are_read_and_absent_counts_stay_none(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "k"})
        reply = {"content": [{"text": "Fine."}], "usage": {"input_tokens": 9, "output_tokens": 3}}
        with patch.object(gateway, "_post", return_value=reply):
            gateway.ask("sys", "user", task="hermes")
        entry = gateway.ledger_entries()[-1]
        self.assertEqual((entry["provider"], entry["task"]), ("anthropic", "hermes"))
        self.assertEqual((entry["input_tokens"], entry["output_tokens"], entry["total_tokens"]),
                         (9, 3, 12))

        local = ModelGateway(env={"OLLAMA_MODEL": "qwen3:4b"})
        with patch.object(local, "_post", return_value={"message": {"content": "Ok."},
                                                        "prompt_eval_count": 20, "eval_count": 5}):
            local.ask("sys", "user")
        with patch.object(local, "_post", return_value={"message": {"content": "Ok."}}):
            local.ask("sys", "user")
        counted, uncounted = local.ledger_entries()
        self.assertEqual((counted["input_tokens"], counted["output_tokens"], counted["total_tokens"]),
                         (20, 5, 25))
        self.assertEqual((uncounted["input_tokens"], uncounted["output_tokens"],
                          uncounted["total_tokens"]), (None, None, None))
        totals = local.ledger()["providers"]["ollama"]
        self.assertEqual((totals["calls"], totals["calls_with_tokens"], totals["total_tokens"]),
                         (2, 1, 25))

    def test_a_failed_call_and_an_empty_reply_are_counted_as_failures(self):
        gateway = ModelGateway(env={"ANTHROPIC_API_KEY": "k", "GROQ_API_KEY": "k", "AGENTIC_OS_MODEL_FAILOVER": "anthropic>groq"})
        with patch.object(gateway, "_post", side_effect=[None, {"choices": []}]):
            self.assertIsNone(gateway.ask("sys", "user"))
        outcomes = [(e["provider"], e["outcome"]) for e in gateway.ledger_entries()]
        self.assertEqual(outcomes, [("anthropic", "error"), ("groq", "empty")])
        providers = gateway.ledger()["providers"]
        self.assertEqual(providers["anthropic"]["failures"], 1)
        self.assertEqual(providers["groq"]["failures"], 1)
        self.assertEqual(providers["anthropic"]["total_tokens"], 0)
        self.assertIsNone(gateway.ledger_entries()[0]["total_tokens"])

    def test_a_role_model_copy_writes_to_the_same_ledger(self):
        gateway = ModelGateway(env={"OLLAMA_MODEL": "hermes3"})
        reply = {"message": {"content": "Ok."}}
        with patch.object(ModelGateway, "_post", autospec=True, return_value=reply):
            gateway.ask("sys", "user", provider="ollama:qwen3")
        self.assertEqual([e["model"] for e in gateway.ledger_entries()], ["qwen3"])

    def test_the_ledger_keeps_only_the_last_entries_and_never_the_text(self):
        from server.model_gateway import LEDGER_ENTRIES
        gateway = ModelGateway(env={"GROQ_API_KEY": "k", "GROQ_MODEL": "m"})
        reply = {"choices": [{"message": {"content": "secret sentence"}}]}
        with patch.object(gateway, "_post", return_value=reply):
            for _ in range(LEDGER_ENTRIES + 3):
                gateway.ask("sys", "user")
        self.assertEqual(len(gateway.ledger_entries()), LEDGER_ENTRIES)
        self.assertEqual(gateway.ledger()["providers"]["groq"]["calls"], LEDGER_ENTRIES + 3)
        self.assertNotIn("secret sentence", repr(gateway.ledger_entries()))

