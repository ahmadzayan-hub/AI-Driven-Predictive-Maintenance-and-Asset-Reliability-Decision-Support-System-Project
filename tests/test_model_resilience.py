"""Retired models, quota and network failures are distinct, never fake success."""

from concurrent.futures import ThreadPoolExecutor
import json
import unittest
from unittest.mock import Mock, patch

import httpx
from server.model_gateway import ModelGateway


class ModelResilienceTests(unittest.TestCase):
    def gateway(self, **extra):
        return ModelGateway({"OPENAI_API_KEY": "synthetic-key-never-transmitted",
                             "OPENAI_MODEL": "synthetic-model", "GROQ_API_KEY": "synthetic-groq", **extra})

    def response(self, status, code=None, kind=None):
        return httpx.Response(status, json={"error": {"code": code, "type": kind,
            "message": "PRIVATE_RESPONSE_CANARY synthetic-key-never-transmitted"}})

    def test_classified_errors_never_relay_response_bodies_or_invent_success(self):
        cases = [(400, "model_decommissioned", None, "model_retired"),
                 (404, "model_not_found", None, "model_unavailable"),
                 (404, None, None, "not_found"),
                 (401, None, None, "credential_rejected"),
                 (402, None, None, "payment_required"),
                 (403, None, None, "permission_denied"),
                 (429, "insufficient_quota", None, "provider_quota"),
                 (400, None, "billing_limit_exceeded", "provider_quota"),
                 (429, None, None, "rate_limited"),
                 (503, None, None, "provider_error"),
                 (422, "unknown_code", None, "request_rejected")]
        for status, code, kind, expected in cases:
            with self.subTest(expected=expected):
                gateway = self.gateway()
                with patch("httpx.post", return_value=self.response(status, code, kind)) as post:
                    result = gateway.narrate("synthetic goal", ["A verified fixture"])
                self.assertEqual(result["source"], "deterministic")
                post.assert_called_once()
                self.assertEqual(gateway.ledger_entries()[-1]["error_code"], expected)
                self.assertEqual(gateway.ledger()["providers"]["openai"]["last_error"], expected)
                ledger = json.dumps(gateway.ledger_entries()) + json.dumps(gateway.ledger())
                self.assertNotIn("PRIVATE_RESPONSE_CANARY", ledger)
                self.assertNotIn("synthetic-key-never-transmitted", ledger)

    def test_timeout_network_invalid_json_and_empty_response_are_distinct(self):
        for error, expected in ((httpx.ReadTimeout("PRIVATE_CANARY"), "timeout"),
                                (httpx.ConnectError("PRIVATE_CANARY"), "network_error")):
            gateway = self.gateway()
            with patch("httpx.post", side_effect=error):
                self.assertIsNone(gateway.ask("fixture", "fixture"))
            self.assertEqual(gateway.ledger_entries()[-1]["error_code"], expected)
        for response, expected in ((httpx.Response(200, text="not JSON"), "invalid_response"),
                                    (httpx.Response(200, text="null"), "invalid_response"),
                                    (httpx.Response(200, json=[]), "invalid_response"),
                                    (httpx.Response(200, json={"choices": []}), "empty_response")):
            gateway = self.gateway(AGENTIC_OS_MODEL_FAILOVER="openai>groq")
            with patch("httpx.post", return_value=response) as post:
                self.assertIsNone(gateway.ask("fixture", "fixture"))
                post.assert_called_once()  # Invalid 200 is not a transient server outage.
            self.assertEqual(gateway.ledger_entries()[-1]["error_code"], expected)

    def test_configured_second_key_is_not_permission_to_transfer_context(self):
        gateway = self.gateway()
        self.assertEqual(gateway._attempts("openai"), ["openai"])
        with patch("httpx.post", side_effect=httpx.ReadTimeout("synthetic")) as post:
            self.assertIsNone(gateway.ask("fixture", "fixture"))
        post.assert_called_once()
        self.assertIn("openai.com", post.call_args.args[0])

    def test_explicit_edge_is_directional_bounded_and_cannot_cross_local_boundary(self):
        gateway = self.gateway(AGENTIC_OS_MODEL_FAILOVER="openai>groq,groq>openai")
        self.assertEqual(gateway._attempts("openai"), ["openai", "groq"])
        reverse = self.gateway(AGENTIC_OS_MODEL_FAILOVER="openai>groq")
        self.assertEqual(reverse._attempts("groq"), ["groq"])
        local = self.gateway(OLLAMA_MODEL="synthetic", AGENTIC_OS_MODEL_FAILOVER="ollama>groq")
        self.assertEqual(local._attempts("ollama"), ["ollama"])
        with patch("httpx.post", side_effect=httpx.ConnectError("synthetic")) as post:
            self.assertIsNone(gateway.ask("fixture", "fixture"))
        self.assertEqual(post.call_count, 2)

    def test_quota_retirement_and_credentials_do_not_transfer_even_with_an_edge(self):
        for status, code in ((429, "insufficient_quota"), (429, None), (401, None),
                              (404, "model_not_found"), (400, "model_decommissioned"), (402, None)):
            gateway = self.gateway(AGENTIC_OS_MODEL_FAILOVER="openai>groq")
            with self.subTest(status=status, code=code), patch("httpx.post", return_value=self.response(status, code)) as post:
                self.assertIsNone(gateway.ask("fixture", "fixture"))
                post.assert_called_once()

    def test_unknown_or_malformed_edges_are_fail_closed(self):
        for edge in ("*", "1", "openai", "openai>unknown", "openai>groq>other", "groq>openai"):
            self.assertEqual(self.gateway(AGENTIC_OS_MODEL_FAILOVER=edge)._attempts("openai"), ["openai"])

    def test_missing_credential_and_missing_model_are_configuration_not_live_availability(self):
        gateway = ModelGateway({"OPENAI_MODEL": "possibly-retired", "GROQ_API_KEY": "PRIVATE",
                                "MISTRAL_API_KEY": "PRIVATE", "AI_GATEWAY_MODEL": "unknown/model"})
        with patch("httpx.post", side_effect=AssertionError("No catalog probe permitted")):
            report = gateway.configuration_report()
        states = {row["provider"]: row["configuration"] for row in report["providers"]}
        self.assertEqual(states, {"openai": "missing_credential", "groq": "configured",
                                 "mistral": "missing_model", "vercel": "missing_credential"})
        self.assertTrue(all(row["availability"] == "unverified" for row in report["providers"]))
        self.assertEqual(report["cost_status"], "unverified")
        missing = next(row for row in report["providers"] if row["provider"] == "mistral")
        self.assertEqual(missing["model_selection"], "missing")
        self.assertNotIn("PRIVATE", json.dumps(report))
        self.assertFalse(report["cross_provider_failover_enabled"])

    def test_explicit_failover_and_deprecated_legacy_default_are_reported_honestly(self):
        gateway = ModelGateway({"ANTHROPIC_API_KEY": "synthetic", "OPENAI_API_KEY": "synthetic",
            "OPENAI_MODEL": "operator-selected", "AGENTIC_OS_MODEL_FAILOVER": "anthropic>openai"})
        report = gateway.configuration_report()
        self.assertTrue(report["cross_provider_failover_enabled"])
        self.assertEqual(report["configured_failover_edges"], [{"from": "anthropic", "to": "openai"}])
        old = next(row for row in report["providers"] if row["provider"] == "anthropic")
        self.assertEqual(old["model_selection"], "legacy_default")
        self.assertEqual(old["lifecycle_review"]["retirement_date"], "2026-11-30")
        self.assertEqual(old["lifecycle_review"]["status_at_review"], "deprecated")
        self.assertEqual(old["availability"], "unverified")
        self.assertEqual(gateway.anthropic_model, "claude-sonnet-4-5")  # Not silently replaced.

    def test_success_clears_last_error_but_keeps_historical_failure_counts(self):
        gateway = self.gateway()
        good = httpx.Response(200, json={"choices": [{"message": {"content": "A real mocked response"}}]})
        with patch("httpx.post", side_effect=[self.response(429), good]):
            self.assertIsNone(gateway.ask("fixture", "fixture"))
            self.assertEqual(gateway.ask("fixture", "fixture"), "A real mocked response")
        totals = gateway.ledger()["providers"]["openai"]
        self.assertEqual(totals["failures_by_category"], {"rate_limited": 1})
        self.assertIsNone(totals["last_error"])
        totals["failures_by_category"]["forged"] = 999
        self.assertNotIn("forged", gateway.ledger()["providers"]["openai"]["failures_by_category"])

    def test_admission_denial_counts_no_provider_call_or_billed_usage(self):
        gateway = self.gateway()
        gateway.budget = Mock(); gateway.budget.allow.return_value = False
        with patch("httpx.post") as post:
            self.assertIsNone(gateway.ask("fixture", "fixture"))
            self.assertIsNone(gateway.ask_json("fixture", "fixture"))
            self.assertEqual(gateway.narrate("fixture", ["fixture"])["source"], "deterministic")
        post.assert_not_called()
        self.assertEqual(gateway.ledger()["entries_kept"], 0)
        self.assertEqual(gateway.ledger()["admission_denials_by_provider"], {"openai": 3})
        gateway.budget.charge.assert_not_called()

    def test_failure_categories_are_thread_local_and_share_aggregate_copy_ledger(self):
        gateway = self.gateway()
        def response(url, **kwargs):
            return self.response(404, "model_not_found") if kwargs["json"]["model"] == "missing" else self.response(429)
        def attempt(model):
            return gateway.ask("fixture", "fixture", provider="openai:" + model)
        with patch("httpx.post", side_effect=response), ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(attempt, ["missing", "limited"])), [None, None])
        entries = {entry["model"]: entry["error_code"] for entry in gateway.ledger_entries()}
        self.assertEqual(entries, {"missing": "model_unavailable", "limited": "rate_limited"})


if __name__ == "__main__":
    unittest.main()
