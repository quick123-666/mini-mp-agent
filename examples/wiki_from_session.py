"""Generate LLM Wiki entries from OpenClaw session history.

Reads the latest N session JSONL files, extracts user/assistant messages,
and feeds them through mini-mp's sprint handler to write wiki entries.

Designed to be called by:
- OpenClaw cron (Knowledge Brain T1 style):  python examples/wiki_from_session.py
- Manual:                                  PYTHONPATH=. python examples/wiki_from_session.py --limit 3

Behaviour:
- Real LLM: writes rich wiki entries (dialogue + entities + topic)
- Mock LLM (E2E_MOCK=1 or no API key): writes structured stub entries to verify schema

CLI flags:
  --limit N        Process only the N most recent sessions (default 3)
  --session-dir D  Override session dir (default: %USERPROFILE%/.qclaw/agents/main/sessions)
  --wiki-root D    Override wiki output dir (default: ./wiki)
  --mock           Force mock LLM (overrides real LLM detection)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SESSION_DIR = Path(os.path.expanduser("~/.qclaw/agents/main/sessions"))
DEFAULT_WIKI_ROOT = ROOT / "wiki"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LLM Wiki from OpenClaw session history")
    p.add_argument("--limit", type=int, default=3, help="process only N most recent sessions")
    p.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR,
                   help="OpenClaw session dir containing <uuid>.jsonl")
    p.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT,
                   help="wiki output root")
    p.add_argument("--mock", action="store_true",
                   help="force mock LLM (graceful degradation)")
    return p.parse_args()


def _list_sessions(session_dir: Path, limit: int) -> list[Path]:
    """Return the N most recent .jsonl files (not .trajectory.jsonl), newest first."""
    if not session_dir.exists():
        return []
    sessions = [p for p in session_dir.glob("*.jsonl") if ".trajectory." not in p.name]
    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions[:limit]


def _extract_messages(jsonl_path: Path, max_chars: int = 4000) -> list[dict]:
    """Walk one .jsonl; return [{role, content, ts}] for user/assistant messages only.

    Truncates total content to max_chars to keep LLM prompt bounded.
    """
    out: list[dict] = []
    total = 0
    try:
        lines = jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") != "message":
            continue
        msg = rec.get("message", {})
        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        if not isinstance(content, str) or not content.strip():
            continue
        content = content.strip()
        if total + len(content) > max_chars:
            content = content[: max(0, max_chars - total)] + "...[truncated]"
        out.append({
            "role": role,
            "content": content,
            "ts": rec.get("timestamp", ""),
        })
        total += len(content)
        if total >= max_chars:
            break
    return out


def _build_task(session_id: str, messages: list[dict]) -> str:
    """Build a sprint-handler task prompt from one session's messages."""
    lines = [
        f"Analyze this OpenClaw session ({session_id}) and produce a wiki summary.",
        "",
        "For each non-trivial decision, fact, or procedure discussed, write a structured entry.",
        "Classify each as: entity (concept), topic (synthesis), or dialogue (raw transcript excerpt).",
        "Tag front-matter with: modes, l1_recipes, roles, and cross-reference related entries via [[wikilinks]].",
        "",
        "--- session transcript ---",
    ]
    for m in messages[-30:]:  # last 30 messages
        lines.append(f"\n[{m['role']} @ {m['ts']}]")
        lines.append(m["content"])
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    use_mock = args.mock or os.environ.get("E2E_MOCK", "0") == "1"

    from scripts.handlers import handle_sprint
    from scripts.llm_client import get_default_llm, has_real_llm

    sessions = _list_sessions(args.session_dir, args.limit)
    if not sessions:
        print(f"ERROR: no session .jsonl files found in {args.session_dir}")
        return 1

    llm = get_default_llm(force_mock=use_mock)
    backend = "mock (forced)" if use_mock else ("real" if has_real_llm() else "mock (auto-fallback)")
    print("=" * 60)
    print(f"WIKI FROM SESSION: {len(sessions)} session(s), backend={backend}")
    print(f"session dir: {args.session_dir}")
    print(f"wiki root  : {args.wiki_root}")
    print("=" * 60)

    args.wiki_root.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict] = []
    for sp in sessions:
        msgs = _extract_messages(sp)
        if not msgs:
            print(f"  [SKIP] {sp.name}: 0 messages")
            continue
        task = _build_task(sp.stem, msgs)
        print(f"  [RUN ] {sp.name}: {len(msgs)} messages, {len(task)} chars task")

        result = handle_sprint(task, llm=llm, wiki_root=args.wiki_root)
        wiki = result.get("wiki", {})
        summary_rows.append({
            "session": sp.stem,
            "ts": datetime.fromtimestamp(sp.stat().st_mtime).isoformat(timespec="seconds"),
            "messages": len(msgs),
            "mode": result.get("mode"),
            "pwr_iters": result.get("pwr", {}).get("iters_run", 0),
            "pwr_score": result.get("pwr", {}).get("final_score"),
            "wiki_dlg": wiki.get("dialogue_written", 0),
            "wiki_ent": wiki.get("entities_written", 0),
            "wiki_topic": wiki.get("topic_written", False),
        })

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if not summary_rows:
        print("(no sessions processed)")
        return 0
    keys = list(summary_rows[0].keys())
    print("| " + " | ".join(keys) + " |")
    print("|" + "|".join("---" for _ in keys) + "|")
    for r in summary_rows:
        print("| " + " | ".join(str(r.get(k, "")) for k in keys) + " |")

    wiki_total_dlg = sum(r["wiki_dlg"] for r in summary_rows)
    wiki_total_ent = sum(r["wiki_ent"] for r in summary_rows)
    wiki_total_topic = sum(1 for r in summary_rows if r["wiki_topic"])
    print()
    print(f"wiki totals: {wiki_total_dlg} dialogue + {wiki_total_ent} entities + {wiki_total_topic} topic")
    print(f"wiki root: {args.wiki_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
