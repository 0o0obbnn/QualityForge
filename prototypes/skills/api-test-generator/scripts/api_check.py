#!/usr/bin/env python3
"""API 测试脚本契约检查器。"""
from __future__ import annotations
import argparse, datetime as _dt, json, re, sys

URL_RE = re.compile(r'https?://[\S]+|localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
SECRET_NAMES = re.compile(r'(password|passwd|secret|api_?key|token|credential|auth_?bearer)', re.IGNORECASE)
SECRET_LITERALS = re.compile(r'["\'](sk-|pk-|Bearer\s|ghp_|AKIA)[\w]+["\']')
# 表示安全配置注入的模式——这些不是硬编码密钥
_SAFE_INJECTION = re.compile(r'os\.environ|os\.getenv|config\.|settings\.|getattr\(')


def finding(code, target, msg):
    return {"code": code, "severity": "REJECT", "target": target, "msg": msg}


def check_script(script):
    findings = []
    if not isinstance(script, dict):
        return {"skill": "18", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                "total_findings": 1,
                "findings": [finding("INVALID_SCRIPT_PACKET", "root",
                                     "脚本包根节点必须是对象")],
                "verdict": "REJECT",
                "routing": "PASS -> 可执行；REJECT -> 需修复硬编码值/缺失依赖/缺失断言"}
    code = script.get("code", "")
    code = code if isinstance(code, str) else ""
    case_refs = script.get("case_refs", [])
    expected_results = [e for e in (script.get("expected_results", []) or []) if isinstance(e, dict)]
    fixture_deps = script.get("fixture_deps", [])
    asserts = [a for a in (script.get("asserts", []) or []) if isinstance(a, dict)]

    # 空脚本体属于证据缺失，而非干净的契约通过：检查 1-2 扫描的是
    # `code`，否则将没有任何可检查的对象。
    if not code.strip():
        findings.append(finding("EMPTY_SCRIPT_BODY", "script",
                                "脚本未声明 code；无法验证契约合规性"))
    # 检查 3-4 依赖 expected_results。缺少它时这两个最强检查会静默失效，
    # 因此必须报告缺失而不是放行。
    if not expected_results:
        findings.append(finding("NO_EXPECTED_RESULTS_DECLARED", "script",
                                "脚本未声明 expected_results；无法验证 assert 覆盖"))

    # 检查 1：硬编码环境信息（URL、IP、localhost）
    for m in URL_RE.finditer(code):
        findings.append(finding("HARDCODED_ENV", f"pos:{m.start()}", f"硬编码 URL/主机 {m.group()!r}；请改用配置注入"))
    # 检查 2：硬编码密钥
    for m in SECRET_LITERALS.finditer(code):
        findings.append(finding("HARDCODED_SECRET", f"pos:{m.start()}", f"疑似密钥字面量 {m.group()!r}"))
    for line_no, line in enumerate(code.split("\n"), 1):
        if SECRET_NAMES.search(line) and ("=" in line or ":" in line):
            # 跳过使用了安全配置注入模式的行
            if _SAFE_INJECTION.search(line):
                continue
            # 值部分是最后一个 '='（赋值）之后或 ':'（字典值）之后的全部内容
            value_part = line.split("=")[-1] if "=" in line else line.split(":", 1)[-1]
            # 跳过引用变量的 f-string/插值字符串（而非字面量）
            if re.search(r'f["\'].*\{[A-Za-z_][A-Za-z0-9_]*\}', value_part):
                continue
            # 检查值一侧是否包含裸字符串字面量（而非字典键）
            # 字典键模式形如 "word": —— 字符串后紧跟冒号
            # 要捕获 password = "abc123"，但不要捕获 {"Authorization": some_var}
            bare_str = re.search(r'["\']([^"\'{\[\]()]{4,})["\'](?!\s*:)', value_part)
            if bare_str:
                findings.append(finding("HARDCODED_SECRET", f"line:{line_no}", f"疑似密钥字面量：{line.strip()[:60]}"))
    # 检查 3：fixture 依赖已声明（存在 expected_results 时，fixture_deps 应非空）
    if expected_results and not fixture_deps:
        findings.append(finding("MISSING_FIXTURE_DECL", "script", "脚本声明了 expected_results 但未声明 fixture_deps"))
    # 检查 4：每个 expected_result 都有对应的 assert
    assert_targets = {a.get("expected_result_id") for a in asserts if a.get("expected_result_id")}
    for er in expected_results:
        er_id = er.get("expected_result_id") or er.get("id")
        if er_id and er_id not in assert_targets:
            findings.append(finding("UNCOVERED_EXPECTED_RESULT", str(er_id), f"expected_result {er_id!r} 没有对应的 assert"))

    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {"skill": "18", "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "total_findings": len(findings), "findings": findings,
            "verdict": "REJECT" if has_reject else "PASS",
            "routing": "PASS -> 可执行；REJECT -> 需修复硬编码值/缺失依赖/缺失断言"}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--script", required=True); p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        script = json.load(open(args.script))
    except (OSError, json.JSONDecodeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr); return 3
    result = check_script(script)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out: open(args.out, "w").write(out)
    else: print(out)
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
