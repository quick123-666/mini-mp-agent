"""Cron-driven LLM Wiki ingest for mini-mp-agent.

Replaces examples/wiki_from_session.py (now a thin wrapper).

Modes (mutually exclusive):
  --source cron-full   Scan ALL session JSONL files under $OPENCLAW_SESSIONS_DIR,
                       ingest any whose mtime > state['last_full_scan_mtime'].
  --source mem         Scan MEMORY.md; ingest new paragraphs (paragraph-level delta).
  --source session     Ingest a single session by --session-id.
  --source auto        (default) Decide based on cron hour: 23=full + mem, else mem + session.

After ingest, rebuild:
  llmwiki/index.md         (time-sorted list of all topics)
  llmwiki/timeline.md      (one-line summary per topic)
  llmwiki/by-project/*.md  (one file per project, lists all topics)

State lives in <wiki_root>/_state.json (atomic write, .tmp.<hex> + os.replace).
Cumulative: each run adds new topics without touching old ones.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent  # repo root (scripts/..)

# Tunables
SESSION_DIR = Path(os.environ.get(
    "OPENCLAW_SESSIONS_DIR",
    str(Path.home() / ".qclaw" / "agents" / "main" / "sessions"),
))
MEMORY_PATH = Path(os.environ.get(
    "OPENCLAW_MEMORY_PATH",
    str(Path.home() / ".qclaw" / "workspace" / "MEMORY.md"),
))
STATE_FILE_NAME = "_state.json"

# Heartbeat patterns (reuse from examples/wiki_from_session.py)
HEARTBEAT_PATTERNS = (
    "openclaw heartbeat",
    "automated heartbeat",
    "no action needed",
    "no action required",
    "no pending tasks",
    "no tasks pending",
    "system check",
    "health check",
    "no reply needed",
    "all systems operational",
)


def _now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write: .tmp.<hex> + os.replace (no torn writes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _load_state(wiki_root: Path) -> dict:
    state_path = wiki_root / STATE_FILE_NAME
    if not state_path.exists():
        return {
            "version": 1,
            "sessions": {},          # session_id -> mtime
            "memory": {"path": str(MEMORY_PATH), "last_line": 0},
            "last_full_scan_mtime": 0.0,
            "last_run_at": "",
        }
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(wiki_root: Path, state: dict) -> None:
    _atomic_write_json(wiki_root / STATE_FILE_NAME, state)


# ── Heartbeat / content helpers ────────────────────────────────────────────

def _is_heartbeat_session(messages: List[dict]) -> bool:
    """True if first user message matches heartbeat pattern."""
    for m in messages[:2]:
        if m.get("role") != "user":
            continue
        content = (m.get("content") or "").lower().strip()
        if not content:
            continue
        return any(p in content for p in HEARTBEAT_PATTERNS)
    return False


def _load_session_jsonl(path: Path) -> List[dict]:
    """Load messages from an OpenClaw session JSONL file.

    OpenClaw envelope shape (v3):
      {"type":"message","message":{"role":"user","content":"...","timestamp":...}}
      {"type":"session","version":3,"id":"...","timestamp":"..."}
      {"type":"model_change",...}   # skipped
      {"type":"thinking_level_change",...}  # skipped
      {"type":"custom",...}          # skipped
      {"type":"tool_result",...}     # included (role=tool)
    We normalize to a flat {role, content} list, dropping non-message types.
    """
    msgs: List[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"  [WARN] could not read {path.name}: {e}")
        return msgs
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") == "message":
            inner = obj.get("message") or {}
            role = inner.get("role", "")
            raw = inner.get("content", "")
            content = _flatten_content(raw)
            if role and content:
                msgs.append({"role": role, "content": content, "timestamp": inner.get("timestamp", "")})
        elif obj.get("type") == "tool_result":
            inner = obj.get("message") or {}
            content = _flatten_content(inner.get("content", ""))
            if content:
                msgs.append({"role": "tool", "content": content[:4000]})
    return msgs


def _flatten_content(raw: Any) -> str:
    """Normalize OpenClaw message content into a string.

    Content can be a plain string OR a list of {type, text} parts (e.g.
    [{"type":"text","text":"..."}, {"type":"toolCall","id":"..."}]).
    For tool calls, we record the tool name. For text, we keep the text.
    """
    if isinstance(raw, str):
        return raw.strip()
    if not isinstance(raw, list):
        return ""
    parts: List[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = item.get("type", "")
        if t == "text":
            text = (item.get("text") or "").strip()
            if text:
                parts.append(text)
        elif t == "toolCall":
            name = item.get("name") or item.get("toolName") or "tool"
            args = item.get("arguments") or item.get("input") or {}
            arg_str = json.dumps(args, ensure_ascii=False) if not isinstance(args, str) else args
            parts.append(f"[tool_call:{name}] {arg_str[:300]}")
        elif t == "toolResult":
            text = (item.get("text") or "").strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _build_task_text(messages: List[dict], max_chars: int = 16000) -> str:
    """Concatenate user + assistant messages into a task string for handle_sprint.

    Caps at max_chars (default 16000) to stay under LLM context. The first
    user message is always kept verbatim (so the topic title can derive from it).
    """
    parts = []
    first_user_seen = False
    for m in messages:
        role = m.get("role", "")
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "user" and not first_user_seen:
            parts.append(f"[user] {content}")
            first_user_seen = True
        elif role in ("user", "assistant"):
            parts.append(f"[{role}] {content}")
    text = "\n".join(parts)
    if len(text) > max_chars:
        # keep first user message + tail (most recent context)
        head = parts[0] if parts else ""
        tail_budget = max_chars - len(head) - 200
        text = head + "\n\n... [truncated middle] ...\n\n" + text[-tail_budget:]
    return text


# ── Ingest session ────────────────────────────────────────────────────────

def _ingest_one_session(
    session_path: Path,
    session_id: str,
    wiki_root: Path,
    real_llm: bool = True,
) -> Dict[str, Any]:
    """Run handle_sprint on a single session and let it write wiki files.

    Returns a summary dict for the cron run log.
    """
    from scripts.handlers import handle_sprint
    from scripts.llm_client import get_default_llm
    from scripts.wiki_store import init_wiki

    init_wiki(wiki_root)
    msgs = _load_session_jsonl(session_path)
    if not msgs:
        return {"session": session_id, "skipped": "empty"}

    if _is_heartbeat_session(msgs):
        return {"session": session_id, "skipped": "heartbeat"}

    task = _build_task_text(msgs)
    if not task:
        return {"session": session_id, "skipped": "no_task"}

    llm = get_default_llm() if real_llm else None
    result = handle_sprint(task, llm=llm, wiki_root=wiki_root)
    wiki = result.get("wiki", {}) or {}
    return {
        "session": session_id,
        "messages": len(msgs),
        "chars": len(task),
        "wiki_topic": wiki.get("topic_written", False),
        "wiki_dlg": wiki.get("dialogue_written", 0),
        "wiki_ent": wiki.get("entities_written", 0),
        "lint_total": sum(int(v) for v in (wiki.get("lint_summary") or {}).values()),
    }


# ── Index rebuilders ──────────────────────────────────────────────────────

def _read_topic_meta(wiki_root: Path) -> List[Dict[str, Any]]:
    """Read all llmwiki/topics/*.md front-matter + first heading."""
    import re as _re
    topics_dir = wiki_root / "topics"
    if not topics_dir.exists():
        return []
    out = []
    for md in sorted(topics_dir.glob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        # parse simple YAML-ish front-matter
        meta: Dict[str, Any] = {"_path": md, "_rel": md.relative_to(wiki_root).as_posix()}
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end > 0:
                block = text[3:end]
                for line in block.splitlines():
                    line = line.strip()
                    if not line or ":" not in line:
                        continue
                    k, _, v = line.partition(":")
                    v = v.strip()
                    # coerce list-like values (tags/decisions/...)
                    if v.startswith("[") and v.endswith("]"):
                        items = [
                            x.strip().strip('"').strip("'")
                            for x in v[1:-1].split(",")
                            if x.strip()
                        ]
                        meta[k.strip()] = items
                    else:
                        meta[k.strip()] = v.strip('"').strip("'")
                # extract a short summary from llm_summary: | block
                m = _re.search(r"llm_summary:\s*\|\s*\n((?:[ \t]+.*\n)+)", text)
                if m:
                    summary = " ".join(
                        ln.strip() for ln in m.group(1).splitlines()
                    )
                    meta["_summary"] = summary[:280]
        out.append(meta)
    return out


def _rebuild_index(wiki_root: Path) -> None:
    topics = _read_topic_meta(wiki_root)
    topics.sort(key=lambda m: m.get("created", ""), reverse=True)
    lines = ["# LLM Wiki Index\n", "_Auto-rebuilt by cron every 3h._\n",
             f"_Total topics: **{len(topics)}**_\n",
             "\n## Topics (newest first)\n"]
    for m in topics:
        rel = m.get("_rel", "")
        title = m.get("slug", rel)
        created = m.get("created", "")
        n_msgs = m.get("messages", "?")
        tags = m.get("tags") or []
        tag_str = " " + " ".join(f"`{t}`" for t in tags[:5]) if tags else ""
        lines.append(f"- **{created}** &middot; [{title}]({rel}) &middot; {n_msgs} msgs{tag_str}")
    _atomic_write_json_or_text(wiki_root / "index.md", "\n".join(lines) + "\n")


def _rebuild_timeline(wiki_root: Path) -> None:
    topics = _read_topic_meta(wiki_root)
    topics.sort(key=lambda m: m.get("created", ""), reverse=True)
    lines = ["# Timeline\n", "_One line per topic, newest first._\n"]
    for m in topics:
        created = m.get("created", "?")[:19]
        rel = m.get("_rel", "")
        summary = m.get("_summary", "")
        if not summary:
            # fall back to first non-empty line of body
            text = m["_path"].read_text(encoding="utf-8", errors="replace")
            for ln in text.splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#") and not ln.startswith("---") and not ln.startswith("-"):
                    summary = ln[:200]
                    break
        lines.append(f"- **{created}** [{m.get('slug', rel)}]({rel}): {summary}")
    _atomic_write_json_or_text(wiki_root / "timeline.md", "\n".join(lines) + "\n")


def _rebuild_by_project(wiki_root: Path) -> None:
    topics = _read_topic_meta(wiki_root)
    by_proj: Dict[str, List[Dict[str, Any]]] = {}
    for m in topics:
        projects = m.get("projects") or ["(uncategorized)"]
        for p in projects:
            p = p.strip()
            if not p:
                continue
            by_proj.setdefault(p, []).append(m)
    out_dir = wiki_root / "by-project"
    out_dir.mkdir(parents=True, exist_ok=True)
    # remove stale project files (projects with no current topics)
    existing = {p.name.removesuffix(".md") for p in out_dir.glob("*.md")}
    wanted = set(by_proj.keys())
    for stale in existing - wanted:
        (out_dir / f"{stale}.md").unlink(missing_ok=True)
    for project, items in by_proj.items():
        items.sort(key=lambda m: m.get("created", ""), reverse=True)
        lines = [
            f"# Project: {project}\n",
            f"_Topics referencing `{project}`: **{len(items)}**_\n",
            "\n## Topics\n",
        ]
        for m in items:
            rel = m.get("_rel", "")
            created = m.get("created", "?")[:19]
            summary = m.get("_summary", "")
            lines.append(f"- **{created}** [{m.get('slug', rel)}]({rel}): {summary}")
        _atomic_write_json_or_text(out_dir / f"{project}.md", "\n".join(lines) + "\n")


def _atomic_write_json_or_text(path: Path, text: str) -> None:
    """Write text atomically. .tmp.<hex> + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _rebuild_all_indexes(wiki_root: Path) -> None:
    _rebuild_index(wiki_root)
    _rebuild_timeline(wiki_root)
    _rebuild_by_project(wiki_root)


# ── Main entry: cron-full scan ────────────────────────────────────────────

def _scan_cron_full(wiki_root: Path, state: dict, real_llm: bool, limit: int) -> List[dict]:
    if not SESSION_DIR.exists():
        print(f"[WARN] session dir not found: {SESSION_DIR}")
        return []
    results: List[dict] = []
    last_full_mtime = state.get("last_full_scan_mtime", 0.0)
    candidates: List[Tuple[float, Path]] = []
    for sp in SESSION_DIR.glob("*.jsonl"):
        try:
            mt = sp.stat().st_mtime
        except OSError:
            continue
        if mt > last_full_mtime:
            candidates.append((mt, sp))
    candidates.sort(reverse=True)
    if limit > 0:
        candidates = candidates[:limit]
    print(f"  cron-full: {len(candidates)} candidate(s) (mtime > {last_full_mtime:.0f})")
    for mt, sp in candidates:
        sid = sp.stem
        if sid in state["sessions"] and state["sessions"][sid] >= mt:
            continue
        print(f"  [RUN ] {sp.name}")
        try:
            r = _ingest_one_session(sp, sid, wiki_root, real_llm=real_llm)
        except Exception as e:
            r = {"session": sid, "error": str(e)[:200]}
        results.append(r)
        if "error" not in r:
            state["sessions"][sid] = mt
    if candidates:
        new_max = max(mt for mt, _ in candidates)
        state["last_full_scan_mtime"] = max(last_full_mtime, new_max)
    return results


# ── Main entry: MEMORY.md paragraph-level delta ───────────────────────────

def _scan_memory(wiki_root: Path, state: dict, real_llm: bool) -> List[dict]:
    if not MEMORY_PATH.exists():
        return []
    mem_state = state.setdefault("memory", {"path": str(MEMORY_PATH), "last_line": 0})
    if mem_state.get("path") != str(MEMORY_PATH):
        # path changed — reset
        mem_state = {"path": str(MEMORY_PATH), "last_line": 0}
        state["memory"] = mem_state
    try:
        text = MEMORY_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"[WARN] cannot read MEMORY: {e}")
        return []
    lines = text.splitlines()
    last = int(mem_state.get("last_line", 0))
    new_lines = lines[last:]
    if not new_lines:
        return []
    # Find new ## YYYY-MM-DD：headers and ingest as 'topic' pages (skipping
    # ones that look like tables/short lines). Each new section becomes one
    # topic page.
    results: List[dict] = []
    section_re = re.compile(r"^## (\d{4}-\d{2}-\d{2})[:：]\s*(.+)$")
    pending: List[Tuple[str, str, List[str]]] = []  # (date, title, body_lines)
    current: Optional[Tuple[str, str, List[str]]] = None
    for ln in new_lines:
        m = section_re.match(ln.strip())
        if m:
            if current is not None:
                pending.append(current)
            current = (m.group(1), m.group(2).strip(), [])
        else:
            if current is not None:
                current[2].append(ln)
    if current is not None:
        pending.append(current)
    for date, title, body in pending:
        if not body or len(body) < 3:
            continue
        body_text = "\n".join(body).strip()
        results.append({
            "mem_section": f"{date}: {title}",
            "chars": len(body_text),
            "ingested": True,
        })
        # Write directly as a topic page (no LLM call — MEMORY is already curated)
        slug = re.sub(r"[^A-Za-z0-9._-]+", "-", title.lower())[:60].strip("-") or "section"
        topic_path = wiki_root / "topics" / f"{date}-{slug}.md"
        text_out = (
            "---\n"
            f"slug: {date}-{slug}\n"
            "type: topic\n"
            f"created: {date}T00:00:00\n"
            "source: memory\n"
            f"title: {title}\n"
            "tags: [memory, curated]\n"
            "llm_summary: |\n"
            f"  {body_text[:600].replace(chr(10), ' ')}\n"
            "---\n\n"
            f"# {title} ({date})\n\n"
            "## Source\n\n"
            f"```\n{body_text}\n```\n"
        )
        _atomic_write_json_or_text(topic_path, text_out)
    mem_state["last_line"] = len(lines)
    return results


# ── CLI entry ─────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(description="LLM Wiki ingest (cron-friendly)")
    p.add_argument("--wiki-root", type=Path,
                   default=ROOT / "llmwiki",
                   help="wiki output root (default: ./llmwiki)")
    p.add_argument("--source", choices=["auto", "cron-full", "mem", "session"],
                   default="auto")
    p.add_argument("--session-id", type=str, default="",
                   help="--source session: which session to ingest")
    p.add_argument("--limit", type=int, default=0,
                   help="max sessions to process (0 = all)")
    p.add_argument("--mock", action="store_true",
                   help="use mock LLM (no API key needed)")
    p.add_argument("--no-skip", action="store_true",
                   help="re-process everything (ignore state)")
    args = p.parse_args()

    args.wiki_root.mkdir(parents=True, exist_ok=True)
    state = {} if args.no_skip else _load_state(args.wiki_root)
    state.setdefault("version", 1)
    state.setdefault("sessions", {})
    state.setdefault("memory", {"path": str(MEMORY_PATH), "last_line": 0})
    state.setdefault("last_full_scan_mtime", 0.0)

    real_llm = not args.mock
    sources = (["cron-full", "mem"] if args.source == "auto" else [args.source])

    all_results: List[dict] = []
    for src in sources:
        print(f"=== source: {src} ===")
        if src == "cron-full":
            r = _scan_cron_full(args.wiki_root, state, real_llm, args.limit)
        elif src == "mem":
            r = _scan_memory(args.wiki_root, state, real_llm)
        elif src == "session":
            if not args.session_id:
                print("[ERR] --session-id required for --source session")
                return 2
            sp = SESSION_DIR / f"{args.session_id}.jsonl"
            if not sp.exists():
                print(f"[ERR] session not found: {sp}")
                return 2
            r = [_ingest_one_session(sp, args.session_id, args.wiki_root, real_llm)]
            state["sessions"][args.session_id] = sp.stat().st_mtime
        else:
            r = []
        all_results.extend(r)

    state["last_run_at"] = _now_iso()
    _save_state(args.wiki_root, state)
    _rebuild_all_indexes(args.wiki_root)

    print()
    print("=== SUMMARY ===")
    for r in all_results:
        if r.get("skipped"):
            print(f"  [SKIP] {r.get('session', '?')}: {r['skipped']}")
        elif r.get("error"):
            print(f"  [ERR ] {r.get('session', '?')}: {r['error']}")
        else:
            print(f"  [OK  ] {r}")
    print(f"  total: {len(all_results)} result(s); state saved to {args.wiki_root / STATE_FILE_NAME}")
    print(f"  indexes rebuilt: index.md, timeline.md, by-project/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
