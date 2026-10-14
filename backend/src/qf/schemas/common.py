"""Shared API envelope helpers aligned with the authoritative OpenAPI contract."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ResponseEnvelope(BaseModel):
    """Successful response envelope from 32-API规范.yaml."""

    model_config = ConfigDict(extra="forbid")

    code: str = "OK"
    message: str
    traceId: str
    data: Any | None = None


def success(data: Any, trace_id: str, message: str = "操作成功") -> dict[str, Any]:
    """Build a successful response without leaking transport internals."""
    return {"code": "OK", "message": message, "traceId": trace_id, "data": data}


def success_paged(
    data: Any, trace_id: str, *, page: int, page_size: int, total: int, message: str = "操作成功"
) -> dict[str, Any]:
    """GenericListResponse 分页信封：page/pageSize/total 与 data 同级（32-API规范）。"""
    return {
        "code": "OK",
        "message": message,
        "traceId": trace_id,
        "data": data,
        "page": page,
        "pageSize": page_size,
        "total": total,
    }


def error(
    code: str,
    message: str,
    trace_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a contract error envelope."""
    payload: dict[str, Any] = {"code": code, "message": message, "traceId": trace_id}
    if details:
        payload["details"] = details
    return payload
