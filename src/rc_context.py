"""Read-only RC context bundle derived from persisted world state.

available_actions is a snapshot of candidates that appear usable now. If a
future RC_AI returns a preferred action, runtime execution must still recheck
the existing ActionPipeline/Director gates before applying any effect.
"""

from __future__ import annotations

from typing import Any

from src.actor_operations import get_active_operation
from src.choice_definitions import get_available_choices
from src.perceived_world import build_perceived_world


META_ACTION_IDS = {"switch_character", "set_emotion"}


def build_rc_context_bundle(actor_id: str, game_state: dict, director) -> dict:
    """Build a YAML/JSON-safe read-only bundle for future RC_AI advisory input."""

    state = game_state if isinstance(game_state, dict) else {}
    world = _resolve_director_world(state)
    context_state = _context_game_state(state, world)

    actor_mode = _actor_mode(actor_id, world, director)
    active_operation = _active_operation_summary(get_active_operation(world, actor_id))

    return _to_safe_value(
        {
            "actor_id": actor_id,
            "actor_profile": _actor_profile(actor_id, state),
            "actor_mode": actor_mode,
            "micro_goal": _micro_goal_summary(actor_id, world),
            "active_operation": active_operation,
            "perceived_world": build_perceived_world(actor_id, world),
            "available_actions": _available_actions(
                actor_id,
                context_state,
                world,
                director,
                actor_mode,
            ),
            "recent_memory": [],
            "notes": [],
        }
    )


def _resolve_director_world(game_state: dict[str, Any]) -> dict[str, Any]:
    world = game_state.get("director_world")
    if isinstance(world, dict):
        return world
    world = game_state.get("world")
    if isinstance(world, dict):
        return world
    return {}


def _context_game_state(
    game_state: dict[str, Any],
    world: dict[str, Any],
) -> dict[str, Any]:
    context = dict(game_state)
    context.setdefault("director_world", world)
    context.setdefault("world", world)
    return context


def _actor_profile(actor_id: str, game_state: dict[str, Any]) -> dict[str, Any]:
    actor = _actor_object(actor_id, game_state)
    label = getattr(actor, "label", None) or getattr(actor, "name", None) or actor_id
    return {"id": actor_id, "label": label}


def _actor_object(actor_id: str, game_state: dict[str, Any]) -> Any:
    party = game_state.get("party")
    if isinstance(party, dict):
        actor = party.get(actor_id)
        if actor is not None:
            return actor
    active = game_state.get("active_char")
    if getattr(active, "name", None) == actor_id:
        return active
    return None


def _actor_mode(actor_id: str, world: dict[str, Any], director) -> str | None:
    if hasattr(director, "get_actor_mode"):
        mode = director.get_actor_mode(world, actor_id, fallback_mode=getattr(director, "mode", None))
        if isinstance(mode, str) and mode:
            return mode

    actor_modes = world.get("actor_modes")
    if isinstance(actor_modes, dict):
        mode = actor_modes.get(actor_id)
        if isinstance(mode, str) and mode:
            return mode
    mode = getattr(director, "mode", None)
    return mode if isinstance(mode, str) and mode else None


def _micro_goal_summary(actor_id: str, world: dict[str, Any]) -> dict[str, Any] | None:
    actor_goals = world.get("actor_micro_goals")
    if not isinstance(actor_goals, dict):
        return None
    state = actor_goals.get(actor_id)
    if not isinstance(state, dict):
        return None

    label = state.get("text") or state.get("label")
    if not isinstance(label, str) or not label:
        return None

    summary: dict[str, Any] = {"label": label}
    for source_key, target_key in (
        ("id", "id"),
        ("action_id", "action_id"),
        ("action", "action_id"),
        ("mode", "mode"),
    ):
        value = state.get(source_key)
        if isinstance(value, str) and value:
            summary[target_key] = value
    return summary


