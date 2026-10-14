# QualityForge 数据库Schema设计

> 本文档仍是团队/生产目标PostgreSQL逻辑/物理Schema权威源，与[04-核心领域模型.md](../01-product/04-核心领域模型.md)和[32-API规范.yaml](32-API规范.yaml)同步。Stage 4本地运行时另使用SQLite schema v2的最小表集；它不是106张目标表的等价移植，也不具备PostgreSQL原生RLS。

本地SQLite只覆盖当前纵向切片的租户、Workspace、用户成员关系、需求/策略/计划/用例稳定根与版本、WorkItem、ReviewTask、AgentSession/Trace、版本索引和幂等记录。所有API访问仍强制校验tenant/workspace；但直接读取数据库文件可绕过应用层，因此只能用于受控单机开发。

## 1. 设计约束

- PostgreSQL 16；UUID主键；复杂受控结构使用JSONB，正文/制品保存受控对象存储引用与digest。
- 租户内业务表必须带`tenant_id`，Workspace内业务表必须同时带`workspace_id`。
- 应用连接角色不是表Owner、不是superuser且无BYPASSRLS；所有租户表启用并强制RLS。
- 正式产出物使用稳定根表和不可变version表；发布版本不得UPDATE正文。
- Audit/Event/Attempt/Decision/Result/Trace类表只追加；应用角色禁止UPDATE/DELETE。
- Secret采用双信封加密；API永不返回`encrypted_value`。
- 历史引用默认`ON DELETE RESTRICT`；仅纯派生索引允许级联重建。
- API使用camelCase，DB使用snake_case，由ORM显式映射。

## 2. 扩展与数据库角色

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE qf_owner NOLOGIN;
CREATE ROLE qf_app_user LOGIN NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- 迁移由qf_owner执行；运行期严禁使用qf_owner或postgres连接。
```

## 3. 平台管理域

```sql
CREATE TABLE t_tenant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUSPENDED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_user (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(320) NOT NULL,
    identity_provider_ref VARCHAR(255),
    password_hash VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','SUSPENDED','DISABLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, username),
    UNIQUE (tenant_id, email)
);

CREATE TABLE t_workspace (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    owner_id UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, name)
);

