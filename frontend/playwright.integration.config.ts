import { defineConfig, devices } from "@playwright/test";

/**
 * 联调配置（真实后端模式，不带 VITE_MOCK）：
 * webServer 启动前端（代理 /api → 127.0.0.1:8000），后端须已在 8000 端口运行。
 */
export default defineConfig({
  testDir: "./e2e-integration",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:4174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "integration",
      use: { ...devices["Desktop Chrome"], channel: process.env.CI ? undefined : "chrome" },
    },
  ],
  webServer: {
    command: "npm run dev:integration",
    url: "http://127.0.0.1:4174",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
