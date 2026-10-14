import { describe, expect, it } from "vitest";

import { pickCurrentRelease } from "./dataService";
import type { ReleaseOption } from "../types";

describe("pickCurrentRelease（WP-01A 当前 Release 口径）", () => {
  it("取列表首位——服务端仅返回 ACTIVE 且按 updatedAt DESC，前端不重算排序", () => {
    const active: ReleaseOption = {
      id: "rel-1",
      name: "R-2026.09",
      status: "ACTIVE",
    };
    const older: ReleaseOption = {
      id: "rel-2",
      name: "R-2026.08",
      status: "ACTIVE",
    };
    expect(pickCurrentRelease([active, older])?.id).toBe("rel-1");
  });

  it("空列表返回 undefined——无 ACTIVE Release 时禁用需要 Release 的创建面", () => {
    expect(pickCurrentRelease([])).toBeUndefined();
  });
});
