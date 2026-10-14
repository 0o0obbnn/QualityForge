"""极简日志配置 — 标准库 logging + trace_id 关联。

错误信封与响应头返回的 traceId 可通过本配置在日志输出中过滤，
打通「响应层 -> 日志层」的失败诊断链路。
"""

from __future__ import annotations

import contextvars
import logging

# 当前请求的 trace_id；中间件在请求入口设置，日志 Filter 注入每条记录。
TRACE_ID: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


class TraceIdFilter(logging.Filter):
    """为每条日志记录补充 trace_id 字段（无请求上下文时为 '-'）。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = TRACE_ID.get()
        return True


_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    """为 qf 命名空间装配携带 trace_id 的控制台输出（幂等）。"""
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s [%(trace_id)s] %(message)s")
    )
    handler.addFilter(TraceIdFilter())
    logger = logging.getLogger("qf")
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True
