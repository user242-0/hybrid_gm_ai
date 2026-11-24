"""Authorization boundary for LLM requests."""

import os

from src.utility.config_loader import get_cfg


_MODES = frozenset({"off", "dialogue_only", "player_only", "rc_only", "all"})


def can_call_llm(
    caller: str,
    action_key: str | None = None,
) -> tuple[bool, str]:
    """Reject existing callers until there is a dedicated Dialogue send path."""
    if os.getenv("GM_USE_STUB") == "1" or os.getenv("CI") == "true":
        return False, "forced_stub"

    try:
        cfg = get_cfg()
    except Exception:
        return False, "config_unavailable"

    llm_cfg = cfg.get("llm") if isinstance(cfg, dict) else None
    mode = llm_cfg.get("mode") if isinstance(llm_cfg, dict) else None
    if not isinstance(mode, str) or mode not in _MODES:
        return False, "invalid_or_missing_llm_mode"
    if mode == "off":
        return False, "llm.mode=off"
    if mode == "dialogue_only":
        return False, "dialogue_send_unavailable"

    # Caller labels and allow_actions cannot authorize any legacy transport.
    return False, "legacy_llm_mode_disabled"


def get_fallback_text(action: str, location: str = "どこか") -> str:
    """フォールバック用テンプレートテキスト"""
    return f"{action}。{location}の空気がわずかに揺れた。"


def log_llm_decision(allowed: bool, reason: str, caller: str, action_key: str | None):
    """LLM判定ログ（最低限）"""
    status = "ALLOW" if allowed else "DENY"
    action_str = f"[{action_key}]" if action_key else ""
    print(f"[LLM] {status}: caller={caller} {action_str} ({reason})")
