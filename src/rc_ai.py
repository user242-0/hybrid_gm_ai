from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.action_definitions import get_action_def
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

    from random import choices as rnd_choices

    weights = [c.emotion_value for c in green]
    return rnd_choices(green, weights=weights, k=1)[0]


def get_emotion(world: Dict) -> Dict[str, float]:
    emo = world.get("emotion") if isinstance(world, dict) else {}
    r = (emo or {}).get("R", 127) / 255.0
    g = (emo or {}).get("G", 127) / 255.0
    b = (emo or {}).get("B", 255) / 255.0
    return {"R": r, "G": g, "B": b}


def emotion_weights(emotion: Dict[str, float]) -> Dict[str, float]:
    r, g, b = emotion["R"], emotion["G"], emotion["B"]
    return {
        "w_micro": 0.4 + 0.4 * g,
        "w_relief": 0.3 + 0.5 * r,
        "w_empathy": 0.2 + 0.6 * b,
        "w_novelty": 0.2 + 0.5 * r - 0.2 * g,
    }


def pick_action(
    world: Dict,
    mode: str,
    actions: List[Dict],
    micro_hint: Optional[str],
) -> Tuple[Optional[str], int, str]:
    """Return an ``(action_id, minutes, reason)`` tuple for the protagonist."""

    if not actions:
        return None, 0, "no-actions"

    emo = get_emotion(world)
    w = emotion_weights(emo)

    last = world.get("_last_action_id") if isinstance(world, dict) else None

    def emo_score_for_action(aid: str) -> float:
        adef = get_action_def(aid)
        delta = adef.get("emotion_delta") or {}
        dR = delta.get("R", 0)
        dG = delta.get("G", 0)
        dB = delta.get("B", 0)

        s_relief = w["w_relief"] * max(0.0, emo["R"] * (-dR / 20.0))
        s_control = w["w_micro"] * max(0.0, emo["G"] * (dG / 20.0))
        s_empathy = w["w_empathy"] * max(0.0, emo["B"] * (dB / 20.0))
        return s_relief + s_control + s_empathy

    def base_score(a: Dict) -> float:
        s = 0.0
        aid = a.get("action")
        t = int(a.get("time_min", 5)) if a.get("time_min") is not None else 5

        if micro_hint and a.get("text") and micro_hint.split(" ")[0] in a["text"]:
            s += 30

        s += max(0, 10 - min(t, 10)) * 0.5

        if last and aid == last:
            s -= 10

        s += emo_score_for_action(aid)
        return s

    ranked = sorted(actions, key=base_score, reverse=True)
    best = ranked[0]
    try:
        minutes = int(best.get("time_min", 5))
    except (TypeError, ValueError):
        minutes = 5
    return best.get("action"), max(0, minutes), "rc_ai-rgb-v1"
