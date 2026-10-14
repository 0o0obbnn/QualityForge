---
name: api-test-generator
description: 已草拟 API 测试脚本（pytest/httpx）的契约门禁。在测试用例已携带 expected_results 且其断言已通过 assertion-verifier 校验之后、脚本提交或执行之前使用。运行四项确定性检查——无硬编码环境配置与密钥、fixture 依赖已声明、断言覆盖 expected_results。断言未验证前不得运行；UI 或性能脚本不得使用（改用 ui-automation-generator 或 performance-test-generator）；测试用例尚无 expected_results 时不得使用。
---

# API Test Generator

把测试用例与已验证的断言转化为可执行的 pytest/httpx 脚本。
生成是 LLM 的工作；契约检查是确定性的，是本 skill 的「牙齿」。

## 四项契约检查

| 检查项                    | Code                        | 拦截什么                                                   |
| ------------------------- | --------------------------- | ---------------------------------------------------------- |
| 无硬编码环境配置          | `HARDCODED_ENV`             | URL/主机/端口以字符串字面量出现，而非配置注入。            |
| 无硬编码密钥              | `HARDCODED_SECRET`          | token/密码/API key 以明文字面量出现（未用 `os.environ`）。 |
| fixture 依赖已声明        | `MISSING_FIXTURE_DECL`      | 脚本有 expected_results 但未声明 fixture_deps。            |
| 断言覆盖 expected_results | `UNCOVERED_EXPECTED_RESULT` | 某个 expected_result 没有对应的 assert 语句。              |

安全模式——`os.environ["TOKEN"]` 与含变量引用的 f-string
（`f"Bearer {token}"`）——明确不判违规。

## 集成

- **输入**：测试用例（含 expected_results）+ 已验证的断言契约
  - fixture DAG 节点 ID。
- **输出**：一份通过校验的脚本，或带具体 findings 的 REJECT。
- **PASS 时**：脚本可执行；fixture 声明告知执行器先构建哪个环境。
- **REJECT 时**：修复具体 finding 后只重跑本 skill。

## 运行确定性检查器

契约检查是本 skill 的牙齿，它是一个脚本——绝不在散文中重新推导：

```bash
python scripts/api_check.py --script path/to/api_script.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

`code` 体为空（`EMPTY_SCRIPT_BODY`）或未声明 `expected_results`
（`NO_EXPECTED_RESULTS_DECLARED`）的脚本一律 REJECT。两种缺失都会静默
禁用扫描相应字段的检查，而未能运行的检查绝不能被报告为已通过。

## 本 skill 禁止事项

- **绝不硬编码认证 token、密钥、URL 或主机。** 使用配置注入
  （`os.environ`、`config.*`）。
- **绝不跳过响应 schema 结构断言。** 每个 `expected_result` 都要有对应的
  assert。
- **绝不提交没有 expected_results 的脚本并称之为干净。** 期望缺失意味着
  断言覆盖门禁从未运行。
- **绝不在本 skill 生成 UI 自动化。** 那是 `ui-automation-generator` 的
  职责。

## 使用示例

**示例 1 —— 正确触发**

```
TC-001（GET /api/v1/orders，期望 200）与 TC-002（POST 创建订单，
期望 order_id 非空）已通过 assertion-verifier 校验（PASS）。
已声明 fixture_deps=["setup_user_session","create_order"]。请生成 pytest 脚本。
```

→ 运行契约检查；四项门禁全过 → PASS，脚本可执行。

**示例 2 —— 错误触发（不要使用本 skill）**

```
给登录 UI 页面生成测试代码。
```

→ 这是 UI 自动化，不是 API。请改用 `ui-automation-generator`。

硬编码配置的正则模式与断言覆盖规则见 `references/api_contract.md`。
