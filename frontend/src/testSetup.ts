import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

afterEach(cleanup);

/**
 * vitest 组件测试 mock：@fluentui/react-components / react-icons 兼容层。
 *
 * tabster 为 CJS 无命名导出（vitest 内 Node 解析绕过 Vite 互操作），
 * 组件测试无需测试第三方组件，mock 为原始 HTML 元素即可验证渲染逻辑。
 */
vi.mock("@fluentui/react-components", async () => {
  const React = await import("react");
  const h = React.createElement;
  const passthrough = (tag: string, props: Record<string, unknown>) => {
    const { children, ...rest } = props;
    return h(tag, rest, children as React.ReactNode);
  };
  return {
    Badge: (props: Record<string, unknown>) => {
      const { children, ...rest } = props;
      return h("span", rest, children as React.ReactNode);
    },
    Button: (props: Record<string, unknown>) => {
      const { children, disabled, onClick, ...rest } = props;
      return h(
        "button",
        { ...rest, type: "button", disabled: disabled === true, onClick: onClick ?? (() => {}) },
        children as React.ReactNode,
      );
    },
    Field: (props: Record<string, unknown>) => passthrough("div", props),
    Input: (props: Record<string, unknown>) => passthrough("input", props),
    Textarea: (props: Record<string, unknown>) => {
      const { value, onChange, ...rest } = props;
      return h("textarea", {
        ...rest,
        value: String(value ?? ""),
        onInput: (event: React.SyntheticEvent<HTMLTextAreaElement>) => {
          if (typeof onChange === "function") {
            onChange(event, { value: (event.target as HTMLTextAreaElement).value });
          }
        },
      });
    },
    MessageBar: (props: Record<string, unknown>) => passthrough("div", props),
    MessageBarBody: (props: Record<string, unknown>) => passthrough("div", props),
    Spinner: (props: Record<string, unknown>) => passthrough("div", props),
  };
});

vi.mock("@fluentui/react-icons", async () => {
  const React = await import("react");
  const h = React.createElement;
  const icon = (name: string) => (props: Record<string, unknown>) =>
    h("span", { ...props, "data-testid": `icon-${name}` });
  return {
    ArrowClockwiseRegular: icon("arrow-clockwise"),
    CheckmarkCircleRegular: icon("checkmark"),
    DismissCircleRegular: icon("dismiss"),
    DocumentSearchRegular: icon("document-search"),
    SignOutRegular: icon("sign-out"),
  };
});
