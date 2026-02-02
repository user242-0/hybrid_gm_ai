# src/utility/llm_guard.py
"""
LLM呼び出しのガード機能
- mode: off / player_only / rc_only / all
- allow_actions: 許可するアクションのリスト
- rate_limit: 呼び出し頻度制限
"""

import time
from typing import Optional, Tuple
from src.utility.config_loader import get_cfg


# レート制限用の状態
_call_history = []  # [(timestamp, turn)]
_current_turn = 0


def reset_turn():
    """ターンをリセット（新しいターン開始時に呼ぶ）"""
    global _current_turn
    _current_turn += 1


def get_current_turn() -> int:
    return _current_turn


def _get_llm_config():
    cfg = get_cfg()
    return cfg.get("llm", {})


def can_call_llm(
    caller: str,  # "player" or "rc"
    action_key: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    LLM呼び出しが許可されるか判定。
    Returns: (allowed, reason)
    """
    llm_cfg = _get_llm_config()

    # デフォルト値
    mode = llm_cfg.get("mode", "off")
    allow_actions = llm_cfg.get("allow_actions", [])
    rate_limit = llm_cfg.get("rate_limit", {})
    calls_per_minute = rate_limit.get("calls_per_minute", 6)
    calls_per_turn = rate_limit.get("calls_per_turn", 1)

    # 1. モードチェック
    if mode == "off":
        return False, "llm.mode=off"

    if mode == "player_only" and caller != "player":
        return False, f"llm.mode=player_only, caller={caller}"

    if mode == "rc_only" and caller != "rc":
        return False, f"llm.mode=rc_only, caller={caller}"

    # mode == "all" は全て許可

    # 2. アクションチェック
    if action_key and allow_actions:
        if action_key not in allow_actions:
            return False, f"action {action_key} not in allow_actions"

    # 3. レート制限チェック
    now = time.time()
    global _call_history

    # 古い履歴を削除（1分以上前）
    _call_history = [(t, turn) for t, turn in _call_history if now - t < 60]

    # calls_per_minute チェック
    if len(_call_history) >= calls_per_minute:
        return False, f"rate_limit: {len(_call_history)}/{calls_per_minute} calls/min"

    # calls_per_turn チェック
    turn_calls = sum(1 for _, turn in _call_history if turn == _current_turn)
    if turn_calls >= calls_per_turn:
        return False, f"rate_limit: {turn_calls}/{calls_per_turn} calls/turn"

    return True, "allowed"


def record_call():
    """LLM呼び出しを記録（許可後に呼ぶ）"""
    _call_history.append((time.time(), _current_turn))


def get_fallback_text(action: str, location: str = "どこか") -> str:
    """フォールバック用テンプレートテキスト"""
    return f"{action}。{location}の空気がわずかに揺れた。"


def log_llm_decision(allowed: bool, reason: str, caller: str, action_key: Optional[str]):
    """LLM判定ログ（最低限）"""
    status = "ALLOW" if allowed else "DENY"
    action_str = f"[{action_key}]" if action_key else ""
    print(f"[LLM] {status}: caller={caller} {action_str} ({reason})")
