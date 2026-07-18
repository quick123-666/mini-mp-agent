"""Phase 6: Wiki integration for sprint handler.

After PWR Loop completes, persist artifacts to the wiki:
1. Parse the task message → write_dialogue
2. Extract entities → write_entity for each
3. Optionally write_topic for cross-cutting synthesis
4. Run lint_wiki at the end

The wiki lives at `<root>/wiki/` by default; can be overridden.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional, List, Dict

from .wiki_store import (
    init_wiki,
    write_dialogue,
    write_entity,
    write_topic,
    search,
    list_all,
)
from .dialogue_parser import parse_messages, group_by_intent, slugify
from .entity_extractor import extract_entities, group_by_type
from .lint_wiki import lint_wiki, lint_summary


def build_messages_from_pwr(task: str, pwr_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert a PWR result dict into a list of messages for wiki parsing.

    Each iteration becomes 2 messages (assistant work + reviewer feedback).
    """
    messages = [{"role": "user", "content": task, "ts": datetime.now().isoformat(timespec="seconds")}]
    for i, it in enumerate(pwr_result.get("iterations", [])):
        ts = it.get("ts") or datetime.now().isoformat(timespec="seconds")
        if it.get("planner"):
            messages.append({"role": "assistant", "content": it["planner"], "ts": ts})
        if it.get("worker"):
            messages.append({"role": "assistant", "content": it["worker"], "ts": ts})
        if it.get("reviewer"):
            messages.append({"role": "assistant", "content": it["reviewer"], "ts": ts})
        if it.get("reflection"):
            messages.append({"role": "assistant", "content": it["reflection"], "ts": ts})
    return messages


