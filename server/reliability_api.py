"""Authenticated, organization-scoped shadow-validation endpoints."""

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from server.reliability_validation import ReliabilityTrials, ValidationError
from server.operations import OperationsError
from server.operations_api import ARABIC_ERRORS

ERRORS = {
    "field": ("Check the supplied value and its allowed range.", "تحقق من القيمة المدخلة والنطاق المسموح."),
    "timestamp": ("Use an ISO date and time with a timezone.", "استخدم تاريخاً ووقتاً بتنسيق ISO مع المنطقة الزمنية."),
    "chronology": ("The supplied dates violate the registered prediction window.", "التواريخ المدخلة لا تتوافق مع نافذة التنبؤ المسجلة."),
    "missing": ("Validation record not found.", "لم يتم العثور على سجل التحقق."),
    "limit": ("This validation ledger has reached its record limit.", "بلغ سجل التحقق الحد الأقصى للسجلات."),
    "asset": ("Register this asset in the selected organization first.", "سجّل هذا الأصل في المؤسسة المختارة أولاً."),
    "replay": ("This request identifier was already used with different values.", "استُخدم معرّف الطلب مسبقاً بقيم مختلفة."),
    "conflict": ("This record changed. Reload it before submitting.", "تغيّر هذا السجل. أعد تحميله قبل الإرسال."),
    "overlap": ("This asset already has an open prediction window.", "لهذا الأصل نافذة تنبؤ مفتوحة بالفعل."),
    "immutable": ("This adjudication is final. Corrections require a new documented trial.", "هذا التقييم نهائي. تتطلب التصحيحات تجربة موثقة جديدة."),
    "immature": ("Wait until the full prediction window has ended.", "انتظر حتى انتهاء نافذة التنبؤ كاملة."),
    "followup": ("Confirm observation through the full prediction window, no later than now.", "أكد اكتمال المتابعة خلال نافذة التنبؤ دون تجاوز الوقت الحالي."),
}


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrialIn(Input):
    request_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    model_version: str = Field(min_length=1, max_length=200)
    baseline_name: str = Field(min_length=1, max_length=200)
    trained_through: str = Field(max_length=50)
    horizon_hours: float = Field(ge=1, le=8760, strict=True)
    threshold: float = Field(ge=0, le=1, strict=True)
    failure_definition: str = Field(min_length=1, max_length=1000)
    cohort_definition: str = Field(min_length=1, max_length=1000)


class PredictionIn(Input):
    revision: int = Field(ge=1, strict=True)
    request_id: str = Field(min_length=1, max_length=80)
    asset_id: str = Field(min_length=1, max_length=80)
    probability: float = Field(ge=0, le=1, strict=True)
    baseline_probability: float = Field(ge=0, le=1, strict=True)


class OutcomeIn(Input):
    revision: int = Field(ge=1, strict=True)
    failed: StrictBool
    actionable: StrictBool | None = None
    failure_at: str | None = Field(default=None, max_length=50)
    observed_through: str = Field(max_length=50)
    evidence_reference: str = Field(min_length=1, max_length=500)


def install_reliability_api(app, store, current_principal):
    trials = ReliabilityTrials(store)
    app.state.reliability_trials = trials

    def invoke(operation, language):
        try:
            return operation()
        except ValidationError as error:
            message = ERRORS[error.code][language == "ar"]
            raise HTTPException(error.status, detail={"code": error.code, "message": message}) from None
        except OperationsError as error:
            message = ARABIC_ERRORS.get(error.code, "تعذر تنفيذ الإجراء.") if language == "ar" else error.message
            raise HTTPException(error.status, detail={"code": error.code, "message": message}) from None

    @app.get("/api/operations/organizations/{org_id}/trials")
    def list_trials(org_id: str, language: str = Query(default="en", pattern="^(en|ar)$"),
                    principal=Depends(current_principal)):
        return invoke(lambda: {"trials": trials.list(principal, org_id)}, language)

    @app.post("/api/operations/organizations/{org_id}/trials", status_code=201)
    def create_trial(org_id: str, body: TrialIn,
                     language: str = Query(default="en", pattern="^(en|ar)$"),
                     principal=Depends(current_principal)):
        return invoke(lambda: trials.create(principal, org_id, body.model_dump()), language)

    @app.get("/api/operations/trials/{trial_id}")
    def get_trial(trial_id: str, language: str = Query(default="en", pattern="^(en|ar)$"),
                  principal=Depends(current_principal)):
        return invoke(lambda: trials.get(principal, trial_id), language)

    @app.post("/api/operations/trials/{trial_id}/predictions")
    def predict(trial_id: str, body: PredictionIn,
                language: str = Query(default="en", pattern="^(en|ar)$"),
                principal=Depends(current_principal)):
        return invoke(lambda: trials.predict(principal, trial_id, body.model_dump()), language)

    @app.post("/api/operations/trials/{trial_id}/predictions/{prediction_id}/outcome")
    def adjudicate(trial_id: str, prediction_id: str, body: OutcomeIn,
                   language: str = Query(default="en", pattern="^(en|ar)$"),
                   principal=Depends(current_principal)):
        return invoke(lambda: trials.adjudicate(principal, trial_id, prediction_id, body.model_dump()), language)
