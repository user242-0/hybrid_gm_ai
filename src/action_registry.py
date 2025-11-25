"""Lightweight action dispatcher used by the director auto-step."""

from __future__ import annotations

from typing import Any, Dict

from src.action_definitions import get_action_def


def _ensure_meter(world: Dict[str, Any], key: str) -> Dict[str, Any]:
    meter = world.get(key)
    if not isinstance(meter, dict):
        meter = {}
        world[key] = meter
    return meter


def ensure_emotion(world: Dict[str, Any]) -> None:
    emo = world.setdefault("emotion", {})
    emo.setdefault("R", 127)
    emo.setdefault("G", 127)
    emo.setdefault("B", 127)

def relax_emotion(world, rate=0.02):
    emo = world.get("emotion", {})
    for ch in ("R","G","B"):
        v = emo.get(ch, 127)
        v = v + (127 - v) * rate    # 2%だけ中庸へ
        emo[ch] = int(v)

def apply_emotion_delta(world: Dict[str, Any], action_id: str) -> None:
    ensure_emotion(world)
    emo = world["emotion"]
    delta = get_action_def(action_id).get("emotion_delta") or {}
    for ch in ("R", "G", "B"):
        if ch in delta:
            v = emo.get(ch, 127)
            d = delta.get(ch, 0)

            # 中心(127)からの距離 0.0〜1.0
            dist = abs(v - 127) / 127.0
            # 端に近いほどスケールを小さく（中心1.0 → 端0.3くらい）
            scale = 1.0 - 0.7 * dist
            d_scaled = int(d * scale)

            v = v + d_scaled
            # ここでだけ clamp（80〜180 とか）
            v = max(0, min(255, v))
            emo[ch] = v
            relax_emotion(world, rate=0.02)
            #emo[ch] = int(max(80, min(180, emo.get(ch, 127) + delta[ch])))


def execute_action(world: Dict[str, Any] | None, action_id: str | None) -> None:
    """Mutate ``world`` according to the requested ``action_id``."""

    if not isinstance(world, dict) or not action_id:
        return

    ensure_emotion(world)
    ###↓
    before = world["emotion"].copy()
    ###↑
    if action_id == "check_tip":
        world["tips_checked"] = world.get("tips_checked", 0) + 1
    elif action_id == "limit_drink":
        world["sobriety_days"] = world.get("sobriety_days", 0) + 1
        entropy = _ensure_meter(world, "entropy")
        value = entropy.get("value", 0)
        entropy["value"] = max(0, int(value) - 1)
    elif action_id == "log_victim":
        world["victim_names_logged"] = world.get("victim_names_logged", 0) + 1
    elif action_id == "collect_fiber":
        world["evidence_score"] = world.get("evidence_score", 0) + 10
    elif action_id == "fix_cam_clock":
        world["cams_fixed"] = world.get("cams_fixed", 0) + 1
    elif action_id == "call_partner":
        world["partner_calls"] = world.get("partner_calls", 0) + 1
    elif action_id == "move_low_profile":
        suspicion = _ensure_meter(world, "suspicion")
        value = suspicion.get("value", 0)
        suspicion["value"] = max(0, int(value) - 1)
    elif action_id == "mark_avoid_shop":
        world["avoid_tags"] = world.get("avoid_tags", 0) + 1
    elif action_id == "file_report":
        world["report_submitted"] = world.get("report_submitted", 0) + 1
    else:
        # Fallback – no direct mutation.
        pass

    apply_emotion_delta(world, action_id)
    ###↓
    after = world["emotion"]

    print(
        f"[EMO] action={action_id} "
        f"R:{before['R']}→{after['R']} "
        f"G:{before['G']}→{after['G']} "
        f"B:{before['B']}→{after['B']}"
    )
    ###↑