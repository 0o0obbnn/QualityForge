import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Vitest 配置：jsdom 环境提供 document 全局（api.ts 的 cookie 读取测试依赖它）。
// setupFiles 引入 @testing-library/jest-dom 匹配器（M1-F1 组件测试）。
// deps.optimizer 预打包 Fluent UI（tabster 为 CJS，需经 Vite 互操作转换后
// 才能提供命名导出，与 vite dev/build 行为一致）。
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // tabster 出 CJS main 被解析时命名导出缺失，强制 ESM 构建包
      tabster: "tabster/dist/esm/index.js",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testSetup.ts"],
    // e2e 目录归 Playwright，vitest 不得收集（否则 CI 的 npm run test 会红）；
    // 自定义 exclude 会覆盖默认值，须保留 node_modules/dist 排除。
    exclude: ["e2e/**", "e2e-integration/**", "playwright.config.ts", "playwright.integration.config.ts", "**/node_modules/**", "**/dist/**", "**/.git/**"],
    deps: {
      optimizer: {
        web: {
          enabled: true,
          include: ["@fluentui/react-components", "@fluentui/react-icons"],
        },
      },
    },
  },
});
