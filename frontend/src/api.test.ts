import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "./api";
import type { ApiEnvelope } from "./types";

/**
 * api() 是前端唯一的网络层逻辑：CSRF 双提交、Content-Type、错误信封解包、credentials。
 * 这些是审核工作台安全性的前端关键路径，必须有断言守护，而非仅靠 tsc 类型检查。
 */
describe("api fetch wrapper", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  /** 模拟一个 fetch Response：json() 返回信封体。 */
  function mockResponse(body: unknown, ok = true, status = 200): Response {
    return { ok, status, json: async () => body } as Response;
  }

  /** 设置 document.cookie（jsdom 下用 getter 覆盖最稳）。 */
  function setCookie(value: string): void {
    Object.defineProperty(document, "cookie", {
      configurable: true,
      get: () => value,
    });
  }

  it("GET 请求不附加 CSRF 头（安全方法豁免）", async () => {
    setCookie("qf_csrf=should-not-be-used");
    fetchMock.mockResolvedValue(
      mockResponse({ code: "OK", message: "", traceId: "t", data: null }),
    );
    await api("/api/v1/ping");
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers((init as RequestInit).headers).has("X-CSRF-Token")).toBe(
      false,
    );
  });

  it("非安全方法从 qf_csrf cookie 读取并附加 X-CSRF-Token 头", async () => {
    setCookie("qf_csrf=my-csrf-token; unrelated=1");
    fetchMock.mockResolvedValue(
      mockResponse({ code: "OK", message: "", traceId: "t", data: null }),
    );
    await api("/api/v1/x", { method: "POST", body: "{}" });
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers((init as RequestInit).headers).get("X-CSRF-Token")).toBe(
      "my-csrf-token",
    );
  });

  it("有 body 时自动设置 Content-Type: application/json", async () => {
    fetchMock.mockResolvedValue(
      mockResponse({ code: "OK", message: "", traceId: "t", data: null }),
    );
    await api("/api/v1/x", { method: "POST", body: JSON.stringify({ a: 1 }) });
    const [, init] = fetchMock.mock.calls[0];
    expect(new Headers((init as RequestInit).headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("credentials 始终为 include（携带 HttpOnly 鉴权 cookie）", async () => {
    fetchMock.mockResolvedValue(
      mockResponse({ code: "OK", message: "", traceId: "t", data: null }),
    );
    await api("/api/v1/x");
    const [, init] = fetchMock.mock.calls[0];
    expect((init as RequestInit).credentials).toBe("include");
  });

  it("非 ok 响应抛出 ApiError（Error 子类）且携带 code 与 traceId", async () => {
    fetchMock.mockResolvedValue(
      mockResponse(
        {
          code: "VALIDATION_FAILED",
          message: "请求参数校验失败",
          traceId: "trace-123",
          data: null,
        },
        false,
        422,
      ),
    );
    await expect(api("/api/v1/x")).rejects.toMatchObject({
      name: "ApiError",
      status: 422,
      code: "VALIDATION_FAILED",
      traceId: "trace-123",
      message: "请求参数校验失败",
    });
    const caught = await api("/api/v1/x").catch((error: unknown) => error);
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toBeInstanceOf(Error);
  });

  it("ok 响应返回完整信封", async () => {
    const envelope: ApiEnvelope<{ id: string }> = {
      code: "OK",
      message: "",
      traceId: "t",
      data: { id: "abc" },
    };
    fetchMock.mockResolvedValue(mockResponse(envelope));
    await expect(api<{ id: string }>("/api/v1/x")).resolves.toEqual(envelope);
  });
});
