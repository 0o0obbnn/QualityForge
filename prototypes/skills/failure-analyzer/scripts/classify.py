#!/usr/bin/env python3
"""
失败分类器——4 类根因分类体系。

类别：ENVIRONMENT、DATA、PRODUCT_BUG、TEST_ASSET_DEFECT
优先级顺序（关键逻辑）：ENVIRONMENT -> DATA -> PRODUCT_BUG -> TEST_ASSET_DEFECT
歧义时默认 TEST_ASSET_DEFECT（安全默认 + 复核标记）。

CLI:
  python classify.py --signal path/to/signal.json [--out path]

退出码：0 已分类（任意类别）| 3 输入无效
"""
from __future__ import annotations
import argparse, datetime as _dt, json, sys

# 信号类型 -> 类别。优先级顺序关键：自上而下检查。
ENVIRONMENT_ERRORS = frozenset({
    "conn_refused", "dns_error", "healthcheck_fail", "oom",
    "disk_full", "infra_timeout", "service_unavailable",
})
DATA_ERRORS = frozenset({
    "fixture_build_fail", "fk_violation", "seed_missing",
    "field_not_in_response", "data_type_mismatch",
})
PRODUCT_BUG_ERRORS = frozenset({
    "assertion_mismatch", "contract_violation", "unexpected_exception",
    "wrong_status_code", "wrong_response_body",
})
TEST_ASSET_ERRORS = frozenset({
    "stale_locator", "tautological_assert", "orphan_assertion",
    "wrong_expected_value", "element_not_found",
})


def _confidence(error_type, matched_class, env_healthy, data_valid):
    """评估分类置信度。低置信 -> 触发复核标记。"""
    # 高置信：error_type 明确且无歧义
    if error_type in ENVIRONMENT_ERRORS and matched_class == "ENVIRONMENT":
        return 0.95
    if error_type in DATA_ERRORS and matched_class == "DATA":
        return 0.9
    if error_type in PRODUCT_BUG_ERRORS and env_healthy and data_valid:
        return 0.9
    if error_type in TEST_ASSET_ERRORS and matched_class == "TEST_ASSET_DEFECT":
        return 0.85
    # 中等：命中但存在歧义
    if matched_class == "PRODUCT_BUG" and (not env_healthy or not data_valid):
        return 0.5  # 过早判定为 product_bug
    # 低置信：默认回退
    return 0.4


def classify(signal):
    """对失败信号分类。返回包含类别 + 置信度 + routing 的 dict。"""
    error_type = signal.get("error_type", "")
    env_healthy = signal.get("env_healthy", None)
    data_valid = signal.get("data_valid", None)

    # 规则 1：ENVIRONMENT
    if error_type in ENVIRONMENT_ERRORS:
        cls = "ENVIRONMENT"
        rule = "规则 1（环境类错误类型）"
    # 规则 2：DATA（在 product_bug 之前检查）
    elif error_type in DATA_ERRORS or data_valid is False:
        cls = "DATA"
        rule = "规则 2（数据类错误类型或 data_valid=False）"
    # 规则 3：PRODUCT_BUG（仅当 env + 数据已确认干净）
    elif error_type in PRODUCT_BUG_ERRORS and env_healthy is True and data_valid is True:
        cls = "PRODUCT_BUG"
        rule = "规则 3（产品类错误 + env_healthy + data_valid）"
    # 规则 3 覆盖：PRODUCT_BUG 错误类型但 env/数据未验证 -> 判定过早
    elif error_type in PRODUCT_BUG_ERRORS and (env_healthy is not True or data_valid is not True):
        cls = "TEST_ASSET_DEFECT"
        rule = "覆盖：PRODUCT_BUG 判定过早（env/数据未验证）-> 默认 TEST_ASSET_DEFECT"
    # 规则 4：TEST_ASSET_DEFECT（显式信号或默认）
    elif error_type in TEST_ASSET_ERRORS:
        cls = "TEST_ASSET_DEFECT"
        rule = "规则 4（测试资产类错误类型）"
    else:
        # 默认回退：TEST_ASSET_DEFECT，低置信
        cls = "TEST_ASSET_DEFECT"
        rule = "规则 4（默认回退——无规则命中）"

    conf = _confidence(error_type, cls, env_healthy, data_valid)

    # 覆盖逻辑已在上方规则 3 覆盖分支内处理；本段只是
    # 根据最终分类构建 routing 建议。
    routing = {
        "ENVIRONMENT": "不得作为产品缺陷立项；重新准备环境并重跑",
        "DATA": "不得作为产品缺陷立项；重建 fixture/数据",
        "PRODUCT_BUG": "作为产品缺陷立项（唯一计入缺陷统计的类别）",
        "TEST_ASSET_DEFECT": "不得作为产品缺陷立项；修复测试；与产品缺陷统计分开",
    }[cls]

    counts_as_product_defect = (cls == "PRODUCT_BUG")
    needs_review = conf < 0.7

    return {
        "skill": "23",
        "classified_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "failure_id": signal.get("failure_id"),
        "error_type": error_type,
        "classification": cls,
        "confidence": conf,
        "rule_fired": rule,
        "counts_as_product_defect": counts_as_product_defect,
        "needs_human_review": needs_review,
        "env_healthy": env_healthy,
        "data_valid": data_valid,
        "routing": routing,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="失败分类器（4 类）")
    p.add_argument("--signal", required=True, help="失败信号 JSON")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        signal = json.load(open(args.signal))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    result = classify(signal)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
