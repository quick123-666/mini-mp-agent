"""Generate LLM Wiki entries from OpenClaw session history (cumulative).

Reads the latest N session JSONL files (skipping ones already indexed),
extracts user/assistant messages, and feeds them through mini-mp's sprint
handler to write wiki entries that accumulate across runs.

Designed to be called by:
- OpenClaw cron (Knowledge Brain T1 style):  python examples/wiki_from_session.py
- Manual:                                  PYTHONPATH=. python examples/wiki_from_session.py --limit 3

Behaviour:
- Real LLM: writes rich wiki entries (dialogue + entities + topic) with cross-refs
- Mock LLM (E2E_MOCK=1 or no API key): writes structured stub entries to verify schema

Cumulative index:
- Tracks processed sessions in <wiki_root>/.index_state.json (session_id -> mtime)
- Skips sessions whose mtime hasn't changed since last successful run
- Lets daily cron accumulate knowledge without re-processing old sessions

CLI flags:
  --limit N        Process only the N most recent NEW sessions (default 5)
  --session-dir D  Override session dir (default: %USERPROFILE%/.qclaw/agents/main/sessions)
  --wiki-root D    Override wiki output dir (default: ./wiki)
  --mock           Force mock LLM (overrides real LLM detection)
  --no-skip        Process all matching sessions (ignore .index_state.json)
  --max-chars N    Max chars of session transcript to feed LLM (default 16000)
  --max-messages N Max messages per session (default 50)
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
STATE_FILE_NAME = ".index_state.json"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LLM Wiki from OpenClaw session history (cumulative)")
    p.add_argument("--limit", type=int, default=5, help="process only N most recent NEW sessions")
    p.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR,
                   help="OpenClaw session dir containing <uuid>.jsonl")
    p.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT,
                   help="wiki output root")
    p.add_argument("--mock", action="store_true",
                   help="force mock LLM (graceful degradation)")
    p.add_argument("--no-skip", action="store_true",
                   help="process all matching sessions (ignore cumulative index)")
    p.add_argument("--max-chars", type=int, default=16000,
                   help="max chars of session transcript to feed LLM (default 16000)")
    p.add_argument("--max-messages", type=int, default=50,
                   help="max messages per session (default 50)")
    return p.parse_args()


def _list_sessions(session_dir: Path, limit: int) -> list[Path]:
    """Return the N most recent .jsonl files (not .trajectory.jsonl), newest first."""
    if not session_dir.exists():
        return []
    sessions = [p for p in session_dir.glob("*.jsonl") if ".trajectory." not in p.name]
    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions[:limit]


def _load_state(wiki_root: Path) -> dict:
    """Load cumulative index state. Returns {session_id: mtime_iso}."""
    state_path = wiki_root / STATE_FILE_NAME
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(wiki_root: Path, state: dict) -> None:
    """Persist cumulative index state (atomic)."""
    state_path = wiki_root / STATE_FILE_NAME
    try:
        from scripts.atomic_write import atomic_write
        atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2))
    except Exception:
        # Fallback: best-effort plain write
        try:
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass


def _filter_new(sessions: list[Path], state: dict) -> list[Path]:
    """Drop sessions whose (id, mtime) is already in state."""
    new = []
    for p in sessions:
        mtime = p.stat().st_mtime
        prev = state.get(p.stem)
        if prev is not None:
            try:
                if abs(float(prev) - mtime) < 1.0:
                    continue
            except (TypeError, ValueError):
                pass
        new.append(p)
    return new


def _extract_messages(jsonl_path: Path, max_chars: int, max_messages: int) -> list[dict]:
    """Walk one .jsonl; return [{role, content, ts}] for user/assistant messages only.

    Truncates total content to max_chars to keep LLM prompt bounded.
    Caps at max_messages to keep per-session cost bounded.
    """
    out: list[dict] = []
    total = 0
    try:
        lines = jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        if len(out) >= max_messages:
            break
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
            remaining = max(0, max_chars - total)
            if remaining < 50:
                break
            content = content[:remaining] + "...[truncated]"
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
        f"Analyze this OpenClaw session ({session_id}) and produce a structured wiki summary.",
        "",
        "For each non-trivial item, write a wiki entry:",
        "- entity: a concept / tool / person / project mentioned",
        "- topic: a synthesis of a multi-step decision or pattern",
        "- dialogue: a verbatim transcript excerpt of a key exchange",
        "",
        "Tag front-matter with: modes=['m_sprint'], l1_recipes=['plan_task','execute_task','review_task'],",
        "roles=['planner','worker','reviewer']. Cross-reference related entries via [[wikilinks]].",
        "",
        "--- session transcript ---",
    ]
    for m in messages:
        lines.append(f"\n[{m['role']} @ {m['ts']}]")
        lines.append(m["content"])
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    use_mock = args.mock or os.environ.get("E2E_MOCK", "0") == "1"

    from scripts.handlers import handle_sprint
    from scripts.llm_client import get_default_llm, has_real_llm
    from scripts.wiki_store import init_wiki

    # Ensure wiki dir structure exists (cumulative state lives here too)
    init_wiki(args.wiki_root)

    state = {} if args.no_skip else _load_state(args.wiki_root)
    all_sessions = _list_sessions(args.session_dir, args.limit)
    sessions = all_sessions if args.no_skip else _filter_new(all_sessions, state)

    if not sessions:
        print("=" * 60)
        print("WIKI FROM SESSION: nothing new to process")
        print(f"  seen so far: {len(state)} sessions in {args.wiki_root / STATE_FILE_NAME}")
        print("=" * 60)
        return 0

    llm = get_default_llm(force_mock=use_mock)
    backend = "mock (forced)" if use_mock else ("real" if has_real_llm() else "mock (auto-fallback)")
    print("=" * 60)
    print(f"WIKI FROM SESSION: {len(sessions)} new session(s) of {len(all_sessions)} candidate(s)")
    print(f"  backend   : {backend}")
    print(f"  session dir: {args.session_dir}")
    print(f"  wiki root  : {args.wiki_root}")
    print(f"  cumulative : {len(state)} sessions already indexed")
    print("=" * 60)

    summary_rows: list[dict] = []
    new_state = dict(state)
    for sp in sessions:
        msgs = _extract_messages(sp, args.max_chars, args.max_messages)
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
            "lint_total": sum(int(v) for v in (wiki.get("lint_summary") or {}).values()),
        })

        # Mark this session as indexed only after a successful run
        new_state[sp.stem] = sp.stat().st_mtime

    _save_state(args.wiki_root, new_state)

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
    print(f"wiki totals (this run): {wiki_total_dlg} dialogue + {wiki_total_ent} entities + {wiki_total_topic} topic")
    print(f"cumulative: {len(new_state)} sessions indexed")
    print(f"wiki root: {args.wiki_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
