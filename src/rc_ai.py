from __future__ import annotations

from random import choices as rnd_choices
from typing import Dict, List, Optional, Tuple

from src.requirements_checker import RequirementsChecker


def select_action(rc_char, game_state, available):
    checker = RequirementsChecker(game_state, rc_char)

    # ❶ switch_character は最優先（input_pending 中でも許可）
    for c in available:
        if c.action_key == "switch_character" and c.is_available(checker):
            return c

    # ❷ 通常時は緑から抽選
    green = [
        c for c in available if c.emotion_axis == "green" and c.is_available(checker)
    ]

    if not green:
        return None

    weights = [c.emotion_value for c in green]
    return rnd_choices(green, weights=weights, k=1)[0]


def pick_action(
    world: Dict,
    mode: str,
    actions: List[Dict],
    micro_hint: Optional[str],
) -> Tuple[Optional[str], int, str]:
    """Return an ``(action_id, minutes, reason)`` tuple for the protagonist."""

    if not actions:
        return None, 0, "no-actions"

    def score(action: Dict) -> float:
        s = 0.0
        action_id = action.get("action")

        # 1) MicroGoal priority
        if micro_hint and isinstance(world, dict):
            recommended_id = world.get("_recommended_action_id")
            if recommended_id and action_id == recommended_id:
                s += 100

        if micro_hint and action.get("text"):
            first_word = micro_hint.split(" ")[0]
            if first_word and first_word in action["text"]:
                s += 50

        # 2) Prefer feasible actions if ``can_do`` helper exists
        try:
            from src.action_registry import can_do  # type: ignore

            if callable(can_do) and action_id and can_do(world, action_id):
                s += 30
        except Exception:
            pass

        # 3) Slight bias towards shorter actions
        try:
            duration = int(action.get("time_min", 5))
        except (TypeError, ValueError):
            duration = 5
        s += max(0, 10 - min(duration, 10)) * 0.5

        # 4) Avoid repeating the last action if possible
        last = world.get("_last_action_id") if isinstance(world, dict) else None
        if last and action_id == last:
            s -= 10

        return s

    ranked = sorted(actions, key=score, reverse=True)
    best = ranked[0]
    try:
        minutes = int(best.get("time_min", 5))
    except (TypeError, ValueError):
        minutes = 5
    return best.get("action"), max(0, minutes), "rc_ai-v0"
