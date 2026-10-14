"""构造 requirement-quality-gate 的对照组与负例。

- case_pass.json：6维度全CLEAR、无finding → 预期 PASS (exit 0)
- case_pass_with_review.json：仅1条REVIEW级finding → 预期 PASS_WITH_REVIEW (exit 1)
- case_negative.json：缺维度 + 未绑定finding + 硬code非法降级 + 未声明来源 → 预期 REJECT (exit 2) 且命中4个结构code
"""
import json

DIMS = ["ambiguity", "consistency", "testability", "completeness", "nfr_measurability", "role_permission"]

pass_packet = {
    "review_id": "CTRL-PASS",
    "source_ids": ["SRC-A"],
    "assessments": [
        {"dimension": d, "status": "CLEAR", "rationale": f"对照用例：{d} 维度无发现", "finding_ids": []}
        for d in DIMS
    ],
    "findings": [],
}

pwr_packet = {
    "review_id": "CTRL-PASS-WITH-REVIEW",
    "source_ids": ["SRC-A"],
    "assessments": [
        {"dimension": d,
         "status": "FINDING" if d == "ambiguity" else "CLEAR",
         "rationale": f"对照用例：{d} 维度" + ("存在1条待澄清歧义" if d == "ambiguity" else "无发现"),
         "finding_ids": ["F-001"] if d == "ambiguity" else []}
        for d in DIMS
    ],
    "findings": [
        {"finding_id": "F-001", "code": "AMBIGUOUS_LANGUAGE", "severity": "REVIEW",
         "source_refs": ["SRC-A§1.1"], "evidence": "对照用例证据：\"系统应尽快返回结果\"",
         "question": "请量化\"尽快\"的响应时间上限"}
    ],
}

negative_packet = {
    "review_id": "NEG-STRUCTURAL",
    "source_ids": ["SRC-A"],
    "assessments": [
        # 故意缺 role_permission 维度（5/6）
        {"dimension": d, "status": "CLEAR", "rationale": "负例：维度覆盖不全", "finding_ids": []}
        for d in DIMS if d != "role_permission"
    ] + [
        # FINDING 状态但引用不存在的 finding
        {"dimension": "consistency", "status": "FINDING", "rationale": "负例：引用幽灵finding", "finding_ids": ["F-GHOST"]},
        # 重复维度
        {"dimension": "ambiguity", "status": "CLEAR", "rationale": "负例：重复评估", "finding_ids": []},
    ],
    "findings": [
        # 硬 code 被非法降级为 REVIEW
        {"finding_id": "F-101", "code": "CROSS_SOURCE_CONFLICT", "severity": "REVIEW",
         "source_refs": ["SRC-A§2"], "evidence": "负例：硬finding被降级", "question": "负例问题"},
        # 未声明的来源引用 + 未绑定到任何维度
        {"finding_id": "F-102", "code": "AMBIGUOUS_LANGUAGE", "severity": "REVIEW",
         "source_refs": ["SRC-UNDECLARED§1"], "evidence": "负例：来源未声明且未绑定", "question": "负例问题"},
        # 缺 evidence 与 question
        {"finding_id": "F-103", "code": "INCOMPLETE_REQUIREMENT", "severity": "REVIEW",
         "source_refs": ["SRC-A§3"], "evidence": "", "question": ""},
    ],
}

for name, pkt in [("case_pass.json", pass_packet),
                  ("case_pass_with_review.json", pwr_packet),
                  ("case_negative.json", negative_packet)]:
    with open(name, "w", encoding="utf-8") as fh:
        json.dump(pkt, fh, ensure_ascii=False, indent=2)
    print("written:", name)
