#!/usr/bin/env python3
"""Build a complete, traceable work queue for unresolved review findings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build review finding resolution queue")
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dimension", help="Select one assessment dimension")
    parser.add_argument("--requirement-id", action="append", help="Select a requirement; repeat for a bounded batch")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, help="Maximum combined finding and assessment jobs")
    args = parser.parse_args()
    if args.offset < 0 or (args.limit is not None and args.limit <= 0):
        raise SystemExit("offset must be non-negative and limit must be positive")
    review = json.loads(args.review.read_text(encoding="utf-8"))
    assessments = review.get("requirement_assessments", [])
    requirements = {item.get("requirement_id"): item for item in review.get("requirements", [])}
    entries = []
    for finding in review.get("findings", []):
        if finding.get("lifecycle_status", "OPEN") in {"RESOLVED", "WITHDRAWN"}:
            continue
        finding_id = finding.get("finding_id")
        updates = [
            {
                "requirement_id": item.get("requirement_id"), "dimension": item.get("dimension"),
                "current_status": item.get("status"), "status": None, "rationale": None,
            }
            for item in assessments if finding_id in item.get("finding_ids", [])
        ]
        entries.append({
            "finding_id": finding_id, "code": finding.get("code"), "severity": finding.get("severity"),
            "question": finding.get("question"), "recommendation": finding.get("recommendation"),
            "current_evidence": finding.get("evidence"), "current_source_refs": finding.get("source_refs", []),
            "decision": None, "resolution": None, "source_refs": [], "assessment_updates": updates,
        })
    assessment_reviews = [
        {
            "assessment_id": item.get("assessment_id"), "requirement_id": item.get("requirement_id"),
            "requirement_title": requirements.get(item.get("requirement_id"), {}).get("title"),
            "dimension": item.get("dimension"), "status": None, "rationale": None, "finding_ids": [],
            "source_refs": requirements.get(item.get("requirement_id"), {}).get("source_refs", []),
        }
        for item in assessments if item.get("status") == "NOT_REVIEWED"
    ]
    requirement_filter = set(args.requirement_id or [])
    if args.dimension:
        entries = [item for item in entries if any(update.get("dimension") == args.dimension for update in item.get("assessment_updates", []))]
        assessment_reviews = [item for item in assessment_reviews if item.get("dimension") == args.dimension]
    if requirement_filter:
        entries = [item for item in entries if any(update.get("requirement_id") in requirement_filter for update in item.get("assessment_updates", []))]
        assessment_reviews = [item for item in assessment_reviews if item.get("requirement_id") in requirement_filter]
    total_jobs = [("resolution", item) for item in entries] + [("assessment", item) for item in assessment_reviews]
    def job_key(job: tuple[str, dict]) -> tuple[str, str, int, str]:
        kind, item = job
        update = (item.get("assessment_updates") or [{}])[0] if kind == "resolution" else item
        return str(update.get("requirement_id", "")), str(update.get("dimension", "")), 0 if kind == "resolution" else 1, str(item.get("finding_id", item.get("assessment_id", "")))
    total_jobs.sort(key=job_key)
    selected_jobs = total_jobs[args.offset:args.offset + args.limit if args.limit is not None else None]
    entries = [item for kind, item in selected_jobs if kind == "resolution"]
    assessment_reviews = [item for kind, item in selected_jobs if kind == "assessment"]
    queue = {
        "meta": {"artifact_kind": "requirement_review_resolution_queue", "schema_version": "1.0"},
        "review_id": review.get("review_id"), "resolutions": entries, "assessment_reviews": assessment_reviews,
        "coverage": {
            "open_finding_count": len(entries),
            "not_reviewed_assessment_count": len(assessment_reviews),
            "reject_count": sum(item.get("severity") == "REJECT" for item in entries),
            "review_count": sum(item.get("severity") == "REVIEW" for item in entries),
            "selected_job_count": len(selected_jobs), "matching_job_count": len(total_jobs),
            "offset": args.offset, "limit": args.limit,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
