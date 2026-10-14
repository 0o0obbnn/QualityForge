import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  IconAgent,
  IconAutomation,
  IconAvatar,
  IconBell,
  IconBoard,
  IconChevronDown,
  IconExecution,
  IconHamburger,
  IconHome,
  IconKnowledge,
  IconMark,
  IconPlanning,
  IconPlatform,
  IconQuality,
  IconSearch,
} from "./Icons";
import { Modal } from "./Modal";
import { ProviderStatusChip } from "./ProviderStatusChip";
import { useToast } from "./Toast";
import { fetchProviderStatus, fetchReviewCount } from "../services/dataService";
import type { Profile, ProviderStatus, ReleaseOption, WorkspaceOption } from "../types";

/**
 * 应用壳（对齐原型侧栏 + 顶栏 + 移动端导航抽屉 qf-shell.js H4 语义）。
 * 侧栏：品牌 + 导航分组（工作/测试/平台）+ 8 模块 + 待审核计数徽标。
 * 顶栏：项目/Release 上下文切换、全局搜索、通知、账号。
 */

interface AppShellProps {
  profile: Profile;
  reviewCount: number;
  onLogout: () => void;
  /** WP-01A 上下文：服务端投影列表与切换回调（列表为空=加载中/无权限面）。 */
  workspaces: WorkspaceOption[];
  releases: ReleaseOption[];
  onSwitchWorkspace: (workspace: WorkspaceOption) => Promise<boolean>;
  onSwitchRelease: (release: ReleaseOption) => void;
  /** WP-01 常用项目置顶/取消（对任意成员工作区可操作）。 */
  onTogglePin: (workspace: WorkspaceOption, pinned: boolean) => Promise<boolean>;
}

const NAV_GROUPS: Array<{
  group: string;
  items: Array<{ key: string; label: string; icon: (props: { size?: number }) => React.ReactNode; to: string }>;
}> = [
  {
    group: "工作",
    items: [
      { key: "artifacts", label: "测试产出物", icon: IconPlanning, to: "/artifacts" },
      { key: "conversations", label: "协作对话", icon: IconAgent, to: "/conversations" },
      { key: "board", label: "任务与审核", icon: IconBoard, to: "/board" },
    ],
  },
  {
    group: "测试",
    items: [
      { key: "knowledge", label: "知识与契约", icon: IconKnowledge, to: "/knowledge/sources" },
      { key: "planning", label: "测试规划与设计", icon: IconPlanning, to: "/planning/strategies" },
      { key: "automation", label: "自动化工作台", icon: IconAutomation, to: "/automation/scripts" },
      { key: "execution", label: "测试执行", icon: IconExecution, to: "/execution-monitor" },
      { key: "quality", label: "质量中心", icon: IconQuality, to: "/quality/analyses" },
    ],
  },
  {
    group: "平台",
    items: [
      { key: "agent", label: "AI Agent 中心", icon: IconAgent, to: "/agent" },
      { key: "platform", label: "平台管理", icon: IconPlatform, to: "/platform" },
    ],
  },
];

