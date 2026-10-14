/**
 * 契约状态展示映射：32/33 状态枚举 → 审核工作台徽章文案与颜色。
 * 抽为纯函数以便用契约测试断言守护（VERDICT 批次结束条件：FAILED→danger）。
 * AgentSession 状态枚举见 03 术语表 §13.13（权威源 33 t_agent_session CHECK）。
 */
export function statusLabel(status: string): string {
  return {
    OPEN: "待审核",
    IN_PROGRESS: "审核中",
    APPROVED: "已批准",
    CHANGES_REQUESTED: "需修改",
    REJECTED: "已拒绝",
    EXPIRED: "已过期",
    SUCCEEDED: "已完成",
    BLOCKED: "已阻塞",
    FAILED: "失败",
    PENDING: "待启动",
    RUNNING: "执行中",
    CANCELLED: "已取消",
  }[status] ?? status
}

export type BadgeColor = "success" | "danger" | "informative"
export type BadgeAppearance = "filled" | "tint"

export function statusBadgeColor(status: string): BadgeColor {
  if (status === "APPROVED") return "success"
  if (status === "REJECTED" || status === "FAILED") return "danger"
  if (status === "EXPIRED") return "danger"
  return "informative"
}

export function statusBadgeAppearance(status: string): BadgeAppearance {
  return status === "APPROVED" ? "filled" : "tint"
}
