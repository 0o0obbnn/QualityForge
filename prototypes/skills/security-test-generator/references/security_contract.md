# 安全测试用例契约

`scripts/security_check.py` 是可执行编码；本文件描述其意图。

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `OUT_OF_SCOPE_TARGET` | REJECT | 目标端点不在策略 In_Scope 中。 |
| `AUTHZ_WITHOUT_RULE_BINDING` | REJECT | 授权测试未绑定权限规则。 |
| `PLAINTEXT_VULN_DETAIL` | REJECT | 报告含未脱敏的可利用细节。 |

## 范围强制（安全规则）

安全测试 MUST 只指向策略 In_Scope 中声明的端点。测试范围外的端点就是未授权扫描——即使该测试"能发现 bug"，未经授权运行本身就是策略违规，且可能违法。

## 脱敏策略

报告不得包含：
- 完整的 exploit payload（脱敏为 "SQL injection payload"）。
- 概念验证命令。
- 可用于复现的攻击向量细节。

报告应写"端点 X 存在 SQL 注入漏洞（class: CWE-89）"——足够分诊，不足以利用。
