import { test } from "@playwright/test";

/**
 * 该文件已被 visual-align-screenshots.spec.ts 取代（原型对齐后的新界面截图）。
 * 保留占位，避免 CI 收集旧选择器导致失败。
 */
test.skip(process.env.CI === "true", "已由 visual-align-screenshots 取代");

test("证据截图已迁移至 visual-align-screenshots", async () => {
  // no-op：证据采集由 visual-align-screenshots.spec.ts 承担
});
