"""Shadow validation must not turn future/missing labels into measured success."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server.auth import Principal
from server.backup import create_backup, restore_backup
from server.operations import Operations, OperationsError
from server.reliability_validation import ReliabilityTrials, ValidationError, summarize
from server.storage import open_store


class ReliabilityValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = open_store(sqlite_path=Path(self.temp.name) / "ledger.db")
        self.addCleanup(self.store.close)
        self.actor = Principal("analyst-a", "owner", "jwt")
        self.other = Principal("analyst-b", "admin", "jwt")
        ops = Operations(self.store)
        self.org = ops.create_organization(self.actor, {"name": "Test facility", "idempotency_key": "org"})["id"]
        site = ops.create_site(self.actor, self.org, {"code": "A", "name": "A", "idempotency_key": "site"})
        self.asset = ops.create_asset(self.actor, self.org, {"site_id": site["id"], "external_id": "PUMP-1",
                                      "source_system": "test", "name": "Pump", "idempotency_key": "asset"})["id"]
        self.now = datetime.now(timezone.utc) + timedelta(minutes=1)
        self.ledger = ReliabilityTrials(self.store, clock=lambda: self.now)
        self.protocol = {"request_id": "protocol-1", "name": "Failure within 24 hours", "model_version": "frozen-1",
                         "baseline_name": "Historical rate", "trained_through": (self.now - timedelta(days=30)).isoformat(),
                         "horizon_hours": 24, "threshold": .5,
                         "failure_definition": "Confirmed loss of function", "cohort_definition": "Registered pumps"}
        self.trial = self.ledger.create(self.actor, self.org, self.protocol)

    def predict(self, **changes):
        body = {"asset_id": self.asset, "request_id": "prediction-1", "probability": .8,
                "baseline_probability": .1, "revision": 1} | changes
        return self.ledger.predict(self.actor, self.trial["id"], body)

    def outcome(self, prediction, **changes):
        return {"revision": 2, "failed": True, "failure_at": (self.now - timedelta(hours=12)).isoformat(),
                "observed_through": self.now.isoformat(), "actionable": True,
                "evidence_reference": "work-order/test-1"} | changes

    def test_empty_trial_is_not_zero_error_or_perfect_accuracy(self):
        metrics = self.trial["metrics"]
        self.assertIsNone(metrics["failure_alert_precision"]["value"])
        self.assertIsNone(metrics["brier_score"])
        self.assertEqual(metrics["evaluated"], 0)

    def test_protocol_retry_reuses_registration_and_rejects_changed_threshold(self):
        self.now += timedelta(minutes=5)
        again = self.ledger.create(self.actor, self.org, self.protocol)
        self.assertEqual(again["id"], self.trial["id"])
        self.assertEqual(again["protocol"]["registered_at"], self.trial["protocol"]["registered_at"])
        with self.assertRaises(ValidationError) as caught:
            self.ledger.create(self.actor, self.org, self.protocol | {"threshold": .9})
        self.assertEqual(caught.exception.code, "replay")

    def test_prediction_is_stamped_before_outcome_and_cannot_backdate(self):
        trial = self.predict()
        p = trial["predictions"][0]
        self.assertEqual(p["predicted_at"], self.now.isoformat())
        self.assertEqual(trial["metrics"]["pending"], 1)
        with self.assertRaises(ValidationError) as caught:
            self.ledger.adjudicate(self.actor, trial["id"], p["id"], self.outcome(p))
        self.assertEqual(caught.exception.code, "immature")

    def test_complete_followup_and_failure_window_are_required(self):
        trial = self.predict()
        p = trial["predictions"][0]
        self.now += timedelta(days=1)
        for changes, code in (({"observed_through": p["predicted_at"]}, "followup"),
                              ({"failure_at": p["predicted_at"]}, "chronology"),
                              ({"observed_through": (self.now + timedelta(days=1)).isoformat()}, "followup")):
            with self.subTest(code=code), self.assertRaises(ValidationError) as caught:
                self.ledger.adjudicate(self.actor, trial["id"], p["id"], self.outcome(p, **changes))
            self.assertEqual(caught.exception.code, code)

    def test_success_requires_evidence_and_stays_immutable(self):
        trial = self.predict()
        p = trial["predictions"][0]
        self.now += timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.ledger.adjudicate(self.actor, trial["id"], p["id"], self.outcome(p, evidence_reference=""))
        done = self.ledger.adjudicate(self.actor, trial["id"], p["id"], self.outcome(p))
        metrics = done["metrics"]
        self.assertEqual(metrics["confusion"]["true_positive"], 1)
        self.assertEqual(metrics["lead_time_hours"]["mean"], 12)
        self.assertAlmostEqual(metrics["brier_score"], .04)
        self.assertAlmostEqual(metrics["baseline"]["brier_score"], .81)
        self.assertIn("self_adjudicated_outcomes", metrics["limitations"])
        with self.assertRaises(ValidationError) as caught:
            self.ledger.adjudicate(self.actor, trial["id"], p["id"], self.outcome(p, revision=3))
        self.assertEqual(caught.exception.code, "immutable")

    def test_foreign_admin_cannot_read_or_mutate_org_trial(self):
        with self.assertRaises(ValidationError) as caught:
            self.ledger.get(self.other, self.trial["id"])
        self.assertEqual((caught.exception.status, caught.exception.code), (404, "missing"))
        for operation in (lambda: self.ledger.list(self.other, self.org),
                          lambda: self.ledger.create(self.other, self.org, self.protocol)):
            with self.assertRaises(OperationsError) as caught:
                operation()
            self.assertEqual(caught.exception.status, 404)

    def test_replay_is_idempotent_but_changed_payload_is_rejected(self):
        first = self.predict()
        again = self.predict()
        self.assertEqual(first, again)
        with self.assertRaises(ValidationError) as caught:
            self.predict(probability=.1)
        self.assertEqual(caught.exception.code, "replay")

    def test_stale_write_and_overlapping_asset_windows_rejected(self):
        self.predict()
        with self.assertRaises(ValidationError) as caught:
            self.predict(request_id="prediction-2")
        self.assertEqual(caught.exception.code, "conflict")
        with self.assertRaises(ValidationError) as caught:
            self.predict(request_id="prediction-2", revision=2)
        self.assertEqual(caught.exception.code, "overlap")

    def test_nonfinite_scores_boolean_probabilities_and_future_training_rejected(self):
        for value in (float("nan"), float("inf"), True, -.1, 1.1):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.predict(probability=value)
        with self.assertRaises(ValidationError):
            self.ledger.create(self.actor, self.org, self.protocol | {"trained_through": self.now.isoformat()})

    def test_registered_asset_and_same_org_required(self):
        with self.assertRaises(ValidationError) as caught:
            self.predict(asset_id="unknown")
        self.assertEqual(caught.exception.code, "asset")

    def test_backup_roundtrip_preserves_protocol_prediction_and_hash(self):
        before = self.predict()
        backup = create_backup(self.store)
        self.store._exec("DELETE FROM reliability_trials")
        restore_backup(self.store, backup)
        after = self.ledger.get(self.actor, self.trial["id"])
        self.assertEqual(before, after)

    def test_list_summaries_do_not_return_all_prediction_rows(self):
        self.predict()
        summaries = self.ledger.list(self.actor, self.org)
        self.assertNotIn("predictions", summaries[0])
        self.assertNotIn("metrics", summaries[0])

    def test_metrics_use_same_complete_cohort_and_do_not_count_pending_as_negative(self):
        base = {"asset_id": "a", "predicted_at": "2026-01-01T00:00:00+00:00",
                "window_end": "2026-01-02T00:00:00+00:00", "submitted_by": "model",
                "probability": .8, "baseline_probability": .2}
        predictions = [base | {"outcome": {"failed": False, "actionable": False, "adjudicated_by": "reviewer"}},
                       base | {"asset_id": "b", "probability": .1,
                               "outcome": {"failed": True, "actionable": None, "adjudicated_by": "reviewer"}},
                       base | {"asset_id": "c", "outcome": None}]
        metrics = summarize(self.protocol, predictions, self.now)
        self.assertEqual(metrics["evaluated"], 2)
        self.assertEqual(metrics["baseline"]["evaluated"], 2)
        self.assertEqual(metrics["pending"], 1)
        self.assertEqual(metrics["confusion"], {"true_positive": 0, "false_positive": 1, "true_negative": 0, "false_negative": 1})
        self.assertEqual(metrics["evaluated_asset_hours"], 48)
        self.assertEqual(metrics["failure_window_recall"]["denominator"], 1)
        self.assertEqual(sum(b["count"] for b in metrics["calibration"]), 2)
        self.assertEqual(metrics["different_actor_adjudications"], 2)
