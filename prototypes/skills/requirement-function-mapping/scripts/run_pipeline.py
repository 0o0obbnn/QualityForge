#!/usr/bin/env python3
"""Run the requirement mapping pipeline with hash-based resumability."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PIPELINE_VERSION = "1.3"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_fingerprint(paths: list[Path], values: list[str]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(str(path.resolve()).encode())
        digest.update(sha256(path).encode())
    for value in values:
        digest.update(value.encode())
    return digest.hexdigest()


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class Stage:
    def __init__(self, name: str, inputs: list[Path], outputs: list[Path], command: list[str], capture_to: Path | None = None):
        self.name = name
        self.inputs = inputs
        self.outputs = outputs
        self.command = command
        self.capture_to = capture_to

    @property
    def script(self) -> Path:
        return Path(self.command[1])

    def fingerprint(self) -> str:
        return stable_fingerprint([*self.inputs, self.script], self.command[2:])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or resume the requirement-function-mapping pipeline")
    parser.add_argument("--source", required=True, type=Path, help="Markdown requirement source")
    parser.add_argument("--out-dir", required=True, type=Path, help="Pipeline artifact directory")
    parser.add_argument("--source-review", type=Path, help="qa-requirement-review source dependency review; required for formal mapping")
    parser.add_argument("--review", type=Path, help="Optional qa-requirement-review JSON")
    parser.add_argument("--resume", action="store_true", help="Reuse a completed stage only when inputs, script and outputs still match")
    parser.add_argument("--from-stage", help="Start at this stage after verifying earlier outputs exist")
    parser.add_argument("--through-stage", help="Stop after this stage")
    return parser.parse_args()


def build_stages(args: argparse.Namespace) -> list[Stage]:
    prefix = args.source.stem
    out = args.out_dir
    draft = out / f"{prefix}_full_discovery_draft.json"
    mapping = out / f"{prefix}_mapping.json"
    graph = out / f"{prefix}_typed_graph.json"
    graph_validation = out / f"{prefix}_typed_graph_validation.json"
    graph_html = out / f"{prefix}_typed_graph.html"
    extract_command = [sys.executable, str(SCRIPTS / "extract_markdown_full_draft.py"), "--source", str(args.source), "--out", str(draft)]
    extract_inputs = [args.source]
    if args.source_review:
        extract_command.extend(["--source-review", str(args.source_review)])
        extract_inputs.append(args.source_review)
    stages = [
        Stage("extract", extract_inputs, [draft], extract_command),
        Stage("finalize", [draft, args.source], [mapping], [sys.executable, str(SCRIPTS / "finalize_mapping.py"), "--mapping", str(draft), "--source", str(args.source), "--out", str(mapping)]),
        Stage("enrich", [mapping, args.source], [graph], [sys.executable, str(SCRIPTS / "enrich_graph_model.py"), "--mapping", str(mapping), "--source", str(args.source), "--out", str(graph)]),
        Stage("validate_graph", [graph, args.source], [graph_validation], [sys.executable, str(SCRIPTS / "validate_mapping.py"), "--mapping", str(graph), "--source", str(args.source)], graph_validation),
        Stage("render_graph", [graph], [graph_html], [sys.executable, str(SCRIPTS / "render_mapping_html.py"), "--mapping", str(graph), "--out", str(graph_html)]),
    ]
    if args.review:
        reviewed = out / f"{prefix}_reviewed_graph.json"
        reviewed_validation = out / f"{prefix}_reviewed_graph_validation.json"
        reviewed_html = out / f"{prefix}_reviewed_graph.html"
        test_input = out / f"{prefix}_test_design_input.json"
        test_validation = out / f"{prefix}_test_design_input_validation.json"
        stages.extend([
            Stage("project_review", [graph, args.review], [reviewed], [sys.executable, str(SCRIPTS / "apply_review_to_mapping.py"), "--mapping", str(graph), "--review", str(args.review), "--out", str(reviewed)]),
            Stage("validate_reviewed", [reviewed, args.source], [reviewed_validation], [sys.executable, str(SCRIPTS / "validate_mapping.py"), "--mapping", str(reviewed), "--source", str(args.source)], reviewed_validation),
            Stage("render_reviewed", [reviewed], [reviewed_html], [sys.executable, str(SCRIPTS / "render_mapping_html.py"), "--mapping", str(reviewed), "--out", str(reviewed_html)]),
            Stage("compile_test_input", [reviewed], [test_input], [sys.executable, str(SCRIPTS / "build_test_design_input.py"), "--mapping", str(reviewed), "--ready-only", "--out", str(test_input)]),
            Stage("validate_test_input", [test_input], [test_validation], [sys.executable, str(SCRIPTS / "validate_test_design_input.py"), "--input", str(test_input)], test_validation),
        ])
    return stages


def outputs_match(record: dict[str, Any], outputs: list[Path]) -> bool:
    expected = record.get("output_sha256", {})
    return bool(outputs) and all(path.exists() and expected.get(str(path.resolve())) == sha256(path) for path in outputs)


def main() -> int:
    args = parse_args()
    required = [args.source, *([args.source_review] if args.source_review else []), *([args.review] if args.review else [])]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"missing pipeline input: {', '.join(missing)}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.out_dir / "pipeline-state.json"
    if args.resume and state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    else:
        state = {"pipeline_version": PIPELINE_VERSION, "created_at": now(), "stages": {}}
    state.update({
        "pipeline_version": PIPELINE_VERSION,
        "updated_at": now(),
        "inputs": {"source": str(args.source.resolve()), "source_review": str(args.source_review.resolve()) if args.source_review else None,
                   "review": str(args.review.resolve()) if args.review else None},
    })
    stages = build_stages(args)
    names = [stage.name for stage in stages]
    for selected, label in ((args.from_stage, "from"), (args.through_stage, "through")):
        if selected and selected not in names:
            raise SystemExit(f"unknown {label} stage {selected!r}; choose from: {', '.join(names)}")
    start = names.index(args.from_stage) if args.from_stage else 0
    end = names.index(args.through_stage) if args.through_stage else len(stages) - 1
    if start > end:
        raise SystemExit("--from-stage must not be after --through-stage")

    for stage in stages[:start]:
        if not all(path.exists() for path in stage.outputs):
            raise SystemExit(f"cannot start from {args.from_stage}: prerequisite output for {stage.name} is missing")

    for stage in stages[start:end + 1]:
        missing_stage_inputs = [str(path) for path in stage.inputs if not path.exists()]
        if missing_stage_inputs:
            raise SystemExit(f"stage {stage.name} missing input: {', '.join(missing_stage_inputs)}")
        fingerprint = stage.fingerprint()
        previous = state["stages"].get(stage.name, {})
        if args.resume and previous.get("status") == "COMPLETED" and previous.get("fingerprint") == fingerprint and outputs_match(previous, stage.outputs):
            previous.update({"last_action": "REUSED", "checked_at": now()})
            print(f"SKIP {stage.name} (verified)")
            continue
        print(f"RUN {stage.name}")
        result = subprocess.run(stage.command, check=False, capture_output=True, text=True)
        if stage.capture_to and result.stdout:
            stage.capture_to.write_text(result.stdout, encoding="utf-8")
        record = {
            "status": "COMPLETED" if result.returncode == 0 else "FAILED",
            "fingerprint": fingerprint,
            "command": stage.command,
            "exit_code": result.returncode,
            "completed_at": now(),
            "last_action": "EXECUTED",
            "output_sha256": {str(path.resolve()): sha256(path) for path in stage.outputs if path.exists()},
        }
        if result.stderr:
            record["stderr"] = result.stderr[-4000:]
        state["stages"][stage.name] = record
        state["updated_at"] = now()
        write_json_atomic(state_path, state)
        if result.returncode != 0:
            print(result.stdout, end="", file=sys.stderr)
            print(result.stderr, end="", file=sys.stderr)
            return result.returncode
    write_json_atomic(state_path, state)
    print(f"PIPELINE COMPLETE through {stages[end].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
