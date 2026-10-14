#!/usr/bin/env python3
"""Validate every standard eval suite and execute each deterministic local runner.

Scope warning, so the headline number is not mistaken for a stronger gate than it
is: suite validation here is a SCHEMA LINT over evals/evals.json. `expected_output`
is prose and is never compared against any produced output, so the "N eval cases"
figure measures manifest well-formedness, not behaviour. Behavioural assertions
live in the deterministic runners executed below and in
prototypes/skills/tests/ (run via `make test-skills`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REQUIRED_EVAL_FIELDS = frozenset({"id", "name", "prompt", "expected_output", "files"})


def skill_directories() -> list[Path]:
    """Return real Skill packages, excluding support directories."""
    return sorted(
        path
        for path in ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def validate_suite(skill_dir: Path) -> tuple[int, list[str]]:
    """Validate one evals/evals.json against the project-wide portable schema."""
    eval_path = skill_dir / "evals" / "evals.json"
    if not eval_path.is_file():
        return 0, [f"{skill_dir.name}: missing evals/evals.json"]

    try:
        payload: Any = json.loads(eval_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 0, [f"{skill_dir.name}: invalid JSON: {exc}"]

    errors: list[str] = []
    if not isinstance(payload, dict):
        return 0, [f"{skill_dir.name}: suite must be an object"]
    if payload.get("skill_name") != skill_dir.name:
        errors.append(f"{skill_dir.name}: skill_name must match directory")

    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        return 0, [*errors, f"{skill_dir.name}: evals must be a non-empty array"]

    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for index, evaluation in enumerate(evals):
        prefix = f"{skill_dir.name}.evals[{index}]"
        if not isinstance(evaluation, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        missing = REQUIRED_EVAL_FIELDS - evaluation.keys()
        if missing:
            errors.append(f"{prefix}: missing {sorted(missing)}")
            continue
        eval_id = str(evaluation["id"])
        name = evaluation["name"]
        if eval_id in seen_ids:
            errors.append(f"{prefix}: duplicate id {eval_id}")
        seen_ids.add(eval_id)
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{prefix}: name must be non-empty")
        elif name in seen_names:
            errors.append(f"{prefix}: duplicate name {name}")
        seen_names.add(name)
        for field in ("prompt", "expected_output"):
            if not isinstance(evaluation[field], str) or not evaluation[field].strip():
                errors.append(f"{prefix}: {field} must be non-empty")
        files = evaluation["files"]
        if not isinstance(files, list) or not all(
            isinstance(item, str) for item in files
        ):
            errors.append(f"{prefix}: files must be an array of paths")
            continue
        for relative_path in files:
            candidate = (skill_dir / relative_path).resolve()
            if skill_dir.resolve() not in candidate.parents or not candidate.is_file():
                errors.append(f"{prefix}: unresolved file {relative_path}")
    return len(evals), errors


def local_runners(skill_dirs: list[Path]) -> list[Path]:
    """Find deterministic eval runners without treating metadata-only suites as executed."""
    runners: list[Path] = []
    for skill_dir in skill_dirs:
        for name in ("test_evals.py", "run_evals.py"):
            candidate = skill_dir / "scripts" / name
            if candidate.is_file():
                runners.append(candidate)
    return runners


def run_local_runner(path: Path) -> str | None:
    """Execute one isolated deterministic runner and return an error, if any."""
    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT.parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return None
    detail = (result.stdout + "\n" + result.stderr).strip()
    return f"{path.relative_to(ROOT)} exited {result.returncode}:\n{detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema-only", action="store_true", help="skip deterministic runner execution"
    )
    args = parser.parse_args()

    skills = skill_directories()
    total_evals = 0
    errors: list[str] = []
    for skill_dir in skills:
        count, suite_errors = validate_suite(skill_dir)
        total_evals += count
        errors.extend(suite_errors)

    runners = local_runners(skills)
    schema_errors = list(errors)
    # Runners must execute even when a manifest fails to lint. Gating them on an
    # empty error list made a single schema typo silently skip every behavioural
    # check while the report showed only the typo.
    executed_runners = 0
    if not args.schema_only:
        for runner in runners:
            runner_error = run_local_runner(runner)
            executed_runners += 1
            if runner_error:
                errors.append(runner_error)

    if errors:
        print("FAIL: standard eval regression")
        for message in errors:
            print(f"- {message}")
        if schema_errors and not args.schema_only:
            print(
                f"({len(schema_errors)} schema error(s); "
                f"{executed_runners}/{len(runners)} runners still executed)"
            )
        return 1

    mode = (
        "schema lint only"
        if args.schema_only
        else "schema lint + deterministic runners"
    )
    print(
        f"PASS: {len(skills)} eval manifests linted, {total_evals} manifest cases, "
        f"{executed_runners} deterministic runners executed ({mode})"
    )
    print(
        "NOTE: manifest cases are schema-checked only; behavioural coverage comes "
        "from the runners above and prototypes/skills/tests (make test-skills)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
