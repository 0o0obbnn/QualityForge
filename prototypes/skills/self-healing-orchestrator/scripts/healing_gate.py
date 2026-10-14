#!/usr/bin/env python3
"""
自愈 gate。三条硬护栏，命中任意一条即否决：
  1. CRITICAL PATH：关键路径失败永不自动 heal。
  2. ASSERTION PROTECTION：触及期望值的 heal 一律 DENY。
  3. HEALING CAP：同一资产 7 天内 heal 超过 3 次即阻断。
"""
from __future__ import annotations
import argparse, datetime as _dt, hashlib, json, sys

HEAL_WINDOW_DAYS = 7
HEAL_CAP = 3
CRITICAL_KEYWORDS = frozenset({
    "login", "auth", "authenticate", "token", "session",
    "payment", "pay", "charge", "refund", "payout", "ledger",
    "permission", "acl", "role", "privilege", "grant", "revoke",
})


def _event_id(asset_id, heal_type):
    h = hashlib.sha1(f"{asset_id}|{heal_type}|{_dt.datetime.now(_dt.timezone.utc).isoformat()}".encode()).hexdigest()
    return f"HEAL-{h[:12]}"


def _is_critical(path_category, asset_id):
    if path_category == "normal":
        lowered = asset_id.lower()
        return any(k in lowered for k in CRITICAL_KEYWORDS)
    return True


def evaluate(*, asset_id, path_category, heal_type, touches_expected, heals_7d, confidence=None):
    event_id = _event_id(asset_id, heal_type)
    base = {"event_id": event_id, "skill": "24", "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "asset_id": asset_id, "path_category": path_category, "heal_type": heal_type,
            "touches_expected": touches_expected, "heals_7d": heals_7d, "confidence": confidence}
    if _is_critical(path_category, asset_id):
        return {"decision": "DENY", "reason": "护栏 1（关键路径）：绝不自动 heal；立即失败并转交人工。",
                "vetoed_by": "CRITICAL_PATH", "skill28_routing": "forced", **base}
    if touches_expected or heal_type == "assertion":
        return {"decision": "DENY", "reason": "护栏 2（断言保护）：期望值改动只能由人工完成。",
                "vetoed_by": "ASSERTION_PROTECTION", "skill28_routing": "forced", **base}
    if heals_7d > HEAL_CAP:
        return {"decision": "DENY", "reason": f"护栏 3（修复上限）：{HEAL_WINDOW_DAYS} 天内已 heal {heals_7d} 次（上限 {HEAL_CAP}）；强制人工重构。",
                "vetoed_by": "HEALING_CAP", "skill28_routing": "forced", **base}
    return {"decision": "ALLOW", "reason": f"全部护栏通过（path={path_category}，heals_7d={heals_7d} <= {HEAL_CAP}）。",
            "vetoed_by": None, "skill28_routing": "sample", "audit_required": True, **base}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--asset-id", required=True)
    p.add_argument("--path-category", default="critical", choices=["critical", "normal"])
    p.add_argument("--heal-type", required=True, choices=["locator", "fixture", "assertion", "other"])
    p.add_argument("--touches-expected", action="store_true")
    # 必填且无默认值：该 gate 没有 heal 历史存储，计数由调用方提供。
    # 若默认为 0，调用方只需省略该 flag 就能静默绕过修复上限——
    # 这条护栏不允许"不说也有值"。
    p.add_argument("--heals-7d", type=int, required=True,
                   help="该资产在 7 天窗口内的历史 heal 次数（无则填 0）")
    p.add_argument("--confidence", type=float, default=None)
    args = p.parse_args(argv)
    if args.confidence is not None and not (0.0 <= args.confidence <= 1.0):
        print(json.dumps({"error": "confidence 必须在 [0.0,1.0] 范围内"}), file=sys.stderr); return 3
    if args.heals_7d < 0:
        print(json.dumps({"error": "heals-7d 必须 >= 0"}), file=sys.stderr); return 3
    result = evaluate(asset_id=args.asset_id, path_category=args.path_category, heal_type=args.heal_type,
                      touches_expected=args.touches_expected, heals_7d=args.heals_7d, confidence=args.confidence)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["decision"] == "DENY" else 0


if __name__ == "__main__":
    sys.exit(main())
