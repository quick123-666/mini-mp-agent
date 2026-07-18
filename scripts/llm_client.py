"""Phase 6: Real LLM client for mini-mp-agent.

Wraps the configured provider (default: minimax-plan/MiniMax-M3 via anthropic-messages)
into a sync LLMCallable that handlers can call directly.

Graceful degradation: if API key missing or network fails, falls back to a deterministic
mock so tests and demos still work offline.

Usage:
    from scripts.llm_client import get_default_llm, make_score_llm
    llm = get_default_llm()
    response = llm("You are Aris.", "hi")
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Callable, Optional

from .pwr_loop import LLMCallable


# ---------- Provider config (read from agent-config.json models.providers) ----------

DEFAULT_PROVIDER = "minimax-plan"
DEFAULT_MODEL = "MiniMax-M3"
DEFAULT_BASE_URL = "https://api.minimax.chat"  # overridable via AGENT_LLM_BASE_URL env


def _read_openclaw_api_key(provider: str = DEFAULT_PROVIDER) -> Optional[str]:
    """Try to read API key from agent-config.json. Returns None if not found."""
    cfg_path = os.path.expanduser("~/.config/agent-platform/agent-config.json")
    if not os.path.exists(cfg_path):
        return None
    try:
        import json
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        # agent-config.json redacts apiKey to "__OPENCLAW_REDACTED__" in config.get,
        # but on disk it's the real key
        providers = cfg.get("models", {}).get("providers", {})
        prov = providers.get(provider, {})
        key = prov.get("apiKey")
        if key and key != "__OPENCLAW_REDACTED__":
            return key
    except Exception:
        return None
    return None


def _has_real_key(provider: str = DEFAULT_PROVIDER) -> bool:
    """Check if we can attempt a real LLM call.

    Real key sources (priority):
    1. ~/.config/agent-platform/agent-config.json (provider's apiKey field, if not redacted)
    2. env var like MINIMAX_API_KEY / MINIMAX_PLAN_API_KEY
    """
    if _read_openclaw_api_key(provider):
        return True
    env_candidates = [
        f"{provider.upper().replace('-', '_')}_API_KEY",
        "LLM_API_KEY",
    ]
    return any(os.environ.get(v) for v in env_candidates)


# ---------- Real LLM call ----------

def _call_anthropic(base_url: str, api_key: str, model: str, system: str, user_msg: str, timeout_s: float = 30.0) -> str:
    """Make an Anthropic-format messages call. Returns the response text.

    For MiniMax-style base_url (https://api.minimax.chat), the anthropic
    endpoint lives under /anthropic/v1/messages. We detect that automatically.
    """
    try:
        import urllib.request
        import json as _json

        body = _json.dumps({
            "model": model,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user_msg}],
        }).encode("utf-8")

        # Endpoint resolution:
        # - if user already passed a /anthropic segment, use as-is
        # - if base_url is api.minimax.chat (and not OpenAI), insert /anthropic
        # - otherwise, default /v1/messages
        if "/anthropic" in base_url:
            endpoint = base_url.rstrip("/") + "/v1/messages"
        elif "minimax.chat" in base_url and "openai" not in base_url.lower():
            endpoint = base_url.rstrip("/") + "/anthropic/v1/messages"
        else:
            endpoint = base_url.rstrip("/") + "/v1/messages"

        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = _json.loads(resp.read().decode("utf-8"))

        # Anthropic format: content_blocks[].text
        blocks = data.get("content", [])
        if isinstance(blocks, list):
            for b in blocks:
                if isinstance(b, dict) and b.get("type") == "text":
                    return b.get("text", "")
        # Fallback: top-level text field
        return data.get("text", data.get("completion", ""))
    except Exception as e:
        raise RuntimeError(f"anthropic call failed: {e}") from e


def _real_llm(system: str, user_msg: str, provider: str = DEFAULT_PROVIDER, model: str = DEFAULT_MODEL, base_url: Optional[str] = None) -> str:
    """Real LLM call. Tries anthropic-messages format at /v1/messages.

    base_url resolution (priority):
      1. explicit argument
      2. AGENT_LLM_BASE_URL env
      3. DEFAULT_BASE_URL (https://api.minimax.chat)
    """
    key = _read_openclaw_api_key(provider) or os.environ.get(f"{provider.upper().replace('-', '_')}_API_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError("no API key available for provider " + provider)
    url = base_url or os.environ.get("AGENT_LLM_BASE_URL") or DEFAULT_BASE_URL
    # strip trailing slash for clean concat
    url = url.rstrip("/")
    return _call_anthropic(url, key, model, system, user_msg)


# ---------- Mock / stub LLM (deterministic for tests) ----------

def _mock_llm(system: str, user_msg: str) -> str:
    """Deterministic mock for tests. Echoes structure from system + length-aware reply.

    Pattern: "[STUB-{role_signature}] processed: {first_60_chars_of_msg}"
    """
    role_signature = "unknown"
    sys_lower = system.lower()
    if "analyst" in sys_lower:
        role_signature = "analyst"
    elif "critic" in sys_lower:
        role_signature = "critic"
    elif "advocate" in sys_lower:
        role_signature = "advocate"
    elif "skeptic" in sys_lower:
        role_signature = "skeptic"
    elif "synthesizer" in sys_lower:
        role_signature = "synthesizer"
    elif "planner" in sys_lower:
        role_signature = "planner"
    elif "worker" in sys_lower:
        role_signature = "worker"
    elif "reviewer" in sys_lower or "review" in sys_lower:
        role_signature = "reviewer"
    elif "reflector" in sys_lower or "reflect" in sys_lower:
        role_signature = "reflector"
    elif "you are" in sys_lower:
        # extract role after "You are"
        m = re.search(r"you are a[n]?\s+([\w\-]+)", sys_lower)
        if m:
            role_signature = m.group(1)

    summary = user_msg[:60].strip()
    if not summary:
        summary = "(empty)"
    return f"[STUB-{role_signature}] processed: {summary}"


# ---------- Score LLM (PWR review) ----------

def make_score_llm(llm: LLMCallable) -> Callable[[str, str], float]:
    """Build a score function from an LLM. Parses '0.85' or '85%' from response.

    Used by PWR loop to score each iteration's review.
    """
    def _score(prompt: str, _expected: str) -> float:
        try:
            response = llm("You are a strict reviewer. Reply with only a number 0.0-1.0", prompt)
            m = re.search(r"(\d+(?:\.\d+)?)\s*(%)?", response)
            if m:
                val = float(m.group(1))
                is_pct = m.group(2) == "%"
                if is_pct:
                    val /= 100.0
                return max(0.0, min(1.0, val))
        except Exception:
            pass
        return 0.5  # fallback when no number found
    return _score


# ---------- Default factory ----------

def get_default_llm(*, force_real: bool = False, force_mock: bool = False) -> LLMCallable:
    """Return the default LLM callable.

    Priority:
    - force_mock=True → mock_llm
    - force_real=True → real_llm (will raise on failure)
    - default: real_llm if API key available, else mock_llm
    """
    if force_mock:
        return _mock_llm
    if force_real or _has_real_key():
        return _real_llm
    return _mock_llm


def has_real_llm() -> bool:
    """True iff a real API key is configured."""
    return _has_real_key()


if __name__ == "__main__":
    import json as _json

    llm = get_default_llm()
    print("Using:", "REAL" if llm is _real_llm else "MOCK")

    response = llm("You are an analyst.", "give me 3 facts about mini-mp")
    print("Response:", response)

    score_fn = make_score_llm(llm)
    score = score_fn("Review this implementation: 168 tests pass, 47KB code", "expect 0.9")
    print("Score:", score)
