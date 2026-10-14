from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "review_source_dependencies.py"
VALIDATOR = (
    Path(__file__).parents[1] / "scripts" / "validate_source_dependency_review.py"
)

DOC = """# 系统功能设计

## 模块A

### 页面B

初始内容。

## 模块C

根据【模块A/页面B】中的配置读取默认值。

根据【模块A/不存在D】中的配置读取系数。

根据“模块C/缺失E/深层F”的规则执行校验。

【业务规则】
1、段落排版标记不构成引用。

导出模板见《附件Z.xlsx》。
"""


class SourceDependencyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.doc = base / "doc.md"
        self.out = base / "review.json"
        self.doc.write_text(DOC, encoding="utf-8")
        subprocess.run(
            ["python3", str(SCRIPT), "--source", str(self.doc), "--out", str(self.out)],
            check=True,
        )
        self.review = json.loads(self.out.read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_resolvable_path_reference_is_available(self) -> None:
        dependency = next(
            item
            for item in self.review["dependencies"]
            if item["target_name"] == "模块A/页面B"
        )
        self.assertEqual(dependency["status"], "available")
        self.assertEqual(dependency["target_locator"], "L5")

    def test_dangling_segment_is_review_required_with_reason(self) -> None:
        dependency = next(
            item
            for item in self.review["dependencies"]
            if item["target_name"] == "模块A/不存在D"
        )
        self.assertEqual(dependency["status"], "review_required")
        self.assertIn("不存在D", dependency["reason"])

    def test_quoted_path_with_missing_middle_segment_reports_first_gap(self) -> None:
        dependency = next(
            item
            for item in self.review["dependencies"]
            if item["target_name"] == "模块C/缺失E/深层F"
        )
        self.assertEqual(dependency["status"], "review_required")
        self.assertIn("缺失E", dependency["reason"])

    def test_plain_bracket_label_without_separator_is_not_a_dependency(self) -> None:
        self.assertFalse(
            any(
                item["target_name"] == "业务规则"
                for item in self.review["dependencies"]
            )
        )

    def test_dangling_path_produces_unresolved_internal_reference_finding(self) -> None:
        codes = [item["code"] for item in self.review["findings"]]
        self.assertIn("UNRESOLVED_INTERNAL_REFERENCE", codes)
        finding = next(
            item
            for item in self.review["findings"]
            if item["code"] == "UNRESOLVED_INTERNAL_REFERENCE"
        )
        self.assertEqual(finding["severity"], "REVIEW")

    def test_output_still_passes_validator(self) -> None:
        result = subprocess.run(
            [
                "python3",
                str(VALIDATOR),
                "--review",
                str(self.out),
                "--source",
                str(self.doc),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
