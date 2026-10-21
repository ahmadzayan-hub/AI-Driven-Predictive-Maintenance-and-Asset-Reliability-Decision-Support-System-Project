"""Observed onboarding progress and runtime readiness; never a commercial score."""
from fastapi import Depends, HTTPException, Query

from server.operations import LIMITS, OperationsError, require_org_access
from server.operations_api import ARABIC_ERRORS
from server.storage import PostgresStore
from server.worker import worker_status


def readiness(store, principal, org_id, execution_mode, identity_mode):
    require_org_access(store, principal, org_id)
    def count(table, extra=""):
        # Tables/predicates are fixed by this module, never request strings.
        return store._exec(f"SELECT COUNT(*) AS n FROM {table} WHERE org_id = ? {extra}", (org_id,))[0]["n"]
    counts = {"members": count("organization_members", "AND role <> 'removed'"),
              "sites": count("operation_sites"), "assets": count("operation_assets"),
              "work_orders": count("work_orders"), "completed_work_orders": count("work_orders", "AND status = 'completed'"),
              "validation_protocols": count("reliability_trials")}
    execution = worker_status(store, execution_mode)
    return {"counts": counts, "execution": execution,
            "identity_mode": identity_mode,
            "database": "postgresql" if isinstance(store, PostgresStore) else "sqlite",
            "record_limits": {k: LIMITS[k] for k in ("organization_members", "operation_sites", "operation_assets", "work_orders")},
            "checks": [
                {"id": "managed_identity", "observed": identity_mode != "local"},
                {"id": "background_execution", "observed": execution_mode == "worker" and execution["ready"]},
                {"id": "registered_assets", "observed": counts["assets"] > 0},
                {"id": "maintenance_action_closed", "observed": counts["completed_work_orders"] > 0},
                {"id": "validation_protocol_registered", "observed": counts["validation_protocols"] > 0}],
            "external_acceptance": ["hosted_load_restart_restore", "independent_domain_validation",
                                    "live_source_contract", "customer_value_and_commercial_terms"],
            "scope": "observed_configuration_and_records_not_release_approval"}


def install_pilot_api(app, store, engine, current_principal, identity_mode):
    @app.get("/api/operations/organizations/{org_id}/readiness")
    def read_readiness(org_id: str, language: str = Query("en", pattern="^(en|ar)$"),
                       principal=Depends(current_principal)):
        try:
            return readiness(store, principal, org_id, engine.execution_mode, identity_mode)
        except OperationsError as error:
            message = ARABIC_ERRORS.get(error.code, "تعذر تنفيذ الإجراء.") if language == "ar" else error.message
            raise HTTPException(error.status, detail={"code": error.code, "message": message}) from None
