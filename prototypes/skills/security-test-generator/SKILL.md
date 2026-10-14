---
name: security-test-generator
description: 生成并门禁安全测试用例（SQL 注入、XSS、authz 绕过、API 安全）。在存在带显式 In_Scope 清单的安全测试策略、且 IR 中已绑定权限规则时使用。强制三项必查——只测范围内目标、authz 绑定 IR 权限规则、漏洞细节脱敏。没有策略范围文档不得触发。功能正确性测试不得使用（改用 api-test-generator）。不得对 In_Scope 之外的 endpoint 生成测试，哪怕只是试探。
---

# Security Test Generator

把安全需求转化为测试用例。这是对安全最敏感的生成器——没有护栏的
安全测试本身就是风险。

## 三项契约检查

| 检查项 | Code | 拦截什么 |
|---|---|---|
| 只测范围内目标 | `OUT_OF_SCOPE_TARGET` | 测试指向策略 In_Scope 之外的 endpoint。 |
| authz 测试绑定规则 | `AUTHZ_WITHOUT_RULE_BINDING` | 授权绕过测试没有权限规则绑定。 |
| 漏洞细节不明文 | `PLAINTEXT_VULN_DETAIL` | 报告含未脱敏、可利用的漏洞细节。 |

对范围外的 endpoint 跑安全测试本身就是风险——可能对并非为安全探测
设计的基础设施触发非预期副作用，并违反约定的测试边界。

## 集成

- **输入**：strategy contract（安全范围）+ interface contracts + IR
  权限规则。
- **输出**：通过校验的安全测试用例（脱敏报告格式）。
- **若被流水线消费**：findings 走专用 security-reporting 通道，
  绝不进通用缺陷看板。



## 范围是授权，不是过滤器

必须声明 `in_scope_endpoints`。它缺失绝不意味着"一切皆可测"——而意味着
授权无法确认，即 `SCOPE_UNDECLARED`。同样，没有 `target_endpoint` 的用例
判 `OUT_OF_SCOPE_TARGET`；authz 测试绑定了 `permission_rule_id` 但没有提供
已知规则集的，判 `AUTHZ_WITHOUT_RULE_BINDING`：无法验证的绑定按缺失处理。
未授权扫描正是本门禁要防止的伤害，因此范围声明缺失绝不能放大范围。

## 运行确定性检查器

```bash
python scripts/security_check.py --packet path/to/security_cases.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **绝不对生产环境执行破坏性 payload。** 只允许隔离环境。
- **绝不测试声明安全范围之外的 endpoint。** 那是未授权扫描，与意图无关。
- **绝不把未声明的范围当作许可。** 授权缺失不等于默示授权。
- **绝不明文输出可利用的漏洞细节。** findings 经脱敏后走 security-reporting 通道。

## 使用示例

**示例 1 —— 正确触发**
```
安全策略 In_Scope=["/api/v1/orders","/api/v1/users"]。
IR 权限规则 PERM-003："用户只能读取自己的订单"。
给 /api/v1/orders 生成 SQL 注入与 authz 绕过测试。
```
→ authz 测试正确绑定到 PERM-003 → 检查通过；目标在范围内 → PASS。

**示例 2 —— 错误触发（不得使用本 skill）**
```
/api/v1/admin/config 这个 endpoint 看起来有风险。给它测一下 SQL 注入。
```
→ /api/v1/admin/config 不在 In_Scope → REJECT OUT_OF_SCOPE_TARGET。
不得在声明范围之外跑安全测试。

范围强制规则、authz 绑定要求与脱敏策略，见 `references/security_contract.md`。
