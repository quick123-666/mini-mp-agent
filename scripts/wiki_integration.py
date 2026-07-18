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

    # 1. parse messages (kept for entities extraction only — no dialogue writes)
    messages = build_messages_from_pwr(task, pwr_result)
    entries = parse_messages(messages)

    # NOTE (v1.1.0): dialogue pages and individual entity pages are no
    # longer written here. The LLM Wiki redesign consolidates 1 session into
    # 1 topic page; entities are recorded as front-matter tags only. The
    # underlying write_dialogue / write_entity APIs in wiki_store are still
    # available for direct callers and tests, but the cron ingest path
    # (scripts/wiki_ingest.py) does not invoke them anymore.
    dialogue_written = 0
    entities_written = 0
    entities: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    # 2. extract entities for topic front-matter tags (no page writes)
    all_text = "\n".join(m["content"] for m in messages if m.get("content"))
    if all_text:
        entities = extract_entities(all_text)
        grouped = group_by_type(entities)
        entities_written = len({e["entity"].lower() for e in entities})

    # 3. optional topic — now the single page written per session, rich
    topic_written = False
    if write_topic_for:
        pwr_status = pwr_result.get("status", "unknown")
        iterations = len(pwr_result.get("iterations", []))
        # Top 10 entities (alphabetical), used both as front-matter tags
        # and as a "Entity tags" section so LCM can grep them.
        entity_tags = sorted({e["entity"] for e in entities})
        body = (
            f"# {write_topic_for}\n\n"
            f"**PWR status:** {pwr_status}  \n"
            f"**Iterations:** {iterations}  \n"
            f"**Modes:** {', '.join(modes or [])}  \n"
            f"**L1 recipes:** {', '.join(l1_recipes or [])}  \n"
            f"**Roles:** {', '.join(roles or [])}  \n"
            f"**Failure categories:** {', '.join(failure_categories or ['none'])}  \n\n"
            f"## Task\n\n{task[:4000]}\n\n"
            f"## Entity tags ({len(entity_tags)})\n\n"
            + (", ".join(f"`{t}`" for t in entity_tags) or "_none_")
            + "\n\n"
            f"## Source session\n\n"
            f"Raw session: `~/.qclaw/agents/main/sessions/<session-id>.jsonl`\n"
        )
        write_topic(
            root,
            slugify(write_topic_for) or "sprint-summary",
            body,
            metadata={"entity_tags": entity_tags} if entity_tags else None,
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
    # Auto-derive a topic title from the task if caller didn't pass one.
    # Sprint runs always benefit from a topic page (cross-cutting synthesis).
    # We strip the meta-prompt prefix so the topic title is the actual user request,
    # not "Analyze this OpenClaw session (...)".
    if not write_topic_for:
        text = (task or "").strip()
        # skip the "Analyze this OpenClaw session (...)..." meta lines
        # look for the first real content after "--- session transcript ---"
        if "--- session transcript ---" in text:
            text = text.split("--- session transcript ---", 1)[1]
        # take the first user message (up to 80 chars, one line)
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("[user"):
                # next non-empty line is the user content
                continue
            if line and not line.startswith("["):
                write_topic_for = line[:80]
                break
        if not write_topic_for:
            write_topic_for = "sprint-summary"
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
