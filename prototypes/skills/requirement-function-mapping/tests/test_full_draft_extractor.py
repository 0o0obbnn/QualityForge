#!/usr/bin/env python3
"""Regression tests for generic full-draft classification and draft safety."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "scripts" / "extract_markdown_full_draft.py"
RENDERER = ROOT / "scripts" / "render_mapping_html.py"
VALIDATOR = ROOT / "scripts" / "validate_mapping.py"
SOURCE_REVIEWER = (
    ROOT.parent / "qa-requirement-review" / "scripts" / "review_source_dependencies.py"
)


FIXTURE = """# 系统功能设计

## 暂无权限

没有权限的用户看到缺省页。

## 订单管理

### 订单列表

#### 功能描述

##### 列表页

<table><tr><th>类型</th><th>字段</th><th>是否必填</th></tr>
<tr><td>筛选条件</td><td>客户编号</td><td>是</td></tr>
<tr><td>按钮</td><td>查询</td><td>-</td></tr>
<tr><td>列表</td><td>序号</td><td>否</td></tr></table>

<table><tr><th>类型</th><th>字段</th><th>是否必填</th></tr>
<tr><td>筛选条件</td><td>客户编号</td><td>是</td></tr></table>

<table><tr><th>类型</th><th>字段</th><th>字段描述</th></tr>
<tr><td>页面标题</td><td>订单列表</td><td>-</td></tr>
<tr><td rowspan="2"></td><td>是否已支付</td><td>下拉框：请选择</td></tr>
<tr><td>支付时间</td><td>日期选择器</td></tr></table>

##### 查看

①审批意见：
单选：通过、不通过，默认选择通过。

②备注：
选择不通过时备注必填，输入框失去焦点后校验。

<table><tr><th>类型</th><th>字段</th><th>是否必填</th></tr>
<tr><td>字段</td><td>订单状态</td><td>否</td></tr></table>

展示字段为：序号、订单金额。

下载记录显示字段：序号、操作人和操作时间。

修改记录包括：序号、变更内容（前值，后值）、变更人、变更时间，按照变更时间倒序排序。

汇总信息包括：汇总金额。

详情信息包括：汇总信息、明细金额。

协议约定的「生效时间」决定订单是否可执行。

<table><tr><th>字段</th><th>是否必填</th><th>描述</th></tr>
<tr><td>确定</td><td>-</td><td>点击后提交当前数据</td></tr></table>

<table><tr><th>触发条件</th><th>提示语</th></tr>
<tr><td>空</td><td>请选择订单类型</td></tr></table>

##### 字段说明

## API接口

<table><tr><th>接口名称</th><th>备注</th></tr>
<tr><td>订单查询接口</td><td>查询订单</td></tr></table>

# 非功能需求

## 性能需求

