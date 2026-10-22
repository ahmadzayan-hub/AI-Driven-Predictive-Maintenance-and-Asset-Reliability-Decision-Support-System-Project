"""HTTP boundary for private RMD evidence; cached public responses are forbidden."""

from urllib.parse import quote
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from server.datasets import DatasetError
from server.rmd_service import MAX_SOURCE_BYTES, RmdError, RmdService


PRIVATE_HEADERS = {"Cache-Control": "private, no-store, max-age=0", "Pragma": "no-cache",
                   "X-Content-Type-Options": "nosniff", "Vary": "Authorization"}


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: str = Field(min_length=1, max_length=128)


def install_rmd_api(app, store, current_principal, identity_mode, env=None, engine=None):
    """Reuse application identity/store. Every service operation checks current ACLs."""
    service = RmdService(store, identity_mode=identity_mode, env=env)
    service.vault_dir = getattr(engine, "vault_dir", None)
    from server import rmd_assistant, rmd_workflow
    app.state.rmd = service
    router = APIRouter(prefix="/api/rmd", tags=["RMD evidence"])

    # This includes dependency authentication failures and request validation
    # responses, which do not reach a route's successful-response headers.
    @app.middleware("http")
    async def private_evidence_responses(request: Request, call_next):
        private = request.url.path == "/api/rmd" or request.url.path.startswith("/api/rmd/")
        try:
            response = await call_next(request)
        except Exception as error:
            if not private:
                raise
            # Keep private source text, converter paths and SQL parameters out
            # of both unexpected responses and observability event payloads.
            logging.getLogger(__name__).error("Private evidence request failed: %s", type(error).__name__)
            response = JSONResponse({"detail": {"code": "evidence_unavailable", "message":
                "تعذّر إكمال طلب الأدلة." if request.query_params.get("language") == "ar" else "The evidence request could not be completed."}}, status_code=500)
        if private:
            response.headers.update(PRIVATE_HEADERS)
        return response

    def invoke(method, *args, language="en", **kwargs):
        try:
            return method(*args, **kwargs)
        except RmdError as error:
            message = error.arabic if language == "ar" else error.message
            raise HTTPException(error.status, detail={"code": error.code, "message": message},
                                headers=PRIVATE_HEADERS) from None
        except DatasetError as error:
            raise HTTPException(error.status, detail={"code": "source_extraction_failed",
                "message": error.ar if language == "ar" else error.en}, headers=PRIVATE_HEADERS) from None

    def download(method, *args, language="en", **kwargs):
        content, content_type, name = invoke(method, *args, language=language, **kwargs)
        # ASCII fallback is constant; supplied Unicode names are encoded rather
        # than interpolated into a header. No server paths are ever exposed.
        return Response(content, media_type=content_type, headers={**PRIVATE_HEADERS,
            "Content-Disposition": "attachment; filename=\"evidence-download\"; filename*=UTF-8''" + quote(name, safe="")})

    @router.get("/packs")
    def packs(language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.list_packs, principal, language=language)

    @router.post("/packs")
    def create_pack(payload: dict = Body(...), language: str = Query("en", pattern="^(en|ar)$"),
                    principal=Depends(current_principal)):
        return invoke(service.create_pack, principal, payload, language=language)

    @router.get("/packs/{pack_id}")
    def pack(pack_id: str, language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.get_pack, principal, pack_id, language=language)

    @router.delete("/packs/{pack_id}")
    def delete_pack(pack_id: str, language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.delete_pack, principal, pack_id, language=language)

    @router.post("/packs/{pack_id}/sources")
    async def upload(pack_id: str, request: Request, filename: str = Query(..., min_length=1, max_length=240),
                     kind: str = Query(..., pattern="^(procedure|workbook)$"),
                     language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        # Authorization precedes reading/converting a potentially expensive file.
        await run_in_threadpool(invoke, service._pack, principal, pack_id, "write", language=language)
        declared = request.headers.get("content-length")
        if declared and (not declared.isdecimal() or int(declared) > MAX_SOURCE_BYTES):
            raise HTTPException(413, detail={"code": "invalid_source_size", "message":
                "حجم المصدر يتجاوز 4 ميجابايت." if language == "ar" else "The source exceeds 4 MB."}, headers=PRIVATE_HEADERS)
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_SOURCE_BYTES:
                raise HTTPException(413, detail={"code": "invalid_source_size", "message":
                    "حجم المصدر يتجاوز 4 ميجابايت." if language == "ar" else "The source exceeds 4 MB."}, headers=PRIVATE_HEADERS)
        return await run_in_threadpool(invoke, service.import_source, principal, pack_id,
                                       filename, bytes(data), kind, language=language)

    @router.get("/packs/{pack_id}/sources/{source_id}")
    def source(pack_id: str, source_id: str, language: str = Query("en", pattern="^(en|ar)$"),
               principal=Depends(current_principal)):
        return invoke(service.get_source, principal, pack_id, source_id, language=language)

    @router.put("/packs/{pack_id}/sources/{source_id}/mapping")
    def mapping(pack_id: str, source_id: str, payload: dict = Body(...),
                language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.save_mapping, principal, pack_id, source_id, payload, language=language)

    @router.patch("/packs/{pack_id}/sources/{source_id}/applicability")
    def applicability(pack_id: str, source_id: str, payload: dict = Body(...),
                      language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.update_applicability, principal, pack_id, source_id, payload, language=language)

    @router.get("/packs/{pack_id}/sources/{source_id}/download")
    def original(pack_id: str, source_id: str, language: str = Query("en", pattern="^(en|ar)$"),
                 principal=Depends(current_principal)):
        return download(service.download_source, principal, pack_id, source_id, language=language)

    @router.get("/packs/{pack_id}/sources/{source_id}/artifacts/{artifact_id}/download")
    def artifact(pack_id: str, source_id: str, artifact_id: str,
                 language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return download(service.download_source, principal, pack_id, source_id, artifact_id, language=language)

    @router.post("/packs/{pack_id}/analyses")
    def analyse(pack_id: str, payload: dict = Body(...), language: str = Query("en", pattern="^(en|ar)$"),
                principal=Depends(current_principal)):
        # The query selects the requested report language unless explicitly set.
        return invoke(service.create_analysis, principal, pack_id, {"language": language, **payload}, language=language)

    @router.get("/packs/{pack_id}/analyses/{analysis_id}")
    def analysis(pack_id: str, analysis_id: str, language: str = Query("en", pattern="^(en|ar)$"),
                 principal=Depends(current_principal)):
        return invoke(service.get_analysis, principal, pack_id, analysis_id, language=language)

    @router.post("/packs/{pack_id}/analyses/{analysis_id}/review-run")
    def review_run(pack_id: str, analysis_id: str, payload: ReviewRequest,
                   language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        invoke(service._pack, principal, pack_id, "write", language=language)
        if engine is None:
            raise HTTPException(503, detail={"code": "review_engine_unavailable", "message":
                "محرك مراجعة النشر غير متاح." if language == "ar" else "The publication review engine is unavailable."}, headers=PRIVATE_HEADERS)
        return invoke(rmd_workflow.create_review_run, service, engine, principal, pack_id,
                      analysis_id, payload.model_dump(), language=language)

    @router.post("/packs/{pack_id}/assistant")
    def assistant(pack_id: str, payload: dict = Body(...), language: str = Query("en", pattern="^(en|ar)$"),
                  principal=Depends(current_principal)):
        return invoke(rmd_assistant.explain, getattr(app.state, "assistant", None), service,
                      principal, pack_id, {"language": language, **payload}, language=language)

    @router.get("/packs/{pack_id}/analyses/{analysis_id}/records")
    def records(pack_id: str, analysis_id: str, grain: str | None = None,
                offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.records, principal, pack_id, analysis_id,
                      {"grain": grain, "offset": offset, "limit": limit}, language=language)

    @router.post("/packs/{pack_id}/analyses/{analysis_id}/records/query")
    def query_records(pack_id: str, analysis_id: str, payload: dict = Body(...),
                      language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.records, principal, pack_id, analysis_id, payload, language=language)

    @router.get("/packs/{pack_id}/knowledge")
    def knowledge(pack_id: str, q: str = Query("", max_length=500), source_id: str | None = None,
                  limit: int = Query(20, ge=1, le=100), language: str = Query("en", pattern="^(en|ar)$"),
                  principal=Depends(current_principal)):
        return invoke(service.search_knowledge, principal, pack_id, q, source_id or None, limit, language=language)

    @router.get("/packs/{pack_id}/links")
    def links(pack_id: str, analysis_id: str | None = None,
              language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.list_links, principal, pack_id, analysis_id, language=language)

    @router.patch("/packs/{pack_id}/links/{link_id}")
    def review_link(pack_id: str, link_id: str, payload: dict = Body(...),
                    language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.review_link, principal, pack_id, link_id, payload, language=language)

    @router.post("/packs/{pack_id}/incidents")
    def incident(pack_id: str, payload: dict = Body(...), language: str = Query("en", pattern="^(en|ar)$"),
                 principal=Depends(current_principal)):
        return invoke(service.create_incident, principal, pack_id, payload, language=language)

    @router.get("/packs/{pack_id}/actions")
    def actions(pack_id: str, language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.list_actions, principal, pack_id, language=language)

    @router.post("/packs/{pack_id}/actions")
    def propose_action(pack_id: str, payload: dict = Body(...),
                       language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.create_action, principal, pack_id, payload, language=language)

    @router.patch("/packs/{pack_id}/actions/{action_id}")
    def action_state(pack_id: str, action_id: str, payload: dict = Body(...),
                     language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.update_action, principal, pack_id, action_id, payload, language=language)

    @router.get("/packs/{pack_id}/audit")
    def audit(pack_id: str, language: str = Query("en", pattern="^(en|ar)$"), principal=Depends(current_principal)):
        return invoke(service.audit, principal, pack_id, language=language)

    @router.get("/packs/{pack_id}/analyses/{analysis_id}/export")
    def export(pack_id: str, analysis_id: str, format: str = Query("html", pattern="^(html|csv)$"),
               fingerprint: str | None = None, language: str = Query("en", pattern="^(en|ar)$"),
               principal=Depends(current_principal)):
        return download(lambda: service.export(principal, pack_id, analysis_id, format,
                        language=language, fingerprint=fingerprint), language=language)

    app.include_router(router)
    return service
