"""One additive API error contract, with legacy `detail` kept for old clients.

Do not include validation inputs, exception reprs or stack traces. A request id
lets operators find the failure without returning private request contents.
"""

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


STATUS_CODES = {
    400: "invalid_request", 401: "authentication_required", 403: "permission_denied",
    404: "not_found", 405: "method_not_allowed", 409: "conflict",
    413: "payload_too_large", 422: "validation_failed", 429: "rate_limited",
    500: "internal_error", 503: "service_unavailable",
}


def error_body(request, status, detail, *, code=None, problems=None):
    """Canonical fields are stable across the core, Operations and RMD APIs."""
    arabic = (request.query_params.get("language") == "ar"
              or request.headers.get("accept-language", "").lower().startswith("ar"))
    message = ("تعذر إكمال الطلب." if arabic else "The request could not be completed.")
    if isinstance(detail, str):
        message = detail
    elif isinstance(detail, dict):
        message = detail.get("message") if isinstance(detail.get("message"), str) else message
        code = code or detail.get("code")
        problems = problems if problems is not None else detail.get("errors", [])
    return {
        "error": {
            "code": code if isinstance(code, str) else STATUS_CODES.get(status, "request_failed"),
            "message": message,
            "problems": problems if isinstance(problems, list) else [],
            "request_id": getattr(request.state, "request_id", None),
        },
        # Compatibility for already installed web/native clients. New clients
        # consume `error`; retain field-error objects during migration.
        "detail": detail,
    }


def error_response(request, status, detail, *, code=None, problems=None, headers=None):
    return JSONResponse(error_body(request, status, detail, code=code, problems=problems),
                        status_code=status, headers=headers)


def install_error_handlers(app):
    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(request, exc.status_code, exc.detail, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        # Pydantic's default includes `input` and sometimes arbitrary `ctx`.
        # Neither is necessary for a field error, and both may contain rows or
        # credentials. Retain only locations, types and bounded descriptions.
        issues = [{"loc": list(item["loc"]), "type": item["type"],
                   "msg": item["msg"]} for item in exc.errors()]
        arabic = (request.query_params.get("language") == "ar"
                  or request.headers.get("accept-language", "").lower().startswith("ar"))
        message = "راجع الحقول المحددة ثم أعد المحاولة." if arabic else "Check the indicated fields and try again."
        body = error_body(request, 422, issues, code="validation_failed", problems=issues)
        body["error"]["message"] = message
        return JSONResponse(body, status_code=422)


def document_errors(schema):
    """Describe the actual common failure shape without exposing a public spec."""
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    schema["components"].setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http", "scheme": "bearer", "bearerFormat": "JWT",
        "description": "Managed-provider token. Local mode uses its single local owner.",
    }
    components["ApiErrorEnvelope"] = {
        "type": "object", "required": ["error", "detail"],
        "properties": {
            "error": {"type": "object", "required": ["code", "message", "problems", "request_id"],
                      "properties": {
                          "code": {"type": "string"}, "message": {"type": "string"},
                          "problems": {"type": "array", "items": {"type": "object"}},
                          "request_id": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                      }},
            "detail": {"description": "Legacy compatibility field; clients should read error."},
        },
    }
    for name, path in schema.get("paths", {}).items():
        for operation in path.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            if name.startswith("/api/") and name not in ("/api/health", "/api/auth/config"):
                operation["security"] = [{"BearerAuth": []}]
            for status in (401, 403, 404, 409, 422, 429, 500):
                response = operation["responses"].setdefault(str(status), {"description": "Request failed"})
                response["content"] = {"application/json": {"schema": {"$ref": "#/components/schemas/ApiErrorEnvelope"}}}
    return schema
