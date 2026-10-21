"""Prospective shadow-validation ledger. No model calls or inferred outcomes.

A protocol and threshold are fixed before predictions. Server time stamps each
prediction; the adjudicator supplies evidence only after its full horizon. The
evaluated population is the non-overlapping registered prediction windows, not
the whole fleet. A ledger makes temporal ordering auditable; it cannot certify
the external evidence or establish causal maintenance savings.
"""

import hashlib
import json
import math
import uuid
from datetime import datetime, timedelta, timezone

from server.operations import OperationsError, require_org_access

MAX_PREDICTIONS = 2000
MAX_TRIALS = 100
ASSET_MONTH_HOURS = 365.25 / 12 * 24


class ValidationError(ValueError):
    def __init__(self, code, status=422):
        self.code, self.status = code, status
        super().__init__(code)


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError()
        return stamp.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise ValidationError("timestamp") from None


def text(value, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationError("field")
    if any(ord(c) < 32 for c in value):
        raise ValidationError("field")
    return value.strip()


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValidationError("field")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValidationError("field")
    return value


def wilson(success, total):
    """Descriptive 95% Wilson interval, not an independence guarantee."""
    if not total:
        return None
    z = 1.959963984540054
    p, zz = success / total, z * z
    center = (p + zz / (2 * total)) / (1 + zz / total)
    half = z * math.sqrt(p * (1 - p) / total + zz / (4 * total * total)) / (1 + zz / total)
    return [max(0.0, center - half), min(1.0, center + half)]


def fraction(success, total):
    return {"numerator": success, "denominator": total,
            "value": success / total if total else None,
            "wilson_95": wilson(success, total)}


def summarize(protocol, predictions, now=None):
    now = now or utcnow()
    evaluated = [p for p in predictions if p.get("outcome") is not None]
    threshold = protocol["threshold"]
    tp = fp = tn = fn = 0
    lead_hours, brier, baseline_brier, actionable = [], [], [], []
    baseline_tp = baseline_fp = baseline_tn = baseline_fn = 0
    exposure = 0.0
    for p in evaluated:
        outcome = p["outcome"]
        predicted, failed = p["probability"] >= threshold, outcome["failed"]
        tp += int(predicted and failed)
        fp += int(predicted and not failed)
        tn += int(not predicted and not failed)
        fn += int(not predicted and failed)
        brier.append((p["probability"] - int(failed)) ** 2)
        baseline = p["baseline_probability"] >= threshold
        baseline_tp += int(baseline and failed)
        baseline_fp += int(baseline and not failed)
        baseline_tn += int(not baseline and not failed)
        baseline_fn += int(not baseline and failed)
        baseline_brier.append((p["baseline_probability"] - int(failed)) ** 2)
        exposure += (timestamp(p["window_end"]) - timestamp(p["predicted_at"])).total_seconds() / 3600
        if predicted and failed:
            lead_hours.append((timestamp(outcome["failure_at"]) - timestamp(p["predicted_at"])).total_seconds() / 3600)
        if predicted and outcome.get("actionable") is not None:
            actionable.append(outcome["actionable"])
    bins = []
    for lower, upper in ((0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1)):
        cohort = [p for p in evaluated if lower <= p["probability"] < upper
                  or (upper == 1 and p["probability"] == 1)]
        bins.append({"lower": lower, "upper": upper, "count": len(cohort),
                     "mean_probability": sum(p["probability"] for p in cohort) / len(cohort) if cohort else None,
                     "observed_failure_rate": sum(p["outcome"]["failed"] for p in cohort) / len(cohort) if cohort else None})
    pending = len(predictions) - len(evaluated)
    return {
        "scope": "registered_nonoverlapping_asset_windows", "registered": len(predictions),
        "evaluated": len(evaluated), "pending": pending,
        "mature_unadjudicated": sum(p.get("outcome") is None and timestamp(p["window_end"]) <= now for p in predictions),
        "confusion": {"true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn},
        "failure_alert_precision": fraction(tp, tp + fp), "failure_window_recall": fraction(tp, tp + fn),
        "actionable_alert_precision": fraction(sum(actionable), len(actionable)),
        "adjudicated_alerts_without_actionability": tp + fp - len(actionable),
        "evaluated_asset_hours": exposure,
        "false_alerts_per_asset_month": fp * ASSET_MONTH_HOURS / exposure if exposure else None,
        "lead_time_hours": {"count": len(lead_hours), "minimum": min(lead_hours) if lead_hours else None,
                            "mean": sum(lead_hours) / len(lead_hours) if lead_hours else None},
        "brier_score": sum(brier) / len(brier) if brier else None, "calibration": bins,
        "baseline": {"name": protocol["baseline_name"], "evaluated": len(evaluated),
                     "brier_score": sum(baseline_brier) / len(baseline_brier) if baseline_brier else None,
                     "confusion": {"true_positive": baseline_tp, "false_positive": baseline_fp,
                                   "true_negative": baseline_tn, "false_negative": baseline_fn}},
        "different_actor_adjudications": sum(p["outcome"]["adjudicated_by"] != p["submitted_by"] for p in evaluated),
        "limitations": ["registered_windows_only", "adjudications_require_independent_evidence",
                        "repeated_assets_not_independent", "no_causal_savings_claim"]
                        + (["incomplete_followup"] if pending else [])
                        + (["self_adjudicated_outcomes"] if any(p["outcome"]["adjudicated_by"] == p["submitted_by"] for p in evaluated) else []),
    }


class ReliabilityTrials:
    def __init__(self, store, clock=utcnow):
        self.store, self.clock = store, clock

    def _row(self, principal, trial_id, permission="read"):
        rows = self.store._exec("SELECT * FROM reliability_trials WHERE id = ?", (trial_id,))
        if not rows:
            raise ValidationError("missing", 404)
        row = rows[0]
        try:
            require_org_access(self.store, principal, row["org_id"], permission)
        except OperationsError as error:
            if error.status == 404:
                raise ValidationError("missing", 404) from None
            raise
        return row

    def list(self, principal, org_id):
        require_org_access(self.store, principal, org_id)
        rows = self.store._exec("SELECT id, org_id, created_at, updated_at, revision, protocol_json FROM reliability_trials "
                                "WHERE org_id = ? ORDER BY created_at DESC", (org_id,))
        return [{key: row[key] for key in ("id", "org_id", "created_at", "updated_at", "revision")} |
                {"protocol": json.loads(row["protocol_json"])} for row in rows]

    def _public(self, row):
        protocol = json.loads(row["protocol_json"])
        predictions = json.loads(row["predictions_json"])
        return {key: row[key] for key in ("id", "org_id", "created_at", "updated_at", "revision")} | {
            "protocol": protocol, "predictions": predictions,
            "metrics": summarize(protocol, predictions, self.clock()),
            "evidence_hash": hashlib.sha256((row["protocol_json"] + row["predictions_json"]).encode()).hexdigest()}

    def get(self, principal, trial_id):
        return self._public(self._row(principal, trial_id))

    def create(self, principal, org_id, data):
        with self.store.atomic("operations:" + org_id):
            require_org_access(self.store, principal, org_id, "manage")
            request_id = text(data.get("request_id"), 80)
            now = self.clock()
            cutoff = timestamp(data.get("trained_through"))
            if cutoff >= now:
                raise ValidationError("chronology")
            protocol = {"name": text(data.get("name")), "model_version": text(data.get("model_version")),
                        "baseline_name": text(data.get("baseline_name")),
                        "trained_through": cutoff.isoformat(), "registered_at": now.isoformat(),
                        "horizon_hours": number(data.get("horizon_hours"), 1, 24 * 365),
                        "threshold": number(data.get("threshold"), 0, 1),
                        "failure_definition": text(data.get("failure_definition"), 1000),
                        "cohort_definition": text(data.get("cohort_definition"), 1000)}
            identifier = hashlib.sha256((org_id + "\0" + principal.subject + "\0" + request_id).encode()).hexdigest()[:32]
            existing = self.store._exec("SELECT * FROM reliability_trials WHERE id = ?", (identifier,))
            if existing:
                prior = json.loads(existing[0]["protocol_json"])
                if {k: v for k, v in prior.items() if k != "registered_at"} != {k: v for k, v in protocol.items() if k != "registered_at"}:
                    raise ValidationError("replay", 409)
                return self._public(existing[0])
            count = self.store._exec("SELECT COUNT(*) AS n FROM reliability_trials WHERE org_id = ?", (org_id,))[0]["n"]
            if count >= MAX_TRIALS:
                raise ValidationError("limit", 409)
            self.store.insert("reliability_trials", {"id": identifier, "org_id": org_id,
                              "created_by": principal.subject, "created_at": now.isoformat(),
                              "updated_at": now.isoformat(), "revision": 1,
                              "protocol_json": json.dumps(protocol), "predictions_json": "[]"})
            return self.get(principal, identifier)

    def _save(self, row, predictions):
        self.store._exec("UPDATE reliability_trials SET predictions_json = ?, revision = ?, updated_at = ? WHERE id = ?",
                         (json.dumps(predictions), row["revision"] + 1, self.clock().isoformat(), row["id"]))

    def predict(self, principal, trial_id, data):
        org_id = self._row(principal, trial_id, "write")["org_id"]
        with self.store.atomic("operations:" + org_id):
            row = self._row(principal, trial_id, "write")
            predictions = json.loads(row["predictions_json"])
            request_id = text(data.get("request_id"), 80)
            asset_id, probability = text(data.get("asset_id"), 80), number(data.get("probability"), 0, 1)
            baseline_probability = number(data.get("baseline_probability"), 0, 1)
            for p in predictions:
                if p["request_id"] == request_id and p["submitted_by"] == principal.subject:
                    if p["asset_id"] != asset_id or p["probability"] != probability or p["baseline_probability"] != baseline_probability:
                        raise ValidationError("replay", 409)
                    return self._public(row)
            if data.get("revision") != row["revision"]:
                raise ValidationError("conflict", 409)
            if len(predictions) >= MAX_PREDICTIONS:
                raise ValidationError("limit", 409)
            assets = self.store._exec("SELECT id FROM operation_assets WHERE id = ? AND org_id = ?", (asset_id, row["org_id"]))
            if not assets:
                raise ValidationError("asset", 404)
            now = self.clock()
            protocol = json.loads(row["protocol_json"])
            if now < timestamp(protocol["registered_at"]):
                raise ValidationError("chronology")
            if any(p["asset_id"] == asset_id and timestamp(p["window_end"]) > now for p in predictions):
                raise ValidationError("overlap", 409)
            predictions.append({"id": uuid.uuid4().hex, "request_id": request_id, "asset_id": asset_id,
                                "probability": probability, "predicted_at": now.isoformat(),
                                "baseline_probability": baseline_probability,
                                "window_end": (now + timedelta(hours=protocol["horizon_hours"])).isoformat(),
                                "submitted_by": principal.subject, "outcome": None})
            self._save(row, predictions)
            return self.get(principal, trial_id)

    def adjudicate(self, principal, trial_id, prediction_id, data):
        org_id = self._row(principal, trial_id, "authorize")["org_id"]
        with self.store.atomic("operations:" + org_id):
            row = self._row(principal, trial_id, "authorize")
            if data.get("revision") != row["revision"]:
                raise ValidationError("conflict", 409)
            predictions = json.loads(row["predictions_json"])
            prediction = next((p for p in predictions if p["id"] == prediction_id), None)
            if prediction is None:
                raise ValidationError("missing", 404)
            if prediction["outcome"] is not None:
                raise ValidationError("immutable", 409)
            now, end = self.clock(), timestamp(prediction["window_end"])
            if now < end:
                raise ValidationError("immature", 409)
            through = timestamp(data.get("observed_through"))
            if through < end or through > now:
                raise ValidationError("followup")
            failed, actionable = data.get("failed"), data.get("actionable")
            if type(failed) is not bool or (actionable is not None and type(actionable) is not bool):
                raise ValidationError("field")
            failure = timestamp(data.get("failure_at")) if failed else None
            if failed and not timestamp(prediction["predicted_at"]) < failure <= end:
                raise ValidationError("chronology")
            if not failed and data.get("failure_at"):
                raise ValidationError("chronology")
            prediction["outcome"] = {"failed": failed, "failure_at": failure.isoformat() if failure else None,
                                     "actionable": actionable, "observed_through": through.isoformat(),
                                     "evidence_reference": text(data.get("evidence_reference"), 500),
                                     "adjudicated_by": principal.subject, "adjudicated_at": now.isoformat()}
            self._save(row, predictions)
            return self.get(principal, trial_id)
