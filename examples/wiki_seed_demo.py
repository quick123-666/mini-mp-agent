"""Seed demo wiki with 5 cross-referenced entries covering all 3 categories.

Run: PYTHONPATH=. python examples/wiki_seed_demo.py
Then: PYTHONPATH=. python examples/wiki_lint_demo.py
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.wiki_store import init_wiki
from scripts.atomic_write import atomic_write

WIKI_ROOT = ROOT / "_seed_wiki"

# Wipe + recreate
if WIKI_ROOT.exists():
    shutil.rmtree(WIKI_ROOT)
init_wiki(WIKI_ROOT)

NOW = datetime.now().isoformat(timespec="microseconds")


def _ts(offset_s: int = 0) -> str:
    """Return an ISO timestamp offset by N seconds from NOW (microsecond precision)."""
    from datetime import timedelta
    return (datetime.fromisoformat(NOW) + timedelta(seconds=offset_s)).isoformat(timespec="microseconds")


def entry(slug: str, type_: str, body: str, **front) -> str:
    """Render one wiki entry with front-matter. Caller MUST pass `created=` to avoid lint dups."""
    lines = [f"---", f"slug: {slug}", f"type: {type_}"]
    for k, v in front.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines += ["---", "", body, ""]
    return "\n".join(lines)


# ---------- 5 entries, 3 categories, cross-referenced ----------

# 1. entity: PWR loop concept
atomic_write(WIKI_ROOT / "entities" / "pwr-loop.md", entry(
    "pwr-loop", "entity",
    "PWR = Plan → Work → Review → Reflect. A 4-phase loop for executing tasks.\n\n"
    "Each phase is a different `SYSTEM_PROMPT` role. The loop iterates until the\n"
    "review score meets the threshold or `max_iter` is hit.\n\n"
    "Related: [[work-method-tree]] describes what the loop consumes. "
    "[[scoring-formula]] gates the loop. [[add-a-recipe]] extends the loop with new tools.",
    created=_ts(0),
    modes=["m_auto", "m_sprint"],
    l1_recipes=["plan_task", "execute_task", "review_task", "reflect_task"],
    roles=["planner", "worker", "reviewer", "reflector"],
))

# 2. entity: work method tree concept
atomic_write(WIKI_ROOT / "entities" / "work-method-tree.md", entry(
    "work-method-tree", "entity",
    "The 4-level work method tree is the source of truth for what tools exist.\n\n"
    "L0 mode · L1 recipe · L2 sub-step · L3 primitive. 18 nodes total, validated\n"
    "by `tree.validate()`. Adding a method = adding a YAML file.\n\n"
    "See also: [[pwr-loop]] consumes L1 recipes. "
    "[[add-a-recipe]] is the canonical procedure for extending the tree. "
    "[[fix-lint-failures]] shows how to keep the wiki that documents it healthy.",
    created=_ts(1),
    modes=["m_task", "m_auto"],
    l1_recipes=["decompose_task", "execute_task"],
    roles=["planner", "worker", "tree_linter"],
))

# 3. topic: scoring formula synthesis
atomic_write(WIKI_ROOT / "topics" / "scoring-formula.md", entry(
    "scoring-formula", "topic",
    "Reviewer scores output on 0.0-1.0 scale. Loop terminates when\n"
    "score >= 0.80 or `max_iter` reached (default 3).\n\n"
    "Score = LLM numeric reply parsed from response, fallback 0.5 if no number found.\n\n"
    "Used in: [[pwr-loop]] review phase. See [[fix-lint-failures]] for what to do when scoring is wrong.",
    created=_ts(2),
    modes=["m_auto", "m_sprint", "m_review"],
    l1_recipes=["review_task"],
    roles=["reviewer"],
))

# 4. dialogue: how to add a new recipe (procedure-style)
atomic_write(WIKI_ROOT / "dialogue" / "add-a-recipe.md", entry(
    "add-a-recipe", "dialogue",
    "Steps to add a new method to the work tree:\n\n"
    "1. Create `methods/recipes/<node_id>.yaml` with required fields:\n"
    "   - `node_id`, `name`, `level` (1/2/3), `purpose`\n"
    "   - `inputs`, `outputs`, `dependencies`\n"
    "   - `selector_keywords` (mix of EN + ZH)\n"
    "2. Add edge in `methods/_meta/graph.json`\n"
    "3. Run `python scripts/methods_tree.py validate` -- must pass\n"
    "4. Run tests: `python tests/test_methods_tree.py`\n\n"
    "No Python change required if the recipe is pure YAML.\n\n"
    "See: [[work-method-tree]] for the overall structure. "
    "If the new recipe writes wiki entries, also read [[fix-lint-failures]].",
    created=_ts(3),
    modes=["m_task"],
    l1_recipes=["plan_task", "execute_task"],
    roles=["planner", "worker"],
))

# 5. dialogue: how to interpret a lint failure (procedure-style)
atomic_write(WIKI_ROOT / "dialogue" / "fix-lint-failures.md", entry(
    "fix-lint-failures", "dialogue",
    "Common wiki lint failures and fixes:\n\n"
    "- `orphan` (dialogue unreferenced): add a wikilink to a related entry\n"
    "- `isolated` (entity no inbound): link to it from at least one dialogue/topic\n"
    "- `broken_wikilinks` (target missing): create the target entry, or fix typo\n"
    "- `mode_coverage` (entry has no classification): add `modes:` and `l1_recipes:`\n"
    "  fields to front-matter\n\n"
    "Run `python examples/wiki_lint_demo.py` to see all 8 steps.\n\n"
    "Related: [[pwr-loop]] writes dialogue. [[scoring-formula]] gates it. "
    "[[add-a-recipe]] adds new methods that may need linting.",
    created=_ts(4),
    modes=["m_sprint"],
    l1_recipes=["lint_wiki", "score_output"],
    roles=["reviewer"],
))


# ---------- Top-level index & log ----------

index_lines = ["# Wiki Index\n",
               "| slug | type | created | modes |",
               "|------|------|---------|-------|"]
for md_path in sorted((WIKI_ROOT / "entities").glob("*.md")):
    index_lines.append(f"| {md_path.stem} | entity | {NOW} | m_task, m_auto |")
for md_path in sorted((WIKI_ROOT / "topics").glob("*.md")):
    index_lines.append(f"| {md_path.stem} | topic | {NOW} | m_auto, m_sprint |")
for md_path in sorted((WIKI_ROOT / "dialogue").glob("*.md")):
    index_lines.append(f"| {md_path.stem} | dialogue | {NOW} | m_task, m_sprint |")
atomic_write(WIKI_ROOT / "index.md", "\n".join(index_lines) + "\n")

with open(WIKI_ROOT / "log.md", "a", encoding="utf-8") as f:
    f.write(f"\n## {NOW} -- seed: 5 entries (2 entities + 1 topic + 2 dialogues), 11 wikilinks\n")

with open(WIKI_ROOT / "log.md", "a", encoding="utf-8") as f:
    f.write(f"\n## {_ts(6)} -- seed complete: lint expected 0 issues on all 8 steps\n")

print("=" * 60)
print("WIKI SEEDED")
print("=" * 60)
print(f"root: {WIKI_ROOT}")
print(f"entities/  : {len(list((WIKI_ROOT / 'entities').glob('*.md')))}")
print(f"topics/    : {len(list((WIKI_ROOT / 'topics').glob('*.md')))}")
print(f"dialogue/  : {len(list((WIKI_ROOT / 'dialogue').glob('*.md')))}")
print()
print("Next: PYTHONPATH=. python examples/wiki_lint_demo.py")
