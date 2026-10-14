from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "extract_markdown_full_draft.py"

DOC = """# 需求标题

## 模块甲

### 页面乙

【业务规则】

1、每月1号，系统自动生成本月的核对任务并写入任务表。

2、每日汇总机构用量并更新配额字段。

3、点击导出按钮后将列表数据导出至Excel文件中下载至本地。

4、次日中午，平台自动停用超额机构的服务状态。

## 非功能需求

系统应每日统计全平台指标。
"""


class SystemJobCandidateTests(unittest.TestCase):
    def test_extract_produces_system_job_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "doc.md"
            out = Path(directory) / "draft.json"
            source.write_text(DOC, encoding="utf-8")
            subprocess.run(
                ["python3", str(SCRIPT), "--source", str(source), "--out", str(out)],
                check=True,
            )
            draft = json.loads(out.read_text(encoding="utf-8"))
            jobs = [
                item
                for item in draft["atomic_functions"]
                if item.get("category") == "system_job"
            ]
            names = {item["name"] for item in jobs}
            self.assertTrue(any("生成" in name for name in names), names)
            self.assertTrue(any("停用" in name for name in names), names)
            for item in jobs:
                self.assertEqual(item["status"], "inferred")
                self.assertEqual(item["origin"], "prose_system_job")
                self.assertTrue(item["evidence"])

    def test_interaction_sentence_is_not_promoted_to_system_job(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "doc.md"
            out = Path(directory) / "draft.json"
            source.write_text(DOC, encoding="utf-8")
            subprocess.run(
                ["python3", str(SCRIPT), "--source", str(source), "--out", str(out)],
                check=True,
            )
            draft = json.loads(out.read_text(encoding="utf-8"))
            jobs = [
                item
                for item in draft["atomic_functions"]
                if item.get("category") == "system_job"
            ]
            self.assertFalse(any("导出" in item["name"] for item in jobs))

    def test_nfr_section_is_excluded_from_system_job_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "doc.md"
            out = Path(directory) / "draft.json"
            source.write_text(DOC, encoding="utf-8")
            subprocess.run(
                ["python3", str(SCRIPT), "--source", str(source), "--out", str(out)],
                check=True,
            )
            draft = json.loads(out.read_text(encoding="utf-8"))
            jobs = [
                item
                for item in draft["atomic_functions"]
                if item.get("category") == "system_job"
            ]
            self.assertFalse(any("统计" in item["name"] for item in jobs))


if __name__ == "__main__":
    unittest.main()
