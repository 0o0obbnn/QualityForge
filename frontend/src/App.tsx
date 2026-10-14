import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { api } from "./api";
import {
  fetchReleases,
  fetchWorkspaces,
  pickCurrentRelease,
  setWorkspacePin,
  switchWorkspaceProfile,
} from "./services/dataService";
import { AppShell } from "./app/AppShell";
import { ToastProvider } from "./app/Toast";
import { AuthPage } from "./pages/AuthPage";
import type { LocalAuthStatus, Profile, ReleaseOption, WorkspaceOption } from "./types";
/**
 * 应用入口（对齐原型 .app 框架 + 路由）：
 * - 路由表：/artifacts 测试产出物、/board 工作看板、/reviews 待我审核及各业务模块
 * - 认证：/auth 路由守卫（mock 模式直接进入工作区）
 * - 视图按路由分包（React.lazy），首屏只加载壳层 + 当前页
 * - 视觉：qf-tokens + qf-components 体系（styles/ 下），无 Fluent UI
 */

const BoardPage = lazy(() => import("./views/BoardPage").then((m) => ({ default: m.BoardPage })));
const ArtifactHubPage = lazy(() => import("./views/ArtifactHubPage").then((m) => ({ default: m.ArtifactHubPage })));
const ReviewsPage = lazy(() => import("./views/ReviewsPage").then((m) => ({ default: m.ReviewsPage })));
const WorkItemPage = lazy(() => import("./views/WorkItemPage").then((m) => ({ default: m.WorkItemPage })));
const PlaceholderPage = lazy(() => import("./views/PlaceholderPage").then((m) => ({ default: m.PlaceholderPage })));
const HelpPage = lazy(() => import("./views/HelpPage").then((m) => ({ default: m.HelpPage })));
const ExecutionMonitorPage = lazy(() => import("./views/ExecutionMonitorPage").then((m) => ({ default: m.ExecutionMonitorPage })));
const EvidencePage = lazy(() => import("./views/EvidencePage").then((m) => ({ default: m.EvidencePage })));
const AnalysesPage = lazy(() => import("./views/quality/AnalysesPage").then((m) => ({ default: m.AnalysesPage })));
const DefectsPage = lazy(() => import("./views/quality/DefectsPage").then((m) => ({ default: m.DefectsPage })));
const ReportsPage = lazy(() => import("./views/quality/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const SourcesPage = lazy(() => import("./views/knowledge/SourcesPage").then((m) => ({ default: m.SourcesPage })));
const ContractsPage = lazy(() => import("./views/knowledge/ContractsPage").then((m) => ({ default: m.ContractsPage })));
const KnowledgePage = lazy(() => import("./views/knowledge/KnowledgePage").then((m) => ({ default: m.KnowledgePage })));
const StrategiesPage = lazy(() => import("./views/planning/StrategiesPage").then((m) => ({ default: m.StrategiesPage })));
const PlansPage = lazy(() => import("./views/planning/PlansPage").then((m) => ({ default: m.PlansPage })));
const CasesPage = lazy(() => import("./views/planning/CasesPage").then((m) => ({ default: m.CasesPage })));
const ScriptsPage = lazy(() => import("./views/automation/ScriptsPage").then((m) => ({ default: m.ScriptsPage })));
const CodeReviewPage = lazy(() => import("./views/automation/CodeReviewPage").then((m) => ({ default: m.CodeReviewPage })));
const AssetsPage = lazy(() => import("./views/automation/AssetsPage").then((m) => ({ default: m.AssetsPage })));
const ExecutionPlansPage = lazy(() => import("./views/ExecutionPlansPage").then((m) => ({ default: m.ExecutionPlansPage })));
const ConversationPage = lazy(() => import("./views/ConversationPage").then((m) => ({ default: m.ConversationPage })));
const AgentCapabilitiesPage = lazy(() => import("./views/agent/AgentCapabilitiesPage").then((m) => ({ default: m.AgentCapabilitiesPage })));
const AgentOperationsPage = lazy(() => import("./views/agent/AgentOperationsPage").then((m) => ({ default: m.AgentOperationsPage })));
const AgentTracePage = lazy(() => import("./views/agent/AgentTracePage").then((m) => ({ default: m.AgentTracePage })));
const WorkspacesPage = lazy(() => import("./views/platform/WorkspacesPage").then((m) => ({ default: m.WorkspacesPage })));
const EnvironmentsPage = lazy(() => import("./views/platform/EnvironmentsPage").then((m) => ({ default: m.EnvironmentsPage })));
const GovernancePage = lazy(() => import("./views/platform/GovernancePage").then((m) => ({ default: m.GovernancePage })));

const MOCK_MODE = import.meta.env.VITE_MOCK === "1";

const MOCK_PROFILE: Profile = {
  userId: "user-mock",
  tenantId: "tenant-mock",
  workspaceId: "ws-mock",
  email: "lead@qualityforge.local",
  actorType: "USER",
  capabilities: [],
  releaseId: "00000000-0000-4000-8000-000000000001",
  releaseName: "R-2026.08",
};

type ViewState = "loading" | "auth-setup" | "auth-login" | "workspace";

export function App() {
  // mock 模式直接以工作区态初始化（避免 effect 内同步 setState，满足 react-hooks/set-state-in-effect）
  const [view, setView] = useState<ViewState>(MOCK_MODE ? "workspace" : "loading");
  const [profile, setProfile] = useState<Profile | undefined>(MOCK_MODE ? MOCK_PROFILE : undefined);
  const [workspaces, setWorkspaces] = useState<WorkspaceOption[]>([]);
  const [releases, setReleases] = useState<ReleaseOption[]>([]);

  /** WP-01A：以服务端 Release 投影解析当前上下文（最近活跃优先），并把列表留给切换器复用。 */
  async function resolveProfileContext(baseProfile: Profile): Promise<Profile> {
    const list = await fetchReleases(baseProfile.workspaceId);
    setReleases(list);
    const current = pickCurrentRelease(list);
    return current ? { ...baseProfile, releaseId: current.id, releaseName: current.name } : baseProfile;
  }

  /** 切换项目：真实模式走服务端专用命令（重签 JWT）后重置 Release；profile 换引用触发全站刷新。 */
  async function switchWorkspace(workspace: WorkspaceOption): Promise<boolean> {
    if (!profile || workspace.id === profile.workspaceId) return true;
    try {
      const nextProfile = MOCK_MODE ? profile : await switchWorkspaceProfile(workspace.id);
      const list = await fetchReleases(workspace.id);
      const current = pickCurrentRelease(list);
      setReleases(list);
      setProfile({
        ...nextProfile,
        workspaceId: workspace.id,
        releaseId: current?.id,
        releaseName: current?.name,
      });
      return true;
    } catch {
      return false;
    }
  }

  /** 常用项目置顶：命令成功后重取列表（服务端置顶组优先；mock 本地重排兜底）。 */
  async function toggleWorkspacePin(workspace: WorkspaceOption, pinned: boolean): Promise<boolean> {
    try {
      await setWorkspacePin(workspace.id, pinned);
      const list = await fetchWorkspaces();
      const next = list
        .map((item) => (item.id === workspace.id ? { ...item, pinned } : item))
        .sort((a, b) => Number(Boolean(b.pinned)) - Number(Boolean(a.pinned)));
      setWorkspaces(next);
      return true;
    } catch {
      return false;
    }
  }

  function switchRelease(release: ReleaseOption): void {
    if (!profile) return;
    setProfile({ ...profile, releaseId: release.id, releaseName: release.name });
  }

  useEffect(() => {
    if (MOCK_MODE) return;
    let active = true;
    api<LocalAuthStatus>("/api/v1/auth/status")
      .then((status) => {
        if (!active) return;
        if (status.data.setupRequired) setView("auth-setup");
        else if (status.data.authenticated && status.data.profile) {
          void resolveProfileContext(status.data.profile)
            .then((nextProfile) => {
              if (active) {
                setProfile(nextProfile);
                setView("workspace");
              }
            })
            .catch(() => {
              if (active) {
                setProfile(status.data.profile!);
                setView("workspace");
              }
            });
        } else setView("auth-login");
      })
      .catch(() => {
        if (active) setView("auth-login");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (view !== "workspace") return;
    let active = true;
    void fetchWorkspaces()
      .then((list) => {
        if (active) setWorkspaces(list);
      })
      .catch(() => {
        /* 列表加载失败不阻塞工作台，切换器保持空态 */
      });
    return () => {
      active = false;
    };
  }, [view]);

  async function logout() {
    try {
      if (!MOCK_MODE) await api<{ loggedOut: boolean }>("/api/v1/auth/logout", { method: "POST" });
    } finally {
      setProfile(undefined);
      setView("auth-login");
    }
  }

  if (view === "loading") {
    return (
      <div className="boot-state">
        <div className="qf-skeleton" style={{ width: 200, height: 24, margin: "auto" }} />
      </div>
    );
  }

  if (view === "auth-setup" || view === "auth-login") {
    return (
      <AuthPage
        mode={view === "auth-setup" ? "setup" : "login"}
        onAuthenticated={(nextProfile) => {
          void resolveProfileContext(nextProfile)
            .then((resolvedProfile) => setProfile(resolvedProfile))
            .catch(() => setProfile(nextProfile))
            .finally(() => setView("workspace"));
        }}
      />
    );
  }

  return (
    <ToastProvider>
      <BrowserRouter>
        <Suspense
          fallback={
            <div style={{ minHeight: "60dvh", display: "grid", placeItems: "center" }}>
              <div className="qf-skeleton" style={{ width: 220, height: 20 }} />
            </div>
          }
        >
        <Routes>
          <Route
            element={
              <AppShell
                profile={profile!}
                reviewCount={7}
                onLogout={() => void logout()}
                workspaces={workspaces}
                releases={releases}
                onSwitchWorkspace={switchWorkspace}
                onSwitchRelease={switchRelease}
                onTogglePin={toggleWorkspacePin}
              />
            }
          >
            <Route index element={<Navigate to="/artifacts" replace />} />
            <Route path="/artifacts" element={<ArtifactHubPage />} />
            <Route path="/board" element={<BoardPage />} />
          <Route path="/conversations" element={<ConversationPage />} />
            <Route path="/reviews" element={<ReviewsPage />} />
            <Route path="/work-items/:workItemId" element={<WorkItemPage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/execution-monitor" element={<ExecutionMonitorPage />} />
            <Route path="/evidence/:executionTaskId" element={<EvidencePage />} />
            <Route path="/quality/analyses" element={<AnalysesPage />} />
            <Route path="/quality/defects" element={<DefectsPage />} />
            <Route path="/quality/reports" element={<ReportsPage />} />
            <Route path="/knowledge/sources" element={<SourcesPage />} />
            <Route path="/knowledge/contracts" element={<ContractsPage />} />
            <Route path="/knowledge/entries" element={<KnowledgePage />} />
            <Route path="/planning/strategies" element={<StrategiesPage />} />
            <Route path="/planning/plans" element={<PlansPage />} />
            <Route path="/planning/cases" element={<CasesPage />} />
            <Route path="/automation/scripts" element={<ScriptsPage />} />
            <Route path="/automation/code-review" element={<CodeReviewPage />} />
            <Route path="/automation/assets" element={<AssetsPage />} />
            <Route path="/execution" element={<ExecutionPlansPage />} />
            <Route path="/agent" element={<AgentCapabilitiesPage />} />
            <Route path="/agent/operations" element={<AgentOperationsPage />} />
            <Route path="/agent/trace/:runId" element={<AgentTracePage />} />
            <Route path="/platform" element={<WorkspacesPage />} />
            <Route path="/platform/environments" element={<EnvironmentsPage />} />
            <Route path="/platform/governance" element={<GovernancePage />} />
            <Route path="/:module" element={<PlaceholderPage />} />
            <Route path="*" element={<Navigate to="/artifacts" replace />} />
          </Route>
        </Routes>
        </Suspense>
      </BrowserRouter>
    </ToastProvider>
  );
}