export function AppShell({
  profile,
  reviewCount,
  onLogout,
  workspaces,
  releases,
  onSwitchWorkspace,
  onSwitchRelease,
  onTogglePin,
}: AppShellProps) {
  const toast = useToast();
  const location = useLocation();
  const isPlatform = location.pathname.startsWith("/platform");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [wsSwitchOpen, setWsSwitchOpen] = useState(false);
  const [releaseSwitchOpen, setReleaseSwitchOpen] = useState(false);
  const [badge, setBadge] = useState(reviewCount);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>({
    status: "UNKNOWN",
    providerId: "—",
  });

  useEffect(() => {
    let active = true;
    void fetchProviderStatus()
      .then((status) => {
        if (active) setProviderStatus(status);
      })
      .catch(() => {
        /* 保持未知态 */
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    void fetchReviewCount(profile)
      .then((count) => {
        if (active) setBadge(count);
      })
      .catch(() => {
        /* 保持初始值 */
      });
    return () => {
      active = false;
    };
  }, [profile]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const currentWorkspaceName = workspaces.find((ws) => ws.id === profile.workspaceId)?.name ?? "当前项目";

  const sidebar = (
    <>
      <div className="brand">
        <span className="mark">
          <IconMark />
        </span>
        QualityForge
      </div>
      {NAV_GROUPS.map((navGroup) => (
        <div key={navGroup.group}>
          <div className="nav-group">{navGroup.group}</div>
          {navGroup.items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.key}
                to={item.to}
                className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                onClick={() => setDrawerOpen(false)}
              >
                <Icon />
                {item.label}
                {item.key === "board" && badge > 0 && (
                  <span className="nav-badge" title={`${badge} 个待审核任务包`}>
                    {badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>
      ))}
      <div className="foot">
        V1 原型 ·{" "}
        <button
          type="button"
          onClick={onLogout}
          style={{ fontSize: 12, border: "none", background: "transparent", color: "var(--qf-accent-600)", cursor: "pointer", padding: 0 }}
        >
          退出登录
        </button>
        <NavLink to="/help" className="foot-link" onClick={() => setDrawerOpen(false)}>
          帮助与术语
        </NavLink>
      </div>
    </>
  );

  return (
    <div className="app">
      <aside className="sidebar">{sidebar}</aside>

      <header className="topbar">
        <button className="nav-hamburger" aria-label="打开导航" onClick={() => setDrawerOpen(true)}>
          <IconHamburger />
        </button>
        <div className="ctx">
          <button className="ctx-btn" onClick={() => setWsSwitchOpen(true)}>
            <IconHome />
            <span className="ctx-long">{isPlatform ? "平台级" : currentWorkspaceName}</span>
            <IconChevronDown />
          </button>
          {!isPlatform && (
            <>
              <span className="ctx-sep">/</span>
              <button className="ctx-btn" onClick={() => setReleaseSwitchOpen(true)}>
                Release {profile.releaseName ?? "未选择"}
                <IconChevronDown />
              </button>
            </>
          )}
        </div>
        <ProviderStatusChip status={providerStatus} />
        <div className="spacer" />
        <div className="search">
          <IconSearch />
          <input type="search" aria-label="搜索产出物、用例、缺陷" placeholder="搜索产出物、用例、缺陷…" />
        </div>
        <button className="icon-btn" aria-label="通知" onClick={() => setNoticeOpen(true)}>
          <IconBell />
        </button>
        <div className="avatar" style={{ cursor: "pointer" }} title="账号" onClick={() => setAccountOpen(true)}>
          <IconAvatar />
        </div>
      </header>

      <main>
        <Outlet context={{ profile }} />
      </main>

      {drawerOpen && <div className="nav-drawer-mask open" onClick={() => setDrawerOpen(false)} />}
      <div className={`nav-drawer${drawerOpen ? " open" : ""}`} aria-label="主导航">
        {sidebar}
      </div>

      <Modal id="m-notice" open={noticeOpen} title="平台公告" triggerNote="触发入口: 顶栏通知铃铛 · 公告/通知类弹窗" onClose={() => setNoticeOpen(false)} footer={<button className="btn btn-primary" onClick={() => setNoticeOpen(false)}>知道了</button>}>
        <div className="mini-card" style={{ border: "none", padding: 0 }}>
          <div className="row"><span className="k">2026-08-11</span><span className="v">Release R-2026.08 已进入测试期,请及时处理待审核项</span></div>
          <div className="row"><span className="k">2026-08-09</span><span className="v">AI Agent 中心新增 Trace 回放视图</span></div>
          <div className="row"><span className="k">2026-08-07</span><span className="v">执行 Runner 升级至 v2.3,支持失败重试预算</span></div>
        </div>
      </Modal>

      <Modal id="m-account" open={accountOpen} title="账号" width="narrow" triggerNote="触发入口: 顶栏头像" onClose={() => setAccountOpen(false)} footer={<button className="btn btn-primary" onClick={() => setAccountOpen(false)}>关闭</button>}>
        <div className="flex" style={{ marginBottom: 14 }}>
          <div className="avatar" style={{ width: 40, height: 40 }}>
            <IconAvatar size={20} />
          </div>
          <div>
            <b>{profile.email.split("@")[0]}</b>
            <div className="small muted">TestLead</div>
          </div>
        </div>
        <a href="#" onClick={(event) => { event.preventDefault(); toast("个人设置页属平台管理范围(演示)", "info"); }}>
          个人设置
        </a>
        <div className="mt-4">
          <button type="button" onClick={onLogout} style={{ border: "none", background: "transparent", color: "var(--qf-accent-600)", cursor: "pointer", padding: 0, fontSize: 13.5 }}>
            退出登录
          </button>
        </div>
      </Modal>

      <Modal id="m-ws-switch" open={wsSwitchOpen} title="切换项目" width="narrow" triggerNote="触发入口: 顶栏项目切换按钮" onClose={() => setWsSwitchOpen(false)} footer={<button className="btn btn-primary" onClick={() => setWsSwitchOpen(false)}>取消</button>}>
        <div className="mini-card" style={{ border: "none", padding: 0 }}>
          {workspaces.length === 0 && <div className="row"><span className="k">项目列表加载中…</span></div>}
          {workspaces.map((workspace) => (
            <div
              key={workspace.id}
              className="row"
              style={{ cursor: "pointer", alignItems: "center" }}
              onClick={() => {
                void onSwitchWorkspace(workspace).then((ok) => {
                  if (ok) {
                    setWsSwitchOpen(false);
                    toast(`已切换到 ${workspace.name}`, "ok");
                  } else {
                    toast("切换失败，请重试", "err");
                  }
                });
              }}
            >
              <span className="k">
                {workspace.pinned ? "📌 " : ""}
                {workspace.name}
              </span>
              <span className="v muted" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onTogglePin(workspace, !workspace.pinned).then((ok) => {
                      toast(ok ? (workspace.pinned ? "已取消置顶" : "已置顶常用项目") : "操作失败，请重试", ok ? "info" : "err");
                    });
                  }}
                  style={{ fontSize: 12, padding: "1px 8px", border: "1px solid var(--qf-line-2, #d8d2c8)", borderRadius: 999, background: "transparent", cursor: "pointer", color: "inherit" }}
                >
                  {workspace.pinned ? "取消置顶" : "置顶"}
                </button>
                {workspace.id === profile.workspaceId ? "当前" : "切换"}
              </span>
            </div>
          ))}
        </div>
        <button className="btn btn-ghost" style={{ width: "100%", marginTop: 12 }} onClick={() => toast("创建新项目见平台管理(演示)", "info")}>
          + 创建新项目
        </button>
      </Modal>

      <Modal id="m-release-switch" open={releaseSwitchOpen} title="切换 Release" width="narrow" triggerNote="触发入口: 顶栏 Release 切换按钮" onClose={() => setReleaseSwitchOpen(false)} footer={<button className="btn btn-primary" onClick={() => setReleaseSwitchOpen(false)}>取消</button>}>
        <div className="mini-card" style={{ border: "none", padding: 0 }}>
          {releases.length === 0 && <div className="row"><span className="k">该工作区暂无 ACTIVE Release</span></div>}
          {releases.map((release) => (
            <button
              key={release.id}
              type="button"
              className="row"
              style={{ width: "100%", border: "none", background: "transparent", cursor: "pointer", textAlign: "left", font: "inherit" }}
              onClick={() => {
                onSwitchRelease(release);
                setReleaseSwitchOpen(false);
                toast(`已切换到 ${release.name}`, "ok");
              }}
            >
              <span className="k">{release.name}</span>
              <span className="v muted">{release.id === profile.releaseId ? "当前" : "切换"}</span>
            </button>
          ))}
        </div>
      </Modal>
    </div>
  );
}
