#!/usr/bin/env python3
"""Stamp a legacy mapping with an explicit artifact kind without changing business facts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KINDS_BY_VERSION = {
    "1.1": "full_discovery_draft",
    "1.2": "normalized_requirement_mapping",
    "1.3": "review_projected_mapping",
}


def infer_kind(data: dict[str, Any]) -> str:
    version = str(data.get("meta", {}).get("schema_version", ""))
    if version == "1.4":
        return "review_projected_typed_graph" if data.get("review_projection") else "typed_requirement_graph"
    if version in KINDS_BY_VERSION:
        return KINDS_BY_VERSION[version]
    raise ValueError(f"unsupported legacy schema version: {version or '<missing>'}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Add artifact_kind to a legacy mapping and write a new file")
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.mapping.resolve() == args.out.resolve():
        raise SystemExit("refusing in-place migration; choose a different --out path")
    data = json.loads(args.mapping.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("mapping root must be an object")
    meta = data.setdefault("meta", {})
    inferred = infer_kind(data)
    existing = meta.get("artifact_kind")
    if existing and existing != inferred:
        raise SystemExit(f"existing artifact_kind {existing!r} conflicts with inferred {inferred!r}")
    meta["artifact_kind"] = inferred
    meta.setdefault("migration_history", []).append({
        "operation": "stamp_artifact_kind",
        "source_sha256": hashlib.sha256(args.mapping.read_bytes()).hexdigest(),
        "migrated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    })
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
