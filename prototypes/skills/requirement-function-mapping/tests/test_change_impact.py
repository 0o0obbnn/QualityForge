from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARATOR = ROOT / "scripts" / "compare_mapping_versions.py"


class ChangeImpactTests(unittest.TestCase):
    def test_rule_change_reaches_bound_atomic_and_parent_function(self) -> None:
        before = {
            "meta": {"graph_snapshot_id": "GRAPH-A"},
            "modules": [{"module_id": "MOD-1", "name": "上报"}],
            "functions": [{"function_id": "FUN-1", "name": "任务记录", "module_id": "MOD-1", "module": "上报", "status": "confirmed"}],
            "atomic_functions": [{"atomic_id": "AF-1", "function_id": "FUN-1", "name": "查询", "action": "查询", "status": "confirmed"}],
            "business_fields": [{"field_id": "FLD-1", "business_name": "页大小", "business_object": "任务记录", "rules": ["最大50"], "status": "confirmed"}],
            "field_bindings": [{"atomic_id": "AF-1", "field_id": "FLD-1", "usages": ["query"], "direction": "read"}],
            "relations": [{"relation_id": "REL-1", "source_id": "MOD-1", "target_id": "FUN-1", "type": "contains"}],
        }
        after = json.loads(json.dumps(before))
        after["meta"]["graph_snapshot_id"] = "GRAPH-B"
        after["business_fields"][0]["rules"] = ["最大100"]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before_path, after_path, out_path = base / "before.json", base / "after.json", base / "impact.json"
            before_path.write_text(json.dumps(before, ensure_ascii=False), encoding="utf-8")
            after_path.write_text(json.dumps(after, ensure_ascii=False), encoding="utf-8")
            subprocess.run(["python3", str(COMPARATOR), "--before", str(before_path), "--after", str(after_path), "--out", str(out_path)], check=True)
            report = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["by_change_type"]["MODIFIED"], 1)
            impacted = {item["entity_id"]: item for item in report["impact"]["nodes"]}
            self.assertEqual(impacted["AF-1"]["distance"], 1)
            self.assertEqual(impacted["FUN-1"]["distance"], 2)

    def test_module_reassignment_is_moved_not_delete_add(self) -> None:
        before = {"meta": {}, "modules": [], "functions": [{"function_id": "FUN-1", "name": "查询", "module": "A", "module_id": "MOD-A"}], "atomic_functions": [], "business_fields": [], "field_bindings": [], "relations": []}
        after = json.loads(json.dumps(before))
        after["functions"][0].update({"module": "B", "module_id": "MOD-B"})
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before_path, after_path, out_path = base / "before.json", base / "after.json", base / "impact.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")
            subprocess.run(["python3", str(COMPARATOR), "--before", str(before_path), "--after", str(after_path), "--out", str(out_path)], check=True)
            report = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(report["changes"][0]["change_type"], "MOVED")
            self.assertEqual(report["summary"]["by_change_type"]["ADDED"], 0)
            self.assertEqual(report["summary"]["by_change_type"]["DELETED"], 0)

    def test_rule_change_reaches_verifying_test_case(self) -> None:
        before = {
            "meta": {"graph_snapshot_id": "GRAPH-A"}, "modules": [], "functions": [],
            "atomic_functions": [], "business_fields": [], "field_bindings": [],
            "business_rules": [{"rule_id": "RULE-1", "statement": "最多50条"}],
            "test_cases": [{"case_id": "TC-1", "title": "验证分页上限", "status": "ACTIVE"}],
            "relations": [{"relation_id": "REL-V", "source_id": "TC-1", "target_id": "RULE-1", "type": "verifies"}],
        }
        after = json.loads(json.dumps(before))
        after["meta"]["graph_snapshot_id"] = "GRAPH-B"
        after["business_rules"][0]["statement"] = "最多100条"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before_path, after_path, out_path = base / "before.json", base / "after.json", base / "impact.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")
            subprocess.run(["python3", str(COMPARATOR), "--before", str(before_path), "--after", str(after_path), "--out", str(out_path)], check=True)
            report = json.loads(out_path.read_text(encoding="utf-8"))
            impacted = {item["entity_id"]: item for item in report["impact"]["nodes"]}
            self.assertEqual(impacted["TC-1"]["distance"], 1)
            self.assertEqual(impacted["TC-1"]["via"], "verifies")

    def test_cycle_respects_max_depth_and_keeps_shortest_path(self) -> None:
        before = {
            "meta": {}, "modules": [], "functions": [],
            "atomic_functions": [{"atomic_id": "AF-1", "name": "查询", "action": "查询"}],
            "business_fields": [
                {"field_id": "FLD-1", "business_name": "A"},
                {"field_id": "FLD-2", "business_name": "B"},
            ],
            "field_bindings": [],
            "relations": [
                {"relation_id": "R1", "source_id": "AF-1", "target_id": "FLD-1", "type": "data_flow"},
                {"relation_id": "R2", "source_id": "FLD-1", "target_id": "FLD-2", "type": "data_flow"},
                {"relation_id": "R3", "source_id": "FLD-2", "target_id": "AF-1", "type": "data_flow"},
            ],
        }
        after = json.loads(json.dumps(before))
        after["atomic_functions"][0]["action"] = "条件查询"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            before_path, after_path, out_path = base / "before.json", base / "after.json", base / "impact.json"
            before_path.write_text(json.dumps(before), encoding="utf-8")
            after_path.write_text(json.dumps(after), encoding="utf-8")
            subprocess.run(["python3", str(COMPARATOR), "--before", str(before_path), "--after", str(after_path), "--max-depth", "1", "--out", str(out_path)], check=True)
            report = json.loads(out_path.read_text(encoding="utf-8"))
            impacted = {item["entity_id"]: item for item in report["impact"]["nodes"]}
            self.assertEqual(set(impacted), {"FLD-1", "FLD-2"})
            self.assertTrue(all(item["distance"] == 1 for item in impacted.values()))


if __name__ == "__main__":
    unittest.main()