def _active_operation_summary(operation: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(operation, dict):
        return None

    mini_goal = operation.get("mini_goal")
    mini_goal_label = None
    if isinstance(mini_goal, dict):
        value = mini_goal.get("label") or mini_goal.get("id")
        if isinstance(value, str) and value:
            mini_goal_label = value

    return {
        "type": operation.get("type") if isinstance(operation.get("type"), str) else None,
        "label": operation.get("label") if isinstance(operation.get("label"), str) else None,
        "status": operation.get("status") if isinstance(operation.get("status"), str) else None,
        "phase": operation.get("phase") if isinstance(operation.get("phase"), str) else None,
        "mini_goal": mini_goal_label,
    }


def _available_actions(
    actor_id: str,
    game_state: dict[str, Any],
    world: dict[str, Any],
    director,
    actor_mode: str | None,
) -> dict[str, list[dict[str, Any]]]:
    actions: dict[str, list[dict[str, Any]]] = {"gui": [], "hud": [], "meta": []}

    for choice in _gui_choices(actor_id, game_state):
        normalized = _normalize_choice(choice)
        bucket = "meta" if normalized["action_id"] in META_ACTION_IDS else "gui"
        actions[bucket].append(normalized)

    for record in _hud_action_records(actor_id, world, game_state, director, actor_mode):
        normalized = _normalize_hud_action(record, _tpo_candidate_lookup(director))
        if normalized is not None:
            actions["hud"].append(normalized)

    return actions


def _gui_choices(actor_id: str, game_state: dict[str, Any]) -> list[Any]:
    actor = _actor_object(actor_id, game_state)
    if actor is None:
        return []
    return list(get_available_choices(actor, game_state))


def _normalize_choice(choice: Any) -> dict[str, Any]:
    action_id = getattr(choice, "action_key", None)
    if not isinstance(action_id, str) or not action_id:
        action_id = ""

    layer = "META" if action_id in META_ACTION_IDS else "GUI"
    return {
        "action_id": action_id,
        "label": str(getattr(choice, "label", None) or action_id),
        "action_layer": layer,
        "params": _to_safe_value(getattr(choice, "params", {}) or {}),
        "source": "choice_definitions",
        "rc_ai_eligible": action_id not in META_ACTION_IDS,
    }


def _hud_action_records(
    actor_id: str,
    world: dict[str, Any],
    game_state: dict[str, Any],
    director,
    actor_mode: str | None,
) -> list[dict[str, Any]]:
    if not hasattr(director, "list_actions_for_actor"):
        return []
    return list(
        director.list_actions_for_actor(
            actor_id,
            actor_mode,
            world=world,
            game_state=game_state,
        )
    )


def _tpo_candidate_lookup(director) -> dict[str, dict[str, Any]]:
    candidates = (
        getattr(director, "goals_dict", {}) or {}
    ).get("hud_actions", {}).get("tpo_candidates", [])
    lookup: dict[str, dict[str, Any]] = {}
    if not isinstance(candidates, list):
        return lookup
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        action_id = candidate.get("id") or candidate.get("action") or candidate.get("action_id")
        if isinstance(action_id, str) and action_id:
            lookup[action_id] = candidate
    return lookup


def _normalize_hud_action(
    record: dict[str, Any],
    tpo_candidates: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    action_id = record.get("action_id") or record.get("action") or record.get("id")
    if not isinstance(action_id, str) or not action_id:
        return None

    candidate = tpo_candidates.get(action_id, {})
    required_operation_type = candidate.get("required_operation_type")
    source = "operation_conditioned_hud" if required_operation_type else "tpo_candidate"
    if not candidate:
        source = "director_micro_goal"

    normalized: dict[str, Any] = {
        "action_id": action_id,
        "label": str(record.get("label") or candidate.get("label") or action_id),
        "action_layer": "HUD",
        "source": source,
        "rc_ai_eligible": True,
    }
    time_min = record.get("time_min")
    if isinstance(time_min, (int, float)):
        normalized["time_min"] = int(time_min)
    if isinstance(required_operation_type, str) and required_operation_type:
        normalized["required_operation_type"] = required_operation_type
    return normalized


def _to_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else str(value)
    if isinstance(value, list):
        return [_to_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_to_safe_value(item) for item in value]
    if isinstance(value, set):
        return [_to_safe_value(item) for item in sorted(value, key=str)]
    if isinstance(value, dict):
        return {str(key): _to_safe_value(item) for key, item in value.items()}
    return str(value)


def format_rc_context_summary(bundle: dict[str, Any] | None) -> str:
    """Return a compact debug-only summary; callers decide where to display it."""

    if not isinstance(bundle, dict):
        return ""

    actor_id = bundle.get("actor_id") or "?"
    actor_mode = bundle.get("actor_mode") or "?"
    perceived = bundle.get("perceived_world")
    location = perceived.get("location") if isinstance(perceived, dict) else "?"
    actions = bundle.get("available_actions")
    if not isinstance(actions, dict):
        actions = {}
    counts = ", ".join(
        f"{layer}:{len(items) if isinstance(items, list) else 0}"
        for layer, items in actions.items()
    )
    return f"RCContext({actor_id}): {location} / {actor_mode} / actions[{counts}]"