响应时间要求。
"""


class FullDraftExtractorTest(unittest.TestCase):
    def run_fixture(self) -> tuple[dict, str]:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "fixture.md"
            mapping = base / "mapping.json"
            report = base / "mapping.html"
            source.write_text(FIXTURE, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--out",
                    str(mapping),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(RENDERER),
                    "--mapping",
                    str(mapping),
                    "--out",
                    str(report),
                ],
                check=True,
            )
            return json.loads(mapping.read_text(encoding="utf-8")), report.read_text(
                encoding="utf-8"
            )

    def test_heading_roles_fields_and_line_aware_binding(self) -> None:
        data, _ = self.run_fixture()
        self.assertEqual(data["meta"]["artifact_kind"], "full_discovery_draft")
        self.assertEqual(data["meta"]["schema_version"], "1.1")
        self.assertEqual(
            [item["name"] for item in data["modules"]],
            ["暂无权限", "订单管理", "API接口"],
        )
        self.assertEqual(
            [item["name"] for item in data["functions"]],
            ["暂无权限", "订单列表", "API接口"],
        )

        atomics = {item["name"]: item for item in data["atomic_functions"]}
        self.assertNotIn("处理订单列表", atomics)
        self.assertIn("查看", atomics)
        self.assertIn("查询", atomics)
        self.assertIn("确定", atomics)
        self.assertIn("订单查询接口", atomics)
        self.assertIn("展示暂无权限缺省页", atomics)
        self.assertEqual(
            atomics["展示暂无权限缺省页"]["actor"], "没有权限（角色）的用户"
        )
        self.assertEqual(
            atomics["展示暂无权限缺省页"]["preconditions"], ["用户没有分配权限（角色）"]
        )
        self.assertNotIn("字段说明", atomics)

        fields = {item["business_name"]: item for item in data["business_fields"]}
        self.assertEqual(
            set(fields),
            {
                "客户编号",
                "是否已支付",
                "支付时间",
                "订单状态",
                "订单金额",
                "操作人",
                "操作时间",
                "变更内容",
                "变更人",
                "变更时间",
                "汇总金额",
                "明细金额",
                "生效时间",
                "订单类型",
                "审批意见",
                "备注",
            },
        )
        self.assertNotIn("按照变更时间倒序排序", fields)
        self.assertNotIn("汇总信息", fields)
        self.assertTrue(
            any(
                item["name_as_written"] == "是否已支付"
                and item["surface"] == "query_condition"
                for item in data["field_occurrences"]
            )
        )
        self.assertNotIn("确定", fields)
        self.assertEqual(
            data["excluded_field_occurrences"][0]["name_as_written"], "序号"
        )
        customer_occurrences = [
            item
            for item in data["field_occurrences"]
            if item["name_as_written"] == "客户编号"
        ]
        self.assertEqual(len(customer_occurrences), 2)
        self.assertEqual(len({item["field_id"] for item in customer_occurrences}), 1)

        binding_pairs = {
            (item["field_id"], item["atomic_id"]) for item in data["field_bindings"]
        }
        self.assertIn(
            (fields["客户编号"]["field_id"], atomics["查询"]["atomic_id"]),
            binding_pairs,
        )
        self.assertIn(
            (fields["订单状态"]["field_id"], atomics["查看"]["atomic_id"]),
            binding_pairs,
        )
        query_binding = next(
            item
            for item in data["field_bindings"]
            if item["field_id"] == fields["客户编号"]["field_id"]
            and item["atomic_id"] == atomics["查询"]["atomic_id"]
        )
        self.assertNotIn("output", query_binding["usages"])
        self.assertTrue(fields["订单类型"]["required"])
        self.assertIn("空 => 请选择订单类型", fields["订单类型"]["rules"])
        self.assertEqual(data["gaps"]["unresolved_validation_rules"], [])

        decisions = {
            (item["heading"], item["decision"])
            for item in data["classification_decisions"]
        }
        self.assertIn(("订单管理", "module"), decisions)
        self.assertIn(("订单列表", "function"), decisions)
        self.assertIn(("查看", "atomic_function"), decisions)
        self.assertIn(("字段说明", "exclude"), decisions)

    def test_failed_draft_is_visibly_marked_unsafe_for_downstream(self) -> None:
        data, html = self.run_fixture()
        self.assertIn("非最终结果", html)
        self.assertIn("不得作为下游测试用例生成的正式输入", html)
        self.assertFalse(data["audit"]["downstream_eligible"])

        spec = importlib.util.spec_from_file_location("mapping_validator", VALIDATOR)
        assert spec is not None and spec.loader is not None
        validator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validator)
        data["audit"]["downstream_eligible"] = True
        errors, _ = validator.validate(data, None)
        self.assertIn(
            "audit.downstream_eligible cannot be true before full semantic acceptance",
            errors,
        )

    def test_source_unit_identity_ignores_line_only_shifts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            first_source, second_source = base / "first.md", base / "second.md"
            first_output, second_output = base / "first.json", base / "second.json"
            first_source.write_text(FIXTURE, encoding="utf-8")
            second_source.write_text("\n\n" + FIXTURE, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(first_source),
                    "--out",
                    str(first_output),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(second_source),
                    "--out",
                    str(second_output),
                ],
                check=True,
            )
            first = json.loads(first_output.read_text(encoding="utf-8"))
            second = json.loads(second_output.read_text(encoding="utf-8"))
        first_units = {
            item["semantic_key"]: item["content_sha256"]
            for item in first["source_units"]
        }
        second_units = {
            item["semantic_key"]: item["content_sha256"]
            for item in second["source_units"]
        }
        self.assertEqual(first_units, second_units)

    def test_nested_capability_headings_are_functions_not_atomic_behaviors(
        self,
    ) -> None:
        fixture = """# 系统功能设计

