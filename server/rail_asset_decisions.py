"""Rail asset screening: deterministic, auditable advice, not a safety decision.

This module deliberately does not train a predictive model or infer OEM support.
Use only validated, pre-decision fields. Source is synthetic unless proven otherwise.
"""
from __future__ import annotations

from math import isfinite

ROLE_TAG = "TEAM3_RAIL_ASSET_MANAGER"
CRITICALITIES = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
REQUIRED = ("Industry_Context", "Asset_Class", "Asset_ID", "Criticality",
            "Condition_Score", "Failure_Count", "Downtime_Hours",
            "Maintenance_Cost_USD", "Production_Loss_USD")


def _number(row, field):
    value = row.get(field)
    if isinstance(value, bool):
        raise ValueError(f"{field}: invalid numeric value")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field}: missing or invalid numeric value") from error
    if not isfinite(result) or result < 0:
        raise ValueError(f"{field}: must be finite and nonnegative")
    return result


def assess_observation(row):
    """Screen one observation. Do not add per-row findings into an asset history."""
    missing = [name for name in REQUIRED if row.get(name) in (None, "")]
    if missing:
        raise ValueError("Missing required fields: " + ", ".join(missing))
    category = str(row["Criticality"])
    if category not in CRITICALITIES:
        raise ValueError("Unknown criticality: " + category)
    if not all(str(row[k]).strip() for k in ("Industry_Context", "Asset_Class", "Asset_ID")):
        raise ValueError("Empty asset identity component")
    condition = _number(row, "Condition_Score")
    if condition > 100:
        raise ValueError("Condition_Score must be between 0 and 100")
    failures = _number(row, "Failure_Count")
    downtime = _number(row, "Downtime_Hours")
    maintenance = _number(row, "Maintenance_Cost_USD")
    loss = _number(row, "Production_Loss_USD")
    return {
        "role_tag": ROLE_TAG,
        "analytic_key": "|".join(str(row[k]).strip() for k in
                                 ("Industry_Context", "Asset_Class", "Asset_ID")),
        "identity_status": "UNVERIFIED_PHYSICAL_IDENTITY",
        "criticality": category,
        "criticality_rank": CRITICALITIES[category],
        "observed_condition_score": condition,
        "observed_failure_count": failures,
        "observed_downtime_hours": downtime,
        "maintenance_cost_usd": maintenance,
        "production_loss_usd": loss,
        "observed_economic_exposure_usd": maintenance + loss,
        "screening": ("engineering_review" if category in ("Critical", "High")
                      and (failures > 0 or condition < 60) else "routine_review"),
        "prediction_status": "NOT_EVALUATED",
        "obsolescence_status": "INSUFFICIENT_OEM_EVIDENCE",
        "replacement_case_status": "INCOMPLETE_LIFECYCLE_COST_DATA",
        "approval_status": "HUMAN_REVIEW_REQUIRED",
        "limitations": [
            "Synthetic observation, not a verified physical asset history.",
            "Maintenance plus service loss is not total lifecycle cost.",
            "No OEM support dates, replacement cost, certified safety risk or RUL.",
            "Screening is not an AI prediction or authority to execute work."
        ],
    }


def authorize(role_tags, action, approved=False):
    """Minimal fail-closed policy for domain advice; enforce additionally in API."""
    roles = set(role_tags or ())
    if ROLE_TAG not in roles:
        return False
    if action in ("read_screening", "propose_intervention"):
        return True
    if action == "release_recommendation":
        return approved is True
    return False