CREATE TABLE t_release (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_key VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    scope_summary TEXT,
    planned_at TIMESTAMPTZ,
    actual_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'PLANNING'
        CHECK (status IN ('PLANNING','TESTING','RELEASED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, release_key)
);

CREATE TABLE t_workspace_pin (
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES t_user(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE CASCADE,
    pinned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, user_id, workspace_id)
);
CREATE INDEX idx_workspace_pin_user ON t_workspace_pin(user_id, pinned_at DESC);

CREATE TABLE t_conversation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID REFERENCES t_release(id) ON DELETE SET NULL,
    work_item_id UUID REFERENCES t_work_item(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL DEFAULT '未命名会话',
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_conversation_ws ON t_conversation(tenant_id, workspace_id, status, last_activity_at DESC);

CREATE TABLE t_conversation_message (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    conversation_id UUID NOT NULL REFERENCES t_conversation(id) ON DELETE RESTRICT,
    actor_type VARCHAR(10) NOT NULL CHECK (actor_type IN ('USER','AGENT','SERVICE','SYSTEM')),
    actor_id UUID NOT NULL,
    message_type VARCHAR(64) NOT NULL,
    content_ref TEXT NOT NULL,
    content_digest CHAR(64) NOT NULL,
    data_class VARCHAR(20) NOT NULL CHECK (data_class IN ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_conversation_message_conv ON t_conversation_message(conversation_id, created_at, id);
-- 只追加：本表无 UPDATE/DELETE 授权路径；SQLite 运行时以集合表承载（批次五十四 v12）

CREATE TABLE t_clarification_request (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    conversation_id UUID REFERENCES t_conversation(id) ON DELETE SET NULL,
    agent_session_id UUID NOT NULL,
    work_item_id UUID REFERENCES t_work_item(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    reason TEXT NOT NULL,
    impact TEXT NOT NULL,
    required_by TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','ANSWERED','CANCELLED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_clarification_session ON t_clarification_request(agent_session_id, status);

CREATE TABLE t_clarification_response (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    request_id UUID NOT NULL REFERENCES t_clarification_request(id) ON DELETE RESTRICT,
    answer_ref TEXT NOT NULL,
    answer_digest CHAR(64) NOT NULL,
    responded_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    responded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    evidence_class VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED' CHECK (evidence_class = 'CONFIRMED'),
    UNIQUE (request_id)
);
-- 答复只追加且每请求至多一条（唯一约束承载）；SQLite 运行时以集合表承载（批次五十五 v13）

CREATE TABLE t_task_card (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    conversation_id UUID REFERENCES t_conversation(id) ON DELETE SET NULL,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE CASCADE,
    release_id UUID REFERENCES t_release(id) ON DELETE RESTRICT,
    objective TEXT NOT NULL,
    scope TEXT NOT NULL,
    input_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    deliverables JSONB NOT NULL DEFAULT '[]'::jsonb,
    acceptance_criteria TEXT NOT NULL,
    constraints TEXT NOT NULL,
    risk_class VARCHAR(30),
    requested_permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    budget JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'SUBMITTED' CHECK (status IN ('DRAFT','SUBMITTED','ACTIVE','SUPERSEDED')),
    content_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_task_card_work_item ON t_task_card(work_item_id, status);

CREATE TABLE t_agent_plan (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE CASCADE,
    task_card_id UUID NOT NULL REFERENCES t_task_card(id) ON DELETE RESTRICT,
    plan_version INTEGER NOT NULL,
    steps JSONB NOT NULL,
    outputs JSONB NOT NULL DEFAULT '[]'::jsonb,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    budget JSONB NOT NULL DEFAULT '{}'::jsonb,
    risks JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING_APPROVAL' CHECK (status IN ('DRAFT','PENDING_APPROVAL','APPROVED','REJECTED','SUPERSEDED')),
    content_digest CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (work_item_id, plan_version)
);
CREATE INDEX idx_agent_plan_work_item ON t_agent_plan(work_item_id, status);

CREATE TABLE t_agent_plan_decision (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    agent_plan_id UUID NOT NULL REFERENCES t_agent_plan(id) ON DELETE RESTRICT,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('APPROVE','REJECT')),
    reason TEXT NOT NULL,
    decided_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    plan_status VARCHAR(20) NOT NULL
);
-- 裁决只追加；摘要漂移由服务层 expectedContentDigest 对账拒绝（409 STALE_ARTIFACT_VERSION）
-- SQLite 运行时以集合表承载（批次五十六 v14）

CREATE TABLE t_environment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    environment_type VARCHAR(50) NOT NULL,
    endpoint_mappings JSONB NOT NULL DEFAULT '{}'::jsonb,
    capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'ONLINE'
        CHECK (status IN ('ONLINE','OFFLINE','DEGRADED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, name)
);

CREATE TABLE t_workspace_secret (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    secret_key VARCHAR(150) NOT NULL,
    encrypted_value BYTEA NOT NULL,
    key_version VARCHAR(100) NOT NULL,
    scope JSONB NOT NULL,
    target_environment_id UUID REFERENCES t_environment(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','ROTATED','REVOKED','EXPIRED')),
    rotated_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (workspace_id, secret_key, target_environment_id)
);

CREATE TABLE t_runner_node (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    name VARCHAR(150) NOT NULL,
    capabilities JSONB NOT NULL,
    runtime_versions JSONB NOT NULL,
    resource_pool_id UUID,
    status VARCHAR(30) NOT NULL DEFAULT 'OFFLINE'
        CHECK (status IN ('ONLINE_IDLE','ONLINE_BUSY','OFFLINE','HEARTBEAT_LOST','DRAINING')),
    heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_llm_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    provider VARCHAR(80) NOT NULL,
    endpoint_ref VARCHAR(500) NOT NULL,
    model_catalog JSONB NOT NULL,
    routing_policy JSONB NOT NULL,
    credential_secret_id UUID REFERENCES t_workspace_secret(id) ON DELETE RESTRICT,
    quota_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    budget_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','DEGRADED','DISABLED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_integration_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    provider VARCHAR(80) NOT NULL,
    name VARCHAR(150) NOT NULL,
    endpoint_ref VARCHAR(500),
    credential_secret_id UUID REFERENCES t_workspace_secret(id) ON DELETE RESTRICT,
    scope_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
        CHECK (status IN ('ACTIVE','DISABLED','ERROR','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (tenant_id, workspace_id, provider, name)
);

CREATE TABLE t_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    actor_type VARCHAR(20) NOT NULL CHECK (actor_type IN ('HUMAN','AGENT','SERVICE','SYSTEM')),
    actor_id UUID,
    action VARCHAR(150) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    resource_version_id UUID,
    request_digest VARCHAR(64),
    decision VARCHAR(20) CHECK (decision IN ('ALLOW','DENY','SUCCESS','FAILURE')),
    details_ref TEXT,
    trace_id VARCHAR(100) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_audit_tenant_time ON t_audit_log(tenant_id, occurred_at DESC);
CREATE INDEX idx_audit_resource ON t_audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_trace ON t_audit_log(trace_id);
```

## 4. RBAC与审核策略

```sql
CREATE TABLE t_role_definition (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    scope_type VARCHAR(20) NOT NULL CHECK (scope_type IN ('PLATFORM','TENANT','WORKSPACE','RESOURCE')),
    built_in BOOLEAN NOT NULL DEFAULT FALSE,
    version INT NOT NULL DEFAULT 1 CHECK (version > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, name, version)
);

CREATE TABLE t_permission (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    permission_key VARCHAR(150) NOT NULL UNIQUE,
    resource_type VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    risk_limit VARCHAR(20) CHECK (risk_limit IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    condition_schema JSONB,
    human_only BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_role_permission (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role_definition_id UUID NOT NULL REFERENCES t_role_definition(id) ON DELETE RESTRICT,
    permission_id UUID NOT NULL REFERENCES t_permission(id) ON DELETE RESTRICT,
    effect VARCHAR(10) NOT NULL CHECK (effect IN ('ALLOW','DENY')),
    conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (role_definition_id, permission_id)
);

CREATE TABLE t_role_binding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN ('USER','SERVICE')),
    subject_id UUID NOT NULL,
    role_definition_id UUID NOT NULL REFERENCES t_role_definition(id) ON DELETE RESTRICT,
    scope_type VARCHAR(20) NOT NULL CHECK (scope_type IN ('PLATFORM','TENANT','WORKSPACE','RESOURCE')),
    scope_id UUID NOT NULL,
    conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMPTZ,
    granted_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (valid_until IS NULL OR valid_until > valid_from)
);
CREATE INDEX idx_role_binding_subject ON t_role_binding(tenant_id, subject_type, subject_id, status);
CREATE INDEX idx_role_binding_scope ON t_role_binding(tenant_id, scope_type, scope_id, status);

CREATE TABLE t_explicit_deny (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    subject_type VARCHAR(20) NOT NULL CHECK (subject_type IN ('USER','SERVICE','AGENT')),
    subject_id UUID NOT NULL,
    permission_key VARCHAR(150) NOT NULL REFERENCES t_permission(permission_key) ON DELETE RESTRICT,
    scope_type VARCHAR(20) NOT NULL,
    scope_id UUID NOT NULL,
    reason TEXT NOT NULL,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_review_policy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(80) NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    policy_type VARCHAR(30) NOT NULL CHECK (policy_type IN ('SINGLE_REVIEW','FOUR_EYES','CODE_REVIEW','EXTERNAL_WRITE','REPORT_SIGNOFF','KNOWLEDGE_PUBLISH')),
    required_stages JSONB NOT NULL,
    required_capabilities JSONB NOT NULL,
    min_approvers INT NOT NULL CHECK (min_approvers >= 1),
    separation_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    blocking_checks JSONB NOT NULL DEFAULT '[]'::jsonb,
    version INT NOT NULL DEFAULT 1 CHECK (version > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (tenant_id, artifact_type, risk_level, version)
);

CREATE TABLE t_authorization_decision (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    actor_type VARCHAR(20) NOT NULL,
    actor_id UUID NOT NULL,
    action VARCHAR(150) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id UUID,
    resource_version_id UUID,
    resource_digest VARCHAR(64),
    policy_versions JSONB NOT NULL,
    role_binding_snapshot JSONB NOT NULL,
    condition_results JSONB NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('ALLOW','DENY')),
    reason_code VARCHAR(100) NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_delegation_grant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    delegator_id UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    delegatee_id UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    permission_keys JSONB NOT NULL,
    scope_type VARCHAR(20) NOT NULL,
    scope_id UUID NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    reason TEXT NOT NULL,
    allow_redelegation BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (delegator_id <> delegatee_id)
);

CREATE TABLE t_support_access_grant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_user_id UUID NOT NULL,
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    ticket_ref VARCHAR(200) NOT NULL,
    reason TEXT NOT NULL,
    permission_keys JSONB NOT NULL,
    approved_by UUID NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 5. 任务看板域

```sql
CREATE TABLE t_work_item (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID REFERENCES t_release(id) ON DELETE RESTRICT,
    test_plan_id UUID,
    parent_work_item_id UUID REFERENCES t_work_item(id) ON DELETE RESTRICT,
    work_item_type VARCHAR(30) NOT NULL CHECK (work_item_type IN ('STRATEGY','PLAN','TEST_DESIGN','AUTOMATION_WEB','AUTOMATION_API','EXECUTION','RESULT_ANALYSIS','DEFECT','REPORT','KNOWLEDGE','GENERAL')),
    title VARCHAR(256) NOT NULL,
    description TEXT,
    objective TEXT NOT NULL,
    acceptance_criteria TEXT NOT NULL DEFAULT '{}',
    constraints TEXT,
    agent_id UUID REFERENCES t_agent(id) ON DELETE SET NULL,  -- 注意:t_agent 建表在本文件 L1694(t_work_item 之后);执行迁移时须先建 t_agent 或后置 ADD CONSTRAINT(2026-08-15 修复说明)
    requires_review BOOLEAN NOT NULL DEFAULT TRUE,
    lock_version INT NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'BACKLOG' CHECK (status IN ('BACKLOG','READY','IN_PROGRESS','PENDING_REVIEW','REWORK','APPROVED','BLOCKED','DONE','CANCELLED')),
    current_actor_type VARCHAR(20) NOT NULL DEFAULT 'NONE' CHECK (current_actor_type IN ('HUMAN','AGENT','SYSTEM','NONE')),
    current_actor_id UUID,
    priority VARCHAR(5) NOT NULL CHECK (priority IN ('P0','P1','P2','P3')),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    owner_id UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    assignee_id UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    review_policy_id UUID REFERENCES t_review_policy(id) ON DELETE RESTRICT,
    due_at TIMESTAMPTZ,
    sla_seconds INT CHECK (sla_seconds IS NULL OR sla_seconds > 0),
    blocked_reason_code VARCHAR(100),
    blocked_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CHECK (parent_work_item_id IS NULL OR parent_work_item_id <> id),
    CHECK (status <> 'BLOCKED' OR blocked_reason_code IS NOT NULL)
);

CREATE TABLE t_work_item_artifact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(80) NOT NULL,
    artifact_id UUID NOT NULL,
    artifact_version_id UUID NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    relation_type VARCHAR(30) NOT NULL CHECK (relation_type IN ('INPUT','OUTPUT','REVIEW_TARGET','EVIDENCE','SUPERSEDES')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (work_item_id, artifact_version_id, relation_type)
);

CREATE TABLE t_work_item_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    attempt_no INT NOT NULL CHECK (attempt_no > 0),
    actor_type VARCHAR(20) NOT NULL CHECK (actor_type IN ('HUMAN','AGENT','SYSTEM')),
    actor_id UUID,
    agent_session_id UUID,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
    input_digest VARCHAR(64),
    output_digest VARCHAR(64),
    error_code VARCHAR(100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE (work_item_id, attempt_no)
);

CREATE TABLE t_work_item_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    sequence_no BIGINT NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    from_status VARCHAR(30),
    to_status VARCHAR(30),
    actor_type VARCHAR(20) NOT NULL,
    actor_id UUID,
    reason TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (work_item_id, sequence_no)
);

CREATE TABLE t_work_item_dependency (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    predecessor_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    successor_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    dependency_type VARCHAR(30) NOT NULL DEFAULT 'FINISH_TO_START',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (predecessor_id <> successor_id),
    UNIQUE (predecessor_id, successor_id)
);

CREATE TABLE t_review_task (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(80) NOT NULL,
    artifact_id UUID NOT NULL,
    artifact_version_id UUID NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    diff_ref TEXT,
    policy_type VARCHAR(30) NOT NULL CHECK (policy_type IN ('SINGLE_REVIEW','FOUR_EYES','CODE_REVIEW','EXTERNAL_WRITE','REPORT_SIGNOFF','KNOWLEDGE_PUBLISH')),
    policy_version_id UUID NOT NULL REFERENCES t_review_policy(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','IN_PROGRESS','APPROVED','CHANGES_REQUESTED','REJECTED','EXPIRED','CANCELLED')),
    check_results_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE t_review_assignment (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    review_task_id UUID NOT NULL REFERENCES t_review_task(id) ON DELETE RESTRICT,
    assignee_id UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    review_role VARCHAR(20) NOT NULL CHECK (review_role IN ('REVIEWER','APPROVER')),
    required_capability VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ASSIGNED' CHECK (status IN ('ASSIGNED','ACCEPTED','APPROVED','CHANGES_REQUESTED','REJECTED','REASSIGNED','EXPIRED')),
    decision VARCHAR(30) CHECK (decision IN ('APPROVE','REQUEST_CHANGES','REJECT')),
    comments TEXT,
    signature TEXT,
    assigned_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TIMESTAMPTZ,
    UNIQUE (review_task_id, assignee_id, review_role)
);
```

## 6. 知识库域

```sql
CREATE TABLE t_source_snapshot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    source_type VARCHAR(30) NOT NULL CHECK (source_type IN ('OPENAPI_FILE','OPENAPI_URL','REPOSITORY','MANUAL','TRAFFIC','OTHER')),
    source_integration_id UUID REFERENCES t_integration_config(id) ON DELETE RESTRICT,
    source_locator TEXT,
    fetched_revision VARCHAR(255),
    raw_content_ref TEXT,
    raw_digest VARCHAR(64),
    media_type VARCHAR(150),
    spec_version VARCHAR(50),
    fetch_status VARCHAR(30) NOT NULL CHECK (fetch_status IN ('PENDING','SUCCEEDED','FAILED','PARTIAL','NO_CONTENT_CHANGE')),
    fetched_by_actor_type VARCHAR(20) NOT NULL,
    fetched_by_actor_id UUID,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    error_code VARCHAR(100),
    error_message TEXT
);
CREATE INDEX idx_source_snapshot_workspace_time ON t_source_snapshot(workspace_id, fetched_at DESC);
CREATE INDEX idx_source_snapshot_digest ON t_source_snapshot(workspace_id, raw_digest);

CREATE TABLE t_requirement_document (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    name VARCHAR(256) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, name)
);

CREATE TABLE t_requirement_document_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    requirement_document_id UUID NOT NULL REFERENCES t_requirement_document(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    source_snapshot_id UUID NOT NULL REFERENCES t_source_snapshot(id) ON DELETE RESTRICT,
    content_ref TEXT NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    parse_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (parse_status IN ('DRAFT','PARSING','COMPLETED','FAILED')),
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_requirement_document_version(id) ON DELETE RESTRICT,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (requirement_document_id, version),
    UNIQUE (requirement_document_id, content_digest)
);

CREATE TABLE t_source_trace_edge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    from_type VARCHAR(80) NOT NULL,
    from_id UUID NOT NULL,
    from_version_id UUID,
    from_digest VARCHAR(64),
    to_type VARCHAR(80) NOT NULL,
    to_id UUID NOT NULL,
    to_version_id UUID,
    to_digest VARCHAR(64),
    relation_type VARCHAR(80) NOT NULL,
    evidence_class VARCHAR(20) NOT NULL CHECK (evidence_class IN ('CONFIRMED','INFERRED','UNRESOLVED','CONTRADICTS')),
    created_by_actor_type VARCHAR(20) NOT NULL,
    created_by_actor_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (from_type, from_id, from_version_id, to_type, to_id, to_version_id, relation_type)
);
CREATE INDEX idx_source_trace_from ON t_source_trace_edge(workspace_id, from_type, from_id);
CREATE INDEX idx_source_trace_to ON t_source_trace_edge(workspace_id, to_type, to_id);

CREATE TABLE t_ai_context_snapshot (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    source_version_refs JSONB NOT NULL,
    environment_ref JSONB,
    policy_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_ref TEXT NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (work_item_id, content_digest)
);

CREATE TABLE t_api_contract (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    name VARCHAR(200) NOT NULL,
    service_key VARCHAR(150) NOT NULL,
    protocol VARCHAR(30) NOT NULL CHECK (protocol IN ('HTTP_REST','GRAPHQL','GRPC','ASYNC_API','OTHER')),
    description TEXT,
    owning_team_ref VARCHAR(255),
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, service_key)
);

CREATE TABLE t_api_contract_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    api_contract_id UUID NOT NULL REFERENCES t_api_contract(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    source_kind VARCHAR(20) NOT NULL CHECK (source_kind IN ('DECLARED','OBSERVED','MANUAL','MERGED')),
    source_snapshot_ids JSONB NOT NULL,
    normalized_spec_ref TEXT NOT NULL,
    normalized_digest VARCHAR(64) NOT NULL,
    parser_name VARCHAR(100) NOT NULL,
    parser_version VARCHAR(50) NOT NULL,
    normalization_rules_version VARCHAR(50) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    validation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (validation_status IN ('PENDING','PASSED','FAILED','WARNING')),
    breaking_change_level VARCHAR(30) NOT NULL DEFAULT 'UNKNOWN' CHECK (breaking_change_level IN ('NONE','NON_BREAKING','POTENTIALLY_BREAKING','BREAKING','UNKNOWN')),
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_api_contract_version(id) ON DELETE RESTRICT,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (api_contract_id, version),
    UNIQUE (api_contract_id, normalized_digest)
);

CREATE TABLE t_api_operation_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    api_contract_version_id UUID NOT NULL REFERENCES t_api_contract_version(id) ON DELETE RESTRICT,
    stable_operation_key VARCHAR(255) NOT NULL,
    operation_id VARCHAR(255),
    method VARCHAR(20) NOT NULL,
    normalized_path VARCHAR(1000) NOT NULL,
    parameter_schema_ref TEXT,
    header_schema_ref TEXT,
    request_body_schemas_ref TEXT,
    response_schemas_ref TEXT,
    security_requirements_ref TEXT,
    schema_digest VARCHAR(64) NOT NULL,
    source_pointer TEXT,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (api_contract_version_id, stable_operation_key),
    UNIQUE (api_contract_version_id, method, normalized_path)
);

CREATE TABLE t_api_contract_baseline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    purpose VARCHAR(30) NOT NULL CHECK (purpose IN ('TEST_DESIGN','MOCK','CONTRACT_ANALYSIS')),
    version INT NOT NULL CHECK (version > 0),
    entries JSONB NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PENDING_REVIEW','APPROVED','RETIRED')),
    content_digest VARCHAR(64) NOT NULL,
    approved_by UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    approved_at TIMESTAMPTZ,
    created_from_work_item_id UUID REFERENCES t_work_item(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, release_id, purpose, version)
);

CREATE TABLE t_knowledge_entry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    knowledge_key VARCHAR(150) NOT NULL,
    category VARCHAR(80) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    review_due_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, knowledge_key)
);

CREATE TABLE t_knowledge_entry_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    knowledge_entry_id UUID NOT NULL REFERENCES t_knowledge_entry(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    title VARCHAR(300) NOT NULL,
    content_ref TEXT NOT NULL,
    applicable_scope JSONB NOT NULL,
    validation_evidence_refs JSONB NOT NULL,
    invalid_conditions JSONB NOT NULL,
    sensitivity VARCHAR(30) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_knowledge_entry_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (knowledge_entry_id, version),
    UNIQUE (knowledge_entry_id, content_digest)
);

CREATE TABLE t_knowledge_candidate (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    origin_type VARCHAR(80) NOT NULL,
    origin_id UUID NOT NULL,
    origin_version_id UUID,
    title VARCHAR(300) NOT NULL,
    content_ref TEXT NOT NULL,
    source_refs JSONB NOT NULL,
    duplicate_candidate_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PENDING_REVIEW','ACCEPTED','REJECTED','EXPIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_knowledge_vector (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    knowledge_entry_version_id UUID NOT NULL REFERENCES t_knowledge_entry_version(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL CHECK (chunk_index >= 0),
    chunk_text_ref TEXT NOT NULL,
    embedding_model VARCHAR(150) NOT NULL,
    embedding_model_version VARCHAR(80) NOT NULL,
    embedding vector(1536) NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    UNIQUE (knowledge_entry_version_id, chunk_index)
);

CREATE TABLE t_knowledge_graph_node (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    node_type VARCHAR(80) NOT NULL,
    business_key VARCHAR(255) NOT NULL,
    label VARCHAR(300) NOT NULL,
    source_version_ref JSONB NOT NULL,
    confidence NUMERIC(5,4),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','STALE','ARCHIVED')),
    UNIQUE (workspace_id, node_type, business_key)
);

CREATE TABLE t_knowledge_graph_edge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    from_node_id UUID NOT NULL REFERENCES t_knowledge_graph_node(id) ON DELETE RESTRICT,
    to_node_id UUID NOT NULL REFERENCES t_knowledge_graph_node(id) ON DELETE RESTRICT,
    relation_type VARCHAR(100) NOT NULL,
    source_version_ref JSONB NOT NULL,
    evidence_class VARCHAR(20) NOT NULL CHECK (evidence_class IN ('CONFIRMED','INFERRED','UNRESOLVED','CONTRADICTS')),
    confidence NUMERIC(5,4),
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','STALE','ARCHIVED')),
    CHECK (from_node_id <> to_node_id),
    UNIQUE (from_node_id, to_node_id, relation_type, source_version_ref)
);
```

## 7. 测试策划与设计域

```sql
CREATE TABLE t_test_strategy (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    strategy_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    legacy_ref VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, release_id, strategy_key)
);

CREATE TABLE t_test_strategy_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_strategy_id UUID NOT NULL REFERENCES t_test_strategy(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    objective TEXT NOT NULL,
    in_scope JSONB NOT NULL,
    out_of_scope JSONB NOT NULL,
    risk_assessment JSONB NOT NULL,
    test_types JSONB NOT NULL,
    approach TEXT NOT NULL,
    entry_criteria JSONB NOT NULL,
    exit_criteria JSONB NOT NULL,
    environment_strategy TEXT NOT NULL,
    data_strategy TEXT NOT NULL,
    automation_strategy TEXT NOT NULL,
    defect_strategy TEXT NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_test_strategy_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_strategy_id, version),
    UNIQUE (test_strategy_id, content_digest)
);

CREATE TABLE t_test_plan (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    requirement_document_id UUID REFERENCES t_requirement_document(id) ON DELETE SET NULL,
    plan_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    lifecycle_status VARCHAR(30) NOT NULL DEFAULT 'NOT_STARTED' CHECK (lifecycle_status IN ('NOT_STARTED','ACTIVE','COMPLETED','CANCELLED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, release_id, plan_key)
);

CREATE TABLE t_test_plan_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_plan_id UUID NOT NULL REFERENCES t_test_plan(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    strategy_version_id UUID NOT NULL REFERENCES t_test_strategy_version(id) ON DELETE RESTRICT,
    objective TEXT NOT NULL,
    plan_type VARCHAR(40) NOT NULL,
    scope JSONB NOT NULL,
    owner_id UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    participants JSONB NOT NULL DEFAULT '[]'::jsonb,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    milestones JSONB NOT NULL,
    resource_requirements JSONB NOT NULL,
    dependencies JSONB NOT NULL DEFAULT '[]'::jsonb,
    acceptance_criteria JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_test_plan_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    UNIQUE (test_plan_id, version),
    UNIQUE (test_plan_id, content_digest)
);

ALTER TABLE t_work_item
    ADD CONSTRAINT fk_work_item_test_plan
    FOREIGN KEY (test_plan_id) REFERENCES t_test_plan(id) ON DELETE RESTRICT;

CREATE TABLE t_testing_ir (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    requirement_version_refs JSONB NOT NULL,
    api_contract_version_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    ir_version INT NOT NULL CHECK (ir_version > 0),
    ir_content_ref TEXT,
    content_digest VARCHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','COMPILING','VALIDATED','FAILED')),
    compile_verdict VARCHAR(30) CHECK (compile_verdict IN ('PASS','PASS_WITH_REVIEW','REJECT')),
    compiler_name VARCHAR(100) NOT NULL,
    compiler_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, requirement_version_refs, ir_version)
);

CREATE TABLE t_business_rule (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    testing_ir_id UUID NOT NULL REFERENCES t_testing_ir(id) ON DELETE RESTRICT,
    rule_key VARCHAR(100) NOT NULL,
    condition TEXT NOT NULL,
    action TEXT,
    applicable_scope JSONB NOT NULL,
    source_trace JSONB NOT NULL,
    evidence_class VARCHAR(20) NOT NULL CHECK (evidence_class IN ('CONFIRMED','INFERRED','UNRESOLVED','CONTRADICTS')),
    confidence NUMERIC(5,4),
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','REJECTED','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (testing_ir_id, rule_key)
);

CREATE TABLE t_test_scenario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_plan_version_id UUID NOT NULL REFERENCES t_test_plan_version(id) ON DELETE RESTRICT,
    scenario_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    description TEXT,
    flow_steps JSONB NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    source_trace JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    supersedes_scenario_id UUID REFERENCES t_test_scenario(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_plan_version_id, scenario_key)
);

CREATE TABLE t_design_test_case (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_scenario_id UUID NOT NULL REFERENCES t_test_scenario(id) ON DELETE RESTRICT,
    draft_no INT NOT NULL CHECK (draft_no > 0),
    title VARCHAR(300) NOT NULL,
    preconditions JSONB NOT NULL,
    steps JSONB NOT NULL,
    test_data_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_results JSONB NOT NULL,
    priority VARCHAR(5) NOT NULL CHECK (priority IN ('P0','P1','P2','P3')),
    test_type VARCHAR(40) NOT NULL,
    source_trace JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    generated_by_agent_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_scenario_id, draft_no),
    UNIQUE (test_scenario_id, content_digest)
);

CREATE TABLE t_test_case (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    case_key VARCHAR(150) NOT NULL,
    title VARCHAR(300) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, case_key)
);

CREATE TABLE t_test_case_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_case_id UUID NOT NULL REFERENCES t_test_case(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    title VARCHAR(300) NOT NULL,
    preconditions JSONB NOT NULL,
    steps JSONB NOT NULL,
    test_data_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_results JSONB NOT NULL,
    priority VARCHAR(5) NOT NULL CHECK (priority IN ('P0','P1','P2','P3')),
    test_type VARCHAR(40) NOT NULL,
    source_trace JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_case_id, version),
    UNIQUE (test_case_id, content_digest)
);

CREATE TABLE t_assertion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_case_version_id UUID REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    design_test_case_id UUID REFERENCES t_design_test_case(id) ON DELETE RESTRICT,
    assertion_key VARCHAR(100) NOT NULL,
    target VARCHAR(500) NOT NULL,
    expression VARCHAR(80) NOT NULL,
    expected JSONB NOT NULL,
    source_trace JSONB NOT NULL,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'UNVERIFIED' CHECK (verification_status IN ('VERIFIED','REJECTED','UNVERIFIED')),
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((test_case_version_id IS NOT NULL)::int + (design_test_case_id IS NOT NULL)::int = 1),
    UNIQUE NULLS NOT DISTINCT (test_case_version_id, design_test_case_id, assertion_key)
);

CREATE TABLE t_test_suite (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    suite_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, suite_key)
);

CREATE TABLE t_test_suite_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_suite_id UUID NOT NULL REFERENCES t_test_suite(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    description TEXT,
    selection_type VARCHAR(20) NOT NULL CHECK (selection_type IN ('STATIC','DYNAMIC')),
    selection_rule JSONB,
    content_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_suite_id, version)
);

CREATE TABLE t_test_suite_case_mapping (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_suite_version_id UUID NOT NULL REFERENCES t_test_suite_version(id) ON DELETE RESTRICT,
    test_case_version_id UUID NOT NULL REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    sequence_no INT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (test_suite_version_id, test_case_version_id)
);
```

## 8. 自动化测试开发域

```sql
CREATE TABLE t_automation_script (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    script_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    automation_type VARCHAR(30) NOT NULL CHECK (automation_type IN ('WEB','API','MOBILE','PERFORMANCE','SECURITY')),
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, script_key)
);

CREATE TABLE t_automation_script_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    automation_script_id UUID NOT NULL REFERENCES t_automation_script(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    language VARCHAR(50) NOT NULL,
    framework VARCHAR(100) NOT NULL,
    framework_version VARCHAR(50) NOT NULL,
    runtime_version VARCHAR(50) NOT NULL,
    source_mode VARCHAR(20) NOT NULL CHECK (source_mode IN ('MANAGED','GIT')),
    code_content_ref TEXT,
    repository_integration_id UUID REFERENCES t_integration_config(id) ON DELETE RESTRICT,
    full_commit_sha VARCHAR(64),
    file_path TEXT,
    blob_sha VARCHAR(64),
    content_digest VARCHAR(64) NOT NULL,
    dependency_lock_ref TEXT,
    dependency_digest VARCHAR(64) NOT NULL,
    type_config JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_automation_script_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((source_mode = 'MANAGED' AND code_content_ref IS NOT NULL AND repository_integration_id IS NULL)
        OR (source_mode = 'GIT' AND repository_integration_id IS NOT NULL AND full_commit_sha IS NOT NULL AND file_path IS NOT NULL AND blob_sha IS NOT NULL)),
    UNIQUE (automation_script_id, version),
    UNIQUE (automation_script_id, content_digest)
);

CREATE TABLE t_automation_script_version_case_binding (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    automation_script_version_id UUID NOT NULL REFERENCES t_automation_script_version(id) ON DELETE RESTRICT,
    test_case_version_id UUID NOT NULL REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    coverage_type VARCHAR(40) NOT NULL,
    coverage_notes TEXT,
    UNIQUE (automation_script_version_id, test_case_version_id)
);

CREATE TABLE t_automation_check_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    script_version_id UUID NOT NULL REFERENCES t_automation_script_version(id) ON DELETE RESTRICT,
    check_type VARCHAR(50) NOT NULL,
    tool_name VARCHAR(100) NOT NULL,
    tool_version VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','PASSED','FAILED','WARNING','CANCELLED')),
    finding_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_ref TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE t_test_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    data_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    schema_ref TEXT NOT NULL,
    content_ref TEXT,
    generator_ref TEXT,
    sensitivity VARCHAR(30) NOT NULL,
    masking_status VARCHAR(20) NOT NULL,
    cleanup_policy JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((content_ref IS NOT NULL)::int + (generator_ref IS NOT NULL)::int = 1),
    UNIQUE (workspace_id, data_key, version)
);

CREATE TABLE t_test_data_profile (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    profile_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    schema_ref TEXT NOT NULL,
    generation_rules JSONB NOT NULL,
    masking_rules JSONB NOT NULL,
    cleanup_rules JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DEPRECATED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, profile_key, version)
);

CREATE TABLE t_locator (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    locator_key VARCHAR(150) NOT NULL,
    page_key VARCHAR(150) NOT NULL,
    element_name VARCHAR(200) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    primary_selector TEXT NOT NULL,
    backup_selectors JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','VERIFIED','DECAYING','FAILED','HEALED_CANDIDATE','DEPRECATED')),  -- 2026-08-15 裁决 B2:新增 PENDING 初始态(自愈验证前)
    source_trace JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    supersedes_locator_id UUID REFERENCES t_locator(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, locator_key, version)
);

CREATE TABLE t_mock_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    mock_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    api_contract_version_id UUID NOT NULL REFERENCES t_api_contract_version(id) ON DELETE RESTRICT,
    operation_version_id UUID REFERENCES t_api_operation_version(id) ON DELETE RESTRICT,
    match_rules JSONB NOT NULL,
    response_rules JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, mock_key, version)
);

CREATE TABLE t_visual_baseline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    baseline_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    artifact_ref TEXT NOT NULL,
    mask_regions JSONB NOT NULL DEFAULT '[]'::jsonb,
    viewport_config JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, baseline_key, version)
);

CREATE TABLE t_performance_baseline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    baseline_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    metric_definitions JSONB NOT NULL,
    workload_model_ref TEXT NOT NULL,
    environment_requirements JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, baseline_key, version)
);
```

## 9. 测试执行域

```sql
CREATE TABLE t_execution_plan (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    plan_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    test_plan_id UUID NOT NULL REFERENCES t_test_plan(id) ON DELETE RESTRICT,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, plan_key)
);

CREATE TABLE t_execution_plan_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_plan_id UUID NOT NULL REFERENCES t_execution_plan(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    test_plan_version_id UUID NOT NULL REFERENCES t_test_plan_version(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    environment_id UUID NOT NULL REFERENCES t_environment(id) ON DELETE RESTRICT,
    scope_configs JSONB NOT NULL,
    trigger_type VARCHAR(20) NOT NULL CHECK (trigger_type IN ('MANUAL','SCHEDULE','WEBHOOK','PIPELINE')),
    cron_expression VARCHAR(150),
    parallelism INT NOT NULL DEFAULT 1 CHECK (parallelism > 0),
    runner_policy JSONB NOT NULL,
    asset_version_refs JSONB NOT NULL,
    configuration_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_execution_plan_version(id) ON DELETE RESTRICT,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (execution_plan_id, version),
    UNIQUE (execution_plan_id, configuration_digest)
);

CREATE TABLE t_execution_contract_baseline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_plan_version_id UUID NOT NULL REFERENCES t_execution_plan_version(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    environment_snapshot_ref TEXT NOT NULL,
    entries JSONB NOT NULL,
    server_mappings JSONB NOT NULL,
    credential_refs JSONB NOT NULL,
    variable_schema JSONB NOT NULL,
    masking_rules JSONB NOT NULL,
    baseline_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (execution_plan_version_id, baseline_digest)
);

CREATE TABLE t_execution_task (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_plan_version_id UUID NOT NULL REFERENCES t_execution_plan_version(id) ON DELETE RESTRICT,
    work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','QUEUED','RUNNING','COMPLETED','FAILED','CANCELLED','TIMED_OUT','BLOCKED')),
    blocked_reason VARCHAR(40) CHECK (blocked_reason IN ('USER_PAUSED','DEPENDENCY_BLOCKED','ENV_ISSUE','PERMISSION','QUALITY')),  -- 仅 status=BLOCKED 时有值;用户主动暂停=USER_PAUSED(裁决 2026-08-14 B4,并入 M1 建表)
    runner_node_id UUID REFERENCES t_runner_node(id) ON DELETE RESTRICT,
    authorization_decision_id UUID NOT NULL REFERENCES t_authorization_decision(id) ON DELETE RESTRICT,
    input_snapshot_digest VARCHAR(64) NOT NULL,
    queued_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_code VARCHAR(100),
    timeout_seconds INTEGER NOT NULL DEFAULT 300,  -- 第0周补丁 B3:任务级超时阈值(2026-08-14)
    lease_expires_at TIMESTAMPTZ,                  -- 第0周补丁 B3:租约到期时间,失联检测依据(2026-08-14)
    retry_of_task_id UUID REFERENCES t_execution_task(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 第0周补丁 B3(2026-08-14):执行任务状态只追加事件表(补 20 §4.2 只追加清单缺口)
CREATE TABLE t_execution_task_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_task_id UUID NOT NULL REFERENCES t_execution_task(id) ON DELETE RESTRICT,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    reason VARCHAR(200),
    correlation_id UUID,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_exec_task_event ON t_execution_task_event(execution_task_id, occurred_at);

CREATE TABLE t_execution_result (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_task_id UUID NOT NULL REFERENCES t_execution_task(id) ON DELETE RESTRICT,
    test_case_version_id UUID NOT NULL REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    script_version_id UUID REFERENCES t_automation_script_version(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PASSED','FAILED','SKIPPED','ERROR','INCONCLUSIVE')),
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_ms BIGINT CHECK (duration_ms IS NULL OR duration_ms >= 0),
    assertion_results_ref TEXT,
    error_type VARCHAR(100),
    error_message TEXT,
    result_digest VARCHAR(64) NOT NULL,
    is_experimental BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (execution_task_id, test_case_version_id, script_version_id)
);

CREATE TABLE t_execution_artifact (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_result_id UUID NOT NULL REFERENCES t_execution_result(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(30) NOT NULL CHECK (artifact_type IN ('LOG','SCREENSHOT','VIDEO','TRACE','REQUEST','RESPONSE','OTHER')),
    storage_ref TEXT NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    media_type VARCHAR(150),
    sensitivity VARCHAR(30) NOT NULL,
    retention_policy JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_api_observation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_result_id UUID NOT NULL REFERENCES t_execution_result(id) ON DELETE RESTRICT,
    operation_version_id UUID REFERENCES t_api_operation_version(id) ON DELETE RESTRICT,
    request_meta_ref TEXT NOT NULL,
    request_body_ref TEXT,
    response_meta_ref TEXT NOT NULL,
    response_body_ref TEXT,
    status_code INT,
    duration_ms BIGINT CHECK (duration_ms IS NULL OR duration_ms >= 0),
    environment_snapshot_ref TEXT NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_contract_check_result (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_result_id UUID NOT NULL REFERENCES t_execution_result(id) ON DELETE RESTRICT,
    execution_contract_baseline_id UUID NOT NULL REFERENCES t_execution_contract_baseline(id) ON DELETE RESTRICT,
    operation_version_id UUID REFERENCES t_api_operation_version(id) ON DELETE RESTRICT,
    check_type VARCHAR(80) NOT NULL,
    status VARCHAR(30) NOT NULL CHECK (status IN ('MATCH','DEVIATION','NOT_CHECKED','INCONCLUSIVE')),
    expected_ref TEXT,
    actual_ref TEXT,
    severity VARCHAR(20) CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 10. 质量分析与缺陷域

```sql
CREATE TABLE t_result_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    analysis_key VARCHAR(150) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, analysis_key)
);

CREATE TABLE t_result_analysis_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    result_analysis_id UUID NOT NULL REFERENCES t_result_analysis(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    execution_result_refs JSONB NOT NULL,
    confirmed_facts JSONB NOT NULL,
    inferences JSONB NOT NULL,
    confidence NUMERIC(5,4),
    alternative_explanations JSONB NOT NULL,
    impact_scope JSONB NOT NULL,
    recommendations JSONB NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_result_analysis_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (result_analysis_id, version),
    UNIQUE (result_analysis_id, content_digest)
);

CREATE TABLE t_failure_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    execution_result_id UUID NOT NULL REFERENCES t_execution_result(id) ON DELETE RESTRICT,
    analysis_version INT NOT NULL CHECK (analysis_version > 0),
    failure_category VARCHAR(30) NOT NULL CHECK (failure_category IN ('PRODUCT_BUG','SCRIPT_ISSUE','ENVIRONMENT_ISSUE','DATA_ISSUE','FLAKY_TEST','UNKNOWN')),
    root_cause_description TEXT,
    evidence_refs JSONB NOT NULL,
    confidence NUMERIC(5,4),
    suggested_action TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','PENDING_REVIEW','CONFIRMED','REJECTED','STALE')),
    review_task_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (execution_result_id, analysis_version)
);

CREATE TABLE t_failure_cluster (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    cluster_key VARCHAR(150) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL,
    algorithm_version VARCHAR(50) NOT NULL,
    fingerprint VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','SPLIT','MERGED','REJECTED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, cluster_key)
);

CREATE TABLE t_failure_cluster_member (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    failure_cluster_id UUID NOT NULL REFERENCES t_failure_cluster(id) ON DELETE RESTRICT,
    failure_analysis_id UUID NOT NULL REFERENCES t_failure_analysis(id) ON DELETE RESTRICT,
    similarity_score NUMERIC(5,4),
    membership_reason TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (failure_cluster_id, failure_analysis_id)
);
CREATE UNIQUE INDEX uq_active_failure_membership
    ON t_failure_cluster_member(failure_analysis_id) WHERE active;

CREATE TABLE t_coverage_report (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    scope_snapshot_ref TEXT NOT NULL,
    denominator_definition_ref VARCHAR(40) NOT NULL CHECK (denominator_definition_ref IN ('INSTANCE','DESIGN','EXECUTABLE','EFFECTIVE','HUMAN_ACCEPTANCE')),  -- 五类覆盖率口径(裁决 2026-08-14,定义见 22 号附录)
    -- 第0周补丁 B5(2026-08-14):EXECUTABLE 维由 13/14 号汇总(AutomationScriptVersionCaseBinding→ExecutionResult),HUMAN_ACCEPTANCE 维由 15 号汇总(ReviewTask APPROVED+PUBLISHED),两维不落本表独立列
    rule_dimension JSONB NOT NULL,
    scenario_dimension JSONB NOT NULL,
    state_dimension JSONB NOT NULL,
    assertion_dimension JSONB NOT NULL,
    api_dimension JSONB NOT NULL,
    verdict VARCHAR(30) NOT NULL CHECK (verdict IN ('PASS','FAIL','PASS_WITH_REVIEW','INCONCLUSIVE')),
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_defect (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    defect_key VARCHAR(150) NOT NULL,
    lifecycle_status VARCHAR(30) NOT NULL DEFAULT 'NEW' CHECK (lifecycle_status IN ('NEW','OPEN','IN_PROGRESS','RESOLVED','VERIFIED','CLOSED','REJECTED','DUPLICATE','ARCHIVED')),
    current_version_id UUID,
    approved_version_id UUID,
    assignee_id UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    duplicate_of_defect_id UUID REFERENCES t_defect(id) ON DELETE RESTRICT,
    created_from_work_item_id UUID NOT NULL REFERENCES t_work_item(id) ON DELETE RESTRICT,
    created_by_actor_type VARCHAR(20) NOT NULL,
    created_by_actor_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (duplicate_of_defect_id IS NULL OR duplicate_of_defect_id <> id),
    CHECK (lifecycle_status <> 'DUPLICATE' OR duplicate_of_defect_id IS NOT NULL),
    UNIQUE (workspace_id, defect_key)
);

CREATE TABLE t_defect_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    defect_id UUID NOT NULL REFERENCES t_defect(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    title VARCHAR(300) NOT NULL,
    description TEXT NOT NULL,
    preconditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    reproduction_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_result TEXT NOT NULL,
    actual_result TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    priority VARCHAR(5) NOT NULL CHECK (priority IN ('P0','P1','P2','P3')),
    defect_type VARCHAR(30) NOT NULL CHECK (defect_type IN ('PRODUCT','SCRIPT','ENVIRONMENT','DATA','SECURITY','PERFORMANCE','USABILITY','OTHER')),
    environment_snapshot_ref TEXT NOT NULL,
    affected_release_ids JSONB NOT NULL,
    labels JSONB NOT NULL DEFAULT '[]'::jsonb,
    component VARCHAR(255),
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_defect_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (defect_id, version),
    UNIQUE (defect_id, content_digest)
);

CREATE TABLE t_defect_evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    defect_version_id UUID NOT NULL REFERENCES t_defect_version(id) ON DELETE RESTRICT,
    evidence_type VARCHAR(50) NOT NULL,
    evidence_id UUID NOT NULL,
    evidence_version_id UUID,
    evidence_digest VARCHAR(64) NOT NULL,
    relation_type VARCHAR(40) NOT NULL CHECK (relation_type IN ('OBSERVED_IN','SUPPORTS_EXPECTED','SUPPORTS_ACTUAL','SUPPORTS_ROOT_CAUSE','REGRESSION_VERIFICATION','CONTRADICTS')),
    source_trace_edge_id UUID REFERENCES t_source_trace_edge(id) ON DELETE RESTRICT,
    added_by_actor_type VARCHAR(20) NOT NULL,
    added_by_actor_id UUID,
    added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (defect_version_id, evidence_type, evidence_id, evidence_version_id, relation_type)
);

CREATE TABLE t_defect_status_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    defect_id UUID NOT NULL REFERENCES t_defect(id) ON DELETE RESTRICT,
    sequence_no BIGINT NOT NULL,
    from_status VARCHAR(30),
    to_status VARCHAR(30) NOT NULL,
    reason TEXT NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    actor_id UUID,
    regression_evidence_ref JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (defect_id, sequence_no)
);

CREATE TABLE t_external_defect_link (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    defect_id UUID NOT NULL REFERENCES t_defect(id) ON DELETE RESTRICT,
    integration_id UUID NOT NULL REFERENCES t_integration_config(id) ON DELETE RESTRICT,
    provider VARCHAR(50) NOT NULL,
    external_tenant_id VARCHAR(255),
    external_project_id VARCHAR(255),
    external_issue_id VARCHAR(255) NOT NULL,
    external_issue_key VARCHAR(255),
    external_url TEXT,
    sync_status VARCHAR(20) NOT NULL DEFAULT 'NOT_SYNCED' CHECK (sync_status IN ('NOT_SYNCED','SYNCING','SYNCED','FAILED','CONFLICT','DISABLED')),
    last_synced_defect_version_id UUID REFERENCES t_defect_version(id) ON DELETE RESTRICT,
    last_remote_version VARCHAR(255),
    remote_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (integration_id, external_issue_id)
);

CREATE TABLE t_defect_sync_attempt (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    defect_id UUID NOT NULL REFERENCES t_defect(id) ON DELETE RESTRICT,
    defect_version_id UUID NOT NULL REFERENCES t_defect_version(id) ON DELETE RESTRICT,
    external_defect_link_id UUID REFERENCES t_external_defect_link(id) ON DELETE RESTRICT,
    operation VARCHAR(20) NOT NULL CHECK (operation IN ('CREATE','UPDATE','COMMENT','TRANSITION','ATTACH','LINK')),
    payload_digest VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    approval_id UUID NOT NULL REFERENCES t_review_task(id) ON DELETE RESTRICT,  -- 与 05 §5.9.8/32 approvalId 统一(裁决 2026-08-14 复核收口)
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CONFLICT','CANCELLED')),
    remote_request_ref TEXT,
    remote_response_ref TEXT,
    error_code VARCHAR(100),
    error_message TEXT,
    retry_of_attempt_id UUID REFERENCES t_defect_sync_attempt(id) ON DELETE RESTRICT,
    retry_count INT NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE t_test_report (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    release_id UUID NOT NULL REFERENCES t_release(id) ON DELETE RESTRICT,
    report_key VARCHAR(150) NOT NULL,
    current_version_id UUID,
    published_version_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, report_key)
);

CREATE TABLE t_test_report_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    test_report_id UUID NOT NULL REFERENCES t_test_report(id) ON DELETE RESTRICT,
    version INT NOT NULL CHECK (version > 0),
    scope_snapshot_ref TEXT NOT NULL,
    execution_snapshot_ref TEXT NOT NULL,
    coverage_report_refs JSONB NOT NULL,
    defect_version_refs JSONB NOT NULL,
    risk_summary JSONB NOT NULL,
    residual_risks JSONB NOT NULL,
    quality_conclusion TEXT NOT NULL,
    data_snapshot_digest VARCHAR(64) NOT NULL,
    review_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (review_status IN ('DRAFT','GENERATING','PENDING_REVIEW','CHANGES_REQUESTED','APPROVED','PUBLISHED','REJECTED','STALE','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    change_summary TEXT,
    supersedes_version_id UUID REFERENCES t_test_report_version(id) ON DELETE RESTRICT,
    generated_by_agent_id UUID,
    agent_run_id UUID,
    created_by UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (test_report_id, version),
    UNIQUE (test_report_id, content_digest)
);

CREATE TABLE t_quality_gate (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    gate_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    rules JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','RETIRED')),
    content_digest VARCHAR(64) NOT NULL,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, gate_key, version)
);

CREATE TABLE t_pipeline_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    pipeline_key VARCHAR(150) NOT NULL,
    integration_id UUID NOT NULL REFERENCES t_integration_config(id) ON DELETE RESTRICT,
    external_pipeline_ref VARCHAR(500) NOT NULL,
    trigger_rules JSONB NOT NULL,
    execution_plan_refs JSONB NOT NULL,
    quality_gate_version_id UUID NOT NULL REFERENCES t_quality_gate(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DISABLED','ARCHIVED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, pipeline_key)
);

CREATE TABLE t_pipeline_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    pipeline_config_id UUID NOT NULL REFERENCES t_pipeline_config(id) ON DELETE RESTRICT,
    external_run_id VARCHAR(255) NOT NULL,
    commit_ref VARCHAR(255),
    release_id UUID REFERENCES t_release(id) ON DELETE RESTRICT,
    execution_task_refs JSONB NOT NULL,
    quality_input_digest VARCHAR(64),
    gate_decision VARCHAR(30) CHECK (gate_decision IN ('PASSED','WARNED','BLOCKED','QUARANTINED','INCONCLUSIVE')),
    exception_decision_ref UUID REFERENCES t_authorization_decision(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE (pipeline_config_id, external_run_id)
);
```

## 11. AI Agent中心域

```sql
CREATE TABLE t_skill (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    skill_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    version VARCHAR(50) NOT NULL,
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    permission_requirements JSONB NOT NULL,
    package_digest VARCHAR(64) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'INSTALLING' CHECK (status IN ('INSTALLING','INACTIVE','ACTIVE','DISABLED','ERROR','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (tenant_id, skill_key, version)
);

CREATE TABLE t_workspace_skill_enablement (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    skill_id UUID NOT NULL REFERENCES t_skill(id) ON DELETE RESTRICT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    config_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    permission_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    approved_by UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, skill_id)
);

CREATE TABLE t_agent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    agent_key VARCHAR(150) NOT NULL,
    name VARCHAR(250) NOT NULL,
    role_description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'INACTIVE' CHECK (status IN ('INACTIVE','ACTIVE','DEGRADED','RETIRED')),
    current_prompt_version_id UUID,
    delegation_depth_limit INT NOT NULL DEFAULT 0 CHECK (delegation_depth_limit >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (tenant_id, agent_key)
);

CREATE TABLE t_workspace_agent_enablement (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    agent_id UUID NOT NULL REFERENCES t_agent(id) ON DELETE RESTRICT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    model_override JSONB,
    budget_limit JSONB NOT NULL DEFAULT '{}'::jsonb,
    permission_limits JSONB NOT NULL DEFAULT '{}'::jsonb,
    approved_by UUID REFERENCES t_user(id) ON DELETE RESTRICT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (workspace_id, agent_id)
);

CREATE TABLE t_agent_skill_grant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES t_agent(id) ON DELETE RESTRICT,
    skill_id UUID NOT NULL REFERENCES t_skill(id) ON DELETE RESTRICT,
    version_range VARCHAR(100) NOT NULL,
    conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (agent_id, skill_id)
);

CREATE TABLE t_agent_workflow (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    workflow_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    dag_definition JSONB NOT NULL,
    human_checkpoints JSONB NOT NULL,
    max_depth INT NOT NULL DEFAULT 1 CHECK (max_depth >= 0),
    max_iterations INT NOT NULL CHECK (max_iterations > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','ACTIVE','RETIRED')),
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (tenant_id, workspace_id, workflow_key, version)
);

CREATE TABLE t_agent_prompt_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    agent_id UUID NOT NULL REFERENCES t_agent(id) ON DELETE RESTRICT,
    version_tag VARCHAR(80) NOT NULL,
    system_prompt_ref TEXT NOT NULL,
    parameter_config JSONB NOT NULL,
    compatibility JSONB NOT NULL,
    content_digest VARCHAR(64) NOT NULL,
    eval_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (eval_status IN ('PENDING','PASSED','FAILED','WARNING')),
    release_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT' CHECK (release_status IN ('DRAFT','PENDING_REVIEW','ACTIVE','RETIRED')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (agent_id, version_tag),
    UNIQUE (agent_id, content_digest)
);

ALTER TABLE t_agent
    ADD CONSTRAINT fk_agent_current_prompt
    FOREIGN KEY (current_prompt_version_id) REFERENCES t_agent_prompt_version(id) ON DELETE RESTRICT;

CREATE TABLE t_agent_session (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    work_item_run_id UUID NOT NULL REFERENCES t_work_item_run(id) ON DELETE RESTRICT,
    agent_id UUID NOT NULL REFERENCES t_agent(id) ON DELETE RESTRICT,
    workflow_version_id UUID REFERENCES t_agent_workflow(id) ON DELETE RESTRICT,
    prompt_version_id UUID NOT NULL REFERENCES t_agent_prompt_version(id) ON DELETE RESTRICT,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','CANCELLED','BLOCKED')),
    input_digest VARCHAR(64) NOT NULL,
    output_digest VARCHAR(64),
    token_usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    cost JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_code VARCHAR(100)
);

ALTER TABLE t_work_item_run
    ADD CONSTRAINT fk_work_item_run_agent_session
    FOREIGN KEY (agent_session_id) REFERENCES t_agent_session(id) ON DELETE RESTRICT;

CREATE TABLE t_agent_trace_node (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    agent_session_id UUID NOT NULL REFERENCES t_agent_session(id) ON DELETE RESTRICT,
    parent_node_id UUID REFERENCES t_agent_trace_node(id) ON DELETE RESTRICT,
    node_type VARCHAR(50) NOT NULL,
    sequence_no BIGINT NOT NULL,
    decision_summary TEXT,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_ref JSONB,
    input_digest VARCHAR(64),
    output_digest VARCHAR(64),
    status VARCHAR(20) NOT NULL,
    duration_ms BIGINT CHECK (duration_ms IS NULL OR duration_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (agent_session_id, sequence_no)
);

CREATE TABLE t_skill_invocation (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    agent_session_id UUID NOT NULL REFERENCES t_agent_session(id) ON DELETE RESTRICT,
    trace_node_id UUID NOT NULL REFERENCES t_agent_trace_node(id) ON DELETE RESTRICT,
    skill_id UUID NOT NULL REFERENCES t_skill(id) ON DELETE RESTRICT,
    skill_version VARCHAR(50) NOT NULL,
    authorization_decision_id UUID NOT NULL REFERENCES t_authorization_decision(id) ON DELETE RESTRICT,
    input_digest VARCHAR(64) NOT NULL,
    output_digest VARCHAR(64),
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','SUCCEEDED','FAILED','DENIED','TIMED_OUT','CANCELLED')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_code VARCHAR(100)
);

CREATE TABLE t_eval_dataset (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    dataset_key VARCHAR(150) NOT NULL,
    version INT NOT NULL CHECK (version > 0),
    scope JSONB NOT NULL,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'DRAFT' CHECK (approval_status IN ('DRAFT','PENDING_REVIEW','APPROVED','REJECTED','ARCHIVED')),
    content_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT (tenant_id, workspace_id, dataset_key, version)
);

CREATE TABLE t_eval_case (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    eval_dataset_id UUID NOT NULL REFERENCES t_eval_dataset(id) ON DELETE RESTRICT,
    case_key VARCHAR(150) NOT NULL,
    case_input_ref TEXT NOT NULL,
    expected_ref TEXT NOT NULL,
    risk_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    UNIQUE (eval_dataset_id, case_key)
);

CREATE TABLE t_eval_run (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE RESTRICT,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('AGENT','SKILL','PROMPT','WORKFLOW')),
    target_version_id UUID NOT NULL,
    dataset_version_id UUID NOT NULL REFERENCES t_eval_dataset(id) ON DELETE RESTRICT,
    environment_ref TEXT,
    metrics JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('PENDING','RUNNING','PASSED','FAILED','CANCELLED')),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE TABLE t_eval_result (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    eval_run_id UUID NOT NULL REFERENCES t_eval_run(id) ON DELETE RESTRICT,
    eval_case_id UUID NOT NULL REFERENCES t_eval_case(id) ON DELETE RESTRICT,
    verdict VARCHAR(20) NOT NULL CHECK (verdict IN ('PASS','FAIL','ERROR','SKIPPED')),
    actual_ref TEXT,
    evidence_ref TEXT,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (eval_run_id, eval_case_id)
);

-- 裁决 B2-3（2026-08-14）：AI 介入点校准记录（21 号 §4 / AC-03 判定底座）
CREATE TABLE t_calibration_record (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES t_tenant(id) ON DELETE RESTRICT,
    workspace_id UUID REFERENCES t_workspace(id) ON DELETE SET NULL,
    intervention_key VARCHAR(80) NOT NULL,
    subject_version TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    metric_definition TEXT NOT NULL,
    threshold REAL NOT NULL,  -- REAL 为 PostgreSQL 合法类型(单精度),SQLite 亦兼容(NUMERIC affinity);2026-08-15 复核确认非缺陷
    sample_size INTEGER NOT NULL,
    baseline TEXT,
    subject_operation TEXT,  -- JSON 数组字符串,如 ["createTestCase","transitionWorkItem"];一介入点多实现点(批3收口 2026-08-14)
    subject_table TEXT,      -- JSON 数组字符串,如 ["t_test_case","t_design_test_case"];NULL=无单一归属(如 INDEPENDENT_VERIFY)
    valid_from TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    fallback_level VARCHAR(10) NOT NULL,
    created_by UUID NOT NULL REFERENCES t_user(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_calibration_key ON t_calibration_record(intervention_key, valid_from, expires_at);

-- 裁决 2026-08-14(M1 最小落点):INDEPENDENT_VERIFY 三层证据第二层裁决表,支撑"禁止 AI 自批"负向用例
CREATE TABLE t_verify_verdict (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES t_workspace(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(80) NOT NULL,
    artifact_version_id UUID NOT NULL,
    verifier_agent_id UUID REFERENCES t_agent(id) ON DELETE SET NULL,
    verdict VARCHAR(20) NOT NULL CHECK (verdict IN ('PASS','FAIL','REVIEW_REQUIRED','ERROR')),  -- 2026-08-15 修复:枚举加引号(原 DDL 不可执行)
    evidence_ref TEXT,
    input_digest VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (artifact_version_id, verifier_agent_id)
);
CREATE INDEX idx_verify_artifact ON t_verify_verdict(artifact_type, artifact_version_id);
```

### 11.1 人机协作目标表（待激活）

2026-08-27需求基线新增以下持久化概念：`t_conversation`、`t_conversation_message`、`t_clarification_request`、`t_clarification_response`、`t_task_card`、`t_agent_plan_version`、`t_task_contract`、`t_run_command`、`t_command_receipt`、`t_budget_policy`、`t_checkpoint`、`t_evaluation_rubric_version`、`t_evaluation_run`、`t_evaluation_dimension_result`、`t_evaluation_blocking_finding`、`t_calibration_sample`。

此清单只用于需求/领域模型对齐，不是可执行DDL。实体边界以39号为准；开发前必须单独补齐FK、唯一约束、RLS、只追加规则、存储期/删除策略、脱敏和迁移/回滚，并在38号登记迁移。未完成该激活包前，本文其余DDL不得被解读为已支持对话与运行命令。

## 12. 稳定根版本指针外键

稳定根先于版本表创建，因此统一在版本表完成后补指针FK：

```sql
ALTER TABLE t_requirement_document
    ADD CONSTRAINT fk_requirement_current_version FOREIGN KEY (current_version_id) REFERENCES t_requirement_document_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_requirement_published_version FOREIGN KEY (published_version_id) REFERENCES t_requirement_document_version(id) ON DELETE RESTRICT;
ALTER TABLE t_api_contract
    ADD CONSTRAINT fk_api_contract_current_version FOREIGN KEY (current_version_id) REFERENCES t_api_contract_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_api_contract_published_version FOREIGN KEY (published_version_id) REFERENCES t_api_contract_version(id) ON DELETE RESTRICT;
ALTER TABLE t_knowledge_entry
    ADD CONSTRAINT fk_knowledge_current_version FOREIGN KEY (current_version_id) REFERENCES t_knowledge_entry_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_knowledge_published_version FOREIGN KEY (published_version_id) REFERENCES t_knowledge_entry_version(id) ON DELETE RESTRICT;
ALTER TABLE t_test_strategy
    ADD CONSTRAINT fk_strategy_current_version FOREIGN KEY (current_version_id) REFERENCES t_test_strategy_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_strategy_published_version FOREIGN KEY (published_version_id) REFERENCES t_test_strategy_version(id) ON DELETE RESTRICT;
ALTER TABLE t_test_plan
    ADD CONSTRAINT fk_plan_current_version FOREIGN KEY (current_version_id) REFERENCES t_test_plan_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_plan_published_version FOREIGN KEY (published_version_id) REFERENCES t_test_plan_version(id) ON DELETE RESTRICT;
ALTER TABLE t_test_case
    ADD CONSTRAINT fk_case_current_version FOREIGN KEY (current_version_id) REFERENCES t_test_case_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_case_published_version FOREIGN KEY (published_version_id) REFERENCES t_test_case_version(id) ON DELETE RESTRICT;
ALTER TABLE t_test_suite
    ADD CONSTRAINT fk_suite_current_version FOREIGN KEY (current_version_id) REFERENCES t_test_suite_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_suite_published_version FOREIGN KEY (published_version_id) REFERENCES t_test_suite_version(id) ON DELETE RESTRICT;
ALTER TABLE t_automation_script
    ADD CONSTRAINT fk_script_current_version FOREIGN KEY (current_version_id) REFERENCES t_automation_script_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_script_published_version FOREIGN KEY (published_version_id) REFERENCES t_automation_script_version(id) ON DELETE RESTRICT;
ALTER TABLE t_execution_plan
    ADD CONSTRAINT fk_execution_plan_current_version FOREIGN KEY (current_version_id) REFERENCES t_execution_plan_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_execution_plan_published_version FOREIGN KEY (published_version_id) REFERENCES t_execution_plan_version(id) ON DELETE RESTRICT;
ALTER TABLE t_result_analysis
    ADD CONSTRAINT fk_analysis_current_version FOREIGN KEY (current_version_id) REFERENCES t_result_analysis_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_analysis_published_version FOREIGN KEY (published_version_id) REFERENCES t_result_analysis_version(id) ON DELETE RESTRICT;
ALTER TABLE t_defect
    ADD CONSTRAINT fk_defect_current_version FOREIGN KEY (current_version_id) REFERENCES t_defect_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_defect_approved_version FOREIGN KEY (approved_version_id) REFERENCES t_defect_version(id) ON DELETE RESTRICT;
ALTER TABLE t_test_report
    ADD CONSTRAINT fk_report_current_version FOREIGN KEY (current_version_id) REFERENCES t_test_report_version(id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_report_published_version FOREIGN KEY (published_version_id) REFERENCES t_test_report_version(id) ON DELETE RESTRICT;
```

应用服务还必须校验指针版本属于同一聚合根、tenant和workspace；普通FK无法表达该跨列约束。

## 13. RLS、只追加权限与索引基线

### 13.1 租户上下文

每个事务开始后、任何查询之前，以参数化方式执行：

```sql
SELECT set_config('app.current_tenant_id', :tenant_id, true);
SELECT set_config('app.current_user_id', :user_id, true);
```

缺失/非法UUID必须在应用层和DB策略两侧fail-closed。禁止信任客户端自行传入的`X-Tenant-ID`。

### 13.2 RLS模板

除`t_tenant`、全局内置Skill/Agent/Permission等特殊表外，所有带`tenant_id`的表执行：

```sql
ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table_name> FORCE ROW LEVEL SECURITY;

CREATE POLICY <table_name>_tenant_isolation ON <table_name>
USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);
```

允许`tenant_id IS NULL`的全局Skill、Agent、Workflow、Eval和RoleDefinition行只能由`qf_owner`迁移/种子写入；运行期应用角色不能创建或修改全局行。具体迁移实现见38号文档。

### 13.3 只追加表

```sql
REVOKE UPDATE, DELETE ON
    t_audit_log,
    t_authorization_decision,
    t_work_item_event,
    t_automation_check_run,
    t_execution_result,
    t_execution_artifact,
    t_api_observation,
    t_contract_check_result,
    t_defect_status_event,
    t_defect_sync_attempt,
    t_agent_session,
    t_agent_trace_node,
    t_skill_invocation,
    t_eval_run,
    t_eval_result
FROM qf_app_user;
```

正式version表的正文列同样不得UPDATE；应用层只允许INSERT新版本和更新稳定根指针。实现可通过列级REVOKE或触发器进一步强制。

### 13.4 必需索引

除各表UNIQUE索引外，至少建立：

```sql
CREATE INDEX idx_work_item_board ON t_work_item(workspace_id, status, assignee_id, due_at);
CREATE INDEX idx_review_inbox ON t_review_task(workspace_id, status, expires_at);
CREATE INDEX idx_review_assignment_user ON t_review_assignment(assignee_id, status, assigned_at);
CREATE INDEX idx_requirement_versions ON t_requirement_document_version(requirement_document_id, version DESC);
CREATE INDEX idx_api_contract_versions ON t_api_contract_version(api_contract_id, version DESC);
CREATE INDEX idx_api_operation_lookup ON t_api_operation_version(api_contract_version_id, method, normalized_path);
CREATE INDEX idx_test_plan_release ON t_test_plan(workspace_id, release_id, lifecycle_status);
CREATE INDEX idx_test_case_status ON t_test_case(workspace_id, status);
CREATE INDEX idx_script_versions ON t_automation_script_version(automation_script_id, version DESC);
CREATE INDEX idx_execution_task_status ON t_execution_task(workspace_id, status, created_at);
CREATE INDEX idx_execution_result_task ON t_execution_result(execution_task_id, status);
CREATE INDEX idx_failure_analysis_result ON t_failure_analysis(execution_result_id, analysis_version DESC);
CREATE INDEX idx_defect_release_status ON t_defect(workspace_id, release_id, lifecycle_status);
CREATE INDEX idx_sync_attempt_status ON t_defect_sync_attempt(workspace_id, status, created_at);
CREATE INDEX idx_agent_session_work_item ON t_agent_session(work_item_run_id, started_at);
```

向量、JSONB和全文索引在有真实查询与数据规模证据后建立；不预设所有JSONB均需GIN。

## 14. 退场表与迁移结论

| 旧表/设计                                 | 目标                                                  |
| ----------------------------------------- | ----------------------------------------------------- |
| `t_test_design_plan`                      | `t_test_strategy` + `t_test_strategy_version`         |
| `t_ai_context`                            | `t_ai_context_snapshot`，Prompt/模型拆至Agent/平台表  |
| 单行Endpoint `t_api_contract`             | 稳定`t_api_contract` + version + operation + baseline |
| `t_baseline_item`                         | API/Visual/Performance专属基线表                      |
| `t_automation_script.test_case_id UNIQUE` | version-case binding多对多表                          |
| `t_failure_cluster.jira_issue_key`        | `t_external_defect_link`                              |
| `t_failure_analysis.manual_verified`      | `t_review_task` + `t_review_assignment`               |
| `t_user.role`                             | RoleDefinition/Permission/RoleBinding                 |

当前无生产数据，Gate D采用目标DDL直接替换旧设计；不编写虚构的数据迁移成功声明。38号文档负责迁移批次、种子和回滚约定。
