"""Parse session dialogue messages into wiki entry candidates.

Phase 4 ship (2026-07-17 23:30).

Used by sprint mode to convert LCM / chat history → wiki entries.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

# Chinese + English stop words
_STOP_WORDS = {
    "的", "了", "是", "在", "我", "你", "他", "它", "我们", "你们",
    "请", "吗", "呢", "啊", "吧", "啦", "嗯", "哦", "哈",
    "一个", "一些", "这个", "那个", "什么", "怎么", "为什么",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "for", "on", "with", "at", "by",
}


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text → url-safe slug. Keeps Chinese chars."""
    s = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text.lower())
    s = re.sub(r"\s+", "-", s.strip())
    return s[:max_len] or "untitled"


def classify_intent(text: str) -> str:
    """Classify message intent. Discussion > question priority (compare/discuss wins)."""
    text_lower = text.lower()
    # discussion first — discussion keywords imply a question but the intent is "compare"
    if "选" in text or "对比" in text or "vs" in text_lower or "比较" in text:
        return "discussion"
    if "?" in text or "吗" in text or "为什么" in text or "怎么" in text:
        return "question"
    if text.startswith("/") or text.startswith("做") or "ship" in text_lower:
        return "command"
    return "statement"


def extract_keywords(text: str, top_k: int = 5) -> list[str]:
    """Crude keyword extraction: 2+ char tokens (incl. hyphens), dedup, no stopwords."""
    # \w includes letters/digits/underscore; \u4e00-\u9fff = Chinese; - allows kebab-case
    tokens = re.findall(r"[\w\u4e00-\u9fff-]{2,}", text)
    seen: list[str] = []
    for t in tokens:
        if t.lower() in _STOP_WORDS:
            continue
        if t not in seen:
            seen.append(t)
        if len(seen) >= top_k:
            break
    return seen


def parse_messages(messages: Iterable[dict]) -> list[dict]:
    """Convert [{role, content, ts}] → list of wiki entry candidates.

    Each entry: ts, role, content, slug, intent, keywords.
    """
    entries: list[dict] = []
    for msg in messages:
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        ts = msg.get("ts") or datetime.now().isoformat(timespec="seconds")
        role = msg.get("role", "unknown")
        slug = slugify(content)
        intent = classify_intent(content)
        keywords = extract_keywords(content)
        entries.append({
            "ts": ts,
            "role": role,
            "content": content,
            "slug": slug,
            "intent": intent,
            "keywords": keywords,
        })
    return entries


def group_by_intent(entries: list[dict]) -> dict[str, list[dict]]:
    """Group entries by intent. Returns {intent: [entries]}."""
    groups: dict[str, list[dict]] = {}
    for e in entries:
        groups.setdefault(e["intent"], []).append(e)
    return groups


if __name__ == "__main__":
    import json

    sample = [
        {"role": "user", "content": "什么是 mp?", "ts": "2026-07-17T23:30:00"},
        {"role": "assistant", "content": "mp = meta-planner, 一个 PWR 循环工具.", "ts": "2026-07-17T23:30:05"},
        {"role": "user", "content": "做一个 hello world", "ts": "2026-07-17T23:30:10"},
        {"role": "user", "content": "对比 mp 和 mini-mp", "ts": "2026-07-17T23:30:15"},
    ]
    entries = parse_messages(sample)
    print(json.dumps(entries, ensure_ascii=False, indent=2))
    print("\n--- by intent ---")
    print(json.dumps(group_by_intent(entries), ensure_ascii=False, indent=2))
