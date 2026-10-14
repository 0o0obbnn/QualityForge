from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]
LOCAL_TERMS_FILE = Path(__file__).resolve().parent / "banned_terms.local.txt"

# 词表两级加载：banned_terms.local.txt（gitignored，存放真实敏感词，仅本地存在，
# 不随仓库分发）；文件缺失时回退到下方演示词表，保证公开克隆仍能验证扫描机制本身。
# 格式：每行「显示名<TAB>正则」，# 开头为注释。
FALLBACK_TERMS = [
    ("ZZDEMO_SENTINEL", r"ZZDEMO_SENTINEL"),
]


def _load_terms() -> list[tuple[str, str]]:
    if LOCAL_TERMS_FILE.exists():
        terms: list[tuple[str, str]] = []
        for line in LOCAL_TERMS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            display, _, pattern = line.partition("\t")
            terms.append((display, pattern.strip() or display))
        if terms:
            return terms
    return FALLBACK_TERMS


FORBIDDEN_TERMS = _load_terms()

SCANNED_GLOBS = [
    "qa-requirement-review/scripts/*.py",
    "qa-requirement-review/references/*.md",
    "qa-requirement-review/SKILL.md",
    "requirement-function-mapping/scripts/*.py",
    "requirement-function-mapping/references/*.md",
    "requirement-function-mapping/SKILL.md",
]


class NoProjectSpecificTermsTests(unittest.TestCase):
    def test_scripts_and_contracts_contain_no_project_terms(self) -> None:
        # 机制自检：词表非空且首个词条的正则能命中其显示名（防止空词表假绿）。
        self.assertGreater(len(FORBIDDEN_TERMS), 0)
        display, pattern = FORBIDDEN_TERMS[0]
        self.assertRegex(f"x{display}x", pattern)

        violations: list[str] = []
        for pattern_glob in SCANNED_GLOBS:
            for path in sorted(SKILLS_ROOT.glob(pattern_glob)):
                text = path.read_text(encoding="utf-8")
                for term, term_pattern in FORBIDDEN_TERMS:
                    for match in re.finditer(term_pattern, text):
                        line_no = text.count("\n", 0, match.start()) + 1
                        violations.append(
                            f"{path.relative_to(SKILLS_ROOT)}:{line_no} 「{term}」"
                        )
        self.assertEqual(
            violations, [], "检测到项目特定词汇泄漏：\n" + "\n".join(violations)
        )


if __name__ == "__main__":
    unittest.main()
