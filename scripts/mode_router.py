"""5-mode router for mini-mp-agent skill.

Modes (per Phase 1 plan):
  qa       - 1 LLM call, <2s, ~500 tokens
  task     - PWR max_iter=1, ~10s, ~1500 tokens
  discuss  - 5 persona parallel, ~20s, ~3000 tokens
  auto     - full PWR + Reflect, ~30s, ~2500 tokens (DEFAULT)
  sprint   - auto + cross-session recall + wiki persist, ~40s, ~3500 tokens

Usage:
    from mini_mp_agent.scripts.mode_router import route, detect_mode
    result = route("find X", mode="auto")          # explicit mode
    result = route("find X")                        # auto-detect
    mode = detect_mode("对比 mp 和 mini-mp")          # "discuss"

Design: M-ModeRouter-001 (imp=0.7)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# -------- keyword sets for detect_mode --------

MODE_KEYWORDS: dict[str, list[str]] = {
    "qa":       ["what is", "how to", "why", "explain", "解释", "什么是", "怎么", "为什么"],
    "task":     ["做", "fix", "修", "create", "写", "实现", "build", "ship", "做一个"],
    "discuss":  ["对比", "评估", "选哪个", "vs", "compare", "讨论", "discussion"],
    "sprint":   ["全栈", "多步", "完整", "ship it", "项目", "一整套", "全套", "entire"],
    # "auto" is default; no keywords
}

MODE_COST: dict[str, dict] = {
    "qa":      {"latency_s": 2,  "tokens": 500},
    "task":    {"latency_s": 10, "tokens": 1500},
    "discuss": {"latency_s": 20, "tokens": 3000},
    "auto":    {"latency_s": 30, "tokens": 2500},
    "sprint":  {"latency_s": 40, "tokens": 3500},
}

VALID_MODES = set(MODE_KEYWORDS.keys()) | {"auto"}

# Tie-breaker priority (higher wins on equal score). Encodes:
# "if both task and sprint hit, sprint wins (more ambitious)"
# "discuss beats task (asks for analysis)"
# "qa loses to anything else (lowest-cost intent)"
MODE_PRIORITY: dict[str, int] = {
    "sprint":  40,
    "discuss": 30,
    "task":    20,
    "qa":      10,
    "auto":     0,
}


@dataclass
class ModeDecision:
    """Result of mode detection."""
    mode: str
    scores: dict[str, int]
    matched_keywords: dict[str, list[str]] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "scores": self.scores,
            "matched_keywords": self.matched_keywords,
            "reason": self.reason,
        }


def detect_mode(task: str) -> ModeDecision:
    """Detect mode from task description by keyword scoring.

    Returns ModeDecision with mode + scores + matched keywords.
    Default mode is "auto" if no keywords hit.
    """
    scores: dict[str, int] = {m: 0 for m in MODE_KEYWORDS}
    matched: dict[str, list[str]] = {m: [] for m in MODE_KEYWORDS}
    task_lower = task.lower()

    for mode, kws in MODE_KEYWORDS.items():
        for kw in kws:
            # word boundary for English, substring for Chinese
            if re.search(rf"\b{re.escape(kw)}\b", task_lower, re.IGNORECASE):
                scores[mode] += 1
                matched[mode].append(kw)
            elif kw in task:  # Chinese: substring
                scores[mode] += 1
                matched[mode].append(kw)

    if max(scores.values()) == 0:
        return ModeDecision(mode="auto", scores=scores, reason="no keyword match → default")

    # Sort by (-score, -priority) so highest score wins; on tie, highest priority wins
    ranked = sorted(
        scores.items(),
        key=lambda kv: (-kv[1], -MODE_PRIORITY.get(kv[0], 0)),
    )
    best_mode = ranked[0][0]
    tied = [m for m, s in scores.items() if s == scores[best_mode]]
    best_matches = matched[best_mode]
    reason_parts = [f"score {scores[best_mode]} on {best_mode}"]
    if len(tied) > 1:
        reason_parts.append(f"tie with {tied}; priority {MODE_PRIORITY[best_mode]} wins")
    reason_parts.append(f"via {best_matches[:3]}")
    return ModeDecision(
        mode=best_mode,
        scores=scores,
        matched_keywords={k: v for k, v in matched.items() if v},
        reason="; ".join(reason_parts),
    )


def _validate_mode(mode: str) -> str:
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode: {mode}; valid: {sorted(VALID_MODES)}")
    return mode


def route(
    task: str,
    mode: Optional[str] = None,
    handlers: Optional[dict[str, Callable]] = None,
) -> dict:
    """Route task to handler. Returns dict with mode/decision/result.

    Args:
        task:    the user's task description
        mode:    explicit mode ("qa"/"task"/"discuss"/"auto"/"sprint") or None for auto-detect
        handlers: optional dict {mode: fn(task)}. Defaults to handlers.py stubs.
    """
    if mode is None:
        decision = detect_mode(task)
        mode = decision.mode
    else:
        _validate_mode(mode)
        decision = detect_mode(task)
        decision.mode = mode
        decision.reason = f"explicit mode={mode} (overrode detected {decision.mode})"

    if handlers is None:
        from .handlers import HANDLERS  # lazy import (handlers may grow)
        handlers = HANDLERS

    _validate_mode(mode)
    handler = handlers[mode]
    result = handler(task)

    return {
        "mode": mode,
        "decision": decision.to_dict(),
        "cost": MODE_COST[mode],
        "result": result,
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m mini_mp_agent.scripts.mode_router '<task>' [mode]")
        sys.exit(1)

    task = sys.argv[1]
    explicit_mode = sys.argv[2] if len(sys.argv) > 2 else None
    out = route(task, mode=explicit_mode)
    print(json.dumps(out, ensure_ascii=False, indent=2))
