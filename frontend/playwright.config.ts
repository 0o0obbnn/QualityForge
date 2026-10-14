import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright 配置（M1-F1）：Chromium 单浏览器，mock 模式 dev server。
 * 冒烟覆盖「生成→审核→退回→复核」关键旅程（开发计划 v1.1 §四 M1 前端轨 4）。
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chrome",
      // 本地用系统 Chrome（Chromium 下载网络不稳定）；CI 用 bundled chromium（frontend.yml 已安装）
      use: { ...devices["Desktop Chrome"], channel: process.env.CI ? undefined : "chrome" },
    },
  ],
  webServer: {
    command: "VITE_MOCK=1 npm run dev",
    url: "http://127.0.0.1:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
});