def persist_to_wiki(
    root: Path,
    task: str,
    pwr_result: Dict[str, Any],
    *,
    write_topic_for: Optional[str] = None,
    modes: Optional[List[str]] = None,
    l1_recipes: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    failure_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Persist a PWR run into the wiki with method-tree classification.

    Args:
        root: wiki root directory
        task: the original user task
        pwr_result: PWRResult.to_dict() output
        write_topic_for: if provided, write a topic page with this slug
        modes: L0 modes to tag every entry with (e.g. ['m_sprint'])
        l1_recipes: L1 recipes that ran (e.g. ['plan_task', 'execute_task'])
        roles: roles that participated (e.g. ['planner', 'worker'])
        failure_categories: failure classes if reflection occurred

    All classification fields propagate to front-matter + cache + index.

    Returns:
        {
            "dialogue_written": N,
            "entities_written": N,
            "topic_written": bool,
            "lint_summary": {...},
        }
    """
    root = Path(root)
    if not (root / "index.md").exists():
        init_wiki(root)

    # 1. parse messages
    messages = build_messages_from_pwr(task, pwr_result)
    entries = parse_messages(messages)

    # 2. write dialogues
    dialogue_written = 0
    for e in entries:
        content = (
            f"## {e['role']}\n\n"
            f"{e['content']}\n\n"
            f"**Intent:** {e['intent']}  \n"
            f"**Keywords:** {', '.join(e['keywords'])}\n"
        )
        write_dialogue(
            root,
            e["slug"],
            content,
            metadata={"ts": e["ts"]},
            modes=modes,
            l1_recipes=l1_recipes,
            roles=roles,
            failure_categories=failure_categories,
        )
        dialogue_written += 1

    # 3. extract entities from all messages
    all_text = "\n".join(m["content"] for m in messages if m.get("content"))
    entities = extract_entities(all_text)
    grouped = group_by_type(entities)

    entities_written = 0
    seen_slugs = set()
    for e in entities:
        if e["entity"].lower() in seen_slugs:
            continue
        seen_slugs.add(e["entity"].lower())
        slug = slugify(e["entity"])
        if not slug:
            continue
        # build a small entity page
        body = (
            f"# {e['entity']}\n\n"
            f"**Type:** {e['type']}  \n"
            f"**Confidence:** {e['confidence']}  \n\n"
            f"Extracted from task: _{task[:100]}_\n\n"
            f"Related: see wiki index.\n"
        )
        write_entity(
            root,
            slug,
            body,
            modes=modes,
            l1_recipes=l1_recipes,
            roles=roles,
            failure_categories=failure_categories,
        )
        entities_written += 1

    # 4. optional topic
    topic_written = False
    if write_topic_for:
        # Build a brief topic page summarizing the run
        pwr_status = pwr_result.get("status", "unknown")
        iterations = len(pwr_result.get("iterations", []))
        body = (
            f"# {write_topic_for}\n\n"
            f"**PWR status:** {pwr_status}  \n"
            f"**Iterations:** {iterations}  \n"
            f"**Modes:** {', '.join(modes or [])}  \n"
            f"**L1 recipes:** {', '.join(l1_recipes or [])}  \n"
            f"**Roles:** {', '.join(roles or [])}  \n\n"
            f"## Task\n\n{task}\n\n"
            f"## Entities\n\n"
            + "\n".join(f"- {e['entity']} ({e['type']})" for e in entities[:10])
            + "\n"
        )
        write_topic(
            root,
            slugify(write_topic_for) or "sprint-summary",
            body,
            modes=modes,
            l1_recipes=l1_recipes,
            roles=roles,
            failure_categories=failure_categories,
        )
        topic_written = True

    # 5. lint with method coverage (Phase 7+)
    try:
        from .methods_tree import MethodsTree
        methods_tree = MethodsTree()
        issues = lint_wiki(root, methods_tree=methods_tree)
    except Exception:
        # Fallback if methods_tree fails to load (e.g. in tests)
        issues = lint_wiki(root)
    summary = lint_summary(issues)

    return {
        "wiki_root": str(root),
        "dialogue_written": dialogue_written,
        "entities_written": entities_written,
        "topic_written": topic_written,
        "lint_summary": summary,
        "entity_count_by_type": {k: len(v) for k, v in grouped.items()},
        "classification": {
            "modes": modes or [],
            "l1_recipes": l1_recipes or [],
            "roles": roles or [],
            "failure_categories": failure_categories or [],
        },
    }


def persist_to_wiki_from_pwr(
    root: Path,
    task: str,
    pwr_result_dict: Dict[str, Any],
    *,
    write_topic_for: Optional[str] = None,
) -> Dict[str, Any]:
    """Auto-derive classification from a PWRResult dict and persist.

    Inspects PWRResult.iterations to determine which L1 recipes ran and
    which roles participated. Sets failure_categories if any iteration
    has a reflection.
    """
    iterations = pwr_result_dict.get("iterations", []) or []
    recipes: List[str] = []
    roles: set[str] = set()
    has_reflection = False
    for it in iterations:
        for key in ("planner", "worker", "reviewer", "reflection"):
            if it.get(key):
                if key == "reflection":
                    has_reflection = True
                else:
                    # role name = which L1 recipe was run
                    recipe_id = f"{key}_task"
                    if recipe_id not in recipes:
                        recipes.append(recipe_id)
                    roles.add(key)
    return persist_to_wiki(
        root,
        task,
        pwr_result_dict,
        write_topic_for=write_topic_for,
        modes=["m_sprint"],  # sprint handler default
        l1_recipes=recipes or None,
        roles=sorted(roles) or None,
        failure_categories=["reflect_triggered"] if has_reflection else None,
    )


# ---------- Sprint handler integration ----------

def wiki_integration_step(root: Path, task: str, pwr_result: Dict[str, Any]) -> Dict[str, Any]:
    """The integration step called by sprint handler after PWR completes.

    Uses persist_to_wiki_from_pwr so modes/l1_recipes/roles are auto-derived
    from the PWRResult (8-step lint mode_coverage passes).
    """
    try:
        return persist_to_wiki_from_pwr(root, task, pwr_result)
    except Exception as e:
        return {"error": str(e), "wiki_root": str(root)}


if __name__ == "__main__":
    import json
    import tempfile
    import sys

    sample_pwr = {
        "status": "success",
        "iterations": [
            {"planner": "Step 1: analyze", "worker": "Did it", "reviewer": "Score: 0.9"},
        ],
    }

    with tempfile.TemporaryDirectory() as tmp:
        result = persist_to_wiki(Path(tmp) / "wiki", "ship Plan F v8.1", sample_pwr, write_topic_for="plan-f-ship")
        print(json.dumps(result, ensure_ascii=False, indent=2))
