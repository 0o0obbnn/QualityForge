# 性能测试脚本契约

`scripts/perf_check.py` 是可执行编码；本文件描述其意图。

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `MOCK_DEP_PERF_ASSERT` | REJECT | 对 mocked 依赖做性能断言。 |
| `SHARED_DATA_NAMESPACE` | REJECT | 压测数据与功能测试共享命名空间。 |
| `THRESHOLD_NOT_FROM_STRATEGY` | REJECT | 阈值并非来自策略契约。 |

## 为什么 mock 依赖上的性能断言毫无意义

mocked 依赖即时响应（它只是 stub）。对着 mock 断言"支付网关响应 < 200ms"，测的是 mock 的响应时间，不是真实网关。结果是虚假信心——真实网关在负载下可能要花 2 秒。

## 数据隔离

压测数据必须使用独立命名空间（例如 `loadtest_*` 表前缀、独立 fixture 命名空间）。与功能测试共享意味着：
- 压测数据量拖垮功能测试速度。
- 功能测试的数据写入污染压测基线。
