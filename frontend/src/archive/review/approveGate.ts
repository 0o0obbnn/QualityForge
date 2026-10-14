/**
 * 批准按钮禁用原因判定（M1-F1）。
 *
 * 验收口径（开发计划 v1.1 §四 M1 前端轨 2）：禁用时必须渲染可见原因，
 * 四类：权限不足 / 陈旧版本 / 前置审核未完成 / 摘要不一致。
 * Page-Map §3 补充：职责分离冲突同属禁用原因；前端禁用不是授权边界（服务端仍会拒绝）。
 *
 * 纯函数层：输入为可观测事实，输出为原因枚举，便于 vitest 契约测试守护。
 */

export type ApproveDisabledReason =
  | "PERMISSION"
  | "STALE_VERSION"
  | "BLOCKING_CHECK"
  | "DIGEST_MISMATCH"
  | "DUTY_SEPARATION"
  | "TASK_CLOSED";

export interface ApproveGateInput {
  /** 当前角色是否具备批准权限（capabilities 含 decide 或角色模板允许） */
  canDecide: boolean;
  /** 产出物版本是否为陈旧版本（已有更新版本或 lockVersion 落后） */
  staleVersion: boolean;
  /** 未通过的 blocking check 列表（确定性检查/独立验证等前置审核） */
  blockingChecks: string[];
  /** 批准绑定摘要与当前内容摘要是否一致 */
  digestMatches: boolean;
  /** 职责分离冲突（作者与审核者为同一主体） */
  dutySeparationConflict: boolean;
  /** 任务已结/会话终态（墙 M-121：M1 契约实际值之一） */
  taskClosed: boolean;
}

export function approveDisabledReasons(input: ApproveGateInput): ApproveDisabledReason[] {
  const reasons: ApproveDisabledReason[] = [];
  if (!input.canDecide) reasons.push("PERMISSION");
  if (input.staleVersion) reasons.push("STALE_VERSION");
  if (input.blockingChecks.length > 0) reasons.push("BLOCKING_CHECK");
  if (!input.digestMatches) reasons.push("DIGEST_MISMATCH");
  if (input.dutySeparationConflict) reasons.push("DUTY_SEPARATION");
  if (input.taskClosed) reasons.push("TASK_CLOSED");
  return reasons;
}

const REASON_LABELS: Record<ApproveDisabledReason, string> = {
  PERMISSION: "当前角色无权批准此产出物",
  STALE_VERSION: "此版本已陈旧，请先查看最新版本",
  BLOCKING_CHECK: "前置审核未完成，阻塞检查未全部通过",
  DIGEST_MISMATCH: "批准摘要与当前内容摘要不一致",
  DUTY_SEPARATION: "职责分离冲突：审核者与作者为同一主体",
  TASK_CLOSED: "任务已结，无法再批准",
};

export function approveDisabledReasonLabel(reason: ApproveDisabledReason): string {
  return REASON_LABELS[reason];
}
