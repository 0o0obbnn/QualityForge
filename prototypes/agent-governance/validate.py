#!/usr/bin/env python3
"""Validate the minimal Agent/Skill governance prototype with stdlib only."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXPECTED_GATE0_SKILLS = {
    "plan-orchestrator",
    "requirement-quality-gate",
    "requirement-compiler",
    "business-rule-extractor",
    "domain-model-extractor",
    "state-machine-builder",
    "ir-validator",
    "strategy-planner",
    "scenario-generator",
    "test-case-generator",
    "assertion-generator",
    "assertion-verifier",
    "coverage-analyzer",
    "hitl-gatekeeper",
}
EXPECTED_EXECUTION_SKILLS = {
    "fixture-dag-planner",
    "test-data-generator",
    "self-healing-orchestrator",
    "hitl-gatekeeper",
}


def load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def validate() -> None:
    registry = load("agents.json")
    workflow = load("gate0-workflow.json")
    platform_review = load("platform-review-agent.json")
    platform_workflow = load("platform-review-workflow.json")
    agents = registry["agents"]
    by_id = {agent["id"]: agent for agent in agents}
    assert len(by_id) == len(agents), "duplicate agent id"
    assert registry["policyDefaults"]["network"]["mode"] == "deny_all"
    assert registry["policyDefaults"]["secrets"]["allowedKeys"] == []
    assert registry["policyDefaults"]["externalWrites"] == "deny"
    assert registry["policyDefaults"]["canonicalAssetWrites"] == "deny"
    assert registry["policyDefaults"]["defaultAutonomyLevel"] == "L2"
    human_only = set(registry["policyDefaults"]["humanOnlyActions"])
    assert "approve_formal_artifact" in human_only
    assert "approve_external_write" in human_only

    supervisors = [agent for agent in agents if agent["kind"] == "supervisor"]
    assert len(supervisors) == 1, "exactly one supervisor is required"
    for agent in agents:
        assert not agent["humanApprovalAuthority"], "AI must not own human approval"
        if agent["kind"] == "subagent":
            assert agent["mayDelegateTo"] == [], "subagent delegation is forbidden"
        for skill in agent["allowedSkills"]:
            assert (ROOT / "prototypes" / "skills" / skill / "SKILL.md").is_file(), (
                f"unknown skill {skill!r}"
            )

    preflight = workflow["preflight"]
    assert preflight["validatorId"] == "governance-structure-validator"
    assert preflight["requiredVerdict"] == "PASS"
    auth = workflow["authorizationPolicy"]
    assert auth["mode"] == "intersection_fail_closed"
    assert "approve_formal_artifact" in auth["humanOnlyActions"]
    artifact_policy = workflow["artifactPolicy"]
    assert artifact_policy["immutableOutputs"] is True
    assert set(artifact_policy["requiredReviewBinding"]) == {
        "artifactType",
        "artifactId",
        "artifactVersionId",
        "contentDigest",
    }
    assert set(artifact_policy["formalArtifactTypes"]) == {
        "TEST_STRATEGY",
        "TEST_PLAN",
        "TEST_CASE",
    }

    nodes = workflow["nodes"]
    node_by_id = {node["id"]: node for node in nodes}
    assert len(node_by_id) == len(nodes), "duplicate workflow node id"
    used_skills = set()
    indegree = {node_id: 0 for node_id in node_by_id}
    outgoing = {node_id: [] for node_id in node_by_id}
    for node in nodes:
        agent = by_id[node["agentId"]]
        assert node["skillId"] in agent["allowedSkills"], (
            f"{node['agentId']} is not allowed to call {node['skillId']}"
        )
        used_skills.add(node["skillId"])
        assert node["output"].startswith("prototypes/agent-governance/runs/{runId}/")
        for dependency in node["dependsOn"]:
            assert dependency in node_by_id, f"unknown dependency {dependency!r}"
            indegree[node["id"]] += 1
            outgoing[dependency].append(node["id"])

    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        current = queue.popleft()
        visited += 1
        for target in outgoing[current]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    assert visited == len(nodes), "workflow must be a DAG"
    assert used_skills == EXPECTED_GATE0_SKILLS, "Gate 0 skill set drifted"
    human_gate = node_by_id["human_gate"]
    assert human_gate["requiredVerdict"] == "BLOCK_HUMAN"
    assert set(human_gate["createsReviewTasksFor"]) == set(
        artifact_policy["formalArtifactTypes"]
    )

    # M3：执行工作流与 Gate 0 同构校验（allowedSkills+DAG，fail-closed）
    execution_workflow = load("execution-workflow.json")
    exec_auth = execution_workflow["authorizationPolicy"]
    assert exec_auth["mode"] == "intersection_fail_closed"
    assert "approve_execution_evidence" in exec_auth["humanOnlyActions"]
    exec_artifact_policy = execution_workflow["artifactPolicy"]
    assert exec_artifact_policy["immutableOutputs"] is True
    assert set(exec_artifact_policy["requiredReviewBinding"]) == {
        "artifactType",
        "artifactId",
        "artifactVersionId",
        "contentDigest",
    }
    assert set(exec_artifact_policy["formalArtifactTypes"]) == {"EXECUTION_EVIDENCE"}

    exec_nodes = execution_workflow["nodes"]
    exec_node_by_id = {node["id"]: node for node in exec_nodes}
    assert len(exec_node_by_id) == len(exec_nodes), (
        "duplicate execution workflow node id"
    )
    exec_used_skills: set[str] = set()
    exec_indegree = {node_id: 0 for node_id in exec_node_by_id}
    exec_outgoing: dict[str, list[str]] = {node_id: [] for node_id in exec_node_by_id}
    for node in exec_nodes:
        agent = by_id[node["agentId"]]
        assert node["skillId"] in agent["allowedSkills"], (
            f"{node['agentId']} is not allowed to call {node['skillId']}"
        )
        exec_used_skills.add(node["skillId"])
        assert node["output"].startswith("prototypes/agent-governance/runs/{runId}/")
        for dependency in node["dependsOn"]:
            assert dependency in exec_node_by_id, f"unknown dependency {dependency!r}"
            exec_indegree[node["id"]] += 1
            exec_outgoing[dependency].append(node["id"])
    exec_queue = deque(
        node_id for node_id, degree in exec_indegree.items() if degree == 0
    )
    exec_visited = 0
    while exec_queue:
        current = exec_queue.popleft()
        exec_visited += 1
        for target in exec_outgoing[current]:
            exec_indegree[target] -= 1
            if exec_indegree[target] == 0:
                exec_queue.append(target)
    assert exec_visited == len(exec_nodes), "execution workflow must be a DAG"
    assert exec_used_skills == EXPECTED_EXECUTION_SKILLS, "execution skill set drifted"
    evidence_gate = exec_node_by_id["evidence_gate"]
    assert evidence_gate["requiredVerdict"] == "BLOCK_HUMAN"
    assert set(evidence_gate["createsReviewTasksFor"]) == set(
        exec_artifact_policy["formalArtifactTypes"]
    )
    runner = by_id["qf-execution"]
    assert runner["kind"] == "subagent"
    assert "modify_test_or_evidence" in runner["deniedActions"], (
        "execution runner must not modify evidence"
    )
    assert not runner["humanApprovalAuthority"]

    reviewer = platform_review["agent"]
    assert reviewer["id"] not in by_id, "platform reviewer must remain outside Gate 0"
    assert reviewer["kind"] == "independent_reviewer"
    assert reviewer["governanceDomain"] == "platform_assurance"
    assert reviewer["mayBeDelegatedBy"] == []
    assert reviewer["mayDelegateTo"] == []
    assert not reviewer["humanApprovalAuthority"]
    reviewer_denies = set(reviewer["deniedActions"])
    assert {
        "accept_production_assignment",
        "repair_reviewed_asset",
        "modify_canonical_asset",
        "modify_source_code",
        "modify_test_or_evidence",
        "approve_review_finding",
        "close_review_finding",
        "write_external_system",
    } <= reviewer_denies
    independence = platform_review["independencePolicy"]
    assert independence["notMemberOfGate0Workflow"] is True
    assert independence["productionAgentsCannotInvoke"] is True
    assert independence["reviewerMustNotHaveProducedSnapshot"] is True
    permissions = platform_review["permissions"]
    assert permissions["network"]["mode"] == "deny_all"
    assert permissions["secrets"]["allowedKeys"] == []
    assert permissions["externalWrites"] == "deny"
    assert permissions["canonicalAssetWrites"] == "deny"
    assert permissions["filesystem"]["write"] == [
        "prototypes/agent-governance/platform-review-runs/{reviewRunId}/**"
    ]
    for skill in reviewer["allowedSkills"]:
        assert (ROOT / "prototypes" / "skills" / skill / "SKILL.md").is_file(), (
            f"unknown platform-review skill {skill!r}"
        )
    review_contract = platform_review["reviewContract"]
    assert review_contract["inputMustBeFrozen"] is True
    assert review_contract["reportIsAdvisoryOnly"] is True
    assert review_contract["humanMustConfirmDisposition"] is True
    assert set(review_contract["evidenceClasses"]) == {
        "CONFIRMED",
        "INFERRED",
        "UNRESOLVED",
    }
    assert len(review_contract["dimensions"]) == 9
    assert platform_workflow["agentId"] == reviewer["id"]
    review_nodes = platform_workflow["nodes"]
    review_node_ids = {node["id"] for node in review_nodes}
    assert len(review_node_ids) == len(review_nodes), (
        "duplicate platform-review node id"
    )
    review_indegree = {node_id: 0 for node_id in review_node_ids}
    review_outgoing = {node_id: [] for node_id in review_node_ids}
    for node in review_nodes:
        assert set(node["dependsOn"]) <= review_node_ids
        for dependency in node["dependsOn"]:
            review_indegree[node["id"]] += 1
            review_outgoing[dependency].append(node["id"])
    review_queue = deque(
        node_id for node_id, degree in review_indegree.items() if degree == 0
    )
    review_visited = 0
    while review_queue:
        current = review_queue.popleft()
        review_visited += 1
        for target in review_outgoing[current]:
            review_indegree[target] -= 1
            if review_indegree[target] == 0:
                review_queue.append(target)
    assert review_visited == len(review_nodes), "platform-review workflow must be a DAG"
    disposition = next(
        node for node in review_nodes if node["id"] == "human_disposition"
    )
    assert disposition["checkType"] == "human_checkpoint"
    assert disposition["requiredActorType"] == "UserIdentity"
    assert disposition["agentMayDecide"] is False

    all_skills = list((ROOT / "prototypes" / "skills").glob("*/SKILL.md"))
    evals = list((ROOT / "prototypes" / "skills").glob("*/evals/evals.json"))
    # 32 个阶段门 skill + 1 个路由元 skill（using-qualityforge，只索引不产出门禁结果）
    assert len(all_skills) == 33, f"expected 33 skills, found {len(all_skills)}"
    assert len(evals) == 33, f"expected 33 standard eval suites, found {len(evals)}"
    print(
        "PASS: 5 agents, 14 Gate 0 skills + 4 execution skills, acyclic workflows, "
        "deny-all network, no secrets, human-only formal approval, "
        "immutable review bindings, immutable execution evidence; "
        "1 external platform reviewer isolated, "
        "read-only, no delegation, advisory-only, human disposition; "
        f"project inventory={len(all_skills)} skills/{len(evals)} eval suites"
    )


if __name__ == "__main__":
    validate()
