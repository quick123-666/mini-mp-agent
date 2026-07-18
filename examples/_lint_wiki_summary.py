"""One-shot 8-step lint summary for the wiki dir passed as --root.

Usage:
  python examples/_lint_wiki_summary.py --root _daily_wiki

Designed for cron: prints a single line summary like
  LINT TOTAL: 906 (orphan=148 isolated=145 contradictions=592 mode_coverage=17 ...)
so the cron output is one line and easy to grep / alert on.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    p = argparse.ArgumentParser(description="8-step lint summary for a wiki root")
    p.add_argument("--root", type=Path, required=True, help="wiki root to lint")
    p.add_argument("--strict", action="store_true", help="exit 1 if TOTAL > 0")
    args = p.parse_args()

    if not args.root.exists():
        print(f"ERROR: {args.root} not found")
        return 1

    # Remove .lock files (in-place; they only block writers)
    for f in args.root.rglob("*.lock"):
        try:
            f.unlink()
        except OSError:
            pass

    from scripts.lint_wiki import lint_wiki
    from scripts.methods_tree import MethodsTree

    methods_tree = MethodsTree()
    report = lint_wiki(args.root, methods_tree=methods_tree)

    parts = []
    total = 0
    for step, issues in report.items():
        n = len(issues)
        total += n
        parts.append(f"{step}={n}")
    print(f"LINT TOTAL: {total} ({' '.join(parts)})")
    return 1 if (args.strict and total > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
