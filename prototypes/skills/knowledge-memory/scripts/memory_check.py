#!/usr/bin/env python3
"""
知识记忆条目校验器。

五项检查（见 references/memory_rules.md）：
  1. NO_PROVENANCE：条目缺少 source 或 confidence。
  2. SENSITIVE_IN_ENTRY：发现未脱敏的敏感模式。
  3. UNVETTED_FEEDBACK：feedback_eligible 但缺少 review_signoff。
  4. NO_TIMESTAMP：缺少 created_at，无法调度衰减。
  5. DUPLICATE_ENTRY：content hash 与已存储条目相同。

CLI:
  python memory_check.py --entry path/to/entry.json [--known-hashes path] [--out path]

退出码：0 PASS | 2 REJECT | 3 输入无效
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys

SENSITIVE_RE = re.compile(r"password=|api_key=|Bearer\s", re.IGNORECASE)
PHONE_RE = re.compile(r"\d{3}-\d{3,4}-\d{3,4}")


def finding(code, target, msg, severity="REJECT"):
    return {"code": code, "severity": severity, "target": target, "msg": msg}


def content_hash(payload):
    """对 {pattern, summary, content} 计算 SHA-1，取前 12 位十六进制——依据 memory_rules.md。"""
    basis = json.dumps(
        {
            "pattern": payload.get("pattern", ""),
            "summary": payload.get("summary", ""),
            "content": payload.get("content", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def check_memory_entry(payload, known_hashes=None):
    """校验单个记忆条目。返回 findings 列表。"""
    findings = []
    known_hashes = set(known_hashes or ())
    if not isinstance(payload, dict):
        return [
            finding("INVALID_ENTRY_PACKET", "root", "记忆条目根节点必须是对象")
        ]

    # 检查 1：出处。`confidence` 与 None 比较，而非真值判断——
    # 合法的 0.0 分是已提供的证据，不是缺失出处。
    source = payload.get("source")
    confidence = payload.get("confidence")
    if not source or not str(source).strip():
        findings.append(finding("NO_PROVENANCE", "source", "条目缺少 source 引用"))
    if confidence is None:
        findings.append(finding("NO_PROVENANCE", "confidence", "条目缺少 confidence 分数"))
    elif isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        findings.append(
            finding("NO_PROVENANCE", "confidence", f"confidence 必须是数字，实际为 {confidence!r}")
        )
    elif not 0.0 <= confidence <= 1.0:
        findings.append(
            finding("NO_PROVENANCE", "confidence", f"confidence {confidence} 超出 [0,1]")
        )

    # 检查 2：敏感内容
    content = payload.get("content", "")
    content = content if isinstance(content, str) else ""
    if SENSITIVE_RE.search(content):
        findings.append(
            finding("SENSITIVE_IN_ENTRY", "content", "条目中存在未脱敏的凭证字面量")
        )
    if PHONE_RE.search(content):
        findings.append(
            finding("SENSITIVE_IN_ENTRY", "content", "条目中存在未脱敏的电话号码模式")
        )

    # 检查 3：反馈审核
    if payload.get("feedback_eligible") and not payload.get("review_signoff"):
        findings.append(
            finding(
                "UNVETTED_FEEDBACK",
                "review_signoff",
                "feedback_eligible 条目缺少 review_signoff；猜测会被自动传播",
            )
        )

    # 检查 4：衰减时间戳
    if not payload.get("created_at"):
        findings.append(
            finding("NO_TIMESTAMP", "created_at", "缺少 created_at；条目永远无法衰减")
        )

    # 检查 5：重复检测
    digest = content_hash(payload)
    if digest in known_hashes:
        findings.append(
            finding("DUPLICATE_ENTRY", digest, f"content hash {digest} 已存在")
        )

    return findings


def check_entry(payload, known_hashes=None):
    """将 findings 列表包装为带 verdict 的信封。"""
    findings = check_memory_entry(payload, known_hashes)
    has_reject = any(f["severity"] == "REJECT" for f in findings)
    return {
        "skill": "29",
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "content_hash": content_hash(payload) if isinstance(payload, dict) else None,
        "total_findings": len(findings),
        "findings": findings,
        "verdict": "REJECT" if has_reject else "PASS",
        "routing": "PASS -> 条目保持可复核状态，不自动发布；REJECT -> 修复出处/脱敏/审核",
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="知识记忆条目校验器")
    p.add_argument("--entry", required=True, help="记忆条目 JSON")
    p.add_argument("--known-hashes", default=None, help="已存储 content hash 的 JSON 数组")
    p.add_argument("--out", default=None)
    args = p.parse_args(argv)
    try:
        with open(args.entry, encoding="utf-8") as handle:
            payload = json.load(handle)
        known = set()
        if args.known_hashes:
            with open(args.known_hashes, encoding="utf-8") as handle:
                known = set(json.load(handle))
    except (OSError, json.JSONDecodeError, TypeError) as e:
        print(json.dumps({"error": f"输入错误：{e}"}), file=sys.stderr)
        return 3
    result = check_entry(payload, known)
    out = json.dumps(result, ensure_ascii=False, indent=2)
    try:
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(out)
        else:
            print(out)
    except OSError as e:
        print(json.dumps({"error": f"输出错误：{e}"}), file=sys.stderr)
        return 3
    return 2 if result["verdict"] == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
