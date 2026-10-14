"""M1-P1：Provider 边界四项加固——超时 / 重试 / 降级 / 成本。

`HardenedPlanningProvider` 装饰任意 `PlanningGenerationProvider`：
- 超时：调用耗时超过 `settings.generation_timeout_ms` 视为失败（同步调用无法抢占，
  超时判定在返回后生效，输出丢弃并计入失败重试）；
- 重试：瞬时失败（超时 / 异常 / 输出结构判分失败）按 `max_attempts` 重试，
  backoff 可注入（测试注 no-op 保证确定性）；
- 降级：重试耗尽后 failover 到 deterministic-local（评估锚点），failover 自身
  失败则 fail-closed 抛 `GenerationUnavailableError`；
- 成本：每次调用追加一行记录（provider/method/duration/status/failover）到
  `provider_call_records`（sqlite_store v3 增量建表，只追加）。

输出结构判分复用既有 Pydantic schemas（strategy/plan），cases 按确定性 provider
的输出契约做形状校验。审核语义与持久化仍归应用层，本装饰器只管生成调用。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import ValidationError

from qf.config import settings
from qf.providers.planning import GeneratedCase, PlanningGenerationProvider, deterministic_planning_provider
from qf.schemas.planning import TestPlanVersionCreate, TestStrategyVersionCreate

_CASE_CONTENT_REQUIRED_KEYS = frozenset(
    {
        "title",
        "preconditions",
        "steps",
        "testDataRefs",
        "expectedResults",
        "priority",
        "testType",
        "assertions",
    }
)


class InvalidOutputError(Exception):
    """Provider 输出未通过结构判分。"""


class GenerationUnavailableError(Exception):
    """Fail-closed：重试耗尽且降级目标也失败。"""


def _validate_summary(result: Any) -> None:
    if not isinstance(result, str) or not result.strip():
        raise InvalidOutputError("summarize 输出必须是非空字符串")


def _validate_strategy(result: Any) -> None:
    if not isinstance(result, dict):
        raise InvalidOutputError("strategy 输出必须是对象")
    try:
        TestStrategyVersionCreate.model_validate(result)
    except ValidationError as exc:
        raise InvalidOutputError(f"strategy 输出结构判分失败: {exc.error_count()} 项") from exc


def _validate_plan(result: Any) -> None:
    if not isinstance(result, dict):
        raise InvalidOutputError("plan 输出必须是对象")
    try:
        TestPlanVersionCreate.model_validate(result)
    except ValidationError as exc:
        raise InvalidOutputError(f"plan 输出结构判分失败: {exc.error_count()} 项") from exc


def _validate_cases(result: Any) -> None:
    if not isinstance(result, list) or not result:
        raise InvalidOutputError("cases 输出必须是非空列表")
    for case in result:
        if not isinstance(case, GeneratedCase) or not case.title.strip():
            raise InvalidOutputError("case 必须是带非空标题的 GeneratedCase")
        if not isinstance(case.content, dict) or not all(key in case.content for key in _CASE_CONTENT_REQUIRED_KEYS):
            raise InvalidOutputError("case 内容缺少契约必填字段")


_OUTPUT_VALIDATORS: dict[str, Callable[[Any], None]] = {
    "summarize": _validate_summary,
    "strategy": _validate_strategy,
    "plan": _validate_plan,
    "cases": _validate_cases,
}

CallRecorder = Callable[[dict[str, Any]], None]


class HardenedPlanningProvider:
    """装饰器：为任意生成 provider 叠加超时/重试/降级/成本四项保障。"""

    def __init__(
        self,
        inner: PlanningGenerationProvider,
        *,
        fallback: PlanningGenerationProvider = deterministic_planning_provider,
        recorder: CallRecorder,
        max_attempts: int = 3,
        backoff: Callable[[int], None] = lambda _attempt: None,
    ) -> None:
        self._inner = inner
        self._fallback = fallback
        self._recorder = recorder
        self._max_attempts = max_attempts
        self._backoff = backoff
        self._failover_events: list[dict[str, Any]] = []
        # 对 Protocol 暴露被装饰 provider 的标识（包装后不变；生效提供者经成本记录追溯）
        self.provider_id = inner.provider_id
        self.provider_version = inner.provider_version

    def pop_failover_events(self) -> list[dict[str, Any]]:
        """取走自上次取走以来的 failover 留痕（供图编排层写入 state）。"""
        events = self._failover_events
        self._failover_events = []
        return events

    def summarize(self, source_content: str) -> str:
        return cast(str, self._invoke("summarize", (source_content,)))

    def strategy(self, source_summary: str) -> dict[str, Any]:
        return cast(dict[str, Any], self._invoke("strategy", (source_summary,)))

    def plan(
        self,
        source_summary: str,
        strategy_version_id: str,
        requirement_version_id: str,
        owner_id: str,
    ) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            self._invoke("plan", (source_summary, strategy_version_id, requirement_version_id, owner_id)),
        )

    def cases(self, source_summary: str, plan_version_id: str) -> list[GeneratedCase]:
        return cast(list[GeneratedCase], self._invoke("cases", (source_summary, plan_version_id)))

    def _invoke(self, method: str, args: tuple[Any, ...]) -> Any:
        validator = _OUTPUT_VALIDATORS[method]
        reason = "未知失败"
        for attempt in range(1, self._max_attempts + 1):
            started = time.monotonic()
            try:
                result = getattr(self._inner, method)(*args)
                duration_ms = int((time.monotonic() - started) * 1000)
                if duration_ms > settings.generation_timeout_ms:
                    reason = f"超时: {duration_ms}ms 超过 {settings.generation_timeout_ms}ms"
                    self._record(method, duration_ms, "TIMEOUT", self._inner)
                else:
                    validator(result)
                    self._record(method, duration_ms, "SUCCESS", self._inner)
                    return result
            except InvalidOutputError as exc:
                duration_ms = int((time.monotonic() - started) * 1000)
                reason = str(exc)
                self._record(method, duration_ms, "INVALID_OUTPUT", self._inner)
            except Exception as exc:  # noqa: BLE001 - provider 边界吞掉内部错误，靠 failover 收敛
                duration_ms = int((time.monotonic() - started) * 1000)
                reason = f"{type(exc).__name__}: {exc}"
                self._record(method, duration_ms, "FAILED", self._inner)
            if attempt < self._max_attempts:
                self._backoff(attempt)
        return self._failover(method, args, validator, reason)

    def _failover(
        self,
        method: str,
        args: tuple[Any, ...],
        validator: Callable[[Any], None],
        reason: str,
    ) -> Any:
        started = time.monotonic()
        try:
            result = getattr(self._fallback, method)(*args)
            validator(result)
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            self._record(method, duration_ms, "FAILED", self._fallback, failover=True)
            raise GenerationUnavailableError(f"降级目标也失败（原因: {reason}）: {exc}") from exc
        duration_ms = int((time.monotonic() - started) * 1000)
        self._record(method, duration_ms, "SUCCESS", self._fallback, failover=True)
        self._failover_events.append(
            {
                "method": method,
                "reason": reason,
                "fromProviderId": self._inner.provider_id,
                "fallbackProviderId": self._fallback.provider_id,
            }
        )
        return result

    def _record(
        self,
        method: str,
        duration_ms: int,
        status: str,
        provider: PlanningGenerationProvider,
        *,
        failover: bool = False,
    ) -> None:
        self._recorder(
            {
                "providerId": provider.provider_id,
                "providerVersion": provider.provider_version,
                "method": method,
                "durationMs": duration_ms,
                "status": status,
                "failover": failover,
                "occurredAt": datetime.now(UTC).isoformat(),
            }
        )
