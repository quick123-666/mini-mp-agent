"""Run the 7+1-step wiki lint on the seed wiki and pretty-print.

Run after wiki_seed_demo.py:
  PYTHONPATH=. python examples/wiki_seed_demo.py
  PYTHONPATH=. python examples/wiki_lint_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.lint_wiki import lint_wiki

WIKI_ROOT = ROOT / "_seed_wiki"


def main():
    if not WIKI_ROOT.exists():
        print(f"ERROR: {WIKI_ROOT} does not exist. Run wiki_seed_demo.py first.")
        return 1

    print("=" * 60)
    print(f"LINT WIKI: {WIKI_ROOT}")
    print("=" * 60)

    report = lint_wiki(WIKI_ROOT)

    total_issues = 0
    step_status = {}
    for step, issues in report.items():
        n = len(issues)
        total_issues += n
        status = "OK" if n == 0 else "ISSUES"
        step_status[step] = (status, n)
        print(f"  [{status:6}] {step:25} {n:3} issues")

    print()
    print(f"TOTAL: {total_issues} issues across 8 steps")

    if total_issues == 0:
        print()
        print("ALL 8 STEPS PASS — wiki is clean and properly classified")
    else:
        print()
        print("Issues by step:")
        for step, (status, n) in step_status.items():
            if n > 0:
                print(f"\n  {step} ({n}):")
                for issue in report[step][:5]:
                    print(f"    - {issue}")
                if len(report[step]) > 5:
                    print(f"    ... and {len(report[step]) - 5} more")

    return 0 if total_issues == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
