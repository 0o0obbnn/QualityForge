"""QualityForge FastAPI reference runtime."""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from qf.api.v1.auth import router as auth_router
from qf.api.v1.collaboration import router as collaboration_router
from qf.api.v1.observability import router as observability_router
from qf.api.v1.planning import router as planning_router
from qf.api.v1.quality import router as quality_router
from qf.api.v1.run_control import router as run_control_router
from qf.config import settings
from qf.log import TRACE_ID, configure_logging
from qf.schemas.common import error
from qf.services.planning_workflow import DomainError

configure_logging()
LOGGER = logging.getLogger(__name__)
SAFE_TRACE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")

app = FastAPI(
    title="QualityForge API",
    description="AI原生端到端测试平台 — Gate 0 planning vertical slice",
    version="0.3.0",
)
app.include_router(auth_router)
app.include_router(planning_router)
app.include_router(collaboration_router)
app.include_router(run_control_router)
app.include_router(quality_router)
app.include_router(observability_router)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Attach a safe trace ID and baseline security headers."""
    incoming = request.headers.get("X-Request-ID", "")
    request.state.trace_id = incoming if SAFE_TRACE_ID.fullmatch(incoming) else str(uuid.uuid4())
    token = TRACE_ID.set(request.state.trace_id)
    try:
        response = await call_next(request)
        LOGGER.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    finally:
        TRACE_ID.reset(token)
    response.headers["X-Request-ID"] = request.state.trace_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; "
        "script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'"
    )
    return response


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env, "runtime": "stage4-local-sqlite"}


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    LOGGER.warning("Domain error %s: %s", exc.code, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, request.state.trace_id, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    LOGGER.warning("Validation failed: %s issue(s)", len(exc.errors()))
    safe_details = {
        "fields": [{"location": [str(item) for item in issue["loc"]], "type": issue["type"]} for issue in exc.errors()]
    }
    return JSONResponse(
        status_code=422,
        content=error("VALIDATION_FAILED", "请求参数校验失败", request.state.trace_id, safe_details),
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT"}.get(
        exc.status_code, "VALIDATION_FAILED"
    )
    LOGGER.warning("HTTP %s -> %s", exc.status_code, code)
    return JSONResponse(
        status_code=exc.status_code,
        content=error(code, "请求无法处理", request.state.trace_id),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    LOGGER.exception("Unhandled request failure", extra={"trace_id": request.state.trace_id})
    return JSONResponse(
        status_code=500,
        content=error("INTERNAL_ERROR", "服务器内部错误", request.state.trace_id),
    )


if settings.frontend_dist.exists():
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
