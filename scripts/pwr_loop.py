"""PWR Loop state machine — Plan → Work → Review → (Reflect if fail) → replan.

Phase 2 ship (2026-07-17 23:21).

Usage:
    from scripts.pwr_loop import run_pwr, PWRIteration, PWRResult
    result = run_pwr("做一个 hello world", max_iter=3)
    print(result.final_result, result.success)

Phase 2 uses stub_llm by default. Phase 3 wires real LLM via injectable llm fn.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from .roles import REFLECTOR_SYSTEM, REVIEWER_SYSTEM, PLANNER_SYSTEM, WORKER_SYSTEM
from .methods_tree import MethodsTree as _MethodsTree  # integrated since Phase 7


# -------- LLM Callable type --------
# Phase 2: stub_llm. Phase 3: real LLM injection.

LLMCallable = Callable[[str, str], str]  # (system_prompt, user_msg) -> response_text


def stub_llm(system_prompt: str, user_msg: str) -> str:
    """Phase 2 stub LLM. Returns role-stamped deterministic echo.

    Phase 3 will inject real LLM (via minimp agent's existing provider).
    """
    role = "unknown"
    if "Planner" in system_prompt:
        role = "planner"
    elif "Worker" in system_prompt:
        role = "worker"
    elif "Reviewer" in system_prompt:
        role = "reviewer"
    elif "Reflector" in system_prompt:
        role = "reflector"
    # Deterministic echo — same input → same output (for testing)
    head = (user_msg or "")[:60].replace("\n", " ")
    return f"[STUB-{role}] processed: {head}"


def make_score_llm(target_score: float = 0.9) -> LLMCallable:
    """Factory: build an LLM that always returns a fixed Reviewer score."""
    def llm(system_prompt: str, user_msg: str) -> str:
        if "Reviewer" in system_prompt:
            return (
                "## Review\n"
                "syntax: pass - ok\n"
                "length: pass - ok\n"
                "relevance: pass - ok\n"
                "coherence: pass - ok\n\n"
                f"Score: {target_score:.2f}\n"
                "Notes: all checks passed\n"
            )
        return stub_llm(system_prompt, user_msg)
    return llm


DEFAULT_LLM: LLMCallable = stub_llm


# -------- Method Tree (Phase 7 integration) --------

_METHOD_TREE: Optional[_MethodsTree] = None


def get_method_tree() -> _MethodsTree:
    """Return the singleton MethodsTree instance.

    Lazily loaded from default location (scripts/../methods/).
    Used by Planner to consult the work method tree before generating a plan.
    """
    global _METHOD_TREE
    if _METHOD_TREE is None:
        _METHOD_TREE = _MethodsTree()
    return _METHOD_TREE


def reset_method_tree() -> None:
    """Reset singleton (used by tests with custom root)."""
    global _METHOD_TREE
    _METHOD_TREE = None


# -------- Data structures --------

@dataclass
class PWRIteration:
    iter: int
    role_history: list[str] = field(default_factory=list)
    plan: str = ""
    result: str = ""
    review_score: float = 0.0
    review_notes: str = ""
    reflection: str = ""
    needs_replan: bool = False


@dataclass
class PWRResult:
    task: str
    iterations: list[PWRIteration]
    final_result: str
    total_iters: int
    success: bool
    mode: str  # "task" / "auto" / "sprint"
    failure_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "iterations": [asdict(it) for it in self.iterations],
            "final_result": self.final_result,
            "total_iters": self.total_iters,
            "success": self.success,
            "mode": self.mode,
            "failure_reason": self.failure_reason,
        }


# -------- Helpers --------

REVIEW_SCORE_PATTERN = re.compile(r"[Ss]core[:\s=]+(\d+\.?\d*)")


def parse_review_score(review_text: str) -> float:
    """Parse score 0-1 from review text. Default 0.5 on no match."""
    if not review_text:
        return 0.5
    m = REVIEW_SCORE_PATTERN.search(review_text)
    if m:
        try:
            v = float(m.group(1))
            if 0 <= v <= 1:
                return v
            # If > 1, treat as percentage
            if 1 < v <= 100:
                return v / 100.0
        except ValueError:
            pass
    # Fallback: any decimal in text
    m = re.search(r"(\d\.\d+)", review_text)
    if m:
        try:
            v = float(m.group(1))
            if 0 <= v <= 1:
                return v
        except ValueError:
            pass
    return 0.5  # ambiguous default


# -------- Main loop --------

def run_pwr(
    task: str,
    max_iter: int = 3,
    threshold: float = 0.8,
    llm: Optional[LLMCallable] = None,
    mode: str = "auto",
) -> PWRResult:
    """Run PWR loop. Phase 2 main API.

    Args:
        task:      user task description
        max_iter:  max iterations (default 3). Each iter = Plan+Work+Review (+optional Reflect)
        threshold: success score threshold (default 0.8). Score >= threshold → success
        llm:       injectable LLM (system_prompt, user_msg) -> response_text. Default stub_llm.
        mode:      "task" (max_iter=1), "auto" (max_iter=3), "sprint" (auto + wiki)

    Returns:
        PWRResult with all iterations + final result + success flag.
    """
    if max_iter < 1:
        raise ValueError(f"max_iter must be >= 1; got {max_iter}")
    if not (0 < threshold <= 1):
        raise ValueError(f"threshold must be in (0, 1]; got {threshold}")

    llm = llm or DEFAULT_LLM
    iterations: list[PWRIteration] = []
    current_task = task

    for i in range(1, max_iter + 1):
        it = PWRIteration(iter=i)

        # 1. PLAN
        plan = llm(PLANNER_SYSTEM, f"task: {current_task}\niter: {i}/{max_iter}")
        it.plan = plan
        it.role_history.append("planner")

        # 2. WORK
        work = llm(WORKER_SYSTEM, f"plan: {plan}\ntask: {current_task}")
        it.result = work
        it.role_history.append("worker")

        # 3. REVIEW
        review_text = llm(REVIEWER_SYSTEM, f"plan: {plan}\nresult: {work}")
        it.review_notes = review_text
        it.review_score = parse_review_score(review_text)
        it.role_history.append("reviewer")

        # 4. SUCCESS check
        if it.review_score >= threshold:
            it.needs_replan = False
            iterations.append(it)
            return PWRResult(
                task=task, iterations=iterations, final_result=it.result,
                total_iters=i, success=True, mode=mode,
            )

        # 5. REFLECT (if not last iter)
        if i < max_iter:
            reflect_text = llm(
                REFLECTOR_SYSTEM,
                f"plan: {plan}\nresult: {work}\nreview: {review_text}\niter: {i}",
            )
            it.reflection = reflect_text
            it.needs_replan = True
            it.role_history.append("reflector")
            # Inject reflection into next iter's task context
            current_task = f"{task}\n[Reflection iter {i}: {reflect_text[:200]}]"

        iterations.append(it)

    # All iters exhausted, not successful
    return PWRResult(
        task=task, iterations=iterations,
        final_result=iterations[-1].result if iterations else "",
        total_iters=len(iterations), success=False, mode=mode,
        failure_reason=f"score {iterations[-1].review_score:.2f} < threshold {threshold:.2f} after {len(iterations)} iters",
    )


# -------- Convenience wrappers per mode --------

def run_task(task: str, llm: Optional[LLMCallable] = None) -> PWRResult:
    """task mode: 1 iter only."""
    return run_pwr(task, max_iter=1, llm=llm, mode="task")


def run_auto(task: str, llm: Optional[LLMCallable] = None) -> PWRResult:
    """auto mode: 3 iter default."""
    return run_pwr(task, max_iter=3, llm=llm, mode="auto")


def run_sprint(task: str, llm: Optional[LLMCallable] = None) -> PWRResult:
    """sprint mode: same as auto + wiki persistence hook (Phase 4).

    Phase 2: same as auto, with mode="sprint" marker.
    """
    result = run_pwr(task, max_iter=3, llm=llm, mode="sprint")
    result.failure_reason = result.failure_reason or ""  # ensure field exists
    return result


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m mini_mp_agent.scripts.pwr_loop <task> [max_iter]")
        sys.exit(1)

    task = sys.argv[1]
    max_iter = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    result = run_pwr(task, max_iter=max_iter)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
