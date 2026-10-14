from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "review_source_dependencies.py"
VALIDATOR = Path(__file__).parents[1] / "scripts" / "validate_source_dependency_review.py"
BUILD_REVIEW = Path(__file__).parents[1] / "scripts" / "build_review_draft.py"
VALIDATE_REVIEW = Path(__file__).parents[1] / "scripts" / "validate_review.py"
MAPPING_PIPELINE = Path(__file__).parents[2] / "requirement-function-mapping" / "scripts" / "run_pipeline.py"
APPLY_REVIEW = Path(__file__).parents[2] / "requirement-function-mapping" / "scripts" / "apply_review_to_mapping.py"
ANALYZE_GAPS = Path(__file__).parents[1] / "scripts" / "analyze_mapping_gaps.py"


FIXTURE = """# 功能需求

## 信息查询

### 基础产品

#### 网页端

展示查询结果。

#### 接口端

响应参数同网页端一致。
其他校验规则同当前一致。

## 导出管理

页面操作如下：

<table><tr><th>类型</th><th>字段</th><th>字段描述</th></tr>
<tr><td>按钮</td><td>查询</td><td>根据筛选条件查询导出任务</td></tr>
<tr><td>按钮</td><td>导出</td><td>按模板生成导出文件</td></tr></table>

导出格式见《导出模板.xlsx》。
批量导出仍使用《导出模板.xlsx》。
"""


class SourceDependencyReviewTests(unittest.TestCase):
    def run_review(self, include_attachment: bool) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, output = base / "requirement.md", base / "review.json"
            source.write_text(FIXTURE, encoding="utf-8")
            command = ["python3", str(SCRIPT), "--source", str(source), "--out", str(output)]
            if include_attachment:
                attachment = base / "导出模板.xlsx"
                attachment.write_bytes(b"fixture")
                command.extend(["--provided-source", str(attachment)])
            subprocess.run(command, check=True)
            subprocess.run(["python3", str(VALIDATOR), "--review", str(output), "--source", str(source)], check=True)
            return json.loads(output.read_text(encoding="utf-8"))

    def test_missing_materials_are_review_findings_not_mapping_guesses(self) -> None:
        data = self.run_review(False)
        self.assertEqual(data["meta"]["artifact_kind"], "requirement_source_dependency_review")
        self.assertEqual(data["summary"]["occurrence_count"], 4)
        self.assertEqual(data["summary"]["distinct_target_count"], 3)
        self.assertEqual(data["summary"]["by_status"], {"available": 1, "review_required": 0, "missing": 3})
        self.assertEqual(len(data["findings"]), 2)
        template_finding = next(item for item in data["findings"] if item["code"] == "MISSING_REFERENCED_ARTIFACT")
        self.assertEqual(len(template_finding["dependency_ids"]), 2)

    def test_explicitly_provided_material_resolves_only_its_dependency(self) -> None:
        data = self.run_review(True)
        template_dependencies = [item for item in data["dependencies"] if item["target_name"] == "导出模板.xlsx"]
        self.assertTrue(all(item["status"] == "available" for item in template_dependencies))
        self.assertEqual([item["code"] for item in data["findings"]], ["MISSING_EXISTING_BASELINE"])

    def test_source_findings_round_trip_through_mapping_into_full_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "requirement.md"
            source_review = base / "source-review.json"
            mapping_dir = base / "mapping"
            full_review = base / "full-review.json"
            analyzed_review = base / "analyzed-review.json"
            projected = base / "projected.json"
            source.write_text(FIXTURE, encoding="utf-8")
            subprocess.run(["python3", str(SCRIPT), "--source", str(source), "--out", str(source_review)], check=True)
            subprocess.run(["python3", str(MAPPING_PIPELINE), "--source", str(source), "--source-review", str(source_review),
                            "--out-dir", str(mapping_dir), "--through-stage", "finalize"], check=True)
            mapping = mapping_dir / "requirement_mapping.json"
            subprocess.run(["python3", str(BUILD_REVIEW), "--source", str(source), "--mapping", str(mapping), "--out", str(full_review)], check=True)
            validation = subprocess.run(["python3", str(VALIDATE_REVIEW), "--review", str(full_review), "--source", str(source)],
                                        check=False, capture_output=True, text=True)
            subprocess.run(["python3", str(ANALYZE_GAPS), "--review", str(full_review), "--mapping", str(mapping), "--out", str(analyzed_review)], check=True)
            subprocess.run(["python3", str(APPLY_REVIEW), "--mapping", str(mapping), "--review", str(full_review), "--out", str(projected)], check=True)
            data = json.loads(full_review.read_text(encoding="utf-8"))
            analyzed_data = json.loads(analyzed_review.read_text(encoding="utf-8"))
            projected_data = json.loads(projected.read_text(encoding="utf-8"))
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertEqual({item["code"] for item in data["findings"]}, {"MISSING_REFERENCED_ARTIFACT", "MISSING_EXISTING_BASELINE"})
        self.assertTrue(all(item["requirement_ids"] for item in data["findings"]))
        self.assertTrue(any(item["disposition"] == "finding" for item in data["source_unit_dispositions"]))
        self.assertTrue({item["finding_id"] for item in data["findings"]}.issubset({item["finding_id"] for item in analyzed_data["findings"]}))
        self.assertTrue(any(item.get("quality_review", {}).get("open_finding_ids") for item in projected_data["atomic_functions"]))
        template_finding = next(item for item in data["findings"] if item["code"] == "MISSING_REFERENCED_ARTIFACT")
        requirements_by_id = {item["requirement_id"]: item for item in data["requirements"]}
        affected_atomic_ids = {
            atomic_id
            for requirement_id in template_finding["requirement_ids"]
            for atomic_id in requirements_by_id[requirement_id].get("atomic_refs", [])
        }
        atomic_names = {
            item["atomic_id"]: item["name"]
            for item in projected_data["atomic_functions"]
        }
        self.assertEqual({atomic_names[atomic_id] for atomic_id in affected_atomic_ids}, {"导出"})


if __name__ == "__main__":
    unittest.main()