## 配置管理

### 接入服务

#### 机构页面管理

<table><tr><th>类型</th><th>字段</th><th>字段描述</th></tr>
<tr><td>筛选条件</td><td>机构名称</td><td>支持模糊查询</td></tr>
<tr><td>按钮</td><td>查询</td><td>根据筛选条件查询</td></tr>
<tr><td>筛选条件</td><td>查询状态</td><td>下拉框：启用、停用</td></tr></table>

1. 仅当前月份的查询状态可以停用/启用。

#### 数据调用量系数（Y）

<table><tr><th>类型</th><th>字段</th><th>字段描述</th></tr>
<tr><td>按钮</td><td>查询</td><td>点击后查询数据</td></tr></table>
"""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, mapping = base / "fixture.md", base / "mapping.json"
            source.write_text(fixture, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--out",
                    str(mapping),
                ],
                check=True,
            )
            data = json.loads(mapping.read_text(encoding="utf-8"))

        functions = {item["name"]: item for item in data["functions"]}
        self.assertIn("机构页面管理", functions)
        self.assertIn("数据调用量系数（Y）", functions)
        self.assertEqual(
            functions["机构页面管理"]["parent_function_id"],
            functions["接入服务"]["function_id"],
        )
        atomics = [
            item
            for item in data["atomic_functions"]
            if item["function_id"] == functions["机构页面管理"]["function_id"]
        ]
        self.assertEqual({item["name"] for item in atomics}, {"查询", "停用", "启用"})
        stop = next(item for item in atomics if item["name"] == "停用")
        self.assertEqual([proof["locator"] for proof in stop["evidence"]], ["L14"])

    def test_images_are_registered_but_do_not_block_text_authority_pipeline(
        self,
    ) -> None:
        fixture = """# 系统功能设计

## 订单管理

### 订单列表

正文明确要求点击查询后展示订单列表。

<img src="media/order-list.png" />
"""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, mapping = base / "fixture.md", base / "mapping.json"
            (base / "media").mkdir()
            (base / "media" / "order-list.png").write_bytes(
                b"not-decoded-by-text-pipeline"
            )
            source.write_text(fixture, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--out",
                    str(mapping),
                ],
                check=True,
            )
            data = json.loads(mapping.read_text(encoding="utf-8"))
        image = next(item for item in data["source_units"] if item["kind"] == "image")
        self.assertFalse(image["relevant"])
        self.assertEqual(image["status"], "skipped")
        self.assertEqual(image["visual_availability"], "available")
        self.assertNotIn("image_ocr", data)
        self.assertNotIn(
            image["unit_id"],
            {item["unit_id"] for item in data["gaps"]["unresolved_references"]},
        )

    def test_reference_dependencies_are_classified_resolved_and_scoped(self) -> None:
        fixture = """# 系统功能设计

## 数据上报

### 任务记录

下载《数据采集标准》压缩包（详见云盘）。
反馈文件格式详见采集标准。
导出模板见《附件1 导出模板.xlsx》。

## 信息查询

### 基础产品

#### 功能描述

##### 网页端

展示查询结果。
状态值显示为《正常》，这是枚举值而不是资料引用。

##### 接口端

