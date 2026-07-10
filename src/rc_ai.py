from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from src.action_definitions import get_action_spec
from src.requirements_checker import RequirementsChecker
from src.utility.config_loader import get_rc_excluded_actions


RC_ADVISORY_SCHEMA_VERSION = "rc_advisory_v0.1"
DETECTIVE_ID = "刑事"
INQUIRY_OPERATION_TYPE = "inquiry"
FIRST_TESTIMONY_MINI_GOAL_ID = "mini_goal_first_testimony"
FIRST_INQUIRY_ACTION_ID = "choose_first_inquiry_target"
FIRST_INQUIRY_INTENT_ID = "advance_inquiry_first_testimony"


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


def generate_rc_advisory(bundle: dict) -> dict:
    """Return one read-only RC intent and preferred action without executing it."""

    context = bundle if isinstance(bundle, dict) else {}
    actor_id = context.get("actor_id")
    actor_id = actor_id if isinstance(actor_id, str) and actor_id else None

    intent = _build_intent(context, actor_id)
    if intent is None:
        return _no_safe_action_advisory(actor_id)

    action = _select_action_for_intent(context, intent)
    if action is None:
        return _no_safe_action_advisory(actor_id)

    params = action.get("params")
    if not isinstance(params, dict):
        params = {}

    return {
        "schema_version": RC_ADVISORY_SCHEMA_VERSION,
        "actor_id": actor_id,
        "interpretation": intent["interpretation"],
        "selected_intent": intent["intent_id"],
        "preferred_action_id": action["action_id"],
        "preferred_action_layer": "HUD",
        "preferred_params": deepcopy(params),
        "rationale": intent["rationale"],
        "confidence": intent["confidence"],
        "auto_execute": False,
    }


def _build_intent(bundle: dict, actor_id: str | None) -> dict | None:
    operation = bundle.get("active_operation")
    if actor_id != DETECTIVE_ID or not isinstance(operation, dict):
        return None
    if operation.get("status") != "active":
        return None
    if operation.get("type") != INQUIRY_OPERATION_TYPE:
        return None
    if operation.get("mini_goal_id") != FIRST_TESTIMONY_MINI_GOAL_ID:
        return None

    return {
        "intent_id": FIRST_INQUIRY_INTENT_ID,
        "preferred_action_id": FIRST_INQUIRY_ACTION_ID,
        "interpretation": "聞き込みOperationが進行中で、最初の証言を固める段階にいる。",
        "rationale": (
            "active inquiry OperationのMiniGoalに直接対応する利用可能候補だから。"
        ),
        "confidence": 1.0,
    }


def _select_action_for_intent(bundle: dict, intent: dict) -> dict | None:
    actions = bundle.get("available_actions")
    if not isinstance(actions, dict):
        return None
    hud_actions = actions.get("hud")
    if not isinstance(hud_actions, list):
        return None

    preferred_action_id = intent.get("preferred_action_id")
    for action in hud_actions:
        if not isinstance(action, dict):
            continue
        if action.get("rc_ai_eligible") is False:
            continue
        action_layer = action.get("action_layer")
        if action_layer not in (None, "HUD"):
            continue
        if action.get("action_id") == preferred_action_id:
            return action
    return None


def _no_safe_action_advisory(actor_id: str | None) -> dict:
    return {
        "schema_version": RC_ADVISORY_SCHEMA_VERSION,
        "actor_id": actor_id,
        "interpretation": "現在の文脈から安全に選べる行動意図がない。",
        "selected_intent": "no_safe_action",
        "preferred_action_id": None,
        "preferred_action_layer": None,
        "preferred_params": {},
        "rationale": "明示的に対応する利用可能候補がない。",
        "confidence": 0.0,
        "auto_execute": False,
    }


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
