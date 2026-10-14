---
name: ui-automation-generator
description: 已草拟 UI 自动化脚本（Playwright/Selenium、Page Object Model）的契约门禁。在 UI 测试用例就绪且 locator 库已存在之后、脚本提交或执行之前，对草拟脚本使用。需要后端或 API 测试时不得使用（改用 api-test-generator）；locator 库缺失时不得使用。不得用它编写 locator（改用 locator-discovery）。
---

# UI Automation Generator

用 Page Object Model 模式把 UI 测试用例转化为 Playwright/Selenium 脚本。
生成是 LLM 的工作；契约检查是确定性的。

## 四项契约检查

regex、分类体系与 POM 规则的完整细节见 `references/ui_contract.md`。
1. `INLINE_XPATH_LITERAL`：脚本中不得出现内联 XPath 字符串。
2. `MISSING_WAIT_STRATEGY`：页面交互必须有显式等待。
3. `POM_VIOLATION`：测试逻辑不得混入 page object，反之亦然。
4. `LOCATOR_NOT_IN_LIBRARY`：脚本必须引用 locator 库中有效的 locator_id。

## 集成

- **输入**：UI 测试用例 + locator 库。
- **输出**：一份通过校验的 POM 结构脚本，或 REJECT。
- **若被流水线消费**：PASS 的脚本方可执行。



## 运行确定性检查器

```bash
python scripts/ui_check.py --script path/to/ui_script.json [--out report.json]
```

Exit codes: `0` PASS | `2` REJECT | `3` invalid input.

## 本 skill 禁止事项

- **反模式**：绝不用基于序号的 XPath 或脆弱的 CSS 选择器。绝不添加任意硬编码 sleep（应使用显式等待）。

## 使用示例

**正确用法：**
- 使用预定义 locator ID 清单生成 UI 自动化。
- 确保每次交互（如 click、type）都显式等待元素就绪。

**错误用法：**
- `page.click('//div[@id="submit"]')`（触发 `INLINE_XPATH_LITERAL`——不得使用内联 locator）。
- 在 Page Object 类里混入断言（触发 `POM_VIOLATION`——逻辑必须分离）。
- 不加显式等待直接调用 `.click()`（触发 `MISSING_WAIT_STRATEGY`）。
