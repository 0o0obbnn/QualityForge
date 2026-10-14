from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENRICHER = ROOT / "scripts" / "enrich_graph_model.py"


class GraphEnrichmentTests(unittest.TestCase):
    def test_materializes_typed_nodes_rules_and_edges(self) -> None:
        proof = {"source_id": "SRC-1", "locator": "L1", "quote": "按时间倒序展示"}
        mapping = {
            "meta": {"schema_version": "1.3"},
            "sources": [{"source_id": "SRC-1"}],
            "modules": [{"module_id": "MOD-1", "name": "上报"}],
            "functions": [{"function_id": "FUN-1", "name": "任务记录", "module_id": "MOD-1", "evidence": [proof]}],
            "atomic_functions": [{"atomic_id": "AF-1", "function_id": "FUN-1", "processing_rules": ["按时间倒序展示"], "evidence": [proof], "status": "confirmed"}],
            "business_fields": [{"field_id": "FLD-1", "business_name": "处理状态", "business_object": "任务记录", "enum_values": ["处理中", "已完成"], "rules": ["最大50字符"], "evidence": [proof], "status": "confirmed", "attribute_provenance": {"business_object": "explicit"}}],
            "field_bindings": [{"atomic_id": "AF-1", "field_id": "FLD-1", "usages": ["display"], "direction": "read", "rules": ["按时间倒序展示"], "evidence": [proof]}],
            "relations": [], "coverage": {},
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, markdown, first, second = base / "mapping.json", base / "requirement.md", base / "first.json", base / "second.json"
            source.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            markdown.write_text("先点击查询，然后显示按时间倒序排列的结果", encoding="utf-8")
            subprocess.run(["python3", str(ENRICHER), "--mapping", str(source), "--source", str(markdown), "--out", str(first)], check=True)
            subprocess.run(["python3", str(ENRICHER), "--mapping", str(first), "--out", str(second)], check=True)
            enriched = json.loads(first.read_text(encoding="utf-8"))
            rerun = json.loads(second.read_text(encoding="utf-8"))
            self.assertEqual(enriched["meta"]["artifact_kind"], "typed_requirement_graph")
            self.assertEqual(enriched["meta"]["schema_version"], "1.4")
            self.assertEqual(len(enriched["business_objects"]), 1)
            self.assertEqual(len(enriched["field_usages"]), 1)
            self.assertEqual(len(enriched["states"]), 2)
            self.assertEqual(len(enriched["business_flow_candidates"]), 1)
            self.assertTrue(any(rule["category"] == "sorting" for rule in enriched["business_rules"]))
            relation_types = {item["type"] for item in enriched["relations"]}
            self.assertTrue({"contains", "uses_field", "field_of", "constrained_by", "has_state"}.issubset(relation_types))
            self.assertEqual(
                {item["rule_id"] for item in enriched["business_rules"]},
                {item["rule_id"] for item in rerun["business_rules"]},
            )

    def test_materializes_explicit_cross_function_state_flow(self) -> None:
        mapping = {
            "meta": {"schema_version": "1.3"}, "sources": [{"source_id": "SRC-1"}],
            "functions": [
                {"function_id": "FUN-ROLE", "name": "角色管理", "evidence": [{"source_id": "SRC-1", "locator": "L1", "quote": "角色管理"}]},
                {"function_id": "FUN-PAGE", "name": "页面管理", "evidence": [{"source_id": "SRC-1", "locator": "L3", "quote": "页面管理"}]},
            ],
            "atomic_functions": [], "business_fields": [], "field_bindings": [], "relations": [], "coverage": {},
        }
        markdown = "# 功能\n\n## 页面管理\n【角色管理】下线角色后，【接入服务/页面管理】同步停用对应角色。\n"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, requirement, output = base / "mapping.json", base / "requirement.md", base / "output.json"
            source.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            requirement.write_text(markdown, encoding="utf-8")
            subprocess.run(["python3", str(ENRICHER), "--mapping", str(source), "--source", str(requirement), "--out", str(output)], check=True)
            enriched = json.loads(output.read_text(encoding="utf-8"))
        relation = next(item for item in enriched["relations"] if item["type"] == "state_flow")
        self.assertEqual((relation["source_id"], relation["target_id"]), ("FUN-ROLE", "FUN-PAGE"))
        self.assertEqual(relation["evidence"][0]["locator"], "L4")


if __name__ == "__main__":
    unittest.main()
