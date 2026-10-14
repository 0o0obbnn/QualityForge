import eslint from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import babelParser from "@babel/eslint-parser";

/**
 * ESLint flat config（TS7 过渡期方案）。
 *
 * 分层策略：
 * - 类型正确性（含未使用变量/导入）→ 由 `tsc --noEmit` 承担（tsconfig 已开 noUnusedLocals/Parameters）
 * - JS 正确性与 React hooks 规则 → 由本 lint 承担
 * - typescript-eslint 尚不支持 TS7，TS 语法解析用 @babel/eslint-parser（语法层，与 TS 版本无关）
 *
 * 因此 no-undef / no-unused-vars 在 TS 文件关闭：Babel 解析器对 TS 类型节点的
 * 作用域表示与类型检查器不一致，会产生大量假阳性，这两条由 tsc 原生覆盖。
 */
export default [
  {
    ignores: ["dist/**", "node_modules/**", "test-results/**", "visual-align/**", "playwright-report/**"],
  },
  eslint.configs.recommended,
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: babelParser,
      parserOptions: {
        requireConfigFile: false,
        sourceType: "module",
        ecmaFeatures: { jsx: true },
        babelOptions: {
          presets: ["@babel/preset-typescript"],
        },
      },
    },
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // TS 文件由 tsc 负责：作用域/类型引用不重复检查（Babel 解析器对 TS 节点有假阳性）
      "no-undef": "off",
      "no-unused-vars": "off",
    },
  },
];
