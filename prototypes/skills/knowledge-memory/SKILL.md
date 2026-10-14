---
name: knowledge-memory
description: 候选知识记忆条目的合规门禁。在 agent 提出一条记忆条目之后、写入共享知识库之前使用——每个条目都要先过这道门。REJECT 缺少出处或时间戳的、含未脱敏凭证或 PII 的、携带未经审核反馈的、或与已存内容重复的条目。不得用本 skill 撰写记忆条目——它只负责校验。
---

# Knowledge Memory (Compliance Gate)

每个候选记忆条目在写入其他 agent 读取的共享知识库之前，都要先过这道门。它校验条目，不撰写条目。

## 本 skill 为何存在

AI agent 的记忆一旦不受监管，就会变成垃圾场。存入未经验证的反馈、存入重复内容，或更糟——存入敏感数据（如密码或 PII）——都会腐蚀知识库。本 skill 扮演守门人，保证只有高质量、安全、可追溯的知识进入记忆系统。

## finding code 与路由

| Code | 严重级别 | 含义 |
|---|---|---|
| `NO_PROVENANCE` | REJECT | 条目缺少来源或置信度。 |
| `SENSITIVE_IN_ENTRY` | REJECT | 发现未脱敏的敏感模式。 |
| `UNVETTED_FEEDBACK` | REJECT | 符合 feedback 条件却没有 review 签核。 |
| `NO_TIMESTAMP` | REJECT | 没有 created_at，无法做衰减调度。 |
| `DUPLICATE_ENTRY` | REJECT | 内容哈希与既有条目相同。 |

处理：
- **REJECT**：该记忆条目不能保存。发送方必须修正。

## 关键机制

- **敏感模式**：必须拒绝形如手机号的模式（`\d{3}-\d{3,4}-\d{3,4}`）以及 `password=`、`api_key=`、`Bearer <token>` 这类字面量。
- **反馈审核（Feedback Vetting）**：标记 `feedback_eligible: true` 的条目必须携带 `review_signoff`（审核者 ID 或时间戳）。未经审核的反馈会把猜测自动传播回流水线——本机制拦的就是这个。
- **衰减**：条目携带 `created_at`，衰减过程据此给旧条目降权。没有时间戳的条目会以全权重永久存留，必须拒绝。
- **重复检测**：内容哈希（`{pattern, summary, content}`，SHA-1 前 12 位十六进制）必须对存储库唯一。

`confidence` 为 `0.0` 是一个*存在的*低置信分数，不是缺失出处。只有缺失、非数值或超出范围的分数才是 `NO_PROVENANCE`。

## 运行确定性检查器

```bash
python scripts/memory_check.py --entry path/to/entry.json [--known-hashes stored_hashes.json] [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input. `--known-hashes` 接收一个由已存内容哈希组成的 JSON 数组；缺了它，重复检测无法运行。

## 本 skill 禁止事项

- **绝不存储密码、API key 或 PII。** 一律扫描并拒绝。
- **绝不存储没有出处（source）的条目。** 我们必须知道知识从哪里来。
- **绝不自动批准未经审核的反馈。**
- **绝不把 PASS 当作发布。** 通过的条目仍可被 review；本门禁放行的是存储，不是把它授权为真理。

## 使用示例

**示例 1 —— 正确触发**
```
存储知识："预发环境需要 VPN 连接。"
Source: "用户手册"
Confidence: 0.95
Created at: 2026-08-07T12:00:00Z
```
→ PASS。已存入记忆。

**示例 2 —— 错误触发（反模式）**
```
存储知识："测试管理员的密码是 password123"
```
→ REJECT。（SENSITIVE_IN_ENTRY）不能存储敏感凭证。