响应参数同网页端一致，其余均保持不变。
需提供接口文档。
其他校验规则同当前一致。

## 结算管理

### 日调用量

支持导出。

## 结算详情（业务侧）

### 日调用量

支持导出，导出规则同接口端一致。
"""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, source_review, mapping = (
                base / "fixture.md",
                base / "source-review.json",
                base / "mapping.json",
            )
            source.write_text(fixture, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(SOURCE_REVIEWER),
                    "--source",
                    str(source),
                    "--out",
                    str(source_review),
                ],
                check=True,
            )
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--source-review",
                    str(source_review),
                    "--out",
                    str(mapping),
                ],
                check=True,
            )
            data = json.loads(mapping.read_text(encoding="utf-8"))

        references = [
            item
            for item in data["source_units"]
            if item["kind"] == "reference_dependency"
        ]
        self.assertEqual(len(references), 8)
        by_type = {
            kind: [item for item in references if item["reference_type"] == kind]
            for kind in {
                "internal_reference",
                "external_artifact",
                "existing_baseline",
                "pending_artifact",
            }
        }
        self.assertEqual(
            {kind: len(items) for kind, items in by_type.items()},
            {
                "internal_reference": 2,
                "external_artifact": 3,
                "existing_baseline": 2,
                "pending_artifact": 1,
            },
        )
        self.assertTrue(
            all(
                item["status"] == "processed"
                and item["resolution_status"] == "target_located"
                for item in by_type["internal_reference"]
            )
        )
        self.assertTrue(
            all(
                item.get("blocking_scope", {}).get("function_id") for item in references
            )
        )
        standard_refs = [
            item
            for item in by_type["external_artifact"]
            if item["target_name"] == "数据采集标准"
        ]
        self.assertEqual(len(standard_refs), 2)
        self.assertEqual(len({item["reference_key"] for item in standard_refs}), 1)
        self.assertEqual(len(data["gaps"]["unresolved_references"]), 6)
        self.assertEqual(data["coverage"]["source_coverage"]["unavailable_units"], 6)
        self.assertEqual(
            data["coverage"]["source_coverage"]["review_required_units"], 0
        )
        self.assertEqual(
            data["coverage"]["reference_summary"],
            {
                "occurrence_count": 8,
                "distinct_target_count": 7,
                "by_type": {
                    "existing_baseline": 2,
                    "external_artifact": 3,
                    "internal_reference": 2,
                    "pending_artifact": 1,
                },
                "by_status": {"processed": 2, "review_required": 0, "unavailable": 6},
            },
        )

    def test_mapping_without_source_review_does_not_judge_missing_materials(
        self,
    ) -> None:
        fixture = """# 需求

## 导出

导出格式见《导出模板.xlsx》。
"""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, mapping = base / "fixture.md", base / "mapping.json"
            source.write_text(fixture, encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--out",
                    str(mapping),
                ],
                check=True,
            )
            data = json.loads(mapping.read_text(encoding="utf-8"))
        self.assertEqual(
            [
                item
                for item in data["source_units"]
                if item["kind"] == "reference_dependency"
            ],
            [],
        )
        self.assertIsNone(data["source_dependency_review"])
        self.assertTrue(
            any("资料依赖评审" in error for error in data["audit"]["errors"])
        )

    def test_source_review_must_match_primary_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, source_review, mapping = (
                base / "fixture.md",
                base / "source-review.json",
                base / "mapping.json",
            )
            source.write_text("# 需求\n\n## 查询\n", encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(SOURCE_REVIEWER),
                    "--source",
                    str(source),
                    "--out",
                    str(source_review),
                ],
                check=True,
            )
            source.write_text("# 需求\n\n## 查询\n\n新增规则。\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(EXTRACTOR),
                    "--source",
                    str(source),
                    "--source-review",
                    str(source_review),
                    "--out",
                    str(mapping),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("different primary source snapshot", result.stderr)


if __name__ == "__main__":
    unittest.main()
