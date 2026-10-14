import { useNavigate } from "react-router-dom";

/**
 * 帮助与术语（H10 最小方案，M2-F0 裁决）：
 * 顶栏/侧栏帮助入口 → 术语表简版（摘录 03-术语表核心条目）。
 * V1 允许占位页（M2 验收 2「占位页允许」），首屏引导与 tooltip 层归 V2。
 */

const GLOSSARY = [
  { term: "WorkItem", def: "工作项：可审核、可执行的最小工作单元，状态机 BACKLOG→READY→IN_PROGRESS→PENDING_REVIEW→APPROVED/DONE" },
  { term: "ReviewTask", def: "审核任务：绑定产出物版本与 contentDigest，决定仅限人工，只追加不可撤销" },
  { term: "contentDigest", def: "内容摘要：产出物版本内容的 SHA-256，批准时绑定，防止陈旧版本被批准" },
  { term: "ExecutionResult", def: "执行结果：不可变事实记录（stdout/stderr/exit-code + digest），不被分析覆盖" },
  { term: "Fact/Inference/Decision", def: "三层分离：执行结果是事实，AI 输出是草稿推断，ReviewTask 批准是决定" },
  { term: "Lead/Cycle Time", def: "Lead=BACKLOG→DONE，Cycle=首次 IN_PROGRESS→DONE；基于事件流计算，禁止人工汇总字段" },
  { term: "SINGLE_REVIEW / FOUR_EYES", def: "审核策略：单人审核 / 双人独立审核（职责分离）" },
  { term: "Fail-Closed", def: "失败关闭：权限/校验/门禁任一层拒绝即拒绝，不默认放行" },
];

export function HelpPage() {
  const navigate = useNavigate();
  return (
    <>
      <div className="page-head">
        <div>
          <h1>帮助与术语</h1>
          <div className="sub">QualityForge 核心术语简版 · 完整术语表见 03-术语表Glossary</div>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => navigate(-1)}>
          ← 返回
        </button>
      </div>

      <div className="panel">
        <div className="phead">
          <h2>术语表</h2>
          <span className="hint">{GLOSSARY.length} 个核心条目</span>
        </div>
        <div className="table-scroll">
          <table data-readonly>
            <thead>
              <tr>
                <th style={{ width: 220 }}>术语</th>
                <th>定义</th>
              </tr>
            </thead>
            <tbody>
              {GLOSSARY.map((item) => (
                <tr key={item.term}>
                  <td className="mono small">{item.term}</td>
                  <td className="small">{item.def}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small muted" style={{ padding: "0 18px 16px" }}>
          首屏引导与术语 tooltip 层归 V2；本页为 H10 裁决的最小方案（帮助入口可达、术语可检索）。
        </p>
      </div>
    </>
  );
}
