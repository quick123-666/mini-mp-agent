"""Phase 5: Entity extractor for wiki enrichment.

Lightweight rule-based extractor (no LLM):
- capitalized word sequences (English)
- known AgentPlatform/mp/mini-mp project names (hard-coded alias table)
- Chinese noun phrases (heuristic: 2-4 chars after 常见名词 particle)

Returns list of {entity, type, confidence, aliases}.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Set


# hard-coded alias table — extend as the wiki grows
ALIAS_TABLE = {
    "mp":          {"canonical": "mp",            "type": "tool",     "aliases": ["meta-planner", "the planner"]},
    "mini-mp":     {"canonical": "mini-mp",       "type": "tool",     "aliases": ["mini-mp-agent", "minimp"]},
    "AgentPlatform":       {"canonical": "AgentPlatform",         "type": "platform", "aliases": ["agent-platform", "OpenClaw"]},
    "OpenClaw":    {"canonical": "OpenClaw",      "type": "platform", "aliases": ["openclaw"]},
    "Aris":        {"canonical": "Aris",          "type": "agent",    "aliases": ["aris bot", "aris_chat_proxy"]},
    "user":       {"canonical": "user",         "type": "person",   "aliases": ["用户", "老板"]},
    "Karpathy":    {"canonical": "Karpathy",      "type": "person",   "aliases": ["karpathy"]},
    "MEMORY.md":   {"canonical": "MEMORY.md",     "type": "file",     "aliases": ["memory.md"]},
    "wiki_store":  {"canonical": "wiki_store",    "type": "tool",     "aliases": ["wiki", "the wiki"]},
    "atomic_write": {"canonical": "atomic_write", "type": "tool",     "aliases": ["atomic write"]},
    "task_queue":  {"canonical": "task_queue",    "type": "tool",     "aliases": ["task queue"]},
    "PWR":         {"canonical": "PWR Loop",      "type": "concept",  "aliases": ["PWR loop", "Plan-Work-Review"]},
    "FizzBuzz":    {"canonical": "FizzBuzz",      "type": "concept",  "aliases": ["fizz buzz"]},
    "MAP-Elites":  {"canonical": "MAP-Elites",    "type": "concept",  "aliases": ["map elites", "map-elites"]},
}

# file-like patterns
FILE_RE = re.compile(r"\b[\w\-./\\]+\.(py|md|json|yaml|yml|ts|js|sh|ps1)\b", re.IGNORECASE)
# English capitalized noun phrase (2+ capitalized words)
EN_PHRASE_RE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){1,3})\b")
# URL
URL_RE = re.compile(r"https?://[^\s)\]]+")
# Chinese noun phrase: 2-4 chars; trailing particle is trimmed in post-processing
ZH_PHRASE_RE = re.compile(r"[\u4e00-\u9fff]{2,4}")
# Particles commonly attached to nouns (trim from phrase end)
ZH_PARTICLE_CHARS = set("的了是有在和与及或也但就并着过")
# Common verb/adjective stopwords to exclude
ZH_STOPWORDS = {
    "我们", "你们", "他们", "这个", "那个", "什么", "怎么", "可以", "应该",
    "讨论", "实现", "测试", "运行", "使用", "考虑", "希望", "认为", "觉得",
    "今天", "明天", "昨天", "现在", "以后", "之前", "然后", "所以",
}
# NEW: any phrase CONTAINING these substrings is a noise phrase (quantity words,
# locative particles, pronouns, time words, common verbs). Matched as substring
# anywhere in the candidate phrase.
ZH_NOISE_SUBSTRINGS = (
    # quantity + measure words
    "一个", "两个", "三个", "几个", "多个", "这个", "那个", "每个", "所有",
    "一些", "一下", "几个", "无数", "许多",
    # pronouns + locative
    "我", "你", "他", "她", "它", "我们", "你们", "他们",
    "这里", "那里", "哪里", "这里", "里面", "外面", "上面", "下面", "中间",
    "里", "中", "内", "外", "上", "下",
    # time
    "今天", "明天", "昨天", "刚才", "现在", "以后", "之前", "后来", "之后",
    "刚才", "一会儿",
    # common verbs
    "写", "读", "看", "听", "说", "做", "想", "是", "有", "在", "到",
    "跑", "调用", "使用", "处理", "运行", "测试", "配置", "安装", "下载",
    "调用", "调用", "跑", "跑通", "执行", "打开", "关闭", "启动", "停止",
    "读", "读取", "写", "写入", "建", "创建", "删", "删除", "改", "修改",
    "跑", "查", "查找", "搜索", "获取", "获得", "得到",
    # common filler
    "请", "建议", "应该", "可以", "需要", "要求", "希望",
)
# NEW: 2-char phrases (the noisiest) are downgraded to confidence 0.3 so they
# get filtered out at the default min_confidence=0.5. 3-4 char phrases keep 0.5.
ZH_TRIGRAMS_REQUIRED = True  # require at least 3 chars for a non-fallback entity


def _match_alias(text_lower: str) -> List[Dict[str, Any]]:
    """Match known aliases (case-insensitive, longest first)."""
    found = []
    seen = set()
    for canonical, meta in sorted(ALIAS_TABLE.items(), key=lambda kv: -len(kv[0])):
        # canonical and all aliases
        candidates = [canonical] + meta["aliases"]
        for cand in candidates:
            cand_lower = cand.lower()
            if cand_lower in seen:
                continue
            if cand_lower in text_lower:
                # boundary check: word boundary for English, char boundary for Chinese
                idx = text_lower.find(cand_lower)
                # verify it's not part of a longer word
                if cand_lower.isascii():
                    before_ok = idx == 0 or not text_lower[idx-1].isalnum()
                    after_pos = idx + len(cand_lower)
                    after_ok = after_pos >= len(text_lower) or not text_lower[after_pos].isalnum()
                    if not (before_ok and after_ok):
                        continue
                found.append({
                    "entity": meta["canonical"],
                    "type": meta["type"],
                    "confidence": 0.95,
                    "matched_as": cand,
                })
                seen.add(cand_lower)
                seen.add(meta["canonical"].lower())
                break
    return found


def _match_files(text: str) -> List[Dict[str, Any]]:
    return [
        {"entity": m.group(0), "type": "file", "confidence": 0.90, "matched_as": m.group(0)}
        for m in FILE_RE.finditer(text)
    ]


def _match_urls(text: str) -> List[Dict[str, Any]]:
    return [
        {"entity": m.group(0), "type": "url", "confidence": 0.99, "matched_as": m.group(0)}
        for m in URL_RE.finditer(text)
    ]


def _match_english_phrases(text: str) -> List[Dict[str, Any]]:
    """Multi-word capitalized phrases not already in alias table."""
    found = []
    for m in EN_PHRASE_RE.finditer(text):
        phrase = m.group(1)
        # skip if it's already in alias table
        if any(phrase.lower() == c.lower() for c in ALIAS_TABLE):
            continue
        if any(phrase.lower() == a.lower() for meta in ALIAS_TABLE.values() for a in meta["aliases"]):
            continue
        # skip common false positives
        if phrase.lower() in {"the", "and", "for", "with", "from"}:
            continue
        found.append({
            "entity": phrase,
            "type": "concept",
            "confidence": 0.65,
            "matched_as": phrase,
        })
    return found


def _match_chinese_phrases(text: str) -> List[Dict[str, Any]]:
    """Chinese noun phrases — heuristic, low confidence.

    Strategy: find every 2-4 char Chinese span, then:
    - trim trailing particle chars (了/的/是/有/在/和/与/及/或/也/但/就/并/着/过)
    - skip if shorter than 2 chars after trim
    - skip if in ZH_STOPWORDS common-verb list
    - skip if contains any ZH_NOISE_SUBSTRINGS (quantities, pronouns, time, common verbs)
    - 2-char phrases get downgraded to confidence 0.3 (filtered at default 0.5)
    - 3-4 char phrases get 0.5 (current)
    """
    found = []
    seen = set()
    for m in ZH_PHRASE_RE.finditer(text):
        phrase = m.group(0)
        # Trim trailing particles
        while phrase and phrase[-1] in ZH_PARTICLE_CHARS:
            phrase = phrase[:-1]
        if len(phrase) < 2:
            continue
        if phrase in ZH_STOPWORDS:
            continue
        # NEW: drop phrases that contain any noise substring anywhere
        if any(ns in phrase for ns in ZH_NOISE_SUBSTRINGS):
            continue
        if phrase in seen:
            continue
        seen.add(phrase)
        # NEW: 2-char phrases are too noisy (most of the 1009-entity flood
        # came from 2-char chunks like 个测试, 服务器, 调用). Downgrade them
        # to 0.3 so the default min_confidence=0.5 filter drops them.
        confidence = 0.30 if len(phrase) == 2 else 0.50
        found.append({
            "entity": phrase,
            "type": "concept",
            "confidence": confidence,
            "matched_as": phrase,
        })
    return found


def extract_entities(text: str, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
    """Extract entities from text. Returns list of {entity, type, confidence, matched_as}."""
    if not text:
        return []

    text_lower = text.lower()
    all_entities = []
    all_entities.extend(_match_alias(text_lower))
    all_entities.extend(_match_files(text))
    all_entities.extend(_match_urls(text))
    all_entities.extend(_match_english_phrases(text))
    all_entities.extend(_match_chinese_phrases(text))

    # dedup by (entity.lower(), type)
    seen = set()
    unique = []
    for e in all_entities:
        key = (e["entity"].lower(), e["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(e)

    # filter by confidence
    filtered = [e for e in unique if e["confidence"] >= min_confidence]
    # sort: high confidence first, then alias matches
    filtered.sort(key=lambda e: (-e["confidence"], e["entity"]))
    return filtered


def group_by_type(entities: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Group entity names by type. Returns {type: [entity, ...]}."""
    groups: Dict[str, List[str]] = {}
    for e in entities:
        groups.setdefault(e["type"], []).append(e["entity"])
    return groups


if __name__ == "__main__":
    sample = (
        "Today we shipped entity_extractor.py. The mp dispatcher and mini-mp-agent work together. "
        "user tested it in MEMORY.md. See https://github.com/x/y for code. "
        "中文测试: 我们讨论了 PWR Loop 的实现细节, Karpathy 也写了相关笔记."
    )
    for e in extract_entities(sample):
        print(f"  [{e['type']:9s}] {e['entity']:30s} conf={e['confidence']:.2f} matched={e['matched_as']!r}")
