from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from src.action_definitions import get_action_spec
from src.requirements_checker import RequirementsChecker
from src.utility.config_loader import get_rc_excluded_actions


def select_action(rc_char, game_state, available):
    checker = RequirementsChecker(game_state, rc_char)

    # デバッグログ用フラグ
    verbose = game_state.get("_rc_ai_verbose", False)

    # ❶ RC除外リストでフィルタ
    excluded = get_rc_excluded_actions()
    filtered = [c for c in available if c.action_key not in excluded]

    if verbose and len(filtered) < len(available):
        removed = [c.action_key for c in available if c.action_key in excluded]
        print(f"[RC_AI] {rc_char.name}: 除外 {removed}")

    # ❷ switch_character は最優先（除外されていなければ）
    for c in filtered:
        if c.action_key == "switch_character" and c.is_available(checker):
            if verbose:
                print(f"[RC_AI] {rc_char.name}: switch_character を選択")
            return c

    # ❸ 通常時は緑から抽選
    green = [
        c for c in filtered if c.emotion_axis == "green" and c.is_available(checker)
    ]

    if not green:
        if verbose:
            print(f"[RC_AI] {rc_char.name}: 緑アクションなし → None")
        return None

    from random import choices as rnd_choices

    weights = [c.emotion_value for c in green]

    # ログ出力: 候補一覧と重み
    if verbose:
        candidates = ", ".join(f"{c.label}({c.emotion_value})" for c in green)
        print(f"[RC_AI] {rc_char.name}: 緑候補=[{candidates}]")

    selected = rnd_choices(green, weights=weights, k=1)[0]

    if verbose:
        print(f"[RC_AI] {rc_char.name}: → {selected.label} を選択")

    return selected


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
        spec = get_action_spec(aid)
        delta = spec.emotion_delta if spec else {}
        if not isinstance(delta, dict):
            delta = {}
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
