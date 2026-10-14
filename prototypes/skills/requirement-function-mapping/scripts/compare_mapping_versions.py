#!/usr/bin/env python3
"""Compare two graph snapshots and calculate bounded dependency impact."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from typing import Any


ENTITY_SPECS = {
    "module": ("modules", "module_id", {"name", "parent_module_id"}, {"parent_module_id"}),
    "function": ("functions", "function_id", {"name", "module_id", "module", "actors", "business_goal", "preconditions", "outcomes", "dependencies", "status"}, {"module_id", "module"}),
    "atomic_function": ("atomic_functions", "atomic_id", {"function_id", "name", "category", "action", "actor", "trigger", "preconditions", "inputs", "processing_rules", "outputs", "state_changes", "branches", "status"}, {"function_id"}),
    "business_field": ("business_fields", "field_id", {"business_name", "technical_name", "business_object", "data_type", "format", "length", "precision", "required", "default_value", "enum_values", "rules", "status"}, {"business_object"}),
    "business_object": ("business_objects", "object_id", {"name", "parent_object_id", "status"}, {"parent_object_id"}),
    "field_usage": ("field_usages", "field_usage_id", {"atomic_id", "field_id", "usages", "direction", "required_here", "condition", "rule_ids"}, {"atomic_id", "field_id"}),
    "business_rule": ("business_rules", "rule_id", {"category", "scope", "statement", "applies_to_ids", "status"}, {"applies_to_ids"}),
    "state": ("states", "state_id", {"field_id", "value", "status"}, {"field_id"}),
    "test_case": ("test_cases", "case_id", {"title", "status", "automation_mode"}, set()),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(entity: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    return {key: entity.get(key) for key in sorted(keys)}


def changed_attributes(before: dict[str, Any], after: dict[str, Any], keys: set[str]) -> list[str]:
    return sorted(key for key in keys if before.get(key) != after.get(key))


def edge_key(relation: dict[str, Any]) -> tuple[Any, Any, Any]:
    return relation.get("source_id"), relation.get("target_id"), relation.get("type")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare requirement graph versions")
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-depth", type=int, default=3)
    args = parser.parse_args()
    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    changes: list[dict[str, Any]] = []
    changed_ids: set[str] = set()

    for entity_type, (array_name, id_key, semantic_keys, move_keys) in ENTITY_SPECS.items():
        old = {item.get(id_key): item for item in before.get(array_name, []) if isinstance(item, dict) and item.get(id_key)}
        new = {item.get(id_key): item for item in after.get(array_name, []) if isinstance(item, dict) and item.get(id_key)}
        for entity_id in sorted(old.keys() - new.keys()):
            changes.append({"change_type": "DELETED", "entity_type": entity_type, "entity_id": entity_id, "before": selected(old[entity_id], semantic_keys), "after": None})
            changed_ids.add(entity_id)
        for entity_id in sorted(new.keys() - old.keys()):
            changes.append({"change_type": "ADDED", "entity_type": entity_type, "entity_id": entity_id, "before": None, "after": selected(new[entity_id], semantic_keys)})
            changed_ids.add(entity_id)
        for entity_id in sorted(old.keys() & new.keys()):
            attributes = changed_attributes(old[entity_id], new[entity_id], semantic_keys)
            if not attributes:
                continue
            change_type = "MOVED" if set(attributes).issubset(move_keys) else "MODIFIED"
            changes.append({"change_type": change_type, "entity_type": entity_type, "entity_id": entity_id,
                            "changed_attributes": attributes, "before": selected(old[entity_id], semantic_keys),
                            "after": selected(new[entity_id], semantic_keys)})
            changed_ids.add(entity_id)

    before_edges = {edge_key(item): item for item in before.get("relations", []) if isinstance(item, dict)}
    after_edges = {edge_key(item): item for item in after.get("relations", []) if isinstance(item, dict)}
    for key in sorted(before_edges.keys() ^ after_edges.keys(), key=str):
        relation = after_edges.get(key) or before_edges.get(key)
        changes.append({"change_type": "RELATION_CHANGED", "entity_type": "relation", "entity_id": relation.get("relation_id"),
                        "relation": {"source_id": key[0], "target_id": key[1], "type": key[2]},
                        "operation": "ADDED" if key in after_edges else "DELETED"})
        changed_ids.update(value for value in key[:2] if value)

    # Bindings are graph edges even though they have no relation_id.
    def binding_key(item: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
        return item.get("atomic_id"), item.get("field_id"), tuple(item.get("usages", [])), item.get("direction")
    old_bindings = {binding_key(item) for item in before.get("field_bindings", []) if isinstance(item, dict)}
    new_bindings = {binding_key(item) for item in after.get("field_bindings", []) if isinstance(item, dict)}
    for key in sorted(old_bindings ^ new_bindings, key=str):
        changes.append({"change_type": "RELATION_CHANGED", "entity_type": "field_binding",
                        "entity_id": f"{key[0]}->{key[1]}", "operation": "ADDED" if key in new_bindings else "DELETED",
                        "relation": {"source_id": key[0], "target_id": key[1], "type": "uses_field"}})
        changed_ids.update(value for value in key[:2] if value)

    adjacency: dict[str, set[tuple[str, str]]] = {}
    combined_relations = list(before_edges) + list(after_edges)
    for source_id, target_id, relation_type in combined_relations:
        if source_id and target_id:
            adjacency.setdefault(source_id, set()).add((target_id, str(relation_type)))
            adjacency.setdefault(target_id, set()).add((source_id, str(relation_type)))
    for atomic_id, field_id, _, _ in old_bindings | new_bindings:
        adjacency.setdefault(atomic_id, set()).add((field_id, "uses_field"))
        adjacency.setdefault(field_id, set()).add((atomic_id, "used_by"))
    for graph in (before, after):
        for atomic in graph.get("atomic_functions", []):
            function_id, atomic_id = atomic.get("function_id"), atomic.get("atomic_id")
            if function_id and atomic_id:
                adjacency.setdefault(function_id, set()).add((atomic_id, "contains"))
                adjacency.setdefault(atomic_id, set()).add((function_id, "contained_by"))

    impacts: dict[str, dict[str, Any]] = {}
    queue = deque((entity_id, 0, None, None) for entity_id in changed_ids)
    visited = {(entity_id, 0) for entity_id in changed_ids}
    while queue:
        entity_id, distance, from_id, via = queue.popleft()
        if distance > 0 and (entity_id not in impacts or distance < impacts[entity_id]["distance"]):
            impacts[entity_id] = {"entity_id": entity_id, "distance": distance, "from_id": from_id, "via": via}
        if distance >= args.max_depth:
            continue
        for target_id, relation_type in adjacency.get(entity_id, set()):
            state = (target_id, distance + 1)
            if state not in visited and target_id not in changed_ids:
                visited.add(state)
                queue.append((target_id, distance + 1, entity_id, relation_type))

    report = {
        "meta": {"artifact_kind": "requirement_graph_change_impact", "schema_version": "1.0"},
        "snapshots": {
            "before": {"file": args.before.name, "sha256": digest(args.before), "graph_snapshot_id": before.get("meta", {}).get("graph_snapshot_id")},
            "after": {"file": args.after.name, "sha256": digest(args.after), "graph_snapshot_id": after.get("meta", {}).get("graph_snapshot_id")},
        },
        "changes": changes,
        "impact": {"max_depth": args.max_depth, "nodes": sorted(impacts.values(), key=lambda item: (item["distance"], item["entity_id"]))},
        "summary": {
            "change_count": len(changes), "direct_changed_node_count": len(changed_ids), "impacted_node_count": len(impacts),
            "by_change_type": {kind: sum(item["change_type"] == kind for item in changes)
                               for kind in ("ADDED", "MODIFIED", "DELETED", "MOVED", "RELATION_CHANGED")},
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
