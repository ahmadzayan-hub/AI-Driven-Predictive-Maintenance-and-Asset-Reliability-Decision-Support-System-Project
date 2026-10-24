"""Network-free, default-off selection shared by the API and durable worker.

Configuration describes capability, not provider entitlement, live-model quality,
or permission to activate a deployment. No credentials are created or changed.
"""

import hashlib
import json
import re
from urllib.parse import urlsplit

from server.model_gateway import ModelGateway, split_spec
from server.quota import ModelBudget
from server.storage import PostgresStore

PROFILE = "specialist_evidence"
REASONS = {
    "disabled": ("Specialist execution is disabled.", "تشغيل الوكلاء المستقلين غير مفعّل."),
    "invalid_flag": ("Use an explicit specialist activation value.", "يلزم إعداد صريح لتفعيل الوكلاء."),
    "managed_identity_required": ("Managed identity is required.", "يلزم مزود هوية مُدار."),
    "worker_execution_required": ("A background worker is required.", "يلزم عامل خلفي للتشغيل."),
    "database_publication_required": ("Reports must use durable database publication.", "يجب حفظ التقارير في قاعدة البيانات الدائمة."),
    "hosted_postgres_required": ("Hosted specialist work requires PostgreSQL.", "يتطلب التشغيل المستضاف قاعدة PostgreSQL."),
    "explicit_model_required": ("Select one configured provider and model explicitly.", "اختر مزودًا ونموذجًا مُعدّين بشكل صريح."),
    "router_not_supported": ("Specialist decisions cannot use automatic model routing.", "لا تسمح قرارات الوكلاء بتوجيه تلقائي للنماذج."),
    "durable_budget_required": ("Durable model admission is required.", "يلزم حد استخدام دائم لاستدعاءات النماذج."),
    "model_budget_zero": ("Model admission is currently set to zero.", "حد السماح باستدعاءات النماذج مضبوط على صفر."),
    "explicit_budget_required": ("Set an explicit positive integer model-admission limit.", "حدّد عددًا صحيحًا موجبًا وصريحًا لسقف استدعاءات النماذج."),
    "budget_configuration_mismatch": ("The durable model budget does not match this configuration.", "حد الاستخدام الدائم لا يطابق هذا الإعداد."),
    "model_unavailable": ("The selected model is unavailable or allows a different recipient.", "النموذج المحدد غير متاح أو يسمح بمزود بديل."),
    "configured_not_live_verified": ("Configured; live-model acceptance is not established by configuration.", "الإعداد مكتمل؛ لا يثبت ذلك نجاح اختبار نموذج فعلي."),
}


def explicit_model_limit(env):
    """Strict opt-in parsing only; ordinary legacy quota defaults are unchanged."""
    raw = env.get("AGENTIC_OS_QUOTA_MODEL_CALLS_PER_DAY")
    if not isinstance(raw, str) or not re.fullmatch(r"[0-9]{1,10}", raw):
        return None
    value = int(raw)
    return value if value <= 2147483647 else None


def configure_specialists(gateway, store, env, *, identity_mode, execution_mode, publish_target):
    """Return (explicit driver or None, safe capability), making no network call."""
    flag = env.get("AGENTIC_OS_SPECIALISTS_ENABLED", "0")
    status = {"profile": PROFILE, "enabled": flag == "1", "configured": False,
              "worker_capable": False, "live_model_verified": False,
              "acceptance_basis": "configuration_only_not_a_live_test"}

    def outcome(reason, driver=None):
        status.update(reason=reason, message=REASONS[reason][0], message_ar=REASONS[reason][1])
        return driver, status

    if flag != "1":
        return outcome("disabled" if flag in {"", "0"} else "invalid_flag")
    if identity_mode != "jwt":
        return outcome("managed_identity_required")
    if execution_mode != "worker":
        return outcome("worker_execution_required")
    if publish_target != "database":
        return outcome("database_publication_required")
    hosted = (env.get("VERCEL") == "1" or bool(env.get("AWS_LAMBDA_FUNCTION_NAME"))
              or env.get("AGENTIC_OS_ENV", "").lower() == "production")
    if hosted and not isinstance(store, PostgresStore):
        return outcome("hosted_postgres_required")
    if not isinstance(gateway, ModelGateway):
        return outcome("router_not_supported")
    selected = env.get("AGENTIC_OS_SPECIALIST_MODEL", "")
    if not isinstance(selected, str) or len(selected) > 160:
        return outcome("explicit_model_required")
    name, model = split_spec(selected)
    if not name or not model:
        return outcome("explicit_model_required")
    budget = getattr(gateway, "budget", None)
    if not isinstance(budget, ModelBudget) or budget.store is not store:
        return outcome("durable_budget_required")
    limit = explicit_model_limit(env)
    if limit is None:
        return outcome("explicit_budget_required")
    if limit == 0:
        return outcome("model_budget_zero")
    if budget.limits["model_calls_per_day"] != limit:
        return outcome("budget_configuration_mismatch")
    from server.specialists import GatewayDecisions
    try:
        driver = GatewayDecisions(gateway, selected)
    except (TypeError, ValueError, KeyError):
        return outcome("model_unavailable")
    recipient = name
    if name == "ollama":
        try:
            target = urlsplit(gateway.ollama_host)
            if (target.scheme not in {"http", "https"} or not target.hostname
                    or target.username or target.password or target.query or target.fragment):
                return outcome("model_unavailable")
        except ValueError:
            return outcome("model_unavailable")
        recipient = gateway.ollama_host.rstrip("/")
    # A changed custom endpoint must not resume a checkpoint for a different
    # recipient. Only a digest is persisted/exposed, never credentials or URLs.
    # The durable checkpoint, not just its advisory heartbeat, also binds every
    # effective admission limit. A worker configured with a larger daily quota
    # cannot resume a run admitted by an API with a smaller limit.
    binding = json.dumps(["specialist-runtime-v1", recipient, budget.limits], sort_keys=True)
    driver.identifier += "@" + hashlib.sha256(binding.encode()).hexdigest()[:20]
    status.update(configured=True, model=driver.provider,
                  admission_credits_per_owner_day=budget.limits["model_calls_per_day"],
                  configuration_id=hashlib.sha256(json.dumps(
                      ["specialist-runtime-v1", driver.identifier, budget.limits],
                      sort_keys=True).encode()).hexdigest()[:20])
    return outcome("configured_not_live_verified", driver)


def worker_prefix(capability):
    """A non-secret configuration binding in an existing trusted heartbeat ID.

    It proves only a matching factory advertised recent activity, not provider
    entitlement or live-model correctness. No schema or access grant is added.
    """
    return "specialist-v1-" + capability["configuration_id"] + "-"


def pipeline_metadata(capability):
    """Exact specialist plan, not an insertion into the deterministic pipeline."""
    if not capability["configured"]:
        return {"stages": [], "profiles": {}, "explicit_plans": {}}
    from server.specialists import SPECS, ROLE_NAMES
    anchors = ("collector", "descriptive", "reporter", "validator")
    stages = [{"role": spec.role, "title": spec.title, "title_ar": spec.title_ar,
               "after": anchor, "question": None, "can_fail_run": True}
              for spec, anchor in zip(SPECS, anchors)]
    return {"stages": stages, "profiles": {PROFILE: list(ROLE_NAMES)},
            "explicit_plans": {PROFILE: [*ROLE_NAMES, "publish"]}}
