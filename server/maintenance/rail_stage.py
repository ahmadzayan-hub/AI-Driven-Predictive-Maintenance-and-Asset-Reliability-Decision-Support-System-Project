"""Railway observation screening as a governed Hermes pipeline stage.

Advisory only: no asset-level identity inference, OEM obsolescence inference,
safety authority, model prediction, or external language-model row disclosure.
"""
from server import analytics
from server.rail_asset_decisions import assess_observation

class RailAssetManagerStage:
    role = "rail_asset_manager"
    title = "Railway Asset Manager — observed risk and economic exposure"
    title_ar = "وكيل إدارة أصول السكك الحديدية: المخاطر والتعرض الاقتصادي"
    after = "sensitivity"
    question = "Which railway observations warrant engineering review?"
    can_fail_run = False

    def run(self, ctx):
        rows = analytics._rows(ctx)
        columns = set(analytics._columns(ctx))
        required = {"Asset_Class", "Industry_Context", "Asset_ID", "Criticality",
                    "Condition_Score", "Failure_Count", "Downtime_Hours",
                    "Maintenance_Cost_USD", "Production_Loss_USD"}
        if not required.issubset(columns):
            summary = ("Railway screening unavailable: required data fields are missing. "
                       "No risk, prediction or lifecycle claim was made.")
            return {"status": "succeeded", "summary": summary,
                    "claims": [], "calculations": [],
                    "quality_checks": [{"name": "field_contract", "passed": False,
                                        "detail": "Missing: " + ", ".join(sorted(required - columns))}],
                    "output": {"applicable": False, "reason": summary}}
        railway = [row for row in rows
                   if str(row.get("Asset_Class", "")).strip().casefold()
                   == "railway signalling"]
        eligible = 0
        rejected = 0
        for_review = 0
        exposure = 0.0
        for row in railway:
            try:
                finding = assess_observation(row)
            except (TypeError, ValueError, AttributeError):
                rejected += 1
                continue
            eligible += 1
            for_review += finding["screening"] == "engineering_review"
            exposure += finding["observed_economic_exposure_usd"]
        exposure = round(exposure, 2)
        prefix = self.role
        calculations = [
            {"id": prefix + ".c_rail", "name": "railway_observations",
             "value": len(railway), "method": "count rows where Asset_Class = Railway Signalling"},
            {"id": prefix + ".c_eligible", "name": "screened_observations",
             "value": eligible, "method": "count railway observations passing domain field checks"},
            {"id": prefix + ".c_rejected", "name": "excluded_observations",
             "value": rejected, "method": "count railway observations that fail input checks"},
            {"id": prefix + ".c_review", "name": "engineering_review_observations",
             "value": for_review, "method": "count valid High/Critical observations with failures or low condition"},
            {"id": prefix + ".c_exposure", "name": "observed_economic_exposure_usd",
             "value": exposure, "method": "sum (Maintenance_Cost_USD + Production_Loss_USD) on valid railway observations; not lifecycle cost"},
        ]
        summary = (f"Screened {eligible} railway observations; {for_review} require "
                   f"engineering review. {rejected} were excluded.")
        claims = [analytics._claim(
            ctx, prefix + ".cl_screen", "calculation",
            f"Of {eligible} screened railway observations, {for_review} were flagged for engineering review.",
            f"من أصل {eligible} سجلاً جرى فحصه للسكك الحديدية، استدعت {for_review} حالة مراجعة هندسية.",
            [prefix + ".c_eligible", prefix + ".c_review"])]
        claims.append(analytics._claim(
            ctx, prefix + ".cl_limits", "limitation",
            "The screening does not establish physical asset identity, failure prediction, obsolescence or lifecycle cost.",
            "هذا الفحص لا يثبت هوية الأصل الفعلية أو توقع الأعطال أو التقادم أو تكلفة دورة الحياة.",
            [prefix + ".c_rail"]))
        return {"status": "succeeded", "summary": summary,
                "claims": claims, "calculations": calculations,
                "quality_checks": [
                    {"name": "field_contract", "passed": True,
                     "detail": "Required fields available"},
                    {"name": "observation_validation", "passed": rejected == 0,
                     "detail": f"{rejected} railway observations excluded"}],
                "output": {"applicable": True, "observation_scope": "Railway Signalling",
                           "screened": eligible, "excluded": rejected,
                           "engineering_review_count": for_review,
                           "observed_economic_exposure_usd": exposure,
                           "human_approval_required": True,
                           "physical_identity_verified": False,
                           "predictive_model_evaluated": False,
                           "obsolescence_evidence_verified": False,
                           "lifecycle_cost_complete": False,
                           "question": self.question,
                           "report_markdown": (
                               "## Railway Asset Manager\n\n" + summary +
                               "\n\nThe reported exposure is observed maintenance cost "
                               "plus estimated service loss, not a replacement business case. "
                               "All proposed actions require human review.")}}
