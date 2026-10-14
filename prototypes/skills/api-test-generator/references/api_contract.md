# API 测试脚本契约

`scripts/api_check.py` 是可执行编码；本文档是意图说明。

## Finding codes

| Code | Severity | 含义 |
|---|---|---|
| `HARDCODED_ENV` | REJECT | 脚本中出现 URL/IP/localhost 字面量。 |
| `HARDCODED_SECRET` | REJECT | 形似密钥的字符串字面量。 |
| `MISSING_FIXTURE_DECL` | REJECT | 脚本有 expected_results 但没有 fixture_deps。 |
| `UNCOVERED_EXPECTED_RESULT` | REJECT | expected_result 没有对应的 assert。 |

## 硬编码配置模式

检查器扫描以下内容：
- URL：`http://`、`https://`、`localhost`、IP 字面量。
- 密钥类名称：`password`、`token`、`api_key`、`secret`、`credential`。
- 密钥字面量前缀：`sk-`、`pk-`、`Bearer `、`ghp_`、`AKIA`。

注释里的 URL 同样会被标记——注释会与代码漂移，一条写着「base URL 是
localhost:8080」的过期注释会掩盖真实的硬编码引用。所有环境相关取值
必须走配置注入（`os.environ` 或配置模块）。

## 断言覆盖

源用例中的每条 `expected_result` 都必须在生成脚本里有对应的
`assert`，通过 `expected_result_id` 关联。一条未被覆盖的
expected_result 意味着测试运行了、却没有校验自己声明的一项预期——
一次静默的 false-pass。
