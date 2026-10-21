"""HTTP boundary for organization maintenance operations."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from server.operations import Operations, OperationsError


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=1, max_length=128)


class OrganizationIn(Input):
    name: str = Field(min_length=1, max_length=160)


class SiteIn(Input):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)


class AssetFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    site_id: str = Field(min_length=1, max_length=64)
    external_id: str = Field(min_length=1, max_length=160)
    source_system: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    criticality: Literal["low", "medium", "high", "critical"] = "medium"


class AssetIn(AssetFields, Input):
    pass


class AssetsImportIn(Input):
    schema_version: Literal[1]
    assets: list[AssetFields] = Field(min_length=1, max_length=500)


class MemberIn(Input):
    subject: str = Field(min_length=1, max_length=256)
    role: Literal["owner", "manager", "technician", "viewer", "removed"]
    expected_version: int = Field(ge=1, strict=True)


class WorkOrderIn(Input):
    asset_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=2000)
    run_id: str = Field(min_length=1, max_length=64)
    asset_column: str = Field(min_length=1, max_length=200)
    source_asset_id: str = Field(min_length=1, max_length=160)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    assignee: str = Field(min_length=1, max_length=256)
    due_date: str = Field(min_length=10, max_length=10)


class PartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    part: str = Field(min_length=1, max_length=160)
    quantity: float = Field(gt=0, le=1000000, allow_inf_nan=False, strict=True)


class WorkOrdersImportIn(Input):
    schema_version: Literal[1]
    work_orders: list[WorkOrderIn] = Field(min_length=1, max_length=100)


class CompletionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: str = Field(min_length=1, max_length=120)
    notes: str = Field(min_length=1, max_length=2000)
    labor_hours: float = Field(ge=0, le=10000, allow_inf_nan=False, strict=True)
    parts: list[PartIn] = Field(default_factory=list, max_length=100)


class WorkOrderPatch(Input):
    expected_version: int = Field(ge=1, strict=True)
    status: Literal["authorized", "in_progress", "completed", "cancelled"] | None = None
    assignee: str | None = Field(default=None, min_length=1, max_length=256)
    due_date: str | None = Field(default=None, min_length=10, max_length=10)
    priority: Literal["low", "medium", "high", "critical"] | None = None
    completion: CompletionIn | None = None


ARABIC_ERRORS = {
    "organization_not_found": "لم يتم العثور على المؤسسة.",
    "record_not_found": "لم يتم العثور على السجل في هذه المؤسسة.",
    "permission_denied": "لا تسمح صلاحياتك بتنفيذ هذا الإجراء في المؤسسة.",
    "run_not_found": "لم يتم العثور على تحليل مصدر تملكه.",
    "evidence_not_ready": "يجب اكتمال التحليل قبل إعداد أمر الصيانة.",
    "asset_mismatch": "معرّف الأصل في المصدر لا يطابق الأصل المسجل.",
    "asset_not_in_evidence": "معرّف الأصل المسجل غير موجود في بيانات التحليل.",
    "ambiguous_asset_column": "اختر عمودًا واحدًا واضحًا لمعرّف الأصل في المصدر.",
    "stale_version": "تغير السجل. أعد تحميله قبل الحفظ.",
    "idempotency_conflict": "استُخدم معرّف الطلب نفسه مع مدخلات مختلفة.",
    "last_owner": "انقل الملكية قبل إزالة المالك الأخير.",
    "capacity_reached": "بلغت المؤسسة الحد المسموح لهذه السجلات.",
    "duplicate_asset": "هذا الأصل مسجل بالفعل ضمن نظام المصدر.",
    "duplicate_site": "يوجد موقع يحمل هذا الرمز بالفعل.",
    "invalid_assignee": "أسند العمل إلى مالك أو مدير أو فني نشط في المؤسسة.",
    "invalid_date": "أدخل تاريخ استحقاق صالحًا بصيغة YYYY-MM-DD.",
    "invalid_priority": "قيمة الأولوية غير صالحة.",
    "invalid_role": "دور العضو في المؤسسة غير صالح.",
    "terminal_order": "لا يمكن تغيير العمل المكتمل أو الملغى.",
    "invalid_transition": "الانتقال إلى حالة الصيانة المطلوبة غير مسموح.",
    "completion_required": "سجل نتيجة الصيانة قبل إكمال العمل.",
    "invalid_completion": "تُقبل بيانات النتيجة فقط عند إكمال العمل.",
    "invalid_labor": "أدخل عدد ساعات عمل محدودًا وغير سالب.",
    "invalid_parts": "قائمة القطع أو كمية إحدى القطع غير صالحة.",
    "invalid_import": "قدم صيغة استيراد الإصدار الأول وسجلات أصول صالحة.",
    "invalid_field": "تحقق من الحقول المطلوبة وصيغها وحدودها.",
    "ambiguous_asset_identity": "يتكرر معرّف الأصل في أكثر من نظام مصدر. تحقق من الهوية قبل مشاركة الأدلة.",
    "work_in_progress": "ألغِ العمل الجاري وأنشئ أمرًا بديلًا لتغيير بيانات التنفيذ.",
    "reassign_work_required": "أعد إسناد العمل المفتوح أو أغلقه قبل إزالة صلاحية التنفيذ.",
    "no_changes": "لم يتم تقديم تغيير في أمر الصيانة.",
}


def install_operations_api(app, store, current_principal):
    service = Operations(store)
    router = APIRouter(prefix="/api/operations")

    def invoke(language, function, *args):
        try:
            return function(*args)
        except OperationsError as error:
            message = ARABIC_ERRORS.get(error.code, "تعذر تنفيذ الإجراء. تحقق من المدخلات والصلاحيات.") if language == "ar" else error.message
            raise HTTPException(status_code=error.status, detail={"code": error.code, "message": message}) from None

    @router.get("/organizations")
    def organizations(principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.list_organizations, principal)

    @router.post("/organizations", status_code=201)
    def organization_create(body: OrganizationIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.create_organization, principal, body.model_dump())

    @router.get("/organizations/{org_id}/overview")
    def overview(org_id: str, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.overview, principal, org_id)

    @router.post("/organizations/{org_id}/members")
    def member(org_id: str, body: MemberIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.set_member, principal, org_id, body.model_dump())

    @router.post("/organizations/{org_id}/sites", status_code=201)
    def site(org_id: str, body: SiteIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.create_site, principal, org_id, body.model_dump())

    @router.post("/organizations/{org_id}/assets", status_code=201)
    def asset(org_id: str, body: AssetIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.create_asset, principal, org_id, body.model_dump())

    @router.post("/organizations/{org_id}/import/assets", status_code=201)
    def asset_import(org_id: str, body: AssetsImportIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.import_assets, principal, org_id, body.model_dump())

    @router.post("/organizations/{org_id}/work-orders", status_code=201)
    def work_create(org_id: str, body: WorkOrderIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.create_work_order, principal, org_id, body.model_dump())

    @router.post("/organizations/{org_id}/import/work-orders", status_code=201)
    def work_import(org_id: str, body: WorkOrdersImportIn, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.import_work_orders, principal, org_id, body.model_dump())

    @router.get("/organizations/{org_id}/work-orders/{order_id}")
    def work_read(org_id: str, order_id: str, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.work_order, principal, org_id, order_id)

    @router.patch("/organizations/{org_id}/work-orders/{order_id}")
    def work_update(org_id: str, order_id: str, body: WorkOrderPatch, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.update_work_order, principal, org_id, order_id, body.model_dump(exclude_unset=True))

    @router.get("/organizations/{org_id}/export")
    def export(org_id: str, principal=Depends(current_principal), language: str = Query("en", pattern="^(en|ar)$")):
        return invoke(language, service.export, principal, org_id)

    app.include_router(router)
    return service
