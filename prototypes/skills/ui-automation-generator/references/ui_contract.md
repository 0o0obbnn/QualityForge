# UI 自动化脚本契约

`scripts/ui_check.py` 是可执行编码；本文件描述其意图。

## Finding Codes

| Code | Severity | 含义 |
|---|---|---|
| `INLINE_XPATH_LITERAL` | REJECT | 脚本中出现 XPath 字符串字面量而非 locator ID。 |
| `MISSING_WAIT_STRATEGY` | REJECT | 交互缺少显式 wait。 |
| `POM_VIOLATION` | REJECT | 测试逻辑混入 page object，或反向混杂。 |
| `LOCATOR_NOT_IN_LIBRARY` | REJECT | 引用的 locator_id 不在库中。 |

## Wait 策略分类

- `visible` — 等待元素出现。
- `clickable` — 等待元素可交互。
- `network_idle` — 等待请求平息。
- `custom` — 显式条件。

不带任何 wait 的交互就是竞态：测试可能在元素存在之前就去点击，产生 flaky 失败。

## POM 分离

Page Object Model：page object 封装 UI 结构与交互；测试函数承载断言与流程。两者混杂（page object 里写测试逻辑，或测试函数里直接操作 DOM）会破坏可维护性与复用。
