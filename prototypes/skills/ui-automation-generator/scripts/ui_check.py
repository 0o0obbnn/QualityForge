#!/usr/bin/env python3
"""UI 自动化脚本契约检查器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, re, sys

INLINE_XPATH_RE = re.compile(r'find_element\s*\(\s*[\'"]\s*(//|/html)', re.IGNORECASE)
WAIT_RE = re.compile(r'wait_for|explicit_wait|wait\.for|expect|locator\.', re.IGNORECASE)


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_script(script):
    findings = []
    code = script.get("code", "")
    locator_refs = script.get("locator_refs", [])
    known_locators = set(script.get("known_locator_ids", []))
    interactions = script.get("interactions", [])

    # 检查 1：禁止内联 XPath
    for m in INLINE_XPATH_RE.finditer(code):
        findings.append(finding("INLINE_XPATH_LITERAL", f"pos:{m.start()}", f"内联 XPath；请改用 locator ID"))
    # 检查 2：交互必须带等待策略
    for ix in interactions:
        iid = ix.get("interaction_id", "?")
        if not ix.get("wait_strategy") and not WAIT_RE.search(ix.get("code", "")):
            findings.append(finding("MISSING_WAIT_STRATEGY", iid, f"interaction {iid!r} 缺少 wait 策略；会导致 flaky"))
    # 检查 3：POM 分层
    if script.get("test_logic_in_page_object"):
        findings.append(finding("POM_VIOLATION", "structure", "在 page object 中检测到测试逻辑"))
    if script.get("page_object_in_test"):
        findings.append(finding("POM_VIOLATION", "structure", "在测试中检测到 page object 逻辑"))
    # 检查 4：locator 引用必须有效
    if known_locators:
        for ref in locator_refs:
            if ref not in known_locators:
                findings.append(finding("LOCATOR_NOT_IN_LIBRARY", ref, f"locator {ref!r} 不在库中"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "19", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> 可以执行；REJECT -> 修复 XPath/wait/POM/locator 问题"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--script", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        script = json.load(open(args.script))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"读取输入失败：{e}"}), file=sys.stderr); return 3
    result = check_script(script)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
