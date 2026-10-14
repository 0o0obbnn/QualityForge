---
name: requirement-compiler
description: 对一次 Testing IR 融合过程做审计。在来源已融合为 IR 草稿之后、该草稿进入 ir-validator 之前使用。检查 packet 非空、来源贡献、冲突多版本保留与 source_trace 完整性。不可用的来源降级为 PASS_WITH_REVIEW，绝不给干净的 PASS。不得使用本 skill 解析来源文档或生成 IR 草稿——它只审计已经发生的融合。
---

# Requirement Compiler

本原型审计一次已完成的融合。它不解析来源文档，也不自行生成草稿。
它检查产出的草稿非空、有来源意识、可追溯，并对不可用的证据与冲突
保持诚实。

## 来源可用性

每个来源以 `source_id` 和一个可用性值声明：

| 可用性             | 处理方式                             |
| ------------------ | ------------------------------------ |
| `AVAILABLE`        | 必须贡献至少一个可追溯的 IR 元素。   |
| `NOT_PROVIDED`     | REVIEW；证据不完整。                 |
| `UNREADABLE`       | REVIEW；解析失败或内容无法消费。     |
| `EXPECTED_MISSING` | REVIEW；当前阶段本应提供该来源。     |
| `NOT_APPLICABLE`   | 无贡献义务。                         |

旧式来源字符串仍然被接受，含义等同 `AVAILABLE`。

## 四项融合义务检查

| 检查项                    | Code                         | 拦截什么                                                |
| ------------------------- | ---------------------------- | ------------------------------------------------------- |
| 冲突保留多个版本          | `CONFLICT_SINGLE_VERSION`    | 冲突的来源版本少于 2 个。                                |
| packet 非空               | `EMPTY_SOURCE_MANIFEST` / `EMPTY_IR_DRAFT` | 没有证据或没有编译出的需求。                 |
| 所有可用来源都有贡献      | `SOURCE_SILENTLY_DROPPED`    | 某个可用的输入来源什么也没贡献。                         |
| 缺失证据可见              | `SOURCE_UNAVAILABLE`         | 期望/提供的证据无法消费；REVIEW。                        |
| source_trace 指向真实输入 | `FABRICATED_SOURCE_TRACE`    | source_trace 引用了声明集合之外的输入。                 |
| 无默认置信度              | `DEFAULT_CONFIDENCE`         | 元素带有「圆得可疑」的默认值，如 0.5/0.9。              |

冲突多版本规则是承重墙。只有单一版本的冲突不是冲突——它是假装成
分析的静默裁决。真实冲突保留所有分歧版本，由人来裁决。

## 集成

- **输入**：编译出的 IR 草稿 + 已声明的输入来源列表。
- **输出**：PASS、PASS_WITH_REVIEW 或 REJECT。缺失的证据绝不会
  变成干净的 PASS，也不会被捏造成需求。

来源贡献规则与默认置信度启发式见 `references/compiler_rules.md`。



## 运行确定性检查器

```bash
python scripts/compile_check.py --packet path/to/compilation.json [--out report.json]
```

Exit codes: `0` PASS | `1` PASS_WITH_REVIEW | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **反模式**：绝不静默丢弃有歧义的需求文本。绝不在编译过程中篡改核心业务逻辑。

## 使用示例

**正确**：触发本 skill，依据来源清单审计一份已存在的 IR 草稿。
**错误**：用本 skill 阅读原始 PRD PDF 并撰写初始 Testing IR。
